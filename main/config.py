import os
import json
from tkinter import messagebox
from functions.get_config import config_path

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