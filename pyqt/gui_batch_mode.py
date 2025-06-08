# filepath: /run/media/laptop/A25E56C85E56953F/Projects/AutoSubSync/pyqt/gui_batch_mode.py
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
from PyQt5.QtCore import Qt, QTimer, QFileInfo, QPoint
from PyQt5.QtGui import QCursor

import os
from constants import VIDEO_EXTENSIONS, SUBTITLE_EXTENSIONS
from utils import update_config

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

class BatchTreeView(QTreeWidget):
    def __init__(self, parent_app=None):  # parent_app is the autosubsync instance
        super().__init__(parent_app)
        self.app_parent = parent_app
        self.setColumnCount(1)
        self.setHeaderHidden(True)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.icon_provider = QFileIconProvider()
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)  # Allow multi-selection for removal
        self.setStyleSheet("QTreeView::item { height: 26px; }")  # Increase item height

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

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): # External drag of files
            event.acceptProposedAction() # Accept, let dropEvent and add_files_or_folders handle placement
        else: # Internal drag of QTreeWidgetItems
            target_item = self.itemAt(event.pos())
            
            is_dragging_video = False
            # Ensure there are selected items to check
            dragged_items = self.selectedItems()
            if not dragged_items: # Should not happen if drag is properly initiated
                super().dragMoveEvent(event) # Default handling
                return

            for item_being_dragged in dragged_items:
                item_path = item_being_dragged.data(0, Qt.UserRole)
                if item_path and os.path.splitext(item_path)[1].lower() in VIDEO_EXTENSIONS:
                    is_dragging_video = True
                    break
            
            if is_dragging_video:
                current_drop_indicator_pos = self.dropIndicatorPosition()
                
                # Condition 1: Trying to drop ON an item (would make it a child of that item)
                if target_item and current_drop_indicator_pos == QAbstractItemView.OnItem:
                    event.ignore()
                    return
                
                # Condition 2: Trying to drop relative to a CHILD item in a way that makes the video a child.
                # If target_item is a child, any internal move operation (OnItem, AboveItem, BelowItem)
                # would effectively make the dragged video a child of target_item's parent.
                if target_item and target_item.parent(): # target_item is a child item
                    event.ignore() # Disallow making a video a child by dropping near/on other children
                    return
                
                # Otherwise (e.g., dropping on viewport, or above/below a TOP-LEVEL item), allow.
                super().dragMoveEvent(event)
            else:
                # Not dragging a video, so allow default behavior (e.g., subtitles can be children)
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
            
            target_item = self.itemAt(event.pos())
            # Prevent a video from being dropped as a child of another item
            if target_item and self.dropIndicatorPosition() == QAbstractItemView.OnItem:
                for item_being_dragged in dragged_items: # Use the captured list
                    item_path = item_being_dragged.data(0, Qt.UserRole)
                    if item_path and os.path.splitext(item_path)[1].lower() in VIDEO_EXTENSIONS:
                        event.ignore()
                        self._items_to_re_expand_paths.clear() # Clear if drop is aborted
                        return
            
            super().dropEvent(event) # Perform the move. Model signals will fire.
            
            if not event.isAccepted(): # If super().dropEvent() did not accept the drop
                self._items_to_re_expand_paths.clear()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        selected_items = self.selectedItems()
        item_at_pos = self.itemAt(event.pos())

        add_files_menu = menu.addMenu("Add files")
        action_add_pair = add_files_menu.addAction("Add pair")
        action_add_folder = add_files_menu.addAction("Add folder")
        action_add_files = add_files_menu.addAction("Add multiple files")
        action_add_continuously = add_files_menu.addAction("Add files (continuously)")

        action_add_pair.triggered.connect(lambda: self.app_parent.handle_add_pair(tree_view_target=True))
        action_add_folder.triggered.connect(lambda: self.app_parent.handle_add_folder(tree_view_target=True))
        action_add_files.triggered.connect(lambda: self.app_parent.handle_add_multiple_files(tree_view_target=True))
        action_add_continuously.triggered.connect(self.app_parent.handle_add_pairs_continuously)
        
        menu.addSeparator()

        if selected_items:  # Operations for selected items
            menu.addAction(f"Remove selected ({len(selected_items)})", self.remove_selected_items)
            if len(selected_items) == 1 and item_at_pos:  # Change only makes sense for a single item
                menu.addAction("Change", lambda: self.change_file_for_item(item_at_pos))
        elif item_at_pos:  # Fallback if no selection but right-clicked on an item
            menu.addAction("Remove", lambda: self.remove_item(item_at_pos))
            menu.addAction("Change", lambda: self.change_file_for_item(item_at_pos))

        if item_at_pos and not item_at_pos.parent():  # Right-clicked a top-level item
            menu.addAction("Add subtitle", lambda: self.add_subtitle_to_item_dialog(item_at_pos))
        
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

    def _get_file_icon(self, file_path):
        return self.icon_provider.icon(QFileInfo(file_path))

    def add_files_or_folders(self, paths, drop_target_item=None):
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
        # Group files by basename (without extension, and common suffixes removed)
        potential_groups = {}
        for fp in file_paths:
            base = os.path.splitext(os.path.basename(fp))[0]
            normalized_base = base.lower()
            common_suffixes = [
                '.en', '.eng', '.english', '.es', '.spa', '.spanish', '.fr', '.fre', '.french',
                '.forced', '.default', '.sdh', '.cc', '.hi',  # Hearing Impaired
                '.srt', '.ass', '.vtt', '.sub', '.idx', '.ssa', '.smi', '.txt'  # Common sub extensions
            ] 
            for suffix in sorted(common_suffixes, key=len, reverse=True):  # Process longer suffixes first
                if normalized_base.endswith(suffix):
                    normalized_base = normalized_base[:-len(suffix)]
            
            normalized_base = normalized_base.strip('.-_ [](){}')  # Further cleanup

            if normalized_base not in potential_groups:
                potential_groups[normalized_base] = []
            potential_groups[normalized_base].append(fp)

        items_added_to_tree = False # Flag to check if any item was actually added to the tree
        for base_key, files_in_group in potential_groups.items():
            videos = sorted([f for f in files_in_group if os.path.splitext(f)[1].lower() in VIDEO_EXTENSIONS])
            subs = sorted([f for f in files_in_group if os.path.splitext(f)[1].lower() in SUBTITLE_EXTENSIONS])

            actual_parent_qwidgetitem = self.invisibleRootItem()
            if drop_target_item:
                if os.path.splitext(files_in_group[0])[1].lower() in SUBTITLE_EXTENSIONS and \
                   not drop_target_item.parent() and \
                   os.path.splitext(drop_target_item.data(0, Qt.UserRole))[1].lower() in (VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS):
                    actual_parent_qwidgetitem = drop_target_item
                    for sub_file in subs:
                        child_item = QTreeWidgetItem(actual_parent_qwidgetitem, [os.path.basename(sub_file)])
                        child_item.setData(0, Qt.UserRole, sub_file)
                        child_item.setIcon(0, self._get_file_icon(sub_file))
                        child_item.setToolTip(0, sub_file)
                        items_added_to_tree = True
                    if items_added_to_tree: actual_parent_qwidgetitem.setExpanded(True)
                    continue

            if videos: 
                parent_file = videos[0]
                parent_item = QTreeWidgetItem(actual_parent_qwidgetitem, [os.path.basename(parent_file)])
                parent_item.setData(0, Qt.UserRole, parent_file)
                parent_item.setIcon(0, self._get_file_icon(parent_file))
                parent_item.setToolTip(0, parent_file)
                items_added_to_tree = True
                for sub_file in subs: 
                    child_item = QTreeWidgetItem(parent_item, [os.path.basename(sub_file)])
                    child_item.setData(0, Qt.UserRole, sub_file)
                    child_item.setIcon(0, self._get_file_icon(sub_file))
                    child_item.setToolTip(0, sub_file)
                if subs: parent_item.setExpanded(True)
            elif subs: 
                parent_file = subs[0]
                parent_item = QTreeWidgetItem(actual_parent_qwidgetitem, [os.path.basename(parent_file)])
                parent_item.setData(0, Qt.UserRole, parent_file)
                parent_item.setIcon(0, self._get_file_icon(parent_file))
                parent_item.setToolTip(0, parent_file)
                items_added_to_tree = True
                for sub_file in subs[1:]:
                    child_item = QTreeWidgetItem(parent_item, [os.path.basename(sub_file)])
                    child_item.setData(0, Qt.UserRole, sub_file)
                    child_item.setIcon(0, self._get_file_icon(sub_file))
                    child_item.setToolTip(0, sub_file)
                if len(subs) > 1: parent_item.setExpanded(True)
        
        if items_added_to_tree:
            self.expandAll() 

    def add_explicit_pair(self, video_ref_path, sub_path):
        parent_item = QTreeWidgetItem(self, [os.path.basename(video_ref_path)])
        parent_item.setData(0, Qt.UserRole, video_ref_path)
        parent_item.setIcon(0, self._get_file_icon(video_ref_path))
        parent_item.setToolTip(0, video_ref_path)

        child_item = QTreeWidgetItem(parent_item, [os.path.basename(sub_path)])
        child_item.setData(0, Qt.UserRole, sub_path)
        child_item.setIcon(0, self._get_file_icon(sub_path))
        child_item.setToolTip(0, sub_path)
        
        parent_item.setExpanded(True)

    def add_subtitle_to_item_dialog(self, parent_item):
        if not parent_item or parent_item.parent():  # Must be a top-level item
            QMessageBox.warning(self.app_parent, "Selection Error", "Please select a video or reference subtitle (a top-level item) to add a subtitle to.")
            return

        file_paths, _ = QFileDialog.getOpenFileNames(self.app_parent, "Select Subtitle File(s)", "", f"Subtitle Files (*{' *'.join(SUBTITLE_EXTENSIONS)})")
        if file_paths:
            any_subtitle_added = False
            for file_path in file_paths:
                ext = os.path.splitext(file_path)[1].lower()
                if ext not in SUBTITLE_EXTENSIONS:
                    QMessageBox.warning(self.app_parent, "Invalid File", f"'{os.path.basename(file_path)}' is not a subtitle file. Skipping.")
                    continue
                child_item = QTreeWidgetItem(parent_item, [os.path.basename(file_path)])
                child_item.setData(0, Qt.UserRole, file_path)
                child_item.setIcon(0, self._get_file_icon(file_path))
                child_item.setToolTip(0, file_path)
                any_subtitle_added = True
            if any_subtitle_added:
                parent_item.setExpanded(True)

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
            file_filter = f"Video/Subtitle Files (*{' *'.join(VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS)})"
            dialog_title = "Select Replacement Video or Reference Subtitle"
        else: 
            file_filter = f"Subtitle Files (*{' *'.join(SUBTITLE_EXTENSIONS)})"
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
            item.setToolTip(0, new_file_path)

    def clear_all_items(self):
        if self.topLevelItemCount() > 0:
            self.clear()

    def get_all_valid_pairs(self):
        pairs = []
        for i in range(self.topLevelItemCount()):
            parent_item = self.topLevelItem(i)
            parent_file = parent_item.data(0, Qt.UserRole)
            if not parent_file or not os.path.exists(parent_file): continue

            parent_ext = os.path.splitext(parent_file)[1].lower()
            if parent_ext not in (VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS): continue

            if parent_item.childCount() > 0:
                for j in range(parent_item.childCount()):
                    child_item = parent_item.child(j)
                    child_file = child_item.data(0, Qt.UserRole)
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

def handle_add_pair(self, tree_view_target=False):
    """Show dialogs to add a video/subtitle pair."""
    video_ref_path, _ = QFileDialog.getOpenFileName(self, "Select Video or Reference Subtitle File", self.config.get("last_used_dir", ""), f"Video/Subtitle Files (*{' *'.join(VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS)})")
    if not video_ref_path:
        return
    self.config["last_used_dir"] = os.path.dirname(video_ref_path)
    
    sub_path, _ = QFileDialog.getOpenFileName(self, "Select Input Subtitle File", self.config.get("last_used_dir", ""), f"Subtitle Files (*{' *'.join(SUBTITLE_EXTENSIONS)})")
    if not sub_path:
        return
    self.config["last_used_dir"] = os.path.dirname(sub_path)
    
    self.batch_tree_view.add_explicit_pair(video_ref_path, sub_path)

def handle_add_folder(self, tree_view_target=False):
    """Add all supported files from a folder to the batch."""
    folder_path = QFileDialog.getExistingDirectory(self, "Select Folder Containing Media Files", self.config.get("last_used_dir", ""))
    if folder_path:
        update_config(self, "last_used_dir", folder_path)
        self.batch_tree_view.add_files_or_folders([folder_path])

def handle_add_multiple_files(self, tree_view_target=False):
    """Allow selection of multiple files to add to the batch."""
    files_paths, _ = QFileDialog.getOpenFileNames(self, "Select Files", self.config.get("last_used_dir", ""), f"All Supported Files (*{' *'.join(VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS)});;Video Files (*{' *'.join(VIDEO_EXTENSIONS)});;Subtitle Files (*{' *'.join(SUBTITLE_EXTENSIONS)})")
    if files_paths:
        update_config(self, "last_used_dir", os.path.dirname(files_paths[0]))
        self.batch_tree_view.add_files_or_folders(files_paths)

def handle_add_pairs_continuously(self):
    """Continuously prompt for video/subtitle pairs until canceled."""
    while True:
        video_ref_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Video or Reference Subtitle File (or Cancel to Stop)", 
            self.config.get("last_used_dir", ""), 
            f"Video/Subtitle Files (*{' *'.join(VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS)})"
        )
        if not video_ref_path:
            break  # User cancelled video selection
        update_config(self, "last_used_dir", os.path.dirname(video_ref_path))

        sub_path, _ = QFileDialog.getOpenFileName(
            self, 
            f"Select Input Subtitle for '{os.path.basename(video_ref_path)}' (or Cancel to Stop)", 
            self.config.get("last_used_dir", ""), 
            f"Subtitle Files (*{' *'.join(SUBTITLE_EXTENSIONS)})"
        )
        if not sub_path:
            break  # User cancelled subtitle selection
        update_config(self, "last_used_dir", os.path.dirname(sub_path))
        
        self.batch_tree_view.add_explicit_pair(video_ref_path, sub_path)

def handle_batch_drop(self, files):
    """Handle files dropped onto the batch input box."""
    if files:
        self.batch_tree_view.add_files_or_folders(files)

def update_batch_buttons_state(self):
    """Update the enabled state of batch buttons based on selection."""
    if hasattr(self, 'btn_batch_remove_selected') and hasattr(self, 'btn_batch_change_selected'):
        has_selection = bool(self.batch_tree_view.selectedItems())
        current_item_exists = bool(self.batch_tree_view.currentItem())
        
        self.btn_batch_remove_selected.setEnabled(has_selection or current_item_exists)
        # Change button only enabled if exactly one item is selected or is current
        self.btn_batch_change_selected.setEnabled(len(self.batch_tree_view.selectedItems()) == 1 or (not has_selection and current_item_exists))

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
