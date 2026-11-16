"""Tests for subtitle encoding detection, conversion safety, and defaults."""

import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main"))
)

import cli  # noqa: E402
import utils  # noqa: E402
from constants import DEFAULT_OPTIONS  # noqa: E402


class TestSubtitleEncoding(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        utils._locale_cache = "en_US"

    def tearDown(self):
        utils._locale_cache = None
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_default_output_encoding_is_utf8_with_bom_recommended(self):
        self.assertEqual(DEFAULT_OPTIONS["output_subtitle_encoding"], "utf_8_sig")
        encodings = utils.get_available_encodings()
        self.assertEqual(encodings[0][0], "utf_8_sig")
        self.assertIn("UTF-8 with BOM", encodings[0][1])
        self.assertIn("Recommended", encodings[0][1])

        utils._locale_cache = "tr_TR"
        tr_encodings = utils.get_available_encodings()
        self.assertEqual(tr_encodings[0][0], "utf_8_sig")
        self.assertIn("Önerilen", tr_encodings[0][1])

    def test_detect_encoding_turkish_cp1254_without_cchardet(self):
        srt_path = os.path.join(self.temp_dir, "turkish_cp1254.srt")
        sample = (
            "1\n00:00:01,000 --> 00:00:03,000\n"
            "Seni eve bırakayım mı? Teşekkürler, çok sağ ol.\n\n"
            "2\n00:00:04,000 --> 00:00:06,000\n"
            "Evet, okuldan eve döndüğümde yağmur yağıyordu.\n\n"
            "3\n00:00:07,000 --> 00:00:09,000\n"
            "Görüşürüz, iyi akşamlar.\n"
        )
        with open(srt_path, "wb") as f:
            f.write(sample.encode("cp1254"))

        with patch.object(utils, "cchardet", None):
            detected = utils.detect_encoding(srt_path)

        self.assertIn(detected, ("cp1254", "windows-1254", "iso-8859-9"))

    def test_detect_encoding_preserves_genuine_windows_1252(self):
        srt_path = os.path.join(self.temp_dir, "english_cp1252.srt")
        sample = (
            "1\n00:00:01,000 --> 00:00:03,000\n"
            "“Hello,” he said — it’s a café naïve résumé.\n"
        )
        with open(srt_path, "wb") as f:
            f.write(sample.encode("cp1252"))

        detected = utils.detect_encoding(srt_path)
        self.assertIn(detected, ("windows-1252", "cp1252"))

    def test_detect_encoding_identifies_utf8_bom(self):
        srt_path = os.path.join(self.temp_dir, "bom.srt")
        with open(srt_path, "w", encoding="utf-8-sig") as f:
            f.write("1\n00:00:01,000 --> 00:00:03,000\nSeni eve bırakayım mı?\n")

        self.assertEqual(utils.detect_encoding(srt_path), "utf-8-sig")

    def test_match_subtitle_encoding_does_not_replace_unencodable_chars_with_question_marks(self):
        in_path = os.path.join(self.temp_dir, "input.srt")
        out_path = os.path.join(self.temp_dir, "output.srt")
        turkish_text = "1\n00:00:01,000 --> 00:00:03,000\nSeni eve bırakayım mı?\n"

        with open(in_path, "w", encoding="cp1252") as f:
            f.write("1\n00:00:01,000 --> 00:00:03,000\nHello world\n")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(turkish_text)

        result = utils.match_subtitle_encoding(in_path, out_path)
        self.assertFalse(result)

        with open(out_path, "r", encoding="utf-8") as f:
            preserved = f.read()
        self.assertEqual(preserved, turkish_text)
        self.assertNotIn("b?rakay?m", preserved)

    def test_match_subtitle_encoding_converts_cp1254_to_utf8_bom_without_duplicate_bom(self):
        in_path = os.path.join(self.temp_dir, "in_cp1254.srt")
        out_path = os.path.join(self.temp_dir, "out.srt")
        turkish_text = "1\n00:00:01,000 --> 00:00:03,000\nSeni eve bırakayım mı?\n"

        with open(in_path, "wb") as f:
            f.write(turkish_text.encode("cp1254"))
        with open(out_path, "wb") as f:
            f.write(turkish_text.encode("cp1254"))

        self.assertTrue(utils.match_subtitle_encoding(in_path, out_path, None, "utf_8_sig"))
        with open(out_path, "rb") as f:
            raw = f.read()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf\xef\xbb\xbf"))
        self.assertEqual(raw.decode("utf-8-sig").replace("\r\n", "\n"), turkish_text)

        # Running again when already utf-8-sig must be a no-op with single BOM
        self.assertTrue(utils.match_subtitle_encoding(in_path, out_path, None, "utf_8_sig"))
        with open(out_path, "rb") as f:
            raw_again = f.read()
        self.assertFalse(raw_again.startswith(b"\xef\xbb\xbf\xef\xbb\xbf"))

    def test_cli_apply_output_encoding_uses_utf8_sig_by_default(self):
        in_path = os.path.join(self.temp_dir, "in.srt")
        out_path = os.path.join(self.temp_dir, "out.srt")
        turkish_text = "1\n00:00:01,000 --> 00:00:03,000\nSeni eve bırakayım mı?\n"

        with open(in_path, "wb") as f:
            f.write(turkish_text.encode("cp1254"))
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(turkish_text)

        cli._apply_output_encoding(in_path, out_path, {})
        with open(out_path, "rb") as f:
            raw = f.read()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(raw.decode("utf-8-sig").replace("\r\n", "\n"), turkish_text)

    def test_detect_encoding_short_utf8_across_global_scripts(self):
        for name, text in (
            ("zh", "1\n00:00:01,000 --> 00:00:02,000\n你好吗\n"),
            ("ja", "1\n00:00:01,000 --> 00:00:02,000\nこんにちは\n"),
            ("ko", "1\n00:00:01,000 --> 00:00:02,000\n안녕하세요\n"),
            ("ar", "1\n00:00:01,000 --> 00:00:02,000\nمرحبا\n"),
            ("hi", "1\n00:00:01,000 --> 00:00:02,000\nनमस्ते\n"),
            ("tr", "1\n00:00:01,000 --> 00:00:02,000\nSeni eve bırakayım mı?\n"),
            ("emoji", "1\n00:00:01,000 --> 00:00:02,000\n🎵 Müzik\n"),
        ):
            path = os.path.join(self.temp_dir, f"short_{name}.srt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            self.assertEqual(utils.detect_encoding(path), "utf-8", msg=name)

    def test_detect_encoding_utf16_le_without_bom_and_thai_cp874(self):
        utf16_path = os.path.join(self.temp_dir, "utf16le_nobom.srt")
        with open(utf16_path, "wb") as f:
            f.write("1\n00:00:01,000 --> 00:00:02,000\nHello world\n".encode("utf-16-le"))
        self.assertEqual(utils._canonical_encoding(utils.detect_encoding(utf16_path)), "utf-16-le")

        thai_path = os.path.join(self.temp_dir, "thai_cp874.srt")
        thai_sample = (
            "1\n00:00:01,000 --> 00:00:04,000\nสวัสดีครับ สบายดีไหมครับ “ขอบคุณ”\n" * 3
        )
        with open(thai_path, "wb") as f:
            f.write(thai_sample.encode("cp874"))
        self.assertEqual(utils.detect_encoding(thai_path), "cp874")

    def test_detect_encoding_french_cp1252_not_misdetected_as_johab(self):
        fr_path = os.path.join(self.temp_dir, "fr_cp1252.srt")
        fr_sample = (
            "1\n00:00:01,000 --> 00:00:04,000\n"
            "Bonjour ! Ça va bien ? Je peux te raccompagner chez toi ce soir ?\n"
        ) * 5
        with open(fr_path, "wb") as f:
            f.write(fr_sample.encode("cp1252"))
        detected = utils.detect_encoding(fr_path)
        self.assertNotEqual(detected, "johab")
        # Decoded text must preserve French 'Ça' without turning it into Hangul
        with open(fr_path, "r", encoding=detected) as f:
            self.assertIn("Ça va bien", f.read())

    def test_find_closest_encoding_maps_korean_thai_and_utf8_bom_for_alass(self):
        self.assertEqual(utils.find_closest_encoding("cp949"), "windows-949")
        self.assertEqual(utils.find_closest_encoding("uhc"), "windows-949")
        self.assertEqual(utils.find_closest_encoding("cp874"), "windows-874")
        self.assertEqual(utils.find_closest_encoding("utf-8-sig"), "utf-8")
        self.assertEqual(utils.find_closest_encoding("mac_cyrillic"), "x-mac-cyrillic")

    def test_match_subtitle_encoding_skips_idx_and_binary_sub_and_updates_xml_header(self):
        idx_path = os.path.join(self.temp_dir, "movie.idx")
        idx_bytes = b"# VobSub index file, v7 - do not edit\nsize: 720x480\n"
        with open(idx_path, "wb") as f:
            f.write(idx_bytes)
        self.assertTrue(utils.match_subtitle_encoding(idx_path, idx_path, None, "utf_8_sig"))
        with open(idx_path, "rb") as f:
            self.assertEqual(f.read(), idx_bytes)

        bin_sub_path = os.path.join(self.temp_dir, "movie.sub")
        bin_bytes = b"\x00\x00\x01\xba\x44\x00\x04\x00\x04\x01\x01\x89\xc3\xf8"
        with open(bin_sub_path, "wb") as f:
            f.write(bin_bytes)
        self.assertTrue(utils.match_subtitle_encoding(idx_path, bin_sub_path, None, "utf_8_sig"))
        with open(bin_sub_path, "rb") as f:
            self.assertEqual(f.read(), bin_bytes)

        ttml_path = os.path.join(self.temp_dir, "sample.ttml")
        ttml_content = (
            '<?xml version="1.0" encoding="ISO-8859-1"?>\n'
            "<tt><body><div><p begin='00:00:01.000' end='00:00:02.000'>Café</p></div></body></tt>\n"
        )
        with open(ttml_path, "wb") as f:
            f.write(ttml_content.encode("iso-8859-1"))
        self.assertTrue(utils.match_subtitle_encoding(ttml_path, ttml_path, None, "utf_8_sig"))
        with open(ttml_path, "rb") as f:
            raw_ttml = f.read()
        self.assertTrue(raw_ttml.startswith(b"\xef\xbb\xbf"))
        decoded_ttml = raw_ttml.decode("utf-8-sig")
        self.assertIn('encoding="UTF-8"', decoded_ttml)
        self.assertIn("Café", decoded_ttml)


if __name__ == "__main__":
    unittest.main()
