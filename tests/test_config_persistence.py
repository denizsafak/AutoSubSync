import os
import sys
import tempfile
import unittest
import json
import shutil
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main")))

import utils
from constants import (
    AUTOMATIC_SAVE_MAP,
    MANUAL_SAVE_MAP,
    DEFAULT_OPTIONS,
    SYNC_TOOLS,
    TranslationDict,
)


class TestConfigPersistence(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "config.json")
        utils._config_cache = None
        utils._locale_cache = None

    def tearDown(self):
        utils._config_cache = None
        utils._locale_cache = None
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_translation_dict_equality_and_hash_across_locales(self):
        translations = {
            "en_US": "Save next to video",
            "tr_TR": "Videonun yanına kaydet",
            "es_ES": "Guardar junto al vídeo",
            "zh_CN": "保存在视频旁边",
        }
        td = TranslationDict(translations)

        # Default locale (en_US)
        utils._locale_cache = "en_US"
        self.assertEqual(str(td), "Save next to video")
        self.assertEqual(td, "Save next to video")
        self.assertEqual(hash(td), hash("Save next to video"))

        # Inverted mapping dictionary lookup with Turkish
        utils._locale_cache = "tr_TR"
        self.assertEqual(str(td), "Videonun yanına kaydet")
        self.assertEqual(td, "Videonun yanına kaydet")
        self.assertEqual(hash(td), hash("Videonun yanına kaydet"))

        mapping = {td: "save_next_to_video"}
        self.assertEqual(mapping.get("Videonun yanına kaydet"), "save_next_to_video")

        # Spanish
        utils._locale_cache = "es_ES"
        self.assertEqual(str(td), "Guardar junto al vídeo")
        self.assertEqual(td, "Guardar junto al vídeo")
        self.assertEqual(hash(td), hash("Guardar junto al vídeo"))

        mapping_es = {td: "save_next_to_video"}
        self.assertEqual(mapping_es.get("Guardar junto al vídeo"), "save_next_to_video")

    def test_automatic_save_map_inversion_lookup(self):
        for loc in ["en_US", "tr_TR", "es_ES", "ru_RU", "ja_JP", "zh_CN"]:
            utils._locale_cache = loc
            save_map = {str(v): k for k, v in AUTOMATIC_SAVE_MAP.items()}
            for internal_key, trans in AUTOMATIC_SAVE_MAP.items():
                display_str = str(trans)
                self.assertEqual(
                    save_map.get(display_str),
                    internal_key,
                    f"Failed lookup for {internal_key} in locale {loc}",
                )

    def test_manual_save_map_inversion_lookup(self):
        for loc in ["en_US", "tr_TR", "es_ES", "de_DE", "fr_FR"]:
            utils._locale_cache = loc
            save_map = {str(v): k for k, v in MANUAL_SAVE_MAP.items()}
            for internal_key, trans in MANUAL_SAVE_MAP.items():
                display_str = str(trans)
                self.assertEqual(
                    save_map.get(display_str),
                    internal_key,
                    f"Failed manual lookup for {internal_key} in locale {loc}",
                )

    def test_handle_save_location_dropdown_with_current_data(self):
        mock_obj = MagicMock()
        mock_obj.config = {"remember_changes": True}
        mock_label = MagicMock()

        mock_dropdown = MagicMock()
        mock_dropdown.currentData.return_value = "save_next_to_video"
        mock_dropdown.currentText.return_value = "Videonun yanına kaydet"

        with patch("utils.save_config"):
            utils.handle_save_location_dropdown(
                mock_obj,
                mock_dropdown,
                {str(v): k for k, v in AUTOMATIC_SAVE_MAP.items()},
                "automatic_save_location",
                "automatic_save_folder",
                mock_label,
                DEFAULT_OPTIONS["automatic_save_location"],
            )

        self.assertEqual(mock_obj.config["automatic_save_location"], "save_next_to_video")

    def test_handle_save_location_dropdown_fallback_string_match(self):
        mock_obj = MagicMock()
        mock_obj.config = {"remember_changes": True}
        mock_label = MagicMock()

        utils._locale_cache = "tr_TR"
        mock_dropdown = MagicMock()
        mock_dropdown.currentData.return_value = None
        mock_dropdown.currentText.return_value = str(AUTOMATIC_SAVE_MAP["save_to_desktop"])

        with patch("utils.save_config"):
            utils.handle_save_location_dropdown(
                mock_obj,
                mock_dropdown,
                {str(v): k for k, v in AUTOMATIC_SAVE_MAP.items()},
                "automatic_save_location",
                "automatic_save_folder",
                mock_label,
                DEFAULT_OPTIONS["automatic_save_location"],
            )

        self.assertEqual(mock_obj.config["automatic_save_location"], "save_to_desktop")


if __name__ == "__main__":
    unittest.main()
