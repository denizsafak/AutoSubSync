import os, base64
import texts
import platform
import logging
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
    QFileIconProvider,
    QDialog,
)
from PyQt6.QtCore import Qt, QTimer, QSize, QFileInfo, QIODevice, QBuffer
from PyQt6.QtGui import QIcon, QDragEnterEvent, QDropEvent, QAction, QActionGroup

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

logger = logging.getLogger(__name__)


class InputBox(QLabel):
    _STATE_CONFIG = {
        "default": {
            "border": COLORS["GREY"],
            "bg": COLORS["BLUE_BACKGROUND"],
            "hover_border": COLORS["BLUE"],
            "hover_bg": COLORS["BLUE_BACKGROUND_HOVER"],
            "text": None,
        },
        "active": {
            "border": COLORS["GREEN"],
            "bg": COLORS["GREEN_BACKGROUND"],
            "hover_border": COLORS["GREEN"],
            "hover_bg": COLORS["GREEN_BACKGROUND_HOVER"],
            "text": None,
        },
        "error": {
            "border": COLORS["RED"],
            "bg": COLORS["RED_BACKGROUND"],
            "hover_border": COLORS["RED"],
            "hover_bg": COLORS["RED_BACKGROUND_HOVER"],
            "text": COLORS["RED"],
        },
    }
    BORDER_RADIUS = 5
    PADDING = 20
    MIN_HEIGHT = 100

    def __init__(
        self,
        parent=None,
        text=texts.DRAG_DROP_FILE,
        label=None,
        input_type=None,
    ):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(True)
        self.setText(text)
        self.setWordWrap(True)  # Enable word wrapping for all text
        self.setObjectName("inputBox")
        self._active_state_key = "default"  # Initialize current state
        self._apply_style()  # Apply initial style
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.file_path = None
        self.input_type = input_type
        self.default_text = text
        self._error_timer = None  # Timer for error message restoration

        # Add clear button
        self.clear_btn = QPushButton("✕", self)
        self.clear_btn.setFixedSize(25, 25)
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self.reset_to_default)
        self.clear_btn.hide()  # Initially hidden

        # Add Go to folder button
        self.goto_folder_btn = QPushButton(texts.GO_TO_FOLDER, self)
        self.goto_folder_btn.setFixedHeight(28)
        self.goto_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.goto_folder_btn.clicked.connect(self.open_file_folder)
        self.goto_folder_btn.hide()
        self.goto_folder_btn.setStyleSheet("font-size: 12px; padding: 2px 10px;")

        # Add "Load library" button for batch mode (top-left position)
        if input_type == "batch":
            self.load_library_btn = QPushButton(texts.LOAD_LIBRARY, self)
            self.load_library_btn.setFixedHeight(28)
            self.load_library_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.load_library_btn.setStyleSheet("font-size: 12px; padding: 2px 10px;")
            self.load_library_btn.clicked.connect(self._on_load_library_clicked)
            self.load_library_btn.show()

        # Add total shifted label for overwrite mode (only for manual tab input boxes)
        if input_type == "subtitle":  # Only for manual tab subtitle input
            self.total_shifted_label = QLabel("", self)
            self.total_shifted_label.setStyleSheet(
                f"QLabel {{ color: {COLORS['GREY']} }}"
            )
            self.total_shifted_label.hide()
            self.total_shifted_ms = 0  # Track total shifted amount

        if label:
            l = QLabel(label, self)
            l.setObjectName("boxLabel")
            l.setStyleSheet(
                f"QLabel#boxLabel {{ background: transparent; border: none; color: {COLORS['GREY']}; }}"
            )
            l.move(10, 8)
            l.show()

    def showEvent(self, event):
        """Reapply stylesheet when the widget is shown to ensure hover and state work correctly."""
        super().showEvent(event)
        self._apply_style()  # Force reapply the current stylesheet

    def handle_file_dialog(self):
        if self.input_type == "subtitle":
            file_filter = (
                f"{texts.SUBTITLE_FILES_LABEL} (*{' *'.join(SUBTITLE_EXTENSIONS)})"
            )
            title = texts.SELECT_SUBTITLE_FILE_TITLE
        elif self.input_type == "video_or_subtitle":
            file_filter = f"{texts.VIDEO_OR_SUBTITLE_FILES_LABEL} (*{' *'.join(VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS)})"
            title = texts.SELECT_VIDEO_OR_SUBTITLE_FILE_TITLE
        else:
            # For "batch" type, file browsing is handled by the menu triggered from mousePressEvent.
            # For other unknown types, or if this is somehow called for batch, do nothing.
            return

        # Get the parent autosubsyncapp instance to access config
        parent = self
        while parent and not isinstance(parent, autosubsyncapp):
            parent = parent.parentWidget()

        if parent:
            file_path = open_filedialog(parent, "file-open", title, file_filter)
            if file_path:
                self.set_file(file_path)

    def mousePressEvent(self, event):
        if (
            event.button() == Qt.MouseButton.LeftButton
            or event.button() == Qt.MouseButton.RightButton
        ):
            if self.input_type == "batch":
                main_window = self.window()
                if isinstance(main_window, autosubsyncapp):
                    # Pass self (InputBox) to position menu correctly and the event position
                    # Include sync tracking submenu for InputBox clicks
                    menu = show_batch_add_menu(
                        main_window,
                        source_widget=self,
                        position=event.globalPosition().toPoint(),
                        include_sync_tracking=True,
                    )
                    # Connect to menu close event to fix hover state
                    if menu:
                        menu.aboutToHide.connect(self._on_menu_closed)
                return  # Prevent default browse_file for batch mode

            elif (
                event.button() == Qt.MouseButton.LeftButton
            ):  # Only browse on left click for non-batch
                self.handle_file_dialog()

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
            self._apply_style(drag_hover=True)  # Apply "hovered" appearance

    def dragLeaveEvent(self, event):
        self._apply_style(drag_hover=False)  # Restore normal appearance with :hover

    def dropEvent(self, event: QDropEvent):
        files = [u.toLocalFile() for u in event.mimeData().urls()]

        if self.input_type == "batch":
            main_window = self.window()
            if isinstance(main_window, autosubsyncapp):
                handle_batch_drop(main_window, files)
            return  # Batch drop handled by main window's BatchTreeView

        # Get the parent autosubsyncapp instance first
        parent = self
        while parent and not isinstance(parent, autosubsyncapp):
            # Access parent as a property, not as a callable
            parent = parent.parentWidget()

        # Handle folder drops for normal mode input boxes
        if parent and not parent.batch_mode_enabled:
            # Check if any of the dropped items are folders
            expanded_files = []
            for file_path in files:
                if os.path.isdir(file_path):
                    # Get files from the folder
                    try:
                        folder_files = []
                        for item in os.listdir(file_path):
                            item_path = os.path.join(file_path, item)
                            if os.path.isfile(item_path):
                                folder_files.append(item_path)

                        # If folder has 1 or 2 files, extract them
                        if 1 <= len(folder_files) <= 2:
                            expanded_files.extend(folder_files)
                        else:
                            # Keep the original folder path for other handling
                            expanded_files.append(file_path)
                    except (OSError, PermissionError):
                        # If we can't read the folder, keep the original path
                        expanded_files.append(file_path)
                else:
                    expanded_files.append(file_path)

            # Update files list with expanded files
            files = expanded_files

        # Special handling for exactly 2 files
        if len(files) == 2 and parent and not parent.batch_mode_enabled:
            # Get extensions of both files
            ext1 = os.path.splitext(files[0])[1].lower()
            ext2 = os.path.splitext(files[1])[1].lower()

            reference_file = None
            subtitle_file = None

            # Determine which is video and which is subtitle
            if ext1 in VIDEO_EXTENSIONS and ext2 in SUBTITLE_EXTENSIONS:
                reference_file = files[0]
                subtitle_file = files[1]
            elif ext1 in SUBTITLE_EXTENSIONS and ext2 in VIDEO_EXTENSIONS:
                reference_file = files[1]
                subtitle_file = files[0]

            # If we have one of each file type, set them appropriately
            if reference_file and subtitle_file and parent:
                # If in auto sync tab inputs
                if self == parent.video_ref_input or self == parent.subtitle_input:
                    # Set the video input
                    parent.video_ref_input.set_file(reference_file)
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
            if isinstance(main_window, autosubsyncapp):
                handle_batch_drop(main_window, files)
            return

    def set_file(self, file_path):
        logger.info(f'Added: "{file_path}"')
        if not os.path.exists(file_path):
            self.show_error("File does not exist")
            return

        # Validate file type
        ext = os.path.splitext(file_path)[1].lower()
        if not ext:
            self.show_error(texts.UNSUPPORTED_SUBTITLE_FORMAT)
            return
        # if ext is empty, treat it as an invalid file
        if self.input_type == "subtitle" and ext not in SUBTITLE_EXTENSIONS:
            self.show_error(texts.UNSUPPORTED_SUBTITLE_FORMAT_WITH_EXT.format(ext=ext))
            return
        elif (
            self.input_type == "video_or_subtitle"
            and ext not in VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS
        ):
            self.show_error(
                texts.UNSUPPORTED_VIDEO_OR_SUBTITLE_FORMAT_WITH_EXT.format(ext=ext)
            )
            return

        self.file_path = file_path
        name = os.path.basename(file_path)
        size = os.path.getsize(file_path)

        # Hide manual sync message when file changes
        main_window = self.window()
        if (
            hasattr(main_window, "manual_message_label")
            and main_window.manual_message_label.isVisible()
        ):
            main_window.manual_message_label.setVisible(False)

        # Load total shifted amount from session data if available
        if hasattr(self, "total_shifted_ms"):
            if hasattr(main_window, "session_shifted_files"):
                self.total_shifted_ms = main_window.session_shifted_files.get(
                    file_path, 0
                )
            else:
                self.total_shifted_ms = 0
            # Update display after loading session data
            if hasattr(main_window, "_update_total_shifted_display"):
                main_window._update_total_shifted_display()

        # Get icon without resizing using custom provider
        provider = QFileIconProvider()
        qicon = provider.icon(QFileInfo(file_path))
        size_icon = QSize(24, 24)
        pixmap = qicon.pixmap(size_icon)

        # Convert to base64 PNG
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        pixmap.save(buffer, "PNG")
        img_data = base64.b64encode(buffer.data()).decode()

        # Update display
        self.setText(
            f'<img src="data:image/png;base64,{img_data}"><br><span style="display: inline-block; max-width: 100%; word-break: break-all;"><b>{name}</b></span><br>{texts.FILE_SIZE}: {format_num(size)}'
        )
        self.setWordWrap(True)
        self._active_state_key = "active"
        self._apply_style()

        # Show and position the clear button in the top right corner
        self.clear_btn.show()
        self.clear_btn.move(self.width() - self.clear_btn.width() - 10, 10)
        # Show and position the Go to folder button in the bottom left
        self.goto_folder_btn.show()
        self.goto_folder_btn.setToolTip(file_path)
        self.goto_folder_btn.move(
            self.width() - self.goto_folder_btn.width() - 10,
            self.height() - self.goto_folder_btn.height() - 10,
        )

    def show_error(self, message):
        logger.warning(f"{message}")

        # Cancel any existing error timer to prevent multiple resets
        if self._error_timer is not None:
            self._error_timer.stop()
            self._error_timer = None

        prev_file_path = self.file_path
        prev_text = self.text() if hasattr(self, "text") else self.default_text
        prev_state = self._active_state_key
        self.setText(message)
        self._active_state_key = "error"
        self._apply_style()
        self.clear_btn.hide()
        self.goto_folder_btn.hide()

        def restore_prev():
            # Only restore if file_path has not changed during error display
            if self.file_path == prev_file_path and prev_file_path:
                self.file_path = prev_file_path
                self.setText(prev_text)
                self._active_state_key = prev_state
                self._apply_style()
                self.clear_btn.show()
                self.goto_folder_btn.show()
            # If file_path changed, do nothing (keep new file and state)
            elif not self.file_path:
                self.reset_to_default()
            self._error_timer = None  # Clear timer reference

        self._error_timer = QTimer()
        self._error_timer.setSingleShot(True)
        self._error_timer.timeout.connect(restore_prev)
        self._error_timer.start(3000)

    def reset_to_default(self):
        logger.info("Resetting InputBox to default state.")

        # Hide manual sync message when file is removed
        main_window = self.window()
        if (
            hasattr(main_window, "manual_message_label")
            and main_window.manual_message_label.isVisible()
        ):
            main_window.manual_message_label.setVisible(False)

        self.file_path = None
        self.setText(self.default_text)
        self._active_state_key = "default"
        self._apply_style()
        self.clear_btn.hide()
        self.goto_folder_btn.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "clear_btn") and self.clear_btn.isVisible():
            self.clear_btn.move(self.width() - self.clear_btn.width() - 10, 10)
        if hasattr(self, "goto_folder_btn") and self.goto_folder_btn.isVisible():
            self.goto_folder_btn.move(
                self.width() - self.goto_folder_btn.width() - 10,
                self.height() - self.goto_folder_btn.height() - 10,
            )
        if (
            hasattr(self, "total_shifted_label")
            and self.total_shifted_label.isVisible()
        ):
            self.total_shifted_label.move(
                10, self.height() - self.total_shifted_label.height() - 10
            )
        # Position load_library_btn at top-right for batch input
        if hasattr(self, "load_library_btn"):
            self.load_library_btn.move(
                self.width() - self.load_library_btn.width() - 10, 10
            )

    def _on_load_library_clicked(self):
        """Handle load library button click."""
        main_window = self.window()
        if isinstance(main_window, autosubsyncapp):
            main_window.smart_load_library()

    def open_file_folder(self):
        if self.file_path and os.path.exists(self.file_path):
            open_folder(self.file_path)
        else:
            QMessageBox.warning(
                self,
                texts.ERROR,
                texts.FILE_DOES_NOT_EXIST,
            )

    def _apply_style(self, drag_hover=False):
        p = self._STATE_CONFIG[self._active_state_key]
        t = f"color: {p['text']};" if p["text"] else ""
        base = f"border-radius:{self.BORDER_RADIUS}px;padding:{self.PADDING}px;min-height:{self.MIN_HEIGHT}px;{t}"
        if drag_hover:
            s = f"QLabel#inputBox{{border:2px dashed {p['hover_border']};background:{p['hover_bg']};{base}}}"
        else:
            s = f"QLabel#inputBox{{border:2px dashed {p['border']};background:{p['bg']};{base}}}QLabel#inputBox:hover{{border-color:{p['hover_border']};background:{p['hover_bg']};}}"
        self.setStyleSheet(s)


class autosubsyncapp(QWidget):
    # Make InputBox accessible as a class attribute for imported functions
    InputBox = InputBox

    COMBO_STYLE = "QComboBox { min-height: 20px; padding: 6px 12px; }"
    TAB_STYLE = f"""
        QTabWidget::pane {{ border: 0; outline: 0; top: 15px; }}
        QTabBar::tab {{ border-radius: 2px; border: none; padding: 10px 20px; margin-right: 6px; background-color: {COLORS['GREY_BACKGROUND']}; }}
        QTabBar::tab:hover {{ background-color: {COLORS['GREY_BACKGROUND_HOVER']}; }}
        QTabBar::tab:selected {{ background-color: {COLORS['GREY_BACKGROUND_HOVER']}; border-bottom: 3px solid {COLORS['GREY']}; }}
        QTabBar::tab:!selected {{ color: {COLORS['GREY']}; }}
    """

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.batch_mode_enabled = self.config.get(
            "batch_mode", DEFAULT_OPTIONS["batch_mode"]
        )
        self.batch_tree_view = BatchTreeView(self)
        icon_path = get_resource_path("autosubsyncapp.assets", "icon.ico")
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
            if platform.system() == "Windows":
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "autosubsyncapp"
                )
        # Theme: apply on startup
        self.apply_theme(self.config.get("theme", DEFAULT_OPTIONS["theme"]))
        # Check for updates at startup if enabled
        if self.config.get(
            "check_updates_startup", DEFAULT_OPTIONS["check_updates_startup"]
        ):
            QTimer.singleShot(1000, lambda: check_for_updates_startup(self))
        # Flag to track if ffmpeg has been initialized
        self._ffmpeg_initialized = False
        self.initUI()
        logger.info("Main window initialized")

    def showEvent(self, event):
        """Handle show event to initialize ffmpeg after GUI is visible."""
        super().showEvent(event)
        # Only initialize ffmpeg once, after the first show
        if not self._ffmpeg_initialized:
            self._ffmpeg_initialized = True
            # Use a short timer to ensure the window is fully rendered
            from utils import initialize_static_ffmpeg

            QTimer.singleShot(100, lambda: initialize_static_ffmpeg(self))

    def apply_theme(self, theme):
        from PyQt6.QtGui import QPalette, QColor

        app = QApplication.instance()
        if theme == "dark":
            app.setStyle("Fusion")
            palette = QPalette()
            dark_bg = QColor(COLORS["DARK_BG"])
            base_bg = QColor(COLORS["DARK_BASE"])
            alt_bg = QColor(COLORS["DARK_ALT"])
            button_bg = QColor(COLORS["DARK_BUTTON"])
            disabled_fg = QColor(COLORS["DARK_DISABLED"])
            palette.setColor(QPalette.ColorRole.Window, dark_bg)
            palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorRole.Base, base_bg)
            palette.setColor(QPalette.ColorRole.AlternateBase, alt_bg)
            palette.setColor(QPalette.ColorRole.ToolTipBase, dark_bg)
            palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorRole.Button, button_bg)
            palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
            # Disabled roles
            palette.setColor(
                QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, disabled_fg
            )
            palette.setColor(
                QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled_fg
            )
            palette.setColor(
                QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, disabled_fg
            )
            palette.setColor(
                QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base, dark_bg
            )
            palette.setColor(
                QPalette.ColorGroup.Disabled, QPalette.ColorRole.Button, dark_bg
            )
            app.setPalette(palette)
        elif theme == "light":
            app.setStyle("Fusion")
            palette = QPalette()
            disabled_fg = QColor(COLORS["LIGHT_DISABLED"])
            palette.setColor(QPalette.ColorRole.Window, QColor(COLORS["LIGHT_BG"]))
            palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.black)
            palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorRole.AlternateBase, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.black)
            palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.black)
            palette.setColor(QPalette.ColorRole.Button, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.black)
            # Disabled roles
            palette.setColor(
                QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, disabled_fg
            )
            palette.setColor(
                QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled_fg
            )
            palette.setColor(
                QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, disabled_fg
            )
            palette.setColor(
                QPalette.ColorGroup.Disabled,
                QPalette.ColorRole.Base,
                Qt.GlobalColor.white,
            )
            palette.setColor(
                QPalette.ColorGroup.Disabled,
                QPalette.ColorRole.Button,
                Qt.GlobalColor.white,
            )
            app.setPalette(palette)
        else:  # system
            app.setStyle("Fusion")
            app.setPalette(QPalette())
        # Force style refresh for all top-level widgets
        style_name = app.style().objectName()
        app.setStyle(style_name)
        for widget in app.topLevelWidgets():
            app.style().polish(widget)
            widget.update()

        # Only update and save config if the theme value is different
        if self.config.get("theme", DEFAULT_OPTIONS["theme"]) != theme:
            self.config["theme"] = theme
            save_config(self.config)

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
        self.tab_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.tab_widget.setStyleSheet(self.TAB_STYLE)
        outer_layout.addWidget(self.tab_widget)
        self.settings_btn = QPushButton(self)
        self.settings_btn.setIcon(
            QIcon(get_resource_path("autosubsyncapp.assets", "settings.svg"))
        )
        self.settings_btn.setToolTip(texts.SETTINGS)
        self.settings_btn.setFixedSize(36, 36)
        self.settings_btn.move(self.width() - 36 - 15, 15)

        # Create settings menu
        self.settings_menu = QMenu(self)

        # Add Language submenu
        self.language_menu = self.settings_menu.addMenu(texts.LANGUAGE)
        self.language_action_group = QActionGroup(self)
        self.language_action_group.setExclusive(True)

        self.language_actions = {}
        for language_name, language_code in LANGUAGES.items():
            action = QAction(language_name, self)
            action.setCheckable(True)
            action.setActionGroup(self.language_action_group)
            action.triggered.connect(
                lambda checked, code=language_code: self.change_language(code)
            )
            self.language_menu.addAction(action)
            self.language_actions[language_code] = action

        # Set the current selection
        current_language = self.config.get("language", DEFAULT_OPTIONS["language"])
        if current_language not in self.language_actions:
            current_language = "en_US"
        self.language_actions[current_language].setChecked(True)

        # Add Theme submenu
        self.theme_menu = self.settings_menu.addMenu(texts.THEME)
        self.theme_action_group = QActionGroup(self)
        self.theme_action_group.setExclusive(True)
        self.theme_system_action = QAction(texts.SYSTEM, self)
        self.theme_system_action.setCheckable(True)
        self.theme_system_action.setActionGroup(self.theme_action_group)
        self.theme_system_action.triggered.connect(lambda: self.apply_theme("system"))
        self.theme_menu.addAction(self.theme_system_action)
        self.theme_dark_action = QAction(texts.DARK, self)
        self.theme_dark_action.setCheckable(True)
        self.theme_dark_action.setActionGroup(self.theme_action_group)
        self.theme_dark_action.triggered.connect(lambda: self.apply_theme("dark"))
        self.theme_menu.addAction(self.theme_dark_action)
        self.theme_light_action = QAction(texts.LIGHT, self)
        self.theme_light_action.setCheckable(True)
        self.theme_light_action.setActionGroup(self.theme_action_group)
        self.theme_light_action.triggered.connect(lambda: self.apply_theme("light"))
        self.theme_menu.addAction(self.theme_light_action)
        # Set checked theme
        theme = self.config.get("theme", DEFAULT_OPTIONS["theme"])
        if theme == "dark":
            self.theme_dark_action.setChecked(True)
        elif theme == "light":
            self.theme_light_action.setChecked(True)
        else:
            self.theme_system_action.setChecked(True)

        self.settings_menu.addSeparator()

        # Add output subtitle encoding submenu
        self.encoding_menu = self.settings_menu.addMenu(
            texts.CHANGE_OUTPUT_SUBTITLE_ENCODING
        )
        self.encoding_action_group = QActionGroup(self)
        self.encoding_action_group.setExclusive(True)

        # Add "Disabled" option
        self.encoding_disabled_action = QAction(texts.DISABLED, self)
        self.encoding_disabled_action.setCheckable(True)
        self.encoding_disabled_action.setActionGroup(self.encoding_action_group)
        self.encoding_disabled_action.triggered.connect(
            lambda: update_config(self, "output_subtitle_encoding", "disabled")
        )
        self.encoding_menu.addAction(self.encoding_disabled_action)

        # Add "Same as input" option
        self.encoding_same_action = QAction(texts.SAME_AS_INPUT_SUBTITLE, self)
        self.encoding_same_action.setCheckable(True)
        self.encoding_same_action.setActionGroup(self.encoding_action_group)
        self.encoding_same_action.triggered.connect(
            lambda: update_config(self, "output_subtitle_encoding", "same_as_input")
        )
        self.encoding_menu.addAction(self.encoding_same_action)

        # Add separator before specific encodings
        self.encoding_menu.addSeparator()

        # Add all available encodings
        from utils import get_available_encodings

        self.encoding_actions = {}
        for encoding_id, encoding_name in get_available_encodings():
            action = QAction(encoding_name, self)
            action.setCheckable(True)
            action.setActionGroup(self.encoding_action_group)
            action.triggered.connect(
                lambda checked, enc=encoding_id: update_config(
                    self, "output_subtitle_encoding", enc
                )
            )
            self.encoding_menu.addAction(action)
            self.encoding_actions[encoding_id] = action

        # Set the current selection
        current_encoding = self.config.get(
            "output_subtitle_encoding", DEFAULT_OPTIONS["output_subtitle_encoding"]
        )
        if current_encoding == "default":
            self.encoding_default_action.setChecked(True)
        elif current_encoding == "same_as_input":
            self.encoding_same_action.setChecked(True)
        elif current_encoding in self.encoding_actions:
            self.encoding_actions[current_encoding].setChecked(True)
        else:
            # Fallback to "Same as input" if invalid encoding
            self.encoding_same_action.setChecked(True)
            update_config(self, "output_subtitle_encoding", "same_as_input")

        # Add Sync Tracking submenu (for Batch Mode)
        self._create_sync_tracking_menu()

        self.backup_subtitles_action = QAction(
            texts.BACKUP_SUBTITLES_BEFORE_OVERWRITING, self
        )
        self.backup_subtitles_action.setCheckable(True)
        self.backup_subtitles_action.setChecked(
            self.config.get(
                "backup_subtitles_before_overwriting",
                DEFAULT_OPTIONS["backup_subtitles_before_overwriting"],
            )
        )
        self.backup_subtitles_action.triggered.connect(
            lambda checked: update_config(
                self, "backup_subtitles_before_overwriting", checked
            )
        )
        self.settings_menu.addAction(self.backup_subtitles_action)

        self.keep_extracted_subtitles_action = QAction(
            texts.KEEP_EXTRACTED_SUBTITLES, self
        )
        self.keep_extracted_subtitles_action.setCheckable(True)
        self.keep_extracted_subtitles_action.setChecked(
            self.config.get(
                "keep_extracted_subtitles", DEFAULT_OPTIONS["keep_extracted_subtitles"]
            )
        )
        self.keep_extracted_subtitles_action.triggered.connect(
            lambda checked: update_config(self, "keep_extracted_subtitles", checked)
        )
        self.settings_menu.addAction(self.keep_extracted_subtitles_action)

        self.keep_converted_subtitles_action = QAction(
            texts.KEEP_CONVERTED_SUBTITLES, self
        )
        self.keep_converted_subtitles_action.setCheckable(True)
        self.keep_converted_subtitles_action.setChecked(
            self.config.get(
                "keep_converted_subtitles", DEFAULT_OPTIONS["keep_converted_subtitles"]
            )
        )
        self.keep_converted_subtitles_action.triggered.connect(
            lambda checked: update_config(self, "keep_converted_subtitles", checked)
        )
        self.settings_menu.addAction(self.keep_converted_subtitles_action)

        self.auto_rename_bracket_paths_action = QAction(texts.ALASS_RENAME_ALWAYS, self)
        self.auto_rename_bracket_paths_action.setCheckable(True)
        self.auto_rename_bracket_paths_action.setChecked(
            self.config.get(
                "auto_rename_bracket_paths",
                DEFAULT_OPTIONS["auto_rename_bracket_paths"],
            )
        )
        self.auto_rename_bracket_paths_action.triggered.connect(
            lambda checked: update_config(self, "auto_rename_bracket_paths", checked)
        )
        self.settings_menu.addAction(self.auto_rename_bracket_paths_action)

        self.add_tool_prefix_action = QAction(texts.ADD_TOOL_PREFIX_TO_SUBTITLES, self)
        self.add_tool_prefix_action.setCheckable(True)
        self.add_tool_prefix_action.setChecked(
            self.config.get("add_tool_prefix", DEFAULT_OPTIONS["add_tool_prefix"])
        )
        self.add_tool_prefix_action.triggered.connect(
            lambda checked: update_config(self, "add_tool_prefix", checked)
        )
        self.settings_menu.addAction(self.add_tool_prefix_action)

        self.settings_menu.addSeparator()

        # Add 'Open config directory' option at the top
        self.open_config_dir_action = QAction(texts.OPEN_CONFIG_FILE_DIRECTORY, self)
        self.open_config_dir_action.triggered.connect(
            lambda: open_config_directory(self)
        )
        self.settings_menu.addAction(self.open_config_dir_action)

        # Add 'Open logs directory' option at the top
        self.open_logs_directory_action = QAction(texts.OPEN_LOGS_DIRECTORY, self)
        self.open_logs_directory_action.triggered.connect(
            lambda: open_logs_directory(self)
        )
        self.settings_menu.addAction(self.open_logs_directory_action)

        # Add 'Keep log records' option
        self.keep_log_records_action = QAction(texts.KEEP_LOG_RECORDS, self)
        self.keep_log_records_action.setCheckable(True)
        self.keep_log_records_action.setChecked(
            self.config.get("keep_log_records", DEFAULT_OPTIONS["keep_log_records"])
        )
        self.keep_log_records_action.triggered.connect(
            lambda checked: update_config(self, "keep_log_records", checked)
        )
        self.settings_menu.addAction(self.keep_log_records_action)

        # Add 'Clear logs directory' option
        self.clear_logs_directory_action = QAction(texts.CLEAR_ALL_LOGS, self)
        self.clear_logs_directory_action.triggered.connect(
            lambda: clear_logs_directory(self)
        )
        self.settings_menu.addAction(self.clear_logs_directory_action)

        self.settings_menu.addSeparator()

        self.remember_changes_action = QAction(texts.REMEMBER_THE_CHANGES, self)
        self.remember_changes_action.setCheckable(True)
        self.remember_changes_action.setChecked(
            self.config.get("remember_changes", DEFAULT_OPTIONS["remember_changes"])
        )
        self.remember_changes_action.triggered.connect(
            lambda checked: toggle_remember_changes(self, checked)
        )
        self.settings_menu.addAction(self.remember_changes_action)

        # Add 'Check for updates at startup' option
        self.check_updates_action = QAction(texts.CHECK_FOR_UPDATES_AT_STARTUP, self)
        self.check_updates_action.setCheckable(True)
        self.check_updates_action.setChecked(
            self.config.get(
                "check_updates_startup", DEFAULT_OPTIONS["check_updates_startup"]
            )
        )
        self.check_updates_action.triggered.connect(
            lambda checked: update_config(self, "check_updates_startup", checked)
        )
        self.settings_menu.addAction(self.check_updates_action)

        # Reset option
        self.reset_action = QAction(texts.RESET_TO_DEFAULT_SETTINGS, self)
        self.reset_action.triggered.connect(lambda: reset_to_defaults(self))
        self.settings_menu.addAction(self.reset_action)

        self.settings_menu.addSeparator()

        # Add About option
        self.about_action = QAction(texts.ABOUT, self)
        self.about_action.triggered.connect(lambda: show_about_dialog(self))
        self.settings_menu.addAction(self.about_action)

        # Connect button click to show menu instead of setting the menu directly
        self.settings_btn.clicked.connect(self.show_settings_menu)
        self.settings_btn.show()
        self.setupAutoSyncTab()
        self.setupManualSyncTab()
        self.setLayout(outer_layout)
        self.update_auto_sync_ui_for_batch()  # Ensure correct UI for batch mode on startup

        # Connect tab change to update InputBox positions
        self.tab_widget.currentChanged.connect(self._update_inputbox_positions_on_tab)

    def _update_inputbox_positions_on_tab(self, index):
        # Find all InputBox instances in the current tab and trigger their resizeEvent
        current_widget = self.tab_widget.widget(index)
        if not current_widget:
            return

        def update_inputboxes(widget):
            for child in widget.findChildren(InputBox):
                # Trigger a resizeEvent to reposition buttons
                child.resizeEvent(None)

        update_inputboxes(current_widget)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "settings_btn"):
            self.settings_btn.move(self.width() - 36 - 15, 15)

    def change_language(self, language_code):
        """Handle language change with restart confirmation"""
        current_language = self.config.get("language", DEFAULT_OPTIONS["language"])

        # If the language is already selected, do nothing
        if current_language == language_code:
            return

        # Ask user if they want to restart the app
        reply = QMessageBox.question(
            self,
            texts.CHANGE_LANGUAGE_TITLE,
            texts.RESTART_APPLICATION_FOR_LANGUAGE_CHANGE,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Update the config
            self.config["language"] = language_code
            save_config(self.config)
            restart_application()
        else:
            # Revert the selection to the current language
            self.language_actions[current_language].setChecked(True)

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
        if hasattr(self, "_handle_shift_input_events"):
            if self._handle_shift_input_events(obj, event):
                return True
        return super().eventFilter(obj, event)

    def show_settings_menu(self):
        # Show the menu at the right position below the button
        self.settings_menu.popup(
            self.settings_btn.mapToGlobal(self.settings_btn.rect().bottomLeft())
        )

    def _create_sync_tracking_menu(self):
        """Create the Sync Tracking submenu in the settings menu."""
        # Create the submenu with dynamic title
        self.sync_tracking_menu = self.settings_menu.addMenu(texts.SYNC_TRACKING)
        self._update_sync_tracking_menu_title()

        # Toggle action (Enabled/Disabled)
        self.sync_tracking_toggle_action = QAction(self)
        self.sync_tracking_toggle_action.setCheckable(True)
        self._update_sync_tracking_toggle_text()
        self.sync_tracking_toggle_action.triggered.connect(
            self._on_skip_processed_changed
        )
        self.sync_tracking_menu.addAction(self.sync_tracking_toggle_action)

        # Clear database action
        self.sync_tracking_clear_action = QAction(
            texts.CLEAR_PROCESSED_ITEMS_DATABASE, self
        )
        self.sync_tracking_clear_action.triggered.connect(
            self._clear_processed_items_database
        )
        self.sync_tracking_menu.addAction(self.sync_tracking_clear_action)

        self.sync_tracking_menu.addSeparator()

        # Backup database action
        self.sync_tracking_backup_action = QAction(
            texts.BACKUP_PROCESSED_DATABASE, self
        )
        self.sync_tracking_backup_action.triggered.connect(
            self._backup_processed_database
        )
        self.sync_tracking_menu.addAction(self.sync_tracking_backup_action)

        # Import database action
        self.sync_tracking_import_action = QAction(
            texts.IMPORT_PROCESSED_DATABASE, self
        )
        self.sync_tracking_import_action.triggered.connect(
            self._import_processed_database
        )
        self.sync_tracking_menu.addAction(self.sync_tracking_import_action)

        self.sync_tracking_menu.addSeparator()

        # Manage library folders action
        self.sync_tracking_manage_library_action = QAction(
            texts.MANAGE_LIBRARY_FOLDERS, self
        )
        self.sync_tracking_manage_library_action.triggered.connect(
            self._open_library_manager
        )
        self.sync_tracking_menu.addAction(self.sync_tracking_manage_library_action)

    def _update_sync_tracking_menu_title(self):
        """Update the sync tracking submenu title based on enabled/disabled state."""
        is_enabled = self.config.get(
            "skip_previously_processed_videos",
            DEFAULT_OPTIONS["skip_previously_processed_videos"],
        )
        if is_enabled:
            title = f"{texts.SYNC_TRACKING} ({texts.ENABLED})"
        else:
            title = f"{texts.SYNC_TRACKING} ({texts.DISABLED})"
        self.sync_tracking_menu.setTitle(title)

    def _update_sync_tracking_toggle_text(self):
        """Update the sync tracking toggle action text and checked state."""
        is_enabled = self.config.get(
            "skip_previously_processed_videos",
            DEFAULT_OPTIONS["skip_previously_processed_videos"],
        )
        self.sync_tracking_toggle_action.setChecked(is_enabled)
        if is_enabled:
            self.sync_tracking_toggle_action.setText(texts.SYNC_TRACKING_ENABLED)
        else:
            self.sync_tracking_toggle_action.setText(texts.SYNC_TRACKING_DISABLED)

    def _on_skip_processed_changed(self, checked):
        """Handle skip previously processed items setting change."""
        update_config(self, "skip_previously_processed_videos", checked)
        # Update the settings menu submenu title and toggle text
        self._update_sync_tracking_menu_title()
        self._update_sync_tracking_toggle_text()
        # Update sync tracking button style
        if hasattr(self, "btn_sync_tracking"):
            from gui_batch_mode import _update_sync_tracking_button_style

            _update_sync_tracking_button_style(self)
        # Trigger re-scan of batch items if batch mode is enabled
        if hasattr(self, "batch_tree_view") and self.batch_mode_enabled:
            self.batch_tree_view.rescan_processed_items()

    def _open_library_manager(self):
        """Open the library manager dialog."""
        from gui_load_library import LibraryManagerDialog

        dialog = LibraryManagerDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Load library folders into batch mode if accepted
            if hasattr(self, "batch_tree_view") and self.batch_mode_enabled:
                from gui_batch_mode import smart_load_library

                smart_load_library(self)

    def _clear_processed_items_database(self):
        """Clear the processed items database after confirmation."""
        from processed_items_manager import get_processed_items_manager

        manager = get_processed_items_manager()
        count = manager.get_processed_count()

        reply = QMessageBox.question(
            self,
            texts.CLEAR_PROCESSED_ITEMS_DATABASE,
            texts.CLEAR_DATABASE_CONFIRM,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            if manager.clear_all():
                QMessageBox.information(
                    self,
                    texts.CLEAR_PROCESSED_ITEMS_DATABASE,
                    str(texts.DATABASE_CLEARED_SUCCESS).format(count=count),
                )
                # Re-scan batch items to update visual state
                if hasattr(self, "batch_tree_view") and self.batch_mode_enabled:
                    self.batch_tree_view.rescan_processed_items()

    def _backup_processed_database(self):
        """Backup the processed items database to a user-selected location."""
        from processed_items_manager import get_processed_items_manager
        import shutil

        manager = get_processed_items_manager()
        db_path = manager.get_db_path()

        if not os.path.exists(db_path):
            QMessageBox.warning(
                self, texts.BACKUP_PROCESSED_DATABASE, texts.DATABASE_NOT_FOUND
            )
            return

        # Open save dialog
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            texts.BACKUP_PROCESSED_DATABASE,
            "processed_items_backup.db",
            "Database Files (*.db)",
        )

        if save_path:
            try:
                shutil.copy2(db_path, save_path)
                QMessageBox.information(
                    self,
                    texts.BACKUP_PROCESSED_DATABASE,
                    str(texts.DATABASE_BACKUP_SUCCESS).format(path=save_path),
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    texts.ERROR,
                    str(texts.DATABASE_BACKUP_FAILED).format(error=str(e)),
                )

    def _import_processed_database(self):
        """Import items from another processed items database."""
        from processed_items_manager import get_processed_items_manager

        # Open file dialog to select database
        import_path, _ = QFileDialog.getOpenFileName(
            self, texts.IMPORT_PROCESSED_DATABASE, "", "Database Files (*.db)"
        )

        if import_path:
            manager = get_processed_items_manager()
            imported, skipped = manager.import_from_database(import_path)

            if imported >= 0:
                QMessageBox.information(
                    self,
                    texts.IMPORT_PROCESSED_DATABASE,
                    str(texts.DATABASE_IMPORT_SUCCESS).format(
                        imported=imported, skipped=skipped
                    ),
                )
                # Re-scan batch items to update visual state
                if hasattr(self, "batch_tree_view") and self.batch_mode_enabled:
                    self.batch_tree_view.rescan_processed_items()
            else:
                QMessageBox.warning(
                    self, texts.IMPORT_PROCESSED_DATABASE, texts.DATABASE_IMPORT_FAILED
                )
