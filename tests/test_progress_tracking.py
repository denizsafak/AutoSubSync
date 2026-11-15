import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "main"))

import sync_core  # noqa: E402


class TestProgressPercentExtraction(unittest.TestCase):
    def test_ignores_percent_in_filenames_and_warnings(self):
        # alass must ignore filenames containing '100%' and match '[...] XX.XX %'
        cleaned, pct = sync_core.process_output(
            "synchronizing '/movies/100% Wolf.srt' to reference file '/movies/99%.mkv'...",
            "alass",
        )
        self.assertIn("100% Wolf.srt", cleaned)
        self.assertIsNone(pct)

        _, pct = sync_core.process_output(
            "3 / 6 [================>--------------------------------] 50.00 % 900.00/s 0s",
            "alass",
        )
        self.assertEqual(pct, 50.0)

        # ffsubsync must ignore filenames containing '100%' and match tqdm / PGS scanner
        _, pct = sync_core.process_output(
            "INFO extracting speech segments from reference '/movies/100% Pure.mkv'...",
            "ffsubsync",
        )
        self.assertIsNone(pct)

        _, pct = sync_core.process_output("  42%|████      | 4.2/10 [00:01<00:01]", "ffsubsync")
        self.assertEqual(pct, 42.0)

        _, pct = sync_core.process_output("Scanning PGS subtitles... 63%", "ffsubsync")
        self.assertEqual(pct, 63.0)

        # lapse matches Listening / slices / cuts / Scanning lines
        _, pct = sync_core.process_output("Listening to the audio 77%", "lapse")
        self.assertEqual(pct, 77.0)
        _, pct = sync_core.process_output("Checking the file in slices 37%", "lapse")
        self.assertEqual(pct, 37.0)
        _, pct = sync_core.process_output("Looking for cuts 91%", "lapse")
        self.assertEqual(pct, 91.0)

        # autosubsync length mismatch warnings must not become sync percentage
        _, pct = sync_core.process_output(
            "WARNING: subtitle and audio lengths differ by 45%. Wrong subtitle file?",
            "autosubsync",
        )
        self.assertIsNone(pct)


class TestSyncProgressTracker(unittest.TestCase):
    def _assert_monotonic_0_to_100(self, recorded):
        self.assertTrue(recorded, "expected at least one progress event")
        self.assertEqual(recorded[0], 0.0)
        self.assertEqual(recorded[-1], 100.0)
        for prev, curr in zip(recorded, recorded[1:]):
            self.assertGreaterEqual(curr, prev, f"progress regressed: {recorded}")

    def test_alass_embedded_prep_then_two_passes_is_monotonic(self):
        recorded = []
        tracker = sync_core.SyncProgressTracker(on_progress=recorded.append, tool="alass")
        tracker.start()
        tracker.handle_prep_stage("probe_streams")
        tracker.handle_prep_stage("extract_embedded")
        for p in (0.0, 25.0, 50.0, 100.0):
            tracker.handle_prep_progress(p)
        tracker.handle_prep_stage("extract_embedded_done")

        # Simulate alass running Guessing framerate ratio + synchronizing
        events = [
            ("Guessing framerate ratio...", None),
            ("1 / 6 [====] 16.67 %", 16.67),
            ("6 / 6 [====] 100.00 %", 100.0),
            ("synchronizing '/tmp/sub.srt' to reference file '/tmp/ref.srt'...", None),
            ("100 / 1000 [==] 10.00 %", 10.0),
            ("500 / 1000 [====] 50.00 %", 50.0),
            ("1000 / 1000 [======] 100.00 %", 100.0),
            ("shifted block of 1000 subtitles", None),
        ]
        for line, pct in events:
            tracker.handle_tool_output("alass", line, pct)
        tracker.finish(True)

        self._assert_monotonic_0_to_100(recorded)
        # Prep + sync should smoothly bridge instead of jumping back to 0 twice
        self.assertTrue(any(80.0 <= p <= 90.0 for p in recorded), recorded)
        self.assertTrue(any(90.0 < p < 100.0 for p in recorded), recorded)

    def test_alass_audio_two_passes_without_prep_never_resets(self):
        recorded = []
        tracker = sync_core.SyncProgressTracker(on_progress=recorded.append, tool="alass")
        tracker.start()
        events = [
            ("extracting audio from reference file '/tmp/movie.mkv'...", None),
            ("Guessing framerate ratio...", None),
            ("2 / 6 [==] 33.33 %", 33.33),
            ("6 / 6 [====] 100.00 %", 100.0),
            ("synchronizing '/tmp/movie.srt' to reference file '/tmp/movie.mkv'...", None),
            ("10 / 100 [=] 10.00 %", 10.0),
            ("50 / 100 [===] 50.00 %", 50.0),
            ("100 / 100 [=====] 100.00 %", 100.0),
        ]
        for line, pct in events:
            tracker.handle_tool_output("alass", line, pct)
        tracker.finish(True)

        self._assert_monotonic_0_to_100(recorded)
        # When "synchronizing" starts at 10%, it must stay above FPS guessing's end
        idx_sync_start = len(
            [p for p in recorded if p < 45.0]
        )
        self.assertGreater(idx_sync_start, 2)
        self.assertEqual(recorded.count(0.0), 1)

    def test_ffsubsync_pgs_with_audio_fallback_is_monotonic(self):
        recorded = []
        tracker = sync_core.SyncProgressTracker(on_progress=recorded.append, tool="ffsubsync")
        tracker.start()
        events = [
            ("INFO Checking video for subtitles stream...", None),
            ("INFO reading PGS timings for stream 0:s:0 from movie.mkv...", None),
            ("Scanning PGS subtitles... 20%", 20.0),
            ("Scanning PGS subtitles... 80%", 80.0),
            ("WARNING PGS subtitle timing extraction failed", None),
            ("INFO extracting speech segments from reference movie.mkv...", None),
            (" 50%|#####     | 30.0/60", 50.0),
            ("100%|##########| 60.0/60", 100.0),
            ("INFO extracting speech segments from subtitles file(s)...", None),
            ("INFO computing alignments...", None),
            ("INFO writing output to out.srt", None),
        ]
        for line, pct in events:
            tracker.handle_tool_output("ffsubsync", line, pct)
        tracker.finish(True)

        self._assert_monotonic_0_to_100(recorded)

    def test_lapse_and_ffmpeg_fallback_never_resets(self):
        recorded = []
        tracker = sync_core.SyncProgressTracker(on_progress=recorded.append, tool="lapse")
        tracker.start()
        events = [
            ("Listening to the audio 25%", 25.0),
            ("Listening to the audio 100%", 100.0),
            ("Lapse could not read this audio, converting it with ffmpeg...", None),
            ("Listening to the audio 50%", 50.0),
            ("Listening to the audio 100%", 100.0),
        ]
        for line, pct in events:
            tracker.handle_tool_output("lapse", line, pct)
        tracker.finish(True)

        self._assert_monotonic_0_to_100(recorded)

    def test_lapse_slices_and_cuts_coalesced_in_log_and_monotonic(self):
        """Newline-delimited lapse slice/cut percentages overwrite in place and drive 0..100 progress."""
        import io
        from unittest.mock import patch, MagicMock
        from gui_log_window import LogWindow
        from PyQt6.QtWidgets import QApplication

        sample_stdout = (
            b"Format: matroska,webm Duration: 10256595000\n"
            b"Reusing the subtitle track we read last time (1454 cues)\n"
            b"Reading 28 chapters as places the film may have been cut\n"
            b"Checking the file in slices 12%\n"
            b"Checking the file in slices 50%\n"
            b"Checking the file in slices 100%\n"
            b"auto: 8 of 8 slices back the offset, 8 sit on a line, 1 group(s)\n"
            b"Looking for cuts 4%\n"
            b"Looking for cuts 52%\n"
            b"Looking for cuts 91%\n"
            b"auto: one offset does not fit the whole file, splitting it\n"
        )
        fake_proc = MagicMock()
        fake_proc.stdout = io.BytesIO(sample_stdout)
        fake_proc.wait.return_value = 0

        _app_qt = QApplication.instance() or QApplication([])
        lw = LogWindow()
        try:
            recorded_pcts = []
            tracker = sync_core.SyncProgressTracker(
                on_progress=recorded_pcts.append, tool="lapse"
            )
            tracker.start()
            lines_seen = []
            cb = sync_core.SyncCallbacks(
                on_subprocess_line=lambda line, ow: (
                    lines_seen.append((line, ow)),
                    lw.append_message(line, overwrite=ow),
                ),
                progress_tracker=tracker,
            )
            with patch("sync_core.create_process", return_value=fake_proc):
                rc = sync_core.run_executable_tool(["lapse", "v.mkv", "s.srt"], cb, sync_tool="lapse")
            self.assertEqual(rc, 0)
            tracker.finish(True)

            self._assert_monotonic_0_to_100(recorded_pcts)
            self.assertEqual(
                [ow for l, ow in lines_seen if l.startswith("Checking the file in slices")],
                [True, True, True],
            )
            self.assertEqual(
                [ow for l, ow in lines_seen if l.startswith("Looking for cuts")],
                [True, True, True],
            )

            plain = lw.log_text.toPlainText()
            self.assertIn("Checking the file in slices 100%", plain)
            self.assertNotIn("Checking the file in slices 12%", plain)
            self.assertNotIn("Checking the file in slices 50%", plain)
            self.assertIn("Looking for cuts 91%", plain)
            self.assertNotIn("Looking for cuts 4%", plain)
            self.assertNotIn("Looking for cuts 52%", plain)
            self.assertIn("auto: 8 of 8 slices back the offset", plain)
        finally:
            lw.close()

    def test_autosubsync_milestones_progress_to_100(self):
        recorded = []
        tracker = sync_core.SyncProgressTracker(on_progress=recorded.append, tool="autosubsync")
        tracker.start()
        for line in (
            "Extracting audio using ffmpeg and reading subtitles...",
            "computing features for 1000 audio samples using 3 parallel process(es)",
            "extracted features of size (1000, 13), performing speech detection",
            "computing best fit with 1000 frames",
            "quality of fit: 12.5, threshold 3.0",
            "Fit complete. Performing resync, writing to out.srt",
            "success!",
        ):
            tracker.handle_tool_output("autosubsync", line, None)
        tracker.finish(True)

        self._assert_monotonic_0_to_100(recorded)
        self.assertGreaterEqual(len(recorded), 7)

    def test_log_window_update_progress_clamps_and_formats(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        from gui_log_window import LogWindow

        _app_qt = QApplication.instance() or QApplication([])
        lw = LogWindow()
        try:
            lw.update_progress(-5)
            self.assertEqual(lw.progress_bar.value(), 0)
            self.assertEqual(lw.progress_bar.minimum(), 0)
            self.assertEqual(lw.progress_bar.maximum(), 100)
            self.assertEqual(lw.progress_bar.format(), "%p%")
            self.assertFalse(lw.progress_bar.isHidden())

            lw.update_progress(42.6, current=2, total=5)
            self.assertEqual(lw.progress_bar.value(), 43)
            self.assertEqual(lw.progress_bar.format(), "%p% (2/5)")

            lw.update_progress(150)
            self.assertEqual(lw.progress_bar.value(), 100)
        finally:
            lw.close()

    def test_batch_mode_progress_is_monotonic_across_items(self):
        """Batch mode must advance smoothly 0..100 across (1/N .. N/N) without resetting to 0."""
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from unittest.mock import patch, MagicMock
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QApplication
        import sync_auto
        from constants import DEFAULT_OPTIONS

        app_qt = QApplication.instance() or QApplication([])

        recorded_updates = []

        class _FakeLogWindow:
            def __init__(self):
                self.cancel_clicked = _DummySignal()
                self.cancel_button = MagicMock()

            def reset_for_new_sync(self):
                pass

            def append_message(self, *args, **kwargs):
                pass

            def update_progress(self, value, current=None, total=None):
                recorded_updates.append((int(value), current, total))

            def handle_batch_completion(self, ok, out, callback, post_success_cb=None, needs_review=False):
                QTimer.singleShot(0, callback)

            def finish_batch_sync(self):
                app_qt.quit()

        class _DummySignal:
            def __init__(self):
                self.slots = []

            def connect(self, fn):
                self.slots.append(fn)

            def disconnect(self):
                self.slots.clear()

        class _FakeBatchTree:
            def __init__(self, pairs):
                self._pairs = pairs

            def get_all_valid_pairs(self):
                return self._pairs

        class _FakeApp:
            def __init__(self, pairs):
                self.config = dict(DEFAULT_OPTIONS, sync_tool="alass")
                self.batch_mode_enabled = True
                self.batch_tree_view = _FakeBatchTree(pairs)
                self.log_window = _FakeLogWindow()

            def restore_auto_sync_tab(self):
                pass

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            pairs = []
            for i in range(3):
                v = os.path.join(tmpdir, f"ep{i+1}.mkv")
                s = os.path.join(tmpdir, f"ep{i+1}.srt")
                with open(v, "wb") as fv:
                    fv.write(b"v")
                with open(s, "w", encoding="utf-8") as fs:
                    fs.write("1\n00:00:01,000 --> 00:00:02,000\nhi\n")
                pairs.append((v, s))

            fake_app = _FakeApp(pairs)

            def _fake_prep(ref, sub, out_dir, **kwargs):
                from subtitle_extractor import SubtitleExtractionResult
                on_stage = kwargs.get("on_stage")
                on_prog = kwargs.get("on_progress")
                if on_stage:
                    on_stage("probe_streams")
                    on_stage("extract_embedded")
                if on_prog:
                    on_prog(50.0)
                    on_prog(100.0)
                if on_stage:
                    on_stage("extract_embedded_done")
                return SubtitleExtractionResult(ref, ref, True)

            def _fake_run_sync(ref, sub, *, tool, output=None, config=None, callbacks=None, process_holder=None):
                tr = callbacks.progress_tracker
                tr.handle_tool_output("alass", "Guessing framerate ratio...", None)
                tr.handle_tool_output("alass", "6 / 6 [====] 100.00 %", 100.0)
                tr.handle_tool_output("alass", f"synchronizing '{sub}' to reference file '{ref}'...", None)
                tr.handle_tool_output("alass", "50 / 100 [====] 50.00 %", 50.0)
                tr.handle_tool_output("alass", "100 / 100 [====] 100.00 %", 100.0)
                tr.finish(True)
                with open(output, "w", encoding="utf-8") as f:
                    f.write("1\n00:00:01,000 --> 00:00:02,000\nhi\n")
                return sync_core.SyncResult(True, output, tool, "ok", 0, 10)

            QTimer.singleShot(5000, app_qt.quit)
            with patch("sync_auto.prepare_sync_reference", side_effect=_fake_prep), \
                 patch("sync_auto.sync_core.run_sync", side_effect=_fake_run_sync), \
                 patch("sync_auto.handle_completion", return_value=True), \
                 patch("sync_auto.determine_output_path", side_effect=lambda app, r, s, *a: s + ".out.srt"), \
                 patch("sync_auto.SyncProcess.cancel", lambda self: None):
                sync_auto.start_sync_process(fake_app)
                app_qt.exec()

            self.assertTrue(recorded_updates)
            values = [v for v, _c, _t in recorded_updates]
            self.assertEqual(values[0], 0)
            self.assertEqual(values[-1], 100)
            for prev, curr in zip(values, values[1:]):
                self.assertGreaterEqual(curr, prev, f"Batch progress regressed: {recorded_updates}")
            self.assertEqual(
                sorted({(c, t) for _v, c, t in recorded_updates if c is not None}),
                [(1, 3), (2, 3), (3, 3)],
            )


if __name__ == "__main__":
    unittest.main()
