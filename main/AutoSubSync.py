import os
import sys
import re
import shutil
import subprocess
import threading
import xml.etree.ElementTree as ET
import ctypes
import json
import webbrowser
import platform
import tkinter as tk
import tkinter.font as tkFont
from datetime import datetime
from tkinter import filedialog, ttk, messagebox, PhotoImage, Menu, simpledialog
from tkinterdnd2 import DND_FILES, TkinterDnD
from alass_encodings import enc_list
import cchardet
import charset_normalizer
import chardet
import requests
import psutil
import signal
import texts

platform = platform.system()
if platform == "Darwin":  # macOS
    from tkmacosx import Button as TkButton
else:  # Windows or Linux
    from tkinter import Button as TkButton


def get_base_dir():
    if getattr(sys, "frozen", False):
        # Running as PyInstaller executable
        if platform == "Linux":
            base_dir = os.path.expanduser("~/.AutoSubSync")
            # Ensure the directory exists
            if not os.path.exists(base_dir):
                os.makedirs(base_dir, exist_ok=True)
        else:
            base_dir = os.path.dirname(sys.executable)
    else:
        # Running as Python script
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return base_dir


base_dir = get_base_dir()
program_dir = os.path.dirname(os.path.abspath(__file__))

# Set the working directory to the script's directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Define paths to the executables - FIXED
ffmpeg_bin = os.path.normpath(os.path.join(program_dir, "resources", "ffmpeg-bin"))
alass_bin = os.path.normpath(os.path.join(program_dir, "resources", "alass-bin"))
ffsubsync_bin = os.path.normpath(
    os.path.join(program_dir, "resources", "ffsubsync-bin")
)

# Add the paths to the system PATH environment variable
os.environ["PATH"] = (
    ffmpeg_bin
    + os.pathsep
    + alass_bin
    + os.pathsep
    + ffsubsync_bin
    + os.pathsep
    + os.environ["PATH"]
)

# Determine correct alass executable based on platform
if platform == "Windows":
    CALL_ALASS = os.path.join(alass_bin, "alass-cli")
elif platform == "Linux":
    CALL_ALASS = os.path.join(alass_bin, "alass-linux64")
else:
    CALL_ALASS = os.path.join(alass_bin, "alass")  # fallback

# Determine correct ffmpeg, ffprobe, and ffsubsync executables based on platform
if platform == "Windows":
    CALL_FFMPEG = os.path.join(ffmpeg_bin, "ffmpeg.exe")
    CALL_FFPROBE = os.path.join(ffmpeg_bin, "ffprobe.exe")
    CALL_FFSUBSYNC = os.path.join(ffsubsync_bin, "ffsubsync.exe")
else:
    CALL_FFMPEG = os.path.join(ffmpeg_bin, "ffmpeg")
    CALL_FFPROBE = os.path.join(ffmpeg_bin, "ffprobe")
    CALL_FFSUBSYNC = os.path.join(ffsubsync_bin, "ffsubsync")

# Set execute permissions for ffmpeg, ffprobe, and ffsubsync in MacOS and Linux
if platform in ["Darwin", "Linux"]:
    import stat

    executables = [CALL_FFMPEG, CALL_FFPROBE, CALL_FFSUBSYNC]
    errors = []
    for exe in executables:
        exe_path = (
            os.path.join(ffmpeg_bin, exe)
            if exe in ["ffmpeg", "ffprobe"]
            else os.path.join(ffsubsync_bin, exe)
        )
        if os.path.exists(exe_path):
            current_permissions = os.stat(exe_path).st_mode
            if not current_permissions & stat.S_IEXEC:
                try:
                    os.chmod(exe_path, current_permissions | stat.S_IEXEC)
                except Exception as e:
                    errors.append(
                        f"Failed to set execute permissions for {exe_path}: {e}"
                    )
    if errors:
        messagebox.showerror("Permission Error", "\n".join(errors))

# Config file
default_settings = {
    "theme": "system",
    "keep_logs": True,
    "log_window_font": "Cascadia Code SemiLight",
    "log_window_font_size": 7,
    "log_window_font_style": "normal",
    "remember_the_changes": True,
    "notify_about_updates": True,
    "ffsubsync_option_framerate": False,
    "ffsubsync_option_gss": False,
    "ffsubsync_option_vad": "default",
    "alass_disable_fps_guessing": False,
    "alass_speed_optimization": False,
    "alass_split_penalty": 7,
    "action_var_auto": "OPTION_SAVE_NEXT_TO_SUBTITLE",
    "sync_tool_var_auto": "SYNC_TOOL_FFSUBSYNC",
    "keep_converted_subtitles": True,
    "keep_extracted_subtitles": True,
    "backup_subtitles_before_overwriting": True,
    "check_video_for_subtitle_stream_in_alass": True,
    "add_prefix": True,
    "additional_ffsubsync_args": "",
    "additional_alass_args": "",
}

config_path = os.path.join(base_dir, "config.json")


def create_config_file():
    with open(config_path, "w", encoding="utf-8") as config_file:
        json.dump(default_settings, config_file, indent=4)


if not os.path.exists(config_path):
    create_config_file()

try:
    with open(config_path, "r", encoding="utf-8") as config_file:
        config = json.load(config_file)
except FileNotFoundError:
    config = {}
    messagebox.showerror("Error", '"config.json" file not found')
try:
    with open("VERSION", "r", encoding="utf-8") as version_file:
        VERSION = version_file.read().strip()
except FileNotFoundError:
    VERSION = " UNKNOWN VERSION"
    messagebox.showerror("Error", '"VERSION" file not found')


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
# Save the updated configuration
try:
    with open(config_path, "w", encoding="utf-8") as config_file:
        json.dump(config, config_file, indent=4)
except Exception as e:
    messagebox.showerror("Error", "Failed to fix font: " + str(e))

# Fix small font size on macOS
if platform == "Darwin":  # macOS
    FONT_SIZE = 12  # Bigger font for macOS
    FONT_SIZE_TWO = 14
else:  # Windows or Linux
    FONT_SIZE = 8  # Default font size
    FONT_SIZE_TWO = 10

# Get the theme from the config, or set it based on the system's theme
THEME = config.get("theme", "system")
if THEME == "system":
    THEME = "dark" if is_dark_mode() else "light"

# File extensions
FFSUBSYNC_SUPPORTED_EXTENSIONS = [".srt", ".ass", ".ssa", ".vtt"]
ALASS_SUPPORTED_EXTENSIONS = [".srt", ".ass", ".ssa", ".sub", ".idx"]
ALASS_EXTRACTABLE_SUBTITLE_EXTENSIONS = {"subrip": "srt", "ass": "ass", "webvtt": "vtt"}
SUBTITLE_EXTENSIONS = [
    ".srt",
    ".vtt",
    ".sbv",
    ".sub",
    ".ass",
    ".ssa",
    ".dfxp",
    ".ttml",
    ".itt",
    ".stl",
    ".idx",
]
VIDEO_EXTENSIONS = [
    ".mp4",
    ".mkv",
    ".avi",
    ".webm",
    ".flv",
    ".mov",
    ".wmv",
    ".mpg",
    ".mpeg",
    ".m4v",
    ".3gp",
    ".h264",
    ".h265",
    ".hevc",
]
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
# Language selection (ALL TRANSLATIONS ARE LOCATED IN "texts.py")
LANGUAGE = config.get("language", "en")
LANGUAGES = {
    "English": "en",
    "Español": "es",
    "Deutsch": "de",
    "Français": "fr",
    "Italiano": "it",
    "Polski": "pl",
    "Português": "pt",
    "Türkçe": "tr",
    "Tiếng Việt": "vi",
    "Bahasa Indonesia": "id",
    "Bahasa Melayu": "ms",
    "ไทย": "th",
    "Українська": "uk",
    "Русский": "ru",
    "中国人": "zh",
    "日本語": "ja",
    "한국어": "ko",
    "हिन्दी": "hi",
    "বাংলা": "bn",
    "اردو": "ur",
    "العربية": "ar",
    "فارسی": "fa",
}
# Program information
PROGRAM_NAME = texts.PROGRAM_NAME
GITHUB_URL = texts.GITHUB_URL
GITHUB_VERSION_URL = texts.GITHUB_VERSION_URL
GITHUB_LATEST_RELEASE_URL = texts.GITHUB_LATEST_RELEASE_URL
# Tooltip texts for checkboxes
TOOLTIP_SAVE_TO_DESKTOP = texts.TOOLTIP_SAVE_TO_DESKTOP[LANGUAGE]
TOOLTIP_REPLACE_ORIGINAL = texts.TOOLTIP_REPLACE_ORIGINAL[LANGUAGE]
TOOLTIP_GSS = texts.TOOLTIP_GSS[LANGUAGE]
TOOLTIP_VAD = texts.TOOLTIP_VAD[LANGUAGE]
TOOLTIP_FRAMERATE = texts.TOOLTIP_FRAMERATE[LANGUAGE]
TOOLTIP_ALASS_SPEED_OPTIMIZATION = texts.TOOLTIP_ALASS_SPEED_OPTIMIZATION[LANGUAGE]
TOOLTIP_ALASS_DISABLE_FPS_GUESSING = texts.TOOLTIP_ALASS_DISABLE_FPS_GUESSING[LANGUAGE]
TOOLTIP_TEXT_ACTION_MENU_AUTO = texts.TOOLTIP_TEXT_ACTION_MENU_AUTO[LANGUAGE]
TOOLTIP_TEXT_SYNC_TOOL_MENU_AUTO = texts.TOOLTIP_TEXT_SYNC_TOOL_MENU_AUTO[LANGUAGE]
# Dialogs - Buttons
NOTIFY_ABOUT_UPDATES_TEXT = texts.NOTIFY_ABOUT_UPDATES_TEXT[LANGUAGE]
UPDATE_AVAILABLE_TEXT = texts.UPDATE_AVAILABLE_TEXT[LANGUAGE]
UPDATE_AVAILABLE_TITLE = texts.UPDATE_AVAILABLE_TITLE[LANGUAGE]
LANGUAGE_LABEL_TEXT = texts.LANGUAGE_LABEL_TEXT[LANGUAGE]
TAB_AUTOMATIC_SYNC = texts.TAB_AUTOMATIC_SYNC[LANGUAGE]
TAB_MANUAL_SYNC = texts.TAB_MANUAL_SYNC[LANGUAGE]
CANCEL_TEXT = texts.CANCEL_TEXT[LANGUAGE]
GENERATE_AGAIN_TEXT = texts.GENERATE_AGAIN_TEXT[LANGUAGE]
GO_BACK = texts.GO_BACK[LANGUAGE]
BATCH_MODE_TEXT = texts.BATCH_MODE_TEXT[LANGUAGE]
NORMAL_MODE_TEXT = texts.NORMAL_MODE_TEXT[LANGUAGE]
START_AUTOMATIC_SYNC_TEXT = texts.START_AUTOMATIC_SYNC_TEXT[LANGUAGE]
START_BATCH_SYNC_TEXT = texts.START_BATCH_SYNC_TEXT[LANGUAGE]
BATCH_INPUT_TEXT = texts.BATCH_INPUT_TEXT[LANGUAGE]
BATCH_INPUT_LABEL_TEXT = texts.BATCH_INPUT_LABEL_TEXT[LANGUAGE]
SHIFT_SUBTITLE_TEXT = texts.SHIFT_SUBTITLE_TEXT[LANGUAGE]
LABEL_SHIFT_SUBTITLE = texts.LABEL_SHIFT_SUBTITLE[LANGUAGE]
REPLACE_ORIGINAL_TITLE = texts.REPLACE_ORIGINAL_TITLE[LANGUAGE]
REPLACE_ORIGINAL_TEXT = texts.REPLACE_ORIGINAL_TEXT[LANGUAGE]
FILE_EXISTS_TITLE = texts.FILE_EXISTS_TITLE[LANGUAGE]
FILE_EXISTS_TEXT = texts.FILE_EXISTS_TEXT[LANGUAGE]
ALREADY_SYNCED_FILES_TITLE = texts.ALREADY_SYNCED_FILES_TITLE[LANGUAGE]
ALREADY_SYNCED_FILES_MESSAGE = texts.ALREADY_SYNCED_FILES_MESSAGE[LANGUAGE]
SUBTITLE_INPUT_TEXT = texts.SUBTITLE_INPUT_TEXT[LANGUAGE]
VIDEO_INPUT_TEXT = texts.VIDEO_INPUT_TEXT[LANGUAGE]
LABEL_DROP_BOX = texts.LABEL_DROP_BOX[LANGUAGE]
WARNING = texts.WARNING[LANGUAGE]
CONFIRM_RESET_MESSAGE = texts.CONFIRM_RESET_MESSAGE[LANGUAGE]
TOGGLE_KEEP_CONVERTED_SUBTITLES_WARNING = texts.TOGGLE_KEEP_CONVERTED_SUBTITLES_WARNING[
    LANGUAGE
]
TOGGLE_KEEP_EXTRACTED_SUBTITLES_WARNING = texts.TOGGLE_KEEP_EXTRACTED_SUBTITLES_WARNING[
    LANGUAGE
]
BACKUP_SUBTITLES_BEFORE_OVERWRITING_WARNING = (
    texts.BACKUP_SUBTITLES_BEFORE_OVERWRITING_WARNING[LANGUAGE]
)
PROMPT_ADDITIONAL_FFSUBSYNC_ARGS = texts.PROMPT_ADDITIONAL_FFSUBSYNC_ARGS[LANGUAGE]
PROMPT_ADDITIONAL_ALASS_ARGS = texts.PROMPT_ADDITIONAL_ALASS_ARGS[LANGUAGE]
LABEL_ADDITIONAL_FFSUBSYNC_ARGS = texts.LABEL_ADDITIONAL_FFSUBSYNC_ARGS[LANGUAGE]
LABEL_ADDITIONAL_ALASS_ARGS = texts.LABEL_ADDITIONAL_ALASS_ARGS[LANGUAGE]
LABEL_CHECK_VIDEO_FOR_SUBTITLE_STREAM = texts.LABEL_CHECK_VIDEO_FOR_SUBTITLE_STREAM[
    LANGUAGE
]
LABEL_ADD_PREFIX = texts.LABEL_ADD_PREFIX[LANGUAGE]
LABEL_BACKUP_SUBTITLES = texts.LABEL_BACKUP_SUBTITLES[LANGUAGE]
LABEL_KEEP_CONVERTED_SUBTITLES = texts.LABEL_KEEP_CONVERTED_SUBTITLES[LANGUAGE]
LABEL_KEEP_EXTRACTED_SUBTITLES = texts.LABEL_KEEP_EXTRACTED_SUBTITLES[LANGUAGE]
LABEL_REMEMBER_THE_CHANGES = texts.LABEL_REMEMBER_THE_CHANGES[LANGUAGE]
LABEL_RESET_TO_DEFAULT_SETTINGS = texts.LABEL_RESET_TO_DEFAULT_SETTINGS[LANGUAGE]
# Options
DEFAULT = texts.DEFAULT[LANGUAGE]
VOICE_ACTIVITY_DETECTOR = texts.VOICE_ACTIVITY_DETECTOR[LANGUAGE]
LABEL_KEEP_LOG_RECORDS = texts.LABEL_KEEP_LOG_RECORDS[LANGUAGE]
LABEL_OPEN_LOGS_FOLDER = texts.LABEL_OPEN_LOGS_FOLDER[LANGUAGE]
LABEL_CLEAR_ALL_LOGS = texts.LABEL_CLEAR_ALL_LOGS[LANGUAGE]
LOG_FILES_DELETE_WARNING = texts.LOG_FILES_DELETE_WARNING[LANGUAGE]
SYNC_TOOL_FFSUBSYNC = texts.SYNC_TOOL_FFSUBSYNC[LANGUAGE]
SYNC_TOOL_ALASS = texts.SYNC_TOOL_ALASS[LANGUAGE]
OPTION_SAVE_NEXT_TO_SUBTITLE = texts.OPTION_SAVE_NEXT_TO_SUBTITLE[LANGUAGE]
OPTION_SAVE_NEXT_TO_VIDEO = texts.OPTION_SAVE_NEXT_TO_VIDEO[LANGUAGE]
OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME = (
    texts.OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME[LANGUAGE]
)
OPTION_SAVE_TO_DESKTOP = texts.OPTION_SAVE_TO_DESKTOP[LANGUAGE]
OPTION_REPLACE_ORIGINAL_SUBTITLE = texts.OPTION_REPLACE_ORIGINAL_SUBTITLE[LANGUAGE]
OPTION_SELECT_DESTINATION_FOLDER = texts.OPTION_SELECT_DESTINATION_FOLDER[LANGUAGE]
CHECKBOX_NO_FIX_FRAMERATE = texts.CHECKBOX_NO_FIX_FRAMERATE[LANGUAGE]
CHECKBOX_GSS = texts.CHECKBOX_GSS[LANGUAGE]
CHECKBOX_VAD = texts.CHECKBOX_VAD[LANGUAGE]
LABEL_SPLIT_PENALTY = texts.LABEL_SPLIT_PENALTY[LANGUAGE]
PAIR_FILES_TITLE = texts.PAIR_FILES_TITLE[LANGUAGE]
PAIR_FILES_MESSAGE = texts.PAIR_FILES_MESSAGE[LANGUAGE]
UNPAIRED_SUBTITLES_TITLE = texts.UNPAIRED_SUBTITLES_TITLE[LANGUAGE]
UNPAIRED_SUBTITLES_MESSAGE = texts.UNPAIRED_SUBTITLES_MESSAGE[LANGUAGE]
NO_VIDEO = texts.NO_VIDEO[LANGUAGE]
NO_SUBTITLE = texts.NO_SUBTITLE[LANGUAGE]
VIDEO_OR_SUBTITLE_TEXT = texts.VIDEO_OR_SUBTITLE_TEXT[LANGUAGE]
VIDEO_INPUT_LABEL = texts.VIDEO_INPUT_LABEL[LANGUAGE]
SUBTITLE_INPUT_LABEL = texts.SUBTITLE_INPUT_LABEL[LANGUAGE]
SUBTITLE_FILES_TEXT = texts.SUBTITLE_FILES_TEXT[LANGUAGE]
CONTEXT_MENU_REMOVE = texts.CONTEXT_MENU_REMOVE[LANGUAGE]
CONTEXT_MENU_CHANGE = texts.CONTEXT_MENU_CHANGE[LANGUAGE]
CONTEXT_MENU_ADD_PAIR = texts.CONTEXT_MENU_ADD_PAIR[LANGUAGE]
CONTEXT_MENU_ADD_PAIRS = texts.CONTEXT_MENU_ADD_PAIRS[LANGUAGE]
CONTEXT_MENU_CLEAR_ALL = texts.CONTEXT_MENU_CLEAR_ALL[LANGUAGE]
CONTEXT_MENU_SHOW_PATH = texts.CONTEXT_MENU_SHOW_PATH[LANGUAGE]
CONTEXT_MENU_COPY = texts.CONTEXT_MENU_COPY[LANGUAGE]
BUTTON_ADD_FILES = texts.BUTTON_ADD_FILES[LANGUAGE]
MENU_ADD_FOLDER = texts.MENU_ADD_FOLDER[LANGUAGE]
MENU_ADD_MULTIPLE_FILES = texts.MENU_ADD_MULTIPLE_FILES[LANGUAGE]
MENU_ADD_REFERENCE_SUBITLE_SUBTITLE_PAIRIS = (
    texts.MENU_ADD_REFERENCE_SUBITLE_SUBTITLE_PAIRIS[LANGUAGE]
)
ALASS_SPEED_OPTIMIZATION_TEXT = texts.ALASS_SPEED_OPTIMIZATION_TEXT[LANGUAGE]
ALASS_DISABLE_FPS_GUESSING_TEXT = texts.ALASS_DISABLE_FPS_GUESSING_TEXT[LANGUAGE]
REF_DROP_TEXT = texts.REF_DROP_TEXT[LANGUAGE]
SUB_DROP_TEXT = texts.SUB_DROP_TEXT[LANGUAGE]
REF_LABEL_TEXT = texts.REF_LABEL_TEXT[LANGUAGE]
SUB_LABEL_TEXT = texts.SUB_LABEL_TEXT[LANGUAGE]
PROCESS_PAIRS = texts.PROCESS_PAIRS[LANGUAGE]
SYNC_TOOL_LABEL_TEXT = texts.SYNC_TOOL_LABEL_TEXT[LANGUAGE]
EXPLANATION_TEXT_IN_REFERENCE_SUBTITLE_PAIRING = (
    texts.EXPLANATION_TEXT_IN_REFERENCE_SUBTITLE_PAIRING[LANGUAGE]
)
THEME_TEXT = texts.THEME_TEXT[LANGUAGE]
THEME_SYSTEM_TEXT = texts.THEME_SYSTEM_TEXT[LANGUAGE]
THEME_DARK_TEXT = texts.THEME_DARK_TEXT[LANGUAGE]
THEME_LIGHT_TEXT = texts.THEME_LIGHT_TEXT[LANGUAGE]
# Log messages
SUCCESS_LOG_TEXT = texts.SUCCESS_LOG_TEXT[LANGUAGE]
SYNC_SUCCESS_MESSAGE = texts.SYNC_SUCCESS_MESSAGE[LANGUAGE]
ERROR_SAVING_SUBTITLE = texts.ERROR_SAVING_SUBTITLE[LANGUAGE]
NON_ZERO_MILLISECONDS = texts.NON_ZERO_MILLISECONDS[LANGUAGE]
SELECT_ONLY_ONE_OPTION = texts.SELECT_ONLY_ONE_OPTION[LANGUAGE]
VALID_NUMBER_MILLISECONDS = texts.VALID_NUMBER_MILLISECONDS[LANGUAGE]
DIALOG_TITLE_TEXT = texts.DIALOG_TITLE_TEXT[LANGUAGE]
FONT_FAMILY_LABEL_TEXT = texts.FONT_FAMILY_LABEL_TEXT[LANGUAGE]
FONT_SIZE_LABEL_TEXT = texts.FONT_SIZE_LABEL_TEXT[LANGUAGE]
FONT_STYLE_LABEL_TEXT = texts.FONT_STYLE_LABEL_TEXT[LANGUAGE]
BOLD_TEXT = texts.BOLD_TEXT[LANGUAGE]
ITALIC_TEXT = texts.ITALIC_TEXT[LANGUAGE]
UNDERLINE_TEXT = texts.UNDERLINE_TEXT[LANGUAGE]
STRIKETHROUGH_TEXT = texts.STRIKETHROUGH_TEXT[LANGUAGE]
FONT_INFORMATION_TEXT = texts.FONT_INFORMATION_TEXT[LANGUAGE]
APPLY_TEXT = texts.APPLY_TEXT[LANGUAGE]
SELECT_SUBTITLE = texts.SELECT_SUBTITLE[LANGUAGE]
SELECT_VIDEO = texts.SELECT_VIDEO[LANGUAGE]
SELECT_VIDEO_OR_SUBTITLE = texts.SELECT_VIDEO_OR_SUBTITLE[LANGUAGE]
DROP_VIDEO_SUBTITLE_PAIR = texts.DROP_VIDEO_SUBTITLE_PAIR[LANGUAGE]
DROP_VIDEO_OR_SUBTITLE = texts.DROP_VIDEO_OR_SUBTITLE[LANGUAGE]
DROP_SUBTITLE_FILE = texts.DROP_SUBTITLE_FILE[LANGUAGE]
DROP_SINGLE_SUBTITLE_FILE = texts.DROP_SINGLE_SUBTITLE_FILE[LANGUAGE]
DROP_SINGLE_SUBTITLE_PAIR = texts.DROP_SINGLE_SUBTITLE_PAIR[LANGUAGE]
SELECT_BOTH_FILES = texts.SELECT_BOTH_FILES[LANGUAGE]
SELECT_DIFFERENT_FILES = texts.SELECT_DIFFERENT_FILES[LANGUAGE]
SUBTITLE_FILE_NOT_EXIST = texts.SUBTITLE_FILE_NOT_EXIST[LANGUAGE]
VIDEO_FILE_NOT_EXIST = texts.VIDEO_FILE_NOT_EXIST[LANGUAGE]
ERROR_LOADING_SUBTITLE = texts.ERROR_LOADING_SUBTITLE[LANGUAGE]
ERROR_CONVERT_TIMESTAMP = texts.ERROR_CONVERT_TIMESTAMP[LANGUAGE]
ERROR_PARSING_TIME_STRING = texts.ERROR_PARSING_TIME_STRING[LANGUAGE]
ERROR_PARSING_TIME_STRING_DETAILED = texts.ERROR_PARSING_TIME_STRING_DETAILED[LANGUAGE]
NO_FILES_TO_SYNC = texts.NO_FILES_TO_SYNC[LANGUAGE]
NO_VALID_FILE_PAIRS = texts.NO_VALID_FILE_PAIRS[LANGUAGE]
ERROR_PROCESS_TERMINATION = texts.ERROR_PROCESS_TERMINATION[LANGUAGE]
BATCH_SYNC_CANCEL_CONFIRMATION = texts.BATCH_SYNC_CANCEL_CONFIRMATION[LANGUAGE]
AUTO_SYNC_CANCELLED = texts.AUTO_SYNC_CANCELLED[LANGUAGE]
BATCH_SYNC_CANCELLED = texts.BATCH_SYNC_CANCELLED[LANGUAGE]
NO_SYNC_PROCESS = texts.NO_SYNC_PROCESS[LANGUAGE]
INVALID_SYNC_TOOL = texts.INVALID_SYNC_TOOL[LANGUAGE]
FAILED_START_PROCESS = texts.FAILED_START_PROCESS[LANGUAGE]
ERROR_OCCURRED = texts.ERROR_OCCURRED[LANGUAGE]
ERROR_DECODING_SUBTITLE = texts.ERROR_DECODING_SUBTITLE[LANGUAGE]
ERROR_EXECUTING_COMMAND = texts.ERROR_EXECUTING_COMMAND[LANGUAGE]
DROP_VALID_FILES = texts.DROP_VALID_FILES[LANGUAGE]
PAIRS_ADDED = texts.PAIRS_ADDED[LANGUAGE]
UNPAIRED_FILES_ADDED = texts.UNPAIRED_FILES_ADDED[LANGUAGE]
UNPAIRED_FILES = texts.UNPAIRED_FILES[LANGUAGE]
DUPLICATE_PAIRS_SKIPPED = texts.DUPLICATE_PAIRS_SKIPPED[LANGUAGE]
PAIR_ALREADY_EXISTS = texts.PAIR_ALREADY_EXISTS[LANGUAGE]
PAIR_ADDED = texts.PAIR_ADDED[LANGUAGE]
SAME_FILE_ERROR = texts.SAME_FILE_ERROR[LANGUAGE]
PAIR_ALREADY_EXISTS = texts.PAIR_ALREADY_EXISTS[LANGUAGE]
SUBTITLE_ADDED = texts.SUBTITLE_ADDED[LANGUAGE]
VIDEO_ADDED = texts.VIDEO_ADDED[LANGUAGE]
FILE_CHANGED = texts.FILE_CHANGED[LANGUAGE]
SELECT_ITEM_TO_CHANGE = texts.SELECT_ITEM_TO_CHANGE[LANGUAGE]
SELECT_ITEM_TO_REMOVE = texts.SELECT_ITEM_TO_REMOVE[LANGUAGE]
FILE_NOT_EXIST = texts.FILE_NOT_EXIST[LANGUAGE]
MULTIPLE_ARGUMENTS = texts.MULTIPLE_ARGUMENTS[LANGUAGE]
INVALID_FILE_FORMAT = texts.INVALID_FILE_FORMAT[LANGUAGE]
INVALID_SYNC_TOOL_SELECTED = texts.INVALID_SYNC_TOOL_SELECTED[LANGUAGE]
TEXT_SELECTED_FOLDER = texts.TEXT_SELECTED_FOLDER[LANGUAGE]
TEXT_NO_FOLDER_SELECTED = texts.TEXT_NO_FOLDER_SELECTED[LANGUAGE]
TEXT_DESTINATION_FOLDER_DOES_NOT_EXIST = texts.TEXT_DESTINATION_FOLDER_DOES_NOT_EXIST[
    LANGUAGE
]
ADDED_PAIRS_MSG = texts.ADDED_PAIRS_MSG[LANGUAGE]
SKIPPED_DUPLICATES_MSG = texts.SKIPPED_DUPLICATES_MSG[LANGUAGE]
NO_VALID_SUBTITLE_PAIRS_TO_PROCESS = texts.NO_VALID_SUBTITLE_PAIRS_TO_PROCESS[LANGUAGE]
NO_MATCHING_SUBTITLE_PAIRS_FOUND = texts.NO_MATCHING_SUBTITLE_PAIRS_FOUND[LANGUAGE]
NO_SUBTITLE_PAIRS_TO_PROCESS = texts.NO_SUBTITLE_PAIRS_TO_PROCESS[LANGUAGE]
NOT_FIND_COMPATIBLE_FILE_MANAGER = texts.NOT_FIND_COMPATIBLE_FILE_MANAGER[LANGUAGE]
FILE_NOT_FOUND = texts.FILE_NOT_FOUND[LANGUAGE]
ERROR_OPENING_DIRECTORY = texts.ERROR_OPENING_DIRECTORY[LANGUAGE]
CONFIG_FILE_NOT_FOUND = texts.CONFIG_FILE_NOT_FOUND[LANGUAGE]
# Log window messages
VIDEO_FILE_NOT_FOUND = texts.VIDEO_FILE_NOT_FOUND[LANGUAGE]
FFPROBE_FAILED = texts.FFPROBE_FAILED[LANGUAGE]
SUBTITLE_EXTRACTION_FAILED = texts.SUBTITLE_EXTRACTION_FAILED[LANGUAGE]
SYNCING_LOG_TEXT = texts.SYNCING_LOG_TEXT[LANGUAGE]
INVALID_PARENT_ITEM = texts.INVALID_PARENT_ITEM[LANGUAGE]
SKIP_NO_VIDEO_NO_SUBTITLE = texts.SKIP_NO_VIDEO_NO_SUBTITLE[LANGUAGE]
SKIP_NO_SUBTITLE = texts.SKIP_NO_SUBTITLE[LANGUAGE]
SKIP_NO_VIDEO = texts.SKIP_NO_VIDEO[LANGUAGE]
SKIP_UNPAIRED_ITEM = texts.SKIP_UNPAIRED_ITEM[LANGUAGE]
SKIPPING_ALREADY_SYNCED = texts.SKIPPING_ALREADY_SYNCED[LANGUAGE]
CONVERTING_SUBTITLE = texts.CONVERTING_SUBTITLE[LANGUAGE]
ERROR_CONVERTING_SUBTITLE = texts.ERROR_CONVERTING_SUBTITLE[LANGUAGE]
SUBTITLE_CONVERTED = texts.SUBTITLE_CONVERTED[LANGUAGE]
ERROR_UNSUPPORTED_CONVERSION = texts.ERROR_UNSUPPORTED_CONVERSION[LANGUAGE]
FAILED_CONVERT_SUBTITLE = texts.FAILED_CONVERT_SUBTITLE[LANGUAGE]
FAILED_CONVERT_VIDEO = texts.FAILED_CONVERT_VIDEO[LANGUAGE]
SPLIT_PENALTY_ZERO = texts.SPLIT_PENALTY_ZERO[LANGUAGE]
SPLIT_PENALTY_SET = texts.SPLIT_PENALTY_SET[LANGUAGE]
USING_REFERENCE_SUBTITLE = texts.USING_REFERENCE_SUBTITLE[LANGUAGE]
USING_VIDEO_FOR_SYNC = texts.USING_VIDEO_FOR_SYNC[LANGUAGE]
ENABLED_NO_FIX_FRAMERATE = texts.ENABLED_NO_FIX_FRAMERATE[LANGUAGE]
ENABLED_GSS = texts.ENABLED_GSS[LANGUAGE]
ADDITIONAL_ARGS_ADDED = texts.ADDITIONAL_ARGS_ADDED[LANGUAGE]
SYNCING_STARTED = texts.SYNCING_STARTED[LANGUAGE]
SYNCING_ENDED = texts.SYNCING_ENDED[LANGUAGE]
SYNC_SUCCESS = texts.SYNC_SUCCESS[LANGUAGE]
SYNC_ERROR = texts.SYNC_ERROR[LANGUAGE]
SYNC_ERROR_OCCURRED = texts.SYNC_ERROR_OCCURRED[LANGUAGE]
BATCH_SYNC_COMPLETED = texts.BATCH_SYNC_COMPLETED[LANGUAGE]
PREPARING_SYNC = texts.PREPARING_SYNC[LANGUAGE]
CONVERTING_TTML = texts.CONVERTING_TTML[LANGUAGE]
CONVERTING_VTT = texts.CONVERTING_VTT[LANGUAGE]
CONVERTING_SBV = texts.CONVERTING_SBV[LANGUAGE]
CONVERTING_SUB = texts.CONVERTING_SUB[LANGUAGE]
CONVERTING_ASS = texts.CONVERTING_ASS[LANGUAGE]
CONVERTING_STL = texts.CONVERTING_STL[LANGUAGE]
ERROR_CONVERTING_SUBTITLE = texts.ERROR_CONVERTING_SUBTITLE[LANGUAGE]
CONVERSION_NOT_SUPPORTED = texts.CONVERSION_NOT_SUPPORTED[LANGUAGE]
SUBTITLE_CONVERTED = texts.SUBTITLE_CONVERTED[LANGUAGE]
RETRY_ENCODING_MSG = texts.RETRY_ENCODING_MSG[LANGUAGE]
ALASS_SPEED_OPTIMIZATION_LOG = texts.ALASS_SPEED_OPTIMIZATION_LOG[LANGUAGE]
ALASS_DISABLE_FPS_GUESSING_LOG = texts.ALASS_DISABLE_FPS_GUESSING_LOG[LANGUAGE]
CHANGING_ENCODING_MSG = texts.CHANGING_ENCODING_MSG[LANGUAGE]
ENCODING_CHANGED_MSG = texts.ENCODING_CHANGED_MSG[LANGUAGE]
SYNC_SUCCESS_COUNT = texts.SYNC_SUCCESS_COUNT[LANGUAGE]
SYNC_FAILURE_COUNT = texts.SYNC_FAILURE_COUNT[LANGUAGE]
SYNC_FAILURE_COUNT_BATCH = texts.SYNC_FAILURE_COUNT_BATCH[LANGUAGE]
ERROR_CHANGING_ENCODING_MSG = texts.ERROR_CHANGING_ENCODING_MSG[LANGUAGE]
BACKUP_CREATED = texts.BACKUP_CREATED[LANGUAGE]
CHECKING_SUBTITLE_STREAMS = texts.CHECKING_SUBTITLE_STREAMS[LANGUAGE]
FOUND_COMPATIBLE_SUBTITLES = texts.FOUND_COMPATIBLE_SUBTITLES[LANGUAGE]
NO_COMPATIBLE_SUBTITLES = texts.NO_COMPATIBLE_SUBTITLES[LANGUAGE]
SUCCESSFULLY_EXTRACTED = texts.SUCCESSFULLY_EXTRACTED[LANGUAGE]
CHOOSING_BEST_SUBTITLE = texts.CHOOSING_BEST_SUBTITLE[LANGUAGE]
CHOSEN_SUBTITLE = texts.CHOSEN_SUBTITLE[LANGUAGE]
FAILED_TO_EXTRACT_SUBTITLES = texts.FAILED_TO_EXTRACT_SUBTITLES[LANGUAGE]
USED_THE_LONGEST_SUBTITLE = texts.USED_THE_LONGEST_SUBTITLE[LANGUAGE]
DELETING_EXTRACTED_SUBTITLE_FOLDER = texts.DELETING_EXTRACTED_SUBTITLE_FOLDER[LANGUAGE]
DELETING_CONVERTED_SUBTITLE = texts.DELETING_CONVERTED_SUBTITLE[LANGUAGE]
ADDED_FILES_TEXT = texts.ADDED_FILES_TEXT[LANGUAGE]
SKIPPED_DUPLICATE_FILES_TEXT = texts.SKIPPED_DUPLICATE_FILES_TEXT[LANGUAGE]
SKIPPED_OTHER_LIST_FILES_TEXT = texts.SKIPPED_OTHER_LIST_FILES_TEXT[LANGUAGE]
SKIPPED_SEASON_EPISODE_DUPLICATES_TEXT = texts.SKIPPED_SEASON_EPISODE_DUPLICATES_TEXT[
    LANGUAGE
]
SKIPPED_INVALID_FORMAT_FILES_TEXT = texts.SKIPPED_INVALID_FORMAT_FILES_TEXT[LANGUAGE]
NO_FILES_SELECTED = texts.NO_FILES_SELECTED[LANGUAGE]
NO_ITEM_SELECTED_TO_REMOVE = texts.NO_ITEM_SELECTED_TO_REMOVE[LANGUAGE]
NO_FILES_SELECTED_TO_SHOW_PATH = texts.NO_FILES_SELECTED_TO_SHOW_PATH[LANGUAGE]
REMOVED_ITEM = texts.REMOVED_ITEM[LANGUAGE]
FILES_MUST_CONTAIN_PATTERNS = texts.FILES_MUST_CONTAIN_PATTERNS[LANGUAGE]
NO_VALID_SUBTITLE_FILES = texts.NO_VALID_SUBTITLE_FILES[LANGUAGE]
default_encoding = sys.getfilesystemencoding()


def create_process(cmd):
    kwargs = {
        "shell": True,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "universal_newlines": True,
        "encoding": default_encoding,
        "errors": "replace",
    }

    if platform == "Windows":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        kwargs.update(
            {"startupinfo": startupinfo, "creationflags": subprocess.CREATE_NO_WINDOW}
        )

    return subprocess.Popen(cmd, **kwargs)


def update_config(key, value):
    if remember_the_changes or key == "remember_the_changes":
        try:
            with open(config_path, "r", encoding="utf-8") as config_file:
                config = json.load(config_file)
        except FileNotFoundError:
            config = {}
            messagebox.showerror("Error", CONFIG_FILE_NOT_FOUND)
        config[key] = value
        with open(config_path, "w", encoding="utf-8") as config_file:
            json.dump(config, config_file, indent=4)


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


# Shift Subtitle Start
total_shifted_milliseconds = {}


def shift_subtitle(subtitle_file, milliseconds, save_to_desktop, replace_original):
    # Load file with encoding detection using detect_encoding function
    try:
        with open(subtitle_file, "rb") as file:
            raw_data = file.read()
            encoding = detect_encoding(subtitle_file)
            lines = raw_data.decode(encoding).splitlines()
    except Exception as e:
        log_message(
            ERROR_LOADING_SUBTITLE.format(error_message=str(e)), "error", tab="manual"
        )
        return
    file_extension = os.path.splitext(subtitle_file)[-1].lower()
    filename = os.path.basename(subtitle_file)
    new_lines = []
    # Calculate total shift if replace_original is used
    if replace_original and subtitle_file in total_shifted_milliseconds:
        total_shifted = total_shifted_milliseconds[subtitle_file] + milliseconds
    else:
        total_shifted = milliseconds

    # Function to apply time shifting based on format
    def shift_time_srt_vtt(line, format_type):
        def replacer(match):
            start = shift_timestamp(match.group(1), format_type)
            end = shift_timestamp(match.group(2), format_type)
            separator = " --> " if format_type == "srt" else " --> "
            return f"{start}{separator}{end}"

        return re.sub(
            r"(\d{2}:\d{2}:\d{2}[,\.]\d{3}) --> (\d{2}:\d{2}:\d{2}[,\.]\d{3})",
            replacer,
            line,
        )

    def shift_time_sbv(line):
        def replacer(match):
            start = shift_timestamp(match.group(1), "sbv")
            end = shift_timestamp(match.group(2), "sbv")
            return f"{start},{end}"

        return re.sub(
            r"(\d+:\d{2}:\d{2}\.\d{3}),(\d+:\d{2}:\d{2}\.\d{3})", replacer, line
        )

    def shift_time_sub(line):
        def replacer(match):
            start = shift_timestamp(match.group(1), "sub")
            end = shift_timestamp(match.group(2), "sub")
            return f"{start},{end}"

        return re.sub(
            r"(\d{2}:\d{2}:\d{2}\.\d{2})\s*,\s*(\d{2}:\d{2}:\d{2}\.\d{2})",
            replacer,
            line,
        )

    def shift_time_stl(line):
        def replacer(match):
            start = shift_timestamp(match.group(1), "stl")
            end = shift_timestamp(match.group(2), "stl")
            suffix = match.group(3)  # Preserve the remaining text
            return f"{start} , {end}{suffix}"

        return re.sub(
            r"(\d{1,2}:\d{2}:\d{2}:\d{2})\s*,\s*(\d{1,2}:\d{2}:\d{2}:\d{2})(.*)",
            replacer,
            line,
        )

    def shift_time_dfxp(line):
        def replacer(match):
            start = shift_timestamp(match.group(1), "dfxp")
            end = shift_timestamp(match.group(2), "dfxp")
            return f'begin="{start}" end="{end}"'

        return re.sub(r'begin="([\d:,\.]+)"\s+end="([\d:,\.]+)"', replacer, line)

    def shift_time_ttml(line):
        # Replace the 'begin' attribute
        line = re.sub(
            r'\bbegin="([^"]+)"',
            lambda m: f'begin="{shift_timestamp(m.group(1), "ttml", m.group(1))}"',
            line,
        )
        # Replace the 'end' attribute
        line = re.sub(
            r'\bend="([^"]+)"',
            lambda m: f'end="{shift_timestamp(m.group(1), "ttml", m.group(1))}"',
            line,
        )
        return line

    def shift_time_ass_ssa(line):
        def replacer(match):
            start = shift_timestamp(match.group(1), "ass_ssa")
            end = shift_timestamp(match.group(2), "ass_ssa")
            return f"{start},{end}"

        return re.sub(
            r"(\d{1,2}:\d{2}:\d{2}\.\d{2}),(\d{1,2}:\d{2}:\d{2}\.\d{2})", replacer, line
        )

    # Helper to shift individual timestamps
    def shift_timestamp(timestamp, format_type, original_time_str=None):
        ms = time_to_milliseconds(timestamp, format_type)
        if ms is None:
            log_message(
                ERROR_CONVERT_TIMESTAMP.format(
                    timestamp=timestamp, format_type=format_type
                ),
                "error",
            )
            return timestamp
        ms += milliseconds
        ms = max(ms, 0)
        shifted_timestamp = milliseconds_to_time(ms, format_type, original_time_str)
        return shifted_timestamp

    # Time conversion functions to handle various formats accurately
    def time_to_milliseconds(time_str, format_type):
        try:
            if format_type in ["srt", "vtt"]:
                parts = re.split(r"[:,.]", time_str)
                h, m, s = map(int, parts[:3])
                ms = int(parts[3])
                return (h * 3600 + m * 60 + s) * 1000 + ms
            if format_type == "sbv":
                parts = re.split(r"[:.]", time_str)
                h, m, s, ms = map(int, parts)
                return (h * 3600 + m * 60 + s) * 1000 + ms
            if format_type == "sub":
                parts = re.split(r"[:.]", time_str)
                h, m, s, cs = map(int, parts)
                return (h * 3600 + m * 60 + s) * 1000 + (cs * 10)
            if format_type == "stl":
                parts = re.split(r"[:.]", time_str)
                h, m, s, f = map(int, parts)
                return (h * 3600 + m * 60 + s) * 1000 + (f * 40)  # Assuming 25 fps
            if format_type == "dfxp":
                parts = re.split(r"[:.,]", time_str)
                h, m, s = map(int, parts[:3])
                ms = int(parts[3].replace(",", "")) if len(parts) > 3 else 0
                return (h * 3600 + m * 60 + s) * 1000 + ms
            if format_type in ["itt", "ttml"]:
                if ":" in time_str:
                    # Handle 'HH:MM:SS.MS' and 'HH:MM:SS:FF' (SMPTE) formats
                    # Check for 'HH:MM:SS.MS' format
                    matches = re.match(r"^(\d+):(\d{2}):(\d{2})(?:\.(\d+))?$", time_str)
                    if matches:
                        h = int(matches.group(1))
                        m = int(matches.group(2))
                        s = int(matches.group(3))
                        ms_str = matches.group(4) or "0"
                        ms = int(ms_str.ljust(3, "0")[:3])
                        return (h * 3600 + m * 60 + s) * 1000 + ms
                    # Check for 'HH:MM:SS:FF' (SMPTE) format
                    matches = re.match(r"^(\d+):(\d{2}):(\d{2}):(\d+)$", time_str)
                    if matches:
                        h = int(matches.group(1))
                        m = int(matches.group(2))
                        s = int(matches.group(3))
                        frames = int(matches.group(4))
                        # Assuming 25 fps
                        ms = int(frames * (1000 / 25))
                        return (h * 3600 + m * 60 + s) * 1000 + ms
                    log_message(
                        ERROR_PARSING_TIME_STRING.format(time_str=time_str),
                        "error",
                        tab="manual",
                    )
                    return None
                # Handle 'SSSSSS.MS' seconds format
                seconds_match = re.match(r"^(\d+(?:\.\d+)?)(?:s)?$", time_str)
                if seconds_match:
                    total_seconds = float(seconds_match.group(1))
                    return int(total_seconds * 1000)
                log_message(
                    ERROR_PARSING_TIME_STRING.format(time_str=time_str),
                    "error",
                    tab="manual",
                )
                return None
            if format_type == "ass_ssa":
                parts = re.split(r"[:.]", time_str)
                h, m, s, cs = map(int, parts)
                return (h * 3600 + m * 60 + s) * 1000 + (cs * 10)
            return None
        except (ValueError, IndexError) as e:
            log_message(
                ERROR_PARSING_TIME_STRING_DETAILED.format(
                    time_str=time_str, format_type=format_type, error_message=str(e)
                ),
                "error",
                tab="manual",
            )
            return None

    def milliseconds_to_time(ms, format_type, original_time_str=None):
        h = ms // 3600000
        m = (ms // 60000) % 60
        s = (ms // 1000) % 60
        ms_remainder = ms % 1000
        if format_type == "srt":
            return f"{h:02}:{m:02}:{s:02},{ms_remainder:03}"
        if format_type == "vtt":
            return f"{h:02}:{m:02}:{s:02}.{ms_remainder:03}"
        if format_type == "sbv":
            return f"{h}:{m:02}:{s:02}.{ms_remainder:03}"
        if format_type == "sub":
            cs = ms_remainder // 10
            return f"{h:02}:{m:02}:{s:02}.{cs:02}"
        if format_type == "stl":
            f = ms_remainder // 40  # Assuming 25 fps
            return f"{h:02}:{m:02}:{s:02}:{f:02}"
        if format_type == "dfxp":
            return f"{h:02}:{m:02}:{s:02},{ms_remainder:03}"
        if format_type in ["ttml", "itt"]:
            if original_time_str:
                if ":" in original_time_str:
                    if "." in original_time_str:
                        # Original format is 'HH:MM:SS.MS' with flexible milliseconds
                        timestamp = f"{h:02}:{m:02}:{s:02}.{ms_remainder:03}"
                        return timestamp
                    if ":" in original_time_str:
                        # Original format is 'HH:MM:SS:FF' (SMPTE)
                        frame_rate = 25  # Assuming 25 fps
                        frames = int(round(ms_remainder / 1000 * frame_rate))
                        return f"{h:02}:{m:02}:{s:02}:{frames:02}"
                    # Original format is 'HH:MM:SS' without milliseconds
                    return f"{h:02}:{m:02}:{s:02}"
                # Original format is seconds 'SSSSSs'
                total_seconds = ms / 1000
                timestamp = f"{total_seconds:.3f}".rstrip("0").rstrip(".") + "s"
                return timestamp
            # Default TTML format
            return f"{h:02}:{m:02}:{s:02}.{ms_remainder:03}"
        if format_type == "ass_ssa":
            cs = ms_remainder // 10
            return f"{h}:{m:02}:{s:02}.{cs:02}"
        return None

    # Process each line based on format type
    for line in lines:
        if file_extension == ".srt":
            new_lines.append(shift_time_srt_vtt(line, "srt") if "-->" in line else line)
        elif file_extension == ".vtt":
            new_lines.append(shift_time_srt_vtt(line, "vtt") if "-->" in line else line)
        elif file_extension == ".sbv":
            new_lines.append(shift_time_sbv(line) if "," in line else line)
        elif file_extension == ".sub":
            new_lines.append(shift_time_sub(line) if "," in line else line)
        elif file_extension == ".stl":
            new_lines.append(shift_time_stl(line) if "," in line else line)
        elif file_extension == ".dfxp":
            new_lines.append(shift_time_dfxp(line))
        elif file_extension in [".ttml", ".itt"]:
            new_lines.append(shift_time_ttml(line))
        elif file_extension in [".ass", ".ssa"]:
            new_lines.append(shift_time_ass_ssa(line))
        else:
            new_lines.append(line)
    # Define file save location and handle existing files
    if replace_original:
        new_subtitle_file = subtitle_file
        if subtitle_file in total_shifted_milliseconds:
            message_text = REPLACE_ORIGINAL_TEXT.format(
                milliseconds=milliseconds, total_shifted=total_shifted
            )
            response = messagebox.askyesno(REPLACE_ORIGINAL_TITLE, message_text)
            if not response:
                return
    elif save_to_desktop:
        desktop_path = get_desktop_path()
        new_subtitle_file = os.path.join(desktop_path, f"{total_shifted}ms_{filename}")
    else:
        new_subtitle_file = os.path.join(
            os.path.dirname(subtitle_file), f"{total_shifted}ms_{filename}"
        )
    if os.path.exists(new_subtitle_file) and not replace_original:
        file_exists_text = FILE_EXISTS_TEXT.format(
            filename=os.path.basename(new_subtitle_file)
        )
        replace = messagebox.askyesno(FILE_EXISTS_TITLE, file_exists_text)
        if not replace:
            return

    def update_progress(progress_bar, value):
        progress_bar["value"] = value
        if value < 100:
            root.after(10, update_progress, progress_bar, value + 3)
        else:
            # Hide the progress bar after completions
            progress_bar.grid_forget()
            log_message(
                SUCCESS_LOG_TEXT.format(
                    milliseconds=milliseconds, new_subtitle_file=new_subtitle_file
                ),
                "success",
                new_subtitle_file,
                tab="manual",
            )

    try:
        # Write to file after progress bar is fully loaded
        with open(new_subtitle_file, "wb") as file:
            file.write("\n".join(new_lines).encode(encoding))
        # Hide current log message
        label_message_manual.grid_forget()
        # Create a progress bar
        progress_bar = ttk.Progressbar(
            root, orient="horizontal", length=200, mode="determinate"
        )
        progress_bar.grid(
            row=5, column=0, columnspan=5, padx=10, pady=(0, 10), sticky="ew"
        )
        update_progress(progress_bar, 0)
        if replace_original:
            total_shifted_milliseconds[subtitle_file] = total_shifted
    except Exception as e:
        log_message(
            ERROR_SAVING_SUBTITLE.format(error_message=str(e)), "error", tab="manual"
        )


# Shift Subtitle End


def sync_subtitle():
    if hasattr(label_drop_box, "tooltip_text"):
        subtitle_file = label_drop_box.tooltip_text
        if subtitle_file:
            try:
                milliseconds = int(entry_milliseconds.get())
                if milliseconds == 0:
                    log_message(NON_ZERO_MILLISECONDS, "error", tab="manual")
                    return
                save_to_desktop = (
                    save_to_desktop_var.get()
                )  # Get the value of the save_to_desktop switch
                replace_original = (
                    replace_original_var.get()
                )  # Get the value of the replace_original switch
                if save_to_desktop and replace_original:
                    log_message(SELECT_ONLY_ONE_OPTION, "error")
                    return
                # Shift subtitle in a separate thread to keep the GUI responsive
                threading.Thread(
                    target=shift_subtitle,
                    args=(
                        subtitle_file,
                        milliseconds,
                        save_to_desktop,
                        replace_original,
                    ),
                ).start()
            except ValueError:
                log_message(VALID_NUMBER_MILLISECONDS, "error", tab="manual")
    else:
        log_message(SELECT_SUBTITLE, "error", tab="manual")


def on_enter(event):
    event.widget.config(bg=COLOR_THREE)


def on_leave(event):
    if hasattr(event.widget, "tooltip_text"):
        event.widget.config(bg=COLOR_TWO)
    else:
        event.widget.config(bg=COLOR_ONE)


current_log_type = None


def log_message(message, msg_type=None, filepath=None, tab="both"):
    global current_log_type
    font_style = ("Arial", FONT_SIZE, "bold")
    if msg_type == "error":
        current_log_type = "error"
        color = COLOR_EIGHT
        bg_color = COLOR_SIX
    elif msg_type == "success":
        current_log_type = "success"
        color = COLOR_NINE
        bg_color = COLOR_TWO
    elif msg_type == "info":
        current_log_type = "info"
        color = COLOR_BW
        bg_color = COLOR_FOUR
    else:
        current_log_type = None
        color = COLOR_BW
        bg_color = COLOR_ONE
    if tab in ["both", "auto"]:
        label_message_auto.config(text=message, fg=color, bg=bg_color, font=font_style)
        if message:
            label_message_auto.grid(
                row=10, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew"
            )
        else:
            label_message_auto.grid_forget()
    if tab in ["both", "manual"]:
        label_message_manual.config(
            text=message, fg=color, bg=bg_color, font=font_style
        )
        if message:
            label_message_manual.grid(
                row=5, column=0, columnspan=5, padx=10, pady=(0, 10), sticky="ew"
            )
        else:
            label_message_manual.grid_forget()
    if msg_type == "success" and filepath:
        label_message_auto.config(cursor="hand2")
        label_message_manual.config(cursor="hand2")
        label_message_auto.bind(
            "<Button-1>", lambda event: open_directory(filepath, tab)
        )
        label_message_manual.bind(
            "<Button-1>", lambda event: open_directory(filepath, tab)
        )
    else:
        label_message_auto.config(cursor="")
        label_message_manual.config(cursor="")
        label_message_auto.unbind("<Button-1>")
        label_message_manual.unbind("<Button-1>")
    label_message_auto.update_idletasks()
    label_message_manual.update_idletasks()


def open_directory(filepath, tab="both"):
    if not os.path.exists(filepath):
        if tab != "ref":
            log_message(FILE_NOT_FOUND, "error", tab=tab)
            return None
        return FILE_NOT_FOUND, "error"
    filepath = os.path.normpath(os.path.realpath(filepath))
    try:
        if platform == "Windows":
            subprocess.run(["explorer", "/select,", filepath], check=False)
        elif platform == "Darwin":  # macOS
            subprocess.call(["open", "-R", filepath])
        else:  # Linux
            directory = os.path.dirname(filepath)
            file_managers = [
                "dolphin",
                "xdg-open",
                "gnome-open",
                "kde-open",
                "nautilus",
                "thunar",
                "pcmanfm",
            ]
            success = False
            for fm in file_managers:
                if shutil.which(fm):
                    try:
                        subprocess.call([fm, directory])
                        success = True
                        break  # Exit loop if successful
                    except Exception:
                        continue  # Try the next file manager

            if not success:
                # This will now be reached if no file manager succeeds
                messagebox.showinfo(
                    "Info", NOT_FIND_COMPATIBLE_FILE_MANAGER.format(directory=directory)
                )
                return None
    except Exception as e:
        if tab != "ref":
            log_message(
                ERROR_OPENING_DIRECTORY.format(variable=str(e)), "error", tab=tab
            )
            return None
        return FILE_NOT_FOUND, "error"


def update_wraplengt(event=None):
    event.widget.config(wraplength=event.widget.winfo_width() - 40)


def checkbox_selected(var):
    if var.get():
        if var == save_to_desktop_var:
            replace_original_var.set(False)
        elif var == replace_original_var:
            save_to_desktop_var.set(False)


def place_window_top_right(event=None, margin=50):
    root.update_idletasks()  # Ensure the window dimensions are updated
    width = root.winfo_width()
    height = root.winfo_height()
    screen_width = root.winfo_screenwidth()
    x = screen_width - width - margin  # Apply margin on the right side
    y = margin  # Margin on the top, converted to integer
    root.geometry(f"{width}x{height}+{x}+{y}")


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
        self.widget.bind("<Button-1>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip is None:
            # Get the position of the widget
            x_pos = self.widget.winfo_rootx()
            y_pos = (
                self.widget.winfo_rooty() + self.widget.winfo_height()
            )  # Adjust tooltip position below the widget
            # Calculate the screen dimensions
            screen_width = self.widget.winfo_screenwidth()
            screen_height = self.widget.winfo_screenheight()
            # Create a temporary label to calculate the width based on content
            temp_label = tk.Label(text=self.text)
            # removed font=("tahoma", "8", "normal") from label
            temp_label.update_idletasks()
            content_width = (
                temp_label.winfo_reqwidth()
            )  # Get the required width of the content
            # Set the tooltip width based on content width, limited to a maximum of 200
            tooltip_width = min(content_width, 200)
            # Calculate wraplength dynamically
            wraplength = min(content_width, 200)
            # Create the tooltip at the calculated position
            self.tooltip = tk.Toplevel(self.widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.attributes("-topmost", True)  # Make the tooltip window topmost
            # Adjust tooltip position to stay within the screen bounds
            if x_pos + tooltip_width > screen_width:
                x_pos = screen_width - tooltip_width
            if y_pos + self.widget.winfo_height() > screen_height:
                y_pos = screen_height - self.widget.winfo_height() - 3
            # Adjust tooltip position to avoid covering the button
            y_pos = max(y_pos, 0)
            # Adjust tooltip position if too far to the left
            x_pos = max(x_pos, 0)
            self.tooltip.wm_geometry("+%d+%d" % (x_pos, y_pos))
            label = tk.Label(
                self.tooltip,
                text=self.text,
                justify=tk.LEFT,
                wraplength=wraplength,
                background="#ffffe0",
                foreground="black",
                relief=tk.SOLID,
                borderwidth=1,
            )
            # removed font=("tahoma", "8", "normal") from label
            label.pack(ipadx=1)

    def hide_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


def on_manual_tab_selected(event=None):
    # Set focus to label_drop_box to prevent autofocus on entry_milliseconds
    label_drop_box.focus_set()
    # Insert default value "0" into entry_milliseconds if it's empty
    if not entry_milliseconds.get():
        entry_milliseconds.insert(0, "0")


def dark_title_bar(window):
    if platform == "Windows" and THEME == "dark":
        try:
            window.update()
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
            get_parent = ctypes.windll.user32.GetParent
            hwnd = get_parent(window.winfo_id())
            rendering_policy = DWMWA_USE_IMMERSIVE_DARK_MODE
            value = 2
            value = ctypes.c_int(value)
            set_window_attribute(
                hwnd, rendering_policy, ctypes.byref(value), ctypes.sizeof(value)
            )
        except Exception:
            pass
    elif platform == "Linux":
        # No direct equivalent for Linux, but you could set window properties
        try:
            window.attributes("-type", "normal")
            if THEME == "dark":
                window.attributes("-alpha", 0.95)  # Slightly transparent for dark theme
        except Exception:
            pass


root = TkinterDnD.Tk()
root.title(PROGRAM_NAME + " v" + VERSION)
root.configure(background=COLOR_BACKGROUND)  # Set window background color
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)  # Allow label_drop_box to fill empty space
root.withdraw()  # Hide the window while it's being built

# Create tabs
tab_control = ttk.Notebook(root)
automatic_tab = ttk.Frame(tab_control)
manual_tab = ttk.Frame(tab_control)
manual_tab.bind("<Visibility>", on_manual_tab_selected)
# Configure grid for automatic_tab
automatic_tab.columnconfigure(0, weight=1)
automatic_tab.rowconfigure(0, weight=1)
# Configure grid for manual_tab
manual_tab.columnconfigure(0, weight=1)
manual_tab.rowconfigure(0, weight=1)
# Add tabs to tab_control
tab_control.add(automatic_tab, text=TAB_AUTOMATIC_SYNC)
tab_control.add(manual_tab, text=TAB_MANUAL_SYNC)
# Place tab_control
tab_control.grid(row=0, column=0, sticky="nsew")
# Create a frame for the labels
top_right_frame = ttk.Frame(root)
top_right_frame.grid(row=0, column=0, sticky="ne", padx=0, pady=0)
# Add "GitHub" label on the right side of the tabs
github_label = ttk.Label(
    top_right_frame,
    text="GitHub",
    cursor="hand2",
    background=COLOR_BACKGROUND,
    foreground=COLOR_SEVEN,
    underline=True,
)
# Add at top of file with other imports:
github_label.bind("<Button-1>", lambda event: webbrowser.open(GITHUB_URL))
github_label.grid(row=0, column=0, sticky="ne", padx=0, pady=(10, 0))


# Settings
def change_log_window_font():
    initial_config = {
        "log_window_font": config["log_window_font"],
        "log_window_font_size": config["log_window_font_size"],
        "log_window_font_style": config["log_window_font_style"],
    }

    def validate_size_entry(input):
        if input.isdigit():
            return True
        if input == "":
            return True
        return False

    def apply_changes(preview=False):
        selected_font_index = font_listbox.curselection()
        if selected_font_index:
            selected_font = font_listbox.get(selected_font_index[0])
            selected_size = custom_size_var.get()
            try:
                selected_font_size = int(selected_size)
            except ValueError:
                selected_font_size = 7
            font_styles = []
            if bold_var.get():
                font_styles.append("bold")
            if italic_var.get():
                font_styles.append("italic")
            if underline_var.get():
                font_styles.append("underline")
            if strikethrough_var.get():
                font_styles.append("overstrike")
            font_style = " ".join(font_styles)
            selected_font_style = "normal" if not font_style else font_style
            if "log_window" in globals():
                log_window.config(
                    font=(selected_font, selected_font_size, selected_font_style)
                )
            if not preview:
                with open(config_path, "w", encoding="utf-8") as f:
                    config["log_window_font"] = selected_font
                    config["log_window_font_size"] = selected_font_size
                    config["log_window_font_style"] = selected_font_style
                    json.dump(config, f, indent=4)

    def update_label(*args):
        apply_changes(preview=True)

    def update_font_size_entry(event):
        selection = font_size_listbox.curselection()
        if selection:
            custom_size_var.set(sizes[selection[0]])

    def cancel_changes():
        config.update(initial_config)
        if "log_window" in globals():
            log_window.config(
                font=(
                    config["log_window_font"],
                    config["log_window_font_size"],
                    config["log_window_font_style"],
                )
            )
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        font_dialog.destroy()

    def close_window():
        apply_changes()
        font_dialog.destroy()

    def move_selection(event):
        if font_listbox == root.focus_get():
            current_selection = font_listbox.curselection()
            if current_selection:
                if event.keysym == "Up":
                    font_listbox.select_clear(0, tk.END)
                    current_index = max(current_selection[0] - 1, 0)
                    font_listbox.selection_set(current_index)
                    font_listbox.see(current_index)
                elif event.keysym == "Down":
                    font_listbox.select_clear(0, tk.END)
                    current_index = min(current_selection[0] + 1, len(fonts) - 1)
                    font_listbox.selection_set(current_index)
                    font_listbox.see(current_index)
                update_label()
        elif font_size_listbox == root.focus_get():
            current_selection = font_size_listbox.curselection()
            if current_selection:
                if event.keysym == "Up":
                    font_size_listbox.select_clear(0, tk.END)
                    current_index = max(current_selection[0] - 1, 0)
                    font_size_listbox.selection_set(current_index)
                    font_size_listbox.see(current_index)
                elif event.keysym == "Down":
                    font_size_listbox.select_clear(0, tk.END)
                    current_index = min(current_selection[0] + 1, len(sizes) - 1)
                    font_size_listbox.selection_set(current_index)
                    font_size_listbox.see(current_index)
                update_font_size_entry(
                    event
                )  # Update font size entry after moving selection
        else:
            current_selection = None

    font_dialog = tk.Toplevel(root)
    dark_title_bar(font_dialog)
    font_dialog.configure(background=COLOR_BACKGROUND)
    font_dialog.title(DIALOG_TITLE_TEXT)
    font_dialog.geometry("500x400")  # Increased width for font styles
    font_dialog.minsize(500, 400)  # Minimum width and height
    # Center the window on screen
    screen_width = font_dialog.winfo_screenwidth()
    screen_height = font_dialog.winfo_screenheight()
    x = (screen_width - 500) // 2
    y = (screen_height - 400) // 2
    font_dialog.geometry(f"+{x}+{y}")
    font_dialog.protocol("WM_DELETE_WINDOW", cancel_changes)
    current_font = config["log_window_font"]
    current_size = str(config["log_window_font_size"])
    current_style = config["log_window_font_style"]
    font_label = tk.Label(
        font_dialog,
        text=FONT_FAMILY_LABEL_TEXT,
        background=COLOR_BACKGROUND,
        foreground=COLOR_BW,
    )
    font_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
    fonts = sorted(set(tkFont.families()))  # Remove duplicates and sort the fonts
    font_listbox = tk.Listbox(
        font_dialog,
        selectmode=tk.SINGLE,
        exportselection=0,
        borderwidth=2,
        background=COLOR_WB,
        fg=COLOR_BW,
    )
    for font in fonts:
        font_listbox.insert(tk.END, font)
    font_listbox.grid(
        row=1, column=0, padx=(10, 2.5), pady=(0, 5), sticky="nsew", rowspan=2
    )
    font_listbox_scrollbar = ttk.Scrollbar(
        font_listbox,
        orient="vertical",
        command=font_listbox.yview,
        style="Vertical.TScrollbar",
    )
    font_listbox.config(yscrollcommand=font_listbox_scrollbar.set)
    font_listbox_scrollbar.pack(side="right", fill="y")
    font_listbox.bind("<<ListboxSelect>>", update_label)
    font_listbox.bind("<Up>", move_selection)
    font_listbox.bind("<Down>", move_selection)
    try:
        font_index = fonts.index(current_font)
        font_listbox.selection_set(font_index)
        font_listbox.see(font_index - 8)
    except ValueError:
        pass
    font_size_label = tk.Label(
        font_dialog,
        text=FONT_SIZE_LABEL_TEXT,
        background=COLOR_BACKGROUND,
        foreground=COLOR_BW,
    )
    font_size_label.grid(row=0, column=1, padx=(2.5, 10), pady=5, sticky="w")
    custom_size_var = tk.StringVar(value=current_size)
    custom_size_entry = tk.Entry(
        font_dialog,
        cursor="xterm",
        textvariable=custom_size_var,
        justify="center",
        borderwidth=2,
        bg=COLOR_WB,
        fg=COLOR_BW,
        insertbackground=COLOR_BW,
    )
    custom_size_entry.grid(row=1, column=1, padx=(2.5, 10), pady=(0, 5), sticky="ew")
    custom_size_entry.config(
        validate="key",
        validatecommand=(custom_size_entry.register(validate_size_entry), "%P"),
    )
    sizes = [str(size) for size in range(3, 43)]
    font_size_listbox = tk.Listbox(
        font_dialog,
        selectmode=tk.SINGLE,
        exportselection=0,
        borderwidth=2,
        background=COLOR_WB,
        fg=COLOR_BW,
    )
    for size in sizes:
        font_size_listbox.insert(tk.END, size)
    font_size_listbox.grid(row=2, column=1, padx=(2.5, 10), pady=(0, 5), sticky="nsew")
    font_size_listbox_scrollbar = ttk.Scrollbar(
        font_size_listbox,
        orient="vertical",
        command=font_size_listbox.yview,
        style="Vertical.TScrollbar",
    )
    font_size_listbox.config(yscrollcommand=font_size_listbox_scrollbar.set)
    font_size_listbox_scrollbar.pack(side="right", fill="y")
    font_size_listbox.bind("<<ListboxSelect>>", update_label)
    font_size_listbox.bind("<ButtonRelease-1>", update_font_size_entry)
    custom_size_var.trace_add("write", update_label)
    font_size_listbox.bind("<Up>", move_selection)
    font_size_listbox.bind("<Down>", move_selection)
    font_style_frame = tk.Frame(font_dialog, background=COLOR_BACKGROUND)
    font_style_frame.grid(row=3, column=0, pady=(0, 5), columnspan=2, sticky="nw")
    font_style_label = tk.Label(
        font_style_frame,
        text=FONT_STYLE_LABEL_TEXT,
        background=COLOR_BACKGROUND,
        foreground=COLOR_BW,
    )
    font_style_label.grid(
        row=0, column=0, padx=10, pady=(0, 5), sticky="w", columnspan=4
    )
    # Font Style Checkboxes
    bold_var = tk.BooleanVar()
    bold_checkbox = tk.Checkbutton(
        font_style_frame,
        text=BOLD_TEXT,
        background=COLOR_BACKGROUND,
        foreground=COLOR_BW,
        variable=bold_var,
        command=update_label,
        selectcolor=COLOR_WB,  # Change the checkbox square background
        activebackground=COLOR_BACKGROUND,
        activeforeground=COLOR_BW,
        highlightthickness=0,
        takefocus=0,
        state="normal",
    )
    italic_var = tk.BooleanVar()
    italic_checkbox = tk.Checkbutton(
        font_style_frame,
        text=ITALIC_TEXT,
        background=COLOR_BACKGROUND,
        foreground=COLOR_BW,
        variable=italic_var,
        command=update_label,
        selectcolor=COLOR_WB,  # Change the checkbox square background
        activebackground=COLOR_BACKGROUND,
        activeforeground=COLOR_BW,
        highlightthickness=0,
        takefocus=0,
        state="normal",
    )
    underline_var = tk.BooleanVar()
    underline_checkbox = tk.Checkbutton(
        font_style_frame,
        text=UNDERLINE_TEXT,
        background=COLOR_BACKGROUND,
        foreground=COLOR_BW,
        variable=underline_var,
        command=update_label,
        selectcolor=COLOR_WB,  # Change the checkbox square background
        activebackground=COLOR_BACKGROUND,
        activeforeground=COLOR_BW,
        highlightthickness=0,
        takefocus=0,
        state="normal",
    )
    strikethrough_var = tk.BooleanVar()
    strikethrough_checkbox = tk.Checkbutton(
        font_style_frame,
        text=STRIKETHROUGH_TEXT,
        background=COLOR_BACKGROUND,
        foreground=COLOR_BW,
        variable=strikethrough_var,
        command=update_label,
        selectcolor=COLOR_WB,  # Change the checkbox square background
        activebackground=COLOR_BACKGROUND,
        activeforeground=COLOR_BW,
        highlightthickness=0,
        takefocus=0,
        state="normal",
    )
    font_information_label = tk.Label(
        font_style_frame,
        text=FONT_INFORMATION_TEXT,
        bg=COLOR_BACKGROUND,
        fg=COLOR_BW,
    )
    bold_checkbox.grid(row=1, column=0, padx=(10, 5), pady=(0, 5), sticky="w")
    italic_checkbox.grid(row=1, column=1, padx=5, pady=(0, 5), sticky="w")
    underline_checkbox.grid(row=1, column=2, padx=5, pady=(0, 5), sticky="w")
    strikethrough_checkbox.grid(row=1, column=3, padx=5, pady=(0, 5), sticky="w")
    font_information_label.grid(
        row=2, column=0, columnspan=5, padx=10, pady=(0, 5), sticky="ew"
    )
    # Apply and Cancel Buttons
    button_frame = tk.Frame(font_dialog, background=COLOR_BACKGROUND)
    button_frame.grid(row=5, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")
    button_frame.grid_columnconfigure(1, weight=1)  # Add space between buttons
    # Apply button on right
    apply_button = TkButton(
        button_frame,
        text=APPLY_TEXT,
        command=close_window,
        padx=10,
        pady=10,
        fg=COLOR_WB,
        bg=BUTTON_COLOR_AUTO,
        activebackground=BUTTON_COLOR_AUTO_ACTIVE,
        activeforeground=COLOR_WB,
        relief=tk.RAISED,
        borderwidth=2,
        cursor="hand2",
        highlightthickness=0,
        takefocus=0,
        state="normal",
    )
    apply_button.grid(row=0, column=1, sticky="ew", padx=(2.5, 0), columnspan=2)
    # Cancel button on left
    cancel_button = TkButton(
        button_frame,
        text=CANCEL_TEXT,
        command=cancel_changes,
        padx=50,
        pady=10,
        fg=COLOR_WB,
        bg=DEFAULT_BUTTON_COLOR,
        activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
        activeforeground=COLOR_WB,
        relief=tk.RAISED,
        borderwidth=2,
        cursor="hand2",
        highlightthickness=0,
        takefocus=0,
        state="normal",
    )
    cancel_button.grid(row=0, column=0, sticky="e", padx=(0, 2.5))
    font_dialog.grid_rowconfigure(2, weight=1)
    font_dialog.grid_columnconfigure(0, weight=3)
    font_dialog.grid_columnconfigure(1, weight=0)
    # Select currently applied font style
    if "bold" in current_style:
        bold_var.set(True)
    if "italic" in current_style:
        italic_var.set(True)
    if "underline" in current_style:
        underline_var.set(True)
    if "overstrike" in current_style:
        strikethrough_var.set(True)
    try:
        font_size_index = sizes.index(current_size)
        font_size_listbox.selection_set(font_size_index)
        font_size_listbox.see(font_size_index - 6)
    except ValueError:
        pass


def restart_program():
    python = sys.executable
    if getattr(sys, "frozen", False):
        # Running as an executable
        os.execl(python, python)
    else:
        # Running as a script
        script_path = os.path.abspath(__file__)
        os.execl(python, python, script_path)


def reset_to_default_settings():
    if messagebox.askyesno(WARNING, CONFIRM_RESET_MESSAGE):
        for key, value in default_settings.items():
            update_config(key, value)
        restart_program()


def toggle_keep_converted_subtitles():
    global keep_converted_subtitles
    if keep_converted_subtitles:
        response = messagebox.askyesno(WARNING, TOGGLE_KEEP_CONVERTED_SUBTITLES_WARNING)
        if not response:
            keep_converted_var.set(keep_converted_subtitles)
            return
    keep_converted_subtitles = not keep_converted_subtitles
    update_config("keep_converted_subtitles", keep_converted_subtitles)


def toggle_remember_the_changes():
    global remember_the_changes
    remember_the_changes = not remember_the_changes
    update_config("remember_the_changes", remember_the_changes)


def toggle_keep_extracted_subtitles():
    global keep_extracted_subtitles
    if keep_extracted_subtitles:
        response = messagebox.askyesno(WARNING, TOGGLE_KEEP_EXTRACTED_SUBTITLES_WARNING)
        if not response:
            keep_extracted_var.set(keep_extracted_subtitles)
            return
    keep_extracted_subtitles = not keep_extracted_subtitles
    update_config("keep_extracted_subtitles", keep_extracted_subtitles)


def toggle_backup_subtitles_before_overwriting():
    global backup_subtitles_before_overwriting
    if backup_subtitles_before_overwriting:
        response = messagebox.askyesno(
            WARNING, BACKUP_SUBTITLES_BEFORE_OVERWRITING_WARNING
        )
        if not response:
            backup_subtitles_var.set(backup_subtitles_before_overwriting)
            return
    backup_subtitles_before_overwriting = not backup_subtitles_before_overwriting
    update_config(
        "backup_subtitles_before_overwriting", backup_subtitles_before_overwriting
    )


def toggle_check_video_for_subtitle_stream_in_alass():
    global check_video_for_subtitle_stream_in_alass
    check_video_for_subtitle_stream_in_alass = (
        not check_video_for_subtitle_stream_in_alass
    )
    update_config(
        "check_video_for_subtitle_stream_in_alass",
        check_video_for_subtitle_stream_in_alass,
    )


def update_additional_ffsubsync_args():
    global additional_ffsubsync_args
    new_args = simpledialog.askstring(
        LABEL_ADDITIONAL_FFSUBSYNC_ARGS,
        PROMPT_ADDITIONAL_FFSUBSYNC_ARGS,
        initialvalue=additional_ffsubsync_args,
    )
    if new_args is not None:
        additional_ffsubsync_args = new_args
        update_config("additional_ffsubsync_args", additional_ffsubsync_args)


def update_additional_alass_args():
    global additional_alass_args
    new_args = simpledialog.askstring(
        LABEL_ADDITIONAL_ALASS_ARGS,
        PROMPT_ADDITIONAL_ALASS_ARGS,
        initialvalue=additional_alass_args,
    )
    if new_args is not None:
        additional_alass_args = new_args
        update_config("additional_alass_args", additional_alass_args)


def set_language(lang):
    global LANGUAGE
    LANGUAGE = lang
    update_config("language", LANGUAGE)
    restart_program()


def check_for_updates():
    def update_check():
        try:
            response = requests.get(GITHUB_VERSION_URL, timeout=10)
            latest_version = response.text.strip()

            def parse_version(v):
                return [int(x) for x in v.split(".")]

            if parse_version(latest_version) > parse_version(VERSION):
                if messagebox.askyesno(
                    texts.UPDATE_AVAILABLE_TITLE[LANGUAGE],
                    texts.UPDATE_AVAILABLE_TEXT[LANGUAGE].format(
                        latest_version=latest_version
                    ),
                ):
                    webbrowser.open(GITHUB_LATEST_RELEASE_URL)
        except Exception:
            pass

    update_thread = threading.Thread(target=update_check)
    update_thread.start()


def toggle_notify_about_updates():
    global notify_about_updates
    notify_about_updates = not notify_about_updates
    update_config("notify_about_updates", notify_about_updates)
    if notify_about_updates:
        check_for_updates()


def set_theme(theme):
    global THEME
    THEME = theme
    update_config("theme", THEME)
    restart_program()


def open_logs_folder():
    logs_folder = os.path.join(base_dir, f"{PROGRAM_NAME}_logs")
    # Ensure logs directory exists
    os.makedirs(logs_folder, exist_ok=True)

    if platform == "Windows":
        os.startfile(logs_folder)
    elif platform == "Darwin":  # macOS
        subprocess.call(["open", logs_folder])
    else:  # Linux
        file_managers = [
            "dolphin",
            "xdg-open",
            "gnome-open",
            "kde-open",
            "nautilus",
            "thunar",
            "pcmanfm",
        ]
        success = False
        for fm in file_managers:
            if shutil.which(fm):
                try:
                    subprocess.call([fm, logs_folder])
                    success = True
                    break  # Exit loop if successful
                except Exception:
                    continue  # Try the next file manager

        if not success:
            # This will now be reached if no file manager succeeds
            messagebox.showinfo(
                "Info", NOT_FIND_COMPATIBLE_FILE_MANAGER.format(directory=logs_folder)
            )


def check_logs_exist():
    try:
        logs_folder = os.path.join(base_dir, f"{PROGRAM_NAME}_logs")
        txt_files = [
            f
            for f in os.listdir(logs_folder)
            if os.path.isfile(os.path.join(logs_folder, f)) and f.endswith(".txt")
        ]
        return len(txt_files)
    except Exception:
        return 0


def clear_all_logs():
    logs_folder = os.path.join(base_dir, f"{PROGRAM_NAME}_logs")
    if os.path.exists(logs_folder):
        num_txt_files = check_logs_exist()
        if num_txt_files == 0:
            return
        if messagebox.askyesno(
            WARNING, LOG_FILES_DELETE_WARNING.format(count=num_txt_files)
        ):
            txt_files = [
                entry.path
                for entry in os.scandir(logs_folder)
                if entry.is_file() and entry.name.endswith(".txt")
            ]
            for file_path in txt_files:
                try:
                    os.remove(file_path)
                except Exception:
                    pass


def toggle_keep_logs():
    global keep_logs
    keep_logs = not keep_logs
    update_config("keep_logs", keep_logs)


def toggle_add_prefix():
    global add_prefix
    add_prefix = not add_prefix
    update_config("add_prefix", add_prefix)


def open_settings(event):
    global logs_exist, log_state
    logs_exist = check_logs_exist()
    log_state = "normal" if logs_exist > 0 else "disabled"
    settings_menu.entryconfig(LABEL_CLEAR_ALL_LOGS, state=log_state)
    settings_menu.post(event.x_root, event.y_root)


logs_exist = check_logs_exist()
log_state = "normal" if logs_exist > 0 else "disabled"
keep_logs = config.get("keep_logs", True)
notify_about_updates = config.get("notify_about_updates", True)
keep_converted_subtitles = config.get("keep_converted_subtitles", False)
keep_extracted_subtitles = config.get("keep_extracted_subtitles", False)
additional_ffsubsync_args = config.get("additional_ffsubsync_args", "")
additional_alass_args = config.get("additional_alass_args", "")
add_prefix = config.get("add_prefix", True)
backup_subtitles_before_overwriting = config.get(
    "backup_subtitles_before_overwriting", False
)
remember_the_changes = config.get("remember_the_changes", False)
check_video_for_subtitle_stream_in_alass = config.get(
    "check_video_for_subtitle_stream_in_alass", False
)
# Add "Settings" icon
settings_icon = PhotoImage(file="settings.png")
settings_label = ttk.Label(
    top_right_frame,
    image=settings_icon,
    cursor="hand2",
    background=COLOR_BACKGROUND,
    foreground=COLOR_BW,
)
# Create a dropdown menu for settings
settings_menu = Menu(top_right_frame, tearoff=0)
# Add language selection to the settings menu
language_var = tk.StringVar(value=LANGUAGE)
language_menu = Menu(settings_menu, tearoff=0)
for label, code in LANGUAGES.items():
    language_menu.add_radiobutton(
        label=label,
        variable=language_var,
        value=code,
        command=lambda c=code: set_language(c),
    )
settings_menu.add_cascade(label=LANGUAGE_LABEL_TEXT, menu=language_menu)
# Add theme selection to the settings menu
theme_var = tk.StringVar(value=config.get("theme", "system"))
theme_menu = Menu(settings_menu, tearoff=0)
themes = {
    "system": THEME_SYSTEM_TEXT,
    "dark": THEME_DARK_TEXT,
    "light": THEME_LIGHT_TEXT,
}
for key, display in themes.items():
    theme_menu.add_radiobutton(
        label=display, variable=theme_var, value=key, command=lambda t=key: set_theme(t)
    )
settings_menu.add_cascade(label=THEME_TEXT, menu=theme_menu)
settings_menu.add_command(label=DIALOG_TITLE_TEXT, command=change_log_window_font)
settings_menu.add_separator()
# Add other settings to the settings menu
keep_logs_var = tk.BooleanVar(value=keep_logs)
keep_converted_var = tk.BooleanVar(value=keep_converted_subtitles)
keep_extracted_var = tk.BooleanVar(value=keep_extracted_subtitles)
backup_subtitles_var = tk.BooleanVar(value=backup_subtitles_before_overwriting)
remember_the_changes_var = tk.BooleanVar(value=remember_the_changes)
add_prefix_var = tk.BooleanVar(value=add_prefix)
check_video_for_subtitle_stream_var = tk.BooleanVar(
    value=check_video_for_subtitle_stream_in_alass
)
notify_about_updates_var = tk.BooleanVar(value=notify_about_updates)
settings_menu.add_command(
    label=LABEL_ADDITIONAL_FFSUBSYNC_ARGS, command=update_additional_ffsubsync_args
)
settings_menu.add_command(
    label=LABEL_ADDITIONAL_ALASS_ARGS, command=update_additional_alass_args
)
settings_menu.add_separator()
settings_menu.add_checkbutton(
    label=LABEL_CHECK_VIDEO_FOR_SUBTITLE_STREAM,
    command=toggle_check_video_for_subtitle_stream_in_alass,
    variable=check_video_for_subtitle_stream_var,
)
settings_menu.add_checkbutton(
    label=LABEL_BACKUP_SUBTITLES,
    command=toggle_backup_subtitles_before_overwriting,
    variable=backup_subtitles_var,
)
settings_menu.add_checkbutton(
    label=LABEL_ADD_PREFIX,
    command=toggle_add_prefix,
    variable=add_prefix_var,
)
settings_menu.add_checkbutton(
    label=LABEL_KEEP_CONVERTED_SUBTITLES,
    command=toggle_keep_converted_subtitles,
    variable=keep_converted_var,
)
settings_menu.add_checkbutton(
    label=LABEL_KEEP_EXTRACTED_SUBTITLES,
    command=toggle_keep_extracted_subtitles,
    variable=keep_extracted_var,
)
settings_menu.add_separator()
# Add Logs options
settings_menu.add_checkbutton(
    label=LABEL_KEEP_LOG_RECORDS, command=toggle_keep_logs, variable=keep_logs_var
)
settings_menu.add_command(label=LABEL_OPEN_LOGS_FOLDER, command=open_logs_folder)
settings_menu.add_command(
    label=LABEL_CLEAR_ALL_LOGS, command=clear_all_logs, state=log_state
)
settings_menu.add_separator()
# Other options
settings_menu.add_checkbutton(
    label=NOTIFY_ABOUT_UPDATES_TEXT,
    command=toggle_notify_about_updates,
    variable=notify_about_updates_var,
)
settings_menu.add_checkbutton(
    label=LABEL_REMEMBER_THE_CHANGES,
    command=toggle_remember_the_changes,
    variable=remember_the_changes_var,
)
settings_menu.add_command(
    label=LABEL_RESET_TO_DEFAULT_SETTINGS, command=reset_to_default_settings
)
settings_label.bind("<Button-1>", open_settings)
settings_label.grid(row=0, column=1, sticky="ne", padx=(5, 10), pady=(10, 0))
# settings end

# Customizing the style of the tabs
style = ttk.Style()
# Set custom theme
style.theme_create(
    "custom",
    parent="alt",
    settings={
        "TNotebook": {
            "configure": {
                "tabposition": "nw",
                "tabmargins": [10, 5, 2, 0],
                "background": COLOR_BACKGROUND,
                "foreground": COLOR_BW,
                "borderwidth": 0,
            }
        },
        "TNotebook.Tab": {
            "configure": {
                "padding": [15, 5],
                "font": ("TkDefaultFont", FONT_SIZE_TWO, "normal"),
                "background": COLOR_PRIMARY,
                "foreground": COLOR_TAB_INACTVE,
                "borderwidth": 1,
            },
            "map": {
                "background": [("selected", COLOR_SECONDARY)],
                "foreground": [("selected", COLOR_BW)],
            },
        },
        "TFrame": {
            "configure": {"background": COLOR_BACKGROUND, "foreground": COLOR_BW}
        },
        "TProgressbar": {
            "configure": {
                "background": COLOR_PROGRESSBAR,
                "troughcolor": COLOR_ONE,
                "borderwidth": 1,
            }
        },
    },
)
style.theme_use("custom")
add_separator = ttk.Separator(automatic_tab, orient="horizontal")
add_separator.grid(row=0, column=0, sticky="new", padx=11, pady=0, columnspan=6)
add_separator = ttk.Separator(manual_tab, orient="horizontal")
add_separator.grid(row=0, column=0, sticky="new", padx=11, pady=0, columnspan=6)
style.map("TSeparator", background=[("", COLOR_BACKGROUND)])


# ---------------- Automatic Tab ---------------- #
# Extract subtitles from video (ALASS)
def extract_subtitles(video_file, subtitle_file, output_dir, log_window):
    if not os.path.exists(video_file):
        log_window.insert(
            tk.END, f"\n{VIDEO_FILE_NOT_FOUND.format(error=video_file)}\n"
        )
        return False
    ffprobe_cmd = [
        CALL_FFPROBE,
        "-v",
        "error",
        "-select_streams",
        "s",
        "-show_entries",
        "stream=index,codec_name:stream_tags=language,title",
        "-of",
        "csv=p=0",
        video_file,
    ]
    try:
        # Use create_process for ffprobe
        probe_process = create_process(ffprobe_cmd)
        output, _ = probe_process.communicate()

        if probe_process.returncode != 0:
            log_window.insert(tk.END, f"\n{FFPROBE_FAILED}\n")
            return False
        # Parse subtitle streams
        subtitle_streams = []
        for line in output.splitlines():
            if not line.strip():
                continue
            parts = line.split(",")
            if len(parts) >= 2:
                stream_index = parts[0].strip()
                codec_name = parts[1].strip()
                language = parts[2].strip() if len(parts) > 2 else ""
                subtitle_streams.append((stream_index, codec_name, language))
        # Filter compatible subtitles
        compatible_subtitles = [
            stream
            for stream in subtitle_streams
            if stream[1] in ALASS_EXTRACTABLE_SUBTITLE_EXTENSIONS
        ]
        if not compatible_subtitles:
            log_window.insert(tk.END, f"{NO_COMPATIBLE_SUBTITLES}\n")
            return False
        # Setup output directory
        output_folder = os.path.join(
            output_dir, "extracted_subtitles_" + os.path.basename(video_file)
        )
        os.makedirs(output_folder, exist_ok=True)
        log_window.insert(
            tk.END,
            f"{FOUND_COMPATIBLE_SUBTITLES.format(count=len(compatible_subtitles), output_folder=output_folder)}\n",
        )
        # Prepare FFmpeg command
        ffmpeg_base_cmd = [CALL_FFMPEG, "-y", "-i", video_file]
        output_files = []
        # Add subtitle mappings
        for i, (stream, codec, language) in enumerate(compatible_subtitles):
            ext = ALASS_EXTRACTABLE_SUBTITLE_EXTENSIONS.get(codec)
            if not ext:
                continue
            lang_suffix = f"_{language}" if language else ""
            output_file = os.path.join(
                output_folder, f"subtitle_{i+1}{lang_suffix}.{ext}"
            )
            output_files.append(output_file)
            ffmpeg_base_cmd.extend(["-map", f"0:{stream}", "-c:s", codec, output_file])
        if not output_files:
            log_window.insert(tk.END, f"{NO_COMPATIBLE_SUBTITLES}\n")
            return False
        # Execute FFmpeg using create_process
        ffmpeg_process = create_process(ffmpeg_base_cmd)
        output, _ = ffmpeg_process.communicate()
        if ffmpeg_process.returncode == 0:
            for output_file in output_files:
                log_window.insert(
                    tk.END,
                    f"{SUCCESSFULLY_EXTRACTED.format(filename=os.path.basename(output_file))}\n",
                )
            log_window.insert(tk.END, f"{CHOOSING_BEST_SUBTITLE}\n")
            closest_subtitle, score = choose_best_subtitle(
                subtitle_file, extracted_subtitles_folder=output_folder
            )
            if closest_subtitle:
                log_window.insert(
                    tk.END,
                    f"{CHOSEN_SUBTITLE.format(filename=os.path.basename(closest_subtitle), score=score)}\n",
                )
                return closest_subtitle
            return True

        log_window.insert(
            tk.END, f"{FAILED_TO_EXTRACT_SUBTITLES.format(error=output)}\n"
        )
        return False
    except Exception as e:
        log_window.insert(
            tk.END, f"\n{SUBTITLE_EXTRACTION_FAILED.format(error=str(e))}\n"
        )
        return False


def parse_timestamps(subtitle_file):
    # If "ALASS_EXTRACTABLE_SUBTITLE_EXTENSIONS" gets updated, this function should be updated accordingly
    sub_encoding = detect_encoding(subtitle_file)
    try:
        results = []
        with open(subtitle_file, "r", encoding=sub_encoding) as file:
            lines = file.readlines()
            if subtitle_file.endswith(".srt") or subtitle_file.endswith(".vtt"):
                for line in lines:
                    if "-->" in line:
                        time_str = line.split("-->")[0].strip()
                        hours, minutes, seconds = map(
                            float, time_str.replace(",", ".").split(":")
                        )
                        total_seconds = hours * 3600 + minutes * 60 + seconds
                        results.append(total_seconds)
            elif subtitle_file.endswith(".ass"):
                for line in lines:
                    if line.startswith("Dialogue"):
                        time_str = line.split(",")[1].strip()
                        hours, minutes, seconds = map(float, time_str.split(":"))
                        total_seconds = hours * 3600 + minutes * 60 + seconds
                        results.append(total_seconds)
        return results
    except Exception:
        return None


def choose_best_subtitle(subtitle_file, extracted_subtitles_folder):
    reference_times = parse_timestamps(subtitle_file)
    if not reference_times:
        # If reference_times is None, find the longest subtitle file
        longest_subtitle = None
        longest_length = 0
        for file in os.listdir(extracted_subtitles_folder):
            candidate = os.path.join(extracted_subtitles_folder, file)
            candidate_times = parse_timestamps(candidate)
            if candidate_times and len(candidate_times) > longest_length:
                longest_length = len(candidate_times)
                longest_subtitle = candidate
        return longest_subtitle, USED_THE_LONGEST_SUBTITLE
    best_subtitle = None
    best_score = float("inf")
    for file in os.listdir(extracted_subtitles_folder):
        candidate = os.path.join(extracted_subtitles_folder, file)
        candidate_times = parse_timestamps(candidate)
        if not candidate_times:
            continue
        # Compare the count of timestamps
        diff_count = abs(len(reference_times) - len(candidate_times))
        if diff_count < best_score:
            best_score = diff_count
            best_subtitle = candidate
    return best_subtitle, best_score


# Convert subtitles to SRT Begin
def convert_sub_to_srt(input_file, output_file):
    encoding = detect_encoding(input_file)
    with open(input_file, "r", encoding=encoding, errors="replace") as sub, open(
        output_file, "w", encoding="utf-8"
    ) as srt:
        srt_counter = 1
        while True:
            line = sub.readline().strip()
            if not line:
                break
            match = re.match(r"\{(\d+)\}\{(\d+)\}(.*)", line)
            if match:
                start, end, text = match.groups()
                text_lines = text.split("|")
                formatted_start = format_sub_time(start)
                formatted_end = format_sub_time(end)
                srt.write(f"{srt_counter}\n")
                srt.write(f"{formatted_start} --> {formatted_end}\n")
                srt.write("\n".join(text_lines) + "\n\n")
                srt_counter += 1
            else:
                timestamps = line
                text_lines = []
                while True:
                    line = sub.readline().strip()
                    if not line:
                        break
                    text_lines.append(line.replace("[br]", "\n"))
                start, end = timestamps.split(",")
                formatted_start = format_sub_time(start)
                formatted_end = format_sub_time(end)
                srt.write(f"{srt_counter}\n")
                srt.write(f"{formatted_start} --> {formatted_end}\n")
                srt.write("\n".join(text_lines) + "\n\n")
                srt_counter += 1


def format_sub_time(time_str):
    if time_str.isdigit():
        ms = int(time_str) * 10
        s, ms = divmod(ms, 1000)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"
    parts = re.split(r"[:.]", time_str)
    h, m, s, ms = map(int, parts)
    ms = ms * 10  # Convert to milliseconds
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def convert_ass_to_srt(input_file, output_file):
    encoding = detect_encoding(input_file)
    with open(input_file, "r", encoding=encoding, errors="replace") as ass, open(
        output_file, "w", encoding="utf-8"
    ) as srt:
        srt_counter = 1
        buffer = ""
        collecting = False
        for line in ass:
            if line.startswith("Dialogue:"):
                collecting = True
                if buffer:
                    srt.write(f"{buffer}\n\n")
                    srt_counter += 1
                parts = line.split(",", 9)
                start = parts[1].strip()
                end = parts[2].strip()
                text = parts[9].replace("\\N", "\n").strip()
                # Replace ASS/SSA tags with SRT tags
                text = text.replace("{i}", "<i>").replace("{/i}", "</i>")
                text = text.replace("{u}", "<u>").replace("{/u}", "</u>")
                text = text.replace("{b}", "<b>").replace("{/b}", "</b>")
                buffer = f"{srt_counter}\n{format_ass_time(start)} --> {format_ass_time(end)}\n{text}"
            elif collecting:
                line = line.strip()
                # Replace ASS/SSA tags with SRT tags
                line = line.replace("{i}", "<i>").replace("{/i}", "</i>")
                line = line.replace("{u}", "<u>").replace("{/u}", "</u>")
                line = line.replace("{b}", "<b>").replace("{/b}", "</b>")
                buffer += f"\n{line}"
        if buffer:
            srt.write(f"{buffer}\n\n")


def format_ass_time(time_str):
    t = time_str.split(":")
    hours = int(t[0])
    minutes = int(t[1])
    seconds = float(t[2])
    return f"{hours:02}:{minutes:02}:{int(seconds):02},{int((seconds - int(seconds)) * 1000):03}"


def convert_ttml_or_dfxp_to_srt(input_file, output_file):
    try:
        with open(input_file, "rb") as file:
            data = file.read()
            encoding = detect_encoding(input_file)
            content = data.decode(encoding, errors="replace")
        root = ET.fromstring(content)
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return
    captions = [elem for elem in root.iter() if strip_namespace(elem.tag) == "p"]
    with open(output_file, "w", encoding="utf-8") as srt:
        for idx, caption in enumerate(captions, 1):
            begin = format_ttml_time(caption.attrib.get("begin"))
            end = format_ttml_time(caption.attrib.get("end"))

            def process_element(elem):
                text = ""
                tag = strip_namespace(elem.tag)
                end_tags = []
                # Handle start tags
                if tag == "br":
                    text += "\n"
                elif tag in ["b", "i", "u", "font"]:
                    text += f"<{tag}>"
                    end_tags.insert(0, f"</{tag}>")
                elif tag == "span":
                    style = elem.attrib.get("style", "")
                    styles = style.strip().lower().split()
                    for style_attr in styles:
                        if style_attr == "bold":
                            text += "<b>"
                            end_tags.insert(0, "</b>")
                        elif style_attr == "italic":
                            text += "<i>"
                            end_tags.insert(0, "</i>")
                        elif style_attr == "underline":
                            text += "<u>"
                            end_tags.insert(0, "</u>")
                    if "color" in elem.attrib:
                        color = elem.attrib["color"]
                        text += f'<font color="{color}">'
                        end_tags.insert(0, "</font>")
                # Add text content
                if elem.text:
                    text += elem.text
                # Recursively process child elements
                for child in elem:
                    text += process_element(child)
                # Handle end tags
                for end_tag in end_tags:
                    text += end_tag
                # Add tail text
                if elem.tail:
                    text += elem.tail
                return text

            # Process caption content
            text = process_element(caption)
            srt.write(f"{idx}\n")
            srt.write(f"{begin} --> {end}\n")
            srt.write(f"{text.strip()}\n\n")


def format_ttml_time(timestamp):
    # Remove 's' suffix if present
    timestamp = timestamp.replace("s", "")
    # Check for SMPTE format HH:MM:SS:FF
    if timestamp.count(":") == 3:
        try:
            hours, minutes, seconds, frames = map(int, timestamp.split(":"))
            frame_rate = 25  # Adjust frame rate as needed
            milliseconds = int((frames / frame_rate) * 1000)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
        except ValueError:
            return timestamp
    # Check if already in HH:MM:SS format
    elif ":" in timestamp:
        return timestamp.replace(".", ",")
    # Convert from seconds to HH:MM:SS,mmm
    else:
        try:
            seconds = float(timestamp)
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            seconds = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace(".", ",")
        except ValueError:
            return timestamp


def convert_vtt_to_srt(input_file, output_file):
    with open(input_file, "rb") as vtt_file:
        vtt_data = vtt_file.read()
        encoding = detect_encoding(input_file)
    with open(input_file, "r", encoding=encoding, errors="replace") as vtt, open(
        output_file, "w", encoding="utf-8"
    ) as srt:
        srt_counter = 1
        allowed_tags = ["b", "i", "u", "font"]
        tag_pattern = re.compile(r"</?(?!" + "|".join(allowed_tags) + r")\w+[^>]*>")
        for line in vtt:
            match = re.match(
                r"(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})", line
            )
            if match:
                start, end = match.groups()
                srt.write(f"{srt_counter}\n")
                srt.write(f"{start.replace('.', ',')} --> {end.replace('.', ',')}\n")
                srt_counter += 1
                text = ""
                while True:
                    try:
                        next_line = next(vtt).strip()
                    except StopIteration:
                        break
                    if not next_line:
                        break
                    cleaned_line = tag_pattern.sub("", next_line)
                    text += cleaned_line + "\n"
                srt.write(f"{text.strip()}\n\n")


def convert_sbv_to_srt(input_file, output_file):
    encoding = detect_encoding(input_file)
    with open(input_file, "r", encoding=encoding, errors="replace") as sbv, open(
        output_file, "w", encoding="utf-8"
    ) as srt:
        srt_counter = 1
        allowed_tags = ["b", "i", "u", "font"]
        tag_pattern = re.compile(r"</?(?!" + "|".join(allowed_tags) + r")\w+[^>]*>")
        timestamp_pattern = re.compile(r"\d+:\d+:\d+\.\d+,\d+:\d+:\d+\.\d+")
        while True:
            timestamps = sbv.readline()
            if not timestamps:
                break
            timestamps = timestamps.strip()
            if not timestamps or not timestamp_pattern.match(timestamps):
                continue
            text_lines = []
            while True:
                position = sbv.tell()
                line = sbv.readline()
                if not line:
                    break
                line = line.strip()
                if timestamp_pattern.match(line):
                    sbv.seek(position)
                    break
                cleaned_line = tag_pattern.sub("", line)
                text_lines.append(cleaned_line)
            if "," in timestamps:
                start, end = timestamps.split(",")
                srt.write(f"{srt_counter}\n")
                srt.write(f"{format_sbv_time(start)} --> {format_sbv_time(end)}\n")
                srt.write("\n".join(text_lines) + "\n")
                srt_counter += 1


def format_sbv_time(time_str):
    h, m, s = time_str.split(":")
    s = s.replace(".", ",")
    return f"{int(h):02}:{int(m):02}:{s}"


def convert_stl_to_srt(input_file, output_file):
    with open(input_file, "rb") as stl:
        stl_data = stl.read()
        encoding = detect_encoding(input_file)
        lines = stl_data.decode(encoding, errors="replace").splitlines()
    with open(output_file, "w", encoding="utf-8") as srt:
        srt_counter = 1
        for line in lines:
            parts = line.strip().split(",", 2)  # Split only on the first two commas
            if len(parts) >= 3:
                start = convert_stl_time(parts[0].strip())
                end = convert_stl_time(parts[1].strip())
                text = (
                    parts[2].strip().replace("| ", "\n").replace("|", "\n")
                )  # Replace '|' with newline
                if text:  # Ensure text is not empty
                    srt.write(f"{srt_counter}\n")
                    srt.write(f"{start} --> {end}\n")
                    srt.write(f"{text}\n\n")
                    srt_counter += 1


def convert_stl_time(time_str):
    h, m, s, f = map(int, time_str.split(":"))
    total_seconds = h * 3600 + m * 60 + s + f / 30
    ms = int((total_seconds - int(total_seconds)) * 1000)
    return f"{int(total_seconds)//3600:02}:{(int(total_seconds)%3600)//60:02}:{int(total_seconds)%60:02},{ms:03}"


def strip_namespace(tag):
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def convert_to_srt(subtitle_file, output_dir, log_window):
    file_extension = os.path.splitext(subtitle_file)[-1].lower()
    original_base_name = os.path.basename(
        os.path.splitext(subtitle_file)[0]
    )  # Store original base name
    srt_file = os.path.join(output_dir, "converted_" + original_base_name + ".srt")
    log_window.insert(
        tk.END,
        f"{PREPARING_SYNC.format(base_name=original_base_name, file_extension=file_extension)}\n",
    )
    converters = {
        ".ttml": convert_ttml_or_dfxp_to_srt,
        ".dfxp": convert_ttml_or_dfxp_to_srt,
        ".itt": convert_ttml_or_dfxp_to_srt,
        ".vtt": convert_vtt_to_srt,
        ".sbv": convert_sbv_to_srt,
        ".sub": convert_sub_to_srt,
        ".ass": convert_ass_to_srt,
        ".ssa": convert_ass_to_srt,
        ".stl": convert_stl_to_srt,
    }
    converter = converters.get(file_extension)
    if converter:
        try:
            log_window.insert(
                tk.END,
                f"{CONVERTING_SUBTITLE.format(file_extension=file_extension.upper())}\n",
            )
            converter(subtitle_file, srt_file)
        except Exception as e:
            log_window.insert(
                tk.END, f"{ERROR_CONVERTING_SUBTITLE.format(error_message=str(e))}\n"
            )
            return None
        log_window.insert(tk.END, f"{SUBTITLE_CONVERTED.format(srt_file=srt_file)}\n")
        return srt_file

    log_window.insert(
        tk.END,
        f"{ERROR_UNSUPPORTED_CONVERSION.format(file_extension=file_extension)}\n",
    )
    return None


# Convert subtitles to SRT End


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


def save_log_file(log_window, suffix=""):
    if keep_logs:
        # Save log window content to a log file
        log_content = log_window.get("1.0", tk.END)
        logs_folder = os.path.join(base_dir, f"{PROGRAM_NAME}_logs")
        os.makedirs(logs_folder, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_filename = os.path.join(logs_folder, f"{timestamp}{suffix}.txt")
        with open(log_filename, "w", encoding="utf-8") as log_file:
            log_file.write(log_content)


def create_process(cmd):
    kwargs = {
        "shell": True,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "universal_newlines": True,
        "encoding": default_encoding,
        "errors": "replace",
    }

    if platform == "Windows":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        kwargs.update(
            {"startupinfo": startupinfo, "creationflags": subprocess.CREATE_NO_WINDOW}
        )

    return subprocess.Popen(cmd, **kwargs)


def kill_process_tree(pid):
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        # First try to terminate children gracefully
        for child in children:
            try:
                child.terminate()
            except Exception:
                pass
        # Give them some time to terminate
        gone, still_alive = psutil.wait_procs(children, timeout=3)
        # Kill remaining children forcefully
        for child in still_alive:
            try:
                child.kill()
            except Exception:
                try:
                    os.kill(child.pid, signal.SIGKILL)  # Force kill as a fallback
                except Exception:
                    pass
        # Kill parent process
        try:
            parent.terminate()
            parent.wait(3)
        except Exception:
            try:
                parent.kill()
            except Exception:
                try:
                    os.kill(parent.pid, signal.SIGKILL)  # Force kill as a fallback
                except Exception:
                    pass
    except psutil.NoSuchProcess:
        pass


def get_desktop_path():
    if platform == "Windows":
        try:
            import winreg

            reg_key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
            )
            desktop = winreg.QueryValueEx(reg_key, "Desktop")[0]
            winreg.CloseKey(reg_key)
        except Exception:
            desktop = "None"
    else:
        from pathlib import Path

        desktop = Path.home() / "Desktop"
    if not os.path.exists(desktop):
        desktop = os.path.normpath(os.path.expanduser("~"))
    return desktop


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
    """Return the encoding from enc_list closest to unsupported_encoding."""
    return min(
        enc_list,
        key=lambda enc: levenshtein_distance(enc.lower(), unsupported_encoding.lower()),
    )


selected_destination_folder = None
subtitle_prefix = "autosync_"


def start_batch_sync():
    global process, output_subtitle_files, cancel_flag_batch, log_window
    sync_tool = sync_tool_var_auto.get()
    if sync_tool == SYNC_TOOL_ALASS:
        SUPPORTED_SUBTITLE_EXTENSIONS = ALASS_SUPPORTED_EXTENSIONS
    elif sync_tool == "ffsubsync":
        SUPPORTED_SUBTITLE_EXTENSIONS = FFSUBSYNC_SUPPORTED_EXTENSIONS
    process = None
    output_subtitle_files = []
    tree_items = treeview.get_children()
    if action_var_auto.get() == OPTION_SELECT_DESTINATION_FOLDER:
        if not os.path.exists(selected_destination_folder):
            log_message(TEXT_DESTINATION_FOLDER_DOES_NOT_EXIST, "error", tab="auto")
            return
    if not tree_items:
        log_message(NO_FILES_TO_SYNC, "error", tab="auto")
        return
    valid_pairs = 0
    for parent in tree_items:
        parent_values = treeview.item(parent, "values")
        if not parent_values:
            continue
        video_file = parent_values[0] if len(parent_values) > 0 else ""
        subtitles = treeview.get_children(parent)
        for sub in subtitles:
            values = treeview.item(sub, "values")
            if not values:
                continue
            subtitle_file = values[0] if len(values) > 0 else ""
            if video_file and subtitle_file:
                valid_pairs += 1
    if valid_pairs == 0:
        log_message(NO_VALID_FILE_PAIRS, "error", tab="auto")
        return

    total_items = valid_pairs
    completed_items = 0
    cancel_flag_batch = False

    def cancel_batch_sync():
        global cancel_flag_batch, process
        response = messagebox.askyesno(
            WARNING, BATCH_SYNC_CANCEL_CONFIRMATION, icon="warning"
        )
        if response:
            cancel_flag_batch = True
            if process:
                try:
                    kill_process_tree(process.pid)
                    process = None
                except Exception as e:
                    log_message(
                        ERROR_PROCESS_TERMINATION.format(error_message=str(e)),
                        "error",
                        tab="auto",
                    )
            log_message(BATCH_SYNC_CANCELLED, "error", tab="auto")
            root.update_idletasks()
            restore_window()

    def restore_window():
        batch_input.grid()
        button_start_automatic_sync.grid()
        batch_mode_button.grid()
        action_menu_auto.grid()
        sync_frame.grid()
        if sync_tool_var_auto.get() == SYNC_TOOL_ALASS:
            alass_split_penalty_slider.grid()
            alass_disable_fps_guessing.grid()
            alass_speed_optimization.grid()
            ffsubsync_option_gss.grid_remove()
            vad_frame.grid_remove()
            ffsubsync_option_framerate.grid_remove()
        else:
            ffsubsync_option_gss.grid()
            vad_frame.grid()
            ffsubsync_option_framerate.grid()
            alass_split_penalty_slider.grid_remove()
            alass_disable_fps_guessing.grid_remove()
            alass_speed_optimization.grid_remove()
        log_window.grid_remove()
        progress_bar.grid_remove()
        button_go_back.grid_remove()
        button_generate_again.grid_remove()
        button_cancel_batch_sync.grid_remove()
        tree_frame.grid()  # Show tree_frame
        automatic_tab.columnconfigure(0, weight=0)
        root.update_idletasks()

    def generate_again():
        treeview.delete(*treeview.get_children())
        batch_input.grid(
            row=0,
            column=0,
            padx=10,
            pady=(10, 0),
            sticky="nsew",
            columnspan=2,
            rowspan=2,
        )
        tree_frame.grid_remove()
        button_start_automatic_sync.grid()
        batch_mode_button.grid()
        log_window.grid_remove()
        progress_bar.grid_remove()
        button_go_back.grid_remove()
        button_generate_again.grid_remove()
        action_menu_auto.grid()
        sync_frame.grid()
        if sync_tool_var_auto.get() == SYNC_TOOL_ALASS:
            alass_split_penalty_slider.grid()
            alass_disable_fps_guessing.grid()
            alass_speed_optimization.grid()
            ffsubsync_option_gss.grid_remove()
            vad_frame.grid_remove()
            ffsubsync_option_framerate.grid_remove()
        else:
            ffsubsync_option_gss.grid()
            vad_frame.grid()
            ffsubsync_option_framerate.grid()
            alass_split_penalty_slider.grid_remove()
            alass_disable_fps_guessing.grid_remove()
            alass_speed_optimization.grid_remove()
        label_message_auto.grid_remove()
        automatic_tab.columnconfigure(0, weight=0)
        root.update_idletasks()

    def execute_cmd(cmd):
        global process
        decoding_error_occurred = False
        try:
            process = create_process(cmd)
            previous_line_had_percentage = False
            for output in process.stdout:
                if cancel_flag_batch:
                    return False
                if sync_tool == SYNC_TOOL_FFSUBSYNC:
                    # Remove timestamps
                    output = re.sub(r"\[\d{2}:\d{2}:\d{2}\]\s*", "", output)
                    # Strip leading spaces
                    output = output.lstrip()
                    # If no "INFO|WARNING|CRITICAL|ERROR" in output, add 9 spaces
                    if not re.search(r"\b(INFO|WARNING|CRITICAL|ERROR)\b", output):
                        output = "         " + output
                    output = " " + output
                    match_percentage = re.search(r"\b(\d+(\.\d+)?)%\|", output)
                elif sync_tool == SYNC_TOOL_ALASS:
                    # Modify ALASS output to show shorter progress bar
                    if "[" in output and "]" in output:
                        output = shorten_progress_bar(output)
                    match_percentage = re.search(
                        r"\[\s*=\s*\]\s*(\d+\.\d+)\s*%", output
                    )
                    if not match_percentage:
                        match_percentage = re.search(
                            r"\d+\s*/\s*\d+\s*\[.*\]\s*(\d+\.\d+)\s*%", output
                        )
                if match_percentage:
                    if previous_line_had_percentage:
                        log_window.replace("end-2l", "end-1l", output)
                    else:
                        log_window.insert(tk.END, output)
                    previous_line_had_percentage = True
                    percentage = float(match_percentage.group(1))
                    adjusted_value = min(97, max(1, percentage))
                    progress_increment = (adjusted_value / 100) * (100 / total_items)
                    progress_bar["value"] = (
                        completed_items / total_items
                    ) * 100 + progress_increment
                else:
                    log_window.insert(tk.END, output)
                    previous_line_had_percentage = False

                if (
                    "error while decoding subtitle from bytes to string" in output
                    and sync_tool == SYNC_TOOL_ALASS
                ):
                    decoding_error_occurred = True
            if process:
                process.wait()
            if "error" in output.lower():
                return 1, decoding_error_occurred
            return process.returncode, decoding_error_occurred
        except Exception as e:
            error_msg = f"{ERROR_EXECUTING_COMMAND}{str(e)}\n"
            if (
                sync_tool == SYNC_TOOL_ALASS
                and "could not convert string to float" in str(e)
            ):
                error_msg += "\n" + ERROR_DECODING_SUBTITLE + "\n"
            log_window.insert(tk.END, error_msg)
            return 1, decoding_error_occurred  # Ensure a tuple is returned

    def run_batch_process():
        nonlocal completed_items, total_items
        success_count = 0
        failure_count = 0
        subtitles_to_skip = set()
        subtitles_to_process = []
        failed_syncs = []
        add_suffix = True
        if (
            action_var_auto.get() == OPTION_REPLACE_ORIGINAL_SUBTITLE
            or action_var_auto.get() == OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME
        ):
            add_suffix = False
        for parent in tree_items:
            if cancel_flag_batch:
                return False
            parent_values = treeview.item(parent, "values")
            if not parent_values:
                log_window.insert(tk.END, f"{INVALID_PARENT_ITEM}\n")
                continue
            video_file = parent_values[0] if len(parent_values) > 0 else ""
            subtitles = treeview.get_children(parent)
            for sub in subtitles:
                values = treeview.item(sub, "values")
                subtitle_file = values[0] if len(values) > 0 else ""
                if not subtitle_file and not video_file:
                    log_window.insert(tk.END, f"\n{SKIP_NO_VIDEO_NO_SUBTITLE}\n")
                    continue
                if not subtitle_file:
                    log_window.insert(
                        tk.END,
                        f"\n{SKIP_NO_SUBTITLE.format(video_file=os.path.basename(video_file))}\n",
                    )
                    continue
                if not video_file:
                    log_window.insert(
                        tk.END,
                        f"\n{SKIP_NO_VIDEO.format(subtitle_file=os.path.basename(subtitle_file))}\n",
                    )
                    continue
                if not values:
                    log_window.insert(tk.END, f"\n{SKIP_UNPAIRED_ITEM}\n")
                    continue
                # Prepare output file path
                if action_var_auto.get() == OPTION_SAVE_TO_DESKTOP:
                    desktop_path = get_desktop_path()
                    base_output_dir = desktop_path
                elif action_var_auto.get() == OPTION_REPLACE_ORIGINAL_SUBTITLE:
                    base_output_dir = os.path.dirname(subtitle_file)
                elif action_var_auto.get() == OPTION_SAVE_NEXT_TO_VIDEO:
                    base_output_dir = os.path.dirname(video_file)
                elif (
                    action_var_auto.get()
                    == OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME
                ):
                    base_output_dir = os.path.dirname(video_file)
                elif action_var_auto.get() == OPTION_SELECT_DESTINATION_FOLDER:
                    base_output_dir = selected_destination_folder
                else:
                    base_output_dir = os.path.dirname(subtitle_file)
                # Determine output extension
                base_name, original_ext = os.path.splitext(
                    os.path.basename(subtitle_file)
                )
                if original_ext in SUPPORTED_SUBTITLE_EXTENSIONS:
                    output_ext = original_ext
                else:
                    output_ext = ".srt"
                # Check for existing autosync files
                # and optionally ending with '_2', '_3', etc.
                autosync_pattern = rf"^{subtitle_prefix}{re.escape(base_name)}(?:_\d+)?{re.escape(output_ext)}$"
                synced_files = [
                    f
                    for f in os.listdir(base_output_dir)
                    if re.match(autosync_pattern, f)
                ]
                if synced_files:
                    subtitles_to_skip.add(subtitle_file)
                else:
                    subtitles_to_process.append((subtitle_file, video_file))
        # Prompt the user
        count = len(subtitles_to_skip)
        if count > 0 and add_suffix:
            skip = messagebox.askyesno(
                ALREADY_SYNCED_FILES_TITLE,
                ALREADY_SYNCED_FILES_MESSAGE.format(count=count),
            )
            if skip:
                total_items -= count
        else:
            skip = False
        for parent in tree_items:
            if cancel_flag_batch:
                return False
            parent_values = treeview.item(parent, "values")
            if not parent_values:
                continue
            video_file = parent_values[0] if len(parent_values) > 0 else ""
            subtitles = treeview.get_children(parent)
            for sub in subtitles:
                values = treeview.item(sub, "values")
                subtitle_file = values[0] if len(values) > 0 else ""
                original_subtitle_file = (
                    subtitle_file  # Store the original subtitle file name
                )
                if not video_file:
                    continue
                if not subtitle_file:
                    continue
                if subtitle_file in subtitles_to_skip and skip:
                    log_window.insert(
                        tk.END,
                        f"{SKIPPING_ALREADY_SYNCED.format(filename=os.path.basename(subtitle_file))}\n\n",
                    )
                    continue

                # Determine base output directory for EACH file pair - moved inside the loop
                if action_var_auto.get() == OPTION_SAVE_TO_DESKTOP:
                    desktop_path = get_desktop_path()
                    base_output_dir = desktop_path
                elif action_var_auto.get() == OPTION_REPLACE_ORIGINAL_SUBTITLE:
                    base_output_dir = os.path.dirname(subtitle_file)
                elif action_var_auto.get() == OPTION_SAVE_NEXT_TO_VIDEO:
                    base_output_dir = os.path.dirname(video_file)
                elif (
                    action_var_auto.get()
                    == OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME
                ):
                    base_output_dir = os.path.dirname(video_file)
                elif action_var_auto.get() == OPTION_SELECT_DESTINATION_FOLDER:
                    base_output_dir = selected_destination_folder
                else:
                    base_output_dir = os.path.dirname(subtitle_file)

                original_base_name = os.path.splitext(os.path.basename(subtitle_file))[
                    0
                ]
                video_file_converted = None
                subtitle_file_converted = None
                closest_subtitle = None
                # Convert subtitle file if necessary
                unsupported_extensions = [
                    ext
                    for ext in SUBTITLE_EXTENSIONS
                    if ext not in SUPPORTED_SUBTITLE_EXTENSIONS
                ]
                log_window.insert(
                    tk.END,
                    SYNCING_LOG_TEXT.format(
                        completed_items + 1,
                        total_items,
                        os.path.basename(original_subtitle_file),
                        os.path.basename(video_file),
                    ),
                )
                completed_items += 1
                if subtitle_file.lower().endswith(tuple(unsupported_extensions)):
                    subtitle_file_converted = convert_to_srt(
                        subtitle_file, base_output_dir, log_window
                    )
                    if subtitle_file_converted:
                        subtitle_file = subtitle_file_converted
                    else:
                        log_window.insert(
                            tk.END,
                            f"{FAILED_CONVERT_SUBTITLE.format(subtitle_file=subtitle_file)}\n\n",
                        )
                        failure_count += 1  # Increment failure count
                        failed_syncs.append(
                            (video_file, subtitle_file, completed_items)
                        )
                        # Log the failed sync
                        continue  # Skip to the next file pair

                original_video_file = video_file
                if sync_tool == SYNC_TOOL_ALASS:
                    # if it is a video file, extract subtitle streams
                    if (
                        video_file.lower().endswith(tuple(VIDEO_EXTENSIONS))
                        and check_video_for_subtitle_stream_in_alass
                    ):
                        log_window.insert(tk.END, CHECKING_SUBTITLE_STREAMS + "\n")
                        closest_subtitle = extract_subtitles(
                            video_file, subtitle_file, base_output_dir, log_window
                        )
                        if closest_subtitle:
                            video_file = closest_subtitle
                # Convert video file if necessary
                if video_file.lower().endswith(tuple(unsupported_extensions)):
                    video_file_converted = convert_to_srt(
                        video_file, base_output_dir, log_window
                    )
                    if video_file_converted:
                        video_file = video_file_converted
                    else:
                        log_window.insert(
                            tk.END,
                            f"{FAILED_CONVERT_VIDEO.format(video_file=video_file)}\n\n",
                        )
                        failure_count += 1  # Increment failure count
                        failed_syncs.append(
                            (video_file, subtitle_file, completed_items)
                        )
                        # Log the failed sync
                        continue  # Skip to the next file pair
                if not original_base_name:
                    continue
                # Update base_name for each subtitle file
                base_name, original_ext = os.path.splitext(
                    os.path.basename(original_subtitle_file)
                )
                if action_var_auto.get() == OPTION_SAVE_NEXT_TO_VIDEO:
                    prefix = subtitle_prefix if add_prefix else ""
                    output_subtitle_file = os.path.join(
                        base_output_dir, f"{prefix}{base_name}{original_ext}"
                    )
                elif (
                    action_var_auto.get()
                    == OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME
                ):
                    output_subtitle_file = os.path.join(
                        base_output_dir,
                        f"{os.path.splitext(os.path.basename(original_video_file))[0]}{original_ext}",
                    )
                elif action_var_auto.get() == OPTION_REPLACE_ORIGINAL_SUBTITLE:
                    output_subtitle_file = subtitle_file
                else:
                    prefix = subtitle_prefix if add_prefix else ""
                    output_subtitle_file = os.path.join(
                        base_output_dir, f"{prefix}{base_name}{original_ext}"
                    )
                if not output_subtitle_file.lower().endswith(
                    tuple(SUPPORTED_SUBTITLE_EXTENSIONS)
                ):
                    output_subtitle_file = (
                        os.path.splitext(output_subtitle_file)[0] + ".srt"
                    )
                if (
                    action_var_auto.get() == OPTION_REPLACE_ORIGINAL_SUBTITLE
                    or action_var_auto.get()
                    == OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME
                ):
                    # if there is a file with the same name as the output_subtitle_file, create a backup
                    if (
                        os.path.exists(output_subtitle_file)
                        and backup_subtitles_before_overwriting
                    ):
                        new_output_subtitle_file = create_backup(output_subtitle_file)
                        log_window.insert(
                            tk.END,
                            f"{BACKUP_CREATED.format(output_subtitle_file=new_output_subtitle_file)}\n",
                        )
                # Handle autosync suffix
                # Updated regex pattern to match filenames starting with 'autosync_' followed by the base name
                # and ending with '_2', '_3', etc.
                if original_ext in SUPPORTED_SUBTITLE_EXTENSIONS:
                    output_ext = original_ext
                else:
                    output_ext = ".srt"
                autosync_pattern = rf"^{subtitle_prefix}{re.escape(original_base_name)}(?:_\d+)?{re.escape(original_ext)}$"
                suffix = 2
                prefix = subtitle_prefix if add_prefix else ""
                while os.path.exists(output_subtitle_file) and add_suffix is True:
                    output_subtitle_file = os.path.join(
                        base_output_dir,
                        f"{prefix}{original_base_name}_{suffix}{output_ext}",
                    )
                    suffix += 1
                subtitle_file = os.path.abspath(subtitle_file)
                if sync_tool == SYNC_TOOL_FFSUBSYNC:
                    cmd = f'"{CALL_FFSUBSYNC}" "{video_file}" -i "{subtitle_file}" -o "{output_subtitle_file}"'
                    if not video_file.lower().endswith(tuple(SUBTITLE_EXTENSIONS)):
                        if (
                            vad_option_map.get(ffsubsync_option_vad_var.get(), "")
                            != "default"
                        ):
                            cmd += f" --vad={vad_option_map.get(ffsubsync_option_vad_var.get(), '')}"
                    if ffsubsync_option_framerate_var.get():
                        cmd += " --no-fix-framerate"
                    if ffsubsync_option_gss_var.get():
                        cmd += " --gss"
                    if additional_ffsubsync_args:
                        cmd += f" {additional_ffsubsync_args}"
                elif sync_tool == SYNC_TOOL_ALASS:
                    split_penalty = alass_split_penalty_var.get()
                    if split_penalty == -1:
                        cmd = f'"{CALL_ALASS}" "{video_file}" "{subtitle_file}" "{output_subtitle_file}" --no-split'
                    else:
                        cmd = f'"{CALL_ALASS}" "{video_file}" "{subtitle_file}" "{output_subtitle_file}" --split-penalty={split_penalty}'
                    if alass_speed_optimization_var.get():
                        cmd += " --speed-optimization 0"
                    if alass_disable_fps_guessing_var.get():
                        cmd += " --disable-fps-guessing"
                    if additional_alass_args:
                        cmd += f" {additional_alass_args}"
                else:
                    log_message(INVALID_SYNC_TOOL, "error", tab="auto")
                    return False
                try:
                    progress_bar["value"] += 1
                    if sync_tool == SYNC_TOOL_FFSUBSYNC:
                        if video_file.lower().endswith(tuple(SUBTITLE_EXTENSIONS)):
                            log_window.insert(tk.END, f"{USING_REFERENCE_SUBTITLE}\n")
                        else:
                            log_window.insert(tk.END, f"{USING_VIDEO_FOR_SYNC}\n")
                            if (
                                vad_option_map.get(ffsubsync_option_vad_var.get(), "")
                                != "default"
                            ):
                                log_window.insert(
                                    tk.END,
                                    f"{VOICE_ACTIVITY_DETECTOR}: {vad_option_map.get(ffsubsync_option_vad_var.get(), '')}\n",
                                )
                        if ffsubsync_option_framerate_var.get():
                            log_window.insert(tk.END, f"{ENABLED_NO_FIX_FRAMERATE}\n")
                        if ffsubsync_option_gss_var.get():
                            log_window.insert(tk.END, f"{ENABLED_GSS}\n")
                        if additional_ffsubsync_args:
                            log_window.insert(
                                tk.END,
                                f"{ADDITIONAL_ARGS_ADDED.format(additional_args=additional_ffsubsync_args)}\n",
                            )
                    elif sync_tool == SYNC_TOOL_ALASS:
                        if split_penalty == -1:
                            log_window.insert(tk.END, f"{SPLIT_PENALTY_ZERO}\n")
                        else:
                            log_window.insert(
                                tk.END,
                                f"{SPLIT_PENALTY_SET.format(split_penalty=split_penalty)}\n",
                            )
                        if alass_speed_optimization_var.get():
                            log_window.insert(
                                tk.END, f"{ALASS_SPEED_OPTIMIZATION_LOG}\n"
                            )
                        if alass_disable_fps_guessing_var.get():
                            log_window.insert(
                                tk.END, f"{ALASS_DISABLE_FPS_GUESSING_LOG}\n"
                            )
                        if additional_alass_args:
                            log_window.insert(
                                tk.END,
                                f"{ADDITIONAL_ARGS_ADDED.format(additional_args=additional_alass_args)}\n",
                            )
                    log_window.insert(tk.END, f"{SYNCING_STARTED}\n")
                except Exception as e:
                    log_window.insert(
                        tk.END, f"{FAILED_START_PROCESS.format(error_message=str(e))}\n"
                    )
                    log_message(
                        FAILED_START_PROCESS.format(error_message=str(e)),
                        "error",
                        tab="auto",
                    )
                    continue
                try:
                    returncode, decoding_error_occurred = execute_cmd(cmd)
                    # alass specific code
                    if sync_tool == SYNC_TOOL_ALASS:
                        encoding_ref = None
                        encoding_inc = detect_encoding(subtitle_file)
                        # if encoding_inc is not inside enc_list, select the closest encoding in enc_list
                        if encoding_inc not in enc_list:
                            closest_encoding = find_closest_encoding(encoding_inc)
                            encoding_inc = closest_encoding
                        if returncode != 0 and decoding_error_occurred:
                            log_window.insert(
                                tk.END, "\n" + RETRY_ENCODING_MSG + "\n\n"
                            )
                            if video_file.lower().endswith(tuple(SUBTITLE_EXTENSIONS)):
                                encoding_ref = detect_encoding(video_file)
                                # if encoding_ref is not inside enc_list, select the closest encoding in enc_list
                                if encoding_ref not in enc_list:
                                    closest_encoding = find_closest_encoding(
                                        encoding_ref
                                    )
                                    encoding_ref = closest_encoding
                                cmd += f" --encoding-ref={encoding_ref}"
                            cmd += f" --encoding-inc={encoding_inc}"
                            returncode, decoding_error_occurred = execute_cmd(cmd)
                        synced_subtitle_encoding = detect_encoding(output_subtitle_file)
                        if synced_subtitle_encoding != encoding_inc:
                            change_encoding_msg = CHANGING_ENCODING_MSG.format(
                                synced_subtitle_encoding=synced_subtitle_encoding,
                                encoding_inc=encoding_inc,
                            )
                            log_window.insert(tk.END, "\n" + change_encoding_msg + "\n")
                            try:
                                with open(
                                    output_subtitle_file,
                                    "r",
                                    encoding=synced_subtitle_encoding,
                                    errors="replace",
                                ) as f:
                                    content = f.read()
                                with open(
                                    output_subtitle_file,
                                    "w",
                                    encoding=encoding_inc,
                                    errors="replace",
                                ) as f:
                                    f.write(content)
                                log_window.insert(
                                    tk.END, "\n" + ENCODING_CHANGED_MSG + "\n"
                                )
                            except Exception as e:
                                error_msg = ERROR_CHANGING_ENCODING_MSG.format(
                                    error_message=str(e)
                                )
                                log_window.insert(tk.END, "\n" + error_msg + "\n")
                        # if keep_extracted_subtitles is False, delete the extracted subtitle folder which is the folder of closest_subtitle.
                        if not keep_extracted_subtitles and closest_subtitle:
                            log_window.insert(
                                tk.END, f"\n{DELETING_EXTRACTED_SUBTITLE_FOLDER}\n\n"
                            )
                            shutil.rmtree(os.path.dirname(closest_subtitle))
                        if not keep_converted_subtitles:
                            if video_file_converted:
                                log_window.insert(
                                    tk.END, f"{DELETING_CONVERTED_SUBTITLE}\n\n"
                                )
                                os.remove(video_file_converted)
                            if subtitle_file_converted:
                                log_window.insert(
                                    tk.END, f"{DELETING_CONVERTED_SUBTITLE}\n\n"
                                )
                                os.remove(subtitle_file_converted)
                    if cancel_flag_batch:
                        return False
                    if returncode == 0:
                        log_window.insert(
                            tk.END,
                            f"{SYNC_SUCCESS.format(output_subtitle_file=output_subtitle_file)}",
                        )
                        success_count += 1
                    else:
                        log_window.insert(
                            tk.END,
                            f"{SYNC_ERROR.format(filename=os.path.basename(subtitle_file))}\n\n",
                        )
                        failure_count += 1
                        failed_syncs.append(
                            (video_file, subtitle_file, completed_items)
                        )
                except Exception as e:
                    error_msg = (
                        "\n" + ERROR_OCCURRED.format(error_message=str(e)) + "\n\n"
                    )
                    failure_count += 1
                    failed_syncs.append((video_file, subtitle_file, completed_items))
                    log_window.insert(tk.END, error_msg)
                progress_bar["value"] = (completed_items / total_items) * 100
                root.update_idletasks()
        if not cancel_flag_batch:
            log_window.insert(tk.END, f"{BATCH_SYNC_COMPLETED}\n")
            log_window.insert(
                tk.END, f"{SYNC_SUCCESS_COUNT.format(success_count=success_count)}\n"
            )
            if failure_count > 0:
                log_window.insert(
                    tk.END,
                    f"{SYNC_FAILURE_COUNT_BATCH.format(failure_count=failure_count)}\n",
                )
                for _, pair in enumerate(failed_syncs):
                    video_file, subtitle_file, item_index = pair
                    log_window.insert(
                        tk.END,
                        f'[{item_index}/{total_items}] "{video_file}" - "{subtitle_file}"\n',
                    )
            log_message(BATCH_SYNC_COMPLETED, "success", tab="auto")
            button_cancel_batch_sync.grid_remove()
            log_window.grid(pady=(10, 10), rowspan=2)
            button_go_back.grid()
            button_generate_again.grid()
            progress_bar.grid_remove()
            log_window.see(tk.END)
            root.after(50, lambda: log_window.see(tk.END))
            save_log_file(log_window, suffix="_batch")
        return True

    try:
        batch_input.grid_remove()
        tree_frame.grid_remove()
        button_start_automatic_sync.grid_remove()
        batch_mode_button.grid_remove()
        label_message_auto.grid_remove()
        action_menu_auto.grid_remove()
        sync_frame.grid_remove()
        ffsubsync_option_gss.grid_remove()
        vad_frame.grid_remove()
        ffsubsync_option_framerate.grid_remove()
        alass_split_penalty_slider.grid_remove()
        alass_disable_fps_guessing.grid_remove()
        alass_speed_optimization.grid_remove()
        button_cancel_batch_sync = TkButton(
            automatic_tab,
            text=CANCEL_TEXT,
            command=cancel_batch_sync,
            padx=10,
            pady=10,
            fg=COLOR_WB,
            bg=DEFAULT_BUTTON_COLOR,
            activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
            activeforeground=COLOR_WB,
            relief=tk.RAISED,
            borderwidth=2,
            cursor="hand2",
            highlightthickness=0,
            takefocus=0,
            state="normal",
        )
        button_cancel_batch_sync.grid(
            row=6, column=0, padx=10, pady=(0, 10), sticky="ew", columnspan=2
        )
        button_generate_again = TkButton(
            automatic_tab,
            text=GENERATE_AGAIN_TEXT,
            command=generate_again,
            padx=10,
            pady=10,
            fg=COLOR_WB,
            bg=BUTTON_COLOR_AUTO,
            activebackground=BUTTON_COLOR_AUTO_ACTIVE,
            activeforeground=COLOR_WB,
            relief=tk.RAISED,
            borderwidth=2,
            cursor="hand2",
            highlightthickness=0,
            takefocus=0,
            state="normal",
        )
        button_generate_again.grid(
            row=11, column=0, padx=10, pady=(0, 10), sticky="ew", columnspan=2
        )
        button_generate_again.grid_remove()
        button_go_back = TkButton(
            automatic_tab,
            text=GO_BACK,
            command=lambda: [log_message("", "info", tab="auto"), restore_window()],
            padx=10,
            pady=10,
            fg=COLOR_WB,
            bg=DEFAULT_BUTTON_COLOR,
            activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
            activeforeground=COLOR_WB,
            relief=tk.RAISED,
            borderwidth=2,
            cursor="hand2",
            highlightthickness=0,
            takefocus=0,
            state="normal",
        )
        button_go_back.grid(
            row=12, column=0, padx=10, pady=(0, 10), sticky="ew", columnspan=2
        )
        button_go_back.grid_remove()
        log_window = tk.Text(automatic_tab, wrap="word")
        log_window.config(
            font=(
                config["log_window_font"],
                config["log_window_font_size"],
                config["log_window_font_style"],
            ),
            bg=COLOR_WB,
            fg=COLOR_BW,
            insertbackground=COLOR_BW,
        )
        log_window.grid(
            row=0, column=0, padx=10, pady=(10, 5), sticky="nsew", columnspan=2
        )
        # Create a context menu for the log window
        log_window_context_menu = tk.Menu(log_window, tearoff=0)
        log_window_context_menu.add_command(
            label=CONTEXT_MENU_COPY,
            command=lambda: log_window.event_generate("<<Copy>>"),
        )

        # Function to show the context menu
        def show_log_window_context_menu(event):
            log_window_context_menu.post(event.x_root, event.y_root)

        # Bind the right-click event to the log window
        if platform == "Darwin":
            log_window.bind("<Button-2>", show_log_window_context_menu)
        else:
            log_window.bind("<Button-3>", show_log_window_context_menu)

        # Add a flag to track whether the user is at the bottom of the log window
        user_at_bottom = True

        def on_log_window_modified(event):
            global user_at_bottom
            # Check if the user is at the bottom of the log window
            if user_at_bottom:
                log_window.see(tk.END)
            log_window.edit_modified(False)  # Reset the modified flag

        # Add a button to scroll to the bottom
        scroll_to_bottom_button = tk.Button(
            log_window,
            text="↓",
            command=lambda: log_window.see(tk.END),
            bg=DEFAULT_BUTTON_COLOR,
            fg=COLOR_WB,
            activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
            activeforeground=COLOR_WB,
            relief=tk.RAISED,
            borderwidth=2,
            padx=7,
            pady=2,
            cursor="hand2",
            highlightthickness=0,
            takefocus=0,
        )
        scroll_to_bottom_button.lower()  # Initially hide the button

        def on_log_window_scroll(*args):
            global user_at_bottom
            # Get the current scroll position
            current_scroll = log_window.yview()
            # Check if the user is at the bottom
            user_at_bottom = (
                current_scroll[1] == 1.0
            )  # 1.0 means the scrollbar is at the bottom
            # Show or hide the "Go to Bottom" button
            if user_at_bottom:
                scroll_to_bottom_button.place_forget()  # Hide the button
            else:
                scroll_to_bottom_button.place(
                    relx=0.99, rely=0.99, anchor="se"
                )  # Show the button
            # Pass valid scroll arguments to the yview method
            if args[0] in ("moveto", "scroll"):
                log_window.yview(*args)

        # Bind the scroll event to track user scrolling
        log_window.config(yscrollcommand=on_log_window_scroll)
        log_window.bind("<<Modified>>", on_log_window_modified)
        log_window.edit_modified(False)
        progress_bar = ttk.Progressbar(
            automatic_tab, orient="horizontal", length=200, mode="determinate"
        )
        progress_bar.grid(
            row=1, column=0, padx=10, pady=(5, 10), sticky="ew", columnspan=2
        )
        root.update_idletasks()
        threading.Thread(target=run_batch_process).start()
    except Exception as e:
        log_message(ERROR_OCCURRED.format(error_message=str(e)), "error", tab="auto")
    automatic_tab.rowconfigure(0, weight=1)
    automatic_tab.rowconfigure(1, weight=0)
    automatic_tab.columnconfigure(0, weight=1)


def toggle_batch_mode():
    if treeview.get_children():
        log_message("", "info", tab="auto")
        if batch_mode_var.get():
            batch_mode_var.set(False)
            batch_mode_button.config(
                text=BATCH_MODE_TEXT,
                bg=DEFAULT_BUTTON_COLOR,
                fg=COLOR_WB,
                activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
            )
            button_start_automatic_sync.config(
                text=START_AUTOMATIC_SYNC_TEXT,
                bg=BUTTON_COLOR_AUTO,
                fg=COLOR_WB,
                activebackground=BUTTON_COLOR_AUTO_ACTIVE,
                command=start_automatic_sync,
            )
            subtitle_input.grid(
                row=1, column=0, padx=10, pady=0, sticky="nsew", columnspan=2
            )
            video_input.grid(
                row=0, column=0, padx=10, pady=(10, 5), sticky="nsew", columnspan=2
            )
            if getattr(subtitle_input, "tooltip_text", None):
                remove_subtitle_button.grid(
                    row=1, column=1, padx=(0, 12), pady=(2, 0), sticky="ne"
                )
            if getattr(video_input, "tooltip_text", None):
                remove_video_button.grid(
                    row=0, column=1, padx=(0, 12), pady=(12, 0), sticky="ne"
                )
            batch_input.grid_remove()
            tree_frame.grid_remove()
            automatic_tab.rowconfigure(1, weight=1)
            root.update_idletasks()
        else:
            batch_mode_var.set(True)
            batch_mode_button.config(
                text=NORMAL_MODE_TEXT,
                bg=DEFAULT_BUTTON_COLOR,
                fg=COLOR_WB,
                activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
            )
            button_start_automatic_sync.config(
                text=START_BATCH_SYNC_TEXT,
                bg=BUTTON_COLOR_BATCH,
                fg=COLOR_WB,
                activebackground=BUTTON_COLOR_BATCH_ACTIVE,
                command=start_batch_sync,
            )
            subtitle_input.grid_remove()
            video_input.grid_remove()
            remove_subtitle_button.grid_remove()
            remove_video_button.grid_remove()
            batch_input.grid(
                row=0,
                column=0,
                padx=10,
                pady=(10, 0),
                sticky="nsew",
                columnspan=2,
                rowspan=2,
            )
            tree_frame.grid()
    else:
        log_message("", "info", tab="auto")
        if batch_mode_var.get():
            batch_mode_var.set(False)
            batch_mode_button.config(
                text=BATCH_MODE_TEXT,
                bg=DEFAULT_BUTTON_COLOR,
                fg=COLOR_WB,
                activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
            )
            button_start_automatic_sync.config(
                text=START_AUTOMATIC_SYNC_TEXT,
                bg=BUTTON_COLOR_AUTO,
                fg=COLOR_WB,
                activebackground=BUTTON_COLOR_AUTO_ACTIVE,
                command=start_automatic_sync,
            )
            subtitle_input.grid(
                row=1, column=0, padx=10, pady=0, sticky="nsew", columnspan=2
            )
            video_input.grid(
                row=0, column=0, padx=10, pady=(10, 5), sticky="nsew", columnspan=2
            )
            if getattr(subtitle_input, "tooltip_text", None):
                remove_subtitle_button.grid(
                    row=1, column=1, padx=(0, 12), pady=(2, 0), sticky="ne"
                )
            if getattr(video_input, "tooltip_text", None):
                remove_video_button.grid(
                    row=0, column=1, padx=(0, 12), pady=(12, 0), sticky="ne"
                )
            batch_input.grid_remove()
            tree_frame.grid_remove()
            automatic_tab.rowconfigure(1, weight=1)
            root.update_idletasks()
        else:
            batch_mode_var.set(True)
            batch_mode_button.config(
                text=NORMAL_MODE_TEXT,
                bg=DEFAULT_BUTTON_COLOR,
                fg=COLOR_WB,
                activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
            )
            button_start_automatic_sync.config(
                text=START_BATCH_SYNC_TEXT,
                bg=BUTTON_COLOR_BATCH,
                fg=COLOR_WB,
                activebackground=BUTTON_COLOR_BATCH_ACTIVE,
                command=start_batch_sync,
            )
            subtitle_input.grid_remove()
            video_input.grid_remove()
            remove_subtitle_button.grid_remove()
            remove_video_button.grid_remove()
            batch_input.grid(
                row=0,
                column=0,
                padx=10,
                pady=(10, 0),
                sticky="nsew",
                columnspan=2,
                rowspan=2,
            )
            tree_frame.grid_remove()


# Helper function to compute effective base name by removing a trailing language tag
# (i.e. the last 2, 3, or 4 letters if preceded by '_', "-" or '.')
def effective_basename(file_path):
    base = os.path.splitext(os.path.basename(file_path))[0]
    for tag_length in [4, 3, 2]:
        if len(base) > tag_length and base[-(tag_length + 1)] in ["_", ".", "-"]:
            return base[: -(tag_length + 1)]
    return base


def process_files(filepaths, reference_pairs=False):
    subtitle_files = []
    video_files = []
    if reference_pairs:
        # Handle reference subtitle pairs
        subtitle_files = []
        reference_files = []
        for i, filepath in enumerate(filepaths):
            if i % 2 == 0:
                reference_files.append(filepath)
            else:
                subtitle_files.append(filepath)
        if not subtitle_files or not reference_files:
            log_message(DROP_VALID_FILES, "error", tab="auto")
            return
        pairs_added = 0
        duplicates = 0
        existing_pairs = set()
        for parent in treeview.get_children():
            parent_values = treeview.item(parent, "values")
            if parent_values and parent_values[0]:
                ref_file = os.path.normpath(parent_values[0].lower())
                subtitles = treeview.get_children(parent)
                for sub in subtitles:
                    values = treeview.item(sub, "values")
                    if values and values[0]:
                        subtitle_file = os.path.normpath(values[0].lower())
                        existing_pairs.add((ref_file, subtitle_file))
        complete_pairs = []
        for ref_file, sub_file in zip(reference_files, subtitle_files):
            ref_name = os.path.basename(ref_file)
            sub_name = os.path.basename(sub_file)
            norm_ref = os.path.normpath(ref_file.lower())
            norm_sub = os.path.normpath(sub_file.lower())
            pair = (norm_ref, norm_sub)
            if pair not in existing_pairs:
                existing_pairs.add(pair)
                pairs_added += 1
                complete_pairs.append((ref_name, sub_name, ref_file, sub_file))
            else:
                duplicates += 1
        batch_input.grid_remove()
        tree_frame.grid()
        for ref_name, sub_name, ref_file, sub_file in complete_pairs:
            parent_id = treeview.insert(
                "", "end", text=ref_name, values=(ref_file,), open=True
            )
            treeview.insert(parent_id, "end", text=sub_name, values=(sub_file,))
            treeview.item(parent_id, tags=("paired",))
        messages = []
        if pairs_added > 0:
            messages.append(
                ADDED_PAIRS_MSG.format(pairs_added, "s" if pairs_added != 1 else "")
            )
        if duplicates > 0:
            messages.append(
                SKIPPED_DUPLICATES_MSG.format(
                    duplicates, "s" if duplicates != 1 else ""
                )
            )
        if messages:
            log_message(", ".join(messages) + ".", "info", tab="auto")
    else:
        for filepath in filepaths:
            if os.path.isdir(filepath):
                for root_dir, _, files in os.walk(filepath):
                    for file in files:
                        full_path = os.path.join(root_dir, file)
                        if full_path.lower().endswith(tuple(SUBTITLE_EXTENSIONS)):
                            subtitle_files.append(full_path)
                        elif full_path.lower().endswith(tuple(VIDEO_EXTENSIONS)):
                            video_files.append(full_path)
            else:
                if filepath.lower().endswith(tuple(SUBTITLE_EXTENSIONS)):
                    subtitle_files.append(filepath)
                elif filepath.lower().endswith(tuple(VIDEO_EXTENSIONS)):
                    video_files.append(filepath)
        # Check if there are any video or subtitle files
        if not subtitle_files and not video_files:
            log_message(DROP_VALID_FILES, "error", tab="auto")
            batch_input.config(bg=COLOR_ONE, fg=COLOR_BW)
            return
        max_length = max(len(subtitle_files), len(video_files))
        subtitle_files.extend([None] * (max_length - len(subtitle_files)))
        video_files.extend([None] * (max_length - len(video_files)))
        pairs_added = 0
        files_not_paired = 0
        duplicates = 0
        existing_pairs = set()
        for parent in treeview.get_children():
            parent_values = treeview.item(parent, "values")
            if parent_values and parent_values[0]:
                video_file_norm = os.path.normpath(parent_values[0].lower())
                subtitles = treeview.get_children(parent)
                for sub in subtitles:
                    values = treeview.item(sub, "values")
                    if values and values[0]:
                        subtitle_file_norm = os.path.normpath(values[0].lower())
                        existing_pairs.add((video_file_norm, subtitle_file_norm))
        incomplete_pairs = []
        complete_pairs = []
        # Pair videos with subtitles based on similar filenames (considering language tags)
        for video_file in sorted(
            video_files, key=lambda x: os.path.basename(x) if x else ""
        ):
            video_name = os.path.basename(video_file) if video_file else NO_VIDEO
            # For a given video, gather all subtitles whose effective base matches
            if video_file:
                video_dir = os.path.dirname(video_file)
                effective_video = effective_basename(video_file)
                matched_subtitles = []
                # First, check in the same directory
                for sub_file in subtitle_files[:]:
                    if sub_file and os.path.dirname(sub_file) == video_dir:
                        if effective_basename(sub_file) == effective_video:
                            matched_subtitles.append(sub_file)
                            subtitle_files.remove(sub_file)
                # If none found in the same directory, check parent directories
                if not matched_subtitles:
                    parent_dir = video_dir
                    while parent_dir != os.path.dirname(parent_dir):
                        parent_dir = os.path.dirname(parent_dir)
                        for sub_file in subtitle_files[:]:
                            if sub_file and os.path.dirname(sub_file) == parent_dir:
                                if effective_basename(sub_file) == effective_video:
                                    matched_subtitles.append(sub_file)
                                    subtitle_files.remove(sub_file)
                        if matched_subtitles:
                            break
                if matched_subtitles:
                    for sub_file in matched_subtitles:
                        subtitle_name = os.path.basename(sub_file)
                        norm_video = os.path.normpath(video_file.lower())
                        norm_subtitle = os.path.normpath(sub_file.lower())
                        pair = (norm_video, norm_subtitle)
                        if pair in existing_pairs:
                            duplicates += 1
                            continue
                        existing_pairs.add(pair)
                        pairs_added += 1
                        complete_pairs.append(
                            (video_name, subtitle_name, video_file, sub_file)
                        )
                else:
                    files_not_paired += 1
                    incomplete_pairs.append((video_name, NO_SUBTITLE, video_file, None))
            else:
                incomplete_pairs.append((video_name, NO_SUBTITLE, video_file, None))
        # Handle remaining unpaired subtitles for single video case
        unpaired_subtitles = list(filter(None, subtitle_files))
        if (
            len(unpaired_subtitles) == 1
            and len(video_files) == 1
            and video_files[0] is not None
        ):
            user_choice = messagebox.askyesno(PAIR_FILES_TITLE, PAIR_FILES_MESSAGE)
            if user_choice:
                subtitle_file = unpaired_subtitles[0]
                video_file = video_files[0]
                norm_video = os.path.normpath(video_file.lower())
                norm_subtitle = os.path.normpath(subtitle_file.lower())
                pair = (norm_video, norm_subtitle)
                if pair not in existing_pairs:
                    existing_pairs.add(pair)
                    pairs_added = 1
                    files_not_paired = 0
                    complete_pairs.append(
                        (
                            os.path.basename(video_file),
                            os.path.basename(subtitle_file),
                            video_file,
                            subtitle_file,
                        )
                    )
                else:
                    duplicates += 1
                    pairs_added = 0
                    files_not_paired = 0
                incomplete_pairs = [
                    pair for pair in incomplete_pairs if pair[2] != video_file
                ]
            else:
                incomplete_pairs.append(
                    (
                        NO_VIDEO,
                        os.path.basename(unpaired_subtitles[0]),
                        None,
                        unpaired_subtitles[0],
                    )
                )
                files_not_paired += 1
        else:
            if unpaired_subtitles:
                unpaired_count = len(unpaired_subtitles)
                user_choice = messagebox.askyesno(
                    UNPAIRED_SUBTITLES_TITLE,
                    UNPAIRED_SUBTITLES_MESSAGE.format(unpaired_count=unpaired_count),
                )
                for sub_file in unpaired_subtitles:
                    subtitle_name = os.path.basename(sub_file)
                    if user_choice:
                        incomplete_pairs.append(
                            (NO_VIDEO, subtitle_name, None, sub_file)
                        )
                    else:
                        incomplete_pairs.append(
                            (subtitle_name, NO_SUBTITLE, sub_file, None)
                        )
                    files_not_paired += 1
        # Insert incomplete pairs first
        for video_name, subtitle_name, video_file, subtitle_file in incomplete_pairs:
            if video_file:
                parent_id = treeview.insert(
                    "", "end", text=video_name, values=(rf"{video_file}",), open=True
                )
                treeview.insert(
                    parent_id,
                    "end",
                    text=subtitle_name,
                    values=(subtitle_file if subtitle_file else ""),
                )
            elif subtitle_file:
                parent_id = treeview.insert(
                    "", "end", text=NO_VIDEO, values=("",), open=True
                )
                treeview.insert(
                    parent_id, "end", text=subtitle_name, values=(subtitle_file,)
                )
            else:
                continue
            treeview.item(parent_id, tags=("incomplete",))
            if not video_file and not subtitle_file:
                treeview.delete(parent_id)
        # Insert complete pairs
        for video_name, subtitle_name, video_file, subtitle_file in complete_pairs:
            parent_id = treeview.insert(
                "", "end", text=video_name, values=(video_file,), open=True
            )
            treeview.insert(
                parent_id, "end", text=subtitle_name, values=(subtitle_file,)
            )
            treeview.item(parent_id, tags=("paired",))
        # Handle UI updates and logging
        batch_input.grid_remove()
        tree_frame.grid()
        messages = []
        if pairs_added > 0:
            messages.append(PAIRS_ADDED.format(count=pairs_added))
        if files_not_paired > 0:
            if pairs_added < 1 or (duplicates > 0 and pairs_added < 1):
                messages.append(UNPAIRED_FILES_ADDED.format(count=files_not_paired))
            else:
                messages.append(UNPAIRED_FILES.format(count=files_not_paired))
        if duplicates > 0:
            messages.append(DUPLICATE_PAIRS_SKIPPED.format(count=duplicates))
        if messages:
            log_message(", ".join(messages) + ".", "info", tab="auto")


def select_folder():
    folder_path = filedialog.askdirectory()
    if folder_path:
        process_files([folder_path])


def browse_batch(event=None):
    paths = filedialog.askopenfilenames(
        filetypes=[
            (
                VIDEO_OR_SUBTITLE_TEXT,
                " ".join([f"*{ext}" for ext in SUBTITLE_EXTENSIONS + VIDEO_EXTENSIONS]),
            )
        ]
    )
    if paths:
        process_files(paths)


# REFERENCE SUBTITLE / SUBTITLE PAIRING START


def reference_subtitle_subtitle_pairs():
    window = tk.Toplevel()
    dark_title_bar(window)
    window.title(MENU_ADD_REFERENCE_SUBITLE_SUBTITLE_PAIRIS)
    window.configure(background=COLOR_BACKGROUND)
    # Store file paths
    ref_file_paths = []
    sub_file_paths = []
    # Set window size and constraints
    width = 800
    height = 600
    window.geometry(f"{width}x{height}")
    window.minsize(width - 100, height - 100)
    # Center the window
    x = (window.winfo_screenwidth() // 2) - (width // 2)
    y = (window.winfo_screenheight() // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")
    window.update_idletasks()
    # Create explanation frame
    explanation_frame = ttk.Frame(window, padding="10")
    explanation_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")
    explanation_label = ttk.Label(
        explanation_frame,
        text=EXPLANATION_TEXT_IN_REFERENCE_SUBTITLE_PAIRING.format(
            program_name=PROGRAM_NAME
        ),
        wraplength=800,
        justify="left",
        background=COLOR_BACKGROUND,
        foreground=COLOR_BW,
    )
    explanation_label.pack(fill="x")
    frame_left = ttk.Frame(window, padding=(10, 0, 5, 0), width=300)
    frame_left.grid(row=1, column=0, sticky="nsew")
    frame_left.pack_propagate(False)
    frame_right = ttk.Frame(window, padding=(5, 0, 10, 0), width=300)
    frame_right.grid(row=1, column=1, sticky="nsew")
    frame_right.pack_propagate(False)
    frame_bottom = ttk.Frame(window, padding=(10, 10))
    frame_bottom.grid(row=2, column=0, columnspan=2, sticky="ew")
    window.grid_columnconfigure(0, weight=1, minsize=300)
    window.grid_columnconfigure(1, weight=1, minsize=300)
    window.grid_rowconfigure(1, weight=1)
    ref_header = ttk.Frame(frame_left)
    ref_header.pack(fill="x", pady=(0, 5))
    ref_header.grid_columnconfigure(0, weight=1)
    sub_header = ttk.Frame(frame_right)
    sub_header.pack(fill="x", pady=(0, 5))
    sub_header.grid_columnconfigure(0, weight=1)
    # Create labels and buttons in headers
    ref_label = ttk.Label(
        ref_header,
        text=REF_LABEL_TEXT,
        anchor="w",
        background=COLOR_BACKGROUND,
        foreground=COLOR_BW,
    )
    ref_label.grid(row=0, column=0, sticky="w")
    ref_add_btn = TkButton(
        ref_header,
        text=BUTTON_ADD_FILES,
        font=f"Arial {FONT_SIZE} bold",
        command=lambda: load_files(listbox_left, ref_file_paths, type="reference"),
        padx=4,
        pady=0,
        fg=COLOR_WB,
        bg=DEFAULT_BUTTON_COLOR,
        activeforeground=COLOR_WB,
        activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
        relief=tk.RIDGE,
        borderwidth=1,
        cursor="hand2",
        highlightthickness=0,
        takefocus=0,
        state="normal",
    )
    ref_add_btn.grid(row=0, column=1, padx=(5, 0))
    ref_remove_btn = TkButton(
        ref_header,
        text=CONTEXT_MENU_REMOVE,
        font=f"Arial {FONT_SIZE} bold",
        command=lambda: remove_selected_item(listbox_left, ref_file_paths),
        padx=4,
        pady=0,
        fg=COLOR_WB,
        bg=DEFAULT_BUTTON_COLOR,
        activeforeground=COLOR_WB,
        activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
        relief=tk.RIDGE,
        borderwidth=1,
        cursor="hand2",
        highlightthickness=0,
        takefocus=0,
        state="normal",
    )
    ref_remove_btn.grid(row=0, column=2, padx=(5, 0))
    sub_label = ttk.Label(
        sub_header,
        text=SUB_LABEL_TEXT,
        anchor="w",
        background=COLOR_BACKGROUND,
        foreground=COLOR_BW,
    )
    sub_label.grid(row=0, column=0, sticky="w")
    sub_add_btn = TkButton(
        sub_header,
        text=BUTTON_ADD_FILES,
        font=f"Arial {FONT_SIZE} bold",
        command=lambda: load_files(listbox_right, sub_file_paths, type="subtitle"),
        padx=4,
        pady=0,
        fg=COLOR_WB,
        bg=DEFAULT_BUTTON_COLOR,
        activeforeground=COLOR_WB,
        activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
        relief=tk.RIDGE,
        borderwidth=1,
        cursor="hand2",
        highlightthickness=0,
        takefocus=0,
        state="normal",
    )
    sub_add_btn.grid(row=0, column=1, padx=(5, 0))
    sub_remove_btn = TkButton(
        sub_header,
        text=CONTEXT_MENU_REMOVE,
        font=f"Arial {FONT_SIZE} bold",
        command=lambda: remove_selected_item(listbox_right, sub_file_paths),
        padx=4,
        pady=0,
        fg=COLOR_WB,
        bg=DEFAULT_BUTTON_COLOR,
        activeforeground=COLOR_WB,
        activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
        relief=tk.RIDGE,
        borderwidth=1,
        cursor="hand2",
        highlightthickness=0,
        takefocus=0,
        state="normal",
    )
    sub_remove_btn.grid(row=0, column=2, padx=(5, 0))
    ref_header.pack_forget()
    sub_header.pack_forget()
    # Create options menus
    ref_options = tk.Menu(window, tearoff=0)
    ref_options.add_command(
        label=CONTEXT_MENU_SHOW_PATH,
        command=lambda: show_path_reference(listbox_left, ref_file_paths),
    )
    ref_options.add_command(
        label=CONTEXT_MENU_REMOVE,
        command=lambda: remove_selected_item(listbox_left, ref_file_paths),
    )
    ref_options.add_separator()
    ref_options.add_command(
        label=BUTTON_ADD_FILES,
        command=lambda: load_files(listbox_left, ref_file_paths, type="reference"),
    )
    ref_options.add_command(
        label=CONTEXT_MENU_CLEAR_ALL,
        command=lambda: clear_files(
            listbox_left, ref_file_paths, ref_header, ref_input
        ),
    )
    sub_options = tk.Menu(window, tearoff=0)
    sub_options.add_command(
        label=CONTEXT_MENU_SHOW_PATH,
        command=lambda: show_path_reference(listbox_right, sub_file_paths),
    )
    sub_options.add_command(
        label=CONTEXT_MENU_REMOVE,
        command=lambda: remove_selected_item(listbox_right, sub_file_paths),
    )
    sub_options.add_separator()
    sub_options.add_command(
        label=BUTTON_ADD_FILES,
        command=lambda: load_files(listbox_right, sub_file_paths, type="subtitle"),
    )
    sub_options.add_command(
        label=CONTEXT_MENU_CLEAR_ALL,
        command=lambda: clear_files(
            listbox_right, sub_file_paths, sub_header, sub_input
        ),
    )
    ref_input = tk.Label(
        frame_left,
        text=REF_DROP_TEXT,
        bg=COLOR_ONE,
        fg=COLOR_BW,
        relief="ridge",
        width=50,
        height=5,
        cursor="hand2",
    )
    ref_input_text = tk.Label(
        frame_left,
        text=REF_LABEL_TEXT,
        bg=COLOR_BACKGROUND,
        fg=COLOR_BW,
        relief="ridge",
        padx=5,
        borderwidth=border_fix,
    )
    ref_input_text.place(in_=ref_input, relx=0, rely=0, anchor="nw")
    ref_input.pack(fill="both", expand=True)
    sub_input = tk.Label(
        frame_right,
        text=SUB_DROP_TEXT,
        bg=COLOR_ONE,
        fg=COLOR_BW,
        relief="ridge",
        width=50,
        height=5,
        cursor="hand2",
    )
    sub_input_text = tk.Label(
        frame_right,
        text=SUB_LABEL_TEXT,
        bg=COLOR_BACKGROUND,
        fg=COLOR_BW,
        relief="ridge",
        padx=5,
        borderwidth=border_fix,
    )
    sub_input_text.place(in_=sub_input, relx=0, rely=0, anchor="nw")
    sub_input.pack(fill="both", expand=True)
    # Create listboxes
    listbox_left = tk.Listbox(
        frame_left,
        selectmode=tk.SINGLE,
        borderwidth=2,
        background=COLOR_WB,
        fg=COLOR_BW,
    )
    listbox_right = tk.Listbox(
        frame_right,
        selectmode=tk.SINGLE,
        borderwidth=2,
        background=COLOR_WB,
        fg=COLOR_BW,
    )

    def log_message_reference(message, msg_type=None):
        global current_log_type
        font_style = ("Arial", FONT_SIZE, "bold")
        if msg_type == "error":
            current_log_type = "error"
            color = COLOR_EIGHT
            bg_color = COLOR_SIX
        elif msg_type == "success":
            current_log_type = "success"
            color = COLOR_NINE
            bg_color = COLOR_TWO
        elif msg_type == "info":
            current_log_type = "info"
            color = COLOR_BW
            bg_color = COLOR_FOUR
        else:
            current_log_type = None
            color = COLOR_BW
            bg_color = COLOR_ONE
        label_message_reference.config(
            text=message, fg=color, bg=bg_color, font=font_style
        )
        if message:
            label_message_reference.grid(
                row=10, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew"
            )
        else:
            label_message_reference.grid_forget()
        label_message_reference.config(cursor="")
        label_message_reference.unbind("<Button-1>")
        label_message_reference.update_idletasks()

    label_message_reference = tk.Label(
        window, text="", bg=COLOR_BACKGROUND, fg=COLOR_BW, anchor="center"
    )
    label_message_reference.bind("<Configure>", update_wraplengt)
    label_message_reference.grid_remove()

    def on_enter(event):
        event.widget.configure(bg=COLOR_THREE)

    def on_leave(event):
        event.widget.configure(bg=COLOR_ONE, fg=COLOR_BW)

    def show_listbox(input_label, listbox, header_frame):
        input_label.pack_forget()
        header_frame.pack(fill="x", pady=(0, 5))
        listbox.pack(fill="both", expand=True)

    def clear_files(listbox, file_paths_list, header_frame, input_label):
        header_frame.pack_forget()
        listbox.pack_forget()
        input_label.pack(fill="both", expand=True)
        file_paths_list.clear()
        listbox.delete(0, tk.END)
        # Update both listboxes to refresh pairing colors
        sort_both_listboxes()
        log_message_reference("Files cleared.", "info")

    def extract_season_episode(filename):
        """
        Extract season and episode numbers from filename.
        Matches patterns like: S01E01, S1E1, 1x01, etc.
        """
        patterns = [
            r"[Ss](\d{1,2})[EeBb](\d{1,2})",  # S01E01, S1E1
            r"(\d{1,2})[xX](\d{1,2})",  # 1x01, 01x01, 1X01, 01X01
            r"\b(\d)(\d{2})\b",  # 101, 201
        ]
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                season, episode = match.groups()
                return int(season), int(episode)
        return None

    def format_display_text(filename):
        """Format filename with season/episode prefix"""
        se_info = extract_season_episode(filename)
        if se_info:
            season, episode = se_info
            return f"[S{season:02d}E{episode:02d}] {filename}"
        return filename

    def get_existing_season_episodes(file_paths):
        """Get set of (season, episode) tuples from existing files"""
        existing_se = set()
        for path in file_paths:
            filename = os.path.basename(path)
            se_info = extract_season_episode(filename)
            if se_info:
                existing_se.add(se_info)
        return existing_se

    def get_se_info_from_path(filepath):
        """Extract season-episode info from filepath"""
        filename = os.path.basename(filepath)
        return extract_season_episode(filename)

    def find_paired_files(left_paths, right_paths):
        """Returns indices of paired files in both lists"""
        paired_indices = []
        for i, left_path in enumerate(left_paths):
            left_se = get_se_info_from_path(left_path)
            if not left_se:
                continue
            for j, right_path in enumerate(right_paths):
                right_se = get_se_info_from_path(right_path)
                if left_se == right_se:
                    paired_indices.append((i, j))
                    break
        return paired_indices

    def update_listbox_colors(listbox_left, listbox_right, left_paths, right_paths):
        """Update background colors for paired items"""
        for lb in [listbox_left, listbox_right]:
            for i in range(lb.size()):
                lb.itemconfig(i, {"bg": COLOR_WB})
        paired = find_paired_files(left_paths, right_paths)
        for left_idx, right_idx in paired:
            listbox_left.itemconfig(left_idx, {"bg": COLOR_TWO})
            listbox_right.itemconfig(right_idx, {"bg": COLOR_TWO})

    def sort_listbox_with_pairs(listbox, file_paths_list, other_paths):
        """Sort listbox items with paired items first"""
        items = []
        paired_indices = {i for i, _ in find_paired_files(file_paths_list, other_paths)}
        for i in range(listbox.size()):
            is_paired = i in paired_indices
            items.append((i, listbox.get(i), file_paths_list[i], is_paired))
        # Sort: paired items first, then alphabetically within groups
        items.sort(key=lambda x: (-x[3], x[1]))  # -x[3] puts True (paired) before False
        listbox.delete(0, tk.END)
        file_paths_list.clear()
        for _, display_text, filepath, _ in items:
            listbox.insert(tk.END, display_text)
            file_paths_list.append(filepath)

    def sort_listbox(listbox, file_paths_list):
        """Sort listbox items considering pairs"""
        other_paths = (
            sub_file_paths if file_paths_list is ref_file_paths else ref_file_paths
        )
        sort_listbox_with_pairs(listbox, file_paths_list, other_paths)
        update_listbox_colors(
            listbox_left, listbox_right, ref_file_paths, sub_file_paths
        )

    def sort_both_listboxes():
        """Sort both listboxes keeping pairs aligned"""
        sort_listbox(listbox_left, ref_file_paths)
        sort_listbox(listbox_right, sub_file_paths)

    def process_files_reference(
        listbox,
        file_paths_list,
        filepaths=None,
        show_ui=True,
        input_label=None,
        header_frame=None,
    ):
        other_file_paths = (
            sub_file_paths if file_paths_list is ref_file_paths else ref_file_paths
        )
        other_file_paths_abs = [os.path.abspath(p) for p in other_file_paths]
        existing_paths_abs = [os.path.abspath(p) for p in file_paths_list]
        valid_extensions = (
            SUBTITLE_EXTENSIONS + VIDEO_EXTENSIONS
            if file_paths_list is ref_file_paths
            else SUBTITLE_EXTENSIONS
        )

        def validate_file(filepath):
            return any(filepath.lower().endswith(ext) for ext in valid_extensions)

        if filepaths is None:
            if file_paths_list is ref_file_paths:
                filetypes = [
                    (
                        VIDEO_OR_SUBTITLE_TEXT,
                        " ".join(
                            [
                                f"*{ext}"
                                for ext in SUBTITLE_EXTENSIONS + VIDEO_EXTENSIONS
                            ]
                        ),
                    )
                ]
            else:
                filetypes = [
                    (
                        SUBTITLE_FILES_TEXT,
                        " ".join([f"*{ext}" for ext in SUBTITLE_EXTENSIONS]),
                    )
                ]
            filepaths = filedialog.askopenfilenames(filetypes=filetypes)
            if not filepaths:
                log_message_reference(NO_FILES_SELECTED, "info")
                return
        existing_se = get_existing_season_episodes(file_paths_list)
        valid_files = []
        invalid_format_files = []
        se_duplicate_files = []
        for path in filepaths:
            if os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        full_path = os.path.join(root, file)
                        abs_path = os.path.abspath(full_path)
                        if validate_file(full_path):
                            se_info = extract_season_episode(file)
                            if se_info:
                                if se_info in existing_se:
                                    se_duplicate_files.append(file)
                                else:
                                    valid_files.append(abs_path)
                                    existing_se.add(se_info)
                            else:
                                invalid_format_files.append(file)
            elif validate_file(path):
                filename = os.path.basename(path)
                abs_path = os.path.abspath(path)
                se_info = extract_season_episode(filename)
                if se_info:
                    if se_info in existing_se:
                        se_duplicate_files.append(filename)
                    else:
                        valid_files.append(abs_path)
                        existing_se.add(se_info)
                else:
                    invalid_format_files.append(filename)

        if not valid_files and not se_duplicate_files:
            if invalid_format_files:
                log_message_reference(FILES_MUST_CONTAIN_PATTERNS, "error")
            else:
                log_message_reference(NO_VALID_SUBTITLE_FILES, "error")
            return
        if show_ui and input_label and header_frame:
            show_listbox(input_label, listbox, header_frame)
        added_files = 0
        skipped_files = 0
        duplicate_in_other = 0
        for filepath in valid_files:
            # Check against absolute paths
            if filepath not in existing_paths_abs:
                # Check against absolute paths in other listbox
                if filepath in other_file_paths_abs:
                    duplicate_in_other += 1
                    continue
                display_text = format_display_text(os.path.basename(filepath))
                listbox.insert(tk.END, display_text)
                file_paths_list.append(filepath)
                added_files += 1
            else:
                skipped_files += 1
        if added_files > 0:
            sort_listbox(listbox, file_paths_list)
        messages = []
        if added_files > 0:
            messages.append(ADDED_FILES_TEXT.format(added_files=added_files))
        if skipped_files > 0:
            messages.append(
                SKIPPED_DUPLICATE_FILES_TEXT.format(skipped_files=skipped_files)
            )
        if duplicate_in_other > 0:
            messages.append(
                SKIPPED_OTHER_LIST_FILES_TEXT.format(
                    duplicate_in_other=duplicate_in_other
                )
            )
        if se_duplicate_files:
            messages.append(
                SKIPPED_SEASON_EPISODE_DUPLICATES_TEXT.format(
                    len=len(se_duplicate_files)
                )
            )
        if invalid_format_files:
            messages.append(
                SKIPPED_INVALID_FORMAT_FILES_TEXT.format(len=len(invalid_format_files))
            )
        if messages:
            log_message_reference(". ".join(messages) + ".", "info")
        sort_both_listboxes()

    def on_file_drop(
        event, listbox, file_paths_list, input_label=None, header_frame=None
    ):
        filepaths = window.tk.splitlist(event.data)
        process_files_reference(
            listbox,
            file_paths_list,
            filepaths,
            bool(input_label and header_frame),
            input_label,
            header_frame,
        )

    def load_files(listbox, file_paths_list, type):
        if type == "reference":
            filetypes = [
                (
                    VIDEO_OR_SUBTITLE_TEXT,
                    " ".join(
                        [f"*{ext}" for ext in SUBTITLE_EXTENSIONS + VIDEO_EXTENSIONS]
                    ),
                )
            ]
        else:
            filetypes = [
                (
                    SUBTITLE_FILES_TEXT,
                    " ".join([f"*{ext}" for ext in SUBTITLE_EXTENSIONS]),
                )
            ]
        filepaths = filedialog.askopenfilenames(filetypes=filetypes)
        if filepaths:
            process_files_reference(
                listbox,
                file_paths_list,
                filepaths,
                show_ui=True,
                input_label=ref_input if listbox == listbox_left else sub_input,
                header_frame=ref_header if listbox == listbox_left else sub_header,
            )
        else:
            log_message_reference(NO_FILES_SELECTED, "info")

    def show_path_reference(listbox, file_paths_list):
        selected = listbox.curselection()
        if not selected:
            log_message_reference(NO_FILES_SELECTED_TO_SHOW_PATH, "info")
            return

        filepath = file_paths_list[selected[0]]
        normalized_path = os.path.normpath(filepath)

        result = open_directory(normalized_path, tab="ref")
        if result:
            text, error = result
            if error:
                log_message_reference(text, error)

    def on_right_click(event, menu):
        menu.post(event.x_root, event.y_root)

    def remove_selected_item(listbox, file_paths_list):
        selected = listbox.curselection()
        if selected:
            file_paths_list.pop(selected[0])
            listbox.delete(selected[0])
            sort_both_listboxes()
            log_message_reference(REMOVED_ITEM, "info")
        else:
            log_message_reference(NO_ITEM_SELECTED_TO_REMOVE, "info")

    def process_pairs():
        ref_files = ref_file_paths
        sub_files = sub_file_paths

        if not ref_files or not sub_files:
            log_message_reference(NO_SUBTITLE_PAIRS_TO_PROCESS, "error")
            return
        paired_indices = find_paired_files(ref_files, sub_files)
        if not paired_indices:
            log_message_reference(NO_MATCHING_SUBTITLE_PAIRS_FOUND, "error")
            return
        files_to_process = []
        for ref_idx, sub_idx in paired_indices:
            files_to_process.append(ref_files[ref_idx])
            files_to_process.append(sub_files[sub_idx])
        if files_to_process:
            process_files(files_to_process, reference_pairs=True)
            window.destroy()
        else:
            log_message_reference(NO_VALID_SUBTITLE_PAIRS_TO_PROCESS, "error")

    def cancel():
        window.destroy()

    cancel_btn = TkButton(
        frame_bottom,
        text=CANCEL_TEXT,
        command=cancel,
        padx=30,
        pady=10,
        fg=COLOR_WB,
        bg=DEFAULT_BUTTON_COLOR,
        activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
        activeforeground=COLOR_WB,
        relief=tk.RAISED,
        borderwidth=2,
        cursor="hand2",
        highlightthickness=0,
        takefocus=0,
        state="normal",
    )
    cancel_btn.pack(side="left", padx=(0, 5))
    process_btn = TkButton(
        frame_bottom,
        text=PROCESS_PAIRS,
        command=process_pairs,
        padx=10,
        pady=10,
        fg=COLOR_WB,
        bg=BUTTON_COLOR_BATCH,
        activebackground=BUTTON_COLOR_BATCH_ACTIVE,
        activeforeground=COLOR_WB,
        relief=tk.RAISED,
        borderwidth=2,
        cursor="hand2",
        highlightthickness=0,
        takefocus=0,
        state="normal",
    )
    process_btn.pack(side="left", fill="x", expand=True)
    ref_input.bind(
        "<Button-1>",
        lambda e: load_files(listbox_left, ref_file_paths, type="reference"),
    )
    ref_input.bind("<Enter>", on_enter)
    ref_input.bind("<Leave>", on_leave)
    ref_input.drop_target_register(DND_FILES)
    ref_input.dnd_bind(
        "<<Drop>>",
        lambda e: on_file_drop(e, listbox_left, ref_file_paths, ref_input, ref_header),
    )
    sub_input.bind(
        "<Button-1>",
        lambda e: load_files(listbox_right, sub_file_paths, type="subtitle"),
    )
    sub_input.bind("<Enter>", on_enter)
    sub_input.bind("<Leave>", on_leave)
    sub_input.drop_target_register(DND_FILES)
    sub_input.dnd_bind(
        "<<Drop>>",
        lambda e: on_file_drop(e, listbox_right, sub_file_paths, sub_input, sub_header),
    )
    listbox_left.drop_target_register(DND_FILES)
    listbox_left.dnd_bind(
        "<<Drop>>", lambda e: on_file_drop(e, listbox_left, ref_file_paths)
    )
    listbox_right.drop_target_register(DND_FILES)
    listbox_right.dnd_bind(
        "<<Drop>>", lambda e: on_file_drop(e, listbox_right, sub_file_paths)
    )
    listbox_left.bind(
        "<Delete>", lambda e: remove_selected_item(listbox_left, ref_file_paths)
    )
    listbox_right.bind(
        "<Delete>", lambda e: remove_selected_item(listbox_right, sub_file_paths)
    )
    if platform == "Darwin":
        listbox_left.bind("<Button-2>", lambda e: on_right_click(e, ref_options))
        listbox_right.bind("<Button-2>", lambda e: on_right_click(e, sub_options))
    else:
        listbox_left.bind("<Button-3>", lambda e: on_right_click(e, ref_options))
        listbox_right.bind("<Button-3>", lambda e: on_right_click(e, sub_options))
    window.mainloop()


# REFERENCE SUBTITLE / SUBTITLE PAIRING END


def on_batch_drop(event):
    filepaths = automatic_tab.tk.splitlist(event.data)
    process_files(filepaths)


def add_pair(multiple=False):
    while True:
        video_file = filedialog.askopenfilename(
            filetypes=[
                (
                    VIDEO_OR_SUBTITLE_TEXT,
                    " ".join(
                        [f"*{ext}" for ext in SUBTITLE_EXTENSIONS + VIDEO_EXTENSIONS]
                    ),
                )
            ]
        )
        if not video_file:
            if not multiple:
                log_message(SELECT_VIDEO, "error", tab="auto")
            break

        subtitle_file = filedialog.askopenfilename(
            filetypes=[
                (
                    SUBTITLE_FILES_TEXT,
                    " ".join([f"*{ext}" for ext in SUBTITLE_EXTENSIONS]),
                )
            ]
        )
        if not subtitle_file:
            log_message(SELECT_SUBTITLE, "error", tab="auto")
            break

        # Check if the same file is selected for both video and subtitle
        if os.path.normpath(video_file.lower()) == os.path.normpath(
            subtitle_file.lower()
        ):
            log_message(SAME_FILE_ERROR, "error", tab="auto")
            if not multiple:
                break
            else:
                continue

        video_name = os.path.basename(video_file)
        subtitle_name = os.path.basename(subtitle_file)
        pair = (
            os.path.normpath(video_file.lower()),
            os.path.normpath(subtitle_file.lower()),
        )

        # Check for duplicates based on normalized full file paths
        duplicate_found = False
        for parent in treeview.get_children():
            existing_video = treeview.item(parent, "values")
            if (
                existing_video
                and os.path.normpath(existing_video[0].lower()) == pair[0]
            ):
                subtitles = treeview.get_children(parent)
                for sub in subtitles:
                    existing_sub = treeview.item(sub, "values")
                    if (
                        existing_sub
                        and os.path.normpath(existing_sub[0].lower()) == pair[1]
                    ):
                        log_message(PAIR_ALREADY_EXISTS, "error", tab="auto")
                        duplicate_found = True
                        break
            if duplicate_found:
                break
        if duplicate_found:
            if not multiple:
                break
            else:
                continue

        parent_id = treeview.insert(
            "", "end", text=video_name, values=(video_file,), open=True
        )
        treeview.insert(parent_id, "end", text=subtitle_name, values=(subtitle_file,))
        treeview.item(parent_id, tags=("paired",))
        log_message(PAIR_ADDED, "info", tab="auto")
        # Handle UI updates
        batch_input.grid_remove()
        tree_frame.grid()

        if not multiple:
            break


def change_selected_item():
    selected_item = treeview.selection()
    if selected_item:
        parent_id = treeview.parent(selected_item)
        is_parent = not parent_id
        if is_parent:
            filetypes = [
                (
                    VIDEO_OR_SUBTITLE_TEXT,
                    " ".join(
                        [f"*{ext}" for ext in SUBTITLE_EXTENSIONS + VIDEO_EXTENSIONS]
                    ),
                )
            ]
        else:
            filetypes = [
                (
                    SUBTITLE_FILES_TEXT,
                    " ".join([f"*{ext}" for ext in SUBTITLE_EXTENSIONS]),
                )
            ]
        new_file = filedialog.askopenfilename(filetypes=filetypes)
        if new_file:
            new_file = os.path.normpath(new_file)
            new_name = os.path.basename(new_file)
            parent_values = treeview.item(parent_id, "values") if parent_id else None
            parent_file = os.path.normpath(parent_values[0]) if parent_values else ""
            current_item_values = treeview.item(selected_item, "values")
            current_file = (
                os.path.normpath(current_item_values[0]) if current_item_values else ""
            )
            item_type = treeview.item(selected_item, "text")
            # Don't proceed if the new file is the same as the current one
            if new_file.lower() == current_file.lower():
                return
            # Don't allow the same file as both parent and child
            if is_parent:
                # Check if any child has the same file
                children = treeview.get_children(selected_item)
                for child in children:
                    child_values = treeview.item(child, "values")
                    if child_values:
                        child_file = os.path.normpath(child_values[0])
                        if new_file.lower() == child_file.lower():
                            log_message(SAME_FILE_ERROR, "error", tab="auto")
                            return
            else:
                if new_file.lower() == parent_file.lower():
                    log_message(SAME_FILE_ERROR, "error", tab="auto")
                    return
            # Gather all existing pairs, excluding the current selection if it's a parent
            existing_pairs = set()
            for item in treeview.get_children():
                if is_parent and item == selected_item:
                    continue
                current_parent_values = treeview.item(item, "values")
                current_parent = (
                    os.path.normpath(current_parent_values[0]).lower()
                    if current_parent_values
                    else ""
                )
                children = treeview.get_children(item)
                for child in children:
                    child_values = treeview.item(child, "values")
                    if child_values:
                        child_file = os.path.normpath(child_values[0]).lower()
                        existing_pairs.add((current_parent, child_file))
            if is_parent:
                new_parent_file = new_file.lower()
                children = treeview.get_children(selected_item)
                for child in children:
                    child_values = treeview.item(child, "values")
                    if child_values:
                        child_file = os.path.normpath(child_values[0]).lower()
                        if (new_parent_file, child_file) in existing_pairs:
                            log_message(PAIR_ALREADY_EXISTS, "error", tab="auto")
                            return
            else:
                new_child_file = new_file.lower()
                new_parent_file = parent_file.lower() if parent_file else ""
                if (new_parent_file, new_child_file) in existing_pairs:
                    log_message(PAIR_ALREADY_EXISTS, "error", tab="auto")
                    return
            treeview.item(selected_item, text=new_name, values=(new_file,))
            # Update the tags of the parent item
            if parent_id:
                parent_text = treeview.item(parent_id, "text")
                if parent_text == NO_VIDEO:
                    treeview.item(parent_id, tags=("incomplete",))
                else:
                    treeview.item(parent_id, tags=("paired",))
            else:
                children = treeview.get_children(selected_item)
                valid_children = [
                    child
                    for child in children
                    if treeview.item(child, "text") != NO_SUBTITLE
                ]
                if not children or not valid_children:
                    treeview.item(selected_item, tags=("incomplete",))
                else:
                    treeview.item(selected_item, tags=("paired",))
            # Log appropriate messages
            if item_type.lower() == NO_SUBTITLE:
                log_message(SUBTITLE_ADDED, "info", tab="auto")
            elif item_type.lower() == NO_VIDEO:
                log_message(VIDEO_ADDED, "info", tab="auto")
            else:
                log_message(FILE_CHANGED, "info", tab="auto")
        else:
            log_message(SELECT_ITEM_TO_CHANGE, "error", tab="auto")


def remove_selected_item():
    selected_items = treeview.selection()
    if selected_items:
        for selected_item in selected_items:
            if treeview.exists(selected_item):
                parent_id = treeview.parent(selected_item)
                if parent_id:
                    treeview.delete(selected_item)
                    if not treeview.get_children(parent_id):
                        treeview.insert(
                            parent_id, "end", text=NO_SUBTITLE, values=("",)
                        )
                        treeview.item(parent_id, tags=("incomplete",))
                else:
                    treeview.delete(selected_item)
    else:
        log_message(SELECT_ITEM_TO_REMOVE, "error", tab="auto")


batch_input = tk.Label(
    automatic_tab,
    text=BATCH_INPUT_TEXT,
    bg=COLOR_ONE,
    fg=COLOR_BW,
    relief="ridge",
    width=40,
    height=5,
    cursor="hand2",
)
batch_input_text = tk.Label(
    automatic_tab,
    text=BATCH_INPUT_LABEL_TEXT,
    bg=COLOR_BACKGROUND,
    fg=COLOR_BW,
    relief="ridge",
    padx=5,
    borderwidth=border_fix,
)
batch_input_text.place(in_=batch_input, relx=0, rely=0, anchor="nw")
batch_input.bind(
    "<Button-1>", lambda event: options_menu.post(event.x_root, event.y_root)
)
if platform == "Darwin":
    batch_input.bind(
        "<Button-2>", lambda event: options_menu.post(event.x_root, event.y_root)
    )
else:
    batch_input.bind(
        "<Button-3>", lambda event: options_menu.post(event.x_root, event.y_root)
    )
batch_input.bind("<Configure>", update_wraplengt)
batch_input.bind("<Enter>", on_enter)
batch_input.bind("<Leave>", on_leave)
batch_input.drop_target_register(DND_FILES)
batch_input.dnd_bind("<<Drop>>", on_batch_drop)
# Create a frame for the Treeview and buttons
tree_frame = ttk.Frame(automatic_tab)
tree_frame.columnconfigure(0, weight=1)
tree_frame.rowconfigure(1, weight=1)
# Create a Treeview for displaying added files
treeview = ttk.Treeview(tree_frame, show="tree")
# Add tags and styles for paired and incomplete entries
treeview.tag_configure("paired", background=COLOR_TWO)
treeview.tag_configure("incomplete", background=COLOR_FIVE)
# Enable drag-and-drop on Treeview
treeview.drop_target_register(DND_FILES)
treeview.dnd_bind("<<Drop>>", on_batch_drop)


def on_double_click(event):
    change_selected_item()
    return "break"


def select_all(event):
    def select_all_children(item):
        children = treeview.get_children(item)
        for child in children:
            treeview.selection_add(child)
            select_all_children(child)

    for item in treeview.get_children():
        treeview.selection_add(item)
        select_all_children(item)


def delete_selected(event):
    remove_selected_item()


# Create a context menu
context_menu = tk.Menu(treeview, tearoff=0)
context_menu.add_command(label=CONTEXT_MENU_REMOVE, command=remove_selected_item)
context_menu.add_command(label=CONTEXT_MENU_CHANGE, command=change_selected_item)
context_menu.add_separator()
context_menu.add_command(label=CONTEXT_MENU_ADD_PAIR, command=add_pair)
context_menu.add_command(
    label=CONTEXT_MENU_CLEAR_ALL,
    command=lambda: treeview.delete(*treeview.get_children()),
)


# Function to show the context menu
def show_path(tab="both"):
    selected_item = treeview.selection()
    if not selected_item:
        return

    item_values = treeview.item(selected_item, "values")
    if not item_values or not item_values[0]:
        return
    path = os.path.normpath(item_values[0])
    open_directory(path, tab)


def show_context_menu(event):
    # Clear previous dynamic menu items
    context_menu.delete(0, tk.END)
    # Select the item under the cursor
    item = treeview.identify_row(event.y)
    if item:
        treeview.selection_set(item)
        item_values = treeview.item(item, "values")
        if item_values and item_values[0]:
            context_menu.add_command(
                label=CONTEXT_MENU_SHOW_PATH, command=lambda: show_path(tab="auto")
            )
            context_menu.add_separator()
    context_menu.add_command(label=CONTEXT_MENU_REMOVE, command=remove_selected_item)
    context_menu.add_command(label=CONTEXT_MENU_CHANGE, command=change_selected_item)
    context_menu.add_separator()  # Add a separator
    context_menu.add_command(label=CONTEXT_MENU_ADD_PAIR, command=add_pair)

    def clear_all():
        treeview.delete(*treeview.get_children())
        tree_frame.grid_remove()
        batch_input.grid()
        log_message("", "info", tab="auto")

    context_menu.add_command(label=CONTEXT_MENU_CLEAR_ALL, command=clear_all)
    context_menu.post(event.x_root, event.y_root)


# Bind the right-click event to the Treeview to show the context menu
if platform == "Darwin":
    treeview.bind("<Button-2>", show_context_menu)
else:
    treeview.bind("<Button-3>", show_context_menu)
# Bind the key events to the treeview
treeview.bind("<Control-a>", select_all)
treeview.bind("<Delete>", delete_selected)
treeview.bind("<Double-1>", on_double_click)
# Create buttons for adding, changing, and removing items
button_change_item = TkButton(
    tree_frame,
    text=CONTEXT_MENU_CHANGE,
    command=change_selected_item,
    font=f"Arial {FONT_SIZE} bold",
    padx=4,
    pady=0,
    fg=COLOR_WB,
    bg=DEFAULT_BUTTON_COLOR,
    activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
    activeforeground=COLOR_WB,
    relief=tk.RAISED,
    borderwidth=2,
    cursor="hand2",
    highlightthickness=0,
    takefocus=0,
    state="normal",
)
button_remove_item = TkButton(
    tree_frame,
    text=CONTEXT_MENU_REMOVE,
    command=remove_selected_item,
    font=f"Arial {FONT_SIZE} bold",
    padx=4,
    pady=0,
    fg=COLOR_WB,
    bg=DEFAULT_BUTTON_COLOR,
    activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
    activeforeground=COLOR_WB,
    relief=tk.RAISED,
    borderwidth=2,
    cursor="hand2",
    highlightthickness=0,
    takefocus=0,
    state="normal",
)
style = ttk.Style()
style.configure(
    "Treeview",
    rowheight=25,
    background=COLOR_ZERO,
    fieldbackground=COLOR_WB,
    foreground=COLOR_BW,
)
style.map("Treeview", background=[("selected", TREEVIEW_SELECTED_COLOR)])
# Replace the "Add Pair" button with a Menubutton
button_addfile = tk.Menubutton(
    tree_frame,
    text=BUTTON_ADD_FILES,
    font=f"Arial {FONT_SIZE} bold",
    padx=4,
    pady=3,
    fg=COLOR_WB,
    bg=DEFAULT_BUTTON_COLOR,
    activebackground=DEFAULT_BUTTON_COLOR,
    activeforeground=COLOR_WB,
    relief=tk.RAISED,
    borderwidth=2,
    cursor="hand2",
)
options_menu = tk.Menu(button_addfile, tearoff=0)
button_addfile.config(menu=options_menu)
options_menu.add_command(label=CONTEXT_MENU_ADD_PAIR, command=add_pair)
options_menu.add_command(
    label=CONTEXT_MENU_ADD_PAIRS, command=lambda: add_pair(multiple=True)
)
options_menu.add_command(label=MENU_ADD_FOLDER, command=select_folder)
options_menu.add_command(label=MENU_ADD_MULTIPLE_FILES, command=browse_batch)
options_menu.add_command(
    label=MENU_ADD_REFERENCE_SUBITLE_SUBTITLE_PAIRIS,
    command=reference_subtitle_subtitle_pairs,
)
# Update the grid layout
button_addfile.grid(row=0, column=0, padx=(0, 2.5), pady=5, sticky="ew")
button_change_item.grid(row=0, column=1, padx=(2.5, 2.5), pady=5, sticky="ew")
button_remove_item.grid(row=0, column=2, padx=(2.5, 0), pady=5, sticky="ew")
treeview.grid(row=1, column=0, columnspan=3, padx=(0, 20), pady=(5, 0), sticky="nsew")
style.configure(
    "Vertical.TScrollbar",
    background=COLOR_BACKGROUND,
    troughcolor=COLOR_ONE,
    arrowcolor=COLOR_BW,
)
# Create a vertical scrollbar for the Treeview
treeview_scrollbar = ttk.Scrollbar(
    tree_frame, orient="vertical", command=treeview.yview, style="Vertical.TScrollbar"
)
treeview_scrollbar.grid(row=1, column=2, sticky="nes", pady=(5, 0))
treeview.configure(yscrollcommand=treeview_scrollbar.set)
tree_frame.grid(
    row=0, column=0, padx=10, pady=(5, 0), sticky="nsew", rowspan=2, columnspan=2
)
tree_frame.grid_remove()
batch_input.grid_remove()


# Start batch mode end
# Start automatic sync begin
def remove_subtitle_input():
    subtitle_input.config(text=SUBTITLE_INPUT_TEXT, bg=COLOR_ONE, fg=COLOR_BW)
    del subtitle_input.tooltip_text
    remove_subtitle_button.grid_remove()


def remove_video_input():
    video_input.config(text=VIDEO_INPUT_TEXT, bg=COLOR_ONE, fg=COLOR_BW)
    del video_input.tooltip_text
    remove_video_button.grid_remove()


def browse_subtitle(event=None):
    subtitle_file_auto = filedialog.askopenfilename(
        filetypes=[
            (SUBTITLE_FILES_TEXT, " ".join([f"*{ext}" for ext in SUBTITLE_EXTENSIONS]))
        ]
    )
    if subtitle_file_auto:
        subtitle_input.config(text=subtitle_file_auto)
        subtitle_input.tooltip_text = subtitle_file_auto
        subtitle_input.config(bg=COLOR_TWO, fg=COLOR_BW)
        remove_subtitle_button.grid(
            row=1, column=1, padx=(0, 12), pady=(2, 0), sticky="ne"
        )
        log_message("", "info", tab="auto")
    else:
        if subtitle_file_auto != "":
            log_message(SELECT_SUBTITLE, "error", tab="auto")
            subtitle_input.config(bg=COLOR_ONE, fg=COLOR_BW)


def browse_video(event=None):
    video_file = filedialog.askopenfilename(
        filetypes=[
            (
                VIDEO_OR_SUBTITLE_TEXT,
                " ".join([f"*{ext}" for ext in SUBTITLE_EXTENSIONS + VIDEO_EXTENSIONS]),
            )
        ]
    )
    if video_file:
        video_input.config(text=video_file)
        video_input.tooltip_text = video_file
        video_input.config(bg=COLOR_TWO, fg=COLOR_BW)
        remove_video_button.grid(
            row=0, column=1, padx=(0, 12), pady=(12, 0), sticky="ne"
        )
        log_message("", "info", tab="auto")
    else:
        if video_file != "":
            log_message(SELECT_VIDEO_OR_SUBTITLE, "error", tab="auto")
            video_input.config(bg=COLOR_ONE, fg=COLOR_BW)


def on_video_drop(event):
    files = event.widget.tk.splitlist(event.data)
    if len(files) == 2:
        video_file = None
        subtitle_file = None
        for file in files:
            if file.lower().endswith(tuple(VIDEO_EXTENSIONS)):
                video_file = file
            elif file.lower().endswith(tuple(SUBTITLE_EXTENSIONS)):
                subtitle_file = file
        if video_file and subtitle_file:
            video_input.config(text=video_file)
            video_input.tooltip_text = video_file
            video_input.config(bg=COLOR_TWO, fg=COLOR_BW)
            subtitle_input.config(text=subtitle_file)
            subtitle_input.tooltip_text = subtitle_file
            subtitle_input.config(bg=COLOR_TWO, fg=COLOR_BW)
            remove_video_button.grid(
                row=0, column=1, padx=(0, 12), pady=(12, 0), sticky="ne"
            )
            remove_subtitle_button.grid(
                row=1, column=1, padx=(0, 12), pady=(2, 0), sticky="ne"
            )
            log_message("", "info", tab="auto")
            return
    elif len(files) != 1:
        log_message(DROP_VIDEO_OR_SUBTITLE, "error", tab="auto")
        return
    filepath = files[0]
    if filepath.lower().endswith(tuple(SUBTITLE_EXTENSIONS + VIDEO_EXTENSIONS)):
        video_input.config(text=filepath)
        video_input.tooltip_text = filepath
        video_input.config(bg=COLOR_TWO, fg=COLOR_BW)
        remove_video_button.grid(
            row=0, column=1, padx=(0, 12), pady=(12, 0), sticky="ne"
        )
        log_message("", "info", tab="auto")
    else:
        log_message(DROP_VIDEO_OR_SUBTITLE, "error", tab="auto")


def on_subtitle_drop(event):
    files = event.widget.tk.splitlist(event.data)
    if len(files) == 2:
        video_file = None
        subtitle_file = None
        for file in files:
            if file.lower().endswith(tuple(VIDEO_EXTENSIONS)):
                video_file = file
            elif file.lower().endswith(tuple(SUBTITLE_EXTENSIONS)):
                subtitle_file = file
        if video_file and subtitle_file:
            video_input.config(text=video_file)
            video_input.tooltip_text = video_file
            video_input.config(bg=COLOR_TWO, fg=COLOR_BW)
            subtitle_input.config(text=subtitle_file)
            subtitle_input.tooltip_text = subtitle_file
            subtitle_input.config(bg=COLOR_TWO, fg=COLOR_BW)
            remove_video_button.grid(
                row=0, column=1, padx=(0, 12), pady=(12, 0), sticky="ne"
            )
            remove_subtitle_button.grid(
                row=1, column=1, padx=(0, 12), pady=(2, 0), sticky="ne"
            )
            log_message("", "info", tab="auto")
            return
    elif len(files) != 1:
        log_message(DROP_SINGLE_SUBTITLE_PAIR, "error", tab="auto")
        return
    filepath = files[0]
    if filepath.lower().endswith(tuple(SUBTITLE_EXTENSIONS)):
        subtitle_input.config(text=filepath)
        subtitle_input.tooltip_text = filepath
        subtitle_input.config(bg=COLOR_TWO, fg=COLOR_BW)
        remove_subtitle_button.grid(
            row=1, column=1, padx=(0, 11), pady=(2, 0), sticky="ne"
        )
        log_message("", "info", tab="auto")
    else:
        log_message(DROP_SUBTITLE_FILE, "error", tab="auto")


process = None


def shorten_progress_bar(line):
    """Shorten the progress bar to 30 characters"""
    start = line.find("[")
    end = line.find("]", start)
    if start != -1 and end != -1:
        progress_bar = line[start : end + 1]
        percent_start = line.find(" ", end) + 1
        percent_end = line.find("%", percent_start)
        percent = float(line[percent_start:percent_end])
        width = 30  # New shorter width
        filled = int(width * percent / 100)
        if filled < width:
            new_progress_bar = (
                "[" + "=" * (filled - 1) + ">" + "-" * (width - filled) + "]"
            )
        else:
            new_progress_bar = "[" + "=" * width + "]"
        return line[:start] + new_progress_bar + line[end + 1 :]
    return line


def start_automatic_sync():
    global process, subtitle_file, video_file, output_subtitle_file, cancel_flag, log_window
    cancel_flag = False  # Add a flag to check if the process is cancelled
    sync_tool = sync_tool_var_auto.get()
    if sync_tool == SYNC_TOOL_ALASS:
        SUPPORTED_SUBTITLE_EXTENSIONS = ALASS_SUPPORTED_EXTENSIONS
    elif sync_tool == "ffsubsync":
        SUPPORTED_SUBTITLE_EXTENSIONS = FFSUBSYNC_SUPPORTED_EXTENSIONS
    subtitle_tooltip_text = getattr(subtitle_input, "tooltip_text", None)
    video_tooltip_text = getattr(video_input, "tooltip_text", None)
    if subtitle_tooltip_text:
        subtitle_file = os.path.abspath(subtitle_tooltip_text)
    else:
        subtitle_file = None
    if video_tooltip_text:
        video_file = os.path.abspath(video_tooltip_text)
    else:
        video_file = None
    if not subtitle_file and not video_file:
        log_message(SELECT_BOTH_FILES, "error", tab="auto")
        return
    if subtitle_file == video_file:
        log_message(SELECT_DIFFERENT_FILES, "error", tab="auto")
        return
    if not subtitle_file:
        log_message(SELECT_SUBTITLE, "error", tab="auto")
        return
    if not video_file:
        log_message(SELECT_VIDEO_OR_SUBTITLE, "error", tab="auto")
        return
    if not os.path.exists(subtitle_file):
        log_message(SUBTITLE_FILE_NOT_EXIST, "error", tab="auto")
        return
    if not os.path.exists(video_file):
        log_message(VIDEO_FILE_NOT_EXIST, "error", tab="auto")
        return
    action = action_var_auto.get()
    if action == OPTION_SAVE_NEXT_TO_VIDEO:
        output_dir = os.path.dirname(video_file)
    elif action == OPTION_SAVE_TO_DESKTOP:
        desktop_path = get_desktop_path()
        output_dir = desktop_path
    elif action == OPTION_REPLACE_ORIGINAL_SUBTITLE:
        output_subtitle_file = subtitle_file
        output_dir = os.path.dirname(subtitle_file)
    elif action == OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME:
        output_dir = os.path.dirname(video_file)
        base_name, ext = os.path.splitext(os.path.basename(subtitle_file))
        if not ext.lower() in SUPPORTED_SUBTITLE_EXTENSIONS:
            ext = ".srt"
        output_subtitle_file = os.path.join(output_dir, f"{base_name}{ext}")
    elif action == OPTION_SELECT_DESTINATION_FOLDER:
        if "selected_destination_folder" in globals() and os.path.exists(
            selected_destination_folder
        ):
            output_dir = selected_destination_folder
        else:
            log_message(TEXT_DESTINATION_FOLDER_DOES_NOT_EXIST, "error", tab="auto")
            return
    else:
        output_dir = os.path.dirname(subtitle_file)
    if action != OPTION_REPLACE_ORIGINAL_SUBTITLE:
        if action == OPTION_SAVE_NEXT_TO_VIDEO:
            base_name, ext = os.path.splitext(os.path.basename(subtitle_file))
        elif action == OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME:
            base_name = os.path.splitext(os.path.basename(video_file))[0]
            ext = os.path.splitext(os.path.basename(subtitle_file))[1]
        else:
            base_name, ext = os.path.splitext(os.path.basename(subtitle_file))
        if not ext.lower() in SUPPORTED_SUBTITLE_EXTENSIONS:
            ext = ".srt"
        if action == OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME:
            filename = f"{base_name}{ext}"
            output_subtitle_file = os.path.join(output_dir, filename)
        else:
            prefix = subtitle_prefix if add_prefix else ""
            filename = f"{prefix}{base_name}{ext}"
            output_subtitle_file = os.path.join(output_dir, filename)
        add_suffix = True

        if (
            action_var_auto.get() == OPTION_REPLACE_ORIGINAL_SUBTITLE
            or action_var_auto.get() == OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME
        ):
            add_suffix = False
        suffix = 2
        prefix = subtitle_prefix if add_prefix else ""
        while os.path.exists(output_subtitle_file) and add_suffix is True:
            filename = f"{prefix}{base_name}_{suffix}{ext}"
            output_subtitle_file = os.path.join(output_dir, filename)
            suffix += 1

    def cancel_automatic_sync():
        global process, cancel_flag
        cancel_flag = True
        if process:
            try:
                kill_process_tree(process.pid)
                process = None
                log_message(AUTO_SYNC_CANCELLED, "error", tab="auto")
            except Exception as e:
                log_message(
                    ERROR_PROCESS_TERMINATION.format(error_message=str(e)),
                    "error",
                    tab="auto",
                )
        else:
            log_message(NO_SYNC_PROCESS, "error", tab="auto")
        restore_window()

    def cancel_process_on_window_close():
        if process:
            cancel_automatic_sync()
        root.destroy()
        os._exit(0)

    root.protocol("WM_DELETE_WINDOW", cancel_process_on_window_close)

    def restore_window():
        video_input.grid()
        subtitle_input.grid()
        if getattr(video_input, "tooltip_text", None):
            remove_video_button.grid(
                row=0, column=1, padx=(0, 12), pady=(12, 0), sticky="ne"
            )
        if getattr(subtitle_input, "tooltip_text", None):
            remove_subtitle_button.grid(
                row=1, column=1, padx=(0, 12), pady=(2, 0), sticky="ne"
            )
        action_menu_auto.grid()
        sync_frame.grid()
        button_start_automatic_sync.grid()
        batch_mode_button.grid()
        if sync_tool_var_auto.get() == SYNC_TOOL_ALASS:
            alass_split_penalty_slider.grid()
            alass_disable_fps_guessing.grid()
            alass_speed_optimization.grid()
            ffsubsync_option_gss.grid_remove()
            vad_frame.grid_remove()
            ffsubsync_option_framerate.grid_remove()
        elif sync_tool_var_auto.get() == SYNC_TOOL_FFSUBSYNC:
            ffsubsync_option_gss.grid()
            vad_frame.grid()
            ffsubsync_option_framerate.grid()
            alass_split_penalty_slider.grid_remove()
            alass_disable_fps_guessing.grid_remove()
            alass_speed_optimization.grid_remove()
        log_window.grid_remove()
        progress_bar.grid_remove()
        button_go_back.grid_remove()
        button_generate_again.grid_remove()
        button_cancel_automatic_sync.grid_remove()
        automatic_tab.columnconfigure(0, weight=0)
        automatic_tab.rowconfigure(1, weight=1)
        root.update_idletasks()

    def generate_again():
        subtitle_input.config(text=SUBTITLE_INPUT_TEXT, bg=COLOR_ONE, fg=COLOR_BW)
        del subtitle_input.tooltip_text
        video_input.config(text=VIDEO_INPUT_TEXT, bg=COLOR_ONE, fg=COLOR_BW)
        del video_input.tooltip_text
        subtitle_input.grid()
        video_input.grid()
        remove_subtitle_button.grid_remove()
        remove_video_button.grid_remove()
        action_menu_auto.grid()
        sync_frame.grid()
        button_start_automatic_sync.grid()
        batch_mode_button.grid()
        if sync_tool_var_auto.get() == SYNC_TOOL_ALASS:
            alass_split_penalty_slider.grid()
            alass_disable_fps_guessing.grid()
            alass_speed_optimization.grid()
            ffsubsync_option_gss.grid_remove()
            vad_frame.grid_remove()
            ffsubsync_option_framerate.grid_remove()
        elif sync_tool_var_auto.get() == SYNC_TOOL_FFSUBSYNC:
            ffsubsync_option_gss.grid()
            vad_frame.grid()
            ffsubsync_option_framerate.grid()
            alass_split_penalty_slider.grid_remove()
            alass_disable_fps_guessing.grid_remove()
            alass_speed_optimization.grid_remove()
        log_window.grid_remove()
        progress_bar.grid_remove()
        button_go_back.grid_remove()
        button_generate_again.grid_remove()
        button_cancel_automatic_sync.grid_remove()
        label_message_auto.grid_remove()
        automatic_tab.columnconfigure(0, weight=0)
        root.update_idletasks()

    def update_progress_auto(progress_bar, value):
        adjusted_value = min(97, max(1, value))
        progress_bar["value"] = adjusted_value

    def build_cmd():
        if sync_tool == SYNC_TOOL_FFSUBSYNC:
            cmd = f'"{CALL_FFSUBSYNC}" "{video_file}" -i "{subtitle_file}" -o "{output_subtitle_file}"'
            if not video_file.lower().endswith(tuple(SUBTITLE_EXTENSIONS)):
                if vad_option_map.get(ffsubsync_option_vad_var.get(), "") != "default":
                    cmd += f" --vad={vad_option_map.get(ffsubsync_option_vad_var.get(), '')}"
            if ffsubsync_option_framerate_var.get():
                cmd += " --no-fix-framerate"
            if ffsubsync_option_gss_var.get():
                cmd += " --gss"
            if additional_ffsubsync_args:
                cmd += f" {additional_ffsubsync_args}"
        elif sync_tool == SYNC_TOOL_ALASS:
            if split_penalty == -1:
                cmd = f'"{CALL_ALASS}" "{video_file}" "{subtitle_file}" "{output_subtitle_file}" --no-split'
            else:
                cmd = f'"{CALL_ALASS}" "{video_file}" "{subtitle_file}" "{output_subtitle_file}" --split-penalty={split_penalty}'
            if alass_speed_optimization_var.get():
                cmd += " --speed-optimization 0"
            if alass_disable_fps_guessing_var.get():
                cmd += " --disable-fps-guessing"
            if additional_alass_args:
                cmd += f" {additional_alass_args}"
        else:
            log_window.insert(tk.END, f"{INVALID_SYNC_TOOL_SELECTED}\n")
            return None
        return cmd

    def execute_cmd(cmd):
        global process, progress_line_number, split_penalty
        split_penalty = alass_split_penalty_var.get()
        process = create_process(cmd)
        progress_bar["value"] = 1
        if sync_tool == SYNC_TOOL_FFSUBSYNC:
            if video_file.lower().endswith(tuple(SUBTITLE_EXTENSIONS)):
                log_window.insert(tk.END, f"{USING_REFERENCE_SUBTITLE}\n")
            else:
                log_window.insert(tk.END, f"{USING_VIDEO_FOR_SYNC}\n")
                if vad_option_map.get(ffsubsync_option_vad_var.get(), "") != "default":
                    log_window.insert(
                        tk.END,
                        f"{VOICE_ACTIVITY_DETECTOR}: {vad_option_map.get(ffsubsync_option_vad_var.get(), '')}\n",
                    )
            if ffsubsync_option_framerate_var.get():
                log_window.insert(tk.END, f"{ENABLED_NO_FIX_FRAMERATE}\n")
            if ffsubsync_option_gss_var.get():
                log_window.insert(tk.END, f"{ENABLED_GSS}\n")
            if additional_ffsubsync_args:
                log_window.insert(
                    tk.END,
                    f"{ADDITIONAL_ARGS_ADDED.format(additional_args=additional_ffsubsync_args)}\n",
                )
        elif sync_tool == SYNC_TOOL_ALASS:
            if split_penalty == -1:
                log_window.insert(tk.END, f"{SPLIT_PENALTY_ZERO}\n")
            else:
                log_window.insert(
                    tk.END, f"{SPLIT_PENALTY_SET.format(split_penalty=split_penalty)}\n"
                )
            if alass_speed_optimization_var.get():
                log_window.insert(tk.END, f"{ALASS_SPEED_OPTIMIZATION_LOG}\n")
            if alass_disable_fps_guessing_var.get():
                log_window.insert(tk.END, f"{ALASS_DISABLE_FPS_GUESSING_LOG}\n")
            if additional_alass_args:
                log_window.insert(
                    tk.END,
                    f"{ADDITIONAL_ARGS_ADDED.format(additional_args=additional_alass_args)}\n",
                )
        log_window.insert(tk.END, f"{SYNCING_STARTED}\n")
        progress_line_number = log_window.index(tk.END).split(".", maxsplit=1)[0]
        decoding_error_occurred = False
        previous_line_had_percentage = False
        for output in process.stdout:
            if cancel_flag:  # Check if the process is cancelled
                break
            if sync_tool == SYNC_TOOL_FFSUBSYNC:
                # Remove timestamps
                output = re.sub(r"\[\d{2}:\d{2}:\d{2}\]\s*", "", output)
                # Strip leading spaces
                output = output.lstrip()
                # If no "INFO|WARNING|CRITICAL|ERROR" in output, add 9 spaces
                if not re.search(r"\b(INFO|WARNING|CRITICAL|ERROR)\b", output):
                    output = "         " + output
                output = " " + output
                match_percentage = re.search(r"\b(\d+(\.\d+)?)%\|", output)
            elif sync_tool == SYNC_TOOL_ALASS:
                # Modify ALASS output to show shorter progress bar
                if "[" in output and "]" in output:
                    output = shorten_progress_bar(output)
                match_percentage = re.search(r"\[\s*=\s*\]\s*(\d+\.\d+)\s*%", output)
                if not match_percentage:
                    match_percentage = re.search(
                        r"\d+\s*/\s*\d+\s*\[.*\]\s*(\d+\.\d+)\s*%", output
                    )
            if match_percentage:
                percentage = float(match_percentage.group(1))
                root.after(10, update_progress_auto, progress_bar, percentage)
                if previous_line_had_percentage:
                    log_window.replace("end-2l", "end-1l", output)
                else:
                    log_window.insert(tk.END, output)
                previous_line_had_percentage = True
            else:
                log_window.insert(tk.END, output)
                previous_line_had_percentage = False
            if (
                "error while decoding subtitle from bytes to string" in output
                and sync_tool == SYNC_TOOL_ALASS
            ):
                decoding_error_occurred = True

        if process is not None and not cancel_flag:
            process.wait()
            if process.returncode == 0:  # Check if the process finished successfully
                if (
                    "error" in output.lower()
                    or not os.path.exists(output_subtitle_file)
                ) and not decoding_error_occurred:
                    return 1, decoding_error_occurred
                return process.returncode, decoding_error_occurred
            return process.returncode, decoding_error_occurred
        return 1, decoding_error_occurred

    def run_subprocess():
        global subtitle_file, video_file, cmd, output_subtitle_file, split_penalty, decoding_error_occurred
        split_penalty = alass_split_penalty_var.get()
        video_file_converted = None
        subtitle_file_converted = None
        closest_subtitle = None
        if (
            action_var_auto.get() == OPTION_REPLACE_ORIGINAL_SUBTITLE
            or action_var_auto.get() == OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME
        ):
            # if there is a file with the same name as the output_subtitle_file, create a backup
            if (
                os.path.exists(output_subtitle_file)
                and backup_subtitles_before_overwriting
            ):
                new_output_subtitle_file = create_backup(output_subtitle_file)
                log_window.insert(
                    tk.END,
                    f"{BACKUP_CREATED.format(output_subtitle_file=new_output_subtitle_file)}\n",
                )
        unsupported_extensions = [
            ext
            for ext in SUBTITLE_EXTENSIONS
            if ext not in SUPPORTED_SUBTITLE_EXTENSIONS
        ]
        try:
            if not output_subtitle_file.lower().endswith(
                tuple(SUPPORTED_SUBTITLE_EXTENSIONS)
            ):
                output_subtitle_file = output_subtitle_file.rsplit(".", 1)[0] + ".srt"
            if subtitle_file.lower().endswith(tuple(unsupported_extensions)):
                subtitle_file_converted = convert_to_srt(
                    subtitle_file, output_dir, log_window
                )
                if subtitle_file_converted:
                    subtitle_file = subtitle_file_converted
            if sync_tool == SYNC_TOOL_ALASS:
                # if it is a video file, extract subtitle streams
                if (
                    video_file.lower().endswith(tuple(VIDEO_EXTENSIONS))
                    and check_video_for_subtitle_stream_in_alass
                ):
                    log_window.insert(tk.END, CHECKING_SUBTITLE_STREAMS + "\n")
                    closest_subtitle = extract_subtitles(
                        video_file, subtitle_file, output_dir, log_window
                    )
                    if closest_subtitle:
                        video_file = closest_subtitle
            if video_file.lower().endswith(tuple(unsupported_extensions)):
                video_file_converted = convert_to_srt(
                    video_file, output_dir, log_window
                )
                if video_file_converted:
                    video_file = video_file_converted
            cmd = build_cmd()
            if cmd is None:
                return
            returncode, decoding_error_occurred = execute_cmd(cmd)
            # alass specific code
            if sync_tool == SYNC_TOOL_ALASS:
                encoding_ref = None
                encoding_inc = detect_encoding(subtitle_file)
                # if encoding_inc is not inside enc_list, select the closest encoding in enc_list
                if encoding_inc not in enc_list:
                    closest_encoding = find_closest_encoding(encoding_inc)
                    encoding_inc = closest_encoding
                # if decoding_error_occurred, retry with detected encodings
                if returncode != 0 and decoding_error_occurred:
                    log_window.insert(tk.END, "\n" + RETRY_ENCODING_MSG + "\n\n")
                    if video_file.lower().endswith(tuple(SUBTITLE_EXTENSIONS)):
                        encoding_ref = detect_encoding(video_file)
                        # if encoding_ref is not inside enc_list, select the closest encoding in enc_list
                        if encoding_ref not in enc_list:
                            closest_encoding = find_closest_encoding(encoding_ref)
                            encoding_ref = closest_encoding
                        cmd += f" --encoding-ref={encoding_ref}"
                    cmd += f" --encoding-inc={encoding_inc}"
                    returncode, decoding_error_occurred = execute_cmd(cmd)
                synced_subtitle_encoding = detect_encoding(output_subtitle_file)
                # If the encoding of synced subtitle is not the same as encoding_inc, change it
                if synced_subtitle_encoding != encoding_inc:
                    change_encoding_msg = CHANGING_ENCODING_MSG.format(
                        synced_subtitle_encoding=synced_subtitle_encoding,
                        encoding_inc=encoding_inc,
                    )
                    log_window.insert(tk.END, "\n" + change_encoding_msg + "\n")
                    try:
                        with open(
                            output_subtitle_file,
                            "r",
                            encoding=synced_subtitle_encoding,
                            errors="replace",
                        ) as f:
                            content = f.read()
                        with open(
                            output_subtitle_file,
                            "w",
                            encoding=encoding_inc,
                            errors="replace",
                        ) as f:
                            f.write(content)
                        log_window.insert(tk.END, "\n" + ENCODING_CHANGED_MSG + "\n")
                    except Exception as e:
                        error_msg = ERROR_CHANGING_ENCODING_MSG.format(
                            error_message=str(e)
                        )
                        log_window.insert(tk.END, "\n" + error_msg + "\n")
                # if keep_extracted_subtitles is False, delete the extracted subtitle folder which is the folder of closest_subtitle.
                if not keep_extracted_subtitles and closest_subtitle:
                    log_window.insert(
                        tk.END, f"\n{DELETING_EXTRACTED_SUBTITLE_FOLDER}\n"
                    )
                    shutil.rmtree(os.path.dirname(closest_subtitle))
                # if video_file_converted or subtitle_file_converted is not None and keep_converted_subtitles is False, delete the converted files
                if not keep_converted_subtitles:
                    if video_file_converted:
                        log_window.insert(tk.END, f"\n{DELETING_CONVERTED_SUBTITLE}\n")
                        os.remove(video_file_converted)
                    if subtitle_file_converted:
                        log_window.insert(tk.END, f"\n{DELETING_CONVERTED_SUBTITLE}\n")
                        os.remove(subtitle_file_converted)
            if cancel_flag:
                return
            if process:
                process.wait()
            if returncode == 0:
                log_window.insert(
                    tk.END,
                    f"\n{SYNC_SUCCESS_MESSAGE.format(output_subtitle_file=output_subtitle_file)}\n",
                )
                log_message(
                    SYNC_SUCCESS_MESSAGE.format(
                        output_subtitle_file=output_subtitle_file
                    ),
                    "success",
                    output_subtitle_file,
                    tab="auto",
                )
            else:
                log_message(
                    SYNC_ERROR_OCCURRED, "error", output_subtitle_file, tab="auto"
                )

        except Exception as e:
            if not cancel_flag:
                error_msg_normal = f"{ERROR_OCCURRED}{str(e)}\n"
                if (
                    sync_tool == SYNC_TOOL_ALASS
                    and "could not convert string to float" in str(e)
                ):
                    log_window.insert(tk.END, f"\n{ERROR_OCCURRED}{str(e)}\n")
                    error_msg_normal = ERROR_DECODING_SUBTITLE
                log_message(error_msg_normal, "error", tab="auto")

        finally:
            if not cancel_flag:
                button_cancel_automatic_sync.grid_remove()
                log_window.grid(pady=(10, 10), rowspan=2)
                button_go_back.grid()
                button_generate_again.grid()
                log_window.insert(tk.END, f"\n{SYNCING_ENDED}\n")
                progress_bar.grid_remove()
                automatic_tab.rowconfigure(1, weight=1)
                root.update_idletasks()
                log_window.see(tk.END)
                save_log_file(log_window, suffix="_normal")
        root.update_idletasks()

    try:
        subtitle_input.grid_remove()
        video_input.grid_remove()
        remove_subtitle_button.grid_remove()
        remove_video_button.grid_remove()
        button_start_automatic_sync.grid_remove()
        batch_mode_button.grid_remove()
        action_menu_auto.grid_remove()
        sync_frame.grid_remove()
        ffsubsync_option_gss.grid_remove()
        vad_frame.grid_remove()
        ffsubsync_option_framerate.grid_remove()
        alass_split_penalty_slider.grid_remove()
        alass_disable_fps_guessing.grid_remove()
        alass_speed_optimization.grid_remove()
        label_message_auto.grid_remove()
        button_cancel_automatic_sync = TkButton(
            automatic_tab,
            text=CANCEL_TEXT,
            command=cancel_automatic_sync,
            padx=10,
            pady=10,
            fg=COLOR_WB,
            bg=DEFAULT_BUTTON_COLOR,
            activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
            activeforeground=COLOR_WB,
            relief=tk.RAISED,
            borderwidth=2,
            cursor="hand2",
            highlightthickness=0,
            takefocus=0,
            state="normal",
        )
        button_cancel_automatic_sync.grid(
            row=6, column=0, padx=10, pady=(0, 10), sticky="ew", columnspan=2
        )
        button_generate_again = TkButton(
            automatic_tab,
            text=GENERATE_AGAIN_TEXT,
            command=generate_again,
            padx=10,
            pady=10,
            fg=COLOR_WB,
            bg=BUTTON_COLOR_AUTO,
            activebackground=BUTTON_COLOR_AUTO_ACTIVE,
            activeforeground=COLOR_WB,
            relief=tk.RAISED,
            borderwidth=2,
            cursor="hand2",
            highlightthickness=0,
            takefocus=0,
            state="normal",
        )
        button_generate_again.grid(
            row=11, column=0, padx=10, pady=(00, 10), sticky="ew", columnspan=2
        )
        button_generate_again.grid_remove()
        button_go_back = TkButton(
            automatic_tab,
            text=GO_BACK,
            command=lambda: [log_message("", "info", tab="auto"), restore_window()],
            padx=10,
            pady=10,
            fg=COLOR_WB,
            bg=DEFAULT_BUTTON_COLOR,
            activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
            activeforeground=COLOR_WB,
            relief=tk.RAISED,
            borderwidth=2,
            cursor="hand2",
            highlightthickness=0,
            takefocus=0,
            state="normal",
        )
        button_go_back.grid(
            row=12, column=0, padx=10, pady=(0, 10), sticky="ew", columnspan=2
        )
        button_go_back.grid_remove()
        log_window = tk.Text(automatic_tab, wrap="word")
        log_window.config(
            font=(
                config["log_window_font"],
                config["log_window_font_size"],
                config["log_window_font_style"],
            ),
            bg=COLOR_WB,
            fg=COLOR_BW,
            insertbackground=COLOR_BW,
        )
        log_window.grid(
            row=0, column=0, padx=10, pady=(10, 5), sticky="nsew", columnspan=2
        )
        # Create a context menu for the log window
        log_window_context_menu = tk.Menu(log_window, tearoff=0)
        log_window_context_menu.add_command(
            label=CONTEXT_MENU_COPY,
            command=lambda: log_window.event_generate("<<Copy>>"),
        )

        # Function to show the context menu
        def show_log_window_context_menu(event):
            log_window_context_menu.post(event.x_root, event.y_root)

        # Bind the right-click event to the log window
        if platform == "Darwin":
            log_window.bind("<Button-2>", show_log_window_context_menu)
        else:
            log_window.bind("<Button-3>", show_log_window_context_menu)

        # Add a flag to track whether the user is at the bottom of the log window
        user_at_bottom = True

        def on_log_window_modified(event):
            global user_at_bottom
            # Check if the user is at the bottom of the log window
            if user_at_bottom:
                log_window.see(tk.END)
            log_window.edit_modified(False)  # Reset the modified flag

        # Add a button to scroll to the bottom
        scroll_to_bottom_button = tk.Button(
            log_window,
            text="↓",
            command=lambda: log_window.see(tk.END),
            bg=DEFAULT_BUTTON_COLOR,
            fg=COLOR_WB,
            activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
            activeforeground=COLOR_WB,
            relief=tk.RAISED,
            borderwidth=2,
            padx=7,
            pady=2,
            cursor="hand2",
            highlightthickness=0,
            takefocus=0,
        )
        scroll_to_bottom_button.lower()  # Initially hide the button

        def on_log_window_scroll(*args):
            global user_at_bottom
            # Get the current scroll position
            current_scroll = log_window.yview()
            # Check if the user is at the bottom
            user_at_bottom = (
                current_scroll[1] == 1.0
            )  # 1.0 means the scrollbar is at the bottom
            # Show or hide the "Go to Bottom" button
            if user_at_bottom:
                scroll_to_bottom_button.place_forget()  # Hide the button
            else:
                scroll_to_bottom_button.place(
                    relx=0.99, rely=0.99, anchor="se"
                )  # Show the button
            # Pass valid scroll arguments to the yview method
            if args[0] in ("moveto", "scroll"):
                log_window.yview(*args)

        # Bind the scroll event to track user scrolling
        log_window.config(yscrollcommand=on_log_window_scroll)

        log_window.bind("<<Modified>>", on_log_window_modified)
        log_window.edit_modified(False)
        progress_bar = ttk.Progressbar(
            automatic_tab, orient="horizontal", length=200, mode="determinate"
        )
        progress_bar.grid(
            row=1, column=0, padx=10, pady=(5, 10), sticky="ew", columnspan=2
        )
        root.update_idletasks()
        threading.Thread(target=run_subprocess).start()
    except Exception as e:
        log_message(ERROR_OCCURRED.format(error_message=str(e)), "error", tab="auto")
    automatic_tab.rowconfigure(0, weight=1)
    automatic_tab.rowconfigure(1, weight=0)
    automatic_tab.columnconfigure(0, weight=1)


# Start automatic sync end
label_message_auto = tk.Label(
    automatic_tab, text="", bg=COLOR_BACKGROUND, fg=COLOR_BW, anchor="center"
)
subtitle_input = tk.Label(
    automatic_tab,
    text=SUBTITLE_INPUT_TEXT,
    bg=COLOR_ONE,
    fg=COLOR_BW,
    relief="ridge",
    width=40,
    height=5,
    cursor="hand2",
)
video_input = tk.Label(
    automatic_tab,
    text=VIDEO_INPUT_TEXT,
    bg=COLOR_ONE,
    fg=COLOR_BW,
    relief="ridge",
    width=40,
    height=5,
    cursor="hand2",
)
video_input_text = tk.Label(
    automatic_tab,
    text=VIDEO_INPUT_LABEL,
    bg=COLOR_BACKGROUND,
    fg=COLOR_BW,
    relief="ridge",
    padx=5,
    borderwidth=border_fix,
)
video_input_text.place(in_=video_input, relx=0, rely=0, anchor="nw")
subtitle_input_text = tk.Label(
    automatic_tab,
    text=SUBTITLE_INPUT_LABEL,
    bg=COLOR_BACKGROUND,
    fg=COLOR_BW,
    relief="ridge",
    padx=5,
    borderwidth=border_fix,
)
subtitle_input_text.place(in_=subtitle_input, relx=0, rely=0, anchor="nw")
button_start_automatic_sync = TkButton(
    automatic_tab,
    text=START_AUTOMATIC_SYNC_TEXT,
    command=start_automatic_sync,
    padx=10,
    pady=10,
    fg=COLOR_WB,
    bg=BUTTON_COLOR_AUTO,
    activebackground=BUTTON_COLOR_AUTO_ACTIVE,
    activeforeground=COLOR_WB,
    relief=tk.RAISED,
    borderwidth=2,
    cursor="hand2",
    highlightthickness=0,
    takefocus=0,
    state="normal",
)
remove_subtitle_button = TkButton(
    automatic_tab,
    text="X",
    font=f"Arial {FONT_SIZE} bold",
    command=remove_subtitle_input,
    padx=4,
    pady=0,
    fg=COLOR_WB,
    bg=DEFAULT_BUTTON_COLOR,
    activeforeground=COLOR_WB,
    activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
    relief=tk.RIDGE,
    borderwidth=1,
    cursor="hand2",
    highlightthickness=0,
    takefocus=0,
    state="normal",
)
remove_subtitle_button.grid_remove()
remove_video_button = TkButton(
    automatic_tab,
    text="X",
    font=f"Arial {FONT_SIZE} bold",
    command=remove_video_input,
    padx=(4),
    pady=0,
    fg=COLOR_WB,
    bg=DEFAULT_BUTTON_COLOR,
    activeforeground=COLOR_WB,
    activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
    relief=tk.RIDGE,
    borderwidth=1,
    cursor="hand2",
    highlightthickness=0,
    takefocus=0,
    state="normal",
)
# Define the mapping for VAD options
vad_option_map = {
    DEFAULT: "default",
    "subs_then_webrtc": "subs_then_webrtc",
    "webrtc": "webrtc",
    "subs_then_auditok": "subs_then_auditok",
    "auditok": "auditok",
    "subs_then_silero": "subs_then_silero",
    "silero": "silero",
}
remove_video_button.grid_remove()
sync_frame = tk.Frame(automatic_tab, bg=COLOR_BACKGROUND)
sync_frame.grid(row=6, column=1, padx=(0, 10), pady=(5, 10), sticky="e")
ffsubsync_option_framerate_var = tk.BooleanVar(
    value=config.get("ffsubsync_option_framerate", False)
)
ffsubsync_option_gss_var = tk.BooleanVar(
    value=config.get("ffsubsync_option_gss", False)
)
ffsubsync_option_vad_var_value = config.get("ffsubsync_option_vad", DEFAULT)
ffsubsync_option_vad_var_value = vad_option_map.get(
    ffsubsync_option_vad_var_value, DEFAULT
)
ffsubsync_option_vad_var = tk.StringVar(value=ffsubsync_option_vad_var_value)
action_var_auto_value = globals().get(
    config.get("action_var_auto", OPTION_SAVE_NEXT_TO_SUBTITLE),
    OPTION_SAVE_NEXT_TO_SUBTITLE,
)
action_var_auto = tk.StringVar(value=action_var_auto_value)
# Convert string values to actual variables
sync_tool_var_auto_value = globals().get(
    config.get("sync_tool_var_auto", SYNC_TOOL_FFSUBSYNC), SYNC_TOOL_FFSUBSYNC
)
sync_tool_var_auto = tk.StringVar(value=sync_tool_var_auto_value)
ffsubsync_option_framerate = tk.Checkbutton(
    automatic_tab,
    text=CHECKBOX_NO_FIX_FRAMERATE,
    background=COLOR_BACKGROUND,
    foreground=COLOR_BW,
    variable=ffsubsync_option_framerate_var,
    command=lambda: update_config(
        "ffsubsync_option_framerate", ffsubsync_option_framerate_var.get()
    ),
    selectcolor=COLOR_WB,  # Change the checkbox square background
    activebackground=COLOR_BACKGROUND,
    activeforeground=COLOR_BW,
    highlightthickness=0,
    takefocus=0,
    state="normal",
)
ffsubsync_option_gss = tk.Checkbutton(
    automatic_tab,
    text=CHECKBOX_GSS,
    background=COLOR_BACKGROUND,
    foreground=COLOR_BW,
    variable=ffsubsync_option_gss_var,
    command=lambda: update_config(
        "ffsubsync_option_gss", ffsubsync_option_gss_var.get()
    ),
    selectcolor=COLOR_WB,  # Change the checkbox square background
    activebackground=COLOR_BACKGROUND,
    activeforeground=COLOR_BW,
    highlightthickness=0,
    takefocus=0,
    state="normal",
)
# Create frame for VAD controls
vad_frame = tk.Frame(automatic_tab, bg=COLOR_BACKGROUND)
vad_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=0, sticky="ew")
vad_frame.columnconfigure(1, weight=1)
vad_label = tk.Label(
    vad_frame, text=VOICE_ACTIVITY_DETECTOR, bg=COLOR_BACKGROUND, fg=COLOR_BW
)
vad_label.grid(row=0, column=0, pady=(5, 5), sticky="w")

ffsubsync_option_vad = ttk.OptionMenu(
    vad_frame,
    ffsubsync_option_vad_var,
    ffsubsync_option_vad_var_value,
    *vad_option_map.keys(),
    command=lambda _: update_config(
        "ffsubsync_option_vad", vad_option_map.get(ffsubsync_option_vad_var.get(), "")
    ),
)
ffsubsync_option_vad.configure(style="TMenubutton", takefocus=0)
ffsubsync_option_vad.grid(row=0, column=1, sticky="w")


def select_destination_folder():
    global tooltip_action_menu_auto, selected_destination_folder
    folder_path = filedialog.askdirectory()
    if folder_path:
        selected_destination_folder = folder_path
        tooltip_action_menu_auto = ToolTip(
            action_menu_auto, TEXT_SELECTED_FOLDER.format(folder_path)
        )
        log_message(TEXT_SELECTED_FOLDER.format(folder_path), "info", tab="auto")
    else:
        log_message(TEXT_NO_FOLDER_SELECTED, "error", tab="auto")
        action_var_auto.set(OPTION_SAVE_NEXT_TO_SUBTITLE)


def on_action_menu_change(*args):
    tooltip_action_menu_auto = ToolTip(action_menu_auto, TOOLTIP_TEXT_ACTION_MENU_AUTO)
    log_message("", "info", tab="auto")
    selected_option = action_var_auto.get()
    if selected_option == OPTION_SELECT_DESTINATION_FOLDER:
        select_destination_folder()
    else:
        # Map the actual variable to its name
        variable_name_map = {
            OPTION_SAVE_NEXT_TO_SUBTITLE: "OPTION_SAVE_NEXT_TO_SUBTITLE",
            OPTION_SAVE_NEXT_TO_VIDEO: "OPTION_SAVE_NEXT_TO_VIDEO",
            OPTION_REPLACE_ORIGINAL_SUBTITLE: "OPTION_REPLACE_ORIGINAL_SUBTITLE",
            OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME: "OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME",
            OPTION_SAVE_TO_DESKTOP: "OPTION_SAVE_TO_DESKTOP",
        }
        variable_name = variable_name_map.get(selected_option, "")
        update_config("action_var_auto", variable_name)


def on_sync_tool_change(*args):
    if sync_tool_var_auto.get() == SYNC_TOOL_ALASS:
        update_config("sync_tool_var_auto", "SYNC_TOOL_ALASS")
        ffsubsync_option_framerate.grid_remove()
        ffsubsync_option_gss.grid_remove()
        vad_frame.grid_remove()
        alass_disable_fps_guessing.grid(
            row=2, column=0, columnspan=5, padx=10, pady=(5, 0), sticky="w"
        )
        alass_speed_optimization.grid(
            row=3, column=0, columnspan=5, padx=10, pady=0, sticky="w"
        )
        alass_split_penalty_slider.grid(
            row=4, column=0, columnspan=5, padx=10, pady=0, sticky="ew"
        )
    else:
        update_config("sync_tool_var_auto", "SYNC_TOOL_FFSUBSYNC")
        alass_split_penalty_slider.grid_remove()
        alass_speed_optimization.grid_remove()
        alass_disable_fps_guessing.grid_remove()
        ffsubsync_option_framerate.grid(
            row=2, column=0, columnspan=5, padx=10, pady=(5, 0), sticky="w"
        )
        ffsubsync_option_gss.grid(
            row=3, column=0, columnspan=5, padx=10, pady=0, sticky="w"
        )
        vad_frame.grid(row=4, column=0, columnspan=5, padx=10, pady=0, sticky="w")


style.configure(
    "TMenubutton", background=COLOR_OPTIONS, foreground=COLOR_BW, relief="flat"
)
action_menu_auto = ttk.OptionMenu(
    automatic_tab,
    action_var_auto,
    action_var_auto_value,
    OPTION_SAVE_NEXT_TO_SUBTITLE,
    OPTION_REPLACE_ORIGINAL_SUBTITLE,
    OPTION_SAVE_NEXT_TO_VIDEO,
    OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME,
    OPTION_SAVE_TO_DESKTOP,
    OPTION_SELECT_DESTINATION_FOLDER,
)
action_menu_auto.configure(style="TMenubutton")
sync_tool_menu_auto = ttk.OptionMenu(
    sync_frame,
    sync_tool_var_auto,
    sync_tool_var_auto_value,
    SYNC_TOOL_FFSUBSYNC,
    SYNC_TOOL_ALASS,
)
sync_tool_menu_auto.configure(style="TMenubutton", takefocus=0)
sync_tool_var_auto.trace_add("write", on_sync_tool_change)
action_var_auto.trace_add("write", on_action_menu_change)
alass_disable_fps_guessing_var = tk.BooleanVar(
    value=config.get("alass_disable_fps_guessing", False)
)
alass_speed_optimization_var = tk.BooleanVar(
    value=config.get("alass_speed_optimization", False)
)
alass_split_penalty_var = tk.IntVar(value=config.get("alass_split_penalty", 7))
alass_disable_fps_guessing = tk.Checkbutton(
    automatic_tab,
    text=ALASS_DISABLE_FPS_GUESSING_TEXT,
    background=COLOR_BACKGROUND,
    foreground=COLOR_BW,
    variable=alass_disable_fps_guessing_var,
    command=lambda: update_config(
        "alass_disable_fps_guessing", alass_disable_fps_guessing_var.get()
    ),
    selectcolor=COLOR_WB,  # Change the checkbox square background
    activebackground=COLOR_BACKGROUND,
    activeforeground=COLOR_BW,
    highlightthickness=0,
    takefocus=0,
    state="normal",
)

alass_speed_optimization = tk.Checkbutton(
    automatic_tab,
    text=ALASS_SPEED_OPTIMIZATION_TEXT,
    background=COLOR_BACKGROUND,
    foreground=COLOR_BW,
    variable=alass_speed_optimization_var,
    command=lambda: update_config(
        "alass_speed_optimization", alass_speed_optimization_var.get()
    ),
    selectcolor=COLOR_WB,  # Change the checkbox square background
    activebackground=COLOR_BACKGROUND,
    activeforeground=COLOR_BW,
    highlightthickness=0,
    takefocus=0,
    state="normal",
)
alass_split_penalty_slider = tk.Scale(
    automatic_tab,
    from_=-1,
    to=100,
    background=COLOR_BACKGROUND,
    foreground=COLOR_BW,
    border=0,
    orient="horizontal",
    variable=alass_split_penalty_var,
    label=LABEL_SPLIT_PENALTY,
    command=lambda value: update_config(
        "alass_split_penalty", alass_split_penalty_var.get()
    ),
    highlightthickness=5,
    highlightbackground=COLOR_BACKGROUND,
    troughcolor=COLOR_ONE,
    activebackground=COLOR_BACKGROUND,
)
tooltip_ffsubsync_option_framerate = ToolTip(
    ffsubsync_option_framerate, TOOLTIP_FRAMERATE
)
tooltip_ffsubsync_option_gss = ToolTip(ffsubsync_option_gss, TOOLTIP_GSS)
tooltip_ffsubsync_option_vad = ToolTip(ffsubsync_option_vad, TOOLTIP_VAD)
tooltip_action_menu_auto = ToolTip(action_menu_auto, TOOLTIP_TEXT_ACTION_MENU_AUTO)
tooltip_sync_tool_menu_auto = ToolTip(
    sync_tool_menu_auto, TOOLTIP_TEXT_SYNC_TOOL_MENU_AUTO
)
tooltip_alass_speed_optimization = ToolTip(
    alass_speed_optimization, TOOLTIP_ALASS_SPEED_OPTIMIZATION
)
tooltip_alass_disable_fps_guessing = ToolTip(
    alass_disable_fps_guessing, TOOLTIP_ALASS_DISABLE_FPS_GUESSING
)
video_input.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew", columnspan=2)
subtitle_input.grid(row=1, column=0, padx=10, pady=0, sticky="nsew", columnspan=2)
if sync_tool_var_auto.get() == SYNC_TOOL_ALASS:
    ffsubsync_option_framerate.grid_remove()
    ffsubsync_option_gss.grid_remove()
    vad_frame.grid_remove()
    alass_disable_fps_guessing.grid(
        row=2, column=0, columnspan=5, padx=10, pady=(5, 0), sticky="w"
    )
    alass_speed_optimization.grid(
        row=3, column=0, columnspan=5, padx=10, pady=0, sticky="w"
    )
    alass_split_penalty_slider.grid(
        row=4, column=0, columnspan=5, padx=10, pady=0, sticky="ew"
    )
else:
    alass_split_penalty_slider.grid_remove()
    alass_speed_optimization.grid_remove()
    alass_disable_fps_guessing.grid_remove()
    ffsubsync_option_framerate.grid(
        row=2, column=0, columnspan=5, padx=10, pady=(5, 0), sticky="w"
    )
    ffsubsync_option_gss.grid(
        row=3, column=0, columnspan=5, padx=10, pady=0, sticky="w"
    )
    vad_frame.grid(row=4, column=0, columnspan=5, padx=10, pady=0, sticky="w")
sync_tool_var_auto.trace_add("write", on_sync_tool_change)
sync_tool_label = tk.Label(
    sync_frame, text=SYNC_TOOL_LABEL_TEXT, bg=COLOR_BACKGROUND, fg=COLOR_BW
)
sync_tool_label.grid(row=0, column=0, padx=(5, 0), sticky="w")
sync_tool_menu_auto.grid(row=0, column=1, padx=(0, 0), sticky="w")
action_menu_auto.grid(
    row=6, column=0, padx=(10, 0), pady=(5, 10), sticky="w", columnspan=2
)
subtitle_input.drop_target_register(DND_FILES)
automatic_tab.columnconfigure(1, weight=1)
batch_mode_var = tk.BooleanVar()
batch_mode_button = TkButton(
    automatic_tab,
    text=BATCH_MODE_TEXT,
    command=toggle_batch_mode,
    padx=10,
    pady=10,
    fg=COLOR_WB,
    bg=DEFAULT_BUTTON_COLOR,
    activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
    activeforeground=COLOR_WB,
    relief=tk.RAISED,
    borderwidth=2,
    cursor="hand2",
    highlightthickness=0,
    takefocus=0,
    state="normal",
)
batch_mode_button.grid(row=5, column=0, padx=(10, 2.5), pady=10, sticky="w")
button_start_automatic_sync.grid(row=5, column=1, padx=(2.5, 10), pady=10, sticky="ew")
subtitle_input.dnd_bind("<<Drop>>", on_subtitle_drop)
subtitle_input.bind("<Button-1>", browse_subtitle)
subtitle_input.bind("<Enter>", on_enter)
subtitle_input.bind("<Leave>", on_leave)
video_input.drop_target_register(DND_FILES)
video_input.dnd_bind("<<Drop>>", on_video_drop)
video_input.bind("<Button-1>", browse_video)
video_input.bind("<Enter>", on_enter)
video_input.bind("<Leave>", on_leave)
label_message_auto.bind("<Configure>", update_wraplengt)
video_input.bind("<Configure>", update_wraplengt)
subtitle_input.bind("<Configure>", update_wraplengt)
# Configure columns in automatic_tab
automatic_tab.rowconfigure(1, weight=1)
automatic_tab.columnconfigure(0, weight=0)
automatic_tab.columnconfigure(1, weight=1)


# ---------------- Automatic Tab ---------------- #
# ---------------- Manual Tab ---------------- #
def on_drop(event):
    filepaths = event.widget.tk.splitlist(event.data)
    if len(filepaths) != 1:
        log_message(DROP_SINGLE_SUBTITLE_FILE, "error", tab="manual")
        label_drop_box.config(bg=COLOR_ONE)
        return
    filepath = filepaths[0]
    if filepath.lower().endswith(tuple(SUBTITLE_EXTENSIONS)):
        label_drop_box.config(text=filepath)
        label_drop_box.tooltip_text = filepath
        label_drop_box.config(bg=COLOR_TWO)
        button_clear.grid()
        log_message("", "info", tab="manual")
    else:
        log_message(DROP_SUBTITLE_FILE, "error", tab="manual")
        label_drop_box.config(bg=COLOR_ONE)


def browse_file(event=None):
    subtitle_file = filedialog.askopenfilename(
        filetypes=[
            (SUBTITLE_FILES_TEXT, " ".join([f"*{ext}" for ext in SUBTITLE_EXTENSIONS]))
        ]
    )
    if subtitle_file:
        label_drop_box.config(text=subtitle_file)
        label_drop_box.tooltip_text = subtitle_file
        label_drop_box.config(bg=COLOR_TWO)
        button_clear.grid()
        log_message("", "info", tab="manual")
    else:
        # Check if the user canceled the dialog
        if subtitle_file != "":
            log_message(SELECT_SUBTITLE, "error", tab="manual")
            label_drop_box.config(bg=COLOR_ONE)


def select_subtitle_at_startup():
    if len(sys.argv) > 1:
        messagebox.showinfo("Command Line Arguments", f"sys.argv: {sys.argv}")
        subtitle_file = sys.argv[1]
        if os.path.isfile(subtitle_file) and subtitle_file.lower().endswith(".srt"):
            # For manual tab
            label_drop_box.config(text=subtitle_file)
            label_drop_box.tooltip_text = subtitle_file
            label_drop_box.config(bg=COLOR_TWO)
            log_message("", "info", tab="manual")
            button_clear.grid()
            # For automatic tab
            subtitle_input.config(text=subtitle_file)
            subtitle_input.tooltip_text = subtitle_file
            subtitle_input.config(bg=COLOR_TWO)
            remove_subtitle_button.grid()
            log_message("", "info", tab="auto")
        elif not os.path.isfile(subtitle_file):
            log_message(FILE_NOT_EXIST, "error", tab="manual")
            label_drop_box.config(bg=COLOR_ONE)
        elif len(sys.argv) > 2:
            log_message(MULTIPLE_ARGUMENTS, "error", tab="manual")
            label_drop_box.config(bg=COLOR_ONE)
        else:
            log_message(INVALID_FILE_FORMAT, "error", tab="manual")
            label_drop_box.config(bg=COLOR_ONE)


def increase_milliseconds():
    current_value = int(entry_milliseconds.get() or 0)
    # Calculate the nearest multiple of 50 greater than the current value
    new_value = ((current_value + 49) // 50) * 50
    if new_value == current_value:
        new_value += 50
    entry_milliseconds.delete(0, tk.END)
    entry_milliseconds.insert(0, str(new_value))


def decrease_milliseconds():
    current_value = int(entry_milliseconds.get() or 0)
    # Calculate the nearest multiple of 50 less than the current value
    new_value = ((current_value - 1) // 50) * 50
    if new_value == current_value:
        new_value -= 50
    entry_milliseconds.delete(0, tk.END)
    entry_milliseconds.insert(0, str(new_value))


def validate_input(new_value):
    if " " in new_value:  # Check if the input contains spaces
        return False
    if new_value in ("", "-"):  # Allow empty string
        return True
    if "--" in new_value:  # Disallow double negative signs
        return False
    try:
        value = int(new_value)
        if value > 0:
            entry_milliseconds.config(bg=COLOR_MILISECONDS_HIGH)
        elif value == 0:
            entry_milliseconds.config(bg=COLOR_WB)
        else:
            entry_milliseconds.config(bg=COLOR_MILISECONDS_LOW)
        return True  # Input is a valid integer
    except ValueError:
        return False  # Input is not a valid integer


def clear_entry(event):
    if entry_milliseconds.get() == "0":
        entry_milliseconds.delete(0, tk.END)


def clear_label_drop_box():
    label_drop_box.config(text=LABEL_DROP_BOX)
    label_drop_box.config(bg=COLOR_ONE)
    del label_drop_box.tooltip_text
    log_message("", "info", tab="manual")
    button_clear.grid_remove()


def enter_key_bind(event):
    if button_start_automatic_sync.winfo_viewable():
        button_start_automatic_sync.invoke()
    elif button_sync.winfo_viewable():
        button_sync.invoke()


label_drop_box = tk.Label(
    manual_tab,
    text=LABEL_DROP_BOX,
    bg=COLOR_ONE,
    fg=COLOR_BW,
    relief="ridge",
    width=40,
    height=17,
    cursor="hand2",
)
label_separator = ttk.Separator(manual_tab, orient="horizontal")
label_message_manual = tk.Label(
    manual_tab, text="", bg=COLOR_BACKGROUND, fg=COLOR_BW, anchor="center"
)
label_milliseconds = tk.Label(
    manual_tab, text=LABEL_SHIFT_SUBTITLE, anchor="w", bg=COLOR_BACKGROUND, fg=COLOR_BW
)
entry_milliseconds = tk.Entry(
    manual_tab,
    cursor="xterm",
    width=15,
    justify="center",
    borderwidth=2,
    validate="key",
    bg=COLOR_WB,
    fg=COLOR_BW,
    insertbackground=COLOR_BW,
)
entry_milliseconds.config(validatecommand=(root.register(validate_input), "%P"))
button_clear = TkButton(
    manual_tab,
    text="X",
    command=clear_label_drop_box,
    font=f"Arial {FONT_SIZE} bold",
    padx=4,
    pady=0,
    fg=COLOR_WB,
    bg=DEFAULT_BUTTON_COLOR,
    activeforeground=COLOR_WB,
    activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
    relief=tk.RIDGE,
    borderwidth=1,
    cursor="hand2",
    highlightthickness=0,
    takefocus=0,
    state="normal",
)
button_minus = TkButton(
    manual_tab,
    text="-",
    command=decrease_milliseconds,
    padx=10,
    pady=6,
    fg=COLOR_WB,
    bg=DEFAULT_BUTTON_COLOR,
    activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
    activeforeground=COLOR_WB,
    relief=tk.RAISED,
    borderwidth=2,
    cursor="hand2",
    highlightthickness=0,
    takefocus=0,
    state="normal",
)
button_plus = TkButton(
    manual_tab,
    text="+",
    command=increase_milliseconds,
    padx=10,
    pady=6,
    fg=COLOR_WB,
    bg=DEFAULT_BUTTON_COLOR,
    activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
    activeforeground=COLOR_WB,
    relief=tk.RAISED,
    borderwidth=2,
    cursor="hand2",
    highlightthickness=0,
    takefocus=0,
    state="normal",
)
button_sync = TkButton(
    manual_tab,
    text=SHIFT_SUBTITLE_TEXT,
    command=sync_subtitle,
    padx=10,
    pady=10,
    fg=COLOR_WB,
    bg=BUTTON_COLOR_MANUAL,
    activebackground=BUTTON_COLOR_MANUAL_ACTIVE,
    activeforeground=COLOR_WB,
    relief=tk.RAISED,
    borderwidth=2,
    cursor="hand2",
    highlightthickness=0,
    takefocus=0,
    state="normal",
)
save_to_desktop_var = tk.BooleanVar()
check_save_to_desktop = tk.Checkbutton(
    manual_tab,
    text=OPTION_SAVE_TO_DESKTOP,
    background=COLOR_BACKGROUND,
    foreground=COLOR_BW,
    variable=save_to_desktop_var,
    command=lambda: checkbox_selected(save_to_desktop_var),
    selectcolor=COLOR_WB,
    activebackground=COLOR_BACKGROUND,
    activeforeground=COLOR_BW,
    highlightthickness=0,
    takefocus=0,
    state="normal",
)
replace_original_var = tk.BooleanVar()
check_replace_original = tk.Checkbutton(
    manual_tab,
    text=OPTION_REPLACE_ORIGINAL_SUBTITLE,
    background=COLOR_BACKGROUND,
    foreground=COLOR_BW,
    variable=replace_original_var,
    command=lambda: checkbox_selected(replace_original_var),
    selectcolor=COLOR_WB,
    activebackground=COLOR_BACKGROUND,
    activeforeground=COLOR_BW,
    highlightthickness=0,
    takefocus=0,
    state="normal",
)
label_drop_box.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew", columnspan=6)
button_clear.grid(row=0, column=3, padx=(0, 12), pady=(12, 5), sticky="ne")
button_clear.grid_remove()
# label_separator.grid(row=1, column=0, sticky="ew", padx=10, pady=5, columnspan=6)
label_milliseconds.grid(row=2, column=0, padx=10, pady=5, sticky="w")
button_minus.grid(row=2, column=1, padx=(0, 5), pady=5, sticky="ew")
entry_milliseconds.grid(row=2, column=2, pady=5, sticky="ew", ipady=7)
button_plus.grid(row=2, column=3, padx=(5, 10), pady=5, sticky="ew")
button_sync.grid(row=3, column=0, padx=10, pady=10, sticky="ew", columnspan=6)
check_save_to_desktop.grid(row=4, column=0, padx=10, pady=5, sticky="w", columnspan=3)
check_replace_original.grid(
    row=4, column=1, padx=(10), pady=5, sticky="e", columnspan=3
)
label_drop_box.bind("<Button-1>", browse_file)
label_drop_box.bind("<Enter>", on_enter)
label_drop_box.bind("<Leave>", on_leave)
label_drop_box.bind("<Configure>", update_wraplengt)
label_drop_box.drop_target_register(DND_FILES)
label_drop_box.dnd_bind("<<Drop>>", on_drop)
label_message_manual.bind("<Configure>", update_wraplengt)
label_message_manual.grid_remove()
entry_milliseconds.bind("<FocusIn>", clear_entry)
# Create tooltips for checkboxes and entry field
tooltip_save_to_desktop = ToolTip(check_save_to_desktop, TOOLTIP_SAVE_TO_DESKTOP)
tooltip_replace_original = ToolTip(check_replace_original, TOOLTIP_REPLACE_ORIGINAL)
tooltip_milliseconds = ToolTip(entry_milliseconds, "1 second = 1000ms")


# ---------------- Manual Tab ---------------- #
# Check for updates after the window is built
def run_after_startup():
    """Run tasks after the application startup."""
    if notify_about_updates:
        check_for_updates()


root.after(2000, run_after_startup)
# Select subtitle file if specified as argument
select_subtitle_at_startup()
root.bind("<Return>", enter_key_bind)
# Calculate minimum width and height based on elements inside
min_width = label_drop_box.winfo_reqwidth() + 95
min_height_automatic = (
    sum(
        widget.winfo_reqheight()
        for widget in (
            label_drop_box,
            label_separator,
            button_sync,
            check_save_to_desktop,
        )
    )
    + 200
)
min_height_manual = sum(
    widget.winfo_reqheight()
    for widget in (
        label_drop_box,
        label_separator,
        label_milliseconds,
        entry_milliseconds,
        button_minus,
        button_plus,
        button_sync,
        check_save_to_desktop,
        check_replace_original,
    )
)
min_height = max(min_height_automatic, min_height_manual)
root.minsize(min_width, min_height)  # Set minimum size for the window
root.update_idletasks()
dark_title_bar(root)
place_window_top_right()
# if icon exists, set it as the window icon
try:
    if os.path.exists("icon.ico"):
        if platform == "Windows":
            root.iconbitmap("icon.ico")
        else:  # Linux or macOS
            icon = PhotoImage(file="icon.ico")
            root.iconphoto(True, icon)
except Exception:
    pass
root.deiconify()  # Show the window after it's been built
root.mainloop()
