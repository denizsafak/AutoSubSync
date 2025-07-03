"""
Subtitle Shifter Module

This module provides functionality to shift subtitle timing by a specified number of milliseconds.
Supported formats include: SRT, VTT, SBV, SUB, STL, DFXP, TTML/ITT, ASS/SSA, and SMI.
"""

import os
import re
import logging
import texts
from typing import Optional, Tuple
from utils import detect_encoding
from constants import DEFAULT_OPTIONS
import platformdirs

logger = logging.getLogger(__name__)


def determine_manual_output_path(app, subtitle, shift_ms, add_prefix=True):
    """
    Determine output path for manual sync based on save location settings.
    """
    config = app.config
    save_loc = config.get(
        "manual_save_location", DEFAULT_OPTIONS["manual_save_location"]
    )

    sub_dir, sub_file = os.path.dirname(subtitle), os.path.basename(subtitle)
    sub_name, sub_ext = os.path.splitext(sub_file)

    # Format shift for filename (using prefix only if enabled)
    if add_prefix:
        if shift_ms >= 0:
            shift_prefix = f"+{shift_ms}ms_"
        else:
            shift_prefix = f"{shift_ms}ms_"
    else:
        shift_prefix = ""

    if save_loc == "same_folder":
        out_dir, out_name = sub_dir, f"{shift_prefix}{sub_name}{sub_ext}"
    elif save_loc == "overwrite_input_subtitle":
        out_dir, out_name = sub_dir, sub_file
    elif save_loc == "save_to_desktop":
        out_dir, out_name = (
            platformdirs.user_desktop_path(),
            f"{shift_prefix}{sub_name}{sub_ext}",
        )
    elif save_loc == "select_destination_folder":
        folder = config.get("manual_save_folder", "")
        out_dir = folder if folder and os.path.isdir(folder) else sub_dir
        out_name = f"{shift_prefix}{sub_name}{sub_ext}"
    else:
        # Default fallback
        out_dir, out_name = sub_dir, f"{shift_prefix}{sub_name}{sub_ext}"

    output_path = os.path.join(out_dir, out_name)
    return output_path


def shift_subtitle(
    subtitle_file: str, milliseconds: int, output_file: str = None
) -> Tuple[Optional[str], bool, str]:
    """
    Shift subtitle timing by specified milliseconds.

    Args:
        subtitle_file: Path to the input subtitle file
        milliseconds: Number of milliseconds to shift (positive for delay, negative for advance)
        output_file: Path for output file. If None, will be automatically generated

    Returns:
        Tuple of (output_file_path, success_flag, message)
    """

    # Load and decode file
    try:
        with open(subtitle_file, "rb") as file:
            raw_data = file.read()
            encoding = detect_encoding(subtitle_file)
            lines = raw_data.decode(encoding).splitlines()
    except Exception as e:
        error_msg = texts.ERROR_LOADING_SUBTITLE_FILE.format(error=str(e))
        logger.error(error_msg)
        return None, False, error_msg

    file_extension = os.path.splitext(subtitle_file)[-1].lower()

    # Determine output file path
    if output_file is None:
        base_name = os.path.splitext(subtitle_file)[0]
        suffix = f"+{milliseconds}" if milliseconds >= 0 else str(milliseconds)
        output_file = f"{base_name}_{suffix}ms{file_extension}"

    # Time conversion functions
    def time_to_ms(time_str: str, fmt: str) -> Optional[int]:
        """Convert time string to milliseconds based on format."""
        try:
            if fmt in ["srt", "vtt"]:
                parts = re.split(r"[:,.]", time_str)
                h, m, s, ms = map(int, parts)
                return (h * 3600 + m * 60 + s) * 1000 + ms
            elif fmt == "sbv":
                parts = re.split(r"[:.]", time_str)
                h, m, s, ms = map(int, parts)
                return (h * 3600 + m * 60 + s) * 1000 + ms
            elif fmt in ["sub", "ass_ssa"]:
                parts = re.split(r"[:.]", time_str)
                h, m, s, cs = map(int, parts)
                return (h * 3600 + m * 60 + s) * 1000 + (cs * 10)
            elif fmt == "stl":
                parts = re.split(r"[:.]", time_str)
                h, m, s, f = map(int, parts)
                return (h * 3600 + m * 60 + s) * 1000 + (f * 40)  # 25 fps
            elif fmt == "dfxp":
                parts = re.split(r"[:.,]", time_str)
                h, m, s = map(int, parts[:3])
                ms_val = int(parts[3]) if len(parts) > 3 else 0
                return (h * 3600 + m * 60 + s) * 1000 + ms_val
            elif fmt in ["ttml", "itt"]:
                if ":" in time_str:
                    # HH:MM:SS.MS or HH:MM:SS:FF format
                    if "." in time_str:
                        h, m, s_ms = time_str.split(":")
                        s, ms_str = s_ms.split(".")
                        ms_val = int(ms_str.ljust(3, "0")[:3])
                        return (int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + ms_val
                    else:
                        parts = time_str.split(":")
                        if len(parts) == 4:  # SMPTE format
                            h, m, s, frames = map(int, parts)
                            ms_val = int(frames * (1000 / 25))  # 25 fps
                            return (h * 3600 + m * 60 + s) * 1000 + ms_val
                else:
                    # Seconds format
                    seconds = float(time_str.rstrip("s"))
                    return int(seconds * 1000)
            return None
        except (ValueError, IndexError):
            return None

    def ms_to_time(ms: int, fmt: str, original: str = None) -> str:
        """Convert milliseconds to time string based on format."""
        h = ms // 3600000
        m = (ms // 60000) % 60
        s = (ms // 1000) % 60
        ms_remainder = ms % 1000

        if fmt == "srt":
            return f"{h:02}:{m:02}:{s:02},{ms_remainder:03}"
        elif fmt == "vtt":
            return f"{h:02}:{m:02}:{s:02}.{ms_remainder:03}"
        elif fmt == "sbv":
            return f"{h}:{m:02}:{s:02}.{ms_remainder:03}"
        elif fmt in ["sub", "ass_ssa"]:
            cs = ms_remainder // 10
            return f"{h:02}:{m:02}:{s:02}.{cs:02}"
        elif fmt == "stl":
            f = ms_remainder // 40  # 25 fps
            return f"{h:02}:{m:02}:{s:02}:{f:02}"
        elif fmt == "dfxp":
            return f"{h:02}:{m:02}:{s:02},{ms_remainder:03}"
        elif fmt in ["ttml", "itt"]:
            if original and ":" not in original:
                # Seconds format
                total_seconds = ms / 1000
                return f"{total_seconds:.3f}".rstrip("0").rstrip(".") + "s"
            elif original and ":" in original and "." not in original:
                # SMPTE format
                frames = int(round(ms_remainder / 1000 * 25))  # 25 fps
                return f"{h:02}:{m:02}:{s:02}:{frames:02}"
            else:
                # Default format
                return f"{h:02}:{m:02}:{s:02}.{ms_remainder:03}"
        return str(ms)

    def shift_timestamp(timestamp: str, fmt: str, original: str = None) -> str:
        """Shift a single timestamp."""
        ms = time_to_ms(timestamp, fmt)
        if ms is None:
            logger.warning(f"Failed to parse timestamp: {timestamp}")
            return timestamp
        shifted_ms = max(0, ms + milliseconds)
        return ms_to_time(shifted_ms, fmt, original)

    # Format-specific shifting functions
    shift_functions = {
        ".srt": lambda line: (
            re.sub(
                r"(\d{2}:\d{2}:\d{2}[,\.]\d{3}) --> (\d{2}:\d{2}:\d{2}[,\.]\d{3})",
                lambda m: f"{shift_timestamp(m.group(1), 'srt')} --> {shift_timestamp(m.group(2), 'srt')}",
                line,
            )
            if "-->" in line
            else line
        ),
        ".vtt": lambda line: (
            re.sub(
                r"(\d{2}:\d{2}:\d{2}[,\.]\d{3}) --> (\d{2}:\d{2}:\d{2}[,\.]\d{3})",
                lambda m: f"{shift_timestamp(m.group(1), 'vtt')} --> {shift_timestamp(m.group(2), 'vtt')}",
                line,
            )
            if "-->" in line
            else line
        ),
        ".sbv": lambda line: (
            re.sub(
                r"(\d+:\d{2}:\d{2}\.\d{3}),(\d+:\d{2}:\d{2}\.\d{3})",
                lambda m: f"{shift_timestamp(m.group(1), 'sbv')},{shift_timestamp(m.group(2), 'sbv')}",
                line,
            )
            if "," in line
            else line
        ),
        ".sub": lambda line: (
            re.sub(
                r"(\d{2}:\d{2}:\d{2}\.\d{2})\s*,\s*(\d{2}:\d{2}:\d{2}\.\d{2})",
                lambda m: f"{shift_timestamp(m.group(1), 'sub')},{shift_timestamp(m.group(2), 'sub')}",
                line,
            )
            if "," in line
            else line
        ),
        ".stl": lambda line: (
            re.sub(
                r"(\d{1,2}:\d{2}:\d{2}:\d{2})\s*,\s*(\d{1,2}:\d{2}:\d{2}:\d{2})(.*)",
                lambda m: f"{shift_timestamp(m.group(1), 'stl')} , {shift_timestamp(m.group(2), 'stl')}{m.group(3)}",
                line,
            )
            if "," in line
            else line
        ),
        ".dfxp": lambda line: re.sub(
            r'begin="([\d:,\.]+)"\s+end="([\d:,\.]+)"',
            lambda m: f'begin="{shift_timestamp(m.group(1), "dfxp")}" end="{shift_timestamp(m.group(2), "dfxp")}"',
            line,
        ),
        ".ttml": lambda line: re.sub(
            r'\b(begin|end)="([^"]+)"',
            lambda m: f'{m.group(1)}="{shift_timestamp(m.group(2), "ttml", m.group(2))}"',
            line,
        ),
        ".itt": lambda line: re.sub(
            r'\b(begin|end)="([^"]+)"',
            lambda m: f'{m.group(1)}="{shift_timestamp(m.group(2), "itt", m.group(2))}"',
            line,
        ),
        ".ass": lambda line: re.sub(
            r"(\d{1,2}:\d{2}:\d{2}\.\d{2}),(\d{1,2}:\d{2}:\d{2}\.\d{2})",
            lambda m: f"{shift_timestamp(m.group(1), 'ass_ssa')},{shift_timestamp(m.group(2), 'ass_ssa')}",
            line,
        ),
        ".ssa": lambda line: re.sub(
            r"(\d{1,2}:\d{2}:\d{2}\.\d{2}),(\d{1,2}:\d{2}:\d{2}\.\d{2})",
            lambda m: f"{shift_timestamp(m.group(1), 'ass_ssa')},{shift_timestamp(m.group(2), 'ass_ssa')}",
            line,
        ),
        ".smi": lambda line: re.sub(
            r"<SYNC Start=(\d+)",
            lambda m: f"<SYNC Start={max(0, int(m.group(1)) + milliseconds)}",
            line,
        ),
    }

    # Process lines
    shift_func = shift_functions.get(file_extension, lambda line: line)
    new_lines = [shift_func(line) for line in lines]

    # Write output file
    try:
        with open(output_file, "w", encoding=encoding, errors="replace") as file:
            file.write("\n".join(new_lines))

        success_msg = texts.SUBTITLE_SHIFTED_SUCCESSFULLY.format(
            milliseconds=milliseconds, output_file=output_file
        )
        logger.info(f"Successfully shifted subtitle by {milliseconds}ms: {output_file}")

        return output_file, True, success_msg

    except Exception as e:
        error_msg = texts.ERROR_SAVING_SHIFTED_SUBTITLE.format(error=str(e))
        logger.error(f"Error saving shifted subtitle: {str(e)}")
        return None, False, error_msg
