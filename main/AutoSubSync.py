import os
import sys
import re
import shutil
import subprocess
import threading
import xml.etree.ElementTree as ET
import json
import webbrowser
# Tkinter GUI
import tkinter as tk
import tkinter.font as tkFont
from datetime import datetime
from tkinter import filedialog, ttk, messagebox, PhotoImage, Menu, simpledialog
from tkinterdnd2 import DND_FILES, TkinterDnD
import requests
import psutil
import signal
import ctypes
import cchardet, charset_normalizer, chardet
from alass_encodings import enc_list
from functions.get_platform import platform
from constants import *
from theme import *
from texts_constants import *
from config import VERSION, config, default_settings
from functions.get_config import config_dir, config_path
from functions.get_desktop_path import desktop_path



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

    def shift_time_smi(line):
        def replacer(match):
            start_ms = int(match.group(1))
            shifted_ms = start_ms + milliseconds
            shifted_ms = max(0, shifted_ms)  # Ensure timestamp doesn't go negative
            return f"<SYNC Start={shifted_ms}"

        return re.sub(r"<SYNC Start=(\d+)", replacer, line)

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
            if format_type == "smi":
                # SMI format uses milliseconds directly
                return int(time_str)
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
        if format_type == "smi":
            # SMI format uses milliseconds directly
            return str(ms)
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
        elif file_extension == ".smi":
            new_lines.append(shift_time_smi(line))
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

def set_language(lang):
    global LANGUAGE
    LANGUAGE = lang
    update_config("language", LANGUAGE)
    restart_program()

def set_theme(theme):
    global THEME
    THEME = theme
    update_config("theme", THEME)
    restart_program()



def save_log_file(log_window, suffix=""):
    if keep_logs:
        # Save log window content to a log file
        log_content = log_window.get("1.0", tk.END)
        logs_folder = os.path.join(config_dir, f"{PROGRAM_NAME}_logs")
        os.makedirs(logs_folder, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_filename = os.path.join(logs_folder, f"{timestamp}{suffix}.txt")
        with open(log_filename, "w", encoding="utf-8") as log_file:
            log_file.write(log_content)


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
