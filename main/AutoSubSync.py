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
