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

    def test_atomic_save_and_load_config(self):
        with patch("utils.get_user_config_path", return_value=self.config_file):
            test_data = {"sync_tool": "lapse", "theme": "dark", "lapse_mode": "voice"}
            utils.save_config(test_data)
            self.assertTrue(os.path.exists(self.config_file))

            utils._config_cache = None
            loaded = utils.load_config()
            self.assertEqual(loaded, test_data)

    def test_save_config_creates_backup(self):
        with patch("utils.get_user_config_path", return_value=self.config_file):
            initial_data = {"sync_tool": "alass", "theme": "light"}
            utils.save_config(initial_data)

            # Second save should create .bak containing initial_data
            updated_data = {"sync_tool": "lapse", "theme": "dark"}
            utils.save_config(updated_data)

            bak_file = f"{self.config_file}.bak"
            self.assertTrue(os.path.exists(bak_file))
            with open(bak_file, "r", encoding="utf-8") as f:
                bak_data = json.load(f)
            self.assertEqual(bak_data, initial_data)

    def test_load_config_corrupted_recovers_from_backup(self):
        with patch("utils.get_user_config_path", return_value=self.config_file):
            good_data = {"sync_tool": "lapse", "remember_changes": True, "custom_suffix": "_synced"}
            utils.save_config(good_data)
            utils.save_config({**good_data, "custom_suffix": "_new"})  # Creates .bak

            # Now corrupt the main config file (e.g. simulate crash leaving 0 bytes or half-written JSON)
            with open(self.config_file, "w", encoding="utf-8") as f:
                f.write("{corrupt json...")

            utils._config_cache = None
            loaded = utils.load_config()
            # Should have recovered from the backup
            self.assertEqual(loaded.get("sync_tool"), "lapse")
            self.assertEqual(loaded.get("remember_changes"), True)

    def test_load_config_empty_file_recovers_from_backup(self):
        with patch("utils.get_user_config_path", return_value=self.config_file):
            good_data = {"sync_tool": "alass", "theme": "dark"}
            utils.save_config(good_data)
            utils.save_config({**good_data, "theme": "light"})  # Creates .bak

            # Truncate main config file to 0 bytes
            with open(self.config_file, "w", encoding="utf-8") as f:
                f.write("")

            utils._config_cache = None
            loaded = utils.load_config()
            self.assertEqual(loaded.get("sync_tool"), "alass")

    def test_load_config_corrupted_without_backup_preserves_corrupt_file(self):
        with patch("utils.get_user_config_path", return_value=self.config_file):
            with open(self.config_file, "w", encoding="utf-8") as f:
                f.write("invalid json contents")

            utils._config_cache = None
            loaded = utils.load_config()
            self.assertEqual(loaded, {})

            # Verify a .corrupt file was preserved
            corrupt_files = [f for f in os.listdir(self.temp_dir) if ".corrupt." in f]
            self.assertTrue(len(corrupt_files) > 0)

    def test_save_config_non_serializable_does_not_corrupt_existing_file(self):
        with patch("utils.get_user_config_path", return_value=self.config_file):
            good_data = {"sync_tool": "ffsubsync"}
            utils.save_config(good_data)

            # Try saving an un-serializable object (e.g. a set)
            bad_data = {"sync_tool": "ffsubsync", "bad_value": {1, 2, 3}}
            utils.save_config(bad_data)

            # Main config should still be intact with good_data
            utils._config_cache = None
            loaded = utils.load_config()
            self.assertEqual(loaded, good_data)

    def test_default_options_contains_sync_tool_options(self):
        self.assertIn("lapse_mode", DEFAULT_OPTIONS)
        self.assertIn("lapse_split_penalty", DEFAULT_OPTIONS)
        self.assertIn("alass_split_penalty", DEFAULT_OPTIONS)
        self.assertIn("ffsubsync_dont_fix_framerate", DEFAULT_OPTIONS)
        self.assertEqual(DEFAULT_OPTIONS["lapse_split_penalty"], 6)
        self.assertEqual(DEFAULT_OPTIONS["alass_split_penalty"], 7)
        self.assertEqual(DEFAULT_OPTIONS["lapse_mode"], "auto")


if __name__ == "__main__":
    unittest.main()
