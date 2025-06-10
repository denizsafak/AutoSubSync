import platform
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QSizePolicy,
    QTabWidget,
    QHBoxLayout,
    QCheckBox,
    QMenu,
    QMessageBox,
    QFileDialog,
    QFileIconProvider
)
from PyQt6.QtCore import Qt, QTimer, QUrl, QSize, QFileInfo, QIODevice, QBuffer
from PyQt6.QtGui import QIcon, QDesktopServices, QDragEnterEvent, QDropEvent, QAction
import os, base64
from utils import *
from constants import *
# Import batch mode functionality
from gui_batch_mode import (
    BatchTreeView, 
    show_batch_add_menu,
    handle_batch_drop,
)

# Import ctypes for Windows-specific taskbar icon
if platform.system() == "Windows":
    import ctypes

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
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(True)
        self.setText(text)
        self.setObjectName("inputBox")
        self.setStyleSheet(
            f"QLabel#inputBox {{{self.STYLE_DEFAULT}}} QLabel#inputBox:hover {{{self.STYLE_DEFAULT_HOVER}}}"
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.file_path = None
        self.input_type = input_type
        self.default_text = text
        
        # Add clear button
        self.clear_btn = QPushButton("✕", self)
        self.clear_btn.setFixedSize(25, 25)
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self.reset_to_default)
        self.clear_btn.hide()  # Initially hidden

        # Add Go to folder button
        self.goto_folder_btn = QPushButton("Go to folder", self)
        self.goto_folder_btn.setFixedHeight(28)
        self.goto_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
        if event.button() == Qt.MouseButton.LeftButton or event.button() == Qt.MouseButton.RightButton:
            if self.input_type == "batch":
                main_window = self.window()
                if isinstance(main_window, autosubsync):
                    # Pass self (InputBox) to position menu correctly and the event position
                    menu = show_batch_add_menu(main_window, source_widget=self, position=event.globalPosition().toPoint())
                    # Connect to menu close event to fix hover state
                    if menu:
                        menu.aboutToHide.connect(self._on_menu_closed)
                return  # Prevent default browse_file for batch mode
            elif event.button() == Qt.MouseButton.LeftButton:  # Only browse on left click for non-batch
                self.browse_file()

    def _on_menu_closed(self):
        """Handle menu close event to reset hover state"""
        # Force update the hover state by checking if mouse is still over the widget
        cursor_pos = self.mapFromGlobal(self.cursor().pos())
        if not self.rect().contains(cursor_pos):
            # Mouse is not over the widget, ensure we're not in hover state
            self.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, False)
            # Force a style update
            self.style().unpolish(self)
            self.style().polish(self)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        files = [u.toLocalFile() for u in event.mimeData().urls()]

        if self.input_type == "batch":
            main_window = self.window()
            if isinstance(main_window, autosubsync):
                handle_batch_drop(main_window, files)
            return  # Batch drop handled by main window's BatchTreeView

        # Get the parent autosubsync instance first
        parent = self
        while parent and not isinstance(parent, autosubsync):
            parent = parent.parent()
            
        # Special handling for exactly 2 files
        if len(files) == 2 and parent and not parent.batch_mode_enabled:
            # Get extensions of both files
            ext1 = os.path.splitext(files[0])[1].lower()
            ext2 = os.path.splitext(files[1])[1].lower()
            
            video_file = None
            subtitle_file = None
            
            # Determine which is video and which is subtitle
            if ext1 in VIDEO_EXTENSIONS and ext2 in SUBTITLE_EXTENSIONS:
                video_file = files[0]
                subtitle_file = files[1]
            elif ext1 in SUBTITLE_EXTENSIONS and ext2 in VIDEO_EXTENSIONS:
                video_file = files[1]
                subtitle_file = files[0]
                
            # If we have one of each file type, set them appropriately
            if video_file and subtitle_file and parent:
                # If in auto sync tab inputs
                if self == parent.video_ref_input or self == parent.subtitle_input:
                    # Set the video input
                    parent.video_ref_input.set_file(video_file)
                    # Set the subtitle input
                    parent.subtitle_input.set_file(subtitle_file)
                    return
                # If in manual sync tab input, use only the subtitle
                elif self == parent.manual_input_box:
                    self.set_file(subtitle_file)
                    return
                
        # Standard single-file handling
        if self.input_type == "subtitle" or self.input_type == "video_or_subtitle":
            if files:
                self.set_file(files[0])
        elif self.input_type == "batch":
            # This case should ideally be fully handled by the main window's BatchTreeView
            # if the InputBox itself is used for dropping when the tree is not yet visible.
            main_window = self.window()
            if isinstance(main_window, autosubsync):
                handle_batch_drop(main_window, files)
            return

    def browse_file(self):
        if self.input_type == "subtitle":
            file_filter = f"Subtitle Files (*{' *'.join(SUBTITLE_EXTENSIONS)})"
        elif self.input_type == "video_or_subtitle":
            file_filter = f"Video/Subtitle Files (*{' *'.join(VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS)})"
        else:
            # For "batch" type, file browsing is handled by the menu triggered from mousePressEvent.
            # For other unknown types, or if this is somehow called for batch, do nothing.
            return
            
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File", "", file_filter)
        if file_path:
            self.set_file(file_path)

    def set_file(self, file_path):
        if not os.path.exists(file_path):
            self.show_error("File does not exist")
            return
            
        # Validate file type
        ext = os.path.splitext(file_path)[1].lower()
        if not ext:
            self.show_error("This is not a supported subtitle format.")
            return
        # if ext is empty, treat it as an invalid file
        if self.input_type == "subtitle" and ext not in SUBTITLE_EXTENSIONS:
            self.show_error(f'"{ext}" is not a supported subtitle format.')
            return
        elif self.input_type == "video_or_subtitle" and ext not in VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS:
            self.show_error(f'"{ext}" is not a supported video or subtitle format.')
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
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
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
    # Make InputBox accessible as a class attribute for imported functions
    InputBox = InputBox

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
        self.batch_tree_view = BatchTreeView(self)
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
        self.tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
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
        self.update_auto_sync_ui_for_batch()  # Ensure correct UI for batch mode on startup

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
        lab.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        row.addWidget(lab)
        combo = QComboBox(self)
        combo.setStyleSheet(style)
        combo.addItems(items)
        combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
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
                
    def eventFilter(self, obj, event):
        """Event filter to handle events for various widgets"""
        # Forward shift input events to the handler
        if hasattr(self, '_handle_shift_input_events'):
            if self._handle_shift_input_events(obj, event):
                return True
        return super().eventFilter(obj, event)

    def show_settings_menu(self):
        # Show the menu at the right position below the button
        self.settings_menu.popup(self.settings_btn.mapToGlobal(
            self.settings_btn.rect().bottomLeft()))
