"""Audio-reference feature tests (audio files accepted as sync inputs).

Covers the pipeline that lets audio-only files (mp3, flac, ...) act as the
reference side of a sync:

* constants: AUDIO_EXTENSIONS / REFERENCE_MEDIA_EXTENSIONS / the new
  "keep_converted_audio_files" default option,
* texts: the new translation strings and their locale parity,
* pairing: audio files classify as reference files and pair with subtitles,
* subtitle_extractor: embedded-subtitle extraction is skipped for audio,
* sync_core.convert_audio_to_mp4: MP4 conversion (real ffmpeg when
  available), reuse of an existing MP4, the AAC fallback, path handling and
  failure handling,
* sync_core.run_sync end-to-end wiring: conversion invocation, cleanup
  according to keep_converted_audio_files, and failure reporting.

The real-ffmpeg tests are skipped when no ffmpeg binary is available; the
run_sync wiring tests fake both the conversion and the sync tool, so they
run everywhere.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main")))


def _import_core_modules():
    """Import constants/texts/pairing/subtitle_extractor/sync_core headless.

    Tries a plain import first (normal on a development machine with the GUI
    stack installed). When that fails with ImportError, lightweight stubs are
    installed for the GUI-only dependencies (PyQt6, requests, webbrowser,
    platformdirs) and the import is retried. The platformdirs stub must yield
    a real directory because utils passes user_config_dir() to os.makedirs.
    """
    try:
        import constants  # noqa: F401
    except ImportError:
        class _StubMeta(type):
            """Makes attribute access and arithmetic work on the class too.

            GUI modules evaluate enum arithmetic at class-definition time
            (e.g. ``Qt.ItemDataRole.UserRole + 10``), which needs dunder
            support on the stub *class*, i.e. on its metaclass.
            """

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

        for name in (
            "PyQt6",
            "PyQt6.QtCore",
            "requests",
            "webbrowser",
            "platformdirs",
        ):
            if name in sys.modules:
                continue
            try:
                __import__(name)
            except ImportError:
                if name == "platformdirs":
                    stub = _StubModule(name)
                    stub.user_config_dir = lambda *args, **kwargs: tempfile.mkdtemp(
                        prefix="AutoSubSync-test-config-"
                    )
                    stub.user_desktop_path = (
                        lambda *args, **kwargs: tempfile.mkdtemp(
                            prefix="AutoSubSync-test-desktop-"
                        )
                    )
                    sys.modules[name] = stub
                else:
                    sys.modules[name] = _StubModule(name)

        # get_locale() (imported by constants/texts) needs QLocale when the
        # real PyQt6 is absent.
        if "PyQt6.QtCore" in sys.modules and isinstance(
            sys.modules["PyQt6.QtCore"], _StubModule
        ):

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

            sys.modules["PyQt6.QtCore"].QLocale = _StubLocale

        import constants  # noqa: F401

    import constants
    import texts
    import pairing
    import subtitle_extractor
    import sync_core
    return constants, texts, pairing, subtitle_extractor, sync_core


constants, texts, pairing, subtitle_extractor, sync_core = _import_core_modules()

# TranslationDict (a str subclass) exposes the locale table via
# _translations; plain dicts (unlikely) are tolerated for robustness.
def _locale_table(translation):
    return translation._translations if hasattr(translation, "_translations") else translation


FFMPEG = constants.FFMPEG_EXECUTABLE
FFMPEG_AVAILABLE = bool(
    (os.path.isfile(FFMPEG) and os.access(FFMPEG, os.X_OK))
    or shutil.which(FFMPEG)
)


def _make_sine_audio(path, duration=1):
    """Write a real audio file at path using the local ffmpeg."""
    subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", f"sine=frequency=440:duration={duration}", path],
        check=True,
    )


class TestAudioExtensionConstants(unittest.TestCase):
    """AUDIO_EXTENSIONS / REFERENCE_MEDIA_EXTENSIONS / default option."""

    def test_common_audio_formats_covered(self):
        for ext in (".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus",
                    ".wav", ".wma", ".mka"):
            self.assertIn(ext, constants.AUDIO_EXTENSIONS, ext)

    def test_extensions_are_normalized(self):
        for ext in constants.AUDIO_EXTENSIONS:
            self.assertTrue(ext.startswith("."))
            self.assertEqual(ext, ext.lower())

    def test_no_overlap_with_video_or_subtitle_extensions(self):
        self.assertFalse(set(constants.AUDIO_EXTENSIONS) & set(constants.VIDEO_EXTENSIONS))
        self.assertFalse(set(constants.AUDIO_EXTENSIONS) & set(constants.SUBTITLE_EXTENSIONS))

    def test_reference_media_extensions_is_video_plus_audio(self):
        self.assertEqual(
            constants.REFERENCE_MEDIA_EXTENSIONS,
            constants.VIDEO_EXTENSIONS + constants.AUDIO_EXTENSIONS,
        )

    def test_keep_converted_audio_files_default_is_false(self):
        # Mirrors keep_converted_subtitles: converted files are deleted
        # after the sync unless the user opts in.
        self.assertIs(constants.DEFAULT_OPTIONS["keep_converted_audio_files"], False)


class TestAudioTexts(unittest.TestCase):
    """The new translation strings are complete and well-formed."""

    def test_keep_converted_audio_files_locales_match_subtitles(self):
        reference = set(_locale_table(texts.KEEP_CONVERTED_SUBTITLES))
        table = _locale_table(texts.KEEP_CONVERTED_AUDIO_FILES)
        self.assertEqual(set(table), reference)

    def test_converting_audio_to_mp4_locales_match_subtitles(self):
        reference = set(_locale_table(texts.KEEP_CONVERTED_SUBTITLES))
        table = _locale_table(texts.CONVERTING_AUDIO_TO_MP4)
        self.assertEqual(set(table), reference)

    def test_converting_audio_to_mp4_has_filename_placeholder_everywhere(self):
        for locale, message in _locale_table(texts.CONVERTING_AUDIO_TO_MP4).items():
            self.assertIn("{filename}", message, locale)


class TestPairingAudioFiles(unittest.TestCase):
    """Audio files classify as reference files and pair with subtitles."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="AutoSubSync-audio-pairing-")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _touch(self, name):
        path = os.path.join(self.temp_dir, name)
        with open(path, "wb") as f:
            f.write(b"x")
        return path

    def test_is_video_file_accepts_audio_extensions(self):
        for ext in (".mp3", ".flac", ".m4a", ".wav"):
            self.assertTrue(pairing.is_video_file(f"x/song{ext}"), ext)

    def test_is_video_file_case_insensitive(self):
        self.assertTrue(pairing.is_video_file("x/song.MP3"))
        self.assertTrue(pairing.is_video_file("x/song.Flac"))

    def test_is_video_file_rejects_subtitles_and_other_files(self):
        self.assertFalse(pairing.is_video_file("x/song.srt"))
        self.assertFalse(pairing.is_video_file("x/song.ass"))
        self.assertFalse(pairing.is_video_file("x/image.jpg"))
        self.assertFalse(pairing.is_video_file("x/song"))  # no extension

    def test_is_subtitle_file_unchanged(self):
        self.assertTrue(pairing.is_subtitle_file("x/song.srt"))
        self.assertFalse(pairing.is_subtitle_file("x/song.mp3"))

    def test_pair_folder_pairs_audio_with_subtitle(self):
        mp3 = self._touch("song.mp3")
        self._touch("song.srt")
        pairs = pairing.pair_folder(self.temp_dir)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0], (mp3, os.path.join(self.temp_dir, "song.srt")))

    def test_pair_folder_audio_without_subtitle_yields_no_pair(self):
        self._touch("song.mp3")
        self.assertEqual(pairing.pair_folder(self.temp_dir), [])

    def test_pair_folder_mixed_video_and_audio(self):
        video = self._touch("ep1.mkv")
        audio = self._touch("ep2.mp3")
        self._touch("ep1.srt")
        self._touch("ep2.srt")
        pairs = dict(pairing.pair_folder(self.temp_dir))
        self.assertEqual(pairs[video], os.path.join(self.temp_dir, "ep1.srt"))
        self.assertEqual(pairs[audio], os.path.join(self.temp_dir, "ep2.srt"))

    def test_pair_folders_across_directories(self):
        video_dir = tempfile.mkdtemp(prefix="AutoSubSync-audio-vids-")
        try:
            audio = os.path.join(video_dir, "song.mp3")
            with open(audio, "wb") as f:
                f.write(b"x")
            sub = os.path.join(self.temp_dir, "song.srt")
            with open(sub, "wb") as f:
                f.write(b"x")
            pairs = pairing.pair_folders(video_dir, self.temp_dir)
            self.assertEqual(pairs, [(audio, sub)])
        finally:
            shutil.rmtree(video_dir, ignore_errors=True)


class TestShouldExtractSubtitlesAudio(unittest.TestCase):
    """Audio references never go through embedded-subtitle extraction."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="AutoSubSync-audio-extract-")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_audio_reference_skips_extraction(self):
        audio = os.path.join(self.temp_dir, "song.mp3")
        with open(audio, "wb") as f:
            f.write(b"x")
        self.assertFalse(
            subtitle_extractor.should_extract_subtitles(
                audio, "autosubsync", {}, override=True
            )
        )

    def test_video_reference_still_extracts(self):
        video = os.path.join(self.temp_dir, "movie.mkv")
        with open(video, "wb") as f:
            f.write(b"x")
        self.assertTrue(
            subtitle_extractor.should_extract_subtitles(
                video, "autosubsync", {}, override=True
            )
        )


class TestConvertAudioToMp4RealFfmpeg(unittest.TestCase):
    """Real conversion tests; skipped when ffmpeg is unavailable."""

    @classmethod
    def setUpClass(cls):
        if not FFMPEG_AVAILABLE:
            raise unittest.SkipTest("ffmpeg not available")

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="AutoSubSync-audio-convert-")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_wav_converts_to_mp4_next_to_source(self):
        wav = os.path.join(self.temp_dir, "tone.wav")
        _make_sine_audio(wav)
        result = sync_core.convert_audio_to_mp4(wav)
        self.assertEqual(result, os.path.join(self.temp_dir, "tone.mp4"))
        self.assertTrue(os.path.isfile(result))
        self.assertGreater(os.path.getsize(result), 0)

    def test_converted_mp4_has_usable_audio_stream(self):
        wav = os.path.join(self.temp_dir, "tone.wav")
        _make_sine_audio(wav)
        result = sync_core.convert_audio_to_mp4(wav)
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0",
             "-show_entries", "stream=codec_name", "-of", "default=nw=1:nk=1",
             result],
            capture_output=True, text=True,
        )
        self.assertEqual(probe.returncode, 0)
        # Remux keeps the source codec; the AAC fallback re-encodes.
        self.assertIn(probe.stdout.strip(), ("pcm_s16le", "aac"))

    def test_flac_converts_with_usable_audio_stream(self):
        flac = os.path.join(self.temp_dir, "tone.flac")
        wav = os.path.join(self.temp_dir, "tone.wav")
        _make_sine_audio(wav)
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", wav, flac],
                       check=True)
        result = sync_core.convert_audio_to_mp4(flac)
        self.assertIsNotNone(result)
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0",
             "-show_entries", "stream=codec_name", "-of", "default=nw=1:nk=1",
             result],
            capture_output=True, text=True,
        )
        # Modern ffmpeg can store FLAC in MP4 directly (remux); older builds
        # fall back to the AAC re-encode. Both outcomes are valid.
        self.assertIn(probe.stdout.strip(), ("flac", "aac"))

    def test_existing_nonempty_mp4_is_reused_without_ffmpeg(self):
        mp3 = os.path.join(self.temp_dir, "tone.mp3")
        mp4 = os.path.join(self.temp_dir, "tone.mp4")
        with open(mp3, "wb") as f:
            f.write(b"x")
        with open(mp4, "wb") as f:
            f.write(b"previously converted")
        with patch("sync_core.run_executable_tool",
                   side_effect=AssertionError("ffmpeg must not run")):
            self.assertEqual(sync_core.convert_audio_to_mp4(mp3), mp4)

    def test_empty_existing_mp4_is_not_reused(self):
        wav = os.path.join(self.temp_dir, "tone.wav")
        mp4 = os.path.join(self.temp_dir, "tone.mp4")
        _make_sine_audio(wav)
        with open(mp4, "wb"):
            pass  # zero bytes: stale/partial output from a crashed run
        result = sync_core.convert_audio_to_mp4(wav)
        self.assertEqual(result, mp4)
        self.assertGreater(os.path.getsize(mp4), 0)

    def test_uppercase_extension_converts_to_lowercase_mp4_name(self):
        wav = os.path.join(self.temp_dir, "tone.WAV")
        _make_sine_audio(wav)
        result = sync_core.convert_audio_to_mp4(wav)
        self.assertEqual(os.path.basename(result), "tone.mp4")

    def test_multi_dot_basename_keeps_intermediate_dots(self):
        # os.path.splitext strips only the final extension.
        wav = os.path.join(self.temp_dir, "artist.track.one.wav")
        _make_sine_audio(wav)
        result = sync_core.convert_audio_to_mp4(wav)
        self.assertEqual(os.path.basename(result), "artist.track.one.mp4")

    def test_failing_ffmpeg_returns_none_and_leaves_no_target(self):
        wav = os.path.join(self.temp_dir, "tone.wav")
        _make_sine_audio(wav)
        failing = os.path.join(self.temp_dir, "failing-ffmpeg.sh")
        with open(failing, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\nexit 1\n")
        os.chmod(failing, 0o755)
        with patch("sync_core.FFMPEG_EXECUTABLE", failing):
            self.assertIsNone(sync_core.convert_audio_to_mp4(wav))
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir, "tone.mp4")))

    def test_missing_ffmpeg_binary_returns_none(self):
        wav = os.path.join(self.temp_dir, "tone.wav")
        _make_sine_audio(wav)
        with patch("sync_core.FFMPEG_EXECUTABLE",
                   os.path.join(self.temp_dir, "no-such-ffmpeg")):
            self.assertIsNone(sync_core.convert_audio_to_mp4(wav))

    def test_target_collision_with_real_video_is_not_converted_over(self):
        # The reuse check only looks at existence and size, so a genuine
        # video named movie.mp4 next to movie.wav is reused as-is. That is
        # the documented behaviour; assert it stays deterministic.
        wav = os.path.join(self.temp_dir, "tone.wav")
        mp4 = os.path.join(self.temp_dir, "tone.mp4")
        _make_sine_audio(wav)
        with open(mp4, "wb") as f:
            f.write(b"unrelated file")
        with patch("sync_core.run_executable_tool",
                   side_effect=AssertionError("ffmpeg must not run")):
            self.assertEqual(sync_core.convert_audio_to_mp4(wav), mp4)


class _FakeSyncTool:
    """Stands in for a sync tool and records what it was asked to do.

    ffsubsync is a module-type tool (sync_core.run_module_tool) while e.g.
    lapse is an executable tool (sync_core.run_executable_tool), so both
    entry points are faked. ffmpeg conversion commands routed through
    run_executable_tool are executed for real so the conversion pipeline is
    exercised end to end.
    """

    OUTPUT = b"1\n00:00:01,000 --> 00:00:02,000\nhi\n"

    def __init__(self):
        self.tool_references = []  # reference paths handed to the sync tool
        self.ffmpeg_cmds = []

    def exec_call(self, cmd, callbacks, *, sync_tool, process_holder=None):
        if os.path.basename(cmd[0]) == "ffmpeg":
            self.ffmpeg_cmds.append(list(cmd))
            return subprocess.run(cmd, capture_output=True).returncode
        self.tool_references.append(cmd[1])
        # The output follows "-o" in ffsubsync's command structure.
        with open(cmd[cmd.index("-o") + 1], "wb") as f:
            f.write(self.OUTPUT)
        return 0

    def module_call(self, module_name, args, callbacks, *, sync_tool, process_holder=None):
        self.tool_references.append(args[0])
        # The formatted cmd_structure ends with the output path.
        with open(args[-1], "wb") as f:
            f.write(self.OUTPUT)
        return 0


class TestRunSyncAudioReferenceWiring(unittest.TestCase):
    """run_sync end-to-end wiring with a faked sync tool (no ffmpeg needed).

    convert_audio_to_mp4 is faked to create the expected .mp4, isolating the
    wiring under test: conversion trigger, reference replacement, cleanup
    according to keep_converted_audio_files, and failure reporting.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="AutoSubSync-audio-runsync-")
        self.audio = os.path.join(self.temp_dir, "movie.mp3")
        self.subtitle = os.path.join(self.temp_dir, "movie.srt")
        with open(self.audio, "wb") as f:
            f.write(b"audio-bytes")
        with open(self.subtitle, "w", encoding="utf-8") as f:
            f.write("1\n00:00:01,000 --> 00:00:03,000\nHello\n")
        self.mp4 = os.path.join(self.temp_dir, "movie.mp4")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _fake_convert(self):
        def convert(audio_path, callbacks=None, process_holder=None):
            target = os.path.splitext(audio_path)[0] + ".mp4"
            with open(target, "wb") as f:
                f.write(b"converted-mp4")
            return target

        return convert

    def _run(self, fake_tool, config):
        with patch("sync_core.convert_audio_to_mp4", side_effect=self._fake_convert()), \
             patch("sync_core.run_executable_tool", side_effect=fake_tool.exec_call), \
             patch("sync_core.run_module_tool", side_effect=fake_tool.module_call):
            return sync_core.run_sync(
                self.audio,
                self.subtitle,
                tool="ffsubsync",
                output=None,
                config=config,
            )

    def test_audio_reference_is_converted_and_used(self):
        fake = _FakeSyncTool()
        result = self._run(fake, {"keep_converted_audio_files": False})
        self.assertTrue(result.ok, result.message)
        # The sync tool received the converted mp4, not the original mp3.
        self.assertEqual(fake.tool_references, [self.mp4])

    def test_converted_mp4_deleted_when_keep_disabled(self):
        result = self._run(_FakeSyncTool(), {"keep_converted_audio_files": False})
        self.assertTrue(result.ok)
        self.assertFalse(os.path.exists(self.mp4))

    def test_converted_mp4_kept_when_keep_enabled(self):
        result = self._run(_FakeSyncTool(), {"keep_converted_audio_files": True})
        self.assertTrue(result.ok)
        self.assertTrue(os.path.exists(self.mp4))
        self.assertEqual(os.path.getsize(self.mp4), len(b"converted-mp4"))

    def test_conversion_failure_reports_sync_error(self):
        fake = _FakeSyncTool()
        with patch("sync_core.convert_audio_to_mp4", return_value=None), \
             patch("sync_core.run_executable_tool", side_effect=fake.exec_call), \
             patch("sync_core.run_module_tool", side_effect=fake.module_call):
            result = sync_core.run_sync(
                self.audio,
                self.subtitle,
                tool="ffsubsync",
                output=None,
                config={"keep_converted_audio_files": False},
            )
        self.assertFalse(result.ok)
        self.assertEqual(result.returncode, 1)
        self.assertIn(os.path.basename(self.audio), result.message)
        # The sync tool was never invoked.
        self.assertEqual(fake.tool_references, [])

    def test_video_reference_skips_conversion(self):
        video = os.path.join(self.temp_dir, "clip.mkv")
        with open(video, "wb") as f:
            f.write(b"video-bytes")
        fake = _FakeSyncTool()
        with patch("sync_core.convert_audio_to_mp4",
                   side_effect=AssertionError("must not convert video")), \
             patch("sync_core.run_executable_tool", side_effect=fake.exec_call), \
             patch("sync_core.run_module_tool", side_effect=fake.module_call):
            result = sync_core.run_sync(
                video,
                self.subtitle,
                tool="ffsubsync",
                output=None,
                config={"keep_converted_audio_files": False},
            )
        self.assertTrue(result.ok, result.message)
        self.assertEqual(fake.tool_references, [video])

    def test_uppercase_audio_extension_is_recognized(self):
        upper = os.path.join(self.temp_dir, "movie.MP3")
        os.replace(self.audio, upper)
        fake = _FakeSyncTool()
        with patch("sync_core.convert_audio_to_mp4", side_effect=self._fake_convert()), \
             patch("sync_core.run_executable_tool", side_effect=fake.exec_call), \
             patch("sync_core.run_module_tool", side_effect=fake.module_call):
            result = sync_core.run_sync(
                upper,
                self.subtitle,
                tool="ffsubsync",
                output=None,
                config={"keep_converted_audio_files": True},
            )
        self.assertTrue(result.ok, result.message)
        self.assertEqual(fake.tool_references,
                         [os.path.join(self.temp_dir, "movie.mp4")])

    def test_real_conversion_inside_run_sync_when_ffmpeg_available(self):
        """Full path with real ffmpeg: run_sync converts, syncs, cleans up."""
        if not FFMPEG_AVAILABLE:
            self.skipTest("ffmpeg not available")
        _make_sine_audio(self.audio)
        fake = _FakeSyncTool()
        with patch("sync_core.run_executable_tool", side_effect=fake.exec_call), \
             patch("sync_core.run_module_tool", side_effect=fake.module_call):
            result = sync_core.run_sync(
                self.audio,
                self.subtitle,
                tool="ffsubsync",
                output=None,
                config={"keep_converted_audio_files": False},
            )
        self.assertTrue(result.ok, result.message)
        self.assertEqual(len(fake.ffmpeg_cmds), 1)
        self.assertEqual(fake.ffmpeg_cmds[0][-1], self.mp4)
        self.assertEqual(fake.tool_references, [self.mp4])
        self.assertFalse(os.path.exists(self.mp4))

    def test_real_conversion_kept_inside_run_sync_when_enabled(self):
        if not FFMPEG_AVAILABLE:
            self.skipTest("ffmpeg not available")
        _make_sine_audio(self.audio)
        fake = _FakeSyncTool()
        with patch("sync_core.run_executable_tool", side_effect=fake.exec_call), \
             patch("sync_core.run_module_tool", side_effect=fake.module_call):
            result = sync_core.run_sync(
                self.audio,
                self.subtitle,
                tool="ffsubsync",
                output=None,
                config={"keep_converted_audio_files": True},
            )
        self.assertTrue(result.ok, result.message)
        self.assertTrue(os.path.isfile(self.mp4))
        self.assertGreater(os.path.getsize(self.mp4), 0)


class TestGuiFiltersIncludeAudio(unittest.TestCase):
    """GUI reference-side filters and predicates accept audio extensions.

    gui_batch_mode is import-stubbed the same way as gui_auto_pairing in
    test_auto_pairing_patterns.py; only its module-level filter strings and
    helper predicates are checked here, no Qt behaviour.
    """

    @classmethod
    def setUpClass(cls):
        try:
            import gui_batch_mode  # noqa: F401
        except ImportError:
            class _StubMeta(type):
                """Makes attribute access and arithmetic work on the class too."""

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

            for name in (
                "PyQt6", "PyQt6.QtCore", "PyQt6.QtWidgets", "PyQt6.QtGui",
                "requests", "webbrowser",
            ):
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
                    sys.modules["platformdirs"] = stub
            if isinstance(sys.modules.get("PyQt6.QtCore"), _StubModule):
                core = sys.modules["PyQt6.QtCore"]

                class _StubLocale:
                    def __init__(self, *a, **k):
                        pass

                    def name(self):
                        return "en_US"

                    def bcp47Name(self):
                        return "en-US"

                    @staticmethod
                    def system():
                        return _StubLocale()

                core.QLocale = _StubLocale
            import gui_batch_mode
        cls.gbm = sys.modules["gui_batch_mode"]

    def test_video_subtitle_filter_lists_audio_extensions(self):
        for ext in (".mp3", ".flac", ".m4a"):
            self.assertIn(f"*{ext}", self.gbm.VIDEO_SUBTITLE_FILTER)

    def test_video_filter_lists_audio_extensions(self):
        for ext in (".mp3", ".flac", ".m4a"):
            self.assertIn(f"*{ext}", self.gbm.VIDEO_FILTER)

    def test_subtitle_filter_excludes_audio_extensions(self):
        for ext in ("mp3", "flac", "m4a"):
            self.assertNotIn(ext, self.gbm.SUBTITLE_FILTER)

    def test_is_video_file_accepts_audio(self):
        self.assertTrue(self.gbm.is_video_file("x/song.mp3"))
        self.assertFalse(self.gbm.is_video_file("x/song.srt"))

    def test_is_media_file_accepts_audio_and_subtitles(self):
        self.assertTrue(self.gbm.is_media_file("x/song.mp3"))
        self.assertTrue(self.gbm.is_media_file("x/song.srt"))
        self.assertFalse(self.gbm.is_media_file("x/image.jpg"))


if __name__ == "__main__":
    unittest.main()
