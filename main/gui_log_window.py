import os
import logging
import texts
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QHBoxLayout,
    QSizePolicy,
    QPushButton,
    QProgressBar,
)
from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtGui import QTextCursor, QColor, QFont, QTextCharFormat, QFontDatabase
from constants import DEFAULT_OPTIONS, COLORS, SYNC_TOOLS, AUTOMATIC_SAVE_MAP
from utils import get_resource_path, get_logs_directory, open_folder

logger = logging.getLogger(__name__)


_log_font_family = None
_log_font_loaded = False


def _get_log_font():
    global _log_font_family, _log_font_loaded
    if not _log_font_loaded:
        _log_font_loaded = True
        try:
            font_path = get_resource_path("autosubsyncapp.assets.fonts", "hack.ttf")
            if font_path and os.path.exists(font_path):
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    if families:
                        _log_font_family = families[0]
                        logger.info(f'Loaded custom font: "{_log_font_family}" for log window.')
        except Exception as e:
            logger.error(f"Exception loading custom font: {e}")

    if _log_font_family:
        return QFont(_log_font_family)
    font = QFont()
    font.setFamilies(["Consolas", "Monospace", "DejaVu Sans Mono", "Courier New"])
    return font


from PyQt6.QtCore import pyqtSignal, QObject, QThread

class LogSignalRelay(QObject):
    append_message_signal = pyqtSignal(str, bool, object, bool, str)


class LogWindow(QWidget):
    cancel_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config_printed = False
        self.signal_relay = LogSignalRelay()
        self.signal_relay.append_message_signal.connect(self._do_append_message)
        self._last_line_is_update = False  # Initialize state for overwrite logic
        self._user_scrolled_up = False  # Track if user scrolled up
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        self.log_text = QTextEdit(readOnly=True)
        self.log_text.setFont(_get_log_font())

        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.log_text.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.log_text, 1)

        # floating scroll-to-bottom button
        self.scroll_button = QPushButton("↓", self.log_text)
        self.scroll_button.setVisible(False)
        self.scroll_button.setFixedSize(35, 35)
        self.scroll_button.clicked.connect(
            lambda: self.log_text.verticalScrollBar().setValue(
                self.log_text.verticalScrollBar().maximum()
            )
        )
        self.log_text.verticalScrollBar().valueChanged.connect(
            self._update_scroll_button
        )

        self.default_char_format = self.log_text.currentCharFormat()

        # Bottom button layout - using vertical layout for buttons in rows
        bottom = QVBoxLayout()
        bottom.setSpacing(15)

        # Create additional buttons that will be shown after completion
        create_btn = (
            getattr(self.parent(), "_button", None)
            if self.parent() is not None
            else None
        ) or (lambda txt, h=40: QPushButton(str(txt)))

        self.go_to_folder_button = create_btn(texts.GO_TO_FOLDER, h=40)
        self.go_to_folder_button.setVisible(False)
        bottom.addWidget(self.go_to_folder_button)

        self.new_conversion_button = create_btn(texts.NEW_CONVERSION, h=40)
        self.new_conversion_button.setVisible(False)
        bottom.addWidget(self.new_conversion_button)

        # Create Go back button
        self.go_back_button = create_btn(texts.GO_BACK, h=40)
        self.go_back_button.setVisible(False)
        bottom.addWidget(self.go_back_button)

        # Progress bar
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        bottom.addLayout(progress_layout)

        # Initially setup with just cancel button
        self.cancel_button = create_btn(texts.CANCEL, h=40)
        self.cancel_button.clicked.connect(self.cancel_clicked.emit)
        bottom.addWidget(self.cancel_button)

        layout.addLayout(bottom)

    def print_config(self, app):
        if self._config_printed:
            return
        self.log_text.clear()
        cfg = app.config
        get = lambda k: cfg.get(k, DEFAULT_OPTIONS.get(k))
        sync_tool = get("sync_tool")
        self.append_message(texts.CONFIGURATION_LABEL, bold=True, color=COLORS["BLUE"])
        if app.batch_mode_enabled:
            pairs = getattr(app, "batch_tree_view", None)
            n = len(pairs.get_all_valid_pairs()) if pairs else 0
            self.append_message(texts.MODE_LABEL, end="")
            self.append_message(texts.BATCH_MODE, bold=True, color=COLORS["GREEN"])
            self.append_message(f"{texts.TOTAL_PAIRS_LABEL} ", end="")
            self.append_message(str(n), bold=True, color=COLORS["GREEN"])
        else:
            self.append_message(texts.MODE_LABEL, end="")
            self.append_message(texts.NORMAL_MODE, bold=True, color=COLORS["GREEN"])
        self.append_message(f"{texts.SYNC_TOOL_LABEL} ", end="")
        self.append_message(sync_tool, bold=True, color=COLORS["GREEN"])
        tool_info = SYNC_TOOLS.get(sync_tool)
        if tool_info and "options" in tool_info:
            opts = tool_info["options"]
            # Filter out spacer options for display
            display_opts = {k: v for k, v in opts.items() if v.get("type") != "spacer"}
            for i, (k, v) in enumerate(display_opts.items()):
                prefix = "└─ " if i == len(display_opts) - 1 else "├─ "
                val = cfg.get(f"{sync_tool}_{k}", v.get("default"))
                opt_type = v.get("type")
                if opt_type == "checkbox":
                    display_val = texts.ENABLED if bool(val) else texts.DISABLED
                elif opt_type == "dropdown":
                    lbls = v.get("value_labels", {})
                    display_val = str(lbls.get(val, val))
                elif sync_tool == "alass" and k == "split_penalty" and val == -1:
                    display_val = texts.NO_SPLITS
                elif (
                    sync_tool == "lapse"
                    and k == "split_penalty"
                    and cfg.get("lapse_mode") in ("nosplit", "ols")
                ):
                    display_val = texts.DISABLED
                elif isinstance(val, bool):
                    display_val = texts.ENABLED if val else texts.DISABLED
                else:
                    display_val = str(val)
                self.append_message(f"{prefix}{v.get('label', k)}: ", end="")
                self.append_message(display_val, bold=True, color=COLORS["GREEN"])
        else:
            self.append_message(
                texts.UNKNOWN_SYNC_TOOL_NO_OPTIONS, color=COLORS["ORANGE"]
            )

        # Translate boolean values for display
        def bool_display(val):
            if val is True:
                return texts.ENABLED
            elif val is False:
                return texts.DISABLED
            return str(val)

        self.append_message(f"{texts.BACKUP_SUBTITLES_BEFORE_OVERWRITING}: ", end="")
        self.append_message(
            bool_display(get("backup_subtitles_before_overwriting")),
            bold=True,
            color=COLORS["GREEN"],
        )

        # Display output subtitle encoding setting
        encoding_setting = get("output_subtitle_encoding")
        if encoding_setting == "disabled":
            encoding_display = texts.DISABLED
        elif encoding_setting == "same_as_input":
            encoding_display = texts.SAME_AS_INPUT_SUBTITLE
        else:
            # Get the display name for the encoding
            from utils import get_available_encodings

            encoding_map = dict(get_available_encodings())
            encoding_display = encoding_map.get(encoding_setting, encoding_setting)
        self.append_message(texts.OUTPUT_SUBTITLE_ENCODING_LABEL, end="")
        self.append_message(encoding_display, bold=True, color=COLORS["GREEN"])

        self.append_message(f"{texts.ADD_TOOL_PREFIX_TO_SUBTITLES}: ", end="")
        self.append_message(
            bool_display(get("add_tool_prefix")), bold=True, color=COLORS["GREEN"]
        )

        custom_suffix = get("custom_suffix")
        if custom_suffix:
            self.append_message(f"{texts.ADD_CUSTOM_SUFFIX_FOR_SUBTITLES}: ", end="")
            self.append_message(
                custom_suffix, bold=True, color=COLORS["GREEN"]
            )

        self.append_message(f"{texts.KEEP_EXTRACTED_SUBTITLES}: ", end="")
        self.append_message(
            bool_display(get("keep_extracted_subtitles")),
            bold=True,
            color=COLORS["GREEN"],
        )
        self.append_message(f"{texts.KEEP_CONVERTED_SUBTITLES}: ", end="")
        self.append_message(
            bool_display(get("keep_converted_subtitles")),
            bold=True,
            color=COLORS["GREEN"],
        )

        loc = get("automatic_save_location")
        # Get display text for the save location (mapping is now key:internal -> value:display)
        save_location_message = AUTOMATIC_SAVE_MAP.get(loc, loc)
        self.append_message(f"{texts.SAVE_LOCATION_LABEL} ", end="")
        self.append_message(save_location_message, bold=True, color=COLORS["GREEN"])
        if loc == "select_destination_folder":
            self.append_message(texts.FOLDER_LABEL, end="")
            self.append_message(
                cfg.get("automatic_save_folder", ""), bold=True, color=COLORS["GREEN"]
            )

        args = cfg.get(f"{sync_tool}_arguments")
        if args:
            self.append_message(texts.ADDITIONAL_ARGUMENTS_LABEL, end="")
            self.append_message(args, bold=True, color=COLORS["GREEN"])
        self.append_message(
            "\n" + texts.SYNC_STARTED_LABEL, bold=True, color=COLORS["BLUE"]
        )
        self._config_printed = True

        # Force scroll to bottom after initial configuration is printed
        self._scroll_to_bottom()

    def append_message(
        self, message, bold=False, color=None, overwrite=False, end="\n"
    ):
        if QThread.currentThread() != self.thread():
            self.signal_relay.append_message_signal.emit(
                str(message), bool(bold), color, bool(overwrite), str(end)
            )
            return
        self._do_append_message(message, bold, color, overwrite, end)

    def _do_append_message(
        self, message, bold=False, color=None, overwrite=False, end="\n"
    ):
        txt = self.log_text
        cursor = txt.textCursor()
        scrollbar = txt.verticalScrollBar()
        # Only auto-scroll if user is at bottom or hasn't scrolled up
        at_bottom = scrollbar.value() >= (scrollbar.maximum() - 10)
        # Set format
        fmt = QTextCharFormat(self.default_char_format)
        if bold:
            fmt.setFontWeight(QFont.Weight.Bold)
        if color:
            fmt.setForeground(QColor(color))
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.setCharFormat(fmt)
        if overwrite:
            if not message:
                return
            if self._last_line_is_update:
                cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                cursor.movePosition(
                    QTextCursor.MoveOperation.EndOfBlock,
                    QTextCursor.MoveMode.KeepAnchor,
                )
                cursor.removeSelectedText()
            cursor.insertText(str(message))
        else:
            if self._last_line_is_update:
                cursor.insertText("\n")
            cursor.insertText(str(message) + end)
        self._last_line_is_update = overwrite
        # Always auto-scroll unless user has scrolled up
        if at_bottom or not self._user_scrolled_up or txt.document().blockCount() <= 30:
            scrollbar.setValue(scrollbar.maximum())
            self._user_scrolled_up = False

    def clear(self):
        self.log_text.clear()
        self._config_printed = False
        self._last_line_is_update = False  # Reset overwrite state
        self._user_scrolled_up = False

    def _position_scroll_button(self):
        margin = 10
        lw = self.log_text.width()
        lh = self.log_text.height()
        sw = self.scroll_button.width()
        sh = self.scroll_button.height()
        sb = self.log_text.verticalScrollBar()
        scrollbar_width = sb.sizeHint().width()
        self.scroll_button.move(lw - sw - margin - scrollbar_width, lh - sh - margin)

    def _update_scroll_button(self):
        sb = self.log_text.verticalScrollBar()
        at_bottom = sb.value() >= (sb.maximum() - 10)
        if at_bottom:
            self.scroll_button.hide()
            self._user_scrolled_up = False
        else:
            self._position_scroll_button()
            self.scroll_button.show()
            self._user_scrolled_up = True

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_scroll_button()

    def update_progress(self, value, current=None, total=None):
        self.progress_bar.setValue(value)
        if self.progress_bar.isHidden():
            self.progress_bar.setVisible(True)

        if total and total > 1 and current:
            self.progress_bar.setFormat(f"%p% ({current}/{total})")
        else:
            self.progress_bar.setFormat("%p%")

    def handle_sync_completion(self, success, output, post_success_callback=None):
        """Handle completion of a synchronization process

        Args:
            success: Whether the synchronization was successful
            output: Path to the output file if successful, None otherwise
            post_success_callback: Optional callback to run after success message but before saved to message
        """
        # Get the main application instance
        app = self.window()
        self.progress_bar.setVisible(False)

        if success:
            self.append_message(
                "\n" + texts.SYNC_COMPLETED_SUCCESSFULLY,
                color=COLORS["GREEN"],
                bold=True,
            )
            # Call the post-success callback (e.g., sync tracking message)
            if post_success_callback:
                post_success_callback()
            self.append_message(
                texts.SAVED_TO_LABEL.format(output=output), color=COLORS["GREY"]
            )

            # Only show "Go to folder" for single file sync
            self.go_to_folder_button.setVisible(True)
            (
                self.go_to_folder_button.clicked.disconnect()
                if hasattr(self.go_to_folder_button, "clicked")
                and self.go_to_folder_button.receivers(self.go_to_folder_button.clicked)
                > 0
                else None
            )
            self.go_to_folder_button.clicked.connect(
                lambda: self._open_output_folder(output)
            )

            # Show and connect the "New conversion" button
            self.new_conversion_button.setVisible(True)
            (
                self.new_conversion_button.clicked.disconnect()
                if hasattr(self.new_conversion_button, "clicked")
                and self.new_conversion_button.receivers(
                    self.new_conversion_button.clicked
                )
                > 0
                else None
            )
            self.new_conversion_button.clicked.connect(
                lambda: self._reset_and_go_back(app)
            )

            # Save log window output to file if keep_log_records is enabled
            self._save_log_output_to_file(app, success=True, mode="normal")
        else:
            logger.error("Synchronization canceled/failed")
            self.append_message(
                "\n" + texts.SYNC_FAILED_CHECK_LOGS,
                color=COLORS["RED"],
                bold=True,
            )
            # Save log output even for failures if enabled
            self._save_log_output_to_file(app, success=False, mode="normal")

        # Hide cancel and show go back button
        self.cancel_button.setVisible(False)
        self.go_back_button.setVisible(True)
        (
            self.go_back_button.clicked.disconnect()
            if hasattr(self.go_back_button, "clicked")
            and self.go_back_button.receivers(self.go_back_button.clicked) > 0
            else None
        )
        self.go_back_button.clicked.connect(app.restore_auto_sync_tab)

        # Force scroll to bottom after buttons are shown
        self._scroll_to_bottom()

    def handle_batch_completion(
        self, success, output, callback, post_success_callback=None
    ):
        """Handle completion of a single item in batch processing

        Args:
            success: Whether the synchronization was successful
            output: Path to the output file if successful, None otherwise
            callback: Function to call to process the next item
            post_success_callback: Optional callback to run after success message but before saved to message
        """
        if success:
            self.append_message(
                "\n" + texts.SYNC_COMPLETED_SUCCESSFULLY,
                color=COLORS["GREEN"],
                bold=True,
            )
            # Call the post-success callback (e.g., sync tracking message)
            if post_success_callback:
                post_success_callback()

            self.append_message(
                texts.SAVED_TO_LABEL.format(output=output),
                color=COLORS["GREY"],
                end="\n\n",
            )
        else:
            logger.error("Synchronization canceled/failed")
            self.append_message(
                "\n" + texts.SYNC_FAILED_CHECK_LOGS,
                color=COLORS["RED"],
                bold=True,
                end="\n\n",
            )

        # Force scroll to bottom only if at bottom
        scrollbar = self.log_text.verticalScrollBar()
        if scrollbar.value() == scrollbar.maximum():
            scrollbar.setValue(scrollbar.maximum())

        # Process next item after a short delay
        # This gives the UI time to update before starting the next process
        from PyQt6.QtCore import QTimer

        QTimer.singleShot(500, callback)

    def finish_batch_sync(self):
        """Update buttons for batch sync completion."""
        app = self.window()
        self.progress_bar.setVisible(False)

        # Save batch log output to file if keep_log_records is enabled
        self._save_log_output_to_file(app, success=True, mode="batch")

        # Hide cancel and show go back button
        self.cancel_button.setVisible(False)
        self.go_back_button.setVisible(True)
        (
            self.go_back_button.clicked.disconnect()
            if hasattr(self.go_back_button, "clicked")
            and self.go_back_button.receivers(self.go_back_button.clicked) > 0
            else None
        )
        self.go_back_button.clicked.connect(app.restore_auto_sync_tab)

        # Show and connect the "New conversion" button
        self.new_conversion_button.setVisible(True)
        (
            self.new_conversion_button.clicked.disconnect()
            if hasattr(self.new_conversion_button, "clicked")
            and self.new_conversion_button.receivers(self.new_conversion_button.clicked)
            > 0
            else None
        )
        self.new_conversion_button.clicked.connect(lambda: self._reset_and_go_back(app))

        # Force scroll to bottom after buttons are shown
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        """Scroll to the bottom of the log text."""
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        self.scroll_button.hide()
        self._user_scrolled_up = False

    def _open_output_folder(self, output_path):
        """Open the folder containing the output file"""
        if output_path and os.path.exists(output_path):
            open_folder(output_path, self)
        else:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.warning(self, texts.ERROR, texts.FILE_DOES_NOT_EXIST)

    def _reset_and_go_back(self, app):
        """Reset inputs and go back to the automatic sync tab"""
        app.restore_auto_sync_tab()

        # Reset inputs based on the mode
        if app.batch_mode_enabled:
            # Clear batch tree view
            if hasattr(app, "batch_tree_view"):
                app.batch_tree_view.clear_all_items()
                # Show the batch input box instead of tree view
                app.update_auto_sync_ui_for_batch()
        else:
            # Reset normal mode inputs
            if hasattr(app, "video_ref_input"):
                app.video_ref_input.reset_to_default()
            if hasattr(app, "subtitle_input"):
                app.subtitle_input.reset_to_default()

    def _save_log_output_to_file(self, app, success, mode):
        """Save the log window output to a file if keep_log_records is enabled

        Args:
            app: The main application instance
            success: Whether the synchronization was successful
            mode: "normal" or "batch" to determine filename prefix
        """
        try:
            # Check if keep_log_records is enabled
            if not app.config.get(
                "keep_log_records", DEFAULT_OPTIONS["keep_log_records"]
            ):
                return

            # Create logs directory
            logs_dir = get_logs_directory()
            os.makedirs(logs_dir, exist_ok=True)

            # Generate filename with date, mode prefix, and status
            current_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            status = "success" if success else "failed"
            filename = f"{mode}_{status}_{current_date}.txt"
            log_file_path = os.path.join(logs_dir, filename)

            # Get the plain text content from the log window
            log_content = self.log_text.toPlainText()

            # Write to file
            with open(
                log_file_path, "w", encoding="utf-8", errors="replace"
            ) as log_file:
                log_file.write(f"AutoSubSync Log - {mode.title()} Mode\n")
                log_file.write(
                    f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
                log_file.write(
                    f"Status: {'Success' if success else 'Failed/Canceled'}\n"
                )
                log_file.write("=" * 50 + "\n\n")
                log_file.write(log_content)

            logger.info(f"Log output saved to: {log_file_path}")

        except Exception as e:
            logger.error(f"Failed to save log output to file: {e}")

    def reset_for_new_sync(self):
        """Reset UI for a new synchronization"""
        # Hide action buttons
        self.go_to_folder_button.setVisible(False)
        self.new_conversion_button.setVisible(False)
        # Hide go back and show cancel
        self.go_back_button.setVisible(False)
        self.cancel_button.setVisible(True)
        self.cancel_button.setText(texts.CANCEL)
        self.cancel_button.setEnabled(
            False
        )  # Disable cancel button initially until sync starts

        # Reset progress bar
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)

        # Reset signal handlers to default
        try:
            self.cancel_clicked.disconnect()
        except Exception:
            pass
        # Default behavior: restore auto sync tab
        app = self.window()
        self.cancel_clicked.connect(app.restore_auto_sync_tab)


class LogWindowHandler(logging.Handler):
    def __init__(self, log_window):
        super().__init__()
        self.log_window = log_window
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record):
        msg = self.format(record)
        color = bold = None
        if record.levelno >= logging.ERROR:
            color = COLORS["RED"]
            bold = True
        elif record.levelno >= logging.WARNING:
            color = COLORS["ORANGE"]
            bold = False
        self.log_window.signal_relay.append_message_signal.emit(
            msg, bool(bold), color, False, "\n"
        )
