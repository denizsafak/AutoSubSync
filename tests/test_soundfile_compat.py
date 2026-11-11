import ctypes.util
import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main"))
)

import compat


class TestSoundfileCompat(unittest.TestCase):
    def setUp(self):
        """Preserve the global lookup state so each test starts cleanly."""
        self._original_find_library = ctypes.util.find_library
        self._ready = compat._soundfile_library_ready
        self._handle = compat._soundfile_library_handle
        self._patched = compat._sndfile_lookup_patched

    def tearDown(self):
        """Restore the process-wide lookup state after each test."""
        ctypes.util.find_library = self._original_find_library
        compat._soundfile_library_ready = self._ready
        compat._soundfile_library_handle = self._handle
        compat._sndfile_lookup_patched = self._patched

    def test_candidates_include_a_bundled_library(self):
        """The maintained soundfile package must expose a loadable library."""
        candidate = next(compat._soundfile_library_candidates(), None)
        if candidate is None:
            self.skipTest("modern soundfile bundle is not installed")
        self.assertTrue(os.path.isfile(candidate))

    def test_patch_only_intercepts_sndfile(self):
        """Patching the lookup must leave every other library name untouched."""
        compat._sndfile_lookup_patched = False
        sentinel = os.path.join(os.sep, "tmp", "libsndfile-test.dylib")
        try:
            compat._patch_sndfile_lookup(sentinel)
            self.assertEqual(ctypes.util.find_library("sndfile"), sentinel)
            self.assertEqual(
                ctypes.util.find_library("c"),
                self._original_find_library("c"),
            )
        finally:
            ctypes.util.find_library = self._original_find_library


if __name__ == "__main__":
    unittest.main()
