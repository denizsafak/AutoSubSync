"""Autosubsync low-quality needs-review flow tests.

autosubsync writes the resynced subtitle even when the fit quality is below
its confidence threshold, then exits with code 1 ("WARNING: low quality of
fit. Wrong subtitle file?"). run_sync must surface that case as a
needs-review success (SyncResult.needs_review, like the LAPSE unsure
verdict flow) instead of a plain failure, while genuine failures — no
warning, or no output written — must keep failing.

The tests fake the module-tool execution (sync_core.run_module_tool) the
same way test_lapse_integration fakes the lapse binary, so no real
autosubsync/torch installation is needed.
"""

import os
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main")))


def _import_sync_core():
    """Import sync_core headless, stubbing GUI-only dependencies if needed.

    Mirrors the graceful stub importer in test_audio_reference.py: a plain
    import is attempted first (development machines with the GUI stack), and
    only on ImportError are PyQt6/requests/webbrowser/platformdirs stubbed.
    """
    try:
        import sync_core  # noqa: F401
    except ImportError:
        class _StubMeta(type):
            def __getattr__(cls, name):
                if name.startswith("__"):
                    raise AttributeError(name)
                return _StubClass

        class _StubClass(metaclass=_StubMeta):
            def __init__(self, *args, **kwargs):
                pass

            def __call__(self, *args, **kwargs):
                return _StubClass()

            def __getattr__(self, name):
                return _StubClass

        class _StubModule(types.ModuleType):
            def __getattr__(self, name):
                if name.startswith("__"):
                    raise AttributeError(name)
                return _StubClass

        for name in ("PyQt6", "PyQt6.QtCore", "requests", "webbrowser"):
            if name not in sys.modules:
                try:
                    __import__(name)
                except ImportError:
                    sys.modules[name] = _StubModule(name)

        if "platformdirs" not in sys.modules:
            try:
                __import__("platformdirs")
            except ImportError:
                stub = _StubModule("platformdirs")
                stub.user_config_dir = lambda *a, **k: tempfile.mkdtemp()
                stub.user_desktop_path = lambda *a, **k: tempfile.mkdtemp()
                sys.modules["platformdirs"] = stub

        core = sys.modules["PyQt6.QtCore"]
        if isinstance(core, _StubModule) and not hasattr(core, "QLocale"):

            class _StubLocale:
                def __init__(self, *args, **kwargs):
                    pass

                def name(self):
                    return "en_US"

                def bcp47Name(self):
                    return "en-US"

                @staticmethod
                def system():
                    return _StubLocale()

            core.QLocale = _StubLocale

        import sync_core
    return sys.modules["sync_core"]


sync_core = _import_sync_core()
from sync_core import SyncCallbacks  # noqa: E402

WARNING_LINE = "WARNING: low quality of fit. Wrong subtitle file?"
OUTPUT_CONTENT = "1\n00:00:02,000 --> 00:00:04,000\nShifted text\n"


class _RecordingCallbacks(SyncCallbacks):
    """SyncCallbacks that records log lines and forwarded subprocess lines.

    on_subprocess_line is set eagerly so run_sync's capture wrapper chains
    this recorder as the "original" handler it forwards to.
    """

    def __init__(self):
        super().__init__()
        self.logs = []
        self.subprocess_lines = []
        self.on_subprocess_line = self._record_subprocess_line

    def _record_subprocess_line(self, line, is_overwrite):
        self.subprocess_lines.append((line, is_overwrite))

    def _log(self, msg, color=None):
        self.logs.append((msg, color))
        super()._log(msg, color)


class TestAutosubsyncNeedsReview(unittest.TestCase):
    """run_sync maps autosubsync's low-quality exit onto needs_review."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="AutoSubSync-ass-needs-review-")
        self.video_path = os.path.join(self.temp_dir, "movie.mkv")
        self.sub_path = os.path.join(self.temp_dir, "movie.srt")
        self.out_path = os.path.join(self.temp_dir, "synced.srt")
        with open(self.video_path, "wb") as f:
            f.write(b"dummy video content")
        with open(self.sub_path, "w", encoding="utf-8") as f:
            f.write("1\n00:00:01,000 --> 00:00:03,000\nHello\n")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _fake_module_tool(self, *, returncode, warn, write_output):
        """Build a run_module_tool stand-in with the requested behaviour."""

        def fake(module_name, args, callbacks, *, sync_tool, process_holder=None):
            if warn:
                callbacks._subprocess_line(WARNING_LINE, False)
            if write_output:
                with open(args[-1], "w", encoding="utf-8") as f:
                    f.write(OUTPUT_CONTENT)
            return returncode

        return fake

    def _run(self, fake_tool, callbacks=None):
        with patch("sync_core.run_module_tool", side_effect=fake_tool):
            return sync_core.run_sync(
                self.video_path,
                self.sub_path,
                tool="autosubsync",
                output=self.out_path,
                config={},
                callbacks=callbacks,
            )

    def test_low_quality_with_output_becomes_needs_review(self):
        callbacks = _RecordingCallbacks()
        result = self._run(
            self._fake_module_tool(returncode=1, warn=True, write_output=True),
            callbacks,
        )
        self.assertTrue(result.ok, result.message)
        self.assertTrue(result.needs_review)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(os.path.exists(self.out_path))
        # The orange explanation was logged and the warning still forwarded.
        self.assertTrue(
            any(color == "orange" for _, color in callbacks.logs), callbacks.logs
        )
        self.assertIn(WARNING_LINE, [line for line, _ in callbacks.subprocess_lines])

    def test_low_quality_without_output_stays_failure(self):
        # Nothing written (e.g. the fit crashed before the resync step).
        result = self._run(
            self._fake_module_tool(returncode=1, warn=True, write_output=False)
        )
        self.assertFalse(result.ok)
        self.assertFalse(result.needs_review)

    def test_failure_with_output_but_no_warning_stays_failure(self):
        # rc=1 with a stray output but no low-quality warning must not be
        # promoted: the output is not a trustworthy autosubsync result.
        result = self._run(
            self._fake_module_tool(returncode=1, warn=False, write_output=True)
        )
        self.assertFalse(result.ok)
        self.assertFalse(result.needs_review)

    def test_success_is_not_flagged(self):
        result = self._run(
            self._fake_module_tool(returncode=0, warn=False, write_output=True)
        )
        self.assertTrue(result.ok)
        self.assertFalse(result.needs_review)

    def test_cancelled_run_is_not_promoted(self):
        callbacks = SyncCallbacks(is_cancelled=lambda: True)
        result = self._run(
            self._fake_module_tool(returncode=1, warn=True, write_output=True),
            callbacks,
        )
        self.assertFalse(result.ok)
        self.assertFalse(result.needs_review)
        self.assertTrue(result.cancelled)

    def test_warning_only_wrapped_for_autosubsync_and_lapse(self):
        # Other tools keep the caller's on_subprocess_line untouched.
        sentinel = object()
        callbacks = SyncCallbacks(on_subprocess_line=sentinel)
        with patch("sync_core.run_module_tool", side_effect=self._fake_module_tool(
                returncode=0, warn=False, write_output=True)):
            sync_core.run_sync(
                self.video_path,
                self.sub_path,
                tool="ffsubsync",
                output=self.out_path,
                config={},
                callbacks=callbacks,
            )
        self.assertIs(callbacks.on_subprocess_line, sentinel)

    def test_output_replaces_input_in_overwrite_mode(self):
        # Overwrite mode routes autosubsync through the temp-output file; a
        # low-quality result must still be promoted into the real output.
        with patch("sync_core.run_module_tool", side_effect=self._fake_module_tool(
                returncode=1, warn=True, write_output=True)):
            result = sync_core.run_sync(
                self.video_path,
                self.sub_path,
                tool="autosubsync",
                output=self.sub_path,  # same as input subtitle -> temp path
                config={"backup_subtitles_before_overwriting": False},
            )
        self.assertTrue(result.ok, result.message)
        self.assertTrue(result.needs_review)
        self.assertEqual(result.output_path, self.sub_path)
        with open(self.sub_path, encoding="utf-8") as f:
            self.assertEqual(f.read(), OUTPUT_CONTENT)


if __name__ == "__main__":
    unittest.main()
