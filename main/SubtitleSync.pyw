import os
import sys
import re
import html
import chardet
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
os.chdir(os.path.dirname(__file__))
total_shifted_milliseconds = {}
def shift_subtitle(subtitle_file, milliseconds, save_to_desktop, replace_original):
    global total_shifted_milliseconds
    try:
        with open(subtitle_file, 'rb') as file:
            raw_data = file.read()
            encoding = chardet.detect(raw_data)['encoding']
            lines = raw_data.decode(encoding).splitlines()
    except Exception as e:
        log_message(f"Error loading subtitle file: {str(e)}", "error", tab='manual')
        return
    directory_path = os.path.dirname(subtitle_file)
    filename = os.path.basename(subtitle_file)
    new_lines = []
    # Calculate total shifted milliseconds for the current subtitle file
    if replace_original and subtitle_file in total_shifted_milliseconds:
        total_shifted = total_shifted_milliseconds[subtitle_file] + milliseconds
    else:
        total_shifted = milliseconds
    for raw_line in lines:
        if isinstance(raw_line, bytes):  # Check if line is still bytes and needs decoding
            try:
                line = raw_line.decode(encoding)
            except UnicodeDecodeError:
                log_message("Error decoding line, skipping...", "error", tab='manual')
                continue
        else:
            line = raw_line
        if '-->' in line:  # Check if the line contains time information
            # Split the time information from the line
            parts = line.strip().split(' --> ')
            start_time, end_time = parts
            # Parse time string to milliseconds
            start_hours, start_minutes, start_seconds_milliseconds = start_time.split(':')
            end_hours, end_minutes, end_seconds_milliseconds = end_time.split(':')
            start_seconds, start_milliseconds = start_seconds_milliseconds.split(',')
            end_seconds, end_milliseconds = end_seconds_milliseconds.split(',')
            start_total_milliseconds = (int(start_hours) * 3600 + int(start_minutes) * 60 + int(start_seconds)) * 1000 + int(start_milliseconds)
            end_total_milliseconds = (int(end_hours) * 3600 + int(end_minutes) * 60 + int(end_seconds)) * 1000 + int(end_milliseconds)
            # Shift the time by the specified milliseconds
            start_total_milliseconds += milliseconds
            end_total_milliseconds += milliseconds
            # Convert negative milliseconds to positive if needed
            start_total_milliseconds = max(start_total_milliseconds, 0)
            end_total_milliseconds = max(end_total_milliseconds, 0)
            # Convert milliseconds to time string format
            shifted_start_time = "{:02d}:{:02d}:{:02d},{:03d}".format(
                (start_total_milliseconds // 3600000),
                (start_total_milliseconds // 60000) % 60,
                (start_total_milliseconds // 1000) % 60,
                start_total_milliseconds % 1000
            )
            shifted_end_time = "{:02d}:{:02d}:{:02d},{:03d}".format(
                (end_total_milliseconds // 3600000),
                (end_total_milliseconds // 60000) % 60,
                (end_total_milliseconds // 1000) % 60,
                end_total_milliseconds % 1000
            )
            new_line = f"{shifted_start_time} --> {shifted_end_time}"
            new_lines.append(new_line)
        else:
            # Preserve HTML tags in subtitle text
            line = html.unescape(line)
            new_lines.append(line)
    if replace_original:
        new_subtitle_file = subtitle_file
        if subtitle_file in total_shifted_milliseconds and total_shifted_milliseconds[subtitle_file] != 0:
            response = messagebox.askyesno("Subtitle Change Confirmation", f"Adjusting again by {milliseconds}ms, will make a total difference of {total_shifted}ms. Proceed?")
            if not response:
                return
    elif save_to_desktop:
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        new_subtitle_file = os.path.join(desktop_path, f"{total_shifted}ms_{filename}")
    else:
        new_subtitle_file = os.path.join(directory_path, f"{total_shifted}ms_{filename}")
    if os.path.exists(new_subtitle_file) and not replace_original:
        replace = messagebox.askyesno("File Exists", f"A file with the name '{os.path.basename(new_subtitle_file)}' already exists. Do you want to replace it?")
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
        with open(new_subtitle_file, 'wb') as file:  # Open in binary mode to preserve encoding
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
    if filepath.lower().endswith('.srt'):
        label_drop_box.config(text=filepath, font=("Calibri", 10, "bold"))
        label_drop_box.tooltip_text = filepath
        label_drop_box.config(bg="lightgreen")  # Change background color to light green
        log_message("", "info", tab='manual')
    else:
        log_message("Please drop a subtitle file.", "error", tab='manual')
        label_drop_box.config(bg="lightgray")  # Restore background color to light gray

def browse_file(event=None):
    subtitle_file = filedialog.askopenfilename(filetypes=[("Subtitle files", "*.srt")])
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
    if hasattr(event.widget, 'tooltip_text'):
        event.widget.config(bg="lightgreen")  # Change background color to light green
    else:
        event.widget.config(bg="lightblue")  # Change background color to light blue

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
            label_message_auto.grid(row=5, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")
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
root = TkinterDnD.Tk()
root.title("Subtitle Synchronization Tool")
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
    subtitle_file_auto = filedialog.askopenfilename(filetypes=[("Subtitle files", "*.srt")])
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
    video_file = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4;*.mkv;*.avi")])
    if video_file:
        label_video.config(text=video_file, font=("Calibri", 10, "bold"))
        label_video.tooltip_text = video_file
        label_video.config(bg="lightgreen")
        log_message("", "info", tab='auto')
    else:
        if video_file != '':
            log_message("Please select a video", "error", tab='auto')
            label_video.config(bg="lightgray")

def on_subtitle_drop(event):
    filepath = event.data.strip("{}")
    if filepath.lower().endswith('.srt'):
        label_subtitle.config(text=filepath, font=("Calibri", 10, "bold"))
        label_subtitle.tooltip_text = filepath
        label_subtitle.config(bg="lightgreen")
        log_message("", "info", tab='auto')
    else:
        log_message("Please drop a subtitle file.", "error", tab='auto')

def on_video_drop(event):
    filepath = event.data.strip("{}")
    if filepath.lower().endswith(('.mp4', '.mkv', '.avi')):
        label_video.config(text=filepath, font=("Calibri", 10, "bold"))
        label_video.tooltip_text = filepath
        label_video.config(bg="lightgreen")
        log_message("", "info", tab='auto')
    else:
        log_message("Please drop a video file.", "error", tab='auto')

process = None
def start_automatic_sync():
    global process
    subtitle_file = getattr(label_subtitle, 'tooltip_text', None)
    video_file = getattr(label_video, 'tooltip_text', None)
    if not subtitle_file or not video_file:
        log_message("Please select a subtitle and a video file.", "error", tab='auto')
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
    cmd = f'ffs "{video_file}" -i "{subtitle_file}" -o "{output_subtitle_file}" --gss'
    def cancel_automatic_sync():
        global process
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
        log_window.grid_remove()
        progress_bar.grid_remove()
        button_generate_again.grid_remove()
        button_cancel_automatic_sync.grid_remove()
        root.update_idletasks()

    def generate_again():
        label_subtitle.grid()
        label_video.grid()
        check_save_to_desktop_auto.grid()
        check_replace_original_auto.grid()
        button_start_automatic_sync.grid()
        log_window.grid_remove()
        progress_bar.grid_remove()
        button_generate_again.grid_remove()
        button_cancel_automatic_sync.grid_remove()
        label_message_auto.grid_remove()
        root.update_idletasks()

    def run_subprocess():
        global process, progress_line_number
        try:
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            progress_bar["value"] = 1
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
                    button_generate_again.grid()
                else:
                    log_message("Error occurred during synchronization. Please check the log messages.", "error", tab='auto')
                    button_cancel_automatic_sync.grid_remove()
                    button_generate_again.grid()
        except Exception as e:
            log_message(f"Error occurred: {e}", "error", tab='auto')
        progress_bar.grid_remove()
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
        button_generate_again.grid(row=7, column=0, padx=10, pady=(00,10), sticky="ew", columnspan=2)
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
label_subtitle = tk.Label(automatic_tab, text="Drag and drop subtitle file here or click to browse.", bg="lightgray", relief="ridge", width=40, height=5, cursor="hand2")
label_video = tk.Label(automatic_tab, text="Drag and drop video file here or click to browse.", bg="lightgray", relief="ridge", width=40, height=5, cursor="hand2")
label_video_text = tk.Label(automatic_tab, text="Video", fg="black", relief="ridge", padx=5, borderwidth=1)
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
save_to_desktop_var_auto = tk.BooleanVar()
replace_original_var_auto = tk.BooleanVar()
check_save_to_desktop_auto = tk.Checkbutton(automatic_tab, text="Save to Desktop", variable=save_to_desktop_var_auto, command=lambda: checkbox_selected_auto(save_to_desktop_var_auto))
check_replace_original_auto = tk.Checkbutton(automatic_tab, text="Replace original subtitle", variable=replace_original_var_auto, command=lambda: checkbox_selected_auto(replace_original_var_auto))
tooltip_save_to_desktop = ToolTip(check_save_to_desktop_auto, TOOLTIP_SAVE_TO_DESKTOP)
tooltip_replace_original = ToolTip(check_replace_original_auto, TOOLTIP_REPLACE_ORIGINAL)
label_subtitle.grid(row=0, column=0, padx=10, pady=(10,5), sticky="nsew", columnspan=2)
label_video.grid(row=1, column=0, padx=10, pady=0, sticky="nsew", columnspan=2)
button_start_automatic_sync.grid(row=2, column=0, padx=10, pady=10, sticky="ew", columnspan=2)
check_save_to_desktop_auto.grid(row=3, column=0, columnspan=5, padx=10, pady=5, sticky="w")
check_replace_original_auto.grid(row=3, column=1, columnspan=5, padx=10, pady=5, sticky="w")
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
min_height_automatic = sum(widget.winfo_reqheight() for widget in (label_drop_box, label_separator, button_sync, check_save_to_desktop)) + 50
min_height_manual = sum(widget.winfo_reqheight() for widget in (label_drop_box, label_separator, label_milliseconds, entry_milliseconds, button_minus, button_plus, button_sync, check_save_to_desktop, check_replace_original))
min_height = max(min_height_automatic, min_height_manual)
root.minsize(min_width, min_height)  # Set minimum size for the window
# if icon exists, set it as the window icon
if os.path.exists('icon.ico'):
    root.iconbitmap('icon.ico')
root.deiconify() # Show the window after it's been built
root.mainloop()