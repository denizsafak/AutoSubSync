# filepath: /run/media/laptop/A25E56C85E56953F/Projects/AutoSubSync/pyqt/gui_log_window.py
import os
import logging
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QPushButton,
    QHBoxLayout,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QTextCursor, QColor
from constants import DEFAULT_OPTIONS, COLORS

logger = logging.getLogger(__name__)

class LogWindow(QWidget):
    """A log window that captures and displays log messages during sync operations."""
    
    # Signal emitted when the cancel button is clicked
    cancel_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self._config_printed = False
        
    def setup_ui(self):
        """Set up the log window UI elements."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create text area for logs
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.log_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.log_text, 1)

        layout.setSpacing(15)
        
        # Bottom controls
        bottom_layout = QHBoxLayout()

        # Add Cancel button using parent's _button method if available
        self.cancel_button = self.parent()._button("Cancel")
        self.cancel_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.cancel_button.clicked.connect(self.cancel_clicked.emit)
        
        bottom_layout.addWidget(self.cancel_button)
        
        layout.addLayout(bottom_layout)
    
    def print_config(self, app_instance):
        """Print configuration details from the app instance to the log window."""
        if self._config_printed:
            return
            
        self.log_text.clear()
        config = app_instance.config
        
        # Helper function to get config values with defaults from DEFAULT_OPTIONS
        def get_config(key):
            return config.get(key, DEFAULT_OPTIONS.get(key))
        
        sync_tool = get_config("sync_tool")
        
        # HEADER - CONFIGURATION
        self.append_message("Configuration:", bold=True)
        
        # Batch or normal mode
        if app_instance.batch_mode_enabled:
            valid_pairs = []
            if hasattr(app_instance, 'batch_tree_view'):
                valid_pairs = app_instance.batch_tree_view.get_all_valid_pairs()
            
            self.append_message(f"Mode: ", end="")
            self.append_message("Batch", bold=True, color=COLORS["GREEN"])
            self.append_message(f"Total pairs: ", end="")
            self.append_message(str(len(valid_pairs)), bold=True, color=COLORS["GREEN"])
        else:
            video_ref_path = app_instance.video_ref_input.file_path if hasattr(app_instance, 'video_ref_input') else "Not set"
            subtitle_path = app_instance.subtitle_input.file_path if hasattr(app_instance, 'subtitle_input') else "Not set"
            self.append_message(f"Mode: ", end="")
            self.append_message("Normal", bold=True, color=COLORS["GREEN"])
            #self.append_message(f"Reference: ", end="")
            #self.append_message(video_ref_path, bold=True, color=COLORS["GREEN"])
            #self.append_message(f"Input subtitle: ", end="")
            #self.append_message(subtitle_path, bold=True, color=COLORS["GREEN"])
        
        # Sync tool and its specific settings
        self.append_message(f"Sync tool: ", end="")
        self.append_message(sync_tool, bold=True, color=COLORS["GREEN"])
        
        # Display sync tool options in tree diagram
        if sync_tool == "alass":
            check_video = get_config("alass_check_video_subtitles")
            disable_fps = get_config("alass_disable_fps_guessing")
            disable_speed = get_config("alass_disable_speed_optimization")
            split_penalty = get_config("alass_split_penalty")
            
            self.append_message(f"├─ Check video for subtitle streams: ", end="")
            self.append_message(str(check_video), bold=True, color=COLORS["GREEN"])
            self.append_message(f"├─ Disable FPS guessing: ", end="")
            self.append_message(str(disable_fps), bold=True, color=COLORS["GREEN"])
            self.append_message(f"├─ Disable speed optimization: ", end="")
            self.append_message(str(disable_speed), bold=True, color=COLORS["GREEN"])
            self.append_message(f"└─ Split penalty: ", end="")
            self.append_message(str(split_penalty), bold=True, color=COLORS["GREEN"])
            
        elif sync_tool == "ffsubsync":
            dont_fix = get_config("ffsubsync_dont_fix_framerate")
            golden_section = get_config("ffsubsync_use_golden_section")
            vad = get_config("ffsubsync_vad")

            self.append_message(f"├─ Don't fix framerate: ", end="")
            self.append_message(str(dont_fix), bold=True, color=COLORS["GREEN"])
            self.append_message(f"├─ Use golden section search: ", end="")
            self.append_message(str(golden_section), bold=True, color=COLORS["GREEN"])
            self.append_message(f"└─ Voice activity detector: ", end="")
            self.append_message(vad, bold=True, color=COLORS["GREEN"])
        
        # Common settings
        add_prefix = get_config("add_autosync_prefix")
        backup = get_config("backup_subtitles_before_overwriting")
        keep_extracted = get_config("keep_extracted_subtitles")
        keep_converted = get_config("keep_converted_subtitles")
        
        self.append_message(f"Add 'autosync' prefix: ", end="")
        self.append_message(str(add_prefix), bold=True, color=COLORS["GREEN"])
        self.append_message(f"Backup subtitles before overwriting: ", end="")
        self.append_message(str(backup), bold=True, color=COLORS["GREEN"])
        self.append_message(f"Keep extracted subtitles: ", end="")
        self.append_message(str(keep_extracted), bold=True, color=COLORS["GREEN"])
        self.append_message(f"Keep converted subtitles: ", end="")
        self.append_message(str(keep_converted), bold=True, color=COLORS["GREEN"])
        
        # Save location
        if app_instance.batch_mode_enabled:
            save_location = get_config("automatic_save_location")
        else:
            save_location = get_config("automatic_save_location")
            
        # Map save location codes to human-readable text
        save_location_map = {
            "save_next_to_input_subtitle": "Next to input subtitle",
            "overwrite_input_subtitle": "Overwrite input subtitle",
            "save_next_to_video": "Next to video",
            "save_next_to_video_with_same_filename": "Next to video with same filename",
            "save_to_desktop": "Desktop",
            "select_destination_folder": f"{config.get('automatic_save_folder', '')}"
        }
        
        save_location_text = save_location_map.get(save_location, save_location)
        self.append_message(f"Save location: ", end="")
        self.append_message(save_location_text, bold=True, color=COLORS["GREEN"])
        
        # Additional arguments if present
        args_key = f"{sync_tool}_arguments"
        args = config.get(args_key)
        if args:
            self.append_message(f"\nAdditional arguments: ", end="")
            self.append_message(args, bold=True, color=COLORS["GREEN"])
            
        self.append_message("\nSync started:\n", bold=True)
        self._config_printed = True
        
    def append_message(self, message, bold=False, color=None, end="\n"):
        """Append a message to the log window, with optional formatting."""
        cursor = self.log_text.textCursor()
        
        # Move to end if needed
        if not cursor.atEnd():
            cursor.movePosition(QTextCursor.MoveOperation.End)
        
        if bold or color:
            # Apply formatting
            fmt = cursor.charFormat()
            if bold: fmt.setFontWeight(700)
            if color: fmt.setForeground(QColor(color))
            cursor.setCharFormat(fmt)
            cursor.insertText(message + end)
            
            # Reset format
            if bold: fmt.setFontWeight(400)
            if color: fmt.clearForeground()
            cursor.setCharFormat(fmt)
        else:
            cursor.insertText(message + end)
        
        # Update UI
        self.log_text.setTextCursor(cursor)
        self.log_text.ensureCursorVisible()
        
    def clear(self):
        """Clear the log window and reset its state."""
        self.log_text.clear()
        self._config_printed = False

# Handler class for redirecting Python's logging system to the log window
class LogWindowHandler(logging.Handler):
    def __init__(self, log_window):
        super().__init__()
        self.log_window = log_window
        self.setFormatter(logging.Formatter('%(message)s'))
        
    def emit(self, record):
        msg = self.format(record)
        color = None
        
        if record.levelno >= logging.ERROR:
            color = COLORS["RED"]
            bold = True
        elif record.levelno >= logging.WARNING:
            color = COLORS["ORANGE"]
            bold = False
        else:
            color = None
            bold = False
            
        # Use QMetaObject.invokeMethod to safely call from any thread
        self.log_window.append_message(msg, bold=bold, color=color)