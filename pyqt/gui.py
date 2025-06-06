import platform
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, 
    QLabel, QComboBox, QSizePolicy, QTabWidget, QLineEdit, QHBoxLayout,
    QCheckBox, QSlider, QGroupBox, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from utils import get_resource_path
from constants import PROGRAM_NAME, VERSION, COLORS

# Import ctypes for Windows-specific taskbar icon
if platform.system() == "Windows":
    import ctypes

class InputBox(QLabel):
    # Define CSS styles as class constants
    STYLE_DEFAULT = f"border:2px dashed {COLORS['GREY']}; border-radius:5px; padding:20px; background:{COLORS['BLUE_BACKGROUND']}; min-height:100px;"
    STYLE_DEFAULT_HOVER = f"background:{COLORS['BLUE_BACKGROUND_HOVER']}; border-color:{COLORS['BLUE']};"
    STYLE_ACTIVE = f"border:2px dashed {COLORS['GREEN']}; border-radius:5px; padding:20px; background:{COLORS['GREEN_BACKGROUND']}; min-height:100px;"
    STYLE_ACTIVE_HOVER = f"background:{COLORS['GREEN_BACKGROUND_HOVER']}; border-color:{COLORS['GREEN']};"
    STYLE_ERROR = f"border:2px dashed {COLORS['RED']}; border-radius:5px; padding:20px; background:{COLORS['RED_BACKGROUND']}; min-height:100px; color:{COLORS['RED']};"
    STYLE_ERROR_HOVER = f"background:{COLORS['RED_BACKGROUND_HOVER']}; border-color:{COLORS['RED']};"

    def __init__(self, parent=None, text="Drag and drop your file here or click to browse.", label=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.setText(text)
        self.setObjectName("inputBox")
        self.setStyleSheet(f"QLabel#inputBox {{ {self.STYLE_DEFAULT} }} QLabel#inputBox:hover {{ {self.STYLE_DEFAULT_HOVER} }}")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCursor(Qt.PointingHandCursor)
        
        # Add label in top-left corner if provided
        self.label = None
        if label:
            self.label = QLabel(label, self)
            self.label.setObjectName("boxLabel")
            self.label.setStyleSheet(f"QLabel#boxLabel {{ background-color: transparent; border: none; color: {COLORS['GREY']}; }}")
            self.label.move(10, 8)
            self.label.show()

class autosubsync(QWidget):
    def __init__(self):
        super().__init__()
        self.batch_mode_enabled = False

        # Set application icon
        icon_path = get_resource_path("autosubsync.assets", "icon.ico")
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
            # Set taskbar icon for Windows
            if platform.system() == "Windows":
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("autosubsync")

        self.initUI()

    def initUI(self):
        self.setWindowTitle(f"{PROGRAM_NAME} v{VERSION}")
        screen = QApplication.primaryScreen().geometry()
        width, height = 500, 800
        self.setGeometry((screen.width() - width) // 2, (screen.height() - height) // 2, width, height)
        
        # Main layout
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(15, 15, 15, 15)
        
        # Tab widget
        self.tab_widget = QTabWidget(self)
        self.tab_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Style tab widget - bottom border when selected
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{ 
                border: 0; 
                outline: 0;
                top: 15px;
            }}
            QTabBar::tab {{
                border: none;
                padding: 10px 20px;
                margin-right: 6px;
                background-color: {COLORS['GREY_BACKGROUND']};
            }}
            QTabBar::tab:hover {{
                background-color: {COLORS['GREY_BACKGROUND_HOVER']};
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS['GREY_BACKGROUND_HOVER']};
                border-bottom: 2px solid {COLORS['GREY']};
            }}
            QTabBar::tab:!selected {{
                color: {COLORS['GREY']};
            }}
        """)
        
        # Set the cursor style for tab bar
        self.tab_widget.tabBar().setCursor(Qt.PointingHandCursor)
        
        # Add tab widget to main layout
        outer_layout.addWidget(self.tab_widget)
        
        # Create settings button with absolute positioning
        self.settings_btn = QPushButton(self)
        self.settings_btn.setIcon(QIcon(get_resource_path("autosubsync.assets", "settings.png")))
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.setFixedSize(36, 36)
        
        # Position settings button at top-right corner
        self.settings_btn.move(self.width() - 36 - 15, 15)  # 15 is the outer margin
        self.settings_btn.show()
        
        # Setup tabs
        self.setupAutoSyncTab()
        self.setupManualSyncTab()
        
        self.setLayout(outer_layout)
    
    def resizeEvent(self, event):
        """Override resize event to reposition settings button"""
        super().resizeEvent(event)
        if hasattr(self, 'settings_btn'):
            self.settings_btn.move(self.width() - 36 - 15, 15)
    
    def setupAutoSyncTab(self):
        container = QWidget()
        container.setAutoFillBackground(True)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # Input boxes
        self.auto_sync_input_layout = QVBoxLayout()
        self.auto_sync_input_layout.setSpacing(0)
        self.auto_sync_input_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self.auto_sync_input_layout, 1)
        self.show_auto_sync_inputs()
        
        # Controls
        controls_layout = QVBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(15)

        # Combo box style
        combo_style = "QComboBox { min-height: 20px; padding: 6px 12px; }"
        
        # Save location combo box
        self.save_combo = self.add_dropdown(controls_layout, "Save location:", ["Save next to input file", "Save to custom location", "Replace original file"], combo_style)
        
        # Sync tool combo box
        self.sync_tool_combo = self.add_dropdown(controls_layout, "Sync tool:", ["ffsubsync", "alass"], combo_style)

        # Connect sync tool combo to update options
        self.sync_tool_combo.currentTextChanged.connect(self.update_sync_tool_options)
        
        # Add sync tool specific options
        self.sync_options_group = QGroupBox("Sync Tool Options")
        self.sync_options_layout = QVBoxLayout()
        self.sync_options_group.setLayout(self.sync_options_layout)
        controls_layout.addWidget(self.sync_options_group)
        
        # Start and Batch mode buttons in a horizontal layout
        btns_layout = QHBoxLayout()
        self.btn_batch_mode = QPushButton("Batch mode", self)
        self.btn_batch_mode.setFixedHeight(60)
        self.btn_batch_mode.setFixedWidth(120)
        self.btn_batch_mode.setCheckable(False)  # Make it a normal button
        self.btn_batch_mode.clicked.connect(self.toggle_batch_mode)
        btns_layout.addWidget(self.btn_batch_mode)
        self.btn_sync = QPushButton("Start", self)
        self.btn_sync.setFixedHeight(60)
        self.btn_sync.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # Expands to fill space
        btns_layout.addWidget(self.btn_sync)
        controls_layout.addLayout(btns_layout)
        
        controls_widget = QWidget()
        controls_widget.setLayout(controls_layout)
        controls_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout.addWidget(controls_widget)
        
        self.tab_widget.addTab(container, "Automatic Sync")
        
        # Initialize sync tool options for default selection
        self.update_sync_tool_options(self.sync_tool_combo.currentText())
    
    def show_auto_sync_inputs(self):
        self.clear_layout(self.auto_sync_input_layout)
        if self.batch_mode_enabled:
            self.batch_input_box = InputBox(self, "Drag and drop files or folder here or click to browse", "Batch mode")
            self.auto_sync_input_layout.addWidget(self.batch_input_box, 1)
        else:
            self.video_input_box = InputBox(self, "Drag and drop video/reference subtitle here or click to browse", "Video/Reference subtitle")
            self.subtitle_input_box = InputBox(self, "Drag and drop subtitle file here or click to browse", "Input Subtitle")
            self.auto_sync_input_layout.addWidget(self.video_input_box, 1)
            self.auto_sync_input_layout.addSpacing(15)  # Add spacing between input boxes
            self.auto_sync_input_layout.addWidget(self.subtitle_input_box, 1)

    def toggle_batch_mode(self):
        self.batch_mode_enabled = not self.batch_mode_enabled
        if self.batch_mode_enabled:
            self.btn_batch_mode.setText("Normal mode")
        else:
            self.btn_batch_mode.setText("Batch mode")
        self.show_auto_sync_inputs()

    def setupManualSyncTab(self):
        container = QWidget()
        container.setAutoFillBackground(True)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # Input box
        self.manual_input_box = InputBox(self, "Drag and drop subtitle file here or click to browse", "Manual Subtitle")
        layout.addWidget(self.manual_input_box, 1)
        
        # Controls
        manual_options_layout = QVBoxLayout()
        manual_options_layout.setContentsMargins(0, 0, 0, 0)
        manual_options_layout.setSpacing(15)

        # Add shift subtitle controls
        shift_layout = QVBoxLayout()
        shift_layout.addWidget(QLabel("Shift subtitle (ms)", self))
        
        shift_input_layout = QHBoxLayout()
        
        # Decrement button
        btn_decrease = QPushButton("-", self)
        btn_decrease.setFixedSize(40, 40)
        shift_input_layout.addWidget(btn_decrease)
        
        # Text input for shift value
        self.shift_input = QLineEdit(self)
        self.shift_input.setText("0")
        self.shift_input.setAlignment(Qt.AlignCenter)
        self.shift_input.setFixedHeight(40)
        shift_input_layout.addWidget(self.shift_input)
        
        # Increment button
        btn_increase = QPushButton("+", self)
        btn_increase.setFixedSize(40, 40)
        shift_input_layout.addWidget(btn_increase)
        
        shift_layout.addLayout(shift_input_layout)
        manual_options_layout.addLayout(shift_layout)
        
        # Save options
        self.manual_save_combo = self.add_dropdown(manual_options_layout, "Save options:", 
                                              ["Save to desktop", "Override input subtitle"], 
                                              "QComboBox { min-height: 20px; padding: 6px 12px; }")
        
        # Start button
        self.btn_manual_sync = QPushButton("Shift subtitle", self)
        self.btn_manual_sync.setFixedHeight(60)
        manual_options_layout.addWidget(self.btn_manual_sync)
        
        manual_options_widget = QWidget()
        manual_options_widget.setLayout(manual_options_layout)
        manual_options_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout.addWidget(manual_options_widget)
        
        self.tab_widget.addTab(container, "Manual Sync")
    
    def add_dropdown(self, parent_layout, label_text, items, style):
        layout = QVBoxLayout()
        layout.addWidget(QLabel(label_text, self))
        combo = QComboBox(self)
        combo.setStyleSheet(style)
        combo.addItems(items)
        layout.addWidget(combo)
        parent_layout.addLayout(layout)
        return combo

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

    def update_sync_tool_options(self, tool):
        """Update sync tool options based on selected tool"""
        # Clear existing options - completely rebuild the layout
        self.clear_layout(self.sync_options_layout)
        
        if tool == "ffsubsync":
            # Add ffsubsync options
            self.ffsubsync_dont_fix_framerate = QCheckBox("Don't fix framerate", self)
            self.ffsubsync_use_golden_section = QCheckBox("Use golden section search", self)
            self.sync_options_layout.addWidget(self.ffsubsync_dont_fix_framerate)
            self.sync_options_layout.addWidget(self.ffsubsync_use_golden_section)
            
            # Add voice activity detector combobox
            vad_layout = QVBoxLayout()
            vad_layout.addWidget(QLabel("Voice activity detector", self))
            self.ffsubsync_vad_combo = QComboBox(self)
            self.ffsubsync_vad_combo.addItems([
                "Default", 
                "subs_then_webrtc", 
                "webrtc", 
                "subs_then_auditok", 
                "auditok", 
                "subs_then_silero", 
                "silero"
            ])
            self.ffsubsync_vad_combo.setStyleSheet("QComboBox { min-height: 20px; padding: 6px 12px; }")
            vad_layout.addWidget(self.ffsubsync_vad_combo)
            self.sync_options_layout.addLayout(vad_layout)
            
        elif tool == "alass":
            # Add alass options
            self.alass_disable_fps_guessing = QCheckBox("Disable FPS guessing", self)
            self.alass_disable_speed_optim = QCheckBox("Disable speed optimization", self)
            self.sync_options_layout.addWidget(self.alass_disable_fps_guessing)
            self.sync_options_layout.addWidget(self.alass_disable_speed_optim)

            # Add split penalty slider
            split_layout = QVBoxLayout()
            # Horizontal layout for label and value
            split_label_layout = QHBoxLayout()
            split_label = QLabel("Split penalty (Default: 7, Recommended: 5-20, No splits: -1)", self)
            split_label_layout.addWidget(split_label)
            self.alass_split_value_label = QLabel(str(7), self)
            self.alass_split_value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            split_label_layout.addWidget(self.alass_split_value_label)
            split_layout.addLayout(split_label_layout)

            self.alass_split_penalty = QSlider(Qt.Horizontal, self)
            self.alass_split_penalty.setMinimum(-1)
            self.alass_split_penalty.setMaximum(100)
            self.alass_split_penalty.setValue(7)  # Default value
            self.alass_split_penalty.setTickPosition(QSlider.TicksBelow)
            self.alass_split_penalty.setTickInterval(5)
            self.alass_split_penalty.setMinimumHeight(25)  # Set minimum height to ensure visibility
            split_layout.addWidget(self.alass_split_penalty)

            # Connect slider value change to update the label
            self.alass_split_penalty.valueChanged.connect(self.update_split_penalty_label)

            # Add range display
            split_value_layout = QHBoxLayout()
            split_value_layout.addStretch()
            split_layout.addLayout(split_value_layout)

            self.sync_options_layout.addLayout(split_layout)

    def update_split_penalty_label(self, value):
        """Update the split penalty label when slider value changes"""
        self.alass_split_value_label.setText(str(value))

