import platform
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QSizePolicy,
    QTabWidget,
    QLineEdit,
    QHBoxLayout,
    QCheckBox,
    QSlider,
    QGroupBox,
    QMenu,
    QAction,
    QMessageBox,
    QInputDialog,
    QFileDialog,
    QFileIconProvider,
)
from PyQt5.QtCore import Qt, QTimer, QUrl, QSize, QFileInfo, QIODevice, QBuffer
from PyQt5.QtGui import QIcon, QIntValidator, QDesktopServices, QDragEnterEvent, QDropEvent
import os, base64
from utils import *
from constants import *

# Import ctypes for Windows-specific taskbar icon
if platform.system() == "Windows":
    import ctypes

class StepOneSlider(QSlider):
    def wheelEvent(self, event):
        if self.orientation() == Qt.Horizontal:
            self.setValue(self.value() + event.angleDelta().y() // 120)
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event):
        delta = {Qt.Key_Left: -1, Qt.Key_Down: -1, Qt.Key_Right: 1, Qt.Key_Up: 1}.get(
            event.key()
        )
        if delta:
            self.setValue(self.value() + delta)
        else:
            super().keyPressEvent(event)


class InputBox(QLabel):
    # Define CSS styles as class constants
    _BASE = "border:2px dashed {}; border-radius:5px; padding:20px; background:{}; min-height:100px;"
    _HOVER = "background:{}; border-color:{};"
    STYLE_DEFAULT = _BASE.format(COLORS["GREY"], COLORS["BLUE_BACKGROUND"])
    STYLE_DEFAULT_HOVER = _HOVER.format(COLORS["BLUE_BACKGROUND_HOVER"], COLORS["BLUE"])
    STYLE_ACTIVE = _BASE.format(COLORS["GREEN"], COLORS["GREEN_BACKGROUND"])
    STYLE_ACTIVE_HOVER = _HOVER.format(
        COLORS["GREEN_BACKGROUND_HOVER"], COLORS["GREEN"]
    )
    STYLE_ERROR = f"{_BASE.format(COLORS['RED'], COLORS['RED_BACKGROUND'])} color:{COLORS['RED']};"
    STYLE_ERROR_HOVER = _HOVER.format(COLORS["RED_BACKGROUND_HOVER"], COLORS["RED"])

    def __init__(
        self,
        parent=None,
        text="Drag and drop your file here or click to browse.",
        label=None,
        input_type=None,
    ):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.setText(text)
        self.setObjectName("inputBox")
        self.setStyleSheet(
            f"QLabel#inputBox {{{self.STYLE_DEFAULT}}} QLabel#inputBox:hover {{{self.STYLE_DEFAULT_HOVER}}}"
        )
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCursor(Qt.PointingHandCursor)
        self.file_path = None
        self.input_type = input_type
        self.default_text = text
        
        # Add clear button
        self.clear_btn = QPushButton("✕", self)
        self.clear_btn.setFixedSize(25, 25)
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self.reset_to_default)
        self.clear_btn.hide()  # Initially hidden

        # Add Go to folder button
        self.goto_folder_btn = QPushButton("Go to folder", self)
        self.goto_folder_btn.setFixedHeight(28)
        self.goto_folder_btn.setCursor(Qt.PointingHandCursor)
        self.goto_folder_btn.clicked.connect(self.open_file_folder)
        self.goto_folder_btn.hide()
        self.goto_folder_btn.setStyleSheet("font-size: 12px; padding: 2px 10px;")
        
        if label:
            l = QLabel(label, self)
            l.setObjectName("boxLabel")
            l.setStyleSheet(
                f"QLabel#boxLabel {{ background: transparent; border: none; color: {COLORS['GREY']}; }}"
            )
            l.move(10, 8)
            l.show()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.browse_file()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if self.input_type == "subtitle" or self.input_type == "video_or_subtitle":
            files = [u.toLocalFile() for u in event.mimeData().urls()]
            if files:
                self.set_file(files[0])
        elif self.input_type == "batch":
            return  # Don't handle batch mode

    def browse_file(self):
        if self.input_type == "subtitle":
            file_filter = f"Subtitle Files (*{' *'.join(SUBTITLE_EXTENSIONS)})"
        elif self.input_type == "video_or_subtitle":
            file_filter = f"Video/Subtitle Files (*{' *'.join(VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS)})"
        else:
            return  # Don't handle batch mode
            
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File", "", file_filter)
        if file_path:
            self.set_file(file_path)

    def set_file(self, file_path):
        if not os.path.exists(file_path):
            self.show_error("File does not exist")
            return
            
        # Validate file type
        ext = os.path.splitext(file_path)[1].lower()
        if self.input_type == "subtitle" and ext not in SUBTITLE_EXTENSIONS:
            self.show_error("Invalid subtitle file")
            return
        elif self.input_type == "video_or_subtitle" and ext not in VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS:
            self.show_error("Invalid video or subtitle file")
            return
        
        self.file_path = file_path
        name = os.path.basename(file_path)
        size = os.path.getsize(file_path)
        
        # Get icon without resizing using custom provider
        provider = QFileIconProvider()
        qicon = provider.icon(QFileInfo(file_path))
        size_icon = QSize(32, 32)
        pixmap = qicon.pixmap(size_icon)
        
        # Convert to base64 PNG
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        pixmap.save(buffer, "PNG")
        img_data = base64.b64encode(buffer.data()).decode()
        
        # Update display
        self.setText(
            f'<img src="data:image/png;base64,{img_data}"><br><span style="display: inline-block; max-width: 100%; word-break: break-all;"><b>{name}</b></span><br>Size: {format_num(size)}'
        )
        self.setWordWrap(True)
        self.setStyleSheet(
            f"QLabel#inputBox {{{self.STYLE_ACTIVE}}} QLabel#inputBox:hover {{{self.STYLE_ACTIVE_HOVER}}}"
        )
        
        # Show and position the clear button in the top right corner
        self.clear_btn.show()
        self.clear_btn.move(self.width() - self.clear_btn.width() - 10, 10)
        # Show and position the Go to folder button in the bottom left
        self.goto_folder_btn.show()
        self.goto_folder_btn.move(self.width() - self.goto_folder_btn.width() - 10, self.height() - self.goto_folder_btn.height() - 10)

    def show_error(self, message):
        self.setText(message)
        self.setStyleSheet(
            f"QLabel#inputBox {{{self.STYLE_ERROR}}} QLabel#inputBox:hover {{{self.STYLE_ERROR_HOVER}}}"
        )
        # Only reset if file_path is still None after timeout
        file_path_at_error = self.file_path
        def maybe_reset():
            if self.file_path is None or self.file_path == file_path_at_error:
                self.reset_to_default()
        QTimer.singleShot(3000, maybe_reset)

    def reset_to_default(self):
        self.file_path = None
        self.setText(self.default_text)
        self.setStyleSheet(
            f"QLabel#inputBox {{{self.STYLE_DEFAULT}}} QLabel#inputBox:hover {{{self.STYLE_DEFAULT_HOVER}}}"
        )
        self.clear_btn.hide()
        self.goto_folder_btn.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'clear_btn') and self.clear_btn.isVisible():
            self.clear_btn.move(self.width() - self.clear_btn.width() - 10, 10)
        if hasattr(self, 'goto_folder_btn') and self.goto_folder_btn.isVisible():
            self.goto_folder_btn.move(self.width() - self.goto_folder_btn.width() - 10, self.height() - self.goto_folder_btn.height() - 10)

    def open_file_folder(self):
        if self.file_path and os.path.exists(self.file_path):
            folder = os.path.dirname(self.file_path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        else:
            QMessageBox.warning(
                self,
                "Error",
                "File does not exist.",
            )


class autosubsync(QWidget):
    COMBO_STYLE = "QComboBox { min-height: 20px; padding: 6px 12px; }"
    TAB_STYLE = f"""
        QTabWidget::pane {{ border: 0; outline: 0; top: 15px; }}
        QTabBar::tab {{ border: none; padding: 10px 20px; margin-right: 6px; background-color: {COLORS['GREY_BACKGROUND']}; }}
        QTabBar::tab:hover {{ background-color: {COLORS['GREY_BACKGROUND_HOVER']}; }}
        QTabBar::tab:selected {{ background-color: {COLORS['GREY_BACKGROUND_HOVER']}; border-bottom: 3px solid {COLORS['GREY']}; }}
        QTabBar::tab:!selected {{ color: {COLORS['GREY']}; }}
    """

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.batch_mode_enabled = self.config.get("batch_mode", False)
        icon_path = get_resource_path("autosubsync.assets", "icon.ico")
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
            if platform.system() == "Windows":
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "autosubsync"
                )
        # Check for updates at startup if enabled
        if self.config.get("check_updates_startup", True):
            QTimer.singleShot(1000, lambda: check_for_updates_startup(self))
        self.initUI()


    def initUI(self):

        self.setWindowTitle(f"{PROGRAM_NAME} v{VERSION}")
        screen = QApplication.primaryScreen().geometry()
        width, height = 500, 800
        self.setGeometry(
            (screen.width() - width) // 2,
            (screen.height() - height) // 2,
            width,
            height,
        )
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(15, 15, 15, 15)
        self.tab_widget = QTabWidget(self)
        self.tab_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tab_widget.setStyleSheet(self.TAB_STYLE)
        outer_layout.addWidget(self.tab_widget)
        self.settings_btn = QPushButton(self)
        self.settings_btn.setIcon(
            QIcon(get_resource_path("autosubsync.assets", "settings.png"))
        )
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.setFixedSize(36, 36)
        self.settings_btn.move(self.width() - 36 - 15, 15)
        
        # Create settings menu
        self.settings_menu = QMenu(self)

        # Add 'Open config directory' option at the top
        self.open_config_dir_action = QAction("Open config directory", self)
        self.open_config_dir_action.triggered.connect(lambda: open_config_directory(self))
        self.settings_menu.addAction(self.open_config_dir_action)

        # Add 'Open logs directory' option at the top
        self.open_logs_directory_action = QAction("Open logs directory", self)
        self.open_logs_directory_action.triggered.connect(lambda: open_logs_directory(self))
        self.settings_menu.addAction(self.open_logs_directory_action)

        # Add 'Clear logs directory' option
        self.clear_logs_directory_action = QAction("Clear all logs", self)
        self.clear_logs_directory_action.triggered.connect(lambda: clear_logs_directory(self))
        self.settings_menu.addAction(self.clear_logs_directory_action)

        self.settings_menu.addSeparator()

        self.remember_changes_action = QAction("Remember the changes", self)
        self.remember_changes_action.setCheckable(True)
        self.remember_changes_action.setChecked(self.config.get("remember_changes", True))
        self.remember_changes_action.triggered.connect(lambda checked: toggle_remember_changes(self, checked))
        self.settings_menu.addAction(self.remember_changes_action)

        # Add 'Check for updates at startup' option
        self.check_updates_action = QAction("Check for updates at startup", self)
        self.check_updates_action.setCheckable(True)
        self.check_updates_action.setChecked(self.config.get("check_updates_startup", True))
        self.check_updates_action.triggered.connect(lambda checked: update_config(self, "check_updates_startup", checked))
        self.settings_menu.addAction(self.check_updates_action)

        # Add separator and reset option
        self.reset_action = QAction("Reset to default settings", self)
        self.reset_action.triggered.connect(lambda: reset_to_defaults(self))
        self.settings_menu.addAction(self.reset_action)

        self.settings_menu.addSeparator()

        # Add separator and About option
        self.about_action = QAction("About", self)
        self.about_action.triggered.connect(lambda: show_about_dialog(self))
        self.settings_menu.addAction(self.about_action)

        # Connect button click to show menu instead of setting the menu directly
        self.settings_btn.clicked.connect(self.show_settings_menu)
        self.settings_btn.show()
        self.setupAutoSyncTab()
        self.setupManualSyncTab()
        self.setLayout(outer_layout)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "settings_btn"):
            self.settings_btn.move(self.width() - 36 - 15, 15)

    def _container(self):
        c = QWidget()
        c.setAutoFillBackground(True)
        l = QVBoxLayout(c)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(15)
        return c, l

    def _button(self, text, h=60, w=None, checkable=False):
        b = QPushButton(text, self)
        b.setFixedHeight(h)
        if w:
            b.setFixedWidth(w)
        b.setCheckable(checkable)
        return b

    def _checkbox(self, text):
        return QCheckBox(text, self)

    def _dropdown(self, parent_layout, label, items, style=None):
        if not style:
            style = self.COMBO_STYLE
        row = QHBoxLayout()
        lab = QLabel(label, self)
        lab.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        row.addWidget(lab)
        combo = QComboBox(self)
        combo.setStyleSheet(style)
        combo.addItems(items)
        combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row.addWidget(combo)
        parent_layout.addLayout(row)
        return combo

    def clear_layout(self, layout):
        """Clear all items from the layout without deleting persistent widgets"""
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
            elif item.layout():
                self.clear_layout(item.layout())

    def setupAutoSyncTab(self):
        c, l = self._container()
        self.auto_sync_input_layout = QVBoxLayout()
        self.auto_sync_input_layout.setSpacing(15)
        self.auto_sync_input_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create the input boxes
        self.batch_input = InputBox(
            self,
            "Drag and drop files or folder here or click to browse",
            "Batch mode",
            input_type="batch",
        )
        
        self.video_ref_input = InputBox(
            self,
            "Drag and drop video/reference subtitle here or click to browse",
            "Video/Reference subtitle",
            input_type="video_or_subtitle",
        )
        
        self.subtitle_input = InputBox(
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
        self.btn_add_args.setToolTip("Additional arguments")
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
        idx = self.sync_tool_combo.findText(self.config.get("sync_tool", "ffsubsync"))
        if idx >= 0:
            self.sync_tool_combo.setCurrentIndex(idx)
        self.sync_tool_combo.currentTextChanged.connect(lambda text: update_config(self, "sync_tool", text))
        save_map = {
            "Save next to input file": "save_next_to_input_file",
            "Save to custom location": "save_to_custom_location",
            "Replace original file": "replace_original_file"
        }
        save_items = list(save_map.keys())
        self.save_combo = self._dropdown(
            controls,
            "Save location:",
            save_items
        )
        
        # Handle display vs actual value mapping
        saved_location = self.config.get("save_location", "save_next_to_input_file")
        # Reverse lookup to find display value
        display_value = next((k for k, v in save_map.items() if v == saved_location), save_items[0])
        
        idx = self.save_combo.findText(display_value)
        if idx >= 0:
            self.save_combo.setCurrentIndex(idx)
            
        # Convert display text to storage value
        self.save_combo.currentTextChanged.connect(
            lambda text: update_config(self, "save_location", save_map.get(text, "save_next_to_input_file"))
        )
        btns = QHBoxLayout()
        self.btn_batch_mode = self._button("Batch mode", w=120)
        self.btn_batch_mode.clicked.connect(self.toggle_batch_mode)
        btns.addWidget(self.btn_batch_mode)
        self.btn_sync = self._button("Start")
        self.btn_sync.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btns.addWidget(self.btn_sync)
        # Add input validation for Start button
        self.btn_sync.clicked.connect(self.validate_auto_sync_inputs)
        controls.addLayout(btns)
        cw = QWidget()
        cw.setLayout(controls)
        cw.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        l.addWidget(cw)
        self.tab_widget.addTab(c, "Automatic Sync")
        self.sync_tool_combo.currentTextChanged.connect(self.update_sync_tool_options)
        self.update_sync_tool_options(self.sync_tool_combo.currentText())

    def validate_auto_sync_inputs(self):
        if self.batch_mode_enabled:
            if not self.batch_input.file_path:
                self.batch_input.show_error("Please select files or a folder.")
                return
        else:
            missing = False
            if not self.video_ref_input.file_path:
                self.video_ref_input.show_error("Please select a video or reference subtitle.")
                missing = True
            if not self.subtitle_input.file_path:
                self.subtitle_input.show_error("Please select a subtitle file.")
                missing = True
            if missing:
                return
        # ...proceed with sync if all inputs are valid...

    def show_add_arguments_dialog(self):
        """Show dialog for additional arguments for the current sync tool"""
        current_tool = self.sync_tool_combo.currentText()
        args_key = f"{current_tool}_arguments"
        current_args = self.config.get(args_key, "")

        args, ok = QInputDialog.getText(
            self,
            f"Additional arguments for {current_tool}",
            f"Enter additional arguments for {current_tool}:",
            QLineEdit.Normal,
            current_args
        )

        if ok:
            update_config(self, args_key, args)
            # Update the button color based on whether arguments exist
            self.btn_add_args.setStyleSheet(f"color: {COLORS['GREEN']};" if args else "")

    def show_auto_sync_inputs(self):
        self.clear_layout(self.auto_sync_input_layout)
        
        # Shorthand references to input boxes
        inputs = [self.batch_input, self.video_ref_input, self.subtitle_input]
        
        # Hide all and ensure correct parent
        for input_box in inputs:
            input_box.hide()
            input_box.setParent(self)
        
        # Show only the appropriate widgets based on mode
        if self.batch_mode_enabled:
            self.batch_input.show()
            self.auto_sync_input_layout.addWidget(self.batch_input, 1)
        else:
            self.video_ref_input.show()
            self.subtitle_input.show()
            self.auto_sync_input_layout.addWidget(self.video_ref_input, 1)
            self.auto_sync_input_layout.addWidget(self.subtitle_input, 1)

    def toggle_batch_mode(self):
        # Update mode and config
        self.batch_mode_enabled = not self.batch_mode_enabled
        update_config(self, "batch_mode", self.batch_mode_enabled)
        self.btn_batch_mode.setText(
            "Normal mode" if self.batch_mode_enabled else "Batch mode"
        )
        self.show_auto_sync_inputs()

    def setupManualSyncTab(self):
        c, l = self._container()
        self.manual_input_box = InputBox(
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
        shift_label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        shift_input.addWidget(shift_label)
        self.btn_shift_minus = self._button("-", h=35, w=35)
        shift_input.addWidget(self.btn_shift_minus)
        self.shift_input = QLineEdit(self)
        self.shift_input.setValidator(QIntValidator(-2147483647, 2147483647, self))
        self.shift_input.setText("0")
        self.shift_input.setAlignment(Qt.AlignCenter)
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
        manual_save_map = {
            "Save to desktop": "save_to_desktop",
            "Override input subtitle": "override_input_subtitle"
        }
        manual_save_items = list(manual_save_map.keys())
        self.manual_save_combo = self._dropdown(
            opts, "Save location:", manual_save_items
        )
        
        # Handle display vs actual value mapping
        manual_saved_location = self.config.get("manual_save_location", "save_to_desktop")
        # Reverse lookup to find display value
        manual_display_value = next((k for k, v in manual_save_map.items() if v == manual_saved_location), manual_save_items[0])
        
        idx = self.manual_save_combo.findText(manual_display_value)
        if idx >= 0:
            self.manual_save_combo.setCurrentIndex(idx)
            
        # Convert display text to storage value
        self.manual_save_combo.currentTextChanged.connect(
            lambda text: update_config(self, "manual_save_location", manual_save_map.get(text, "save_to_desktop"))
        )
        self.btn_manual_sync = self._button("Start")
        opts.addWidget(self.btn_manual_sync)
        # Add input validation for Manual Sync Start button
        self.btn_manual_sync.clicked.connect(self.validate_manual_sync_inputs)
        ow = QWidget()
        ow.setLayout(opts)
        ow.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        l.addWidget(ow)
        self.tab_widget.addTab(c, "Manual Sync")
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
        if not self.manual_input_box.file_path:
            self.manual_input_box.show_error("Please select a subtitle file.")
            return
        if self.shift_input.text() == "0" or not self.shift_input.text():
            QMessageBox.warning(
                self,
                "Invalid Shift",
                "Please enter a non-zero value.",
            )
            return
        # ...proceed with manual sync if input is valid...

    def _update_shift_input_color(self):
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
        try:
            val = int(self.shift_input.text())
        except ValueError:
            val = 0
        val += 50
        self.shift_input.setText(f"+{val}" if val > 0 else str(val))

    def _decrement_shift(self):
        try:
            val = int(self.shift_input.text())
        except ValueError:
            val = 0
        val -= 50
        self.shift_input.setText(f"+{val}" if val > 0 else str(val))

    def _create_slider(self, parent_layout, title, minv, maxv, default, tick=5):
        lay = QVBoxLayout()
        lab_lay = QHBoxLayout()
        lab = QLabel(title, self)
        lab_lay.addWidget(lab)
        val_lab = QLabel(str(default), self)
        val_lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lab_lay.addWidget(val_lab)
        lay.addLayout(lab_lay)
        slider = StepOneSlider(Qt.Horizontal, self)
        slider.setMinimum(minv)
        slider.setMaximum(maxv)
        slider.setValue(default)
        slider.setTickPosition(QSlider.TicksBelow)
        slider.setTickInterval(tick)
        slider.setMinimumHeight(30)
        slider.valueChanged.connect(lambda v: val_lab.setText(str(v)))
        lay.addWidget(slider)
        parent_layout.addLayout(lay)
        return slider, val_lab

    def update_sync_tool_options(self, tool):
        self.clear_layout(self.sync_options_layout)
        
        # Check if there are arguments for the current tool and update button color
        args_key = f"{tool}_arguments"
        has_args = bool(self.config.get(args_key, ""))
        self.btn_add_args.setStyleSheet(f"color: {COLORS['GREEN']};" if has_args else "")
        
        if tool == "ffsubsync":
            self.ffsubsync_dont_fix_framerate = self._checkbox("Don't fix framerate")
            self.ffsubsync_dont_fix_framerate.setChecked(self.config.get("ffsubsync_dont_fix_framerate", False))
            self.ffsubsync_dont_fix_framerate.toggled.connect(lambda state: update_config(self, "ffsubsync_dont_fix_framerate", state))
            self.ffsubsync_use_golden_section = self._checkbox(
                "Use golden section search"
            )
            self.ffsubsync_use_golden_section.setChecked(self.config.get("ffsubsync_use_golden_section", False))
            self.ffsubsync_use_golden_section.toggled.connect(lambda state: update_config(self, "ffsubsync_use_golden_section", state))
            self.sync_options_layout.addWidget(self.ffsubsync_dont_fix_framerate)
            self.sync_options_layout.addWidget(self.ffsubsync_use_golden_section)
            vad_map = {"Default": "default"}
            vad_items = ["Default"] + FFSUBSYNC_VAD_OPTIONS
            self.ffsubsync_vad_combo = self._dropdown(
                self.sync_options_layout, "Voice activity detector:", vad_items
            )
            
            # Handle display vs actual value mapping
            saved_vad = self.config.get("ffsubsync_vad", "default")
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
            self.alass_check_video_subtitles.setChecked(self.config.get("alass_check_video_subtitles", True))
            self.alass_check_video_subtitles.toggled.connect(lambda state: update_config(self, "alass_check_video_subtitles", state))
            self.alass_disable_fps_guessing = self._checkbox("Disable FPS guessing")
            self.alass_disable_fps_guessing.setChecked(self.config.get("alass_disable_fps_guessing", False))
            self.alass_disable_fps_guessing.toggled.connect(lambda state: update_config(self, "alass_disable_fps_guessing", state))
            self.alass_disable_speed_optim = self._checkbox(
                "Disable speed optimization"
            )
            self.alass_disable_speed_optim.setChecked(self.config.get("alass_disable_speed_optim", False))
            self.alass_disable_speed_optim.toggled.connect(lambda state: update_config(self, "alass_disable_speed_optim", state))
            self.sync_options_layout.addWidget(self.alass_check_video_subtitles)
            self.sync_options_layout.addWidget(self.alass_disable_fps_guessing)
            self.sync_options_layout.addWidget(self.alass_disable_speed_optim)
            self.alass_split_penalty, _ = self._create_slider(
                self.sync_options_layout,
                "Split penalty (Default: 7, Recommended: 5-20, No splits: -1)",
                -1,
                100,
                self.config.get("alass_split_penalty", 7),
            )
            self.alass_split_penalty.valueChanged.connect(lambda value: update_config(self, "alass_split_penalty", value))
        
        # Ensure the + button stays on top
        if hasattr(self, 'btn_add_args'):
            self.btn_add_args.raise_()

    def eventFilter(self, obj, event):
        if obj == self.shift_input:
            from PyQt5.QtCore import QEvent

            if event.type() == QEvent.KeyPress:
                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    if not self.shift_input.text().strip():
                        self.shift_input.setText("0")
                    self.shift_input.clearFocus()
                    return True
            elif event.type() == QEvent.FocusOut:
                if not self.shift_input.text().strip():
                    self.shift_input.setText("0")
                self.shift_input.clearFocus()
        return super().eventFilter(obj, event)

    def _shift_input_wheel_event(self, event):
        if event.angleDelta().y() > 0:
            self._increment_shift()
        else:
            self._decrement_shift()

    def show_settings_menu(self):
        # Show the menu at the right position below the button
        self.settings_menu.popup(self.settings_btn.mapToGlobal(
            self.settings_btn.rect().bottomLeft()))
