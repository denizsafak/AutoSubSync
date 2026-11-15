import os
import sys
import json
import tempfile
import threading
import logging
import subprocess
import platform
import signal
import time
import shutil
from typing import Optional
import texts

try:
    import cchardet
except:
    cchardet = None
try:
    import chardet
except:
    chardet = None
try:
    import charset_normalizer
except:
    charset_normalizer = None
from PyQt6.QtCore import pyqtSignal, QObject
import requests
import webbrowser

logger = logging.getLogger(__name__)

# Module-level cache for config path and config data
_config_path_cache = None
_config_path_logged = False
_config_cache = None
_config_cache_lock = threading.RLock()
_locale_cache = None
default_encoding = sys.getfilesystemencoding()

# Thread-safe process creation lock
_process_lock = threading.Lock()


def create_process(cmd):
    """Create a subprocess with proper threading support and termination handling."""
    with _process_lock:
        logger.info(f"Executing: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
        env = {**os.environ, "TERM": "dumb", "COLUMNS": "70"}

        # If executing lapse, ensure LAPSE_ONNXRUNTIME and LAPSE_VAD_MODEL are provided
        if cmd and ("lapse" in os.path.basename(cmd[0]).lower()):
            exe_dir = os.path.dirname(cmd[0])
            base_dir = os.path.dirname(os.path.abspath(__file__))

            # Resolve silero_vad.onnx model path
            if "LAPSE_VAD_MODEL" not in env:
                candidates = [
                    os.path.join(exe_dir, "silero_vad.onnx"),
                    os.path.join(base_dir, "resources", "lapse", "silero_vad.onnx"),
                ]
                if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
                    candidates.append(
                        os.path.join(sys._MEIPASS, "resources", "lapse", "silero_vad.onnx")
                    )
                for candidate in candidates:
                    if os.path.isfile(candidate):
                        env["LAPSE_VAD_MODEL"] = candidate
                        break

            # Resolve onnxruntime shared library
            if "LAPSE_ONNXRUNTIME" not in env:
                lib_names = (
                    ("onnxruntime.dll",)
                    if platform.system() == "Windows"
                    else (
                        "libonnxruntime.dylib",
                        "libonnxruntime.1.dylib",
                    )
                    if platform.system() == "Darwin"
                    else ("libonnxruntime.so", "libonnxruntime.so.1")
                )
                search_dirs = [exe_dir, os.path.join(base_dir, "resources", "lapse")]
                if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
                    search_dirs.append(
                        os.path.join(sys._MEIPASS, "resources", "lapse")
                    )
                found_lib = None
                for sdir in search_dirs:
                    if os.path.isdir(sdir):
                        for lib_name in lib_names:
                            candidate = os.path.join(sdir, lib_name)
                            if os.path.isfile(candidate):
                                found_lib = candidate
                                break
                    if found_lib:
                        break

                if not found_lib:
                    try:
                        import onnxruntime

                        capi_dir = os.path.join(
                            os.path.dirname(onnxruntime.__file__), "capi"
                        )
                        if os.path.isdir(capi_dir):
                            for f in os.listdir(capi_dir):
                                if "libonnxruntime" in f or "onnxruntime.dll" in f:
                                    found_lib = os.path.join(capi_dir, f)
                                    break
                    except Exception:
                        pass

                if found_lib:
                    env["LAPSE_ONNXRUNTIME"] = found_lib

            # Resolve whisper-cli path if available
            if "LAPSE_WHISPER_CLI" not in env:
                try:
                    from resources import whisper_download

                    whisper_cli = whisper_download.installed_cli()
                    if whisper_cli:
                        env["LAPSE_WHISPER_CLI"] = whisper_cli
                        if platform.system() == "Linux":
                            whisper_dir = os.path.dirname(whisper_cli)
                            ld_path = env.get("LD_LIBRARY_PATH", "")
                            if whisper_dir and whisper_dir not in ld_path.split(":"):
                                env["LD_LIBRARY_PATH"] = (
                                    f"{whisper_dir}:{ld_path}" if ld_path else whisper_dir
                                )
                except Exception:
                    pass

        kwargs = {
            "shell": False,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "universal_newlines": False,
            "bufsize": 0,
            "env": env,
        }

        if platform.system() == "Windows" and hasattr(subprocess, "STARTUPINFO"):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            kwargs.update(
                {
                    "startupinfo": startupinfo,
                    "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
                }
            )
        elif platform.system() != "Windows":
            # On Unix-like systems, create a new session/process group via posix_spawn
            kwargs["start_new_session"] = True

        return subprocess.Popen(cmd, **kwargs)



def terminate_process_safely(process):
    """Safely terminate a process and its children using threading."""

    def _terminate():
        if not process or process.poll() is not None:
            return

        try:
            logger.info(f"Terminating process: {process.pid}")
            if platform.system() == "Windows":
                # On Windows, terminate the process group
                process.send_signal(signal.CTRL_BREAK_EVENT)
                time.sleep(0.5)
                if process.poll() is None:
                    process.terminate()
                    time.sleep(1)
                    if process.poll() is None:
                        process.kill()
            else:
                # On Unix-like systems, terminate the process group
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    time.sleep(0.5)
                    if process.poll() is None:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    # Process already terminated
                    pass
                except OSError:
                    # Fallback to direct process termination
                    process.terminate()
                    time.sleep(1)
                    if process.poll() is None:
                        process.kill()
        except Exception as e:
            logger.error(f"Error terminating process: {e}")

    # Run termination in a separate thread to avoid blocking
    threading.Thread(target=_terminate, daemon=True).start()


def create_backup(file_path):
    base_name, ext = os.path.splitext(os.path.basename(file_path))
    backup_dir = os.path.dirname(file_path)
    backup_file = os.path.join(backup_dir, f"backup_{base_name}{ext}")
    suffix = 2
    while os.path.exists(backup_file):
        backup_file = os.path.join(backup_dir, f"backup_{base_name}_{suffix}{ext}")
        suffix += 1
    shutil.copy2(file_path, backup_file)
    logger.info(f"Backup created at: {backup_file}")
    return backup_file


def detect_encoding(file_path):
    with open(file_path, "rb") as f:
        raw_data = f.read()
    detected_encoding = None
    for detectors in (cchardet, charset_normalizer, chardet):
        try:
            result = detectors.detect(raw_data)["encoding"]
        except Exception:
            continue
        if result is not None:
            detected_encoding = result
            break
    encoding = detected_encoding if detected_encoding else "utf-8"
    return encoding.lower()


def levenshtein_distance(s1, s2):
    """Compute the Levenshtein distance between s1 and s2."""
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    if not s2:
        return len(s1)
    previous = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1, 1):
        current = [i]
        for j, c2 in enumerate(s2, 1):
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (c1 != c2))
            )
        previous = current
    return previous[-1]


def find_closest_encoding(unsupported_encoding):
    from alass_encodings import enc_list

    """Return the encoding from enc_list closest to unsupported_encoding."""
    return min(
        enc_list,
        key=lambda enc: levenshtein_distance(enc.lower(), unsupported_encoding.lower()),
    )


def match_subtitle_encoding(
    input_subtitle_path, output_subtitle_path, log_window=None, target_encoding=None
):
    """
    Check if input and output subtitle files have different encodings.
    If they differ, re-encode the output file to match the target encoding.

    Args:
        input_subtitle_path (str): Path to the original input subtitle file
        output_subtitle_path (str): Path to the synced output subtitle file
        log_window: Optional log window to display results
        target_encoding (str): Target encoding to use. If None, uses input file's encoding

    Returns:
        bool: True if encoding was matched or files already match, False if failed
    """
    try:
        from constants import COLORS

        # Check if both files exist
        if not os.path.exists(input_subtitle_path) or not os.path.exists(
            output_subtitle_path
        ):
            msg = texts.CANNOT_MATCH_ENCODING_FILES_DO_NOT_EXIST
            logger.warning(msg)
            if log_window:
                log_window.append_message(msg, color=COLORS["ORANGE"])
            return False

        # Detect encodings
        input_encoding = detect_encoding(input_subtitle_path)
        output_encoding = detect_encoding(output_subtitle_path)

        # Determine the target encoding
        if target_encoding:
            final_encoding = target_encoding
        else:
            final_encoding = input_encoding

        logger.info(f"Checking subtitle encodings...")
        logger.info(f"Input subtitle encoding: {input_encoding}")
        logger.info(f"Output subtitle encoding: {output_encoding}")
        logger.info(f"Target encoding: {final_encoding}")

        # if log_window:
        #     log_window.append_message(f"Checking subtitle encodings...", color=COLORS["GREY"])

        # If encodings are the same, no action needed
        if final_encoding.lower() == output_encoding.lower():
            msg = "Subtitle encodings matched"
            logger.info(msg)
            # if log_window:
            #     log_window.append_message(msg, color=COLORS["GREY"])
            return True

        # Read output file content with detected encoding
        try:
            with open(
                output_subtitle_path, "r", encoding=output_encoding, errors="replace"
            ) as f:
                content = f.read()
        except UnicodeDecodeError:
            warning_msg = texts.FAILED_TO_READ_OUTPUT_WITH_ENCODING.format(
                encoding=output_encoding
            )
            logger.warning(warning_msg)
            if log_window:
                log_window.append_message(warning_msg, color=COLORS["ORANGE"])
            with open(
                output_subtitle_path, "r", encoding="utf-8", errors="replace"
            ) as f:
                content = f.read()

        # Write content back with target encoding
        try:
            with open(
                output_subtitle_path, "w", encoding=final_encoding, errors="replace"
            ) as f:
                f.write(content)
            success_msg = texts.CHANGED_OUTPUT_SUBTITLE_ENCODING.format(
                output_encoding=output_encoding, final_encoding=final_encoding
            )
            logger.info(success_msg)
            if log_window:
                log_window.append_message(success_msg, color=COLORS["GREY"])
            return True
        except (UnicodeEncodeError, LookupError) as e:
            error_msg = texts.FAILED_TO_REENCODE_KEEPING_ORIGINAL.format(
                final_encoding=final_encoding, error=e
            )
            logger.warning(error_msg)
            if log_window:
                log_window.append_message(error_msg, color=COLORS["ORANGE"])
            return False

    except Exception as e:
        error_msg = texts.ERROR_MATCHING_SUBTITLE_ENCODING.format(error=e)
        logger.error(error_msg)
        if log_window:
            log_window.append_message(error_msg, color=COLORS["RED"])
        return False


def get_available_encodings():
    """Get a sorted list of available encodings with user-friendly names."""
    # Dictionary mapping Python codec names to their display names
    codec_display_names = {
        # Most common encodings listed first for easy access
        "utf_8": "UTF-8",
        "latin_1": "ISO-8859-1 (Latin-1)",
        "ascii": "ASCII",
        "cp1252": "Windows-1252",
        "utf_8_sig": "UTF-8 with BOM",
        "utf_16": "UTF-16",
        "utf_16_le": "UTF-16 LE",
        "utf_16_be": "UTF-16 BE",
        "utf_32": "UTF-32",
        "utf_32_le": "UTF-32 LE",
        "utf_32_be": "UTF-32 BE",
        # East Asian encodings
        "big5": "Big5 (Chinese)",
        "big5hkscs": "Big5-HKSCS (Chinese)",
        "gb2312": "GB2312 (Chinese)",
        "gbk": "GBK (Chinese)",
        "gb18030": "GB18030 (Chinese)",
        "hz": "HZ (Chinese)",
        "cp932": "CP932 (Japanese)",
        "euc_jp": "EUC-JP (Japanese)",
        "shift_jis": "Shift-JIS (Japanese)",
        "shift_jis_2004": "Shift-JIS-2004 (Japanese)",
        "shift_jisx0213": "Shift-JISX0213 (Japanese)",
        "euc_jis_2004": "EUC-JIS-2004 (Japanese)",
        "euc_jisx0213": "EUC-JISX0213 (Japanese)",
        "iso2022_jp": "ISO-2022-JP (Japanese)",
        "iso2022_jp_1": "ISO-2022-JP-1 (Japanese)",
        "iso2022_jp_2": "ISO-2022-JP-2 (Japanese)",
        "iso2022_jp_2004": "ISO-2022-JP-2004 (Japanese)",
        "iso2022_jp_3": "ISO-2022-JP-3 (Japanese)",
        "iso2022_jp_ext": "ISO-2022-JP-EXT (Japanese)",
        "cp949": "CP949 (Korean)",
        "euc_kr": "EUC-KR (Korean)",
        "johab": "Johab (Korean)",
        "iso2022_kr": "ISO-2022-KR (Korean)",
        "cp950": "CP950 (Chinese)",
        # Cyrillic encodings
        "cp866": "CP866 (Cyrillic)",
        "cp1251": "Windows-1251 (Cyrillic)",
        "iso8859_5": "ISO-8859-5 (Cyrillic)",
        "koi8_r": "KOI8-R (Russian)",
        "koi8_u": "KOI8-U (Ukrainian)",
        "koi8_t": "KOI8-T",
        "kz1048": "KZ-1048",
        "cp1125": "CP1125 (Ukrainian)",
        "mac_cyrillic": "Mac Cyrillic",
        "ptcp154": "PTCP154 (Cyrillic Asian)",
        # European encodings
        "cp437": "CP437 (DOS)",
        "cp850": "CP850 (DOS)",
        "cp852": "CP852 (DOS)",
        "cp857": "CP857 (DOS Turkish)",
        "cp858": "CP858 (DOS with Euro)",
        "cp1250": "Windows-1250 (Central Europe)",
        "cp1253": "Windows-1253 (Greek)",
        "cp1254": "Windows-1254 (Turkish)",
        "cp1257": "Windows-1257 (Baltic)",
        "iso8859_2": "ISO-8859-2 (Central Europe)",
        "iso8859_3": "ISO-8859-3 (South Europe)",
        "iso8859_4": "ISO-8859-4 (North Europe)",
        "iso8859_9": "ISO-8859-9 (Turkish)",
        "iso8859_10": "ISO-8859-10 (Nordic)",
        "iso8859_13": "ISO-8859-13 (Baltic)",
        "iso8859_14": "ISO-8859-14 (Celtic)",
        "iso8859_15": "ISO-8859-15 (Western Europe)",
        "iso8859_16": "ISO-8859-16 (South-Eastern Europe)",
        "mac_latin2": "Mac Latin-2",
        "mac_roman": "Mac Roman",
        "mac_turkish": "Mac Turkish",
        "mac_iceland": "Mac Icelandic",
        # Middle Eastern encodings
        "cp856": "CP856 (Hebrew)",
        "cp862": "CP862 (DOS Hebrew)",
        "cp864": "CP864 (DOS Arabic)",
        "cp1255": "Windows-1255 (Hebrew)",
        "cp1256": "Windows-1256 (Arabic)",
        "iso8859_6": "ISO-8859-6 (Arabic)",
        "iso8859_7": "ISO-8859-7 (Greek)",
        "iso8859_8": "ISO-8859-8 (Hebrew)",
        "mac_greek": "Mac Greek",
        # Other encodings
        "cp037": "CP037 (IBM EBCDIC)",
        "cp273": "CP273 (IBM EBCDIC)",
        "cp424": "CP424 (IBM EBCDIC)",
        "cp500": "CP500 (IBM EBCDIC)",
        "cp720": "CP720 (Arabic)",
        "cp737": "CP737 (Greek)",
        "cp775": "CP775 (Baltic)",
        "cp855": "CP855 (DOS Cyrillic)",
        "cp860": "CP860 (Portuguese)",
        "cp861": "CP861 (Icelandic)",
        "cp863": "CP863 (Canadian)",
        "cp865": "CP865 (Nordic)",
        "cp869": "CP869 (Greek)",
        "cp874": "CP874 (Thai)",
        "cp875": "CP875 (EBCDIC Greek)",
        "cp1006": "CP1006 (Urdu)",
        "cp1026": "CP1026 (IBM EBCDIC)",
        "cp1140": "CP1140 (IBM EBCDIC)",
        "cp1258": "Windows-1258 (Vietnamese)",
        "iso8859_11": "ISO-8859-11 (Thai)",
        "utf_7": "UTF-7",
    }

    # Define the order of most common encodings
    common_encodings = [
        "ascii",
        "utf_8",
        "utf_8_sig",
        "utf_16",
        "utf_16_le",
        "utf_16_be",
        "utf_32",
        "utf_32_le",
        "utf_32_be",
        "cp1252",
        "latin_1",
    ]

    # Build result list with common encodings first, then others alphabetically
    result = []

    # Add common encodings in the specified order
    for enc in common_encodings:
        if enc in codec_display_names:
            result.append((enc, codec_display_names[enc]))

    # Add all other encodings alphabetically by display name
    for enc, name in sorted(codec_display_names.items(), key=lambda x: x[1]):
        if enc not in common_encodings:
            result.append((enc, name))

    return result


def get_user_config_path():
    global _config_path_cache, _config_path_logged
    if _config_path_cache is not None:
        return _config_path_cache
    from constants import PROGRAM_NAME
    from platformdirs import user_config_dir

    config_dir = user_config_dir(PROGRAM_NAME, appauthor=False, roaming=True)
    os.makedirs(config_dir, exist_ok=True)
    _config_path_cache = os.path.join(config_dir, "config.json")
    if not _config_path_logged:
        logger.info(f"User config path: {_config_path_cache}")
        _config_path_logged = True
    return _config_path_cache


def get_logs_directory():
    from constants import PROGRAM_NAME

    logs_dir = os.path.join(tempfile.gettempdir(), PROGRAM_NAME)
    # Create the directory if it doesn't exist (thread/process-safe)
    os.makedirs(logs_dir, exist_ok=True)

    return logs_dir


def _atomic_write_config(config_path, config_dict):
    """
    Internal helper to atomically write config dict to disk via a temporary file and fsync.
    """
    config_dir = os.path.dirname(config_path)
    os.makedirs(config_dir, exist_ok=True)

    try:
        data = json.dumps(config_dict, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to serialize config to JSON: {e}")
        return False

    tmp_path = os.path.join(config_dir, f"config.json.tmp.{os.getpid()}")

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_path, config_path)
        return True
    except Exception as e:
        logger.warning(f"Failed to write config file: {e}")
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return False


def load_config():
    """
    Load configuration with caching to avoid multiple file reads.
    Thread-safe implementation with atomic write integrity.
    """
    global _config_cache

    with _config_cache_lock:
        # Return cached config if available
        if _config_cache is not None:
            return (
                _config_cache.copy()
            )  # Return a copy to prevent external modifications

        config_path = get_user_config_path()

        if not os.path.exists(config_path):
            logger.info("Config file does not exist, using defaults")
            _config_cache = {}
            return {}

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                raise ValueError("Config file is empty (0 bytes)")

            config = json.loads(content)
            if not isinstance(config, dict):
                raise ValueError("Config root is not a dictionary")

            logger.info("Config file loaded successfully")
            _config_cache = config.copy()
            return config
        except Exception as e:
            logger.warning(f"Failed to load config ({e})")
            # Preserve corrupt config to prevent total loss before starting fresh
            try:
                corrupt_path = f"{config_path}.corrupt.{int(time.time())}"
                if os.path.exists(config_path):
                    shutil.copy2(config_path, corrupt_path)
                    logger.info(f"Preserved corrupted config at {corrupt_path}")
            except Exception:
                pass

            _config_cache = {}
            return {}


def save_config(config):
    """
    Save configuration atomically and update cache.
    Thread-safe implementation.
    """
    global _config_cache

    if not isinstance(config, dict):
        logger.warning("save_config called with non-dict config")
        return

    with _config_cache_lock:
        config_path = get_user_config_path()
        if _atomic_write_config(config_path, config):
            logger.info("Config file updated")
            _config_cache = config.copy()


def clear_config_cache():
    """
    Clear the config cache to force reload on next access.
    Useful when config needs to be reloaded from disk.
    """
    global _config_cache, _locale_cache

    with _config_cache_lock:
        _config_cache = None
        _locale_cache = None
    logger.debug("Config cache cleared")


def restart_application():
    """Restart the application, handling AppImage, frozen executables, and pip installs."""
    from PyQt6.QtWidgets import QApplication

    appimage = os.environ.get("APPIMAGE")

    try:
        if appimage:
            # Running as AppImage
            logger.info(f"Restarting AppImage: {appimage}")
            logger.info(f"AppImage exists: {os.path.exists(appimage)}")
            logger.info(f"AppImage is executable: {os.access(appimage, os.X_OK)}")
            
            # Verify the AppImage file exists and is executable
            if not os.path.exists(appimage):
                logger.error(f"AppImage file not found: {appimage}")
                return
            
            if not os.access(appimage, os.X_OK):
                logger.warning(f"AppImage not executable, attempting to set execute permission")
                try:
                    import stat
                    os.chmod(appimage, os.stat(appimage).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                except Exception as e:
                    logger.error(f"Failed to set execute permission: {e}")
            
            # Clear mount-related env vars for clean restart
            env = os.environ.copy()
            for var in ("APPDIR", "ARGV0", "OWD", "APPIMAGE_SILENT_INSTALL"):
                env.pop(var, None)
            
            # Also restore LD_LIBRARY_PATH if modified by AppImage
            if "LD_LIBRARY_PATH_ORIG" in env:
                env["LD_LIBRARY_PATH"] = env["LD_LIBRARY_PATH_ORIG"]
            elif "LD_LIBRARY_PATH" in env:
                del env["LD_LIBRARY_PATH"]
            
            cmd = [appimage] + sys.argv[1:]
            logger.info(f"Restart command: {cmd}")
            subprocess.Popen(
                cmd,
                start_new_session=True,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif getattr(sys, "frozen", False):
            # Frozen executable (PyInstaller on Windows/macOS/Linux)
            # sys.executable is the frozen executable itself
            subprocess.Popen(
                [sys.executable] + sys.argv[1:],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            # Python script or pip-installed entry point
            # sys.argv[0] contains the script/entry point path
            argv0 = sys.argv[0]

            if argv0.endswith(".py"):
                # Running as a Python script directly
                cmd = [sys.executable] + sys.argv
            else:
                # Pip-installed entry point
                # On Windows, pip creates .exe wrapper files in Scripts folder
                # sys.argv[0] may not have .exe extension, so we need to find the actual executable
                if platform.system() == "Windows":
                    # Try to find the .exe file
                    if os.path.exists(argv0 + ".exe"):
                        cmd = [argv0 + ".exe"] + sys.argv[1:]
                    elif os.path.exists(argv0):
                        cmd = sys.argv
                    else:
                        # Fallback: use python -m to run the module
                        cmd = [sys.executable, "-m", "main.main"] + sys.argv[1:]
                else:
                    # On Unix, entry points are executable scripts
                    cmd = sys.argv

            logger.info(f"Restart command: {cmd}")
            subprocess.Popen(
                cmd,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except Exception as e:
        logger.error(f"Failed to restart application: {e}")
        return

    QApplication.quit()


def get_version():
    """Return the current version of the application."""
    try:
        with open(get_resource_path("/", "VERSION"), "r") as f:
            return f.read().strip()
    except Exception:
        return "Unknown"


def get_resource_path(package, resource):
    """
    Get the path to a resource file, with fallback to local file system.

    Args:
        package (str): Package name containing the resource (e.g., 'autosubsyncapp.assets')
        resource (str): Resource filename (e.g., 'icon.ico')

    Returns:
        str: Path to the resource file, or None if not found
    """
    from importlib import resources

    # Try using importlib.resources first
    try:
        with resources.path(package, resource) as resource_path:
            if os.path.exists(resource_path):
                return str(resource_path)
    except (ImportError, FileNotFoundError):
        pass

    # Always try to resolve as a relative path from this file
    parts = package.split(".")
    rel_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), *parts[1:], resource
    )
    if os.path.exists(rel_path):
        return rel_path

    # Fallback to local file system
    try:
        # Extract the subdirectory from package name (e.g., 'assets' from 'autosubsyncapp.assets')
        subdir = package.split(".")[-1] if "." in package else package
        local_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), subdir, resource
        )
        if os.path.exists(local_path):
            return local_path
    except Exception:
        pass

    return None


def load_svg_icon(icon_path, size=20):
    """Render an SVG file into a QIcon at the given logical size.

    Reading the SVG into a pixmap ourselves avoids platform icon-loader
    caches that can keep returning the previous theme's pixmap after a
    light/dark theme switch.
    """
    from PyQt6.QtCore import QSize
    from PyQt6.QtGui import QIcon, QImageReader, QPixmap

    if not icon_path or not os.path.exists(icon_path):
        return QIcon()

    # Render larger than the logical size so the icon stays crisp on HiDPI.
    pixel_size = max(64, int(size) * 4)
    reader = QImageReader(icon_path)
    reader.setScaledSize(QSize(pixel_size, pixel_size))
    image = reader.read()
    if image.isNull():
        return QIcon(icon_path)
    return QIcon(QPixmap.fromImage(image))


def format_num(size):
    """Format file size in human readable format"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def shorten_path(path, maxlen=50):
    if len(path) <= maxlen:
        return path
    else:
        return path[: maxlen // 2 - 2] + "…" + path[-maxlen // 2 + 1 :]


def open_folder(path, parent=None):
    """
    Opens a folder in the system's file explorer.

    Args:
        path (str): Path to a file or directory to open
        parent: Optional parent widget for error messages

    Returns:
        bool: True if successful, False otherwise
    """
    from PyQt6.QtWidgets import QMessageBox
    from PyQt6.QtCore import QUrl
    from PyQt6.QtGui import QDesktopServices

    if not path:
        return False

    try:
        # Check if path is a directory (for multiple chapter files)
        if os.path.isdir(path):
            folder = path
        else:
            folder = os.path.dirname(path)

        logger.info(f"Opening folder: {folder}")
        if platform.system() == "Linux" and getattr(sys, "frozen", False):
            # When bundled with PyInstaller on Linux, LD_LIBRARY_PATH is set,
            # which can cause conflicts with system utilities like xdg-open.
            # We invoke xdg-open with a cleaned environment.
            env = os.environ.copy()
            if "LD_LIBRARY_PATH_ORIG" in env:
                env["LD_LIBRARY_PATH"] = env["LD_LIBRARY_PATH_ORIG"]
            elif "LD_LIBRARY_PATH" in env:
                del env["LD_LIBRARY_PATH"]
            subprocess.Popen(["xdg-open", folder], env=env)
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        return True
    except Exception as e:
        logger.error(f"Could not open folder: {e}")
        if parent:
            QMessageBox.critical(
                parent,
                texts.OPEN_FOLDER_ERROR_TITLE,
                texts.COULD_NOT_OPEN_FOLDER.format(error=e),
            )
        return False


def open_filedialog(
    parent_instance,
    dialog_type,
    title,
    file_filter=None,
    initial_dir=None,
    multiple=False,
):
    """Helper function for file selection dialogs that update the last used directory.

    Args:
        parent_instance: The parent widget/window for the dialog
        dialog_type: 'file-open', 'files-open', or 'directory' for different QFileDialog types
        title: Title for the dialog
        file_filter: Optional filter for file types
        initial_dir: Initial directory to open the dialog at
        multiple: Whether to allow multiple selection

    Returns:
        Selected file path(s) or None if canceled
    """
    from PyQt6.QtWidgets import QFileDialog

    config_dir = (
        parent_instance.config.get("last_used_dir", "")
        if hasattr(parent_instance, "config")
        else ""
    )
    start_dir = initial_dir or config_dir or ""

    result = None

    if dialog_type == "file-open":
        result, _ = QFileDialog.getOpenFileName(
            parent_instance, title, start_dir, file_filter or ""
        )
    elif dialog_type == "files-open":
        result, _ = QFileDialog.getOpenFileNames(
            parent_instance, title, start_dir, file_filter or ""
        )
    elif dialog_type == "directory":
        result = QFileDialog.getExistingDirectory(parent_instance, title, start_dir)

    # Update the last used directory if a file/directory was selected
    if result:
        if isinstance(result, list) and result:  # Multiple files selected
            update_config(parent_instance, "last_used_dir", os.path.dirname(result[0]))
        elif isinstance(result, str) and result:  # Single file or directory
            if dialog_type == "directory":
                update_config(parent_instance, "last_used_dir", result)
            else:
                update_config(parent_instance, "last_used_dir", os.path.dirname(result))

    return result


# Settings menu


def update_config(obj, key, value):
    from constants import DEFAULT_OPTIONS

    # logger.info(f"Updating {key} to {value}")

    obj.config[key] = value
    # Only save settings if remember_changes is enabled (default: True)
    if obj.config.get("remember_changes", DEFAULT_OPTIONS["remember_changes"]):
        save_config(obj.config)


def toggle_remember_changes(obj, checked):
    # Always save this setting to the config file, regardless of the current remember_changes value
    obj.config["remember_changes"] = checked
    save_config(obj.config)


def reset_to_defaults(parent):
    from PyQt6.QtWidgets import QMessageBox

    # Show confirmation dialog
    reply = QMessageBox.question(
        parent,
        texts.RESET_SETTINGS_TITLE,
        texts.RESET_SETTINGS_CONFIRMATION,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )

    if reply == QMessageBox.StandardButton.Yes:
        config_path = get_user_config_path()
        bak_path = f"{config_path}.bak"
        try:
            if os.path.exists(config_path):
                os.remove(config_path)
                logger.info("Config file removed for reset to defaults.")
            if os.path.exists(bak_path):
                os.remove(bak_path)
                logger.info("Backup config file removed for reset to defaults.")
            clear_config_cache()
            restart_application()
        except Exception as e:
            logger.error(f"Failed to reset settings: {e}")
            QMessageBox.critical(
                parent, texts.ERROR, texts.FAILED_TO_RESET_SETTINGS.format(error=str(e))
            )


def open_config_directory(parent=None):
    """Open the config directory in the system file manager"""
    from PyQt6.QtWidgets import QMessageBox

    try:
        config_path = get_user_config_path()
        config_dir = os.path.dirname(config_path)
        open_folder(config_dir, parent)
    except Exception as e:
        logger.error(f"Could not open config location: {e}")
        QMessageBox.critical(
            parent, texts.ERROR, texts.COULD_NOT_OPEN_CONFIG_LOCATION.format(error=e)
        )


def open_logs_directory(parent=None):
    """Open the logs directory used by the program."""
    logs_dir = get_logs_directory()
    open_folder(logs_dir, parent)


def clear_logs_directory(parent=None):
    """Delete logs directory after user confirmation."""
    from PyQt6.QtWidgets import QMessageBox

    try:
        logs_dir = get_logs_directory()

        # Count files in the directory
        total_files = len(
            [
                f
                for f in os.listdir(logs_dir)
                if os.path.isfile(os.path.join(logs_dir, f))
            ]
        )
        logger.info(
            f"Attempting to clear logs directory: {logs_dir} ({total_files} files)"
        )

        if total_files == 0:
            QMessageBox.information(
                parent, texts.LOGS_DIRECTORY_TITLE, texts.LOGS_DIRECTORY_EMPTY
            )
            return

        # Ask for confirmation with file count
        reply = QMessageBox.question(
            parent,
            texts.DELETE_LOGS_DIRECTORY_TITLE,
            texts.DELETE_LOGS_DIRECTORY_CONFIRMATION.format(total_files=total_files),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            import shutil

            # Remove the entire directory
            shutil.rmtree(logs_dir)
            logger.info("Logs directory cleared.")

            QMessageBox.information(
                parent, texts.LOGS_DIRECTORY_CLEARED_TITLE, texts.LOGS_DIRECTORY_CLEARED
            )
    except Exception as e:
        logger.error(f"Failed to clear logs directory: {e}")
        QMessageBox.critical(
            parent,
            texts.ERROR,
            texts.FAILED_TO_CLEAR_LOGS_DIRECTORY.format(error=str(e)),
        )


def safe_open_url(url):
    """Open a URL in the default browser, handling PyInstaller LD_LIBRARY_PATH issues on Linux."""
    import sys
    import platform
    import subprocess

    if platform.system() == "Linux" and getattr(sys, "frozen", False):
        # Use xdg-open with a clean environment
        env = os.environ.copy()
        if "LD_LIBRARY_PATH_ORIG" in env:
            env["LD_LIBRARY_PATH"] = env["LD_LIBRARY_PATH_ORIG"]
        elif "LD_LIBRARY_PATH" in env:
            del env["LD_LIBRARY_PATH"]
        try:
            subprocess.Popen(["xdg-open", url], env=env)
            return True
        except Exception as e:
            logger.error(f"Failed to open URL with xdg-open: {e}")
            return False
    else:
        try:
            return webbrowser.open(url, new=2)
        except Exception as e:
            logger.error(f"Failed to open URL with webbrowser: {e}")
            return False


def show_about_dialog(parent):
    """Show an About dialog with program information including GitHub link."""
    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon
    from constants import (
        PROGRAM_NAME,
        VERSION,
        PROGRAM_TAGLINE,
        PROGRAM_DESCRIPTION,
        COLORS,
        GITHUB_URL,
    )

    icon = parent.windowIcon()
    dialog = QDialog(parent)
    dialog.setWindowTitle(texts.ABOUT_PROGRAM_TITLE.format(program_name=PROGRAM_NAME))
    dialog.setWindowFlags(
        dialog.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
    )
    dialog.setFixedSize(400, 320)
    layout = QVBoxLayout(dialog)
    layout.setSpacing(10)
    header_layout = QHBoxLayout()
    icon_label = QLabel()
    if not icon.isNull():
        icon_label.setPixmap(icon.pixmap(64, 64))
    else:
        icon_label.setText("\U0001f4da")
        icon_label.setStyleSheet("font-size: 48px;")
    header_layout.addWidget(icon_label)
    title_label = QLabel(
        f"<h1 style='margin-bottom: 0;'>{PROGRAM_NAME} <span style='font-size: 12px; font-weight: normal; color: {COLORS['GREY']};'>v{VERSION}</span></h1><h3 style='margin-top: 5px;'>{PROGRAM_TAGLINE}</h3>"
    )
    title_label.setTextFormat(Qt.TextFormat.RichText)
    header_layout.addWidget(title_label, 1)
    layout.addLayout(header_layout)
    desc_label = QLabel(
        f"<p>{PROGRAM_DESCRIPTION}</p>" f"<p>{texts.VISIT_GITHUB_PAGE}</p>"
    )
    desc_label.setTextFormat(Qt.TextFormat.RichText)
    desc_label.setWordWrap(True)
    layout.addWidget(desc_label)
    github_btn = QPushButton(texts.VISIT_GITHUB_PAGE_BUTTON)
    github_btn.setIcon(QIcon(get_resource_path("autosubsyncapp.assets", "github.svg")))
    github_btn.clicked.connect(lambda: safe_open_url(GITHUB_URL))
    github_btn.setFixedHeight(32)
    layout.addWidget(github_btn)
    update_btn = QPushButton(texts.CHECK_FOR_UPDATES_BUTTON)
    update_btn.clicked.connect(lambda: manual_check_for_updates(parent))
    update_btn.setFixedHeight(32)
    layout.addWidget(update_btn)
    close_btn = QPushButton(texts.CLOSE_BUTTON)
    close_btn.clicked.connect(dialog.accept)
    close_btn.setFixedHeight(32)
    layout.addWidget(close_btn)
    dialog.exec()


def show_tool_info_dialog(parent):
    from PyQt6.QtWidgets import (
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QPushButton,
        QLabel,
        QWidget,
        QStyle,
    )
    from PyQt6.QtCore import Qt, QUrl
    from PyQt6.QtGui import QIcon, QDesktopServices
    from PyQt6.QtWidgets import QApplication
    from constants import SYNC_TOOLS, COLORS
    from utils import get_resource_path, safe_open_url
    import platform

    tool_name = getattr(parent.sync_tool_combo, "currentText", lambda: "")()
    tool = SYNC_TOOLS.get(tool_name, {})
    if not tool:
        return
    d = QDialog(parent)
    d.setWindowTitle(texts.ABOUT_PROGRAM_TITLE.format(program_name=tool_name))
    d.setWindowFlags(d.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
    main_layout = QVBoxLayout(d)
    main_layout.setSpacing(10)
    main_layout.setContentsMargins(12, 14, 12, 12)
    header = QHBoxLayout()
    icon = QLabel()
    style = (
        parent.style() if hasattr(parent, "style") else QApplication.instance().style()
    )
    info_icon = style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)
    icon.setPixmap(info_icon.pixmap(32, 32))
    header.addWidget(icon)
    version = tool.get("version", "")
    if tool_name == "lapse":
        from resources import lapse_download

        version = lapse_download.current_version(
            lapse_download.installed(tool["executable"].get(platform.system()))
        )
    t = QLabel(
        f"<h1 style='margin-bottom: 0;'>{tool_name} <span style='font-size: 12px; font-weight: normal; color: {COLORS['GREY']};'>v{version}</span></h1>"
    )
    t.setTextFormat(Qt.TextFormat.RichText)
    header.addWidget(t, 1)
    main_layout.addLayout(header)
    # Use row layouts for label-value pairs
    info_layout = QVBoxLayout()
    info_layout.setSpacing(6)
    info_layout.setContentsMargins(5, 0, 5, 5)

    def row(label_widget, value_widget):
        h = QHBoxLayout()
        h.addWidget(label_widget, alignment=Qt.AlignmentFlag.AlignTop)
        h.addWidget(value_widget, 1)
        return h

    def bold_label(text):
        lab = QLabel(f"<b>{text}</b>")
        lab.setTextFormat(Qt.TextFormat.RichText)
        return lab

    def wrap_label(text):
        if isinstance(text, list):
            text = ", ".join(str(x) for x in text)
        lab = QLabel(text)
        lab.setWordWrap(True)
        return lab

    desc = str(tool.get("description", ""))
    desc = desc.replace("<p>", "").replace("</p>", "").replace("\n", "<br>")
    desc_label = QLabel(desc)
    desc_label.setWordWrap(True)
    desc_label.setTextFormat(Qt.TextFormat.RichText)
    info_layout.addWidget(desc_label)
    typ = tool.get("type", "")
    if typ == "module":
        label = texts.MODULE_LABEL
        val = tool.get("module", "")
    elif typ == "executable":
        label = texts.EXECUTABLE_LABEL
        exe = tool.get("executable", "")
        val = exe.get(platform.system(), exe) if isinstance(exe, dict) else exe
    else:
        label = "Module/Executable"  # TODO
        val = tool.get("module", tool.get("executable", ""))
    cmd = tool.get("cmd_structure", [])
    cmd_str = " ".join(str(x) for x in cmd) if isinstance(cmd, list) else str(cmd)
    cmd_label = QLabel(f"<pre style='font-size:12px'>{cmd_str}</pre>")
    cmd_label.setTextFormat(Qt.TextFormat.RichText)
    cmd_label.setWordWrap(True)
    # Add each field as a row (label and value in same row)
    info_layout.addLayout(
        row(bold_label(texts.TYPE_LABEL), wrap_label(tool.get("type", "")))
    )
    info_layout.addLayout(row(bold_label(label + ":"), wrap_label(val)))
    info_layout.addLayout(row(bold_label(texts.COMMAND_STRUCTURE_LABEL), cmd_label))
    info_layout.addLayout(
        row(
            bold_label(texts.SUPPORTED_FORMATS_LABEL),
            wrap_label(tool.get("supported_formats", "")),
        )
    )
    info_layout.addLayout(
        row(
            bold_label(texts.SUPPORTS_SUBTITLE_REFERENCE_LABEL),
            wrap_label(
                texts.YES_LABEL
                if tool.get("supports_subtitle_as_reference", False)
                else texts.NO_LABEL
            ),
        )
    )
    form_widget = QWidget()
    form_widget.setLayout(info_layout)
    main_layout.addWidget(form_widget)
    if tool.get("github"):
        b = QPushButton(texts.VISIT_GITHUB_PAGE_BUTTON)
        b.setIcon(QIcon(get_resource_path("autosubsyncapp.assets", "github.svg")))
        b.clicked.connect(lambda: safe_open_url(tool["github"]))
        b.setFixedHeight(32)
        main_layout.addWidget(b)
    if tool.get("documentation"):
        b = QPushButton(texts.DOCUMENTATION_BUTTON)
        b.clicked.connect(lambda: safe_open_url(tool["documentation"]))
        b.setFixedHeight(32)
        main_layout.addWidget(b)
    c = QPushButton(texts.CLOSE_BUTTON)
    c.clicked.connect(d.accept)
    c.setFixedHeight(32)
    main_layout.addWidget(c)
    d.adjustSize()
    d.setFixedSize(d.sizeHint())
    d.exec()


def get_version_info(module_name):
    """Return version information of a package, compatible with PyInstaller."""
    try:
        try:
            from importlib.metadata import version
        except ImportError:
            from importlib_metadata import version  # type: ignore

        return version(module_name)
    except Exception:
        # Fallback: try to get __version__ attribute
        try:
            mod = __import__(module_name)
            return getattr(mod, "__version__", "0.0")
        except Exception:
            return "0.0"


# Update checking functionality
class UpdateSignals(QObject):
    update_available = pyqtSignal(str, str)
    up_to_date = pyqtSignal(str)
    check_failed = pyqtSignal(str)


class LapseUpdateSignals(QObject):
    update_available = pyqtSignal(str, str)
    update_complete = pyqtSignal(bool, str)
    progress = pyqtSignal(int)
    up_to_date = pyqtSignal(str)
    check_failed = pyqtSignal(str)


class UnifiedUpdateSignals(QObject):
    finished = pyqtSignal(dict)


def get_locale():
    """Get the current locale of the system using PyQt with caching."""
    global _locale_cache

    # Return cached locale if available
    if _locale_cache is not None:
        return _locale_cache

    from PyQt6.QtCore import QLocale
    from constants import LANGUAGES

    config = load_config()
    system_locale = QLocale().name()

    if config.get("language") in LANGUAGES.values():
        _locale_cache = config.get("language")
    elif system_locale in LANGUAGES.values():
        _locale_cache = system_locale
    else:
        # If not found, return default English locale
        _locale_cache = "en_US"

    return _locale_cache


def _show_update_message(parent, remote_version, local_version):
    from PyQt6.QtWidgets import QMessageBox
    from constants import GITHUB_LATEST_RELEASE_URL, PROGRAM_NAME
    from utils import safe_open_url

    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Icon.Information)
    msg_box.setWindowTitle(texts.UPDATE_AVAILABLE_TITLE)
    msg_box.setText(
        texts.NEW_VERSION_AVAILABLE.format(
            program_name=PROGRAM_NAME,
            local_version=local_version,
            remote_version=remote_version,
        )
    )
    msg_box.setInformativeText(texts.VISIT_GITHUB_DOWNLOAD_LATEST)
    msg_box.setStandardButtons(
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)
    if msg_box.exec() == QMessageBox.StandardButton.Yes:
        try:
            safe_open_url(GITHUB_LATEST_RELEASE_URL)
        except Exception:
            pass


def _show_up_to_date(parent, version):
    from PyQt6.QtWidgets import QMessageBox
    from constants import PROGRAM_NAME

    QMessageBox.information(
        parent,
        texts.UP_TO_DATE_TITLE,
        texts.RUNNING_LATEST_VERSION.format(program_name=PROGRAM_NAME, version=version),
    )


def _show_check_failed(parent, error_message):
    from PyQt6.QtWidgets import QMessageBox

    QMessageBox.warning(
        parent,
        texts.UPDATE_CHECK_FAILED_TITLE,
        texts.COULD_NOT_CHECK_FOR_UPDATES.format(error_message=error_message),
    )


def manual_check_for_updates(parent):
    """Manually check for updates for both AutoSubSync and LAPSE, displaying a single unified dialog."""
    logger.info("Manual update check triggered.")
    from constants import (
        GITHUB_VERSION_URL,
        VERSION,
        GITHUB_LATEST_RELEASE_URL,
        PROGRAM_NAME,
        SYNC_TOOLS,
    )
    import platform
    import certifi
    from PyQt6.QtWidgets import QMessageBox

    signals = UnifiedUpdateSignals()

    def handle_unified_result(res):
        app_remote = res.get("app_remote")
        app_update = res.get("app_update", False)
        app_error = res.get("app_error")
        lapse_local = res.get("lapse_local")
        lapse_remote = res.get("lapse_remote")
        lapse_update = res.get("lapse_update", False)
        lapse_error = res.get("lapse_error")

        # Scenario 1: AutoSubSync update is available
        if app_update:
            msg_box = QMessageBox(parent)
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setWindowTitle(str(texts.UPDATE_AVAILABLE_TITLE))
            app_text = str(texts.NEW_VERSION_AVAILABLE).format(
                program_name=PROGRAM_NAME,
                local_version=VERSION,
                remote_version=app_remote,
            )
            if lapse_update:
                lapse_text = str(texts.NEW_VERSION_AVAILABLE).format(
                    program_name="LAPSE",
                    local_version=lapse_local,
                    remote_version=lapse_remote,
                )
                msg_box.setText(f"{app_text}\n\n{lapse_text}")
                msg_box.setInformativeText(
                    f"{texts.VISIT_GITHUB_DOWNLOAD_LATEST}\n\n{texts.UPDATE_LAPSE_CONFIRMATION}"
                )
            else:
                msg_box.setText(app_text)
                msg_box.setInformativeText(str(texts.VISIT_GITHUB_DOWNLOAD_LATEST))
            msg_box.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)
            if msg_box.exec() == QMessageBox.StandardButton.Yes:
                safe_open_url(GITHUB_LATEST_RELEASE_URL)
                if lapse_update:
                    _perform_lapse_update(parent, lapse_remote)
            return

        # Scenario 2: AutoSubSync is up to date, but LAPSE update is available
        if app_remote and not app_update and lapse_update:
            msg_box = QMessageBox(parent)
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setWindowTitle(str(texts.UPDATE_AVAILABLE_TITLE))
            status_text = str(texts.RUNNING_LATEST_VERSION).format(
                program_name=PROGRAM_NAME,
                version=VERSION,
            )
            lapse_text = str(texts.NEW_VERSION_AVAILABLE).format(
                program_name="LAPSE",
                local_version=lapse_local,
                remote_version=lapse_remote,
            )
            msg_box.setText(f"{status_text}\n\n{lapse_text}")
            msg_box.setInformativeText(str(texts.UPDATE_LAPSE_CONFIRMATION))
            msg_box.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)
            if msg_box.exec() == QMessageBox.StandardButton.Yes:
                _perform_lapse_update(parent, lapse_remote)
            return

        # Scenario 3: Both are up to date
        if app_remote and not app_update:
            msg = str(texts.RUNNING_LATEST_VERSION).format(
                program_name=PROGRAM_NAME,
                version=VERSION,
            )
            if lapse_local and not lapse_update:
                msg += f"\n\n{str(texts.LAPSE_UP_TO_DATE).format(version=lapse_local)}"
            QMessageBox.information(parent, str(texts.UP_TO_DATE_TITLE), msg)
            return

        # Scenario 4: Update check failed
        err = app_error or lapse_error or "Unknown error"
        _show_check_failed(parent, err)

    signals.finished.connect(handle_unified_result)

    def worker():
        from resources import lapse_download

        res = {
            "app_remote": None,
            "app_update": False,
            "app_error": None,
            "lapse_local": None,
            "lapse_remote": None,
            "lapse_update": False,
            "lapse_error": None,
        }

        # Check AutoSubSync
        try:
            logger.info("Checking for updates...")
            response = requests.get(
                GITHUB_VERSION_URL, timeout=5, verify=certifi.where()
            )
            response.raise_for_status()
            remote = response.text.strip()
            res["app_remote"] = remote
            if int("".join(remote.split("."))) > int("".join(VERSION.split("."))):
                logger.info(f"Update available: {VERSION} -> {remote}")
                res["app_update"] = True
            else:
                logger.info(f"Up to date (Remote: {remote}, Local: {VERSION})")
        except Exception as e:
            logger.error(f"Update check failed: {e}")
            res["app_error"] = str(e)

        # Check LAPSE
        try:
            logger.info("Checking for LAPSE updates...")
            tool = SYNC_TOOLS.get("lapse", {})
            bundled = tool.get("executable", {}).get(platform.system())
            exe = lapse_download.installed(bundled)
            if exe and os.path.isfile(exe):
                current = lapse_download.current_version(exe)
                res["lapse_local"] = current
                latest = lapse_download.latest_version()
                res["lapse_remote"] = latest
                if latest and current and latest != current:
                    logger.info(f"LAPSE update available: {current} -> {latest}")
                    res["lapse_update"] = True
                elif latest and current:
                    logger.info(
                        f"LAPSE up to date (Remote: {latest}, Local: {current})"
                    )
            else:
                logger.info("LAPSE not installed, skipping LAPSE update check.")
        except Exception as e:
            logger.warning(f"LAPSE update check failed: {e}")
            res["lapse_error"] = str(e)

        signals.finished.emit(res)

    threading.Thread(target=worker, daemon=True).start()


def check_for_updates_startup(parent):
    from constants import GITHUB_VERSION_URL, VERSION

    signals = UpdateSignals()
    show_result = getattr(parent, "_show_update_check_result", False)
    parent._show_update_check_result = False

    signals.update_available.connect(lambda r, l: _show_update_message(parent, r, l))
    signals.up_to_date.connect(
        lambda v: _show_up_to_date(parent, v) if show_result else None
    )
    signals.check_failed.connect(
        lambda e: _show_check_failed(parent, e) if show_result else None
    )

    def worker():
        try:
            logger.info("Checking for updates...")
            import certifi

            response = requests.get(
                GITHUB_VERSION_URL, timeout=5, verify=certifi.where()
            )
            response.raise_for_status()
            remote = response.text.strip()
            try:
                if int("".join(remote.split("."))) > int("".join(VERSION.split("."))):
                    logger.info(f"Update available: {VERSION} -> {remote}")
                    signals.update_available.emit(remote, VERSION)
                elif show_result:
                    logger.info("Already up to date.")
                    signals.up_to_date.emit(VERSION)
                else:
                    logger.info(f"Up to date (Remote: {remote}, Local: {VERSION})")
            except ValueError as ve:
                logger.warning(f"Version comparison failed: {ve}")
        except Exception as e:
            logger.error(f"Update check failed: {e}")
            signals.check_failed.emit(str(e))

    threading.Thread(target=worker, daemon=True).start()


def check_for_lapse_updates(parent, manual=False):
    """Check if a new version of LAPSE is available and prompt user to update.

    Runs in a background thread and shows the update dialog on the GUI thread
    when the installed version differs from the latest release. A version the
    user previously skipped (config key "lapse_skip_version") is not prompted
    for again; manual checks are unaffected because they do not pass through
    the dialog-skip gate.
    """
    from constants import SYNC_TOOLS
    import platform

    signals = LapseUpdateSignals()
    signals.update_available.connect(
        lambda r, l: _show_lapse_update_dialog(parent, r, l)
    )

    def worker():
        try:
            logger.info("Checking for LAPSE updates...")
            from resources import lapse_download

            tool = SYNC_TOOLS.get("lapse", {})
            bundled = tool.get("executable", {}).get(platform.system())
            exe = lapse_download.installed(bundled)
            if not exe or not os.path.isfile(exe):
                logger.info("LAPSE not installed, skipping LAPSE update check.")
                return
            current = lapse_download.current_version(exe)
            if not current:
                return
            latest = lapse_download.latest_version()
            if latest and current != latest:
                skipped_version = load_config().get("lapse_skip_version", "")
                if latest == skipped_version:
                    logger.info(
                        f"LAPSE update {latest} skipped by user; not prompting."
                    )
                    return
                logger.info(f"LAPSE update available: {current} -> {latest}")
                signals.update_available.emit(latest, current)
            elif latest and current == latest:
                logger.info(f"LAPSE up to date (Remote: {latest}, Local: {current})")
        except Exception as e:
            logger.warning(f"LAPSE update check failed: {e}")

    threading.Thread(target=worker, daemon=True).start()


check_for_lapse_updates_startup = check_for_lapse_updates


def _show_lapse_update_dialog(parent, remote_version, local_version):
    """Show the LAPSE update prompt with Yes / No / 'Skip this version' actions.

    "Yes" downloads the new release right away. "No" and closing the dialog
    (X / Esc) do nothing, so the prompt reappears on the next launch.
    "Skip this version" records the offered version in the config so the
    startup check stops asking for that exact version (a newer release will
    prompt again).
    """
    from PyQt6.QtWidgets import QMessageBox

    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Icon.Information)
    msg_box.setWindowTitle(str(texts.UPDATE_AVAILABLE_TITLE))
    msg_box.setText(
        str(texts.NEW_VERSION_AVAILABLE).format(
            program_name="LAPSE",
            local_version=local_version,
            remote_version=remote_version,
        )
    )
    msg_box.setInformativeText(str(texts.UPDATE_LAPSE_CONFIRMATION))
    update_button = msg_box.addButton(QMessageBox.StandardButton.Yes)
    no_button = msg_box.addButton(QMessageBox.StandardButton.No)
    skip_button = msg_box.addButton(
        str(texts.SKIP_THIS_VERSION), QMessageBox.ButtonRole.NoRole
    )
    msg_box.setDefaultButton(update_button)
    msg_box.setEscapeButton(no_button)
    msg_box.exec()
    if msg_box.clickedButton() is skip_button:
        config = load_config()
        config["lapse_skip_version"] = remote_version
        save_config(config)
    elif msg_box.clickedButton() is update_button:
        _perform_lapse_update(parent, remote_version)


def _create_download_dialog(parent, title, initial_text):
    """Create a non-closable modal download dialog with percentage/indeterminate progress."""
    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
    from PyQt6.QtCore import Qt

    class _NonClosableDialog(QDialog):
        def __init__(self, dlg_parent=None):
            super().__init__(dlg_parent)
            self._allow_close = False

        def keyPressEvent(self, event):
            if event.key() == Qt.Key.Key_Escape and not self._allow_close:
                event.ignore()
                return
            super().keyPressEvent(event)

        def closeEvent(self, event):
            if not self._allow_close:
                event.ignore()
                return
            super().closeEvent(event)

        def finish_and_close(self):
            self._allow_close = True
            self.accept()

    dialog = _NonClosableDialog(parent)
    dialog.setWindowTitle(str(title))
    dialog.setWindowFlags(
        dialog.windowFlags()
        & ~Qt.WindowType.WindowContextHelpButtonHint
        & ~Qt.WindowType.WindowCloseButtonHint
    )
    dialog.setWindowModality(
        Qt.WindowModality.WindowModal if parent else Qt.WindowModality.ApplicationModal
    )
    dialog.setMinimumWidth(420)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(14)

    label = QLabel(str(initial_text))
    label.setWordWrap(True)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label)

    progress_bar = QProgressBar()
    progress_bar.setRange(0, 0)
    progress_bar.setTextVisible(False)
    layout.addWidget(progress_bar)

    def set_progress(pct):
        if 0 <= pct <= 100:
            if progress_bar.maximum() != 100:
                progress_bar.setRange(0, 100)
                progress_bar.setTextVisible(True)
                progress_bar.setFormat("%p%")
            progress_bar.setValue(pct)
        else:
            if progress_bar.maximum() != 0 or progress_bar.minimum() != 0:
                progress_bar.setRange(0, 0)
                progress_bar.setTextVisible(False)

    return dialog, label, progress_bar, set_progress


def _perform_lapse_update(parent, remote_version):
    from PyQt6.QtWidgets import QMessageBox

    dialog, label, _progress_bar, set_progress = _create_download_dialog(
        parent, texts.UPDATE_AVAILABLE_TITLE, texts.UPDATING_LAPSE
    )
    signals = LapseUpdateSignals(dialog)
    dialog._signals = signals

    def on_progress(pct):
        set_progress(pct)
        if pct < 0 and label.text() == str(texts.UPDATING_LAPSE):
            pass
        elif 0 <= pct <= 100:
            label.setText(f"{texts.UPDATING_LAPSE} ({pct}%)")

    def on_complete(success, message):
        dialog.finish_and_close()
        if success:
            QMessageBox.information(
                parent,
                str(texts.UPDATE_AVAILABLE_TITLE),
                str(texts.LAPSE_UPDATE_SUCCESS).format(version=message),
            )
        else:
            QMessageBox.warning(
                parent,
                str(texts.ERROR),
                str(texts.LAPSE_UPDATE_FAILED).format(error=message),
            )

    signals.progress.connect(on_progress)
    signals.update_complete.connect(on_complete)
    dialog.show()

    def download_thread():
        try:
            from resources import lapse_download

            downloaded = lapse_download.download(progress_cb=signals.progress.emit)
            if downloaded and os.path.isfile(downloaded):
                signals.update_complete.emit(True, remote_version)
            else:
                signals.update_complete.emit(False, "Binary not found after download")
        except Exception as e:
            logger.error(f"Failed to download LAPSE update: {e}")
            signals.update_complete.emit(False, str(e))

    threading.Thread(target=download_thread, daemon=True).start()


def ensure_whisper_with_dialog(parent, callback=None):
    """Ensure whisper-cli and ggml-base.bin are downloaded, showing a modal progress dialog.

    Uses a non-closable modal QDialog with percentage progress so canceling a
    sync does not interrupt the Whisper download.
    """
    from resources import whisper_download

    if not whisper_download.needs_download():
        if callback:
            callback(True)
        return

    from PyQt6.QtWidgets import QMessageBox
    from PyQt6.QtCore import QObject, pyqtSignal

    class WhisperDownloadSignals(QObject):
        status = pyqtSignal(str)
        progress = pyqtSignal(int)
        finished = pyqtSignal(bool, str)

    dialog, label, _progress_bar, set_progress = _create_download_dialog(
        parent,
        "Downloading Whisper",
        "Preparing Whisper speech filter (whisper-cli & ggml-base.bin)...",
    )
    signals = WhisperDownloadSignals(dialog)
    dialog._signals = signals

    def on_status(msg):
        label.setText(msg)
        if hasattr(parent, "log_window") and parent.log_window:
            parent.log_window.append_message(msg, color="grey")

    def on_finished(success, error_msg):
        dialog.finish_and_close()
        if success:
            if hasattr(parent, "log_window") and parent.log_window:
                parent.log_window.append_message(
                    "Whisper speech filter ready (whisper-cli & ggml-base.bin).",
                    color="green",
                )
        else:
            if hasattr(parent, "log_window") and parent.log_window:
                parent.log_window.append_message(
                    f"Whisper download failed: {error_msg}",
                    color="red",
                )
            QMessageBox.warning(
                parent,
                "Downloading Whisper",
                f"Failed to download Whisper components:\n{error_msg}",
            )
        if callback:
            callback(success)

    signals.status.connect(on_status)
    signals.progress.connect(set_progress)
    signals.finished.connect(on_finished)
    dialog.show()

    def download_thread():
        try:
            whisper_download.ensure_whisper(
                log_cb=signals.status.emit,
                progress_cb=signals.progress.emit,
            )
            signals.finished.emit(True, "")
        except Exception as e:
            logger.error(f"Failed to download Whisper components: {e}")
            signals.finished.emit(False, str(e))

    threading.Thread(target=download_thread, daemon=True).start()


def update_folder_label(label, folder_path=""):
    """Helper function to update the folder label consistently"""
    if folder_path:
        # Check if label supports rich text (has setTextFormat method)

        from constants import COLORS
        from PyQt6.QtCore import Qt

        label.setText(
            texts.SELECTED_FOLDER.format(
                color=COLORS["GREEN"], folder_path=shorten_path(folder_path)
            )
        )
        label.setTextFormat(Qt.TextFormat.RichText)
        # Set tooltip to show full path
        label.setToolTip(folder_path)
        label.show()
    else:
        label.setToolTip("")  # Clear tooltip when no folder
        label.hide()


def handle_save_location_dropdown(
    obj,
    dropdown,
    save_map,
    config_key,
    folder_key,
    label,
    default_value,
    skip_dialog=False,
):
    """
    Generic handler for save location dropdowns with folder selection and label update.
    """
    try:
        if dropdown.currentIndex() < 0:
            return
    except Exception:
        pass

    internal_val = dropdown.currentData()
    if not internal_val:
        text = dropdown.currentText()
        if not text:
            return
        internal_val = save_map.get(text)
        if not internal_val:
            for k, v in save_map.items():
                if str(k) == text or k == text:
                    internal_val = v
                    break
        if not internal_val:
            return

    # Handle folder selection case
    if internal_val == "select_destination_folder" and not skip_dialog:
        folder = open_filedialog(obj, "directory", texts.SELECT_DESTINATION_FOLDER)
        if folder:
            update_config(obj, folder_key, folder)
            update_folder_label(label, folder)
        else:
            # Revert to previous selection if cancelled
            prev = obj.config.get(config_key, default_value)
            idx = dropdown.findData(prev)
            if idx < 0:
                display = next(
                    (str(k) for k, v in save_map.items() if v == prev),
                    str(list(save_map.keys())[0]),
                )
                idx = dropdown.findText(display)
            if idx >= 0:
                dropdown.setCurrentIndex(idx)
            update_folder_label(label)
            return

    # Update config for any selection
    update_config(obj, config_key, internal_val)

    # Update label based on current selection
    if internal_val == "select_destination_folder":
        folder = obj.config.get(folder_key, "")
        update_folder_label(label, folder)
    else:
        update_folder_label(label)


# Dependency initialization for pip installs
class DownloadSignals(QObject):
    """Signals for dependency download progress."""

    finished = pyqtSignal(bool, str)  # success, JSON-encoded list of [component, error] pairs
    status = pyqtSignal(str)          # current status label text
    progress = pyqtSignal(int)        # 0-100 percentage, or -1 for indeterminate


FFmpegDownloadSignals = DownloadSignals  # backward compatibility alias


def _needs_lapse_download():
    """Return True if lapse binary or silero_vad.onnx need to be downloaded (pip installs only)."""
    if getattr(sys, "frozen", False):
        return False  # PyInstaller build: lapse is bundled
    try:
        from resources import lapse_download

        lapse_bin = "lapse.exe" if platform.system() == "Windows" else "lapse"
        lapse_path = os.path.join(lapse_download.DIST_BIN_PATH, lapse_bin)
        silero_path = os.path.join(lapse_download.DIST_BIN_PATH, "silero_vad.onnx")
        return not (os.path.isfile(lapse_path) and os.path.isfile(silero_path))
    except Exception as e:
        logger.debug(f"Could not check lapse download status: {e}")
        return False


def initialize_static_ffmpeg(parent=None, callback=None):
    """
    Initialize static_ffmpeg and lapse if needed (for pip installs).
    Shows a single loading dialog while downloading any missing components.

    Components are downloaded sequentially; the status label updates in real time.
    On per-component failure a QMessageBox warning is shown, but the other
    component's result is still reported correctly.

    Args:
        parent: Parent widget for the dialog
        callback: Optional callback called when done (receives overall success bool)

    Returns:
        bool: True if successful or not needed, False if a critical component failed
    """
    from PyQt6.QtWidgets import QMessageBox
    from constants import NEEDS_STATIC_FFMPEG, FFMPEG_EXECUTABLE

    # --- Determine what needs downloading ---
    needs_ffmpeg = NEEDS_STATIC_FFMPEG
    needs_lapse = _needs_lapse_download()

    # Fast path: check if static_ffmpeg executables are already cached on disk
    if needs_ffmpeg:
        try:
            import static_ffmpeg
            from static_ffmpeg import run

            platform_dir = run.get_platform_dir()
            if platform.system() == "Windows":
                ffmpeg_path = os.path.join(platform_dir, "ffmpeg.exe")
                ffprobe_path = os.path.join(platform_dir, "ffprobe.exe")
            else:
                ffmpeg_path = os.path.join(platform_dir, "ffmpeg")
                ffprobe_path = os.path.join(platform_dir, "ffprobe")

            if os.path.isfile(ffmpeg_path) and os.path.isfile(ffprobe_path):
                static_ffmpeg.add_paths()
                logger.info(f"Using static_ffmpeg (module): {ffmpeg_path}")
                needs_ffmpeg = False
        except ImportError as e:
            logger.error(f"static_ffmpeg not installed: {e}")
            if callback:
                callback(False)
            return False
        except Exception as e:
            logger.debug(f"Error checking for static_ffmpeg: {e}")

    # Nothing to download — everything is already present
    if not needs_ffmpeg and not needs_lapse:
        if not NEEDS_STATIC_FFMPEG:
            logger.info(f"Using bundled FFmpeg: {FFMPEG_EXECUTABLE}")
        if callback:
            callback(True)
        return True

    # --- Show combined download dialog ---
    from PyQt6.QtCore import QThread

    class DownloadThread(QThread):
        """Background thread that downloads missing dependencies sequentially."""

        def __init__(self, signals, do_ffmpeg, do_lapse):
            super().__init__()
            self.signals = signals
            self.do_ffmpeg = do_ffmpeg
            self.do_lapse = do_lapse

        def run(self):
            errors = []  # list of [component, error_msg]

            # --- FFmpeg ---
            if self.do_ffmpeg:
                self.signals.status.emit(texts.DOWNLOADING_FFMPEG_FIRST_RUN)
                self.signals.progress.emit(-1)
                try:
                    import static_ffmpeg
                    from static_ffmpeg import run as ffmpeg_run

                    platform_dir = ffmpeg_run.get_platform_dir()
                    if platform.system() == "Windows":
                        ffmpeg_path = os.path.join(platform_dir, "ffmpeg.exe")
                        ffprobe_path = os.path.join(platform_dir, "ffprobe.exe")
                    else:
                        ffmpeg_path = os.path.join(platform_dir, "ffmpeg")
                        ffprobe_path = os.path.join(platform_dir, "ffprobe")

                    # Remove stale .crumb so static_ffmpeg re-downloads if binaries are missing
                    if not os.path.isfile(ffmpeg_path) or not os.path.isfile(ffprobe_path):
                        crumb_file = os.path.join(platform_dir, "installed.crumb")
                        if os.path.exists(crumb_file):
                            try:
                                os.remove(crumb_file)
                                logger.info("Removed installed.crumb to force re-download")
                            except OSError as e:
                                logger.warning(f"Could not remove installed.crumb: {e}")

                    orig_download_file = getattr(ffmpeg_run, "download_file", None)

                    def _download_with_progress(url, local_path):
                        timeout = getattr(ffmpeg_run, "TIMEOUT", 600)
                        part_path = local_path + ".part"
                        try:
                            with requests.get(url, stream=True, timeout=timeout) as req:
                                req.raise_for_status()
                                try:
                                    total = int(req.headers.get("content-length") or 0)
                                except (AttributeError, TypeError, ValueError):
                                    total = 0
                                downloaded = 0
                                last_pct = -1
                                self.signals.progress.emit(0 if total > 0 else -1)
                                with open(part_path, "wb") as f:
                                    for chunk in req.iter_content(chunk_size=262144):
                                        if not chunk:
                                            continue
                                        f.write(chunk)
                                        downloaded += len(chunk)
                                        if total > 0:
                                            pct = min(100, int(downloaded * 100 / total))
                                            if pct != last_pct:
                                                last_pct = pct
                                                self.signals.progress.emit(pct)
                                if total > 0 and downloaded < total:
                                    raise RuntimeError(
                                        f"Incomplete FFmpeg download: received {downloaded} of {total} bytes"
                                    )
                                if total <= 0:
                                    self.signals.progress.emit(100)
                            os.replace(part_path, local_path)
                        except Exception:
                            if os.path.exists(part_path):
                                os.unlink(part_path)
                            raise
                        self.signals.progress.emit(-1)  # Extraction phase
                        return local_path

                    try:
                        if callable(orig_download_file):
                            ffmpeg_run.download_file = _download_with_progress
                        ffmpeg_path, ffprobe_path = (
                            ffmpeg_run.get_or_fetch_platform_executables_else_raise()
                        )
                    finally:
                        if callable(orig_download_file):
                            ffmpeg_run.download_file = orig_download_file

                    if not os.path.isfile(ffmpeg_path) or not os.path.isfile(ffprobe_path):
                        errors.append(["ffmpeg", "FFmpeg download failed — files not found after download"])
                    else:
                        static_ffmpeg.add_paths()
                        logger.info(f"Using static_ffmpeg (downloaded): {ffmpeg_path}")
                except ImportError as e:
                    errors.append(["ffmpeg", f"static_ffmpeg not installed: {e}"])
                except Exception as e:
                    errors.append(["ffmpeg", str(e)])

            # --- lapse ---
            if self.do_lapse:
                self.signals.status.emit(texts.DOWNLOADING_LAPSE_FIRST_RUN)
                try:
                    from resources import lapse_download

                    downloaded = lapse_download.download(
                        progress_cb=self.signals.progress.emit
                    )
                    if downloaded and os.path.isfile(downloaded):
                        logger.info(f"Using lapse (downloaded): {downloaded}")
                    else:
                        errors.append(["lapse", "lapse download failed — binary not found after download"])
                except Exception as e:
                    errors.append(["lapse", str(e)])

            self.signals.finished.emit(len(errors) == 0, json.dumps(errors))

    # Choose dialog title based on what's being downloaded
    if needs_ffmpeg and needs_lapse:
        dialog_title = texts.DOWNLOADING_DEPENDENCIES
    elif needs_ffmpeg:
        dialog_title = texts.DOWNLOADING_FFMPEG
    else:
        dialog_title = texts.DOWNLOADING_LAPSE

    initial_text = (
        texts.DOWNLOADING_FFMPEG_FIRST_RUN if needs_ffmpeg else texts.DOWNLOADING_LAPSE_FIRST_RUN
    )
    dialog, label, _progress_bar, set_progress = _create_download_dialog(
        parent, dialog_title, initial_text
    )

    # Wire up signals
    dl_signals = DownloadSignals(dialog)
    dialog._signals = dl_signals
    thread = DownloadThread(dl_signals, needs_ffmpeg, needs_lapse)

    def on_status(msg):
        label.setText(msg)

    def on_finished(success, error_data):
        dialog.finish_and_close()
        try:
            errors = json.loads(error_data)
        except Exception:
            errors = []

        for component, error_msg in errors:
            if component == "ffmpeg":
                logger.error(f"FFmpeg download failed: {error_msg}")
                QMessageBox.warning(
                    parent,
                    texts.DOWNLOADING_FFMPEG,
                    texts.FFMPEG_DOWNLOAD_FAILED.format(error=error_msg),
                )
            elif component == "lapse":
                logger.error(f"lapse download failed: {error_msg}")
                QMessageBox.warning(
                    parent,
                    texts.DOWNLOADING_LAPSE,
                    texts.LAPSE_DOWNLOAD_FAILED.format(error=error_msg),
                )

        if callback:
            callback(success)

    dl_signals.status.connect(on_status)
    dl_signals.progress.connect(set_progress)
    dl_signals.finished.connect(on_finished)

    thread.start()

    # Show dialog (blocks until download completes)
    dialog.exec()

    # Wait for thread to finish if it's still running
    if thread.isRunning():
        thread.wait()

    return True



def check_file_readable(file_path: str) -> tuple[bool, str]:
    """Check if a file exists and can be opened for reading.

    Returns:
        tuple of (is_readable, error_message)
    """
    if not file_path:
        return False, str(texts.NO_FILE_PATH_PROVIDED)
    from constants import is_remote_url

    if is_remote_url(file_path):
        return True, ""
    if not os.path.exists(file_path):
        return False, f"{texts.FILE_DOES_NOT_EXIST} ({file_path})"
    try:
        with open(file_path, "rb") as f:
            f.read(1)
        return True, ""
    except Exception as e:
        return False, str(e)


def check_file_writable(file_path: str) -> tuple[bool, str]:
    """Check if a file can be opened for writing or created in its directory.

    Returns:
        tuple of (is_writable, error_message)
    """
    if not file_path:
        return False, str(texts.NO_FILE_PATH_PROVIDED)
    if os.path.exists(file_path):
        try:
            # Check if existing file is writable without truncating
            with open(file_path, "a+b") as f:
                pass
            return True, ""
        except Exception as e:
            return False, str(e)
    else:
        parent_dir = os.path.dirname(os.path.abspath(file_path))
        if not os.path.exists(parent_dir):
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except Exception as e:
                return False, str(e)
        try:
            fd, tmp_file = tempfile.mkstemp(dir=parent_dir, prefix=".test_write_")
            os.close(fd)
            if os.path.exists(tmp_file):
                os.remove(tmp_file)
            return True, ""
        except Exception as e:
            return False, str(e)


def check_pgs_subtitles_usable(reference: str) -> tuple[bool, str]:
    """Check if the reference file contains usable PGS subtitles.

    Fast check (~10ms) that inspects container stream headers via ffprobe.

    Returns:
        tuple of (is_usable, message_or_reason)
    """
    from constants import is_remote_url, FFPROBE_EXECUTABLE

    if not reference or is_remote_url(reference):
        return False, "Remote URLs or empty paths do not support PGS timing extraction"

    if not os.path.exists(reference):
        return False, "Reference file does not exist"

    try:
        from ffsubsync.speech_transformers import find_pgs_stream

        ffmpeg_dir = (os.path.dirname(FFPROBE_EXECUTABLE) or None) if FFPROBE_EXECUTABLE else None
        stream = find_pgs_stream(reference, ffmpeg_path=ffmpeg_dir)
        if not stream:
            return False, "No PGS (hdmv_pgs_subtitle) subtitle stream found"

        return True, f"Detected PGS stream {stream}"
    except Exception as e:
        return False, f"PGS probe check failed: {e}"


def _accumulate_pgs_packet(
    pts_str,
    dur_str,
    size_str,
    results: list[tuple[float, float]],
    current_start: Optional[float],
) -> tuple[Optional[float], Optional[float]]:
    """Accumulate a single PGS packet into cue (start, end) intervals.

    Handles both duration-bearing packets and Matroska Show/Clear pairs.
    Returns (updated_current_start, parsed_pts_or_None).
    """
    if pts_str is None or size_str is None:
        return current_start, None
    try:
        pts = float(pts_str)
        size = int(size_str)
        dur = float(dur_str) if dur_str not in (None, "N/A", "") else None
    except (ValueError, TypeError):
        return current_start, None

    if dur is not None and size > 50:
        results.append((pts, pts + dur))
        current_start = None
    elif size > 50:
        if current_start is not None and pts > current_start:
            results.append((current_start, min(pts, current_start + 7.0)))
        current_start = pts
    else:
        # Clear packet (size <= 50)
        if current_start is not None and pts > current_start:
            results.append((current_start, pts))
            current_start = None

    return current_start, pts


def extract_pgs_packet_timings(
    fname: str,
    stream: str,
    ffprobe_cmd: str,
    *,
    duration_sec: Optional[float] = None,
    progress_cb=None,
    is_cancelled=None,
    process_holder: Optional[dict] = None,
) -> Optional[list[tuple[float, float]]]:
    """Extract (start_sec, end_sec) cue intervals from a PGS stream via ffprobe.

    Handles both duration-bearing packets and standard Matroska Show/Clear pairs.
    Streams CSV lines incrementally when progress/cancellation hooks are supplied
    and ffmpeg.probe is not monkeypatched.
    """
    import ffmpeg

    probe_stream = stream[2:] if stream.startswith("0:") else stream
    results: list[tuple[float, float]] = []
    current_start: Optional[float] = None

    use_streaming = (
        (progress_cb is not None or is_cancelled is not None or process_holder is not None)
        and getattr(ffmpeg.probe, "__module__", "") == "ffmpeg._probe"
    )

    if use_streaming:
        cmd = [
            ffprobe_cmd,
            "-v",
            "error",
            "-show_packets",
            "-select_streams",
            probe_stream,
            "-show_entries",
            "packet=pts_time,duration_time,size",
            "-of",
            "csv=p=0",
            fname,
        ]
        proc = None
        last_pct = -1
        try:
            proc = create_process(cmd)
            if process_holder is not None:
                process_holder["process"] = proc
            if proc.stdout is not None:
                for raw_line in proc.stdout:
                    if is_cancelled and is_cancelled():
                        terminate_process_safely(proc)
                        return None
                    line = (
                        raw_line.decode("utf-8", errors="replace").strip()
                        if isinstance(raw_line, bytes)
                        else str(raw_line).strip()
                    )
                    if not line:
                        continue
                    parts = line.split(",")
                    if len(parts) < 3:
                        continue
                    current_start, pts = _accumulate_pgs_packet(
                        parts[0].strip(),
                        parts[1].strip(),
                        parts[2].strip(),
                        results,
                        current_start,
                    )
                    if (
                        pts is not None
                        and progress_cb
                        and duration_sec
                        and duration_sec > 0
                    ):
                        pct = min(99, max(0, int((pts / duration_sec) * 100)))
                        if pct > last_pct:
                            last_pct = pct
                            progress_cb(float(pct))
            if proc.stdout is not None:
                proc.stdout.close()
            proc.wait()
            if is_cancelled and is_cancelled():
                return None
            if progress_cb and results:
                progress_cb(100.0)
        except Exception:
            if proc is not None and proc.poll() is None:
                terminate_process_safely(proc)
            return None
        finally:
            if process_holder is not None and process_holder.get("process") is proc:
                process_holder["process"] = None
    else:
        try:
            probe_data = ffmpeg.probe(
                fname,
                cmd=ffprobe_cmd,
                show_packets=None,
                select_streams=probe_stream,
                show_entries="packet=pts_time,duration_time,size",
            )
        except Exception:
            return None

        for packet in probe_data.get("packets", []):
            current_start, _ = _accumulate_pgs_packet(
                packet.get("pts_time"),
                packet.get("duration_time"),
                packet.get("size"),
                results,
                current_start,
            )

    if current_start is not None:
        results.append((current_start, current_start + 3.0))

    return results if results else None


def _format_srt_timestamp(seconds: float) -> str:
    """Format seconds as an SRT timestamp (HH:MM:SS,mmm)."""
    total_ms = max(0, int(round(float(seconds) * 1000)))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def extract_pgs_timings_to_srt(
    reference: str,
    *,
    stream: Optional[str] = None,
    min_cues: int = 1,
    duration_sec: Optional[float] = None,
    progress_cb=None,
    is_cancelled=None,
    process_holder: Optional[dict] = None,
) -> tuple[Optional[str], str, int]:
    """Extract PGS subtitle packet timings from a video into a temporary SRT file.

    Avoids OCR by writing placeholder text with the exact PGS cue timestamps so
    timing-based sync engines (such as alass and LAPSE) can align against them.

    Returns:
        tuple of (temp_srt_path_or_None, reason_or_stream_info, cue_count)
    """
    from constants import is_remote_url, FFPROBE_EXECUTABLE

    if is_cancelled and is_cancelled():
        return None, "Cancelled", 0

    if not reference or is_remote_url(reference):
        return None, "Remote URLs or empty paths do not support PGS timing extraction", 0

    if not os.path.exists(reference):
        return None, "Reference file does not exist", 0

    try:
        from ffsubsync.speech_transformers import find_pgs_stream
        from ffsubsync.ffmpeg_utils import ffmpeg_bin_path

        ffmpeg_dir = (os.path.dirname(FFPROBE_EXECUTABLE) or None) if FFPROBE_EXECUTABLE else None
        if not stream:
            stream = find_pgs_stream(reference, ffmpeg_path=ffmpeg_dir)
        if not stream:
            return None, "No PGS (hdmv_pgs_subtitle) subtitle stream found", 0

        ffprobe_cmd = ffmpeg_bin_path("ffprobe", False, ffmpeg_resources_path=ffmpeg_dir)
        timings = extract_pgs_packet_timings(
            reference,
            stream,
            ffprobe_cmd,
            duration_sec=duration_sec,
            progress_cb=progress_cb,
            is_cancelled=is_cancelled,
            process_holder=process_holder,
        )
        if is_cancelled and is_cancelled():
            return None, "Cancelled", 0
        if not timings:
            return None, f"No usable PGS timing packets in stream {stream}", 0

        if len(timings) < min_cues:
            return (
                None,
                f"Only {len(timings)} PGS cues in stream {stream} (minimum {min_cues} required)",
                len(timings),
            )

        tmp_path = None
        try:
            temp_dir = get_logs_directory()
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".srt",
                prefix="autosubsync_pgs_",
                dir=temp_dir,
                encoding="utf-8",
                delete=False,
            ) as tmp:
                tmp_path = tmp.name
                for idx, (start_sec, end_sec) in enumerate(timings, 1):
                    s = max(0.0, float(start_sec))
                    e = max(float(end_sec), s + 0.05)
                    tmp.write(
                        f"{idx}\n"
                        f"{_format_srt_timestamp(s)} --> {_format_srt_timestamp(e)}\n"
                        "PGS\n\n"
                    )
        except Exception:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            raise

        return tmp_path, f"Detected PGS stream {stream}", len(timings)
    except Exception as e:
        return None, f"PGS timing extraction failed: {e}", 0
