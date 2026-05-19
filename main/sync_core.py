"""Pure-Python subtitle sync orchestration.

No PyQt6, no GUI dependencies. Consumed by both the GUI (via the SyncProcess
adapter in sync_auto.py) and the CLI (cli.py). Progress, log lines, errors,
and cancellation flow through the SyncCallbacks dataclass.
"""

import os
import re
import sys
import time
import logging
import platform
import importlib
import multiprocessing
from dataclasses import dataclass
from typing import Callable, Optional

import platformdirs
import texts
from constants import SYNC_TOOLS, DEFAULT_OPTIONS, SUBTITLE_EXTENSIONS
from utils import (
    create_process,
    create_backup,
    default_encoding,
    detect_encoding,
    find_closest_encoding,
)
from alass_encodings import enc_list

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    ok: bool
    output_path: Optional[str]
    tool_used: str
    message: str
    returncode: Optional[int]
    elapsed_ms: int
    cancelled: bool = False


@dataclass
class SyncCallbacks:
    """Optional hooks for progress reporting, logging, error reporting, and cancellation.

    Any field left as None is treated as a no-op. is_cancelled returning True
    causes the sync to short-circuit at the next poll point.
    """

    on_log: Optional[Callable[[str, Optional[str]], None]] = None
    on_progress: Optional[Callable[[float], None]] = None
    on_subprocess_line: Optional[Callable[[str, bool], None]] = None
    on_error: Optional[Callable[[str], None]] = None
    is_cancelled: Optional[Callable[[], bool]] = None

    def _log(self, msg, color=None):
        if self.on_log:
            self.on_log(msg, color)

    def _progress(self, percent):
        if self.on_progress:
            self.on_progress(percent)

    def _subprocess_line(self, line, is_overwrite):
        if self.on_subprocess_line:
            self.on_subprocess_line(line, is_overwrite)

    def _error(self, msg):
        if self.on_error:
            self.on_error(msg)

    def _cancelled(self):
        return bool(self.is_cancelled() if self.is_cancelled else False)


def shorten_progress_bar(line: str) -> str:
    """Compress an alass-style progress bar line down to 25-char width."""
    start = line.find("[")
    end = line.find("]", start)
    if start != -1 and end != -1:
        try:
            percent = float(line[line.find(" ", end) + 1 : line.find("%", end)])
        except (ValueError, IndexError):
            return line
        width, filled = 25, int(25 * percent / 100)
        new_bar = (
            "[" + "=" * (filled - 1) + ">" + "-" * (width - filled) + "]"
            if filled < width
            else "[" + "=" * width + "]"
        )
        return line[:start] + new_bar + line[end + 1 :]
    return line


def process_output(message: str, sync_tool: str):
    """Clean a chunk of subprocess output and extract its percent-complete value."""
    if not message:
        return "", None
    percent_match = re.search(r"(\d{1,2}(?:\.\d{1,2})?)\s*%", message)
    percent = float(percent_match.group(1)) if percent_match else None
    lines = message.split("\n")
    if sync_tool == "alass":
        result = [
            (
                shorten_progress_bar(line)
                if "[" in line and "]" in line
                else line.rstrip()
            )
            for line in lines
        ]
    else:
        result = [line.rstrip() for line in lines]
    return "\n".join(result), percent


def get_tool_with_fallback(
    ref_path: str, *, config: dict, callbacks: Optional[SyncCallbacks] = None
):
    """Resolve the configured sync tool. Falls back to the default if the
    configured tool does not support subtitle-as-reference and a subtitle
    reference was provided. Returns (tool_name, tool_info, tool_type).
    """
    t = config.get("sync_tool", DEFAULT_OPTIONS["sync_tool"])
    info = SYNC_TOOLS[t]
    t_type = info.get("type", "executable")
    supports_sub_ref = info.get("supports_subtitle_as_reference", True)
    ref_ext = os.path.splitext(ref_path)[1].lower()
    is_video = ref_ext not in SUBTITLE_EXTENSIONS
    if not supports_sub_ref and not is_video:
        fallback = DEFAULT_OPTIONS["sync_tool"]
        if callbacks:
            callbacks._log(
                str(texts.TOOL_DOES_NOT_SUPPORT_SUBTITLE_REFERENCE).format(
                    tool=t, fallback=fallback
                ),
                "orange",
            )
        logger.info(
            f"{t} does not support subtitle files as reference. Falling back to {fallback}."
        )
        t = fallback
        info = SYNC_TOOLS[t]
        t_type = info.get("type", "executable")
    return t, info, t_type


def determine_output_path(
    reference: str,
    subtitle: str,
    *,
    config: dict,
    subtitle_was_converted: bool = False,
) -> str:
    """Compute the output subtitle path according to the config's save mode."""
    save_loc = config.get(
        "automatic_save_location", DEFAULT_OPTIONS["automatic_save_location"]
    )
    add_prefix = config.get("add_tool_prefix", DEFAULT_OPTIONS["add_tool_prefix"])
    sub_dir, sub_file = os.path.dirname(subtitle), os.path.basename(subtitle)
    sub_name, sub_ext = os.path.splitext(sub_file)
    ref_dir, vid_file = os.path.dirname(reference), os.path.basename(reference)
    ref_name, _ = os.path.splitext(vid_file)
    tool = config.get("sync_tool", DEFAULT_OPTIONS["sync_tool"])
    prefix = f"{tool}_" if add_prefix else ""
    suffix = config.get("custom_suffix", DEFAULT_OPTIONS.get("custom_suffix", ""))
    
    if subtitle_was_converted:
        sub_ext = ".srt"
        
    if save_loc == "save_next_to_input_subtitle":
        out_dir, out_name = sub_dir, f"{prefix}{sub_name}{suffix}{sub_ext}"
    elif save_loc == "overwrite_input_subtitle":
        out_dir, out_name = (
            sub_dir,
            (sub_file if not subtitle_was_converted else f"{sub_name}{sub_ext}"),
        )
    elif save_loc == "save_next_to_video":
        out_dir, out_name = ref_dir, f"{prefix}{sub_name}{suffix}{sub_ext}"
    elif save_loc == "save_next_to_video_with_same_filename":
        out_dir, out_name = ref_dir, f"{ref_name}{suffix}{sub_ext}"
    elif save_loc == "save_to_desktop":
        out_dir, out_name = (
            platformdirs.user_desktop_path(),
            f"{prefix}{sub_name}{suffix}{sub_ext}",
        )
    elif save_loc == "select_destination_folder":
        folder = config.get("automatic_save_folder", "")
        out_dir = folder if folder and os.path.isdir(folder) else sub_dir
        out_name = f"{prefix}{sub_name}{suffix}{sub_ext}"
    else:
        out_dir, out_name = sub_dir, f"{prefix}{sub_name}{suffix}{sub_ext}"
    output_path = os.path.join(out_dir, out_name)
    if save_loc not in (
        "save_next_to_video_with_same_filename",
        "overwrite_input_subtitle",
    ):
        base, ext = os.path.splitext(out_name)
        counter = 2
        while os.path.exists(output_path):
            out_name = f"{base}_{counter}{ext}"
            output_path = os.path.join(out_dir, out_name)
            counter += 1
    return output_path


def build_cmd(
    tool: str,
    exe: Optional[str],
    reference: str,
    subtitle: str,
    output: str,
    *,
    config: dict,
):
    """Build the invocation argv for a sync tool.

    For executable tools, exe is the path/name and it appears as cmd[0].
    For module tools, pass exe=None; the returned list contains only the args.
    """
    cmd_structure = SYNC_TOOLS[tool].get("cmd_structure")
    head = [exe] if exe else []
    cmd = head + [
        part.format(reference=reference, subtitle=subtitle, output=output)
        for part in cmd_structure
    ]
    if tool == "alass":
        try:
            subtitle_encoding = detect_encoding(subtitle)
            new_subtitle_encoding = (
                subtitle_encoding
                if subtitle_encoding in enc_list
                else find_closest_encoding(subtitle_encoding)
            )
            cmd.extend(["--encoding-inc", new_subtitle_encoding])
        except Exception as e:
            logger.warning(f"Failed to detect subtitle encoding: {e}")
        ref_ext = os.path.splitext(reference)[1].lower()
        if ref_ext in SUBTITLE_EXTENSIONS:
            try:
                ref_encoding = detect_encoding(reference)
                new_ref_encoding = (
                    ref_encoding
                    if ref_encoding in enc_list
                    else find_closest_encoding(ref_encoding)
                )
                cmd.extend(["--encoding-ref", new_ref_encoding])
            except Exception as e:
                logger.warning(f"Failed to detect reference encoding: {e}")
    return _append_opts(cmd, tool, config)


def _append_opts(cmd, tool: str, config: dict):
    info = SYNC_TOOLS.get(tool, {})
    for name, opt in info.get("options", {}).items():
        arg, default = opt.get("argument"), opt.get("default")
        val = config.get(f"{tool}_{name}", default)
        if arg and val != default:
            if name == "split_penalty" and val == -1:
                no_splits_arg = opt.get("no_split_argument")
                if no_splits_arg:
                    cmd.append(no_splits_arg)
            elif isinstance(default, bool):
                cmd.append(arg)
            else:
                cmd.extend([arg, str(val)])
    extra = config.get(f"{tool}_arguments", "").strip().split()
    return cmd + extra if extra else cmd


def module_worker(module_name, args, conn, idx, total):
    """Top-level multiprocessing target for module-based sync tools.

    Must live at module scope so spawn-based multiprocessing (Windows/macOS)
    can pickle the target. idx and total are kept for call-site API stability;
    they aren't used internally.
    """
    try:
        module = importlib.import_module(module_name)

        class PipeStream:
            def __init__(self, conn):
                self.conn = conn
                self._buffer = ""
                self._last_was_cr = False

            def write(self, s):
                self._buffer += s
                while True:
                    i = min(
                        [
                            x
                            for x in (
                                self._buffer.find("\r"),
                                self._buffer.find("\n"),
                            )
                            if x != -1
                        ],
                        default=-1,
                    )
                    if i == -1:
                        break
                    ch = self._buffer[i]
                    part, self._buffer = self._buffer[:i], self._buffer[i + 1 :]
                    self.conn.send(
                        ("progress", part, ch == "\r" or self._last_was_cr)
                    )
                    self._last_was_cr = ch == "\r"

            def flush(self):
                if self._buffer:
                    self.conn.send(("progress", self._buffer, self._last_was_cr))
                    self._buffer = ""
                    self._last_was_cr = False

        log_stream = PipeStream(conn)
        root_logger = logging.getLogger()
        old_handlers = root_logger.handlers[:]
        handler = logging.StreamHandler(log_stream)
        handler.setFormatter(logging.Formatter("%(levelname)-6s %(message)s"))
        root_logger.handlers = [handler]
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = log_stream
        try:
            rc = module.cli_entry(args) if hasattr(module, "cli_entry") else 1
        except SystemExit as e:
            rc = e.code if hasattr(e, "code") else 1
        except Exception as e:
            conn.send(("error", f"Module execution failed: {e}"))
            rc = 1
        finally:
            log_stream.flush()
            root_logger.handlers = old_handlers
            sys.stdout, sys.stderr = old_stdout, old_stderr
        conn.send(("finished", rc))
    except Exception as e:
        conn.send(("error", f"Failed to import module '{module_name}': {e}"))
        conn.send(("finished", 1))


def run_module_tool(
    module_name: str,
    args,
    callbacks: SyncCallbacks,
    *,
    sync_tool: str,
    process_holder: Optional[dict] = None,
):
    """Run a module-based sync tool (autosubsync) in a child process.

    Streams progress/error/finished messages back via Pipe and forwards them
    through callbacks. Returns the child's returncode. If process_holder is
    given, the multiprocessing.Process handle is stored at key "module_proc"
    so an external cancel can call .terminate().
    """
    parent_conn, child_conn = multiprocessing.Pipe()
    proc = multiprocessing.Process(
        target=module_worker,
        args=(module_name, args, child_conn, None, None),
    )
    if process_holder is not None:
        process_holder["module_proc"] = proc
    proc.start()
    rc = 1
    while True:
        if callbacks._cancelled():
            break
        if parent_conn.poll(0.1):
            msg = parent_conn.recv()
            if msg[0] == "progress":
                cleaned, percent = process_output(msg[1], sync_tool)
                callbacks._subprocess_line(cleaned, msg[2])
                if percent is not None:
                    callbacks._progress(percent)
            elif msg[0] == "error":
                callbacks._error(msg[1])
            elif msg[0] == "finished":
                rc = msg[1]
                break
    proc.join(timeout=1)
    return rc


def run_executable_tool(
    cmd,
    callbacks: SyncCallbacks,
    *,
    sync_tool: str,
    process_holder: Optional[dict] = None,
):
    """Run an external sync tool binary, streaming its stdout/stderr.

    Reads in 128-byte chunks and splits on \\r / \\n so progress bars that
    rewrite the same line are forwarded with is_overwrite=True.
    """
    process = create_process(cmd)
    if process_holder is not None:
        process_holder["process"] = process
    buffer = b""
    last_was_cr = False
    while True:
        if callbacks._cancelled():
            break
        chunk = process.stdout.read(128)
        if not chunk:
            break
        buffer += chunk
        while True:
            cr_pos, lf_pos = buffer.find(b"\r"), buffer.find(b"\n")
            if cr_pos == -1 and lf_pos == -1:
                break
            if cr_pos != -1 and (lf_pos == -1 or cr_pos < lf_pos):
                part, buffer = buffer[:cr_pos], buffer[cr_pos + 1 :]
                is_overwrite = True
                last_was_cr = True
            elif lf_pos != -1:
                part, buffer = buffer[:lf_pos], buffer[lf_pos + 1 :]
                is_overwrite = last_was_cr
                last_was_cr = False
            else:
                break
            cleaned, percent = process_output(
                part.decode(default_encoding, errors="replace"), sync_tool
            )
            if cleaned or not part:
                callbacks._subprocess_line(cleaned, is_overwrite)
            if percent is not None:
                callbacks._progress(percent)
    if buffer and not callbacks._cancelled():
        cleaned, percent = process_output(
            buffer.decode(default_encoding, errors="replace").rstrip("\r\n"),
            sync_tool,
        )
        if cleaned:
            callbacks._subprocess_line(cleaned, last_was_cr)
        if percent is not None:
            callbacks._progress(percent)
    return process.wait() if not callbacks._cancelled() else 1


def run_sync(
    reference: str,
    subtitle: str,
    *,
    tool: str,
    output: Optional[str] = None,
    config: dict,
    callbacks: Optional[SyncCallbacks] = None,
    process_holder: Optional[dict] = None,
) -> SyncResult:
    """Orchestrate a single subtitle sync. Pure logic, no Qt.

    Performs path validation, tool fallback, output-path resolution, backup,
    autosubsync overwrite-protection, tool execution, and post-replace of the
    temp output file. Returns a SyncResult; errors/progress are also reported
    through callbacks as they happen.
    """
    callbacks = callbacks or SyncCallbacks()
    start = time.monotonic()

    if not os.path.exists(reference) and not os.path.exists(subtitle):
        callbacks._error(str(texts.SKIPPING_BOTH_FILES_DO_NOT_EXIST))
        return SyncResult(
            False, None, tool, "both files missing", None, _elapsed(start)
        )
    if not os.path.exists(reference):
        callbacks._error(str(texts.SKIPPING_REFERENCE_FILE_DOES_NOT_EXIST))
        return SyncResult(False, None, tool, "reference missing", None, _elapsed(start))
    if not os.path.exists(subtitle):
        callbacks._error(str(texts.SKIPPING_SUBTITLE_FILE_DOES_NOT_EXIST))
        return SyncResult(False, None, tool, "subtitle missing", None, _elapsed(start))
    if tool not in SYNC_TOOLS:
        msg = str(texts.UNKNOWN_SYNC_TOOL).format(tool=tool)
        callbacks._error(msg)
        return SyncResult(False, None, tool, "unknown tool", None, _elapsed(start))

    current_tool = tool
    current_tool_info = SYNC_TOOLS[tool]
    current_tool_type = current_tool_info.get("type", "executable")
    supports_sub_ref = current_tool_info.get("supports_subtitle_as_reference", True)
    ref_ext = os.path.splitext(reference)[1].lower()
    is_video_ref = ref_ext not in SUBTITLE_EXTENSIONS
    if not supports_sub_ref and not is_video_ref:
        default_tool = DEFAULT_OPTIONS["sync_tool"]
        callbacks._log(
            str(texts.TOOL_DOES_NOT_SUPPORT_SUBTITLE_REFERENCE).format(
                tool=current_tool, fallback=default_tool
            ),
            "orange",
        )
        logger.info(
            f"{current_tool} does not support subtitle files as reference. "
            f"Falling back to {default_tool}."
        )
        current_tool = default_tool
        current_tool_info = SYNC_TOOLS[current_tool]
        current_tool_type = current_tool_info.get("type", "executable")

    if not output:
        output = determine_output_path(reference, subtitle, config=config)

    backup_enabled = config.get(
        "backup_subtitles_before_overwriting",
        DEFAULT_OPTIONS["backup_subtitles_before_overwriting"],
    )
    if backup_enabled and os.path.exists(output):
        try:
            create_backup(output)
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")

    effective_output = output
    use_temp_output = False
    temp_output_path = None
    if current_tool == "autosubsync" and os.path.abspath(output) == os.path.abspath(
        subtitle
    ):
        base, ext = os.path.splitext(output)
        temp_output_path = f"{base}.autosubsync-tmp{ext}"
        counter = 2
        while os.path.exists(temp_output_path):
            temp_output_path = f"{base}.autosubsync-tmp-{counter}{ext}"
            counter += 1
        effective_output = temp_output_path
        use_temp_output = True
        logger.info(
            "Autosubsync overwrite avoided: using temp output '%s'", effective_output
        )

    rc = None
    try:
        if current_tool_type == "module":
            module_name = current_tool_info.get("module")
            cmd_args = build_cmd(
                current_tool,
                None,
                reference,
                subtitle,
                effective_output,
                config=config,
            )
            logger.info(f"Executing: {module_name} {' '.join(cmd_args)}")
            rc = run_module_tool(
                module_name,
                cmd_args,
                callbacks,
                sync_tool=current_tool,
                process_holder=process_holder,
            )
        else:
            exe_info = current_tool_info["executable"]
            current_os = platform.system()
            exe = exe_info.get(current_os) if isinstance(exe_info, dict) else exe_info
            if not exe:
                msg = str(texts.NO_EXECUTABLE_FOUND).format(
                    tool=current_tool, os=current_os
                )
                callbacks._error(msg)
                return SyncResult(
                    False, None, current_tool, msg, None, _elapsed(start)
                )
            cmd = build_cmd(
                current_tool,
                exe,
                reference,
                subtitle,
                effective_output,
                config=config,
            )
            if callbacks._cancelled():
                return SyncResult(
                    False, None, current_tool, "cancelled", None, _elapsed(start), True
                )
            rc = run_executable_tool(
                cmd,
                callbacks,
                sync_tool=current_tool,
                process_holder=process_holder,
            )

        if rc == 0 and use_temp_output and not callbacks._cancelled():
            try:
                if not os.path.exists(temp_output_path):
                    callbacks._error("Autosubsync did not produce an output file.")
                    rc = 1
                else:
                    logger.info(
                        "Replacing original output '%s' with temp '%s'",
                        output,
                        temp_output_path,
                    )
                    os.replace(temp_output_path, output)
                    logger.info("Replacement successful")
            except Exception as e:
                callbacks._error(f"Failed to replace original subtitle: {e}")
                logger.error("Replacement failed: %s", e)
                rc = 1

        if (
            (rc != 0 or callbacks._cancelled())
            and use_temp_output
            and temp_output_path
            and os.path.exists(temp_output_path)
        ):
            try:
                os.remove(temp_output_path)
                logger.info("Removed temp output '%s'", temp_output_path)
            except Exception:
                logger.warning("Failed to remove temp output '%s'", temp_output_path)

        if callbacks._cancelled():
            return SyncResult(
                False, None, current_tool, "cancelled", rc, _elapsed(start), True
            )
        if rc != 0:
            msg = str(texts.TOOL_FAILED_WITH_CODE).format(tool=tool, code=rc)
            callbacks._error(msg)
            return SyncResult(False, None, current_tool, msg, rc, _elapsed(start))
        return SyncResult(True, output, current_tool, "ok", rc, _elapsed(start))
    except Exception as e:
        if callbacks._cancelled():
            return SyncResult(
                False, None, current_tool, "cancelled", rc, _elapsed(start), True
            )
        error_msg = str(texts.ERROR_PREFIX) + " " + str(e)
        if tool == "alass" and "could not convert string to float" in str(e):
            if any(c in reference or c in subtitle for c in ["[", "]"]):
                error_msg += "\n\n" + str(texts.ALASS_BRACKETS_ERROR)
        callbacks._error(error_msg)
        return SyncResult(False, None, current_tool, error_msg, rc, _elapsed(start))


def _elapsed(start: float) -> int:
    return int((time.monotonic() - start) * 1000)
