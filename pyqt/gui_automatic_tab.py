"""
This module provides the automatic synchronization tab functionality for AutoSubSync.
It's designed to be imported and attached to the main application at runtime.

The module exports:
- attach_functions_to_autosubsync: Function to attach all tab functionality to the main class
- All the UI setup and functionality for the automatic synchronization tab
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, 
    QVBoxLayout, 
    QPushButton,
    QHBoxLayout,
    QSlider,
    QGroupBox,
    QInputDialog,
    QLineEdit,
    QSizePolicy,
    QLabel,
    QMessageBox
)
from PyQt6.QtCore import Qt
from constants import COLORS, FFSUBSYNC_VAD_OPTIONS, DEFAULT_OPTIONS
from utils import update_config, handle_save_location_dropdown, update_folder_label, shorten_path
# Import directly from gui_batch_mode for cleaner integration
import gui_batch_mode

logger = logging.getLogger(__name__)

def attach_functions_to_autosubsync(autosubsync_class):
    """Attach automatic tab functions to the autosubsync class"""
    autosubsync_class.setupAutoSyncTab = setup_auto_sync_tab
    autosubsync_class.validate_auto_sync_inputs = validate_auto_sync_inputs
    autosubsync_class.show_add_arguments_dialog = show_add_arguments_dialog
    autosubsync_class.show_auto_sync_inputs = show_auto_sync_inputs
    autosubsync_class.update_auto_sync_ui_for_batch = update_auto_sync_ui_for_batch
    autosubsync_class.update_sync_tool_options = update_sync_tool_options
    autosubsync_class.update_args_tooltip = update_args_tooltip
    autosubsync_class._create_slider = _create_slider
    autosubsync_class.OneStepSlider = OneStepSlider

class OneStepSlider(QSlider):
    """Enhanced QSlider that responds to single mouse wheel steps and keyboard navigation."""
    def wheelEvent(self, event):
        if self.orientation() == Qt.Orientation.Horizontal:
            self.setValue(self.value() + event.angleDelta().y() // 120)
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event):
        delta = {Qt.Key.Key_Left: -1, Qt.Key.Key_Down: -1, Qt.Key.Key_Right: 1, Qt.Key.Key_Up: 1}.get(
            event.key()
        )
        if delta:
            self.setValue(self.value() + delta)
        else:
            super().keyPressEvent(event)

def setup_auto_sync_tab(self):
    """Set up the Automatic Sync tab UI components"""
    c, l = self._container()
    self.auto_sync_input_layout = QVBoxLayout()
    self.auto_sync_input_layout.setSpacing(15)
    self.auto_sync_input_layout.setContentsMargins(0, 0, 0, 0)
    
    # Create the input boxes
    self.batch_input = self.InputBox(
        self,
        "Drag and drop files or folder here or click to browse",
        "Batch mode",
        input_type="batch",
    )
    
    self.video_ref_input = self.InputBox(
        self,
        "Drag and drop video/reference subtitle here or click to browse",
        "Video/Reference subtitle",
        input_type="video_or_subtitle",
    )
    
    self.subtitle_input = self.InputBox(
        self,
        "Drag and drop subtitle file here or click to browse",
        "Input Subtitle",
        input_type="subtitle",
    )
    
    # Simply add layout to container
    l.addLayout(self.auto_sync_input_layout, 1)
    self.show_auto_sync_inputs()
    controls = QVBoxLayout()
    controls.setContentsMargins(0, 0, 0, 0)
    controls.setSpacing(15)

    # Create a horizontal layout for the sync options group title and the + button
    self.sync_options_group = QGroupBox("Sync tool settings")

    # Create the + button for additional arguments
    self.btn_add_args = QPushButton("+", self)
    self.btn_add_args.setFixedSize(30, 30)
    self.update_args_tooltip()
    self.btn_add_args.clicked.connect(self.show_add_arguments_dialog)

    # Set the sync options group layout
    self.sync_options_layout = QVBoxLayout()
    self.sync_options_group.setLayout(self.sync_options_layout)
    controls.addWidget(self.sync_options_group)

    # Position the + button in the top right of the group box
    self.btn_add_args.setParent(self.sync_options_group)
    self.sync_options_group.resizeEvent = lambda event: self.btn_add_args.move(
        self.sync_options_group.width() - self.btn_add_args.width() - 10, 30
    )

    self.sync_tool_combo = self._dropdown(
        controls, "Sync tool:", ["ffsubsync", "alass"]
    )
    idx = self.sync_tool_combo.findText(self.config.get("sync_tool", DEFAULT_OPTIONS["sync_tool"]))
    if idx >= 0:
        self.sync_tool_combo.setCurrentIndex(idx)
    self.sync_tool_combo.currentTextChanged.connect(lambda text: update_config(self, "sync_tool", text))
    save_map = {
        "Save next to input subtitle": "save_next_to_input_subtitle",
        "Overwrite input subtitle": "overwrite_input_subtitle",
        "Save next to video": "save_next_to_video",
        "Save next to video with same filename": "save_next_to_video_with_same_filename",
        "Save to desktop": "save_to_desktop",
        "Select destination folder": "select_destination_folder",
    }
    save_items = list(save_map.keys())
    self.save_combo = self._dropdown(
        controls,
        "Save location:",
        save_items
    )
    # Add label to display selected folder
    self.selected_folder_label = QLabel("", self)
    self.selected_folder_label.setWordWrap(True)
    self.selected_folder_label.hide()  # Hide initially
    controls.addWidget(self.selected_folder_label)
    
    # Handle display vs actual value mapping
    saved_location = self.config.get("automatic_save_location", DEFAULT_OPTIONS["automatic_save_location"])
    # Reverse lookup to find display value
    display_value = next((k for k, v in save_map.items() if v == saved_location), save_items[0])
    
    idx = self.save_combo.findText(display_value)
    if idx >= 0:
        self.save_combo.setCurrentIndex(idx)
        
    self.save_combo.currentTextChanged.connect(
        lambda: handle_save_location_dropdown(
            self,
            self.save_combo,
            save_map,
            "automatic_save_location",
            "automatic_save_folder",
            self.selected_folder_label,
            DEFAULT_OPTIONS["automatic_save_location"],
        )
    )
    
    # Initialize folder label on startup
    if saved_location == "select_destination_folder":
        folder = self.config.get("automatic_save_folder", "")
        update_folder_label(self.selected_folder_label, folder)
    else:
        update_folder_label(self.selected_folder_label)
    
    btns = QHBoxLayout()
    self.btn_batch_mode = self._button("Batch mode", w=120)
    self.btn_batch_mode.clicked.connect(lambda: gui_batch_mode.toggle_batch_mode(self))
    btns.addWidget(self.btn_batch_mode)
    self.btn_sync = self._button("Start")
    self.btn_sync.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    btns.addWidget(self.btn_sync)
    # Add input validation for Start button
    self.btn_sync.clicked.connect(self.validate_auto_sync_inputs)
    controls.addLayout(btns)
    cw = QWidget()
    cw.setLayout(controls)
    cw.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    l.addWidget(cw)
    self.tab_widget.addTab(c, "Automatic Sync")
    self.sync_tool_combo.currentTextChanged.connect(self.update_sync_tool_options)
    self.update_sync_tool_options(self.sync_tool_combo.currentText())
    self.update_auto_sync_ui_for_batch() # Ensure correct UI for batch mode on startup

def validate_auto_sync_inputs(self):
    """Validate automatic sync inputs before processing"""
    if self.batch_mode_enabled:
        # Use the batch validation function from gui_batch_mode
        return gui_batch_mode.validate_batch_inputs(self)
    else:  # Normal mode validation
        missing = False
        if not self.video_ref_input.file_path:
            self.video_ref_input.show_error("Please select a video or reference subtitle.")
            missing = True
        if not self.subtitle_input.file_path:
            self.subtitle_input.show_error("Please select a subtitle file.")
            missing = True
        # Prevent using the same file for both inputs
        if (
            self.video_ref_input.file_path
            and self.subtitle_input.file_path
            and self.video_ref_input.file_path == self.subtitle_input.file_path
        ):
            logger.warning("Cannot use the same file for both inputs.")
            QMessageBox.warning(self, "Invalid Input", "Cannot use the same file for both inputs.")
            return False
        if missing:
            return False
        
        logger.info("Automatic sync input validation passed.")
        return True  # Indicate validation passed

def show_add_arguments_dialog(self):
    """Show dialog for additional arguments for the sync tool"""
    current_tool = self.sync_tool_combo.currentText()
    args_key = f"{current_tool}_arguments"
    current_args = self.config.get(args_key, "")

    args, ok = QInputDialog.getText(
        self,
        f"Additional arguments for {current_tool}",
        f"Enter additional arguments for {current_tool}:",
        QLineEdit.EchoMode.Normal,
        current_args
    )

    if ok:
        logger.info(f"Arguments set for {current_tool}: {args}")
        update_config(self, args_key, args)
        # Update the button color based on whether arguments exist
        self.btn_add_args.setStyleSheet(f"color: {COLORS['GREEN']};" if args else "")
        self.update_args_tooltip()

def show_auto_sync_inputs(self):
    """Update the automatic sync input UI based on current mode"""
    # Clear existing widgets from the layout first, but don't delete them
    # as they are member variables.
    self.clear_layout(self.auto_sync_input_layout)
    
    # Initialize batch mode UI elements if they don't exist
    if not hasattr(self, 'batch_buttons_widget'):
        gui_batch_mode.create_batch_interface(self)

    # Ensure all input elements are correctly parented to self (the main window)
    # This helps if they were previously removed from layouts.
    for widget in [self.batch_input, self.video_ref_input, self.subtitle_input, self.batch_tree_view, self.batch_buttons_widget]:
        if widget.parent() != self:
            widget.setParent(self)
        widget.hide()  # Hide all initially

    if self.batch_mode_enabled:
        if self.batch_tree_view.has_items():
            self.auto_sync_input_layout.addWidget(self.batch_buttons_widget)
            self.auto_sync_input_layout.addWidget(self.batch_tree_view, 1) 
            self.batch_buttons_widget.show()
            self.batch_tree_view.show()
            # Disconnect previous connections to avoid duplicates
            try:
                self.batch_tree_view.itemSelectionChanged.disconnect()
            except Exception:
                pass
            # Enable/disable buttons based on selection in tree view
            self.batch_tree_view.itemSelectionChanged.connect(lambda: gui_batch_mode.update_batch_buttons_state(self))
            gui_batch_mode.update_batch_buttons_state(self)  # Initial state
        else:
            self.auto_sync_input_layout.addWidget(self.batch_input, 1) 
            self.batch_input.show()
    else:  # Normal (non-batch) mode
        self.auto_sync_input_layout.addWidget(self.video_ref_input, 1)
        self.auto_sync_input_layout.addWidget(self.subtitle_input, 1)
        self.video_ref_input.show()
        self.subtitle_input.show()

def update_auto_sync_ui_for_batch(self):
    """Update UI for batch mode"""
    self.show_auto_sync_inputs()

def update_sync_tool_options(self, tool):
    """Update sync tool options based on selected tool"""
    self.clear_layout(self.sync_options_layout)
    
    # Check if there are arguments for the current tool and update button color
    args_key = f"{tool}_arguments"
    has_args = bool(self.config.get(args_key, ""))
    self.btn_add_args.setStyleSheet(f"color: {COLORS['GREEN']};" if has_args else "")
    self.update_args_tooltip()
    
    if tool == "ffsubsync":
        self.ffsubsync_dont_fix_framerate = self._checkbox("Don't fix framerate")
        self.ffsubsync_dont_fix_framerate.setChecked(self.config.get("ffsubsync_dont_fix_framerate", DEFAULT_OPTIONS["ffsubsync_dont_fix_framerate"]))
        self.ffsubsync_dont_fix_framerate.toggled.connect(lambda state: update_config(self, "ffsubsync_dont_fix_framerate", state))
        self.ffsubsync_use_golden_section = self._checkbox(
            "Use golden section search"
        )
        self.ffsubsync_use_golden_section.setChecked(self.config.get("ffsubsync_use_golden_section", DEFAULT_OPTIONS["ffsubsync_use_golden_section"]))
        self.ffsubsync_use_golden_section.toggled.connect(lambda state: update_config(self, "ffsubsync_use_golden_section", state))
        self.sync_options_layout.addWidget(self.ffsubsync_dont_fix_framerate)
        self.sync_options_layout.addWidget(self.ffsubsync_use_golden_section)
        vad_map = {"Default": "default"}
        vad_items = ["Default"] + FFSUBSYNC_VAD_OPTIONS
        self.ffsubsync_vad_combo = self._dropdown(
            self.sync_options_layout, "Voice activity detector:", vad_items
        )
        
        # Handle display vs actual value mapping
        saved_vad = self.config.get("ffsubsync_vad", DEFAULT_OPTIONS["ffsubsync_vad"])
        display_value = saved_vad if saved_vad in vad_items else "Default"
        
        idx = self.ffsubsync_vad_combo.findText(display_value)
        if idx >= 0:
            self.ffsubsync_vad_combo.setCurrentIndex(idx)
            
        # Map "Default" to "default" but keep others as is
        self.ffsubsync_vad_combo.currentTextChanged.connect(
            lambda text: update_config(self, "ffsubsync_vad", vad_map.get(text, text))
        )
    elif tool == "alass":
        self.alass_check_video_subtitles = self._checkbox(
            "Check video for subtitle streams"
        )
        self.alass_check_video_subtitles.setChecked(self.config.get("alass_check_video_subtitles", DEFAULT_OPTIONS["alass_check_video_subtitles"]))
        self.alass_check_video_subtitles.toggled.connect(lambda state: update_config(self, "alass_check_video_subtitles", state))
        self.alass_disable_fps_guessing = self._checkbox("Disable FPS guessing")
        self.alass_disable_fps_guessing.setChecked(self.config.get("alass_disable_fps_guessing", DEFAULT_OPTIONS["alass_disable_fps_guessing"]))
        self.alass_disable_fps_guessing.toggled.connect(lambda state: update_config(self, "alass_disable_fps_guessing", state))
        self.alass_disable_speed_optimization = self._checkbox(
            "Disable speed optimization"
        )
        self.alass_disable_speed_optimization.setChecked(self.config.get("alass_disable_speed_optimization", DEFAULT_OPTIONS["alass_disable_speed_optimization"]))
        self.alass_disable_speed_optimization.toggled.connect(lambda state: update_config(self, "alass_disable_speed_optimization", state))
        self.sync_options_layout.addWidget(self.alass_check_video_subtitles)
        self.sync_options_layout.addWidget(self.alass_disable_fps_guessing)
        self.sync_options_layout.addWidget(self.alass_disable_speed_optimization)
        self.alass_split_penalty, _ = self._create_slider(
            self.sync_options_layout,
            "Split penalty (Default: 7, Recommended: 5-20, No splits: -1)",
            -1,
            100,
            self.config.get("alass_split_penalty", DEFAULT_OPTIONS["alass_split_penalty"]),
        )
        self.alass_split_penalty.valueChanged.connect(lambda value: update_config(self, "alass_split_penalty", value))
    
    # Ensure the + button stays on top
    if hasattr(self, 'btn_add_args'):
        self.btn_add_args.raise_()

def update_args_tooltip(self):
    """Update tooltip for arguments button"""
    current_tool = self.sync_tool_combo.currentText() if hasattr(self, "sync_tool_combo") else ""
    args_key = f"{current_tool}_arguments"
    current_args = self.config.get(args_key, "")
    
    tooltip = "Additional arguments"
    if current_args:
        tooltip += f"\n⤷ {current_args}"
        
    self.btn_add_args.setToolTip(tooltip)

def _create_slider(self, parent_layout, title, minv, maxv, default, tick=5):
    """Create a slider with proper labels"""
    from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel
    
    lay = QVBoxLayout()
    lab_lay = QHBoxLayout()
    lab = QLabel(title, self)
    lab_lay.addWidget(lab)
    val_lab = QLabel(str(default), self)
    val_lab.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    lab_lay.addWidget(val_lab)
    lay.addLayout(lab_lay)
    
    # Use OneStepSlider for improved keyboard and mouse wheel navigation
    slider = OneStepSlider(Qt.Orientation.Horizontal, self)
        
    slider.setMinimum(minv)
    slider.setMaximum(maxv)
    slider.setValue(default)
    slider.setTickPosition(QSlider.TickPosition.TicksBelow)
    slider.setTickInterval(tick)
    slider.setMinimumHeight(30)
    slider.valueChanged.connect(lambda v: val_lab.setText(str(v)))
    lay.addWidget(slider)
    parent_layout.addLayout(lay)
    return slider, val_lab