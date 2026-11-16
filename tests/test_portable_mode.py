import io
import json
import os
import platform
import shutil
import sqlite3
import stat
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_DIR = os.path.join(PROJECT_ROOT, "main")
if MAIN_DIR not in sys.path:
    sys.path.insert(0, MAIN_DIR)

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import QApplication, QMessageBox

import constants
import texts
import utils
from resources import lapse_download, whisper_download


class TestPortableModeTranslations(unittest.TestCase):
    PORTABLE_KEYS = [
        "PORTABLE_MODE",
        "PORTABLE_MODE_ENABLE_CONFIRM",
        "PORTABLE_MODE_DISABLE_CONFIRM",
        "PORTABLE_MODE_TARGET_EXISTS_DISABLE",
        "PORTABLE_MODE_OVERWRITE_AND_MOVE",
        "PORTABLE_MODE_KEEP_SYSTEM_DATA",
        "PORTABLE_MODE_TARGET_EXISTS_ENABLE",
        "PORTABLE_MODE_USE_EXISTING_PORTABLE",
        "PORTABLE_MODE_MOVE_TOOLS_CHECKBOX",
        "PORTABLE_MODE_MIGRATING",
        "PORTABLE_MODE_MIGRATION_FAILED",
        "PORTABLE_MODE_BUSY",
        "PORTABLE_MODE_UNSUPPORTED_NOT_FROZEN",
        "PORTABLE_MODE_UNSUPPORTED_READONLY",
        "PORTABLE_MODE_UNSUPPORTED_TRANSLOCATED",
        "PORTABLE_MODE_UNSUPPORTED_SYSTEM_INSTALL",
    ]

    def test_all_languages_present_and_formattable(self):
        expected_langs = set(constants.LANGUAGES.values())
        for key in self.PORTABLE_KEYS:
            tdict = getattr(texts, key)
            self.assertEqual(
                set(tdict._translations.keys()),
                expected_langs,
                f"{key} missing/extra languages",
            )
            for lang, val in tdict._translations.items():
                self.assertTrue(val.strip(), f"{key}[{lang}] is empty")
                if "{path}" in tdict._translations["en_US"]:
                    self.assertIn("{path}", val, f"{key}[{lang}] missing {{path}}")
                    val.format(path="/tmp/AutoSubSync_data")
                if "{size}" in tdict._translations["en_US"]:
                    self.assertIn("{size}", val, f"{key}[{lang}] missing {{size}}")
                    val.format(size="142.0 MB")
                if "{error}" in tdict._translations["en_US"]:
                    self.assertIn("{error}", val, f"{key}[{lang}] missing {{error}}")
                    val.format(error="disk full")


class TestPortableModeDetection(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        utils.clear_config_cache()

    def tearDown(self):
        utils.clear_config_cache()
        self.tmpdir.cleanup()

    def test_source_or_pypi_not_frozen_is_unsupported(self):
        with patch.dict(os.environ, {}, clear=False), patch.object(
            sys, "frozen", False, create=True
        ):
            os.environ.pop("APPIMAGE", None)
            # Even if AutoSubSync_data exists next to main.py, source/PyPI must ignore it
            status = utils.get_portable_mode_status()
            self.assertFalse(status["supported"])
            self.assertFalse(status["usable"])
            self.assertFalse(status["active"])
            self.assertEqual(status["reason"], "not_frozen")
            self.assertIsNone(status["base_dir"])
            self.assertIsNone(status["portable_dir"])
            self.assertFalse(utils.is_portable_mode())

    def test_windows_or_linux_frozen_writable_dir(self):
        exe_dir = os.path.join(self.tmpdir.name, "AutoSubSync")
        os.makedirs(exe_dir)
        exe_path = os.path.join(exe_dir, "AutoSubSync.exe")

        with patch.dict(os.environ, {}, clear=False), patch.object(
            sys, "frozen", True, create=True
        ), patch.object(sys, "executable", exe_path), patch(
            "platform.system", return_value="Windows"
        ):
            os.environ.pop("APPIMAGE", None)
            status = utils.get_portable_mode_status()
            self.assertTrue(status["supported"])
            self.assertTrue(status["usable"])
            self.assertFalse(status["active"])
            self.assertEqual(status["reason"], "ok")
            self.assertEqual(status["base_dir"], os.path.realpath(exe_dir))
            self.assertEqual(
                status["portable_dir"],
                os.path.join(os.path.realpath(exe_dir), utils.PORTABLE_DIR_NAME),
            )

            # Creating a regular file named AutoSubSync_data must not activate portable mode
            with open(status["portable_dir"], "w") as f:
                f.write("not a dir")
            self.assertFalse(utils.is_portable_mode())
            os.remove(status["portable_dir"])

            # Creating the directory activates portable mode
            os.makedirs(status["portable_dir"])
            status_on = utils.get_portable_mode_status()
            self.assertTrue(status_on["usable"])
            self.assertTrue(status_on["active"])
            self.assertTrue(utils.is_portable_mode())

    def test_appimage_uses_appimage_parent_directory(self):
        usb_dir = os.path.join(self.tmpdir.name, "usb")
        mount_dir = os.path.join(self.tmpdir.name, "tmp_mount", "usr", "bin")
        os.makedirs(usb_dir)
        os.makedirs(mount_dir)
        appimage_file = os.path.join(usb_dir, "AutoSubSync.AppImage")
        with open(appimage_file, "wb") as f:
            f.write(b"ELF")

        with patch.dict(os.environ, {"APPIMAGE": appimage_file}, clear=False), patch.object(
            sys, "frozen", True, create=True
        ), patch.object(sys, "executable", os.path.join(mount_dir, "AutoSubSync")), patch(
            "platform.system", return_value="Linux"
        ):
            status = utils.get_portable_mode_status()
            self.assertTrue(status["supported"])
            self.assertTrue(status["usable"])
            self.assertFalse(status["active"])
            self.assertEqual(status["base_dir"], os.path.realpath(usb_dir))
            os.makedirs(status["portable_dir"])
            self.assertTrue(utils.is_portable_mode())

    def test_macos_app_bundle_resolves_parent_of_dot_app(self):
        usb_dir = os.path.join(self.tmpdir.name, "mac_usb")
        macos_bin_dir = os.path.join(
            usb_dir, "AutoSubSync.app", "Contents", "MacOS"
        )
        os.makedirs(macos_bin_dir)
        exe_path = os.path.join(macos_bin_dir, "AutoSubSync")

        with patch.dict(os.environ, {}, clear=False), patch.object(
            sys, "frozen", True, create=True
        ), patch.object(sys, "executable", exe_path), patch(
            "platform.system", return_value="Darwin"
        ):
            os.environ.pop("APPIMAGE", None)
            status = utils.get_portable_mode_status()
            self.assertTrue(status["supported"])
            self.assertTrue(status["usable"])
            self.assertEqual(status["base_dir"], os.path.realpath(usb_dir))
            self.assertEqual(
                status["portable_dir"],
                os.path.join(os.path.realpath(usb_dir), utils.PORTABLE_DIR_NAME),
            )

    def test_macos_app_translocation_is_detected_and_disabled(self):
        exe_path = (
            "/private/var/folders/xx/abc/T/AppTranslocation/"
            "1234-5678/d/AutoSubSync.app/Contents/MacOS/AutoSubSync"
        )
        with patch.dict(os.environ, {}, clear=False), patch.object(
            sys, "frozen", True, create=True
        ), patch.object(sys, "executable", exe_path), patch(
            "platform.system", return_value="Darwin"
        ):
            os.environ.pop("APPIMAGE", None)
            status = utils.get_portable_mode_status()
            self.assertFalse(status["supported"])
            self.assertFalse(status["usable"])
            self.assertFalse(status["active"])
            self.assertEqual(status["reason"], "translocated")

    def test_linux_system_install_deb_is_detected_and_disabled(self):
        for exe_path in (
            "/opt/autosubsync/AutoSubSync",
            "/usr/lib/autosubsync/AutoSubSync",
        ):
            with patch.dict(os.environ, {}, clear=False), patch.object(
                sys, "frozen", True, create=True
            ), patch.object(sys, "executable", exe_path), patch(
                "platform.system", return_value="Linux"
            ):
                os.environ.pop("APPIMAGE", None)
                status = utils.get_portable_mode_status()
                self.assertFalse(status["supported"])
                self.assertFalse(status["usable"])
                self.assertFalse(status["active"])
                self.assertEqual(status["reason"], "system_install")

    def test_windows_and_macos_system_install_directories(self):
        with patch.dict(
            os.environ,
            {
                "ProgramFiles": r"C:\Program Files",
                "ProgramFiles(x86)": r"C:\Program Files (x86)",
            },
            clear=False,
        ), patch("platform.system", return_value="Windows"):
            self.assertTrue(
                utils._is_system_install_directory(r"C:\Program Files\AutoSubSync")
            )
            self.assertFalse(utils._is_system_install_directory(r"E:\Portable\AutoSubSync"))

        with patch("platform.system", return_value="Darwin"):
            self.assertTrue(utils._is_system_install_directory("/Applications"))
            self.assertFalse(utils._is_system_install_directory("/Volumes/USB"))

    def test_macos_applications_writable_is_still_rejected_as_system_install(self):
        # On macOS, /Applications is often writable by admin users, yet must not host AutoSubSync_data
        with patch.dict(os.environ, {}, clear=False), patch.object(
            sys, "frozen", True, create=True
        ), patch.object(
            sys, "executable", "/Applications/AutoSubSync.app/Contents/MacOS/AutoSubSync"
        ), patch(
            "platform.system", return_value="Darwin"
        ), patch.object(
            utils, "_is_directory_writable", return_value=True
        ):
            os.environ.pop("APPIMAGE", None)
            status = utils.get_portable_mode_status()
            self.assertFalse(status["supported"])
            self.assertFalse(status["usable"])
            self.assertFalse(status["active"])
            self.assertEqual(status["reason"], "system_install")

    def test_symlinked_portable_binary_resolves_to_target_directory(self):
        real_usb_dir = os.path.join(self.tmpdir.name, "real_usb")
        bin_link_dir = os.path.join(self.tmpdir.name, "user_bin")
        os.makedirs(real_usb_dir)
        os.makedirs(bin_link_dir)
        real_exe = os.path.join(real_usb_dir, "AutoSubSync")
        with open(real_exe, "wb") as f:
            f.write(b"BIN")
        link_exe = os.path.join(bin_link_dir, "AutoSubSync")
        os.symlink(real_exe, link_exe)

        with patch.dict(os.environ, {}, clear=False), patch.object(
            sys, "frozen", True, create=True
        ), patch.object(sys, "executable", link_exe), patch(
            "platform.system", return_value="Linux"
        ):
            os.environ.pop("APPIMAGE", None)
            status = utils.get_portable_mode_status()
            self.assertTrue(status["usable"])
            self.assertEqual(status["base_dir"], os.path.realpath(real_usb_dir))

    def test_unicode_path_supported_across_status_and_config(self):
        unicode_dir = os.path.join(self.tmpdir.name, "USB_ŞÇÖ_日本語")
        os.makedirs(unicode_dir)
        exe_path = os.path.join(unicode_dir, "AutoSubSync")
        with patch.dict(os.environ, {}, clear=False), patch.object(
            sys, "frozen", True, create=True
        ), patch.object(sys, "executable", exe_path), patch(
            "platform.system", return_value="Linux"
        ):
            os.environ.pop("APPIMAGE", None)
            status = utils.get_portable_mode_status()
            self.assertTrue(status["usable"])
            os.makedirs(status["portable_dir"])
            utils.clear_config_cache()
            utils.save_config({"language": "ja_JP"})
            cfg_file = os.path.join(status["portable_dir"], "config.json")
            self.assertTrue(os.path.isfile(cfg_file))

    def test_readonly_directory_is_marked_not_writable(self):
        ro_dir = os.path.join(self.tmpdir.name, "ro_app")
        os.makedirs(ro_dir)
        exe_path = os.path.join(ro_dir, "AutoSubSync")

        with patch.dict(os.environ, {}, clear=False), patch.object(
            sys, "frozen", True, create=True
        ), patch.object(sys, "executable", exe_path), patch(
            "platform.system", return_value="Linux"
        ), patch.object(
            utils, "_is_directory_writable", return_value=False
        ):
            os.environ.pop("APPIMAGE", None)
            status = utils.get_portable_mode_status()
            self.assertTrue(status["supported"])
            self.assertFalse(status["usable"])
            self.assertFalse(status["active"])
            self.assertEqual(status["reason"], "not_writable")


class _PortableEnvMixin:
    def _setup_portable_env(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.usb_dir = os.path.join(self.tmpdir.name, "usb_app")
        self.sys_config_dir = os.path.join(self.tmpdir.name, "sys_config")
        self.sys_data_dir = os.path.join(self.tmpdir.name, "sys_data")
        self.sys_logs_dir = os.path.join(self.tmpdir.name, "sys_logs")
        os.makedirs(self.usb_dir)
        os.makedirs(self.sys_config_dir)
        os.makedirs(self.sys_data_dir)
        os.makedirs(self.sys_logs_dir)
        self.portable_dir = os.path.join(self.usb_dir, utils.PORTABLE_DIR_NAME)
        self.exe_path = os.path.join(self.usb_dir, "AutoSubSync")
        utils.clear_config_cache()

        self._patches = [
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "executable", self.exe_path),
            patch.object(utils, "_is_directory_writable", return_value=True),
            patch.object(utils, "_is_system_install_directory", return_value=False),
            patch.object(
                utils, "get_system_config_dir", return_value=self.sys_config_dir
            ),
            patch.object(utils, "get_system_data_dir", return_value=self.sys_data_dir),
            patch.object(
                utils, "get_system_logs_directory", return_value=self.sys_logs_dir
            ),
            patch.object(
                lapse_download,
                "_default_dist_bin_path",
                return_value=os.path.join(self.sys_data_dir, "lapse"),
            ),
            patch.object(
                whisper_download,
                "_default_dist_bin_path",
                return_value=os.path.join(self.sys_data_dir, "whisper"),
            ),
        ]
        for p in self._patches:
            p.start()

    def _teardown_portable_env(self):
        from processed_items_manager import close_processed_items_manager
        from gui_load_library import close_library_folders_manager

        close_processed_items_manager()
        close_library_folders_manager()
        for p in reversed(self._patches):
            p.stop()
        utils.clear_config_cache()
        self.tmpdir.cleanup()


class TestPortableRoutingAndDownloads(unittest.TestCase, _PortableEnvMixin):
    def setUp(self):
        self._setup_portable_env()

    def tearDown(self):
        self._teardown_portable_env()

    def test_config_db_logs_and_cache_routing(self):
        from processed_items_manager import (
            ProcessedItemsManager,
            close_processed_items_manager,
        )
        from gui_load_library import (
            LibraryFoldersManager,
            close_library_folders_manager,
        )

        # Non-portable routes to system dirs
        self.assertEqual(
            utils.get_user_config_path(),
            os.path.join(self.sys_config_dir, "config.json"),
        )
        self.assertEqual(utils.get_logs_directory(), self.sys_logs_dir)

        # Activate portable mode
        os.makedirs(self.portable_dir)
        utils.clear_config_cache()

        expected_cfg = os.path.join(self.portable_dir, "config.json")
        self.assertEqual(utils.get_user_config_path(), expected_cfg)
        utils.save_config({"language": "tr_TR"})
        self.assertTrue(os.path.isfile(expected_cfg))

        # Logs directory inside portable folder
        expected_logs = os.path.join(self.portable_dir, "logs")
        self.assertEqual(utils.get_logs_directory(), expected_logs)
        self.assertTrue(os.path.isdir(expected_logs))

        # SQLite managers follow portable dir cleanly
        pim = ProcessedItemsManager()
        lfm = LibraryFoldersManager()
        self.assertEqual(
            os.path.realpath(pim.get_db_path()),
            os.path.realpath(os.path.join(self.portable_dir, "processed_items.db")),
        )
        self.assertEqual(
            os.path.realpath(lfm._get_db_path()),
            os.path.realpath(os.path.join(self.portable_dir, "library_folders.db")),
        )
        close_processed_items_manager()
        close_library_folders_manager()

        # LAPSE cache directory routing
        self.assertEqual(
            utils.get_lapse_cache_directories(),
            [utils.get_portable_lapse_cache_dir()],
        )

    def test_create_process_sets_portable_lapse_cache_env(self):
        os.makedirs(self.portable_dir)
        utils.clear_config_cache()

        captured = {}

        class _DummyProc:
            pid = 1234

        def fake_popen(cmd, **kwargs):
            captured["env"] = kwargs.get("env")
            return _DummyProc()

        with patch("subprocess.Popen", side_effect=fake_popen):
            utils.create_process([os.path.join(self.usb_dir, "lapse"), "--version"])

        self.assertEqual(
            captured["env"]["LAPSE_CACHE"], utils.get_portable_lapse_cache_dir()
        )

    def test_downloaders_route_to_portable_namespaced_and_shared_dirs(self):
        os.makedirs(self.portable_dir)
        tag = utils._get_portable_platform_tag()

        self.assertEqual(
            lapse_download.get_dist_bin_path(),
            os.path.join(self.portable_dir, "bin", "lapse", tag),
        )
        self.assertEqual(
            whisper_download.get_dist_bin_path(),
            os.path.join(self.portable_dir, "bin", "whisper", tag),
        )
        self.assertEqual(
            whisper_download.get_model_dir(),
            os.path.join(self.portable_dir, "bin", "whisper"),
        )

        # Monkeypatching DIST_BIN_PATH in tests still takes precedence
        custom_override = os.path.join(self.tmpdir.name, "test_override")
        with patch.object(lapse_download, "DIST_BIN_PATH", custom_override), patch.object(
            whisper_download, "DIST_BIN_PATH", custom_override
        ):
            self.assertEqual(lapse_download.get_dist_bin_path(), custom_override)
            self.assertEqual(whisper_download.get_dist_bin_path(), custom_override)
            self.assertEqual(whisper_download.get_model_dir(), custom_override)

    def test_lapse_download_creates_missing_portable_parents(self):
        os.makedirs(self.portable_dir)
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            payload = b"#!/bin/sh\necho 2.6.0\n"
            info = tarfile.TarInfo(name=lapse_download.BINARY_NAME)
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
        archive_bytes = buf.getvalue()

        mock_resp = MagicMock()
        mock_resp.headers = {"content-length": str(len(archive_bytes))}
        mock_resp.content = archive_bytes
        mock_resp.iter_content.return_value = [archive_bytes]
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_resp), patch.object(
            lapse_download, "get_archive_filename", return_value="lapse-linux.tar.gz"
        ):
            dest = lapse_download.download()

        self.assertTrue(os.path.isfile(dest))
        self.assertTrue(
            dest.startswith(os.path.join(self.portable_dir, "bin", "lapse"))
        )

    def test_whisper_cli_extract_symlink_fallback_for_fat_usb(self):
        os.makedirs(self.portable_dir)
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            # Multi-hop symlinks (appeared BEFORE target file, like real tarballs)
            s1 = tarfile.TarInfo(name="lib/libwhisper.so")
            s1.type = tarfile.SYMTYPE
            s1.linkname = "libwhisper.so.1"
            tar.addfile(s1)

            s2 = tarfile.TarInfo(name="lib/libwhisper.so.1")
            s2.type = tarfile.SYMTYPE
            s2.linkname = "libwhisper.so.1.8.0"
            tar.addfile(s2)

            lib_data = b"SHAREDLIB"
            lib_info = tarfile.TarInfo(name="lib/libwhisper.so.1.8.0")
            lib_info.size = len(lib_data)
            tar.addfile(lib_info, io.BytesIO(lib_data))

            cli_data = b"CLI_BINARY"
            cli_info = tarfile.TarInfo(name=f"bin/{whisper_download.BINARY_NAME}")
            cli_info.size = len(cli_data)
            tar.addfile(cli_info, io.BytesIO(cli_data))

        archive_bytes = buf.getvalue()
        releases_payload = [
            {
                "assets": [
                    {
                        "name": "whisper-linux-x86_64.tar.gz",
                        "browser_download_url": "https://example.invalid/whisper.tar.gz",
                    }
                ]
            }
        ]

        api_resp = MagicMock()
        api_resp.json.return_value = releases_payload
        api_resp.raise_for_status = MagicMock()
        api_resp.__enter__.return_value = api_resp

        dl_resp = MagicMock()
        dl_resp.headers = {"content-length": str(len(archive_bytes))}
        dl_resp.content = archive_bytes
        dl_resp.iter_content.return_value = [archive_bytes]
        dl_resp.raise_for_status = MagicMock()
        dl_resp.__enter__.return_value = dl_resp

        with patch("platform.system", return_value="Linux"), patch.object(
            whisper_download,
            "get_archive_filename",
            return_value="whisper-linux-x86_64.tar.gz",
        ), patch(
            "requests.get", side_effect=[api_resp, dl_resp]
        ), patch(
            "os.symlink", side_effect=OSError("Operation not permitted (FAT32)")
        ):
            cli_path = whisper_download.download_cli()

        bin_dir = whisper_download.get_dist_bin_path()
        self.assertEqual(cli_path, os.path.join(bin_dir, whisper_download.BINARY_NAME))
        self.assertTrue(os.path.isfile(cli_path))
        # Both symlink targets should have been materialized as real copies
        for libname in ("libwhisper.so", "libwhisper.so.1", "libwhisper.so.1.8.0"):
            fpath = os.path.join(bin_dir, libname)
            self.assertTrue(os.path.isfile(fpath), f"Missing copied lib {libname}")
            self.assertFalse(os.path.islink(fpath))
            with open(fpath, "rb") as f:
                self.assertEqual(f.read(), b"SHAREDLIB")

    def test_whisper_model_download_shared_across_os_in_portable_mode(self):
        os.makedirs(self.portable_dir)
        # Pre-populate a Windows whisper binary + shared ggml model on USB
        win_bin_dir = os.path.join(self.portable_dir, "bin", "whisper", "windows-amd64")
        os.makedirs(win_bin_dir, exist_ok=True)
        with open(os.path.join(win_bin_dir, "whisper-cli.exe"), "wb") as f:
            f.write(b"WIN_EXE")

        model_bytes = b"GGML_MODEL_PAYLOAD"
        dl_resp = MagicMock()
        dl_resp.headers = {"content-length": str(len(model_bytes))}
        dl_resp.iter_content.return_value = [model_bytes]
        dl_resp.raise_for_status = MagicMock()
        dl_resp.__enter__.return_value = dl_resp

        with patch("requests.get", return_value=dl_resp):
            model_path = whisper_download.download_model("ggml-base.bin")

        self.assertEqual(
            model_path,
            os.path.join(self.portable_dir, "bin", "whisper", "ggml-base.bin"),
        )
        self.assertTrue(os.path.isfile(model_path))

        # Switching to Linux on the same USB stick reuses shared ggml-base.bin
        # while scoping whisper-cli lookup to linux-amd64
        with patch("platform.system", return_value="Linux"), patch(
            "platform.machine", return_value="x86_64"
        ), patch("shutil.which", return_value=None):
            self.assertEqual(whisper_download.installed_model("ggml-base.bin"), model_path)
            self.assertEqual(
                whisper_download.get_dist_bin_path(),
                os.path.join(self.portable_dir, "bin", "whisper", "linux-amd64"),
            )
            self.assertIsNone(whisper_download.installed_cli())
            self.assertTrue(whisper_download.needs_download("ggml-base.bin"))

    def test_restart_application_frozen_restores_ld_path_and_filters_psn(self):
        mock_qapp = MagicMock()
        with patch.object(sys, "frozen", True, create=True), patch.object(
            sys, "executable", self.exe_path
        ), patch.object(
            sys, "argv", [self.exe_path, "-psn_0_12345", "--flag"]
        ), patch.dict(
            os.environ,
            {"LD_LIBRARY_PATH": "/tmp/pyi", "LD_LIBRARY_PATH_ORIG": "/usr/lib"},
            clear=False,
        ), patch(
            "platform.system", return_value="Darwin"
        ), patch(
            "subprocess.Popen"
        ) as popen_mock, patch(
            "PyQt6.QtWidgets.QApplication.quit", mock_qapp
        ):
            os.environ.pop("APPIMAGE", None)
            utils.restart_application()

        popen_mock.assert_called_once()
        cmd, kwargs = popen_mock.call_args[0][0], popen_mock.call_args[1]
        self.assertEqual(cmd, [self.exe_path, "--flag"])
        self.assertEqual(kwargs["env"]["LD_LIBRARY_PATH"], "/usr/lib")
        self.assertTrue(kwargs["start_new_session"])
        mock_qapp.assert_called_once()


class TestPortableModeMigration(unittest.TestCase, _PortableEnvMixin):
    def setUp(self):
        self._setup_portable_env()

    def tearDown(self):
        self._teardown_portable_env()

    def _populate_system_data(self, with_tools=True):
        with open(os.path.join(self.sys_config_dir, "config.json"), "w") as f:
            json.dump({"language": "de_DE", "always_on_top": True}, f)

        # Create real SQLite DBs and leave an open manager connection to test DB closing
        from processed_items_manager import ProcessedItemsManager
        from gui_load_library import LibraryFoldersManager

        self.sample_sub = os.path.join(self.tmpdir.name, "movie.srt")
        with open(self.sample_sub, "w") as f:
            f.write("1\n00:00:01,000 --> 00:00:02,000\nhello\n")
        self.sample_folder = os.path.join(self.tmpdir.name, "movies")
        os.makedirs(self.sample_folder, exist_ok=True)

        pim = ProcessedItemsManager()
        self.assertTrue(pim.mark_as_processed(self.sample_sub, silent=True))
        lfm = LibraryFoldersManager()
        self.assertTrue(lfm.add_folder(self.sample_folder))

        with open(os.path.join(self.sys_logs_dir, "autosubsync_2026_11_16.txt"), "w") as f:
            f.write("sync log entry\n")
        with open(os.path.join(self.sys_logs_dir, "temp_extract.srt"), "w") as f:
            f.write("1\n00:00:01,000 --> 00:00:02,000\nhi\n")

        if with_tools:
            sys_lapse = os.path.join(self.sys_data_dir, "lapse")
            os.makedirs(sys_lapse, exist_ok=True)
            with open(os.path.join(sys_lapse, lapse_download.BINARY_NAME), "wb") as f:
                f.write(b"LAPSE_EXE")

            sys_whisper = os.path.join(self.sys_data_dir, "whisper")
            os.makedirs(sys_whisper, exist_ok=True)
            with open(os.path.join(sys_whisper, whisper_download.BINARY_NAME), "wb") as f:
                f.write(b"WHISPER_CLI")
            with open(os.path.join(sys_whisper, "ggml-base.bin"), "wb") as f:
                f.write(b"MODEL_DATA_12345")

    def test_enable_and_disable_full_roundtrip(self):
        self._populate_system_data(with_tools=True)
        info_on = utils.get_portable_migration_info(True)
        self.assertFalse(info_on["target_exists"])
        self.assertTrue(info_on["has_downloaded_tools"])
        self.assertGreater(info_on["tools_size_bytes"], 0)

        progress_values = []
        utils.migrate_portable_mode(True, progress_cb=progress_values.append)

        self.assertTrue(utils.is_portable_mode())
        self.assertEqual(progress_values[0], 0)
        self.assertEqual(progress_values[-1], 100)

        # Verify files moved into portable layout
        self.assertTrue(os.path.isfile(os.path.join(self.portable_dir, "config.json")))
        self.assertTrue(os.path.isfile(os.path.join(self.portable_dir, "processed_items.db")))
        self.assertTrue(os.path.isfile(os.path.join(self.portable_dir, "library_folders.db")))
        self.assertTrue(
            os.path.isfile(
                os.path.join(self.portable_dir, "logs", "autosubsync_2026_11_16.txt")
            )
        )
        tag = utils._get_portable_platform_tag()
        self.assertTrue(
            os.path.isfile(
                os.path.join(self.portable_dir, "bin", "lapse", tag, lapse_download.BINARY_NAME)
            )
        )
        self.assertTrue(
            os.path.isfile(
                os.path.join(self.portable_dir, "bin", "whisper", tag, whisper_download.BINARY_NAME)
            )
        )
        self.assertTrue(
            os.path.isfile(os.path.join(self.portable_dir, "bin", "whisper", "ggml-base.bin"))
        )

        # System sources should have been cleaned up
        self.assertFalse(os.path.exists(os.path.join(self.sys_config_dir, "config.json")))
        self.assertFalse(os.path.exists(os.path.join(self.sys_config_dir, "processed_items.db")))
        self.assertFalse(
            os.path.exists(os.path.join(self.sys_logs_dir, "autosubsync_2026_11_16.txt"))
        )

        # Verify migrated SQLite DB contents are readable cleanly via managers
        from processed_items_manager import ProcessedItemsManager
        from gui_load_library import LibraryFoldersManager

        self.assertTrue(ProcessedItemsManager().is_processed(self.sample_sub))
        self.assertEqual(
            LibraryFoldersManager().get_all_folders(), [self.sample_folder]
        )

        # Now toggle OFF (disable portable mode)
        info_off = utils.get_portable_migration_info(False)
        self.assertFalse(info_off["target_exists"])
        self.assertTrue(info_off["has_downloaded_tools"])

        utils.migrate_portable_mode(False)

        self.assertFalse(utils.is_portable_mode())
        self.assertFalse(os.path.exists(self.portable_dir))
        self.assertTrue(os.path.isfile(os.path.join(self.sys_config_dir, "config.json")))
        self.assertTrue(os.path.isfile(os.path.join(self.sys_config_dir, "processed_items.db")))
        self.assertTrue(os.path.isfile(os.path.join(self.sys_config_dir, "library_folders.db")))
        self.assertTrue(
            os.path.isfile(
                os.path.join(self.sys_logs_dir, "autosubsync_2026_11_16.txt")
            )
        )
        self.assertTrue(
            os.path.isfile(os.path.join(self.sys_data_dir, "lapse", lapse_download.BINARY_NAME))
        )
        self.assertTrue(
            os.path.isfile(
                os.path.join(self.sys_data_dir, "whisper", whisper_download.BINARY_NAME)
            )
        )
        self.assertTrue(
            os.path.isfile(os.path.join(self.sys_data_dir, "whisper", "ggml-base.bin"))
        )

    def test_enable_without_moving_tools_keeps_system_tools(self):
        self._populate_system_data(with_tools=True)
        utils.migrate_portable_mode(True, move_tools=False)

        self.assertTrue(utils.is_portable_mode())
        self.assertTrue(os.path.isfile(os.path.join(self.portable_dir, "config.json")))
        # Tools remain in system folder
        self.assertTrue(
            os.path.isfile(os.path.join(self.sys_data_dir, "lapse", lapse_download.BINARY_NAME))
        )
        self.assertTrue(
            os.path.isfile(os.path.join(self.sys_data_dir, "whisper", "ggml-base.bin"))
        )
        self.assertFalse(os.path.exists(os.path.join(self.portable_dir, "bin")))

    def test_disable_keep_existing_system_data(self):
        # Put older data in system dir AND newer data in portable dir
        with open(os.path.join(self.sys_config_dir, "config.json"), "w") as f:
            json.dump({"language": "en_US"}, f)

        os.makedirs(os.path.join(self.portable_dir, "logs"), exist_ok=True)
        with open(os.path.join(self.portable_dir, "config.json"), "w") as f:
            json.dump({"language": "ja_JP"}, f)
        with open(os.path.join(self.portable_dir, "logs", "portable_only.txt"), "w") as f:
            f.write("portable log\n")

        info = utils.get_portable_migration_info(False)
        self.assertTrue(info["target_exists"])

        utils.migrate_portable_mode(False, overwrite_target=False)
        self.assertFalse(os.path.exists(self.portable_dir))
        with open(os.path.join(self.sys_config_dir, "config.json"), "r") as f:
            self.assertEqual(json.load(f)["language"], "en_US")
        # Non-conflicting files like logs still migrate
        self.assertTrue(
            os.path.isfile(os.path.join(self.sys_logs_dir, "portable_only.txt"))
        )

    def test_mid_copy_failure_rolls_back_cleanly_including_preexisting_targets(self):
        self._populate_system_data(with_tools=False)

        # Case 1: Enable failed mid-way when portable_dir did not exist
        real_copy2 = shutil.copy2
        calls = {"count": 0}

        def failing_copy2(src, dst, *args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 2:
                raise OSError("Simulated USB write error")
            return real_copy2(src, dst, *args, **kwargs)

        with patch("shutil.copy2", side_effect=failing_copy2):
            with self.assertRaises(OSError):
                utils.migrate_portable_mode(True)

        self.assertFalse(os.path.exists(self.portable_dir))
        self.assertTrue(os.path.isfile(os.path.join(self.sys_config_dir, "config.json")))
        self.assertTrue(
            os.path.isfile(os.path.join(self.sys_config_dir, "processed_items.db"))
        )

        # Case 2: Disable with overwrite_target=True when system config already exists;
        # failure on second file must restore original system config intact!
        os.makedirs(os.path.join(self.portable_dir, "logs"), exist_ok=True)
        with open(os.path.join(self.portable_dir, "config.json"), "w") as f:
            json.dump({"language": "fr_FR"}, f)
        with open(os.path.join(self.portable_dir, "logs", "log1.txt"), "w") as f:
            f.write("log1")

        # Keep existing system config to verify restoration
        with open(os.path.join(self.sys_config_dir, "config.json"), "w") as f:
            json.dump({"language": "en_US"}, f)

        calls["count"] = 0
        with patch("shutil.copy2", side_effect=failing_copy2):
            with self.assertRaises(OSError):
                utils.migrate_portable_mode(False, overwrite_target=True)

        # Portable dir still exists cleanly and original system config was restored
        self.assertTrue(os.path.isdir(self.portable_dir))
        with open(os.path.join(self.sys_config_dir, "config.json"), "r") as f:
            self.assertEqual(json.load(f)["language"], "en_US")
        self.assertFalse(os.path.exists(os.path.join(self.sys_logs_dir, "log1.txt")))

    def test_sqlite_wal_files_not_mismatched_and_partial_tools_skipped(self):
        # Keep-target (overwrite_target=False) must NEVER mix source -wal with existing destination .db
        os.makedirs(self.portable_dir, exist_ok=True)
        with open(os.path.join(self.portable_dir, "processed_items.db"), "wb") as f:
            f.write(b"PORTABLE_DB")
        with open(os.path.join(self.sys_config_dir, "processed_items.db"), "wb") as f:
            f.write(b"SYSTEM_DB")
        with open(os.path.join(self.sys_config_dir, "processed_items.db-wal"), "wb") as f:
            f.write(b"SYSTEM_WAL")

        # Also leave an incomplete .part whisper download and nested subdir in system tools
        sys_whisper = os.path.join(self.sys_data_dir, "whisper")
        nested = os.path.join(sys_whisper, "nested")
        os.makedirs(nested, exist_ok=True)
        with open(os.path.join(sys_whisper, "ggml-base.bin.part"), "wb") as f:
            f.write(b"PARTIAL")
        with open(os.path.join(nested, "whisper-cli"), "wb") as f:
            f.write(b"CLI_BIN")

        utils.migrate_portable_mode(True, overwrite_target=False, move_tools=True)

        # Destination DB preserved and source WAL was NOT copied next to it
        with open(os.path.join(self.portable_dir, "processed_items.db"), "rb") as f:
            self.assertEqual(f.read(), b"PORTABLE_DB")
        self.assertFalse(
            os.path.exists(os.path.join(self.portable_dir, "processed_items.db-wal"))
        )
        # Incomplete .part file was skipped, real CLI moved and nested empty dir cleaned
        tag = utils._get_portable_platform_tag()
        migrated_cli = os.path.join(
            self.portable_dir, "bin", "whisper", tag, "nested", "whisper-cli"
        )
        self.assertTrue(os.path.isfile(migrated_cli))
        if os.name != "nt":
            self.assertTrue(os.access(migrated_cli, os.X_OK))
        self.assertFalse(
            os.path.exists(
                os.path.join(self.portable_dir, "bin", "whisper", tag, "ggml-base.bin.part")
            )
        )
        self.assertFalse(os.path.exists(nested))

    def test_overwrite_db_removes_stale_dst_wal_and_restores_on_failure(self):
        self._populate_system_data(with_tools=False)
        # Create stale WAL in portable dir alongside existing portable DB
        os.makedirs(self.portable_dir, exist_ok=True)
        with open(os.path.join(self.portable_dir, "processed_items.db"), "wb") as f:
            f.write(b"OLD_PORTABLE_DB")
        with open(os.path.join(self.portable_dir, "processed_items.db-wal"), "wb") as f:
            f.write(b"STALE_PORTABLE_WAL")

        # Fail during logs copy AFTER DB overwrite staged stale WAL cleanup:
        real_copy2 = shutil.copy2

        def fail_on_log(src, dst, *args, **kwargs):
            if os.path.basename(src).endswith(".txt"):
                raise OSError("Simulated failure on log copy")
            return real_copy2(src, dst, *args, **kwargs)

        with patch("shutil.copy2", side_effect=fail_on_log):
            with self.assertRaises(OSError):
                utils.migrate_portable_mode(True, overwrite_target=True)

        # Rollback must keep BOTH original portable DB and its WAL intact
        with open(os.path.join(self.portable_dir, "processed_items.db"), "rb") as f:
            self.assertEqual(f.read(), b"OLD_PORTABLE_DB")
        with open(os.path.join(self.portable_dir, "processed_items.db-wal"), "rb") as f:
            self.assertEqual(f.read(), b"STALE_PORTABLE_WAL")

        # Now succeed with overwrite_target=True -> stale WAL at dst must be cleaned up
        utils.migrate_portable_mode(True, overwrite_target=True)
        self.assertTrue(
            os.path.isfile(os.path.join(self.portable_dir, "processed_items.db"))
        )
        self.assertFalse(
            os.path.exists(os.path.join(self.portable_dir, "processed_items.db-wal"))
        )

    def test_disable_removes_readonly_portable_files(self):
        os.makedirs(self.portable_dir, exist_ok=True)
        ro_file = os.path.join(self.portable_dir, "config.json")
        with open(ro_file, "w") as f:
            json.dump({"language": "en_US"}, f)
        os.chmod(ro_file, 0o444)

        utils.migrate_portable_mode(False)
        self.assertFalse(os.path.exists(self.portable_dir))
        self.assertTrue(os.path.isfile(os.path.join(self.sys_config_dir, "config.json")))


class TestPortableModeGUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _create_window(self, status_dict):
        from gui import autosubsyncapp
        from gui_automatic_tab import attach_functions_to_autosubsyncapp as attach_auto
        from gui_manual_tab import attach_functions_to_autosubsyncapp as attach_manual
        from gui_batch_mode import attach_functions_to_autosubsyncapp as attach_batch
        from gui_auto_pairing import (
            attach_functions_to_autosubsyncapp as attach_pairing,
        )
        from gui_multiple_subs import (
            attach_functions_to_autosubsyncapp as attach_multiple,
        )

        attach_auto(autosubsyncapp)
        attach_manual(autosubsyncapp)
        attach_batch(autosubsyncapp)
        attach_pairing(autosubsyncapp)
        attach_multiple(autosubsyncapp)

        tmpdir = tempfile.TemporaryDirectory()
        cfg_dir = os.path.join(tmpdir.name, "cfg")
        logs_dir = os.path.join(tmpdir.name, "logs")
        os.makedirs(cfg_dir)
        os.makedirs(logs_dir)
        utils.clear_config_cache()

        patches = [
            patch("gui.get_portable_mode_status", return_value=status_dict),
            patch.object(utils, "get_portable_mode_status", return_value=status_dict),
            patch.object(utils, "get_system_config_dir", return_value=cfg_dir),
            patch.object(utils, "get_system_logs_directory", return_value=logs_dir),
            patch("gui.QTimer.singleShot", side_effect=lambda ms, cb: None),
        ]
        for p in patches:
            p.start()

        win = autosubsyncapp()
        return win, tmpdir, patches

    def _cleanup_window(self, win, tmpdir, patches):
        from processed_items_manager import close_processed_items_manager
        from gui_load_library import close_library_folders_manager

        win.close()
        win.deleteLater()
        self.app.processEvents()
        close_processed_items_manager()
        close_library_folders_manager()
        for p in reversed(patches):
            p.stop()
        utils.clear_config_cache()
        tmpdir.cleanup()

    def test_menu_position_default_unchecked_and_disabled_click_info(self):
        status = {
            "supported": False,
            "usable": False,
            "active": False,
            "reason": "not_frozen",
            "base_dir": None,
            "portable_dir": None,
        }
        win, tmpdir, patches = self._create_window(status)
        try:
            actions = win.settings_menu.actions()
            p_idx = actions.index(win.portable_mode_action)
            a_idx = actions.index(win.always_on_top_action)
            self.assertEqual(p_idx + 1, a_idx)
            self.assertTrue(win.portable_mode_action.isCheckable())
            self.assertFalse(win.portable_mode_action.isChecked())
            self.assertFalse(win.portable_mode_action.isEnabled())

            # Clicking disabled item inside _SettingsMenu must close menu & show info
            win.settings_menu.show()
            rect = win.settings_menu.actionGeometry(win.portable_mode_action)
            center = QPointF(rect.center())
            ev = QMouseEvent(
                QMouseEvent.Type.MouseButtonRelease,
                center,
                center,
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
            with patch("gui.QMessageBox.information") as info_mock:
                win.settings_menu.mouseReleaseEvent(ev)
                self.assertEqual(info_mock.call_count, 1)
                msg = info_mock.call_args[0][2]
                self.assertEqual(msg, str(texts.PORTABLE_MODE_UNSUPPORTED_NOT_FROZEN))
                self.assertFalse(win.settings_menu.isVisible())

            # Key activation on disabled item when focused also triggers info
            win.settings_menu.show()
            key_ev = QKeyEvent(
                QKeyEvent.Type.KeyPress,
                Qt.Key.Key_Return,
                Qt.KeyboardModifier.NoModifier,
            )
            with patch.object(
                win.settings_menu,
                "activeAction",
                return_value=win.portable_mode_action,
            ), patch("gui.QMessageBox.information") as info_mock:
                win.settings_menu.keyPressEvent(key_ev)
                self.assertEqual(info_mock.call_count, 1)

            # Verify remaining unsupported reasons display tailored info
            for reason, expected_dict in (
                ("translocated", texts.PORTABLE_MODE_UNSUPPORTED_TRANSLOCATED),
                ("system_install", texts.PORTABLE_MODE_UNSUPPORTED_SYSTEM_INSTALL),
                ("not_writable", texts.PORTABLE_MODE_UNSUPPORTED_READONLY),
            ):
                with patch(
                    "gui.get_portable_mode_status",
                    return_value={
                        "supported": reason == "not_writable",
                        "usable": False,
                        "active": False,
                        "reason": reason,
                        "base_dir": "/opt/autosubsync",
                        "portable_dir": None,
                    },
                ), patch("gui.QMessageBox.information") as info_mock:
                    win.show_portable_mode_unavailable_info()
                    expected_msg = str(expected_dict).format(path="/opt/autosubsync")
                    self.assertEqual(info_mock.call_args[0][2], expected_msg)
        finally:
            self._cleanup_window(win, tmpdir, patches)

    def test_usable_toggle_busy_guard_cancel_success_and_error(self):
        portable_dir = "/tmp/fake_usb/AutoSubSync_data"
        status_off = {
            "supported": True,
            "usable": True,
            "active": False,
            "reason": "ok",
            "base_dir": "/tmp/fake_usb",
            "portable_dir": portable_dir,
        }
        win, tmpdir, patches = self._create_window(status_off)
        try:
            self.assertTrue(win.portable_mode_action.isEnabled())
            self.assertFalse(win.portable_mode_action.isChecked())

            # Busy guard prevents toggling during sync
            win._batch_state = {"should_cancel": False}
            with patch("gui.QMessageBox.warning") as warn_mock, patch(
                "gui.migrate_portable_mode"
            ) as mig_mock:
                win.toggle_portable_mode(True)
                self.assertEqual(warn_mock.call_count, 1)
                self.assertFalse(mig_mock.called)
                self.assertFalse(win.portable_mode_action.isChecked())
            del win._batch_state

            # Cancel confirmation reverts checkbox without migrating
            info_payload = {
                "status": status_off,
                "portable_dir": portable_dir,
                "target_exists": False,
                "has_downloaded_tools": False,
                "tools_size_bytes": 0,
                "config_file_count": 1,
                "log_file_count": 0,
            }
            with patch("gui.get_portable_migration_info", return_value=info_payload), patch(
                "gui.QMessageBox.exec", return_value=QMessageBox.StandardButton.No
            ), patch("gui.migrate_portable_mode") as mig_mock:
                win.toggle_portable_mode(True)
                self.assertFalse(mig_mock.called)
                self.assertFalse(win.portable_mode_action.isChecked())

            # Confirmed enable runs migration worker, closes progress dialog, restarts app
            with patch("gui.get_portable_migration_info", return_value=info_payload), patch(
                "gui.QMessageBox.exec", return_value=QMessageBox.StandardButton.Yes
            ), patch("gui.migrate_portable_mode") as mig_mock, patch(
                "gui.restart_application"
            ) as restart_mock:
                win.toggle_portable_mode(True)
                self.app.processEvents()
                mig_mock.assert_called_once()
                _, kwargs = mig_mock.call_args
                self.assertTrue(kwargs["overwrite_target"])
                self.assertTrue(kwargs["move_tools"])
                restart_mock.assert_called_once()

            # Failed migration shows critical error, reverts check state, does not restart
            with patch("gui.get_portable_migration_info", return_value=info_payload), patch(
                "gui.QMessageBox.exec", return_value=QMessageBox.StandardButton.Yes
            ), patch(
                "gui.migrate_portable_mode", side_effect=OSError("Permission denied")
            ), patch("gui.QMessageBox.critical") as crit_mock, patch(
                "gui.restart_application"
            ) as restart_mock:
                win.portable_mode_action.setChecked(True)
                win.toggle_portable_mode(True)
                self.app.processEvents()
                crit_mock.assert_called_once()
                self.assertIn("Permission denied", crit_mock.call_args[0][2])
                self.assertFalse(win.portable_mode_action.isChecked())
                restart_mock.assert_not_called()
        finally:
            self._cleanup_window(win, tmpdir, patches)

    def test_conflict_dialog_and_unchecked_move_tools_option(self):
        portable_dir = "/tmp/fake_usb/AutoSubSync_data"
        status_off = {
            "supported": True,
            "usable": True,
            "active": False,
            "reason": "ok",
            "base_dir": "/tmp/fake_usb",
            "portable_dir": portable_dir,
        }
        win, tmpdir, patches = self._create_window(status_off)
        try:
            info_conflict = {
                "status": status_off,
                "portable_dir": portable_dir,
                "target_exists": True,
                "has_downloaded_tools": True,
                "tools_size_bytes": 150 * 1024 * 1024,
                "config_file_count": 2,
                "log_file_count": 1,
            }

            def fake_exec(msgbox_self):
                cb = msgbox_self.checkBox()
                self.assertIsNotNone(cb)
                self.assertTrue(cb.isChecked())
                self.assertIn("150.0 MB", cb.text())
                cb.setChecked(False)
                # Click "Use Portable Data" (ActionRole keep_btn)
                for btn in msgbox_self.buttons():
                    if btn.text() == str(texts.PORTABLE_MODE_USE_EXISTING_PORTABLE):
                        msgbox_self.clickedButton = lambda b=btn: b
                        return 0
                raise AssertionError("Keep/Use Portable button missing")

            with patch("gui.get_portable_migration_info", return_value=info_conflict), patch.object(
                QMessageBox, "exec", fake_exec
            ), patch("gui.migrate_portable_mode") as mig_mock, patch(
                "gui.restart_application"
            ) as restart_mock:
                win.toggle_portable_mode(True)
                self.app.processEvents()
                mig_mock.assert_called_once()
                _, kwargs = mig_mock.call_args
                self.assertFalse(kwargs["overwrite_target"])
                self.assertFalse(kwargs["move_tools"])
                restart_mock.assert_called_once()
        finally:
            self._cleanup_window(win, tmpdir, patches)


if __name__ == "__main__":
    unittest.main()
