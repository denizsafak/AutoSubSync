import json
import os
import re
import shutil
from dataclasses import dataclass, field
from typing import Optional

import texts
from utils import (
    check_file_writable,
    create_process,
    detect_encoding,
    pick_unique_path,
    terminate_process_safely,
)
from constants import (
    DEFAULT_OPTIONS,
    FFMPEG_EXECUTABLE,
    FFPROBE_EXECUTABLE,
    NEEDS_STATIC_FFMPEG,
    EXTRACTABLE_SUBTITLE_EXTENSIONS,
    SUBTITLE_EXTENSIONS,
    AUDIO_EXTENSIONS,
    SYNC_TOOLS,
    is_remote_url,
    is_video_extension,
)

# Prefix used when extracting embedded subtitle tracks next to a video file.
EXTRACTED_TRACK_PREFIX = "extracted_track"

_FFSUBSYNC_AUDIO_VAD_FALLBACK = {
    "default": "webrtc",
    "subs_then_webrtc": "webrtc",
    "subs_then_auditok": "auditok",
    "subs_then_silero": "silero",
}

# Map container subtitle codecs reported by ffprobe to the ffmpeg encoder
# required to serialize each stream into its target text subtitle format.
_SUBTITLE_CODEC_ENCODERS = {
    "subrip": "srt",
    "srt": "srt",
    "ass": "ass",
    "ssa": "ssa",
    "webvtt": "webvtt",
    "mov_text": "srt",
}


@dataclass(frozen=True)
class EmbeddedSubtitleStream:
    """Metadata describing an embedded subtitle stream inside a video file."""

    stream_index: str
    subtitle_order: int
    codec_name: str
    extension: Optional[str] = None
    language: str = ""
    title: str = ""
    is_default: bool = False
    is_forced: bool = False

    @property
    def is_extractable(self) -> bool:
        """Return True if this stream can be extracted to a standalone subtitle file."""
        return bool(self.extension)


@dataclass
class SubtitleProbeResult:
    """Result of probing a video container for embedded subtitle streams."""

    streams: list[EmbeddedSubtitleStream] = field(default_factory=list)
    duration_sec: Optional[float] = None
    error: Optional[str] = None
    cancelled: bool = False

    @property
    def extractable_streams(self) -> list[EmbeddedSubtitleStream]:
        """Return only embedded subtitle streams that can be extracted as text files."""
        return [stream for stream in self.streams if stream.is_extractable]


@dataclass
class SubtitleSelectionExtractionResult:
    """Result of extracting user-selected embedded subtitles next to a video."""

    extracted_files: list[str] = field(default_factory=list)
    error: Optional[str] = None
    cancelled: bool = False


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


def is_extracted_track_subtitle(subtitle_path: Optional[str]) -> bool:
    """Return True if ``subtitle_path`` basename starts with ``extracted_track``."""
    if not subtitle_path or not isinstance(subtitle_path, str):
        return False
    return os.path.basename(subtitle_path).lower().startswith(EXTRACTED_TRACK_PREFIX)


def resolve_sync_config_for_subtitle(
    reference: Optional[str],
    subtitle: Optional[str],
    config: Optional[dict],
) -> dict:
    """Return an effective sync config with embedded subtitle checks disabled when needed.

    When the ``sync_extracted_tracks_against_audio`` setting is enabled,
    ``reference`` is a local video file, and ``subtitle`` starts with
    ``extracted_track``, returns a shallow copy of ``config`` with embedded
    subtitle and PGS reference options disabled across all sync tools (and
    ``ffsubsync_vad`` switched to an audio-only VAD such as ``webrtc``).
    """
    base_config = dict(DEFAULT_OPTIONS) if config is None else config
    if not base_config.get(
        "sync_extracted_tracks_against_audio",
        DEFAULT_OPTIONS["sync_extracted_tracks_against_audio"],
    ):
        return base_config
    if not is_video_extension(reference) or not is_extracted_track_subtitle(subtitle):
        return base_config

    effective = dict(base_config)
    for tool_name, tool_data in SYNC_TOOLS.items():
        if "check_video_for_subtitles" in tool_data.get("options", {}):
            effective[f"{tool_name}_check_video_for_subtitles"] = False

    lapse_info = SYNC_TOOLS.get("lapse", {})
    lapse_all_opts = {
        **lapse_info.get("options", {}),
        **lapse_info.get("other_options", {}),
    }
    if "sub_track" in lapse_all_opts:
        effective["lapse_sub_track"] = -1

    effective["ffsubsync_use_pgs_subtitles"] = False
    current_vad = effective.get(
        "ffsubsync_vad", DEFAULT_OPTIONS.get("ffsubsync_vad", "default")
    )
    if not current_vad or current_vad in _FFSUBSYNC_AUDIO_VAD_FALLBACK:
        effective["ffsubsync_vad"] = _FFSUBSYNC_AUDIO_VAD_FALLBACK.get(
            current_vad, "webrtc"
        )
    return effective


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
    effective_config = resolve_sync_config_for_subtitle(reference, subtitle, config)
    enabled = should_extract_subtitles(reference, tool, effective_config, override)
    result = SubtitleExtractionResult(
        original_reference=reference,
        effective_reference=reference,
        enabled=enabled,
    )
    if not enabled:
        return result

    def emit(msg, color="grey", overwrite=False):
        """Record log output and forward live updates when a callback is attached."""
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


def _resolve_media_binary(executable: str) -> str:
    """Resolve an FFmpeg/FFprobe binary, activating cached static_ffmpeg paths if needed."""
    if not executable:
        return executable
    if (
        os.path.isabs(executable)
        or os.path.sep in executable
        or (os.path.altsep and os.path.altsep in executable)
        or shutil.which(executable)
    ):
        return executable
    if NEEDS_STATIC_FFMPEG:
        try:
            import static_ffmpeg
            from static_ffmpeg import run as ffmpeg_run

            platform_dir = ffmpeg_run.get_platform_dir()
            if os.path.isdir(platform_dir):
                static_ffmpeg.add_paths()
        except Exception:
            pass
    return executable


def _get_subtitle_encoder(codec_name: str) -> str:
    """Return the ffmpeg subtitle encoder name for the given ffprobe codec."""
    return _SUBTITLE_CODEC_ENCODERS.get(codec_name, codec_name)


def _sanitize_language_tag(language: str) -> str:
    """Return a filesystem-safe language tag, ignoring empty or unknown tags."""
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "", (language or "").strip())
    if cleaned.lower() in ("", "und", "unknown"):
        return ""
    return cleaned[:32]


def _parse_ffprobe_streams_details(
    output_text: str,
) -> tuple[list[EmbeddedSubtitleStream], Optional[float]]:
    """Parse detailed subtitle stream metadata and duration from ffprobe JSON."""
    streams: list[EmbeddedSubtitleStream] = []
    duration_sec: Optional[float] = None
    json_start = output_text.find("{")
    if json_start < 0:
        return streams, duration_sec

    data = json.loads(output_text[json_start:])
    raw_duration = (data.get("format") or {}).get("duration")
    if raw_duration not in (None, "N/A", ""):
        try:
            dur = float(raw_duration)
            if dur > 0:
                duration_sec = dur
        except (ValueError, TypeError):
            pass

    for order, stream in enumerate(data.get("streams") or [], start=1):
        idx = stream.get("index")
        codec = str(stream.get("codec_name") or "").strip()
        if idx is None or not codec:
            continue
        tags = stream.get("tags") or {}
        disposition = stream.get("disposition") or {}
        language = str(tags.get("language") or "").strip()
        title = str(tags.get("title") or "").strip()
        ext = EXTRACTABLE_SUBTITLE_EXTENSIONS.get(codec)
        streams.append(
            EmbeddedSubtitleStream(
                stream_index=str(idx),
                subtitle_order=order,
                codec_name=codec,
                extension=ext,
                language=language,
                title=title,
                is_default=bool(disposition.get("default")),
                is_forced=bool(disposition.get("forced")),
            )
        )
    return streams, duration_sec


def _parse_ffprobe_streams_json(output_text):
    """Parse subtitle streams and container duration from ffprobe JSON output."""
    detailed_streams, duration_sec = _parse_ffprobe_streams_details(output_text)
    subtitle_streams = [
        (stream.stream_index, stream.codec_name, stream.language)
        for stream in detailed_streams
    ]
    return subtitle_streams, duration_sec


def probe_embedded_subtitles(
    video_file: str,
    *,
    is_cancelled=None,
    process_holder: Optional[dict] = None,
) -> SubtitleProbeResult:
    """Probe a video file for embedded subtitle streams and container duration.

    Supports cooperative cancellation via ``is_cancelled`` and exposes the
    running ffprobe subprocess through ``process_holder`` so callers can
    terminate long probes immediately.
    """
    if not video_file or not os.path.isfile(video_file):
        return SubtitleProbeResult(
            error=str(texts.VIDEO_FILE_NOT_FOUND).format(video_file=video_file)
        )

    if is_cancelled and is_cancelled():
        return SubtitleProbeResult(cancelled=True)

    ffprobe_cmd = [
        _resolve_media_binary(FFPROBE_EXECUTABLE),
        "-v",
        "error",
        "-select_streams",
        "s",
        "-show_entries",
        "format=duration:stream=index,codec_name:stream_tags=language,title:stream_disposition=default,forced",
        "-of",
        "json",
        video_file,
    ]
    probe_process = None
    try:
        probe_process = create_process(ffprobe_cmd)
        if process_holder is not None:
            process_holder["process"] = probe_process
        output, _ = probe_process.communicate()
        if process_holder is not None and process_holder.get("process") is probe_process:
            process_holder["process"] = None

        if is_cancelled and is_cancelled():
            return SubtitleProbeResult(cancelled=True)

        if probe_process.returncode != 0:
            return SubtitleProbeResult(error=str(texts.FFPROBE_FAILED_TO_ANALYZE_VIDEO))

        output_text = (
            output.decode("utf-8", errors="replace")
            if isinstance(output, bytes)
            else str(output)
        )
        streams, duration_sec = _parse_ffprobe_streams_details(output_text)
        return SubtitleProbeResult(streams=streams, duration_sec=duration_sec)
    except Exception as exc:
        if is_cancelled and is_cancelled():
            return SubtitleProbeResult(cancelled=True)
        return SubtitleProbeResult(
            error=str(texts.SUBTITLE_EXTRACTION_FAILED).format(error=str(exc))
        )
    finally:
        if (
            probe_process is not None
            and process_holder is not None
            and process_holder.get("process") is probe_process
        ):
            process_holder["process"] = None


def build_extracted_subtitle_path(
    video_file: str,
    stream: EmbeddedSubtitleStream,
    *,
    output_dir: Optional[str] = None,
    reserved: Optional[set[str]] = None,
) -> str:
    """Compute a non-colliding ``extracted_track[n]_...`` path for an embedded stream.

    Defaults to the directory containing ``video_file``, names the output
    ``extracted_track<n>_<lang>.<ext>`` (or ``extracted_track<n>_subtitle.<ext>``
    when the language is unknown), and appends ``_2``, ``_3``, ... via
    ``pick_unique_path`` so existing files are never overwritten.
    """
    target_dir = output_dir or os.path.dirname(os.path.abspath(video_file))
    ext = stream.extension or EXTRACTABLE_SUBTITLE_EXTENSIONS.get(stream.codec_name, "srt")
    lang_tag = _sanitize_language_tag(stream.language)
    suffix = lang_tag if lang_tag else "subtitle"
    base_name = f"{EXTRACTED_TRACK_PREFIX}{stream.subtitle_order}_{suffix}.{ext}"
    return pick_unique_path(os.path.join(target_dir, base_name), reserved=reserved)


def _cleanup_partial_outputs(paths: list[str]) -> None:
    """Remove newly created partial output files after a failed or cancelled run."""
    for path in paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


def _run_ffmpeg_extract_streams(
    video_file: str,
    stream_targets: list[tuple[str, str, str]],
    *,
    duration_sec: Optional[float] = None,
    on_log=None,
    on_progress=None,
    on_stage=None,
    is_cancelled=None,
    process_holder: Optional[dict] = None,
) -> tuple[list[str], Optional[str], bool]:
    """Run ffmpeg once to extract one or more subtitle streams with live progress.

    Args:
        video_file: Source video file path.
        stream_targets: Sequence of ``(stream_index, codec_name, output_file)``.
        duration_sec: Optional container duration used to compute percentages.
        on_log: Optional callback ``(message, color, overwrite)``.
        on_progress: Optional callback receiving a ``0.0..100.0`` percentage.
        on_stage: Optional callback notified with ``"extract_embedded"``.
        is_cancelled: Optional zero-arg predicate returning True if cancelled.
        process_holder: Optional dict storing the active subprocess under ``"process"``.

    Returns:
        ``(extracted_paths, error_message, cancelled)``.
    """
    if not stream_targets:
        return [], None, False

    if is_cancelled and is_cancelled():
        return [], None, True

    ffmpeg_cmd = [
        _resolve_media_binary(FFMPEG_EXECUTABLE),
        "-y",
        "-v",
        "error",
        "-nostats",
        "-progress",
        "pipe:1",
        "-i",
        video_file,
    ]
    planned_outputs: list[str] = []
    pre_existing: set[str] = set()
    for stream_index, codec_name, output_file in stream_targets:
        encoder = _get_subtitle_encoder(codec_name)
        if os.path.exists(output_file):
            pre_existing.add(output_file)
        planned_outputs.append(output_file)
        ffmpeg_cmd.extend(["-map", f"0:{stream_index}", "-c:s", encoder, output_file])

    newly_created = [path for path in planned_outputs if path not in pre_existing]
    ffmpeg_process = None
    try:
        if on_stage is not None:
            on_stage("extract_embedded")
        ffmpeg_process = create_process(ffmpeg_cmd)
        if process_holder is not None:
            process_holder["process"] = ffmpeg_process

        error_lines: list[str] = []
        last_pct = -1
        if ffmpeg_process.stdout is not None:
            for raw_line in ffmpeg_process.stdout:
                if is_cancelled and is_cancelled():
                    terminate_process_safely(ffmpeg_process)
                    ffmpeg_process.wait()
                    _cleanup_partial_outputs(newly_created)
                    return [], None, True
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
                            pct = min(
                                99,
                                max(0, int((out_us / 1_000_000.0 / duration_sec) * 100)),
                            )
                            if pct > last_pct:
                                last_pct = pct
                                if on_progress is not None:
                                    on_progress(float(pct))
                                if on_log is not None:
                                    on_log(
                                        texts.EXTRACTING_EMBEDDED_SUBTITLES_PROGRESS.format(
                                            percent=pct
                                        ),
                                        "grey",
                                        True,
                                    )
                    except (ValueError, TypeError):
                        pass
                elif (
                    line == "progress=end"
                    and duration_sec
                    and duration_sec > 0
                    and last_pct < 100
                ):
                    last_pct = 100
                    if on_progress is not None:
                        on_progress(100.0)
                    if on_log is not None:
                        on_log(
                            texts.EXTRACTING_EMBEDDED_SUBTITLES_PROGRESS.format(
                                percent=100
                            ),
                            "grey",
                            True,
                        )
                elif "=" not in line:
                    error_lines.append(line)
            ffmpeg_process.stdout.close()

        rc = ffmpeg_process.wait()
        if process_holder is not None and process_holder.get("process") is ffmpeg_process:
            process_holder["process"] = None

        if is_cancelled and is_cancelled():
            _cleanup_partial_outputs(newly_created)
            return [], None, True

        if rc == 0:
            if last_pct >= 0 and last_pct < 100:
                if on_progress is not None:
                    on_progress(100.0)
                if on_log is not None:
                    on_log(
                        texts.EXTRACTING_EMBEDDED_SUBTITLES_PROGRESS.format(percent=100),
                        "grey",
                        True,
                    )
            elif on_progress is not None and last_pct < 100:
                on_progress(100.0)

            existing_outputs = [p for p in planned_outputs if os.path.isfile(p)]
            if len(existing_outputs) == len(planned_outputs):
                return existing_outputs, None, False
            _cleanup_partial_outputs(newly_created)
            return [], str(texts.SUBTITLE_EXTRACTION_FAILED).format(error="Empty output"), False

        _cleanup_partial_outputs(newly_created)
        error_output = "\n".join(error_lines).strip() or f"ffmpeg exited with code {rc}"
        return [], str(texts.SUBTITLE_EXTRACTION_FAILED).format(error=error_output), False
    except Exception as exc:
        _cleanup_partial_outputs(newly_created)
        if is_cancelled and is_cancelled():
            return [], None, True
        return [], str(texts.SUBTITLE_EXTRACTION_FAILED).format(error=str(exc)), False
    finally:
        if (
            ffmpeg_process is not None
            and process_holder is not None
            and process_holder.get("process") is ffmpeg_process
        ):
            process_holder["process"] = None


def extract_selected_embedded_subtitles(
    video_file: str,
    streams: list[EmbeddedSubtitleStream],
    *,
    output_dir: Optional[str] = None,
    duration_sec: Optional[float] = None,
    on_progress=None,
    is_cancelled=None,
    process_holder: Optional[dict] = None,
) -> SubtitleSelectionExtractionResult:
    """Extract user-selected embedded subtitle streams next to ``video_file``.

    Never overwrites existing subtitle files; collisions are resolved using
    ``_2``, ``_3``, ... suffixes via ``build_extracted_subtitle_path``.
    """
    if not video_file or not os.path.isfile(video_file):
        return SubtitleSelectionExtractionResult(
            error=str(texts.VIDEO_FILE_NOT_FOUND).format(video_file=video_file)
        )

    extractable = [stream for stream in streams if stream.is_extractable]
    if not extractable:
        return SubtitleSelectionExtractionResult(
            error=str(texts.NO_EXTRACTABLE_EMBEDDED_SUBTITLES)
        )

    reserved: set[str] = set()
    stream_targets: list[tuple[str, str, str]] = []
    for stream in extractable:
        target_path = build_extracted_subtitle_path(
            video_file, stream, output_dir=output_dir, reserved=reserved
        )
        stream_targets.append((stream.stream_index, stream.codec_name, target_path))

    writable, write_err = check_file_writable(stream_targets[0][2])
    if not writable:
        return SubtitleSelectionExtractionResult(
            error=str(texts.SUBTITLE_EXTRACTION_FAILED).format(error=write_err)
        )

    extracted_files, error, cancelled = _run_ffmpeg_extract_streams(
        video_file,
        stream_targets,
        duration_sec=duration_sec,
        on_progress=on_progress,
        is_cancelled=is_cancelled,
        process_holder=process_holder,
    )
    return SubtitleSelectionExtractionResult(
        extracted_files=extracted_files,
        error=error,
        cancelled=cancelled,
    )


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
        """Record log output and forward live updates when a callback is attached."""
        text = str(msg)
        if not overwrite:
            log_messages.append(text)
        if on_log is not None:
            on_log(text, color, overwrite)

    probe = probe_embedded_subtitles(
        video_file,
        is_cancelled=is_cancelled,
        process_holder=process_holder,
    )
    if probe.cancelled:
        return None, None, log_messages, subtitle_streams
    if probe.error:
        emit(probe.error, "grey")
        return None, None, log_messages, subtitle_streams

    subtitle_streams = [
        (stream.stream_index, stream.codec_name, stream.language)
        for stream in probe.streams
    ]
    if probe_meta is not None and probe.duration_sec is not None:
        probe_meta["duration_sec"] = probe.duration_sec

    compatible_subtitles = probe.extractable_streams
    if not compatible_subtitles:
        return None, None, log_messages, subtitle_streams

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

    stream_targets: list[tuple[str, str, str]] = []
    for i, stream in enumerate(compatible_subtitles):
        ext = stream.extension
        if not ext:
            continue
        lang_suffix = f"_{stream.language}" if stream.language else ""
        output_file = os.path.join(
            output_folder, f"subtitle_{i + 1}{lang_suffix}.{ext}"
        )
        stream_targets.append((stream.stream_index, stream.codec_name, output_file))

    if not stream_targets:
        return None, None, log_messages, subtitle_streams

    extracted_files, error, cancelled = _run_ffmpeg_extract_streams(
        video_file,
        stream_targets,
        duration_sec=probe.duration_sec,
        on_log=emit,
        on_progress=on_progress,
        on_stage=on_stage,
        is_cancelled=is_cancelled,
        process_holder=process_holder,
    )
    if cancelled:
        return None, None, log_messages, subtitle_streams
    if error:
        emit(error, "grey")
        return None, None, log_messages, subtitle_streams

    for output_file in extracted_files:
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
