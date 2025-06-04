import os
import sys
import json
import subprocess
import ctypes
import tkinter as tk
from theme import THEME
from functions.get_platform import platform
from functions.get_config import config_path
from config import default_settings
from texts_constants import CONFIG_FILE_NOT_FOUND, WARNING, CONFIRM_RESET_MESSAGE
from config import config
import cchardet
import charset_normalizer
import chardet
from tkinter import messagebox

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
    global config
    if config.get("remember_the_changes", True) or key == "remember_the_changes":
        try:
            with open(config_path, "r", encoding="utf-8") as config_file:
                config = json.load(config_file)
        except FileNotFoundError:
            config = {}
            messagebox.showerror("Error", CONFIG_FILE_NOT_FOUND)
        config[key] = value
        with open(config_path, "w", encoding="utf-8") as config_file:
            json.dump(config, config_file, indent=4)


def reset_to_default_settings():
    if messagebox.askyesno(WARNING, CONFIRM_RESET_MESSAGE):
        for key, value in default_settings.items():
            update_config(key, value)
        restart_program()
        


def restart_program():
    python = sys.executable
    if getattr(sys, "frozen", False):
        # Running as an executable
        os.execl(python, python)
    else:
        # Running as a script
        script_path = os.path.abspath(__file__)
        os.execl(python, python, script_path)


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

