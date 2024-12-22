import os
import sys
import re
import shutil
import chardet
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import xml.etree.ElementTree as ET
import ctypes
# Program information
PROGRAM_NAME = "AutoSubSync"
VERSION = "v2.8"
GITHUB_URL = "https://github.com/denizsafak/AutoSubSync"
# File extensions
FFSUBSYNC_SUPPORTED_EXTENSIONS = ['.srt', '.ass', '.ssa']
ALASS_SUPPORTED_EXTENSIONS = ['.srt', '.ass', '.ssa', '.sub', '.idx']
SUBTITLE_EXTENSIONS = ['.srt', '.vtt', '.sbv', '.sub', '.ass', '.ssa', '.dfxp', '.ttml', '.itt', '.stl', '.idx']
VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.avi', '.webm', '.flv', '.mov', '.wmv', '.mpg', '.mpeg', '.m4v', '.3gp', '.h264', '.h265', '.hevc']
# Colors
DEFULT_BUTTON_COLOR = "gray50"
DEFAULT_BUTTON_COLOR_ACTIVE = "gray40"
BUTTON_COLOR_MANUAL = "#32993a"
BUTTON_COLOR_MANUAL_ACTIVE = "#2d8a35"
BUTTON_COLOR_AUTO = "royal blue"
BUTTON_COLOR_AUTO_ACTIVE = "RoyalBlue3"
BUTTON_COLOR_BATCH = "#b05958"
BUTTON_COLOR_BATCH_ACTIVE = "#a15150"
BUTTON_COLOR_BATCH_OPTIONS = "gray80"
BUTTON_COLOR_BATCH_OPTIONS_ACTIVE = "gray70"
COLOR_PRIMARY = "#C0C0C0"       # Inactive tab color
COLOR_SECONDARY = "#707070"     # Active tab color
COLOR_BACKGROUND = "SystemButtonFace"    # Background color
COLOR_TEXT = "black"            # Text color
COLOR_PROGRESSBAR = "#00a31e"  # Bright green color for progress bar
# Tooltip texts for checkboxes
TOOLTIP_SAVE_TO_DESKTOP = "Check this box if you want to save the new subtitle to your Desktop. If unchecked, it will be saved in the original subtitle's folder."
TOOLTIP_REPLACE_ORIGINAL = "Check this box if you want to replace the original subtitle file with the new one. Please be careful. It will overwrite the current subtitle."
TOOLTIP_GSS = "--gss: Use golden-section search to find the optimal ratio between video and subtitle framerates (by default, only a few common ratios are evaluated)"
TOOLTIP_VAD = "--vad=auditok: Auditok can sometimes work better in the case of low-quality audio than WebRTC's VAD. Auditok does not specifically detect voice, but instead detects all audio; this property can yield suboptimal syncing behavior when a proper VAD can work well, but can be effective in some cases."
TOOLTIP_FRAMERATE = "--no-fix-framerate: If specified, ffsubsync will not attempt to correct a framerate mismatch between reference and subtitles. This can be useful when you know that the video and subtitle framerates are same, only the subtitles are out of sync."
TOOLTIP_ALASS_SPEED_OPTIMIZATION = "--speed optimization 0: Disable speed optimization for better accuracy. This will increase the processing time."
TOOLTIP_ALASS_DISABLE_FPS_GUESSING = "--disable-fps-guessing: Disables guessing and correcting of framerate differences between reference file and input file."
TOOLTIP_TEXT_ACTION_MENU_AUTO = "Choose what to do with the synchronized subtitle file(s).\n\nNote: Existing subtitle files will be backed up in the same folder, if they need to be replaced."
TOOLTIP_TEXT_SYNC_TOOL_MENU_AUTO = "Select the tool to use for synchronization."
# Dialogs - Buttons
TAB_AUTOMATIC_SYNC = 'Automatic Sync'
TAB_MANUAL_SYNC = 'Manual Sync'
CANCEL_TEXT = 'Cancel'
GENERATE_AGAIN_TEXT = 'Generate Again'
GO_BACK = 'Go Back'
BATCH_MODE_TEXT = 'Batch Mode'
NORMAL_MODE_TEXT = 'Normal Mode'
START_AUTOMATIC_SYNC_TEXT = 'Start Automatic Sync'
START_BATCH_SYNC_TEXT = 'Start Batch Sync'
BATCH_INPUT_LABEL = "Drag and drop multiple files/folders here or click to browse.\n\n(Videos and subtitles that have the same filenames will be\n paired automatically. You need to pair others manually.)"
BATCH_INPUT_TEXT = "Batch Processing Mode"
SHIFT_SUBTITLE_TEXT = 'Shift Subtitle'
LABEL_SHIFT_SUBTITLE = "Shift subtitle by (milliseconds):"
REPLACE_ORIGINAL_TITLE = "Subtitle Change Confirmation"
REPLACE_ORIGINAL_TEXT = "Adjusting again by {milliseconds}ms, will make a total difference of {total_shifted}ms. Proceed?"
FILE_EXISTS_TITLE = "File Exists"
FILE_EXISTS_TEXT = "A file with the name '{filename}' already exists. Do you want to replace it?"
ALREADY_SYNCED_FILES_TITLE = "Already Synced Files Detected"
ALREADY_SYNCED_FILES_MESSAGE = "Detected {count} subtitle(s) already synced, because there are subtitles that have 'autosync_' prefix in the same folder with same filenames. Do you want to skip processing them?\n\n(Even if you say no, your existing subtitles will not be overwritten. The subtitle will be saved with different name.)"
SUBTITLE_INPUT_TEXT = "Drag and drop the unsynchronized subtitle file here or click to browse."
VIDEO_INPUT_TEXT = "Drag and drop video or reference subtitle file here or click to browse."
LABEL_DROP_BOX = "Drag and drop subtitle file here or click to browse."
# Options
SYNC_TOOL_FFSUBSYNC = "ffsubsync"
SYNC_TOOL_ALASS = "alass"
OPTION_SAVE_NEXT_TO_SUBTITLE = "Save next to subtitle"
OPTION_SAVE_NEXT_TO_VIDEO = "Save next to video"
OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME = "Save next to video with same filename"
OPTION_SAVE_TO_DESKTOP = "Save to Desktop"
OPTION_REPLACE_ORIGINAL_SUBTITLE = "Replace original subtitle"
OPTION_SELECT_DESTINATION_FOLDER = "Select destination folder"
CHECKBOX_NO_FIX_FRAMERATE = "Don't fix framerate"
CHECKBOX_GSS = "Use golden-section search"
CHECKBOX_VAD = "Use auditok instead of WebRTC's VAD"
LABEL_SPLIT_PENALTY = "Split Penalty (Default: 7, Recommended: 5-20, No splits: 0)"
PAIR_FILES_TITLE = "Pair Files"
PAIR_FILES_MESSAGE = "The subtitle and video have different filenames. Do you want to pair them?"
UNPAIRED_SUBTITLES_TITLE = "Unpaired Subtitles"
UNPAIRED_SUBTITLES_MESSAGE = "There are {unpaired_count} unpaired subtitle(s). Do you want to add them as subtitles with [no video] tag?"
NO_VIDEO = "[no video]"
NO_SUBTITLE = "[no subtitle]"
VIDEO_OR_SUBTITLE_TEXT = "Video or subtitle"
VIDEO_INPUT_LABEL = "Video/Reference subtitle"
SUBTITLE_INPUT_LABEL = "Subtitle"
SUBTITLE_FILES_TEXT = "Subtitle files"
CONTEXT_MENU_REMOVE = "Remove"
CONTEXT_MENU_CHANGE = "Change"
CONTEXT_MENU_ADD_PAIR = "Add Pair"
CONTEXT_MENU_CLEAR_ALL = "Clear All"
CONTEXT_MENU_SHOW_PATH = "Show path"
BUTTON_ADD_FILES = "Add files"
MENU_ADD_FOLDER = "Add Folder"
MENU_ADD_MULTIPLE_FILES = "Add Multiple Files"
ALASS_SPEED_OPTIMIZATION_TEXT = "Disable speed optimization"
ALASS_DISABLE_FPS_GUESSING_TEXT = "Disable FPS guessing"
# Log messages
SUCCESS_LOG_TEXT = "Success! Subtitle shifted by {milliseconds} milliseconds and saved to: {new_subtitle_file}"
SYNC_SUCCESS_MESSAGE = "Success! Synchronized subtitle saved to: {output_subtitle_file}"
ERROR_SAVING_SUBTITLE = "Error saving subtitle file: {error_message}"
NON_ZERO_MILLISECONDS = "Please enter a non-zero value for milliseconds."
SELECT_ONLY_ONE_OPTION = "Please select only one option: Save to Desktop or Replace Original Subtitle."
VALID_NUMBER_MILLISECONDS = "Please enter a valid number of milliseconds."
SELECT_SUBTITLE = "Please select a subtitle file."
SELECT_VIDEO = "Please select a video file."
SELECT_VIDEO_OR_SUBTITLE = "Please select a video or reference subtitle."
DROP_VIDEO_SUBTITLE_PAIR = "Please drop a video, subtitle or pair."
DROP_VIDEO_OR_SUBTITLE = "Please drop a video or reference subtitle file."
DROP_SUBTITLE_FILE = "Please drop a subtitle file."
DROP_SINGLE_SUBTITLE_FILE = "Please drop a single subtitle file."
DROP_SINGLE_SUBTITLE_PAIR = "Please drop a single subtitle or pair."
SELECT_BOTH_FILES = "Please select both video/reference subtitle and subtitle file."
SELECT_DIFFERENT_FILES = "Please select different subtitle files."
SUBTITLE_FILE_NOT_EXIST = "Subtitle file do not exist."
VIDEO_FILE_NOT_EXIST = "Video file do not exist."
ERROR_LOADING_SUBTITLE = "Error loading subtitle file: {error_message}"
ERROR_CONVERT_TIMESTAMP = "Failed to convert timestamp '{timestamp}' for format '{format_type}'"
ERROR_PARSING_TIME_STRING = "Error parsing time string '{time_str}'"
ERROR_PARSING_TIME_STRING2 = "Error parsing time string '{time_str}' for format '{format_type}': {error_message}"
NO_FILES_TO_SYNC = "No files to sync. Please add files to the batch list."
NO_VALID_FILE_PAIRS = "No valid file pairs to sync."
ERROR_PROCESS_TERMINATION = "Error occurred during process termination: {error_message}"
AUTO_SYNC_CANCELLED = "Automatic synchronization cancelled."
BATCH_SYNC_CANCELLED = "Batch synchronization cancelled."
NO_SYNC_PROCESS = "No synchronization process to cancel."
INVALID_SYNC_TOOL = "Invalid sync tool selected."
FAILED_START_PROCESS = "Failed to start process: {error_message}"
ERROR_OCCURRED = "Error occurred: {error_message}"
DROP_VALID_FILES = "Please drop valid subtitle and video files."
PAIRS_ADDED = "Added {count} pair{s}"
UNPAIRED_FILES_ADDED = "Added {count} unpaired file{s}"
UNPAIRED_FILES = "{count} unpaired file{s}"
DUPLICATE_PAIRS_SKIPPED = "{count} duplicate pair{s} skipped"
PAIR_ALREADY_EXISTS = "This pair already exists."
PAIR_ADDED = "Added 1 pair."
SAME_FILE_ERROR = "Cannot use the same file for both inputs."
PAIR_ALREADY_EXISTS = "This pair already exists. Please select a different file."
SUBTITLE_ADDED = "Subtitle added."
VIDEO_ADDED = "Video/reference subtitle added."
FILE_CHANGED = "File changed."
SELECT_ITEM_TO_CHANGE = "Please select an item to change."
SELECT_ITEM_TO_REMOVE = "Please select an item to remove."
FILE_NOT_EXIST = "File specified in the argument does not exist."
MULTIPLE_ARGUMENTS = "Multiple arguments provided. Please provide only one subtitle file path."
INVALID_FILE_FORMAT = "Invalid file format. Please provide a subtitle file."
INVALID_SYNC_TOOL_SELECTED = "Invalid sync tool selected."
TEXT_SELECTED_FOLDER = "Selected folder: {}"
TEXT_NO_FOLDER_SELECTED = "No folder selected."
TEXT_DESTINATION_FOLDER_DOES_NOT_EXIST = "The selected destination folder does not exist."
# Log window messages
INVALID_PARENT_ITEM = "Invalid parent item with no values."
SKIP_NO_VIDEO_NO_SUBTITLE = "Skipping entry with no video and no subtitle."
SKIP_NO_SUBTITLE = "Skipping '{video_file}': No subtitle file."
SKIP_NO_VIDEO = "Skipping '{subtitle_file}': No video/reference file."
SKIP_UNPAIRED_ITEM = "Unpaired item skipped."
SKIPPING_ALREADY_SYNCED = "Skipping {filename}: Already synced."
CONVERTING_SUBTITLE = "Converting {file_extension} to SRT..."
ERROR_CONVERTING_SUBTITLE = "Error converting subtitle: {error_message}"
SUBTITLE_CONVERTED = "Subtitle successfully converted and saved to: {srt_file}."
ERROR_UNSUPPORTED_CONVERSION = "Error: Conversion for {file_extension} is not supported."
FAILED_CONVERT_SUBTITLE = "Failed to convert subtitle file: {subtitle_file}"
FAILED_CONVERT_VIDEO = "Failed to convert video/reference file: {video_file}"
SKIPPING_FILE_EXISTS = "Skipping {filename}: Output file exists."
SPLIT_PENALTY_ZERO = "Split penalty is set to 0. Using --no-split argument..."
SPLIT_PENALTY_SET = "Split penalty is set to {split_penalty}..."
USING_REFERENCE_SUBTITLE = "Using reference subtitle for syncing..."
USING_VIDEO_FOR_SYNC = "Using video for syncing..."
ENABLED_NO_FIX_FRAMERATE = "Enabled: Don't fix framerate."
ENABLED_GSS = "Enabled: Golden-section search."
ENABLED_AUDITOK_VAD = "Enabled: Using auditok instead of WebRTC's VAD."
SYNCING_STARTED = "Syncing started:"
SYNCING_ENDED = "Syncing ended.\n"
SYNC_SUCCESS = "Success! Synchronized subtitle saved to: {output_subtitle_file}\n\n"
SYNC_ERROR = "Error occurred during synchronization of {filename}"
SYNC_ERROR_OCCURRED = "Error occurred during synchronization. Please check the log messages."
BATCH_SYNC_COMPLETED = "Batch syncing completed."
PREPARING_SYNC = "Preparing {base_name}{file_extension} for automatic sync..."
CONVERTING_TTML = "Converting TTML/DFXP/ITT to SRT..."
CONVERTING_VTT = "Converting VTT to SRT..."
CONVERTING_SBV = "Converting SBV to SRT..."
CONVERTING_SUB = "Converting SUB to SRT..."
CONVERTING_ASS = "Converting ASS/SSA to SRT..."
CONVERTING_STL = "Converting STL to SRT..."
ERROR_CONVERTING_SUBTITLE = "Error converting subtitle: {error_message}"
CONVERSION_NOT_SUPPORTED = "Error: Conversion for {file_extension} is not supported."
SUBTITLE_CONVERTED = "Subtitle successfully converted and saved to: {srt_file}."
RETRY_ENCODING_MSG = "Previous sync failed. Retrying with pre-detected encodings...\n\n"
ALASS_SPEED_OPTIMIZATION_LOG = "Disabled: Speed optinization..."
ALASS_DISABLE_FPS_GUESSING_LOG = "Disabled: FPS guessing..."
CHANGING_ENCODING_MSG = "\nEncoding of the synced subtitle does not match the original subtitle's encoding. Changing the encoding from {synced_subtitle_encoding} to {encoding_inc}...\n"
ENCODING_CHANGED_MSG = "\nEncoding changed successfully.\n"
ERROR_CHANGING_ENCODING_MSG = "\nError changing encoding: {error_message}\n"
BACKUP_CREATED = "A backup of the existing subtitle file has been saved to: {output_subtitle_file}.\n"
# Alass integration
def find_ffmpeg_paths():
    ffmpeg_path = subprocess.check_output("where ffmpeg", shell=True).decode().strip()
    ffprobe_path = subprocess.check_output("where ffprobe", shell=True).decode().strip()
    return ffmpeg_path, ffprobe_path
ffmpeg_path, ffprobe_path = find_ffmpeg_paths()
env = os.environ.copy()
env["ALASS_FFMPEG_PATH"] = ffmpeg_path
env["ALASS_FFPROBE_PATH"] = ffprobe_path
alass_cli_path = os.path.join(os.path.dirname(__file__), "alass", "alass-cli.exe")
# Icon fix
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID((PROGRAM_NAME+"."+VERSION).lower())
os.chdir(os.path.dirname(__file__))
# Shift Subtitle Start
total_shifted_milliseconds = {}
def log_message(message, level, tab='manual'):
    print(f"[{level.upper()}] {message}")
def shift_subtitle(subtitle_file, milliseconds, save_to_desktop, replace_original):
    global total_shifted_milliseconds
    # Load file with encoding detection
    try:
        with open(subtitle_file, 'rb') as file:
            raw_data = file.read()
            encoding = chardet.detect(raw_data)['encoding']
            lines = raw_data.decode(encoding).splitlines()
    except Exception as e:
        log_message(ERROR_LOADING_SUBTITLE.format(error_message=str(e)), "error", tab='manual')
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
            separator = " --> " if format_type == 'srt' else " --> "
            return f"{start}{separator}{end}"
        return re.sub(
            r'(\d{2}:\d{2}:\d{2}[,\.]\d{3}) --> (\d{2}:\d{2}:\d{2}[,\.]\d{3})',
            replacer,
            line
        )
    def shift_time_sbv(line):
        def replacer(match):
            start = shift_timestamp(match.group(1), 'sbv')
            end = shift_timestamp(match.group(2), 'sbv')
            return f"{start},{end}"
        return re.sub(
            r'(\d+:\d{2}:\d{2}\.\d{3}),(\d+:\d{2}:\d{2}\.\d{3})',
            replacer,
            line
        )
    def shift_time_sub(line):
        def replacer(match):
            start = shift_timestamp(match.group(1), 'sub')
            end = shift_timestamp(match.group(2), 'sub')
            return f"{start},{end}"
        return re.sub(
            r'(\d{2}:\d{2}:\d{2}\.\d{2})\s*,\s*(\d{2}:\d{2}:\d{2}\.\d{2})',
            replacer,
            line
        )
    def shift_time_stl(line):
        def replacer(match):
            start = shift_timestamp(match.group(1), 'stl')
            end = shift_timestamp(match.group(2), 'stl')
            suffix = match.group(3)  # Preserve the remaining text
            return f"{start} , {end}{suffix}"
        return re.sub(
            r'(\d{1,2}:\d{2}:\d{2}:\d{2})\s*,\s*(\d{1,2}:\d{2}:\d{2}:\d{2})(.*)',
            replacer,
            line
        )
    def shift_time_dfxp(line):
        def replacer(match):
            start = shift_timestamp(match.group(1), "dfxp")
            end = shift_timestamp(match.group(2), "dfxp")
            return f'begin="{start}" end="{end}"'
        return re.sub(
            r'begin="([\d:,\.]+)"\s+end="([\d:,\.]+)"',
            replacer,
            line
        )
    def shift_time_ttml(line):
        # Replace the 'begin' attribute
        line = re.sub(
            r'\bbegin="([^"]+)"',
            lambda m: f'begin="{shift_timestamp(m.group(1), "ttml", m.group(1))}"',
            line
        )
        # Replace the 'end' attribute
        line = re.sub(
            r'\bend="([^"]+)"',
            lambda m: f'end="{shift_timestamp(m.group(1), "ttml", m.group(1))}"',
            line
        )
        return line
    def shift_time_ass_ssa(line):
        def replacer(match):
            start = shift_timestamp(match.group(1), 'ass_ssa')
            end = shift_timestamp(match.group(2), 'ass_ssa')
            return f"{start},{end}"
        return re.sub(
            r'(\d{1,2}:\d{2}:\d{2}\.\d{2}),(\d{1,2}:\d{2}:\d{2}\.\d{2})',
            replacer,
            line
        )
    # Helper to shift individual timestamps
    def shift_timestamp(timestamp, format_type, original_time_str=None):
        ms = time_to_milliseconds(timestamp, format_type)
        if ms is None:
            log_message(ERROR_CONVERT_TIMESTAMP.format(timestamp=timestamp, format_type=format_type), "error")
            return timestamp
        ms += milliseconds
        ms = max(ms, 0)
        shifted_timestamp = milliseconds_to_time(ms, format_type, original_time_str)
        return shifted_timestamp
    # Time conversion functions to handle various formats accurately
    def time_to_milliseconds(time_str, format_type):
        try:
            if format_type in ['srt', 'vtt']:
                parts = re.split(r'[:,.]', time_str)
                h, m, s = map(int, parts[:3])
                ms = int(parts[3])
                return (h * 3600 + m * 60 + s) * 1000 + ms
            elif format_type == 'sbv':
                parts = re.split(r'[:.]', time_str)
                h, m, s, ms = map(int, parts)
                return (h * 3600 + m * 60 + s) * 1000 + ms
            elif format_type == 'sub':
                parts = re.split(r'[:.]', time_str)
                h, m, s, cs = map(int, parts)
                return (h * 3600 + m * 60 + s) * 1000 + (cs * 10)
            elif format_type == 'stl':
                parts = re.split(r'[:.]', time_str)
                h, m, s, f = map(int, parts)
                return (h * 3600 + m * 60 + s) * 1000 + (f * 40)  # Assuming 25 fps
            elif format_type == 'dfxp':
                parts = re.split(r'[:.,]', time_str)
                h, m, s = map(int, parts[:3])
                ms = int(parts[3].replace(',', '')) if len(parts) > 3 else 0
                return (h * 3600 + m * 60 + s) * 1000 + ms
            elif format_type in ['itt', 'ttml']:
                if ':' in time_str:
                    # Handle 'HH:MM:SS.MS' and 'HH:MM:SS:FF' (SMPTE) formats
                    # Check for 'HH:MM:SS.MS' format
                    matches = re.match(r'^(\d+):(\d{2}):(\d{2})(?:\.(\d+))?$', time_str)
                    if matches:
                        h = int(matches.group(1))
                        m = int(matches.group(2))
                        s = int(matches.group(3))
                        ms_str = matches.group(4) or '0'
                        ms = int(ms_str.ljust(3, '0')[:3])
                        return (h * 3600 + m * 60 + s) * 1000 + ms
                    # Check for 'HH:MM:SS:FF' (SMPTE) format
                    matches = re.match(r'^(\d+):(\d{2}):(\d{2}):(\d+)$', time_str)
                    if matches:
                        h = int(matches.group(1))
                        m = int(matches.group(2))
                        s = int(matches.group(3))
                        frames = int(matches.group(4))
                        # Assuming 25 fps
                        ms = int(frames * (1000 / 25))
                        return (h * 3600 + m * 60 + s) * 1000 + ms
                    else:
                        log_message(ERROR_PARSING_TIME_STRING.format(time_str=time_str), "error", tab='manual')
                        return None
                else:
                    # Handle 'SSSSSS.MS' seconds format
                    seconds_match = re.match(r'^(\d+(?:\.\d+)?)(?:s)?$', time_str)
                    if seconds_match:
                        total_seconds = float(seconds_match.group(1))
                        return int(total_seconds * 1000)
                    else:
                        log_message(ERROR_PARSING_TIME_STRING.format(time_str=time_str), "error", tab='manual')
                        return None
            elif format_type == 'ass_ssa':
                parts = re.split(r'[:.]', time_str)
                h, m, s, cs = map(int, parts)
                return (h * 3600 + m * 60 + s) * 1000 + (cs * 10)
        except (ValueError, IndexError) as e:
            log_message(ERROR_PARSING_TIME_STRING2.format(time_str=time_str, format_type=format_type, error_message=str(e)), "error", tab='manual')
            return None

    def milliseconds_to_time(ms, format_type, original_time_str=None):
        h = ms // 3600000
        m = (ms // 60000) % 60
        s = (ms // 1000) % 60
        ms_remainder = ms % 1000
        if format_type == 'srt':
            return f"{h:02}:{m:02}:{s:02},{ms_remainder:03}"
        elif format_type == 'vtt':
            return f"{h:02}:{m:02}:{s:02}.{ms_remainder:03}"
        elif format_type == 'sbv':
            return f"{h}:{m:02}:{s:02}.{ms_remainder:03}"
        elif format_type == 'sub':
            cs = ms_remainder // 10
            return f"{h:02}:{m:02}:{s:02}.{cs:02}"
        elif format_type == 'stl':
            f = ms_remainder // 40  # Assuming 25 fps
            return f"{h:02}:{m:02}:{s:02}:{f:02}"
        elif format_type == 'dfxp':
            return f"{h:02}:{m:02}:{s:02},{ms_remainder:03}"
        elif format_type in ['ttml', 'itt']:
            if original_time_str:
                if ':' in original_time_str:
                    if '.' in original_time_str:
                        # Original format is 'HH:MM:SS.MS' with flexible milliseconds
                        timestamp = f"{h:02}:{m:02}:{s:02}.{ms_remainder:03}"
                        return timestamp
                    elif ':' in original_time_str:
                        # Original format is 'HH:MM:SS:FF' (SMPTE)
                        frame_rate = 25  # Assuming 25 fps
                        frames = int(round(ms_remainder / 1000 * frame_rate))
                        return f"{h:02}:{m:02}:{s:02}:{frames:02}"
                    else:
                        # Original format is 'HH:MM:SS' without milliseconds
                        return f"{h:02}:{m:02}:{s:02}"
                else:
                    # Original format is seconds 'SSSSSs'
                    total_seconds = ms / 1000
                    timestamp = f"{total_seconds:.3f}".rstrip('0').rstrip('.') + 's'
                    return timestamp
            else:
                # Default TTML format
                return f"{h:02}:{m:02}:{s:02}.{ms_remainder:03}"
        elif format_type == 'ass_ssa':
            cs = ms_remainder // 10
            return f"{h}:{m:02}:{s:02}.{cs:02}"
    # Process each line based on format type
    for line in lines:
        if file_extension == '.srt':
            new_lines.append(shift_time_srt_vtt(line, 'srt') if '-->' in line else line)
        elif file_extension == '.vtt':
            new_lines.append(shift_time_srt_vtt(line, 'vtt') if '-->' in line else line)
        elif file_extension == '.sbv':
            new_lines.append(shift_time_sbv(line) if ',' in line else line)
        elif file_extension == '.sub':
            new_lines.append(shift_time_sub(line) if ',' in line else line)
        elif file_extension == '.stl':
            new_lines.append(shift_time_stl(line) if ',' in line else line)
        elif file_extension == '.dfxp':
            new_lines.append(shift_time_dfxp(line))
        elif file_extension in ['.ttml', '.itt']:
            new_lines.append(shift_time_ttml(line))
        elif file_extension in ['.ass', '.ssa']:
            new_lines.append(shift_time_ass_ssa(line))
        else:
            new_lines.append(line)
    # Define file save location and handle existing files
    if replace_original:
        new_subtitle_file = subtitle_file
        if subtitle_file in total_shifted_milliseconds:
            message_text = REPLACE_ORIGINAL_TEXT.format(milliseconds=milliseconds, total_shifted=total_shifted)
            response = messagebox.askyesno(
                            REPLACE_ORIGINAL_TITLE,
                            message_text
            )
            if not response:
                return
    elif save_to_desktop:
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        new_subtitle_file = os.path.join(desktop_path, f"{total_shifted}ms_{filename}")
    else:
        new_subtitle_file = os.path.join(os.path.dirname(subtitle_file), f"{total_shifted}ms_{filename}")
    if os.path.exists(new_subtitle_file) and not replace_original:
        file_exists_text = FILE_EXISTS_TEXT.format(filename=os.path.basename(new_subtitle_file))
        replace = messagebox.askyesno(
                    FILE_EXISTS_TITLE,
                    file_exists_text
                )
        if not replace:
            return
    def update_progress(progress_bar, value):
        progress_bar["value"] = value
        if value < 100:
            root.after(10, update_progress, progress_bar, value + 3)
        else:
            # Hide the progress bar after completions
            progress_bar.grid_forget()
            log_message(SUCCESS_LOG_TEXT.format(milliseconds=milliseconds, new_subtitle_file=new_subtitle_file), "success", new_subtitle_file, tab='manual')
    try:
        # Write to file after progress bar is fully loaded
        with open(new_subtitle_file, 'wb') as file:
            file.write('\n'.join(new_lines).encode(encoding))
        # Hide current log message
        label_message_manual.grid_forget()
        # Create a progress bar
        progress_bar = ttk.Progressbar(root, orient="horizontal", length=200, mode="determinate")
        progress_bar.grid(row=5, column=0, columnspan=5, padx=10, pady=(0, 10), sticky="ew")
        update_progress(progress_bar, 0)
        if replace_original:
            total_shifted_milliseconds[subtitle_file] = total_shifted
    except Exception as e:
        log_message(ERROR_SAVING_SUBTITLE.format(error_message=str(e)), "error", tab='manual')
# Shift Subtitle End

def sync_subtitle():
    if hasattr(label_drop_box, 'tooltip_text'):
        subtitle_file = label_drop_box.tooltip_text
        if subtitle_file:
            try:
                milliseconds = int(entry_milliseconds.get())
                if milliseconds == 0:
                    log_message(NON_ZERO_MILLISECONDS, "error", tab='manual')
                    return
                save_to_desktop = save_to_desktop_var.get()  # Get the value of the save_to_desktop switch
                replace_original = replace_original_var.get()  # Get the value of the replace_original switch
                if save_to_desktop and replace_original:
                    log_message(SELECT_ONLY_ONE_OPTION, "error")
                    return
                # Shift subtitle in a separate thread to keep the GUI responsive
                threading.Thread(target=shift_subtitle, args=(subtitle_file, milliseconds, save_to_desktop, replace_original)).start()
            except ValueError:
                log_message(VALID_NUMBER_MILLISECONDS, "error", tab='manual')
    else:
        log_message(SELECT_SUBTITLE, "error", tab='manual')

def on_enter(event):
    event.widget.config(bg="lightblue")

def on_leave(event):
    if hasattr(event.widget, 'tooltip_text'):
        event.widget.config(bg="lightgreen")
    else:
        event.widget.config(bg="lightgray")

current_log_type = None
def log_message(message, msg_type=None, filepath=None, tab='both'):
    global current_log_type
    font_style = ("Arial", 8, "bold")
    if msg_type == "error":
        current_log_type = "error"
        color = "red"
        bg_color = "RosyBrown1"
    elif msg_type == "success":
        current_log_type = "success"
        color = "green"
        bg_color = "lightgreen"
    elif msg_type == "info":
        current_log_type = "info"
        color = "black"
        bg_color = "lightgoldenrodyellow"
    else:
        current_log_type = None
        color = "black"
        bg_color = "lightgrey"
    if tab in ['both', 'auto']:
        label_message_auto.config(text=message, fg=color, bg=bg_color, font=font_style)
        if message:
            label_message_auto.grid(row=10, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")
        else:
            label_message_auto.grid_forget()
    if tab in ['both', 'manual']:
        label_message_manual.config(text=message, fg=color, bg=bg_color, font=font_style)
        if message:
            label_message_manual.grid(row=5, column=0, columnspan=5, padx=10, pady=(0, 10), sticky="ew")
        else:
            label_message_manual.grid_forget()
    if msg_type == "success" and filepath:
        message += f" Click to open: {filepath}"
        label_message_auto.config(cursor="hand2")
        label_message_manual.config(cursor="hand2")
        label_message_auto.bind("<Button-1>", lambda event: open_directory(filepath))
        label_message_manual.bind("<Button-1>", lambda event: open_directory(filepath))
    else:
        label_message_auto.config(cursor="")
        label_message_manual.config(cursor="")
        label_message_auto.unbind("<Button-1>")
        label_message_manual.unbind("<Button-1>")
    label_message_auto.update_idletasks()
    label_message_manual.update_idletasks()

def open_directory(filepath):
    directory = os.path.dirname(filepath)
    if os.path.isdir(directory):
        # Select the file in the file explorer
        selected_file = os.path.realpath(filepath)
        subprocess.run(f'explorer /select,"{selected_file}"')

def update_wraplengt(event=None):
    event.widget.config(wraplength=event.widget.winfo_width() - 60)

def checkbox_selected(var):
    if var.get():
        if var == save_to_desktop_var:
            replace_original_var.set(False)
        elif var == replace_original_var:
            save_to_desktop_var.set(False)
            
def place_window_top_right(event=None, margin=50):
    width = root.winfo_width()
    height = root.winfo_height()
    x = root.winfo_screenwidth() - width - margin - 10
    y = margin
    root.geometry('{}x{}+{}+{}'.format(width, height, x, y))

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
    def show_tooltip(self, event=None):
        if self.tooltip is None:
            # Get the position of the widget
            x_pos = self.widget.winfo_rootx()
            y_pos = self.widget.winfo_rooty() + self.widget.winfo_height()  # Adjust tooltip position below the widget
            # Calculate the screen dimensions
            screen_width = self.widget.winfo_screenwidth()
            screen_height = self.widget.winfo_screenheight()
            # Create a temporary label to calculate the width based on content
            temp_label = tk.Label(text=self.text, font=("tahoma", "8", "normal"))
            temp_label.update_idletasks()
            content_width = temp_label.winfo_reqwidth()  # Get the required width of the content
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
            if y_pos < 0:
                y_pos = 0
            # Adjust tooltip position if too far to the left
            if x_pos < 0:
                x_pos = 0
            self.tooltip.wm_geometry("+%d+%d" % (x_pos, y_pos))
            label = tk.Label(self.tooltip, text=self.text, justify=tk.LEFT, wraplength=wraplength, background="#ffffe0", relief=tk.SOLID, borderwidth=1, font=("tahoma", "8", "normal"))
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

root = TkinterDnD.Tk()
root.title(PROGRAM_NAME +" "+VERSION)
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)  # Allow label_drop_box to fill empty space
root.withdraw() # Hide the window while it's being built
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
# Add "GitHub" label on the right side of the tabs
github_label = ttk.Label(root, text="GitHub", cursor="hand2", foreground="#007FFF", background="SystemButtonFace", underline=True)
github_label.bind("<Button-1>", lambda event: os.system("start "+GITHUB_URL))
github_label.grid(row=0, column=0, sticky="ne", padx=10, pady=(10,0))
# Customizing the style of the tabs
style = ttk.Style()
# Set custom theme
style.theme_create("custom", parent="alt", settings={
    "TNotebook": {
        "configure": {
            "tabposition": "nw",
            "tabmargins": [10, 5, 2, 0],
            "background": COLOR_BACKGROUND,
            "borderwidth": 0,
        }
    },
    "TNotebook.Tab": {
        "configure": {
            "padding": [15, 5],
            "font": ("TkDefaultFont", 10, "normal"),
            "background": COLOR_PRIMARY,
            "foreground": COLOR_TEXT,
            "borderwidth": 1,
        },
        "map": {
            "background": [("selected", COLOR_SECONDARY)],
            "foreground": [("selected", "white")]
        }
    },
    "TFrame": {
        "configure": {
            "background": COLOR_BACKGROUND
        }
    },
    "TProgressbar": {
        "configure": {
            "background": COLOR_PROGRESSBAR,
            "troughcolor": COLOR_BACKGROUND,
            "borderwidth": 1
        }
    }
})
style.theme_use("custom")
add_separator = ttk.Separator(automatic_tab, orient='horizontal')
add_separator.grid(row=0, column=0, sticky="new", padx=11, pady=0, columnspan=6)
add_separator = ttk.Separator(manual_tab, orient='horizontal')
add_separator.grid(row=0, column=0, sticky="new", padx=11, pady=0, columnspan=6)
style.map("TSeparator", background=[("","SystemButtonFace")])

# ---------------- Automatic Tab ---------------- #
# Convert subtitles to SRT Begin
def convert_sub_to_srt(input_file, output_file):
    with open(input_file, 'rb') as sub_file:
        sub_data = sub_file.read()
        encoding = chardet.detect(sub_data)['encoding']
    with open(input_file, 'r', encoding=encoding, errors='replace') as sub, open(output_file, 'w', encoding='utf-8') as srt:
        srt_counter = 1
        while True:
            timestamps = sub.readline().strip()
            if not timestamps:
                break
            text_lines = []
            while True:
                line = sub.readline().strip()
                if not line:
                    break
                text_lines.append(line.replace('[br]', '\n'))
            start, end = timestamps.split(',')
            formatted_start = format_sub_time(start)
            formatted_end = format_sub_time(end)
            srt.write(f"{srt_counter}\n")
            srt.write(f"{formatted_start} --> {formatted_end}\n")
            srt.write('\n'.join(text_lines) + '\n\n')
            srt_counter += 1

def convert_ass_to_srt(input_file, output_file):
    with open(input_file, 'rb') as ass_file:
        ass_data = ass_file.read()
        encoding = chardet.detect(ass_data)['encoding']
    with open(input_file, 'r', encoding=encoding, errors='replace') as ass, open(output_file, 'w', encoding='utf-8') as srt:
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

def convert_ttml_or_dfxp_to_srt(input_file, output_file):
    try:
        with open(input_file, 'rb') as file:
            data = file.read()
            encoding = chardet.detect(data)['encoding']
            content = data.decode(encoding, errors='replace')
        root = ET.fromstring(content)
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return
    captions = [elem for elem in root.iter() if strip_namespace(elem.tag) == 'p']
    with open(output_file, 'w', encoding='utf-8') as srt:
        for idx, caption in enumerate(captions, 1):
            begin = format_ttml_time(caption.attrib.get('begin'))
            end = format_ttml_time(caption.attrib.get('end'))
            def process_element(elem):
                text = ''
                tag = strip_namespace(elem.tag)
                end_tags = []
                # Handle start tags
                if tag == 'br':
                    text += '\n'
                elif tag in ['b', 'i', 'u', 'font']:
                    text += f"<{tag}>"
                    end_tags.insert(0, f"</{tag}>")
                elif tag == 'span':
                    style = elem.attrib.get('style', '')
                    styles = style.strip().lower().split()
                    for style_attr in styles:
                        if style_attr == 'bold':
                            text += '<b>'
                            end_tags.insert(0, '</b>')
                        elif style_attr == 'italic':
                            text += '<i>'
                            end_tags.insert(0, '</i>')
                        elif style_attr == 'underline':
                            text += '<u>'
                            end_tags.insert(0, '</u>')
                    if 'color' in elem.attrib:
                        color = elem.attrib['color']
                        text += f'<font color="{color}">'
                        end_tags.insert(0, '</font>')
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

def convert_vtt_to_srt(input_file, output_file):
    with open(input_file, 'rb') as vtt_file:
        vtt_data = vtt_file.read()
        encoding = chardet.detect(vtt_data)['encoding']
    with open(input_file, 'r', encoding=encoding, errors='replace') as vtt, open(output_file, 'w', encoding='utf-8') as srt:
        srt_counter = 1
        allowed_tags = ['b', 'i', 'u', 'font']
        tag_pattern = re.compile(r'</?(?!' + '|'.join(allowed_tags) + r')\w+[^>]*>')
        for line in vtt:
            match = re.match(r'(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})', line)
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
                    cleaned_line = tag_pattern.sub('', next_line)
                    text += cleaned_line + "\n"
                srt.write(f"{text.strip()}\n\n")

def convert_sbv_to_srt(input_file, output_file):
    with open(input_file, 'rb') as sbv_file:
        sbv_data = sbv_file.read()
        encoding = chardet.detect(sbv_data)['encoding']
    with open(input_file, 'r', encoding=encoding, errors='replace') as sbv, open(output_file, 'w', encoding='utf-8') as srt:
        srt_counter = 1
        allowed_tags = ['b', 'i', 'u', 'font']
        tag_pattern = re.compile(r'</?(?!' + '|'.join(allowed_tags) + r')\w+[^>]*>')
        timestamp_pattern = re.compile(r'\d+:\d+:\d+\.\d+,\d+:\d+:\d+\.\d+')
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
                cleaned_line = tag_pattern.sub('', line)
                text_lines.append(cleaned_line)
            if ',' in timestamps:
                start, end = timestamps.split(',')
                srt.write(f"{srt_counter}\n")
                srt.write(f"{format_sbv_time(start)} --> {format_sbv_time(end)}\n")
                srt.write('\n'.join(text_lines) + '\n')
                srt_counter += 1

def convert_stl_to_srt(input_file, output_file):
    with open(input_file, 'rb') as stl:
        stl_data = stl.read()
        encoding = chardet.detect(stl_data)['encoding']
        lines = stl_data.decode(encoding, errors='replace').splitlines()
    with open(output_file, 'w', encoding='utf-8') as srt:
        srt_counter = 1
        for line in lines:
            parts = line.strip().split(',', 2)  # Split only on the first two commas
            if len(parts) >= 3:
                start = convert_stl_time(parts[0].strip())
                end = convert_stl_time(parts[1].strip())
                text = parts[2].strip().replace('| ', '\n').replace('|', '\n')  # Replace '|' with newline
                if text:  # Ensure text is not empty
                    srt.write(f"{srt_counter}\n")
                    srt.write(f"{start} --> {end}\n")
                    srt.write(f"{text}\n\n")
                    srt_counter += 1

def format_ttml_time(timestamp):
    # Remove 's' suffix if present
    timestamp = timestamp.replace('s', '')
    # Check for SMPTE format HH:MM:SS:FF
    if timestamp.count(':') == 3:
        try:
            hours, minutes, seconds, frames = map(int, timestamp.split(':'))
            frame_rate = 25  # Adjust frame rate as needed
            milliseconds = int((frames / frame_rate) * 1000)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
        except ValueError:
            return timestamp
    # Check if already in HH:MM:SS format
    elif ':' in timestamp:
        return timestamp.replace('.', ',')
    # Convert from seconds to HH:MM:SS,mmm
    else:
        try:
            seconds = float(timestamp)
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            seconds = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace('.', ',')
        except ValueError:
            return timestamp

def format_sub_time(time_str):
    parts = re.split(r'[:.]', time_str)
    h, m, s, ms = parts
    ms = ms.ljust(3, '0')[:3] # Ensure milliseconds are 3 digits
    return f"{int(h):02}:{int(m):02}:{int(s):02},{ms}"

def format_sbv_time(time_str):
    h, m, s = time_str.split(':')
    s = s.replace('.', ',')
    return f"{int(h):02}:{int(m):02}:{s}"

def format_ass_time(time_str):
    t = time_str.split(':')
    hours = int(t[0])
    minutes = int(t[1])
    seconds = float(t[2])
    return f"{hours:02}:{minutes:02}:{int(seconds):02},{int((seconds - int(seconds)) * 1000):03}"

def convert_stl_time(time_str):
    h, m, s, f = map(int, time_str.split(':'))
    total_seconds = h * 3600 + m * 60 + s + f / 30
    ms = int((total_seconds - int(total_seconds)) * 1000)
    return f"{int(total_seconds)//3600:02}:{(int(total_seconds)%3600)//60:02}:{int(total_seconds)%60:02},{ms:03}"

def strip_namespace(tag):
    if '}' in tag:
        return tag.split('}', 1)[1]
    return tag

def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    result = chardet.detect(raw_data)
    encoding = result['encoding']
    return encoding

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

# Convert subtitles to SRT End
def start_batch_sync():
    global selected_destination_folder
    sync_tool = sync_tool_var_auto.get()
    if sync_tool == SYNC_TOOL_ALASS:
        SUPPORTED_SUBTITLE_EXTENSIONS = ALASS_SUPPORTED_EXTENSIONS
    elif sync_tool == 'ffsubsync':
        SUPPORTED_SUBTITLE_EXTENSIONS = FFSUBSYNC_SUPPORTED_EXTENSIONS
    global process_list, output_subtitle_files
    process_list = []
    output_subtitle_files = []
    tree_items = treeview.get_children()
    if action_var_auto.get()  == OPTION_SELECT_DESTINATION_FOLDER:
        if not os.path.exists(selected_destination_folder):
            log_message(TEXT_DESTINATION_FOLDER_DOES_NOT_EXIST, "error", tab='auto')
            return
    if not tree_items:
        log_message(NO_FILES_TO_SYNC, "error", tab='auto')
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
            if (video_file and subtitle_file):
                valid_pairs += 1
    if valid_pairs == 0:
        log_message(NO_VALID_FILE_PAIRS, "error", tab='auto')
        return
    
    total_items = valid_pairs
    completed_items = 0
    cancel_flag = False

    def cancel_batch_sync():
        nonlocal cancel_flag
        cancel_flag = True
        for process in process_list:
            if process and process.poll() is None:
                try:
                    subprocess.Popen(['taskkill', '/F', '/T', '/PID', str(process.pid)],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
                except Exception as e:
                    log_message(ERROR_PROCESS_TERMINATION.format(error_message=str(e)), "error", tab='auto')
        log_message(BATCH_SYNC_CANCELLED, "error", tab='auto')
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
            ffsubsync_option_vad.grid_remove()
            ffsubsync_option_framerate.grid_remove()
        else:
            ffsubsync_option_gss.grid()
            ffsubsync_option_vad.grid()
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
        batch_input.grid(row=0, column=0, padx=10, pady=(10,0), sticky="nsew", columnspan=2, rowspan=2)
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
            ffsubsync_option_vad.grid_remove()
            ffsubsync_option_framerate.grid_remove()
        else:
            ffsubsync_option_gss.grid()
            ffsubsync_option_vad.grid()
            ffsubsync_option_framerate.grid()
            alass_split_penalty_slider.grid_remove()
            alass_disable_fps_guessing.grid_remove()
            alass_speed_optimization.grid_remove()
        label_message_auto.grid_remove()
        automatic_tab.columnconfigure(0, weight=0)
        root.update_idletasks()

    # Convert files if necessary
    def convert_to_srt(subtitle_file):
        file_extension = os.path.splitext(subtitle_file)[-1].lower()
        original_base_name = os.path.basename(os.path.splitext(subtitle_file)[0])  # Store original base name
        srt_file = os.path.join(os.path.dirname(subtitle_file), 'converted_' + original_base_name + '.srt')
        log_window.insert(tk.END, f"{PREPARING_SYNC.format(base_name=original_base_name, file_extension=file_extension)}\n")
        converters = {
            '.ttml': convert_ttml_or_dfxp_to_srt,
            '.dfxp': convert_ttml_or_dfxp_to_srt,
            '.itt': convert_ttml_or_dfxp_to_srt,
            '.vtt': convert_vtt_to_srt,
            '.sbv': convert_sbv_to_srt,
            '.sub': convert_sub_to_srt,
            '.ass': convert_ass_to_srt,
            '.ssa': convert_ass_to_srt,
            '.stl': convert_stl_to_srt
        }
        converter = converters.get(file_extension)
        if converter:
            try:
                log_window.insert(tk.END, f"{CONVERTING_SUBTITLE.format(file_extension=file_extension.upper())}\n")
                converter(subtitle_file, srt_file)
            except Exception as e:
                log_window.insert(tk.END, f"{ERROR_CONVERTING_SUBTITLE.format(error_message=str(e))}\n")
                return None
            log_window.insert(tk.END, f"{SUBTITLE_CONVERTED.format(srt_file=srt_file)}\n")
            return srt_file
        else:
            log_window.insert(tk.END, f"{ERROR_UNSUPPORTED_CONVERSION.format(file_extension=file_extension)}\n")
            return None
    def convert_files():
        nonlocal subtitle_file, video_file
        original_base_name = os.path.splitext(os.path.basename(subtitle_file))[0]
        # Convert subtitle file if necessary
        unsupported_extensions = [ext for ext in SUBTITLE_EXTENSIONS if ext not in SUPPORTED_SUBTITLE_EXTENSIONS]
        if subtitle_file.lower().endswith(tuple(unsupported_extensions)):
            subtitle_file_converted = convert_to_srt(subtitle_file)
            if subtitle_file_converted:
                subtitle_file = subtitle_file_converted
            else:
                log_window.insert(tk.END, f"{FAILED_CONVERT_SUBTITLE.format(subtitle_file=subtitle_file)}\n")
                return False
        # Convert video file if necessary
        if video_file.lower().endswith(tuple(unsupported_extensions)):
            video_file_converted = convert_to_srt(video_file)
            if video_file_converted:
                video_file = video_file_converted
            else:
                log_window.insert(tk.END, f"{FAILED_CONVERT_VIDEO.format(video_file=video_file)}\n")
                return False
        return original_base_name

    def execute_cmd(cmd):
        decoding_error_occurred = False
        try:
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            for output in process.stdout:
                if cancel_flag:
                    process.kill()
                    restore_window()
                    return 1, decoding_error_occurred  # Ensure a tuple is returned
                if sync_tool == SYNC_TOOL_FFSUBSYNC:
                    match_percentage = re.search(r'\b(\d+(\.\d+)?)%\|', output)
                elif sync_tool == SYNC_TOOL_ALASS:
                    match_percentage = re.search(r'\[\s*=\s*\]\s*(\d+\.\d+)\s*%', output)
                    if not match_percentage:
                        match_percentage = re.search(r'\d+\s*/\s*\d+\s*\[.*\]\s*(\d+\.\d+)\s*%', output)
                if match_percentage:
                    percentage = float(match_percentage.group(1))
                    adjusted_value = min(97, max(1, percentage))
                    progress_increment = (adjusted_value / 100) * (100 / total_items)
                    progress_bar["value"] = (completed_items / total_items) * 100 + progress_increment
                if "%" in output:
                    log_window.replace("end-2l", "end-1l", output)
                else:
                    log_window.insert(tk.END, output)
                log_window.see(tk.END)
                if "error while decoding subtitle from bytes to string" in output and sync_tool == SYNC_TOOL_ALASS:
                    decoding_error_occurred = True
            process.wait()
            return process.returncode, decoding_error_occurred
        except Exception as e:
            error_msg = f"Error executing command: {str(e)}\n"
            log_window.insert(tk.END, error_msg)
            return 1, decoding_error_occurred  # Ensure a tuple is returned
        
    def run_batch_process():
        nonlocal completed_items
        subtitles_to_skip = set()
        subtitles_to_process = []
        add_suffix = True
        if action_var_auto.get() == OPTION_REPLACE_ORIGINAL_SUBTITLE or action_var_auto.get() == OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME:
            add_suffix = False
        for parent in tree_items:
            if cancel_flag:
                restore_window()
                return
            parent_values = treeview.item(parent, "values")
            if not parent_values:
                log_window.insert(tk.END, f"{INVALID_PARENT_ITEM}\n")
                continue
            video_file = parent_values[0] if len(parent_values) > 0 else ""
            subtitles = treeview.get_children(parent)
            for sub in subtitles:
                if cancel_flag:
                    restore_window()
                    return
                values = treeview.item(sub, "values")
                subtitle_file = values[0] if len(values) > 0 else ""
                if not subtitle_file and not video_file:
                    log_window.insert(tk.END, f"\n{SKIP_NO_VIDEO_NO_SUBTITLE}\n")
                    continue
                elif not subtitle_file:
                    log_window.insert(tk.END, f"\n{SKIP_NO_SUBTITLE.format(video_file=os.path.basename(video_file))}\n")
                    continue
                elif not video_file:
                    log_window.insert(tk.END, f"\n{SKIP_NO_VIDEO.format(subtitle_file=os.path.basename(subtitle_file))}\n")
                    continue
                elif not values:
                    log_window.insert(tk.END, f"\n{SKIP_UNPAIRED_ITEM}\n")
                    continue
                # Prepare output file path
                if action_var_auto.get() == OPTION_SAVE_TO_DESKTOP:
                    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                    base_output_dir = desktop_path
                elif action_var_auto.get() == OPTION_REPLACE_ORIGINAL_SUBTITLE:
                    base_output_dir = os.path.dirname(subtitle_file)
                elif action_var_auto.get() == OPTION_SAVE_NEXT_TO_VIDEO:
                    base_output_dir = os.path.dirname(video_file)
                elif action_var_auto.get() == OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME:
                    base_output_dir = os.path.dirname(video_file)
                elif action_var_auto.get() == OPTION_SELECT_DESTINATION_FOLDER:
                    base_output_dir = selected_destination_folder
                else:
                    base_output_dir = os.path.dirname(subtitle_file)
                # Determine output extension
                base_name, original_ext = os.path.splitext(os.path.basename(subtitle_file))
                if original_ext in SUPPORTED_SUBTITLE_EXTENSIONS:
                    output_ext = original_ext
                else:
                    output_ext = '.srt'
                # Check for existing autosync files
                # and optionally ending with '_2', '_3', etc.
                autosync_pattern = rf'^autosync_{re.escape(base_name)}(?:_\d+)?{re.escape(output_ext)}$'
                synced_files = [f for f in os.listdir(base_output_dir) if re.match(autosync_pattern, f)]
                if synced_files:
                    subtitles_to_skip.add(subtitle_file)
                else:
                    subtitles_to_process.append((subtitle_file, video_file))
        # Prompt the user
        count = len(subtitles_to_skip)
        if count > 0 and add_suffix:
            skip = messagebox.askyesno(
                ALREADY_SYNCED_FILES_TITLE,
                ALREADY_SYNCED_FILES_MESSAGE.format(count=count)
            )
        else:
            skip = False
        for parent in tree_items:
            if cancel_flag:
                restore_window()
                return
            parent_values = treeview.item(parent, "values")
            if not parent_values:
                continue
            video_file = parent_values[0] if len(parent_values) > 0 else ""
            subtitles = treeview.get_children(parent)
            for sub in subtitles:
                if cancel_flag:
                    restore_window()
                    return
                values = treeview.item(sub, "values")
                subtitle_file = values[0] if len(values) > 0 else ""
                original_subtitle_file = subtitle_file  # Store the original subtitle file name
                if not video_file:
                    continue
                if not subtitle_file:
                    continue
                if subtitle_file in subtitles_to_skip and skip:
                    log_window.insert(tk.END, f"\n{SKIPPING_ALREADY_SYNCED.format(filename=os.path.basename(subtitle_file))}\n")
                    continue  
                original_base_name = convert_files()
                if not original_base_name:
                    continue
                # Update base_name for each subtitle file
                base_name, original_ext = os.path.splitext(os.path.basename(original_subtitle_file))
                if action_var_auto.get() == OPTION_SAVE_NEXT_TO_VIDEO:
                    output_subtitle_file = os.path.join(base_output_dir, f"autosync_{base_name}{original_ext}")
                elif action_var_auto.get() == OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME:
                    output_subtitle_file = os.path.join(base_output_dir, f"{os.path.splitext(os.path.basename(video_file))[0]}{original_ext}")
                elif action_var_auto.get() == OPTION_REPLACE_ORIGINAL_SUBTITLE:
                    output_subtitle_file = subtitle_file
                else:
                    output_subtitle_file = os.path.join(base_output_dir, f"autosync_{base_name}{original_ext}")
                if not output_subtitle_file.lower().endswith(tuple(SUPPORTED_SUBTITLE_EXTENSIONS)):
                    output_subtitle_file = os.path.splitext(output_subtitle_file)[0] + '.srt'
                if action_var_auto.get() == OPTION_REPLACE_ORIGINAL_SUBTITLE or action_var_auto.get() == OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME:
                    # if there is a file with the same name as the output_subtitle_file, create a backup
                    if os.path.exists(output_subtitle_file):
                        new_output_subtitle_file = create_backup(output_subtitle_file)
                        log_window.insert(tk.END, f"{BACKUP_CREATED.format(output_subtitle_file=new_output_subtitle_file)}")
                # Handle autosync suffix
                # Updated regex pattern to match filenames starting with 'autosync_' followed by the base name
                # and ending with '_2', '_3', etc.
                if original_ext in SUPPORTED_SUBTITLE_EXTENSIONS:
                    output_ext = original_ext
                else:
                    output_ext = '.srt'
                autosync_pattern = rf'^autosync_{re.escape(original_base_name)}(?:_\d+)?{re.escape(original_ext)}$'
                suffix = 2
                while os.path.exists(output_subtitle_file) and add_suffix == True:
                    output_subtitle_file = os.path.join(
                        base_output_dir,
                        f"autosync_{original_base_name}_{suffix}{output_ext}"
                    )
                    suffix += 1
                if sync_tool == SYNC_TOOL_FFSUBSYNC:
                    cmd = f'ffs "{video_file}" -i "{subtitle_file}" -o "{output_subtitle_file}"'
                    if not video_file.lower().endswith(tuple(SUBTITLE_EXTENSIONS)):
                        if ffsubsync_option_framerate_var.get():
                            cmd += " --no-fix-framerate"
                        if ffsubsync_option_gss_var.get():
                            cmd += " --gss"
                        if ffsubsync_option_vad_var.get():
                            cmd += " --vad=auditok"
                elif sync_tool == SYNC_TOOL_ALASS:
                    split_penalty = alass_split_penalty_var.get()
                    if split_penalty == 0:
                        cmd = f'"{alass_cli_path}" "{video_file}" "{subtitle_file}" "{output_subtitle_file}" --no-split'
                    else:
                        cmd = f'"{alass_cli_path}" "{video_file}" "{subtitle_file}" "{output_subtitle_file}" --split-penalty={split_penalty}'
                    if alass_speed_optimization_var.get():
                        cmd += " --speed-optimization 0"
                    if alass_disable_fps_guessing_var.get():
                        cmd += " --disable-fps-guessing"
                else:
                    log_message(INVALID_SYNC_TOOL, "error", tab='auto')
                    return
                log_window.insert(tk.END, f"\n[{completed_items + 1}/{total_items}] Syncing {os.path.basename(original_subtitle_file)} with {os.path.basename(video_file)}...\n")
                try:
                    progress_bar["value"] += 1
                    if sync_tool == SYNC_TOOL_FFSUBSYNC:
                        if video_file.lower().endswith(tuple(SUBTITLE_EXTENSIONS)):
                            log_window.insert(tk.END, f"{USING_REFERENCE_SUBTITLE}\n")
                        else:
                            log_window.insert(tk.END, f"{USING_VIDEO_FOR_SYNC}\n")
                            if ffsubsync_option_framerate_var.get():
                                log_window.insert(tk.END, f"{ENABLED_NO_FIX_FRAMERATE}\n")
                            if ffsubsync_option_gss_var.get():
                                log_window.insert(tk.END, f"{ENABLED_GSS}\n")
                            if ffsubsync_option_vad_var.get():
                                log_window.insert(tk.END, f"{ENABLED_AUDITOK_VAD}\n")
                    elif sync_tool == SYNC_TOOL_ALASS:
                        if split_penalty == 0:
                            log_window.insert(tk.END, f"{SPLIT_PENALTY_ZERO}\n")
                        else:
                            log_window.insert(tk.END, f"{SPLIT_PENALTY_SET.format(split_penalty=split_penalty)}\n")
                        if alass_speed_optimization_var.get():
                            log_window.insert(tk.END, f"{ALASS_SPEED_OPTIMIZATION_LOG}\n")
                        if alass_disable_fps_guessing_var.get():
                            log_window.insert(tk.END, f"{ALASS_DISABLE_FPS_GUESSING_LOG}\n")
                    log_window.insert(tk.END, f"{SYNCING_STARTED}\n")
                    process = subprocess.Popen(
                        cmd, shell=True, stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, universal_newlines=True
                    )
                    process_list.append(process)
                except Exception as e:
                    log_window.insert(tk.END, f"{FAILED_START_PROCESS.format(error_message=str(e))}\n")
                    log_message(FAILED_START_PROCESS.format(error_message=str(e)), "error", tab='auto')
                    continue
                try:
                    returncode, decoding_error_occurred = execute_cmd(cmd)
                    # alass specific code
                    if sync_tool == SYNC_TOOL_ALASS:
                        encoding_ref = None
                        encoding_inc = detect_encoding(subtitle_file)
                        # if decoding_error_occurred, retry with detected encodings
                        if returncode != 0 and decoding_error_occurred:
                            log_window.insert(tk.END, "\n" + RETRY_ENCODING_MSG)
                            if video_file.lower().endswith(tuple(SUBTITLE_EXTENSIONS)):
                                encoding_ref = detect_encoding(video_file)
                                cmd += f" --encoding-ref={encoding_ref}"
                            cmd += f" --encoding-inc={encoding_inc}"
                            returncode, decoding_error_occurred = execute_cmd(cmd)
                        synced_subtitle_encoding = detect_encoding(output_subtitle_file)
                        # If the encoding of synced subtitle is not the same as encoding_inc, change it
                        if synced_subtitle_encoding != encoding_inc:
                            change_encoding_msg = CHANGING_ENCODING_MSG.format(synced_subtitle_encoding=synced_subtitle_encoding, encoding_inc=encoding_inc)
                            log_window.insert(tk.END, change_encoding_msg)
                            try:
                                with open(output_subtitle_file, 'r', encoding=synced_subtitle_encoding) as f:
                                    content = f.read()
                                with open(output_subtitle_file, 'w', encoding=encoding_inc) as f:
                                    f.write(content)
                                log_window.insert(tk.END, ENCODING_CHANGED_MSG+"\n")
                            except Exception as e:
                                error_msg = ERROR_CHANGING_ENCODING_MSG.format(error_message=str(e))
                                log_window.insert(tk.END, error_msg)
                    if cancel_flag:
                        process_list.remove(process)
                        restore_window()
                        return
                    if returncode == 0:
                        log_window.insert(tk.END, f"{SYNC_SUCCESS.format(output_subtitle_file=output_subtitle_file)}")
                    else:
                        log_window.insert(tk.END, f"{SYNC_ERROR.format(filename=os.path.basename(subtitle_file))}\n")
                except Exception as e:
                    error_msg = ERROR_OCCURRED.format(error_message=str(e))
                    log_window.insert(tk.END, error_msg)
                process_list.remove(process)
                completed_items += 1
                progress_bar["value"] = (completed_items / total_items) * 100
                root.update_idletasks()
        log_window.insert(tk.END, f"\n{BATCH_SYNC_COMPLETED}\n")
        log_message(BATCH_SYNC_COMPLETED, "success", tab='auto')
        log_window.see(tk.END)
        button_cancel_batch_sync.grid_remove()
        log_window.grid(pady=(10, 10), rowspan=2)
        button_go_back.grid()
        button_generate_again.grid()
        progress_bar.grid_remove()
    try:
        batch_input.grid_remove()
        tree_frame.grid_remove()
        button_start_automatic_sync.grid_remove()
        batch_mode_button.grid_remove()
        label_message_auto.grid_remove()
        action_menu_auto.grid_remove()
        sync_frame.grid_remove()
        ffsubsync_option_gss.grid_remove()
        ffsubsync_option_vad.grid_remove()
        ffsubsync_option_framerate.grid_remove()
        alass_split_penalty_slider.grid_remove()
        alass_disable_fps_guessing.grid_remove()
        alass_speed_optimization.grid_remove()
        button_cancel_batch_sync = tk.Button(
            automatic_tab,
            text=CANCEL_TEXT,
            command=cancel_batch_sync,
            padx=10,
            pady=10,
            fg="white",
            bg=DEFULT_BUTTON_COLOR,
            activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
            activeforeground="white",
            relief=tk.RAISED,
            borderwidth=2,
            cursor="hand2"
        )
        button_cancel_batch_sync.grid(row=6, column=0, padx=10, pady=(0,10), sticky="ew", columnspan=2)
        button_generate_again = tk.Button(
            automatic_tab,
            text=GENERATE_AGAIN_TEXT,
            command=generate_again,
            padx=10,
            pady=10,
            fg="white",
            bg=BUTTON_COLOR_AUTO,
            activebackground=BUTTON_COLOR_AUTO_ACTIVE,
            activeforeground="white",
            relief=tk.RAISED,
            borderwidth=2,
            cursor="hand2"
        )
        button_generate_again.grid(row=11, column=0, padx=10, pady=(0,10), sticky="ew", columnspan=2)
        button_generate_again.grid_remove()

        button_go_back = tk.Button(
            automatic_tab,
            text=GO_BACK,
            command=lambda: [log_message("", "info", tab='auto'), restore_window()],
            padx=10,
            pady=10,
            fg="white",
            bg=DEFULT_BUTTON_COLOR,
            activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
            activeforeground="white",
            relief=tk.RAISED,
            borderwidth=2,
            cursor="hand2"
        )
        button_go_back.grid(row=12, column=0, padx=10, pady=(0,10), sticky="ew", columnspan=2)
        button_go_back.grid_remove()
        log_window = tk.Text(automatic_tab, wrap="word")
        log_window.config(font=("Arial", 7))
        log_window.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew", columnspan=2)
        progress_bar = ttk.Progressbar(automatic_tab, orient="horizontal", length=200, mode="determinate")
        progress_bar.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="ew", columnspan=2)
        root.update_idletasks()
        threading.Thread(target=run_batch_process).start()
    except Exception as e:
        log_message(ERROR_OCCURRED.format(error_message=str(e)), "error", tab='auto')
    automatic_tab.rowconfigure(0, weight=1)
    automatic_tab.rowconfigure(1, weight=0)
    automatic_tab.columnconfigure(0, weight=1)
# Global variable to store options state
options_states = {}
def toggle_batch_mode():
    global options_states
    if treeview.get_children():
        log_message("", "info", tab='auto')
        if batch_mode_var.get():
            batch_mode_var.set(False)
            batch_mode_button.config(text=BATCH_MODE_TEXT, bg=DEFULT_BUTTON_COLOR, activebackground=DEFAULT_BUTTON_COLOR_ACTIVE)
            button_start_automatic_sync.config(text=START_AUTOMATIC_SYNC_TEXT, bg=BUTTON_COLOR_AUTO, activebackground=BUTTON_COLOR_AUTO_ACTIVE, command=start_automatic_sync)
            subtitle_input.grid(row=1, column=0, padx=10, pady=0, sticky="nsew", columnspan=2)
            video_input.grid(row=0, column=0, padx=10, pady=(10,5), sticky="nsew", columnspan=2)
            if getattr(subtitle_input, 'tooltip_text', None):
                remove_subtitle_button.grid(row=1, column=1, padx=(0, 12), pady=(2,0), sticky="ne")
            if getattr(video_input, 'tooltip_text', None):
                remove_video_button.grid(row=0, column=1, padx=(0, 12), pady=(12,0), sticky="ne")
            batch_input.grid_remove()
            tree_frame.grid_remove()
            automatic_tab.rowconfigure(1, weight=1)
            root.update_idletasks()
            # Restore options state
            for option in [ffsubsync_option_gss, ffsubsync_option_vad, ffsubsync_option_framerate]:
                if options_states.get(option) == 'disabled':
                    option.config(state='disabled')
            options_states = {}
        else:
            batch_mode_var.set(True)
            batch_mode_button.config(text=NORMAL_MODE_TEXT, bg=DEFULT_BUTTON_COLOR, activebackground=DEFAULT_BUTTON_COLOR_ACTIVE)
            button_start_automatic_sync.config(text=START_BATCH_SYNC_TEXT, bg=BUTTON_COLOR_BATCH, activebackground=BUTTON_COLOR_BATCH_ACTIVE, command=start_batch_sync)
            subtitle_input.grid_remove()
            video_input.grid_remove()
            remove_subtitle_button.grid_remove()
            remove_video_button.grid_remove()
            batch_input.grid(row=0, column=0, padx=10, pady=(10,0), sticky="nsew", columnspan=2, rowspan=2)
            tree_frame.grid(row=0, column=0, padx=5, pady=(5,0), sticky="nsew", columnspan=2, rowspan=2)
            # Enable options if disabled
            options_states = {}
            for option in [ffsubsync_option_gss, ffsubsync_option_vad, ffsubsync_option_framerate]:
                if option.cget('state') == 'disabled':
                    options_states[option] = 'disabled'
                    option.config(state='normal')
    else:
        log_message("", "info", tab='auto')
        if batch_mode_var.get():
            batch_mode_var.set(False)
            batch_mode_button.config(text=BATCH_MODE_TEXT, bg=DEFULT_BUTTON_COLOR, activebackground=DEFAULT_BUTTON_COLOR_ACTIVE)
            button_start_automatic_sync.config(text=START_AUTOMATIC_SYNC_TEXT, bg=BUTTON_COLOR_AUTO, activebackground=BUTTON_COLOR_AUTO_ACTIVE, command=start_automatic_sync)
            subtitle_input.grid(row=1, column=0, padx=10, pady=0, sticky="nsew", columnspan=2)
            video_input.grid(row=0, column=0, padx=10, pady=(10,5), sticky="nsew", columnspan=2)
            if getattr(subtitle_input, 'tooltip_text', None):
                remove_subtitle_button.grid(row=1, column=1, padx=(0, 12), pady=(2,0), sticky="ne")
            if getattr(video_input, 'tooltip_text', None):
                remove_video_button.grid(row=0, column=1, padx=(0, 12), pady=(12,0), sticky="ne")
            batch_input.grid_remove()
            tree_frame.grid_remove()
            automatic_tab.rowconfigure(1, weight=1)
            root.update_idletasks()
            # Restore options state
            for option in [ffsubsync_option_gss, ffsubsync_option_vad, ffsubsync_option_framerate]:
                if options_states.get(option) == 'disabled':
                    option.config(state='disabled')
            options_states = {}
        else:
            batch_mode_var.set(True)
            batch_mode_button.config(text=NORMAL_MODE_TEXT, bg=DEFULT_BUTTON_COLOR, activebackground=DEFAULT_BUTTON_COLOR_ACTIVE)
            button_start_automatic_sync.config(text=START_BATCH_SYNC_TEXT, bg=BUTTON_COLOR_BATCH, activebackground=BUTTON_COLOR_BATCH_ACTIVE, command=start_batch_sync)
            subtitle_input.grid_remove()
            video_input.grid_remove()
            remove_subtitle_button.grid_remove()
            remove_video_button.grid_remove()
            batch_input.grid(row=0, column=0, padx=10, pady=(10,0), sticky="nsew", columnspan=2, rowspan=2)
            tree_frame.grid_remove()
            # Enable options if disabled
            options_states = {}
            for option in [ffsubsync_option_gss, ffsubsync_option_vad, ffsubsync_option_framerate]:
                if option.cget('state') == 'disabled':
                    options_states[option] = 'disabled'
                    option.config(state='normal')

def process_files(filepaths):
    subtitle_files = []
    video_files = []
    # Separate the files into video and subtitle lists
    for filepath in filepaths:
        if os.path.isdir(filepath):
            for root, _, files in os.walk(filepath):
                for file in files:
                    full_path = os.path.join(root, file)
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
        log_message(DROP_VALID_FILES, "error", tab='auto')
        batch_input.config(bg="lightgray")
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
            video_file = os.path.normpath(parent_values[0].lower())
            subtitles = treeview.get_children(parent)
            for sub in subtitles:
                values = treeview.item(sub, "values")
                if values and values[0]:
                    subtitle_file = os.path.normpath(values[0].lower())
                    existing_pairs.add((video_file, subtitle_file))
    incomplete_pairs = []
    complete_pairs = []
    # Pair videos with subtitles based on the same filename (search within the same directory first, then parent directories)
    for video_file in sorted(video_files, key=lambda x: os.path.basename(x) if x else ''):
        video_name = os.path.basename(video_file) if video_file else NO_VIDEO
        subtitle_name = NO_SUBTITLE
        subtitle_file = None
        if video_file:
            video_dir = os.path.dirname(video_file)
            # Check if there is a subtitle in the same directory with the same name as the video
            base_name = os.path.splitext(os.path.basename(video_file))[0]
            for sub_file in subtitle_files[:]:
                if sub_file and os.path.dirname(sub_file) == video_dir and os.path.splitext(os.path.basename(sub_file))[0] == base_name:
                    subtitle_file = sub_file
                    subtitle_name = os.path.basename(subtitle_file)
                    subtitle_files.remove(sub_file)
                    break
            # If no subtitle is found in the same directory, check parent directories
            if not subtitle_file:
                parent_dir = video_dir
                while parent_dir != os.path.dirname(parent_dir):  # Check parent directories until root
                    parent_dir = os.path.dirname(parent_dir)
                    for sub_file in subtitle_files[:]:
                        if sub_file and os.path.dirname(sub_file) == parent_dir and os.path.splitext(os.path.basename(sub_file))[0] == base_name:
                            subtitle_file = sub_file
                            subtitle_name = os.path.basename(subtitle_file)
                            subtitle_files.remove(sub_file)
                            break
                    if subtitle_file:
                        break
            if subtitle_file:
                norm_video = os.path.normpath(video_file.lower())
                norm_subtitle = os.path.normpath(subtitle_file.lower())
                pair = (norm_video, norm_subtitle)
                if pair in existing_pairs:
                    duplicates += 1
                    continue
                existing_pairs.add(pair)
                pairs_added += 1
                complete_pairs.append((video_name, subtitle_name, video_file, subtitle_file))
            else:
                files_not_paired += 1
                incomplete_pairs.append((video_name, subtitle_name, video_file, subtitle_file))
        else:
            incomplete_pairs.append((video_name, subtitle_name, video_file, subtitle_file))
    # Handle remaining unpaired subtitles
    unpaired_subtitles = list(filter(None, subtitle_files))
    if len(unpaired_subtitles) == 1 and len(video_files) == 1 and video_files[0] is not None:
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
                complete_pairs.append((os.path.basename(video_file), os.path.basename(subtitle_file), video_file, subtitle_file))
            else:
                duplicates += 1
                pairs_added = 0
                files_not_paired = 0
            # Remove the video file from incomplete pairs if it was added
            incomplete_pairs = [pair for pair in incomplete_pairs if pair[2] != video_file]
        else:
            incomplete_pairs.append((NO_VIDEO, os.path.basename(unpaired_subtitles[0]), None, unpaired_subtitles[0]))
            files_not_paired += 1
    else:
        if unpaired_subtitles:
            unpaired_count = len(unpaired_subtitles)
            user_choice = messagebox.askyesno(UNPAIRED_SUBTITLES_TITLE, UNPAIRED_SUBTITLES_MESSAGE.format(unpaired_count=unpaired_count))
            for sub_file in unpaired_subtitles:
                subtitle_name = os.path.basename(sub_file)
                if user_choice:
                    incomplete_pairs.append((NO_VIDEO, subtitle_name, None, sub_file))
                else:
                    incomplete_pairs.append((subtitle_name, NO_SUBTITLE, sub_file, None))
                files_not_paired += 1
    # Insert incomplete pairs first
    for video_name, subtitle_name, video_file, subtitle_file in incomplete_pairs:
        if video_file:
            parent_id = treeview.insert("", "end", text=video_name, values=(rf"{video_file}",), open=True)
            treeview.insert(parent_id, "end", text=subtitle_name, values=(subtitle_file if subtitle_file else ""))
        elif subtitle_file:
            parent_id = treeview.insert("", "end", text=NO_VIDEO, values=("",), open=True)
            treeview.insert(parent_id, "end", text=subtitle_name, values=(subtitle_file,))
        else:
            continue
        treeview.item(parent_id, tags=("incomplete",))
        if not video_file and not subtitle_file:
            treeview.delete(parent_id)
    # Insert complete pairs
    for video_name, subtitle_name, video_file, subtitle_file in complete_pairs:
        parent_id = treeview.insert("", "end", text=video_name, values=(video_file,), open=True)
        treeview.insert(parent_id, "end", text=subtitle_name, values=(subtitle_file,))
        treeview.item(parent_id, tags=("paired",))
    # Handle UI updates and logging
    batch_input.grid_remove()
    tree_frame.grid(row=0, column=0, padx=5, pady=(5,0), sticky="nsew", columnspan=2, rowspan=2)
    messages = []
    if pairs_added > 0:
        messages.append(PAIRS_ADDED.format(count=pairs_added, s='s' if pairs_added != 1 else ''))
    if files_not_paired > 0:
        if pairs_added < 1 or (duplicates > 0 and pairs_added < 1):
            messages.append(UNPAIRED_FILES_ADDED.format(count=files_not_paired, s='s' if files_not_paired != 1 else ''))
        else:
            messages.append(UNPAIRED_FILES.format(count=files_not_paired, s='s' if files_not_paired != 1 else ''))
    if duplicates > 0:
        messages.append(DUPLICATE_PAIRS_SKIPPED.format(count=duplicates, s='s' if duplicates != 1 else ''))
    if messages:
        log_message(" and ".join(messages) + ".", "info", tab='auto')

# Function to select a folder
def select_folder():
    folder_path = filedialog.askdirectory()
    if folder_path:
        process_files([folder_path])
        
def browse_batch(event=None):
    paths = filedialog.askopenfilenames(filetypes = [(VIDEO_OR_SUBTITLE_TEXT, ";".join([f"*{ext}" for ext in SUBTITLE_EXTENSIONS + VIDEO_EXTENSIONS]))])
    if paths:
        process_files(paths)

def on_batch_drop(event):
    filepaths = automatic_tab.tk.splitlist(event.data)
    process_files(filepaths)

def add_pair():
    video_file = filedialog.askopenfilename(filetypes = [(VIDEO_OR_SUBTITLE_TEXT, ";".join([f"*{ext}" for ext in SUBTITLE_EXTENSIONS + VIDEO_EXTENSIONS]))])
    if video_file:
        subtitle_file = filedialog.askopenfilename(filetypes=[(SUBTITLE_FILES_TEXT, ";".join([f"*{ext}" for ext in SUBTITLE_EXTENSIONS]))])
        if subtitle_file:
            # Check if the same file is selected for both video and subtitle
            if os.path.normpath(video_file.lower()) == os.path.normpath(subtitle_file.lower()):
                log_message(SAME_FILE_ERROR, "error", tab='auto')
                return
            video_name = os.path.basename(video_file)
            subtitle_name = os.path.basename(subtitle_file)
            pair = (os.path.normpath(video_file.lower()), os.path.normpath(subtitle_file.lower()))
            # Check for duplicates based on normalized full file paths
            for parent in treeview.get_children():
                existing_video = treeview.item(parent, "values")
                if existing_video and os.path.normpath(existing_video[0].lower()) == pair[0]:
                    subtitles = treeview.get_children(parent)
                    for sub in subtitles:
                        existing_sub = treeview.item(sub, "values")
                        if existing_sub and os.path.normpath(existing_sub[0].lower()) == pair[1]:
                            log_message(PAIR_ALREADY_EXISTS, "error", tab='auto')
                            return
            parent_id = treeview.insert("", "end", text=video_name, values=(video_file,), open=True)
            treeview.insert(parent_id, "end", text=subtitle_name, values=(subtitle_file,))
            treeview.item(parent_id, tags=("paired",))
            log_message(PAIR_ADDED, "info", tab='auto')
            # Handle UI updates
            batch_input.grid_remove()
            tree_frame.grid(row=0, column=0, padx=5, pady=(5,0), sticky="nsew", columnspan=2, rowspan=2)
        else:
            log_message(SELECT_SUBTITLE, "error", tab='auto')
    else:
        log_message(SELECT_VIDEO, "error", tab='auto')

def change_selected_item():
    selected_item = treeview.selection()
    if selected_item:
        parent_id = treeview.parent(selected_item)
        is_parent = not parent_id
        if is_parent:
            filetypes = [(VIDEO_OR_SUBTITLE_TEXT, ";".join([f"*{ext}" for ext in SUBTITLE_EXTENSIONS + VIDEO_EXTENSIONS]))]
        else:
            filetypes = [(SUBTITLE_FILES_TEXT, ";".join([f"*{ext}" for ext in SUBTITLE_EXTENSIONS]))]
        new_file = filedialog.askopenfilename(filetypes=filetypes)
        if new_file:
            new_file = os.path.normpath(new_file)
            new_name = os.path.basename(new_file)
            parent_values = treeview.item(parent_id, "values") if parent_id else None
            parent_file = os.path.normpath(parent_values[0]) if parent_values else ""
            current_item_values = treeview.item(selected_item, "values")
            current_file = os.path.normpath(current_item_values[0]) if current_item_values else ""
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
                    child_file = os.path.normpath(child_values[0]) if child_values else ""
                    if new_file.lower() == child_file.lower():
                        log_message(SAME_FILE_ERROR, "error", tab='auto')
                        return
            else:
                if new_file.lower() == parent_file.lower():
                    log_message(SAME_FILE_ERROR, "error", tab='auto')
                    return
            # Gather all existing pairs, excluding the current selection if it's a parent
            existing_pairs = set()
            for item in treeview.get_children():
                if is_parent and item == selected_item:
                    continue
                current_parent_values = treeview.item(item, "values")
                current_parent = os.path.normpath(current_parent_values[0]).lower() if current_parent_values else ""
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
                            log_message(PAIR_ALREADY_EXISTS, "error", tab='auto')
                            return
            else:
                new_child_file = new_file.lower()
                new_parent_file = parent_file.lower() if parent_file else ""
                if (new_parent_file, new_child_file) in existing_pairs:
                    log_message(PAIR_ALREADY_EXISTS, "error", tab='auto')
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
                valid_children = [child for child in children if treeview.item(child, "text") != NO_SUBTITLE]
                if not children or not valid_children:
                    treeview.item(selected_item, tags=("incomplete",))
                else:
                    treeview.item(selected_item, tags=("paired",))
            # Log appropriate messages
            if item_type.lower() == NO_SUBTITLE:
                log_message(SUBTITLE_ADDED, "info", tab='auto')
            elif item_type.lower() == NO_VIDEO:
                log_message(VIDEO_ADDED, "info", tab='auto')
            else:
                log_message(FILE_CHANGED, "info", tab='auto')
        else:
            log_message(SELECT_ITEM_TO_CHANGE, "error", tab='auto')

def remove_selected_item():
    selected_items = treeview.selection()
    if selected_items:
        for selected_item in selected_items:
            if treeview.exists(selected_item):
                parent_id = treeview.parent(selected_item)
                if parent_id:
                    treeview.delete(selected_item)
                    if not treeview.get_children(parent_id):
                        treeview.insert(parent_id, "end", text=NO_SUBTITLE, values=("",))
                        treeview.item(parent_id, tags=("incomplete",))
                else:
                    treeview.delete(selected_item)
    else:
        log_message(SELECT_ITEM_TO_REMOVE, "error", tab='auto')
batch_input = tk.Label(automatic_tab, text=BATCH_INPUT_LABEL, bg="lightgray", relief="ridge", width=40, height=5, cursor="hand2")
batch_input_text = tk.Label(automatic_tab, text=BATCH_INPUT_TEXT, fg="black", relief="ridge", padx=5, borderwidth=1)
batch_input_text.place(in_=batch_input, relx=0, rely=0, anchor="nw")
batch_input.bind("<Button-1>", lambda event: options_menu.post(event.x_root, event.y_root))
batch_input.bind("<Button-3>", lambda event: options_menu.post(event.x_root, event.y_root))
batch_input.bind("<Enter>", on_enter)
batch_input.bind("<Leave>", on_leave)
batch_input.drop_target_register(DND_FILES)
batch_input.dnd_bind('<<Drop>>', on_batch_drop)
# Create a frame for the Treeview and buttons
tree_frame = ttk.Frame(automatic_tab)
tree_frame.columnconfigure(0, weight=1)
tree_frame.rowconfigure(1, weight=1)
# Create a Treeview for displaying added files
treeview = ttk.Treeview(tree_frame, show='tree')
# Add tags and styles for paired and incomplete entries
treeview.tag_configure("paired", background="lightgreen")
treeview.tag_configure("incomplete", background="lightcoral")
# Enable drag-and-drop on Treeview
treeview.drop_target_register(DND_FILES)
treeview.dnd_bind('<<Drop>>', on_batch_drop)
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
context_menu.add_command(label=CONTEXT_MENU_CLEAR_ALL, command=lambda: treeview.delete(*treeview.get_children()))
# Function to show the context menu
def show_path():
    selected_item = treeview.selection()
    if selected_item:
        item_values = treeview.item(selected_item, "values")
        if item_values and item_values[0]:
            path = item_values[0]
            folder = os.path.dirname(path)
            subprocess.run(['explorer', '/select,', os.path.normpath(path)])
def show_context_menu(event):
    # Clear previous dynamic menu items
    context_menu.delete(0, tk.END)
    # Select the item under the cursor
    item = treeview.identify_row(event.y)
    if item:
        treeview.selection_set(item)
        item_values = treeview.item(item, "values")
        if item_values and item_values[0]:
            context_menu.add_command(label=CONTEXT_MENU_SHOW_PATH, command=show_path)
            context_menu.add_separator()
    context_menu.add_command(label=CONTEXT_MENU_REMOVE, command=remove_selected_item)
    context_menu.add_command(label=CONTEXT_MENU_CHANGE, command=change_selected_item)
    context_menu.add_separator()  # Add a separator
    context_menu.add_command(label=CONTEXT_MENU_ADD_PAIR, command=add_pair)
    context_menu.add_command(label=CONTEXT_MENU_CLEAR_ALL, command=lambda: treeview.delete(*treeview.get_children()))
    context_menu.post(event.x_root, event.y_root)
# Bind the right-click event to the Treeview to show the context menu
treeview.bind("<Button-3>", show_context_menu)
# Bind the key events to the treeview
treeview.bind("<Control-a>", select_all)
treeview.bind("<Delete>", delete_selected)
treeview.bind("<Double-1>", on_double_click)
# Create a vertical scrollbar for the Treeview
treeview_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=treeview.yview)
treeview.configure(yscrollcommand=treeview_scrollbar.set)
# Create buttons for adding, changing, and removing items
button_change_item = tk.Button(
    tree_frame,
    text=CONTEXT_MENU_CHANGE,
    command=change_selected_item,
    padx=10,
    pady=5,
    fg="black",
    bg=BUTTON_COLOR_BATCH_OPTIONS,
    activebackground=BUTTON_COLOR_BATCH_OPTIONS_ACTIVE,
    activeforeground="black",
    relief=tk.RAISED,
    borderwidth=2,
    cursor="hand2"
)
button_remove_item = tk.Button(
    tree_frame,
    text=CONTEXT_MENU_REMOVE,
    command=remove_selected_item,
    padx=10,
    pady=5,
    fg="black",
    bg=BUTTON_COLOR_BATCH_OPTIONS,
    activebackground=BUTTON_COLOR_BATCH_OPTIONS_ACTIVE,
    activeforeground="black",
    relief=tk.RAISED,
    borderwidth=2,
    cursor="hand2"
)
style = ttk.Style()
style.configure("Treeview", rowheight=25)
style.map("Treeview", background=[('selected', 'steel blue')])
# Replace the "Add Pair" button with a Menubutton
button_addfile = tk.Menubutton(
    tree_frame,
    text=BUTTON_ADD_FILES,
    padx=10,
    pady=7.5,
    fg="black",
    bg=BUTTON_COLOR_BATCH_OPTIONS,
    activebackground=BUTTON_COLOR_BATCH_OPTIONS,
    activeforeground="black",
    relief=tk.RAISED,
    borderwidth=2,
    cursor="hand2"
)
options_menu = tk.Menu(button_addfile, tearoff=0)
button_addfile.config(menu=options_menu)
options_menu.add_command(label=CONTEXT_MENU_ADD_PAIR, command=add_pair)
options_menu.add_command(label=MENU_ADD_FOLDER, command=select_folder)
options_menu.add_command(label=MENU_ADD_MULTIPLE_FILES, command=browse_batch)
# Update the grid layout
button_addfile.grid(row=0, column=0, padx=(5,2.5), pady=5, sticky="ew")
button_change_item.grid(row=0, column=1, padx=(2.5,2.5), pady=5, sticky="ew")
button_remove_item.grid(row=0, column=2,columnspan=3, padx=(2.5,5), pady=5, sticky="ew")
treeview.grid(row=1, column=0, columnspan=3, padx=5, pady=(5,0), sticky="nsew")
treeview_scrollbar.grid(row=1, column=3, sticky="ns", pady=(5,0))
tree_frame.grid_remove()
batch_input.grid_remove()
# Start batch mode end
# Start automatic sync begin
def remove_subtitle_input():
    subtitle_input.config(text=SUBTITLE_INPUT_TEXT, bg="lightgray", font=("Segoe UI", 9, "normal"))
    del subtitle_input.tooltip_text
    remove_subtitle_button.grid_remove()

def remove_video_input():
    video_input.config(text=VIDEO_INPUT_TEXT, bg="lightgray", font=("Segoe UI", 9, "normal"))
    del video_input.tooltip_text
    ffsubsync_option_gss.config(state=tk.NORMAL)
    ffsubsync_option_vad.config(state=tk.NORMAL)
    ffsubsync_option_framerate.config(state=tk.NORMAL)
    remove_video_button.grid_remove()

def browse_subtitle(event=None):
    subtitle_file_auto = filedialog.askopenfilename(
        filetypes=[(SUBTITLE_FILES_TEXT, ";".join([f"*{ext}" for ext in SUBTITLE_EXTENSIONS]))]
    )
    if subtitle_file_auto:
        subtitle_input.config(text=subtitle_file_auto, font=("Calibri", 10, "bold"))
        subtitle_input.tooltip_text = subtitle_file_auto
        subtitle_input.config(bg="lightgreen")
        remove_subtitle_button.grid(row=1, column=1, padx=(0, 12), pady=(2,0), sticky="ne")
        log_message("", "info", tab='auto')
    else:
        if subtitle_file_auto != '':
            log_message(SELECT_SUBTITLE, "error", tab='auto')
            subtitle_input.config(bg="lightgray")

def browse_video(event=None):
    video_file = filedialog.askopenfilename(filetypes=[(VIDEO_OR_SUBTITLE_TEXT, ";".join([f"*{ext}" for ext in SUBTITLE_EXTENSIONS + VIDEO_EXTENSIONS]))])
    if video_file:
        video_input.config(text=video_file, font=("Calibri", 10, "bold"))
        video_input.tooltip_text = video_file
        video_input.config(bg="lightgreen")
        remove_video_button.grid(row=0, column=1, padx=(0, 12), pady=(12,0), sticky="ne")
        log_message("", "info", tab='auto')
        if video_file.lower().endswith(tuple(SUBTITLE_EXTENSIONS)):
            # If the video file is a subtitle, disable parameters
            ffsubsync_option_gss.config(state=tk.DISABLED)
            ffsubsync_option_vad.config(state=tk.DISABLED)
            ffsubsync_option_framerate.config(state=tk.DISABLED)
        else:
            ffsubsync_option_gss.config(state=tk.NORMAL)
            ffsubsync_option_vad.config(state=tk.NORMAL)
            ffsubsync_option_framerate.config(state=tk.NORMAL)
    else:
        if video_file != '':
            log_message(SELECT_VIDEO_OR_SUBTITLE, "error", tab='auto')
            video_input.config(bg="lightgray")

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
            video_input.config(text=video_file, font=("Calibri", 10, "bold"))
            video_input.tooltip_text = video_file
            video_input.config(bg="lightgreen")
            subtitle_input.config(text=subtitle_file, font=("Calibri", 10, "bold"))
            subtitle_input.tooltip_text = subtitle_file
            subtitle_input.config(bg="lightgreen")
            remove_video_button.grid(row=0, column=1, padx=(0, 12), pady=(12,0), sticky="ne")
            remove_subtitle_button.grid(row=1, column=1, padx=(0, 12), pady=(2,0), sticky="ne")
            log_message("", "info", tab='auto')
            ffsubsync_option_gss.config(state=tk.NORMAL)
            ffsubsync_option_vad.config(state=tk.NORMAL)
            ffsubsync_option_framerate.config(state=tk.NORMAL)
            return
    elif len(files) != 1:
        log_message(DROP_VIDEO_OR_SUBTITLE, "error", tab='auto')
        return
    filepath = files[0]
    if filepath.lower().endswith(tuple(SUBTITLE_EXTENSIONS + VIDEO_EXTENSIONS)):
        video_input.config(text=filepath, font=("Calibri", 10, "bold"))
        video_input.tooltip_text = filepath
        video_input.config(bg="lightgreen")
        remove_video_button.grid(row=0, column=1, padx=(0, 12), pady=(12,0), sticky="ne")
        log_message("", "info", tab='auto')
        if filepath.lower().endswith(tuple(SUBTITLE_EXTENSIONS)):
            ffsubsync_option_gss.config(state=tk.DISABLED)
            ffsubsync_option_vad.config(state=tk.DISABLED)
            ffsubsync_option_framerate.config(state=tk.DISABLED)
        else:
            ffsubsync_option_gss.config(state=tk.NORMAL)
            ffsubsync_option_vad.config(state=tk.NORMAL)
            ffsubsync_option_framerate.config(state=tk.NORMAL)
    else:
        log_message(DROP_VIDEO_OR_SUBTITLE, "error", tab='auto')

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
            video_input.config(text=video_file, font=("Calibri", 10, "bold"))
            video_input.tooltip_text = video_file
            video_input.config(bg="lightgreen")
            subtitle_input.config(text=subtitle_file, font=("Calibri", 10, "bold"))
            subtitle_input.tooltip_text = subtitle_file
            subtitle_input.config(bg="lightgreen")
            remove_video_button.grid(row=0, column=1, padx=(0, 12), pady=(12,0), sticky="ne")
            remove_subtitle_button.grid(row=1, column=1, padx=(0, 12), pady=(2,0), sticky="ne")
            log_message("", "info", tab='auto')
            ffsubsync_option_gss.config(state=tk.NORMAL)
            ffsubsync_option_vad.config(state=tk.NORMAL)
            ffsubsync_option_framerate.config(state=tk.NORMAL)
            return
    elif len(files) != 1:
        log_message(DROP_SINGLE_SUBTITLE_PAIR, "error", tab='auto')
        return
    filepath = files[0]
    if filepath.lower().endswith(tuple(SUBTITLE_EXTENSIONS)):
        subtitle_input.config(text=filepath, font=("Calibri", 10, "bold"))
        subtitle_input.tooltip_text = filepath
        subtitle_input.config(bg="lightgreen")
        remove_subtitle_button.grid(row=1, column=1, padx=(0, 11), pady=(2,0), sticky="ne")
        log_message("", "info", tab='auto')
    else:
        log_message(DROP_SUBTITLE_FILE, "error", tab='auto')

process = None

def start_automatic_sync():
    sync_tool = sync_tool_var_auto.get()
    if sync_tool == SYNC_TOOL_ALASS:
        SUPPORTED_SUBTITLE_EXTENSIONS = ALASS_SUPPORTED_EXTENSIONS
    elif sync_tool == 'ffsubsync':
        SUPPORTED_SUBTITLE_EXTENSIONS = FFSUBSYNC_SUPPORTED_EXTENSIONS
    global process, subtitle_file, video_file, output_subtitle_file
    subtitle_file = getattr(subtitle_input, 'tooltip_text', None)
    video_file = getattr(video_input, 'tooltip_text', None)
    if not subtitle_file and not video_file:
        log_message(SELECT_BOTH_FILES, "error", tab='auto')
        return
    if subtitle_file == video_file:
        log_message(SELECT_DIFFERENT_FILES, "error", tab='auto')
        return
    if not subtitle_file:
        log_message(SELECT_SUBTITLE, "error", tab='auto')
        return
    if not video_file:
        log_message(SELECT_VIDEO_OR_SUBTITLE, "error", tab='auto')
        return
    if not os.path.exists(subtitle_file):
        log_message(SUBTITLE_FILE_NOT_EXIST, "error", tab='auto')
        return
    if not os.path.exists(video_file):
        log_message(VIDEO_FILE_NOT_EXIST, "error", tab='auto')
        return
    action = action_var_auto.get()
    if action == OPTION_SAVE_NEXT_TO_VIDEO:
        output_dir = os.path.dirname(video_file)
    elif action == OPTION_SAVE_TO_DESKTOP:
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        output_dir = desktop_path
    elif action == OPTION_REPLACE_ORIGINAL_SUBTITLE:
        output_subtitle_file = subtitle_file
        output_dir = None
    elif action == OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME:
        output_dir = os.path.dirname(video_file)
        base_name, ext = os.path.splitext(os.path.basename(subtitle_file))
        if not ext.lower() in SUPPORTED_SUBTITLE_EXTENSIONS:
            ext = '.srt'
        output_subtitle_file = os.path.join(output_dir, f"{base_name}{ext}")
    elif action == OPTION_SELECT_DESTINATION_FOLDER:
        if 'selected_destination_folder' in globals() and os.path.exists(selected_destination_folder):
            output_dir = selected_destination_folder
        else:
            log_message(TEXT_DESTINATION_FOLDER_DOES_NOT_EXIST, "error", tab='auto')
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
            ext = '.srt'
        if action == OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME:
            filename = f"{base_name}{ext}"
            output_subtitle_file = os.path.join(output_dir, filename)
        else:
            filename = f"autosync_{base_name}{ext}"
            output_subtitle_file = os.path.join(output_dir, filename)
        add_suffix = True

        if action_var_auto.get() == OPTION_REPLACE_ORIGINAL_SUBTITLE or action_var_auto.get() == OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME:
            add_suffix = False
        suffix = 2
        while os.path.exists(output_subtitle_file) and add_suffix == True:
            filename = f"autosync_{base_name}_{suffix}{ext}"
            output_subtitle_file = os.path.join(output_dir, filename)
            suffix += 1
    def cancel_automatic_sync():
        global process
        if process:
            try:
                subprocess.Popen(['taskkill', '/F', '/T', '/PID', str(process.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
                process = None
                log_message(AUTO_SYNC_CANCELLED, "error", tab='auto')
            except Exception as e:
                log_message(ERROR_PROCESS_TERMINATION.format(error_message=str(e)), "error", tab='auto')
        else:
            log_message(NO_SYNC_PROCESS, "error", tab='auto')
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
        if getattr(video_input, 'tooltip_text', None):
            remove_video_button.grid(row=0, column=1, padx=(0, 12), pady=(12,0), sticky="ne")
        if getattr(subtitle_input, 'tooltip_text', None):
            remove_subtitle_button.grid(row=1, column=1, padx=(0, 12), pady=(2,0), sticky="ne")
        action_menu_auto.grid()
        sync_frame.grid()
        button_start_automatic_sync.grid()
        batch_mode_button.grid()
        if sync_tool_var_auto.get() == SYNC_TOOL_ALASS:
            alass_split_penalty_slider.grid()
            alass_disable_fps_guessing.grid()
            alass_speed_optimization.grid()
            ffsubsync_option_gss.grid_remove()
            ffsubsync_option_vad.grid_remove()
            ffsubsync_option_framerate.grid_remove()
        elif sync_tool_var_auto.get() == SYNC_TOOL_FFSUBSYNC:
            ffsubsync_option_gss.grid()
            ffsubsync_option_vad.grid()
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
        root.update_idletasks()

    def generate_again():
        subtitle_input.config(text=SUBTITLE_INPUT_TEXT, bg="lightgray", font=("Segoe UI", 9, "normal"))
        del subtitle_input.tooltip_text
        video_input.config(text=VIDEO_INPUT_TEXT, bg="lightgray", font=("Segoe UI", 9, "normal"))
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
            ffsubsync_option_vad.grid_remove()
            ffsubsync_option_framerate.grid_remove()
        elif sync_tool_var_auto.get() == SYNC_TOOL_FFSUBSYNC:
            ffsubsync_option_gss.grid()
            ffsubsync_option_vad.grid()
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
        ffsubsync_option_gss.config(state=tk.NORMAL)
        ffsubsync_option_vad.config(state=tk.NORMAL)
        ffsubsync_option_framerate.config(state=tk.NORMAL)
        automatic_tab.columnconfigure(0, weight=0)
        root.update_idletasks()

    def convert_to_srt(subtitle_file):
        file_extension = os.path.splitext(subtitle_file)[-1].lower()
        base_name = os.path.basename(os.path.splitext(subtitle_file)[0])
        srt_file = os.path.join(os.path.dirname(subtitle_file), 'converted_' + base_name + '.srt')
        log_window.insert(tk.END, f"{PREPARING_SYNC.format(base_name=base_name, file_extension=file_extension)}\n")
        if file_extension in ['.ttml', '.dfxp', '.itt']:
            log_window.insert(tk.END, f"{CONVERTING_TTML}\n")
            try:
                convert_ttml_or_dfxp_to_srt(subtitle_file, srt_file)
            except Exception as e:
                log_window.insert(tk.END, f"{ERROR_CONVERTING_SUBTITLE.format(error_message=str(e))}\n")
        elif file_extension == '.vtt':
            log_window.insert(tk.END, f"{CONVERTING_VTT}\n")
            try:
                convert_vtt_to_srt(subtitle_file, srt_file)
            except Exception as e:
                log_window.insert(tk.END, f"{ERROR_CONVERTING_SUBTITLE.format(error_message=str(e))}\n")
        elif file_extension == '.sbv':
            log_window.insert(tk.END, f"{CONVERTING_SBV}\n")
            try:
                convert_sbv_to_srt(subtitle_file, srt_file)
            except Exception as e:
                log_window.insert(tk.END, f"{ERROR_CONVERTING_SUBTITLE.format(error_message=str(e))}\n")
        elif file_extension == '.sub':
            log_window.insert(tk.END, f"{CONVERTING_SUB}\n")
            try:
                convert_sub_to_srt(subtitle_file, srt_file)
            except Exception as e:
                log_window.insert(tk.END, f"{ERROR_CONVERTING_SUBTITLE.format(error_message=str(e))}\n")
        elif file_extension in ['.ass', '.ssa']:
            log_window.insert(tk.END, f"{CONVERTING_ASS}\n")
            try:
                convert_ass_to_srt(subtitle_file, srt_file)
            except Exception as e:
                log_window.insert(tk.END, f"{ERROR_CONVERTING_SUBTITLE.format(error_message=str(e))}\n")
        elif file_extension == '.stl':
            log_window.insert(tk.END, f"{CONVERTING_STL}\n")
            try:
                convert_stl_to_srt(subtitle_file, srt_file)
            except Exception as e:
                log_window.insert(tk.END, f"{ERROR_CONVERTING_SUBTITLE.format(error_message=str(e))}\n")
        else:
            log_window.insert(tk.END, f"{CONVERSION_NOT_SUPPORTED.format(file_extension=file_extension)}\n")
            return None
        if srt_file:
            log_window.insert(tk.END, f"{SUBTITLE_CONVERTED.format(srt_file=srt_file)}\n")
            return srt_file

    def update_progress_auto(progress_bar, value):
        adjusted_value = min(97, max(1, value))
        progress_bar["value"] = adjusted_value

    def build_cmd():
        if sync_tool == SYNC_TOOL_FFSUBSYNC:
            cmd = f'ffs "{video_file}" -i "{subtitle_file}" -o "{output_subtitle_file}"'
            if not video_file.lower().endswith(tuple(SUBTITLE_EXTENSIONS)):
                if ffsubsync_option_framerate_var.get():
                    cmd += " --no-fix-framerate"
                if ffsubsync_option_gss_var.get():
                    cmd += (" --gss")
                if ffsubsync_option_vad_var.get():
                    cmd += (" --vad=auditok")
        elif sync_tool == SYNC_TOOL_ALASS:
            if split_penalty == 0:
                cmd = f'"{alass_cli_path}" "{video_file}" "{subtitle_file}" "{output_subtitle_file}" --no-split'
            else:
                cmd = f'"{alass_cli_path}" "{video_file}" "{subtitle_file}" "{output_subtitle_file}" --split-penalty={split_penalty}'
            if alass_speed_optimization_var.get():
                cmd += " --speed-optimization 0"
            if alass_disable_fps_guessing_var.get():
                cmd += " --disable-fps-guessing"
        else:
            log_message(INVALID_SYNC_TOOL_SELECTED, "error", tab='auto')
            return None
        return cmd
    
    def execute_cmd(cmd):
        global process, progress_line_number, subtitle_file, video_file, output_subtitle_file, split_penalty
        split_penalty = alass_split_penalty_var.get()
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        progress_bar["value"] = 1
        if sync_tool == SYNC_TOOL_FFSUBSYNC:
            if video_file.lower().endswith(tuple(SUBTITLE_EXTENSIONS)):
                log_window.insert(tk.END, f"{USING_REFERENCE_SUBTITLE}\n")
            else:
                log_window.insert(tk.END, f"{USING_VIDEO_FOR_SYNC}\n")
                if ffsubsync_option_framerate_var.get():
                    log_window.insert(tk.END, f"{ENABLED_NO_FIX_FRAMERATE}\n")
                if ffsubsync_option_gss_var.get():
                    log_window.insert(tk.END, f"{ENABLED_GSS}\n")
                if ffsubsync_option_vad_var.get():
                    log_window.insert(tk.END, f"{ENABLED_AUDITOK_VAD}\n")
        elif sync_tool == SYNC_TOOL_ALASS:
            if split_penalty == 0:
                log_window.insert(tk.END, f"{SPLIT_PENALTY_ZERO}\n")
            else:
                log_window.insert(tk.END, f"{SPLIT_PENALTY_SET.format(split_penalty=split_penalty)}\n")
            if alass_speed_optimization_var.get():
                log_window.insert(tk.END, f"{ALASS_SPEED_OPTIMIZATION_LOG}\n")
            if alass_disable_fps_guessing_var.get():
                log_window.insert(tk.END, f"{ALASS_DISABLE_FPS_GUESSING_LOG}\n")
        log_window.insert(tk.END, f"{SYNCING_STARTED}\n")
        progress_line_number = log_window.index(tk.END).split(".")[0]
        decoding_error_occurred = False
        for output in process.stdout:
            if sync_tool == SYNC_TOOL_FFSUBSYNC:
                match_percentage = re.search(r'\b(\d+(\.\d+)?)%\|', output)
            elif sync_tool == SYNC_TOOL_ALASS:
                match_percentage = re.search(r'\[\s*=\s*\]\s*(\d+\.\d+)\s*%', output)
                if not match_percentage:
                    match_percentage = re.search(r'\d+\s*/\s*\d+\s*\[.*\]\s*(\d+\.\d+)\s*%', output)
            if match_percentage:
                percentage = float(match_percentage.group(1))
                root.after(10, update_progress_auto, progress_bar, percentage)
            if "%" in output:
                log_window.replace("end-2l", "end-1l", output)
            else:
                log_window.insert(tk.END, output)
            log_window.see(tk.END)
            if "error while decoding subtitle from bytes to string" in output and sync_tool == SYNC_TOOL_ALASS:
                decoding_error_occurred = True
        if process is not None:
            process.wait()
            if process.returncode == 0:
                log_window.insert(tk.END, f"\n{SYNC_SUCCESS_MESSAGE.format(output_subtitle_file=output_subtitle_file)}\n")
                log_message(SYNC_SUCCESS_MESSAGE.format(output_subtitle_file=output_subtitle_file), "success", output_subtitle_file, tab='auto')
                button_cancel_automatic_sync.grid_remove()
                log_window.grid(pady=(10, 10), rowspan=2)
                button_go_back.grid()
                button_generate_again.grid()
            return process.returncode, decoding_error_occurred
        return 1, decoding_error_occurred  # Ensure a tuple is returned in case process is None
            
    def run_subprocess():
        global process, progress_line_number, subtitle_file, video_file, cmd, output_subtitle_file, split_penalty, decoding_error_occurred
        split_penalty = alass_split_penalty_var.get()
        if action_var_auto.get() == OPTION_REPLACE_ORIGINAL_SUBTITLE or action_var_auto.get() == OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME:
            # if there is a file with the same name as the output_subtitle_file, create a backup
            if os.path.exists(output_subtitle_file):
                new_output_subtitle_file = create_backup(output_subtitle_file)
                log_window.insert(tk.END, f"{BACKUP_CREATED.format(output_subtitle_file=new_output_subtitle_file)}\n")
        unsupported_extensions = [ext for ext in SUBTITLE_EXTENSIONS if ext not in SUPPORTED_SUBTITLE_EXTENSIONS]
        if subtitle_file.lower().endswith(tuple(unsupported_extensions)):
            subtitle_file = convert_to_srt(subtitle_file)
        if video_file.lower().endswith(tuple(unsupported_extensions)):
            video_file = convert_to_srt(video_file)
        try:
            if not output_subtitle_file.lower().endswith(tuple(SUPPORTED_SUBTITLE_EXTENSIONS)):
                output_subtitle_file = output_subtitle_file.rsplit('.', 1)[0] + '.srt'
            cmd = build_cmd()
            if cmd is None:
                return
            returncode, decoding_error_occurred = execute_cmd(cmd)
            # alass specific code
            if sync_tool == SYNC_TOOL_ALASS:
                encoding_ref = None
                encoding_inc = detect_encoding(subtitle_file)
                # if decoding_error_occurred, retry with detected encodings
                if returncode != 0 and decoding_error_occurred:
                    log_window.insert(tk.END, "\n" + RETRY_ENCODING_MSG)
                    if video_file.lower().endswith(tuple(SUBTITLE_EXTENSIONS)):
                        encoding_ref = detect_encoding(video_file)
                        cmd += f" --encoding-ref={encoding_ref}"
                    cmd += f" --encoding-inc={encoding_inc}"
                    execute_cmd(cmd)
                synced_subtitle_encoding = detect_encoding(output_subtitle_file)
                # If the encoding of synced subtitle is not the same as encoding_inc, change it
                if synced_subtitle_encoding != encoding_inc:
                    change_encoding_msg = CHANGING_ENCODING_MSG.format(synced_subtitle_encoding=synced_subtitle_encoding, encoding_inc=encoding_inc)
                    log_window.insert(tk.END, change_encoding_msg)
                    try:
                        with open(output_subtitle_file, 'r', encoding=synced_subtitle_encoding) as f:
                            content = f.read()
                        with open(output_subtitle_file, 'w', encoding=encoding_inc) as f:
                            f.write(content)
                        log_window.insert(tk.END, ENCODING_CHANGED_MSG)
                    except Exception as e:
                        error_msg = ERROR_CHANGING_ENCODING_MSG.format(error_message=str(e))
                        log_window.insert(tk.END, error_msg)
            log_window.insert(tk.END, f"\n{SYNCING_ENDED}\n")
        except Exception as e:
            log_message(ERROR_OCCURRED.format(error_message=str(e)), "error", tab='auto')   
        finally:
            log_window.see(tk.END)
            progress_bar.grid_remove()
            automatic_tab.rowconfigure(1, weight=1)
            root.update_idletasks()
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
        ffsubsync_option_vad.grid_remove()
        ffsubsync_option_framerate.grid_remove()
        alass_split_penalty_slider.grid_remove()
        alass_disable_fps_guessing.grid_remove()
        alass_speed_optimization.grid_remove()
        label_message_auto.grid_remove()
        button_cancel_automatic_sync = tk.Button(
            automatic_tab,
            text=CANCEL_TEXT,
            command=cancel_automatic_sync,
            padx=10,
            pady=10,
            fg="white",
            bg=DEFULT_BUTTON_COLOR,
            activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
            activeforeground="white",
            relief=tk.RAISED,
            borderwidth=2,
            cursor="hand2"
        )
        button_cancel_automatic_sync.grid(row=6, column=0, padx=10, pady=(0,10), sticky="ew", columnspan=2)
        button_generate_again = tk.Button(
            automatic_tab,
            text=GENERATE_AGAIN_TEXT,
            command=generate_again,
            padx=10,
            pady=10,
            fg="white",
            bg=BUTTON_COLOR_AUTO,
            activebackground=BUTTON_COLOR_AUTO_ACTIVE,
            activeforeground="white",
            relief=tk.RAISED,
            borderwidth=2,
            cursor="hand2"
        )
        button_generate_again.grid(row=11, column=0, padx=10, pady=(00,10), sticky="ew", columnspan=2)
        button_generate_again.grid_remove()
        button_go_back = tk.Button(
            automatic_tab,
            text= GO_BACK,
            command=lambda: [log_message("", "info", tab='auto'), restore_window()],
            padx=10,
            pady=10,
            fg="white",
            bg=DEFULT_BUTTON_COLOR,
            activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
            activeforeground="white",
            relief=tk.RAISED,
            borderwidth=2,
            cursor="hand2"
        )
        button_go_back.grid(row=12, column=0, padx=10, pady=(0,10), sticky="ew", columnspan=2)
        button_go_back.grid_remove()
        log_window = tk.Text(automatic_tab, wrap="word")
        log_window.config(font=("Arial", 7))
        log_window.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew", columnspan=2)
        progress_bar = ttk.Progressbar(automatic_tab, orient="horizontal", length=200, mode="determinate")
        progress_bar.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="ew", columnspan=2)
        root.update_idletasks()
        threading.Thread(target=run_subprocess).start()
    except Exception as e:
        log_message(ERROR_OCCURRED.format(error_message=str(e)), "error", tab='auto')
    automatic_tab.rowconfigure(0, weight=1)
    automatic_tab.rowconfigure(1, weight=0)
    automatic_tab.columnconfigure(0, weight=1)
# Start automatic sync end
label_message_auto = tk.Label(automatic_tab, text="", fg="black", anchor="center")
subtitle_input = tk.Label(automatic_tab, text=SUBTITLE_INPUT_TEXT, bg="lightgray", relief="ridge", width=40, height=5, cursor="hand2")
video_input = tk.Label(automatic_tab, text=VIDEO_INPUT_TEXT, bg="lightgray", relief="ridge", width=40, height=5, cursor="hand2")
video_input_text = tk.Label(automatic_tab, text=VIDEO_INPUT_LABEL, fg="black", relief="ridge", padx=5, borderwidth=1)
video_input_text.place(in_=video_input, relx=0, rely=0, anchor="nw")
subtitle_input_text = tk.Label(automatic_tab, text=SUBTITLE_INPUT_LABEL, fg="black", relief="ridge", padx=5, borderwidth=1) 
subtitle_input_text.place(in_=subtitle_input, relx=0, rely=0, anchor="nw")
button_start_automatic_sync = tk.Button(
    automatic_tab,
    text=START_AUTOMATIC_SYNC_TEXT,
    command=start_automatic_sync,
    padx=10,
    pady=10,
    fg="white",
    bg=BUTTON_COLOR_AUTO,
    activebackground=BUTTON_COLOR_AUTO_ACTIVE,
    activeforeground="white",
    relief=tk.RAISED,
    borderwidth=2,
    cursor="hand2"
)
remove_subtitle_button = tk.Button(
    automatic_tab,
    text="X",
    font='Arial 8 bold',
    command=remove_subtitle_input,
    padx=4,
    pady=0,
    fg="white",
    bg=DEFULT_BUTTON_COLOR,
    activeforeground="white",
    activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
    relief=tk.RIDGE,
    borderwidth=1,
    cursor="hand2"
)
remove_subtitle_button.grid_remove()
remove_video_button = tk.Button(
    automatic_tab,
    text="X",
    font='Arial 8 bold',
    command=remove_video_input,
    padx=(4),
    pady=0,
    fg="white",
    bg=DEFULT_BUTTON_COLOR,
    activeforeground="white",
    activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
    relief=tk.RIDGE,
    borderwidth=1,
    cursor="hand2"
)
remove_video_button.grid_remove()
sync_frame = tk.Frame(automatic_tab)
sync_frame.grid(row=6, column=1, padx=(0, 10), pady=(5,10), sticky="e")
ffsubsync_option_framerate_var = tk.BooleanVar()
ffsubsync_option_gss_var = tk.BooleanVar()
ffsubsync_option_vad_var = tk.BooleanVar()
action_var_auto = tk.StringVar(value=OPTION_SAVE_NEXT_TO_SUBTITLE)
sync_tool_var_auto = tk.StringVar(value=SYNC_TOOL_FFSUBSYNC)
ffsubsync_option_framerate = tk.Checkbutton(automatic_tab, text=CHECKBOX_NO_FIX_FRAMERATE, variable=ffsubsync_option_framerate_var)
ffsubsync_option_gss = tk.Checkbutton(automatic_tab, text=CHECKBOX_GSS, variable=ffsubsync_option_gss_var)
ffsubsync_option_vad = tk.Checkbutton(automatic_tab, text=CHECKBOX_VAD, variable=ffsubsync_option_vad_var)
def select_destination_folder():
    global tooltip_action_menu_auto
    folder_path = filedialog.askdirectory()
    if folder_path:
        global selected_destination_folder
        selected_destination_folder = folder_path
        tooltip_action_menu_auto = ToolTip(action_menu_auto, TEXT_SELECTED_FOLDER.format(folder_path))
        log_message(TEXT_SELECTED_FOLDER.format(folder_path), "info", tab='auto')
    else:
        log_message(TEXT_NO_FOLDER_SELECTED, "error", tab='auto')
        action_var_auto.set(OPTION_SAVE_NEXT_TO_SUBTITLE)
def on_action_menu_change(*args):
    log_message("", "info", tab='auto')
    tooltip_action_menu_auto = ToolTip(action_menu_auto, TOOLTIP_TEXT_ACTION_MENU_AUTO)
    if action_var_auto.get() == OPTION_SELECT_DESTINATION_FOLDER:
        select_destination_folder()
action_menu_auto = ttk.OptionMenu(
    automatic_tab, 
    action_var_auto, 
    OPTION_SAVE_NEXT_TO_SUBTITLE,
    OPTION_SAVE_NEXT_TO_SUBTITLE, 
    OPTION_SAVE_NEXT_TO_VIDEO,
    OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME,
    OPTION_SAVE_TO_DESKTOP, 
    OPTION_REPLACE_ORIGINAL_SUBTITLE,
    OPTION_SELECT_DESTINATION_FOLDER
)
action_var_auto.trace_add("write", on_action_menu_change)
sync_tool_menu_auto = ttk.OptionMenu(sync_frame, sync_tool_var_auto, SYNC_TOOL_FFSUBSYNC, SYNC_TOOL_FFSUBSYNC, SYNC_TOOL_ALASS)
alass_disable_fps_guessing_var = tk.BooleanVar()
alass_disable_fps_guessing = tk.Checkbutton(automatic_tab, text=ALASS_DISABLE_FPS_GUESSING_TEXT, variable=alass_disable_fps_guessing_var)
alass_speed_optimization_var = tk.BooleanVar()
alass_speed_optimization = tk.Checkbutton(automatic_tab, text=ALASS_SPEED_OPTIMIZATION_TEXT, variable=alass_speed_optimization_var)
alass_split_penalty_var = tk.IntVar(value=7)
alass_split_penalty_slider = tk.Scale(automatic_tab, from_=0, to=100, orient="horizontal", variable=alass_split_penalty_var, label=LABEL_SPLIT_PENALTY)
tooltip_ffsubsync_option_framerate = ToolTip(ffsubsync_option_framerate, TOOLTIP_FRAMERATE)
tooltip_ffsubsync_option_gss = ToolTip(ffsubsync_option_gss, TOOLTIP_GSS)
tooltip_ffsubsync_option_vad = ToolTip(ffsubsync_option_vad, TOOLTIP_VAD)
tooltip_action_menu_auto = ToolTip(action_menu_auto, TOOLTIP_TEXT_ACTION_MENU_AUTO)
tooltip_sync_tool_menu_auto = ToolTip(sync_tool_menu_auto, TOOLTIP_TEXT_SYNC_TOOL_MENU_AUTO)
tooltip_alass_speed_optimization = ToolTip(alass_speed_optimization, TOOLTIP_ALASS_SPEED_OPTIMIZATION)
tooltip_alass_disable_fps_guessing = ToolTip(alass_disable_fps_guessing, TOOLTIP_ALASS_DISABLE_FPS_GUESSING)
video_input.grid(row=0, column=0, padx=10, pady=(10,5), sticky="nsew", columnspan=2)
subtitle_input.grid(row=1, column=0, padx=10, pady=0, sticky="nsew", columnspan=2)
ffsubsync_option_framerate.grid(row=2, column=0, columnspan=5, padx=10, pady=(5,0), sticky="w")
ffsubsync_option_gss.grid(row=3, column=0, columnspan=5, padx=10, pady=0, sticky="w")
ffsubsync_option_vad.grid(row=4, column=0, columnspan=5, padx=10, pady=0, sticky="w")
def on_sync_tool_change(*args):
    if sync_tool_var_auto.get() == SYNC_TOOL_ALASS:
        ffsubsync_option_framerate.grid_remove()
        ffsubsync_option_gss.grid_remove()
        ffsubsync_option_vad.grid_remove()
        alass_disable_fps_guessing.grid(row=2, column=0, columnspan=5, padx=10, pady=(5,0), sticky="w")
        alass_speed_optimization.grid(row=3, column=0, columnspan=5, padx=10, pady=0, sticky="w")
        alass_split_penalty_slider.grid(row=4, column=0, columnspan=5, padx=10, pady=0, sticky="ew")
    else:
        alass_split_penalty_slider.grid_remove()
        alass_speed_optimization.grid_remove()
        alass_disable_fps_guessing.grid_remove()
        ffsubsync_option_framerate.grid(row=2, column=0, columnspan=5, padx=10, pady=(5,0), sticky="w")
        ffsubsync_option_gss.grid(row=3, column=0, columnspan=5, padx=10, pady=0, sticky="w")
        ffsubsync_option_vad.grid(row=4, column=0, columnspan=5, padx=10, pady=0, sticky="w")
sync_tool_var_auto.trace_add("write", on_sync_tool_change)
sync_tool_label = tk.Label(sync_frame, text="Sync using", fg="black")
sync_tool_label.grid(row=0, column=0, padx=(5, 0), sticky="w")
sync_tool_menu_auto.grid(row=0, column=0, padx=(70, 0), sticky="w")
action_menu_auto.grid(row=6, column=0, padx=(10, 0), pady=(5,10), sticky="w", columnspan=2)
subtitle_input.drop_target_register(DND_FILES)
automatic_tab.columnconfigure(1, weight=1)
batch_mode_var = tk.BooleanVar()
batch_mode_button = tk.Button(
    automatic_tab,
    text=BATCH_MODE_TEXT,
    command=toggle_batch_mode,
    padx=10,
    pady=10,
    fg="white",
    bg=DEFULT_BUTTON_COLOR,
    activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
    activeforeground="white",
    relief=tk.RAISED,
    borderwidth=2,
    cursor="hand2"
)
batch_mode_button.grid(row=5, column=0, padx=(10,2.5), pady=10, sticky="w")
# Ensure button_start_automatic_sync is set to expand horizontally
button_start_automatic_sync.grid(row=5, column=1, padx=(2.5,10), pady=10, sticky="ew")
subtitle_input.dnd_bind('<<Drop>>', on_subtitle_drop)
subtitle_input.bind("<Button-1>", browse_subtitle)
subtitle_input.bind("<Enter>", on_enter)
subtitle_input.bind("<Leave>", on_leave)
video_input.drop_target_register(DND_FILES)
video_input.dnd_bind('<<Drop>>', on_video_drop)
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
        log_message(DROP_SINGLE_SUBTITLE_FILE, "error", tab='manual')
        label_drop_box.config(bg="lightgray")
        return
    filepath = filepaths[0]
    if filepath.lower().endswith(tuple(SUBTITLE_EXTENSIONS)):
        label_drop_box.config(text=filepath, font=("Calibri", 10, "bold"))
        label_drop_box.tooltip_text = filepath
        label_drop_box.config(bg="lightgreen")
        button_clear.grid()
        log_message("", "info", tab='manual')
    else:
        log_message(DROP_SUBTITLE_FILE, "error", tab='manual')
        label_drop_box.config(bg="lightgray")

def browse_file(event=None):
    subtitle_file = filedialog.askopenfilename(filetypes=[(SUBTITLE_FILES_TEXT, ";".join([f"*{ext}" for ext in SUBTITLE_EXTENSIONS]))])
    if subtitle_file:
        label_drop_box.config(text=subtitle_file, font=("Calibri", 10, "bold"))
        label_drop_box.tooltip_text = subtitle_file
        label_drop_box.config(bg="lightgreen")  # Change background color to light green
        button_clear.grid()
        log_message("", "info", tab='manual')
    else:
        # Check if the user canceled the dialog
        if subtitle_file != '':
            log_message(SELECT_SUBTITLE, "error", tab='manual')
            label_drop_box.config(bg="lightgray")  # Restore background color to light gray

def select_subtitle_at_startup():
    if len(sys.argv) > 1:
        subtitle_file = sys.argv[1]
        if os.path.isfile(subtitle_file) and subtitle_file.lower().endswith('.srt'):
            # For manual tab
            label_drop_box.config(text=subtitle_file, font=("Calibri", 10, "bold"))
            label_drop_box.tooltip_text = subtitle_file
            label_drop_box.config(bg="lightgreen")
            log_message("", "info", tab='manual')
            button_clear.grid()
            # For automatic tab
            subtitle_input.config(text=subtitle_file, font=("Calibri", 10, "bold"))
            subtitle_input.tooltip_text = subtitle_file
            subtitle_input.config(bg="lightgreen")
            remove_subtitle_button.grid()
            log_message("", "info", tab='auto')
        elif not os.path.isfile(subtitle_file):
            log_message(FILE_NOT_EXIST, "error", tab='manual')
            label_drop_box.config(bg="lightgray")
        elif len(sys.argv) > 2:
            log_message(MULTIPLE_ARGUMENTS, "error", tab='manual')
            label_drop_box.config(bg="lightgray")
        else:
            log_message(INVALID_FILE_FORMAT, "error", tab='manual')
            label_drop_box.config(bg="lightgray")

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
    if ' ' in new_value:  # Check if the input contains spaces
        return False
    if new_value == '' or new_value == '-':  # Allow empty string
        return True
    if '--' in new_value:  # Disallow double negative signs
        return False
    try:
        value = int(new_value)
        if value > 0:
            entry_milliseconds.config(bg="aliceblue")
        elif value == 0:
            entry_milliseconds.config(bg="white")
        else:
            entry_milliseconds.config(bg="mistyrose1")
        return True  # Input is a valid integer
    except ValueError:
        return False  # Input is not a valid integer

def clear_entry(event):
    if entry_milliseconds.get() == "0":
        entry_milliseconds.delete(0, tk.END)

def clear_label_drop_box():
    label_drop_box.config(text=LABEL_DROP_BOX)
    label_drop_box.config(bg="lightgray")
    del label_drop_box.tooltip_text
    button_clear.grid_remove()

label_drop_box = tk.Label(manual_tab, text=LABEL_DROP_BOX, bg="lightgray", relief="ridge", width=40, height=17, cursor="hand2")
label_separator = ttk.Separator(manual_tab, orient='horizontal')
label_message_manual = tk.Label(manual_tab, text="", fg="black", anchor="center")
label_milliseconds = tk.Label(manual_tab, text=LABEL_SHIFT_SUBTITLE, anchor="w")
entry_milliseconds = tk.Entry(manual_tab, cursor="xterm", width=15, justify="center", borderwidth=2, validate='key')
entry_milliseconds.config(validatecommand=(root.register(validate_input), '%P'))
button_clear = tk.Button(
    manual_tab, text="X",
    command=clear_label_drop_box,
    font='Arial 8 bold',
    padx=4,
    pady=0,
    fg="white",
    bg=DEFULT_BUTTON_COLOR,
    activeforeground="white",
    activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
    relief=tk.RIDGE,
    borderwidth=1,
    cursor="hand2"
)
button_minus = tk.Button(
    manual_tab, text="-",
    command=decrease_milliseconds,
    padx=10,
    pady=5,
    fg="white",
    bg=DEFULT_BUTTON_COLOR,
    activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
    activeforeground="white",
    relief=tk.RAISED,
    borderwidth=2,
    cursor="hand2"
)
button_plus = tk.Button(
    manual_tab, text="+",
    command=increase_milliseconds,
    padx=10,
    pady=5,
    fg="white",
    bg=DEFULT_BUTTON_COLOR,
    activebackground=DEFAULT_BUTTON_COLOR_ACTIVE,
    activeforeground="white",
    relief=tk.RAISED,
    borderwidth=2,
    cursor="hand2"
)
button_sync = tk.Button(
    manual_tab,
    text=SHIFT_SUBTITLE_TEXT,
    command=sync_subtitle,
    padx=10,
    pady=10,
    fg="white",
    bg=BUTTON_COLOR_MANUAL,
    activebackground=BUTTON_COLOR_MANUAL_ACTIVE,
    activeforeground="white",
    relief=tk.RAISED,
    borderwidth=2,
    cursor="hand2"
)
save_to_desktop_var = tk.BooleanVar()
check_save_to_desktop = tk.Checkbutton(manual_tab, text=OPTION_SAVE_TO_DESKTOP, variable=save_to_desktop_var, command=lambda: checkbox_selected(save_to_desktop_var))
replace_original_var = tk.BooleanVar()
check_replace_original = tk.Checkbutton(manual_tab, text=OPTION_REPLACE_ORIGINAL_SUBTITLE, variable=replace_original_var, command=lambda: checkbox_selected(replace_original_var))
label_drop_box.grid(row=0, column=0, padx=10, pady=(10,5), sticky="nsew", columnspan=6)
button_clear.grid(row=0, column=3, padx=(0,12), pady=(12,5), sticky="ne")
button_clear.grid_remove()
label_separator.grid(row=1, column=0, sticky="ew", padx=10, pady=5, columnspan=6)
label_milliseconds.grid(row=2, column=0, padx=10, pady=5, sticky="w")
button_minus.grid(row=2, column=1, padx=(0,5), pady=5, sticky="ew")
entry_milliseconds.grid(row=2, column=2, pady=5, sticky="ew", ipady=7)
button_plus.grid(row=2, column=3, padx=(5,10), pady=5, sticky="ew")
button_sync.grid(row=3, column=0, padx=10, pady=10, sticky="ew",  columnspan=6)
check_save_to_desktop.grid(row=4, column=0, padx=10, pady=5, sticky="w", columnspan=3)
check_replace_original.grid(row=4, column=1, padx=(10), pady=5, sticky="e", columnspan=3)
label_drop_box.bind("<Button-1>", browse_file)
label_drop_box.bind("<Enter>", on_enter)
label_drop_box.bind("<Leave>", on_leave)
label_drop_box.bind("<Configure>", update_wraplengt)
label_drop_box.drop_target_register(DND_FILES)
label_drop_box.dnd_bind('<<Drop>>', on_drop)
label_message_manual.bind("<Configure>", update_wraplengt)
label_message_manual.grid_remove()
entry_milliseconds.bind("<FocusIn>", clear_entry)
# Create tooltips for checkboxes and entry field
tooltip_save_to_desktop = ToolTip(check_save_to_desktop, TOOLTIP_SAVE_TO_DESKTOP)
tooltip_replace_original = ToolTip(check_replace_original, TOOLTIP_REPLACE_ORIGINAL)
tooltip_milliseconds = ToolTip(entry_milliseconds, "1 second = 1000ms")
# ---------------- Manual Tab ---------------- #
root.update_idletasks()
# Place the window at the top right corner of the screen
place_window_top_right()
# Select subtitle file if specified as argument
select_subtitle_at_startup()
# Calculate minimum width and height based on elements inside
min_width = label_drop_box.winfo_reqwidth() + 95 
min_height_automatic = sum(widget.winfo_reqheight() for widget in (label_drop_box, label_separator, button_sync, check_save_to_desktop)) + 200
min_height_manual = sum(widget.winfo_reqheight() for widget in (label_drop_box, label_separator, label_milliseconds, entry_milliseconds, button_minus, button_plus, button_sync, check_save_to_desktop, check_replace_original))
min_height = max(min_height_automatic, min_height_manual)
root.minsize(min_width, min_height)  # Set minimum size for the window
# if icon exists, set it as the window icon
if os.path.exists('icon.ico'):
    root.iconbitmap('icon.ico')
root.deiconify() # Show the window after it's been built
root.mainloop()