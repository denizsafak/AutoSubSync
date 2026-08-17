import os
import shutil
from dataclasses import dataclass, field
from typing import Optional

import texts
from utils import create_process, detect_encoding
from constants import (
    DEFAULT_OPTIONS,
    FFMPEG_EXECUTABLE,
    FFPROBE_EXECUTABLE,
    EXTRACTABLE_SUBTITLE_EXTENSIONS,
    SUBTITLE_EXTENSIONS,
    SYNC_TOOLS,
)


@dataclass
class SubtitleExtractionResult:
    """Result of preparing a reference for subtitle synchronization."""

    original_reference: str
    effective_reference: str
    enabled: bool = False
    extracted_subtitle: Optional[str] = None
    score: object = None
    messages: list = field(default_factory=list)
    cleanup_dir: Optional[str] = None


def should_extract_subtitles(reference, tool, config, override=None):
    """Return whether embedded-subtitle extraction applies to this sync."""
    if os.path.splitext(reference)[1].lower() in SUBTITLE_EXTENSIONS:
        return False

    # Tools that natively search and parse embedded subtitles (like lapse)
    # should NOT use external ffmpeg pre-extraction.
    if tool == "lapse":
        return False

    tool_info = SYNC_TOOLS.get(tool, {})
    option = tool_info.get("options", {}).get("check_video_for_subtitles")
    if not option:
        return False
    if override is not None:
        return bool(override)
    return bool(
        config.get(
            f"{tool}_check_video_for_subtitles",
            option.get("default", False),
        )
    )


def prepare_sync_reference(
    reference,
    subtitle,
    output_dir,
    *,
    tool,
    config,
    override=None,
):
    """Prepare a video reference, optionally replacing it with an embedded subtitle.

    Extraction failures are deliberately non-fatal: callers always receive the
    original reference as a fallback.
    """
    enabled = should_extract_subtitles(reference, tool, config, override)
    result = SubtitleExtractionResult(
        original_reference=reference,
        effective_reference=reference,
        enabled=enabled,
    )
    if not enabled:
        return result

    result.messages.append(texts.CHECKING_VIDEO_FOR_EMBEDDED_SUBTITLES)
    if not config.get(
        "keep_extracted_subtitles",
        DEFAULT_OPTIONS["keep_extracted_subtitles"],
    ):
        result.cleanup_dir = os.path.join(
            output_dir, "extracted_subtitles_" + os.path.basename(reference)
        )
    try:
        extracted, score, messages = extract_subtitles(reference, subtitle, output_dir)
        result.messages.extend(messages)
        result.score = score
        if extracted:
            result.extracted_subtitle = extracted
            result.effective_reference = extracted
            result.messages.append(
                texts.EXTRACTION_SELECTED_WITH_TIMESTAMP.format(
                    filename=os.path.basename(extracted), score=score
                )
            )
        else:
            result.messages.append(texts.EXTRACTION_NO_COMPATIBLE_SUBTITLES)
    except Exception as exc:
        result.messages.append(texts.EXTRACTION_FAILED_PREFIX + str(exc))
    except BaseException:
        cleanup_extracted_subtitles(result)
        raise
    return result


def cleanup_extracted_subtitles(result):
    """Remove temporary extraction output when the result requests cleanup."""
    if not result or not result.cleanup_dir:
        return
    try:
        if os.path.isdir(result.cleanup_dir):
            shutil.rmtree(result.cleanup_dir)
    finally:
        result.cleanup_dir = None


def parse_timestamps(subtitle_file):
    # Fast timestamp extraction for comparison
    try:
        sub_encoding = detect_encoding(subtitle_file)
        ext = os.path.splitext(subtitle_file)[1].lower()

        with open(subtitle_file, "r", encoding=sub_encoding, errors="replace") as file:
            # Read file once and process efficiently
            if ext in (".srt", ".vtt"):
                return [
                    float(line.split("-->")[0].strip().replace(",", ".").split(":")[0])
                    * 3600
                    + float(
                        line.split("-->")[0].strip().replace(",", ".").split(":")[1]
                    )
                    * 60
                    + float(
                        line.split("-->")[0].strip().replace(",", ".").split(":")[2]
                    )
                    for line in file
                    if "-->" in line
                ]
            elif ext in (".ass", ".ssa"):
                return [
                    float(line.split(",")[1].strip().split(":")[0]) * 3600
                    + float(line.split(",")[1].strip().split(":")[1]) * 60
                    + float(line.split(",")[1].strip().split(":")[2])
                    for line in file
                    if line.startswith("Dialogue")
                ]
        return []
    except Exception:
        return None


def choose_best_subtitle(subtitle_file, extracted_subtitles_folder):
    reference_times = parse_timestamps(subtitle_file)
    if not reference_times:
        # If reference_times is None, find the longest subtitle file
        longest_subtitle = None
        longest_length = 0
        for file in os.listdir(extracted_subtitles_folder):
            candidate = os.path.join(extracted_subtitles_folder, file)
            candidate_times = parse_timestamps(candidate)
            if candidate_times and len(candidate_times) > longest_length:
                longest_length = len(candidate_times)
                longest_subtitle = candidate
        return longest_subtitle, texts.USED_LONGEST_SUBTITLE_FILE
    best_subtitle = None
    best_score = float("inf")
    for file in os.listdir(extracted_subtitles_folder):
        candidate = os.path.join(extracted_subtitles_folder, file)
        candidate_times = parse_timestamps(candidate)
        if not candidate_times:
            continue
        # Compare the count of timestamps
        diff_count = abs(len(reference_times) - len(candidate_times))
        if diff_count < best_score:
            best_score = diff_count
            best_subtitle = candidate
    return best_subtitle, best_score


def extract_subtitles(video_file, subtitle_file, output_dir):
    """
    Extract subtitles from video and choose the best match.

    Args:
        video_file: Path to the video file
        subtitle_file: Path to the reference subtitle file
        output_dir: Directory to extract subtitles to

    Returns:
        tuple: (best_subtitle_path, best_score, log_messages) or (None, None, log_messages) if failed
    """
    log_messages = []

    # Fast validation
    if not os.path.exists(video_file):
        log_messages.append(texts.VIDEO_FILE_NOT_FOUND.format(video_file=video_file))
        return None, None, log_messages
    ffprobe_cmd = [
        FFPROBE_EXECUTABLE,
        "-v",
        "error",
        "-select_streams",
        "s",
        "-show_entries",
        "stream=index,codec_name:stream_tags=language,title",
        "-of",
        "csv=p=0",
        video_file,
    ]
    try:
        # Use create_process for ffprobe
        probe_process = create_process(ffprobe_cmd)
        output, _ = probe_process.communicate()

        if probe_process.returncode != 0:
            log_messages.append(texts.FFPROBE_FAILED_TO_ANALYZE_VIDEO)
            return None, None, log_messages
        # Parse subtitle streams
        subtitle_streams = []
        output_text = output.decode("utf-8") if isinstance(output, bytes) else output
        for line in output_text.splitlines():
            if not line.strip():
                continue
            parts = line.split(",")
            if len(parts) >= 2:
                stream_index = parts[0].strip()
                codec_name = parts[1].strip()
                language = parts[2].strip() if len(parts) > 2 else ""
                subtitle_streams.append((stream_index, codec_name, language))
        # Filter compatible subtitles
        compatible_subtitles = [
            stream
            for stream in subtitle_streams
            if stream[1] in EXTRACTABLE_SUBTITLE_EXTENSIONS
        ]
        if not compatible_subtitles:
            return None, None, log_messages
        # Setup output directory
        output_folder = os.path.join(
            output_dir, "extracted_subtitles_" + os.path.basename(video_file)
        )
        os.makedirs(output_folder, exist_ok=True)
        log_messages.append(
            texts.FOUND_COMPATIBLE_SUBTITLES_EXTRACTING.format(
                count=len(compatible_subtitles), output_folder=output_folder
            )
        )
        # Prepare FFmpeg command
        ffmpeg_base_cmd = [FFMPEG_EXECUTABLE, "-y", "-i", video_file]
        output_files = []
        # Add subtitle mappings
        for i, (stream, codec, language) in enumerate(compatible_subtitles):
            ext = EXTRACTABLE_SUBTITLE_EXTENSIONS.get(codec)
            if not ext:
                continue
            lang_suffix = f"_{language}" if language else ""
            output_file = os.path.join(
                output_folder, f"subtitle_{i+1}{lang_suffix}.{ext}"
            )
            output_files.append(output_file)
            ffmpeg_base_cmd.extend(["-map", f"0:{stream}", "-c:s", codec, output_file])
        if not output_files:
            return None, None, log_messages
        # Execute FFmpeg using create_process
        ffmpeg_process = create_process(ffmpeg_base_cmd)
        output, _ = ffmpeg_process.communicate()
        if ffmpeg_process.returncode == 0:
            for output_file in output_files:
                log_messages.append(
                    texts.SUCCESSFULLY_EXTRACTED_SUBTITLE.format(
                        filename=os.path.basename(output_file)
                    )
                )
            log_messages.append(texts.CHOOSING_BEST_SUBTITLE_MATCH)
            closest_subtitle, score = choose_best_subtitle(
                subtitle_file, extracted_subtitles_folder=output_folder
            )
            if closest_subtitle:
                return closest_subtitle, score, log_messages
            return None, None, log_messages

        error_output = output.decode("utf-8") if isinstance(output, bytes) else output
        log_messages.append(texts.SUBTITLE_EXTRACTION_FAILED.format(error=error_output))
        return None, None, log_messages
    except Exception as e:
        log_messages.append(texts.SUBTITLE_EXTRACTION_FAILED.format(error=str(e)))
        return None, None, log_messages
