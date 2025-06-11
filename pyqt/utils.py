import os
import sys
import json
import tempfile
import urllib.request
import threading
import logging
from PyQt6.QtWidgets import QApplication, QMessageBox, QFileDialog
from PyQt6.QtCore import QUrl, QProcess, pyqtSignal, QObject
from PyQt6.QtGui import QDesktopServices

logger = logging.getLogger(__name__)

# Module-level cache for config path
_config_path_cache = None
_config_path_logged = False

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
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def shorten_path(path, maxlen=50):
    if len(path) <= maxlen:
        return path
    else:
        return path[:maxlen//2-2] + '…' + path[-maxlen//2+1:]


def open_filedialog(parent_instance, dialog_type, title, file_filter=None, initial_dir=None, multiple=False):
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
    config_dir = parent_instance.config.get("last_used_dir", "") if hasattr(parent_instance, "config") else ""
    start_dir = initial_dir or config_dir or ""
    
    result = None
    
    if dialog_type == 'file-open':
        result, _ = QFileDialog.getOpenFileName(parent_instance, title, start_dir, file_filter or "")
    elif dialog_type == 'files-open':
        result, _ = QFileDialog.getOpenFileNames(parent_instance, title, start_dir, file_filter or "")
    elif dialog_type == 'directory':
        result = QFileDialog.getExistingDirectory(parent_instance, title, start_dir)
    
    # Update the last used directory if a file/directory was selected
    if result:
        if isinstance(result, list) and result:  # Multiple files selected
            update_config(parent_instance, "last_used_dir", os.path.dirname(result[0]))
        elif isinstance(result, str) and result:  # Single file or directory
            if dialog_type == 'directory':
                update_config(parent_instance, "last_used_dir", result)
            else:
                update_config(parent_instance, "last_used_dir", os.path.dirname(result))
    
    return result


# Settings menu

def update_config(obj, key, value):
    obj.config[key] = value
    # Only save settings if remember_changes is enabled (default: True)
    if obj.config.get("remember_changes", True):
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
        "Are you sure you want to reset settings to default?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No
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
            QMessageBox.critical(
                parent,
                "Error",
                f"Failed to reset settings: {str(e)}"
            )

def open_config_directory(parent=None):
    """Open the config directory in the system file manager"""

    try:
        config_path = get_user_config_path()
        logger.info(f"Opening config directory: {os.path.dirname(config_path)}")
        # Open the directory containing the config file
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(config_path)))
    except Exception as e:
        logger.error(f"Could not open config location: {e}")
        QMessageBox.critical(
            parent, "Config Error", f"Could not open config location:\n{e}"
        )

def open_logs_directory(parent=None):
    """Open the logs directory used by the program."""
    try:
        logger.info(f"Opening logs directory: {get_logs_directory()}")
        # Open the directory in file explorer
        QDesktopServices.openUrl(QUrl.fromLocalFile(get_logs_directory()))
    except Exception as e:
        logger.error(f"Could not open logs directory: {e}")
        QMessageBox.critical(
            parent, "logs directory Error", f"Could not open logs directory:\n{e}"
        )

def clear_logs_directory(parent=None):
    """Delete logs directory after user confirmation."""
    try:
        logs_dir = get_logs_directory()
        
        # Count files in the directory
        total_files = len([f for f in os.listdir(logs_dir) if os.path.isfile(os.path.join(logs_dir, f))])
        logger.info(f"Attempting to clear logs directory: {logs_dir} ({total_files} files)")

        if total_files == 0:
            QMessageBox.information(
                parent,
                "Logs Directory",
                "Logs directory is empty."
            )
            return
        
        # Ask for confirmation with file count
        reply = QMessageBox.question(
            parent,
            "Delete logs directory",
            f"Are you sure you want to delete logs directory with {total_files} files?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            import shutil
            # Remove the entire directory
            shutil.rmtree(logs_dir)
            logger.info("Logs directory cleared.")

            QMessageBox.information(
                parent,
                "Logs Directory Cleared",
                f"Logs directory has been successfully deleted."
            )
    except Exception as e:
        logger.error(f"Failed to clear logs directory: {e}")
        QMessageBox.critical(
            parent,
            "Error",
            f"Failed to clear logs directory: {str(e)}"
        )

def show_about_dialog(parent):
    """Show an About dialog with program information including GitHub link."""
    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon
    from constants import PROGRAM_NAME, VERSION, PROGRAM_TAGLINE, PROGRAM_DESCRIPTION, COLORS, GITHUB_URL
    
    icon = parent.windowIcon()
    dialog = QDialog(parent)
    dialog.setWindowTitle(f"About {PROGRAM_NAME}")
    dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
    dialog.setFixedSize(400, 320)
    layout = QVBoxLayout(dialog)
    layout.setSpacing(10)
    header_layout = QHBoxLayout()
    icon_label = QLabel()
    if not icon.isNull():
        icon_label.setPixmap(icon.pixmap(64, 64))
    else:
        icon_label.setText("\U0001F4DA")
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
    msg_box.setText(f"A new version of {PROGRAM_NAME} is available! ({local_version} → {remote_version})")
    msg_box.setInformativeText("Please visit the GitHub repository and download the latest version. Would you like to open the GitHub releases page?")
    msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)
    if msg_box.exec() == QMessageBox.StandardButton.Yes:
        try:
            QDesktopServices.openUrl(QUrl(GITHUB_LATEST_RELEASE_URL))
        except Exception:
            pass

def _show_up_to_date(parent, version):
    from constants import PROGRAM_NAME
    QMessageBox.information(parent, "Up to Date", f"You are running the latest version of {PROGRAM_NAME} ({version}).")

def _show_check_failed(parent, error_message):
    QMessageBox.warning(parent, "Update Check Failed", f"Could not check for updates:\n{error_message}")

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
    signals.up_to_date.connect(lambda v: _show_up_to_date(parent, v) if show_result else None)
    signals.check_failed.connect(lambda e: _show_check_failed(parent, e) if show_result else None)
    
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
        if hasattr(label, 'setTextFormat'):
            from constants import COLORS
            from PyQt6.QtCore import Qt
            label.setText(f'Selected folder: <span style="color:{COLORS["GREEN"]}">{shorten_path(folder_path)}</span>')
            label.setTextFormat(Qt.TextFormat.RichText)
        else:
            label.setText(f"Selected folder: {shorten_path(folder_path)}")
        # Set tooltip to show full path
        label.setToolTip(folder_path)
        label.show()
    else:
        label.setToolTip("")  # Clear tooltip when no folder
        label.hide()

def handle_save_location_dropdown(obj, dropdown, save_map, config_key, folder_key, label, default_value, skip_dialog=False):
    """
    Generic handler for save location dropdowns with folder selection and label update.
    """
    text = dropdown.currentText()
    
    # Handle folder selection case
    if save_map.get(text) == "select_destination_folder" and not skip_dialog:
        folder = open_filedialog(
            obj, 
            'directory', 
            "Select Destination Folder"
        )
        if folder:
            update_config(obj, folder_key, folder)
            update_folder_label(label, folder)
        else:
            # Revert to previous selection if cancelled
            prev = obj.config.get(config_key, default_value)
            display = next((k for k, v in save_map.items() if v == prev), list(save_map.keys())[0])
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
