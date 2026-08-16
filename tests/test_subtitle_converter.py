import os
import sys
import tempfile
import unittest
import shutil

# Ensure main directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main")))

from subtitle_converter import (
    convert_to_srt,
    format_ass_time,
    convert_ass_to_srt,
    convert_vtt_to_srt,
    convert_sbv_to_srt,
)


class TestSubtitleConverter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_format_ass_time_precision_and_overflows(self):
        # Exact milliseconds
        self.assertEqual(format_ass_time("0:00:01.00"), "00:00:01,000")
        self.assertEqual(format_ass_time("0:00:08.20"), "00:00:08,200")
        self.assertEqual(format_ass_time("0:00:05.50"), "00:00:05,500")
        # Floating point rounding boundary
        self.assertEqual(format_ass_time("1:02:59.99"), "01:02:59,990")
        self.assertEqual(format_ass_time("0:59:59.99"), "00:59:59,990")

    def test_convert_ass_with_formatting_and_styles(self):
        ass_content = """[Script Info]
Title: Sample ASS
ScriptType: v4.00+

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:05.12,0:01:09.85,Default,,0,0,0,,Line 1 with {i}italics{/i} and {b}bold{/b}
Dialogue: 0,0:01:10.00,0:01:14.25,Default,,0,0,0,,Line 2 standard text
Dialogue: 0,0:01:15.00,0:01:18.00,Default,,0,0,0,,Line 3\\Nwith line break
"""
        ass_file = os.path.join(self.temp_dir, "test.ass")
        with open(ass_file, "w", encoding="utf-8") as f:
            f.write(ass_content)

        out_srt = os.path.join(self.temp_dir, "test.srt")
        convert_ass_to_srt(ass_file, out_srt)

        self.assertTrue(os.path.exists(out_srt))
        with open(out_srt, "r", encoding="utf-8") as f:
            srt_content = f.read()

        self.assertIn("00:01:05,120 --> 00:01:09,850", srt_content)
        self.assertIn("Line 1 with <i>italics</i> and <b>bold</b>", srt_content)
        self.assertIn("00:01:10,000 --> 00:01:14,250", srt_content)
        self.assertIn("Line 2 standard text", srt_content)
        self.assertIn("Line 3\nwith line break", srt_content)

    def test_convert_vtt_to_srt(self):
        vtt_content = """WEBVTT

00:00:01.000 --> 00:00:04.000
Hello VTT world

00:00:05.500 --> 00:00:08.200
Second VTT line
"""
        vtt_file = os.path.join(self.temp_dir, "test.vtt")
        with open(vtt_file, "w", encoding="utf-8") as f:
            f.write(vtt_content)

        out_srt = os.path.join(self.temp_dir, "test_vtt.srt")
        convert_vtt_to_srt(vtt_file, out_srt)

        self.assertTrue(os.path.exists(out_srt))
        with open(out_srt, "r", encoding="utf-8") as f:
            srt_content = f.read()
        self.assertIn("00:00:01,000 --> 00:00:04,000", srt_content)
        self.assertIn("Hello VTT world", srt_content)

    def test_convert_sbv_to_srt(self):
        sbv_content = """0:00:01.000,0:00:04.000
Hello SBV world

0:00:05.500,0:00:08.200
Second SBV line
"""
        sbv_file = os.path.join(self.temp_dir, "test.sbv")
        with open(sbv_file, "w", encoding="utf-8") as f:
            f.write(sbv_content)

        out_srt = os.path.join(self.temp_dir, "test_sbv.srt")
        convert_sbv_to_srt(sbv_file, out_srt)

        self.assertTrue(os.path.exists(out_srt))
        with open(out_srt, "r", encoding="utf-8") as f:
            srt_content = f.read()
        self.assertIn("00:00:01,000 --> 00:00:04,000", srt_content)
        self.assertIn("Hello SBV world", srt_content)

    def test_convert_to_srt_wrapper(self):
        ass_file = os.path.join(self.temp_dir, "test_wrapper.ass")
        with open(ass_file, "w", encoding="utf-8") as f:
            f.write("""[Script Info]
ScriptType: v4.00+
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:02.00,Default,,0,0,0,,Wrapper test
""")
        converted, msgs = convert_to_srt(ass_file, self.temp_dir)
        self.assertIsNotNone(converted)
        self.assertTrue(os.path.exists(converted))
        self.assertTrue(converted.endswith(".srt"))


if __name__ == "__main__":
    unittest.main()
