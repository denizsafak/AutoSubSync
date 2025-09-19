"""
This module provides batch processing functionality for AutoSubSync.
It's designed to be imported and used by the main application without creating circular imports.

The module exports:
- BatchTreeView: A tree view widget for displaying and managing batches of video/subtitle files
- Helper functions for batch operations that are attached to the main app at runtime
"""

from PyQt6.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QAbstractItemView,
    QMenu,
    QMessageBox,
    QFileIconProvider,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt, QTimer, QFileInfo, QPoint
from PyQt6.QtGui import QCursor, QColor

import os
import re
import logging
import texts
from constants import VIDEO_EXTENSIONS, SUBTITLE_EXTENSIONS, COLORS
from utils import update_config, open_filedialog, open_folder

# Set up logging for batch events
logger = logging.getLogger(__name__)

# Constants for file dialogs
VIDEO_SUBTITLE_FILTER = f"{texts.VIDEO_OR_SUBTITLE_FILES_LABEL} (*{' *'.join(VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS)})"
VIDEO_FILTER = f"{texts.VIDEO_FILES_LABEL} (*{' *'.join(VIDEO_EXTENSIONS)})"
SUBTITLE_FILTER = f"{texts.SUBTITLE_FILES_LABEL} (*{' *'.join(SUBTITLE_EXTENSIONS)})"


# Helper functions for file operations
def get_file_extension(file_path):
    """Get the lowercase extension of a file path."""
    return os.path.splitext(file_path)[1].lower() if file_path else ""


def is_video_file(file_path):
    """Check if a file is a video file based on its extension."""
    return get_file_extension(file_path) in VIDEO_EXTENSIONS


def is_subtitle_file(file_path):
    """Check if a file is a subtitle file based on its extension."""
    return get_file_extension(file_path) in SUBTITLE_EXTENSIONS


def is_media_file(file_path):
    """Check if a file is either a video or subtitle file."""
    ext = get_file_extension(file_path)
    return ext in VIDEO_EXTENSIONS or ext in SUBTITLE_EXTENSIONS


def update_last_dir(app_instance, dir_path):
    """Update the last used directory in app config."""
    update_config(app_instance, "last_used_dir", dir_path)


def get_basename(file_path):
    """Get the basename of a file path."""
    return os.path.basename(file_path) if file_path else ""


def effective_basename(file_path):
    """Extract effective basename from file path, handling language tags.

    Removes potential language tags that are often 2-4 characters and
    preceded by a separator character like '_', '.', or '-'.

    Args:
        file_path: Path to a file

    Returns:
        Base filename without extension or language tags
    """
    base = os.path.splitext(os.path.basename(file_path))[0]
    for tag_length in [4, 3, 2]:
        if len(base) > tag_length and base[-(tag_length + 1)] in ["_", ".", "-"]:
            return base[: -(tag_length + 1)]
    return base


def calculate_file_similarity(reference_name, sub_name):
    """Calculate similarity score between reference and subtitle filenames.

    This function uses multiple methods to determine the similarity:
    1. Uses effective_basename to remove language tags
    2. Calculates common prefix length
    3. Uses a string similarity ratio

    Args:
        reference_name: Basename of a reference file
        sub_name: Basename of a subtitle file

    Returns:
        Similarity score (higher is more similar)
    """
    # Clean and prepare names
    reference_base = effective_basename(reference_name).lower().strip(".-_ [](){}")
    sub_base = effective_basename(sub_name).lower().strip(".-_ [](){}")

    # Calculate common prefix length
    common_len = 0
    for i in range(min(len(reference_base), len(sub_base))):
        if reference_base[i] == sub_base[i]:
            common_len += 1
        else:
            break

    # Calculate similarity score - weight by:
    # 1. Common prefix length (heavily weighted)
    # 2. Length difference (penalty for very different lengths)
    # 3. Bonus for exact match after processing

    similarity = common_len * 10  # Base score from common prefix

    # Penalty for length difference
    length_diff = abs(len(reference_base) - len(sub_base))
    similarity -= min(
        length_diff * 2, similarity // 2
    )  # Don't let penalty exceed half the score

    # Exact match bonus
    if reference_base == sub_base:
        similarity += 50

    return max(0, similarity)  # Ensure non-negative score


def create_tree_widget_item(file_path, parent=None, icon_provider=None, item_id=None):
    """Create a QTreeWidgetItem for a file path.

    Args:
        file_path: Path to the file
        parent: Optional parent item
        icon_provider: Optional QFileIconProvider for file icons
        item_id: Optional ID for the item

    Returns:
        A configured QTreeWidgetItem
    """
    basename = get_basename(file_path)
    if parent:
        item = QTreeWidgetItem(parent, [basename])
    else:
        item = QTreeWidgetItem([basename])

    item.setData(0, Qt.ItemDataRole.UserRole, file_path)
    if item_id is not None:
        item.setData(0, BatchTreeView.ITEM_ID_ROLE, item_id)

    # Add icon if provider is available
    if icon_provider:
        item.setIcon(0, icon_provider.icon(QFileInfo(file_path)))

    return item


def attach_functions_to_autosubsyncapp(autosubsyncapp_class):
    """Attach batch mode functions to the autosubsyncapp class"""
    autosubsyncapp_class.show_batch_add_menu = show_batch_add_menu
    autosubsyncapp_class.handle_add_pair = handle_add_pair
    autosubsyncapp_class.handle_add_folder = handle_add_folder
    autosubsyncapp_class.handle_add_multiple_files = handle_add_multiple_files
    autosubsyncapp_class.handle_add_pairs_continuously = handle_add_pairs_continuously
    autosubsyncapp_class.handle_batch_drop = handle_batch_drop
    autosubsyncapp_class.update_batch_buttons_state = update_batch_buttons_state
    autosubsyncapp_class.toggle_batch_mode = toggle_batch_mode
    autosubsyncapp_class.validate_batch_inputs = validate_batch_inputs


class BatchTreeView(QTreeWidget):
    VALID_STATE_ROLE = (
        Qt.ItemDataRole.UserRole + 10
    )  # Role to store parent item's validity state
    ITEM_ID_ROLE = Qt.ItemDataRole.UserRole + 11  # Role to store the item's unique ID

    def _is_parent_item_valid(self, item):
        """Helper to determine if a parent item is valid (has exactly one child, and that child has no children and is not a video file)."""
        # Quick early returns for invalid cases
        if not item or item.parent() or item.childCount() != 1:
            return False

        first_child = item.child(0)
        if not first_child or first_child.childCount() > 0:
            return False

        # Check if child is a subtitle (not a video)
        child_file_path = first_child.data(0, Qt.ItemDataRole.UserRole)
        return (
            child_file_path
            and get_file_extension(child_file_path) not in VIDEO_EXTENSIONS
        )

    def is_duplicate_pair(self, reference_path, sub_path):
        """Return True if (reference_path, sub_path) matches an existing valid top-level pair."""
        norm_v, norm_s = os.path.normpath(reference_path), os.path.normpath(sub_path)
        return (norm_v, norm_s) in self._current_pair_id_set

    def __init__(self, parent_app=None):  # parent_app is the autosubsyncapp instance
        super().__init__(parent_app)
        self.app_parent = parent_app
        self._next_item_id = 1  # Initialize the ID counter
        self.setColumnCount(1)
        self.setHeaderHidden(False)  # Show header to display pair counts
        # self.headerItem().setTextAlignment(0, Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.icon_provider = QFileIconProvider()
        self.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )  # Allow multi-selection for removal

        self._update_ui_timer = QTimer(self)
        self._update_ui_timer.setSingleShot(True)
        self._update_ui_timer.setInterval(0)  # Process on next event loop iteration
        self._update_ui_timer.timeout.connect(self._perform_actual_ui_update)

        self._items_to_re_expand_paths = (
            set()
        )  # For preserving expansion state during moves

        # Cache for performance optimization
        self._current_pair_id_set = set()
        self._item_to_pair_id_map = {}

        # Drag state management
        self._is_drag_highlighted = False
        self._base_stylesheet = "QTreeView::item { height: 32px; }"
        self._update_stylesheet()

        # Connect model signals to schedule UI update
        model = self.model()
        model.rowsInserted.connect(self._schedule_ui_update)
        model.rowsRemoved.connect(self._schedule_ui_update)
        model.modelReset.connect(self._schedule_ui_update)

    def _get_next_id(self):
        """Get the next available unique ID for a tree item."""
        current_id = self._next_item_id
        self._next_item_id += 1
        return current_id

    def _schedule_ui_update(self, *args):  # Accept any arguments from signals
        self._update_ui_timer.start()

    def _perform_actual_ui_update(self):
        # Check if this is an internal drag/drop operation
        is_internal_move = hasattr(self, "_in_internal_drag") and self._in_internal_drag

        # Phase 1: Rebuild pair ID set and item-to-pair_id map for efficient validation
        self._current_pair_id_set.clear()
        self._item_to_pair_id_map.clear()
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item and item.childCount() == 1:  # Potential pair structure
                parent_path = item.data(0, Qt.ItemDataRole.UserRole)
                child_item = item.child(0)
                child_path = child_item.data(0, Qt.ItemDataRole.UserRole)

                if (
                    parent_path
                    and child_path
                    and not child_item.childCount()
                    and is_subtitle_file(child_path)
                ):
                    norm_parent = os.path.normpath(parent_path)
                    norm_child = os.path.normpath(child_path)
                    if (
                        norm_parent != norm_child
                    ):  # Ensure parent and child are not the same file
                        pair_id = (norm_parent, norm_child)
                        self._current_pair_id_set.add(pair_id)
                        self._item_to_pair_id_map[id(item)] = pair_id

        # Continue with existing UI update logic - but ONLY trigger app parent updates if not an internal move
        if (
            self.app_parent
            and hasattr(self.app_parent, "update_auto_sync_ui_for_batch")
            and not is_internal_move
        ):
            self.app_parent.update_auto_sync_ui_for_batch()

        # Re-apply expansion state for items that were moved
        if self._items_to_re_expand_paths:
            self._apply_expansion_recursive(
                self
            )  # Start recursion from the tree itself
            self._items_to_re_expand_paths.clear()  # Clear after use

        self._update_parent_item_style()  # Update styles for all parent items
        self._update_header_pair_counts()  # Update header with valid/invalid pair counts
        self._sort_top_level_items()  # Sort/expand items after updates

        # Log appropriate message based on operation type
        if is_internal_move:
            logger.info(
                f"Internal move - {self.topLevelItemCount()} parents, {len(self._current_pair_id_set)} valid pairs"
            )
        else:
            logger.info(
                f"UI update: {self.topLevelItemCount()} top-level items, {len(self._current_pair_id_set)} valid pairs"
            )

        # Reset internal move flag
        if hasattr(self, "_in_internal_drag"):
            self._in_internal_drag = False

    def _sort_top_level_items(self):
        # Expand all top-level items
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item:  # Ensure item is valid
                item.setExpanded(True)

    def _get_provisional_validity(self, item):
        # This method determines 'validity' based on the item's current children structure.
        # Use the helper function for validity
        is_valid = self._is_parent_item_valid(item)
        return "valid" if is_valid else "invalid"

    def _update_header_pair_counts(self):
        """Updates the header with counts of valid and invalid pairs."""
        valid_pairs = 0
        invalid_pairs = 0
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item.data(0, self.VALID_STATE_ROLE) == "valid":
                valid_pairs += 1
            else:
                invalid_pairs += 1

        header_text = texts.PAIRS_HEADER_LABEL.format(
            valid=valid_pairs, invalid=invalid_pairs
        )
        self.setHeaderLabel(header_text)

    def _apply_expansion_recursive(self, parent_item_or_tree):
        """Recursively expand items whose paths are in the re-expansion set."""
        # Determine if we're processing a tree widget or a tree item
        is_tree = not isinstance(parent_item_or_tree, QTreeWidgetItem)
        get_child = (
            parent_item_or_tree.topLevelItem if is_tree else parent_item_or_tree.child
        )
        child_count = (
            parent_item_or_tree.topLevelItemCount()
            if is_tree
            else parent_item_or_tree.childCount()
        )

        # Process all children
        for i in range(child_count):
            if item := get_child(i):
                # Re-expand if needed
                if path := item.data(0, Qt.ItemDataRole.UserRole):
                    if path in self._items_to_re_expand_paths:
                        item.setExpanded(True)
                # Process children recursively
                if item.childCount() > 0:
                    self._apply_expansion_recursive(item)

    def _parse_rgba_to_qcolor(self, rgba_str):
        """Helper to convert "rgba(R,G,B,A_float)" string to QColor."""
        match = re.match(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)", rgba_str)
        if match:
            r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
            a_float = float(match.group(4))
            # QColor alpha is 0-255
            a_int = int(a_float * 255)
            return QColor(r, g, b, a_int)
        # Fallback if parsing fails (e.g., return transparent or a default error color)
        # For now, returning transparent, but you might want to log an error.
        return Qt.GlobalColor.transparent

    def _set_item_tooltip(self, item, message=None):
        """Set tooltip for items - only show validity status for parent items."""
        if not item:
            return

        item_id = item.data(0, self.ITEM_ID_ROLE)
        id_text = f"(#{item_id})" if item_id is not None else ""

        # If it has a parent, it is a child item, so we don't show validity status
        if item.parent():
            item.setToolTip(0, f"{id_text}")
            return

        if message:
            item.setToolTip(
                0,
                texts.BATCH_PAIR_STATUS_INVALID_LABEL.format(
                    id_text=id_text, message=message
                ),
            )
            return

        item.setToolTip(0, texts.BATCH_PAIR_STATUS_VALID_LABEL.format(id_text=id_text))

    def _validate_item(self, item):
        """Validate an item and return its validity state.
        Uses precomputed _current_pair_id_set for duplicate checks.
        """

        # Check if item has exactly one child
        if item.childCount() == 0:
            return False, texts.BATCH_VALIDATE_ADD_SUBTITLE

        # Check if item has more than one child
        if item.childCount() > 1:
            return False, texts.BATCH_VALIDATE_TOO_MANY_FILES

        # Check if the child has no children
        child_item = item.child(0)
        if child_item.childCount() > 0:
            return False, texts.BATCH_VALIDATE_NESTED_NOT_ALLOWED

        # Check if the child is a video file
        if is_video_file(child_item.data(0, Qt.ItemDataRole.UserRole)):
            return False, texts.BATCH_VALIDATE_VIDEO_NOT_ALLOWED

        # Path validation
        parent_path = item.data(0, Qt.ItemDataRole.UserRole)
        child_path = child_item.data(0, Qt.ItemDataRole.UserRole)

        if not parent_path or not child_path:
            return False, texts.BATCH_VALIDATE_MISSING_FILE_PATH

        norm_parent = os.path.normpath(parent_path)
        norm_child = os.path.normpath(child_path)

        if norm_parent == norm_child:
            return False, texts.BATCH_VALIDATE_SAME_FILE

        if not is_subtitle_file(child_path):
            return False, texts.BATCH_VALIDATE_CHILD_NOT_SUBTITLE

        # Check for duplicates using the precomputed set
        current_item_pair_id = self._item_to_pair_id_map.get(id(item))
        if current_item_pair_id:
            # Only invalidate the newest duplicate (highest ITEM_ID_ROLE)
            duplicate_ids = []
            for i in range(self.topLevelItemCount()):
                top = self.topLevelItem(i)
                if top.childCount() == 1:
                    p = os.path.normpath(top.data(0, Qt.ItemDataRole.UserRole))
                    c = os.path.normpath(top.child(0).data(0, Qt.ItemDataRole.UserRole))
                    if (p, c) == current_item_pair_id:
                        duplicate_ids.append(top.data(0, self.ITEM_ID_ROLE))
            if len(duplicate_ids) > 1:
                current_id = item.data(0, self.ITEM_ID_ROLE)
                if current_id == max(duplicate_ids):
                    return False, texts.BATCH_VALIDATE_DUPLICATE_PAIR

        return True, None

    def _apply_item_styles(self, item, is_valid):
        """Apply styling to an item based on its validity.

        Args:
            item: QTreeWidgetItem to style
            is_valid: Boolean indicating if the item is valid
        """
        green_qcolor = self._parse_rgba_to_qcolor(COLORS["GREEN_BACKGROUND_HOVER"])
        red_qcolor = self._parse_rgba_to_qcolor(COLORS["RED_BACKGROUND_HOVER"])
        default_qcolor = QColor(Qt.GlobalColor.transparent)

        if not item.parent():  # Top-level item
            item.setData(0, self.VALID_STATE_ROLE, "valid" if is_valid else "invalid")
            item.setBackground(0, green_qcolor if is_valid else red_qcolor)
        else:  # Child or deeper descendant
            item.setBackground(0, default_qcolor)
            item.setData(0, self.VALID_STATE_ROLE, None)  # Clear state for non-parents

    def _find_root_ancestor(self, item):
        """Find the top-level ancestor of an item."""
        if not item:
            return None
        current = item
        while current.parent():
            current = current.parent()
        return current

    def _update_parent_item_style(
        self, specific_items_affected=None, old_parents_affected=None
    ):
        """Update item background colors based on validity state.
        Efficiently updates specific items if provided, otherwise full scan.
        """

        def process_item_recursive(item_to_process):
            is_top_level = not item_to_process.parent()

            # Apply appropriate styling based on item type
            if is_top_level:
                is_valid, message = self._validate_item(item_to_process)
                self._apply_item_styles(item_to_process, is_valid)
            else:
                self._apply_item_styles(item_to_process, False)

            # Update tooltip
            self._set_item_tooltip(
                item_to_process, message if is_top_level and not is_valid else None
            )

            # Process all children
            for i in range(item_to_process.childCount()):
                if child := item_to_process.child(i):
                    process_item_recursive(child)

        # Determine which items to process
        if specific_items_affected:
            # Get unique root ancestors from affected items and old parents
            # Use a list instead of a set since QTreeWidgetItem is not hashable
            roots_to_process = []

            for item_list in (specific_items_affected, old_parents_affected or []):
                for item in item_list:
                    if root := self._find_root_ancestor(item):
                        if root.treeWidget() == self and root not in roots_to_process:
                            roots_to_process.append(root)

            # Process identified root items
            for root_item in roots_to_process:
                process_item_recursive(root_item)
        else:
            # Process all top-level items
            for i in range(self.topLevelItemCount()):
                if top_item := self.topLevelItem(i):
                    process_item_recursive(top_item)

    def _update_stylesheet(self):
        """Update the stylesheet based on current drag state."""
        if self._is_drag_highlighted:
            drag_style = f"""
                QTreeWidget {{
                    background-color: {COLORS['BLUE_BACKGROUND_HOVER']};
                }}
            """
            self.setStyleSheet(self._base_stylesheet + drag_style)
        else:
            self.setStyleSheet(self._base_stylesheet)

    def _set_drag_highlight(self, enabled):
        """Enable or disable drag highlighting."""
        if self._is_drag_highlighted != enabled:
            self._is_drag_highlighted = enabled
            self._update_stylesheet()

    def dragEnterEvent(self, event):
        # Check if this is an internal drag operation (from this widget itself)
        if not event.mimeData().hasUrls() and event.source() == self:
            # Mark as internal drag operation to optimize updates
            self._in_internal_drag = True
            logger.info("Internal drag operation started")

        if event.mimeData().hasUrls():
            self._set_drag_highlight(True)
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragLeaveEvent(self, event):
        self._set_drag_highlight(False)
        super().dragLeaveEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            self._set_drag_highlight(False)
            # Not an internal operation if we're dropping URLs
            self._in_internal_drag = False
            # Process the dropped files/folders
            urls = event.mimeData().urls()
            paths = [url.toLocalFile() for url in urls if url.isLocalFile()]
            if paths:
                drop_target_item = self.itemAt(event.position().toPoint())
                self.add_files_or_folders(paths, drop_target_item=drop_target_item)
            event.acceptProposedAction()
        else:
            # This is still an internal drop even if we're calling super
            super().dropEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        selected_items = self.selectedItems()
        item_at_pos = self.itemAt(event.pos())

        add_files_menu = menu.addMenu(texts.ADD_FILES)
        action_add_pair = add_files_menu.addAction(texts.ADD_PAIR)
        action_add_continuously = add_files_menu.addAction(texts.ADD_PAIR_CONTINUOUSLY)
        action_add_folder = add_files_menu.addAction(texts.ADD_FOLDER)
        action_add_files = add_files_menu.addAction(texts.ADD_MULTIPLE_FILES)
        add_files_menu.addSeparator()
        action_auto_pairing = add_files_menu.addAction(
            texts.AUTO_PAIRING_SEASON_EPISODE
        )
        # Add "pair multiple subtitles with single source" option
        action_pair_multiple_subs = add_files_menu.addAction(
            texts.PAIR_MULTIPLE_SUBTITLES_WITH_SINGLE_SOURCE
        )

        action_add_pair.triggered.connect(lambda: self.app_parent.handle_add_pair())
        action_add_folder.triggered.connect(lambda: self.app_parent.handle_add_folder())
        action_add_files.triggered.connect(
            lambda: self.app_parent.handle_add_multiple_files()
        )
        action_add_continuously.triggered.connect(
            self.app_parent.handle_add_pairs_continuously
        )
        # Connect the new auto-pairing option
        action_auto_pairing.triggered.connect(
            lambda: self.app_parent.open_auto_pairing_dialog()
        )
        # Connect the "pair multiple subtitles with single source" option
        action_pair_multiple_subs.triggered.connect(
            lambda: self.app_parent.open_pair_multiple_subs_dialog()
        )

        menu.addSeparator()

        if item_at_pos and not item_at_pos.parent():  # Right-clicked a top-level item
            menu.addAction(
                texts.ADD_SUBTITLE_TO_ITEM,
                lambda: self.add_subtitle_to_item_dialog(item_at_pos),
            )
            # Check if the top-level item is a subtitle file
            item_path = item_at_pos.data(0, Qt.ItemDataRole.UserRole)
            if (
                item_path
                and os.path.splitext(item_path)[1].lower() in SUBTITLE_EXTENSIONS
            ):
                menu.addAction(
                    texts.ADD_VIDEO_TO_ITEM,
                    lambda: self.add_video_to_subtitle_dialog(item_at_pos),
                )

        # Add 'Go to folder' option for any item
        if item_at_pos:
            menu.addAction(
                texts.GO_TO_FOLDER, lambda: self.open_item_folder(item_at_pos)
            )

        if selected_items:  # Operations for selected items
            if (
                len(selected_items) == 1 and item_at_pos
            ):  # Change only makes sense for a single item
                menu.addAction(
                    texts.CHANGE, lambda: self.change_file_for_item(item_at_pos)
                )
            menu.addAction(
                texts.REMOVE_SELECTED_COUNT.format(len=len(selected_items)),
                self.remove_selected_items,
            )
        elif item_at_pos:  # Fallback if no selection but right-clicked on an item
            menu.addAction(texts.REMOVE, lambda: self.remove_item(item_at_pos))
            menu.addAction(texts.CHANGE, lambda: self.change_file_for_item(item_at_pos))

        menu.addSeparator()
        action_clear_all = menu.addAction(texts.CLEAR_ALL)
        action_clear_all.triggered.connect(self.clear_all_items)
        if not self.has_items():
            action_clear_all.setEnabled(False)
        if (
            not selected_items and not item_at_pos
        ):  # Disable remove/change if not on item and no selection
            for act in menu.actions():
                # Disable actions whose triggered slot is self.remove_item or self.change_file_for_item
                if hasattr(act, "triggered"):
                    # Check if the action's triggered signal is connected to the relevant methods
                    # This is a heuristic: check if the slot lambda contains 'remove_item' or 'change_file_for_item'
                    slot_repr = repr(act.triggered)
                    if (
                        "remove_item" in slot_repr
                        or "change_file_for_item" in slot_repr
                    ):
                        act.setEnabled(False)

        menu.popup(self.viewport().mapToGlobal(event.pos()))

    def keyPressEvent(self, event):
        """Handle keyboard events."""
        if event.key() == Qt.Key.Key_Delete:
            # Delete key pressed - remove selected items
            self.remove_selected_items()
        else:
            # Pass other key events to the parent class
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        """Handle mouse press events to clear selection when clicking empty area."""
        item = self.itemAt(event.position().toPoint())
        if item is None:
            # Clicked on empty area - clear selection
            self.clearSelection()
            self.setCurrentItem(None)

        # Call parent implementation to handle normal clicking behavior
        super().mousePressEvent(event)

    def _get_file_icon(self, file_path):
        """Get the icon for a file using the QFileIconProvider."""
        return self.icon_provider.icon(QFileInfo(file_path))

    def add_files_or_folders(self, paths, drop_target_item=None):
        logger.info(f"Adding files/folders: {len(paths)} items")
        # Special case: Check if there are exactly 2 files, one video and one subtitle
        if len(paths) == 2 and all(os.path.isfile(p) for p in paths):
            if paths[0] == paths[1]:
                QMessageBox.warning(
                    self.app_parent,
                    texts.INVALID_PAIR_TITLE,
                    texts.CANNOT_PAIR_FILE_WITH_ITSELF,
                )
                return
            exts = [os.path.splitext(path)[1].lower() for path in paths]
            # Check if we have one video and one subtitle file
            if exts[0] in VIDEO_EXTENSIONS and exts[1] in SUBTITLE_EXTENSIONS:
                if self.is_duplicate_pair(paths[0], paths[1]):
                    QMessageBox.warning(
                        self.app_parent,
                        texts.BATCH_VALIDATE_DUPLICATE_PAIR,
                        texts.BATCH_VALIDATE_DUPLICATE_PAIR,
                    )
                    return
                reference_path, sub_path = paths[0], paths[1]
                self.add_explicit_pair(reference_path, sub_path)
                logger.info(
                    f"Added pair: {os.path.basename(reference_path)} + {os.path.basename(sub_path)}"
                )
                return
            elif exts[1] in VIDEO_EXTENSIONS and exts[0] in SUBTITLE_EXTENSIONS:
                if self.is_duplicate_pair(paths[1], paths[0]):
                    QMessageBox.warning(
                        self.app_parent,
                        texts.BATCH_VALIDATE_DUPLICATE_PAIR,
                        texts.BATCH_VALIDATE_DUPLICATE_PAIR,
                    )
                    return
                reference_path, sub_path = paths[1], paths[0]
                self.add_explicit_pair(reference_path, sub_path)
                logger.info(
                    f"Added pair: {os.path.basename(reference_path)} + {os.path.basename(sub_path)}"
                )
                return

        # Standard processing for all other cases
        files_to_process = []
        for path in paths:
            if os.path.isdir(path):
                for root, _, filenames in os.walk(path):
                    for filename in filenames:
                        file_path = os.path.join(root, filename)
                        ext = os.path.splitext(file_path)[1].lower()
                        if ext in VIDEO_EXTENSIONS or ext in SUBTITLE_EXTENSIONS:
                            files_to_process.append(file_path)
            elif os.path.isfile(path):
                ext = os.path.splitext(path)[1].lower()
                if ext in VIDEO_EXTENSIONS or ext in SUBTITLE_EXTENSIONS:
                    files_to_process.append(path)

        if not files_to_process:
            logger.warning("No supported media files found in dropped/added paths.")
            QMessageBox.warning(
                self.app_parent,
                texts.NO_MEDIA_FILES_FOUND_TITLE,
                texts.NO_MEDIA_FILES_FOUND_MESSAGE,
            )
            return

        if files_to_process:
            logger.info(f"Processing {len(files_to_process)} files for pairing")
            skipped = 0
            self.add_paired_files(files_to_process, drop_target_item=drop_target_item)
            if skipped:
                QMessageBox.information(
                    self.app_parent,
                    texts.DUPLICATES_SKIPPED_TITLE,
                    texts.DUPLICATES_SKIPPED_MESSAGE.format(count=skipped),
                )

    def _create_tree_item(self, file_path):
        """Helper to create a new tree item for a file."""
        item_id = self._get_next_id()
        item = create_tree_widget_item(
            file_path, icon_provider=self.icon_provider, item_id=item_id
        )
        return item

    def _pair_references_with_subtitles(self, references, subs):
        """Match references with their corresponding subtitles."""
        paired_references = set()
        paired_subs = set()
        reference_sub_pairs = []

        # First pass: exact basename matching
        for reference in references:
            reference_base = effective_basename(reference).lower().strip(".-_ [](){}")
            for sub in subs:
                if sub in paired_subs:
                    continue
                sub_base = effective_basename(sub).lower().strip(".-_ [](){}")
                if reference_base == sub_base:
                    reference_sub_pairs.append((reference, sub))
                    paired_references.add(reference)
                    paired_subs.add(sub)
                    break

        # Second pass: similarity-based matching
        for reference in references:
            if reference in paired_references:
                continue
            best_match = None
            best_score = 0
            for sub in subs:
                if sub in paired_subs:
                    continue
                similarity = calculate_file_similarity(reference, sub)
                if similarity > best_score:
                    best_score = similarity
                    best_match = sub
            if best_match and best_score >= 30:
                reference_sub_pairs.append((reference, best_match))
                paired_references.add(reference)
                paired_subs.add(best_match)
        return reference_sub_pairs, paired_references, paired_subs

    def add_paired_files(self, file_paths, drop_target_item=None):
        newly_created_items = []
        skipped = 0

        # Separate references and subtitles
        references = sorted([f for f in file_paths if is_video_file(f)])
        subs = sorted([f for f in file_paths if is_subtitle_file(f)])

        # Match references with subtitles
        pairs, paired_references, paired_subs = self._pair_references_with_subtitles(
            references, subs
        )

        # Create tree items for each reference-sub pair
        for reference, sub_file_path in pairs:
            if reference == sub_file_path or self.is_duplicate_pair(
                reference, sub_file_path
            ):
                skipped += 1
                continue

            parent_item = self._create_tree_item(reference)
            # Ensure child gets an ID
            child_item = create_tree_widget_item(
                sub_file_path,
                parent=parent_item,
                icon_provider=self.icon_provider,
                item_id=self._get_next_id(),
            )
            parent_item.setExpanded(True)
            newly_created_items.append(parent_item)

        # Create items for unpaired files
        for reference in references:
            if reference not in paired_references:
                newly_created_items.append(self._create_tree_item(reference))

        for sub in subs:
            if sub not in paired_subs:
                newly_created_items.append(self._create_tree_item(sub))

        # Add all newly created items to the tree
        if newly_created_items:
            # Sort by validity and name
            newly_created_items.sort(
                key=lambda item: (
                    0 if self._get_provisional_validity(item) == "invalid" else 1,
                    os.path.basename(item.data(0, Qt.ItemDataRole.UserRole)).lower(),
                )
            )

            # Add to tree
            for item in reversed(newly_created_items):
                self.insertTopLevelItem(0, item)

        # Show message about skipped items
        if skipped:
            logger.info(f"Skipped {skipped} duplicate pairs")
            QMessageBox.information(
                self.app_parent,
                texts.DUPLICATES_SKIPPED_TITLE,
                texts.DUPLICATES_SKIPPED_MESSAGE.format(count=skipped),
            )

        logger.info(
            f"Paired {len(pairs)} reference-subtitle pairs. Unpaired references: {len(references) - len(paired_references)}, unpaired subs: {len(subs) - len(paired_subs)}"
        )

    def add_explicit_pair(self, video_ref_path, sub_path):
        logger.info(
            f"Adding pair: {os.path.basename(video_ref_path)} + {os.path.basename(sub_path)}"
        )
        parent_item_id = self._get_next_id()
        parent_item = create_tree_widget_item(
            video_ref_path, None, self.icon_provider, item_id=parent_item_id
        )

        child_item_id = self._get_next_id()
        child_item = create_tree_widget_item(
            sub_path, parent_item, self.icon_provider, item_id=child_item_id
        )

        parent_item.setExpanded(True)
        self.insertTopLevelItem(
            0, parent_item
        )  # Insert the configured parent item at the top
        # UI update (including sort) will be scheduled by model signals

    def add_subtitle_to_item_dialog(self, parent_item):
        logger.info(
            f"Adding subtitle to item: {os.path.basename(parent_item.data(0, Qt.ItemDataRole.UserRole)) if parent_item and parent_item.data(0, Qt.ItemDataRole.UserRole) else None}"
        )
        if not parent_item or parent_item.parent():  # Must be a top-level item
            QMessageBox.warning(
                self.app_parent,
                texts.SELECTION_ERROR_TITLE,
                texts.SELECT_TOP_LEVEL_ITEM_MESSAGE,
            )
            return

        file_paths = open_filedialog(
            self.app_parent,
            "files-open",
            texts.SELECT_SUBTITLE_FILE_TITLE,
            SUBTITLE_FILTER,
        )

        if file_paths:
            # Set internal operation flag to prevent full UI updates
            self._in_internal_drag = True

            skipped = 0
            any_subtitle_added = False
            child_items_added = []

            for file_path in file_paths:
                if file_path == parent_item.data(0, Qt.ItemDataRole.UserRole):
                    skipped += 1
                    continue
                if not is_subtitle_file(file_path):
                    QMessageBox.warning(
                        self.app_parent,
                        texts.INVALID_FILE_TITLE,
                        texts.INVALID_SUBTITLE_FILE_MESSAGE.format(
                            filename=get_basename(file_path)
                        ),
                    )
                    continue
                if self.is_duplicate_pair(
                    parent_item.data(0, Qt.ItemDataRole.UserRole), file_path
                ):
                    skipped += 1
                    continue
                # Ensure child gets an ID
                child_item = create_tree_widget_item(
                    file_path,
                    parent_item,
                    self.icon_provider,
                    item_id=self._get_next_id(),
                )
                child_items_added.append(child_item)
                any_subtitle_added = True

            if skipped:
                QMessageBox.information(
                    self.app_parent,
                    texts.DUPLICATES_SKIPPED_TITLE,
                    texts.DUPLICATES_SKIPPED_MESSAGE.format(count=skipped),
                )
            if any_subtitle_added:
                parent_item.setExpanded(True)

                # Only update the specific item that was modified
                self._update_parent_item_style([parent_item])
                self._schedule_ui_update()

    def add_video_to_subtitle_dialog(self, subtitle_item):
        """Add a video file as parent to an existing subtitle item, maintaining item position."""

        logger.info(
            f"Adding video to subtitle item: {os.path.basename(subtitle_item.data(0, Qt.ItemDataRole.UserRole)) if subtitle_item and subtitle_item.data(0, Qt.ItemDataRole.UserRole) else None}"
        )

        # Verify the item is actually a subtitle
        item_path = subtitle_item.data(0, Qt.ItemDataRole.UserRole)
        if not item_path or not is_subtitle_file(item_path):
            QMessageBox.warning(
                self.app_parent,
                texts.INVALID_FILE_TITLE,
                texts.INVALID_SUBTITLE_FILE_MESSAGE.format(
                    filename=get_basename(item_path)
                ),
            )
            return

        reference_path = open_filedialog(
            self.app_parent, "file-open", texts.SELECT_VIDEO_FILE_TITLE, VIDEO_FILTER
        )

        if not reference_path:
            return

        if reference_path == subtitle_item.data(0, Qt.ItemDataRole.UserRole):
            QMessageBox.warning(
                self.app_parent,
                texts.INVALID_PAIR_TITLE,
                texts.CANNOT_PAIR_FILE_WITH_ITSELF,
            )
            return

        if self.is_duplicate_pair(
            reference_path, subtitle_item.data(0, Qt.ItemDataRole.UserRole)
        ):
            QMessageBox.warning(
                self.app_parent,
                texts.BATCH_VALIDATE_DUPLICATE_PAIR,
                texts.BATCH_VALIDATE_DUPLICATE_PAIR,
            )
            return

        # Set internal operation flag to prevent full UI updates
        self._in_internal_drag = True

        # Find the index of the subtitle item to preserve position
        root = self.invisibleRootItem()
        sub_index = -1
        for i in range(root.childCount()):
            if root.child(i) == subtitle_item:
                sub_index = i
                break

        if sub_index == -1:
            return  # Item not found, should not happen

        # Create new video parent item with an ID
        video_item_id = self._get_next_id()
        video_item = create_tree_widget_item(
            reference_path, None, self.icon_provider, item_id=video_item_id
        )

        # Preserve subtitle's existing ID or assign a new one if it doesn't have one
        subtitle_item_id = subtitle_item.data(0, self.ITEM_ID_ROLE)
        if subtitle_item_id is None:
            subtitle_item_id = self._get_next_id()
            subtitle_item.setData(0, self.ITEM_ID_ROLE, subtitle_item_id)

        # Take the subtitle item from its current position
        root.removeChild(subtitle_item)

        # Add the subtitle as a child of the video item
        video_item.addChild(subtitle_item)

        # Insert the video item back at the same position
        root.insertChild(sub_index, video_item)

        # Expand the new video parent
        video_item.setExpanded(True)

        # Only update this specific item
        self._update_parent_item_style([video_item])
        self._schedule_ui_update()

    def remove_item(self, item):
        if item:
            logger.info(
                f"Removing item: {os.path.basename(item.data(0, Qt.ItemDataRole.UserRole)) if item.data(0, Qt.ItemDataRole.UserRole) else None}"
            )
            # Set internal operation flag to prevent full UI updates
            self._in_internal_drag = True
            root = self.invisibleRootItem()
            (item.parent() or root).removeChild(item)
            # Only schedule a targeted UI update
            self._schedule_ui_update()

    def remove_selected_items(self):
        selected = self.selectedItems()
        logger.info(f"Removing selected items: {len(selected)}")
        if not selected:
            current = self.currentItem()
            if current:
                selected = [current]
            else:
                return

        if len(selected) > 9:
            reply = QMessageBox.question(
                self.app_parent,
                texts.CONFIRM_REMOVE_SELECTED_TITLE,
                texts.CONFIRM_REMOVE_SELECTED_MESSAGE.format(count=len(selected)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Set internal operation flag to prevent full UI updates
        self._in_internal_drag = True

        # We'll process as a batch removal
        root = self.invisibleRootItem()
        for item in selected:
            (item.parent() or root).removeChild(item)

        # Schedule a single UI update after all removals
        self._schedule_ui_update()

    def change_file_for_item(self, item):
        if not item:
            return
        logger.info(
            f"Changing file for item: {os.path.basename(item.data(0, Qt.ItemDataRole.UserRole)) if item.data(0, Qt.ItemDataRole.UserRole) else None}"
        )
        current_file_path = item.data(0, Qt.ItemDataRole.UserRole)
        is_parent = not item.parent()

        if is_parent:
            file_filter = VIDEO_SUBTITLE_FILTER
            dialog_title = texts.SELECT_REPLACEMENT_VIDEO_OR_SUBTITLE_TITLE
        else:
            file_filter = SUBTITLE_FILTER
            dialog_title = texts.SELECT_REPLACEMENT_SUBTITLE_TITLE

        # Use the centralized function for file selection
        initial_dir = (
            os.path.dirname(current_file_path)
            if current_file_path and os.path.exists(os.path.dirname(current_file_path))
            else None
        )
        new_file_path = open_filedialog(
            self.app_parent, "file-open", dialog_title, file_filter, initial_dir
        )

        if new_file_path:
            new_ext = os.path.splitext(new_file_path)[1].lower()
            valid_new_type = False
            if is_parent and new_ext in (VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS):
                valid_new_type = True
            elif not is_parent and new_ext in SUBTITLE_EXTENSIONS:
                valid_new_type = True

            if not valid_new_type:
                QMessageBox.warning(
                    self.app_parent,
                    texts.INVALID_FILE_TYPE_TITLE,
                    texts.INVALID_FILE_TYPE_MESSAGE,
                )
                return

            item.setText(0, os.path.basename(new_file_path))
            item.setData(0, Qt.ItemDataRole.UserRole, new_file_path)
            item.setIcon(0, self._get_file_icon(new_file_path))

    def clear_all_items(self):
        pair_count = self.topLevelItemCount()
        logger.info(f"Clearing all items. Count: {pair_count}")
        if pair_count > 9:
            reply = QMessageBox.question(
                self.app_parent,
                texts.CONFIRM_CLEAR_ALL_TITLE,
                texts.CONFIRM_CLEAR_ALL_MESSAGE,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        if pair_count > 0:
            self.clear()

    def open_item_folder(self, item):
        """Open the folder containing the file for the given item."""
        if not item:
            return

        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(
                self.app_parent,
                texts.FILE_NOT_FOUND_TITLE,
                texts.FILE_NOT_FOUND_MESSAGE,
            )
            return

        open_folder(file_path)

    def get_all_valid_pairs(self):
        pairs = []
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if (
                item
                and item.childCount() == 1
                and item.data(0, self.VALID_STATE_ROLE) == "valid"
            ):
                reference_path = item.data(0, Qt.ItemDataRole.UserRole)
                sub_item = item.child(0)
                sub_path = sub_item.data(0, Qt.ItemDataRole.UserRole)
                if reference_path and sub_path:
                    pairs.append((reference_path, sub_path))
        return pairs

    def has_items(self):
        return self.topLevelItemCount() > 0


# Helper functions for the main application's batch mode
def create_batch_interface(self):
    """Create the batch mode interface elements for the main application."""
    # Initialize batch mode UI elements if they don't exist
    if not hasattr(self, "batch_buttons_widget"):
        self.batch_buttons_widget = QWidget(self)
        batch_buttons_layout = QHBoxLayout(self.batch_buttons_widget)
        batch_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_batch_add_files = QPushButton(
            texts.ADD_FILES, self.batch_buttons_widget
        )
        self.btn_batch_add_files.clicked.connect(
            lambda: self.show_batch_add_menu(self.btn_batch_add_files)
        )
        self.btn_batch_remove_selected = QPushButton(
            texts.REMOVE_SELECTED, self.batch_buttons_widget
        )
        self.btn_batch_remove_selected.clicked.connect(
            self.batch_tree_view.remove_selected_items
        )
        self.btn_batch_change_selected = QPushButton(
            texts.CHANGE_SELECTED, self.batch_buttons_widget
        )
        self.btn_batch_change_selected.clicked.connect(
            lambda: self.batch_tree_view.change_file_for_item(
                self.batch_tree_view.currentItem()
            )
        )

        batch_buttons_layout.addWidget(self.btn_batch_add_files)
        batch_buttons_layout.addWidget(self.btn_batch_remove_selected)
        batch_buttons_layout.addWidget(self.btn_batch_change_selected)


def show_batch_add_menu(self, source_widget=None, position=None):
    """Show the batch add menu with various file addition options.

    Args:
        source_widget: The widget that triggered the menu (optional)
        position: The global position where to show the menu (optional)
    """
    menu = QMenu(self)
    action_add_pair = menu.addAction(texts.ADD_PAIR)
    action_add_continuously = menu.addAction(texts.ADD_PAIR_CONTINUOUSLY)
    action_add_folder = menu.addAction(texts.ADD_FOLDER)
    action_add_files = menu.addAction(texts.ADD_MULTIPLE_FILES)
    # Add new auto-pairing option
    menu.addSeparator()
    action_auto_pairing = menu.addAction(texts.AUTO_PAIRING_SEASON_EPISODE)
    # Add "pair multiple subtitles with single source" option
    action_pair_multiple_subs = menu.addAction(texts.PAIR_MULTIPLE_SUBTITLES_WITH_SINGLE_SOURCE)

    action_add_pair.triggered.connect(lambda: handle_add_pair(self))
    action_add_folder.triggered.connect(lambda: handle_add_folder(self))
    action_add_files.triggered.connect(lambda: handle_add_multiple_files(self))
    action_add_continuously.triggered.connect(
        lambda: handle_add_pairs_continuously(self)
    )
    # Connect the new auto-pairing option
    action_auto_pairing.triggered.connect(lambda: self.open_auto_pairing_dialog())
    # Connect the "pair multiple subtitles with single source" option
    action_pair_multiple_subs.triggered.connect(lambda: self.open_pair_multiple_subs_dialog())

    # Show menu at the specified position, or at a position relevant to the source widget
    if position:
        menu.popup(position)
    elif source_widget:
        # For InputBox, position at bottom-left. For button, also bottom-left.
        if isinstance(source_widget, QLabel) and hasattr(source_widget, "input_type"):
            menu.popup(source_widget.mapToGlobal(QPoint(0, source_widget.height())))
        else:  # Assuming QPushButton or similar
            menu.popup(source_widget.mapToGlobal(source_widget.rect().bottomLeft()))
    else:
        # Default fallback to cursor position
        menu.popup(QCursor.pos())

    return menu  # Return the menu so caller can connect to its signals


def handle_add_pair(self):
    """Show dialogs to add a video/subtitle pair."""
    video_ref_path = open_filedialog(
        self,
        "file-open",
        texts.SELECT_VIDEO_OR_SUBTITLE_FILE_TITLE,
        VIDEO_SUBTITLE_FILTER,
    )
    if not video_ref_path:
        return

    # Check if the selected file is a supported media type
    ext = os.path.splitext(video_ref_path)[1].lower()
    if ext not in (VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS):
        QMessageBox.warning(
            self,
            texts.UNSUPPORTED_FILE_TYPE_TITLE,
            texts.UNSUPPORTED_FILE_TYPE_MESSAGE,
        )
        return

    sub_path = open_filedialog(
        self, "file-open", texts.SELECT_SUBTITLE_FILE_TITLE, SUBTITLE_FILTER
    )
    if not sub_path:
        return

    # Check if the selected subtitle file is supported
    ext = os.path.splitext(sub_path)[1].lower()
    if ext not in SUBTITLE_EXTENSIONS:
        QMessageBox.warning(
            self,
            texts.UNSUPPORTED_FILE_TYPE_TITLE,
            texts.UNSUPPORTED_SUBTITLE_FORMAT,
        )
        return

    if video_ref_path == sub_path:
        QMessageBox.warning(
            self, texts.INVALID_PAIR_TITLE, texts.CANNOT_PAIR_FILE_WITH_ITSELF
        )
        return

    if self.batch_tree_view.is_duplicate_pair(video_ref_path, sub_path):
        QMessageBox.warning(
            self,
            texts.BATCH_VALIDATE_DUPLICATE_PAIR,
            texts.BATCH_VALIDATE_DUPLICATE_PAIR,
        )
        return
    self.batch_tree_view.add_explicit_pair(video_ref_path, sub_path)


def handle_add_folder(self):
    """Add all supported files from a folder to the batch."""
    folder_path = open_filedialog(
        self, "directory", texts.SELECT_FOLDER_CONTAINING_MEDIA_FILES_TITLE
    )
    if folder_path:
        # Check if folder contains any media files before adding
        media_files_found = False
        for root, _, filenames in os.walk(folder_path):
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext in VIDEO_EXTENSIONS or ext in SUBTITLE_EXTENSIONS:
                    media_files_found = True
                    break
            if media_files_found:
                break

        if not media_files_found:
            QMessageBox.warning(
                self,
                texts.NO_MEDIA_FILES_FOUND_TITLE,
                texts.NO_MEDIA_FILES_FOUND_MESSAGE,
            )
            return

        self.batch_tree_view.add_files_or_folders([folder_path])


def handle_add_multiple_files(self):
    """Allow selection of multiple files to add to the batch."""
    files_paths = open_filedialog(
        self, "files-open", texts.SELECT_FILES_TITLE, VIDEO_SUBTITLE_FILTER
    )
    if files_paths:
        # Check if any of the selected files are supported media types
        supported_files = []
        for file_path in files_paths:
            ext = os.path.splitext(file_path)[1].lower()
            if ext in VIDEO_EXTENSIONS or ext in SUBTITLE_EXTENSIONS:
                supported_files.append(file_path)

        if not supported_files:
            QMessageBox.warning(
                self,
                texts.NO_MEDIA_FILES_FOUND_TITLE,
                texts.NO_MEDIA_FILES_FOUND_MESSAGE,
            )
            return
        elif len(supported_files) < len(files_paths):
            unsupported_count = len(files_paths) - len(supported_files)
            QMessageBox.information(
                self,
                texts.SOME_FILES_SKIPPED_TITLE,
                texts.SOME_FILES_SKIPPED_MESSAGE.format(count=unsupported_count),
            )

        self.batch_tree_view.add_files_or_folders(supported_files)


def handle_add_pairs_continuously(self):
    """Continuously prompt for video/subtitle pairs until canceled."""
    while True:
        video_ref_path = open_filedialog(
            self,
            "file-open",
            texts.SELECT_VIDEO_OR_SUBTITLE_FILE_TITLE,
            VIDEO_SUBTITLE_FILTER,
        )
        if not video_ref_path:
            break  # User cancelled video selection

        # Check if the selected file is a supported media type
        ext = os.path.splitext(video_ref_path)[1].lower()
        if ext not in (VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS):
            QMessageBox.warning(
                self,
                texts.UNSUPPORTED_FILE_TYPE_TITLE,
                texts.UNSUPPORTED_FILE_TYPE_MESSAGE,
            )
            continue

        sub_path = open_filedialog(
            self,
            "file-open",
            texts.SELECT_SUBTITLE_FILE_TITLE,
            SUBTITLE_FILTER,
        )
        if not sub_path:
            break  # User cancelled subtitle selection

        # Check if the selected subtitle file is supported
        ext = os.path.splitext(sub_path)[1].lower()
        if ext not in SUBTITLE_EXTENSIONS:
            QMessageBox.warning(
                self,
                texts.UNSUPPORTED_FILE_TYPE_TITLE,
                texts.UNSUPPORTED_SUBTITLE_FORMAT,
            )
            continue

        if video_ref_path == sub_path:
            QMessageBox.warning(
                self, texts.INVALID_PAIR_TITLE, texts.CANNOT_PAIR_FILE_WITH_ITSELF
            )
            continue

        if self.batch_tree_view.is_duplicate_pair(video_ref_path, sub_path):
            QMessageBox.warning(
                self,
                texts.BATCH_VALIDATE_DUPLICATE_PAIR,
                texts.BATCH_VALIDATE_DUPLICATE_PAIR,
            )
            continue
        self.batch_tree_view.add_explicit_pair(video_ref_path, sub_path)


def handle_batch_drop(self, files):
    logger.info(f"handle_batch_drop: {len(files)} files")
    """Handle files dropped onto the batch input box."""
    if files:
        self.batch_tree_view.add_files_or_folders(files)


def update_batch_buttons_state(self):
    """Update the enabled state of batch buttons based on selection."""

    if hasattr(self, "btn_batch_remove_selected") and hasattr(
        self, "btn_batch_change_selected"
    ):
        selected_items = self.batch_tree_view.selectedItems()
        has_selection = bool(selected_items)

        # Avoid unnecessary UI updates by checking if state actually changed
        new_remove_state = has_selection
        new_change_state = len(selected_items) == 1

        # Only update if state changed
        if self.btn_batch_remove_selected.isEnabled() != new_remove_state:
            self.btn_batch_remove_selected.setEnabled(new_remove_state)

        if self.btn_batch_change_selected.isEnabled() != new_change_state:
            self.btn_batch_change_selected.setEnabled(new_change_state)


def toggle_batch_mode(self):
    """Toggle between batch mode and normal mode."""
    self.batch_mode_enabled = not self.batch_mode_enabled
    update_config(self, "batch_mode", self.batch_mode_enabled)
    self.btn_batch_mode.setText(
        texts.NORMAL_MODE if self.batch_mode_enabled else texts.BATCH_MODE
    )
    self.show_auto_sync_inputs()


def validate_batch_inputs(self):
    """Validate batch mode inputs."""
    if not self.batch_tree_view.has_items():
        # Show error in batch input instead of QMessageBox
        if hasattr(self, "batch_input"):
            self.batch_input.show_error(texts.BATCH_ADD_FILES_ERROR)
        return False

    valid_pairs = self.batch_tree_view.get_all_valid_pairs()
    if not valid_pairs:
        logger.warning("No valid pairs found for batch processing.")
        QMessageBox.warning(
            self, texts.NO_VALID_PAIRS_TITLE, texts.NO_VALID_PAIRS_MESSAGE
        )
        return False

    # Log information about valid pairs for debugging
    logger.info(
        f"Batch mode validation passed with {len(valid_pairs)} valid pairs. Starting sync..."
    )

    return True  # Indicate validation passed
