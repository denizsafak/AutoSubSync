#!/usr/bin/env python3
"""Generate AutoSubSync screenshots at the same resolution as the README images.

Creates temporary fake movie and subtitle files, populates Batch mode and the
Sync Log view (and optionally Normal mode), and captures the active window
including its OS title bar using KDE Spectacle (or Qt widget grab in offscreen
mode) before scaling to 385x641 in ``images/``.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
MAIN_DIR = os.path.join(REPO_ROOT, "main")
if MAIN_DIR not in sys.path:
    sys.path.insert(0, MAIN_DIR)

TARGET_WIDTH = 385
TARGET_HEIGHT = 641

FAKE_MOVIES = [
    (
        "Velvet Pendulum (2089)",
        "Velvet.Pendulum.2089.2160p.WEB-DL.DV.HDR.DDP5.1.HEVC.mkv",
        "Velvet.Pendulum.2089.2160p.WEB-DL.DV.HDR.DDP5.1.HEVC.en.srt",
    ),
    (
        "Glass Astrolabe (2074)",
        "Glass.Astrolabe.2074.1080p.BluRay.REMUX.AVC.DTS-HD.MA.7.1.mkv",
        "Glass.Astrolabe.2074.1080p.BluRay.REMUX.AVC.DTS-HD.MA.7.1.en.srt",
    ),
    (
        "Cinder Cartographer (2091)",
        "Cinder.Cartographer.2091.2160p.BluRay.x265.10bit.HDR.DTS-HD.MA.mkv",
        "Cinder.Cartographer.2091.2160p.BluRay.x265.10bit.HDR.DTS-HD.MA.en.srt",
    ),
    (
        "Saffron Monolith (2083)",
        "Saffron.Monolith.2083.2160p.UHD.BluRay.HEVC.TrueHD.7.1.Atmos.mkv",
        "Saffron.Monolith.2083.2160p.UHD.BluRay.HEVC.TrueHD.7.1.Atmos.en.srt",
    ),
    (
        "Copper Starlight (2096)",
        "Copper.Starlight.2096.1080p.BluRay.AVC.DTS-HD.MA.5.1.mkv",
        "Copper.Starlight.2096.1080p.BluRay.AVC.DTS-HD.MA.5.1.en.srt",
    ),
    (
        "Hollow Meridian (2085)",
        "Hollow.Meridian.2085.1080p.WEB-DL.H264.DDP5.1.mkv",
        "Hollow.Meridian.2085.1080p.WEB-DL.H264.DDP5.1.en.srt",
    ),
]


def _create_fake_media(temp_dir):
    """Create temporary fake video and subtitle files and return (video, sub) pairs."""
    pairs = []
    for folder_name, video_name, sub_name in FAKE_MOVIES:
        movie_dir = os.path.join(temp_dir, "Movies", folder_name)
        os.makedirs(movie_dir, exist_ok=True)
        video_path = os.path.join(movie_dir, video_name)
        sub_path = os.path.join(movie_dir, sub_name)
        with open(video_path, "wb") as fh:
            fh.write(b"FAKE_VIDEO_DATA")
        with open(sub_path, "w", encoding="utf-8") as fh:
            fh.write("1\n00:00:01,000 --> 00:00:03,000\nSample subtitle line.\n")
        pairs.append((video_path, sub_path))
    return pairs


def _trim_transparent_shadow(image):
    """Crop outer fully/mostly transparent window-shadow border from a QImage."""
    from PyQt6.QtCore import QRect

    if not image.hasAlphaChannel():
        return image

    w, h = image.width(), image.height()
    min_x, min_y, max_x, max_y = w, h, -1, -1
    for y in range(h):
        for x in range(w):
            if (image.pixel(x, y) >> 24) >= 240:
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
                if y < min_y:
                    min_y = y
                if y > max_y:
                    max_y = y

    if max_x >= min_x and max_y >= min_y:
        # Inset by 2px to strip KDE Breeze's 1px light outer window border
        inset = 2 if (max_x - min_x > 20 and max_y - min_y > 20) else 0
        return image.copy(
            QRect(
                min_x + inset,
                min_y + inset,
                max_x - min_x + 1 - 2 * inset,
                max_y - min_y + 1 - 2 * inset,
            )
        )
    return image


def _capture_window(
    app,
    widget,
    output_path,
    temp_dir,
    use_spectacle=True,
    width=TARGET_WIDTH,
    height=TARGET_HEIGHT,
):
    """Capture the active window (including OS title bar when available) and scale."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QImage

    widget.raise_()
    widget.activateWindow()
    for _ in range(5):
        app.processEvents()
        time.sleep(0.05)

    if use_spectacle and shutil.which("spectacle"):
        raw_path = os.path.join(temp_dir, "raw_capture.png")
        subprocess.run(
            ["spectacle", "-b", "-n", "-a", "-o", raw_path],
            check=True,
        )
        image = QImage(raw_path)
        image = _trim_transparent_shadow(image)
        os.remove(raw_path)
    else:
        image = widget.grab().toImage()

    if image.width() != width or image.height() != height:
        image = image.scaled(
            width,
            height,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    image.save(output_path, "PNG")


def _populate_fake_sync_log(app, win):
    """Populate the Sync Log view with realistic fake movie sync progress."""
    from constants import COLORS

    win.show_log_window()
    log = win.log_window
    log.reset_for_new_sync()
    log.cancel_button.setVisible(True)
    log.cancel_button.setEnabled(True)

    f1, v1_name, s1_name = FAKE_MOVIES[0]
    f2, v2_name, s2_name = FAKE_MOVIES[1]
    base = "/home/user/Movies"
    v1 = f"{base}/{f1}/{v1_name}"
    s1 = f"{base}/{f1}/{s1_name}"
    out1 = f"/home/user/Desktop/{s1_name.replace('.en.srt', '_synced.en.srt')}"
    v2 = f"{base}/{f2}/{v2_name}"
    s2 = f"{base}/{f2}/{s2_name}"

    log.append_message("Processing pair [1/5]", bold=True, color=COLORS["BLUE"])
    log.append_message("Reference: ", end="")
    log.append_message(v1, color=COLORS["GREY"])
    log.append_message("Subtitle: ", end="")
    log.append_message(s1, color=COLORS["GREY"])
    log.append_message("")
    log.append_message(
        f"INFO     extracting speech segments from reference '{v1}'..."
    )
    log.append_message("INFO     Checking video for subtitles stream...")
    log.append_message("INFO     detected encoding: UTF-8")
    log.append_message("INFO     ...success!")
    log.append_message("INFO     ...done")
    log.append_message(
        f"INFO     extracting speech segments from subtitles file(s) ['{s1}']..."
    )
    log.append_message("INFO     detected encoding: UTF-8")
    log.append_message("INFO     computing alignments...")
    log.append_message("INFO     ...done")
    log.append_message("INFO     score: 204816.000")
    log.append_message("INFO     offset seconds: 1.420")
    log.append_message("INFO     framerate scale factor: 1.000")
    log.append_message(f"INFO     writing output to {out1}")
    log.append_message("")
    log.append_message("Synchronization completed successfully.", bold=True, color=COLORS["GREEN"])
    log.append_message(f"Saved to: {out1}", color=COLORS["GREY"])
    log.append_message("")
    log.append_message("Processing pair [2/5]", bold=True, color=COLORS["BLUE"])
    log.append_message("Reference: ", end="")
    log.append_message(v2, color=COLORS["GREY"])
    log.append_message("Subtitle: ", end="")
    log.append_message(s2, color=COLORS["GREY"])
    log.append_message("")
    log.append_message(
        f"INFO     extracting speech segments from reference '{v2}'..."
    )
    log.append_message("INFO     Checking video for subtitles stream...")
    log.append_message("INFO     detected encoding: UTF-8")
    log.append_message("INFO     ...success!")
    log.append_message("INFO     ...done")
    log.append_message(
        f"INFO     extracting speech segments from subtitles file(s) ['{s2}']..."
    )
    log.append_message("INFO     detected encoding: UTF-8")
    log.append_message("INFO     computing alignments...")
    log.update_progress(40, 2, 5)

    app.processEvents()
    sb = log.log_text.verticalScrollBar()
    sb.setValue(sb.maximum())
    app.processEvents()


def generate_screenshots(output_dir, offscreen=False, populate_normal=False):
    """Launch the AutoSubSync GUI and capture screenshots into output_dir."""
    if offscreen:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    # Render Qt widgets natively near TARGET_WIDTH (500 * 0.77 = 385) for sharp text
    os.environ.setdefault("QT_SCALE_FACTOR", "0.77")

    from PyQt6.QtWidgets import QApplication

    import gui
    import utils as app_utils
    from gui_automatic_tab import attach_functions_to_autosubsyncapp as attach_auto
    from gui_batch_mode import attach_functions_to_autosubsyncapp as attach_batch
    from gui_manual_tab import attach_functions_to_autosubsyncapp as attach_manual

    attach_auto(gui.autosubsyncapp)
    attach_manual(gui.autosubsyncapp)
    attach_batch(gui.autosubsyncapp)

    os.makedirs(output_dir, exist_ok=True)
    temp_dir = tempfile.mkdtemp(prefix="AutoSubSync-screenshots-")
    cfg_dir = os.path.join(temp_dir, "cfg")
    os.makedirs(cfg_dir, exist_ok=True)

    app = QApplication.instance() or QApplication(sys.argv)
    fake_pairs = _create_fake_media(temp_dir)
    default_cfg = {
        "batch_mode": False,
        "check_updates_startup": False,
        "always_on_top": False,
        "automatic_save_location": "save_to_desktop",
        "manual_save_location": "overwrite_input_subtitle",
    }
    use_spectacle = not offscreen and bool(
        os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    )

    try:
        app_utils.clear_config_cache()
        with (
            patch("gui.check_for_updates_startup"),
            patch("gui.check_for_lapse_updates_startup"),
            patch("utils.initialize_static_ffmpeg"),
            patch.object(
                app_utils,
                "get_user_config_path",
                return_value=os.path.join(cfg_dir, "config.json"),
            ),
            patch.object(app_utils, "load_config", return_value=dict(default_cfg)),
            patch("gui.load_config", return_value=dict(default_cfg)),
        ):
            win = gui.autosubsyncapp()
            win.show()
            app.processEvents()

            # 1. Normal mode (Automatic Sync) - empty by default (or populated if requested)
            if populate_normal:
                first_video, first_sub = fake_pairs[0]
                win.video_ref_input.set_file(first_video)
                win.subtitle_input.set_file(first_sub)
            _capture_window(
                app,
                win,
                os.path.join(output_dir, "AutoSubSync1.png"),
                temp_dir,
                use_spectacle=use_spectacle,
            )

            # 2. Manual Sync tab
            win.tab_widget.setCurrentIndex(1)
            _capture_window(
                app,
                win,
                os.path.join(output_dir, "AutoSubSync2.png"),
                temp_dir,
                use_spectacle=use_spectacle,
            )

            # 3. Batch mode populated with fake movie & subtitle pairs
            win.tab_widget.setCurrentIndex(0)
            win.toggle_batch_mode()
            for video_path, sub_path in fake_pairs:
                win.batch_tree_view.add_explicit_pair(video_path, sub_path)
            _capture_window(
                app,
                win,
                os.path.join(output_dir, "AutoSubSync3.png"),
                temp_dir,
                use_spectacle=use_spectacle,
            )

            # 4. Processing / Sync Log view
            _populate_fake_sync_log(app, win)
            _capture_window(
                app,
                win,
                os.path.join(output_dir, "AutoSubSync4.png"),
                temp_dir,
                use_spectacle=use_spectacle,
            )

            win.close()
            win.deleteLater()
            app.processEvents()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(
        description="Generate AutoSubSync screenshots (385x641) replacing images/AutoSubSync*.png."
    )
    parser.add_argument(
        "-o",
        "--output",
        default=os.path.join(REPO_ROOT, "images"),
        help="Output directory for generated PNGs (default: images)",
    )
    parser.add_argument(
        "--offscreen",
        action="store_true",
        help="Render in Qt offscreen mode (no OS window title bar)",
    )
    parser.add_argument(
        "--populate-normal",
        action="store_true",
        help="Also load a fake movie and subtitle into Normal mode for AutoSubSync1.png",
    )
    args = parser.parse_args()
    generate_screenshots(
        args.output,
        offscreen=args.offscreen,
        populate_normal=args.populate_normal,
    )
    print(f"Screenshots saved to {args.output}")


if __name__ == "__main__":
    main()
