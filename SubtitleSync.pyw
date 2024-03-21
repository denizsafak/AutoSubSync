import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import chardet
import html
import sys

# Dictionary to store total shifted milliseconds for each subtitle file
total_shifted_milliseconds = {}
def shift_subtitle(subtitle_file, milliseconds, save_to_desktop, replace_original):
    global total_shifted_milliseconds
    try:
        with open(subtitle_file, 'rb') as file:
            raw_data = file.read()
            encoding = chardet.detect(raw_data)['encoding']
            lines = raw_data.decode(encoding).splitlines()
    except Exception as e:
        log_message(f"Error loading subtitle file: {str(e)}", "error")
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
                log_message("Error decoding line, skipping...", "error")
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
            log_message(f"Success! Subtitle shifted by {milliseconds} milliseconds and saved to: {new_subtitle_file}", "success", new_subtitle_file)
    try:
        # Write to file after progress bar is fully loaded
        with open(new_subtitle_file, 'wb') as file:  # Open in binary mode to preserve encoding
            file.write('\n'.join(new_lines).encode(encoding))
        # Hide current log message
        label_message.grid_forget()
        # Create a progress bar
        progress_bar = ttk.Progressbar(root, orient="horizontal", length=200, mode="determinate")
        progress_bar.grid(row=5, column=0, columnspan=5, padx=10, pady=(0, 10), sticky="ew")
        update_progress(progress_bar, 0)
        if replace_original:
            total_shifted_milliseconds[subtitle_file] = total_shifted
    except Exception as e:
        log_message(f"Error saving subtitle file: {str(e)}", "error")

def sync_subtitle():
    if hasattr(label_drop_box, 'tooltip_text'):
        subtitle_file = label_drop_box.tooltip_text
        if subtitle_file:
            try:
                milliseconds = int(entry_milliseconds.get())
                if milliseconds == 0:
                    log_message("Please enter a non-zero value for milliseconds.", "error")
                    return
                save_to_desktop = save_to_desktop_var.get()  # Get the value of the save_to_desktop switch
                replace_original = replace_original_var.get()  # Get the value of the replace_original switch
                if save_to_desktop and replace_original:
                    log_message("Please select only one option: Save to Desktop or Replace Original Subtitle.", "error")
                    return
                shift_subtitle(subtitle_file, milliseconds, save_to_desktop, replace_original)
            except ValueError:
                log_message("Please enter a valid number of milliseconds.", "error")
    else:
        log_message("Please select a subtitle", "error")

def on_drop(event):
    filepath = event.data.strip("{}")  # Remove curly braces from the path
    # Check if the dropped file has the .srt extension
    if filepath.lower().endswith('.srt'):
        label_drop_box.config(text=filepath, font=("Calibri", 10, "bold"))
        label_drop_box.tooltip_text = filepath
        label_drop_box.config(bg="lightgreen")  # Change background color to light green
        log_message("", "info")
    else:
        log_message("Please drop a valid subtitle file.", "error")
        label_drop_box.config(bg="lightgray")  # Restore background color to light gray

def browse_file(event=None):
    subtitle_file = filedialog.askopenfilename(filetypes=[("Subtitle files", "*.srt")])
    if subtitle_file:
        label_drop_box.config(text=subtitle_file, font=("Calibri", 10, "bold"))
        label_drop_box.tooltip_text = subtitle_file
        label_drop_box.config(bg="lightgreen")  # Change background color to light green
        log_message("", "info")
    else:
        # Check if the user canceled the dialog
        if subtitle_file != '':
            log_message("Please select a subtitle", "error")
            label_drop_box.config(bg="lightgray")  # Restore background color to light gray

def select_subtitle_at_startup():
    if len(sys.argv) > 1:
        subtitle_file = sys.argv[1]
        if os.path.isfile(subtitle_file) and subtitle_file.lower().endswith('.srt'):
            label_drop_box.config(text=subtitle_file, font=("Calibri", 10, "bold"))
            label_drop_box.tooltip_text = subtitle_file
            label_drop_box.config(bg="lightgreen")
            log_message("", "info")
        elif not os.path.isfile(subtitle_file):
            log_message("File specified in the argument does not exist.", "error")
            label_drop_box.config(bg="lightgray")
        elif len(sys.argv) > 2:
            log_message("Multiple arguments provided. Please provide only one subtitle file path.", "error")
            label_drop_box.config(bg="lightgray")
        else:
            print(sys.argv[1])
            log_message("Invalid file format. Please provide a subtitle file.", "error")
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
    if hasattr(label_drop_box, 'tooltip_text'):
        label_drop_box.config(bg="lightgreen")  # Change background color to light green
    else:
        label_drop_box.config(bg="lightblue")  # Change background color to light blue

def on_leave(event):
    if hasattr(label_drop_box, 'tooltip_text'):
        label_drop_box.config(bg="lightgreen")  # Change background color to light green
    else:
        label_drop_box.config(bg="lightgray")  # Restore background color to light gray

current_log_type = None
def log_message(message, msg_type=None, filepath=None):
    global current_log_type
    if msg_type == "error":
        current_log_type = "error"
        color = "red"
        bg_color = "RosyBrown1"  # Set background color for error messages
    elif msg_type == "success":
        current_log_type = "success"
        color = "green"
        bg_color = "lightgreen"  # Set background color for success messages
    elif msg_type == "info":
        current_log_type = "info"
        color = "black"
        bg_color = "light goldenrod"  # Set background color for success messages
    else:
        current_log_type = None
        color = "black"
        bg_color = "light grey"  # Default background color for other messages
    label_message.config(text=message, fg=color, bg=bg_color)
    if message:
        label_message.grid(row=5, column=0, columnspan=5, padx=10, pady=(0, 10), sticky="ew")  # Place label_message below other elements
    else:
        label_message.grid_forget()  # Hide label_message if there is no log message
    label_message.config(font=("Arial", 8, "bold"))  # Make the log message bold
    if msg_type == "success" and filepath:
        label_message.config(cursor="hand2")
        label_message.bind("<Button-1>", lambda event: open_directory(filepath))

def open_directory(filepath):
    directory = os.path.dirname(filepath)
    if os.path.isdir(directory):
        # Select the file in the file explorer
        selected_file = '"' + os.path.realpath(filepath) + '"'
        os.system(f'start explorer /select,{selected_file}')

def update_wraplengt(event=None):
    label_drop_box.config(wraplength=label_drop_box.winfo_width() - 60)
    label_message.config(wraplength=label_message.winfo_width() - 60)

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
            y_pos = self.widget.winfo_rooty() - 55  # Adjust tooltip position above the widget
            # Calculate the screen dimensions
            screen_width = self.widget.winfo_screenwidth()
            # Calculate the size of the tooltip
            tooltip_width = 200  # Adjust as needed
            tooltip_height = 50  # Adjust as needed
            # Create the tooltip at the calculated position
            self.tooltip = tk.Toplevel(self.widget)
            self.tooltip.wm_overrideredirect(True)
            # Adjust tooltip position to stay within the screen bounds
            if x_pos + tooltip_width > screen_width:
                x_pos = screen_width - tooltip_width - 3
            if y_pos < 0:
                y_pos = 0
            # Adjust tooltip position to avoid covering the button
            if y_pos < tooltip_height:
                y_pos = tooltip_height
            # Adjust tooltip position if too far to the left
            if x_pos < 0:
                x_pos = 0
            elif x_pos + tooltip_width > screen_width:
                x_pos = screen_width - tooltip_width
            self.tooltip.wm_geometry("+%d+%d" % (x_pos, y_pos))
            # Adjust wrap length based on available width
            wrap_length = min(tooltip_width, 200)  # Adjust as needed
            label = tk.Label(self.tooltip, text=self.text, justify=tk.LEFT, wraplength=wrap_length, background="#ffffe0", relief=tk.SOLID, borderwidth=1, font=("tahoma", "8", "normal"))
            label.pack(ipadx=1)
    def hide_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

# Define tooltip text for checkboxes
TOOLTIP_SAVE_TO_DESKTOP = "Check this box if you want to save the shifted subtitle to your Desktop. If unchecked, it will be saved in the original subtitle's folder."
TOOLTIP_REPLACE_ORIGINAL = "Check this box if you want to replace the original subtitle file with the shifted one. Please be careful. It will overwrite the current subtitle."
root = TkinterDnD.Tk()
root.title("Subtitle Synchronization Tool")
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)  # Allow label_drop_box to fill empty space
root.withdraw() # Hide the window while it's being built
label_drop_box = tk.Label(root, text="Drag and drop subtitle file here or click to browse.", bg="lightgray", relief="ridge", width=40, height=17, cursor="hand2")
label_separator = ttk.Separator(root, orient='horizontal')
label_message = tk.Label(root, text="", fg="black", anchor="center")  # Adjust wraplength as needed
label_milliseconds = tk.Label(root, text="Shift subtitle by (milliseconds):", anchor="w")
entry_milliseconds = tk.Entry(root, cursor="xterm", width=15, justify="center", borderwidth=2, validate='key')
entry_milliseconds.insert(0, "0")  # Set default value to 0
entry_milliseconds.config(validatecommand=(root.register(validate_input), '%P'))
button_minus = tk.Button(
    root, text="-",
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
    root, text="+",
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
    root,
    text="Shift Subtitle",
    command=sync_subtitle,
    padx=10,
    pady=10,
    fg="white",
    bg="#08872a",
    activebackground="#076921",
    activeforeground="white",
    relief=tk.RAISED,
    borderwidth=2,
    cursor="hand2"
)
label_drop_box.bind("<Button-1>", browse_file)
label_drop_box.bind("<Enter>", on_enter)
label_drop_box.bind("<Leave>", on_leave)
entry_milliseconds.bind("<FocusIn>", clear_entry)
label_drop_box.grid(row=0, column=0, columnspan=5, padx=10, pady=10, sticky="nsew")
label_separator.grid(row=1, column=0, columnspan=5, sticky="ew", padx=10, pady=5)
label_milliseconds.grid(row=2, column=0, padx=10, pady=5, sticky="w")
button_minus.grid(row=2, column=1, padx=(0,5), pady=5, sticky="ew")
entry_milliseconds.grid(row=2, column=2, pady=5, sticky="ew", ipady=7)
button_plus.grid(row=2, column=3, padx=(5,10), pady=5, sticky="ew")
button_sync.grid(row=3, column=0, columnspan=5, padx=10, pady=10, sticky="ew")
label_drop_box.drop_target_register(DND_FILES)
label_drop_box.dnd_bind('<<Drop>>', on_drop)
# Checkbutton for choosing to save to desktop or current folder
save_to_desktop_var = tk.BooleanVar()
check_save_to_desktop = tk.Checkbutton(root, text="Save to Desktop", variable=save_to_desktop_var, command=lambda: checkbox_selected(save_to_desktop_var))
check_save_to_desktop.grid(row=4, column=0, columnspan=5, padx=10, pady=(0, 10), sticky="w")
replace_original_var = tk.BooleanVar()
check_replace_original = tk.Checkbutton(root, text="Replace original subtitle", variable=replace_original_var, command=lambda: checkbox_selected(replace_original_var))
check_replace_original.grid(row=4, column=1, columnspan=5, padx=(10,0), pady=(0, 10), sticky="w")
label_drop_box.bind("<Configure>", update_wraplengt)
label_message.bind("<Configure>", update_wraplengt)
# Create tooltips for checkboxes
tooltip_save_to_desktop = ToolTip(check_save_to_desktop, TOOLTIP_SAVE_TO_DESKTOP)
tooltip_replace_original = ToolTip(check_replace_original, TOOLTIP_REPLACE_ORIGINAL)
# Place the window at the top right corner of the screen
root.update_idletasks()
place_window_top_right()
# Select subtitle file if specified as argument
select_subtitle_at_startup()
# Calculate minimum width and height based on elements inside
min_width = label_drop_box.winfo_reqwidth() + 90  # Add some padding
min_height = sum(widget.winfo_reqheight() for widget in (label_drop_box, label_separator, label_milliseconds, button_sync, check_save_to_desktop, check_replace_original)) + 60  # Add padding and adjust as needed
root.minsize(min_width, min_height)  # Set minimum size for the window
root.deiconify() # Show the window after it's been built
root.mainloop()