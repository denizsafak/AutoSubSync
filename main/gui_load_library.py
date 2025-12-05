"""
Library Folders Manager for AutoSubSync Batch Mode.

This module provides a system to save and manage library folders
that can be quickly loaded into the Batch Mode.
"""

import os
import sqlite3
import logging
import threading
import texts
import re
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QFileDialog,
    QMessageBox,
    QScrollArea,
    QFrame,
    QWidget,
    QDialogButtonBox,
    QHeaderView,
    QMenu,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QShortcut, QKeySequence
from constants import COLORS
from constants import PROGRAM_NAME

logger = logging.getLogger(__name__)


class LibraryFoldersManager:
    """
    Manages a database of library folders for quick loading into Batch Mode.

    Uses SQLite to persist folder paths that can be loaded later.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern to ensure single database connection."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the database connection and create tables if needed."""
        if self._initialized:
            return

        self._initialized = True
        self._db_lock = threading.Lock()
        self._conn = None
        self._init_database()

    def _get_db_path(self) -> str:
        """Get the path to the SQLite database file."""
        from utils import get_user_config_path

        config_path = get_user_config_path()
        config_dir = os.path.dirname(config_path)
        return os.path.join(config_dir, "library_folders.db")

    def _init_database(self):
        """Initialize the SQLite database and create tables."""
        try:
            db_path = self._get_db_path()
            self._conn = sqlite3.connect(db_path, check_same_thread=False)

            cursor = self._conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS library_folders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    folder_path TEXT UNIQUE NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            self._conn.commit()
            logger.info(f"Library folders database initialized at: {db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize library folders database: {e}")
            raise

    def add_folder(self, folder_path: str) -> bool:
        """
        Add a folder to the library.

        Args:
            folder_path: Absolute path to the folder

        Returns:
            True if added successfully, False if already exists or error
        """
        try:
            with self._db_lock:
                cursor = self._conn.cursor()
                cursor.execute(
                    "INSERT OR IGNORE INTO library_folders (folder_path) VALUES (?)",
                    (folder_path,),
                )
                self._conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to add folder to library: {e}")
            return False

    def remove_folder(self, folder_path: str) -> bool:
        """
        Remove a folder from the library.

        Args:
            folder_path: Absolute path to the folder

        Returns:
            True if removed successfully, False if not found or error
        """
        try:
            with self._db_lock:
                cursor = self._conn.cursor()
                cursor.execute(
                    "DELETE FROM library_folders WHERE folder_path = ?", (folder_path,)
                )
                self._conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to remove folder from library: {e}")
            return False

    def get_all_folders(self) -> list:
        """
        Get all folders in the library.

        Returns:
            List of folder paths
        """
        try:
            with self._db_lock:
                cursor = self._conn.cursor()
                cursor.execute(
                    "SELECT folder_path FROM library_folders ORDER BY added_at ASC"
                )
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get library folders: {e}")
            return []

    def get_folder_count(self) -> int:
        """Get the number of folders in the library."""
        try:
            with self._db_lock:
                cursor = self._conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM library_folders")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to get folder count: {e}")
            return 0

    def clear_all(self) -> bool:
        """
        Remove all folders from the library.

        Returns:
            True if cleared successfully, False on error
        """
        try:
            with self._db_lock:
                cursor = self._conn.cursor()
                cursor.execute("DELETE FROM library_folders")
                self._conn.commit()
                logger.info("Library folders cleared")
                return True
        except Exception as e:
            logger.error(f"Failed to clear library folders: {e}")
            return False

    def folder_exists_in_library(self, folder_path: str) -> bool:
        """Check if a folder is already in the library."""
        try:
            with self._db_lock:
                cursor = self._conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM library_folders WHERE folder_path = ?",
                    (folder_path,),
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Failed to check folder existence: {e}")
            return False


def get_library_folders_manager() -> LibraryFoldersManager:
    """Get the singleton instance of LibraryFoldersManager."""
    return LibraryFoldersManager()


class LibraryManagerDialog(QDialog):
    """
    Dialog for managing library folders.

    Allows adding, removing, and viewing folders that can be
    quickly loaded into Batch Mode.
    """

    # Role for storing folder path
    FOLDER_PATH_ROLE = Qt.ItemDataRole.UserRole + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle(f"{PROGRAM_NAME} - {texts.LIBRARY_MANAGER_TITLE}")
        self.resize(700, 500)
        self.setMinimumSize(500, 400)

        self.manager = get_library_folders_manager()
        self.initUI()
        self.load_folders()

    def initUI(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        # Explanation section (similar to gui_auto_pairing.py)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMaximumHeight(100)

        exp_widget = QWidget()
        exp_layout = QVBoxLayout(exp_widget)
        exp_layout.setContentsMargins(0, 0, 0, 0)
        exp_layout.addWidget(QLabel(f"<h2>{texts.LIBRARY_MANAGER_TITLE}</h2>"))
        desc = QLabel(texts.LIBRARY_MANAGER_DESC)
        desc.setWordWrap(True)
        exp_layout.addWidget(desc)
        exp_layout.addStretch()
        scroll.setWidget(exp_widget)
        layout.addWidget(scroll)

        # Add some spacing between description and buttons
        layout.addSpacing(10)

        # Button panel
        button_layout = QHBoxLayout()

        self.add_folder_btn = QPushButton(texts.ADD_FOLDER)
        self.add_folder_btn.clicked.connect(self.add_folder)
        button_layout.addWidget(self.add_folder_btn)

        self.remove_folder_btn = QPushButton(texts.REMOVE_SELECTED)
        self.remove_folder_btn.clicked.connect(self.remove_selected_folders)
        self.remove_folder_btn.setEnabled(False)
        button_layout.addWidget(self.remove_folder_btn)

        self.clear_all_btn = QPushButton(texts.CLEAR_ALL)
        self.clear_all_btn.clicked.connect(self.clear_all_folders)
        button_layout.addWidget(self.clear_all_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Folder list
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderLabels([texts.FOLDER_PATH, texts.STATUS])
        self.folder_tree.setColumnCount(2)
        self.folder_tree.setRootIsDecorated(False)
        self.folder_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.folder_tree.setStyleSheet("QTreeView::item { height: 32px; }")
        self.folder_tree.itemSelectionChanged.connect(self.update_button_states)

        # Add Delete key shortcut
        delete_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self)
        delete_shortcut.activated.connect(self.remove_selected_folders)

        # Add right-click context menu
        self.folder_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.folder_tree.customContextMenuRequested.connect(self.show_context_menu)

        # Set column widths
        header = self.folder_tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.folder_tree.setColumnWidth(1, 120)

        layout.addWidget(self.folder_tree)

        # Bottom section with count and dialog buttons
        bottom_layout = QHBoxLayout()
        self.folder_count_label = QLabel("")
        self.folder_count_label.setStyleSheet("color: grey; font-size: 12px;")
        bottom_layout.addWidget(self.folder_count_label)
        bottom_layout.addStretch()

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.btn_load = button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.btn_load.setText(texts.LOAD_LIBRARY)
        bottom_layout.addWidget(button_box)

        layout.addLayout(bottom_layout)

        self.update_button_states()

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

    def load_folders(self):
        """Load folders from database into the tree widget."""
        self.folder_tree.clear()
        folders = self.manager.get_all_folders()

        for folder_path in folders:
            self.add_folder_item(folder_path)

        self.update_folder_count()
        self.update_button_states()

    def add_folder_item(self, folder_path: str):
        """Add a folder item to the tree widget."""
        item = QTreeWidgetItem()
        item.setText(0, folder_path)
        item.setData(0, self.FOLDER_PATH_ROLE, folder_path)

        # Check if folder exists and set status
        if os.path.isdir(folder_path):
            item.setText(1, texts.FOLDER_EXISTS)
            # Set green background for existing folders
            green_qcolor = self._parse_rgba_to_qcolor(COLORS["GREEN_BACKGROUND_HOVER"])
            item.setBackground(0, green_qcolor)
            item.setBackground(1, green_qcolor)
        else:
            item.setText(1, texts.FOLDER_DOES_NOT_EXIST)
            # Set red background for missing folders
            red_qcolor = self._parse_rgba_to_qcolor(COLORS["RED_BACKGROUND_HOVER"])
            item.setBackground(0, red_qcolor)
            item.setBackground(1, red_qcolor)

        self.folder_tree.addTopLevelItem(item)

    def add_folder(self):
        """Open folder dialog and add selected folder to library."""
        folder = QFileDialog.getExistingDirectory(
            self, texts.SELECT_FOLDER, "", QFileDialog.Option.ShowDirsOnly
        )

        if folder:
            if self.manager.folder_exists_in_library(folder):
                QMessageBox.information(
                    self, texts.INFORMATION, texts.FOLDER_ALREADY_IN_LIBRARY
                )
                return

            if self.manager.add_folder(folder):
                self.add_folder_item(folder)
                self.update_folder_count()
                self.update_button_states()  # Update button states after adding
                logger.info(f"Added folder to library: {folder}")
            else:
                QMessageBox.warning(self, texts.ERROR, texts.FAILED_TO_ADD_FOLDER)

    def remove_selected_folders(self):
        """Remove selected folders from the library."""
        selected_items = self.folder_tree.selectedItems()
        if not selected_items:
            return

        # Confirmation for multiple removals
        if len(selected_items) > 1:
            reply = QMessageBox.question(
                self,
                texts.CONFIRMATION,
                texts.CONFIRM_REMOVE_FOLDERS.format(count=len(selected_items)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        for item in selected_items:
            folder_path = item.data(0, self.FOLDER_PATH_ROLE)
            if self.manager.remove_folder(folder_path):
                index = self.folder_tree.indexOfTopLevelItem(item)
                self.folder_tree.takeTopLevelItem(index)
                logger.info(f"Removed folder from library: {folder_path}")

        self.update_folder_count()
        self.update_button_states()

    def clear_all_folders(self):
        """Clear all folders from the library after confirmation."""
        count = self.manager.get_folder_count()
        if count == 0:
            return

        reply = QMessageBox.question(
            self,
            texts.CONFIRMATION,
            texts.CONFIRM_CLEAR_LIBRARY.format(count=count),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.manager.clear_all():
                self.folder_tree.clear()
                self.update_folder_count()
                self.update_button_states()
                logger.info("Library folders cleared")

    def update_folder_count(self):
        """Update the folder count label."""
        count = self.folder_tree.topLevelItemCount()
        self.folder_count_label.setText(texts.LIBRARY_FOLDER_COUNT.format(count=count))

    def update_button_states(self):
        """Update button enabled states based on selection."""
        has_selection = len(self.folder_tree.selectedItems()) > 0
        has_items = self.folder_tree.topLevelItemCount() > 0

        self.remove_folder_btn.setEnabled(has_selection)
        self.clear_all_btn.setEnabled(has_items)
        self.btn_load.setEnabled(has_items)

    def show_context_menu(self, position):
        """Show context menu for the tree widget."""
        if self.folder_tree.topLevelItemCount() == 0:
            return

        menu = QMenu(self)

        # Add "Remove selected" action
        remove_action = menu.addAction(texts.REMOVE_SELECTED)
        remove_action.triggered.connect(self.remove_selected_folders)

        # Only enable if items are selected
        has_selection = len(self.folder_tree.selectedItems()) > 0
        remove_action.setEnabled(has_selection)

        # Show the menu at the cursor position
        menu.exec(self.folder_tree.mapToGlobal(position))

    def get_valid_folders(self) -> list:
        """Get list of folders that exist on disk."""
        folders = self.manager.get_all_folders()
        return [f for f in folders if os.path.isdir(f)]

    def get_all_folders_from_ui(self) -> list:
        """Get all folders currently in the tree widget."""
        folders = []
        for i in range(self.folder_tree.topLevelItemCount()):
            item = self.folder_tree.topLevelItem(i)
            folder_path = item.data(0, self.FOLDER_PATH_ROLE)
            if folder_path:
                folders.append(folder_path)
        return folders
