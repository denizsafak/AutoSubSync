import subprocess
from config import config
from functions.get_platform import platform

def is_dark_mode():
    if platform == "Windows":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            ) as key:
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return value == 0
        except Exception:
            return False
    elif platform == "Linux":
        # Check for GNOME dark mode
        try:
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
                capture_output=True,
                text=True,
                check=False,
            )
            return "dark" in result.stdout.lower()
        except Exception:
            return False
    return False

# Get the theme from the config, or set it based on the system's theme
THEME = config.get("theme", "system")
if THEME == "system":
    THEME = "dark" if is_dark_mode() else "light"

# Define color schemes for light and dark themes
COLOR_SCHEMES = {
    "COLOR_BW": ("black", "white"),
    "COLOR_WB": ("white", "black"),
    "COLOR_BACKGROUND": ("#f1f0f1", "#202020"),
    "COLOR_PRIMARY": ("gray85", "gray10"),
    "COLOR_SECONDARY": ("gray75", "gray30"),
    "COLOR_TAB_INACTVE": ("gray20", "gray60"),
    "COLOR_PROGRESSBAR": ("#00a31e", "#00a31e"),
    "COLOR_ZERO": ("lightgrey", "grey10"),
    "COLOR_ONE": ("lightgrey", "grey20"),
    "COLOR_TWO": ("lightgreen", "#0a420a"),
    "COLOR_THREE": ("lightblue", "#12303b"),
    "COLOR_FOUR": ("lightgoldenrodyellow", "#5c5c0a"),
    "COLOR_FIVE": ("lightcoral", "#5b0b0b"),
    "COLOR_SIX": ("RosyBrown1", "red4"),
    "COLOR_SEVEN": ("#007FFF", "#389afc"),
    "COLOR_EIGHT": ("red", "#ffeded"),
    "COLOR_NINE": ("green", "lightgreen"),
    "COLOR_OPTIONS": ("gray85", "gray30"),
    "TREEVIEW_SELECTED_COLOR": ("steelblue", "#325d81"),
    "COLOR_MILISECONDS_HIGH": ("aliceblue", "#001b33"),
    "COLOR_MILISECONDS_LOW": ("mistyrose", "#330500"),
    "DEFAULT_BUTTON_COLOR": ("gray50", "gray50"),
    "DEFAULT_BUTTON_COLOR_ACTIVE": ("gray40", "gray40"),
    "BUTTON_COLOR_MANUAL": ("#32993a", "#3ec149"),
    "BUTTON_COLOR_MANUAL_ACTIVE": ("#2d8a35", "#38ad42"),
    "BUTTON_COLOR_AUTO": ("royalblue", "#6699ff"),
    "BUTTON_COLOR_AUTO_ACTIVE": ("RoyalBlue3", "#6585e7"),
    "BUTTON_COLOR_BATCH": ("#b05958", "#be7674"),
    "BUTTON_COLOR_BATCH_ACTIVE": ("#a15150", "#b66463"),
}
# Select the appropriate color scheme based on the theme
is_dark_theme = THEME == "dark"
border_fix = 0 if is_dark_theme else 1
COLOR_BACKGROUND = COLOR_SCHEMES["COLOR_BACKGROUND"][is_dark_theme]
COLOR_BW = COLOR_SCHEMES["COLOR_BW"][is_dark_theme]
COLOR_WB = COLOR_SCHEMES["COLOR_WB"][is_dark_theme]
COLOR_PRIMARY = COLOR_SCHEMES["COLOR_PRIMARY"][is_dark_theme]
COLOR_SECONDARY = COLOR_SCHEMES["COLOR_SECONDARY"][is_dark_theme]
COLOR_TAB_INACTVE = COLOR_SCHEMES["COLOR_TAB_INACTVE"][is_dark_theme]
COLOR_PROGRESSBAR = COLOR_SCHEMES["COLOR_PROGRESSBAR"][is_dark_theme]
COLOR_ZERO = COLOR_SCHEMES["COLOR_ZERO"][is_dark_theme]
COLOR_ONE = COLOR_SCHEMES["COLOR_ONE"][is_dark_theme]
COLOR_TWO = COLOR_SCHEMES["COLOR_TWO"][is_dark_theme]
COLOR_THREE = COLOR_SCHEMES["COLOR_THREE"][is_dark_theme]
COLOR_FOUR = COLOR_SCHEMES["COLOR_FOUR"][is_dark_theme]
COLOR_FIVE = COLOR_SCHEMES["COLOR_FIVE"][is_dark_theme]
COLOR_SIX = COLOR_SCHEMES["COLOR_SIX"][is_dark_theme]
COLOR_SEVEN = COLOR_SCHEMES["COLOR_SEVEN"][is_dark_theme]
COLOR_EIGHT = COLOR_SCHEMES["COLOR_EIGHT"][is_dark_theme]
COLOR_NINE = COLOR_SCHEMES["COLOR_NINE"][is_dark_theme]
COLOR_OPTIONS = COLOR_SCHEMES["COLOR_OPTIONS"][is_dark_theme]
TREEVIEW_SELECTED_COLOR = COLOR_SCHEMES["TREEVIEW_SELECTED_COLOR"][is_dark_theme]
COLOR_MILISECONDS_HIGH = COLOR_SCHEMES["COLOR_MILISECONDS_HIGH"][is_dark_theme]
COLOR_MILISECONDS_LOW = COLOR_SCHEMES["COLOR_MILISECONDS_LOW"][is_dark_theme]
DEFAULT_BUTTON_COLOR = COLOR_SCHEMES["DEFAULT_BUTTON_COLOR"][is_dark_theme]
DEFAULT_BUTTON_COLOR_ACTIVE = COLOR_SCHEMES["DEFAULT_BUTTON_COLOR_ACTIVE"][
    is_dark_theme
]
BUTTON_COLOR_MANUAL = COLOR_SCHEMES["BUTTON_COLOR_MANUAL"][is_dark_theme]
BUTTON_COLOR_MANUAL_ACTIVE = COLOR_SCHEMES["BUTTON_COLOR_MANUAL_ACTIVE"][is_dark_theme]
BUTTON_COLOR_AUTO = COLOR_SCHEMES["BUTTON_COLOR_AUTO"][is_dark_theme]
BUTTON_COLOR_AUTO_ACTIVE = COLOR_SCHEMES["BUTTON_COLOR_AUTO_ACTIVE"][is_dark_theme]
BUTTON_COLOR_BATCH = COLOR_SCHEMES["BUTTON_COLOR_BATCH"][is_dark_theme]
BUTTON_COLOR_BATCH_ACTIVE = COLOR_SCHEMES["BUTTON_COLOR_BATCH_ACTIVE"][is_dark_theme]

# Font Fix: if platform is macOS or Linux, adjust font settings accordingly
if platform == "Darwin" and config.get("log_window_font", "Cascadia Code") in [
    "Cascadia Code",
    "Cascadia Code SemiLight",
]:
    config["log_window_font"] = "Andale Mono"
    config["log_window_font_size"] = 10
    config["log_window_font_style"] = "normal"
elif platform == "Linux" and config.get("log_window_font", "Cascadia Code") in [
    "Cascadia Code",
    "Cascadia Code SemiLight",
]:
    config["log_window_font"] = "Noto Sans Sinhala"
    config["log_window_font_size"] = 8
    config["log_window_font_style"] = "normal"

# Fix small font size on macOS
if platform == "Darwin":  # macOS
    FONT_SIZE = 12  # Bigger font for macOS
    FONT_SIZE_TWO = 14
else:  # Windows or Linux
    FONT_SIZE = 8  # Default font size
    FONT_SIZE_TWO = 10