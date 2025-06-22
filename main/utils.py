import os
import sys
import json
import tempfile
import urllib.request
import threading
import logging
import subprocess
import platform
import signal
import time
import shutil
import cchardet, charset_normalizer, chardet
from PyQt6.QtWidgets import QApplication, QMessageBox, QFileDialog
from PyQt6.QtCore import QUrl, QProcess, pyqtSignal, QObject
from PyQt6.QtGui import QDesktopServices

logger = logging.getLogger(__name__)

# Module-level cache for config path
_config_path_cache = None
_config_path_logged = False
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
            msg = "Cannot match encoding: one or both subtitle files do not exist"
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
            with open(output_subtitle_path, "r", encoding=output_encoding) as f:
                content = f.read()
        except UnicodeDecodeError:
            warning_msg = f"Failed to read output file with detected encoding {output_encoding}, trying utf-8"
            logger.warning(warning_msg)
            if log_window:
                log_window.append_message(warning_msg, color=COLORS["ORANGE"])
            with open(
                output_subtitle_path, "r", encoding="utf-8", errors="replace"
            ) as f:
                content = f.read()

        # Write content back with target encoding
        try:
            with open(output_subtitle_path, "w", encoding=final_encoding) as f:
                f.write(content)
            success_msg = f"Changed output subtitle encoding from {output_encoding} to {final_encoding}"
            logger.info(success_msg)
            if log_window:
                log_window.append_message(success_msg, color=COLORS["GREY"])
            return True
        except (UnicodeEncodeError, LookupError) as e:
            error_msg = f"Failed to re-encode to {final_encoding}: {e}. Keeping original encoding."
            logger.warning(error_msg)
            if log_window:
                log_window.append_message(error_msg, color=COLORS["ORANGE"])
            return False

    except Exception as e:
        error_msg = f"Error matching subtitle encoding: {e}"
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
    try:
        config = {}
        with open(get_user_config_path(), "r", encoding="utf-8") as f:
            config = json.load(f)
        logger.info("Config file loaded successfully")
        return config
    except Exception as e:
        logger.info(f"Failed to load config: {e}")
        return {}


def save_config(config):
    try:
        with open(get_user_config_path(), "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        logger.info("Config file updated")
    except Exception as e:
        logger.warning(f"Failed to save config: {e}")


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
        package (str): Package name containing the resource (e.g., 'autosubsync.assets')
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
        # Extract the subdirectory from package name (e.g., 'assets' from 'autosubsync.assets')
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
                parent, "Open Folder Error", f"Could not open folder:\n{e}"
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
        "Reset Settings",
        "Are you sure you want to reset settings to default? This will restart the application and remove your current settings.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )

    if reply == QMessageBox.StandardButton.Yes:
        config_path = get_user_config_path()
        try:
            # Remove the config file if it exists
            if os.path.exists(config_path):
                os.remove(config_path)
                logger.info("Config file removed for reset to defaults.")

            # Restart the application
            QProcess.startDetached(sys.executable, sys.argv)
            QApplication.quit()
        except Exception as e:
            logger.error(f"Failed to reset settings: {e}")
            QMessageBox.critical(parent, "Error", f"Failed to reset settings: {str(e)}")


def open_config_directory(parent=None):
    """Open the config directory in the system file manager"""
    try:
        config_path = get_user_config_path()
        config_dir = os.path.dirname(config_path)
        open_folder(config_dir, parent)
    except Exception as e:
        logger.error(f"Could not open config location: {e}")
        QMessageBox.critical(
            parent, "Config Error", f"Could not open config location:\n{e}"
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
                parent, "Logs Directory", "Logs directory is empty."
            )
            return

        # Ask for confirmation with file count
        reply = QMessageBox.question(
            parent,
            "Delete logs directory",
            f"Are you sure you want to delete logs directory with {total_files} files?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            import shutil

            # Remove the entire directory
            shutil.rmtree(logs_dir)
            logger.info("Logs directory cleared.")

            QMessageBox.information(
                parent,
                "Logs Directory Cleared",
                f"Logs directory has been successfully deleted.",
            )
    except Exception as e:
        logger.error(f"Failed to clear logs directory: {e}")
        QMessageBox.critical(
            parent, "Error", f"Failed to clear logs directory: {str(e)}"
        )


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
    dialog.setWindowTitle(f"About {PROGRAM_NAME}")
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
        f"<p>{PROGRAM_DESCRIPTION}</p>"
        "<p>Visit the GitHub repository for updates, documentation, and to report issues.</p>"
    )
    desc_label.setTextFormat(Qt.TextFormat.RichText)
    desc_label.setWordWrap(True)
    layout.addWidget(desc_label)
    github_btn = QPushButton("Visit GitHub Repository")
    github_btn.setIcon(QIcon(get_resource_path("autosubsync.assets", "github.png")))
    github_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_URL)))
    github_btn.setFixedHeight(32)
    layout.addWidget(github_btn)
    update_btn = QPushButton("Check for updates")
    update_btn.clicked.connect(lambda: manual_check_for_updates(parent))
    update_btn.setFixedHeight(32)
    layout.addWidget(update_btn)
    close_btn = QPushButton("Close")
    close_btn.clicked.connect(dialog.accept)
    close_btn.setFixedHeight(32)
    layout.addWidget(close_btn)
    dialog.exec()


# Update checking functionality
class UpdateSignals(QObject):
    update_available = pyqtSignal(str, str)
    up_to_date = pyqtSignal(str)
    check_failed = pyqtSignal(str)


def _show_update_message(parent, remote_version, local_version):
    from constants import GITHUB_LATEST_RELEASE_URL, PROGRAM_NAME

    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Icon.Information)
    msg_box.setWindowTitle("Update Available")
    msg_box.setText(
        f"A new version of {PROGRAM_NAME} is available! ({local_version} → {remote_version})"
    )
    msg_box.setInformativeText(
        "Please visit the GitHub repository and download the latest version. Would you like to open the GitHub releases page?"
    )
    msg_box.setStandardButtons(
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)
    if msg_box.exec() == QMessageBox.StandardButton.Yes:
        try:
            QDesktopServices.openUrl(QUrl(GITHUB_LATEST_RELEASE_URL))
        except Exception:
            pass


def _show_up_to_date(parent, version):
    from constants import PROGRAM_NAME

    QMessageBox.information(
        parent,
        "Up to Date",
        f"You are running the latest version of {PROGRAM_NAME} ({version}).",
    )


def _show_check_failed(parent, error_message):
    QMessageBox.warning(
        parent, "Update Check Failed", f"Could not check for updates:\n{error_message}"
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
            with urllib.request.urlopen(GITHUB_VERSION_URL, timeout=5) as response:
                remote = response.read().decode().strip()
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
        if hasattr(label, "setTextFormat"):
            from constants import COLORS
            from PyQt6.QtCore import Qt

            label.setText(
                f'Selected folder: <span style="color:{COLORS["GREEN"]}">{shorten_path(folder_path)}</span>'
            )
            label.setTextFormat(Qt.TextFormat.RichText)
        else:
            label.setText(f"Selected folder: {shorten_path(folder_path)}")
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
        folder = open_filedialog(obj, "directory", "Select Destination Folder")
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
