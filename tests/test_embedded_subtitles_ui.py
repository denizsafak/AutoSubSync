"""Tests for extracting user-selected embedded subtitles in Normal and Batch modes."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main")))

try:
    from PyQt6.QtCore import QPoint, Qt
    from PyQt6.QtGui import QContextMenuEvent, QMouseEvent
    from PyQt6.QtWidgets import QApplication, QDialog, QMenu
except ImportError:  # pragma: no cover - PyQt6 is a runtime dependency
    QApplication = None
    QDialog = None

import constants
import subtitle_extractor
import texts
import utils


FFMPEG = constants.FFMPEG_EXECUTABLE
FFMPEG_AVAILABLE = bool(
    (os.path.isfile(FFMPEG) and os.access(FFMPEG, os.X_OK)) or shutil.which(FFMPEG)
)


def _create_test_video_with_subtitles(
    temp_dir: str,
    filename: str,
    tracks: list[dict],
) -> str:
    """Create a tiny real video container with the specified embedded subtitle tracks.

    Each track dict supports: ``codec`` (e.g. ``"srt"``, ``"ass"``, ``"mov_text"``),
    ``language``, ``title``, ``default`` (bool), ``forced`` (bool), ``text``.
    """
    video_path = os.path.join(temp_dir, filename)
    cmd = [
        FFMPEG,
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=black:s=64x64:d=2",
    ]
    sub_files = []
    for idx, track in enumerate(tracks):
        sub_path = os.path.join(temp_dir, f"_src_{filename}_{idx}.srt")
        cue_text = track.get("text", f"Hello track {idx + 1}")
        with open(sub_path, "w", encoding="utf-8") as fh:
            fh.write(f"1\n00:00:00,400 --> 00:00:01,600\n{cue_text}\n\n")
        sub_files.append(sub_path)
        cmd.extend(["-i", sub_path])

    cmd.extend(["-map", "0:v:0"])
    for idx in range(len(tracks)):
        cmd.extend(["-map", f"{idx + 1}:s:0"])

    cmd.extend(["-c:v", "mpeg4", "-t", "2"])
    for idx, track in enumerate(tracks):
        codec = track.get("codec", "srt")
        cmd.extend([f"-c:s:{idx}", codec])
        if track.get("language"):
            cmd.extend([f"-metadata:s:s:{idx}", f"language={track['language']}"])
        if track.get("title"):
            cmd.extend([f"-metadata:s:s:{idx}", f"title={track['title']}"])
        dispositions = []
        if track.get("default"):
            dispositions.append("default")
        if track.get("forced"):
            dispositions.append("forced")
        if dispositions:
            cmd.extend([f"-disposition:s:{idx}", "+".join(dispositions)])
        else:
            cmd.extend([f"-disposition:s:{idx}", "0"])

    cmd.append(video_path)
    subprocess.run(cmd, check=True, capture_output=True)
    for sub_path in sub_files:
        os.remove(sub_path)
    return video_path


class TestPickUniquePath(unittest.TestCase):
    """Tests for utils.pick_unique_path collision-free _2, _3 naming."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="AutoSubSync-unique-path-")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_unused_and_numbered_collisions(self):
        base = os.path.join(self.temp_dir, "movie.eng.srt")
        self.assertEqual(utils.pick_unique_path(base), base)

        with open(base, "w", encoding="utf-8") as fh:
            fh.write("existing")
        second = os.path.join(self.temp_dir, "movie.eng_2.srt")
        self.assertEqual(utils.pick_unique_path(base), second)

        with open(second, "w", encoding="utf-8") as fh:
            fh.write("existing 2")
        third = os.path.join(self.temp_dir, "movie.eng_3.srt")
        self.assertEqual(utils.pick_unique_path(base), third)

    def test_reserved_set_prevents_in_batch_collisions(self):
        base = os.path.join(self.temp_dir, "movie.eng.srt")
        reserved: set[str] = set()
        first = utils.pick_unique_path(base, reserved=reserved)
        second = utils.pick_unique_path(base, reserved=reserved)
        third = utils.pick_unique_path(base, reserved=reserved)
        self.assertEqual(first, base)
        self.assertEqual(second, os.path.join(self.temp_dir, "movie.eng_2.srt"))
        self.assertEqual(third, os.path.join(self.temp_dir, "movie.eng_3.srt"))


class TestEmbeddedSubtitleTranslations(unittest.TestCase):
    """Ensure all new translation dictionaries cover every supported locale."""

    def test_new_keys_match_all_supported_locales(self):
        expected_locales = set(constants.LANGUAGES.values())
        new_keys = [
            "USE_EMBEDDED_SUBTITLE",
            "USE_EMBEDDED_SUBTITLES",
            "SYNC_EXTRACTED_TRACKS_AGAINST_AUDIO",
            "EXTRACT_EMBEDDED_SUBTITLES_TOOLTIP",
            "EXTRACT_BUTTON",
            "SELECT_EMBEDDED_SUBTITLE_PROMPT",
            "SELECT_EMBEDDED_SUBTITLES_PROMPT",
            "NO_EXTRACTABLE_EMBEDDED_SUBTITLES",
            "TRACK_LABEL",
            "TITLE_LABEL",
            "FORMAT_LABEL",
            "FLAGS_LABEL",
            "FORCED_LABEL",
            "EXTRACTING_EMBEDDED_SUBTITLES",
            "SELECT_ALL",
        ]
        for key in new_keys:
            val = getattr(texts, key)
            table = getattr(val, "_translations", {})
            self.assertEqual(set(table.keys()), expected_locales, key)
            for locale, text in table.items():
                self.assertTrue(bool(str(text).strip()), f"{key}.{locale}")


@unittest.skipUnless(FFMPEG_AVAILABLE, "ffmpeg/ffprobe executable is required")
class TestEmbeddedSubtitleBackend(unittest.TestCase):
    """Integration tests for probing and extracting embedded subtitles via ffmpeg."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="AutoSubSync-emb-backend-")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_probe_and_extract_multiple_tracks_next_to_mkv(self):
        mkv_path = _create_test_video_with_subtitles(
            self.temp_dir,
            "episode.mkv",
            [
                {
                    "codec": "srt",
                    "language": "eng",
                    "title": "English Full",
                    "default": True,
                    "text": "First English track",
                },
                {
                    "codec": "srt",
                    "language": "eng",
                    "title": "English SDH",
                    "forced": True,
                    "text": "Second English track",
                },
                {
                    "codec": "ass",
                    "language": "tur",
                    "title": "Turkish ASS",
                    "text": "Merhaba dunya",
                },
                {
                    "codec": "webvtt",
                    "language": "und",
                    "text": "Undetermined VTT",
                },
            ],
        )

        probe = subtitle_extractor.probe_embedded_subtitles(mkv_path)
        self.assertIsNone(probe.error)
        self.assertFalse(probe.cancelled)
        self.assertEqual(len(probe.extractable_streams), 4)

        s0, s1, s2, s3 = probe.extractable_streams
        self.assertEqual((s0.language, s0.title, s0.is_default, s0.extension), ("eng", "English Full", True, "srt"))
        self.assertEqual((s1.language, s1.title, s1.is_forced, s1.extension), ("eng", "English SDH", True, "srt"))
        self.assertEqual((s2.language, s2.title, s2.extension), ("tur", "Turkish ASS", "ass"))
        self.assertEqual((s3.language, s3.extension), ("", "vtt"))

        # Pre-create extracted_track1_eng.srt to ensure it is NEVER overwritten
        existing_eng = os.path.join(self.temp_dir, "extracted_track1_eng.srt")
        with open(existing_eng, "w", encoding="utf-8") as fh:
            fh.write("DO NOT OVERWRITE")

        progress_updates = []
        result = subtitle_extractor.extract_selected_embedded_subtitles(
            mkv_path,
            [s0, s1, s2, s3],
            duration_sec=probe.duration_sec,
            on_progress=progress_updates.append,
        )
        self.assertIsNone(result.error)
        self.assertFalse(result.cancelled)
        self.assertEqual(
            result.extracted_files,
            [
                os.path.join(self.temp_dir, "extracted_track1_eng_2.srt"),
                os.path.join(self.temp_dir, "extracted_track2_eng.srt"),
                os.path.join(self.temp_dir, "extracted_track3_tur.ass"),
                os.path.join(self.temp_dir, "extracted_track4_subtitle.vtt"),
            ],
        )
        with open(existing_eng, "r", encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "DO NOT OVERWRITE")
        for path in result.extracted_files:
            self.assertTrue(os.path.isfile(path))
            self.assertGreater(os.path.getsize(path), 0)
        self.assertTrue(any(p == 100.0 for p in progress_updates))

    def test_extract_mov_text_from_mp4(self):
        mp4_path = _create_test_video_with_subtitles(
            self.temp_dir,
            "clip.mp4",
            [{"codec": "mov_text", "language": "spa", "text": "Hola mundo"}],
        )
        probe = subtitle_extractor.probe_embedded_subtitles(mp4_path)
        self.assertIsNone(probe.error)
        self.assertEqual(len(probe.extractable_streams), 1)
        self.assertEqual(probe.extractable_streams[0].codec_name, "mov_text")
        self.assertEqual(probe.extractable_streams[0].extension, "srt")

        res = subtitle_extractor.extract_selected_embedded_subtitles(
            mp4_path, probe.extractable_streams, duration_sec=probe.duration_sec
        )
        self.assertIsNone(res.error)
        self.assertEqual(res.extracted_files, [os.path.join(self.temp_dir, "extracted_track1_spa.srt")])
        with open(res.extracted_files[0], "r", encoding="utf-8") as fh:
            self.assertIn("Hola mundo", fh.read())

    def test_probe_video_without_subtitles_returns_empty(self):
        mkv_path = _create_test_video_with_subtitles(self.temp_dir, "nosubs.mkv", [])
        probe = subtitle_extractor.probe_embedded_subtitles(mkv_path)
        self.assertIsNone(probe.error)
        self.assertEqual(probe.extractable_streams, [])

    def test_probe_missing_video_returns_error(self):
        probe = subtitle_extractor.probe_embedded_subtitles(
            os.path.join(self.temp_dir, "missing.mkv")
        )
        self.assertIsNotNone(probe.error)

    def test_build_extracted_subtitle_path_sanitizes_language(self):
        video_file = os.path.join(self.temp_dir, "film.mkv")
        und_stream = subtitle_extractor.EmbeddedSubtitleStream(
            stream_index="1",
            subtitle_order=1,
            codec_name="subrip",
            extension="srt",
            language="und",
        )
        self.assertEqual(
            subtitle_extractor.build_extracted_subtitle_path(video_file, und_stream),
            os.path.join(self.temp_dir, "extracted_track1_subtitle.srt"),
        )
        unknown_stream = subtitle_extractor.EmbeddedSubtitleStream(
            stream_index="3",
            subtitle_order=3,
            codec_name="subrip",
            extension="srt",
            language="unknown",
        )
        self.assertEqual(
            subtitle_extractor.build_extracted_subtitle_path(video_file, unknown_stream),
            os.path.join(self.temp_dir, "extracted_track3_subtitle.srt"),
        )
        traversal_stream = subtitle_extractor.EmbeddedSubtitleStream(
            stream_index="2",
            subtitle_order=2,
            codec_name="subrip",
            extension="srt",
            language="../en",
        )
        built = subtitle_extractor.build_extracted_subtitle_path(
            video_file, traversal_stream
        )
        self.assertEqual(os.path.dirname(built), self.temp_dir)
        self.assertEqual(os.path.basename(built), "extracted_track2_en.srt")


@unittest.skipIf(QApplication is None, "PyQt6 is required for embedded subtitle UI tests")
class TestEmbeddedSubtitlesDialogUI(unittest.TestCase):
    """Tests for EmbeddedSubtitlesDialog and workflow in single and multi modes."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="AutoSubSync-emb-dlg-")
        self.video_path = os.path.join(self.temp_dir, "movie.mkv")
        with open(self.video_path, "wb") as fh:
            fh.write(b"fake-video")
        self.streams = [
            subtitle_extractor.EmbeddedSubtitleStream(
                stream_index="1",
                subtitle_order=1,
                codec_name="subrip",
                extension="srt",
                language="eng",
                title="English",
                is_default=False,
            ),
            subtitle_extractor.EmbeddedSubtitleStream(
                stream_index="2",
                subtitle_order=2,
                codec_name="ass",
                extension="ass",
                language="jpn",
                title="Japanese Signs",
                is_default=True,
                is_forced=True,
            ),
        ]

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_single_select_dialog_buttons_and_extract(self):
        import gui_embedded_subtitles

        dlg = gui_embedded_subtitles.EmbeddedSubtitlesDialog(
            self.video_path, self.streams, allow_multiple=False
        )
        self.addCleanup(dlg.deleteLater)

        self.assertEqual(dlg.btn_extract.text(), str(texts.EXTRACT_BUTTON))
        self.assertEqual(dlg.btn_cancel.text(), str(texts.CANCEL))
        self.assertTrue(dlg.select_all_checkbox.isHidden())
        # Normal mode must not show checkmarks on items
        for idx in range(dlg.stream_tree.topLevelItemCount()):
            row_item = dlg.stream_tree.topLevelItem(idx)
            self.assertFalse(bool(row_item.flags() & Qt.ItemFlag.ItemIsUserCheckable))
            self.assertIsNone(row_item.data(0, Qt.ItemDataRole.CheckStateRole))
        # Default stream (#2) is pre-selected
        self.assertEqual(dlg.selected_streams(), [self.streams[1]])
        self.assertTrue(dlg.btn_extract.isEnabled())

        # Select the first stream instead
        first_item = dlg.stream_tree.topLevelItem(0)
        dlg.stream_tree.setCurrentItem(first_item)
        first_item.setSelected(True)
        self.assertEqual(dlg.selected_streams(), [self.streams[0]])

        expected_out = os.path.join(self.temp_dir, "extracted_track1_eng.srt")

        # Verify progress label does not duplicate percentage shown in progress bar
        dlg._on_extract_progress(45.0)
        self.assertEqual(dlg.progress_bar.value(), 45)
        self.assertEqual(
            dlg.progress_label.text(), str(texts.EXTRACTING_EMBEDDED_SUBTITLES)
        )
        self.assertNotIn("%", dlg.progress_label.text())

        def fake_extract(video_file, streams, **kwargs):
            with open(expected_out, "w", encoding="utf-8") as fh:
                fh.write("1\n00:00:01,000 --> 00:00:02,000\nExtracted\n")
            return subtitle_extractor.SubtitleSelectionExtractionResult(
                extracted_files=[expected_out]
            )

        with patch.object(
            gui_embedded_subtitles,
            "extract_selected_embedded_subtitles",
            side_effect=fake_extract,
        ):
            dlg.btn_extract.click()
            # Process worker finished signal until dialog closes
            for _ in range(100):
                self.app.processEvents()
                if dlg.result() == QDialog.DialogCode.Accepted:
                    break
                dlg._extract_worker and dlg._extract_worker.wait(50)

        self.assertEqual(dlg.result(), QDialog.DialogCode.Accepted)
        self.assertEqual(dlg.get_extracted_files(), [expected_out])

    def test_multi_select_dialog_checkboxes_and_row_click_toggle(self):
        import gui_embedded_subtitles

        dlg = gui_embedded_subtitles.EmbeddedSubtitlesDialog(
            self.video_path, self.streams, allow_multiple=True
        )
        self.addCleanup(dlg.deleteLater)
        dlg.show()
        self.app.processEvents()

        # With 2+ streams, initially none checked and Extract disabled
        self.assertFalse(dlg.select_all_checkbox.isHidden())
        self.assertEqual(dlg.select_all_checkbox.text(), str(texts.SELECT_ALL))
        self.assertEqual(dlg.select_all_checkbox.checkState(), Qt.CheckState.Unchecked)
        self.assertEqual(dlg.selected_streams(), [])
        self.assertFalse(dlg.btn_extract.isEnabled())

        # Click "Select all" -> all streams checked and Extract enabled
        dlg.select_all_checkbox.click()
        self.assertEqual(dlg.selected_streams(), self.streams)
        self.assertEqual(dlg.select_all_checkbox.checkState(), Qt.CheckState.Checked)
        self.assertTrue(dlg.btn_extract.isEnabled())

        # Click "Select all" again -> all streams deselected and Extract disabled
        dlg.select_all_checkbox.click()
        self.assertEqual(dlg.selected_streams(), [])
        self.assertEqual(dlg.select_all_checkbox.checkState(), Qt.CheckState.Unchecked)
        self.assertFalse(dlg.btn_extract.isEnabled())

        # Partial row toggle shows PartiallyChecked; clicking Select all selects all
        dlg.stream_tree.topLevelItem(0).setCheckState(0, Qt.CheckState.Checked)
        self.assertEqual(
            dlg.select_all_checkbox.checkState(), Qt.CheckState.PartiallyChecked
        )
        dlg.select_all_checkbox.click()
        self.assertEqual(dlg.selected_streams(), self.streams)
        self.assertEqual(dlg.select_all_checkbox.checkState(), Qt.CheckState.Checked)
        dlg.select_all_checkbox.click()
        self.assertEqual(dlg.selected_streams(), [])

        # Clicking row 0 and row 1 anywhere toggles their checkboxes cleanly
        for row_idx in (0, 1):
            item = dlg.stream_tree.topLevelItem(row_idx)
            rect = dlg.stream_tree.visualItemRect(item)
            # Click near the center-right (Title column) away from checkbox indicator
            pos = rect.center()
            event = QMouseEvent(
                QMouseEvent.Type.MouseButtonRelease,
                pos.toPointF(),
                dlg.stream_tree.viewport().mapToGlobal(pos).toPointF(),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
            dlg.stream_tree.mouseReleaseEvent(event)

        self.assertEqual(dlg.selected_streams(), self.streams)
        self.assertTrue(dlg.btn_extract.isEnabled())

        # Cancel leaves no files and rejects
        dlg.btn_cancel.click()
        self.assertEqual(dlg.result(), QDialog.DialogCode.Rejected)
        self.assertEqual(dlg.get_extracted_files(), [])

    def test_workflow_no_compatible_subtitles_informs_user(self):
        import gui_embedded_subtitles

        pgs_only = subtitle_extractor.SubtitleProbeResult(
            streams=[
                subtitle_extractor.EmbeddedSubtitleStream(
                    stream_index="1",
                    subtitle_order=1,
                    codec_name="hdmv_pgs_subtitle",
                    extension=None,
                    language="eng",
                )
            ]
        )
        with patch.object(
            gui_embedded_subtitles,
            "_probe_video_with_progress",
            return_value=pgs_only,
        ), patch.object(gui_embedded_subtitles.QMessageBox, "information") as info_mock:
            res = gui_embedded_subtitles.extract_embedded_subtitles_workflow(
                None, self.video_path, allow_multiple=False
            )
        self.assertIsNone(res)
        info_mock.assert_called_once()


@unittest.skipIf(QApplication is None, "PyQt6 is required for normal/batch UI tests")
class TestNormalAndBatchModeIntegration(unittest.TestCase):
    """Tests for Normal mode InputBox button visibility and Batch mode context menu."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])
        import gui
        from gui_automatic_tab import attach_functions_to_autosubsyncapp as attach_auto
        from gui_batch_mode import attach_functions_to_autosubsyncapp as attach_batch
        from gui_manual_tab import attach_functions_to_autosubsyncapp as attach_manual

        attach_auto(gui.autosubsyncapp)
        attach_manual(gui.autosubsyncapp)
        attach_batch(gui.autosubsyncapp)
        cls.gui = gui

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="AutoSubSync-ui-int-")
        self.video_path = os.path.join(self.temp_dir, "movie.mkv")
        self.audio_path = os.path.join(self.temp_dir, "audio.mp3")
        self.sub_path = os.path.join(self.temp_dir, "movie.srt")
        self.extracted_1 = os.path.join(self.temp_dir, "movie.eng.srt")
        self.extracted_2 = os.path.join(self.temp_dir, "movie.tur.srt")

        with open(self.video_path, "wb") as fh:
            fh.write(b"video")
        with open(self.audio_path, "wb") as fh:
            fh.write(b"audio")
        for p in (self.sub_path, self.extracted_1, self.extracted_2):
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("1\n00:00:01,000 --> 00:00:02,000\nHi\n")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_main_window(self):
        import utils as app_utils

        cfg_dir = os.path.join(self.temp_dir, "cfg")
        os.makedirs(cfg_dir, exist_ok=True)
        app_utils.clear_config_cache()
        self._patches = [
            patch("gui.check_for_updates_startup"),
            patch("gui.check_for_lapse_updates_startup"),
            patch("utils.initialize_static_ffmpeg"),
            patch.object(app_utils, "get_user_config_path", return_value=os.path.join(cfg_dir, "config.json")),
            patch.object(
                app_utils,
                "load_config",
                return_value={"batch_mode": False, "check_updates_startup": False},
            ),
            patch(
                "gui.load_config",
                return_value={"batch_mode": False, "check_updates_startup": False},
            ),
        ]
        for p in self._patches:
            p.start()
            self.addCleanup(p.stop)
        win = self.gui.autosubsyncapp()
        self.addCleanup(win.deleteLater)
        # Prevent startup QTimer(1000) / QTimer(1500) from firing after win is deleted
        return win

    def test_normal_mode_button_visibility_and_assignment(self):
        import gui_automatic_tab

        win = self._create_main_window()
        win.show()
        self.app.processEvents()

        btn = win.subtitle_input.extract_embedded_btn
        self.assertEqual(btn.text(), str(texts.USE_EMBEDDED_SUBTITLE))
        self.assertTrue(btn.isHidden())
        self.assertFalse(hasattr(win.manual_input_box, "extract_embedded_btn"))

        # Add a video in Video/Reference Subtitle while Input Subtitle is empty
        win.video_ref_input.set_file(self.video_path)
        self.app.processEvents()
        self.assertFalse(btn.isHidden())
        # Positioned in bottom-right corner matching goto_folder_btn placement
        self.assertEqual(
            btn.x(),
            win.subtitle_input.width() - btn.width() - 10,
        )
        self.assertEqual(
            btn.y(),
            win.subtitle_input.height() - btn.height() - 10,
        )

        # Adding a subtitle hides extract button and shows Go to folder
        win.subtitle_input.set_file(self.sub_path)
        self.app.processEvents()
        self.assertTrue(btn.isHidden())
        self.assertFalse(win.subtitle_input.goto_folder_btn.isHidden())

        # Clearing Input Subtitle makes extract button reappear
        win.subtitle_input.clear_btn.click()
        self.app.processEvents()
        self.assertFalse(btn.isHidden())

        # Switching reference to audio or subtitle hides extract button
        win.video_ref_input.set_file(self.audio_path)
        self.app.processEvents()
        self.assertTrue(btn.isHidden())

        win.video_ref_input.set_file(self.sub_path)
        self.app.processEvents()
        self.assertTrue(btn.isHidden())

        # Reload video, click extract button -> extracted subtitle populates Input Subtitle
        win.video_ref_input.set_file(self.video_path)
        self.app.processEvents()
        self.assertFalse(btn.isHidden())

        with patch.object(
            gui_automatic_tab,
            "extract_embedded_subtitles_workflow",
            return_value=[self.extracted_1],
        ) as wf_mock:
            btn.click()
        wf_mock.assert_called_once_with(win, self.video_path, allow_multiple=False)
        self.assertEqual(win.subtitle_input.file_path, self.extracted_1)
        self.assertTrue(btn.isHidden())

    def test_batch_mode_context_menu_and_multi_extract(self):
        import gui_batch_mode
        import gui_embedded_subtitles

        win = self._create_main_window()
        win.batch_mode_enabled = True
        tree = win.batch_tree_view

        video_item = gui_batch_mode.create_tree_widget_item(
            self.video_path, None, tree.icon_provider, item_id=tree._get_next_id()
        )
        audio_item = gui_batch_mode.create_tree_widget_item(
            self.audio_path, None, tree.icon_provider, item_id=tree._get_next_id()
        )
        sub_item = gui_batch_mode.create_tree_widget_item(
            self.sub_path, None, tree.icon_provider, item_id=tree._get_next_id()
        )
        tree.addTopLevelItem(video_item)
        tree.addTopLevelItem(audio_item)
        tree.addTopLevelItem(sub_item)
        win.show_auto_sync_inputs()
        win.show()
        self.app.processEvents()

        def menu_actions_for_item(target_item):
            captured = []

            def fake_popup(menu_self, _pos):
                captured.extend(act.text() for act in menu_self.actions() if act.text())

            rect = tree.visualItemRect(target_item)
            event = QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse,
                rect.center(),
                tree.viewport().mapToGlobal(rect.center()),
            )
            with patch.object(QMenu, "popup", fake_popup):
                tree.contextMenuEvent(event)
            return captured

        video_actions = menu_actions_for_item(video_item)
        audio_actions = menu_actions_for_item(audio_item)
        sub_actions = menu_actions_for_item(sub_item)

        self.assertIn(str(texts.USE_EMBEDDED_SUBTITLES), video_actions)
        self.assertNotIn(str(texts.USE_EMBEDDED_SUBTITLES), audio_actions)
        self.assertNotIn(str(texts.USE_EMBEDDED_SUBTITLES), sub_actions)

        # Extracting multiple subtitles attaches them as children of video_item
        with patch.object(
            gui_embedded_subtitles,
            "extract_embedded_subtitles_workflow",
            return_value=[self.extracted_1, self.extracted_2],
        ) as wf_mock:
            tree.extract_embedded_subtitles_for_item(video_item)

        wf_mock.assert_called_once_with(win, self.video_path, allow_multiple=True)
        self.assertEqual(video_item.childCount(), 2)
        self.assertEqual(
            video_item.child(0).data(0, Qt.ItemDataRole.UserRole), self.extracted_1
        )
        self.assertEqual(
            video_item.child(1).data(0, Qt.ItemDataRole.UserRole), self.extracted_2
        )
        self.assertEqual(
            video_item.data(0, gui_batch_mode.BatchTreeView.VALID_STATE_ROLE), "valid"
        )
        self.assertEqual(
            tree.get_all_valid_pairs(),
            [
                (self.video_path, self.extracted_1),
                (self.video_path, self.extracted_2),
            ],
        )

        # Undo cleanly removes the added child items
        self.assertTrue(tree.undo())
        restored_video = tree.find_parent_by_path(self.video_path)
        self.assertIsNotNone(restored_video)
        self.assertEqual(restored_video.childCount(), 0)
        self.assertTrue(tree.redo())
        redone_video = tree.find_parent_by_path(self.video_path)
        self.assertIsNotNone(redone_video)
        self.assertEqual(redone_video.childCount(), 2)

        # Child item right-click must NOT show Use embedded subtitles
        child_actions = menu_actions_for_item(redone_video.child(0))
        self.assertNotIn(str(texts.USE_EMBEDDED_SUBTITLES), child_actions)

    @unittest.skipUnless(FFMPEG_AVAILABLE, "ffmpeg/ffprobe executable is required")
    def test_end_to_end_real_probe_and_dialog_extraction(self):
        import gui_embedded_subtitles

        mkv_path = _create_test_video_with_subtitles(
            self.temp_dir,
            "real_e2e.mkv",
            [
                {"codec": "srt", "language": "eng", "title": "English", "text": "One"},
                {"codec": "ass", "language": "tur", "title": "Turkish", "text": "Iki"},
            ],
        )
        # Pre-occupy extracted_track1_eng.srt to ensure _2 suffix is used
        existing_path = os.path.join(self.temp_dir, "extracted_track1_eng.srt")
        with open(existing_path, "w", encoding="utf-8") as fh:
            fh.write("KEEP ME")

        def auto_accept_dialog(dialog_self):
            # Trigger extraction of the first stream in single-select mode
            dialog_self.stream_tree.topLevelItem(0).setSelected(True)
            dialog_self.stream_tree.setCurrentItem(dialog_self.stream_tree.topLevelItem(0))
            dialog_self._on_extract_clicked()
            for _ in range(200):
                self.app.processEvents()
                if dialog_self.result() == QDialog.DialogCode.Accepted:
                    break
                if dialog_self._extract_worker:
                    dialog_self._extract_worker.wait(50)
            return dialog_self.result()

        with patch.object(
            gui_embedded_subtitles.EmbeddedSubtitlesDialog,
            "exec",
            auto_accept_dialog,
        ):
            extracted = gui_embedded_subtitles.extract_embedded_subtitles_workflow(
                None, mkv_path, allow_multiple=False
            )

        expected_path = os.path.join(self.temp_dir, "extracted_track1_eng_2.srt")
        self.assertEqual(extracted, [expected_path])
        self.assertTrue(os.path.isfile(expected_path))
        with open(existing_path, "r", encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "KEEP ME")
        with open(expected_path, "r", encoding="utf-8") as fh:
            self.assertIn("One", fh.read())

    def test_settings_toggle_exists_and_persists(self):
        win = self._create_main_window()
        action = win.sync_extracted_tracks_against_audio_action
        self.assertIn(action, win.settings_menu.actions())
        self.assertTrue(action.isCheckable())
        self.assertTrue(action.isChecked())
        self.assertEqual(
            action.text(), str(texts.SYNC_EXTRACTED_TRACKS_AGAINST_AUDIO)
        )

        action.trigger()
        self.assertFalse(action.isChecked())
        self.assertFalse(win.config["sync_extracted_tracks_against_audio"])


class TestSyncExtractedTracksAgainstAudio(unittest.TestCase):
    """Tests for disabling embedded subtitle checks when syncing extracted_track* files."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="AutoSubSync-extracted-sync-")
        self.video_path = os.path.join(self.temp_dir, "movie.mkv")
        self.audio_path = os.path.join(self.temp_dir, "song.mp3")
        self.ref_sub_path = os.path.join(self.temp_dir, "reference.srt")
        self.extracted_sub = os.path.join(self.temp_dir, "extracted_track1_eng.srt")
        self.normal_sub = os.path.join(self.temp_dir, "regular.srt")

        with open(self.video_path, "wb") as fh:
            fh.write(b"video")
        with open(self.audio_path, "wb") as fh:
            fh.write(b"audio")
        for p in (self.ref_sub_path, self.extracted_sub, self.normal_sub):
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("1\n00:00:01,000 --> 00:00:02,000\nLine\n\n")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_resolve_config_disables_embedded_for_all_tools_when_enabled(self):
        base_cfg = dict(
            constants.DEFAULT_OPTIONS,
            sync_extracted_tracks_against_audio=True,
            alass_check_video_for_subtitles=True,
            autosubsync_check_video_for_subtitles=True,
            lapse_check_video_for_subtitles=True,
            ffsubsync_use_pgs_subtitles=True,
            ffsubsync_vad="default",
        )
        eff = subtitle_extractor.resolve_sync_config_for_subtitle(
            self.video_path, self.extracted_sub, base_cfg
        )
        # Original dict must not be mutated
        self.assertTrue(base_cfg["alass_check_video_for_subtitles"])
        self.assertEqual(base_cfg["ffsubsync_vad"], "default")

        self.assertFalse(eff["alass_check_video_for_subtitles"])
        self.assertFalse(eff["autosubsync_check_video_for_subtitles"])
        self.assertFalse(eff["lapse_check_video_for_subtitles"])
        self.assertFalse(eff["ffsubsync_use_pgs_subtitles"])
        self.assertEqual(eff["ffsubsync_vad"], "webrtc")

        # Verify command builders honor the effective config
        import sync_core

        ff_cmd = sync_core.build_cmd(
            "ffsubsync", None, self.video_path, self.extracted_sub, "out.srt", config=eff
        )
        self.assertIn("--vad", ff_cmd)
        self.assertEqual(ff_cmd[ff_cmd.index("--vad") + 1], "webrtc")
        self.assertNotIn("--pgs-ref-stream", ff_cmd)

        lapse_cmd = sync_core.build_cmd(
            "lapse", "lapse", self.video_path, self.extracted_sub, "out.srt", config=eff
        )
        self.assertIn("--no-embedded", lapse_cmd)

    def test_resolve_config_respects_subs_then_auditok_and_silero(self):
        for subs_vad, audio_vad in (
            ("subs_then_webrtc", "webrtc"),
            ("subs_then_auditok", "auditok"),
            ("subs_then_silero", "silero"),
            ("auditok", "auditok"),
        ):
            cfg = dict(constants.DEFAULT_OPTIONS, ffsubsync_vad=subs_vad)
            eff = subtitle_extractor.resolve_sync_config_for_subtitle(
                self.video_path, self.extracted_sub, cfg
            )
            self.assertEqual(eff["ffsubsync_vad"], audio_vad)

    def test_resolve_config_noop_when_toggle_disabled_or_non_matching(self):
        disabled_cfg = dict(
            constants.DEFAULT_OPTIONS,
            sync_extracted_tracks_against_audio=False,
            alass_check_video_for_subtitles=True,
            ffsubsync_use_pgs_subtitles=True,
        )
        self.assertIs(
            subtitle_extractor.resolve_sync_config_for_subtitle(
                self.video_path, self.extracted_sub, disabled_cfg
            ),
            disabled_cfg,
        )

        enabled_cfg = dict(constants.DEFAULT_OPTIONS, sync_extracted_tracks_against_audio=True)
        # Non-extracted_track subtitle
        self.assertIs(
            subtitle_extractor.resolve_sync_config_for_subtitle(
                self.video_path, self.normal_sub, enabled_cfg
            ),
            enabled_cfg,
        )
        # Non-video references (audio, subtitle, remote URL)
        for non_vid in (
            self.audio_path,
            self.ref_sub_path,
            "https://example.com/movie.mkv",
        ):
            self.assertIs(
                subtitle_extractor.resolve_sync_config_for_subtitle(
                    non_vid, self.extracted_sub, enabled_cfg
                ),
                enabled_cfg,
            )

    def test_prepare_sync_reference_and_run_sync_skip_embedded_for_extracted_track(self):
        import sync_core

        cfg = dict(
            constants.DEFAULT_OPTIONS,
            sync_extracted_tracks_against_audio=True,
            alass_check_video_for_subtitles=True,
            autosubsync_check_video_for_subtitles=True,
            ffsubsync_use_pgs_subtitles=True,
            ffsubsync_vad="default",
        )
        for tool in ("alass", "autosubsync", "lapse"):
            prep = subtitle_extractor.prepare_sync_reference(
                self.video_path,
                self.extracted_sub,
                self.temp_dir,
                tool=tool,
                config=cfg,
            )
            self.assertFalse(prep.enabled)
            self.assertEqual(prep.effective_reference, self.video_path)

        # run_sync with ffsubsync passes --vad webrtc and skips PGS check
        captured = {}

        def fake_module_tool(mod, args, callbacks, *, sync_tool, process_holder=None):
            captured["args"] = args
            out_idx = args.index("-o") + 1
            with open(args[out_idx], "w", encoding="utf-8") as fh:
                fh.write("1\n00:00:01,000 --> 00:00:02,000\nSynced\n")
            return 0

        out_ff = os.path.join(self.temp_dir, "out_ff.srt")
        with patch("utils.check_pgs_subtitles_usable") as pgs_mock, patch.object(
            sync_core, "run_module_tool", side_effect=fake_module_tool
        ):
            res = sync_core.run_sync(
                self.video_path,
                self.extracted_sub,
                tool="ffsubsync",
                output=out_ff,
                config=cfg,
            )
        self.assertTrue(res.ok)
        pgs_mock.assert_not_called()
        self.assertIn("--vad", captured["args"])
        self.assertEqual(
            captured["args"][captured["args"].index("--vad") + 1], "webrtc"
        )
        self.assertNotIn("--pgs-ref-stream", captured["args"])

        # run_sync with alass skips PGS extraction
        out_alass = os.path.join(self.temp_dir, "out_alass.srt")

        def fake_exec(cmd, callbacks, *, sync_tool, process_holder=None):
            with open(out_alass, "w", encoding="utf-8") as fh:
                fh.write("1\n00:00:01,000 --> 00:00:02,000\nSynced\n")
            return 0

        with patch("utils.extract_pgs_timings_to_srt") as alass_pgs_mock, patch.object(
            sync_core, "run_executable_tool", side_effect=fake_exec
        ):
            res_alass = sync_core.run_sync(
                self.video_path,
                self.extracted_sub,
                tool="alass",
                output=out_alass,
                config=cfg,
            )
        self.assertTrue(res_alass.ok)
        alass_pgs_mock.assert_not_called()

    def test_sync_process_logs_extracted_track_audio_sync_and_toggle_hint(self):
        from types import SimpleNamespace
        import sync_auto
        import sync_core

        # Verify translation dictionary covers all locales and placeholders
        translations = texts.SYNCING_EXTRACTED_TRACK_AGAINST_AUDIO_LOG._translations
        self.assertEqual(set(translations.keys()), set(constants.LANGUAGES.values()))
        for lang, msg in translations.items():
            self.assertIn("{settings}", msg, msg=f"Missing {{settings}} in {lang}")
            self.assertIn("{option}", msg, msg=f"Missing {{option}} in {lang}")

        expected_log = texts.SYNCING_EXTRACTED_TRACK_AGAINST_AUDIO_LOG.format(
            settings=texts.SETTINGS,
            option=texts.SYNC_EXTRACTED_TRACKS_AGAINST_AUDIO,
        )

        class DummySignal:
            def __init__(self, target=None):
                self._target = target

            def emit(self, *args):
                if self._target is not None:
                    self._target.append(args)

        def run_prepare_and_run(sub_path, toggle_enabled):
            logged = []
            app_mock = SimpleNamespace(
                config=dict(
                    constants.DEFAULT_OPTIONS,
                    sync_extracted_tracks_against_audio=toggle_enabled,
                    sync_tool="ffsubsync",
                )
            )
            proc = sync_auto.SyncProcess.__new__(sync_auto.SyncProcess)
            proc.app = app_mock
            proc.reference_path = self.video_path
            proc.subtitle_path = sub_path
            proc.output_path = os.path.join(self.temp_dir, "out.srt")
            proc.should_cancel = False
            proc._process_holder = {}
            proc._extraction = None
            proc.signals = SimpleNamespace(
                log=DummySignal(logged),
                colored_progress=DummySignal(),
                progress_percent=DummySignal(),
                pair_header=DummySignal(),
                error=DummySignal(),
                finished=DummySignal(),
            )

            fake_res = sync_core.SyncResult(
                ok=True,
                output_path=proc.output_path,
                tool_used="ffsubsync",
                message="ok",
                returncode=0,
                elapsed_ms=10,
            )
            with patch.object(
                sync_core, "get_tool_with_fallback", return_value=("ffsubsync", False, None)
            ), patch.object(sync_core, "run_sync", return_value=fake_res):
                proc._prepare_and_run(
                    self.video_path, sub_path, self.temp_dir, "ffsubsync", []
                )
            return logged

        # Enabled + extracted_track* + video -> logs blue hint mentioning toggle
        logs_enabled = run_prepare_and_run(self.extracted_sub, True)
        self.assertIn((expected_log, "blue"), logs_enabled)
        self.assertIn(str(texts.SETTINGS), expected_log)
        self.assertIn(str(texts.SYNC_EXTRACTED_TRACKS_AGAINST_AUDIO), expected_log)

        # Disabled -> does not log hint
        logs_disabled = run_prepare_and_run(self.extracted_sub, False)
        self.assertNotIn((expected_log, "blue"), logs_disabled)

        # Regular subtitle -> does not log hint
        logs_regular = run_prepare_and_run(self.ref_sub_path, True)
        self.assertNotIn((expected_log, "blue"), logs_regular)

    def test_cross_os_and_pypi_edge_cases(self):
        # 1. Overly long language tag metadata is sanitized and clamped
        long_stream = subtitle_extractor.EmbeddedSubtitleStream(
            stream_index="2",
            subtitle_order=1,
            codec_name="subrip",
            extension="srt",
            language="en/" + ("x" * 100),
        )
        out_path = subtitle_extractor.build_extracted_subtitle_path(
            self.video_path, long_stream
        )
        self.assertLessEqual(len(os.path.basename(out_path)), 64)
        self.assertTrue(os.path.basename(out_path).startswith("extracted_track1_"))

        # 2. pick_unique_path skips broken symlinks (lexists)
        if hasattr(os, "symlink"):
            symlink_target = os.path.join(self.temp_dir, "extracted_track1_eng.srt")
            try:
                os.symlink(
                    os.path.join(self.temp_dir, "missing_target.srt"), symlink_target
                )
                self.assertEqual(
                    utils.pick_unique_path(symlink_target),
                    os.path.join(self.temp_dir, "extracted_track1_eng_2.srt"),
                )
            except (OSError, NotImplementedError):
                pass

        # 3. lapse_sub_track is reset to -1 so --sub-track is never passed with --no-embedded
        cfg = dict(
            constants.DEFAULT_OPTIONS,
            sync_extracted_tracks_against_audio=True,
            lapse_check_video_for_subtitles=True,
            lapse_sub_track=3,
        )
        resolved = subtitle_extractor.resolve_sync_config_for_subtitle(
            self.video_path, self.extracted_sub, cfg
        )
        self.assertFalse(resolved["lapse_check_video_for_subtitles"])
        self.assertEqual(resolved["lapse_sub_track"], -1)
        import sync_core

        lapse_cmd = sync_core.build_cmd(
            "lapse", "lapse", self.video_path, self.extracted_sub, self.temp_dir + "/out.srt", config=resolved
        )
        self.assertIn("--no-embedded", lapse_cmd)
        self.assertNotIn("--sub-track", lapse_cmd)

        # 4. Bare executable resolution activates static_ffmpeg paths when available in PyPI mode
        static_dir = os.path.join(self.temp_dir, "static_ff")
        os.makedirs(static_dir, exist_ok=True)
        with patch.object(subtitle_extractor, "NEEDS_STATIC_FFMPEG", True), patch(
            "shutil.which", return_value=None
        ), patch("static_ffmpeg.run.get_platform_dir", return_value=static_dir), patch(
            "static_ffmpeg.add_paths"
        ) as add_paths_mock:
            resolved_bin = subtitle_extractor._resolve_media_binary("ffprobe")
        add_paths_mock.assert_called_once()
        self.assertEqual(resolved_bin, "ffprobe")


if __name__ == "__main__":
    unittest.main()
