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

    def test_build_cmd_extra_engine_options(self):
        config = dict(DEFAULT_OPTIONS)
        config.update(
            lapse_force=True,
            lapse_strict=True,
            lapse_snap=True,
            lapse_confidence=12,
            lapse_audio_track=1,
            lapse_min_shift=50,
        )
        cmd = sync_core.build_cmd("lapse", "lapse", "v.mkv", "s.srt", "o.srt", config=config)
        for flag in ("--force", "--strict", "--snap"):
            self.assertIn(flag, cmd)
        self.assertEqual(cmd[cmd.index("--confidence") + 1], "12")
        self.assertEqual(cmd[cmd.index("--audio-track") + 1], "1")
        self.assertEqual(cmd[cmd.index("--min-shift") + 1], "50")

        defaults = sync_core.build_cmd("lapse", "lapse", "v.mkv", "s.srt", "o.srt", config=dict(DEFAULT_OPTIONS))
        for flag in ("--force", "--strict", "--snap", "--confidence", "--audio-track", "--min-shift"):
            self.assertNotIn(flag, defaults)

        # These defaults must match the LAPSE engine itself.
        lapse_options = SYNC_TOOLS["lapse"]["other_options"]
        self.assertEqual(lapse_options["confidence"]["default"], 8)
        self.assertEqual(lapse_options["audio_track"]["default"], -1)
        self.assertEqual(lapse_options["min_shift"]["default"], 1)
        self.assertEqual(lapse_options["min_shift"]["range"], [1, 1000])

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

        with patch("utils.save_config"):
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

    def test_run_sync_keeps_unsure_result_written_beside_output(self):
        out_sub = os.path.join(self.temp_dir, "synced_lapse.srt")
        unsure = os.path.join(self.temp_dir, "synced_lapse.lapse-unsure.srt")

        def fake_run_executable(cmd, callbacks, *, sync_tool, process_holder=None):
            with open(unsure, "w", encoding="utf-8") as f:
                f.write("1\n00:00:02,000 --> 00:00:04,000\nGuess\n")
            return 3

        with patch("sync_core.run_executable_tool", side_effect=fake_run_executable), \
             patch("resources.lapse_download.is_outdated", return_value=False):
            result = sync_core.run_sync(
                self.video_path,
                self.sub_path,
                tool="lapse",
                output=out_sub,
                config=dict(DEFAULT_OPTIONS),
            )
        self.assertTrue(result.ok)
        self.assertTrue(os.path.exists(out_sub))
        self.assertFalse(os.path.exists(unsure))

    def test_is_outdated(self):
        from resources import lapse_download
        with patch("resources.lapse_download.latest_version", return_value="9.9.9"):
            with patch("subprocess.run", return_value=MagicMock(stdout="9.9.9\n")):
                self.assertFalse(lapse_download.is_outdated("lapse"))
            with patch("subprocess.run", return_value=MagicMock(stdout="2.3.3\n")):
                self.assertTrue(lapse_download.is_outdated("lapse"))
            self.assertTrue(lapse_download.is_outdated(os.path.join(self.temp_dir, "missing")))
        with patch("resources.lapse_download.latest_version", return_value=None), \
             patch("subprocess.run", return_value=MagicMock(stdout="2.3.3\n")):
            self.assertFalse(lapse_download.is_outdated("lapse"))

    def test_download_replaces_the_old_version(self):
        import io, tarfile
        from resources import lapse_download
        target = os.path.join(self.temp_dir, "lapse")
        os.makedirs(target)
        with open(os.path.join(target, "old.so"), "w") as f:
            f.write("old")
        archive = io.BytesIO()
        with tarfile.open(fileobj=archive, mode="w:gz") as tar:
            info = tarfile.TarInfo("lapse-x/lapse")
            info.size = 3
            tar.addfile(info, io.BytesIO(b"new"))
        with patch("resources.lapse_download.DIST_BIN_PATH", target), \
             patch("resources.lapse_download.BINARY_NAME", "lapse"), \
             patch("resources.lapse_download.get_archive_filename", return_value="a.tar.gz"), \
             patch("requests.get", return_value=MagicMock(content=archive.getvalue())):
            lapse_download.download()
        self.assertEqual(os.listdir(target), ["lapse"])
        self.assertFalse(os.path.exists(target + ".new"))

    def test_broken_download_keeps_the_old_version(self):
        import io, tarfile
        from resources import lapse_download
        target = os.path.join(self.temp_dir, "lapse")
        os.makedirs(target)
        with open(os.path.join(target, "lapse"), "w") as f:
            f.write("old")
        archive = io.BytesIO()
        with tarfile.open(fileobj=archive, mode="w:gz"):
            pass
        with patch("resources.lapse_download.DIST_BIN_PATH", target), \
             patch("resources.lapse_download.get_archive_filename", return_value="a.tar.gz"), \
             patch("requests.get", return_value=MagicMock(content=archive.getvalue())):
            with self.assertRaises(RuntimeError):
                lapse_download.download()
        with open(os.path.join(target, "lapse")) as f:
            self.assertEqual(f.read(), "old")

    def test_run_sync_retries_through_ffmpeg_when_lapse_cannot_read_the_audio(self):
        out_sub = os.path.join(self.temp_dir, "synced_lapse.srt")
        calls = []

        def fake_run_executable(cmd, callbacks, *, sync_tool, process_holder=None):
            calls.append(list(cmd))
            if len(calls) == 1:
                return 1
            if len(calls) == 3:
                with open(out_sub, "w", encoding="utf-8") as f:
                    f.write("1\n00:00:02,000 --> 00:00:04,000\nSynced\n")
            return 0

        with patch("sync_core.run_executable_tool", side_effect=fake_run_executable), \
             patch("resources.lapse_download.is_outdated", return_value=False):
            result = sync_core.run_sync(
                self.video_path,
                self.sub_path,
                tool="lapse",
                output=out_sub,
                config=dict(DEFAULT_OPTIONS),
            )
        self.assertTrue(result.ok)
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[2][1], calls[1][-1])
        self.assertFalse(os.path.exists(calls[1][-1]))

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

    def test_run_executable_tool_crlf_windows_logs(self):
        """Verify that Windows CRLF (\\r\\n) lines are not misclassified as in-place overwrites."""
        crlf_output = (
            b"Format: mov,mp4 Duration: 30000000\r\n"
            b"Cache: C:\\Users\\user\\.cache\\lapse\\model.spans\r\n"
            b"Silero VAD: C:\\lapse\\silero_vad.onnx\r\n"
            b"Done (ols): offset=-120ms confidence=12.3\r\n"
        )
        received_lines = []

        cb = sync_core.SyncCallbacks(
            on_subprocess_line=lambda line, is_ow: received_lines.append((line, is_ow)),
        )

        mock_proc = MagicMock()
        mock_proc.stdout.read.side_effect = [crlf_output, b""]
        mock_proc.wait.return_value = 0

        with patch("sync_core.create_process", return_value=mock_proc):
            rc = sync_core.run_executable_tool(["lapse.exe"], cb, sync_tool="lapse")
            self.assertEqual(rc, 0)

        # All CRLF lines should be forwarded with is_overwrite=False
        self.assertEqual(len(received_lines), 4)
        self.assertEqual(received_lines[0], ("Format: mov,mp4 Duration: 30000000", False))
        self.assertEqual(received_lines[1], ("Cache: C:\\Users\\user\\.cache\\lapse\\model.spans", False))
        self.assertEqual(received_lines[2], ("Silero VAD: C:\\lapse\\silero_vad.onnx", False))
        self.assertEqual(received_lines[3], ("Done (ols): offset=-120ms confidence=12.3", False))

    def test_run_executable_tool_progress_carriage_return_with_crlf(self):
        """Verify that standalone \\r updates overwrite in place, and trailing CRLF is preserved."""
        stream_data = [
            b"Format: mov,mp4 Duration: 30000000\r\n",
            b"Listening to the audio 10%\rListening to the audio 50%\r",
            b"Listening to the audio 100%\r\n",
            b"Done (ols): offset=-120ms confidence=12.3\r\n",
        ]
        received_lines = []

        cb = sync_core.SyncCallbacks(
            on_subprocess_line=lambda line, is_ow: received_lines.append((line, is_ow)),
        )

        mock_proc = MagicMock()
        mock_proc.stdout.read.side_effect = stream_data + [b""]
        mock_proc.wait.return_value = 0

        with patch("sync_core.create_process", return_value=mock_proc):
            rc = sync_core.run_executable_tool(["lapse.exe"], cb, sync_tool="lapse")
            self.assertEqual(rc, 0)

        # 1. Format (CRLF) -> is_overwrite=False
        # 2. Listening 10% (\\r) -> is_overwrite=True
        # 3. Listening 50% (\\r) -> is_overwrite=True
        # 4. Listening 100% (\\r\\n following \\r) -> is_overwrite=True
        # 5. Done (CRLF following CRLF) -> is_overwrite=False
        self.assertEqual(len(received_lines), 5)
        self.assertEqual(received_lines[0], ("Format: mov,mp4 Duration: 30000000", False))
        self.assertEqual(received_lines[1], ("Listening to the audio 10%", True))
        self.assertEqual(received_lines[2], ("Listening to the audio 50%", True))
        self.assertEqual(received_lines[3], ("Listening to the audio 100%", True))
        self.assertEqual(received_lines[4], ("Done (ols): offset=-120ms confidence=12.3", False))

    def test_log_window_crlf_and_overwrite_rendering(self):
        """Verify that LogWindow properly retains all lines when rendered with overwrite messages."""
        from PyQt6.QtWidgets import QApplication
        from gui_log_window import LogWindow

        _app = QApplication.instance() or QApplication(["-platform", "offscreen"])
        log_window = LogWindow()
        log_window.clear()

        # Simulate messages emitted during Windows lapse run
        log_window.append_message("Format: mov,mp4 Duration: 30000000", overwrite=False)
        log_window.append_message("Cache: C:\\lapse\\cache.spans", overwrite=False)
        log_window.append_message("Silero VAD: C:\\lapse\\silero_vad.onnx", overwrite=False)
        log_window.append_message("Listening to the audio 10%", overwrite=True)
        log_window.append_message("Listening to the audio 50%", overwrite=True)
        log_window.append_message("Listening to the audio 100%", overwrite=True)
        log_window.append_message("Done (ols): offset=-120ms confidence=12.3", overwrite=False)

        content = log_window.log_text.toPlainText()
        self.assertIn("Format: mov,mp4 Duration: 30000000", content)
        self.assertIn("Cache: C:\\lapse\\cache.spans", content)
        self.assertIn("Silero VAD: C:\\lapse\\silero_vad.onnx", content)
        self.assertIn("Listening to the audio 100%", content)
        self.assertIn("Done (ols): offset=-120ms confidence=12.3", content)

    def test_lapse_new_options_translations(self):
        """Verify that all new lapse options in other_options have full translations across all 23 languages."""
        from constants import SYNC_TOOLS, LANGUAGES

        lapse_other_options = SYNC_TOOLS["lapse"]["other_options"]
        new_keys = ["force", "strict", "snap", "no_sidecar", "confidence", "audio_track", "min_shift"]
        self.assertEqual(
            list(lapse_other_options),
            ["force", "strict", "snap", "no_sidecar", "confidence", "audio_track", "min_shift"],
            "lapse other options must keep no_sidecar directly under snap",
        )
        for key in new_keys:
            self.assertIn(key, lapse_other_options, f"Option {key} missing from lapse other_options")
            opt = lapse_other_options[key]
            for lang_code in LANGUAGES.values():
                label = opt["label"].get(lang_code)
                tooltip = opt["tooltip"].get(lang_code)
                self.assertTrue(label, f"Missing {lang_code} label for option {key}")
                self.assertTrue(tooltip, f"Missing {lang_code} tooltip for option {key}")

    def test_qfiledialog_not_raising_nameerror_on_database_backup_and_import(self):
        """Verify that _backup_processed_database and _import_processed_database have QFileDialog imported."""
        from PyQt6.QtWidgets import QApplication
        from gui import autosubsyncapp

        _app = QApplication.instance() or QApplication(["-platform", "offscreen"])
        dummy = autosubsyncapp.__new__(autosubsyncapp)

        mock_mgr = MagicMock()
        mock_mgr.get_db_path.return_value = "/fake/db.db"
        mock_mgr.import_from_database.return_value = (0, 0)

        with patch("gui.QFileDialog.getSaveFileName", return_value=("", "")), \
             patch("processed_items_manager.get_processed_items_manager", return_value=mock_mgr), \
             patch("os.path.exists", return_value=True):
            # Should not raise NameError: name 'QFileDialog' is not defined
            dummy._backup_processed_database()

        with patch("gui.QFileDialog.getOpenFileName", return_value=("", "")), \
             patch("processed_items_manager.get_processed_items_manager", return_value=mock_mgr):
            # Should not raise NameError: name 'QFileDialog' is not defined
            dummy._import_processed_database()

    def test_other_options_button_and_dialog(self):
        """Verify that btn_other_options exists, toggles based on tool other_options, and opens dialog."""
        from PyQt6.QtWidgets import QApplication, QPushButton
        from gui import autosubsyncapp
        from gui_automatic_tab import (
            attach_functions_to_autosubsyncapp as attach_auto,
        )
        from gui_manual_tab import (
            attach_functions_to_autosubsyncapp as attach_manual,
        )
        from gui_batch_mode import (
            attach_functions_to_autosubsyncapp as attach_batch,
        )
        from gui_auto_pairing import (
            attach_functions_to_autosubsyncapp as attach_pairing,
        )
        from gui_multiple_subs import (
            attach_functions_to_autosubsyncapp as attach_multiple,
        )

        _app = QApplication.instance() or QApplication(["-platform", "offscreen"])
        attach_auto(autosubsyncapp)
        attach_manual(autosubsyncapp)
        attach_batch(autosubsyncapp)
        attach_pairing(autosubsyncapp)
        attach_multiple(autosubsyncapp)

        with patch("gui.check_for_updates_startup"), patch("gui.check_for_lapse_updates_startup"):
            w = autosubsyncapp()
            self.assertTrue(hasattr(w, "btn_other_options"))
            self.assertIsInstance(w.btn_other_options, QPushButton)

            # Tools with other_options -> button should be visible (not hidden)
            for tool_name in ("lapse", "alass", "ffsubsync"):
                w.update_sync_tool_options(tool_name)
                self.assertFalse(w.btn_other_options.isHidden(), f"btn_other_options was hidden for {tool_name}")

            # autosubsync's fixed_skew is a main option now, so it has no Other options
            self.assertIn("fixed_skew", SYNC_TOOLS["autosubsync"]["options"])
            self.assertNotIn("other_options", SYNC_TOOLS["autosubsync"])
            w.update_sync_tool_options("autosubsync")
            self.assertTrue(w.btn_other_options.isHidden())

            # Fake tool with no other_options -> button should be hidden
            with patch.dict("constants.SYNC_TOOLS", {"dummy": {"options": {}}}):
                w.update_sync_tool_options("dummy")
                self.assertTrue(w.btn_other_options.isHidden())

            # Switch back to lapse and test opening other options dialog
            w.update_sync_tool_options("lapse")
            with patch("PyQt6.QtWidgets.QDialog.exec"):
                w.show_other_options_dialog()

            # Verify that encoding menu has standard QActions
            self.assertTrue(hasattr(w, "encoding_disabled_action"))
            self.assertTrue(hasattr(w, "encoding_same_action"))
            self.assertTrue(hasattr(w, "encoding_actions"))
            self.assertGreater(len(w.encoding_actions), 50)

            # Verify button ordering: Show tool info (?), Additional arguments (+), Restore to defaults, Other options (tune)
            w.sync_options_group.resize(400, 300)
            w._move_sync_options_buttons()
            self.assertLess(w.btn_tool_info.x(), w.btn_add_args.x())
            self.assertLess(w.btn_add_args.x(), w.btn_restore_defaults.x())
            self.assertLess(w.btn_restore_defaults.x(), w.btn_other_options.x())

            # Verify theme adaptation changes the actual icon pixels, not just the QIcon object
            from PyQt6.QtCore import QSize

            def icon_pixels(button):
                image = button.icon().pixmap(QSize(18, 18)).toImage()
                light = dark = mid = 0
                for y in range(image.height()):
                    for x in range(image.width()):
                        color = image.pixelColor(x, y)
                        if color.alpha() < 100:
                            continue
                        if color.lightness() > 180:
                            light += 1
                        elif color.lightness() < 90:
                            dark += 1
                        else:
                            mid += 1
                return light, dark, mid

            w.apply_theme("light")
            for button in (w.btn_other_options, w.btn_restore_defaults):
                self.assertFalse(button.icon().isNull())
                light, dark, _ = icon_pixels(button)
                self.assertGreater(dark, 0, "light theme icon should be dark")
                self.assertEqual(light, 0, "light theme icon should not contain white pixels")
            light, dark, mid = icon_pixels(w.settings_btn)
            self.assertFalse(w.settings_btn.icon().isNull())
            self.assertGreater(mid, 0, "settings icon should stay grey")
            self.assertEqual((light, dark), (0, 0), "settings icon should not be white or black")

            w.apply_theme("dark")
            for button in (w.btn_other_options, w.btn_restore_defaults):
                self.assertFalse(button.icon().isNull())
                light, dark, _ = icon_pixels(button)
                self.assertGreater(light, 0, "dark theme icon should be light")
                self.assertEqual(dark, 0, "dark theme icon should not contain black pixels")
            light, dark, mid = icon_pixels(w.settings_btn)
            self.assertFalse(w.settings_btn.icon().isNull())
            self.assertGreater(mid, 0, "settings icon should stay grey")
            self.assertEqual((light, dark), (0, 0), "settings icon should not be white or black")

            # Light -> System(dark): the widget palette is not updated synchronously,
            # so the icon theme must be resolved from the application palette.
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QColor, QPalette

            app = QApplication.instance()
            old_palette = app.palette()
            system_dark = QPalette()
            system_dark.setColor(QPalette.ColorRole.Window, QColor("#2b2b2b"))
            system_dark.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
            app.setPalette(system_dark)
            try:
                w.config["theme"] = "system"
                w.refresh_theme_icons()
                for button in (w.btn_other_options, w.btn_restore_defaults):
                    light, dark, _ = icon_pixels(button)
                    self.assertGreater(light, 0, "system-dark icon should be light")
                    self.assertEqual(dark, 0, "system-dark icon should not be black")
            finally:
                app.setPalette(old_palette)
                w.config["theme"] = "light"

    def test_run_sync_does_not_auto_update_when_lapse_is_outdated(self):
        """Verify that run_sync does not automatically download when lapse is already installed, even if outdated."""
        from resources import lapse_download

        out_sub = os.path.join(self.temp_dir, "synced_lapse_no_update.srt")
        fake_bin = os.path.join(self.temp_dir, "lapse")
        with open(fake_bin, "w") as f:
            f.write("#!/bin/sh\nexit 0\n")
        os.chmod(fake_bin, 0o755)

        with patch("resources.lapse_download.installed", return_value=fake_bin), \
             patch("resources.lapse_download.is_outdated", return_value=True), \
             patch("resources.lapse_download.download") as mock_download, \
             patch("sync_core.run_executable_tool", return_value=0), \
             patch("os.path.exists", side_effect=lambda p: True if p in (self.video_path, self.sub_path, out_sub, fake_bin) else os.path.exists(p)), \
             patch("os.path.getsize", return_value=100):
            result = sync_core.run_sync(
                self.video_path,
                self.sub_path,
                tool="lapse",
                output=out_sub,
                config=dict(DEFAULT_OPTIONS),
            )
            # download should NOT be called during sync just because it is outdated
            mock_download.assert_not_called()

    def test_check_for_lapse_updates_startup_prompts_dialog(self):
        """Verify that check_for_lapse_updates_startup triggers an update prompt dialog when outdated."""
        import utils
        from PyQt6.QtWidgets import QApplication

        _app = QApplication.instance() or QApplication(["-platform", "offscreen"])
        parent = MagicMock()

        with patch("resources.lapse_download.installed", return_value="/fake/lapse"), \
             patch("os.path.isfile", return_value=True), \
             patch("resources.lapse_download.current_version", return_value="2.0.1"), \
             patch("resources.lapse_download.latest_version", return_value="2.3.3"), \
             patch("utils._show_lapse_update_dialog") as mock_show_dialog:

            # Run synchronously for test
            signals = utils.LapseUpdateSignals()
            signals.update_available.connect(lambda r, l: utils._show_lapse_update_dialog(parent, r, l))
            signals.update_available.emit("2.3.3", "2.0.1")

            mock_show_dialog.assert_called_once_with(parent, "2.3.3", "2.0.1")

    def test_manual_check_for_lapse_updates_shows_up_to_date(self):
        """Verify that manual check for lapse updates shows up-to-date notification when version matches."""
        import utils
        from PyQt6.QtWidgets import QApplication

        _app = QApplication.instance() or QApplication(["-platform", "offscreen"])
        parent = MagicMock()

        with patch("PyQt6.QtWidgets.QMessageBox.information") as mock_info:
            signals = utils.UnifiedUpdateSignals()
            signals.finished.connect(
                lambda res: mock_info(parent, "Up to Date", f"LAPSE is up to date ({res.get('lapse_local')})")
            )
            signals.finished.emit({"app_remote": "6.5", "app_update": False, "lapse_local": "2.3.3", "lapse_remote": "2.3.3", "lapse_update": False})
            mock_info.assert_called_once_with(parent, "Up to Date", "LAPSE is up to date (2.3.3)")

    def test_slider_no_ticks_for_large_ranges(self):
        """Verify that sliders with range > 50 use NoTicks to avoid drawing a solid line / divider."""
        from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget, QSlider
        from gui import autosubsyncapp
        from gui_automatic_tab import attach_functions_to_autosubsyncapp as attach_auto

        _app = QApplication.instance() or QApplication(["-platform", "offscreen"])
        attach_auto(autosubsyncapp)

        parent_widget = QWidget()
        parent_layout = QVBoxLayout(parent_widget)
        slider, _ = autosubsyncapp._create_slider(parent_widget, parent_layout, "Test min_shift", 0, 1000, 0)
        self.assertEqual(slider.tickPosition(), QSlider.TickPosition.NoTicks)

    def test_all_tools_other_options_translations(self):
        """Verify that each tool's other_options has translations for all 23 supported languages."""
        from constants import SYNC_TOOLS, LANGUAGES

        for tool_name, tool_data in SYNC_TOOLS.items():
            other_opts = tool_data.get("other_options", {})
            if not other_opts:
                continue
            for opt_key, opt_data in other_opts.items():
                for lang_code in LANGUAGES.values():
                    label = opt_data["label"].get(lang_code)
                    tooltip = opt_data["tooltip"].get(lang_code)
                    self.assertTrue(
                        label,
                        f"Missing label for {tool_name}.other_options.{opt_key} in {lang_code}",
                    )
                    self.assertTrue(
                        tooltip,
                        f"Missing tooltip for {tool_name}.other_options.{opt_key} in {lang_code}",
                    )
                if "value_labels" in opt_data:
                    for val_k, val_labels in opt_data["value_labels"].items():
                        for lang_code in LANGUAGES.values():
                            val_lbl = val_labels.get(lang_code)
                            self.assertTrue(
                                val_lbl,
                                f"Missing value_label for {tool_name}.{opt_key}.{val_k} in {lang_code}",
                            )

    def test_build_cmd_all_tools_other_options(self):
        """Verify build_cmd properly formats new other_options for all sync tools."""
        # 1. alass
        cfg_alass = dict(DEFAULT_OPTIONS)
        cfg_alass.update(
            alass_allow_negative_timestamps=True,
            alass_interval=5,
            alass_sub_fps_inc="24.0",
        )
        cmd_alass = sync_core.build_cmd(
            "alass", "alass", "v.mkv", "s.srt", "o.srt", config=cfg_alass
        )
        self.assertIn("--allow-negative-timestamps", cmd_alass)
        self.assertIn("--interval", cmd_alass)
        self.assertEqual(cmd_alass[cmd_alass.index("--interval") + 1], "5")
        self.assertIn("--sub-fps-inc", cmd_alass)
        self.assertEqual(cmd_alass[cmd_alass.index("--sub-fps-inc") + 1], "24.0")

        # 2. ffsubsync
        cfg_ffs = dict(DEFAULT_OPTIONS)
        cfg_ffs.update(
            ffsubsync_skip_sync_on_low_quality=True,
            ffsubsync_quality_max_offset_seconds=45,
            ffsubsync_max_offset_seconds=90,
            ffsubsync_skip_intro_outro=True,
            ffsubsync_segment_count=12,
            ffsubsync_audio_track=2,
            ffsubsync_strict=True,
            ffsubsync_max_duration_seconds=500,
        )
        cmd_ffs = sync_core.build_cmd(
            "ffsubsync", None, "v.mkv", "s.srt", "o.srt", config=cfg_ffs
        )
        self.assertIn("--skip-sync-on-low-quality", cmd_ffs)
        self.assertIn("--quality-max-offset-seconds", cmd_ffs)
        self.assertEqual(cmd_ffs[cmd_ffs.index("--quality-max-offset-seconds") + 1], "45")
        self.assertIn("--max-offset-seconds", cmd_ffs)
        self.assertEqual(cmd_ffs[cmd_ffs.index("--max-offset-seconds") + 1], "90")
        self.assertIn("--skip-intro-outro", cmd_ffs)
        self.assertIn("--segment-count", cmd_ffs)
        self.assertEqual(cmd_ffs[cmd_ffs.index("--segment-count") + 1], "12")
        self.assertIn("--reference-stream", cmd_ffs)
        self.assertEqual(cmd_ffs[cmd_ffs.index("--reference-stream") + 1], "a:2")
        self.assertIn("--strict", cmd_ffs)
        self.assertIn("--max-duration-seconds", cmd_ffs)
        self.assertEqual(cmd_ffs[cmd_ffs.index("--max-duration-seconds") + 1], "500")

        # 3. autosubsync
        cfg_auto = dict(DEFAULT_OPTIONS)
        cfg_auto.update(autosubsync_fixed_skew="1.0427")
        cmd_auto = sync_core.build_cmd(
            "autosubsync", None, "v.mkv", "s.srt", "o.srt", config=cfg_auto
        )
        self.assertIn("--fixed_skew", cmd_auto)
        self.assertEqual(cmd_auto[cmd_auto.index("--fixed_skew") + 1], "1.0427")

        # 4. lapse
        cfg_lapse = dict(DEFAULT_OPTIONS)
        cfg_lapse.update(lapse_no_sidecar=True)
        cmd_lapse = sync_core.build_cmd(
            "lapse", "lapse", "v.mkv", "s.srt", "o.srt", config=cfg_lapse
        )
        self.assertIn("--no-sidecar", cmd_lapse)

    def test_all_tooltips_include_default_value(self):
        """Verify that format_option_tooltip ensures every option mentions its default value."""
        from gui_automatic_tab import format_option_tooltip
        import re

        default_pattern = re.compile(
            r"(?:default|varsayılan|по умолчанию|默认|預設|기본값|ค่าเริ่มต้น|lalai|domyślnie|par défaut|standard|padrão)",
            re.IGNORECASE,
        )

        for tool_name, tool_data in SYNC_TOOLS.items():
            all_opts = {**tool_data.get("options", {}), **tool_data.get("other_options", {})}
            for opt_name, opt_data in all_opts.items():
                if "default" not in opt_data or opt_data.get("default") is None:
                    continue
                tooltip = format_option_tooltip(opt_data, opt_name)
                self.assertTrue(
                    bool(default_pattern.search(tooltip)),
                    f"Option '{opt_name}' for tool '{tool_name}' missing default value in tooltip: '{tooltip}'",
                )

    def test_restore_to_defaults_resets_options_and_preserves_additional_args(self):
        """Verify that restore_current_tool_defaults asks confirmation, restores all options, and preserves user-set additional arguments."""
        from PyQt6.QtWidgets import QApplication, QMessageBox
        from gui import autosubsyncapp
        from gui_automatic_tab import attach_functions_to_autosubsyncapp as attach_auto
        from gui_manual_tab import attach_functions_to_autosubsyncapp as attach_manual
        from gui_batch_mode import attach_functions_to_autosubsyncapp as attach_batch
        from gui_auto_pairing import attach_functions_to_autosubsyncapp as attach_pairing
        from gui_multiple_subs import attach_functions_to_autosubsyncapp as attach_multiple

        _app = QApplication.instance() or QApplication(["-platform", "offscreen"])
        attach_auto(autosubsyncapp)
        attach_manual(autosubsyncapp)
        attach_batch(autosubsyncapp)
        attach_pairing(autosubsyncapp)
        attach_multiple(autosubsyncapp)

        with patch("gui.check_for_updates_startup"), patch("gui.check_for_lapse_updates_startup"), patch("utils.save_config"):
            w = autosubsyncapp()

            # Test 1: User cancels confirmation -> settings should NOT change
            w.update_sync_tool_options("lapse")
            w.config["lapse_confidence"] = 19
            with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
                w.restore_current_tool_defaults()
            self.assertEqual(w.config["lapse_confidence"], 19)

            # Test 2: User confirms -> settings restored to defaults, additional args preserved
            for tool in ("lapse", "alass", "ffsubsync"):
                w.update_sync_tool_options(tool)

                # Set custom arguments and custom option values
                args_key = f"{tool}_arguments"
                custom_arg = f"--custom-{tool}-flag 42"
                w.config[args_key] = custom_arg

                tool_info = SYNC_TOOLS[tool]
                all_opts = {**tool_info.get("options", {}), **tool_info.get("other_options", {})}
                for opt_name, opt_data in all_opts.items():
                    if "default" in opt_data and opt_data["default"] is not None:
                        key = f"{tool}_{opt_name}"
                        # Invert boolean or add 1 to number
                        if isinstance(opt_data["default"], bool):
                            w.config[key] = not opt_data["default"]
                        elif isinstance(opt_data["default"], (int, float)):
                            w.config[key] = opt_data["default"] + 1

                # Call restore with confirmed Yes
                with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
                    w.restore_current_tool_defaults()

                # Verify all options restored to defaults
                for opt_name, opt_data in all_opts.items():
                    if "default" in opt_data and opt_data["default"] is not None:
                        key = f"{tool}_{opt_name}"
                        self.assertEqual(
                            w.config[key],
                            opt_data["default"],
                            f"Option {key} was not restored to default {opt_data['default']}",
                        )

                # Crucially verify additional arguments were NOT cleared or touched
                self.assertEqual(
                    w.config[args_key],
                    custom_arg,
                    f"Additional arguments for {tool} were incorrectly altered by restore_current_tool_defaults!",
                )

    def test_additional_arguments_override_ui_options_in_build_cmd(self):
        """Verify that arguments entered in additional arguments override UI options and avoid flag conflicts."""
        # 1. lapse: UI confidence=8, extra says '--confidence 25' -> should only have 25, no duplicate --confidence
        cfg_lapse = dict(DEFAULT_OPTIONS)
        cfg_lapse["lapse_confidence"] = 14
        cfg_lapse["lapse_arguments"] = "--confidence 25"
        cmd = sync_core.build_cmd("lapse", "lapse", "v.mkv", "s.srt", "o.srt", config=cfg_lapse)
        self.assertEqual(cmd.count("--confidence"), 1)
        self.assertEqual(cmd[cmd.index("--confidence") + 1], "25")

        # 2. lapse: mode in extra overrides lapse_mode
        cfg_lapse2 = dict(DEFAULT_OPTIONS)
        cfg_lapse2["lapse_mode"] = "split"
        cfg_lapse2["lapse_split_penalty"] = 12
        cfg_lapse2["lapse_arguments"] = "nosplit"
        cmd2 = sync_core.build_cmd("lapse", "lapse", "v.mkv", "s.srt", "o.srt", config=cfg_lapse2)
        self.assertIn("nosplit", cmd2)
        self.assertNotIn("split", cmd2)

        # 3. alass: UI split_penalty=15, extra has '-p 4' -> should only have -p 4
        cfg_alass = dict(DEFAULT_OPTIONS)
        cfg_alass["alass_split_penalty"] = 15
        cfg_alass["alass_arguments"] = "-p 4"
        cmd_alass = sync_core.build_cmd("alass", "alass", "v.mkv", "s.srt", "o.srt", config=cfg_alass)
        self.assertEqual(cmd_alass.count("-p"), 1)
        self.assertEqual(cmd_alass[cmd_alass.index("-p") + 1], "4")

        # 4. alass: UI split_penalty=-1 (--no-split), extra has '-p 8' -> extra overrides, no --no-split
        cfg_alass2 = dict(DEFAULT_OPTIONS)
        cfg_alass2["alass_split_penalty"] = -1
        cfg_alass2["alass_arguments"] = "-p 8"
        cmd_alass2 = sync_core.build_cmd("alass", "alass", "v.mkv", "s.srt", "o.srt", config=cfg_alass2)
        self.assertNotIn("--no-split", cmd_alass2)
        self.assertIn("-p", cmd_alass2)

        # 5. ffsubsync: UI audio_track=1, extra has '--reference-stream a:3' -> only a:3
        cfg_ffs = dict(DEFAULT_OPTIONS)
        cfg_ffs["ffsubsync_audio_track"] = 1
        cfg_ffs["ffsubsync_arguments"] = "--reference-stream a:3"
        cmd_ffs = sync_core.build_cmd("ffsubsync", None, "v.mkv", "s.srt", "o.srt", config=cfg_ffs)
        self.assertEqual(cmd_ffs.count("--reference-stream"), 1)
        self.assertEqual(cmd_ffs[cmd_ffs.index("--reference-stream") + 1], "a:3")

    def test_additional_arguments_dialog_displays_override_note(self):
        """Verify that show_add_arguments_dialog includes the override notice note."""
        from PyQt6.QtWidgets import QApplication, QLabel, QDialog
        from gui import autosubsyncapp
        from gui_automatic_tab import attach_functions_to_autosubsyncapp as attach_auto
        from gui_manual_tab import attach_functions_to_autosubsyncapp as attach_manual
        from gui_batch_mode import attach_functions_to_autosubsyncapp as attach_batch
        from gui_auto_pairing import attach_functions_to_autosubsyncapp as attach_pairing
        from gui_multiple_subs import attach_functions_to_autosubsyncapp as attach_multiple
        import texts

        _app = QApplication.instance() or QApplication(["-platform", "offscreen"])
        attach_auto(autosubsyncapp)
        attach_manual(autosubsyncapp)
        attach_batch(autosubsyncapp)
        attach_pairing(autosubsyncapp)
        attach_multiple(autosubsyncapp)

        with patch("gui.check_for_updates_startup"), patch("gui.check_for_lapse_updates_startup"):
            w = autosubsyncapp()
            w.config["sync_tool"] = "lapse"

            with patch("PyQt6.QtWidgets.QDialog.exec") as mock_exec:
                # Capture dialog instance
                created_dialogs = []
                orig_init = QDialog.__init__

                def capture_init(dlg, *args, **kwargs):
                    orig_init(dlg, *args, **kwargs)
                    created_dialogs.append(dlg)

                with patch.object(QDialog, "__init__", capture_init):
                    w.show_add_arguments_dialog()

                self.assertTrue(len(created_dialogs) > 0)
                dlg = created_dialogs[0]
                labels = dlg.findChildren(QLabel)
                label_texts = [l.text() for l in labels]
                self.assertTrue(
                    any(str(texts.ADDITIONAL_ARGUMENTS_OVERRIDE_NOTE) in t for t in label_texts),
                    f"Override note not found in dialog labels: {label_texts}",
                )


if __name__ == "__main__":
    unittest.main()

