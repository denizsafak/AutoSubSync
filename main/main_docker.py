import sys
import os

# Try to import PyQt6 first, fallback to PySide6
try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QIcon
    from PyQt6.QtCore import qInstallMessageHandler, QtMsgType, Qt

    QT_LIB = "PyQt6"
    print("Using PyQt6")
except ImportError:
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QIcon
        from PySide6.QtCore import qInstallMessageHandler, QtMsgType, Qt

        QT_LIB = "PySide6"
        print("Using PySide6")
    except ImportError:
        print("Neither PyQt6 nor PySide6 is available!")
        sys.exit(1)

# The rest of the original main.py imports and code...
import platform
import logging

# Add the directory to Python path
# sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

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

# Add bundled ffmpeg to PATH if available
if FFMPEG_DIR:
    os.environ["PATH"] = os.pathsep.join([FFMPEG_DIR, os.environ.get("PATH", "")])

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
    logger.info(f"Starting application with {QT_LIB}")
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
    import multiprocessing

    multiprocessing.freeze_support()  # Fix for PyInstaller on Windows
    main()
