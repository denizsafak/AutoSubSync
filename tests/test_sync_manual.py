"""Manual shift of subtitle timings (main/sync_manual.py)."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main"))
)

from sync_manual import shift_subtitle  # noqa: E402


class TestShiftSubtitle(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_shift_vtt_cues_without_hours(self):
        vtt_file = os.path.join(self.temp_dir, "short.vtt")
        with open(vtt_file, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n00:01.000 --> 00:04.000\nHello\n")
        out_file = os.path.join(self.temp_dir, "shifted.vtt")

        shift_subtitle(vtt_file, 2000, out_file)

        with open(out_file, "r", encoding="utf-8") as f:
            self.assertIn("00:00:03.000 --> 00:00:06.000", f.read())


if __name__ == "__main__":
    unittest.main()
