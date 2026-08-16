import os
import sys
import tempfile
import unittest
import subprocess
import shutil
import json
from unittest.mock import patch

# Ensure main directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main")))

import texts
from constants import DEFAULT_OPTIONS
import sync_core
import call_autosubsync


class TestAutosubsyncAssConversion(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.video_path = os.path.join(self.temp_dir, "movie.mp4")
        # Generate short audio container for testing
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
            "-c:a", "aac",
            self.video_path,
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Dual-language named .ass subtitle as reported in the issue (subtitle.chs&eng.ass)
        self.ass_path = os.path.join(self.temp_dir, "subtitle.chs&eng.ass")
        ass_content = """[Script Info]
Title: Dual Language Test Subtitle
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,Hello World / 你好世界
Dialogue: 0,0:00:03.50,0:00:04.80,Default,,0,0,0,,Second Line / 第二行
"""
        with open(self.ass_path, "w", encoding="utf-8") as f:
            f.write(ass_content)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_autosubsync_auto_converts_ass_to_srt_before_backend_execution(self):
        """Verify .ass input is auto-converted to .srt before being handed to autosubsync backend."""
        config = dict(DEFAULT_OPTIONS)
        config["sync_tool"] = "autosubsync"
        config["automatic_save_location"] = "save_next_to_input_subtitle"

        executed_cmd_args = []
        logged_messages = []

        def mock_run_module_tool(module_name, cmd_args, callbacks, sync_tool, process_holder=None):
            self.assertEqual(module_name, "call_autosubsync")
            executed_cmd_args.extend(cmd_args)
            # cmd_args structure: [video, subtitle_input, output_path, ...]
            passed_sub = cmd_args[1]
            output_file = cmd_args[2]

            # Verify that subtitle passed to autosubsync backend is an SRT file
            self.assertTrue(passed_sub.endswith(".srt"), f"Expected .srt passed to autosubsync, got {passed_sub}")
            self.assertTrue(os.path.exists(passed_sub), f"Converted srt {passed_sub} does not exist")

            # Verify that the converted SRT has the content from the .ass file
            with open(passed_sub, "r", encoding="utf-8") as f:
                srt_content = f.read()
            self.assertIn("Hello World / 你好世界", srt_content)
            self.assertIn("00:00:01,000 --> 00:00:03,000", srt_content)

            # Simulate successful autosubsync writing synced content
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(srt_content)
            return 0

        callbacks = sync_core.SyncCallbacks(
            on_log=lambda msg, color: logged_messages.append(msg)
        )

        with patch("sync_core.run_module_tool", side_effect=mock_run_module_tool):
            result = sync_core.run_sync(
                self.video_path,
                self.ass_path,
                tool="autosubsync",
                config=config,
                callbacks=callbacks,
            )

            self.assertTrue(result.ok, f"Sync failed: {result.message}")
            self.assertIsNotNone(result.output_path)
            self.assertTrue(os.path.exists(result.output_path))
            self.assertGreater(os.path.getsize(result.output_path), 0)
            self.assertTrue(result.output_path.endswith(".srt"))

            # Verify conversion log message was emitted
            self.assertTrue(any("Converting" in msg for msg in logged_messages))

            # Verify temporary converted .srt was cleaned up
            temp_converted = executed_cmd_args[1]
            self.assertFalse(os.path.exists(temp_converted), f"Temp file {temp_converted} was not cleaned up")

    def test_autosubsync_fails_when_backend_exits_with_code_1_on_empty_or_bad_fit(self):
        """Verify that when autosubsync encounters degenerate fit (code 1), error is surfaced."""
        config = dict(DEFAULT_OPTIONS)
        config["sync_tool"] = "autosubsync"

        def mock_run_module_tool(module_name, cmd_args, callbacks, sync_tool, process_holder=None):
            # Simulate autosubsync returning 1 due to low quality of fit
            return 1

        error_messages = []
        callbacks = sync_core.SyncCallbacks(
            on_error=lambda msg: error_messages.append(msg)
        )

        with patch("sync_core.run_module_tool", side_effect=mock_run_module_tool):
            result = sync_core.run_sync(
                self.video_path,
                self.ass_path,
                tool="autosubsync",
                config=config,
                callbacks=callbacks,
            )

            self.assertFalse(result.ok)
            self.assertEqual(result.returncode, 1)
            self.assertTrue(len(error_messages) > 0)
            self.assertIn("failed", error_messages[0].lower())

    def test_autosubsync_fails_when_output_is_0_bytes_despite_rc_0(self):
        """Verify that if autosubsync produces a 0-byte output file, sync_core marks it as failure."""
        config = dict(DEFAULT_OPTIONS)
        config["sync_tool"] = "autosubsync"
        out_file = os.path.join(self.temp_dir, "empty_out.srt")

        def mock_run_module_tool(module_name, cmd_args, callbacks, sync_tool, process_holder=None):
            # Create a 0-byte file and return 0
            with open(out_file, "w", encoding="utf-8") as f:
                pass
            return 0

        error_messages = []
        callbacks = sync_core.SyncCallbacks(
            on_error=lambda msg: error_messages.append(msg)
        )

        with patch("sync_core.run_module_tool", side_effect=mock_run_module_tool):
            result = sync_core.run_sync(
                self.video_path,
                self.ass_path,
                tool="autosubsync",
                output=out_file,
                config=config,
                callbacks=callbacks,
            )

            self.assertFalse(result.ok)
            self.assertTrue(any("empty" in msg.lower() for msg in error_messages))

    def test_call_autosubsync_cli_entry_positional_args_and_return_code(self):
        """Verify call_autosubsync.cli_entry properly parses positional args and return code."""
        out_target = os.path.join(self.temp_dir, "cli_test_out.srt")

        # Running cli_entry with nonexistent files should exit non-zero and not return 0
        rc = call_autosubsync.cli_entry(["nonexistent.mp4", "nonexistent.srt", out_target])
        self.assertNotEqual(rc, 0)
        self.assertFalse(os.path.exists(out_target))

    def test_cli_sync_autosubsync_with_ass_end_to_end(self):
        """Test assy-cli sync video.mp4 subtitle.chs&eng.ass -o output.ass -t autosubsync --json"""
        out_target = os.path.join(self.temp_dir, "output.ass")
        cmd = [
            sys.executable,
            "-m", "cli",
            "sync",
            self.video_path,
            self.ass_path,
            "-o", out_target,
            "-t", "autosubsync",
            "--json",
        ]
        env = dict(os.environ)
        env["PYTHONPATH"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main"))

        res = subprocess.run(cmd, capture_output=True, text=True, env=env)
        # Note: Since the test audio is a synthetic sine wave, autosubsync evaluates quality of fit.
        # It must exit cleanly with JSON output regardless of pass/fail and NEVER produce a 0-byte file marked ok: true.
        self.assertIn(res.returncode, (0, 1))  # 0 if fit passed, 1 if EXIT_SYNC_FAILED

        stdout_text = res.stdout.strip()
        self.assertTrue(len(stdout_text) > 0, f"Expected stdout JSON, got empty stdout. Stderr: {res.stderr}")
        data = json.loads(stdout_text)
        self.assertEqual(data["input"], self.ass_path)
        self.assertEqual(data["tool"], "autosubsync")

        if data["ok"]:
            self.assertTrue(os.path.exists(out_target))
            self.assertGreater(os.path.getsize(out_target), 0)
        else:
            # When sync fails, output should NOT be a valid 0-byte file claimed as success
            self.assertFalse(data["ok"])
            self.assertIn("failed", data["message"].lower())


if __name__ == "__main__":
    unittest.main()
