"""
This module provides batch processing functionality for AutoSubSync.
It's designed to be imported and used by the main application without creating circular imports.

The module exports:
- BatchTreeView: A tree view widget for displaying and managing batches of video/subtitle files
- Helper functions for batch operations that are attached to the main app at runtime
"""

from PyQt5.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QAbstractItemView,
    QMenu,
    QMessageBox,
    QFileDialog,
    QFileIconProvider,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QWidget
)
from PyQt5.QtCore import Qt, QTimer, QFileInfo, QPoint, QUrl
from PyQt5.QtGui import QCursor, QColor, QDesktopServices

import os
import re
from constants import VIDEO_EXTENSIONS, SUBTITLE_EXTENSIONS, COLORS
from utils import update_config

# Constants for file dialogs
VIDEO_SUBTITLE_FILTER = f"Video/Subtitle Files (*{' *'.join(VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS)})"
VIDEO_FILTER = f"Video Files (*{' *'.join(VIDEO_EXTENSIONS)})"
SUBTITLE_FILTER = f"Subtitle Files (*{' *'.join(SUBTITLE_EXTENSIONS)})"

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

def calculate_file_similarity(video_name, sub_name):
    """Calculate similarity score between video and subtitle filenames.
    
    This function uses multiple methods to determine the similarity:
    1. Uses effective_basename to remove language tags
    2. Calculates common prefix length
    3. Uses a string similarity ratio
    
    Args:
        video_name: Basename of a video file
        sub_name: Basename of a subtitle file
        
    Returns:
        Similarity score (higher is more similar)
    """
    # Clean and prepare names
    video_base = effective_basename(video_name).lower().strip('.-_ [](){}')
    sub_base = effective_basename(sub_name).lower().strip('.-_ [](){}')
    
    # Calculate common prefix length
    common_len = 0
    for i in range(min(len(video_base), len(sub_base))):
        if video_base[i] == sub_base[i]:
            common_len += 1
        else:
            break
            
    # Calculate similarity score - weight by:
    # 1. Common prefix length (heavily weighted)
    # 2. Length difference (penalty for very different lengths)
    # 3. Bonus for exact match after processing
    
    similarity = common_len * 10  # Base score from common prefix
    
    # Penalty for length difference
    length_diff = abs(len(video_base) - len(sub_base))
    similarity -= min(length_diff * 2, similarity // 2)  # Don't let penalty exceed half the score
    
    # Exact match bonus
    if video_base == sub_base:
        similarity += 50
        
    return max(0, similarity)  # Ensure non-negative score

def create_tree_widget_item(file_path, parent=None, icon_provider=None):
    """Create a QTreeWidgetItem for a file path.
    
    Args:
        file_path: Path to the file
        parent: Optional parent item
        icon_provider: Optional QFileIconProvider for file icons
        
    Returns:
        A configured QTreeWidgetItem
    """
    basename = get_basename(file_path)
    if parent:
        item = QTreeWidgetItem(parent, [basename])
    else:
        item = QTreeWidgetItem([basename])
    
    item.setData(0, Qt.UserRole, file_path)
    
    # Add icon if provider is available
    if icon_provider:
        item.setIcon(0, icon_provider.icon(QFileInfo(file_path)))
        
    return item

def attach_functions_to_autosubsync(autosubsync_class):
    """Attach batch mode functions to the autosubsync class"""
    autosubsync_class.show_batch_add_menu = show_batch_add_menu
    autosubsync_class.handle_add_pair = handle_add_pair
    autosubsync_class.handle_add_folder = handle_add_folder
    autosubsync_class.handle_add_multiple_files = handle_add_multiple_files
    autosubsync_class.handle_add_pairs_continuously = handle_add_pairs_continuously
    autosubsync_class.handle_batch_drop = handle_batch_drop
    autosubsync_class.update_batch_buttons_state = update_batch_buttons_state
    autosubsync_class.toggle_batch_mode = toggle_batch_mode
    autosubsync_class.validate_batch_inputs = validate_batch_inputs


def select_files_with_directory_update(parent_instance, dialog_type, title, file_filter=None, initial_dir=None, multiple=False):
    """Helper function for file selection dialogs that update the last used directory.
    
    Args:
        parent_instance: The parent widget/window for the dialog
        dialog_type: 'file-open', 'files-open', or 'directory' for different QFileDialog types
        title: Title for the dialog
        file_filter: Optional filter for file types
        initial_dir: Initial directory to open the dialog at
        multiple: Whether to allow multiple selection
        
    Returns:
        Selected file path(s) or None if canceled
    """
    config_dir = parent_instance.config.get("last_used_dir", "") if hasattr(parent_instance, "config") else ""
    start_dir = initial_dir or config_dir or ""
    
    result = None
    
    if dialog_type == 'file-open':
        result, _ = QFileDialog.getOpenFileName(parent_instance, title, start_dir, file_filter or "")
    elif dialog_type == 'files-open':
        result, _ = QFileDialog.getOpenFileNames(parent_instance, title, start_dir, file_filter or "")
    elif dialog_type == 'directory':
        result = QFileDialog.getExistingDirectory(parent_instance, title, start_dir)
    
    # Update the last used directory if a file/directory was selected
    if result:
        if isinstance(result, list) and result:  # Multiple files selected
            update_config(parent_instance, "last_used_dir", os.path.dirname(result[0]))
        elif isinstance(result, str) and result:  # Single file or directory
            if dialog_type == 'directory':
                update_config(parent_instance, "last_used_dir", result)
            else:
                update_config(parent_instance, "last_used_dir", os.path.dirname(result))
    
    return result

class BatchTreeView(QTreeWidget):
    VALID_STATE_ROLE = Qt.UserRole + 10  # Role to store parent item's validity state

    def _is_parent_item_valid(self, item):
        """Helper to determine if a parent item is valid (has exactly one child, and that child has no children and is not a video file)."""
        if not item or item.parent(): # Must be a top-level item
            return False
        if item.childCount() == 1:
            first_child = item.child(0)
            if first_child and first_child.childCount() > 0: # Child must not have children
                return False
            elif first_child: # Child exists and has no children
                child_file_path = first_child.data(0, Qt.UserRole)
                if child_file_path:
                    child_ext = get_file_extension(child_file_path)
                    if child_ext in VIDEO_EXTENSIONS: # Child must not be a video file
                        return False
            return True # Valid: one child, no grandchildren, child is not a video
        return False # Not exactly one child

    def __init__(self, parent_app=None):  # parent_app is the autosubsync instance
        super().__init__(parent_app)
        self.app_parent = parent_app
        self.setColumnCount(1)
        self.setHeaderHidden(False)  # Show header to display pair counts
        #self.headerItem().setTextAlignment(0, Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setStyleSheet("QTreeView::item { height: 32px; }")
        self.icon_provider = QFileIconProvider()
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)  # Allow multi-selection for removal

        self._update_ui_timer = QTimer(self)
        self._update_ui_timer.setSingleShot(True)
        self._update_ui_timer.setInterval(0) # Process on next event loop iteration
        self._update_ui_timer.timeout.connect(self._perform_actual_ui_update)

        self._items_to_re_expand_paths = set() # For preserving expansion state during moves

        # Connect model signals to schedule UI update
        model = self.model()
        model.rowsInserted.connect(self._schedule_ui_update)
        model.rowsRemoved.connect(self._schedule_ui_update)
        model.modelReset.connect(self._schedule_ui_update)

    def _schedule_ui_update(self, *args): # Accept any arguments from signals
        self._update_ui_timer.start()

    def _perform_actual_ui_update(self):
        if self.app_parent and hasattr(self.app_parent, 'update_auto_sync_ui_for_batch'):
            self.app_parent.update_auto_sync_ui_for_batch()

        # Re-apply expansion state for items that were moved
        if self._items_to_re_expand_paths:
            self._apply_expansion_recursive(self) # Start recursion from the tree itself
            self._items_to_re_expand_paths.clear() # Clear after use
        
        self._update_parent_item_style() # Update styles for all parent items
        self._update_header_pair_counts() # Update header with valid/invalid pair counts
        self._sort_top_level_items() # Sort items after updates

    def _sort_top_level_items(self):
        # Expand all top-level items
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item: # Ensure item is valid
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
        
        header_text = f"Pairs ({valid_pairs} Valid, {invalid_pairs} Invalid)"
        self.setHeaderLabel(header_text)

    def _apply_expansion_recursive(self, parent_item_or_tree):
        if isinstance(parent_item_or_tree, QTreeWidgetItem):
            child_count = parent_item_or_tree.childCount()
            get_child = parent_item_or_tree.child
        else: # It's the tree itself (QTreeWidget)
            child_count = parent_item_or_tree.topLevelItemCount()
            get_child = parent_item_or_tree.topLevelItem

        for i in range(child_count):
            item = get_child(i)
            if item: # Ensure item is valid
                path = item.data(0, Qt.UserRole)
                if path in self._items_to_re_expand_paths:
                    item.setExpanded(True)
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
        return Qt.transparent

    def _set_item_tooltip(self, item):
        """Set tooltip for items - only show validity status for parent items."""
        if not item:
            return

        is_parent = not bool(item.parent())
        tooltip_text = ""  # Default to empty tooltip

        if is_parent:
            status_string = item.data(0, self.VALID_STATE_ROLE)
            if status_string:  # e.g., 'valid' or 'invalid'
                status_display = status_string.capitalize()
                tooltip_text = f"Status: {status_display}"
                
                # Add informative message for invalid items
                if status_string == "invalid":
                    child_count = item.childCount()
                    if child_count == 0:
                        tooltip_text += "\nAdd a subtitle file to this item"
                    elif child_count > 1:
                        tooltip_text += "\nToo many files - keep only one subtitle per item"
                    elif child_count == 1:
                        first_child = item.child(0)
                        if first_child and first_child.childCount() > 0:
                            tooltip_text += "\nNested items not allowed - remove extra levels"
                        elif first_child:
                            # Check if single child is a video file
                            child_file_path = first_child.data(0, Qt.UserRole)
                            if child_file_path:
                                child_ext = os.path.splitext(child_file_path)[1].lower()
                                if child_ext in VIDEO_EXTENSIONS:
                                    tooltip_text += "\nVideo files cannot be children - add a subtitle instead"
        
        item.setToolTip(0, tooltip_text)  # Children get empty tooltip

    def _update_parent_item_style(self, specific_items_affected=None, old_parents_affected=None):
        """Update item background colors based on validity state.
           Efficiently updates specific items if provided, otherwise full scan.
           A parent is 'valid' if it has exactly one child, and that child has no children.
        """
        green_qcolor = self._parse_rgba_to_qcolor(COLORS['GREEN_BACKGROUND_HOVER']) 
        red_qcolor = self._parse_rgba_to_qcolor(COLORS['RED_BACKGROUND_HOVER'])     
        default_qcolor = QColor(Qt.transparent)

        def _apply_validity_and_style_recursive(item_to_style):
            is_stylable_parent = not bool(item_to_style.parent())

            if is_stylable_parent:
                # Use the helper function to determine validity
                is_valid = self._is_parent_item_valid(item_to_style)
                
                item_to_style.setData(0, self.VALID_STATE_ROLE, "valid" if is_valid else "invalid")
                item_to_style.setBackground(0, green_qcolor if is_valid else red_qcolor)

                for i in range(item_to_style.childCount()):
                    child = item_to_style.child(i)
                    if child:
                        _apply_validity_and_style_recursive(child)
            
            else:  # Child item or deeper descendant
                item_to_style.setBackground(0, default_qcolor)
                item_to_style.setData(0, self.VALID_STATE_ROLE, None) # Clear state for non-parents

                for i in range(item_to_style.childCount()):
                    grand_child = item_to_style.child(i)
                    if grand_child:
                        _apply_validity_and_style_recursive(grand_child)

            # Update tooltip after all state and style information is set
            self._set_item_tooltip(item_to_style)

        if specific_items_affected:
            roots_to_process = set()
            for item in specific_items_affected:
                if item:
                    current_ancestor = item
                    while current_ancestor.parent():
                        current_ancestor = current_ancestor.parent()
                    roots_to_process.add(current_ancestor)
            
            if old_parents_affected:
                for item in old_parents_affected:
                    if item: 
                        old_ancestor = item
                        while old_ancestor.parent(): 
                            old_ancestor = old_ancestor.parent()
                        roots_to_process.add(old_ancestor)

            for root_item in roots_to_process:
                if root_item and root_item.treeWidget() == self: 
                     _apply_validity_and_style_recursive(root_item)
        else:
            for i in range(self.topLevelItemCount()):
                top_item = self.topLevelItem(i)
                if top_item:
                    _apply_validity_and_style_recursive(top_item)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            files = [u.toLocalFile() for u in event.mimeData().urls()]
            # Determine drop target
            target_item = self.itemAt(event.pos())
            self.add_files_or_folders(files, drop_target_item=target_item) # Model signals will trigger update
            event.acceptProposedAction()
        else:
            # Handle internal move
            dragged_items = self.selectedItems() # Capture selected items (those being dragged)
            if not dragged_items: 
                super().dropEvent(event) # Default handling or ignore
                return

            self._items_to_re_expand_paths.clear()
            for item in dragged_items:
                if item.isExpanded(): 
                    path = item.data(0, Qt.UserRole)
                    if path:
                        self._items_to_re_expand_paths.add(path)
            
            super().dropEvent(event) # Perform the move. Model signals will fire.
            
            if not event.isAccepted(): # If super().dropEvent() did not accept the drop
                self._items_to_re_expand_paths.clear()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        selected_items = self.selectedItems()
        item_at_pos = self.itemAt(event.pos())

        add_files_menu = menu.addMenu("Add files")
        action_add_pair = add_files_menu.addAction("Add pair")
        action_add_continuously = add_files_menu.addAction("Add pair (continuously)")
        action_add_folder = add_files_menu.addAction("Add folder")
        action_add_files = add_files_menu.addAction("Add multiple files")

        action_add_pair.triggered.connect(lambda: self.app_parent.handle_add_pair())
        action_add_folder.triggered.connect(lambda: self.app_parent.handle_add_folder())
        action_add_files.triggered.connect(lambda: self.app_parent.handle_add_multiple_files())
        action_add_continuously.triggered.connect(self.app_parent.handle_add_pairs_continuously)
        
        menu.addSeparator()

        if item_at_pos and not item_at_pos.parent():  # Right-clicked a top-level item
            menu.addAction("Add subtitle to this item", lambda: self.add_subtitle_to_item_dialog(item_at_pos))
            # Check if the top-level item is a subtitle file
            item_path = item_at_pos.data(0, Qt.UserRole)
            if item_path and os.path.splitext(item_path)[1].lower() in SUBTITLE_EXTENSIONS:
                menu.addAction("Add video to this item", lambda: self.add_video_to_subtitle_dialog(item_at_pos))

        # Add 'Go to folder' option for any item
        if item_at_pos:
            menu.addAction("Go to folder", lambda: self.open_item_folder(item_at_pos))

        if selected_items:  # Operations for selected items
            if len(selected_items) == 1 and item_at_pos:  # Change only makes sense for a single item
                menu.addAction("Change", lambda: self.change_file_for_item(item_at_pos))
            menu.addAction(f"Remove selected ({len(selected_items)})", self.remove_selected_items)
        elif item_at_pos:  # Fallback if no selection but right-clicked on an item
            menu.addAction("Remove", lambda: self.remove_item(item_at_pos))
            menu.addAction("Change", lambda: self.change_file_for_item(item_at_pos))


        
        menu.addSeparator()
        action_clear_all = menu.addAction("Clear all")
        action_clear_all.triggered.connect(self.clear_all_items)
        if not self.has_items():
            action_clear_all.setEnabled(False)
        if not selected_items and not item_at_pos:  # Disable remove/change if not on item and no selection
            for act in menu.actions():
                if act.text().startswith("Remove") or act.text().startswith("Change"):
                    act.setEnabled(False)

        menu.popup(self.viewport().mapToGlobal(event.pos()))

    def keyPressEvent(self, event):
        """Handle keyboard events."""
        if event.key() == Qt.Key_Delete:
            # Delete key pressed - remove selected items
            self.remove_selected_items()
        else:
            # Pass other key events to the parent class
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        """Handle mouse press events to clear selection when clicking empty area."""
        item = self.itemAt(event.pos())
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
        # Special case: Check if there are exactly 2 files, one video and one subtitle
        if len(paths) == 2 and all(os.path.isfile(path) for path in paths):
            exts = [os.path.splitext(path)[1].lower() for path in paths]
            # Check if we have one video and one subtitle file
            if (exts[0] in VIDEO_EXTENSIONS and exts[1] in SUBTITLE_EXTENSIONS):
                video_path, sub_path = paths[0], paths[1]
                self.add_explicit_pair(video_path, sub_path)
                return
            elif (exts[1] in VIDEO_EXTENSIONS and exts[0] in SUBTITLE_EXTENSIONS):
                video_path, sub_path = paths[1], paths[0]
                self.add_explicit_pair(video_path, sub_path)
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
        
        if files_to_process:
            self.add_paired_files(files_to_process, drop_target_item=drop_target_item)

    def add_paired_files(self, file_paths, drop_target_item=None):
        newly_created_top_level_items = [] # Collect new items here

        # First separate videos and subtitles
        videos = sorted([f for f in file_paths if os.path.splitext(f)[1].lower() in VIDEO_EXTENSIONS])
        subs = sorted([f for f in file_paths if os.path.splitext(f)[1].lower() in SUBTITLE_EXTENSIONS])
        
        # Store which files have been paired already
        paired_videos = set()
        paired_subs = set()
        
        # Create video-subtitle pairs based on basename similarity
        video_sub_pairs = []
        
        # First pass: Try exact basename matching (without language tags)
        for video in videos:
            video_base = effective_basename(video).lower().strip('.-_ [](){}')
            
            best_match = None
            for sub in subs:
                if sub in paired_subs:
                    continue
                    
                sub_base = effective_basename(sub).lower().strip('.-_ [](){}')
                
                # If bases match exactly
                if video_base == sub_base:
                    best_match = sub
                    break
            
            if best_match:
                video_sub_pairs.append((video, best_match))
                paired_videos.add(video)
                paired_subs.add(best_match)
        
        # Second pass: Try to match remaining videos/subs with more flexible matching
        for video in videos:
            if video in paired_videos:
                continue
                
            video_base = effective_basename(video).lower().strip('.-_ [](){}')
            best_match = None
            best_score = 0
            
            for sub in subs:
                if sub in paired_subs:
                    continue
                    
                sub_base = effective_basename(sub).lower().strip('.-_ [](){}')
                
                # Calculate similarity score
                similarity_score = calculate_file_similarity(video_base, sub_base)
                
                if similarity_score > best_score:
                    best_score = similarity_score
                    best_match = sub
            
            # If we found a match with a reasonable score (at least 30)
            if best_match and best_score >= 30:
                video_sub_pairs.append((video, best_match))
                paired_videos.add(video)
                paired_subs.add(best_match)
        
        # Handle any videos or subs that couldn't be paired
        # Create individual entries for unpaired videos
        for video in videos:
            if video not in paired_videos:
                parent_item = QTreeWidgetItem([os.path.basename(video)])
                parent_item.setData(0, Qt.UserRole, video)
                parent_item.setIcon(0, self._get_file_icon(video))
                newly_created_top_level_items.append(parent_item)
        
        # Create individual entries for unpaired subs
        for sub in subs:
            if sub not in paired_subs:
                parent_item = QTreeWidgetItem([os.path.basename(sub)])
                parent_item.setData(0, Qt.UserRole, sub)
                parent_item.setIcon(0, self._get_file_icon(sub))
                newly_created_top_level_items.append(parent_item)
        
        # Now create tree items for each video-sub pair
        for video, sub in video_sub_pairs:
            # Create a new parent item for the video
            parent_item = QTreeWidgetItem([os.path.basename(video)])
            parent_item.setData(0, Qt.UserRole, video)
            parent_item.setIcon(0, self._get_file_icon(video))
            
            # Add the subtitle as a child
            child_item = QTreeWidgetItem(parent_item, [os.path.basename(sub)])
            child_item.setData(0, Qt.UserRole, sub)
            child_item.setIcon(0, self._get_file_icon(sub))
            
            # Expand the parent item and add to our collection
            parent_item.setExpanded(True)
            newly_created_top_level_items.append(parent_item)
            
        # Special case: Handle dropping subtitles onto an existing item
        if drop_target_item and drop_target_item.parent() is None and len(paired_videos) == 0 and len(subs) > 0:
            target_item_path = drop_target_item.data(0, Qt.UserRole)
            target_is_valid_top_level_media = (
                target_item_path and
                os.path.splitext(target_item_path)[1].lower() in (VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS)
            )
            
            if target_is_valid_top_level_media:
                # Add any subtitles that weren't paired as children to the drop target
                for sub in subs:
                    if sub not in paired_subs:  # Only add unpaired subtitles
                        child_item = QTreeWidgetItem(drop_target_item, [os.path.basename(sub)])
                        child_item.setData(0, Qt.UserRole, sub)
                        child_item.setIcon(0, self._get_file_icon(sub))
                        drop_target_item.setExpanded(True)
                        # Mark this subtitle as paired so it doesn't get added as a standalone item
                        paired_subs.add(sub)
        
        if newly_created_top_level_items:
            def sort_key_for_new_items(item):
                state = self._get_provisional_validity(item)
                file_path = item.data(0, Qt.UserRole)
                name = os.path.basename(file_path) if file_path else ""
                return (0 if state == 'invalid' else 1, name.lower())

            newly_created_top_level_items.sort(key=sort_key_for_new_items)

            for item in reversed(newly_created_top_level_items):
                self.insertTopLevelItem(0, item)

    def add_explicit_pair(self, video_ref_path, sub_path):
        """Add an explicit video-subtitle pair to the tree.
        
        Args:
            video_ref_path: Path to video or reference subtitle file
            sub_path: Path to subtitle file to synchronize
        """
        parent_item = create_tree_widget_item(video_ref_path, None, self.icon_provider)
        child_item = create_tree_widget_item(sub_path, parent_item, self.icon_provider)
        
        parent_item.setExpanded(True)
        self.insertTopLevelItem(0, parent_item) # Insert the configured parent item at the top
        # UI update (including sort) will be scheduled by model signals

    def add_subtitle_to_item_dialog(self, parent_item):
        if not parent_item or parent_item.parent():  # Must be a top-level item
            QMessageBox.warning(self.app_parent, "Selection Error", "Please select a video or reference subtitle (a top-level item) to add a subtitle to.")
            return

        file_paths = select_files_with_directory_update(
            self.app_parent,
            'files-open',
            "Select Subtitle File(s)",
            SUBTITLE_FILTER
        )
        
        if file_paths:
            any_subtitle_added = False
            for file_path in file_paths:
                if not is_subtitle_file(file_path):
                    QMessageBox.warning(self.app_parent, "Invalid File", f"'{get_basename(file_path)}' is not a subtitle file. Skipping.")
                    continue
                
                child_item = create_tree_widget_item(file_path, parent_item, self.icon_provider)
                any_subtitle_added = True
            
            if any_subtitle_added:
                parent_item.setExpanded(True)

    def add_video_to_subtitle_dialog(self, subtitle_item):
        """Add a video file as parent to an existing subtitle item, maintaining item position."""

        # Verify the item is actually a subtitle
        item_path = subtitle_item.data(0, Qt.UserRole)
        if not item_path or not is_subtitle_file(item_path):
            QMessageBox.warning(self.app_parent, "Invalid Item", "Selected item is not a subtitle file.")
            return

        video_path = select_files_with_directory_update(
            self.app_parent, 
            'file-open', 
            "Select Video File", 
            VIDEO_FILTER
        )
        
        if not video_path:
            return

        # Find the index of the subtitle item to preserve position
        root = self.invisibleRootItem()
        sub_index = -1
        for i in range(root.childCount()):
            if root.child(i) == subtitle_item:
                sub_index = i
                break

        if sub_index == -1:
            return  # Item not found, should not happen

        # Create new video parent item
        video_item = create_tree_widget_item(video_path, None, self.icon_provider)

        # Take the subtitle item from its current position
        root.removeChild(subtitle_item)
        
        # Add the subtitle as a child of the video item
        video_item.addChild(subtitle_item)
        
        # Insert the video item back at the same position
        root.insertChild(sub_index, video_item)
        
        # Expand the new video parent
        video_item.setExpanded(True)

    def remove_item(self, item):
        if item:
            root = self.invisibleRootItem()
            (item.parent() or root).removeChild(item)

    def remove_selected_items(self):
        selected = self.selectedItems()
        if not selected:
            current = self.currentItem()
            if current: selected = [current]
            else: return

        root = self.invisibleRootItem()
        for item in selected:
            (item.parent() or root).removeChild(item)

    def change_file_for_item(self, item):
        if not item: return

        current_file_path = item.data(0, Qt.UserRole)
        is_parent = not item.parent()
        
        if is_parent:
            file_filter = VIDEO_SUBTITLE_FILTER
            dialog_title = "Select Replacement Video or Reference Subtitle"
        else: 
            file_filter = SUBTITLE_FILTER
            dialog_title = "Select Replacement Subtitle File"

        new_file_path, _ = QFileDialog.getOpenFileName(self.app_parent, dialog_title, os.path.dirname(current_file_path) if current_file_path and os.path.exists(os.path.dirname(current_file_path)) else "", file_filter)
        
        if new_file_path:
            new_ext = os.path.splitext(new_file_path)[1].lower()
            valid_new_type = False
            if is_parent and new_ext in (VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS):
                valid_new_type = True
            elif not is_parent and new_ext in SUBTITLE_EXTENSIONS:
                valid_new_type = True

            if not valid_new_type:
                QMessageBox.warning(self.app_parent, "Invalid File Type", "The selected file type is not appropriate for this item.")
                return

            item.setText(0, os.path.basename(new_file_path))
            item.setData(0, Qt.UserRole, new_file_path)
            item.setIcon(0, self._get_file_icon(new_file_path))

    def clear_all_items(self):
        if self.topLevelItemCount() > 0:
            self.clear()

    def open_item_folder(self, item):
        """Open the folder containing the file for the given item using QDesktopServices."""
        if not item:
            return
        
        file_path = item.data(0, Qt.UserRole)
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self.app_parent, "File Not Found", "The file does not exist or path is invalid.")
            return
        
        folder_path = os.path.dirname(file_path)
        if not os.path.isdir(folder_path):
            QMessageBox.warning(self.app_parent, "Folder Not Found", "The folder does not exist.")
            return
        
        # Use QDesktopServices to open the folder
        folder_url = QUrl.fromLocalFile(folder_path)
        QDesktopServices.openUrl(folder_url)

    def get_all_valid_pairs(self):
        pairs = []
        for i in range(self.topLevelItemCount()):
            parent_item = self.topLevelItem(i)
            parent_file = parent_item.data(0, Qt.UserRole)
            # Ensure parent file exists and is a recognized media or subtitle type
            if not parent_file or not os.path.exists(parent_file): continue
            parent_ext = os.path.splitext(parent_file)[1].lower()
            if parent_ext not in (VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS): continue

            # To form a pair for processing, the parent_item (video or reference subtitle)
            # must have at least one child subtitle file that exists.
            if parent_item.childCount() > 0:
                for j in range(parent_item.childCount()):
                    child_item = parent_item.child(j)
                    child_file = child_item.data(0, Qt.UserRole)
                    # Ensure child file exists and is a subtitle type
                    if not child_file or not os.path.exists(child_file): continue
                    child_ext = os.path.splitext(child_file)[1].lower()
                    if child_ext in SUBTITLE_EXTENSIONS:
                        pairs.append((parent_file, child_file))
        return pairs
            
    def has_items(self):
        return self.topLevelItemCount() > 0


# Helper functions for the main application's batch mode
def create_batch_interface(self):
    """Create the batch mode interface elements for the main application."""
    # Initialize batch mode UI elements if they don't exist
    if not hasattr(self, 'batch_buttons_widget'):
        self.batch_buttons_widget = QWidget(self)
        batch_buttons_layout = QHBoxLayout(self.batch_buttons_widget)
        batch_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_batch_add_files = QPushButton("Add Files", self.batch_buttons_widget)
        self.btn_batch_add_files.clicked.connect(lambda: self.show_batch_add_menu(self.btn_batch_add_files))
        self.btn_batch_remove_selected = QPushButton("Remove Selected", self.batch_buttons_widget)
        self.btn_batch_remove_selected.clicked.connect(self.batch_tree_view.remove_selected_items)
        self.btn_batch_change_selected = QPushButton("Change Selected", self.batch_buttons_widget)
        self.btn_batch_change_selected.clicked.connect(lambda: self.batch_tree_view.change_file_for_item(self.batch_tree_view.currentItem()))
        
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
    action_add_pair = menu.addAction("Add pair")
    action_add_continuously = menu.addAction("Add pair (continuously)")
    action_add_folder = menu.addAction("Add folder")
    action_add_files = menu.addAction("Add multiple files")


    action_add_pair.triggered.connect(lambda: handle_add_pair(self))
    action_add_folder.triggered.connect(lambda: handle_add_folder(self))
    action_add_files.triggered.connect(lambda: handle_add_multiple_files(self))
    action_add_continuously.triggered.connect(lambda: handle_add_pairs_continuously(self))
    
    # Show menu at the specified position, or at a position relevant to the source widget
    if position:
        menu.popup(position)
    elif source_widget:
        # For InputBox, position at bottom-left. For button, also bottom-left.
        if isinstance(source_widget, QLabel) and hasattr(source_widget, 'input_type'):
             menu.popup(source_widget.mapToGlobal(QPoint(0, source_widget.height())))
        else:  # Assuming QPushButton or similar
             menu.popup(source_widget.mapToGlobal(source_widget.rect().bottomLeft()))
    else: 
        # Default fallback to cursor position
        menu.popup(QCursor.pos())
        
    return menu  # Return the menu so caller can connect to its signals

def handle_add_pair(self):
    """Show dialogs to add a video/subtitle pair."""
    video_ref_path = select_files_with_directory_update(
        self, 
        'file-open', 
        "Select Video or Reference Subtitle File", 
        VIDEO_SUBTITLE_FILTER
    )
    if not video_ref_path:
        return
    
    sub_path = select_files_with_directory_update(
        self, 
        'file-open', 
        "Select Input Subtitle File", 
        SUBTITLE_FILTER
    )
    if not sub_path:
        return
    
    self.batch_tree_view.add_explicit_pair(video_ref_path, sub_path)

def handle_add_folder(self):
    """Add all supported files from a folder to the batch."""
    folder_path = select_files_with_directory_update(
        self, 
        'directory', 
        "Select Folder Containing Media Files"
    )
    if folder_path:
        self.batch_tree_view.add_files_or_folders([folder_path])

def handle_add_multiple_files(self):
    """Allow selection of multiple files to add to the batch."""
    files_paths = select_files_with_directory_update(
        self, 
        'files-open', 
        "Select Files", 
        VIDEO_SUBTITLE_FILTER
    )
    if files_paths:
        self.batch_tree_view.add_files_or_folders(files_paths)

def handle_add_pairs_continuously(self):
    """Continuously prompt for video/subtitle pairs until canceled."""
    while True:
        video_ref_path = select_files_with_directory_update(
            self, 
            'file-open', 
            "Select Video or Reference Subtitle File (or Cancel to Stop)", 
            VIDEO_SUBTITLE_FILTER
        )
        if not video_ref_path:
            break  # User cancelled video selection

        sub_path = select_files_with_directory_update(
            self, 
            'file-open', 
            f"Select Input Subtitle for '{os.path.basename(video_ref_path)}' (or Cancel to Stop)", 
            SUBTITLE_FILTER
        )
        if not sub_path:
            break  # User cancelled subtitle selection
        
        self.batch_tree_view.add_explicit_pair(video_ref_path, sub_path)

def handle_batch_drop(self, files):
    """Handle files dropped onto the batch input box."""
    if files:
        self.batch_tree_view.add_files_or_folders(files)

def update_batch_buttons_state(self):
    """Update the enabled state of batch buttons based on selection."""
    if hasattr(self, 'btn_batch_remove_selected') and hasattr(self, 'btn_batch_change_selected'):
        selected_items = self.batch_tree_view.selectedItems()
        has_selection = bool(selected_items)
        
        # Remove button only enabled when items are actually selected
        self.btn_batch_remove_selected.setEnabled(has_selection)
        # Change button only enabled when exactly one item is selected
        self.btn_batch_change_selected.setEnabled(len(selected_items) == 1)

def toggle_batch_mode(self):
    """Toggle between batch mode and normal mode."""
    self.batch_mode_enabled = not self.batch_mode_enabled
    update_config(self, "batch_mode", self.batch_mode_enabled)
    self.btn_batch_mode.setText(
        "Normal mode" if self.batch_mode_enabled else "Batch mode"
    )
    self.show_auto_sync_inputs()

def validate_batch_inputs(self):
    """Validate batch mode inputs."""
    if not self.batch_tree_view.has_items():
        # Try to show error on batch_input if it's visible, otherwise use QMessageBox
        if self.batch_input.isVisible():  # batch_input is the QLabel
            self.batch_input.show_error("Please add files or a folder to the batch.")
        else:  # Should not happen if tree is empty, batch_input should be visible
            QMessageBox.warning(self, "Batch Empty", "Please add files or folders to the batch.")
        return False  # Indicate validation failed
    
    valid_pairs = self.batch_tree_view.get_all_valid_pairs()
    if not valid_pairs:
        QMessageBox.warning(self, "No Valid Pairs", "No valid, existing file pairs found in the batch for processing. Ensure each video/reference has at least one subtitle child, and files exist.")
        return False
    
    return True  # Indicate validation passed
