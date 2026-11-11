"""Numbering edge-case tests for output paths (subtitles and converted audio).

Both the subtitle output system (sync_core.determine_output_path) and the
audio-conversion system (sync_core._pick_audio_mp4_target) avoid collisions
with "_2", "_3", ... numbered names. These tests pin down the shared
semantics:

* the first non-existing name is chosen, existing files are never touched,
* unrelated files that merely look numbered (e.g. xxx_2, xxx_101) are
  skipped like any other,
* numbering is unbounded (no cap such as 100), so folders with many
  numbered files still get a valid name,
* stems that already end in numbers/underscores keep working.

determine_output_path additionally has deliberately non-numbered save
modes (overwrite_input_subtitle, save_next_to_video_with_same_filename).
"""

import os
import shutil
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main")))


def _import_sync_core():
    """Import sync_core headless, stubbing GUI-only dependencies if needed.

    Mirrors the graceful stub importer in test_audio_reference.py.
    """
    try:
        import sync_core  # noqa: F401
    except ImportError:
        # The stub must be fully capable (attribute access AND arithmetic on
        # the class itself) because other test modules in the same process
        # may later import GUI modules that evaluate enum arithmetic like
        # ``Qt.ItemDataRole.UserRole + 10`` at class-definition time.
        class _StubMeta(type):
            def __getattr__(cls, name):
                if name.startswith("__"):
                    raise AttributeError(name)
                return _StubClass

            def _stub_op(cls, *args, **kwargs):
                return _StubClass

            __add__ = __radd__ = __sub__ = __rsub__ = _stub_op
            __mul__ = __rmul__ = __truediv__ = __floordiv__ = _stub_op
            __mod__ = __or__ = __ror__ = __and__ = __rand__ = _stub_op
            __xor__ = __rxor__ = __lshift__ = __rshift__ = _stub_op

            def __lt__(cls, other):
                return False

            def __le__(cls, other):
                return True

            def __gt__(cls, other):
                return False

            def __ge__(cls, other):
                return True

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


def _occupy(directory, *names):
    """Create zero-byte files in directory and return their paths."""
    paths = []
    for name in names:
        path = os.path.join(directory, name)
        with open(path, "wb"):
            pass
        paths.append(path)
    return paths


class TestAudioTargetNumbering(unittest.TestCase):
    """_pick_audio_mp4_target picks the first free _N name, unboundedly."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="AutoSubSync-numbering-audio-")
        self.stem = os.path.join(self.temp_dir, "xxx")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_free_name_returned_as_is(self):
        self.assertEqual(sync_core._pick_audio_mp4_target(self.stem),
                         os.path.join(self.temp_dir, "xxx.mp4"))

    def test_occupied_base_skips_to_2(self):
        _occupy(self.temp_dir, "xxx.mp4")
        self.assertEqual(sync_core._pick_audio_mp4_target(self.stem),
                         os.path.join(self.temp_dir, "xxx_2.mp4"))

    def test_unrelated_numbered_files_are_skipped(self):
        # xxx.mp4 and an unrelated xxx_2.mp4 exist: numbering moves past
        # both, leaving them untouched.
        _occupy(self.temp_dir, "xxx.mp4", "xxx_2.mp4")
        self.assertEqual(sync_core._pick_audio_mp4_target(self.stem),
                         os.path.join(self.temp_dir, "xxx_3.mp4"))

    def test_high_numbers_do_not_confuse_first_free_search(self):
        # xxx.mp4 and xxx_101.mp4 exist, everything between is free: the
        # FIRST free candidate (xxx_2.mp4) is chosen, xxx_101 is untouched.
        _occupy(self.temp_dir, "xxx.mp4", "xxx_101.mp4")
        self.assertEqual(sync_core._pick_audio_mp4_target(self.stem),
                         os.path.join(self.temp_dir, "xxx_2.mp4"))

    def test_numbering_is_unbounded_past_100(self):
        # xxx.mp4 plus xxx_2..xxx_121 occupied: must still find xxx_122
        # (a capped search would fail around xxx_100/xxx_101).
        names = ["xxx.mp4"] + [f"xxx_{n}.mp4" for n in range(2, 122)]
        _occupy(self.temp_dir, *names)
        self.assertEqual(sync_core._pick_audio_mp4_target(self.stem),
                         os.path.join(self.temp_dir, "xxx_122.mp4"))

    def test_stem_ending_with_number_101(self):
        # An audio file literally named xxx_101.mp3: its conversion target
        # is xxx_101.mp4, and a collision there numbers on as xxx_101_2.mp4.
        stem = os.path.join(self.temp_dir, "xxx_101")
        self.assertEqual(sync_core._pick_audio_mp4_target(stem),
                         os.path.join(self.temp_dir, "xxx_101.mp4"))
        _occupy(self.temp_dir, "xxx_101.mp4")
        self.assertEqual(sync_core._pick_audio_mp4_target(stem),
                         os.path.join(self.temp_dir, "xxx_101_2.mp4"))

    def test_gap_in_numbering_is_filled(self):
        # xxx.mp4 and xxx_3.mp4 exist (xxx_2 missing): the gap is filled.
        _occupy(self.temp_dir, "xxx.mp4", "xxx_3.mp4")
        self.assertEqual(sync_core._pick_audio_mp4_target(self.stem),
                         os.path.join(self.temp_dir, "xxx_2.mp4"))

    def test_existing_files_are_not_modified(self):
        occupied = _occupy(self.temp_dir, "xxx.mp4", "xxx_2.mp4")

        def read_all(paths):
            contents = []
            for p in paths:
                with open(p, "rb") as f:
                    contents.append(f.read())
            return contents

        before = read_all(occupied)
        sync_core._pick_audio_mp4_target(self.stem)
        self.assertEqual(before, read_all(occupied))


class TestSubtitleOutputNumbering(unittest.TestCase):
    """determine_output_path numbers colliding subtitle outputs the same way."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="AutoSubSync-numbering-sub-")
        self.subtitle = os.path.join(self.temp_dir, "movie.srt")
        with open(self.subtitle, "wb") as f:
            f.write(b"1\n")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _output(self, config=None):
        return sync_core.determine_output_path(
            os.path.join(self.temp_dir, "movie.mkv"),
            self.subtitle,
            config=config or {},
        )

    def test_input_subtitle_collision_numbers_to_2(self):
        # In "save next to input subtitle" mode the base output name IS the
        # input subtitle's name, so it always collides and numbers on.
        self.assertEqual(self._output(),
                         os.path.join(self.temp_dir, "movie_2.srt"))

    def test_free_name_returned_as_is(self):
        subtitle = os.path.join(self.temp_dir, "fresh.srt")
        output = sync_core.determine_output_path(
            os.path.join(self.temp_dir, "movie.mkv"), subtitle, config={}
        )
        self.assertEqual(output, subtitle)

    def test_occupied_extra_name_skips_to_next(self):
        # movie.srt (input) and movie_2.srt both exist -> movie_3.srt.
        _occupy(self.temp_dir, "movie_2.srt")
        self.assertEqual(self._output(),
                         os.path.join(self.temp_dir, "movie_3.srt"))

    def test_unrelated_numbered_files_are_skipped(self):
        _occupy(self.temp_dir, "movie.srt", "movie_2.srt")
        self.assertEqual(self._output(),
                         os.path.join(self.temp_dir, "movie_3.srt"))

    def test_high_numbers_do_not_confuse_first_free_search(self):
        _occupy(self.temp_dir, "movie.srt", "movie_101.srt")
        self.assertEqual(self._output(),
                         os.path.join(self.temp_dir, "movie_2.srt"))

    def test_numbering_is_unbounded_past_100(self):
        names = ["movie.srt"] + [f"movie_{n}.srt" for n in range(2, 122)]
        _occupy(self.temp_dir, *names)
        self.assertEqual(self._output(),
                         os.path.join(self.temp_dir, "movie_122.srt"))

    def test_stem_ending_with_number(self):
        # A subtitle literally named xxx_101.srt collides as xxx_101_2.srt.
        subtitle = os.path.join(self.temp_dir, "xxx_101.srt")
        with open(subtitle, "wb") as f:
            f.write(b"1\n")
        output = sync_core.determine_output_path(
            os.path.join(self.temp_dir, "xxx_101.mkv"), subtitle, config={}
        )
        self.assertEqual(output, os.path.join(self.temp_dir, "xxx_101_2.srt"))

    def test_overwrite_mode_does_not_number(self):
        output = sync_core.determine_output_path(
            os.path.join(self.temp_dir, "movie.mkv"),
            self.subtitle,
            config={"automatic_save_location": "overwrite_input_subtitle"},
        )
        self.assertEqual(output, self.subtitle)

    def test_same_filename_mode_does_not_number(self):
        _occupy(self.temp_dir, "movie.srt")
        output = sync_core.determine_output_path(
            os.path.join(self.temp_dir, "movie.mkv"),
            self.subtitle,
            config={
                "automatic_save_location": "save_next_to_video_with_same_filename",
                "custom_suffix": "",
            },
        )
        self.assertEqual(output, os.path.join(self.temp_dir, "movie.srt"))


if __name__ == "__main__":
    unittest.main()
