"""
This module provides the automatic synchronization tab functionality for AutoSubSync.
It's designed to be imported and attached to the main application at runtime.

The module exports:
- attach_functions_to_autosubsyncapp: Function to attach all tab functionality to the main class
- All the UI setup and functionality for the automatic synchronization tab
"""

import os
import logging
import texts
from gui_log_window import LogWindow
from sync_auto import start_sync_process
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
    QSpacerItem,
    QLabel,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from constants import COLORS, DEFAULT_OPTIONS, SYNC_TOOLS, AUTOMATIC_SAVE_MAP
from utils import (
    update_config,
    handle_save_location_dropdown,
    update_folder_label,
    show_tool_info_dialog,
)

# Import directly from gui_batch_mode for cleaner integration
import gui_batch_mode

logger = logging.getLogger(__name__)


def attach_functions_to_autosubsyncapp(autosubsyncapp_class):
    """Attach automatic tab functions to the autosubsyncapp class"""
    autosubsyncapp_class.setupAutoSyncTab = setup_auto_sync_tab
    autosubsyncapp_class.validate_auto_sync_inputs = validate_auto_sync_inputs
    autosubsyncapp_class.show_add_arguments_dialog = show_add_arguments_dialog
    autosubsyncapp_class.show_auto_sync_inputs = show_auto_sync_inputs
    autosubsyncapp_class.update_auto_sync_ui_for_batch = update_auto_sync_ui_for_batch
    autosubsyncapp_class.update_sync_tool_options = update_sync_tool_options
    autosubsyncapp_class.update_args_tooltip = update_args_tooltip
    autosubsyncapp_class._create_slider = _create_slider
    autosubsyncapp_class.OneStepSlider = OneStepSlider
    autosubsyncapp_class.show_log_window = show_log_window
    autosubsyncapp_class.restore_auto_sync_tab = restore_auto_sync_tab
    autosubsyncapp_class.show_log_window = show_log_window
    autosubsyncapp_class.show_tool_info_dialog = show_tool_info_dialog


class OneStepSlider(QSlider):
    """Enhanced QSlider that responds to single mouse wheel steps and keyboard navigation."""

    def wheelEvent(self, event):
        if self.orientation() == Qt.Orientation.Horizontal:
            self.setValue(self.value() + event.angleDelta().y() // 120)
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event):
        delta = {
            Qt.Key.Key_Left: -1,
            Qt.Key.Key_Down: -1,
            Qt.Key.Key_Right: 1,
            Qt.Key.Key_Up: 1,
        }.get(event.key())
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
        texts.DRAG_DROP_FILE,
        texts.BATCH_MODE,
        input_type="batch",
    )

    self.video_ref_input = self.InputBox(
        self,
        texts.DRAG_DROP_VIDEO_SUBTITLE_FILES,
        texts.VIDEO_OR_SUBTITLE_FILES_LABEL,
        input_type="video_or_subtitle",
    )

    self.subtitle_input = self.InputBox(
        self,
        texts.DRAG_DROP_SUBTITLE_OR_BROWSE,
        texts.INPUT_SUBTITLE_LABEL,
        input_type="subtitle",
    )

    # Simply add layout to container
    l.addLayout(self.auto_sync_input_layout, 1)
    self.show_auto_sync_inputs()
    controls = QVBoxLayout()
    controls.setContentsMargins(0, 0, 0, 0)
    controls.setSpacing(15)

    # Create a horizontal layout for the sync options group title and the + button
    self.sync_options_group = QGroupBox(texts.SYNC_TOOL_SETTINGS)

    # Create the + button for additional arguments
    self.btn_add_args = QPushButton("+", self)
    self.btn_add_args.setFixedSize(30, 30)
    self.update_args_tooltip()
    self.btn_add_args.clicked.connect(self.show_add_arguments_dialog)

    # Create the ? button for tool info
    self.btn_tool_info = QPushButton("?", self)
    self.btn_tool_info.setFixedSize(30, 30)
    self.btn_tool_info.setToolTip(texts.SHOW_TOOL_INFORMATION)
    self.btn_tool_info.clicked.connect(self.show_tool_info_dialog)

    # Set the sync options group layout
    self.sync_options_layout = QVBoxLayout()
    self.sync_options_group.setLayout(self.sync_options_layout)
    controls.addWidget(self.sync_options_group)

    # Position the + and ? buttons in the top right of the group box
    self.btn_add_args.setParent(self.sync_options_group)
    self.btn_tool_info.setParent(self.sync_options_group)

    def _move_buttons(event=None):
        # Place + to the left of ?
        x_info = self.sync_options_group.width() - self.btn_tool_info.width() - 10
        x_add = x_info - self.btn_add_args.width() - 5
        y = 30
        self.btn_add_args.move(x_add, y)
        self.btn_tool_info.move(x_info, y)
        # Ensure both buttons are on top
        self.btn_add_args.raise_()
        self.btn_tool_info.raise_()

    self.sync_options_group.resizeEvent = _move_buttons

    self.sync_tool_combo = self._dropdown(
        controls, texts.SYNC_TOOL_LABEL, list(SYNC_TOOLS.keys())
    )
    idx = self.sync_tool_combo.findText(
        self.config.get("sync_tool", DEFAULT_OPTIONS["sync_tool"])
    )
    if idx >= 0:
        self.sync_tool_combo.setCurrentIndex(idx)
    self.sync_tool_combo.currentTextChanged.connect(
        lambda text: update_config(self, "sync_tool", text)
    )
    save_items = list(AUTOMATIC_SAVE_MAP.values())  # Use values as display text
    self.save_combo = self._dropdown(controls, texts.SAVE_LOCATION_LABEL, save_items)
    # Add label to display selected folder
    self.selected_folder_label = QLabel("", self)
    self.selected_folder_label.setWordWrap(True)
    self.selected_folder_label.hide()  # Hide initially
    controls.addWidget(self.selected_folder_label)

    # Handle display vs actual value mapping
    saved_location = self.config.get(
        "automatic_save_location", DEFAULT_OPTIONS["automatic_save_location"]
    )
    # Look up display value from internal value
    display_value = AUTOMATIC_SAVE_MAP.get(saved_location, save_items[0])

    idx = self.save_combo.findText(display_value)
    if idx >= 0:
        self.save_combo.setCurrentIndex(idx)

    # Connect change handler with lambda to convert display text to internal value
    self.save_combo.currentTextChanged.connect(
        lambda text: handle_save_location_dropdown(
            self,
            self.save_combo,
            {v: k for k, v in AUTOMATIC_SAVE_MAP.items()},  # Invert mapping for lookup
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
    self.btn_batch_mode = self._button(texts.BATCH_MODE, w=120)
    self.btn_batch_mode.clicked.connect(lambda: gui_batch_mode.toggle_batch_mode(self))
    btns.addWidget(self.btn_batch_mode)
    self.btn_sync = self._button(texts.START)
    self.btn_sync.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    btns.addWidget(self.btn_sync)
    # Add input validation for Start button
    self.btn_sync.clicked.connect(self.validate_auto_sync_inputs)
    controls.addLayout(btns)
    cw = QWidget()
    cw.setLayout(controls)
    cw.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    l.addWidget(cw)
    # Set an object name for the tab so we can find it later
    c.setObjectName("auto_sync_tab")
    self.tab_widget.addTab(c, texts.AUTOMATIC_SYNC_TAB_LABEL)
    self.sync_tool_combo.currentTextChanged.connect(self.update_sync_tool_options)
    self.update_sync_tool_options(self.sync_tool_combo.currentText())
    self.update_auto_sync_ui_for_batch()  # Ensure correct UI for batch mode on startup


def validate_auto_sync_inputs(self):
    """Validate automatic sync inputs before processing"""
    if self.batch_mode_enabled:
        # Use the batch validation function from gui_batch_mode
        validation_result = gui_batch_mode.validate_batch_inputs(self)
        if validation_result:
            self.show_log_window()
            # Start the batch sync process
            start_sync_process(self)
        return validation_result
    else:  # Normal mode validation
        missing = False
        if not self.video_ref_input.file_path:
            self.video_ref_input.show_error(
                texts.PLEASE_SELECT_VIDEO_OR_REFERENCE_SUBTITLE
            )
            missing = True
        if not self.subtitle_input.file_path:
            self.subtitle_input.show_error(texts.PLEASE_SELECT_SUBTITLE_FILE)
            missing = True
        # Prevent using the same file for both inputs
        if (
            self.video_ref_input.file_path
            and self.subtitle_input.file_path
            and self.video_ref_input.file_path == self.subtitle_input.file_path
        ):
            logger.warning("Cannot use the same file for both inputs.")
            QMessageBox.warning(
                self,
                texts.INVALID_FILE_TITLE,
                texts.CANNOT_USE_SAME_FILE_FOR_BOTH_INPUTS,
            )
            return False
        # Check if files exist
        if self.video_ref_input.file_path and not os.path.exists(
            self.video_ref_input.file_path
        ):
            QMessageBox.warning(
                self,
                texts.FILE_NOT_FOUND_TITLE,
                texts.VIDEO_REFERENCE_FILE_DOES_NOT_EXIST,
            )
            return False
        if self.subtitle_input.file_path and not os.path.exists(
            self.subtitle_input.file_path
        ):
            QMessageBox.warning(
                self, texts.FILE_NOT_FOUND_TITLE, texts.SUBTITLE_FILE_DOES_NOT_EXIST
            )
            return False
        if missing:
            return False

        logger.info("Automatic sync input validation passed. Starting sync...")
        self.show_log_window()
        # Start the single file sync process
        start_sync_process(self)
        return True  # Indicate validation passed


def show_add_arguments_dialog(self):
    """Show dialog for additional arguments for the sync tool"""
    current_tool = self.sync_tool_combo.currentText()
    args_key = f"{current_tool}_arguments"
    current_args = self.config.get(args_key, "")

    args, ok = QInputDialog.getText(
        self,
        texts.ADDITIONAL_ARGUMENTS_TITLE.format(tool=current_tool),
        texts.ENTER_ADDITIONAL_ARGUMENTS_PROMPT.format(tool=current_tool),
        QLineEdit.EchoMode.Normal,
        current_args,
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
    if not hasattr(self, "batch_buttons_widget"):
        gui_batch_mode.create_batch_interface(self)

    # Ensure all input elements are correctly parented to self (the main window)
    # This helps if they were previously removed from layouts.
    for widget in [
        self.batch_input,
        self.video_ref_input,
        self.subtitle_input,
        self.batch_tree_view,
        self.batch_buttons_widget,
    ]:
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
            self.batch_tree_view.itemSelectionChanged.connect(
                lambda: gui_batch_mode.update_batch_buttons_state(self)
            )
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

    # Update button text based on current mode
    if hasattr(self, "btn_batch_mode"):
        if self.batch_mode_enabled:
            self.btn_batch_mode.setText(texts.NORMAL_MODE)
        else:
            self.btn_batch_mode.setText(texts.BATCH_MODE)


def update_sync_tool_options(self, tool):
    """Update sync tool options based on selected tool"""
    self.clear_layout(self.sync_options_layout)

    # Check if there are arguments for the current tool and update button color
    args_key = f"{tool}_arguments"
    has_args = bool(self.config.get(args_key, ""))
    self.btn_add_args.setStyleSheet(f"color: {COLORS['GREEN']};" if has_args else "")
    self.update_args_tooltip()

    # Update the group box title to include the tool description if available
    tool_info = SYNC_TOOLS.get(tool, {})
    description = tool_info.get("description", "")
    self.sync_options_group.setTitle(f"{texts.SYNC_TOOL_SETTINGS} - {tool}")

    # If the tool doesn't exist in SYNC_TOOLS, exit early
    if tool not in SYNC_TOOLS:
        return

    # Get the options for the selected tool
    tool_options = tool_info.get("options", {})

    # Track created widgets to avoid garbage collection
    self.tool_option_widgets = {}

    # Create UI elements for each option
    for option_name, option_data in tool_options.items():
        option_type = option_data.get("type")
        label = option_data.get("label", "")
        tooltip = option_data.get("tooltip", "")
        config_key = f"{tool}_{option_name}"
        default = option_data.get("default", DEFAULT_OPTIONS.get(config_key, None))

        if option_type == "checkbox":
            # Create checkbox
            checkbox = self._checkbox(label)
            argument = option_data.get("argument", "")
            tooltip_text = (
                f"{argument}: {tooltip}"
                if argument and tooltip
                else (argument if argument else tooltip)
            )
            checkbox.setToolTip(tooltip_text)
            checkbox.setChecked(self.config.get(config_key, default))
            checkbox.toggled.connect(
                lambda state, key=config_key: update_config(self, key, state)
            )
            self.sync_options_layout.addWidget(checkbox)
            self.tool_option_widgets[option_name] = checkbox

        elif option_type == "dropdown":
            values = option_data.get("values", [])
            labels = option_data.get("value_labels", {})

            dropdown = self._dropdown(
                self.sync_options_layout, label, [labels.get(v, v) for v in values]
            )
            argument = option_data.get("argument", "")
            tooltip_text = (
                f"{argument}: {tooltip}"
                if argument and tooltip
                else (argument if argument else tooltip)
            )
            dropdown.setToolTip(tooltip_text)

            saved = self.config.get(config_key, default)
            if (idx := dropdown.findText(labels.get(saved, saved))) >= 0:
                dropdown.setCurrentIndex(idx)

            dropdown.currentTextChanged.connect(
                lambda text: update_config(
                    self,
                    config_key,
                    next((v for v in values if labels.get(v, v) == text), text),
                )
            )
            self.tool_option_widgets[option_name] = dropdown

        elif option_type == "slider":
            # Create slider
            range_min, range_max = option_data.get("range", [0, 100])
            current_value = self.config.get(config_key, default)
            slider, val_label = self._create_slider(
                self.sync_options_layout, label, range_min, range_max, current_value
            )
            argument = option_data.get("argument", "")
            tooltip_text = (
                f"{argument}: {tooltip}"
                if argument and tooltip
                else (argument if argument else tooltip)
            )
            slider.setToolTip(tooltip_text)

            # Special handling for alass split_penalty slider
            if tool == "alass" and option_name == "split_penalty":

                def update_split_penalty_display(value):
                    val_label.setText("No splits" if value == -1 else str(value))
                    # Only update config if value changed
                    if self.config.get(config_key) != value:
                        update_config(self, config_key, value)

                # Set initial display
                update_split_penalty_display(current_value)
                slider.valueChanged.connect(update_split_penalty_display)
            else:
                slider.valueChanged.connect(
                    lambda value, key=config_key: update_config(self, key, value)
                )
            self.tool_option_widgets[option_name] = slider

        elif option_type == "spacer":
            value = option_data.get("value", 10)
            spacer = QSpacerItem(
                0, value, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
            )
            self.sync_options_layout.addItem(spacer)
            self.tool_option_widgets[option_name] = spacer

    # Ensure the + button stays on top
    if hasattr(self, "btn_add_args"):
        self.btn_add_args.raise_()


def update_args_tooltip(self):
    """Update tooltip for arguments button"""
    current_tool = (
        self.sync_tool_combo.currentText() if hasattr(self, "sync_tool_combo") else ""
    )
    args_key = f"{current_tool}_arguments"
    current_args = self.config.get(args_key, "")

    tooltip = texts.ADDITIONAL_ARGUMENTS
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


def show_log_window(self):
    """Show the log window for displaying sync progress."""
    # Create log window to display sync progress if it doesn't exist
    if not hasattr(self, "log_window"):
        self.log_window = LogWindow(self)
        # Connect cancel button to return to the automatic sync tab
        self.log_window.cancel_clicked.connect(self.restore_auto_sync_tab)

    # Store the current automatic tab widget before we replace it
    if not hasattr(self, "_stored_auto_tab_widget"):
        auto_tab_index = self.tab_widget.indexOf(
            self.tab_widget.findChild(QWidget, "auto_sync_tab")
        )
        if auto_tab_index >= 0:
            # Store the old widget for later restoration
            self._stored_auto_tab_widget = self.tab_widget.widget(auto_tab_index)
            self._stored_auto_tab_index = auto_tab_index
            # Remove the tab but don't delete the widget
            self.tab_widget.removeTab(auto_tab_index)
            self._stored_auto_tab_widget.setParent(None)
            # Insert the log window as a new tab at the same position
            self.tab_widget.insertTab(
                auto_tab_index, self.log_window, texts.SYNC_LOG_TAB_LABEL
            )
            self.tab_widget.setCurrentIndex(auto_tab_index)

    # Show the log window and print configuration
    self.log_window.clear()
    self.log_window.print_config(self)


def restore_auto_sync_tab(self):
    """Restore the automatic sync tab after the log window is closed."""
    if hasattr(self, "_stored_auto_tab_widget") and hasattr(
        self, "_stored_auto_tab_index"
    ):
        # First remove the log window tab
        log_tab_index = self.tab_widget.indexOf(self.log_window)
        if log_tab_index >= 0:
            self.tab_widget.removeTab(log_tab_index)

        # Re-insert the original auto sync tab
        self.tab_widget.insertTab(
            self._stored_auto_tab_index,
            self._stored_auto_tab_widget,
            texts.AUTOMATIC_SYNC_TAB_LABEL,
        )
        self.tab_widget.setCurrentIndex(self._stored_auto_tab_index)

        # Update input box button positions
        if hasattr(self, "batch_mode_enabled"):
            if self.batch_mode_enabled and hasattr(self, "batch_input"):
                # Force a resize event to reposition buttons
                if hasattr(self.batch_input, "resizeEvent"):
                    self.batch_input.resizeEvent(None)
            else:
                # Normal mode - update positions for both input boxes
                if hasattr(self, "video_ref_input") and hasattr(
                    self.video_ref_input, "resizeEvent"
                ):
                    self.video_ref_input.resizeEvent(None)
                if hasattr(self, "subtitle_input") and hasattr(
                    self.subtitle_input, "resizeEvent"
                ):
                    self.subtitle_input.resizeEvent(None)

        # Clear the stored references
        delattr(self, "_stored_auto_tab_widget")
        delattr(self, "_stored_auto_tab_index")
