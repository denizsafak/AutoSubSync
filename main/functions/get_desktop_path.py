import os
from platformdirs import user_desktop_dir

def get_desktop_path():
    desktop = user_desktop_dir()
    if not os.path.exists(desktop):
        desktop = os.path.normpath(os.path.expanduser("~"))
    return desktop

desktop_path = get_desktop_path()