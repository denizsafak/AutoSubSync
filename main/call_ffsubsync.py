import os
import sys
import platform
from multiprocessing import freeze_support
try:
    from . import compat  # Installed package: relative import
except ImportError:
    import compat  # Direct script execution: bare import

# Monkey-patch subprocess.Popen to always use CREATE_NO_WINDOW on Windows
import subprocess

if platform.system() == "Windows":
    _orig_popen = subprocess.Popen

    def _patched_popen(*args, **kwargs):
        flags = kwargs.get("creationflags", 0)
        flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
        kwargs["creationflags"] = flags
        return _orig_popen(*args, **kwargs)

    subprocess.Popen = _patched_popen


def _get_silero_vad_model_path():
    """Locate the silero_vad.onnx model file."""
    try:
        from utils import get_resource_path
        model_path = get_resource_path("autosubsyncapp.resources.lapse", "silero_vad.onnx")
        if model_path and os.path.isfile(model_path):
            return model_path
    except Exception:
        pass

    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(base_dir, "resources", "lapse", "silero_vad.onnx")
    if os.path.isfile(candidate):
        return candidate

    if hasattr(sys, "_MEIPASS"):
        meipass_candidate = os.path.join(sys._MEIPASS, "resources", "lapse", "silero_vad.onnx")
        if os.path.isfile(meipass_candidate):
            return meipass_candidate

    try:
        from resources import lapse_download
        downloaded = lapse_download.download()
        candidate = os.path.join(os.path.dirname(downloaded), "silero_vad.onnx")
        if os.path.isfile(candidate):
            return candidate
    except Exception:
        pass

    return candidate if os.path.isfile(candidate) else None


def _patch_ffsubsync_silero():
    """Patch ffsubsync to use ONNX Runtime with silero_vad.onnx instead of requiring PyTorch."""
    try:
        import ffsubsync.speech_transformers as st
        import numpy as np
    except Exception:
        return

    _orig_make_silero = getattr(st, "_make_silero_detector", None)

    def _make_onnx_silero_detector(sample_rate: int, frame_rate: int, non_speech_label: float):
        try:
            import onnxruntime as ort
        except ImportError:
            if _orig_make_silero is not None:
                return _orig_make_silero(sample_rate, frame_rate, non_speech_label)
            raise ImportError(
                "Silero VAD requires 'onnxruntime' (or 'torch'), but neither is installed. "
                "Install onnxruntime with 'pip install onnxruntime'."
            )

        model_path = _get_silero_vad_model_path()
        if not model_path or not os.path.exists(model_path):
            if _orig_make_silero is not None:
                try:
                    return _orig_make_silero(sample_rate, frame_rate, non_speech_label)
                except Exception:
                    pass
            raise FileNotFoundError(
                f"Silero VAD ONNX model not found (searched: {model_path}). "
                "Please download the lapse/silero resource package."
            )

        opts = ort.SessionOptions()
        opts.log_severity_level = 3  # Suppress verbose ONNX logs
        session = ort.InferenceSession(model_path, opts, providers=["CPUExecutionProvider"])
        sr_model = 16000
        chunk_size = 512
        state = np.zeros((2, 1, 128), dtype=np.float32)
        sr_tensor = np.array(sr_model, dtype=np.int64)
        window_duration = 1.0 / sample_rate
        frames_per_output_window = int(window_duration * frame_rate + 0.5)

        def _detect(asegment) -> np.ndarray:
            nonlocal state
            if not isinstance(asegment, np.ndarray):
                audio = np.frombuffer(asegment, dtype=np.int16).astype(np.float32) / 32768.0
            else:
                audio = asegment.astype(np.float32) / 32768.0 if asegment.dtype == np.int16 else asegment

            if len(audio) == 0:
                return np.array([], dtype=np.float32)

            if frame_rate != sr_model:
                target_len = int(len(audio) * sr_model / frame_rate)
                if target_len == 0:
                    return np.array([non_speech_label] * max(1, len(audio) // frames_per_output_window))
                indices = np.linspace(0, len(audio) - 1, target_len)
                audio_16k = np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)
            else:
                audio_16k = audio

            num_chunks = len(audio_16k) // chunk_size
            chunk_probs = []
            for i in range(num_chunks):
                chunk = audio_16k[i * chunk_size : (i + 1) * chunk_size].reshape(1, chunk_size)
                out, state = session.run(None, {"input": chunk, "state": state, "sr": sr_tensor})
                chunk_probs.append(float(out[0][0]))

            remainder = len(audio_16k) % chunk_size
            if remainder > 0:
                pad = np.zeros(chunk_size - remainder, dtype=np.float32)
                chunk = np.concatenate([audio_16k[num_chunks * chunk_size:], pad]).reshape(1, chunk_size)
                out, state = session.run(None, {"input": chunk, "state": state, "sr": sr_tensor})
                chunk_probs.append(float(out[0][0]))

            total_output_windows = int(np.ceil(len(audio) / frames_per_output_window))
            if len(chunk_probs) == 0:
                return np.full(total_output_windows, non_speech_label, dtype=np.float32)

            chunk_times = (np.arange(len(chunk_probs)) + 0.5) * (chunk_size / sr_model)
            window_times = (np.arange(total_output_windows) + 0.5) * window_duration
            interp_probs = np.interp(window_times, chunk_times, chunk_probs)
            result = 1.0 - (1.0 - interp_probs) * (1.0 - non_speech_label)
            return result.astype(np.float32)

        return _detect

    st._make_silero_detector = _make_onnx_silero_detector


def _load_ffsubsync():
    try:
        from ffsubsync.ffsubsync import main as ffsubsync_main
        _patch_ffsubsync_silero()
        return ffsubsync_main, None
    except Exception as e:
        return None, e


def cli_entry(args=None):
    """
    Entry point for module-based execution. Accepts a list of arguments (excluding script name),
    sets sys.argv accordingly, and calls main().
    Returns the exit code from main()..
    """
    import sys as _sys

    ffsubsync_main, import_error = _load_ffsubsync()
    if ffsubsync_main is None:
        msg = (
            "ffsubsync is not available. Install it with 'pip install ffsubsync' "
            "or 'pip install assy' to use this sync tool."
        )
        print(msg, file=_sys.stderr)
        if import_error:
            print(f"Import error: {import_error}", file=_sys.stderr)
        return 1

    old_argv = _sys.argv
    if args is not None:
        _sys.argv = [old_argv[0]] + args
    try:
        return ffsubsync_main()
    finally:
        _sys.argv = old_argv


if __name__ == "__main__":
    freeze_support()  # fix https://github.com/pyinstaller/pyinstaller/issues/4104
    sys.exit(cli_entry())

