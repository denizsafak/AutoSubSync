"""Window sizing and scrollable tab regression tests.

The main window used to open with a fixed 500x800 client area centered on the
full screen. On displays whose work area is shorter than that, the title bar
was placed above the screen and the bottom of the window below it.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main")))

try:
    from PyQt6.QtCore import QRect
    from PyQt6.QtWidgets import QApplication, QScrollArea
except ImportError:  # pragma: no cover - PyQt6 is a runtime dependency
    QRect = None
    QApplication = None
    QScrollArea = None


@unittest.skipIf(QRect is None, "PyQt6 is required for window sizing tests")
class TestInitialWindowGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import gui

        cls.gui = gui

    def test_default_size_on_large_screen(self):
        available = QRect(0, 0, 1920, 1040)
        geometry = self.gui.initial_window_geometry(available)
        self.assertEqual((geometry.width(), geometry.height()), (500, 800))
        self.assertTrue(available.contains(geometry))

    def test_fits_short_work_area(self):
        available = QRect(0, 0, 1280, 760)
        geometry = self.gui.initial_window_geometry(available)
        self.assertEqual((geometry.width(), geometry.height()), (500, 720))
        self.assertTrue(available.contains(geometry))
        self.assertGreater(geometry.y(), available.y())

    def test_respects_offset_work_area(self):
        available = QRect(0, 40, 1366, 728)
        geometry = self.gui.initial_window_geometry(available)
        self.assertTrue(available.contains(geometry))
        self.assertGreaterEqual(geometry.x(), available.x())
        self.assertGreaterEqual(geometry.y(), available.y())

    def test_fits_narrow_screen(self):
        available = QRect(0, 0, 500, 400)
        geometry = self.gui.initial_window_geometry(available)
        self.assertTrue(available.contains(geometry))
        self.assertLessEqual(geometry.width(), available.width())
        self.assertLessEqual(geometry.height(), available.height())

    def test_fits_small_high_dpi_work_area(self):
        # e.g. a 1366x768 panel at 200% scaling has a ~683x384 logical area.
        available = QRect(0, 0, 683, 384)
        geometry = self.gui.initial_window_geometry(available)
        self.assertTrue(available.contains(geometry))
        self.assertGreater(geometry.y(), available.y())

    def test_wrap_filename_adds_break_points(self):
        name = (
            "TLOTR.The.Return.of.the.King.2003.Extended.BluRay.1080p."
            "DTSES6.1.x264-CHD.DVDRip.srt"
        )
        wrapped = self.gui.wrap_filename(name)
        self.assertIn("\u200b", wrapped)
        self.assertEqual(wrapped.replace("\u200b", ""), name)

        long_word = "A" * 40
        wrapped_word = self.gui.wrap_filename(long_word)
        self.assertIn("\u200b", wrapped_word)
        self.assertEqual(wrapped_word.replace("\u200b", ""), long_word)


@unittest.skipIf(QApplication is None, "PyQt6 is required for window sizing tests")
class TestScrollableTabContent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])
        import gui

        cls.gui = gui

    def test_tab_content_is_wrapped_in_scroll_area(self):
        page, content_layout = self.gui.autosubsyncapp._container(None)
        self.assertIsInstance(page._scroll_area, QScrollArea)
        self.assertIs(page._scroll_content, content_layout.parentWidget())
        self.assertIs(page._scroll_area.widget(), page._scroll_content)
        self.assertTrue(page._scroll_area.widgetResizable())

    def test_scrollbar_padding_only_when_needed(self):
        page, content_layout = self.gui.autosubsyncapp._container(None)
        scrollbar = page._scroll_area.verticalScrollBar()
        self.assertEqual(content_layout.contentsMargins().right(), 0)
        scrollbar.setRange(0, 100)
        self.assertEqual(content_layout.contentsMargins().right(), 10)
        scrollbar.setRange(0, 0)
        self.assertEqual(content_layout.contentsMargins().right(), 0)

    def test_long_filename_does_not_force_wide_minimum(self):
        import tempfile

        long_name = (
            "TLOTR.The.Return.of.the.King.2003.Extended.BluRay.1080p."
            "DTSES6.1.x264-CHD.DVDRip.srt"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, long_name)
            with open(path, "w", encoding="utf-8"):
                pass

            input_box = self.gui.InputBox(input_type="subtitle")
            try:
                input_box.set_file(path)
                self.assertIn("\u200b", input_box.text())
                self.assertLess(input_box.minimumSizeHint().width(), 250)
            finally:
                input_box.deleteLater()

    def test_always_on_top_option_and_translations(self):
        from PyQt6.QtCore import Qt
        from unittest.mock import patch
        import constants
        import texts

        self.assertFalse(constants.DEFAULT_OPTIONS["always_on_top"])
        for lang_code in constants.LANGUAGES.values():
            self.assertIn(lang_code, texts.ALWAYS_ON_TOP._translations)
            self.assertIn(lang_code, texts.ALWAYS_ON_TOP_UNSUPPORTED_WAYLAND._translations)

        with patch("gui.load_config", return_value=dict(constants.DEFAULT_OPTIONS)), \
             patch("gui.save_config"):
            w = self.gui.autosubsyncapp()
            try:
                self.assertTrue(w.always_on_top_action.isCheckable())
                self.assertFalse(w.always_on_top_action.isChecked())
                self.assertFalse(bool(w.windowFlags() & Qt.WindowType.WindowStaysOnTopHint))

                w.show()
                self.assertTrue(w.isVisible())

                w.toggle_always_on_top(True)
                self.assertTrue(w.config["always_on_top"])
                self.assertTrue(bool(w.windowFlags() & Qt.WindowType.WindowStaysOnTopHint))
                self.assertTrue(w.isVisible())

                w.toggle_always_on_top(False)
                self.assertFalse(w.config["always_on_top"])
                self.assertFalse(bool(w.windowFlags() & Qt.WindowType.WindowStaysOnTopHint))
                self.assertTrue(w.isVisible())
            finally:
                w.close()
                w.deleteLater()

    def test_always_on_top_platform_backends_avoid_reopening_visible_window(self):
        from unittest.mock import MagicMock, patch
        import utils

        fake_win = MagicMock()
        fake_win.isVisible.return_value = True
        fake_win.winId.return_value = 12345
        fake_win.windowTitle.return_value = "AutoSubSync"

        # 1. Wayland: must invoke Wayland backend and never call setWindowFlag/show
        with patch("PyQt6.QtGui.QGuiApplication.platformName", return_value="wayland"), \
             patch("utils._set_wayland_always_on_top", return_value=True) as mock_wl:
            self.assertTrue(utils.set_window_always_on_top(fake_win, True))
            mock_wl.assert_called_once_with(os.getpid(), "AutoSubSync", True)
            fake_win.setWindowFlag.assert_not_called()
            fake_win.show.assert_not_called()

        # 2. X11 (xcb): must send _NET_WM_STATE_ABOVE without calling setWindowFlag/show
        fake_win.reset_mock()
        with patch("PyQt6.QtGui.QGuiApplication.platformName", return_value="xcb"), \
             patch("utils._set_x11_always_on_top", return_value=True) as mock_x11:
            self.assertTrue(utils.set_window_always_on_top(fake_win, True))
            mock_x11.assert_called_once_with(12345, True)
            fake_win.setWindowFlag.assert_not_called()
            fake_win.show.assert_not_called()

        # 3. Windows: must use SetWindowPos helper without calling setWindowFlag/show
        fake_win.reset_mock()
        with patch("sys.platform", "win32"), \
             patch("PyQt6.QtGui.QGuiApplication.platformName", return_value="windows"), \
             patch("utils._set_windows_always_on_top", return_value=True) as mock_win32:
            self.assertTrue(utils.set_window_always_on_top(fake_win, True))
            mock_win32.assert_called_once_with(12345, True)
            fake_win.setWindowFlag.assert_not_called()
            fake_win.show.assert_not_called()

        # 4. macOS: must use Cocoa window level helper without calling setWindowFlag/show
        fake_win.reset_mock()
        with patch("sys.platform", "darwin"), \
             patch("PyQt6.QtGui.QGuiApplication.platformName", return_value="cocoa"), \
             patch("utils._set_macos_always_on_top", return_value=True) as mock_mac:
            self.assertTrue(utils.set_window_always_on_top(fake_win, False))
            mock_mac.assert_called_once_with(fake_win, False)
            fake_win.setWindowFlag.assert_not_called()
            fake_win.show.assert_not_called()

        # 5. Unsupported compositor revert check in gui toggle
        import constants
        with patch("gui.load_config", return_value=dict(constants.DEFAULT_OPTIONS)), \
             patch("gui.save_config"), \
             patch("gui.QMessageBox.information") as mock_info:
            w = self.gui.autosubsyncapp()
            try:
                w.always_on_top_action.setChecked(True)
                with patch.object(w, "apply_always_on_top", return_value=False):
                    w.toggle_always_on_top(True)
                self.assertFalse(w.config["always_on_top"])
                self.assertFalse(w.always_on_top_action.isChecked())
                mock_info.assert_called_once()
            finally:
                w.close()
                w.deleteLater()


if __name__ == "__main__":
    unittest.main()
