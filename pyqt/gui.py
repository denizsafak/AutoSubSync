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
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QIntValidator
from utils import get_resource_path
from constants import PROGRAM_NAME, VERSION, COLORS

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
        self.batch_mode_enabled = False
        icon_path = get_resource_path("autosubsync.assets", "icon.ico")
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
            if platform.system() == "Windows":
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "autosubsync"
                )
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
        self.sync_options_group = QGroupBox("Sync Tool Options")
        self.sync_options_layout = QVBoxLayout()
        self.sync_options_group.setLayout(self.sync_options_layout)
        controls.addWidget(self.sync_options_group)
        self.sync_tool_combo = self._dropdown(
            controls, "Sync tool:", ["ffsubsync", "alass"]
        )
        self.sync_tool_combo.currentTextChanged.connect(self.update_sync_tool_options)
        self.save_combo = self._dropdown(
            controls,
            "Save location:",
            [
                "Save next to input file",
                "Save to custom location",
                "Replace original file",
            ],
        )
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
        self.update_sync_tool_options(self.sync_tool_combo.currentText())

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
        # Clear input on focus if value is '0' (efficient inline lambda)
        self.shift_input.focusInEvent = lambda event: (
            self.shift_input.clear() if self.shift_input.text() == "0" else None
        ) or QLineEdit.focusInEvent(self.shift_input, event)
        self.btn_shift_plus = self._button("+", h=35, w=35)
        shift_input.addWidget(self.btn_shift_plus)
        opts.addLayout(shift_input)
        self.manual_save_combo = self._dropdown(
            opts, "Save location:", ["Save to desktop", "Override input subtitle"]
        )
        self.btn_manual_sync = self._button("Start")
        opts.addWidget(self.btn_manual_sync)
        ow = QWidget()
        ow.setLayout(opts)
        ow.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        l.addWidget(ow)
        self.tab_widget.addTab(c, "Manual Sync")
        # Connect shift +/- buttons
        self.btn_shift_plus.clicked.connect(self._increment_shift)
        self.btn_shift_minus.clicked.connect(self._decrement_shift)
        # Timers for holding buttons
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
        # Add '+' if positive and not already present
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

        if tool == "ffsubsync":
            self.ffsubsync_dont_fix_framerate = self._checkbox("Don't fix framerate")
            self.ffsubsync_use_golden_section = self._checkbox(
                "Use golden section search"
            )
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

        elif tool == "alass":
            self.alass_check_video_subtitles = self._checkbox(
                "Check video for subtitle streams"
            )
            self.alass_check_video_subtitles.setChecked(True)
            self.alass_disable_fps_guessing = self._checkbox("Disable FPS guessing")
            self.alass_disable_speed_optim = self._checkbox(
                "Disable speed optimization"
            )
            self.sync_options_layout.addWidget(self.alass_check_video_subtitles)
            self.sync_options_layout.addWidget(self.alass_disable_fps_guessing)
            self.sync_options_layout.addWidget(self.alass_disable_speed_optim)
            self.alass_split_penalty, _ = self._create_slider(
                self.sync_options_layout,
                "Split penalty (Default: 7, Recommended: 5-20, No splits: -1)",
                -1,
                100,
                7,
            )

    def eventFilter(self, obj, event):
        # Unfocus shift_input on Enter or when losing focus (e.g., switching tabs)
        if obj == self.shift_input:
            from PyQt5.QtCore import QEvent

            if event.type() == QEvent.KeyPress:
                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    # If empty, set value to 0
                    if not self.shift_input.text().strip():
                        self.shift_input.setText("0")
                    self.shift_input.clearFocus()
                    return True
            elif event.type() == QEvent.FocusOut:
                # If empty when focus is lost, set value to 0
                if not self.shift_input.text().strip():
                    self.shift_input.setText("0")
                self.shift_input.clearFocus()
        return super().eventFilter(obj, event)
