import json
import os
import shutil
from dataclasses import dataclass, field
from typing import Optional

import texts
from utils import create_process, detect_encoding, terminate_process_safely
from constants import (
    DEFAULT_OPTIONS,
    FFMPEG_EXECUTABLE,
    FFPROBE_EXECUTABLE,
    EXTRACTABLE_SUBTITLE_EXTENSIONS,
    SUBTITLE_EXTENSIONS,
    AUDIO_EXTENSIONS,
    SYNC_TOOLS,
    is_remote_url,
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
    cleanup_files: list = field(default_factory=list)
    pgs_checked: bool = False
    pgs_used_message: Optional[str] = None
    cancelled: bool = False


def should_extract_subtitles(reference, tool, config, override=None):
    """Return whether embedded-subtitle extraction applies to this sync."""
    if is_remote_url(reference):
        return False

    if os.path.splitext(reference)[1].lower() in SUBTITLE_EXTENSIONS:
        return False

    # Audio-only references have no embedded subtitle streams; sync_core
    # wraps them into an .mp4 later, which would not add any either.
    if os.path.splitext(reference)[1].lower() in AUDIO_EXTENSIONS:
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
    on_log=None,
    on_progress=None,
    on_stage=None,
    is_cancelled=None,
    process_holder=None,
):
    """Prepare a video reference, optionally replacing it with an embedded subtitle.

    Extraction failures are deliberately non-fatal: callers always receive the
    original reference as a fallback. When streaming callbacks are provided
    (on_log, on_progress, on_stage, is_cancelled, process_holder), messages,
    stage transitions, and progress percentages are emitted live as each step runs.
    """
    enabled = should_extract_subtitles(reference, tool, config, override)
    result = SubtitleExtractionResult(
        original_reference=reference,
        effective_reference=reference,
        enabled=enabled,
    )
    if not enabled:
        return result

    def emit(msg, color="grey", overwrite=False):
        text = str(msg)
        if not overwrite:
            result.messages.append(text)
        if on_log is not None:
            on_log(text, color, overwrite)

    if on_stage is not None:
        on_stage("probe_streams")
    emit(texts.CHECKING_VIDEO_FOR_EMBEDDED_SUBTITLES, "grey")
    if is_cancelled and is_cancelled():
        result.cancelled = True
        return result

    if not config.get(
        "keep_extracted_subtitles",
        DEFAULT_OPTIONS["keep_extracted_subtitles"],
    ):
        result.cleanup_dir = os.path.join(
            output_dir, "extracted_subtitles_" + os.path.basename(reference)
        )
    probe_meta = {}
    try:
        try:
            extracted, score, messages, subtitle_streams = _extract_subtitles_with_streams(
                reference,
                subtitle,
                output_dir,
                on_log=emit,
                on_progress=on_progress,
                on_stage=on_stage,
                is_cancelled=is_cancelled,
                process_holder=process_holder,
                probe_meta=probe_meta,
            )
        except TypeError:
            # Support tests or callers monkeypatching _extract_subtitles_with_streams
            # with the minimal 3-argument signature.
            extracted, score, messages, subtitle_streams = _extract_subtitles_with_streams(
                reference, subtitle, output_dir
            )
            for m in messages:
                emit(m, "grey")

        if is_cancelled and is_cancelled():
            result.cancelled = True
            cleanup_extracted_subtitles(result)
            return result

        result.score = score
        if extracted:
            if on_stage is not None:
                on_stage("extract_embedded_done")
            result.extracted_subtitle = extracted
            result.effective_reference = extracted
            emit(
                texts.EXTRACTION_SELECTED_WITH_TIMESTAMP.format(
                    filename=os.path.basename(extracted), score=score
                ),
                "grey",
            )
            return result

        if tool == "alass":
            result.pgs_checked = True
            # Reuse the header-only ffprobe stream list so videos without PGS
            # streams never trigger a second ffprobe call or packet scan.
            pgs_streams = [
                f"0:s:{idx}"
                for idx, (_, codec, _) in enumerate(subtitle_streams)
                if codec == "hdmv_pgs_subtitle"
            ]
            if pgs_streams:
                if on_stage is not None:
                    on_stage("pgs_scan")
                emit(texts.CHECKING_VIDEO_FOR_PGS_SUBTITLES, "grey")
                from utils import extract_pgs_timings_to_srt

                duration_sec = probe_meta.get("duration_sec")

                def pgs_progress_cb(pct):
                    pct_int = int(pct)
                    if on_progress is not None:
                        on_progress(float(pct))
                    if on_log is not None:
                        on_log(
                            str(texts.SCANNING_PGS_SUBTITLES_PROGRESS).format(
                                percent=pct_int
                            ),
                            "grey",
                            True,
                        )

                pgs_kwargs = {
                    "stream": pgs_streams[0],
                    "min_cues": 1,
                }
                if (
                    on_progress is not None
                    or on_log is not None
                    or is_cancelled is not None
                    or process_holder is not None
                ):
                    pgs_kwargs.update(
                        {
                            "duration_sec": duration_sec,
                            "progress_cb": pgs_progress_cb,
                            "is_cancelled": is_cancelled,
                            "process_holder": process_holder,
                        }
                    )

                pgs_srt, reason, cue_count = extract_pgs_timings_to_srt(
                    reference, **pgs_kwargs
                )
                if is_cancelled and is_cancelled():
                    result.cancelled = True
                    if pgs_srt and os.path.exists(pgs_srt):
                        try:
                            os.remove(pgs_srt)
                        except OSError:
                            pass
                    return result
                if pgs_srt:
                    if on_stage is not None:
                        on_stage("pgs_scan_done")
                    result.extracted_subtitle = pgs_srt
                    result.effective_reference = pgs_srt
                    result.cleanup_files.append(pgs_srt)
                    success_msg = str(
                        texts.USING_EMBEDDED_PGS_SUBTITLES_AS_REFERENCE
                    ).format(reason=reason, cue_count=cue_count)
                    result.pgs_used_message = success_msg
                    emit(success_msg, "green")
                    return result
                emit(
                    str(texts.NO_USABLE_PGS_FALLBACK_VIDEO_AUDIO).format(reason=reason),
                    "grey",
                )
                return result

        emit(texts.EXTRACTION_NO_COMPATIBLE_SUBTITLES, "grey")
    except Exception as exc:
        emit(texts.EXTRACTION_FAILED_PREFIX + str(exc), "grey")
    except BaseException:
        cleanup_extracted_subtitles(result)
        raise
    return result


def cleanup_extracted_subtitles(result):
    """Remove temporary extraction output when the result requests cleanup."""
    if not result:
        return
    if result.cleanup_dir:
        try:
            if os.path.isdir(result.cleanup_dir):
                shutil.rmtree(result.cleanup_dir)
        finally:
            result.cleanup_dir = None
    if result.cleanup_files:
        try:
            for path in result.cleanup_files:
                if path and os.path.exists(path):
                    os.remove(path)
        finally:
            result.cleanup_files.clear()


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
    best_subtitle, best_score, log_messages, _ = _extract_subtitles_with_streams(
        video_file, subtitle_file, output_dir
    )
    return best_subtitle, best_score, log_messages


def _parse_ffprobe_streams_json(output_text):
    """Parse subtitle streams and container duration from ffprobe JSON output."""
    subtitle_streams = []
    duration_sec = None
    json_start = output_text.find("{")
    if json_start < 0:
        return subtitle_streams, duration_sec
    data = json.loads(output_text[json_start:])
    raw_duration = (data.get("format") or {}).get("duration")
    if raw_duration not in (None, "N/A", ""):
        try:
            dur = float(raw_duration)
            if dur > 0:
                duration_sec = dur
        except (ValueError, TypeError):
            pass
    for stream in data.get("streams") or []:
        idx = stream.get("index")
        codec = str(stream.get("codec_name") or "").strip()
        tags = stream.get("tags") or {}
        language = str(tags.get("language") or "").strip()
        if idx is not None and codec:
            subtitle_streams.append((str(idx), codec, language))
    return subtitle_streams, duration_sec


def _extract_subtitles_with_streams(
    video_file,
    subtitle_file,
    output_dir,
    *,
    on_log=None,
    on_progress=None,
    on_stage=None,
    is_cancelled=None,
    process_holder=None,
    probe_meta=None,
):
    """Extract compatible embedded subtitles and also return header-probed subtitle streams."""
    log_messages = []
    subtitle_streams = []

    def emit(msg, color="grey", overwrite=False):
        text = str(msg)
        if not overwrite:
            log_messages.append(text)
        if on_log is not None:
            on_log(text, color, overwrite)

    # Fast validation
    if not os.path.exists(video_file):
        emit(texts.VIDEO_FILE_NOT_FOUND.format(video_file=video_file), "grey")
        return None, None, log_messages, subtitle_streams
    ffprobe_cmd = [
        FFPROBE_EXECUTABLE,
        "-v",
        "error",
        "-select_streams",
        "s",
        "-show_entries",
        "format=duration:stream=index,codec_name:stream_tags=language,title",
        "-of",
        "json",
        video_file,
    ]
    probe_process = None
    ffmpeg_process = None
    try:
        # Use create_process for ffprobe
        probe_process = create_process(ffprobe_cmd)
        if process_holder is not None:
            process_holder["process"] = probe_process
        output, _ = probe_process.communicate()
        if process_holder is not None and process_holder.get("process") is probe_process:
            process_holder["process"] = None

        if is_cancelled and is_cancelled():
            return None, None, log_messages, subtitle_streams

        if probe_process.returncode != 0:
            emit(texts.FFPROBE_FAILED_TO_ANALYZE_VIDEO, "grey")
            return None, None, log_messages, subtitle_streams

        output_text = output.decode("utf-8", errors="replace") if isinstance(output, bytes) else output
        subtitle_streams, duration_sec = _parse_ffprobe_streams_json(output_text)
        if probe_meta is not None and duration_sec is not None:
            probe_meta["duration_sec"] = duration_sec

        # Filter compatible subtitles
        compatible_subtitles = [
            stream
            for stream in subtitle_streams
            if stream[1] in EXTRACTABLE_SUBTITLE_EXTENSIONS
        ]
        if not compatible_subtitles:
            return None, None, log_messages, subtitle_streams
        # Setup output directory
        output_folder = os.path.join(
            output_dir, "extracted_subtitles_" + os.path.basename(video_file)
        )
        os.makedirs(output_folder, exist_ok=True)
        emit(
            texts.FOUND_COMPATIBLE_SUBTITLES_EXTRACTING.format(
                count=len(compatible_subtitles), output_folder=output_folder
            ),
            "grey",
        )
        # Prepare FFmpeg command with machine-readable progress on stdout
        ffmpeg_base_cmd = [
            FFMPEG_EXECUTABLE,
            "-y",
            "-v",
            "error",
            "-nostats",
            "-progress",
            "pipe:1",
            "-i",
            video_file,
        ]
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
            return None, None, log_messages, subtitle_streams

        # Execute FFmpeg and stream progress live
        if on_stage is not None:
            on_stage("extract_embedded")
        ffmpeg_process = create_process(ffmpeg_base_cmd)
        if process_holder is not None:
            process_holder["process"] = ffmpeg_process
        error_lines = []
        last_pct = -1
        if ffmpeg_process.stdout is not None:
            for raw_line in ffmpeg_process.stdout:
                if is_cancelled and is_cancelled():
                    terminate_process_safely(ffmpeg_process)
                    ffmpeg_process.wait()
                    return None, None, log_messages, subtitle_streams
                line = (
                    raw_line.decode("utf-8", errors="replace").strip()
                    if isinstance(raw_line, bytes)
                    else str(raw_line).strip()
                )
                if not line:
                    continue
                if line.startswith("out_time_us=") and duration_sec and duration_sec > 0:
                    try:
                        out_us = int(line.split("=", 1)[1])
                        if out_us >= 0:
                            pct = min(99, max(0, int((out_us / 1_000_000.0 / duration_sec) * 100)))
                            if pct > last_pct:
                                last_pct = pct
                                if on_progress is not None:
                                    on_progress(float(pct))
                                if on_log is not None:
                                    emit(
                                        texts.EXTRACTING_EMBEDDED_SUBTITLES_PROGRESS.format(
                                            percent=pct
                                        ),
                                        "grey",
                                        overwrite=True,
                                    )
                    except (ValueError, TypeError):
                        pass
                elif line == "progress=end" and duration_sec and duration_sec > 0 and last_pct < 100:
                    last_pct = 100
                    if on_progress is not None:
                        on_progress(100.0)
                    if on_log is not None:
                        emit(
                            texts.EXTRACTING_EMBEDDED_SUBTITLES_PROGRESS.format(percent=100),
                            "grey",
                            overwrite=True,
                        )
                elif "=" not in line:
                    error_lines.append(line)
            ffmpeg_process.stdout.close()
        rc = ffmpeg_process.wait()
        if process_holder is not None and process_holder.get("process") is ffmpeg_process:
            process_holder["process"] = None

        if is_cancelled and is_cancelled():
            return None, None, log_messages, subtitle_streams

        if rc == 0:
            if last_pct >= 0 and last_pct < 100:
                if on_progress is not None:
                    on_progress(100.0)
                if on_log is not None:
                    emit(
                        texts.EXTRACTING_EMBEDDED_SUBTITLES_PROGRESS.format(percent=100),
                        "grey",
                        overwrite=True,
                    )
            elif on_progress is not None and last_pct < 100:
                on_progress(100.0)
            for output_file in output_files:
                emit(
                    texts.SUCCESSFULLY_EXTRACTED_SUBTITLE.format(
                        filename=os.path.basename(output_file)
                    ),
                    "grey",
                )
            emit(texts.CHOOSING_BEST_SUBTITLE_MATCH, "grey")
            closest_subtitle, score = choose_best_subtitle(
                subtitle_file, extracted_subtitles_folder=output_folder
            )
            if closest_subtitle:
                return closest_subtitle, score, log_messages, subtitle_streams
            return None, None, log_messages, subtitle_streams

        error_output = "\n".join(error_lines)
        emit(texts.SUBTITLE_EXTRACTION_FAILED.format(error=error_output), "grey")
        return None, None, log_messages, subtitle_streams
    except Exception as e:
        emit(texts.SUBTITLE_EXTRACTION_FAILED.format(error=str(e)), "grey")
        return None, None, log_messages, subtitle_streams
    finally:
        for proc in (probe_process, ffmpeg_process):
            if proc is not None and process_holder is not None and process_holder.get("process") is proc:
                process_holder["process"] = None
