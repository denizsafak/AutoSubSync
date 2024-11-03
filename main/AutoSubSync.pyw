import os
import sys
import re
import chardet
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import xml.etree.ElementTree as ET
program_name = "AutoSubSync"
version = "v2.4"
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
        log_message(f"Error loading subtitle file: {str(e)}", "error", tab='manual')
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
            log_message(f"Failed to convert timestamp '{timestamp}' for format '{format_type}'", "error")
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
                        log_message(f"Error parsing time string '{time_str}'", "error", tab='manual')
                        return None
                else:
                    # Handle 'SSSSSS.MS' seconds format
                    seconds_match = re.match(r'^(\d+(?:\.\d+)?)(?:s)?$', time_str)
                    if seconds_match:
                        total_seconds = float(seconds_match.group(1))
                        return int(total_seconds * 1000)
                    else:
                        log_message(f"Error parsing time string '{time_str}'", "error", tab='manual')
                        return None
            elif format_type == 'ass_ssa':
                parts = re.split(r'[:.]', time_str)
                h, m, s, cs = map(int, parts)
                return (h * 3600 + m * 60 + s) * 1000 + (cs * 10)
        except (ValueError, IndexError) as e:
            log_message(f"Error parsing time string '{time_str}' for format '{format_type}': {str(e)}", "error", tab='manual')
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
            response = messagebox.askyesno(
                "Subtitle Change Confirmation",
                f"Adjusting again by {milliseconds}ms, will make a total difference of {total_shifted}ms. Proceed?"
            )
            if not response:
                return
    elif save_to_desktop:
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        new_subtitle_file = os.path.join(desktop_path, f"{total_shifted}ms_{filename}")
    else:
        new_subtitle_file = os.path.join(os.path.dirname(subtitle_file), f"{total_shifted}ms_{filename}")

    if os.path.exists(new_subtitle_file) and not replace_original:
        replace = messagebox.askyesno(
            "File Exists",
            f"A file with the name '{os.path.basename(new_subtitle_file)}' already exists. Do you want to replace it?"
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
            log_message(f"Success! Subtitle shifted by {milliseconds} milliseconds and saved to: {new_subtitle_file}", "success", new_subtitle_file, tab='manual')
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
        log_message(f"Error saving subtitle file: {str(e)}", "error", tab='manual')
# Shift Subtitle End

def sync_subtitle():
    if hasattr(label_drop_box, 'tooltip_text'):
        subtitle_file = label_drop_box.tooltip_text
        if subtitle_file:
            try:
                milliseconds = int(entry_milliseconds.get())
                if milliseconds == 0:
                    log_message("Please enter a non-zero value for milliseconds.", "error", tab='manual')
                    return
                save_to_desktop = save_to_desktop_var.get()  # Get the value of the save_to_desktop switch
                replace_original = replace_original_var.get()  # Get the value of the replace_original switch
                if save_to_desktop and replace_original:
                    log_message("Please select only one option: Save to Desktop or Replace Original Subtitle.", "error")
                    return
                # Shift subtitle in a separate thread to keep the GUI responsive
                threading.Thread(target=shift_subtitle, args=(subtitle_file, milliseconds, save_to_desktop, replace_original)).start()
            except ValueError:
                log_message("Please enter a valid number of milliseconds.", "error", tab='manual')
    else:
        log_message("Please select a subtitle.", "error", tab='manual')

def on_drop(event):
    filepath = event.data.strip("{}")  # Remove curly braces from the path
    # Check if the dropped file has the .srt extension
    if filepath.lower().endswith(('.srt', '.vtt', '.sbv', '.sub', '.ass', '.ssa', '.dfxp', '.ttml', '.itt', '.stl')):
        label_drop_box.config(text=filepath, font=("Calibri", 10, "bold"))
        label_drop_box.tooltip_text = filepath
        label_drop_box.config(bg="lightgreen")  # Change background color to light green
        log_message("", "info", tab='manual')
    else:
        log_message("Please drop a subtitle file.", "error", tab='manual')
        label_drop_box.config(bg="lightgray")  # Restore background color to light gray

def browse_file(event=None):
    subtitle_file = filedialog.askopenfilename(filetypes=[("Subtitle files", "*.srt;*.vtt;*.sbv;*.sub;*.ass;*.ssa;*.dfxp;*.ttml;*.itt;*.stl")])
    if subtitle_file:
        label_drop_box.config(text=subtitle_file, font=("Calibri", 10, "bold"))
        label_drop_box.tooltip_text = subtitle_file
        label_drop_box.config(bg="lightgreen")  # Change background color to light green
        log_message("", "info", tab='manual')
    else:
        # Check if the user canceled the dialog
        if subtitle_file != '':
            log_message("Please select a subtitle", "error", tab='manual')
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
            # For automatic tab
            label_subtitle.config(text=subtitle_file, font=("Calibri", 10, "bold"))
            label_subtitle.tooltip_text = subtitle_file
            label_subtitle.config(bg="lightgreen")
            log_message("", "info", tab='auto')
        elif not os.path.isfile(subtitle_file):
            log_message("File specified in the argument does not exist.", "error", tab='manual')
            label_drop_box.config(bg="lightgray")
        elif len(sys.argv) > 2:
            log_message("Multiple arguments provided. Please provide only one subtitle file path.", "error", tab='manual')
            label_drop_box.config(bg="lightgray")
        else:
            print(sys.argv[1])
            log_message("Invalid file format. Please provide a subtitle file.", "error", tab='manual')
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
            entry_milliseconds.config(bg="aliceblue")  # Set background color to light green for positive numbers
        elif value == 0:
            entry_milliseconds.config(bg="white")
        else:
            entry_milliseconds.config(bg="mistyrose1")  # Set background color to salmon for negative numbers
        return True  # Input is a valid integer
    except ValueError:
        return False  # Input is not a valid integer

def clear_entry(event):
    if entry_milliseconds.get() == "0":
        entry_milliseconds.delete(0, tk.END)

def on_enter(event):
    event.widget.config(bg="lightblue")

def on_leave(event):
    if hasattr(event.widget, 'tooltip_text'):
        event.widget.config(bg="lightgreen")  # Change background color to light green
    else:
        event.widget.config(bg="lightgray")  # Restore background color to light gray

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
    if msg_type == "success":
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
        selected_file = '"' + os.path.realpath(filepath) + '"'
        os.system(f'start explorer /select,{selected_file}')

def update_wraplengt(event=None):
    event.widget.config(wraplength=event.widget.winfo_width() - 60)

def checkbox_selected(var):
    if var.get():
        if var == save_to_desktop_var:
            replace_original_var.set(False)
        elif var == replace_original_var:
            save_to_desktop_var.set(False)

def checkbox_selected_auto(var):
    if var.get():
        if var == save_to_desktop_var_auto:
            replace_original_var_auto.set(False)
        elif var == replace_original_var_auto:
            save_to_desktop_var_auto.set(False)

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

# Define tooltip text for checkboxes
TOOLTIP_SAVE_TO_DESKTOP = "Check this box if you want to save the new subtitle to your Desktop. If unchecked, it will be saved in the original subtitle's folder."
TOOLTIP_REPLACE_ORIGINAL = "Check this box if you want to replace the original subtitle file with the new one. Please be careful. It will overwrite the current subtitle."
TOOLTIP_GSS = "--gss: Use golden-section search to find the optimal ratio between video and subtitle framerates (by default, only a few common ratios are evaluated)"
TOOLTIP_VAD = "--vad=auditok: Auditok can sometimes work better in the case of low-quality audio than WebRTC's VAD. Auditok does not specifically detect voice, but instead detects all audio; this property can yield suboptimal syncing behavior when a proper VAD can work well, but can be effective in some cases."
TOOLTIP_FRAMERATE = "--no-fix-framerate: If specified, ffsubsync will not attempt to correct a framerate mismatch between reference and subtitles. This can be useful when you know that the video and subtitle framerates are same, only the subtitles are out of sync."
root = TkinterDnD.Tk()
root.title(program_name +" "+version)
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
tab_control.add(automatic_tab, text='Automatic Sync')
tab_control.add(manual_tab, text='Manual Sync')
# Place tab_control
tab_control.grid(row=0, column=0, sticky="nsew")
# Add "GitHub" label on the right side of the tabs
github_label = ttk.Label(root, text="GitHub", cursor="hand2", foreground="#007FFF", background="SystemButtonFace", underline=True)
github_label.bind("<Button-1>", lambda event: os.system("start https://github.com/denizsafak/AutoSubSync"))
github_label.grid(row=0, column=0, sticky="ne", padx=10, pady=(10,0))
# Customizing the style of the tabs
style = ttk.Style()
# Define colors
COLOR_PRIMARY = "#C0C0C0"       # Inactive tab color
COLOR_SECONDARY = "#707070"     # Active tab color
COLOR_BACKGROUND = "SystemButtonFace"    # Background color
COLOR_TEXT = "black"            # Text color
COLOR_PROGRESSBAR = "#00a31e"  # Bright green color for progress bar
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
def browse_subtitle(event=None):
    subtitle_file_auto = filedialog.askopenfilename(filetypes=[("Subtitle files", "*.srt;*.vtt;*.sbv;*.sub;*.ass;*.ssa;*.dfxp;*.ttml;*.itt;*.stl")])
    filetypes=[("Subtitle files", "*.srt;*.vtt;*.sbv;*.sub;*.ass;*.ssa;*.dfxp;*.ttml;*.itt;*.stl")]
    if subtitle_file_auto:
        label_subtitle.config(text=subtitle_file_auto, font=("Calibri", 10, "bold"))
        label_subtitle.tooltip_text = subtitle_file_auto
        label_subtitle.config(bg="lightgreen")
        log_message("", "info", tab='auto')
    else:
        if subtitle_file_auto != '':
            log_message("Please select a subtitle", "error", tab='auto')
            label_subtitle.config(bg="lightgray")

def browse_video(event=None):
    video_file = filedialog.askopenfilename(filetypes=[("Video or subtitle", "*.srt;*.vtt;*.sbv;*.sub;*.ass;*.ssa;*.dfxp;*.ttml;*.itt;*.stl;*.mp4;*.mkv;*.avi;*.webm;*.flv;*.mov;*.wmv;*.mpg;*.mpeg;*.m4v;*.3gp;*.h264;*.h265;*.hevc")])
    if video_file:
        label_video.config(text=video_file, font=("Calibri", 10, "bold"))
        label_video.tooltip_text = video_file
        label_video.config(bg="lightgreen")
        log_message("", "info", tab='auto')
        if video_file.lower().endswith(('.srt', '.vtt', '.sbv', '.sub', '.ass', '.ssa', '.dfxp', '.ttml', '.itt', '.stl')):
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
            log_message("Please select a video or subtitle.", "error", tab='auto')
            label_video.config(bg="lightgray")

def on_video_drop(event):
    filepath = event.data.strip("{}")
    if filepath.lower().endswith(('.srt', '.vtt', '.sbv', '.sub', '.ass', '.ssa', '.dfxp', '.ttml', '.itt', '.stl', '.mp4', '.mkv', '.avi', '.webm', '.flv', '.mov', '.wmv', '.mpg', '.mpeg', '.m4v', '.3gp', '.h264', '.h265', '.hevc')):
        label_video.config(text=filepath, font=("Calibri", 10, "bold"))
        label_video.tooltip_text = filepath
        label_video.config(bg="lightgreen")
        log_message("", "info", tab='auto')
        if filepath.lower().endswith(('.srt', '.vtt', '.sbv', '.sub', '.ass', '.ssa', '.dfxp', '.ttml', '.itt', '.stl')):
            # If the video file is a subtitle, disable parameters
            ffsubsync_option_gss.config(state=tk.DISABLED)
            ffsubsync_option_vad.config(state=tk.DISABLED)
            ffsubsync_option_framerate.config(state=tk.DISABLED)
        else:
            ffsubsync_option_gss.config(state=tk.NORMAL)
            ffsubsync_option_vad.config(state=tk.NORMAL)
            ffsubsync_option_framerate.config(state=tk.NORMAL)
    else:
        log_message("Please drop a video or subtitle.", "error", tab='auto')

def on_subtitle_drop(event):
    filepath = event.data.strip("{}")
    if filepath.lower().endswith(('.srt', '.vtt', '.sbv', '.sub', '.ass', '.ssa', '.dfxp', '.ttml', '.itt', '.stl')):
        label_subtitle.config(text=filepath, font=("Calibri", 10, "bold"))
        label_subtitle.tooltip_text = filepath
        label_subtitle.config(bg="lightgreen")
        log_message("", "info", tab='auto')
    else:
        log_message("Please drop a subtitle file.", "error", tab='auto')
        
process = None
def start_automatic_sync():
    global process, subtitle_file, video_file, output_subtitle_file
    subtitle_file = getattr(label_subtitle, 'tooltip_text', None)
    video_file = getattr(label_video, 'tooltip_text', None)
    if subtitle_file == video_file:
        log_message("Please select different subtitle files.", "error", tab='auto')
        return
    if not subtitle_file and not video_file:
        log_message("Please select both video/reference subtitle and subtitle file.", "error", tab='auto')
        return
    if not subtitle_file:
        log_message("Please select a subtitle file.", "error", tab='auto')
        return
    if not video_file:
        log_message("Please select a video or reference subtitle file.", "error", tab='auto')
        return
    if not os.path.exists(subtitle_file):
        log_message("Subtitle file does not exist.", "error", tab='auto')
        return
    if not os.path.exists(video_file):
        log_message("Video file does not exist.", "error", tab='auto')
        return
    if save_to_desktop_var_auto.get():
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        output_subtitle_file = os.path.join(desktop_path, f"autosync_{os.path.basename(subtitle_file)}")
    elif replace_original_var_auto.get():
        output_subtitle_file = subtitle_file
    else:
        output_subtitle_file = os.path.join(os.path.dirname(subtitle_file), f"autosync_{os.path.basename(subtitle_file)}")
    if os.path.exists(output_subtitle_file) and not replace_original_var_auto.get():
        replace_confirmation = tk.messagebox.askyesno("File Exists", f"A file with the name '{os.path.basename(output_subtitle_file)}' already exists. Do you want to replace it?")
        if not replace_confirmation:
            return
    # if the video_file is a subtitle, don't add parameters
    if not video_file.lower().endswith(('.srt', '.vtt', '.sbv', '.sub', '.ass', '.ssa', '.dfxp', '.ttml', '.itt', '.stl')):
        if ffsubsync_option_framerate_var.get():
            cmd += " --no-fix-framerate"
        if ffsubsync_option_gss_var.get():
            cmd += (" --gss")
        if ffsubsync_option_vad_var.get():
            cmd += (" --vad=auditok")
    def cancel_automatic_sync():
        global process, ffsubsync_option_vad, ffsubsync_option_gss, ffsubsync_option_framerate
        if process:
            try:
                subprocess.Popen(['taskkill', '/F', '/T', '/PID', str(process.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
                process = None
                log_message("Automatic synchronization cancelled.", "error", tab='auto')
            except Exception as e:
                log_message(f"Error occurred during process termination: {e}", "error", tab='auto')
        else:
            log_message("No synchronization process to cancel.", "error", tab='auto')
        restore_window()
    def cancel_process_on_window_close ():
        if process:
            cancel_automatic_sync()
        root.destroy()
        os._exit(0)
    root.protocol("WM_DELETE_WINDOW", cancel_process_on_window_close)

    def restore_window():
        label_subtitle.grid()
        label_video.grid()
        check_save_to_desktop_auto.grid()
        check_replace_original_auto.grid()
        button_start_automatic_sync.grid()
        ffsubsync_option_gss.grid()
        ffsubsync_option_vad.grid()
        ffsubsync_option_framerate.grid()
        log_window.grid_remove()
        progress_bar.grid_remove()
        button_generate_again.grid_remove()
        button_cancel_automatic_sync.grid_remove()
        root.update_idletasks()

    def generate_again():
        label_subtitle.config(text="Drag and drop the unsynchronized subtitle file here or click to browse.", bg="lightgray", font=("Segoe UI", 9, "normal"))
        del label_subtitle.tooltip_text
        label_video.config(text="Drag and drop video or reference subtitle file here or click to browse.", bg="lightgray", font=("Segoe UI", 9, "normal"))
        del label_video.tooltip_text
        label_subtitle.grid()
        label_video.grid()
        check_save_to_desktop_auto.grid()
        check_replace_original_auto.grid()
        button_start_automatic_sync.grid()
        ffsubsync_option_gss.grid()
        ffsubsync_option_vad.grid()
        ffsubsync_option_framerate.grid()
        log_window.grid_remove()
        progress_bar.grid_remove()
        button_generate_again.grid_remove()
        button_cancel_automatic_sync.grid_remove()
        label_message_auto.grid_remove()
        ffsubsync_option_gss.config(state=tk.NORMAL)
        ffsubsync_option_vad.config(state=tk.NORMAL)
        ffsubsync_option_framerate.config(state=tk.NORMAL)
        root.update_idletasks()

    def run_subprocess():
        global process, progress_line_number, subtitle_file, video_file, cmd, output_subtitle_file
        # Convert subtitles to SRT Begin
        def convert_to_srt(subtitle_file):
            file_extension = os.path.splitext(subtitle_file)[-1].lower()
            base_name = os.path.basename(os.path.splitext(subtitle_file)[0])
            srt_file = os.path.join(os.path.dirname(subtitle_file), 'converted_' + base_name + '.srt')
            log_window.insert(tk.END, f"Preparing " + base_name + file_extension + " for automatic sync...\n")
            if file_extension == '.ttml':
                convert_ttml_or_dfxo_to_srt(subtitle_file, srt_file)
            elif file_extension == '.dfxp':
                convert_ttml_or_dfxo_to_srt(subtitle_file, srt_file)
            elif file_extension == '.itt':
                convert_ttml_or_dfxo_to_srt(subtitle_file, srt_file)
            elif file_extension == '.vtt':
                convert_vtt_to_srt(subtitle_file, srt_file)
            elif file_extension == '.sbv':
                convert_sbv_to_srt(subtitle_file, srt_file)
            elif file_extension == '.sub':
                convert_sub_to_srt(subtitle_file, srt_file)
            elif file_extension == '.ass':
                convert_ass_to_srt(subtitle_file, srt_file)
            elif file_extension == '.ssa':
                convert_ass_to_srt(subtitle_file, srt_file)
            elif file_extension == '.stl':
                convert_stl_to_srt(subtitle_file, srt_file)
            else:
                log_window.insert(tk.END, f"Error: Conversion for {file_extension} is not supported.\n")
                return None
            log_window.insert(tk.END, f"Subtitle successfully converted and saved to: {srt_file}.\n")
            return srt_file

        def convert_sub_to_srt(input_file, output_file):
            try:
                log_window.insert(tk.END, f"Converting SUB to SRT...\n")
                with open(input_file, 'r', encoding='utf-8') as sub, open(output_file, 'w', encoding='utf-8') as srt:
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
            except Exception as e:
                log_window.insert(tk.END, f"Error converting SUB to SRT: {str(e)}\n")

        def convert_ass_to_srt(input_file, output_file):
            try:
                log_window.insert(tk.END, f"Converting ASS/SSA to SRT...\n")
                with open(input_file, 'r', encoding='utf-8') as ass, open(output_file, 'w', encoding='utf-8') as srt:
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
                            buffer = f"{srt_counter}\n{format_ass_time(start)} --> {format_ass_time(end)}\n{text}"
                        elif collecting:
                            buffer += f"\n{line.strip()}"
                    if buffer:
                        srt.write(f"{buffer}\n\n")
            except Exception as e:
                log_window.insert(tk.END, f"Error converting ASS/SSA to SRT: {str(e)}\n")

        def strip_namespace(tag):
            if '}' in tag:
                return tag.split('}', 1)[1]
            return tag

        def convert_ttml_or_dfxo_to_srt(input_file, output_file):
            try:
                log_window.insert(tk.END, f"Converting TTML/DFXP/ITT to SRT...\n")
                tree = ET.parse(input_file)
                root = tree.getroot()

                captions = [elem for elem in root.iter() if strip_namespace(elem.tag) == 'p']

                with open(output_file, 'w', encoding='utf-8') as srt:
                    for idx, caption in enumerate(captions, 1):
                        begin = format_ttml_time(caption.attrib.get('begin'))
                        end = format_ttml_time(caption.attrib.get('end'))
                        # Handle text and line breaks
                        text_parts = []
                        for elem in caption.iter():
                            if strip_namespace(elem.tag) == 'br':
                                text_parts.append('\n')
                            elif elem.text:
                                text_parts.append(elem.text.strip())
                            if elem.tail:
                                text_parts.append(elem.tail.strip())
                        # Join parts with space only between text (not newlines)
                        text = ''
                        for i, part in enumerate(text_parts):
                            if part:
                                if i > 0 and part != '\n' and text_parts[i-1] != '\n':
                                    text += ' '
                                text += part
                        srt.write(f"{idx}\n")
                        srt.write(f"{begin} --> {end}\n")
                        srt.write(f"{text}\n\n")
            except Exception as e:
                log_window.insert(tk.END, f"Error converting TTML/DFXP/ITT to SRT: {str(e)}\n")

        def convert_vtt_to_srt(input_file, output_file):
            try:
                log_window.insert(tk.END, f"Converting VTT to SRT...\n")
                with open(input_file, 'r', encoding='utf-8') as vtt, open(output_file, 'w', encoding='utf-8') as srt:
                    srt_counter = 1
                    in_cue = False
                    for line in vtt:
                        match = re.match(r'(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})', line)
                        if match:
                            in_cue = True
                            start, end = match.groups()
                            srt.write(f"{srt_counter}\n")
                            srt.write(f"{start.replace('.', ',')} --> {end.replace('.', ',')}\n")
                            srt_counter += 1
                            text = ""
                            while True:
                                next_line = next(vtt).strip()
                                if not next_line:
                                    break
                                text += re.sub(r'<[^>]+>', '', next_line) + "\n"
                            srt.write(f"{text.strip()}\n\n")
                        elif in_cue:
                            continue
                        elif line.strip() == "":
                            in_cue = False
            except Exception as e:
                log_window.insert(tk.END, f"Error converting VTT to SRT: {str(e)}\n")

        def convert_sbv_to_srt(input_file, output_file):
            try:
                log_window.insert(tk.END, f"Converting SBV to SRT...\n")
                with open(input_file, 'r', encoding='utf-8') as sbv, open(output_file, 'w', encoding='utf-8') as srt:
                    srt_counter = 1
                    while True:
                        timestamps = sbv.readline().strip()
                        if not timestamps:
                            break
                        text_lines = []
                        while True:
                            line = sbv.readline().strip()
                            if not line:
                                break
                            text_lines.append(line)
                        start, end = timestamps.split(',')
                        srt.write(f"{srt_counter}\n")
                        srt.write(f"{format_sbv_time(start)} --> {format_sbv_time(end)}\n")
                        srt.write('\n'.join(text_lines) + '\n\n')
                        srt_counter += 1
            except Exception as e:
                log_window.insert(tk.END, f"Error converting SBV to SRT: {str(e)}\n")

        def convert_stl_to_srt(input_file, output_file):
            try:
                log_window.insert(tk.END, f"Converting STL to SRT...\n")
                with open(input_file, 'rb') as stl, open(output_file, 'w', encoding='utf-8') as srt:
                    stl_data = stl.read()
                    encoding = chardet.detect(stl_data)['encoding']
                    lines = stl_data.decode(encoding).splitlines()
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
            except Exception as e:
                log_window.insert(tk.END, f"Error converting STL to SRT: {str(e)}\n")

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
            ms = ms.ljust(3, '0')[:3]  # Pad with zeros on the right and truncate to three digits
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
        # Convert subtitles to SRT End

        # .ass and .ssa excluded because ffsubsync can work with them.
        if subtitle_file.lower().endswith(('.vtt', '.sbv', '.sub', '.dfxp', '.ttml', '.itt', '.stl')):
            subtitle_file = convert_to_srt(subtitle_file)
        if video_file.lower().endswith(('.vtt', '.sbv', '.sub', '.dfxp', '.ttml', '.itt', '.stl')):
            video_file = convert_to_srt(video_file)

        try:
            # FFSUBSYNC CAN ONLY OUTPUT .ASS AND .SRT, SO THIS IS NECESSARY.
            if not output_subtitle_file.lower().endswith(('.srt', '.ass', '.ssa')):
                output_subtitle_file = output_subtitle_file.rsplit('.', 1)[0] + '.srt'
            cmd = f'ffs "{video_file}" -i "{subtitle_file}" -o "{output_subtitle_file}"'
            #log_window.insert(tk.END, 'Running command: \n"' + cmd +'"\n')
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            progress_bar["value"] = 1
            # if video file is not a subtitle
            if video_file.lower().endswith(('.srt', '.vtt', '.sbv', '.sub', '.ass', '.ssa', '.dfxp', '.ttml', '.itt', '.stl')):
                log_window.insert(tk.END, "Using reference subtitle for syncing...\n")
            else:
                log_window.insert(tk.END, "Using video for syncing...\n")
                if ffsubsync_option_framerate_var.get():
                    log_window.insert(tk.END, "Enabled: Don't fix framerate.\n")
                if ffsubsync_option_gss_var.get():
                    log_window.insert(tk.END, "Enabled: Golden-section search.\n")
                if ffsubsync_option_vad_var.get():
                    log_window.insert(tk.END, "Enabled: Using auditok instead of WebRTC's VAD.\n") 
            log_window.insert(tk.END, "Syncing started:\n")
            progress_line_number = log_window.index(tk.END).split(".")[0]  # Get the current line number
            for output in process.stdout:
                match_percentage = re.search(r'\b(\d+(\.\d+)?)%\|', output)
                if match_percentage:
                    percentage = float(match_percentage.group(1))
                    root.after(10, update_progress_auto, progress_bar, percentage)
                if "%" in output:  # If the output line contains a percentage, it's a progress update
                    log_window.delete("end-2l", "end-1l")  # Delete the last progress update
                    log_window.insert(tk.END, output)  # Insert the new progress update
                else:  # Otherwise, it's a regular log message
                    log_window.insert(tk.END, output)
                log_window.see(tk.END)
            log_window.insert(tk.END, "\nSyncing ended.\n")
            if process is not None:
                process.wait()
                if process.returncode == 0:
                    log_message(f"Success! Synchronized subtitle saved to: {output_subtitle_file}", "success", output_subtitle_file, tab='auto')
                    button_cancel_automatic_sync.grid_remove()
                    log_window.grid(pady=(10, 10), rowspan=2)
                    button_generate_again.grid()
                else:
                    log_message("Error occurred during synchronization. Please check the log messages.", "error", tab='auto')
                    button_cancel_automatic_sync.grid_remove()
                    log_window.grid(pady=(10, 10), rowspan=2)
                    button_generate_again.grid()
        except Exception as e:
            log_message(f"Error occurred: {e}", "error", tab='auto')
        progress_bar.grid_remove()
        log_window.see(tk.END)
        automatic_tab.rowconfigure(1, weight=1)
        root.update_idletasks()

    def update_progress_auto(progress_bar, value):
        adjusted_value = min(97, max(1, value))
        progress_bar["value"] = adjusted_value
    try:
        label_subtitle.grid_remove()
        label_video.grid_remove()
        check_save_to_desktop_auto.grid_remove()
        check_replace_original_auto.grid_remove()
        button_start_automatic_sync.grid_remove()
        ffsubsync_option_gss.grid_remove()
        ffsubsync_option_vad.grid_remove()
        ffsubsync_option_framerate.grid_remove()
        label_message_auto.grid_remove()
        button_cancel_automatic_sync = tk.Button(
            automatic_tab,
            text="Cancel",
            command=cancel_automatic_sync,
            padx=10,
            pady=10,
            fg="white",
            bg="#707070",  # Grey background color
            activebackground="#616161",  # Darker grey when active
            activeforeground="white",
            relief=tk.RAISED,
            borderwidth=2,
            cursor="hand2"
        )
        button_cancel_automatic_sync.grid(row=6, column=0, padx=10, pady=(0,10), sticky="ew", columnspan=2)
        button_generate_again = tk.Button(
            automatic_tab,
            text="Generate Again",
            command=generate_again,
            padx=10,
            pady=10,
            fg="white",
            bg="#007FFF",
            activebackground="#0061c2",
            activeforeground="white",
            relief=tk.RAISED,
            borderwidth=2,
            cursor="hand2"
        )
        button_generate_again.grid(row=11, column=0, padx=10, pady=(00,10), sticky="ew", columnspan=2)
        button_generate_again.grid_remove()
        log_window = tk.Text(automatic_tab, wrap="word")
        log_window.config(font=("Arial", 7))
        log_window.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew")
        progress_bar = ttk.Progressbar(automatic_tab, orient="horizontal", length=200, mode="determinate")
        progress_bar.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="ew")
        root.update_idletasks()
        threading.Thread(target=run_subprocess).start()
    except Exception as e:
        log_message(f"Error occurred: {e}", "error", tab='auto')
    automatic_tab.rowconfigure(0, weight=1)
    automatic_tab.rowconfigure(1, weight=0)
label_message_auto = tk.Label(automatic_tab, text="", fg="black", anchor="center")
label_subtitle = tk.Label(automatic_tab, text="Drag and drop the unsynchronized subtitle file here or click to browse.", bg="lightgray", relief="ridge", width=40, height=5, cursor="hand2")
label_video = tk.Label(automatic_tab, text="Drag and drop video or reference subtitle file here or click to browse.", bg="lightgray", relief="ridge", width=40, height=5, cursor="hand2")
label_video_text = tk.Label(automatic_tab, text="Video/Reference subtitle", fg="black", relief="ridge", padx=5, borderwidth=1)
label_video_text.place(in_=label_video, relx=0, rely=0, anchor="nw")
label_subtitle_text = tk.Label(automatic_tab, text="Subtitle", fg="black", relief="ridge", padx=5, borderwidth=1) 
label_subtitle_text.place(in_=label_subtitle, relx=0, rely=0, anchor="nw")
button_start_automatic_sync = tk.Button(
    automatic_tab,
    text="Start Automatic Sync",
    command=start_automatic_sync,
    padx=10,
    pady=10,
    fg="white",
    bg="#007FFF",
    activebackground="#0061c2",
    activeforeground="white",
    relief=tk.RAISED,
    borderwidth=2,
    cursor="hand2"
)
ffsubsync_option_framerate_var = tk.BooleanVar()
ffsubsync_option_gss_var = tk.BooleanVar()
ffsubsync_option_vad_var = tk.BooleanVar()
save_to_desktop_var_auto = tk.BooleanVar()
replace_original_var_auto = tk.BooleanVar()
ffsubsync_option_framerate = tk.Checkbutton(automatic_tab, text="Don't fix framerate", variable=ffsubsync_option_framerate_var)
ffsubsync_option_gss = tk.Checkbutton(automatic_tab, text="Use golden-section search", variable=ffsubsync_option_gss_var)
ffsubsync_option_vad = tk.Checkbutton(automatic_tab, text="Use auditok instead of WebRTC's VAD", variable=ffsubsync_option_vad_var)
check_save_to_desktop_auto = tk.Checkbutton(automatic_tab, text="Save to Desktop", variable=save_to_desktop_var_auto, command=lambda: checkbox_selected_auto(save_to_desktop_var_auto))
check_replace_original_auto = tk.Checkbutton(automatic_tab, text="Replace original subtitle", variable=replace_original_var_auto, command=lambda: checkbox_selected_auto(replace_original_var_auto))
tooltip_ffsubsync_option_framerate = ToolTip(ffsubsync_option_framerate, TOOLTIP_FRAMERATE)
tooltip_ffsubsync_option_gss = ToolTip(ffsubsync_option_gss, TOOLTIP_GSS)
tooltip_ffsubsync_option_vad = ToolTip(ffsubsync_option_vad, TOOLTIP_VAD)
tooltip_save_to_desktop = ToolTip(check_save_to_desktop_auto, TOOLTIP_SAVE_TO_DESKTOP)
tooltip_replace_original = ToolTip(check_replace_original_auto, TOOLTIP_REPLACE_ORIGINAL)
label_video.grid(row=0, column=0, padx=10, pady=(10,5), sticky="nsew", columnspan=2)
label_subtitle.grid(row=1, column=0, padx=10, pady=0, sticky="nsew", columnspan=2)
ffsubsync_option_framerate.grid(row=2, column=0, columnspan=5, padx=10, pady=(5,0), sticky="w")
ffsubsync_option_gss.grid(row=3, column=0, columnspan=5, padx=10, pady=0, sticky="w")
ffsubsync_option_vad.grid(row=4, column=0, columnspan=5, padx=10, pady=0, sticky="w")
button_start_automatic_sync.grid(row=5, column=0, padx=10, pady=10, sticky="ew", columnspan=2)
check_save_to_desktop_auto.grid(row=6, column=0, columnspan=5, padx=10, pady=5, sticky="w")
check_replace_original_auto.grid(row=6, column=1, columnspan=5, padx=10, pady=5, sticky="w")
label_subtitle.drop_target_register(DND_FILES)
label_subtitle.dnd_bind('<<Drop>>', on_subtitle_drop)
label_subtitle.bind("<Button-1>", browse_subtitle)
label_subtitle.bind("<Enter>", on_enter)
label_subtitle.bind("<Leave>", on_leave)
label_video.drop_target_register(DND_FILES)
label_video.dnd_bind('<<Drop>>', on_video_drop)
label_video.bind("<Button-1>", browse_video)
label_video.bind("<Enter>", on_enter)
label_video.bind("<Leave>", on_leave)
label_message_auto.bind("<Configure>", update_wraplengt)
label_video.bind("<Configure>", update_wraplengt)
label_subtitle.bind("<Configure>", update_wraplengt)
automatic_tab.rowconfigure(0, weight=1)
automatic_tab.rowconfigure(1, weight=1)
# ---------------- Automatic Tab ---------------- #

# ---------------- Manual Tab ---------------- #
label_drop_box = tk.Label(manual_tab, text="Drag and drop subtitle file here or click to browse.", bg="lightgray", relief="ridge", width=40, height=17, cursor="hand2")
label_separator = ttk.Separator(manual_tab, orient='horizontal')
label_message_manual = tk.Label(manual_tab, text="", fg="black", anchor="center")
label_milliseconds = tk.Label(manual_tab, text="Shift subtitle by (milliseconds):", anchor="w")
entry_milliseconds = tk.Entry(manual_tab, cursor="xterm", width=15, justify="center", borderwidth=2, validate='key')
entry_milliseconds.config(validatecommand=(root.register(validate_input), '%P'))
button_minus = tk.Button(
    manual_tab, text="-",
    command=decrease_milliseconds,
    padx=10,
    pady=5,
    fg="white",
    bg="gray50",
    activebackground="gray40",
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
    bg="gray50",
    activebackground="gray40",
    activeforeground="white",
    relief=tk.RAISED,
    borderwidth=2,
    cursor="hand2"
)
button_sync = tk.Button(
    manual_tab,
    text="Shift Subtitle",
    command=sync_subtitle,
    padx=10,
    pady=10,
    fg="white",
    bg="#00a31e",
    activebackground="#007d17",
    activeforeground="white",
    relief=tk.RAISED,
    borderwidth=2,
    cursor="hand2"
)
save_to_desktop_var = tk.BooleanVar()
check_save_to_desktop = tk.Checkbutton(manual_tab, text="Save to Desktop", variable=save_to_desktop_var, command=lambda: checkbox_selected(save_to_desktop_var))
replace_original_var = tk.BooleanVar()
check_replace_original = tk.Checkbutton(manual_tab, text="Replace original subtitle", variable=replace_original_var, command=lambda: checkbox_selected(replace_original_var))
label_drop_box.grid(row=0, column=0, padx=10, pady=(10,5), sticky="nsew", columnspan=6)
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