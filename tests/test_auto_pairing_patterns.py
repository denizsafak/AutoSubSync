"""Season/episode pattern tests for the auto-pairing file matcher.

Covers every entry in gui_auto_pairing.PATTERNS, one test per pattern, plus
pattern precedence, the basename-only matching rule, non-match guarantees
against common false positives (years, resolutions, codec tags, words that
merely contain a marker), and the exact filenames from GitHub issue #98.

gui_auto_pairing (via the utils/constants import chain) imports PyQt6 and
requests at module level, but the logic under test is pure Python. If the
GUI stack is not installed, lightweight stub modules are installed so these
tests can still run headless; on a normal development machine the real
modules are imported and the stubs are never used.
"""

import os
import re
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main")))


class _StubClass:
    """Universal stand-in for an imported GUI-only symbol.

    The class itself is subclassable (utils derives ``UpdateSignals`` from
    ``QObject``), callable with any arguments (``pyqtSignal(str, str)``) and
    tolerates attribute access on both the class and instances, which is all
    gui_auto_pairing needs at import time.
    """

    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return _StubClass()

    def __getattr__(self, name):
        return _StubClass


class _StubModule(types.ModuleType):
    """Module stand-in that yields _StubClass for any requested symbol."""

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return _StubClass


def _import_gui_auto_pairing():
    """Import gui_auto_pairing, stubbing GUI-only dependencies when missing.

    Tries a plain import first (the normal case on a development machine).
    Only when that fails with ImportError are stub modules installed for
    PyQt6 and requests, after which the import is retried. Returns the
    imported module.
    """
    try:
        import gui_auto_pairing  # noqa: F401
    except ImportError:
        for name in (
            "PyQt6",
            "PyQt6.QtCore",
            "PyQt6.QtWidgets",
            "PyQt6.QtGui",
            "requests",
            "platformdirs",
        ):
            if name in sys.modules:
                continue
            try:
                __import__(name)
            except ImportError:
                if name == "platformdirs":
                    # utils calls user_config_dir() and passes the result to
                    # os.makedirs, so the stub must yield a real directory.
                    stub = _StubModule(name)
                    stub.user_config_dir = lambda *args, **kwargs: tempfile.mkdtemp(
                        prefix="AutoSubSync-test-config-"
                    )
                    sys.modules[name] = stub
                else:
                    sys.modules[name] = _StubModule(name)
        import gui_auto_pairing
    return sys.modules["gui_auto_pairing"]


gui_auto_pairing = _import_gui_auto_pairing()
extract_season_episode = gui_auto_pairing.extract_season_episode
PATTERNS = gui_auto_pairing.PATTERNS
KIND_SEASON_EPISODE = gui_auto_pairing.KIND_SEASON_EPISODE
KIND_EPISODE_ONLY = gui_auto_pairing.KIND_EPISODE_ONLY

# The two subtitle filenames reported in GitHub issue #98.
ISSUE_98_SUB_1 = "[English] Melo Is My Nature episode 1 - 1155113v [DownSub.com].srt"
ISSUE_98_SUB_2 = "[English] Melo Is My Nature episode 2 - 1155114v [DownSub.com].srt"

# Filename tables: (label, filename, expected (season, episode, key) tuple).
# Expectations are written out in full so a regression in the canonical
# "s01e05" key formatting is caught as well, not just the numbers.
SXXEYY_CASES = [
    ("two-digit season and episode", "Show S01E05.mkv", (1, 5, "s01e05")),
    ("lowercase marker", "series s02e07.mp4", (2, 7, "s02e07")),
    ("wide season number", "Show S10E02.mkv", (10, 2, "s10e02")),
    ("multi-digit episode", "show s1e156.srt", (1, 156, "s01e156")),
    ("dot-separated with resolution tag", "Show.S01E05.720p.mkv", (1, 5, "s01e05")),
]

SXXBYY_CASES = [
    ("B-variant episode marker", "Show S01B03.mkv", (1, 3, "s01e03")),
    ("lowercase B-variant", "show s2b10.srt", (2, 10, "s02e10")),
]

NUMBER_X_CASES = [
    ("single digit season", "Show 1x05.mkv", (1, 5, "s01e05")),
    ("two-digit season", "Show 12x03.mkv", (12, 3, "s12e03")),
    ("zero-padded season, long episode", "Show 01x156.mkv", (1, 156, "s01e156")),
]

E_EP_CASES = [
    ("E marker", "Show E05.mkv", (1, 5, "s1e05")),
    ("EP marker", "Show EP156.mkv", (1, 156, "s1e156")),
    ("single digit episode", "show e5.srt", (1, 5, "s1e05")),
    ("EP01", "Show EP01.mkv", (1, 1, "s1e01")),
]

PART_CASES = [
    ("no separator", "Show Part001.mkv", (1, 1, "s1e01")),
    ("Pt abbreviation", "Show Pt156.mkv", (1, 156, "s1e156")),
    ("space separator", "Show Part 2.mkv", (1, 2, "s1e02")),
    ("dot separator", "Show part.3.mkv", (1, 3, "s1e03")),
    ("underscore separator", "Show Part_4.mkv", (1, 4, "s1e04")),
    ("dash separator", "Show Part-5.mkv", (1, 5, "s1e05")),
]

EPISODE_WORD_CASES = [
    ("issue #98 subtitle 1", ISSUE_98_SUB_1, (1, 1, "s1e01")),
    ("issue #98 subtitle 2", ISSUE_98_SUB_2, (1, 2, "s1e02")),
    ("zero-padded episode", "Show Episode 01.srt", (1, 1, "s1e01")),
    ("dot separator", "Show Episode.1.srt", (1, 1, "s1e01")),
    ("underscore separator", "Show Episode_1.srt", (1, 1, "s1e01")),
    ("dash separator", "Show Episode-1.srt", (1, 1, "s1e01")),
    ("no separator", "Show Episode1.srt", (1, 1, "s1e01")),
    ("Ep abbreviation with space", "Show Ep 1.srt", (1, 1, "s1e01")),
    ("Ep abbreviation with dot", "Show Ep.01.srt", (1, 1, "s1e01")),
    ("all-caps filename", "Show EPISODE 7.srt", (1, 7, "s1e07")),
    ("three-digit episode", "Show Episode 100.srt", (1, 100, "s1e100")),
]

BOLUM_CASES = [
    ("bölüm with space", "Show bölüm 1.srt", (1, 1, "s1e01")),
    ("Bölüm with dot", "Show Bölüm.02.srt", (1, 2, "s1e02")),
    ("ASCII bolum in caps", "Show BOLUM 3.srt", (1, 3, "s1e03")),
    ("bölüm with underscore", "Show bölüm_04.srt", (1, 4, "s1e04")),
    ("uppercase Turkish diacritics", "Show BÖLÜM 5.srt", (1, 5, "s1e05")),
    ("bolum without separator", "Show bolum5.srt", (1, 5, "s1e05")),
]

BARE_THREE_DIGIT_CASES = [
    ("season 1 episode 1", "Show 101.mkv", (1, 1, "s01e01")),
    ("season 3 episode 5", "Show 305.mkv", (3, 5, "s03e05")),
    ("season 9 episode 5", "Show 905.mkv", (9, 5, "s09e05")),
    ("bare number without title", "101.mkv", (1, 1, "s01e01")),
]

NON_MATCH_CASES = [
    # Plain movie names carry no episode information at all.
    ("plain movie name", "Some Movie.mkv"),
    # A release year must not be read as season/episode (1994 -> S19E94).
    ("release year", "Movie 1994.mkv"),
    # Four-digit numbers are never split into season+episode.
    ("four-digit number", "Show 1101.mkv"),
    # Resolution tags: 1080p/2160p fail the pattern numerically, but 720p and
    # 480i are exactly three digits and must be excluded via the p/i guard.
    ("1080p resolution", "Show 1080p.srt"),
    ("720p resolution", "Show 720p.mkv"),
    ("480i resolution", "Show 480i.mkv"),
    # Codec tags would otherwise become phantom seasons (x264 -> S02E64).
    ("x264 codec", "Show x264.mkv"),
    ("x265 codec", "Show x265.mkv"),
    ("h264 codec prefix", "h264 Show.mkv"),
    ("H.264 codec with dot", "Show H.264.mkv"),
    # Word-boundary guard: markers inside other words must not match
    # ("ep" in Deep/Sept/Epic, "pt" in Script/Sept, "part" in Apartment).
    ("ep inside a word", "Deep 1.mkv"),
    ("pt inside a word", "Script 2.mkv"),
    ("pt inside Sept", "Sept 2.mkv"),
    ("part inside a word", "Apartment 1.mkv"),
    ("ep prefix without digits", "Epic 1.mkv"),
    # Markers without a number are incomplete, not episodes.
    ("episode without number", "episode.mkv"),
    ("bolum without number", "bolum.mkv"),
    ("part without number", "Part.mkv"),
    ("incomplete SxxE marker", "Show S01E.mkv"),
]

# (label, filename, expected season, expected episode) — key is checked via
# the full tuple in the pattern tables above; these cases only pin which
# pattern wins when several could match.
PRECEDENCE_CASES = [
    ("SxxEyy beats NxY", "Show.S02E03.1x04.mkv", 2, 3),
    ("SxxEyy beats word form", "Show S01E05 episode 8.mkv", 1, 5),
    ("E marker beats Part", "Show E05 Part 2.mkv", 1, 5),
]


class TestExtractSeasonEpisode(unittest.TestCase):
    """Behavioural coverage of extract_season_episode, pattern by pattern."""

    def _assert_matches(self, cases):
        """Assert each (label, filename, expected) row matches exactly."""
        for label, filename, expected in cases:
            with self.subTest(pattern_case=label, filename=filename):
                self.assertEqual(extract_season_episode(filename), expected)

    def test_sxxeyy_pattern(self):
        """Season+episode marker S01E05 (any season width, long episodes)."""
        self._assert_matches(SXXEYY_CASES)

    def test_sxxyyy_b_pattern(self):
        """B-variant season+episode marker S01B03 maps onto the same key."""
        self._assert_matches(SXXBYY_CASES)

    def test_number_x_pattern(self):
        """NxY style markers (1x05, 12x03) are recognised as season+episode."""
        self._assert_matches(NUMBER_X_CASES)

    def test_e_and_ep_pattern(self):
        """Bare E/EP markers default to season 1."""
        self._assert_matches(E_EP_CASES)

    def test_part_pattern(self):
        """Part/Pt markers default to season 1 and allow common separators."""
        self._assert_matches(PART_CASES)

    def test_episode_word_pattern(self):
        """Word-form Episode/Ep markers with optional separators are matched.

        This includes the exact subtitle filenames from GitHub issue #98,
        which previously reported "Missing season/episode info".
        """
        self._assert_matches(EPISODE_WORD_CASES)

    def test_bolum_pattern(self):
        """Turkish 'bölüm' (and ASCII 'bolum') markers default to season 1."""
        self._assert_matches(BOLUM_CASES)

    def test_bare_three_digit_pattern(self):
        """Bare three-digit numbers (101 = S01E01) are the last-resort match."""
        self._assert_matches(BARE_THREE_DIGIT_CASES)

    def test_pattern_precedence(self):
        """More specific markers win: PATTERNS is tried strictly in order."""
        for label, filename, season, episode in PRECEDENCE_CASES:
            with self.subTest(precedence_case=label, filename=filename):
                result = extract_season_episode(filename)
                self.assertEqual((result[0], result[1]), (season, episode))

    def test_non_matches(self):
        """Movie names, years, resolutions, codecs and embedded words never match."""
        for label, filename in NON_MATCH_CASES:
            with self.subTest(non_match_case=label, filename=filename):
                self.assertEqual(
                    extract_season_episode(filename), (None, None, None)
                )

    def test_matching_uses_basename_only(self):
        """Directory components are ignored; only the filename is scanned."""
        with self.subTest(case="marker inside path is found"):
            self.assertEqual(
                extract_season_episode("/tv/Season 2/Show 2x10.mkv"),
                (2, 10, "s02e10"),
            )
        with self.subTest(case="number in directory is ignored"):
            self.assertEqual(
                extract_season_episode("/media/101/show.mkv"), (None, None, None)
            )
        with self.subTest(case="resolution in directory is ignored"):
            self.assertEqual(
                extract_season_episode("/data/720p/episode 3.mkv"), (1, 3, "s1e03")
            )


class TestPatternDefinitions(unittest.TestCase):
    """Structural invariants of the PATTERNS table itself."""

    def test_patterns_use_known_kinds(self):
        """Every pattern is tagged with one of the two defined kinds."""
        self.assertTrue(PATTERNS, "PATTERNS must not be empty")
        for pattern, kind in PATTERNS:
            with self.subTest(pattern=pattern):
                self.assertIn(kind, (KIND_SEASON_EPISODE, KIND_EPISODE_ONLY))

    def test_kind_tag_matches_capture_group_count(self):
        """Episode-only patterns capture one group; season+episode two.

        extract_season_episode reads group(1) for KIND_EPISODE_ONLY and
        groups 1+2 for KIND_SEASON_EPISODE, so a mismatch between a
        pattern's tag and its capture groups would crash at runtime.
        """
        for pattern, kind in PATTERNS:
            with self.subTest(pattern=pattern):
                expected_groups = 1 if kind == KIND_EPISODE_ONLY else 2
                self.assertEqual(re.compile(pattern).groups, expected_groups)

    def test_every_pattern_has_matching_test_cases(self):
        """Each pattern is exercised by at least one positive case.

        Guards against a future pattern being added to PATTERNS without
        coverage: compile every pattern and require that it matches at
        least one filename from the positive tables in this module.
        """
        positive_filenames = [
            filename
            for table in (
                SXXEYY_CASES,
                SXXBYY_CASES,
                NUMBER_X_CASES,
                E_EP_CASES,
                PART_CASES,
                EPISODE_WORD_CASES,
                BOLUM_CASES,
                BARE_THREE_DIGIT_CASES,
            )
            for _, filename, _ in table
        ]
        for pattern, kind in PATTERNS:
            with self.subTest(pattern=pattern):
                compiled = re.compile(pattern)
                self.assertTrue(
                    any(compiled.search(os.path.basename(f).lower()) for f in positive_filenames),
                    f"pattern {pattern!r} ({kind}) has no positive test case",
                )


if __name__ == "__main__":
    unittest.main()
