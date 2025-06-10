"""
This module provides the manual subtitle synchronization tab functionality for AutoSubSync.
It's designed to be imported and attached to the main application at runtime.

The module exports:
- attach_functions_to_autosubsync: Function to attach all tab functionality to the main class
- All the UI setup and functionality for the manual synchronization tab
"""

import os
import logging
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QHBoxLayout,
    QMessageBox,
    QSizePolicy,
)
from PyQt6.QtGui import QIntValidator
from PyQt6.QtCore import Qt, QTimer
from constants import COLORS
from utils import handle_save_location_dropdown, update_folder_label

logger = logging.getLogger(__name__)

def attach_functions_to_autosubsync(autosubsync_class):
    """Attach manual tab functions to the autosubsync class"""
    autosubsync_class.setupManualSyncTab = setup_manual_sync_tab
    autosubsync_class.validate_manual_sync_inputs = validate_manual_sync_inputs
    autosubsync_class._update_shift_input_color = _update_shift_input_color
    autosubsync_class._increment_shift = _increment_shift
    autosubsync_class._decrement_shift = _decrement_shift
    autosubsync_class._shift_input_wheel_event = _shift_input_wheel_event
    autosubsync_class._handle_shift_input_events = _handle_shift_input_events
    autosubsync_class._is_child_of = _is_child_of

def setup_manual_sync_tab(self):
    """Setup the Manual Sync tab in the main window"""
    c, l = self._container()
    self.manual_input_box = self.InputBox(
        self,
        "Drag and drop subtitle file here or click to browse",
        "Input Subtitle",
        input_type="subtitle",
    )
    l.addWidget(self.manual_input_box, 1)
    opts = QVBoxLayout()
    opts.setContentsMargins(0, 0, 0, 0)
    opts.setSpacing(15)
    shift_input = QHBoxLayout()
    shift_label = QLabel("Shift subtitle (ms)", self)
    shift_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    shift_input.addWidget(shift_label)
    self.btn_shift_minus = self._button("-", h=35, w=35)
    shift_input.addWidget(self.btn_shift_minus)
    self.shift_input = QLineEdit(self)
    self.shift_input.setValidator(QIntValidator(-2147483647, 2147483647, self))
    self.shift_input.setText("0")
    self.shift_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.shift_input.setFixedHeight(35)
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
    manual_save_map = {
        "Save next to input subtitle": "save_next_to_input_subtitle",
        "Overwrite input subtitle": "overwrite_input_subtitle",
        "Save to desktop": "save_to_desktop",
        "Select destination folder": "select_destination_folder",
    }
    manual_save_items = list(manual_save_map.keys())
    self.manual_save_combo = self._dropdown(
        opts, "Save location:", manual_save_items
    )
    # Add label to display selected folder
    self.manual_selected_folder_label = QLabel("", self)
    self.manual_selected_folder_label.setWordWrap(True)
    self.manual_selected_folder_label.hide()  # Hide initially
    opts.addWidget(self.manual_selected_folder_label)
    
    # Handle display vs actual value mapping
    manual_saved_location = self.config.get("manual_save_location", "save_next_to_input_subtitle")
    # Reverse lookup to find display value
    manual_display_value = next((k for k, v in manual_save_map.items() if v == manual_saved_location), manual_save_items[0])
    
    idx = self.manual_save_combo.findText(manual_display_value)
    if idx >= 0:
        self.manual_save_combo.setCurrentIndex(idx)
        
    self.manual_save_combo.currentTextChanged.connect(
        lambda: handle_save_location_dropdown(
            self,
            self.manual_save_combo,
            manual_save_map,
            "manual_save_location",
            "manual_save_folder",
            self.manual_selected_folder_label,
            "save_next_to_input_subtitle"
        )
    )
    
    # Initialize folder label on startup
    if manual_saved_location == "select_destination_folder":
        folder = self.config.get("manual_save_folder", "")
        update_folder_label(self.manual_selected_folder_label, folder)
    else:
        update_folder_label(self.manual_selected_folder_label)
    
    self.btn_manual_sync = self._button("Start")
    opts.addWidget(self.btn_manual_sync)
    # Add input validation for Manual Sync Start button
    self.btn_manual_sync.clicked.connect(self.validate_manual_sync_inputs)
    ow = QWidget()
    ow.setLayout(opts)
    ow.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    l.addWidget(ow)
    self.tab_widget.addTab(c, "Manual Sync")
    
    # Connect tab change event to clear focus from shift_input
    self.tab_widget.currentChanged.connect(lambda: self.shift_input.clearFocus() if hasattr(self, 'shift_input') else None)
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
        logger.warning("No subtitle file selected for manual sync.")
        self.manual_input_box.show_error("Please select a subtitle file.")
        return False
    if self.shift_input.text() == "0" or not self.shift_input.text():
        logger.warning("Invalid shift value for manual sync.")
        QMessageBox.warning(
            self,
            "Invalid Shift",
            "Please enter a non-zero value.",
        )
        return False
    
    # Print manual sync information
    print("Mode: Manual")
    print(f"Input: {self.manual_input_box.file_path}")
    print(f"Shift: {self.shift_input.text()} ms")
    
    logger.info("Manual sync input validation passed.")
    return True  # Indicate validation passed

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
        if hasattr(self, 'shift_input') and self.shift_input.hasFocus():
            # Get the widget that was clicked
            clicked_widget = self.childAt(event.pos())
            # If clicked widget is not the shift_input or its child, unfocus shift_input
            if clicked_widget != self.shift_input and not self._is_child_of(clicked_widget, self.shift_input):
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