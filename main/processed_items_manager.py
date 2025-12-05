"""
Smart Deduplication System for AutoSubSync Batch Mode.

This module provides content-based hashing to detect and skip
video files that have already been processed.
"""

import os
import sqlite3
import hashlib
import logging
import threading
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Chunk size for partial hashing (64KB)
HASH_CHUNK_SIZE = 64 * 1024  # 64KB


class ProcessedItemsManager:
    """
    Manages a database of processed items using content-based hashing.

    Uses partial hashing strategy for efficient fingerprinting:
    - File Size + First 64KB + Last 64KB

    This approach handles file moves/renames while remaining performant
    for large video files.
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

    def get_db_path(self) -> str:
        """Get the path to the SQLite database file (public method)."""
        return self._get_db_path()

    def _get_db_path(self) -> str:
        """Get the path to the SQLite database file."""
        from utils import get_user_config_path

        config_path = get_user_config_path()
        config_dir = os.path.dirname(config_path)
        return os.path.join(config_dir, "processed_items.db")

    def _init_database(self):
        """Initialize the SQLite database and create tables."""
        try:
            db_path = self._get_db_path()
            self._conn = sqlite3.connect(db_path, check_same_thread=False)

            cursor = self._conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_hash TEXT UNIQUE NOT NULL,
                    file_size INTEGER NOT NULL,
                    original_filename TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_file_hash ON processed_items(file_hash)
            """
            )
            self._conn.commit()
            logger.info(f"Processed items database initialized at: {db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize processed items database: {e}")
            raise

    def _calculate_partial_hash(self, filepath: str) -> Optional[Tuple[str, int]]:
        """
        Calculate a partial hash of a file for efficient fingerprinting.

        Strategy: File Size + First 64KB + Last 64KB

        Args:
            filepath: Path to the file to hash

        Returns:
            Tuple of (hash_string, file_size) or None if file cannot be read
        """
        try:
            if not os.path.exists(filepath):
                logger.warning(f"File does not exist: {filepath}")
                return None

            file_size = os.path.getsize(filepath)
            hasher = hashlib.sha256()

            # Include file size in hash
            hasher.update(str(file_size).encode("utf-8"))

            with open(filepath, "rb") as f:
                # Read first 64KB
                first_chunk = f.read(HASH_CHUNK_SIZE)
                hasher.update(first_chunk)

                # Read last 64KB (if file is large enough)
                if file_size > HASH_CHUNK_SIZE * 2:
                    f.seek(-HASH_CHUNK_SIZE, os.SEEK_END)
                    last_chunk = f.read(HASH_CHUNK_SIZE)
                    hasher.update(last_chunk)
                elif file_size > HASH_CHUNK_SIZE:
                    # File is between 64KB and 128KB, read the remaining part
                    last_chunk = f.read()
                    hasher.update(last_chunk)

            return (hasher.hexdigest(), file_size)

        except PermissionError:
            logger.error(f"Permission denied reading file: {filepath}")
            return None
        except Exception as e:
            logger.error(f"Error calculating hash for {filepath}: {e}")
            return None

    def is_processed(self, filepath: str) -> bool:
        """
        Check if a file has been previously processed.

        Args:
            filepath: Path to the file to check

        Returns:
            True if the file hash exists in the database, False otherwise
        """
        hash_result = self._calculate_partial_hash(filepath)
        if hash_result is None:
            return False

        file_hash, _ = hash_result

        with self._db_lock:
            try:
                cursor = self._conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM processed_items WHERE file_hash = ?", (file_hash,)
                )
                result = cursor.fetchone()
                return result is not None
            except Exception as e:
                logger.error(f"Error checking processed status: {e}")
                return False

    def mark_as_processed(self, filepath: str, silent: bool = False) -> bool:
        """
        Mark a file as processed in the database.

        Args:
            filepath: Path to the file to mark as processed
            silent: If True, suppress info logging (useful for batch operations)

        Returns:
            True if successfully marked, False otherwise
        """
        hash_result = self._calculate_partial_hash(filepath)
        if hash_result is None:
            return False

        file_hash, file_size = hash_result
        filename = os.path.basename(filepath)

        with self._db_lock:
            try:
                cursor = self._conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO processed_items 
                    (file_hash, file_size, original_filename, processed_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (file_hash, file_size, filename),
                )
                self._conn.commit()
                if not silent:
                    logger.info(
                        f"[Sync Tracking] Item '{filename}' added to processed items database."
                    )
                return True
            except Exception as e:
                logger.error(f"Error marking file as processed: {e}")
                return False

    def remove_from_processed(self, filepath: str, silent: bool = False) -> bool:
        """
        Remove a file from the processed database.

        Args:
            filepath: Path to the file to remove
            silent: If True, suppress info logging (useful for batch operations)

        Returns:
            True if successfully removed, False otherwise
        """
        hash_result = self._calculate_partial_hash(filepath)
        if hash_result is None:
            return False

        file_hash, _ = hash_result
        filename = os.path.basename(filepath)

        with self._db_lock:
            try:
                cursor = self._conn.cursor()
                cursor.execute(
                    "DELETE FROM processed_items WHERE file_hash = ?", (file_hash,)
                )
                self._conn.commit()
                if not silent and cursor.rowcount > 0:
                    logger.info(
                        f"[Sync Tracking] Item '{filename}' removed from processed items database."
                    )
                return cursor.rowcount > 0
            except Exception as e:
                logger.error(f"Error removing file from processed database: {e}")
                return False

    def clear_all(self) -> bool:
        """
        Clear all entries from the processed items database.

        Returns:
            True if successfully cleared, False otherwise
        """
        with self._db_lock:
            try:
                cursor = self._conn.cursor()
                cursor.execute("DELETE FROM processed_items")
                self._conn.commit()
                logger.info("Processed items database cleared.")
                return True
            except Exception as e:
                logger.error(f"Error clearing processed items database: {e}")
                return False

    def get_processed_count(self) -> int:
        """
        Get the count of processed items in the database.

        Returns:
            Number of processed items
        """
        with self._db_lock:
            try:
                cursor = self._conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM processed_items")
                result = cursor.fetchone()
                return result[0] if result else 0
            except Exception as e:
                logger.error(f"Error getting processed count: {e}")
                return 0

    def close(self):
        """Close the database connection."""
        if self._conn:
            with self._db_lock:
                self._conn.close()
                self._conn = None
                logger.info("Processed items database connection closed.")

    def import_from_database(self, import_path: str) -> Tuple[int, int]:
        """
        Import items from another processed items database.

        Args:
            import_path: Path to the database file to import from

        Returns:
            Tuple of (imported_count, skipped_count), or (-1, -1) on error
        """
        import sqlite3

        try:
            # Connect to the import database
            import_conn = sqlite3.connect(import_path)
            import_cursor = import_conn.cursor()

            # Check if the table exists
            import_cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='processed_items'"
            )
            if not import_cursor.fetchone():
                logger.error(
                    f"Import database does not contain processed_items table: {import_path}"
                )
                import_conn.close()
                return (-1, -1)

            # Get all items from import database
            import_cursor.execute(
                "SELECT file_hash, file_size, original_filename FROM processed_items"
            )
            items_to_import = import_cursor.fetchall()
            import_conn.close()

            imported = 0
            skipped = 0

            with self._db_lock:
                cursor = self._conn.cursor()
                for file_hash, file_size, original_filename in items_to_import:
                    try:
                        cursor.execute(
                            """
                            INSERT OR IGNORE INTO processed_items 
                            (file_hash, file_size, original_filename, processed_at)
                            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                            """,
                            (file_hash, file_size, original_filename),
                        )
                        if cursor.rowcount > 0:
                            imported += 1
                        else:
                            skipped += 1
                    except Exception as e:
                        logger.warning(
                            f"Failed to import item {original_filename}: {e}"
                        )
                        skipped += 1

                self._conn.commit()

            logger.info(
                f"Imported {imported} items, skipped {skipped} duplicates from {import_path}"
            )
            return (imported, skipped)

        except Exception as e:
            logger.error(f"Failed to import from database {import_path}: {e}")
            return (-1, -1)


# Convenience function to get the singleton instance
def get_processed_items_manager() -> ProcessedItemsManager:
    """Get the singleton ProcessedItemsManager instance."""
    return ProcessedItemsManager()
