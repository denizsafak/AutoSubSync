import os
import logging
import texts
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileIconProvider,
    QWidget,
    QMessageBox,
    QMenu,
    QDialogButtonBox,
    QTreeWidget,
    QTreeWidgetItem,
    QSplitter,
    QScrollArea,
    QFrame,
)
from PyQt6.QtCore import Qt, QFileInfo
from constants import VIDEO_EXTENSIONS, SUBTITLE_EXTENSIONS, PROGRAM_NAME
from utils import open_filedialog, open_folder

logger = logging.getLogger(__name__)


def _collect_files_from_paths(paths, allowed_extensions):
    """Collect valid files from files and directories by allowed extensions."""
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
    return all_files


class MultipleSubsDialog(QDialog):
    """Dialog to pair one reference (video or reference subtitle) with multiple subtitles."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle(
            f"{PROGRAM_NAME} - {texts.PAIR_MULTIPLE_SUBTITLES_WITH_SINGLE_SOURCE}"
        )
        self.resize(850, 600)

        self.icon_provider = QFileIconProvider()
        self.subtitle_files = []
        self._init_ui()

    # --- UI construction ---
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        # Explanation section (similar to auto pairing dialog)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMaximumHeight(100)

        exp_widget = QWidget()
        exp_layout = QVBoxLayout(exp_widget)
        exp_layout.setContentsMargins(0, 0, 0, 0)
        exp_layout.addWidget(QLabel(f"<h2>{texts.HOW_THE_PAIRING_WORKS}</h2>"))

        # Custom description specific to this dialog
        desc = QLabel(
            text=texts.MULTIPLE_SUBTITLES_DESC.format(program_name=PROGRAM_NAME)
        )
        desc.setWordWrap(True)
        exp_layout.addWidget(desc)
        exp_layout.addStretch()
        scroll.setWidget(exp_widget)
        layout.addWidget(scroll)

        # Panels in a splitter for a consistent layout with auto pairing
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(15)

        # Left: reference input (single)
        ref_panel = QWidget()
        ref_layout = QVBoxLayout(ref_panel)
        ref_layout.setContentsMargins(0, 0, 0, 0)
        ref_layout.setSpacing(10)

        # Use the app's InputBox but subclass to catch set/reset events for UI updates
        parent_input_cls = self.parent_window.InputBox if self.parent_window else QLabel

        dialog = self

        class ReferenceInputBox(parent_input_cls):
            def set_file(self, file_path):  # type: ignore[override]
                super().set_file(file_path)
                # Ensure the selected reference isn't listed among subtitles
                dialog._on_reference_changed(file_path)
                dialog._update_ui_state()

            def reset_to_default(self):  # type: ignore[override]
                super().reset_to_default()
                dialog._update_ui_state()

        self.ref_input = ReferenceInputBox(
            parent=self,
            label=texts.VIDEO_OR_SUBTITLE_FILES_LABEL,
            text=texts.DRAG_DROP_VIDEO_SUBTITLE_FILES,
            input_type="video_or_subtitle",
        )
        # Click to open single file selector directly (no menu)
        self.ref_input.mousePressEvent = lambda e: self._select_reference_file(
            "file-open"
        )
        ref_layout.addWidget(self.ref_input)

        splitter.addWidget(ref_panel)

        # Right: subtitles list (multiple)
        sub_panel = QWidget()
        sub_layout = QVBoxLayout(sub_panel)
        sub_layout.setContentsMargins(0, 0, 0, 0)
        sub_layout.setSpacing(10)

        # Buttons panel at top (similar to auto pairing)
        sub_buttons_widget = QWidget()
        sub_buttons_layout = QHBoxLayout(sub_buttons_widget)
        sub_buttons_layout.setContentsMargins(0, 0, 0, 0)
        sub_buttons_layout.setSpacing(5)

        btn_add_files = QPushButton(texts.ADD_FILES)
        btn_add_files.clicked.connect(self._show_add_subs_menu_button)

        btn_remove = QPushButton(texts.REMOVE_SELECTED)
        btn_remove.setEnabled(False)
        btn_remove.clicked.connect(self._remove_selected_subtitles)

        btn_clear = QPushButton(texts.CLEAR_ALL)
        btn_clear.clicked.connect(self._clear_subtitles)

        sub_buttons_layout.addWidget(btn_add_files)
        sub_buttons_layout.addWidget(btn_remove)
        sub_buttons_layout.addStretch()
        sub_buttons_layout.addWidget(btn_clear)

        # Add buttons first, then list
        sub_layout.addWidget(sub_buttons_widget)
        self.sub_list = self._create_tree_widget()
        sub_layout.addWidget(self.sub_list)

        # Save refs for state updates and menu anchor
        self._sub_remove_btn = btn_remove
        self._sub_add_files_btn = btn_add_files

        splitter.addWidget(sub_panel)
        splitter.setSizes([450, 450])
        layout.addWidget(splitter)

        # Footer
        footer = QHBoxLayout()
        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: grey; font-size: 12px;")
        footer.addWidget(self.count_label)
        footer.addStretch()

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._add_pairs_to_batch)
        button_box.rejected.connect(self.close)
        self.btn_ok = button_box.button(QDialogButtonBox.StandardButton.Ok)
        footer.addWidget(button_box)
        layout.addLayout(footer)

        # Context menu and drag-drop for subtitles list
        self.sub_list.itemSelectionChanged.connect(self._on_sub_selection_changed)
        self.sub_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sub_list.customContextMenuRequested.connect(
            self._show_subtitles_context_menu
        )
        self._setup_list_drag_drop()

        self._update_headers()
        self._update_ui_state()

    def _create_tree_widget(self):
        widget = QTreeWidget()
        widget.setHeaderHidden(False)
        widget.setColumnCount(1)
        widget.setRootIsDecorated(False)
        widget.setStyleSheet("QTreeView::item { height: 32px; }")
        widget.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        return widget

    def _select_reference_file(self, mode):
        if mode == "folder":
            folder = open_filedialog(
                self.parent_window,
                "directory",
                texts.SELECT_FOLDER_CONTAINING_MEDIA_FILES_TITLE,
            )
            if not folder:
                return
            files = _collect_files_from_paths(
                [folder], VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS
            )
            if not files:
                QMessageBox.warning(
                    self,
                    texts.NO_MEDIA_FILES_FOUND_TITLE,
                    texts.NO_MEDIA_FILES_FOUND_MESSAGE,
                )
                return
            # Prefer a video if available
            files.sort(
                key=lambda f: os.path.splitext(f)[1].lower() not in VIDEO_EXTENSIONS,
            )
            self.ref_input.set_file(files[0])
        else:
            file_path = open_filedialog(
                self.parent_window,
                "file-open",
                texts.SELECT_VIDEO_OR_SUBTITLE_FILE_TITLE,
                f"{texts.VIDEO_OR_SUBTITLE_FILES_LABEL} (*{' *'.join(VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS)})",
            )
            if file_path:
                self.ref_input.set_file(file_path)

    def _show_add_subs_menu_button(self):
        """Show dropdown menu anchored to the top Add Files button (like auto pairing)."""
        menu = QMenu(self)
        menu.addAction(texts.ADD_MULTIPLE_FILES, self._add_subtitle_files_dialog)
        menu.addAction(texts.ADD_FOLDER, self._add_subtitle_folder)
        btn = getattr(self, "_sub_add_files_btn", None)
        if btn:
            menu.popup(btn.mapToGlobal(btn.rect().bottomLeft()))
        else:
            menu.popup(self.mapToGlobal(self.rect().center()))

    # --- Subtitles list interactions ---
    def _setup_list_drag_drop(self):
        w = self.sub_list
        w.setAcceptDrops(True)
        w.viewport().setAcceptDrops(True)
        w.setDropIndicatorShown(True)
        w.setDragEnabled(False)
        w.setDragDropMode(QTreeWidget.DragDropMode.DropOnly)

        w.dragEnterEvent = lambda e: (
            e.acceptProposedAction() if e.mimeData().hasUrls() else e.ignore()
        )
        w.dragMoveEvent = lambda e: (
            e.acceptProposedAction() if e.mimeData().hasUrls() else e.ignore()
        )
        w.dropEvent = self._handle_subtitles_drop

    def _handle_subtitles_drop(self, event):
        if event.mimeData().hasUrls():
            paths = [
                u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()
            ]
            files = _collect_files_from_paths(paths, SUBTITLE_EXTENSIONS)
            if files:
                self._add_subtitles(files)
            event.acceptProposedAction()

    def _add_subtitle_files_dialog(self):
        files = open_filedialog(
            self.parent_window,
            "files-open",
            texts.SELECT_SUBTITLE_FILE_TITLE,
            f"{texts.SUBTITLE_FILES_LABEL} (*{' *'.join(SUBTITLE_EXTENSIONS)})",
        )
        if files:
            self._add_subtitles(files)

    def _add_subtitle_folder(self):
        folder = open_filedialog(
            self.parent_window,
            "directory",
            texts.SELECT_FOLDER_CONTAINING_MEDIA_FILES_TITLE,
        )
        if not folder:
            return
        files = _collect_files_from_paths([folder], SUBTITLE_EXTENSIONS)
        if files:
            self._add_subtitles(files)
        else:
            QMessageBox.warning(
                self,
                texts.NO_MEDIA_FILES_FOUND_TITLE,
                texts.NO_MEDIA_FILES_FOUND_MESSAGE,
            )

    def _add_subtitles(self, files):
        # Deduplicate, keep order
        added = 0
        skipped_ext = 0
        skipped_dups = 0
        skipped_same_as_ref = 0
        ref_path = getattr(self.ref_input, "file_path", None)
        for f in files:
            if not os.path.isfile(f):
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext not in SUBTITLE_EXTENSIONS:
                skipped_ext += 1
                continue
            # Do not allow adding the selected reference file to the subtitles list
            if ref_path and os.path.normpath(f) == os.path.normpath(ref_path):
                skipped_same_as_ref += 1
                continue
            if f not in self.subtitle_files:
                self.subtitle_files.append(f)
                item = QTreeWidgetItem([os.path.basename(f)])
                item.setData(0, Qt.ItemDataRole.UserRole, f)
                item.setIcon(0, self.icon_provider.icon(QFileInfo(f)))
                item.setToolTip(0, f)
                self.sub_list.addTopLevelItem(item)
                added += 1
            else:
                skipped_dups += 1
        # Inform about any skipped files (extensions or duplicates)
        if skipped_ext or skipped_dups or skipped_same_as_ref:
            parts = []
            if skipped_ext:
                parts.append(texts.SOME_FILES_SKIPPED_MESSAGE.format(count=skipped_ext))
            if skipped_dups:
                parts.append(
                    texts.SKIPPED_FILES_ALREADY_IN_THIS_LIST.format(count=skipped_dups)
                )
            if skipped_same_as_ref:
                msg = texts.CANNOT_PAIR_FILE_WITH_ITSELF
                if skipped_same_as_ref > 1:
                    msg = f"{msg} (x{skipped_same_as_ref})"
                parts.append(msg)
            QMessageBox.information(
                self,
                texts.SOME_FILES_SKIPPED_TITLE,
                "\n".join(parts),
            )

        self._update_headers()
        self._update_ui_state()

    def _remove_selected_subtitles(self):
        selected = self.sub_list.selectedItems()
        if not selected:
            return
        root = self.sub_list.invisibleRootItem()
        for it in selected:
            path = it.data(0, Qt.ItemDataRole.UserRole)
            if path in self.subtitle_files:
                self.subtitle_files.remove(path)
            root.removeChild(it)
        self._update_headers()
        self._update_ui_state()

    def _clear_subtitles(self):
        self.subtitle_files.clear()
        self.sub_list.clear()
        self._update_headers()
        self._update_ui_state()

    def _on_sub_selection_changed(self):
        self._sub_remove_btn.setEnabled(bool(self.sub_list.selectedItems()))

    def _show_subtitles_context_menu(self, position):
        menu = QMenu(self)
        menu.addAction(texts.ADD_MULTIPLE_FILES, self._add_subtitle_files_dialog)
        menu.addAction(texts.ADD_FOLDER, self._add_subtitle_folder)
        menu.addSeparator()
        has_sel = bool(self.sub_list.selectedItems())
        act_remove = menu.addAction(
            texts.REMOVE_SELECTED, self._remove_selected_subtitles
        )
        act_remove.setEnabled(has_sel)
        menu.addAction(texts.CLEAR_ALL, self._clear_subtitles)

        # Go to folder for first selected item
        if has_sel:
            menu.addSeparator()
            menu.addAction(
                texts.GO_TO_FOLDER,
                lambda: self._go_to_folder(self.sub_list.selectedItems()[0]),
            )

        menu.popup(self.sub_list.mapToGlobal(position))

    def _go_to_folder(self, item):
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

    # --- State and actions ---
    def _update_headers(self):
        self.sub_list.setHeaderLabel(
            texts.SUBTITLE_FILES_TOTAL.format(count=len(self.subtitle_files))
        )

    def _update_ui_state(self):
        has_ref = bool(getattr(self.ref_input, "file_path", None))
        has_subs = len(self.subtitle_files) > 0
        self.btn_ok.setEnabled(has_ref and has_subs)
        # Update count label
        if has_subs:
            self.count_label.setText(
                texts.TOTAL_VALID_PAIRS.format(pairs_count=len(self.subtitle_files))
            )
            self.count_label.setVisible(True)
        else:
            self.count_label.setVisible(False)

    def _add_pairs_to_batch(self):
        ref = getattr(self.ref_input, "file_path", None)
        if not ref:
            QMessageBox.warning(
                self,
                texts.ERROR,
                texts.PLEASE_SELECT_VIDEO_OR_REFERENCE_SUBTITLE,
            )
            return

        if not self.subtitle_files:
            QMessageBox.warning(
                self,
                texts.NO_MEDIA_FILES_FOUND_TITLE,
                texts.NO_MEDIA_FILES_FOUND_MESSAGE,
            )
            return

        view = self.parent_window.batch_tree_view

        # Check if the reference already exists as a parent in the batch
        existing_parent = view.find_parent_by_path(ref)

        if existing_parent:
            # Add subtitles as children to the existing parent
            added, skipped_same, skipped_dups = view.add_children_to_parent(
                existing_parent, self.subtitle_files
            )
        else:
            # Create a new parent with all subtitles as children
            added, skipped_same, skipped_dups = view.add_parent_with_children(
                ref, self.subtitle_files
            )

        if added == 0:
            # Nothing was added; inform why
            if skipped_dups or skipped_same:
                # Prefer a more specific title when only duplicate pairs were skipped
                if skipped_dups and not skipped_same:
                    QMessageBox.information(
                        self,
                        texts.DUPLICATES_SKIPPED_TITLE,
                        texts.DUPLICATES_SKIPPED_MESSAGE.format(count=skipped_dups),
                    )
                else:
                    parts = []
                    if skipped_dups:
                        parts.append(
                            texts.DUPLICATES_SKIPPED_MESSAGE.format(count=skipped_dups)
                        )
                    if skipped_same:
                        msg = texts.CANNOT_PAIR_FILE_WITH_ITSELF
                        if skipped_same > 1:
                            msg = f"{msg} (x{skipped_same})"
                        parts.append(msg)
                    QMessageBox.information(self, texts.NO_NEW_PAIRS, "\n".join(parts))
            else:
                QMessageBox.information(
                    self, texts.NO_NEW_PAIRS, texts.ALL_PAIRS_ALREADY_EXIST_IN_BATCH
                )
        else:
            # Inform if some were skipped even though some pairs were added
            if skipped_dups or skipped_same:
                parts = []
                if skipped_dups:
                    parts.append(
                        texts.DUPLICATES_SKIPPED_MESSAGE.format(count=skipped_dups)
                    )
                if skipped_same:
                    # If multiple identical-to-reference were skipped, add a count hint
                    msg = texts.CANNOT_PAIR_FILE_WITH_ITSELF
                    if skipped_same > 1:
                        msg = f"{msg} (x{skipped_same})"
                    parts.append(msg)
                QMessageBox.information(
                    self,
                    texts.SOME_FILES_SKIPPED_TITLE,
                    "\n".join(parts),
                )
            self.close()

    def _on_reference_changed(self, new_ref_path: str | None):
        """When reference changes, ensure it's not present in the subtitles list."""
        if not new_ref_path:
            return
        # Normalize path for comparison
        norm_ref = os.path.normpath(new_ref_path)
        removed = 0
        # Remove any matching entries from the in-memory list and the UI widget
        root = self.sub_list.invisibleRootItem()
        to_remove_indices = [
            i
            for i, p in enumerate(self.subtitle_files)
            if os.path.normpath(p) == norm_ref
        ]
        if to_remove_indices:
            # Remove from end to start to keep indices valid
            for idx in reversed(to_remove_indices):
                del self.subtitle_files[idx]
                removed += 1
            # Remove matching UI items
            for i in reversed(range(self.sub_list.topLevelItemCount())):
                it = self.sub_list.topLevelItem(i)
                p = it.data(0, Qt.ItemDataRole.UserRole)
                if p and os.path.normpath(p) == norm_ref:
                    root.removeChild(it)
        if removed:
            # Notify user the file cannot be both reference and subtitle
            msg = texts.CANNOT_PAIR_FILE_WITH_ITSELF
            if removed > 1:
                msg = f"{msg} (x{removed})"
            QMessageBox.information(self, texts.SOME_FILES_SKIPPED_TITLE, msg)
            self._update_headers()
            self._update_ui_state()


def attach_functions_to_autosubsyncapp(autosubsyncapp_class):
    """Attach function to open the dialog from the main app."""
    autosubsyncapp_class.open_pair_multiple_subs_dialog = (
        lambda self: MultipleSubsDialog(self).exec()
    )
