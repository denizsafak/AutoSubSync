import os
import re
import logging
import texts
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileIconProvider,
    QSplitter,
    QWidget,
    QMessageBox,
    QScrollArea,
    QFrame,
    QMenu,
    QDialogButtonBox,
    QTreeWidget,
    QTreeWidgetItem,
)
from PyQt6.QtCore import Qt, QFileInfo
from PyQt6.QtGui import QColor
from constants import VIDEO_EXTENSIONS, SUBTITLE_EXTENSIONS, PROGRAM_NAME, COLORS
from utils import open_filedialog, open_folder

logger = logging.getLogger(__name__)

# Season/episode patterns for matching video/subtitle files
PATTERNS = [
    r"(?:s|S)(\d{1,2})(?:[eE])(\d{1,2})",  # S01E01, S1E1, etc.
    r"(?:s|S)(\d{1,2})(?:[bB])(\d{1,2})",  # S01B01, S1B1, etc.
    r"(\d{1,2})x(\d{1,2})",  # 1x01, 01x1, etc.
    r"(?:[eE][pP]?|EP)(\d{1,2})",  # E01, EP01 (assumes season 1)
    r"(?:[pP](?:art|t))(\d{1,2})",  # Part01, Pt1 (assumes season 1)
    r"(?<!\d)([1-9])(\d{2})(?!\d)",  # 101, 201, etc.
]


def extract_season_episode(filename):
    """Extract season and episode from filename."""
    base = os.path.basename(filename).lower()
    for i, pattern in enumerate(PATTERNS):
        if match := re.search(pattern, base):
            if i in [3, 4]:  # Episode/Part only (assumes season 1)
                episode = int(match.group(1))
                return 1, episode, f"s1e{episode:02d}"
            else:
                season, episode = int(match.group(1)), int(match.group(2))
                return season, episode, f"s{season:02d}e{episode:02d}"
    return None, None, None


def collect_files_from_paths(paths, allowed_extensions, prioritize_videos=False):
    """Collect valid files from paths (files or directories)."""
    all_files = []
    for path in paths:
        if os.path.isdir(path):
            for root, _, filenames in os.walk(path):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    if os.path.splitext(file_path)[1].lower() in allowed_extensions:
                        all_files.append(file_path)
        elif (
            os.path.isfile(path)
            and os.path.splitext(path)[1].lower() in allowed_extensions
        ):
            all_files.append(path)

    # Sort to prioritize video files first if requested
    if prioritize_videos:
        all_files.sort(
            key=lambda f: (
                os.path.splitext(f)[1].lower()
                not in VIDEO_EXTENSIONS,  # Videos first (False sorts before True)
                os.path.basename(f).lower(),  # Then alphabetically
            )
        )

    return all_files


def get_list_components(dialog, is_reference):
    """Get UI components for reference or subtitle list."""
    prefix = "ref" if is_reference else "sub"
    return {
        "list": dialog.reference_files if is_reference else dialog.subtitle_files,
        "widget": dialog.ref_list_widget if is_reference else dialog.sub_list_widget,
        "input_box": getattr(dialog, f"{prefix}_input_box"),
        "buttons": getattr(dialog, f"{prefix}_buttons_widget"),
        "remove_btn": getattr(dialog, f"{prefix}_remove_selected_btn"),
        "move_btn": getattr(dialog, f"{prefix}_move_to_other_btn"),
        "allowed_ext": (
            (VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS)
            if is_reference
            else SUBTITLE_EXTENSIONS
        ),
        "type": "reference" if is_reference else "subtitle",
    }


def toggle_ui_visibility(widget, buttons, input_box, show_list):
    """Toggle visibility between list view and input box."""
    if show_list:
        input_box.setHidden(True)
        buttons.setHidden(False)
        widget.setHidden(False)
    else:
        widget.setHidden(True)
        buttons.setHidden(True)
        input_box.setHidden(False)


class AutoPairingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle(f"{PROGRAM_NAME} - {texts.AUTO_PAIRING_SEASON_EPISODE}")
        self.resize(900, 700)
        self.setMinimumSize(600, 500)

        self.reference_files, self.subtitle_files, self.paired_items = [], [], {}
        self.icon_provider = QFileIconProvider()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        # Explanation section
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMaximumHeight(100)

        exp_widget = QWidget()
        exp_layout = QVBoxLayout(exp_widget)
        exp_layout.setContentsMargins(0, 0, 0, 0)
        exp_layout.addWidget(QLabel(f"<h2>{texts.HOW_THE_PAIRING_WORKS}</h2>"))
        desc = QLabel(
            texts.HOW_THE_PAIRING_WORKS_DESC.format(program_name=PROGRAM_NAME)
        )
        desc.setWordWrap(True)
        exp_layout.addWidget(desc)
        exp_layout.addStretch()
        scroll.setWidget(exp_widget)
        layout.addWidget(scroll)

        # Main panels with file lists
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(15)

        # Create file list widgets and panels
        self.ref_list_widget = self._create_tree_widget()
        self.sub_list_widget = self._create_tree_widget()

        for i, (name, widget) in enumerate(
            [
                (texts.VIDEO_OR_SUBTITLE_FILES_LABEL, self.ref_list_widget),
                (texts.SUBTITLE_FILES_LABEL, self.sub_list_widget),
            ]
        ):
            panel = self._create_file_panel(name, widget, i == 0)
            splitter.addWidget(panel)

        splitter.setSizes([450, 450])
        layout.addWidget(splitter)

        # Bottom section
        bottom_layout = QHBoxLayout()
        self.pairs_count_label = QLabel("")
        self.pairs_count_label.setStyleSheet("color: grey; font-size: 12px;")
        bottom_layout.addWidget(self.pairs_count_label)
        bottom_layout.addStretch()

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.add_pairs_to_batch)
        button_box.rejected.connect(self.close)
        self.btn_add_pairs = button_box.button(QDialogButtonBox.StandardButton.Ok)
        bottom_layout.addWidget(button_box)
        layout.addLayout(bottom_layout)

        self.update_ui_state()
        self.update_header_labels()

    def _create_tree_widget(self):
        """Create and configure a tree widget for file lists."""
        widget = QTreeWidget()
        widget.setHeaderHidden(False)
        widget.setColumnCount(1)
        widget.setRootIsDecorated(False)
        widget.setStyleSheet("QTreeView::item { height: 32px; }")
        widget.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        widget.setHidden(True)
        widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        return widget

    def _create_file_panel(self, name, widget, is_reference):
        """Create a file panel with input box, buttons, and tree widget."""
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 10, 0, 10)
        panel_layout.setSpacing(10)

        # Input box with drag & drop support
        if is_reference:
            input_text = texts.DRAG_DROP_VIDEO_SUBTITLE_FILES_OR_CLICK
        else:
            input_text = texts.DRAG_DROP_SUBTITLE_FILES_OR_CLICK
        input_box = self.parent_window.InputBox(
            parent=self,
            label=name,
            text=input_text,
            input_type="video_or_subtitle" if is_reference else "subtitle",
        )
        input_box.mousePressEvent = lambda e: self.show_add_menu(e, is_reference)
        input_box.dropEvent = lambda e: self._handle_drop(e, is_reference)

        # Button panel
        buttons = self._create_button_panel(is_reference)

        # Connect widget events
        widget.itemSelectionChanged.connect(
            lambda: self.on_selection_changed(is_reference)
        )
        widget.customContextMenuRequested.connect(
            lambda pos: self.show_context_menu(pos, is_reference)
        )
        self._setup_list_drag_drop(widget, is_reference)

        # Store references
        prefix = "ref" if is_reference else "sub"
        setattr(self, f"{prefix}_input_box", input_box)
        setattr(self, f"{prefix}_buttons_widget", buttons)
        setattr(
            self,
            f"{prefix}_remove_selected_btn",
            buttons.findChild(QPushButton, "remove"),
        )
        setattr(
            self, f"{prefix}_move_to_other_btn", buttons.findChild(QPushButton, "move")
        )

        panel_layout.addWidget(input_box)
        panel_layout.addWidget(buttons)
        panel_layout.addWidget(widget)
        return panel

    def _create_button_panel(self, is_reference):
        """Create button panel for file operations."""
        buttons = QWidget()
        buttons.setHidden(True)
        btn_layout = QHBoxLayout(buttons)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(5)

        add_files_btn = QPushButton(texts.ADD_FILES)
        add_files_btn.clicked.connect(lambda: self.show_add_menu_button(is_reference))

        remove_btn = QPushButton(texts.REMOVE_SELECTED)
        remove_btn.setObjectName("remove")
        remove_btn.setEnabled(False)
        remove_btn.clicked.connect(lambda: self.remove_selected(is_reference))

        move_btn = QPushButton("⇄")
        move_btn.setFixedWidth(30)
        move_btn.setObjectName("move")
        move_btn.setToolTip(texts.MOVE_SELECTED_ITEMS_TO_OTHER_LIST)
        move_btn.setEnabled(False)
        move_btn.clicked.connect(lambda: self.move_to_other_list(is_reference))

        btn_layout.addWidget(add_files_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addWidget(move_btn)
        btn_layout.addStretch()

        return buttons

    def update_header_labels(self):
        """Update the header labels with file counts."""
        self.ref_list_widget.setHeaderLabel(
            texts.VIDEO_REFERENCE_SUBTITLES_TOTAL.format(
                count=len(self.reference_files)
            )
        )
        self.sub_list_widget.setHeaderLabel(
            texts.SUBTITLE_FILES_TOTAL.format(count=len(self.subtitle_files))
        )

    def show_add_menu(self, event, is_reference):
        """Show context menu for adding files."""
        menu = QMenu(self)
        menu.addAction(
            texts.ADD_MULTIPLE_FILES, lambda: self.add_files_dialog(is_reference)
        )
        menu.addAction(texts.ADD_FOLDER, lambda: self.add_folder(is_reference))
        menu.popup(event.globalPosition().toPoint())

    def show_add_menu_button(self, is_reference):
        """Show context menu when Add Files button is clicked."""
        menu = QMenu(self)
        menu.addAction(
            texts.ADD_MULTIPLE_FILES, lambda: self.add_files_dialog(is_reference)
        )
        menu.addAction(texts.ADD_FOLDER, lambda: self.add_folder(is_reference))

        button = (
            self.ref_buttons_widget if is_reference else self.sub_buttons_widget
        ).findChildren(QPushButton)[0]
        menu.popup(button.mapToGlobal(button.rect().bottomLeft()))

    def on_selection_changed(self, is_reference):
        """Handle selection change in list widgets."""
        components = get_list_components(self, is_reference)
        has_selection = bool(components["widget"].selectedItems())
        components["remove_btn"].setEnabled(has_selection)
        components["move_btn"].setEnabled(has_selection)

    def show_context_menu(self, position, is_reference):
        """Show context menu for list widget."""
        components = get_list_components(self, is_reference)

        menu = QMenu(self)
        add_files_menu = menu.addMenu(texts.ADD_FILES)
        add_files_menu.addAction(
            texts.ADD_MULTIPLE_FILES, lambda: self.add_files_dialog(is_reference)
        )
        add_files_menu.addAction(
            texts.ADD_FOLDER, lambda: self.add_folder(is_reference)
        )

        menu.addSeparator()

        has_selection = bool(components["widget"].selectedItems())
        move_action = menu.addAction(texts.MOVE_TO_OTHER_LIST)
        move_action.setEnabled(has_selection)
        move_action.triggered.connect(lambda: self.move_to_other_list(is_reference))

        remove_action = menu.addAction(texts.REMOVE_SELECTED)
        remove_action.setEnabled(has_selection)
        remove_action.triggered.connect(lambda: self.remove_selected(is_reference))

        menu.addSeparator()

        # Add "Go to folder" option for any selected item
        if has_selection:
            go_to_folder_action = menu.addAction(texts.GO_TO_FOLDER)
            go_to_folder_action.triggered.connect(
                lambda: self.go_to_folder(components["widget"].selectedItems()[0])
            )

        menu.addAction(texts.CLEAR_ALL, lambda: self.clear_files(is_reference))
        menu.popup(components["widget"].mapToGlobal(position))

    def _handle_drop(self, event, is_reference):
        """Handle drop events on input boxes and list widgets."""
        if event.mimeData().hasUrls():
            paths = [
                url.toLocalFile()
                for url in event.mimeData().urls()
                if url.isLocalFile()
            ]
            allowed = (
                (VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS)
                if is_reference
                else SUBTITLE_EXTENSIONS
            )
            all_files = collect_files_from_paths(
                paths, allowed, prioritize_videos=is_reference
            )

            if all_files:
                self.add_files(is_reference, all_files)

            event.acceptProposedAction()

    def _setup_list_drag_drop(self, widget, is_reference):
        """Setup drag and drop for list widget."""
        widget.setAcceptDrops(True)
        widget.viewport().setAcceptDrops(True)
        widget.setDropIndicatorShown(True)
        widget.setDragEnabled(False)
        widget.setDragDropMode(QTreeWidget.DragDropMode.DropOnly)

        widget.dragEnterEvent = lambda e: (
            e.acceptProposedAction() if e.mimeData().hasUrls() else e.ignore()
        )
        widget.dragMoveEvent = lambda e: (
            e.acceptProposedAction() if e.mimeData().hasUrls() else e.ignore()
        )
        widget.dropEvent = lambda e: self._handle_drop(e, is_reference)

    def remove_selected(self, is_reference):
        """Remove selected items from the specified list."""
        components = get_list_components(self, is_reference)
        selected_items = components["widget"].selectedItems()
        if not selected_items:
            return

        # Remove files from the file list and widget
        for item in selected_items:
            file_path = item.data(0, Qt.ItemDataRole.UserRole)
            if file_path in components["list"]:
                components["list"].remove(file_path)
            root = components["widget"].invisibleRootItem()
            root.removeChild(item)

        # If no items left, hide widget and show input box
        if components["widget"].topLevelItemCount() == 0:
            toggle_ui_visibility(
                components["widget"],
                components["buttons"],
                components["input_box"],
                False,
            )

        self.pair_files()
        self.update_ui_state()
        self.update_header_labels()

    def move_to_other_list(self, is_reference):
        """Move selected items to the other list."""
        source = get_list_components(self, is_reference)
        target = get_list_components(self, not is_reference)

        selected_items = source["widget"].selectedItems()
        if not selected_items:
            return

        files_to_move = []
        items_to_remove = []
        errors = {"duplicate_episode": [], "moving_video": []}

        # Collect files and items to move
        for item in selected_items:
            file_path = item.data(0, Qt.ItemDataRole.UserRole)
            if file_path in source["list"]:
                ext = os.path.splitext(file_path)[1].lower()

                # Check if trying to move video file from reference to subtitle list
                if is_reference and ext in VIDEO_EXTENSIONS:
                    errors["moving_video"].append(os.path.basename(file_path))
                elif ext in target["allowed_ext"] and file_path not in target["list"]:
                    # Check for duplicate season-episode in target list
                    season, episode, _ = extract_season_episode(file_path)
                    if season and episode:
                        existing_episodes = {
                            extract_season_episode(f)[:2]
                            for f in target["list"]
                            if extract_season_episode(f)[0]
                        }

                        if (season, episode) not in existing_episodes:
                            files_to_move.append(file_path)
                            items_to_remove.append(item)
                        else:
                            errors["duplicate_episode"].append(
                                os.path.basename(file_path)
                            )
                    else:
                        files_to_move.append(file_path)
                        items_to_remove.append(item)

        # Show error messages if any
        error_messages = []
        if errors["moving_video"]:
            error_messages.append(
                texts.SKIPPED_FILES_VIDEO_CANT_MOVE.format(
                    count=len(errors["moving_video"])
                )
            )
        if errors["duplicate_episode"]:
            error_messages.append(
                texts.SKIPPED_FILES_DUPLICATE_EPISODE.format(
                    count=len(errors["duplicate_episode"])
                )
            )

        if error_messages:
            QMessageBox.warning(self, texts.MOVE_ERRORS, "\n".join(error_messages))

        if not files_to_move:
            return

        # Move files
        for i, file_path in enumerate(files_to_move):
            source["list"].remove(file_path)
            root = source["widget"].invisibleRootItem()
            root.removeChild(items_to_remove[i])

            target["list"].append(file_path)
            season, episode, original_match = extract_season_episode(file_path)
            name = f"[{original_match.upper()}] {os.path.basename(file_path)}"

            item = QTreeWidgetItem([name])
            item.setData(0, Qt.ItemDataRole.UserRole, file_path)
            item.setIcon(0, self.icon_provider.icon(QFileInfo(file_path)))
            item.setToolTip(0, file_path)
            target["widget"].addTopLevelItem(item)

        # Update UI visibility
        if source["widget"].topLevelItemCount() == 0:
            toggle_ui_visibility(
                source["widget"], source["buttons"], source["input_box"], False
            )

        if target["widget"].topLevelItemCount() > 0:
            toggle_ui_visibility(
                target["widget"], target["buttons"], target["input_box"], True
            )

        self.pair_files()
        self.update_ui_state()
        self.update_header_labels()

    def add_files_dialog(self, is_reference):
        """Show file dialog to add files."""
        files = open_filedialog(
            self.parent_window,
            "files-open",
            (
                texts.SELECT_VIDEO_OR_SUBTITLE_FILE_TITLE
                if is_reference
                else texts.SELECT_SUBTITLE_FILE_TITLE
            ),
            (
                f"{texts.VIDEO_OR_SUBTITLE_FILES_LABEL if is_reference else texts.SUBTITLE_FILES_LABEL} (*{' *'.join(VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS)})"
                if is_reference
                else f"{texts.SUBTITLE_FILES_LABEL} (*{' *'.join(SUBTITLE_EXTENSIONS)})"
            ),
        )
        if files:
            self.add_files(is_reference, files)

    def add_files(self, is_reference=True, files=None):
        """Add files to reference or subtitle list."""
        if not files:
            return

        file_list = self.reference_files if is_reference else self.subtitle_files
        widget = self.ref_list_widget if is_reference else self.sub_list_widget
        input_box = self.ref_input_box if is_reference else self.sub_input_box
        buttons = self.ref_buttons_widget if is_reference else self.sub_buttons_widget
        allowed = (
            (VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS)
            if is_reference
            else SUBTITLE_EXTENSIONS
        )
        list_type = texts.REFERENCE if is_reference else texts.SUBTITLE

        # Statistics for detailed reporting
        stats = {
            "invalid_extension": 0,
            "already_in_list": 0,
            "already_in_other_list": 0,
            "no_season_episode": 0,
            "duplicate_season_episode": 0,
            "added": 0,
        }

        # Filter valid files by extension
        valid_extensions = [
            f
            for f in files
            if os.path.isfile(f) and os.path.splitext(f)[1].lower() in allowed
        ]
        stats["invalid_extension"] = len(files) - len(valid_extensions)

        if not valid_extensions:
            if stats["invalid_extension"] > 0:
                QMessageBox.warning(
                    self,
                    texts.INVALID_FILE_TYPE_TITLE,
                    texts.NONE_OF_SELECTED_FILES_HAVE_VALID_EXTENSIONS.format(
                        list_type=list_type
                    ),
                )
            return

        # Check for duplicates in the same list
        unique_in_list = []
        for f in valid_extensions:
            if f in file_list:
                stats["already_in_list"] += 1
            else:
                unique_in_list.append(f)

        # Check for duplicates between the two lists
        other_list = self.subtitle_files if is_reference else self.reference_files
        unique_files = []
        for f in unique_in_list:
            if f in other_list:
                stats["already_in_other_list"] += 1
            else:
                unique_files.append(f)

        if not unique_files:
            QMessageBox.warning(
                self,
                texts.DUPLICATES_SKIPPED_TITLE,
                texts.ALL_FILES_ALREADY_IN_LISTS.format(list_type=list_type),
            )
            return

        # Process files with season/episode info and check for duplicates
        files_with_episodes = []
        existing_episodes = {
            extract_season_episode(f)[:2]
            for f in file_list
            if extract_season_episode(f)[0]
        }

        for file_path in unique_files:
            season, episode, original_match = extract_season_episode(file_path)
            if season and episode:
                if (season, episode) not in existing_episodes:
                    files_with_episodes.append(file_path)
                    existing_episodes.add((season, episode))
                else:
                    stats["duplicate_season_episode"] += 1
            else:
                stats["no_season_episode"] += 1

        stats["added"] = len(files_with_episodes)

        # Update UI and add files if any are valid
        if files_with_episodes:
            input_box.setHidden(True)
            buttons.setHidden(False)
            widget.setHidden(False)

            for path in files_with_episodes:
                file_list.append(path)
                season, episode, original_match = extract_season_episode(path)
                name = f"[{original_match.upper()}] {os.path.basename(path)}"

                item = QTreeWidgetItem([name])
                item.setData(0, Qt.ItemDataRole.UserRole, path)
                item.setIcon(0, self.icon_provider.icon(QFileInfo(path)))
                item.setToolTip(0, path)
                widget.addTopLevelItem(item)

            # Update pairing and UI state
            self.pair_files()
            self.update_ui_state()
            self.update_header_labels()

        # Show import summary message only if there are skipped items to report
        skipped = (
            stats["invalid_extension"]
            + stats["already_in_list"]
            + stats["already_in_other_list"]
            + stats["no_season_episode"]
            + stats["duplicate_season_episode"]
        )

        if skipped > 0:
            message_parts = []

            if stats["added"] > 0:
                message_parts.append(
                    texts.SUCCESSFULLY_ADDED_FILES.format(count=stats["added"])
                )

            if stats["no_season_episode"] > 0:
                message_parts.append(
                    texts.SKIPPED_FILES_MISSING_SEASON_EPISODE.format(
                        count=stats["no_season_episode"]
                    )
                )

            if stats["duplicate_season_episode"] > 0:
                message_parts.append(
                    texts.SKIPPED_FILES_DUPLICATE_EPISODE.format(
                        count=stats["duplicate_season_episode"]
                    )
                )

            if stats["already_in_list"] > 0:
                message_parts.append(
                    texts.SKIPPED_FILES_ALREADY_IN_THIS_LIST.format(
                        count=stats["already_in_list"]
                    )
                )

            if stats["already_in_other_list"] > 0:
                message_parts.append(
                    texts.SKIPPED_FILES_ALREADY_IN_OTHER_LIST.format(
                        count=stats["already_in_other_list"]
                    )
                )

            if stats["invalid_extension"] > 0:
                message_parts.append(
                    texts.SKIPPED_FILES_INVALID_EXTENSION.format(
                        count=stats["invalid_extension"]
                    )
                )

            # Show appropriate message based on whether any files were added
            if stats["added"] > 0:
                QMessageBox.information(
                    self, texts.IMPORT_SUMMARY, "\n".join(message_parts)
                )
            else:
                QMessageBox.warning(
                    self, texts.IMPORT_SUMMARY, "\n".join(message_parts)
                )

    def add_folder(self, is_reference):
        """Add files from folder."""
        folder = open_filedialog(
            self.parent_window,
            "directory",
            texts.SELECT_FOLDER_CONTAINING_MEDIA_FILES_TITLE,
        )
        if not folder:
            return

        allowed = (
            (VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS)
            if is_reference
            else SUBTITLE_EXTENSIONS
        )
        files = collect_files_from_paths(
            [folder], allowed, prioritize_videos=is_reference
        )
        self.add_files(is_reference, files)

    def clear_files(self, is_reference):
        """Clear files from list."""
        components = get_list_components(self, is_reference)
        components["list"].clear()
        components["widget"].clear()
        toggle_ui_visibility(
            components["widget"], components["buttons"], components["input_box"], False
        )

        self.paired_items = {}
        self.update_pairing_display()
        self.update_ui_state()
        self.update_header_labels()

    def pair_files(self):
        """Auto-pair files by season/episode."""
        self.paired_items = {}

        # Build lookup dictionaries
        ref_dict = {}
        for path in self.reference_files:
            season, episode, _ = extract_season_episode(path)
            if season and episode:
                ref_dict.setdefault((season, episode), []).append(path)

        sub_dict = {}
        for path in self.subtitle_files:
            season, episode, _ = extract_season_episode(path)
            if season and episode:
                sub_dict.setdefault((season, episode), []).append(path)

        # Match files
        for key, ref_files in ref_dict.items():
            if key in sub_dict:
                for ref in ref_files:
                    for sub in sub_dict[key]:
                        if sub not in self.paired_items.values():
                            self.paired_items[ref] = sub
                            break

        self.update_pairing_display()

    def update_pairing_display(self):
        """Update visual pairing display and sort items with paired ones first."""
        green = QColor(
            *[int(x) for x in re.findall(r"\d+", COLORS["GREEN_BACKGROUND_HOVER"])[:3]],
            int(
                float(re.findall(r"[\d.]+", COLORS["GREEN_BACKGROUND_HOVER"])[-1]) * 255
            ),
        )

        for widget, check in [
            (self.ref_list_widget, lambda p: p in self.paired_items),
            (self.sub_list_widget, lambda p: p in self.paired_items.values()),
        ]:
            # Collect all items with their data
            items_data = []
            for i in range(widget.topLevelItemCount()):
                item = widget.topLevelItem(i)
                path = item.data(0, Qt.ItemDataRole.UserRole)
                is_paired = check(path)
                items_data.append((item.text(0), path, item.icon(0), is_paired))

            # Sort items: paired first, then by season/episode order
            items_data.sort(
                key=lambda x: (not x[3], x[0])
            )  # not x[3] puts paired (True) first

            # Clear widget and re-add sorted items
            widget.clear()
            for text, path, icon, is_paired in items_data:
                new_item = QTreeWidgetItem([text])
                new_item.setData(0, Qt.ItemDataRole.UserRole, path)
                new_item.setIcon(0, icon)
                new_item.setToolTip(0, path)
                new_item.setBackground(
                    0, green if is_paired else QColor(Qt.GlobalColor.transparent)
                )
                widget.addTopLevelItem(new_item)

    def update_ui_state(self):
        """Update UI state."""
        # Update remove buttons based on actual selection state
        ref_has_selection = bool(self.ref_list_widget.selectedItems())
        sub_has_selection = bool(self.sub_list_widget.selectedItems())

        self.ref_remove_selected_btn.setEnabled(ref_has_selection)
        self.sub_remove_selected_btn.setEnabled(sub_has_selection)
        self.btn_add_pairs.setEnabled(bool(self.paired_items))

        # Update pairs count label (only show when > 0 pairs)
        pairs_count = len(self.paired_items)
        if pairs_count > 0:
            self.pairs_count_label.setText(
                texts.TOTAL_VALID_PAIRS.format(pairs_count=pairs_count)
            )
            self.pairs_count_label.setVisible(True)
        else:
            self.pairs_count_label.setVisible(False)

    def add_pairs_to_batch(self):
        """Add pairs to batch processing."""
        if not self.paired_items:
            QMessageBox.information(
                self, texts.NO_VALID_PAIRS_TITLE, texts.NO_VALID_PAIRS_MESSAGE
            )
            return

        batch_view = self.parent_window.batch_tree_view
        pairs_added = 0

        for ref, sub in self.paired_items.items():
            if not batch_view.is_duplicate_pair(ref, sub):
                batch_view.add_explicit_pair(ref, sub)
                pairs_added += 1

        if pairs_added > 0:
            self.close()
        else:
            QMessageBox.information(
                self, texts.NO_NEW_PAIRS, texts.ALL_PAIRS_ALREADY_EXIST_IN_BATCH
            )

    def go_to_folder(self, item):
        """Open the folder containing the file for the given item."""
        if not item:
            return

        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(
                self,
                texts.FILE_NOT_FOUND_TITLE,
                texts.FILE_NOT_FOUND_MESSAGE,
            )
            return

        open_folder(file_path, self)


def attach_functions_to_autosubsyncapp(autosubsyncapp_class):
    """Attach auto-pairing functions."""
    autosubsyncapp_class.open_auto_pairing_dialog = lambda self: AutoPairingDialog(
        self
    ).exec()
