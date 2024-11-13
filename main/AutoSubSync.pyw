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
version = "v2.5"
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
            subtitle_input.config(text=subtitle_file, font=("Calibri", 10, "bold"))
            subtitle_input.tooltip_text = subtitle_file
            subtitle_input.config(bg="lightgreen")
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
# Convert subtitles to SRT End

def start_batch_sync():
    global process_list, output_subtitle_files
    process_list = []
    output_subtitle_files = []
    tree_items = treeview.get_children()
    if not tree_items:
        log_message("No files to sync. Please add files to the batch list.", "error", tab='auto')
        return

    # Step 1: Count valid pairs
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
        log_message("No valid file pairs to sync.", "error", tab='auto')
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
                    log_message(f"Error occurred during process termination: {e}", "error", tab='auto')
        log_message("Batch synchronization cancelled.", "error", tab='auto')
        restore_window()

    def restore_window():
        batch_input.grid()
        button_start_automatic_sync.grid()
        batch_mode_button.grid()
        check_save_to_desktop_auto.grid()
        check_replace_original_auto.grid()
        ffsubsync_option_gss.grid()
        ffsubsync_option_vad.grid()
        ffsubsync_option_framerate.grid()
        log_window.grid_remove()
        progress_bar.grid_remove()
        button_generate_again.grid_remove()
        button_cancel_batch_sync.grid_remove()
        tree_frame.grid()  # Show tree_frame
        automatic_tab.columnconfigure(0, weight=0)
        root.update_idletasks()

    def generate_again():
        # Clear all tree items
        treeview.delete(*treeview.get_children())
        batch_input.grid(row=0, column=0, padx=10, pady=(10,0), sticky="nsew", columnspan=2, rowspan=2)
        tree_frame.grid_remove()
        button_start_automatic_sync.grid()
        batch_mode_button.grid()
        log_window.grid_remove()
        progress_bar.grid_remove()
        button_generate_again.grid_remove()
        check_save_to_desktop_auto.grid()
        check_replace_original_auto.grid()
        ffsubsync_option_gss.grid()
        ffsubsync_option_vad.grid()
        ffsubsync_option_framerate.grid()
        label_message_auto.grid_remove()
        automatic_tab.columnconfigure(0, weight=0)
        root.update_idletasks()

    def run_batch_process():
        nonlocal completed_items
        for parent in tree_items:
            if cancel_flag:
                restore_window()
                return
            parent_values = treeview.item(parent, "values")
            if not parent_values:
                log_window.insert(tk.END, "Invalid parent item with no values.\n")
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
                    log_window.insert(tk.END, "\nSkipping entry with no video and no subtitle.\n")
                    continue
                elif not subtitle_file:
                    log_window.insert(tk.END, f"\nSkipping '{os.path.basename(video_file)}': No subtitle file.\n")
                    continue
                elif not video_file:
                    log_window.insert(tk.END, f"\nSkipping '{os.path.basename(subtitle_file)}': No video/reference file.\n")
                    continue
                elif not values:
                    log_window.insert(tk.END, "\nUnpaired item skipped.\n")
                    continue
                # Convert files if necessary
                def convert_to_srt(subtitle_file):
                    file_extension = os.path.splitext(subtitle_file)[-1].lower()
                    base_name = os.path.basename(os.path.splitext(subtitle_file)[0])
                    srt_file = os.path.join(os.path.dirname(subtitle_file), 'converted_' + base_name + '.srt')
                    log_window.insert(tk.END, f"Preparing {base_name}{file_extension} for automatic sync...\n")
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
                            log_window.insert(tk.END, f"Converting {file_extension.upper()} to SRT...\n")
                            converter(subtitle_file, srt_file)
                        except Exception as e:
                            log_window.insert(tk.END, f"Error converting subtitle: {e}\n")
                            return None
                        log_window.insert(tk.END, f"Subtitle successfully converted and saved to: {srt_file}.\n")
                        return srt_file
                    else:
                        log_window.insert(tk.END, f"Error: Conversion for {file_extension} is not supported.\n")
                        return None
                def convert_files():
                    nonlocal subtitle_file, video_file
                    # Convert subtitle file if necessary
                    if subtitle_file.lower().endswith(('.vtt', '.sbv', '.sub', '.dfxp', '.ttml', '.itt', '.stl')):
                        subtitle_file_converted = convert_to_srt(subtitle_file)
                        if subtitle_file_converted:
                            subtitle_file = subtitle_file_converted
                        else:
                            log_window.insert(tk.END, f"Failed to convert subtitle file: {subtitle_file}\n")
                            return False
                    # Convert video file if necessary
                    if video_file.lower().endswith(('.vtt', '.sbv', '.sub', '.dfxp', '.ttml', '.itt', '.stl')):
                        video_file_converted = convert_to_srt(video_file)
                        if video_file_converted:
                            video_file = video_file_converted
                        else:
                            log_window.insert(tk.END, f"Failed to convert video/reference file: {video_file}\n")
                            return False
                    return True
                if not convert_files():
                    continue
                # Prepare output file path
                if save_to_desktop_var_auto.get():
                    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                    output_subtitle_file = os.path.join(desktop_path, f"autosync_{os.path.basename(subtitle_file)}")
                elif replace_original_var_auto.get():
                    output_subtitle_file = subtitle_file
                else:
                    output_subtitle_file = os.path.join(os.path.dirname(subtitle_file), f"autosync_{os.path.basename(subtitle_file)}")
                if os.path.exists(output_subtitle_file) and not replace_original_var_auto.get():
                    replace_confirmation = tk.messagebox.askyesno("File Exists",
                                                                 f"A file with the name '{os.path.basename(output_subtitle_file)}' already exists. Do you want to replace it?")
                    if not replace_confirmation:
                        log_window.insert(tk.END, f"Skipping {os.path.basename(subtitle_file)}: Output file exists.\n")
                        continue
                if not output_subtitle_file.lower().endswith(('.srt', '.ass', '.ssa')):
                    output_subtitle_file = os.path.splitext(output_subtitle_file)[0] + '.srt'
                cmd = f'ffs "{video_file}" -i "{subtitle_file}" -o "{output_subtitle_file}"'
                if not video_file.lower().endswith(('.srt', '.vtt', '.sbv', '.sub', '.ass', '.ssa', '.dfxp', '.ttml', '.itt', '.stl')):
                    if ffsubsync_option_framerate_var.get():
                        cmd += " --no-fix-framerate"
                    if ffsubsync_option_gss_var.get():
                        cmd += " --gss"
                    if ffsubsync_option_vad_var.get():
                        cmd += " --vad=auditok"
                log_window.insert(tk.END, f"\n[{completed_items + 1}/{total_items}] Syncing {os.path.basename(subtitle_file)} with {os.path.basename(video_file)}...\n")
                try:
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
                    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
                    process_list.append(process)
                except Exception as e:
                    log_window.insert(tk.END, f"Failed to start process: {e}\n")
                    log_message(f"Failed to start process: {e}", "error", tab='auto')
                    continue

                for output in process.stdout:
                    if cancel_flag:
                        process.kill()
                        restore_window()
                        return
                    match_percentage = re.search(r'\b(\d+(\.\d+)?)%\|', output)
                    if match_percentage:
                        percentage = float(match_percentage.group(1))
                        adjusted_value = min(97, max(1, percentage))
                        progress_increment = (adjusted_value / 100) * (100 / total_items)
                        progress_bar["value"] = (completed_items / total_items) * 100 + progress_increment
                    if "%" in output:
                        log_window.delete("end-2l", "end-1l")
                        log_window.insert(tk.END, output)
                    else:
                        log_window.insert(tk.END, output)
                    log_window.see(tk.END)
                process.wait()
                if cancel_flag:
                    process_list.remove(process)
                    restore_window()
                    return
                if process.returncode == 0:
                    log_window.insert(tk.END, f"Success! Synchronized subtitle saved to: {output_subtitle_file}\n\n")
                else:
                    log_window.insert(tk.END, f"Error occurred during synchronization of {os.path.basename(subtitle_file)}\n")
                    log_message(f"Error occurred during synchronization of {os.path.basename(subtitle_file)}", "error", tab='auto')
                process_list.remove(process)
                completed_items +=1  # Increment only for valid processed pair
                progress_bar["value"] = (completed_items / total_items) * 100
                root.update_idletasks()
        log_window.see(tk.END)
        log_window.insert(tk.END, "\nBatch syncing completed.\n")
        log_message("Batch syncing completed.", "success", tab='auto')
        button_cancel_batch_sync.grid_remove()
        log_window.grid(pady=(10, 10), rowspan=2)
        button_generate_again.grid()  # Show the Generate Again button
        progress_bar.grid_remove()

    try:
        batch_input.grid_remove()
        tree_frame.grid_remove()
        button_start_automatic_sync.grid_remove()
        batch_mode_button.grid_remove()
        label_message_auto.grid_remove()
        check_save_to_desktop_auto.grid_remove()
        check_replace_original_auto.grid_remove()
        ffsubsync_option_gss.grid_remove()
        ffsubsync_option_vad.grid_remove()
        ffsubsync_option_framerate.grid_remove()
        button_cancel_batch_sync = tk.Button(
            automatic_tab,
            text="Cancel",
            command=cancel_batch_sync,
            padx=10,
            pady=10,
            fg="white",
            bg="#707070",
            activebackground="#616161",
            activeforeground="white",
            relief=tk.RAISED,
            borderwidth=2,
            cursor="hand2"
        )
        button_cancel_batch_sync.grid(row=6, column=0, padx=10, pady=(0,10), sticky="ew", columnspan=2)
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
        button_generate_again.grid(row=11, column=0, padx=10, pady=(0,10), sticky="ew", columnspan=2)
        button_generate_again.grid_remove()
        log_window = tk.Text(automatic_tab, wrap="word")
        log_window.config(font=("Arial", 7))
        log_window.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew", columnspan=2)
        progress_bar = ttk.Progressbar(automatic_tab, orient="horizontal", length=200, mode="determinate")
        progress_bar.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="ew", columnspan=2)
        root.update_idletasks()
        threading.Thread(target=run_batch_process).start()
    except Exception as e:
        log_message(f"Error occurred: {e}", "error", tab='auto')
    automatic_tab.rowconfigure(0, weight=1)
    automatic_tab.rowconfigure(1, weight=0)
    automatic_tab.columnconfigure(0, weight=1)

def toggle_batch_mode():
    if treeview.get_children():
        log_message("", "info", tab='auto')
        if batch_mode_var.get():
            batch_mode_var.set(False)
            batch_mode_button.config(text="Batch Mode", bg="gray50", activebackground="gray40")
            button_start_automatic_sync.config(text="Start Automatic Sync", bg="dodger blue", activebackground="DodgerBlue3", command=start_automatic_sync)
            subtitle_input.grid(row=1, column=0, padx=10, pady=0, sticky="nsew", columnspan=2)
            video_input.grid(row=0, column=0, padx=10, pady=(10,5), sticky="nsew", columnspan=2)
            batch_input.grid_remove()
            tree_frame.grid_remove()
            automatic_tab.rowconfigure(1, weight=1)
            root.update_idletasks()
        else:
            batch_mode_var.set(True)
            batch_mode_button.config(text="Normal Mode", bg="gray50", activebackground="gray40")
            button_start_automatic_sync.config(text="Start Batch Sync", bg="light slate blue", activebackground="SlateBlue3", command=start_batch_sync)
            subtitle_input.grid_remove()
            video_input.grid_remove()
            batch_input.grid(row=0, column=0, padx=10, pady=(10,0), sticky="nsew", columnspan=2, rowspan=2)
            tree_frame.grid(row=0, column=0, padx=5, pady=(5,0), sticky="nsew", columnspan=2, rowspan=2)
    else:
        log_message("", "info", tab='auto')
        if batch_mode_var.get():
            batch_mode_var.set(False)
            batch_mode_button.config(text="Batch Mode", bg="gray50", activebackground="gray40")
            button_start_automatic_sync.config(text="Start Automatic Sync", bg="dodger blue", activebackground="DodgerBlue3", command=start_automatic_sync)
            subtitle_input.grid(row=1, column=0, padx=10, pady=0, sticky="nsew", columnspan=2)
            video_input.grid(row=0, column=0, padx=10, pady=(10,5), sticky="nsew", columnspan=2)
            batch_input.grid_remove()
            tree_frame.grid_remove()
            automatic_tab.rowconfigure(1, weight=1)
            root.update_idletasks()
        else:
            batch_mode_var.set(True)
            batch_mode_button.config(text="Normal Mode", bg="gray50", activebackground="gray40")
            button_start_automatic_sync.config(text="Start Batch Sync", bg="light slate blue", activebackground="SlateBlue3", command=start_batch_sync)
            subtitle_input.grid_remove()
            video_input.grid_remove()
            batch_input.grid(row=0, column=0, padx=10, pady=(10,0), sticky="nsew", columnspan=2, rowspan=2)
            tree_frame.grid_remove()

def browse_batch(event=None):
    paths = filedialog.askopenfilenames(filetypes=[("Video or subtitle", "*.srt;*.vtt;*.sbv;*.sub;*.ass;*.ssa;*.dfxp;*.ttml;*.itt;*.stl;*.mp4;*.mkv;*.avi;*.webm;*.flv;*.mov;*.wmv;*.mpg;*.mpeg;*.m4v;*.3gp;*.h264;*.h265;*.hevc")])
    if paths:
        process_files(paths)

def on_batch_drop(event):
    filepaths = automatic_tab.tk.splitlist(event.data)
    process_files(filepaths)

def process_files(filepaths):
    subtitle_files = []
    video_files = []
    # Separate the files into video and subtitle lists
    for filepath in filepaths:
        if os.path.isdir(filepath):
            for root, _, files in os.walk(filepath):
                for file in files:
                    full_path = os.path.join(root, file)
                    if full_path.lower().endswith(('.srt', '.vtt', '.sbv', '.sub', '.ass', '.ssa', '.dfxp', '.ttml', '.itt', '.stl')):
                        subtitle_files.append(full_path)
                    elif full_path.lower().endswith(('.mp4', '.mkv', '.avi', '.webm', '.flv', '.mov', '.wmv', '.mpg', '.mpeg', '.m4v', '.3gp', '.h264', '.h265', '.hevc')):
                        video_files.append(full_path)
        else:
            if filepath.lower().endswith(('.srt', '.vtt', '.sbv', '.sub', '.ass', '.ssa', '.dfxp', '.ttml', '.itt', '.stl')):
                subtitle_files.append(filepath)
            elif filepath.lower().endswith(('.mp4', '.mkv', '.avi', '.webm', '.flv', '.mov', '.wmv', '.mpg', '.mpeg', '.m4v', '.3gp', '.h264', '.h265', '.hevc')):
                video_files.append(filepath)
    # Check if there are any video or subtitle files
    if not subtitle_files and not video_files:
        log_message("Please drop valid subtitle and video files.", "error", tab='auto')
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
        video_name = os.path.basename(video_file) if video_file else "[no video]"
        subtitle_name = "[no subtitle]"
        subtitle_file = None
        if video_file:
            video_dir = os.path.dirname(video_file)
            # First, check if there is a subtitle in the same directory with the same name as the video
            base_name = os.path.splitext(os.path.basename(video_file))[0]
            for sub_file in subtitle_files[:]:
                if sub_file and os.path.dirname(sub_file) == video_dir and os.path.splitext(os.path.basename(sub_file))[0] == base_name:
                    subtitle_file = sub_file
                    subtitle_name = os.path.basename(subtitle_file)
                    subtitle_files.remove(sub_file)  # Remove paired subtitle from the list
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
                            subtitle_files.remove(sub_file)  # Remove paired subtitle from the list
                            break
                    if subtitle_file:
                        break
            if subtitle_file:
                # Normalize paths for comparison
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
    # Insert incomplete pairs first
    for video_name, subtitle_name, video_file, subtitle_file in incomplete_pairs:
        parent_id = treeview.insert("", "end", text=video_name, values=(rf"{video_file}" if video_file else "",), open=True)
        treeview.insert(parent_id, "end", text=subtitle_name, values=(subtitle_file if subtitle_file else ""))
        treeview.item(parent_id, tags=("incomplete",))
        if not video_file and not subtitle_file:
            treeview.delete(parent_id)  # Remove the node if no video and no subtitle
    # Insert complete pairs
    for video_name, subtitle_name, video_file, subtitle_file in complete_pairs:
        parent_id = treeview.insert("", "end", text=video_name, values=(video_file,), open=True)
        treeview.insert(parent_id, "end", text=subtitle_name, values=(subtitle_file,))
        treeview.item(parent_id, tags=("paired",))
    # Handle remaining unpaired subtitles
    unpaired_subtitles = list(filter(None, subtitle_files))
    if unpaired_subtitles:
        unpaired_count = len(unpaired_subtitles)
        user_choice = messagebox.askyesno("Unpaired Subtitles",
                                        f"There are {unpaired_count} unpaired subtitle(s). Do you want to add them as subtitles with [no video] tag?")
        for sub_file in unpaired_subtitles:
            subtitle_name = os.path.basename(sub_file)
            if user_choice:
                parent_id = treeview.insert("", "end", text="[no video]", values=("",), open=True)
                treeview.insert(parent_id, "end", text=subtitle_name, values=(sub_file,))
                treeview.item(parent_id, tags=("incomplete",))
                files_not_paired += 1
            else:
                parent_id = treeview.insert("", "end", text=subtitle_name, values=(sub_file,), open=True)
                treeview.insert(parent_id, "end", text="[no subtitle]", values=("",))
                treeview.item(parent_id, tags=("incomplete",))
                files_not_paired += 1
    batch_input.grid_remove()
    tree_frame.grid(row=0, column=0, padx=5, pady=(5,0), sticky="nsew", columnspan=2, rowspan=2)
    messages = []
    if pairs_added > 0:
        messages.append(f"Added {pairs_added} pair{'s' if pairs_added != 1 else ''}")
    if files_not_paired > 0:
        if pairs_added < 1 or (duplicates > 0 and pairs_added < 1):
            messages.append(f"Added {files_not_paired} unpaired file{'s' if files_not_paired != 1 else ''}")
        else:
            messages.append(f"{files_not_paired} unpaired file{'s' if files_not_paired != 1 else ''}")
    if duplicates > 0:
        messages.append(f"{duplicates} duplicate pair{'s' if duplicates != 1 else ''} skipped")
    if messages:
        log_message(" and ".join(messages) + ".", "info", tab='auto')

def add_pair():
    video_file = filedialog.askopenfilename(filetypes=[("Video or subtitle", "*.srt;*.vtt;*.sbv;*.sub;*.ass;*.ssa;*.dfxp;*.ttml;*.itt;*.stl;*.mp4;*.mkv;*.avi;*.webm;*.flv;*.mov;*.wmv;*.mpg;*.mpeg;*.m4v;*.3gp;*.h264;*.h265;*.hevc")])
    if video_file:
        subtitle_file = filedialog.askopenfilename(filetypes=[("Subtitle files", "*.srt;*.vtt;*.sbv;*.sub;*.ass;*.ssa;*.dfxp;*.ttml;*.itt;*.stl")])
        if subtitle_file:
            video_name = os.path.basename(video_file)
            subtitle_name = os.path.basename(subtitle_file)
            pair = (video_file.lower(), subtitle_file.lower())
            # Check for duplicates based on full file paths
            for parent in treeview.get_children():
                existing_video = treeview.item(parent, "values")
                if existing_video and existing_video[0].lower() == pair[0]:
                    subtitles = treeview.get_children(parent)
                    for sub in subtitles:
                        existing_sub = treeview.item(sub, "values")
                        if existing_sub and existing_sub[0].lower() == pair[1]:
                            log_message("This pair already exists.", "error", tab='auto')
                            return
            parent_id = treeview.insert("", "end", text=video_name, values=(video_file,), open=True)
            treeview.insert(parent_id, "end", text=subtitle_name, values=(subtitle_file,))
            treeview.item(parent_id, tags=("paired",))
            log_message("Added 1 pair.", "info", tab='auto')
        else:
            log_message("Please select a subtitle file.", "error", tab='auto')
    else:
        log_message("Please select a video file.", "error", tab='auto')

def change_selected_item():
    selected_item = treeview.selection()
    if selected_item:
        parent_id = treeview.parent(selected_item)
        is_parent = not parent_id
        if is_parent:
            filetypes = [("Video or subtitle", "*.srt;*.vtt;*.sbv;*.sub;*.ass;*.ssa;*.dfxp;*.ttml;*.itt;*.stl;*.mp4;*.mkv;*.avi;*.webm;*.flv;*.mov;*.wmv;*.mpg;*.mpeg;*.m4v;*.3gp;*.h264;*.h265;*.hevc")]
        else:
            filetypes = [("Subtitle files", "*.srt;*.vtt;*.sbv;*.sub;*.ass;*.ssa;*.dfxp;*.ttml;*.itt;*.stl")]
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
                        log_message("Cannot use the same file for both inputs.", "error", tab='auto')
                        return
            else:
                if new_file.lower() == parent_file.lower():
                    log_message("Cannot use the same file for both inputs.", "error", tab='auto')
                    return
            # Gather all existing pairs, excluding the current selection if it's a parent
            existing_pairs = set()
            for item in treeview.get_children():
                if is_parent and item == selected_item:
                    continue  # Skip the selected parent
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
                            log_message("This pair already exists. Please select a different file.", "error", tab='auto')
                            return
            else:
                new_child_file = new_file.lower()
                new_parent_file = parent_file.lower() if parent_file else ""
                if (new_parent_file, new_child_file) in existing_pairs:
                    log_message("This pair already exists. Please select a different file.", "error", tab='auto')
                    return
            # Update the item's name and value
            treeview.item(selected_item, text=new_name, values=(new_file,))
            # Update the tags of the parent item
            if parent_id:
                parent_text = treeview.item(parent_id, "text")
                if parent_text == "[no video]":
                    treeview.item(parent_id, tags=("incomplete",))
                else:
                    treeview.item(parent_id, tags=("paired",))
            else:
                children = treeview.get_children(selected_item)
                valid_children = [child for child in children if treeview.item(child, "text") != "[no subtitle]"]
                if not children or not valid_children:
                    treeview.item(selected_item, tags=("incomplete",))
                else:
                    treeview.item(selected_item, tags=("paired",))
            # Log appropriate messages
            if item_type.lower() == "[no subtitle]":
                log_message("Subtitle added.", "info", tab='auto')
            elif item_type.lower() == "[no video]":
                log_message("Video/reference subtitle added.", "info", tab='auto')
            else:
                log_message("File changed.", "info", tab='auto')
        else:
            log_message("Please select an item to change.", "error", tab='auto')

def remove_selected_item():
    selected_items = treeview.selection()
    if selected_items:
        for selected_item in selected_items:
            if treeview.exists(selected_item):
                parent_id = treeview.parent(selected_item)
                if parent_id:
                    treeview.delete(selected_item)
                    if not treeview.get_children(parent_id):
                        treeview.insert(parent_id, "end", text="[no subtitle]", values=("",))
                        treeview.item(parent_id, tags=("incomplete",))
                else:
                    treeview.delete(selected_item)
    else:
        log_message("Please select an item to remove.", "error", tab='auto')

# Define batch input label
batch_input = tk.Label(automatic_tab, text="Drag and drop multiple files/folders here or click to browse.\n\n(Videos and subtitles that has the same filenames will be\n paired automatically. You need to pair others manually.)", bg="lightgray", relief="ridge", width=40, height=5, cursor="hand2")
batch_input_text = tk.Label(automatic_tab, text="Batch Processing Mode", fg="black", relief="ridge", padx=5, borderwidth=1)
batch_input_text.place(in_=batch_input, relx=0, rely=0, anchor="nw")
batch_input.bind("<Button-1>", browse_batch)
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
context_menu.add_command(label="Remove", command=remove_selected_item)
context_menu.add_command(label="Change", command=change_selected_item)
context_menu.add_separator()  # Add a separator
context_menu.add_command(label="Add Pair", command=add_pair)
context_menu.add_command(label="Clear All", command=lambda: treeview.delete(*treeview.get_children()))
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
            context_menu.add_command(label="Show path", command=show_path)
            context_menu.add_separator()
    context_menu.add_command(label="Remove", command=remove_selected_item)
    context_menu.add_command(label="Change", command=change_selected_item)
    context_menu.add_separator()  # Add a separator
    context_menu.add_command(label="Add Pair", command=add_pair)
    context_menu.add_command(label="Clear All", command=lambda: treeview.delete(*treeview.get_children()))
    context_menu.post(event.x_root, event.y_root)
# Bind the right-click event to the Treeview to show the context menu
treeview.bind("<Button-3>", show_context_menu)
# Bind the key events to the treeview
treeview.bind("<Control-a>", select_all)
treeview.bind("<Delete>", delete_selected)
treeview.bind("<Double-1>", on_double_click)
# Create buttons for adding, changing, and removing items
button_change_item = tk.Button(
    tree_frame,
    text="Change",
    command=change_selected_item,
    padx=10,
    pady=5,
    fg="black",
    bg="light gray",
    activebackground="gray",
    activeforeground="black",
    relief=tk.RAISED,
    borderwidth=2,
    cursor="hand2"
)
button_remove_item = tk.Button(
    tree_frame,
    text="Remove",
    command=remove_selected_item,
    padx=10,
    pady=5,
    fg="black",
    bg="light gray",
    activebackground="gray",
    activeforeground="black",
    relief=tk.RAISED,
    borderwidth=2,
    cursor="hand2"
)
# Define styles
style = ttk.Style()
style.configure("Treeview", rowheight=25)
style.map("Treeview", background=[('selected', 'steel blue')])
# Function to select a folder
def select_folder():
    folder_path = filedialog.askdirectory()
    if folder_path:
        process_files([folder_path])
# Replace the "Add Pair" button with a Menubutton
button_options = tk.Menubutton(
    tree_frame,
    text="Add files",
    padx=10,
    pady=7.5,
    fg="black",
    bg="light gray",
    activebackground="light gray",
    activeforeground="black",
    relief=tk.RAISED,
    borderwidth=2,
    cursor="hand2"
)
options_menu = tk.Menu(button_options, tearoff=0)
button_options.config(menu=options_menu)
options_menu.add_command(label="Add Pair", command=add_pair)
options_menu.add_command(label="Select a Folder", command=select_folder)
options_menu.add_command(label="Select Multiple Files", command=browse_batch)
# Update the grid layout
button_options.grid(row=0, column=0, padx=(5,2.5), pady=5, sticky="ew")
button_change_item.grid(row=0, column=1, padx=(2.5,2.5), pady=5, sticky="ew")
button_remove_item.grid(row=0, column=2, padx=(2.5,5), pady=5, sticky="ew")
button_change_item.grid(row=0, column=1, padx=(2.5,2.5), pady=5, sticky="ew")
button_remove_item.grid(row=0, column=2, padx=(2.5,5), pady=5, sticky="ew")
treeview.grid(row=1, column=0, columnspan=3, padx=5, pady=(5,0), sticky="nsew")
tree_frame.grid_remove()
batch_input.grid_remove()
# Start batch mode end

# Start automatic sync begin
def browse_subtitle(event=None):
    subtitle_file_auto = filedialog.askopenfilename(filetypes=[("Subtitle files", "*.srt;*.vtt;*.sbv;*.sub;*.ass;*.ssa;*.dfxp;*.ttml;*.itt;*.stl")])
    filetypes=[("Subtitle files", "*.srt;*.vtt;*.sbv;*.sub;*.ass;*.ssa;*.dfxp;*.ttml;*.itt;*.stl")]
    if subtitle_file_auto:
        subtitle_input.config(text=subtitle_file_auto, font=("Calibri", 10, "bold"))
        subtitle_input.tooltip_text = subtitle_file_auto
        subtitle_input.config(bg="lightgreen")
        log_message("", "info", tab='auto')
    else:
        if subtitle_file_auto != '':
            log_message("Please select a subtitle", "error", tab='auto')
            subtitle_input.config(bg="lightgray")

def browse_video(event=None):
    video_file = filedialog.askopenfilename(filetypes=[("Video or subtitle", "*.srt;*.vtt;*.sbv;*.sub;*.ass;*.ssa;*.dfxp;*.ttml;*.itt;*.stl;*.mp4;*.mkv;*.avi;*.webm;*.flv;*.mov;*.wmv;*.mpg;*.mpeg;*.m4v;*.3gp;*.h264;*.h265;*.hevc")])
    if video_file:
        video_input.config(text=video_file, font=("Calibri", 10, "bold"))
        video_input.tooltip_text = video_file
        video_input.config(bg="lightgreen")
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
            video_input.config(bg="lightgray")

def on_video_drop(event):
    files = event.widget.tk.splitlist(event.data)
    if len(files) != 1:
        log_message("Please drop single video or subtitle file.", "error", tab='auto')
        return
    filepath = files[0]
    if filepath.lower().endswith(('.srt', '.vtt', '.sbv', '.sub', '.ass', '.ssa', '.dfxp', '.ttml', '.itt', '.stl', '.mp4', '.mkv', '.avi', '.webm', '.flv', '.mov', '.wmv', '.mpg', '.mpeg', '.m4v', '.3gp', '.h264', '.h265', '.hevc')):
        video_input.config(text=filepath, font=("Calibri", 10, "bold"))
        video_input.tooltip_text = filepath
        video_input.config(bg="lightgreen")
        log_message("", "info", tab='auto')
        if filepath.lower().endswith(('.srt', '.vtt', '.sbv', '.sub', '.ass', '.ssa', '.dfxp', '.ttml', '.itt', '.stl')):
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
    files = event.widget.tk.splitlist(event.data)
    if len(files) != 1:
        log_message("Please drop single subtitle file.", "error", tab='auto')
        return
    filepath = files[0]
    if filepath.lower().endswith(('.srt', '.vtt', '.sbv', '.sub', '.ass', '.ssa', '.dfxp', '.ttml', '.itt', '.stl')):
        subtitle_input.config(text=filepath, font=("Calibri", 10, "bold"))
        subtitle_input.tooltip_text = filepath
        subtitle_input.config(bg="lightgreen")
        log_message("", "info", tab='auto')
    else:
        log_message("Please drop a subtitle file.", "error", tab='auto')

process = None
def start_automatic_sync():
    global process, subtitle_file, video_file, output_subtitle_file
    subtitle_file = getattr(subtitle_input, 'tooltip_text', None)
    video_file = getattr(video_input, 'tooltip_text', None)
    if not subtitle_file and not video_file:
        log_message("Please select both video/reference subtitle and subtitle file.", "error", tab='auto')
        return
    if subtitle_file == video_file:
        log_message("Please select different subtitle files.", "error", tab='auto')
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
        subtitle_input.grid()
        video_input.grid()
        check_save_to_desktop_auto.grid()
        check_replace_original_auto.grid()
        button_start_automatic_sync.grid()
        batch_mode_button.grid()
        ffsubsync_option_gss.grid()
        ffsubsync_option_vad.grid()
        ffsubsync_option_framerate.grid()
        log_window.grid_remove()
        progress_bar.grid_remove()
        button_generate_again.grid_remove()
        button_cancel_automatic_sync.grid_remove()
        automatic_tab.columnconfigure(0, weight=0)
        root.update_idletasks()

    def generate_again():
        subtitle_input.config(text="Drag and drop the unsynchronized subtitle file here or click to browse.", bg="lightgray", font=("Segoe UI", 9, "normal"))
        del subtitle_input.tooltip_text
        video_input.config(text="Drag and drop video or reference subtitle file here or click to browse.", bg="lightgray", font=("Segoe UI", 9, "normal"))
        del video_input.tooltip_text
        subtitle_input.grid()
        video_input.grid()
        check_save_to_desktop_auto.grid()
        check_replace_original_auto.grid()
        button_start_automatic_sync.grid()
        batch_mode_button.grid()
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
        automatic_tab.columnconfigure(0, weight=0)
        root.update_idletasks()

    def convert_to_srt(subtitle_file):
        file_extension = os.path.splitext(subtitle_file)[-1].lower()
        base_name = os.path.basename(os.path.splitext(subtitle_file)[0])
        srt_file = os.path.join(os.path.dirname(subtitle_file), 'converted_' + base_name + '.srt')
        log_window.insert(tk.END, f"Preparing " + base_name + file_extension + " for automatic sync...\n")
        if file_extension == '.ttml':
            log_window.insert(tk.END, "Converting TTML/DFXP/ITT to SRT...\n")
            try:
                convert_ttml_or_dfxp_to_srt(subtitle_file, srt_file)
            except Exception as e:
                log_window.insert(tk.END, f"Error converting subtitle: {e}\n")
        elif file_extension == '.dfxp':
            log_window.insert(tk.END, "Converting TTML/DFXP/ITT to SRT...\n")
            try:
                convert_ttml_or_dfxp_to_srt(subtitle_file, srt_file)
            except Exception as e:
                log_window.insert(tk.END, f"Error converting subtitle: {e}\n")
        elif file_extension == '.itt':
            log_window.insert(tk.END, "Converting TTML/DFXP/ITT to SRT...\n")
            try:
                convert_ttml_or_dfxp_to_srt(subtitle_file, srt_file)
            except Exception as e:
                log_window.insert(tk.END, f"Error converting subtitle: {e}\n")
        elif file_extension == '.vtt':
            log_window.insert(tk.END, f"Converting VTT to SRT...\n")
            try:
                convert_vtt_to_srt(subtitle_file, srt_file)
            except Exception as e:
                log_window.insert(tk.END, f"Error converting subtitle: {e}\n")
        elif file_extension == '.sbv':
            log_window.insert(tk.END, f"Converting SBV to SRT...\n")
            try:
                convert_sbv_to_srt(subtitle_file, srt_file)
            except Exception as e:
                log_window.insert(tk.END, f"Error converting subtitle: {e}\n")
        elif file_extension == '.sub':
            log_window.insert(tk.END, f"Converting SUB to SRT...\n")
            try:
                convert_sub_to_srt(subtitle_file, srt_file)
            except Exception as e:
                log_window.insert(tk.END, f"Error converting subtitle: {e}\n")
        elif file_extension == '.ass':
            log_window.insert(tk.END, f"Converting ASS/SSA to SRT...\n")
            try:
                convert_ass_to_srt(subtitle_file, srt_file)
            except Exception as e:
                log_window.insert(tk.END, f"Error converting subtitle: {e}\n")
        elif file_extension == '.ssa':
            log_window.insert(tk.END, f"Converting ASS/SSA to SRT...\n")
            try:
                convert_ass_to_srt(subtitle_file, srt_file)
            except Exception as e:
                log_window.insert(tk.END, f"Error converting subtitle: {e}\n")
        elif file_extension == '.stl':
            log_window.insert(tk.END, f"Converting STL to SRT...\n")
            try:
                convert_stl_to_srt(subtitle_file, srt_file)
            except Exception as e:
                log_window.insert(tk.END, f"Error converting subtitle: {e}\n")
        else:
            log_window.insert(tk.END, f"Error: Conversion for {file_extension} is not supported.\n")
            return None
        if srt_file:
            log_window.insert(tk.END, f"Subtitle successfully converted and saved to: {srt_file}.\n")
            return srt_file
        
    def run_subprocess():
        global process, progress_line_number, subtitle_file, video_file, cmd, output_subtitle_file
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
            # if the video_file is a subtitle, don't add parameters
            if not video_file.lower().endswith(('.srt', '.vtt', '.sbv', '.sub', '.ass', '.ssa', '.dfxp', '.ttml', '.itt', '.stl')):
                if ffsubsync_option_framerate_var.get():
                    cmd += " --no-fix-framerate"
                if ffsubsync_option_gss_var.get():
                    cmd += (" --gss")
                if ffsubsync_option_vad_var.get():
                    cmd += (" --vad=auditok")
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
        subtitle_input.grid_remove()
        video_input.grid_remove()
        button_start_automatic_sync.grid_remove()
        batch_mode_button.grid_remove()
        check_save_to_desktop_auto.grid_remove()
        check_replace_original_auto.grid_remove()
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
        log_window.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew", columnspan=2)
        progress_bar = ttk.Progressbar(automatic_tab, orient="horizontal", length=200, mode="determinate")
        progress_bar.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="ew", columnspan=2)
        root.update_idletasks()
        threading.Thread(target=run_subprocess).start()
    except Exception as e:
        log_message(f"Error occurred: {e}", "error", tab='auto')
    automatic_tab.rowconfigure(0, weight=1)
    automatic_tab.rowconfigure(1, weight=0)
    automatic_tab.columnconfigure(0, weight=1)
# Start automatic sync end
label_message_auto = tk.Label(automatic_tab, text="", fg="black", anchor="center")
subtitle_input = tk.Label(automatic_tab, text="Drag and drop the unsynchronized subtitle file here or click to browse.", bg="lightgray", relief="ridge", width=40, height=5, cursor="hand2")
video_input = tk.Label(automatic_tab, text="Drag and drop video or reference subtitle file here or click to browse.", bg="lightgray", relief="ridge", width=40, height=5, cursor="hand2")
video_input_text = tk.Label(automatic_tab, text="Video/Reference subtitle", fg="black", relief="ridge", padx=5, borderwidth=1)
video_input_text.place(in_=video_input, relx=0, rely=0, anchor="nw")
subtitle_input_text = tk.Label(automatic_tab, text="Subtitle", fg="black", relief="ridge", padx=5, borderwidth=1) 
subtitle_input_text.place(in_=subtitle_input, relx=0, rely=0, anchor="nw")
button_start_automatic_sync = tk.Button(
    automatic_tab,
    text="Start Automatic Sync",
    command=start_automatic_sync,
    padx=10,
    pady=10,
    fg="white",
    bg="dodger blue",
    activebackground="DodgerBlue3",
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
video_input.grid(row=0, column=0, padx=10, pady=(10,5), sticky="nsew", columnspan=2)
subtitle_input.grid(row=1, column=0, padx=10, pady=0, sticky="nsew", columnspan=2)
ffsubsync_option_framerate.grid(row=2, column=0, columnspan=5, padx=10, pady=(5,0), sticky="w")
ffsubsync_option_gss.grid(row=3, column=0, columnspan=5, padx=10, pady=0, sticky="w")
ffsubsync_option_vad.grid(row=4, column=0, columnspan=5, padx=10, pady=0, sticky="w")
check_save_to_desktop_auto.grid(row=6, column=0, columnspan=5, padx=10, pady=5, sticky="w")
check_replace_original_auto.grid(row=6, column=1, columnspan=5, padx=10, pady=5, sticky="e")
subtitle_input.drop_target_register(DND_FILES)
automatic_tab.columnconfigure(1, weight=1)
batch_mode_var = tk.BooleanVar()
batch_mode_button = tk.Button(
    automatic_tab,
    text="Batch Mode",
    command=toggle_batch_mode,
    padx=10,
    pady=10,
    fg="white",
    bg="gray50",  # Different color for Batch Mode
    activebackground="gray40",
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
    bg="#00b503",
    activebackground="#009602",
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