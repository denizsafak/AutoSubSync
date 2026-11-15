"""Batch pairing of videos and subtitles (main/pairing.py)."""

import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main"))
)

from pairing import pair_paths  # noqa: E402


class TestPairPaths(unittest.TestCase):
    def test_episode_number_is_not_a_language_tag(self):
        pairs, _, _ = pair_paths(
            ["Show_01.mkv", "Show_02.mkv", "Show_03.mkv"],
            ["Show_02.srt", "Show_03.srt"],
        )
        self.assertEqual(
            sorted(pairs),
            [("Show_02.mkv", "Show_02.srt"), ("Show_03.mkv", "Show_03.srt")],
        )

    def test_language_tag_is_still_stripped(self):
        pairs, _, _ = pair_paths(["Show.S01E02.mkv"], ["Show.S01E02.en.srt"])
        self.assertEqual(pairs, [("Show.S01E02.mkv", "Show.S01E02.en.srt")])


if __name__ == "__main__":
    unittest.main()
