"""Pure path-pairing helpers for batch sync.

Extracted from gui_batch_mode.py so the CLI can drive batch operations without
any Qt dependency. The GUI re-imports effective_basename, calculate_file_similarity,
and pair_paths from this module.
"""

import os
from typing import Iterable

from constants import VIDEO_EXTENSIONS, SUBTITLE_EXTENSIONS


def is_video_file(file_path: str) -> bool:
    return os.path.splitext(file_path)[-1].lower() in VIDEO_EXTENSIONS


def is_subtitle_file(file_path: str) -> bool:
    return os.path.splitext(file_path)[-1].lower() in SUBTITLE_EXTENSIONS


def effective_basename(file_path: str) -> str:
    """Strip extension and a trailing language tag (e.g. .en, .eng, _es-ES)."""
    base = os.path.splitext(os.path.basename(file_path))[0]
    for tag_length in [4, 3, 2]:
        if len(base) > tag_length and base[-(tag_length + 1)] in ["_", ".", "-"]:
            return base[: -(tag_length + 1)]
    return base


def calculate_file_similarity(reference_name: str, sub_name: str) -> int:
    """Score how likely two filenames are a video/subtitle pair.

    Higher is better. The batch matcher uses a threshold of 30.
    """
    reference_base = effective_basename(reference_name).lower().strip(".-_ [](){}")
    sub_base = effective_basename(sub_name).lower().strip(".-_ [](){}")

    common_len = 0
    for i in range(min(len(reference_base), len(sub_base))):
        if reference_base[i] == sub_base[i]:
            common_len += 1
        else:
            break

    similarity = common_len * 10
    length_diff = abs(len(reference_base) - len(sub_base))
    similarity -= min(length_diff * 2, similarity // 2)
    if reference_base == sub_base:
        similarity += 50
    return max(0, similarity)


def pair_paths(references: Iterable[str], subs: Iterable[str]):
    """Pair video references to subtitle files.

    Two-pass: (1) exact effective-basename match, (2) similarity score >= 30.
    Returns (pairs, paired_references, paired_subs) where pairs is a list of
    (reference, subtitle) tuples and the two sets contain the matched inputs.
    """
    references = list(references)
    subs = list(subs)
    paired_references = set()
    paired_subs = set()
    pairs = []

    for reference in references:
        reference_base = effective_basename(reference).lower().strip(".-_ [](){}")
        for sub in subs:
            if sub in paired_subs:
                continue
            sub_base = effective_basename(sub).lower().strip(".-_ [](){}")
            if reference_base == sub_base:
                pairs.append((reference, sub))
                paired_references.add(reference)
                paired_subs.add(sub)
                break

    for reference in references:
        if reference in paired_references:
            continue
        best_match = None
        best_score = 0
        for sub in subs:
            if sub in paired_subs:
                continue
            similarity = calculate_file_similarity(reference, sub)
            if similarity > best_score:
                best_score = similarity
                best_match = sub
        if best_match and best_score >= 30:
            pairs.append((reference, best_match))
            paired_references.add(reference)
            paired_subs.add(best_match)
    return pairs, paired_references, paired_subs


def _scan_dir(folder: str, recursive: bool):
    """Yield absolute paths to files in folder (optionally recursive)."""
    if recursive:
        for root, _dirs, files in os.walk(folder):
            for name in files:
                yield os.path.join(root, name)
    else:
        for name in os.listdir(folder):
            full = os.path.join(folder, name)
            if os.path.isfile(full):
                yield full


def pair_folder(folder: str, *, recursive: bool = False):
    """Find video+subtitle files in one folder and pair them.

    Returns a list of (video_path, subtitle_path) tuples.
    """
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Not a directory: {folder}")
    videos = sorted(p for p in _scan_dir(folder, recursive) if is_video_file(p))
    subs = sorted(p for p in _scan_dir(folder, recursive) if is_subtitle_file(p))
    pairs, _, _ = pair_paths(videos, subs)
    return pairs


def pair_folders(video_dir: str, subtitle_dir: str, *, recursive: bool = False):
    """Pair videos from one directory with subtitles from another.

    Returns a list of (video_path, subtitle_path) tuples.
    """
    for d in (video_dir, subtitle_dir):
        if not os.path.isdir(d):
            raise FileNotFoundError(f"Not a directory: {d}")
    videos = sorted(p for p in _scan_dir(video_dir, recursive) if is_video_file(p))
    subs = sorted(p for p in _scan_dir(subtitle_dir, recursive) if is_subtitle_file(p))
    pairs, _, _ = pair_paths(videos, subs)
    return pairs
