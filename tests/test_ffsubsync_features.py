import os
import sys
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main")))

from constants import (
    DEFAULT_OPTIONS,
    SYNC_TOOLS,
    is_remote_url,
)
from utils import check_file_readable, check_pgs_subtitles_usable
from subtitle_extractor import should_extract_subtitles
from sync_core import build_cmd, determine_output_path, run_sync
import call_ffsubsync


def test_is_remote_url():
    """Verify that remote streaming URLs are properly identified."""
    assert is_remote_url("http://example.com/video.mp4") is True
    assert is_remote_url("https://example.com/stream.mkv?token=123") is True
    assert is_remote_url("rtmp://live.stream/vid") is True
    assert is_remote_url("rtsp://camera.local/stream") is True
    assert is_remote_url("ftp://ftp.example.com/video.avi") is True

    assert is_remote_url("/home/user/video.mkv") is False
    assert is_remote_url("video.mp4") is False
    assert is_remote_url("C:\\Videos\\video.mp4") is False
    assert is_remote_url("") is False
    assert is_remote_url(None) is False
    assert is_remote_url(123) is False


def test_ffsubsync_options_order_and_schema():
    """Verify that ffsubsync options are correctly ordered (split_penalty directly above vad) and extract_audio_first is removed."""
    options = SYNC_TOOLS["ffsubsync"]["options"]
    keys = list(options.keys())
    assert "split_penalty" in keys
    assert "vad" in keys
    assert "extract_audio_first" not in keys

    # Split penalty must be placed immediately before vad
    vad_index = keys.index("vad")
    split_index = keys.index("split_penalty")
    assert split_index == vad_index - 1

    assert options["split_penalty"]["type"] == "slider"
    assert options["split_penalty"]["default"] == -1
    assert options["split_penalty"]["range"] == [-1, 50]

    assert "use_pgs_subtitles" in options
    assert options["use_pgs_subtitles"]["type"] == "checkbox"
    assert options["use_pgs_subtitles"]["default"] is False
    assert options["use_pgs_subtitles"]["argument"] == "--pgs-ref-stream"

    assert "multi_segment_sync" in options
    assert options["multi_segment_sync"]["type"] == "checkbox"
    assert options["multi_segment_sync"]["default"] is False

    # Check that default options dictionary contains them
    assert DEFAULT_OPTIONS["ffsubsync_split_penalty"] == -1
    assert DEFAULT_OPTIONS["ffsubsync_use_pgs_subtitles"] is False
    assert DEFAULT_OPTIONS["ffsubsync_multi_segment_sync"] is False


def test_ffsubsync_command_builder_defaults():
    """Verify default ffsubsync command generation."""
    config = dict(DEFAULT_OPTIONS)
    cmd = build_cmd(
        "ffsubsync",
        None,
        "video.mp4",
        "in.srt",
        "out.srt",
        config=config,
    )
    # Default options should not append extra split or pgs flags
    assert "--split-penalty" not in cmd
    assert "--pgs-ref-stream" not in cmd
    assert "--multi-segment-sync" not in cmd


def test_ffsubsync_command_builder_split_penalty():
    """Verify split penalty argument generation for ffsubsync."""
    # When enabled (> 0)
    config = dict(DEFAULT_OPTIONS)
    config["ffsubsync_split_penalty"] = 5
    cmd = build_cmd("ffsubsync", None, "video.mp4", "in.srt", "out.srt", config=config)
    assert "--split-penalty" in cmd
    idx = cmd.index("--split-penalty")
    assert cmd[idx + 1] == "5"

    # When disabled (-1)
    config["ffsubsync_split_penalty"] = -1
    cmd = build_cmd("ffsubsync", None, "video.mp4", "in.srt", "out.srt", config=config)
    assert "--split-penalty" not in cmd
    assert "--no-split" not in cmd


def test_ffsubsync_command_builder_flags():
    """Verify boolean flags for ffsubsync."""
    config = dict(DEFAULT_OPTIONS)
    config["ffsubsync_use_pgs_subtitles"] = True
    config["ffsubsync_multi_segment_sync"] = True

    cmd = build_cmd("ffsubsync", None, "video.mp4", "in.srt", "out.srt", config=config)
    assert "--pgs-ref-stream" in cmd
    assert "--multi-segment-sync" in cmd


def test_ffsubsync_vad_invalid_value_fallback():
    """Verify that an invalid or numeric VAD setting (e.g. 9) is sanitized and falls back to default."""
    config = dict(DEFAULT_OPTIONS)
    config["ffsubsync_vad"] = 9  # Erroneous numeric value from slider
    cmd = build_cmd("ffsubsync", None, "video.mp4", "in.srt", "out.srt", config=config)
    assert "--vad" not in cmd or cmd[cmd.index("--vad") + 1] != "9"

    config["ffsubsync_vad"] = "invalid_detector"
    cmd = build_cmd("ffsubsync", None, "video.mp4", "in.srt", "out.srt", config=config)
    assert "--vad" not in cmd or cmd[cmd.index("--vad") + 1] != "invalid_detector"


def test_determine_output_path_remote_url(tmp_path):
    """Verify determine_output_path handles remote URLs safely."""
    sub_file = str(tmp_path / "subtitle.srt")
    url = "https://example.com/videos/awesome_movie_1080p.mkv?token=abc"

    config = dict(DEFAULT_OPTIONS)

    # Next to subtitle
    config["automatic_save_location"] = "save_next_to_input_subtitle"
    out = determine_output_path(url, sub_file, config=config)
    assert os.path.dirname(out) == str(tmp_path)
    assert "subtitle" in os.path.basename(out)

    # Next to video with same filename (for URL should use URL basename in sub folder)
    config["automatic_save_location"] = "save_next_to_video_with_same_filename"
    out = determine_output_path(url, sub_file, config=config)
    assert os.path.dirname(out) == str(tmp_path)
    assert os.path.basename(out) == "awesome_movie_1080p.srt"


def test_check_file_readable_remote_url():
    """Verify check_file_readable passes for remote URLs without file access errors."""
    ok, err = check_file_readable("https://example.com/video.mp4")
    assert ok is True
    assert err == ""

    ok, err = check_file_readable("/nonexistent/file/path.mp4")
    assert ok is False
    assert err != ""


def test_should_extract_subtitles_remote_url():
    """Verify should_extract_subtitles skips embedded extraction on remote URLs."""
    config = dict(DEFAULT_OPTIONS)
    config["ffsubsync_check_video_for_subtitles"] = True

    # Remote URL should not trigger embedded extraction
    assert should_extract_subtitles("https://example.com/video.mkv", "ffsubsync", config) is False


def test_check_pgs_subtitles_usable(tmp_path):
    """Verify check_pgs_subtitles_usable correctly detects usable or missing PGS streams."""
    dummy_video = str(tmp_path / "movie.mkv")
    with open(dummy_video, "wb") as f:
        f.write(b"dummy mkv content")

    # When no PGS stream is found
    with patch("ffsubsync.speech_transformers.find_pgs_stream", return_value=None):
        usable, reason = check_pgs_subtitles_usable(dummy_video)
        assert usable is False
        assert "No PGS" in reason

    # When PGS stream is detected
    with patch("ffsubsync.speech_transformers.find_pgs_stream", return_value="0:s:0"):
        usable, reason = check_pgs_subtitles_usable(dummy_video)
        assert usable is True
        assert "Detected PGS stream 0:s:0" in reason


def test_patch_ffsubsync_pgs_timings_show_clear_pairs():
    """Verify _patch_ffsubsync_pgs_timings correctly pairs Show (size > 50) and Clear (size <= 50) packets."""
    call_ffsubsync._patch_ffsubsync_pgs_timings()
    import ffsubsync.speech_transformers as st

    mock_probe = {
        "packets": [
            {"pts_time": "117.534", "size": "15351", "duration_time": "N/A"},  # Show
            {"pts_time": "119.369", "size": "30", "duration_time": "N/A"},     # Clear
            {"pts_time": "197.447", "size": "12000", "duration_time": "N/A"},  # Show
            {"pts_time": "198.448", "size": "30", "duration_time": "N/A"},     # Clear
        ]
    }
    with patch("ffmpeg.probe", return_value=mock_probe):
        timings = st._get_pgs_timings_via_ffprobe("test.mkv", "0:s:0")
        assert timings is not None
        assert len(timings) == 2
        assert timings[0] == (117.534, 119.369)
        assert timings[1] == (197.447, 198.448)


def test_patch_preserves_upstream_behavior_for_numeric_durations():
    """Verify the patched PGS timing extraction matches upstream ffsubsync exactly when packet durations are available."""
    import call_ffsubsync

    call_ffsubsync._patch_ffsubsync_pgs_timings()
    import ffsubsync.speech_transformers as st

    orig_func = call_ffsubsync._orig_get_pgs_timings_via_ffprobe
    assert orig_func is not None

    mock_probe = {
        "packets": [
            {"pts_time": "10.0", "duration_time": "2.5", "size": "8000"},  # Show with duration
            {"pts_time": "12.5", "duration_time": "N/A", "size": "30"},    # Clear
            {"pts_time": "20.0", "duration_time": "1.0", "size": "6000"},  # Show with duration
            {"pts_time": "21.0", "duration_time": "N/A", "size": "30"},    # Clear
            {"pts_time": "30.0", "duration_time": "N/A", "size": "30"},    # Clear, no open Show
        ]
    }
    with patch("ffmpeg.probe", return_value=mock_probe):
        upstream = orig_func("test.mkv", "0:s:0")
        patched = st._get_pgs_timings_via_ffprobe("test.mkv", "0:s:0")

    assert upstream == patched == [(10.0, 12.5), (20.0, 21.0)]


def test_run_sync_pgs_fallback_when_unusable(tmp_path):
    """Verify run_sync skips --pgs-ref-stream and falls back to audio when PGS timings are unusable."""
    video_file = str(tmp_path / "movie.mkv")
    with open(video_file, "wb") as f:
        f.write(b"dummy video")

    sub_file = str(tmp_path / "movie.srt")
    with open(sub_file, "w", encoding="utf-8") as f:
        f.write("1\n00:00:01,000 --> 00:00:04,000\nHello World\n")

    config = dict(DEFAULT_OPTIONS)
    config["ffsubsync_use_pgs_subtitles"] = True

    captured_cmds = []

    def mock_run_module(mod, cmd_args, callbacks, **kwargs):
        captured_cmds.append(cmd_args)
        out_path = cmd_args[cmd_args.index("-o") + 1]
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("1\n00:00:01,000 --> 00:00:04,000\nSynced\n")
        return 0

    with patch("utils.check_pgs_subtitles_usable", return_value=(False, "no usable timing packets")), \
         patch("sync_core.run_module_tool", side_effect=mock_run_module):
        logs = []
        callbacks = MagicMock()
        callbacks._log.side_effect = lambda msg, color=None: logs.append((str(msg), color))
        callbacks._cancelled.return_value = False
        result = run_sync(video_file, sub_file, tool="ffsubsync", config=config, callbacks=callbacks)
        assert any("Checking for PGS subtitles..." in m for m, c in logs)
        assert result.ok is True
        # Verify that --pgs-ref-stream was NOT passed due to fallback
        assert len(captured_cmds) == 1
        assert "--pgs-ref-stream" not in captured_cmds[0]


def test_call_ffsubsync_pgs_patch_fallback(tmp_path):
    """Verify that call_ffsubsync patches PGSSpeechTransformer to safely fall back to audio VAD."""
    call_ffsubsync._patch_ffsubsync_pgs_fallback()
    import ffsubsync.speech_transformers as st
    import numpy as np

    transformer = st.PGSSpeechTransformer(sample_rate=100)

    # When orig_fit fails with ValueError, safe_fit should fall back to VideoSpeechTransformer
    with patch("ffsubsync.speech_transformers.find_pgs_stream", return_value="0:s:0"), \
         patch("ffsubsync.speech_transformers._get_pgs_timings_via_ffprobe", side_effect=ValueError("Failed to get PGS timings")), \
         patch.object(st.VideoSpeechTransformer, "fit", return_value=None), \
         patch.object(st.VideoSpeechTransformer, "transform", return_value=np.zeros(100)):
        result = transformer.fit("some_video.mkv")
        assert result is transformer
        assert transformer.transform("some_video.mkv") is not None


def test_run_sync_with_remote_url(tmp_path):
    """Verify run_sync handles remote URLs without missing file errors."""
    sub_file = str(tmp_path / "test.srt")
    with open(sub_file, "w", encoding="utf-8") as f:
        f.write("1\n00:00:01,000 --> 00:00:04,000\nHello World\n")

    url = "https://example.com/stream.mp4"
    config = dict(DEFAULT_OPTIONS)

    with patch("sync_core.run_module_tool", return_value=0):
        result = run_sync(
            url,
            sub_file,
            tool="ffsubsync",
            config=config,
        )
        assert result.message != "reference missing"
        assert result.message != "both files missing"


def test_process_output_strips_ansi_and_stray_cursor_codes():
    """Verify process_output strips ANSI escape sequences and stray [A cursor movement codes."""
    from sync_core import process_output

    sample_output = "\n".join([
        "[A[A",
        "[A",
        "  0%|          | 0/60 [00:00<?, ?it/s]",
        "[A[A[A",
        "100%|##########| 60.0/60 [00:00<00:00, 164.38it/s]\x1b[A",
        "INFO   multi-segment sync: sampling 8 segment(s) at [0, 1457, 2913]",
        "[A[A",
        "[INFO] starting sync",
        "[A] Track A",
    ])

    cleaned, percent = process_output(sample_output, "ffsubsync")
    cleaned_lines = cleaned.split("\n")

    assert "[A[A" not in cleaned_lines
    assert "[A" not in cleaned_lines
    assert "[A[A[A" not in cleaned_lines
    assert any("multi-segment sync" in l for l in cleaned_lines)
    assert any("[INFO] starting sync" in l for l in cleaned_lines)
    assert any("[A] Track A" in l for l in cleaned_lines)
    assert percent is not None


def test_upstream_ffsubsync_pgs_support_detector():
    """Detect if upstream ffsubsync natively supports Matroska Show/Clear packet pairs without our patch.

    If upstream ffsubsync fixes this in a future release, this test emits a clear warning/notice
    so developers know the custom patch in call_ffsubsync.py is no longer necessary.
    """
    import warnings
    import call_ffsubsync

    call_ffsubsync._patch_ffsubsync_pgs_timings()
    orig_func = getattr(call_ffsubsync, "_orig_get_pgs_timings_via_ffprobe", None)
    if orig_func is None:
        return

    mock_probe = {
        "packets": [
            {"pts_time": "10.0", "size": "5000", "duration_time": "N/A"},  # Show
            {"pts_time": "12.5", "size": "30", "duration_time": "N/A"},    # Clear
        ]
    }
    with patch("ffmpeg.probe", return_value=mock_probe):
        result = orig_func("test.mkv", "0:s:0")
        if result is not None and len(result) > 0:
            warnings.warn(
                "NOTICE: Upstream ffsubsync now natively supports Matroska Show/Clear PGS packet timings! "
                "The patch _patch_ffsubsync_pgs_timings in call_ffsubsync.py may no longer be required.",
                UserWarning,
            )
