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
)
from PyQt5.QtCore import Qt, QTimer, QProcess, QUrl
from PyQt5.QtGui import QIcon, QIntValidator, QDesktopServices
import os, sys
from utils import get_resource_path, load_config, save_config, get_user_config_path, get_logs_directory
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
        if label:
            l = QLabel(label, self)
            l.setObjectName("boxLabel")
            l.setStyleSheet(
                f"QLabel#boxLabel {{ background: transparent; border: none; color: {COLORS['GREY']}; }}"
            )
            l.move(10, 8)
            l.show()


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
            QTimer.singleShot(1000, self.check_for_updates_startup)
        self.initUI()

    def update_config(self, key, value):
        self.config[key] = value
        # Only save settings if remember_changes is enabled (default: True)
        if self.config.get("remember_changes", True):
            save_config(self.config)

    def toggle_remember_changes(self, checked):
        # Always save this setting to the config file, regardless of the current remember_changes value
        self.config["remember_changes"] = checked
        save_config(self.config)

    def reset_to_defaults(self):
        # Show confirmation dialog
        reply = QMessageBox.question(
            self, 
            "Reset Settings", 
            "Are you sure you want to reset settings to default?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            config_path = get_user_config_path()
            try:
                # Remove the config file if it exists
                if os.path.exists(config_path):
                    os.remove(config_path)
                
                # Restart the application
                QProcess.startDetached(sys.executable, sys.argv)
                QApplication.quit()
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to reset settings: {str(e)}"
                )

    def open_config_directory(self):
        """Open the config directory in the system file manager"""

        try:
            config_path = get_user_config_path()
            # Open the directory containing the config file
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(config_path)))
        except Exception as e:
            QMessageBox.critical(
                self, "Config Error", f"Could not open config location:\n{e}"
            )

    def open_logs_directory(self):
        """Open the logs directory used by the program."""
        try:
            # Open the directory in file explorer
            QDesktopServices.openUrl(QUrl.fromLocalFile(get_logs_directory()))
        except Exception as e:
            QMessageBox.critical(
                self, "logs directory Error", f"Could not open logs directory:\n{e}"
            )

    def clear_logs_directory(self):
        """Delete logs directory after user confirmation."""
        try:
            logs_dir = get_logs_directory()
            
            # Count files in the directory
            total_files = len([f for f in os.listdir(logs_dir) if os.path.isfile(os.path.join(logs_dir, f))])
            
            if total_files == 0:
                QMessageBox.information(
                    self,
                    "Logs Directory",
                    "Logs directory is empty."
                )
                return
            
            # Ask for confirmation with file count
            reply = QMessageBox.question(
                self,
                "Delete logs directory",
                f"Are you sure you want to delete logs directory with {total_files} files?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                import shutil
                # Remove the entire directory
                shutil.rmtree(logs_dir)

                QMessageBox.information(
                    self,
                    "Logs Directory Cleared",
                    f"Logs directory has been successfully deleted."
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to clear logs directory: {str(e)}"
            )

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
        self.open_config_dir_action.triggered.connect(self.open_config_directory)
        self.settings_menu.addAction(self.open_config_dir_action)

        # Add 'Open logs directory' option at the top
        self.open_logs_directory_action = QAction("Open logs directory", self)
        self.open_logs_directory_action.triggered.connect(self.open_logs_directory)
        self.settings_menu.addAction(self.open_logs_directory_action)

        # Add 'Clear logs directory' option
        self.clear_logs_directory_action = QAction("Clear all logs", self)
        self.clear_logs_directory_action.triggered.connect(self.clear_logs_directory)
        self.settings_menu.addAction(self.clear_logs_directory_action)

        self.settings_menu.addSeparator()

        self.remember_changes_action = QAction("Remember the changes", self)
        self.remember_changes_action.setCheckable(True)
        self.remember_changes_action.setChecked(self.config.get("remember_changes", True))
        self.remember_changes_action.triggered.connect(self.toggle_remember_changes)
        self.settings_menu.addAction(self.remember_changes_action)

        # Add 'Check for updates at startup' option
        self.check_updates_action = QAction("Check for updates at startup", self)
        self.check_updates_action.setCheckable(True)
        self.check_updates_action.setChecked(self.config.get("check_updates_startup", True))
        self.check_updates_action.triggered.connect(lambda checked: self.update_config("check_updates_startup", checked))
        self.settings_menu.addAction(self.check_updates_action)

        # Add separator and reset option
        self.reset_action = QAction("Reset to default settings", self)
        self.reset_action.triggered.connect(self.reset_to_defaults)
        self.settings_menu.addAction(self.reset_action)

        self.settings_menu.addSeparator()

        # Add separator and About option
        self.about_action = QAction("About", self)
        self.about_action.triggered.connect(self.show_about_dialog)
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
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

    def setupAutoSyncTab(self):
        c, l = self._container()
        self.auto_sync_input_layout = QVBoxLayout()
        self.auto_sync_input_layout.setSpacing(15)
        self.auto_sync_input_layout.setContentsMargins(0, 0, 0, 0)
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
        self.sync_tool_combo.currentTextChanged.connect(lambda text: (self.update_config("sync_tool", text), self.update_sync_tool_options(text)))
        self.save_combo = self._dropdown(
            controls,
            "Save location:",
            [
                "Save next to input file",
                "Save to custom location",
                "Replace original file",
            ],
        )
        idx = self.save_combo.findText(self.config.get("save_location", "Save next to input file"))
        if idx >= 0:
            self.save_combo.setCurrentIndex(idx)
        self.save_combo.currentTextChanged.connect(lambda text: self.update_config("save_location", text))
        btns = QHBoxLayout()
        self.btn_batch_mode = self._button("Batch mode", w=120)
        self.btn_batch_mode.clicked.connect(self.toggle_batch_mode)
        btns.addWidget(self.btn_batch_mode)
        self.btn_sync = self._button("Start")
        self.btn_sync.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btns.addWidget(self.btn_sync)
        controls.addLayout(btns)
        cw = QWidget()
        cw.setLayout(controls)
        cw.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        l.addWidget(cw)
        self.tab_widget.addTab(c, "Automatic Sync")
        self.sync_tool_combo.currentTextChanged.connect(self.update_sync_tool_options)
        self.update_sync_tool_options(self.sync_tool_combo.currentText())

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
            self.update_config(args_key, args)
            # Update the button color based on whether arguments exist
            self.btn_add_args.setStyleSheet(f"color: {COLORS['GREEN']};" if args else "")

    def show_auto_sync_inputs(self):
        self.clear_layout(self.auto_sync_input_layout)
        if self.batch_mode_enabled:
            self.auto_sync_input_layout.addWidget(
                InputBox(
                    self,
                    "Drag and drop files or folder here or click to browse",
                    "Batch mode",
                ),
                1,
            )
        else:
            self.auto_sync_input_layout.addWidget(
                InputBox(
                    self,
                    "Drag and drop video/reference subtitle here or click to browse",
                    "Video/Reference subtitle",
                ),
                1,
            )
            self.auto_sync_input_layout.addWidget(
                InputBox(
                    self,
                    "Drag and drop subtitle file here or click to browse",
                    "Input Subtitle",
                ),
                1,
            )

    def toggle_batch_mode(self):
        self.batch_mode_enabled = not self.batch_mode_enabled
        self.update_config("batch_mode", self.batch_mode_enabled)
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
        self.manual_save_combo = self._dropdown(
            opts, "Save location:", ["Save to desktop", "Override input subtitle"]
        )
        idx = self.manual_save_combo.findText(self.config.get("manual_save_location", "Save to desktop"))
        if idx >= 0:
            self.manual_save_combo.setCurrentIndex(idx)
        self.manual_save_combo.currentTextChanged.connect(lambda text: self.update_config("manual_save_location", text))
        self.btn_manual_sync = self._button("Start")
        opts.addWidget(self.btn_manual_sync)
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
            self.ffsubsync_dont_fix_framerate.toggled.connect(lambda state: self.update_config("ffsubsync_dont_fix_framerate", state))
            self.ffsubsync_use_golden_section = self._checkbox(
                "Use golden section search"
            )
            self.ffsubsync_use_golden_section.setChecked(self.config.get("ffsubsync_use_golden_section", False))
            self.ffsubsync_use_golden_section.toggled.connect(lambda state: self.update_config("ffsubsync_use_golden_section", state))
            self.sync_options_layout.addWidget(self.ffsubsync_dont_fix_framerate)
            self.sync_options_layout.addWidget(self.ffsubsync_use_golden_section)
            vad_items = [
                "Default",
                "subs_then_webrtc",
                "webrtc",
                "subs_then_auditok",
                "auditok",
                "subs_then_silero",
                "silero",
            ]
            self.ffsubsync_vad_combo = self._dropdown(
                self.sync_options_layout, "Voice activity detector:", vad_items
            )
            idx = self.ffsubsync_vad_combo.findText(self.config.get("ffsubsync_vad", "Default"))
            if idx >= 0:
                self.ffsubsync_vad_combo.setCurrentIndex(idx)
            self.ffsubsync_vad_combo.currentTextChanged.connect(lambda text: self.update_config("ffsubsync_vad", text))
        elif tool == "alass":
            self.alass_check_video_subtitles = self._checkbox(
                "Check video for subtitle streams"
            )
            self.alass_check_video_subtitles.setChecked(self.config.get("alass_check_video_subtitles", True))
            self.alass_check_video_subtitles.toggled.connect(lambda state: self.update_config("alass_check_video_subtitles", state))
            self.alass_disable_fps_guessing = self._checkbox("Disable FPS guessing")
            self.alass_disable_fps_guessing.setChecked(self.config.get("alass_disable_fps_guessing", False))
            self.alass_disable_fps_guessing.toggled.connect(lambda state: self.update_config("alass_disable_fps_guessing", state))
            self.alass_disable_speed_optim = self._checkbox(
                "Disable speed optimization"
            )
            self.alass_disable_speed_optim.setChecked(self.config.get("alass_disable_speed_optim", False))
            self.alass_disable_speed_optim.toggled.connect(lambda state: self.update_config("alass_disable_speed_optim", state))
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
            self.alass_split_penalty.valueChanged.connect(lambda value: self.update_config("alass_split_penalty", value))
        
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

    def show_about_dialog(self):
        """Show an About dialog with program information including GitHub link."""
        from PyQt5.QtWidgets import QDialog
        from PyQt5.QtCore import QUrl
        from PyQt5.QtGui import QDesktopServices
        icon = self.windowIcon()
        dialog = QDialog(self)
        dialog.setWindowTitle(f"About {PROGRAM_NAME}")
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dialog.setFixedSize(400, 320)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        header_layout = QHBoxLayout()
        icon_label = QLabel()
        if not icon.isNull():
            icon_label.setPixmap(icon.pixmap(64, 64))
        else:
            icon_label.setText("\U0001F4DA")
            icon_label.setStyleSheet("font-size: 48px;")
        header_layout.addWidget(icon_label)
        title_label = QLabel(
            f"<h1 style='margin-bottom: 0;'>{PROGRAM_NAME} <span style='font-size: 12px; font-weight: normal; color: {COLORS['GREY']};'>v{VERSION}</span></h1><h3 style='margin-top: 5px;'>{PROGRAM_TAGLINE}</h3>"
        )
        title_label.setTextFormat(Qt.RichText)
        header_layout.addWidget(title_label, 1)
        layout.addLayout(header_layout)
        desc_label = QLabel(
            f"<p>{PROGRAM_DESCRIPTION}</p>"
            "<p>Visit the GitHub repository for updates, documentation, and to report issues.</p>"
        )
        desc_label.setTextFormat(Qt.RichText)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        github_btn = QPushButton("Visit GitHub Repository")
        github_btn.setIcon(QIcon(get_resource_path("autosubsync.assets", "github.png")))
        github_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_URL)))
        github_btn.setFixedHeight(32)
        layout.addWidget(github_btn)
        update_btn = QPushButton("Check for updates")
        update_btn.clicked.connect(self.manual_check_for_updates)
        update_btn.setFixedHeight(32)
        layout.addWidget(update_btn)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        close_btn.setFixedHeight(32)
        layout.addWidget(close_btn)
        dialog.exec_()

    def manual_check_for_updates(self):
        """Manually check for updates and always show result"""
        self._show_update_check_result = True
        self.check_for_updates_startup()

    def check_for_updates_startup(self):
        import urllib.request
        from PyQt5.QtCore import QUrl
        from PyQt5.QtGui import QDesktopServices
        def show_update_message(remote_version, local_version):
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle("Update Available")
            msg_box.setText(
                f"A new version of {PROGRAM_NAME} is available! ({local_version} > {remote_version})"
            )
            msg_box.setInformativeText(
                "Please visit the GitHub repository and download the latest version. "
                "Would you like to open the GitHub releases page?"
            )
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg_box.setDefaultButton(QMessageBox.Yes)
            if msg_box.exec_() == QMessageBox.Yes:
                try:
                    QDesktopServices.openUrl(QUrl(GITHUB_LATEST_RELEASE_URL))
                except Exception:
                    pass
        show_result = (
            hasattr(self, "_show_update_check_result")
            and self._show_update_check_result
        )
        self._show_update_check_result = False
        try:
            update_url = GITHUB_VERSION_URL
            with urllib.request.urlopen(update_url) as response:
                remote_raw = response.read().decode().strip()
            local_raw = VERSION
            remote_version = remote_raw
            local_version = local_raw
            try:
                remote_num = int("".join(remote_version.split(".")))
                local_num = int("".join(local_version.split(".")))
            except ValueError:
                return
            if remote_num > local_num:
                QTimer.singleShot(
                    1000, lambda: show_update_message(remote_version, local_version)
                )
            elif show_result:
                QMessageBox.information(
                    self,
                    "Up to Date",
                    f"You are running the latest version of {PROGRAM_NAME} ({local_version}).",
                )
        except Exception as e:
            if show_result:
                QMessageBox.warning(
                    self,
                    "Update Check Failed",
                    f"Could not check for updates:\n{str(e)}",
                )
            pass
