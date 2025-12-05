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
from PyQt6.QtCore import Qt, QTimer, QFileInfo, QPoint, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QCursor, QColor, QShortcut, QKeySequence

import os
import re
import logging
import texts
from constants import VIDEO_EXTENSIONS, SUBTITLE_EXTENSIONS, COLORS, DEFAULT_OPTIONS
from utils import update_config, open_filedialog, open_folder, load_config

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
    # Sync tracking functions
    autosubsyncapp_class.show_sync_tracking_menu = show_sync_tracking_menu
    autosubsyncapp_class.smart_load_library = smart_load_library
    autosubsyncapp_class.open_library_manager = open_library_manager


class ProcessedItemsScanner(QObject):
    """
    Worker object for scanning files to check if they are already processed.
    Runs in a background thread to keep the UI responsive.
    """

    # Signals
    scan_started = pyqtSignal()
    scan_progress = pyqtSignal(int, int)  # current, total
    item_scanned = pyqtSignal(str, bool)  # filepath, is_processed
    scan_finished = pyqtSignal(dict)  # results: {filepath: is_processed}

    def __init__(self):
        super().__init__()
        self._files_to_scan = []
        self._is_running = False
        self._should_stop = False

    def set_files(self, files):
        """Set the files to scan."""
        self._files_to_scan = files.copy()

    def stop(self):
        """Request the scanner to stop."""
        self._should_stop = True

    def run(self):
        """Perform the scanning operation."""
        from processed_items_manager import get_processed_items_manager

        self._is_running = True
        self._should_stop = False
        self.scan_started.emit()

        results = {}
        manager = get_processed_items_manager()
        total = len(self._files_to_scan)

        for i, filepath in enumerate(self._files_to_scan):
            if self._should_stop:
                break

            is_processed = manager.is_processed(filepath)
            results[filepath] = is_processed
            self.item_scanned.emit(filepath, is_processed)
            self.scan_progress.emit(i + 1, total)

        self._is_running = False
        self.scan_finished.emit(results)


class DatabaseOperationWorker(QObject):
    """
    Worker object for adding/removing items from the processed database.
    Runs in a background thread to keep the UI responsive.
    """

    # Signals
    operation_started = pyqtSignal()
    operation_progress = pyqtSignal(int, int)  # current, total
    item_processed = pyqtSignal(str, bool)  # filepath, success
    operation_finished = pyqtSignal(
        int, str
    )  # count, operation_type ('add' or 'remove')

    def __init__(self):
        super().__init__()
        self._file_paths = []
        self._operation = "add"  # 'add' or 'remove'
        self._is_running = False
        self._should_stop = False

    def set_files(self, file_paths, operation="add"):
        """Set the files to process and the operation type."""
        self._file_paths = file_paths.copy()
        self._operation = operation

    def stop(self):
        """Request the worker to stop."""
        self._should_stop = True

    def run(self):
        """Perform the database operation."""
        from processed_items_manager import get_processed_items_manager

        self._is_running = True
        self._should_stop = False
        self.operation_started.emit()

        manager = get_processed_items_manager()
        total = len(self._file_paths)
        success_count = 0

        for i, filepath in enumerate(self._file_paths):
            if self._should_stop:
                break

            if self._operation == "add":
                success = manager.mark_as_processed(filepath, silent=True)
            else:  # remove
                success = manager.remove_from_processed(filepath, silent=True)

            if success:
                success_count += 1

            self.item_processed.emit(filepath, success)
            self.operation_progress.emit(i + 1, total)

        self._is_running = False
        self.operation_finished.emit(success_count, self._operation)


class BatchTreeView(QTreeWidget):
    VALID_STATE_ROLE = (
        Qt.ItemDataRole.UserRole + 10
    )  # Role to store parent item's validity state
    ITEM_ID_ROLE = Qt.ItemDataRole.UserRole + 11  # Role to store the item's unique ID
    PROCESSED_STATE_ROLE = (
        Qt.ItemDataRole.UserRole + 12
    )  # Role to store if item is already processed
    FORCE_PROCESS_ROLE = (
        Qt.ItemDataRole.UserRole + 13
    )  # Role to store if item should be force processed

    def _is_parent_item_valid(self, item):
        """Helper to determine if a parent item is valid.

        A parent is valid if:
        - It has at least one child
        - All children are subtitle files (not video files)
        - No children have nested children
        """
        # Quick early returns for invalid cases
        if not item or item.parent() or item.childCount() < 1:
            return False

        # Check all children - all must be valid subtitles with no nested children
        for i in range(item.childCount()):
            child = item.child(i)
            if not child or child.childCount() > 0:
                return False
            child_file_path = child.data(0, Qt.ItemDataRole.UserRole)
            if (
                not child_file_path
                or get_file_extension(child_file_path) in VIDEO_EXTENSIONS
            ):
                return False
        return True

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

        # Smart Deduplication - async scanning setup
        self._processed_items_cache = {}  # Cache: filepath -> is_processed
        self._scanner_thread = None
        self._scanner = None
        self._is_scanning = False
        self._pending_scan_files = []  # Files waiting to be scanned
        self._scan_debounce_timer = QTimer(self)
        self._scan_debounce_timer.setSingleShot(True)
        self._scan_debounce_timer.setInterval(100)  # Debounce scan requests
        self._scan_debounce_timer.timeout.connect(self._start_pending_scan)

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

        # Undo/Redo stacks
        self._undo_stack = []  # Stack of saved states for undo
        self._redo_stack = []  # Stack of saved states for redo
        self._max_undo_levels = 100  # Maximum number of undo levels
        self._is_restoring_state = False  # Flag to prevent saving state during restore

        # Track if library has been loaded (for Load/Reload library text)
        self._library_loaded = False

        # Set up keyboard shortcuts for undo/redo (work even without focus)
        self._setup_shortcuts()

        # Set up loading overlay label (centered in the tree view)
        self._setup_loading_overlay()

    def _setup_shortcuts(self):
        """Set up keyboard shortcuts for undo/redo operations."""
        # Use WindowShortcut context so shortcuts work when the main window is active
        # and the batch tree view is visible, regardless of which specific widget has focus

        # Ctrl+Z for Undo
        self._undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        self._undo_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self._undo_shortcut.activated.connect(self._handle_undo_shortcut)

        # Ctrl+Y for Redo (explicit)
        self._redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self)
        self._redo_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self._redo_shortcut.activated.connect(self._handle_redo_shortcut)

        # Ctrl+Shift+Z for Redo (alternative)
        self._redo_shortcut_alt = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        self._redo_shortcut_alt.setContext(Qt.ShortcutContext.WindowShortcut)
        self._redo_shortcut_alt.activated.connect(self._handle_redo_shortcut)

    def _handle_undo_shortcut(self):
        """Handle undo shortcut - only if batch tree is visible."""
        if self.isVisible():
            self.undo()

    def _handle_redo_shortcut(self):
        """Handle redo shortcut - only if batch tree is visible."""
        if self.isVisible():
            self.redo()

    def _setup_loading_overlay(self):
        """Set up a centered loading overlay label."""
        self._loading_overlay = QLabel(self.viewport())
        self._loading_overlay.setText(texts.LOADING_PLEASE_WAIT)
        self._loading_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_overlay.setStyleSheet(
            f"""
            QLabel {{
                background-color: rgba(0, 0, 0, 0.7);
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 20px 40px;
                border-radius: 8px;
            }}
        """
        )
        self._loading_overlay.setVisible(False)
        self._loading_overlay.adjustSize()
        self._is_loading = False  # Track loading state for disabling interaction

    def _show_loading_overlay(self, show):
        """Show or hide the loading overlay (centered in the tree view)."""
        self._is_loading = show
        if show:
            # Disable interaction while loading
            self.setEnabled(False)
            # Re-center the overlay
            self._loading_overlay.adjustSize()
            viewport = self.viewport()
            x = (viewport.width() - self._loading_overlay.width()) // 2
            y = (viewport.height() - self._loading_overlay.height()) // 2
            self._loading_overlay.move(x, y)
            self._loading_overlay.raise_()
        else:
            # Re-enable interaction when done loading
            self.setEnabled(True)
        self._loading_overlay.setVisible(show)

    def resizeEvent(self, event):
        """Handle resize to keep loading overlay centered."""
        super().resizeEvent(event)
        if hasattr(self, "_loading_overlay") and self._loading_overlay.isVisible():
            viewport = self.viewport()
            x = (viewport.width() - self._loading_overlay.width()) // 2
            y = (viewport.height() - self._loading_overlay.height()) // 2
            self._loading_overlay.move(x, y)

    def _get_next_id(self):
        """Get the next available unique ID for a tree item."""
        current_id = self._next_item_id
        self._next_item_id += 1
        return current_id

    # --- Smart Deduplication Methods ---

    def _is_skip_processed_enabled(self):
        """Check if skip previously processed items is enabled in settings."""
        if self.app_parent and hasattr(self.app_parent, "config"):
            return self.app_parent.config.get(
                "skip_previously_processed_videos",
                DEFAULT_OPTIONS.get("skip_previously_processed_videos", True),
            )
        config = load_config()
        return config.get(
            "skip_previously_processed_videos",
            DEFAULT_OPTIONS.get("skip_previously_processed_videos", True),
        )

    def _queue_files_for_scan(self, filepaths):
        """Queue files for processed status scanning."""
        if not self._is_skip_processed_enabled():
            return

        # Only scan video files (references)
        video_files = [f for f in filepaths if is_video_file(f)]
        if not video_files:
            return

        # Add to pending scan list (avoid duplicates, but always re-check if not in cache)
        for f in video_files:
            norm_f = os.path.normpath(f)
            if norm_f not in self._pending_scan_files:
                self._pending_scan_files.append(norm_f)

        # Debounce the scan start
        self._scan_debounce_timer.start()

    def _start_pending_scan(self):
        """Start scanning pending files in background thread."""
        if not self._pending_scan_files:
            return

        if self._is_scanning:
            # Already scanning, will be retriggered when current scan finishes
            return

        files_to_scan = self._pending_scan_files.copy()
        self._pending_scan_files.clear()

        # Show scanning status
        self._show_scanning_status(True)

        # Create scanner and thread
        self._scanner_thread = QThread()
        self._scanner = ProcessedItemsScanner()
        self._scanner.set_files(files_to_scan)
        self._scanner.moveToThread(self._scanner_thread)

        # Connect signals
        self._scanner_thread.started.connect(self._scanner.run)
        self._scanner.item_scanned.connect(self._on_item_scanned)
        self._scanner.scan_finished.connect(self._on_scan_finished)
        self._scanner.scan_finished.connect(self._scanner_thread.quit)
        self._scanner_thread.finished.connect(self._cleanup_scanner)

        self._is_scanning = True
        self._scanner_thread.start()

    def _on_item_scanned(self, filepath, is_processed):
        """Handle individual item scan result."""
        self._processed_items_cache[filepath] = is_processed
        if is_processed:
            self._mark_item_as_processed(filepath)

    def _on_scan_finished(self, results):
        """Handle scan completion."""
        self._is_scanning = False
        self._show_scanning_status(False)

        # Update cache with all results
        self._processed_items_cache.update(results)

        # Update all items with processed status
        self._update_processed_visual_state()

        # Update header to reflect skipped items
        self._update_header_pair_counts()

        # Check if there are more files to scan
        if self._pending_scan_files:
            self._scan_debounce_timer.start()

    def _cleanup_scanner(self):
        """Clean up scanner resources."""
        if self._scanner:
            self._scanner.deleteLater()
            self._scanner = None
        if self._scanner_thread:
            self._scanner_thread.deleteLater()
            self._scanner_thread = None

    def _show_scanning_status(self, show):
        """Show or hide the scanning status indicator (centered overlay)."""
        self._show_loading_overlay(show)

    def _mark_item_as_processed(self, filepath):
        """Mark a specific item as processed based on filepath."""
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item:
                item_path = item.data(0, Qt.ItemDataRole.UserRole)
                if item_path and os.path.normpath(item_path) == os.path.normpath(
                    filepath
                ):
                    # Check if not force processed
                    if not item.data(0, self.FORCE_PROCESS_ROLE):
                        item.setData(0, self.PROCESSED_STATE_ROLE, True)
                        self._apply_processed_style(item, True)

    def _update_processed_visual_state(self):
        """Update visual state for all items based on processed status."""
        if not self._is_skip_processed_enabled():
            # Clear all processed states if feature is disabled
            for i in range(self.topLevelItemCount()):
                item = self.topLevelItem(i)
                if item:
                    item.setData(0, self.PROCESSED_STATE_ROLE, False)
                    item.setToolTip(0, "")  # Clear processed tooltip
            # Trigger full UI update to restore normal styling
            self._schedule_ui_update()
            return

        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item:
                item_path = item.data(0, Qt.ItemDataRole.UserRole)
                if item_path:
                    # Check cache first
                    is_processed = self._processed_items_cache.get(
                        os.path.normpath(item_path), False
                    )
                    # Only mark as processed if not force processed
                    if item.data(0, self.FORCE_PROCESS_ROLE):
                        is_processed = False

                    item.setData(0, self.PROCESSED_STATE_ROLE, is_processed)
                    self._apply_processed_style(item, is_processed)

        # Trigger UI update to apply correct styling
        self._schedule_ui_update()

    def _apply_processed_style(self, item, is_processed):
        """Apply visual styling to indicate an item is already processed."""
        if is_processed and self._is_skip_processed_enabled():
            processed_color = self._parse_rgba_to_qcolor(COLORS["PROCESSED_BACKGROUND"])
            item.setBackground(0, processed_color)
            # Set tooltip
            item.setToolTip(0, str(texts.ITEM_ALREADY_PROCESSED))
        else:
            # Clear processed state - let _apply_item_styles handle the normal styling
            item.setToolTip(0, "")  # Clear tooltip so validation can set it

    def rescan_processed_items(self):
        """Re-scan all items for processed status. Called when settings change."""
        # Clear cache
        self._processed_items_cache.clear()

        if not self._is_skip_processed_enabled():
            # Clear all processed states
            self._update_processed_visual_state()
            return

        # Collect all reference files
        files_to_scan = []
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item:
                item_path = item.data(0, Qt.ItemDataRole.UserRole)
                if item_path and is_video_file(item_path):
                    files_to_scan.append(item_path)

        if files_to_scan:
            self._pending_scan_files.extend(files_to_scan)
            self._scan_debounce_timer.start()

    def refresh_processed_status(self):
        """Refresh the processed status of all items and scan library folders for new items.

        This clears the cache and rescans all video files to check their
        current status in the processed items database.
        """
        if not self.topLevelItemCount():
            return

        # Clear existing cache to force fresh database lookups
        self._processed_items_cache.clear()

        # Clear any pending scans
        self._pending_scan_files.clear()

        # Also clear any force process / manual skip states
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item:
                item.setData(0, self.FORCE_PROCESS_ROLE, False)
                item.setData(0, self.PROCESSED_STATE_ROLE, False)

        # Collect all video files to scan
        files_to_scan = []
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item:
                item_path = item.data(0, Qt.ItemDataRole.UserRole)
                if item_path and is_video_file(item_path):
                    norm_path = os.path.normpath(item_path)
                    if norm_path not in files_to_scan:
                        files_to_scan.append(norm_path)

        if files_to_scan:
            self._pending_scan_files.extend(files_to_scan)
            # Start scan immediately (no debounce for manual refresh)
            self._start_pending_scan()

    def scan_library_for_new_items(self, folders):
        """Scan library folders for new files and add them at the beginning of the list.
        Also removes items whose files no longer exist on disk.

        Args:
            folders: List of folder paths to scan
        """
        # First, remove items that no longer exist on disk
        items_to_remove = []
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item:
                item_path = item.data(0, Qt.ItemDataRole.UserRole)
                if item_path and not os.path.exists(item_path):
                    items_to_remove.append(item)
                # Also check children (subtitles) - if subtitle is missing, just clear it
                for j in range(item.childCount()):
                    child = item.child(j)
                    if child:
                        child_path = child.data(0, Qt.ItemDataRole.UserRole)
                        if child_path and not os.path.exists(child_path):
                            # Mark for removal from parent
                            item.removeChild(child)

        if items_to_remove:
            self._save_state_for_undo()
            for item in items_to_remove:
                index = self.indexOfTopLevelItem(item)
                if index >= 0:
                    self.takeTopLevelItem(index)
            logger.info(
                f"Removed {len(items_to_remove)} items - files no longer exist on disk"
            )
            self._update_header_pair_counts()

        if not folders:
            return

        # Get valid folders that exist
        valid_folders = [f for f in folders if os.path.isdir(f)]
        if not valid_folders:
            return

        # Collect all existing file paths in the batch list (both references and subtitles)
        existing_files = set()
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item:
                item_path = item.data(0, Qt.ItemDataRole.UserRole)
                if item_path:
                    existing_files.add(os.path.normpath(item_path))
                # Also check children (subtitles)
                for j in range(item.childCount()):
                    child = item.child(j)
                    if child:
                        child_path = child.data(0, Qt.ItemDataRole.UserRole)
                        if child_path:
                            existing_files.add(os.path.normpath(child_path))

        # Collect new files from library folders
        new_files = []
        for folder in valid_folders:
            for root, _, filenames in os.walk(folder):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    norm_path = os.path.normpath(file_path)
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in VIDEO_EXTENSIONS or ext in SUBTITLE_EXTENSIONS:
                        if norm_path not in existing_files:
                            new_files.append(file_path)

        if not new_files:
            return

        # Save state for undo before making changes
        self._save_state_for_undo()

        # Process and pair the new files, then insert at the beginning
        logger.info(f"Found {len(new_files)} new files in library folders")

        # Separate into videos and subtitles
        new_videos = [f for f in new_files if get_file_extension(f) in VIDEO_EXTENSIONS]
        new_subs = [
            f for f in new_files if get_file_extension(f) in SUBTITLE_EXTENSIONS
        ]

        # Pair them using the existing pairing logic
        paired_references = set()
        paired_subs = set()
        pairs_to_add = []

        # Try to pair videos with subtitles
        for video in new_videos:
            video_base = effective_basename(video).lower().strip(".-_ [](){}")
            best_match = None
            for sub in new_subs:
                if sub in paired_subs:
                    continue
                sub_base = effective_basename(sub).lower().strip(".-_ [](){}")
                if video_base == sub_base:
                    best_match = sub
                    break

            if best_match:
                pairs_to_add.append((video, best_match))
                paired_references.add(video)
                paired_subs.add(best_match)
            else:
                # Add video without subtitle
                pairs_to_add.append((video, None))
                paired_references.add(video)

        # Add remaining unpaired subtitles as standalone items
        for sub in new_subs:
            if sub not in paired_subs:
                pairs_to_add.append((None, sub))

        # Create all items first, then sort them
        newly_created_items = []
        for video, sub in pairs_to_add:
            if video and sub:
                # Create paired item
                if not self.is_duplicate_pair(video, sub):
                    item = self._create_tree_item(video)
                    sub_item = self._create_tree_item(sub)
                    item.addChild(sub_item)
                    item.setExpanded(True)
                    # Track the pair
                    norm_v, norm_s = os.path.normpath(video), os.path.normpath(sub)
                    self._current_pair_id_set.add((norm_v, norm_s))
                    newly_created_items.append(item)
            elif video:
                # Add video without subtitle
                item = self._create_tree_item(video)
                newly_created_items.append(item)
            elif sub:
                # Add subtitle without video (rare case)
                item = self._create_tree_item(sub)
                newly_created_items.append(item)

        if newly_created_items:
            # Check processed status directly from database for sorting
            from processed_items_manager import get_processed_items_manager

            manager = get_processed_items_manager()

            # Sort items: invalid not-skipped (0), valid not-skipped (1), invalid skipped (2), valid skipped (3)
            def get_sort_key(item):
                is_valid = self._get_provisional_validity(item) == "valid"
                # Check if item is processed (will be skipped) - check for all video files
                item_path = item.data(0, Qt.ItemDataRole.UserRole)
                is_processed = False
                if item_path and is_video_file(item_path):
                    # Check database directly for accurate status
                    is_processed = manager.is_processed(item_path)
                    # Also update cache
                    norm_path = os.path.normpath(item_path)
                    self._processed_items_cache[norm_path] = is_processed

                # Sorting priority:
                # 0: Invalid not-skipped (need attention first)
                # 1: Valid not-skipped (ready to process)
                # 2: Invalid skipped
                # 3: Valid skipped (last)
                if not is_valid and not is_processed:
                    return (0, os.path.basename(item_path or "").lower())
                elif is_valid and not is_processed:
                    return (1, os.path.basename(item_path or "").lower())
                elif not is_valid and is_processed:
                    return (2, os.path.basename(item_path or "").lower())
                else:  # is_valid and is_processed
                    return (3, os.path.basename(item_path or "").lower())

            newly_created_items.sort(key=get_sort_key)

            # Insert items at the beginning of the list (in reverse order to maintain sort)
            # Also apply processed state immediately based on cache
            for item in reversed(newly_created_items):
                self.insertTopLevelItem(0, item)
                # Apply processed visual state if applicable
                item_path = item.data(0, Qt.ItemDataRole.UserRole)
                if item_path:
                    norm_path = os.path.normpath(item_path)
                    is_processed = self._processed_items_cache.get(norm_path, False)
                    if is_processed:
                        item.setData(0, self.PROCESSED_STATE_ROLE, True)
                        self._apply_processed_style(item, True)

            # Mark library as loaded
            self._library_loaded = True

            logger.info(
                f"Added {len(newly_created_items)} new items from library folders"
            )
            self._update_header_pair_counts()

    def force_process_items(self, items):
        """Mark items to be force processed, ignoring their processed status."""
        self._save_state_for_undo()  # Save state before modifying
        for item in items:
            if item and not item.parent():  # Only top-level items
                item.setData(0, self.FORCE_PROCESS_ROLE, True)
                item.setData(0, self.PROCESSED_STATE_ROLE, False)
                # Clear the processed tooltip
                item.setToolTip(0, "")

        # Trigger UI update to restore proper styling
        self._schedule_ui_update()

    def skip_process_items(self, items):
        """Mark items to be skipped (not processed), applying processed status."""
        self._save_state_for_undo()  # Save state before modifying
        for item in items:
            if item and not item.parent():  # Only top-level items
                item.setData(0, self.FORCE_PROCESS_ROLE, False)
                item.setData(0, self.PROCESSED_STATE_ROLE, True)
                self._apply_processed_style(item, True)

        # Update header to reflect skipped items
        self._update_header_pair_counts()
        # Trigger UI update
        self._schedule_ui_update()

    def add_items_to_processed_database(self, items):
        """Add selected video items to the processed items database asynchronously."""
        # Collect file paths
        file_paths = []
        self._pending_db_items = {}  # Map filepath -> item for updating after operation

        for item in items:
            if item and not item.parent():  # Only top-level items
                item_path = item.data(0, Qt.ItemDataRole.UserRole)
                if item_path and is_video_file(item_path):
                    norm_path = os.path.normpath(item_path)
                    file_paths.append(item_path)
                    self._pending_db_items[norm_path] = item

        if not file_paths:
            return

        # Show confirmation dialog if more than 3 items
        if len(file_paths) > 3:
            reply = QMessageBox.question(
                self,
                texts.CONFIRMATION,
                texts.CONFIRM_ADD_TO_DATABASE.format(count=len(file_paths)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                self._pending_db_items.clear()
                return

        # Show loading indicator
        self._show_scanning_status(True)

        # Create worker and thread
        self._db_worker_thread = QThread()
        self._db_worker = DatabaseOperationWorker()
        self._db_worker.set_files(file_paths, "add")
        self._db_worker.moveToThread(self._db_worker_thread)

        # Connect signals
        self._db_worker_thread.started.connect(self._db_worker.run)
        self._db_worker.item_processed.connect(self._on_db_item_added)
        self._db_worker.operation_finished.connect(self._on_db_add_finished)
        self._db_worker.operation_finished.connect(self._db_worker_thread.quit)
        self._db_worker_thread.finished.connect(self._cleanup_db_worker)

        self._db_worker_thread.start()

    def _on_db_item_added(self, filepath, success):
        """Handle individual item added to database."""
        if success:
            norm_path = os.path.normpath(filepath)
            self._processed_items_cache[norm_path] = True

            # Update item visual state if we have reference to it
            if (
                hasattr(self, "_pending_db_items")
                and norm_path in self._pending_db_items
            ):
                item = self._pending_db_items[norm_path]
                if item:
                    item.setData(0, self.PROCESSED_STATE_ROLE, True)
                    item.setData(0, self.FORCE_PROCESS_ROLE, False)
                    self._apply_processed_style(item, True)

    def _on_db_add_finished(self, count, operation):
        """Handle add operation completion."""
        self._show_scanning_status(False)

        if count > 0:
            logger.info(
                f"[Sync Tracking] Added {count} video(s) to processed items database."
            )
            # Update header to reflect changes
            self._update_header_pair_counts()
            # Trigger UI update
            self._schedule_ui_update()

        # Clear pending items
        if hasattr(self, "_pending_db_items"):
            self._pending_db_items.clear()

    def remove_items_from_processed_database(self, items):
        """Remove selected video items from the processed items database asynchronously."""
        # Collect file paths
        file_paths = []
        self._pending_db_remove_items = (
            {}
        )  # Map filepath -> item for updating after operation

        for item in items:
            if item and not item.parent():  # Only top-level items
                item_path = item.data(0, Qt.ItemDataRole.UserRole)
                if item_path and is_video_file(item_path):
                    norm_path = os.path.normpath(item_path)
                    file_paths.append(item_path)
                    self._pending_db_remove_items[norm_path] = item

        if not file_paths:
            return

        # Show confirmation dialog if more than 3 items
        if len(file_paths) > 3:
            reply = QMessageBox.question(
                self,
                texts.CONFIRMATION,
                texts.CONFIRM_REMOVE_FROM_DATABASE.format(count=len(file_paths)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                self._pending_db_remove_items.clear()
                return

        # Show loading indicator
        self._show_scanning_status(True)

        # Create worker and thread
        self._db_remove_worker_thread = QThread()
        self._db_remove_worker = DatabaseOperationWorker()
        self._db_remove_worker.set_files(file_paths, "remove")
        self._db_remove_worker.moveToThread(self._db_remove_worker_thread)

        # Connect signals
        self._db_remove_worker_thread.started.connect(self._db_remove_worker.run)
        self._db_remove_worker.item_processed.connect(self._on_db_item_removed)
        self._db_remove_worker.operation_finished.connect(self._on_db_remove_finished)
        self._db_remove_worker.operation_finished.connect(
            self._db_remove_worker_thread.quit
        )
        self._db_remove_worker_thread.finished.connect(self._cleanup_db_remove_worker)

        self._db_remove_worker_thread.start()

    def _on_db_item_removed(self, filepath, success):
        """Handle individual item removed from database."""
        if success:
            norm_path = os.path.normpath(filepath)
            self._processed_items_cache[norm_path] = False

            # Update item visual state if we have reference to it
            if (
                hasattr(self, "_pending_db_remove_items")
                and norm_path in self._pending_db_remove_items
            ):
                item = self._pending_db_remove_items[norm_path]
                if item:
                    item.setData(0, self.PROCESSED_STATE_ROLE, False)
                    item.setToolTip(0, "")

    def _on_db_remove_finished(self, count, operation):
        """Handle remove operation completion."""
        self._show_scanning_status(False)

        if count > 0:
            logger.info(
                f"[Sync Tracking] Removed {count} video(s) from processed items database."
            )
            # Update header to reflect changes
            self._update_header_pair_counts()
            # Trigger UI update to restore normal styling
            self._schedule_ui_update()

        # Clear pending items
        if hasattr(self, "_pending_db_remove_items"):
            self._pending_db_remove_items.clear()

    def _cleanup_db_worker(self):
        """Clean up add database worker resources."""
        if hasattr(self, "_db_worker") and self._db_worker:
            self._db_worker.deleteLater()
            self._db_worker = None
        if hasattr(self, "_db_worker_thread") and self._db_worker_thread:
            self._db_worker_thread.deleteLater()
            self._db_worker_thread = None

    def _cleanup_db_remove_worker(self):
        """Clean up remove database worker resources."""
        if hasattr(self, "_db_remove_worker") and self._db_remove_worker:
            self._db_remove_worker.deleteLater()
            self._db_remove_worker = None
        if hasattr(self, "_db_remove_worker_thread") and self._db_remove_worker_thread:
            self._db_remove_worker_thread.deleteLater()
            self._db_remove_worker_thread = None

    def is_item_processed(self, item):
        """Check if an item is marked as processed and should be skipped."""
        if not self._is_skip_processed_enabled():
            return False

        # If force process is set, never skip
        if item.data(0, self.FORCE_PROCESS_ROLE):
            return False

        return item.data(0, self.PROCESSED_STATE_ROLE) or False

    def get_processable_items(self):
        """Get list of valid pairs that should be processed (excluding skipped items)."""
        processable = []
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item and self._is_parent_item_valid(item):
                if not self.is_item_processed(item):
                    processable.append(item)
        return processable

    # --- End Smart Deduplication Methods ---

    def _schedule_ui_update(self, *args):  # Accept any arguments from signals
        self._update_ui_timer.start()

    def _perform_actual_ui_update(self):
        # Check if this is an internal drag/drop operation
        is_internal_move = hasattr(self, "_in_internal_drag") and self._in_internal_drag

        # Phase 1: Rebuild pair ID set and item-to-pair_id map for efficient validation
        # Now supports one-to-many: a single parent can have multiple subtitle children
        self._current_pair_id_set.clear()
        self._item_to_pair_id_map.clear()
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if (
                item and item.childCount() >= 1
            ):  # Potential pair structure (one or more children)
                parent_path = item.data(0, Qt.ItemDataRole.UserRole)
                if not parent_path:
                    continue

                norm_parent = os.path.normpath(parent_path)
                item_pairs = []  # Store all valid pairs for this parent item

                # Process all children of this parent
                for j in range(item.childCount()):
                    child_item = item.child(j)
                    child_path = (
                        child_item.data(0, Qt.ItemDataRole.UserRole)
                        if child_item
                        else None
                    )

                    if (
                        child_path
                        and not child_item.childCount()
                        and is_subtitle_file(child_path)
                    ):
                        norm_child = os.path.normpath(child_path)
                        if (
                            norm_parent != norm_child
                        ):  # Ensure parent and child are not the same file
                            pair_id = (norm_parent, norm_child)
                            self._current_pair_id_set.add(pair_id)
                            item_pairs.append(pair_id)

                # Store all pairs for this item (for duplicate detection)
                if item_pairs:
                    self._item_to_pair_id_map[id(item)] = item_pairs

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
        """Updates the header with counts of valid, invalid, and skipped pairs.

        For one-to-many relationships, each child subtitle under a valid parent
        counts as one valid pair. Invalid parents count as one invalid entry.
        Processed/skipped items are counted separately.
        """
        valid_pairs = 0
        invalid_parents = 0
        skipped_pairs = 0

        skip_enabled = self._is_skip_processed_enabled()

        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            is_valid = item.data(0, self.VALID_STATE_ROLE) == "valid"

            # Check processed status from both item data and cache
            is_processed_data = item.data(0, self.PROCESSED_STATE_ROLE)
            is_force_process = item.data(0, self.FORCE_PROCESS_ROLE)

            # Also check cache for processed status
            item_path = item.data(0, Qt.ItemDataRole.UserRole)
            is_processed_cache = False
            if item_path:
                norm_path = os.path.normpath(item_path)
                is_processed_cache = self._processed_items_cache.get(norm_path, False)

            is_processed = (
                is_processed_data or is_processed_cache
            ) and not is_force_process

            if is_valid:
                child_count = item.childCount()
                if skip_enabled and is_processed:
                    # Count as skipped
                    skipped_pairs += child_count
                else:
                    # Count as valid
                    valid_pairs += child_count
            else:
                invalid_parents += 1

        header_text = texts.PAIRS_HEADER_LABEL.format(
            valid=valid_pairs, invalid=invalid_parents, skipped=skipped_pairs
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

        # Check if item is skipped (processed) - this takes priority over invalid status
        is_processed_data = item.data(0, self.PROCESSED_STATE_ROLE)
        is_force_process = item.data(0, self.FORCE_PROCESS_ROLE)

        # Also check cache
        item_path = item.data(0, Qt.ItemDataRole.UserRole)
        is_processed_cache = False
        if item_path:
            norm_path = os.path.normpath(item_path)
            is_processed_cache = self._processed_items_cache.get(norm_path, False)

        is_processed = (
            is_processed_data or is_processed_cache
        ) and not is_force_process

        # If item is processed and skip is enabled, always show "Skipped" status
        # regardless of validity (since it will be skipped anyway)
        if is_processed and self._is_skip_processed_enabled():
            item.setToolTip(
                0, texts.BATCH_PAIR_STATUS_SKIPPED_LABEL.format(id_text=id_text)
            )
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

        Supports one-to-many relationships: a parent can have multiple subtitle children.
        Each child must be a subtitle file (not video), and must not be nested.
        Also checks for duplicate children within the same parent and marks them.
        Uses precomputed _current_pair_id_set for duplicate checks.
        """

        # Check if item has at least one child
        if item.childCount() == 0:
            return False, texts.BATCH_VALIDATE_ADD_SUBTITLE

        parent_path = item.data(0, Qt.ItemDataRole.UserRole)
        if not parent_path:
            return False, texts.BATCH_VALIDATE_MISSING_FILE_PATH

        norm_parent = os.path.normpath(parent_path)

        # Track child paths to detect duplicates within this parent
        # Maps normalized path -> list of child items with that path
        child_path_items = {}
        has_duplicates = False

        # First pass: collect all children and check basic validity
        for i in range(item.childCount()):
            child_item = item.child(i)

            # Check if the child has no nested children
            if child_item.childCount() > 0:
                return False, texts.BATCH_VALIDATE_NESTED_NOT_ALLOWED

            child_path = child_item.data(0, Qt.ItemDataRole.UserRole)

            if not child_path:
                return False, texts.BATCH_VALIDATE_MISSING_FILE_PATH

            # Check if the child is a video file (not allowed)
            if is_video_file(child_path):
                return False, texts.BATCH_VALIDATE_VIDEO_NOT_ALLOWED

            norm_child = os.path.normpath(child_path)

            if norm_parent == norm_child:
                return False, texts.BATCH_VALIDATE_SAME_FILE

            if not is_subtitle_file(child_path):
                return False, texts.BATCH_VALIDATE_CHILD_NOT_SUBTITLE

            # Track this child for duplicate detection
            if norm_child not in child_path_items:
                child_path_items[norm_child] = []
            child_path_items[norm_child].append(child_item)

        # Second pass: mark duplicates with prefix and update display
        duplicate_prefix = texts.DUPLICATE_PREFIX
        for norm_path, items in child_path_items.items():
            if len(items) > 1:
                has_duplicates = True
                # Mark duplicate items with prefix, but skip the first (original) item
                for idx, child_item in enumerate(items):
                    child_path = child_item.data(0, Qt.ItemDataRole.UserRole)
                    basename = get_basename(child_path)
                    current_text = child_item.text(0)
                    if idx == 0:
                        # First item is the original - remove prefix if present
                        if current_text.startswith(duplicate_prefix):
                            child_item.setText(0, basename)
                    else:
                        # Subsequent items are duplicates - add prefix if not present
                        if not current_text.startswith(duplicate_prefix):
                            child_item.setText(0, f"{duplicate_prefix} {basename}")
            else:
                # Ensure non-duplicates don't have the prefix
                child_item = items[0]
                child_path = child_item.data(0, Qt.ItemDataRole.UserRole)
                basename = get_basename(child_path)
                current_text = child_item.text(0)
                if current_text.startswith(duplicate_prefix):
                    child_item.setText(0, basename)

        if has_duplicates:
            return False, texts.BATCH_VALIDATE_DUPLICATE_CHILD

        # Check for duplicates using the precomputed set
        # For one-to-many, check if any pair in this item duplicates another item's pair
        current_item_pairs = self._item_to_pair_id_map.get(id(item), [])
        if current_item_pairs:
            for pair_id in current_item_pairs:
                # Count how many times this pair appears across all items
                duplicate_count = 0
                duplicate_item_ids = []
                for j in range(self.topLevelItemCount()):
                    top = self.topLevelItem(j)
                    top_pairs = self._item_to_pair_id_map.get(id(top), [])
                    if pair_id in top_pairs:
                        duplicate_count += 1
                        duplicate_item_ids.append(top.data(0, self.ITEM_ID_ROLE))

                if duplicate_count > 1:
                    # Only invalidate the newest duplicate (highest ITEM_ID_ROLE)
                    current_id = item.data(0, self.ITEM_ID_ROLE)
                    if current_id == max(duplicate_item_ids):
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
        processed_qcolor = self._parse_rgba_to_qcolor(COLORS["PROCESSED_BACKGROUND"])
        default_qcolor = QColor(Qt.GlobalColor.transparent)

        if not item.parent():  # Top-level item
            item.setData(0, self.VALID_STATE_ROLE, "valid" if is_valid else "invalid")

            # Check if item is processed (Smart Deduplication)
            # Check both item data and cache
            is_processed_data = item.data(0, self.PROCESSED_STATE_ROLE)
            is_force_process = item.data(0, self.FORCE_PROCESS_ROLE)

            # Also check cache
            item_path = item.data(0, Qt.ItemDataRole.UserRole)
            is_processed_cache = False
            if item_path:
                norm_path = os.path.normpath(item_path)
                is_processed_cache = self._processed_items_cache.get(norm_path, False)

            is_processed = (
                is_processed_data or is_processed_cache
            ) and not is_force_process

            # Update the item's processed state data if cache says it's processed
            if is_processed_cache and not is_processed_data and not is_force_process:
                item.setData(0, self.PROCESSED_STATE_ROLE, True)

            if is_processed and self._is_skip_processed_enabled():
                # Processed items get grey background
                item.setBackground(0, processed_qcolor)
                item.setToolTip(0, str(texts.ITEM_ALREADY_PROCESSED))
            else:
                # Normal valid/invalid styling
                item.setBackground(0, green_qcolor if is_valid else red_qcolor)
                # Clear processed tooltip if not processed
                if not is_processed:
                    pass  # Let validation set the tooltip
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
            # Internal drag-and-drop move - save state for undo
            self._save_state_for_undo()
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

        # Smart Deduplication - Force process / Skip process / Add to database options
        if self._is_skip_processed_enabled():
            # Check if any selected items are processed (greyed out) or not processed
            # Also track which items are actually in the database vs just marked as skipped
            processed_items = []  # Items visually marked as processed/skipped
            not_processed_items = []  # Items not visually marked as processed
            items_in_database = []  # Items actually in the processed database
            items_not_in_database = []  # Items not in the processed database
            all_top_level_items = []
            items_to_check = (
                selected_items
                if selected_items
                else ([item_at_pos] if item_at_pos else [])
            )

            for item in items_to_check:
                if item and not item.parent():  # Top-level items only
                    item_path = item.data(0, Qt.ItemDataRole.UserRole)

                    # Only process video files for database operations
                    # Skip subtitle parent items (when subtitle is the reference)
                    if not item_path or not is_video_file(item_path):
                        continue

                    all_top_level_items.append(item)

                    # Check visual state (for skip/force options)
                    is_visually_processed = item.data(0, self.PROCESSED_STATE_ROLE)

                    # Check database status (via cache) for add/remove options
                    norm_path = os.path.normpath(item_path)
                    is_in_database = self._processed_items_cache.get(norm_path, False)

                    if is_visually_processed:
                        processed_items.append(item)
                    else:
                        not_processed_items.append(item)

                    # For database operations, check actual database status
                    if is_in_database:
                        items_in_database.append(item)
                    else:
                        items_not_in_database.append(item)

            if processed_items or not_processed_items:
                menu.addSeparator()

            if processed_items:
                action_force_process = menu.addAction(
                    texts.FORCE_PROCESS_SELECTED_VIDEOS
                )
                action_force_process.triggered.connect(
                    lambda checked=False, items=processed_items: self.force_process_items(
                        items
                    )
                )

            if not_processed_items:
                action_skip_process = menu.addAction(texts.SKIP_PROCESS_SELECTED_VIDEOS)
                action_skip_process.triggered.connect(
                    lambda checked=False, items=not_processed_items: self.skip_process_items(
                        items
                    )
                )

            # Add to database option - only for items NOT already in database
            # Don't show database options while scanning - cache might not be complete
            if not self._is_scanning:
                if items_not_in_database:
                    action_add_to_db = menu.addAction(
                        texts.ADD_VIDEOS_TO_PROCESSED_DATABASE
                    )
                    action_add_to_db.triggered.connect(
                        lambda checked=False, items=items_not_in_database: self.add_items_to_processed_database(
                            items
                        )
                    )

                # Remove from database option - only for items actually in database
                if items_in_database:
                    action_remove_from_db = menu.addAction(
                        texts.REMOVE_VIDEOS_FROM_PROCESSED_DATABASE
                    )
                    action_remove_from_db.triggered.connect(
                        lambda checked=False, items=items_in_database: self.remove_items_from_processed_database(
                            items
                        )
                    )

        menu.addSeparator()
        action_clear_all = menu.addAction(texts.CLEAR_ALL)
        action_clear_all.triggered.connect(self.clear_all_items)
        if not self.has_items():
            action_clear_all.setEnabled(False)

        # Add Undo/Redo actions
        menu.addSeparator()
        action_undo = menu.addAction(f"{texts.UNDO} (Ctrl+Z)")
        action_undo.triggered.connect(self.undo)
        action_undo.setEnabled(self.can_undo())

        action_redo = menu.addAction(f"{texts.REDO} (Ctrl+Y)")
        action_redo.triggered.connect(self.redo)
        action_redo.setEnabled(self.can_redo())

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
        """Add files or folders to the batch tree.

        Returns:
            True if files were added successfully, False if no supported files found
        """
        logger.info(f"Adding files/folders: {len(paths)} items")
        # Save state for undo before making changes
        self._save_state_for_undo()
        # Special case: Check if there are exactly 2 files, one video and one subtitle
        if len(paths) == 2 and all(os.path.isfile(p) for p in paths):
            if paths[0] == paths[1]:
                QMessageBox.warning(
                    self.app_parent,
                    texts.INVALID_PAIR_TITLE,
                    texts.CANNOT_PAIR_FILE_WITH_ITSELF,
                )
                return False
            exts = [os.path.splitext(path)[1].lower() for path in paths]
            # Check if we have one video and one subtitle file
            if exts[0] in VIDEO_EXTENSIONS and exts[1] in SUBTITLE_EXTENSIONS:
                if self.is_duplicate_pair(paths[0], paths[1]):
                    QMessageBox.warning(
                        self.app_parent,
                        texts.BATCH_VALIDATE_DUPLICATE_PAIR,
                        texts.BATCH_VALIDATE_DUPLICATE_PAIR,
                    )
                    return False
                reference_path, sub_path = paths[0], paths[1]
                self.add_explicit_pair(reference_path, sub_path)
                logger.info(
                    f"Added pair: {os.path.basename(reference_path)} + {os.path.basename(sub_path)}"
                )
                return True
            elif exts[1] in VIDEO_EXTENSIONS and exts[0] in SUBTITLE_EXTENSIONS:
                if self.is_duplicate_pair(paths[1], paths[0]):
                    QMessageBox.warning(
                        self.app_parent,
                        texts.BATCH_VALIDATE_DUPLICATE_PAIR,
                        texts.BATCH_VALIDATE_DUPLICATE_PAIR,
                    )
                    return False
                reference_path, sub_path = paths[1], paths[0]
                self.add_explicit_pair(reference_path, sub_path)
                logger.info(
                    f"Added pair: {os.path.basename(reference_path)} + {os.path.basename(sub_path)}"
                )
                return True

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
            return False

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
            return True
        return False

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
            # Check processed status directly from database for sorting
            # (same logic as scan_library_for_new_items for consistency)
            from processed_items_manager import get_processed_items_manager

            manager = get_processed_items_manager()

            # Sort items: invalid not-skipped (0), valid not-skipped (1), invalid skipped (2), valid skipped (3)
            def get_sort_key(item):
                is_valid = self._get_provisional_validity(item) == "valid"
                # Check if item is processed (will be skipped) - check for all video files
                item_path = item.data(0, Qt.ItemDataRole.UserRole)
                is_processed = False
                if item_path and is_video_file(item_path):
                    # Check database directly for accurate status
                    is_processed = manager.is_processed(item_path)
                    # Also update cache
                    norm_path = os.path.normpath(item_path)
                    self._processed_items_cache[norm_path] = is_processed

                # Sorting priority:
                # 0: Invalid not-skipped (need attention first)
                # 1: Valid not-skipped (ready to process)
                # 2: Invalid skipped
                # 3: Valid skipped (last)
                if not is_valid and not is_processed:
                    return (0, os.path.basename(item_path or "").lower())
                elif is_valid and not is_processed:
                    return (1, os.path.basename(item_path or "").lower())
                elif not is_valid and is_processed:
                    return (2, os.path.basename(item_path or "").lower())
                else:  # is_valid and is_processed
                    return (3, os.path.basename(item_path or "").lower())

            newly_created_items.sort(key=get_sort_key)

            # Add to tree (in reverse order to maintain sort when inserting at beginning)
            # Also apply processed visual state immediately based on cache
            for item in reversed(newly_created_items):
                self.insertTopLevelItem(0, item)
                # Apply processed visual state if applicable
                item_path = item.data(0, Qt.ItemDataRole.UserRole)
                if item_path:
                    norm_path = os.path.normpath(item_path)
                    is_processed = self._processed_items_cache.get(norm_path, False)
                    if is_processed:
                        item.setData(0, self.PROCESSED_STATE_ROLE, True)
                        self._apply_processed_style(item, True)

            # Queue all references for Smart Deduplication scan (for async verification)
            self._queue_files_for_scan(references)

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
        # Save state for undo before making changes
        self._save_state_for_undo()
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

        # Queue for Smart Deduplication scan
        self._queue_files_for_scan([video_ref_path])

    def add_parent_with_children(self, reference_path, subtitle_paths):
        """Add a parent (video/reference subtitle) with multiple subtitle children.

        Returns tuple: (added_count, skipped_same_count, skipped_duplicate_count)
        """
        logger.info(
            f"Adding parent with {len(subtitle_paths)} children: {os.path.basename(reference_path)}"
        )

        added = 0
        skipped_same = 0
        skipped_dups = 0

        # Filter out invalid subtitles first
        valid_subs = []
        for sub_path in subtitle_paths:
            norm_ref = os.path.normpath(reference_path)
            norm_sub = os.path.normpath(sub_path)

            # Cannot pair file with itself
            if norm_ref == norm_sub:
                skipped_same += 1
                continue

            # Check if this pair already exists
            if self.is_duplicate_pair(reference_path, sub_path):
                skipped_dups += 1
                continue

            valid_subs.append(sub_path)

        if not valid_subs:
            return (0, skipped_same, skipped_dups)

        # Save state for undo before making changes
        self._save_state_for_undo()

        # Create parent item
        parent_item_id = self._get_next_id()
        parent_item = create_tree_widget_item(
            reference_path, None, self.icon_provider, item_id=parent_item_id
        )

        # Add all valid children
        for sub_path in valid_subs:
            child_item_id = self._get_next_id()
            child_item = create_tree_widget_item(
                sub_path, parent_item, self.icon_provider, item_id=child_item_id
            )
            added += 1

        parent_item.setExpanded(True)
        self.insertTopLevelItem(0, parent_item)
        # UI update (including sort) will be scheduled by model signals

        return (added, skipped_same, skipped_dups)

    def find_parent_by_path(self, reference_path):
        """Find an existing top-level parent item by its file path."""
        norm_ref = os.path.normpath(reference_path)
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            item_path = item.data(0, Qt.ItemDataRole.UserRole)
            if item_path and os.path.normpath(item_path) == norm_ref:
                return item
        return None

    def add_children_to_parent(self, parent_item, subtitle_paths):
        """Add multiple subtitle children to an existing parent item.

        Returns tuple: (added_count, skipped_same_count, skipped_duplicate_count)
        """
        if not parent_item:
            return (0, 0, 0)

        reference_path = parent_item.data(0, Qt.ItemDataRole.UserRole)
        logger.info(
            f"Adding {len(subtitle_paths)} children to existing parent: {os.path.basename(reference_path)}"
        )

        added = 0
        skipped_same = 0
        skipped_dups = 0

        valid_subs = []
        for sub_path in subtitle_paths:
            norm_ref = os.path.normpath(reference_path)
            norm_sub = os.path.normpath(sub_path)

            # Cannot pair file with itself
            if norm_ref == norm_sub:
                skipped_same += 1
                continue

            # Check if this pair already exists
            if self.is_duplicate_pair(reference_path, sub_path):
                skipped_dups += 1
                continue

            valid_subs.append(sub_path)

        if not valid_subs:
            return (0, skipped_same, skipped_dups)

        # Save state for undo before making changes
        self._save_state_for_undo()

        # Add all valid children
        for sub_path in valid_subs:
            child_item_id = self._get_next_id()
            child_item = create_tree_widget_item(
                sub_path, parent_item, self.icon_provider, item_id=child_item_id
            )
            added += 1

        parent_item.setExpanded(True)
        self._schedule_ui_update()

        return (added, skipped_same, skipped_dups)

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
            # Save state for undo before making changes
            self._save_state_for_undo()
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

        # Save state for undo before making changes
        self._save_state_for_undo()

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
            # Save state for undo before making changes
            self._save_state_for_undo()
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

        # Save state for undo before making changes
        self._save_state_for_undo()

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

            # Save state for undo before making changes
            self._save_state_for_undo()

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
            # Save state for undo before making changes
            self._save_state_for_undo()
            self.clear()
            # Reset library loaded flag when tree is cleared
            self._library_loaded = False

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
        """Get all valid pairs from the batch tree.

        Supports one-to-many relationships: each child subtitle under a valid
        parent creates a separate pair with the same reference/video.

        Skips items that are marked as processed (unless force-processed)
        when the "skip previously processed items" setting is enabled.

        Returns:
            List of tuples (reference_path, subtitle_path)
        """
        pairs = []
        skip_processed = self._is_skip_processed_enabled()

        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if (
                item
                and item.childCount() >= 1
                and item.data(0, self.VALID_STATE_ROLE) == "valid"
            ):
                reference_path = item.data(0, Qt.ItemDataRole.UserRole)
                if not reference_path:
                    continue

                # Check if item should be skipped (processed but not force-processed)
                if skip_processed:
                    is_processed = item.data(0, self.PROCESSED_STATE_ROLE)
                    is_force_process = item.data(0, self.FORCE_PROCESS_ROLE)

                    # Also check cache for immediate updates
                    if not is_processed and reference_path:
                        norm_path = os.path.normpath(reference_path)
                        is_processed = self._processed_items_cache.get(norm_path, False)

                    if is_processed and not is_force_process:
                        # Skip this item - it was already processed
                        continue

                # Collect all child subtitles as separate pairs
                for j in range(item.childCount()):
                    sub_item = item.child(j)
                    if sub_item:
                        sub_path = sub_item.data(0, Qt.ItemDataRole.UserRole)
                        if sub_path:
                            pairs.append((reference_path, sub_path))
        return pairs

    def has_items(self):
        return self.topLevelItemCount() > 0

    # ==================== Undo/Redo System ====================

    def _save_state_for_undo(self):
        """Save the current tree state to the undo stack.

        Only saves state if the tree has items. This prevents undoing
        back to an empty state when first adding files.
        """
        if self._is_restoring_state:
            return  # Don't save state while restoring

        # Don't save empty state - we don't want to undo back to empty
        if self.topLevelItemCount() == 0:
            return

        state = self._serialize_tree_state()
        self._undo_stack.append(state)

        # Limit undo stack size
        if len(self._undo_stack) > self._max_undo_levels:
            self._undo_stack.pop(0)

        # Clear redo stack when a new action is performed
        self._redo_stack.clear()

        logger.info(f"State saved for undo. Undo stack size: {len(self._undo_stack)}")

    def _serialize_tree_state(self):
        """Serialize the current tree state to a list of dictionaries."""
        state = {"next_item_id": self._next_item_id, "items": []}

        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item:
                state["items"].append(self._serialize_item(item))

        return state

    def _serialize_item(self, item):
        """Serialize a single tree item and its children."""
        item_data = {
            "file_path": item.data(0, Qt.ItemDataRole.UserRole),
            "item_id": item.data(0, self.ITEM_ID_ROLE),
            "text": item.text(0),
            "force_process": item.data(0, self.FORCE_PROCESS_ROLE) or False,
            "manually_skipped": item.data(0, self.PROCESSED_STATE_ROLE) or False,
            "children": [],
        }

        for i in range(item.childCount()):
            child = item.child(i)
            if child:
                item_data["children"].append(self._serialize_item(child))

        return item_data

    def _restore_tree_state(self, state):
        """Restore the tree state from a serialized state dictionary."""
        self._is_restoring_state = True

        try:
            # Clear current tree without triggering undo save
            self.clear()

            # Restore next_item_id
            self._next_item_id = state.get("next_item_id", 1)

            # Restore all items
            for item_data in state.get("items", []):
                item = self._deserialize_item(item_data)
                if item:
                    self.addTopLevelItem(item)
                    item.setExpanded(True)

            # Trigger UI update
            self._schedule_ui_update()

            # Re-apply processed states from cache after restore
            self._reapply_processed_states_from_cache()

        finally:
            self._is_restoring_state = False

    def _reapply_processed_states_from_cache(self):
        """Re-apply processed states and styles to items after undo/redo."""
        if not self._is_skip_processed_enabled():
            return

        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item:
                # Check if force process is set (takes priority)
                if item.data(0, self.FORCE_PROCESS_ROLE):
                    item.setData(0, self.PROCESSED_STATE_ROLE, False)
                    continue

                # Check if manually skipped (from undo state)
                if item.data(0, self.PROCESSED_STATE_ROLE):
                    self._apply_processed_style(item, True)
                    continue

                # Otherwise check cache for processed status
                item_path = item.data(0, Qt.ItemDataRole.UserRole)
                if item_path:
                    norm_path = os.path.normpath(item_path)
                    is_processed = self._processed_items_cache.get(norm_path, False)
                    if is_processed:
                        item.setData(0, self.PROCESSED_STATE_ROLE, True)
                        self._apply_processed_style(item, True)

    def _deserialize_item(self, item_data):
        """Deserialize a single tree item and its children from saved data."""
        file_path = item_data.get("file_path")
        if not file_path:
            return None

        item = QTreeWidgetItem([item_data.get("text", get_basename(file_path))])
        item.setData(0, Qt.ItemDataRole.UserRole, file_path)
        item.setData(0, self.ITEM_ID_ROLE, item_data.get("item_id"))
        item.setIcon(0, self.icon_provider.icon(QFileInfo(file_path)))

        # Restore force_process and manually_skipped states
        if item_data.get("force_process", False):
            item.setData(0, self.FORCE_PROCESS_ROLE, True)
        if item_data.get("manually_skipped", False):
            item.setData(0, self.PROCESSED_STATE_ROLE, True)

        # Restore children
        for child_data in item_data.get("children", []):
            child = self._deserialize_item(child_data)
            if child:
                item.addChild(child)

        return item

    def undo(self):
        """Undo the last action by restoring the previous state."""
        if not self._undo_stack:
            logger.info("Nothing to undo")
            return False

        # Save current state to redo stack before undoing
        current_state = self._serialize_tree_state()
        self._redo_stack.append(current_state)

        # Pop and restore the previous state
        previous_state = self._undo_stack.pop()
        self._restore_tree_state(previous_state)

        logger.info(
            f"Undo performed. Undo stack: {len(self._undo_stack)}, Redo stack: {len(self._redo_stack)}"
        )
        return True

    def redo(self):
        """Redo the last undone action by restoring the next state."""
        if not self._redo_stack:
            logger.info("Nothing to redo")
            return False

        # Save current state to undo stack before redoing
        current_state = self._serialize_tree_state()
        self._undo_stack.append(current_state)

        # Pop and restore the next state
        next_state = self._redo_stack.pop()
        self._restore_tree_state(next_state)

        logger.info(
            f"Redo performed. Undo stack: {len(self._undo_stack)}, Redo stack: {len(self._redo_stack)}"
        )
        return True

    def can_undo(self):
        """Check if undo is available."""
        return len(self._undo_stack) > 0

    def can_redo(self):
        """Check if redo is available."""
        return len(self._redo_stack) > 0


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

        # Sync tracking dropdown button (replaces Change selected button)
        self.btn_sync_tracking = QPushButton(
            texts.SYNC_TRACKING, self.batch_buttons_widget
        )
        self.btn_sync_tracking.clicked.connect(
            lambda: self.show_sync_tracking_menu(self.btn_sync_tracking)
        )
        # Update button color based on sync tracking status
        _update_sync_tracking_button_style(self)

        self.btn_batch_refresh = QPushButton(texts.REFRESH, self.batch_buttons_widget)
        self.btn_batch_refresh.setToolTip(texts.REFRESH_PROCESSED_STATUS_TOOLTIP)
        self.btn_batch_refresh.clicked.connect(
            self.batch_tree_view.refresh_processed_status
        )

        batch_buttons_layout.addWidget(self.btn_batch_add_files)
        batch_buttons_layout.addWidget(self.btn_batch_remove_selected)
        batch_buttons_layout.addWidget(self.btn_sync_tracking)
        batch_buttons_layout.addWidget(self.btn_batch_refresh)


def show_sync_tracking_menu(self, source_widget=None, position=None):
    """Show the sync tracking menu with library and processed video options.

    Args:
        source_widget: The widget that triggered the menu (optional)
        position: The global position where to show the menu (optional)
    """
    menu = QMenu(self)

    # Processed videos section - use dynamic text based on current state (moved to top)
    is_enabled = self.config.get(
        "skip_previously_processed_videos",
        DEFAULT_OPTIONS["skip_previously_processed_videos"],
    )
    skip_text = (
        str(texts.SYNC_TRACKING_ENABLED)
        if is_enabled
        else str(texts.SYNC_TRACKING_DISABLED)
    )
    action_skip_processed = menu.addAction(skip_text)
    action_skip_processed.setCheckable(True)
    action_skip_processed.setChecked(is_enabled)

    action_clear_database = menu.addAction(texts.CLEAR_PROCESSED_ITEMS_DATABASE)

    menu.addSeparator()

    # Backup/Import section
    action_backup_database = menu.addAction(texts.BACKUP_PROCESSED_DATABASE)
    action_import_database = menu.addAction(texts.IMPORT_PROCESSED_DATABASE)

    menu.addSeparator()

    # Library section
    action_manage_library = menu.addAction(texts.MANAGE_LIBRARY_FOLDERS)
    # Use Reload library if library has been loaded, otherwise Load library
    load_library_text = (
        texts.RELOAD_LIBRARY
        if self.batch_tree_view._library_loaded
        else texts.LOAD_LIBRARY
    )
    action_load_library = menu.addAction(load_library_text)

    # Connect actions
    action_manage_library.triggered.connect(lambda: self.open_library_manager())
    action_load_library.triggered.connect(lambda: self.smart_load_library())
    action_skip_processed.triggered.connect(
        lambda checked: self._on_skip_processed_changed(checked)
    )
    action_clear_database.triggered.connect(
        lambda: self._clear_processed_items_database()
    )
    action_backup_database.triggered.connect(lambda: self._backup_processed_database())
    action_import_database.triggered.connect(lambda: self._import_processed_database())

    # Show menu at the specified position
    if position:
        menu.popup(position)
    elif source_widget:
        menu.popup(source_widget.mapToGlobal(source_widget.rect().bottomLeft()))
    else:
        menu.popup(QCursor.pos())

    return menu


def _update_sync_tracking_button_style(self):
    """Update the sync tracking button text color based on enabled/disabled state."""
    is_enabled = self.config.get(
        "skip_previously_processed_videos",
        DEFAULT_OPTIONS["skip_previously_processed_videos"],
    )
    if is_enabled:
        self.btn_sync_tracking.setStyleSheet(f"color: {COLORS['GREEN']};")
    else:
        self.btn_sync_tracking.setStyleSheet("")  # Reset to default


def smart_load_library(self):
    """Smart load library - open manager if empty, otherwise scan for new items in library folders."""
    from gui_load_library import get_library_folders_manager, LibraryManagerDialog

    manager = get_library_folders_manager()
    folders = manager.get_all_folders()

    if not folders:
        # No folders in library, open the manager dialog
        self.open_library_manager()
    else:
        # Scan library folders for new items and add them
        valid_folders = [f for f in folders if os.path.isdir(f)]

        if not valid_folders:
            # All folders are invalid, show manager
            QMessageBox.warning(
                self, texts.LIBRARY_MANAGER_TITLE, texts.NO_VALID_LIBRARY_FOLDERS
            )
            self.open_library_manager()
            return

        # Scan for new items and add them to batch tree
        self.batch_tree_view.scan_library_for_new_items(valid_folders)


def open_library_manager(self):
    """Open the Library Manager dialog."""
    from gui_load_library import LibraryManagerDialog

    dialog = LibraryManagerDialog(self)
    if dialog.exec():
        # User clicked "Load library" - load valid folders
        valid_folders = dialog.get_valid_folders()
        if valid_folders:
            self.batch_tree_view.add_files_or_folders(valid_folders)
            logger.info(f"Loaded {len(valid_folders)} library folders from manager")


def show_batch_add_menu(
    self, source_widget=None, position=None, include_sync_tracking=False
):
    """Show the batch add menu with various file addition options.

    Args:
        source_widget: The widget that triggered the menu (optional)
        position: The global position where to show the menu (optional)
        include_sync_tracking: Whether to include the Sync tracking submenu (for InputBox clicks)
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
    action_pair_multiple_subs = menu.addAction(
        texts.PAIR_MULTIPLE_SUBTITLES_WITH_SINGLE_SOURCE
    )

    action_add_pair.triggered.connect(lambda: handle_add_pair(self))
    action_add_folder.triggered.connect(lambda: handle_add_folder(self))
    action_add_files.triggered.connect(lambda: handle_add_multiple_files(self))
    action_add_continuously.triggered.connect(
        lambda: handle_add_pairs_continuously(self)
    )
    # Connect the new auto-pairing option
    action_auto_pairing.triggered.connect(lambda: self.open_auto_pairing_dialog())
    # Connect the "pair multiple subtitles with single source" option
    action_pair_multiple_subs.triggered.connect(
        lambda: self.open_pair_multiple_subs_dialog()
    )

    # Add Sync tracking submenu if requested (for InputBox clicks)
    if include_sync_tracking:
        menu.addSeparator()
        is_enabled = self.config.get(
            "skip_previously_processed_videos",
            DEFAULT_OPTIONS["skip_previously_processed_videos"],
        )
        status_text = str(texts.ENABLED) if is_enabled else str(texts.DISABLED)
        sync_tracking_menu = menu.addMenu(f"{texts.SYNC_TRACKING} ({status_text})")

        # Processed videos section - use dynamic text based on current state (at top)
        skip_text = (
            str(texts.SYNC_TRACKING_ENABLED)
            if is_enabled
            else str(texts.SYNC_TRACKING_DISABLED)
        )
        action_skip_processed = sync_tracking_menu.addAction(skip_text)
        action_skip_processed.setCheckable(True)
        action_skip_processed.setChecked(is_enabled)

        action_clear_database = sync_tracking_menu.addAction(
            texts.CLEAR_PROCESSED_ITEMS_DATABASE
        )

        sync_tracking_menu.addSeparator()

        # Backup/Import section
        action_backup_database = sync_tracking_menu.addAction(
            texts.BACKUP_PROCESSED_DATABASE
        )
        action_import_database = sync_tracking_menu.addAction(
            texts.IMPORT_PROCESSED_DATABASE
        )

        sync_tracking_menu.addSeparator()

        # Library section
        action_manage_library = sync_tracking_menu.addAction(
            texts.MANAGE_LIBRARY_FOLDERS
        )
        # Use Reload library if library has been loaded, otherwise Load library
        load_library_text = (
            texts.RELOAD_LIBRARY
            if self.batch_tree_view._library_loaded
            else texts.LOAD_LIBRARY
        )
        action_load_library = sync_tracking_menu.addAction(load_library_text)

        # Connect sync tracking actions
        action_manage_library.triggered.connect(lambda: self.open_library_manager())
        action_load_library.triggered.connect(lambda: self.smart_load_library())
        action_skip_processed.triggered.connect(
            lambda checked: self._on_skip_processed_changed(checked)
        )
        action_clear_database.triggered.connect(
            lambda: self._clear_processed_items_database()
        )
        action_backup_database.triggered.connect(
            lambda: self._backup_processed_database()
        )
        action_import_database.triggered.connect(
            lambda: self._import_processed_database()
        )

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
