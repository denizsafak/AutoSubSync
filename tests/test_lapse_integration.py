import os
import sys
import tempfile
import unittest
import shutil
import platform
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main")))

from constants import SYNC_TOOLS, DEFAULT_OPTIONS
import sync_core
from cli import TOOL_CHOICES
import resources.lapse_download as lapse_download


class TestLapseIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.video_path = os.path.join(self.temp_dir, "movie.mkv")
        with open(self.video_path, "wb") as f:
            f.write(b"dummy video content")

        self.sub_path = os.path.join(self.temp_dir, "movie.srt")
        with open(self.sub_path, "w", encoding="utf-8") as f:
            f.write("1\n00:00:01,000 --> 00:00:03,000\nHello World\n")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sync_tools_contains_lapse_with_valid_metadata(self):
        self.assertIn("lapse", SYNC_TOOLS)
        tool = SYNC_TOOLS["lapse"]
        self.assertEqual(tool["type"], "executable")
        self.assertEqual(tool["github"], "https://github.com/Schwponaco-org/lapse")
        self.assertEqual(
            tool["documentation"],
            "https://github.com/Schwponaco-org/lapse/blob/main/docs/benchmarks.md",
        )
        self.assertTrue(tool["supports_subtitle_as_reference"])
        self.assertIn(".srt", tool["supported_formats"])
        self.assertIn(".ass", tool["supported_formats"])
        self.assertIn(".ssa", tool["supported_formats"])
        self.assertIn(".vtt", tool["supported_formats"])

    def test_cli_choices_includes_lapse(self):
        self.assertIn("lapse", TOOL_CHOICES)

    def test_lapse_download_architecture_mapping(self):
        with patch("platform.system", return_value="Linux"), patch("platform.machine", return_value="x86_64"):
            self.assertEqual(lapse_download.get_archive_filename(), "lapse-linux-amd64.tar.gz")

        with patch("platform.system", return_value="Linux"), patch("platform.machine", return_value="aarch64"):
            self.assertEqual(lapse_download.get_archive_filename(), "lapse-linux-arm64.tar.gz")

        with patch("platform.system", return_value="Darwin"), patch("platform.machine", return_value="arm64"):
            self.assertEqual(lapse_download.get_archive_filename(), "lapse-macos-arm64.tar.gz")

        with patch("platform.system", return_value="Darwin"), patch("platform.machine", return_value="x86_64"):
            self.assertEqual(lapse_download.get_archive_filename(), "lapse-macos-x86_64.tar.gz")

        with patch("platform.system", return_value="Windows"), patch("platform.machine", return_value="AMD64"):
            self.assertEqual(lapse_download.get_archive_filename(), "lapse-windows-x64.zip")

    def test_build_cmd_default_mode(self):
        config = dict(DEFAULT_OPTIONS)
        cmd = sync_core.build_cmd(
            "lapse",
            "/usr/bin/lapse",
            self.video_path,
            self.sub_path,
            os.path.join(self.temp_dir, "out.srt"),
            config=config,
        )
        expected = [
            "/usr/bin/lapse",
            self.video_path,
            self.sub_path,
            "--output",
            os.path.join(self.temp_dir, "out.srt"),
            "--no-backup",
        ]
        self.assertEqual(cmd, expected)

    def test_build_cmd_nosplit_and_ols_modes(self):
        config = dict(DEFAULT_OPTIONS)
        config["lapse_mode"] = "nosplit"
        cmd = sync_core.build_cmd(
            "lapse",
            "lapse",
            self.video_path,
            self.sub_path,
            os.path.join(self.temp_dir, "out.srt"),
            config=config,
        )
        self.assertIn("nosplit", cmd)

        config["lapse_mode"] = "ols"
        cmd = sync_core.build_cmd(
            "lapse",
            "lapse",
            self.video_path,
            self.sub_path,
            os.path.join(self.temp_dir, "out.srt"),
            config=config,
        )
        self.assertIn("ols", cmd)

    def test_build_cmd_split_mode_with_penalty(self):
        config = dict(DEFAULT_OPTIONS)
        config["lapse_mode"] = "split"
        config["lapse_split_penalty"] = 14
        cmd = sync_core.build_cmd(
            "lapse",
            "lapse",
            self.video_path,
            self.sub_path,
            os.path.join(self.temp_dir, "out.srt"),
            config=config,
        )
        self.assertIn("split", cmd)
        split_idx = cmd.index("split")
        self.assertEqual(cmd[split_idx + 1], "14")

    def test_build_cmd_flags_and_arguments(self):
        config = dict(DEFAULT_OPTIONS)
        config["lapse_no_cache"] = True
        config["lapse_full_scan"] = True
        config["lapse_arguments"] = "--audio-track 2"

        cmd = sync_core.build_cmd(
            "lapse",
            "lapse",
            self.video_path,
            self.sub_path,
            os.path.join(self.temp_dir, "out.srt"),
            config=config,
        )
        self.assertIn("--no-cache", cmd)
        self.assertIn("--full-scan", cmd)
        self.assertIn("--audio-track", cmd)
        self.assertIn("2", cmd)

    def test_run_sync_auto_downloads_lapse_when_missing(self):
        config = dict(DEFAULT_OPTIONS)
        out_sub = os.path.join(self.temp_dir, "synced_lapse.srt")
        fake_downloaded_bin = os.path.join(self.temp_dir, "downloaded_lapse")
        with open(fake_downloaded_bin, "w") as f:
            f.write("#!/bin/sh\n")

        def fake_run_executable(cmd, callbacks, *, sync_tool, process_holder=None):
            with open(out_sub, "w", encoding="utf-8") as f:
                f.write("1\n00:00:02,000 --> 00:00:04,000\nSynced text\n")
            return 0

        with patch("resources.lapse_download.DIST_BIN_PATH", os.path.join(self.temp_dir, "nonexistent")), \
             patch("resources.lapse_download.download", return_value=fake_downloaded_bin) as mock_dl, \
             patch("sync_core.run_executable_tool", side_effect=fake_run_executable):
            with patch.dict(SYNC_TOOLS["lapse"]["executable"], {platform.system(): "/nonexistent/lapse"}):
                result = sync_core.run_sync(
                    self.video_path,
                    self.sub_path,
                    tool="lapse",
                    output=out_sub,
                    config=config,
                )
                self.assertTrue(result.ok)
                mock_dl.assert_called_once()

    def test_run_sync_with_lapse_success(self):
        config = dict(DEFAULT_OPTIONS)
        out_sub = os.path.join(self.temp_dir, "synced_lapse.srt")

        def fake_run_executable(cmd, callbacks, *, sync_tool, process_holder=None):
            with open(out_sub, "w", encoding="utf-8") as f:
                f.write("1\n00:00:02,000 --> 00:00:04,000\nSynced text\n")
            return 0

        with patch("sync_core.run_executable_tool", side_effect=fake_run_executable):
            result = sync_core.run_sync(
                self.video_path,
                self.sub_path,
                tool="lapse",
                output=out_sub,
                config=config,
            )
            self.assertTrue(result.ok)
            self.assertEqual(result.output_path, out_sub)
            self.assertEqual(result.tool_used, "lapse")
            self.assertTrue(os.path.exists(out_sub))

    def test_build_py_ast_extracts_lapse(self):
        import build

        tools = build.get_sync_tools_names_from_constants()
        self.assertIn("lapse", tools)

        versions = build.get_sync_tools_versions()
        self.assertIn("lapse", versions)
        self.assertEqual(versions["lapse"]["version"], "2.0.1")
        self.assertEqual(
            versions["lapse"]["github"], "https://github.com/Schwponaco-org/lapse"
        )

    def test_dropdown_option_updates_correct_key(self):
        mode_data = SYNC_TOOLS["lapse"]["options"]["mode"]
        values = mode_data["values"]
        labels = mode_data["value_labels"]

        config = {}
        for target_mode in ("nosplit", "ols", "split", "auto"):
            display_text = str(labels[target_mode])
            resolved_value = next((v for v in values if str(labels.get(v, v)) == display_text), display_text)
            config["lapse_mode"] = resolved_value
            self.assertEqual(config["lapse_mode"], target_mode)

    def test_lapse_skips_external_embedded_subtitle_extraction(self):
        import subtitle_extractor

        config = dict(DEFAULT_OPTIONS)
        config["lapse_check_video_for_subtitles"] = True
        should_extract = subtitle_extractor.should_extract_subtitles(
            self.video_path, "lapse", config
        )
        self.assertFalse(should_extract)

    def test_build_cmd_no_embedded_when_disabled(self):
        config = dict(DEFAULT_OPTIONS)
        config["lapse_check_video_for_subtitles"] = False

        cmd = sync_core.build_cmd(
            "lapse",
            "lapse",
            self.video_path,
            self.sub_path,
            os.path.join(self.temp_dir, "out.srt"),
            config=config,
        )
        self.assertIn("--no-embedded", cmd)

    def test_build_cmd_auto_mode_custom_penalty(self):
        config = dict(DEFAULT_OPTIONS)
        config["lapse_mode"] = "auto"
        config["lapse_split_penalty"] = 9

        cmd = sync_core.build_cmd(
            "lapse",
            "lapse",
            self.video_path,
            self.sub_path,
            os.path.join(self.temp_dir, "out.srt"),
            config=config,
        )
        self.assertIn("auto", cmd)
        auto_idx = cmd.index("auto")
        self.assertEqual(cmd[auto_idx + 1], "9")

    def test_process_output_filters_demuxer_warnings(self):
        noisy_output = (
            "[matroska,webm @ 0x55e31ea90440] Could not find codec parameters for stream 2 (Subtitle: hdmv_pgs_subtitle): unspecified size\n"
            "Consider increasing the value for the 'analyzeduration' (0) and 'probesize' (5000000) options\n"
            "Listening to the audio 46%\n"
        )
        cleaned, percent = sync_core.process_output(noisy_output, "lapse")
        self.assertNotIn("Could not find codec parameters", cleaned)
        self.assertNotIn("Consider increasing the value", cleaned)
        self.assertIn("Listening to the audio 46%", cleaned)
        self.assertEqual(percent, 46.0)

    def test_lapse_split_penalty_disabled_in_nosplit_and_ols_modes(self):
        from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QGroupBox, QCheckBox
        app = QApplication.instance() or QApplication(["-platform", "offscreen"])

        from gui_automatic_tab import update_sync_tool_options, _create_slider
        from gui import autosubsyncapp

        dummy = QWidget()
        dummy.config = dict(DEFAULT_OPTIONS)
        dummy.sync_options_layout = QVBoxLayout(dummy)
        dummy.sync_options_group = QGroupBox(dummy)
        dummy.btn_add_args = QWidget(dummy)
        dummy.btn_add_args.setStyleSheet = MagicMock()
        dummy.update_args_tooltip = MagicMock()
        dummy.clear_layout = MagicMock()
        dummy._checkbox = lambda label: QCheckBox(str(label), dummy)
        dummy.COMBO_STYLE = ""
        dummy._create_slider = _create_slider.__get__(dummy, QWidget)
        dummy._dropdown = autosubsyncapp._dropdown.__get__(dummy, QWidget)

        # Test initial auto mode -> slider enabled
        dummy.config["lapse_mode"] = "auto"
        update_sync_tool_options(dummy, "lapse")
        split_slider = dummy.tool_option_widgets["split_penalty"]
        self.assertTrue(split_slider.isEnabled())
        self.assertTrue(split_slider.title_label.isEnabled())

        # Switch to nosplit -> slider disabled
        mode_combo = dummy.tool_option_widgets["mode"]
        labels = SYNC_TOOLS["lapse"]["options"]["mode"]["value_labels"]
        nosplit_text = str(labels.get("nosplit", "nosplit"))
        mode_combo.setCurrentText(nosplit_text)
        self.assertFalse(split_slider.isEnabled())
        self.assertFalse(split_slider.title_label.isEnabled())

        # Switch to split mode -> slider enabled
        split_text = str(labels.get("split", "split"))
        mode_combo.setCurrentText(split_text)
        self.assertTrue(split_slider.isEnabled())
        self.assertTrue(split_slider.title_label.isEnabled())

        # Switch to ols -> slider disabled
        ols_text = str(labels.get("ols", "ols"))
        mode_combo.setCurrentText(ols_text)
        self.assertFalse(split_slider.isEnabled())
        self.assertFalse(split_slider.title_label.isEnabled())

    def test_ffsubsync_onnx_silero_vad_sync(self):
        import call_ffsubsync
        import subprocess

        # Create synthetic audio in video
        synth_vid = os.path.join(self.temp_dir, "synth.mp4")
        synth_sub = os.path.join(self.temp_dir, "synth.srt")
        synth_out = os.path.join(self.temp_dir, "synth_out.srt")

        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "sine=frequency=1000:duration=2",
                "-f", "lavfi", "-i", "color=c=black:s=320x240:d=2",
                "-c:a", "aac", "-c:v", "libx264",
                synth_vid,
            ],
            capture_output=True,
        )
        with open(synth_sub, "w", encoding="utf-8") as f:
            f.write("1\n00:00:00,500 --> 00:00:01,500\nHello world\n")

        # Run ffsubsync with --vad silero
        exit_code = call_ffsubsync.cli_entry(
            [synth_vid, "-i", synth_sub, "-o", synth_out, "--vad", "silero"]
        )
        self.assertEqual(exit_code, 0)
        self.assertTrue(os.path.exists(synth_out))
        self.assertGreater(os.path.getsize(synth_out), 0)

    def test_lapse_download_architecture_mapping_all_os(self):
        from resources import lapse_download

        test_cases = [
            ("windows", "amd64", "lapse-windows-x64.zip"),
            ("windows", "x86_64", "lapse-windows-x64.zip"),
            ("windows", "arm64", "lapse-windows-x64.zip"),
            ("darwin", "arm64", "lapse-macos-arm64.tar.gz"),
            ("darwin", "aarch64", "lapse-macos-arm64.tar.gz"),
            ("darwin", "x86_64", "lapse-macos-x86_64.tar.gz"),
            ("darwin", "amd64", "lapse-macos-x86_64.tar.gz"),
            ("linux", "amd64", "lapse-linux-amd64.tar.gz"),
            ("linux", "x86_64", "lapse-linux-amd64.tar.gz"),
            ("linux", "arm64", "lapse-linux-arm64.tar.gz"),
            ("linux", "aarch64", "lapse-linux-arm64.tar.gz"),
        ]

        for system, machine, expected in test_cases:
            with patch("platform.system", return_value=system.capitalize()):
                with patch("platform.machine", return_value=machine):
                    arch = lapse_download.get_archive_filename()
                    self.assertEqual(
                        arch,
                        expected,
                        f"Failed mapping for {system} / {machine}: got {arch}, expected {expected}",
                    )

    def test_ensure_silero_vad_helper(self):
        from resources import lapse_download
        silero_path = lapse_download.ensure_silero_vad()
        self.assertIsNotNone(silero_path)
        self.assertTrue(os.path.isfile(silero_path))
    def test_create_process_injects_lapse_env_vars(self):
        from utils import create_process

        test_os_list = ["Linux", "Darwin", "Windows"]
        for os_name in test_os_list:
            fake_dir = os.path.join(self.temp_dir, f"fake_{os_name}")
            os.makedirs(fake_dir, exist_ok=True)
            fake_exe = os.path.join(fake_dir, "lapse.exe" if os_name == "Windows" else "lapse")
            fake_silero = os.path.join(fake_dir, "silero_vad.onnx")
            lib_name = (
                "onnxruntime.dll"
                if os_name == "Windows"
                else "libonnxruntime.dylib"
                if os_name == "Darwin"
                else "libonnxruntime.so"
            )
            fake_lib = os.path.join(fake_dir, lib_name)
            with open(fake_exe, "w") as f:
                f.write("#!/bin/sh\nexit 0\n")
            with open(fake_silero, "w") as f:
                f.write("onnx")
            with open(fake_lib, "w") as f:
                f.write("dll")

            with patch("platform.system", return_value=os_name):
                with patch("subprocess.Popen") as mock_popen:
                    mock_popen.return_value.stdout = MagicMock()
                    mock_popen.return_value.poll.return_value = 0
                    create_process([fake_exe, "--vad"])
                    self.assertTrue(mock_popen.called)
                    call_kwargs = mock_popen.call_args[1]
                    env = call_kwargs.get("env", {})
                    self.assertEqual(env.get("LAPSE_VAD_MODEL"), fake_silero)
                    self.assertEqual(env.get("LAPSE_ONNXRUNTIME"), fake_lib)


if __name__ == "__main__":
    unittest.main()

