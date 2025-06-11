from utils import get_version

# Program Information
PROGRAM_NAME = "AutoSubSync"
PROGRAM_TAGLINE = "Subtitle Synchronizer"
PROGRAM_DESCRIPTION = "Synchronize subtitle files with video using advanced algorithms."
GITHUB_URL = "https://github.com/denizsafak/AutoSubSync"
GITHUB_VERSION_URL = "https://raw.githubusercontent.com/denizsafak/AutoSubSync/refs/heads/main/main/VERSION"
GITHUB_LATEST_RELEASE_URL = "https://github.com/denizsafak/AutoSubSync/releases/latest"
VERSION = get_version()

DEFAULT_OPTIONS = {
    "sync_tool": "ffsubsync",
    "ffsubsync_dont_fix_framerate": False,
    "ffsubsync_use_golden_section": False,
    "ffsubsync_vad": "default",
    "alass_check_video_subtitles": True,
    "alass_disable_fps_guessing": False,
    "alass_disable_speed_optimization": False,
    "alass_split_penalty": 7,
    "automatic_save_location": "save_next_to_input_subtitle",
    "manual_save_location": "save_next_to_input_subtitle",
    "remember_changes": True,
    "check_updates_startup": True,
    "batch_mode": False,
    "add_autosync_prefix": True,
    "backup_subtitles_before_overwriting": True,
    "keep_extracted_subtitles": False,
    "keep_converted_subtitles": False,
}

COLORS = {
    "GREY": "#808080",
    "BLUE": "#6ab0de",
    "GREEN": "#42ad4a",
    "RED": "#c0392b",
    "GREY_BACKGROUND": "rgba(128, 128, 128, 0.15)",
    "GREY_BACKGROUND_HOVER": "rgba(128, 128, 128, 0.3)",
    "BLUE_BACKGROUND": "rgba(0, 102, 255, 0.05)",
    "BLUE_BACKGROUND_HOVER": "rgba(0, 102, 255, 0.1)",
    "GREEN_BACKGROUND": "rgba(66, 173, 73, 0.1)",
    "GREEN_BACKGROUND_HOVER": "rgba(66, 173, 73, 0.15)",
    "RED_BACKGROUND": "rgba(232, 78, 60, 0.1)",
    "RED_BACKGROUND_HOVER": "rgba(232, 78, 60, 0.15)",
}

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
    ".smi",
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

FFSUBSYNC_VAD_OPTIONS = [
    "subs_then_webrtc",
    "webrtc",
    "subs_then_auditok",
    "auditok",
    "subs_then_silero",
    "silero",
]
