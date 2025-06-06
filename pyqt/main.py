import os
import sys
import platform
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

# Add the directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from gui import autosubsync
from utils import get_resource_path
from texts import PROGRAM_NAME, VERSION

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


def main():
    """Main entry point for console usage."""
    app = QApplication(sys.argv)

    # Set application icon using get_resource_path from utils
    icon_path = get_resource_path("autosubsync.assets", "icon.ico")
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))

    # Set the .desktop name on Linux
    if platform.system() == "Linux":
        try:
            app.setDesktopFileName("autosubsync.desktop")
        except AttributeError:
            pass

    ex = autosubsync()
    ex.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
