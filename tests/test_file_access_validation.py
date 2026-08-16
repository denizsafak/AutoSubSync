import os
import sys
import tempfile
import unittest
import shutil
from unittest.mock import MagicMock, patch

# Ensure main directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main")))

import texts
from constants import DEFAULT_OPTIONS
from utils import check_file_readable, check_file_writable
import sync_core
import sync_auto


class TestFileAccessValidation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.video_path = os.path.join(self.temp_dir, "test_video.mp4")
        with open(self.video_path, "wb") as f:
            f.write(b"dummy video content")

        self.sub_path = os.path.join(self.temp_dir, "test_subtitle.srt")
        with open(self.sub_path, "w", encoding="utf-8") as f:
            f.write("1\n00:00:01,000 --> 00:00:02,000\nHello\n")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_check_file_readable_valid(self):
        ok, err = check_file_readable(self.sub_path)
        self.assertTrue(ok)
        self.assertEqual(err, "")

    def test_check_file_readable_nonexistent(self):
        nonexistent = os.path.join(self.temp_dir, "nonexistent.srt")
        ok, err = check_file_readable(nonexistent)
        self.assertFalse(ok)
        self.assertIn("does not exist", err.lower())

    def test_check_file_readable_empty_path(self):
        ok, err = check_file_readable("")
        self.assertFalse(ok)
        self.assertIn("No file path provided", err)

    def test_check_file_readable_permission_denied(self):
        with patch("builtins.open", side_effect=PermissionError("Permission denied: file is locked by another process")):
            ok, err = check_file_readable(self.sub_path)
            self.assertFalse(ok)
            self.assertIn("Permission denied", err)

    def test_check_file_writable_valid_existing(self):
        ok, err = check_file_writable(self.sub_path)
        self.assertTrue(ok)
        self.assertEqual(err, "")
        # Verify content was preserved
        with open(self.sub_path, "r", encoding="utf-8") as f:
            self.assertIn("Hello", f.read())

    def test_check_file_writable_new_file_in_existing_dir(self):
        new_file = os.path.join(self.temp_dir, "new_sub.srt")
        ok, err = check_file_writable(new_file)
        self.assertTrue(ok)
        self.assertEqual(err, "")
        # Temp check file should be removed
        self.assertFalse(os.path.exists(new_file))

    def test_check_file_writable_permission_denied(self):
        ro_dir = os.path.join(self.temp_dir, "readonly_dir")
        os.makedirs(ro_dir, exist_ok=True)
        out_file = os.path.join(ro_dir, "out.srt")
        os.chmod(ro_dir, 0o444)
        try:
            ok, err = check_file_writable(out_file)
            self.assertFalse(ok)
            self.assertTrue(len(err) > 0)
        finally:
            os.chmod(ro_dir, 0o777)

    def test_sync_core_reports_error_when_subtitle_is_unreadable_or_locked(self):
        """Verify run_sync surfaces COULD_NOT_ACCESS_OR_WRITE_SUBTITLE with path and exception."""
        config = dict(DEFAULT_OPTIONS)
        error_logs = []
        callbacks = sync_core.SyncCallbacks(
            on_error=lambda msg: error_logs.append(msg)
        )

        with patch("sync_core.check_file_readable", side_effect=[(True, ""), (False, "Permission denied: file locked")]):
            result = sync_core.run_sync(
                self.video_path,
                self.sub_path,
                tool="alass",
                config=config,
                callbacks=callbacks,
            )

            self.assertFalse(result.ok)
            self.assertTrue(len(error_logs) > 0)
            self.assertIn("Permission denied: file locked", error_logs[0])
            self.assertIn(self.sub_path, error_logs[0])

    def test_sync_core_reports_error_when_reference_is_unreadable_or_locked(self):
        """Verify run_sync surfaces COULD_NOT_ACCESS_REFERENCE_FILE with path and exception."""
        config = dict(DEFAULT_OPTIONS)
        error_logs = []
        callbacks = sync_core.SyncCallbacks(
            on_error=lambda msg: error_logs.append(msg)
        )

        with patch("sync_core.check_file_readable", return_value=(False, "Permission denied: file locked")):
            result = sync_core.run_sync(
                self.video_path,
                self.sub_path,
                tool="alass",
                config=config,
                callbacks=callbacks,
            )

            self.assertFalse(result.ok)
            self.assertTrue(len(error_logs) > 0)
            self.assertIn("Permission denied: file locked", error_logs[0])
            self.assertIn(self.video_path, error_logs[0])

    def test_sync_core_reports_error_when_output_is_unwritable(self):
        """Verify run_sync surfaces COULD_NOT_WRITE_OUTPUT_FILE with path and exception."""
        config = dict(DEFAULT_OPTIONS)
        error_logs = []
        callbacks = sync_core.SyncCallbacks(
            on_error=lambda msg: error_logs.append(msg)
        )

        with patch("sync_core.check_file_writable", return_value=(False, "Permission denied: readonly destination")):
            result = sync_core.run_sync(
                self.video_path,
                self.sub_path,
                tool="alass",
                output=os.path.join(self.temp_dir, "unwritable_out.srt"),
                config=config,
                callbacks=callbacks,
            )

            self.assertFalse(result.ok)
            self.assertTrue(len(error_logs) > 0)
            self.assertIn("Permission denied: readonly destination", error_logs[0])

    def test_alass_rename_locked_file_logs_error_without_dialog(self):
        """Verify _ensure_alass_safe_paths logs red error in log window without popup dialogs on locked file rename failure."""
        app_mock = MagicMock()
        app_mock.config = {
            "auto_rename_bracket_paths": True,
            "disable_alass_rename_prompt": False,
        }

        with patch("sync_auto._has_brackets", return_value=True), \
             patch("sync_auto._rename_path_components", side_effect=PermissionError("File locked by Subtitle Edit")), \
             patch("sync_auto.append_log") as mock_append_log:

            success, ref, sub = sync_auto._ensure_alass_safe_paths(
                app_mock,
                os.path.join(self.temp_dir, "[Locked] Video.mp4"),
                os.path.join(self.temp_dir, "[Locked] Subtitle.srt"),
            )

            self.assertFalse(success)
            # Verify red error was logged
            self.assertTrue(mock_append_log.called)
            logged_error = str(mock_append_log.call_args[0][1])
            self.assertIn("File locked by Subtitle Edit", logged_error)


if __name__ == "__main__":
    unittest.main()
