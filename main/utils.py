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
from PyQt6.QtWidgets import QApplication, QMessageBox, QFileDialog
from PyQt6.QtCore import QUrl, QProcess, pyqtSignal, QObject
from PyQt6.QtGui import QDesktopServices
import requests
import webbrowser

logger = logging.getLogger(__name__)

# Module-level cache for config path and config data
_config_path_cache = None
_config_path_logged = False
_config_cache = None
_config_cache_lock = threading.Lock()
_locale_cache = None
default_encoding = sys.getfilesystemencoding()

# Thread-safe process creation lock
_process_lock = threading.Lock()


def create_process(cmd):
    """Create a subprocess with proper threading support and termination handling."""
    with _process_lock:
        logger.info(f"Executing: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
        env = {**os.environ, "TERM": "dumb", "COLUMNS": "70"}
        kwargs = {
            "shell": False,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "universal_newlines": False,
            "bufsize": 0,
            "env": env,
        }

        if platform.system() == "Windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            kwargs.update(
                {
                    "startupinfo": startupinfo,
                    "creationflags": subprocess.CREATE_NO_WINDOW
                    | subprocess.CREATE_NEW_PROCESS_GROUP,
                }
            )
        else:
            # On Unix-like systems, create a new process group
            kwargs["preexec_fn"] = os.setsid

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
    # Create the directory if it doesn't exist
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    return logs_dir


def load_config():
    """
    Load configuration with caching to avoid multiple file reads.
    Thread-safe implementation.
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
                config = json.load(f)
            logger.info("Config file loaded successfully")
            _config_cache = config.copy()
            return config
        except Exception as e:
            logger.info(f"Failed to load config: {e}")
            _config_cache = {}
            return {}


def save_config(config):
    """
    Save configuration and update cache.
    """
    global _config_cache

    try:
        with open(get_user_config_path(), "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        logger.info("Config file updated")

        # Update cache with new config
        with _config_cache_lock:
            _config_cache = config.copy()
    except Exception as e:
        logger.warning(f"Failed to save config: {e}")


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
    """Restart the application, handling AppImage, frozen executables, and scripts."""
    appimage = os.environ.get("APPIMAGE")

    if appimage:
        # Running as AppImage - clear mount-related env vars for clean restart
        env = os.environ.copy()
        for var in ("APPDIR", "ARGV0", "OWD", "APPIMAGE_SILENT_INSTALL"):
            env.pop(var, None)
        subprocess.Popen(
            [appimage] + sys.argv[1:],
            start_new_session=True,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    elif getattr(sys, "frozen", False):
        # Frozen executable (Windows/macOS)
        subprocess.Popen([sys.executable] + sys.argv[1:], start_new_session=True)
    else:
        # Python script
        subprocess.Popen([sys.executable] + sys.argv, start_new_session=True)

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
        try:
            if os.path.exists(config_path):
                os.remove(config_path)
                logger.info("Config file removed for reset to defaults.")
            restart_application()
        except Exception as e:
            logger.error(f"Failed to reset settings: {e}")
            QMessageBox.critical(
                parent, texts.ERROR, texts.FAILED_TO_RESET_SETTINGS.format(error=str(e))
            )


def open_config_directory(parent=None):
    """Open the config directory in the system file manager"""
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
    from constants import PROGRAM_NAME

    QMessageBox.information(
        parent,
        texts.UP_TO_DATE_TITLE,
        texts.RUNNING_LATEST_VERSION.format(program_name=PROGRAM_NAME, version=version),
    )


def _show_check_failed(parent, error_message):
    QMessageBox.warning(
        parent,
        texts.UPDATE_CHECK_FAILED_TITLE,
        texts.COULD_NOT_CHECK_FOR_UPDATES.format(error_message=error_message),
    )


def manual_check_for_updates(parent):
    logger.info("Manual update check triggered.")
    parent._show_update_check_result = True
    check_for_updates_startup(parent)


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
    text = dropdown.currentText()

    # Handle folder selection case
    if save_map.get(text) == "select_destination_folder" and not skip_dialog:
        folder = open_filedialog(obj, "directory", texts.SELECT_DESTINATION_FOLDER)
        if folder:
            update_config(obj, folder_key, folder)
            update_folder_label(label, folder)
        else:
            # Revert to previous selection if cancelled
            prev = obj.config.get(config_key, default_value)
            display = next(
                (k for k, v in save_map.items() if v == prev), list(save_map.keys())[0]
            )
            idx = dropdown.findText(display)
            if idx >= 0:
                dropdown.setCurrentIndex(idx)
            update_folder_label(label)
            return

    # Update config for any selection
    update_config(obj, config_key, save_map.get(text, default_value))

    # Update label based on current selection
    if save_map.get(text) == "select_destination_folder":
        folder = obj.config.get(folder_key, "")
        update_folder_label(label, folder)
    else:
        update_folder_label(label)


# FFmpeg initialization for pip installs
class FFmpegDownloadSignals(QObject):
    """Signals for FFmpeg download progress."""

    finished = pyqtSignal(bool, str)  # success, error_message


def initialize_static_ffmpeg(parent=None, callback=None):
    """
    Initialize static_ffmpeg if needed (for pip installs).
    Shows a loading dialog while downloading.

    Args:
        parent: Parent widget for the dialog
        callback: Optional callback function to call when done (receives success bool)

    Returns:
        bool: True if successful or not needed, False if failed
    """
    from constants import NEEDS_STATIC_FFMPEG

    if not NEEDS_STATIC_FFMPEG:
        if callback:
            callback(True)
        return True

    # Need to download - show dialog
    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
    from PyQt6.QtCore import Qt, QThread

    class DownloadThread(QThread):
        """Thread to download ffmpeg without blocking UI."""

        def __init__(self, signals):
            super().__init__()
            self.signals = signals

        def run(self):
            try:
                import static_ffmpeg
                from static_ffmpeg import run

                # This actually downloads the binaries if not present
                run.get_or_fetch_platform_executables_else_raise()
                # Then add them to PATH
                static_ffmpeg.add_paths()
                self.signals.finished.emit(True, "")
            except ImportError as e:
                self.signals.finished.emit(
                    False, f"static_ffmpeg not installed: {str(e)}"
                )
            except Exception as e:
                self.signals.finished.emit(False, str(e))

    # Create and show the dialog
    dialog = QDialog(parent)
    dialog.setWindowTitle(texts.DOWNLOADING_FFMPEG)
    dialog.setWindowFlags(
        dialog.windowFlags()
        & ~Qt.WindowType.WindowContextHelpButtonHint
        & ~Qt.WindowType.WindowCloseButtonHint
    )
    dialog.setModal(True)
    dialog.setFixedSize(400, 120)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(15)

    label = QLabel(texts.DOWNLOADING_FFMPEG_FIRST_RUN)
    label.setWordWrap(True)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label)

    progress = QProgressBar()
    progress.setRange(0, 0)  # Indeterminate progress
    progress.setTextVisible(False)
    layout.addWidget(progress)

    # Setup signals and thread
    signals = FFmpegDownloadSignals()
    thread = DownloadThread(signals)

    def on_finished(success, error_msg):
        dialog.accept()
        if success:
            logger.info("FFmpeg downloaded and paths added successfully")
        else:
            logger.error(f"FFmpeg download failed: {error_msg}")
            QMessageBox.warning(
                parent,
                texts.DOWNLOADING_FFMPEG,
                texts.FFMPEG_DOWNLOAD_FAILED.format(error=error_msg),
            )
        if callback:
            callback(success)

    signals.finished.connect(on_finished)
    thread.finished.connect(thread.deleteLater)

    # Start download in background
    thread.start()

    # Show dialog (blocks until download completes)
    dialog.exec()

    # Wait for thread to finish
    thread.wait()

    return True
