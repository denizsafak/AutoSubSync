"""Batch mode: adding a reference subtitle to an existing subtitle item.

The right-click "add video to this item" flow on a subtitle item used to
restrict the picker to video/audio files. It now also accepts reference
subtitles, so users with an existing subtitle tree can attach a reference
subtitle without leaving batch mode.
"""

import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main")))

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication
except ImportError:  # pragma: no cover - PyQt6 is a runtime dependency
    Qt = None
    QApplication = None


@unittest.skipIf(QApplication is None, "PyQt6 is required for batch tree tests")
class TestAddReferenceToSubtitle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])
        import gui_batch_mode
        import texts

        cls.gbm = gui_batch_mode
        cls.texts = texts

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.subtitle = os.path.join(self.temp_dir, "episode.srt")
        self.reference_subtitle = os.path.join(self.temp_dir, "reference.srt")
        self.reference_video = os.path.join(self.temp_dir, "reference.mkv")
        for path in (self.subtitle, self.reference_subtitle):
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("1\n00:00:01,000 --> 00:00:02,000\nHello\n")
        with open(self.reference_video, "wb") as fh:
            fh.write(b"video")
        self.tree = self.gbm.BatchTreeView(None)

    def tearDown(self):
        self.tree.deleteLater()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _add_subtitle_item(self):
        item = self.gbm.create_tree_widget_item(
            self.subtitle,
            None,
            self.tree.icon_provider,
            item_id=self.tree._get_next_id(),
        )
        self.tree.insertTopLevelItem(0, item)
        return item

    def _run_dialog(self, item, selected_path):
        calls = {}

        def fake_open_filedialog(
            parent, dialog_type, title, file_filter, *args, **kwargs
        ):
            calls["parent"] = parent
            calls["dialog_type"] = dialog_type
            calls["title"] = title
            calls["file_filter"] = file_filter
            return selected_path

        with patch.object(self.gbm, "open_filedialog", side_effect=fake_open_filedialog):
            self.tree.add_video_to_subtitle_dialog(item)
        return calls

    def test_reference_subtitle_is_accepted_as_parent(self):
        item = self._add_subtitle_item()
        calls = self._run_dialog(item, self.reference_subtitle)

        self.assertEqual(
            calls["title"], self.texts.SELECT_VIDEO_OR_SUBTITLE_FILE_TITLE
        )
        self.assertEqual(calls["file_filter"], self.gbm.VIDEO_SUBTITLE_FILTER)
        self.assertIn("*.srt", calls["file_filter"])

        self.assertEqual(self.tree.topLevelItemCount(), 1)
        parent = self.tree.topLevelItem(0)
        self.assertEqual(
            parent.data(0, Qt.ItemDataRole.UserRole), self.reference_subtitle
        )
        self.assertEqual(parent.childCount(), 1)
        self.assertEqual(
            parent.child(0).data(0, Qt.ItemDataRole.UserRole), self.subtitle
        )
        self.assertEqual(
            parent.data(0, self.gbm.BatchTreeView.VALID_STATE_ROLE), "valid"
        )
        self.assertEqual(
            self.tree.get_all_valid_pairs(), [(self.reference_subtitle, self.subtitle)]
        )

    def test_video_reference_is_still_accepted(self):
        item = self._add_subtitle_item()
        self._run_dialog(item, self.reference_video)

        self.assertEqual(self.tree.topLevelItemCount(), 1)
        parent = self.tree.topLevelItem(0)
        self.assertEqual(
            parent.data(0, Qt.ItemDataRole.UserRole), self.reference_video
        )
        self.assertEqual(parent.childCount(), 1)

    def test_unsupported_reference_is_rejected(self):
        item = self._add_subtitle_item()
        bad_path = os.path.join(self.temp_dir, "cover.jpg")
        with open(bad_path, "wb") as fh:
            fh.write(b"image")

        with patch.object(self.gbm.QMessageBox, "warning") as warning:
            self._run_dialog(item, bad_path)

        warning.assert_called_once()
        self.assertEqual(self.tree.topLevelItemCount(), 1)
        unchanged = self.tree.topLevelItem(0)
        self.assertEqual(
            unchanged.data(0, Qt.ItemDataRole.UserRole), self.subtitle
        )
        self.assertEqual(unchanged.childCount(), 0)


if __name__ == "__main__":
    unittest.main()
