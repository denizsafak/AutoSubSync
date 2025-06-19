import platform
from utils import get_version, get_resource_path

# Program Information
PROGRAM_NAME = "AutoSubSync"
PROGRAM_TAGLINE = "Subtitle Synchronizer"
PROGRAM_DESCRIPTION = "Synchronize subtitle files with video using advanced algorithms."
GITHUB_URL = "https://github.com/denizsafak/AutoSubSync"
GITHUB_VERSION_URL = "https://raw.githubusercontent.com/denizsafak/AutoSubSync/refs/heads/main/main/VERSION"
GITHUB_LATEST_RELEASE_URL = "https://github.com/denizsafak/AutoSubSync/releases/latest"
VERSION = get_version()

# ffmpeg and ffprobe paths
_exe_suffix = ".exe" if platform.system() == "Windows" else ""
FFMPEG_EXECUTABLE = get_resource_path("autosubsync.resources.ffmpeg-bin", f"ffmpeg{_exe_suffix}")
FFPROBE_EXECUTABLE = get_resource_path("autosubsync.resources.ffmpeg-bin", f"ffprobe{_exe_suffix}")

# Synchronization tools
SYNC_TOOLS = {
    "ffsubsync": {
        "description": "Automatic subtitle synchronization tool using audio alignment",
        "github": "https://github.com/smacke/ffsubsync",
        "supported_formats": [".srt", ".ass", ".ssa", ".vtt"],
        "executable": {
            "Windows": get_resource_path("autosubsync.resources.ffsubsync-bin", "ffsubsync.exe"),
            "Linux": get_resource_path("autosubsync.resources.ffsubsync-bin", "ffsubsync"),
            "Darwin": get_resource_path("autosubsync.resources.ffsubsync-bin", "ffsubsync")
        },
        "cmd_structure": ["{reference}", "-i", "{subtitle}", "-o", "{output}"],
        "options": {
            "dont_fix_framerate": {
                "type": "checkbox",
                "label": "Don't fix framerate",
                "tooltip": "--no-fix-framerate: Disable automatic frame rate correction",
                "argument": "--no-fix-framerate",
                "default": False
            },
            "use_golden_section": {
                "type": "checkbox",
                "label": "Use golden section search",
                "tooltip": "--gss: Use golden section search for better alignment",
                "argument": "--gss",
                "default": False
            },
            "vad": {
                "type": "dropdown",
                "label": "Voice activity detector",
                "tooltip": "--vad: Enable voice activity detection for better alignment",
                "argument": "--vad",
                "default": "default",
                "values": ["default", "subs_then_webrtc", "subs_then_auditok", "subs_then_silero", "webrtc", "auditok", "silero"],
                "value_labels": {
                    "default": "Default",
                    "subs_then_webrtc": "Subs then WebRTC",
                    "subs_then_auditok": "Subs then Auditok",
                    "subs_then_silero": "Subs then Silero",
                    "webrtc": "WebRTC",
                    "auditok": "Auditok",
                    "silero": "Silero"
                }
            }
        }
    },
    "alass": {
        "description": "Audio-based subtitle synchronization with high accuracy",
        "github": "https://github.com/kaegi/alass",
        "supported_formats": [".srt", ".ass", ".ssa", ".sub", ".idx"],
        "executable": {
            "Windows": get_resource_path("autosubsync.resources.alass-bin", "alass-cli.exe"),
            "Linux": get_resource_path("autosubsync.resources.alass-bin", "alass-linux64"),
            "Darwin": "alass-cli"
        },
        "cmd_structure": ["{reference}", "{subtitle}", "{output}"],
        "options": {
            "check_video_for_subtitles": {
                "type": "checkbox",
                "label": "Check video subtitles",
                "tooltip": "Check if video already contains subtitles",
                "default": True
            },
            "disable_fps_guessing": {
                "type": "checkbox",
                "label": "Disable FPS guessing",
                "tooltip": "--disable-fps-guessing: Disable automatic frame rate detection",
                "argument": "--disable-fps-guessing",
                "default": False
            },
            "disable_speed_optimization": {
                "type": "checkbox",
                "label": "Disable speed optimization",
                "tooltip": "--speed-optimization 0: Disable speed optimization algorithms",
                "argument": "--speed-optimization 0",
                "default": False
            },
            "split_penalty": {
                "type": "slider",
                "label": "Split penalty",
                "tooltip": "--split-penalty: Penalty for splitting subtitles during alignment\n(Default: 7, Recommended: 5-20, No splits: -1)",
                "argument": "--split-penalty",
                "range": [-1, 100],
                "default": 7
            }
        }
    }
}

DEFAULT_OPTIONS = {
    "sync_tool": "ffsubsync",
    "automatic_save_location": "save_next_to_input_subtitle",
    "manual_save_location": "save_next_to_input_subtitle",
    "remember_changes": True,
    "check_updates_startup": True,
    "batch_mode": False,
    "add_tool_prefix": False,
    "backup_subtitles_before_overwriting": True,
    "keep_extracted_subtitles": False,
    "keep_converted_subtitles": False,
    "output_subtitle_encoding": "same_as_input",
    "add_ms_prefix_to_filename": True,
}

AUTOMATIC_SAVE_MAP = {
    "save_next_to_input_subtitle": "Save next to input subtitle",
    "overwrite_input_subtitle": "Overwrite input subtitle",
    "save_next_to_video": "Save next to video",
    "save_next_to_video_with_same_filename": "Save next to video with same filename",
    "save_to_desktop": "Save to desktop",
    "select_destination_folder": "Select destination folder",
}

MANUAL_SAVE_MAP = {
    "save_next_to_input_subtitle": "Save next to input subtitle",
    "overwrite_input_subtitle": "Overwrite input subtitle",
    "save_to_desktop": "Save to desktop",
    "select_destination_folder": "Select destination folder",
}

COLORS = {
    "GREY": "#808080",
    "BLUE": "#6ab0de",
    "GREEN": "#42ad4a",
    "RED": "#c0392b",
    "ORANGE": "#e67e22",
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

EXTRACTABLE_SUBTITLE_EXTENSIONS = {
    "subrip": "srt",
    "ass": "ass",
    "webvtt": "vtt"
}
