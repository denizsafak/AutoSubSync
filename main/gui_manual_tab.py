"""
This module provides the manual subtitle synchronization tab functionality for AutoSubSync.
It's designed to be imported and attached to the main application at runtime.

The module exports:
- attach_functions_to_autosubsyncapp: Function to attach all tab functionality to the main class
- All the UI setup and functionality for the manual synchronization tab
"""

import os
import logging
import texts
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QHBoxLayout,
    QMessageBox,
    QSizePolicy,
    QCheckBox,
    QProgressBar,
)
from PyQt6.QtGui import QIntValidator
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from constants import COLORS, DEFAULT_OPTIONS, MANUAL_SAVE_MAP
from utils import (
    handle_save_location_dropdown,
    update_folder_label,
    update_config,
    open_folder,
)
from sync_manual import shift_subtitle, determine_manual_output_path

logger = logging.getLogger(__name__)


class ManualSyncWorker(QThread):
    """Worker thread for manual sync operations"""

    progress_update = pyqtSignal(int)  # Progress percentage
    finished = pyqtSignal(bool, str, str)  # success, result_file, message

    def __init__(self, subtitle_file, shift_ms, output_file):
        super().__init__()
        self.subtitle_file = subtitle_file
        self.shift_ms = shift_ms
        self.output_file = output_file

    def run(self):
        """Execute the subtitle shift operation"""
        try:
            # Simulate progress updates during the operation
            self.progress_update.emit(25)

            # Perform the actual shift operation
            result_file, success, message = shift_subtitle(
                self.subtitle_file, self.shift_ms, self.output_file
            )

            self.progress_update.emit(75)

            # Small delay to show progress completion
            self.msleep(200)
            self.progress_update.emit(100)

            # Emit the result
            self.finished.emit(success, result_file if success else "", message)

        except Exception as e:
            error_msg = texts.UNEXPECTED_ERROR_DURING_SYNC.format(error=str(e))
            logger.error(error_msg)
            self.finished.emit(False, "", error_msg)


def attach_functions_to_autosubsyncapp(autosubsyncapp_class):
    """Attach manual tab functions to the autosubsyncapp class"""
    autosubsyncapp_class.setupManualSyncTab = setup_manual_sync_tab
    autosubsyncapp_class.validate_manual_sync_inputs = validate_manual_sync_inputs
    autosubsyncapp_class._update_shift_input_color = _update_shift_input_color
    autosubsyncapp_class._increment_shift = _increment_shift
    autosubsyncapp_class._decrement_shift = _decrement_shift
    autosubsyncapp_class._shift_input_wheel_event = _shift_input_wheel_event
    autosubsyncapp_class._handle_shift_input_events = _handle_shift_input_events
    autosubsyncapp_class._is_child_of = _is_child_of
    autosubsyncapp_class._update_total_shifted_display = _update_total_shifted_display
    autosubsyncapp_class._update_prefix_checkbox_state = _update_prefix_checkbox_state
    autosubsyncapp_class._would_overwrite_input_file = _would_overwrite_input_file
    autosubsyncapp_class._on_settings_changed = _on_settings_changed
    autosubsyncapp_class._show_message = _show_message
    autosubsyncapp_class._start_manual_sync = _start_manual_sync
    autosubsyncapp_class._on_sync_finished = _on_sync_finished
    autosubsyncapp_class._on_message_clicked = _on_message_clicked


def setup_manual_sync_tab(self):
    """Setup the Manual Sync tab in the main window"""
    c, l = self._container()

    # Initialize session tracking for shifted files
    if not hasattr(self, "session_shifted_files"):
        self.session_shifted_files = (
            {}
        )  # Dictionary to track {file_path: total_shifted_ms}

    self.manual_input_box = self.InputBox(
        self,
        texts.DRAG_DROP_SUBTITLE_OR_BROWSE,
        texts.INPUT_SUBTITLE_LABEL,
        input_type="subtitle",
    )
    l.addWidget(self.manual_input_box, 1)
    opts = QVBoxLayout()
    opts.setContentsMargins(0, 0, 0, 0)
    opts.setSpacing(15)

    # Add millisecond prefix checkbox
    self.add_ms_prefix_checkbox = QCheckBox(texts.ADD_MS_PREFIX_TO_FILENAME, self)
    self.add_ms_prefix_checkbox.setChecked(
        self.config.get(
            "add_ms_prefix_to_filename", DEFAULT_OPTIONS["add_ms_prefix_to_filename"]
        )
    )
    self.add_ms_prefix_checkbox.toggled.connect(self._on_settings_changed)
    opts.addWidget(self.add_ms_prefix_checkbox)

    shift_input = QHBoxLayout()
    shift_label = QLabel(texts.SHIFT_SUBTITLE_LABEL, self)
    shift_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    shift_input.addWidget(shift_label)
    self.btn_shift_minus = self._button("-", h=35, w=35)
    shift_input.addWidget(self.btn_shift_minus)
    self.shift_input = QLineEdit(self)
    self.shift_input.setValidator(QIntValidator(-2147483647, 2147483647, self))
    self.shift_input.setText("0")
    self.shift_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.shift_input.setFixedHeight(35)
    self.shift_input.setToolTip(texts.SECOND_MS_TOOLTIP)
    shift_input.addWidget(self.shift_input)
    self.shift_input.textChanged.connect(self._update_shift_input_color)
    self.shift_input.installEventFilter(self)
    self.shift_input.focusInEvent = lambda event: (
        self.shift_input.clear() if self.shift_input.text() == "0" else None
    ) or QLineEdit.focusInEvent(self.shift_input, event)
    self.shift_input.wheelEvent = self._shift_input_wheel_event
    self.btn_shift_plus = self._button("+", h=35, w=35)
    shift_input.addWidget(self.btn_shift_plus)
    opts.addLayout(shift_input)

    # Install event filter on main window to catch global mouse clicks
    self.installEventFilter(self)
    manual_save_items = list(MANUAL_SAVE_MAP.values())  # Use values as display text
    self.manual_save_combo = self._dropdown(
        opts, texts.SAVE_LOCATION_LABEL, manual_save_items
    )
    # Add label to display selected folder
    self.manual_selected_folder_label = QLabel("", self)
    self.manual_selected_folder_label.setWordWrap(True)
    self.manual_selected_folder_label.hide()  # Hide initially
    opts.addWidget(self.manual_selected_folder_label)

    # Handle display vs actual value mapping
    manual_saved_location = self.config.get(
        "manual_save_location", DEFAULT_OPTIONS["manual_save_location"]
    )
    # Look up display value from internal value
    manual_display_value = MANUAL_SAVE_MAP.get(
        manual_saved_location, manual_save_items[0]
    )

    idx = self.manual_save_combo.findText(manual_display_value)
    if idx >= 0:
        self.manual_save_combo.setCurrentIndex(idx)

    # Connect change handler with lambda to convert display text to internal value
    self.manual_save_combo.currentTextChanged.connect(self._on_settings_changed)

    # Initialize folder label on startup
    if manual_saved_location == "select_destination_folder":
        folder = self.config.get("manual_save_folder", "")
        update_folder_label(self.manual_selected_folder_label, folder)
    else:
        update_folder_label(self.manual_selected_folder_label)

    # Initialize total shifted display based on current save location
    self._update_total_shifted_display()

    # Initialize prefix checkbox state based on current save location
    self._update_prefix_checkbox_state()

    self.btn_manual_sync = self._button(texts.START)
    opts.addWidget(self.btn_manual_sync)

    # Add progress bar (initially hidden)
    self.manual_progress_bar = QProgressBar(self)
    self.manual_progress_bar.setRange(0, 100)
    self.manual_progress_bar.setVisible(False)
    opts.addWidget(self.manual_progress_bar)

    # Add message label (initially hidden)
    self.manual_message_label = QLabel("", self)
    self.manual_message_label.setWordWrap(True)
    self.manual_message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.manual_message_label.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    self.manual_message_label.setVisible(False)
    self.manual_message_label.setStyleSheet(
        f"QLabel {{ padding: 10px; border-radius: 5px; }}"
    )
    self.manual_message_label.mousePressEvent = self._on_message_clicked
    opts.addWidget(self.manual_message_label)

    # Add input validation for Manual Sync Start button
    self.btn_manual_sync.clicked.connect(self.validate_manual_sync_inputs)
    ow = QWidget()
    ow.setLayout(opts)
    ow.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    l.addWidget(ow)
    self.tab_widget.addTab(c, texts.MANUAL_SYNC_TAB_LABEL)

    # Connect tab change event to clear focus from shift_input
    self.tab_widget.currentChanged.connect(
        lambda: self.shift_input.clearFocus() if hasattr(self, "shift_input") else None
    )
    self.btn_shift_plus.clicked.connect(self._increment_shift)
    self.btn_shift_minus.clicked.connect(self._decrement_shift)
    self._plus_timer = QTimer(self)
    self._plus_timer.setInterval(150)
    self._plus_timer.timeout.connect(self._increment_shift)
    self.btn_shift_plus.pressed.connect(self._plus_timer.start)
    self.btn_shift_plus.released.connect(self._plus_timer.stop)
    self._minus_timer = QTimer(self)
    self._minus_timer.setInterval(150)
    self._minus_timer.timeout.connect(self._decrement_shift)
    self.btn_shift_minus.pressed.connect(self._minus_timer.start)
    self.btn_shift_minus.released.connect(self._minus_timer.stop)


def validate_manual_sync_inputs(self):
    """Validate manual sync inputs before processing"""
    if not self.manual_input_box.file_path:
        self.manual_input_box.show_error(texts.PLEASE_SELECT_SUBTITLE_FILE)
        return False
    if self.shift_input.text() == "0" or not self.shift_input.text():
        logger.warning("Invalid shift value for manual sync.")
        self._show_message(texts.PLEASE_ENTER_NON_ZERO_VALUE, "error")
        return False

    logger.info("Manual sync input validation passed. Starting shift...")

    # Get shift value
    try:
        shift_ms = int(self.shift_input.text())
    except ValueError:
        shift_ms = 0

    if shift_ms == 0:
        self._show_message(texts.PLEASE_ENTER_NON_ZERO_VALUE, "error")
        return False

    # Determine output file location using the new function
    save_location = self.config.get(
        "manual_save_location", DEFAULT_OPTIONS["manual_save_location"]
    )

    # Validate destination folder if needed
    if save_location == "select_destination_folder":
        folder = self.config.get("manual_save_folder", "")
        if not folder:
            self._show_message(
                texts.PLEASE_SELECT_DESTINATION_FOLDER,
                "error",
            )
            return False
        if not os.path.exists(folder):
            self._show_message(
                texts.SELECTED_DESTINATION_FOLDER_NOT_EXIST.format(folder=folder),
                "error",
            )
            return False

    # Use the new output path determination function
    add_prefix = self.add_ms_prefix_checkbox.isChecked()
    output_file = determine_manual_output_path(
        self, self.manual_input_box.file_path, shift_ms, add_prefix
    )

    # Check if output file already exists and warn user (except for overwrite mode)
    if save_location != "overwrite_input_subtitle" and os.path.exists(output_file):
        reply = QMessageBox.question(
            self,
            texts.FILE_ALREADY_EXISTS_TITLE,
            texts.FILE_ALREADY_EXISTS_MESSAGE.format(
                filename=os.path.basename(output_file)
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.No:
            return False

    # Start the threaded operation
    self._start_manual_sync(shift_ms, output_file)
    return True


def _show_message(self, message, msg_type="info"):
    """Show message in the message label with appropriate styling"""
    self.manual_message_label.setText(message)
    # Store the message type for click handling
    self.manual_message_label.message_type = msg_type

    if msg_type == "error":
        self.manual_message_label.setStyleSheet(
            f"QLabel {{ background: {COLORS['RED_BACKGROUND']}; color: {COLORS['RED']}; padding: 10px; border-radius: 5px; border: 1px solid {COLORS['RED']}; }}"
        )
        self.manual_message_label.setCursor(Qt.CursorShape.ArrowCursor)
    elif msg_type == "success":
        self.manual_message_label.setStyleSheet(
            f"QLabel {{ background: {COLORS['GREEN_BACKGROUND']}; color: {COLORS['GREEN']}; padding: 10px; border-radius: 5px; border: 1px solid {COLORS['GREEN']}; }}"
        )
        self.manual_message_label.setCursor(Qt.CursorShape.PointingHandCursor)

    # Calculate the required height for the text
    self.manual_message_label.setVisible(True)

    # Force the widget to calculate its height based on content
    font_metrics = self.manual_message_label.fontMetrics()
    text_rect = font_metrics.boundingRect(
        0,
        0,
        self.manual_message_label.width()
        - 22,  # Account for padding (10px * 2) + border (1px * 2)
        0,
        Qt.TextFlag.TextWordWrap,
        message,
    )

    # Set minimum height to ensure all text is visible (add padding and border)
    required_height = text_rect.height() + 22  # 20px padding + 2px border
    self.manual_message_label.setMinimumHeight(required_height)

    # Update the layout
    self.manual_message_label.updateGeometry()


def _start_manual_sync(self, shift_ms, output_file):
    """Start the manual sync operation in a worker thread"""
    # Disable the start button
    self.btn_manual_sync.setEnabled(False)
    self.btn_manual_sync.setText(texts.PROCESSING)

    # Hide any previous messages and show progress bar
    self.manual_message_label.setVisible(False)
    self.manual_progress_bar.setValue(0)
    self.manual_progress_bar.setVisible(True)

    # Create and start worker thread
    self.sync_worker = ManualSyncWorker(
        self.manual_input_box.file_path, shift_ms, output_file
    )

    # Connect signals
    self.sync_worker.progress_update.connect(self.manual_progress_bar.setValue)
    self.sync_worker.finished.connect(self._on_sync_finished)

    # Start the worker
    self.sync_worker.start()


def _on_sync_finished(self, success, result_file, message):
    """Handle completion of sync operation"""
    # Hide progress bar and re-enable button
    self.manual_progress_bar.setVisible(False)
    self.btn_manual_sync.setEnabled(True)
    self.btn_manual_sync.setText(texts.START)

    if success and result_file:
        # Determine if this is actually an overwrite operation by checking the final paths
        input_path = os.path.abspath(self.manual_input_box.file_path)
        output_path = os.path.abspath(result_file)
        is_actual_overwrite = input_path == output_path

        # Update total shifted amount only if actually overwriting the same file
        if is_actual_overwrite and hasattr(self.manual_input_box, "total_shifted_ms"):
            # Get the shift amount from the worker
            shift_ms = self.sync_worker.shift_ms

            # Update the tracked total shifted amount
            if self.manual_input_box.file_path not in self.session_shifted_files:
                self.session_shifted_files[self.manual_input_box.file_path] = 0

            # Add the new shift to the total
            self.session_shifted_files[self.manual_input_box.file_path] += shift_ms
            # Update the display value
            self.manual_input_box.total_shifted_ms = self.session_shifted_files[
                self.manual_input_box.file_path
            ]
            # Update the display
            self._update_total_shifted_display()

            # Log that we tracked an overwrite
            logger.info(
                f"Tracked shift of {shift_ms}ms for {self.manual_input_box.file_path}, new total: {self.manual_input_box.total_shifted_ms}ms"
            )

        self._show_message(message, "success")
        # Store the result file path for click handling
        self.manual_message_label.result_file_path = result_file
    else:
        self._show_message(
            texts.FAILED_TO_SHIFT_SUBTITLE.format(message=message), "error"
        )
        logger.error(f"Manual sync failed: {message}")

    # Clean up worker
    self.sync_worker = None


def _update_shift_input_color(self):
    """Update the color of the shift input based on its value"""
    try:
        val = int(self.shift_input.text())
    except ValueError:
        val = 0
    text = self.shift_input.text()
    if val > 0 and not text.startswith("+"):
        self.shift_input.blockSignals(True)
        self.shift_input.setText(f"+{val}")
        self.shift_input.blockSignals(False)
    if val > 0:
        self.shift_input.setStyleSheet(f"QLineEdit {{ color: {COLORS['GREEN']}; }}")
    elif val < 0:
        self.shift_input.setStyleSheet(f"QLineEdit {{ color: {COLORS['RED']}; }}")
    else:
        self.shift_input.setStyleSheet("")


def _increment_shift(self):
    """Increment the shift value by 50ms"""
    try:
        val = int(self.shift_input.text())
    except ValueError:
        val = 0
    val += 50
    self.shift_input.setText(f"+{val}" if val > 0 else str(val))


def _decrement_shift(self):
    """Decrement the shift value by 50ms"""
    try:
        val = int(self.shift_input.text())
    except ValueError:
        val = 0
    val -= 50
    self.shift_input.setText(f"+{val}" if val > 0 else str(val))


def _shift_input_wheel_event(self, event):
    """Handle mouse wheel events on the shift input"""
    if event.angleDelta().y() > 0:
        self._increment_shift()
    else:
        self._decrement_shift()


def _handle_shift_input_events(self, obj, event):
    """Handle keyboard events for shift input field"""
    from PyQt6.QtCore import QEvent

    if obj == self.shift_input:
        if event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if not self.shift_input.text().strip():
                    self.shift_input.setText("0")
                self.shift_input.clearFocus()
                return True
        elif event.type() == QEvent.Type.FocusOut:
            if not self.shift_input.text().strip():
                self.shift_input.setText("0")
    elif event.type() == QEvent.Type.MouseButtonPress:
        # Check if click is outside shift_input to unfocus it
        if hasattr(self, "shift_input") and self.shift_input.hasFocus():
            # Get the widget that was clicked
            clicked_widget = self.childAt(event.pos())
            # If clicked widget is not the shift_input or its child, unfocus shift_input
            if clicked_widget != self.shift_input and not self._is_child_of(
                clicked_widget, self.shift_input
            ):
                self.shift_input.clearFocus()
    return False  # Let other events pass through


def _is_child_of(self, widget, parent):
    """Check if widget is a child of parent widget"""
    if not widget or not parent:
        return False
    current = widget
    while current:
        if current == parent:
            return True
        current = current.parent()
    return False


def _update_total_shifted_display(self):
    """Update the total shifted label visibility - optimized for performance"""
    if (
        not hasattr(self, "manual_input_box")
        or not hasattr(self.manual_input_box, "total_shifted_label")
        or not self.manual_input_box.file_path
    ):
        return

    # Quick check: if save location is explicit overwrite, we know the result
    save_location = self.config.get(
        "manual_save_location", DEFAULT_OPTIONS["manual_save_location"]
    )

    # Fast path for explicit overwrite mode
    will_overwrite = save_location == "overwrite_input_subtitle"

    # Only do expensive path calculation if not in explicit overwrite mode
    if not will_overwrite:
        add_prefix = (
            self.add_ms_prefix_checkbox.isChecked()
            if hasattr(self, "add_ms_prefix_checkbox")
            else True
        )
        if add_prefix:
            # If prefix is enabled, it will definitely not overwrite (creates new filename)
            will_overwrite = False
        else:
            # No prefix - need to calculate full path to be sure
            output_file = determine_manual_output_path(
                self, self.manual_input_box.file_path, 0, add_prefix
            )
            will_overwrite = os.path.abspath(
                self.manual_input_box.file_path
            ) == os.path.abspath(output_file)

    # Show/hide label based on whether it would overwrite
    if will_overwrite and hasattr(self, "session_shifted_files"):
        total_ms = self.session_shifted_files.get(self.manual_input_box.file_path, 0)
        if total_ms != 0:
            text = texts.TOTAL_SHIFTED_LABEL.format(total_ms=total_ms)
            self.manual_input_box.total_shifted_label.setText(text)
            self.manual_input_box.total_shifted_label.adjustSize()
            self.manual_input_box.total_shifted_label.show()
            self.manual_input_box.total_shifted_label.move(
                10,
                self.manual_input_box.height()
                - self.manual_input_box.total_shifted_label.height()
                - 10,
            )
            return

    # Hide in all other cases
    self.manual_input_box.total_shifted_label.hide()


def _update_prefix_checkbox_state(self):
    """Update the prefix checkbox enabled/disabled state based on save location"""
    if not hasattr(self, "add_ms_prefix_checkbox"):
        return

    save_location = self.config.get(
        "manual_save_location", DEFAULT_OPTIONS["manual_save_location"]
    )

    if save_location == "overwrite_input_subtitle":
        # Disable checkbox when explicitly overwriting (prefix is not relevant)
        self.add_ms_prefix_checkbox.setEnabled(False)
        self.add_ms_prefix_checkbox.setToolTip(
            texts.PREFIX_NOT_APPLICABLE_WHEN_OVERWRITING
        )
    else:
        # Enable checkbox for other save modes
        self.add_ms_prefix_checkbox.setEnabled(True)
        self.add_ms_prefix_checkbox.setToolTip("")


def _would_overwrite_input_file(self, shift_ms=0):
    """Check if the current settings would result in overwriting the input file"""
    if not hasattr(self, "manual_input_box") or not self.manual_input_box.file_path:
        return False

    # Get the settings that affect output path
    add_prefix = (
        self.add_ms_prefix_checkbox.isChecked()
        if hasattr(self, "add_ms_prefix_checkbox")
        else True
    )

    # Determine what the output path would be
    output_file = determine_manual_output_path(
        self, self.manual_input_box.file_path, shift_ms, add_prefix
    )

    # Compare absolute paths
    input_path = os.path.abspath(self.manual_input_box.file_path)
    output_path = os.path.abspath(output_file)

    return input_path == output_path


def _on_settings_changed(self, value=None):
    """Handle any setting change that affects output path or display"""
    # Handle different types of changes
    if hasattr(self, "manual_save_combo") and self.sender() == self.manual_save_combo:
        # Save location dropdown changed
        handle_save_location_dropdown(
            self,
            self.manual_save_combo,
            {v: k for k, v in MANUAL_SAVE_MAP.items()},
            "manual_save_location",
            "manual_save_folder",
            self.manual_selected_folder_label,
            DEFAULT_OPTIONS["manual_save_location"],
        )
        self._update_prefix_checkbox_state()
    elif (
        hasattr(self, "add_ms_prefix_checkbox")
        and self.sender() == self.add_ms_prefix_checkbox
    ):
        # Prefix checkbox changed
        update_config(self, "add_ms_prefix_to_filename", value)

    # Always update total shifted display after any change
    self._update_total_shifted_display()


def _on_message_clicked(self, event):
    """Handle clicking on the message label"""
    # Only handle left mouse button clicks
    if event.button() != Qt.MouseButton.LeftButton:
        return

    # Only handle success messages that have a result file path
    if (
        hasattr(self.manual_message_label, "message_type")
        and self.manual_message_label.message_type == "success"
        and hasattr(self.manual_message_label, "result_file_path")
    ):

        result_file = self.manual_message_label.result_file_path

        # Check if file exists
        if os.path.exists(result_file):
            # Open containing folder using the new open_folder function
            open_folder(result_file, self)
        else:
            # Show error dialog if file not found
            QMessageBox.warning(
                self,
                texts.FILE_NOT_FOUND_TITLE,
                texts.FILE_NOT_FOUND_MESSAGE.format(
                    filename=os.path.basename(result_file)
                ),
            )
            logger.warning(f"Result file not found: {result_file}")
