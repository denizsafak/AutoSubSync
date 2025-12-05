import os
import sys
import platform
import logging
import multiprocessing

# Fix multiprocessing for installed packages:
# - On Linux: use 'fork' to avoid re-importing the 'main' module (which conflicts with our package name)
# - On Windows/macOS: 'fork' is unavailable or unsafe, so we rely on freeze_support()
#   and running from PyInstaller builds (which handle this correctly)
if not getattr(sys, "frozen", False):
    if platform.system() == "Linux":
        try:
            multiprocessing.set_start_method("fork", force=True)
        except RuntimeError:
            pass  # Already set
    else:
        # For Windows/macOS pip installs, ensure freeze_support is called early
        multiprocessing.freeze_support()

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import qInstallMessageHandler, QtMsgType

# Add the directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui import autosubsyncapp
from gui_automatic_tab import (
    attach_functions_to_autosubsyncapp as attach_auto_functions,
)
from gui_manual_tab import attach_functions_to_autosubsyncapp as attach_manual_functions
from gui_batch_mode import attach_functions_to_autosubsyncapp as attach_batch_functions
from gui_auto_pairing import (
    attach_functions_to_autosubsyncapp as attach_auto_pairing_functions,
)
from gui_multiple_subs import (
    attach_functions_to_autosubsyncapp as attach_multiple_subs_functions,
)
from utils import get_resource_path
from constants import PROGRAM_NAME, VERSION, FFMPEG_DIR

# Build PATH with bundled tools and platform-specific directories
_path_additions = [
    p
    for p in [
        FFMPEG_DIR,
        "/opt/homebrew/bin" if platform.system() == "Darwin" else None,  # Apple Silicon
        "/usr/local/bin" if platform.system() == "Darwin" else None,  # Intel Mac
    ]
    if p and os.path.isdir(p)
]

if _path_additions:
    os.environ["PATH"] = os.pathsep.join(_path_additions + [os.environ.get("PATH", "")])

# Setup root logger with basic configuration
try:
    from rich.console import Console
    from rich.logging import RichHandler

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=Console(file=sys.stderr))],
    )
except:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)

# Attach tab module functions to the autosubsyncapp class
attach_auto_functions(autosubsyncapp)
attach_manual_functions(autosubsyncapp)
attach_batch_functions(autosubsyncapp)
attach_auto_pairing_functions(autosubsyncapp)
attach_multiple_subs_functions(autosubsyncapp)


# Custom message handler to filter out specific Qt warnings
def qt_message_handler(mode, context, message):
    if "Wayland does not support QWindow::requestActivate()" in message:
        return  # Suppress this specific message
    if "Could not register app ID" in message and "autosubsyncapp" in message:
        return  # Suppress the portal registration error for autosubsyncapp
    if mode == QtMsgType.QtWarningMsg:
        print(f"Qt Warning: {message}")
    elif mode == QtMsgType.QtCriticalMsg:
        print(f"Qt Critical: {message}")
    elif mode == QtMsgType.QtFatalMsg:
        print(f"Qt Fatal: {message}")
    elif mode == QtMsgType.QtInfoMsg:
        print(f"Qt Info: {message}")


# Install the custom message handler
qInstallMessageHandler(qt_message_handler)

# Ensure sys.stdout and sys.stderr are valid in GUI mode
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

# Set application ID for Windows taskbar icon
if platform.system() == "Windows":
    import ctypes

    app_id = f"{PROGRAM_NAME}.{VERSION}"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

# Handle Wayland on Linux GNOME
if platform.system() == "Linux":
    xdg_session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    if (
        "gnome" in desktop
        and xdg_session == "wayland"
        and "QT_QPA_PLATFORM" not in os.environ
    ):
        os.environ["QT_QPA_PLATFORM"] = "wayland"

# Set up main logger
logger = logging.getLogger(__name__)


def main():
    """Main entry point for console usage."""
    logger.info("Starting application")
    app = QApplication(sys.argv)

    # Set application icon using get_resource_path from utils
    icon_path = get_resource_path("autosubsyncapp.assets", "icon.ico")
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))

    # Set the .desktop name on Linux
    if platform.system() == "Linux":
        try:
            app.setDesktopFileName("autosubsyncapp")
        except AttributeError:
            logger.warning("setDesktopFileName not available on this Qt version")

    ex = autosubsyncapp()
    ex.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    multiprocessing.freeze_support()  # Fix for PyInstaller on Windows
    main()
