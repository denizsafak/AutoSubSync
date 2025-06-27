import sys
import os
import re
import logging
import threading
import time
import platform
import platformdirs
import importlib
import multiprocessing
from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtWidgets import QApplication
from constants import SYNC_TOOLS, COLORS, DEFAULT_OPTIONS, SUBTITLE_EXTENSIONS
from utils import (
    create_process,
    create_backup,
    default_encoding,
    detect_encoding,
    find_closest_encoding,
    match_subtitle_encoding,
)
from alass_encodings import enc_list
from subtitle_converter import convert_to_srt
from subtitle_extractor import extract_subtitles

logger = logging.getLogger(__name__)


# --- GLOBAL HELPERS ---
def get_encoding_setting(app):
    return app.config.get(
        "output_subtitle_encoding", DEFAULT_OPTIONS["output_subtitle_encoding"]
    )


def match_output_encoding(app, in_path, out_path):
    enc = get_encoding_setting(app)
    if enc == "disabled":
        logger.info("Output encoding disabled, not modifying output")
    elif enc == "same_as_input":
        match_subtitle_encoding(in_path, out_path, getattr(app, "log_window", None))
    else:
        match_subtitle_encoding(
            in_path, out_path, getattr(app, "log_window", None), enc
        )


def cleanup_files(files, folder=None):
    for f in files:
        try:
            if os.path.exists(f):
                os.remove(f)
        except OSError as e:
            logger.error(f"Failed to remove {f}: {e}")
    if folder and os.path.exists(folder):
        try:
            import shutil

            shutil.rmtree(folder)
        except OSError as e:
            logger.error(f"Failed to remove {folder}: {e}")


def append_log(app, msg, color=None, bold=False, end="\n", overwrite=False):
    if hasattr(app, "log_window"):
        app.log_window.append_message(
            msg, color=color, bold=bold, end=end, overwrite=overwrite
        )


def update_progress(app, percent, idx=None, total=None):
    if hasattr(app, "log_window"):
        app.log_window.update_progress(percent, idx, total)


def handle_completion(app, ok, out, in_path):
    if ok and (not out or not os.path.exists(out)):
        ok = False
        append_log(app, "Sync failed. Please check the logs.", COLORS["RED"])
    if ok and out and os.path.exists(out):
        try:
            match_output_encoding(app, in_path, out)
        except Exception as e:
            logger.warning(f"Failed to match subtitle encoding: {e}")
    return ok


# --- SIGNALS ---
class SyncSignals(QObject):
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str, bool)
    progress_percent = pyqtSignal(float)
    error = pyqtSignal(str)


def shorten_progress_bar(line):
    start = line.find("[")
    end = line.find("]", start)
    if start != -1 and end != -1:
        percent = float(line[line.find(" ", end) + 1 : line.find("%", end)])
        width, filled = 25, int(25 * percent / 100)
        new_bar = (
            "[" + "=" * (filled - 1) + ">" + "-" * (width - filled) + "]"
            if filled < width
            else "[" + "=" * width + "]"
        )
        return line[:start] + new_bar + line[end + 1 :]
    return line


def module_worker(module_name, args, conn, idx, total):
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
                            for x in (self._buffer.find("\r"), self._buffer.find("\n"))
                            if x != -1
                        ],
                        default=-1,
                    )
                    if i == -1:
                        break
                    ch = self._buffer[i]
                    part, self._buffer = self._buffer[:i], self._buffer[i + 1 :]
                    self.conn.send(("progress", part, ch == "\r" or self._last_was_cr))
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


class SyncProcess:
    def __init__(self, app):
        self.app = app
        self.signals = SyncSignals()
        self.process = None  # For subprocess.Popen or multiprocessing.Process
        self.should_cancel = False
        self._process_lock = threading.Lock()
        self._module_proc = None  # For module-based multiprocessing
        self._module_proc_pipe = None

    def cancel(self):
        self.should_cancel = True

        def _cancel():
            try:
                with self._process_lock:
                    # Terminate external process
                    if (
                        self.process
                        and hasattr(self.process, "poll")
                        and self.process.poll() is None
                    ):
                        from utils import terminate_process_safely

                        terminate_process_safely(self.process)
                        for _ in range(10):
                            if self.process.poll() is not None:
                                break
                            time.sleep(0.1)
                    # Terminate module process
                    if self._module_proc and self._module_proc.is_alive():
                        self._module_proc.terminate()
                        self._module_proc.join(timeout=1)
            except Exception as e:
                logger.error(f"Error canceling process: {e}")

        threading.Thread(target=_cancel, daemon=True).start()

    def run_sync(self, reference, subtitle, tool="ffsubsync", output=None):
        if hasattr(self.app, "log_window"):
            self.app.log_window.append_message(f"Reference: ", end="")
            self.app.log_window.append_message(reference, color=COLORS["GREY"])
            self.app.log_window.append_message(f"Subtitle: ", end="")
            self.app.log_window.append_message(subtitle, color=COLORS["GREY"])
            self.app.log_window.append_message("")
            self.app.log_window.cancel_button.setEnabled(True)
        threading.Thread(
            target=self._run, args=(reference, subtitle, tool, output), daemon=True
        ).start()

    def _run(self, reference, subtitle, tool, output):
        try:
            if not os.path.exists(reference) and not os.path.exists(subtitle):
                self.signals.error.emit("Skipping: Both files does not exist")
                self.signals.finished.emit(False, None)
                return
            elif not os.path.exists(reference):
                self.signals.error.emit("Skipping: Reference file does not exist")
                self.signals.finished.emit(False, None)
                return
            elif not os.path.exists(subtitle):
                self.signals.error.emit("Skipping: Subtitle file does not exist")
                self.signals.finished.emit(False, None)
                return
            if tool not in SYNC_TOOLS:
                self.signals.error.emit(f"Unknown sync tool: {tool}")
                return
            tool_info, tool_type = SYNC_TOOLS[tool], SYNC_TOOLS[tool].get(
                "type", "executable"
            )
            rc = None
            if tool_type == "module":
                module_name = tool_info.get("module")
                idx, total = getattr(self.app, "_current_batch_idx", None), getattr(
                    self.app, "_current_batch_total", None
                )
                cmd_args = self._build_cmd(tool, None, reference, subtitle, output)[1:]
                parent_conn, child_conn = multiprocessing.Pipe()
                # Use top-level module_worker for Windows compatibility
                proc = multiprocessing.Process(
                    target=module_worker,
                    args=(module_name, cmd_args, child_conn, idx, total),
                )
                self._module_proc = proc
                self._module_proc_pipe = parent_conn
                proc.start()
                while True:
                    if self.should_cancel:
                        break
                    if parent_conn.poll(0.1):
                        msg = parent_conn.recv()
                        if msg[0] == "progress":
                            cleaned_msg, percent = self._process_output(msg[1])
                            self.signals.progress.emit(cleaned_msg, msg[2])
                            if percent is not None:
                                self.signals.progress_percent.emit(percent)
                        elif msg[0] == "error":
                            self.signals.error.emit(msg[1])
                        elif msg[0] == "finished":
                            rc = msg[1]
                            break
                proc.join(timeout=1)
            else:
                exe_info = tool_info["executable"]
                current_os = platform.system()
                exe = (
                    exe_info.get(current_os) if isinstance(exe_info, dict) else exe_info
                )
                if not exe:
                    self.signals.error.emit(
                        f"No executable found for {tool} on {current_os}"
                    )
                    self.signals.finished.emit(False, None)
                    return
                if not output:
                    output = determine_output_path(self.app, reference, subtitle)
                config = self.app.config
                backup_enabled = config.get(
                    "backup_subtitles_before_overwriting",
                    DEFAULT_OPTIONS["backup_subtitles_before_overwriting"],
                )
                if backup_enabled and os.path.exists(output):
                    try:
                        create_backup(output)
                    except Exception as e:
                        logger.error(f"Failed to create backup: {e}")
                cmd = self._build_cmd(tool, exe, reference, subtitle, output)
                with self._process_lock:
                    if self.should_cancel:
                        return
                    self.process = create_process(cmd)
                buffer = b""
                last_was_cr = False
                while True:
                    if self.should_cancel:
                        break
                    chunk = self.process.stdout.read(128)
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
                        cleaned_msg, percent = self._process_output(
                            part.decode(default_encoding, errors="replace")
                        )
                        if cleaned_msg or not part:
                            self.signals.progress.emit(cleaned_msg, is_overwrite)
                        if percent is not None:
                            self.signals.progress_percent.emit(percent)
                if buffer and not self.should_cancel:
                    cleaned_msg, percent = self._process_output(
                        buffer.decode(default_encoding, errors="replace").rstrip("\r\n")
                    )
                    if cleaned_msg:
                        self.signals.progress.emit(cleaned_msg, last_was_cr)
                    if percent is not None:
                        self.signals.progress_percent.emit(percent)
                rc = self.process.wait() if not self.should_cancel else 1
            if rc != 0 and not self.should_cancel:
                self.signals.error.emit(f"{tool} failed with code {rc}")
                self.signals.finished.emit(False, None)
            elif self.should_cancel:
                self.signals.finished.emit(False, None)
            else:
                self.signals.finished.emit(True, output)
        except Exception as e:
            if not self.should_cancel:
                error_msg = f"Error: {str(e)}"
                if tool == "alass" and "could not convert string to float" in str(e):
                    if any(c in reference or c in subtitle for c in ["[", "]"]):
                        error_msg += "\n\nThis error is likely caused because of '[' or ']' characters in file or folder names. ALASS cannot process names containing these characters. Please rename your files or folders and try again."
                self.signals.error.emit(error_msg)
                self.signals.finished.emit(False, None)
            else:
                self.signals.finished.emit(False, None)

    def _process_output(self, message):
        if not message:
            return "", None
        percent_match = re.search(r"(\d{1,2}(?:\.\d{1,2})?)\s*%", message)
        percent = float(percent_match.group(1)) if percent_match else None
        sync_tool = self.app.config.get("sync_tool", DEFAULT_OPTIONS["sync_tool"])
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

    def _build_cmd(self, tool, exe, reference, subtitle, output):
        cmd_structure = SYNC_TOOLS[tool].get("cmd_structure")
        cmd = [exe] + [
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
        return self._append_opts(cmd, tool)

    def _append_opts(self, cmd, tool):
        config = self.app.config
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


class LogWindowStream:
    def __init__(self, emit_func, progress_percent_emit=None, idx=None, total=None):
        self.emit_func, self.progress_percent_emit, self.idx, self.total = (
            emit_func,
            progress_percent_emit,
            idx,
            total,
        )
        self._buffer, self._last_was_cr = "", False

    def write(self, s):
        self._buffer += s
        while True:
            idx = min(
                (
                    i
                    for i in (self._buffer.find("\r"), self._buffer.find("\n"))
                    if i != -1
                ),
                default=-1,
            )
            if idx == -1:
                break
            ch = self._buffer[idx]
            line, self._buffer = self._buffer[:idx], self._buffer[idx + 1 :]
            display_line = line
            if self.idx is not None and self.total is not None:
                percent_match = re.search(r"(\d{1,2}(?:\.\d{1,2})?)\s*%", line)
                if percent_match:
                    display_line = f"{line} [{self.idx}/{self.total}]"
            if self.progress_percent_emit:
                percent_match = re.search(r"(\d{1,2}(?:\.\d{1,2})?)\s*%", line)
                if percent_match:
                    try:
                        self.progress_percent_emit(float(percent_match.group(1)))
                    except Exception:
                        pass
            if ch == "\r":
                self.emit_func(display_line, True)
                self._last_was_cr = True
            else:
                self.emit_func(display_line, self._last_was_cr)
                self._last_was_cr = False

    def flush(self):
        if self._buffer:
            display_line = self._buffer
            if self.idx is not None and self.total is not None:
                percent_match = re.search(r"(\d{1,2}(?:\.\d{1,2})?)\s*%", self._buffer)
                if percent_match:
                    display_line = f"{self._buffer} [{self.idx}/{self.total}]"
            if self.progress_percent_emit:
                percent_match = re.search(r"(\d{1,2}(?:\.\d{1,2})?)\s*%", self._buffer)
                if percent_match:
                    try:
                        self.progress_percent_emit(float(percent_match.group(1)))
                    except Exception:
                        pass
            self.emit_func(display_line, self._last_was_cr)
            self._buffer = ""
            self._last_was_cr = False


def start_sync_process(app):
    try:
        if hasattr(app, "log_window"):
            app.log_window.reset_for_new_sync()
        items = (
            [
                {"reference_path": vp, "subtitle_path": sp}
                for vp, sp in app.batch_tree_view.get_all_valid_pairs()
            ]
            if app.batch_mode_enabled
            else [
                {
                    "reference_path": app.video_ref_input.file_path,
                    "subtitle_path": app.subtitle_input.file_path,
                }
            ]
        )
        if not items:
            return
        tool = app.config.get("sync_tool", DEFAULT_OPTIONS["sync_tool"])
        (
            current_item_idx,
            batch_success_count,
            batch_fail_count,
            total_items,
            failed_pairs,
        ) = (0, 0, 0, len(items), [])
        app._batch_state = {"should_cancel": False, "current_process": None}
        if app.batch_mode_enabled and len(items) > 1:

            def cancel_batch():
                from PyQt6.QtWidgets import QMessageBox

                reply = QMessageBox.question(
                    app,
                    "Cancel Batch Sync",
                    f"Are you sure you want to cancel batch sync?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.No:
                    return
                if hasattr(app, "_batch_state"):
                    app._batch_state["should_cancel"] = True
                    current_proc = app._batch_state.get("current_process")
                if current_proc:
                    current_proc.cancel()
                if hasattr(app, "log_window"):
                    from PyQt6.QtCore import QTimer

                    def save_and_restore():
                        app.log_window._save_log_output_to_file(
                            app, success=False, mode="batch"
                        )
                        app.restore_auto_sync_tab()

                    QTimer.singleShot(50, save_and_restore)
                else:
                    app.restore_auto_sync_tab()

            app.log_window.cancel_clicked.disconnect()
            app.log_window.cancel_clicked.connect(cancel_batch)
        else:

            def cancel_single():
                if hasattr(app, "_current_sync_process"):
                    app._current_sync_process.cancel()
                app.restore_auto_sync_tab()

            app.log_window.cancel_clicked.disconnect()
            app.log_window.cancel_clicked.connect(cancel_single)

        def process_next_item():
            nonlocal current_item_idx, batch_success_count, batch_fail_count, failed_pairs
            if hasattr(app, "_batch_state") and app._batch_state.get(
                "should_cancel", False
            ):
                logger.info("Batch sync cancelled by user")
                if hasattr(app, "_batch_state"):
                    del app._batch_state
                return
            if current_item_idx >= len(items):
                if app.batch_mode_enabled and total_items > 1:
                    append_log(app, "Batch sync completed.", COLORS["BLUE"], True)
                    append_log(app, f"Total pairs: {total_items}", COLORS["BLUE"])
                    append_log(
                        app, f"Successful: {batch_success_count}", COLORS["GREEN"]
                    )
                    if batch_fail_count > 0:
                        append_log(
                            app,
                            f"Failed: {batch_fail_count}",
                            COLORS["RED"],
                            end="\n\n",
                        )
                        for fail_idx, v, s in failed_pairs:
                            append_log(
                                app,
                                f"Failed pair: [{fail_idx+1}/{total_items}]",
                                COLORS["RED"],
                            )
                            append_log(app, "Reference: ", end="")
                            append_log(app, v, COLORS["ORANGE"], end="\n")
                            append_log(app, "Subtitle: ", end="")
                            append_log(app, s, COLORS["ORANGE"], end="\n\n")
                    app.log_window.finish_batch_sync()
                if hasattr(app, "_batch_state"):
                    del app._batch_state
                return
            it = items[current_item_idx]
            original_idx = current_item_idx
            original_ref_path, original_sub_path = (
                it["reference_path"],
                it["subtitle_path"],
            )
            if app.batch_mode_enabled and len(items) > 1:
                append_log(
                    app,
                    f"Processing pair [{current_item_idx+1}/{len(items)}]",
                    COLORS["BLUE"],
                    True,
                )
            output_path = determine_output_path(
                app, original_ref_path, original_sub_path
            )
            output_dir = os.path.dirname(output_path)
            ref_ext = os.path.splitext(original_ref_path)[1].lower()
            is_video_ref = ref_ext not in SUBTITLE_EXTENSIONS
            check_video_subs = is_video_ref and app.config.get(
                f"{tool}_check_video_for_subtitles",
                SYNC_TOOLS[tool]
                .get("options", {})
                .get("check_video_for_subtitles", {})
                .get("default", False),
            )
            extracted_subtitle_path, extracted_folder_to_clean = None, None
            if check_video_subs:
                append_log(
                    app, "Checking video for embedded subtitles...", COLORS["GREY"]
                )
                extraction_result, extraction_done, log_lock = (
                    [None, None, []],
                    threading.Event(),
                    threading.Lock(),
                )

                def run_extraction():
                    try:
                        result = extract_subtitles(
                            original_ref_path, original_sub_path, output_dir
                        )
                        extraction_result[0], extraction_result[1] = (
                            result[0],
                            result[1],
                        )
                        with log_lock:
                            extraction_result[2].extend(result[2])
                    except Exception as e:
                        logger.exception(f"Extraction failed: {e}")
                        with log_lock:
                            extraction_result[2].append(f"Extraction failed: {str(e)}")
                    finally:
                        extraction_done.set()

                threading.Thread(target=run_extraction, daemon=True).start()
                last_log_count = 0
                while not extraction_done.is_set():
                    with log_lock:
                        while last_log_count < len(extraction_result[2]):
                            append_log(
                                app,
                                f"{extraction_result[2][last_log_count]}",
                                COLORS["GREY"],
                            )
                            last_log_count += 1
                    QApplication.processEvents()
                    time.sleep(0.05)
                with log_lock:
                    for i in range(last_log_count, len(extraction_result[2])):
                        append_log(app, f"{extraction_result[2][i]}", COLORS["GREY"])
                extracted_subtitle_path, extraction_score = (
                    extraction_result[0],
                    extraction_result[1],
                )
                if extracted_subtitle_path:
                    filename = os.path.basename(extracted_subtitle_path)
                    append_log(
                        app,
                        f"Selected: {filename} with timestamp difference: {extraction_score}",
                        COLORS["BLUE"],
                    )
                    if not app.config.get(
                        "keep_extracted_subtitles",
                        DEFAULT_OPTIONS["keep_extracted_subtitles"],
                    ):
                        extracted_folder_to_clean = os.path.dirname(
                            extracted_subtitle_path
                        )
                else:
                    append_log(
                        app,
                        "No compatible subtitles found to extract, using video...",
                        COLORS["ORANGE"],
                    )
            output_path = determine_output_path(
                app, original_ref_path, original_sub_path
            )
            output_dir = os.path.dirname(output_path)
            converted_files_to_clean = []

            def convert_if_needed(file_path):
                ext = os.path.splitext(file_path)[-1].lower()
                supported = SYNC_TOOLS[tool].get("supported_formats", [])
                if ext in SUBTITLE_EXTENSIONS and ext not in supported:
                    converted, msgs = convert_to_srt(file_path, output_dir)
                    for msg in msgs:
                        append_log(app, msg, COLORS["GREY"])
                    if converted:
                        if not app.config.get(
                            "keep_converted_subtitles",
                            DEFAULT_OPTIONS["keep_converted_subtitles"],
                        ):
                            converted_files_to_clean.append(converted)
                        return converted
                    append_log(
                        app,
                        f"Conversion failed for {os.path.basename(file_path)}",
                        COLORS["RED"],
                    )
                    return None
                return file_path

            reference_to_process = (
                extracted_subtitle_path
                if extracted_subtitle_path
                else original_ref_path
            )
            reference_path = convert_if_needed(reference_to_process)
            subtitle_path = convert_if_needed(original_sub_path)
            subtitle_was_converted = (
                subtitle_path != original_sub_path and subtitle_path is not None
            )
            current_item_idx += 1
            if not reference_path or not subtitle_path:
                if app.batch_mode_enabled and total_items > 1:
                    batch_fail_count += 1
                    failed_pairs.append(
                        (original_idx, original_ref_path, original_sub_path)
                    )
                    update_progress(
                        app,
                        int((original_idx + 1) * 100 / total_items),
                        original_idx + 1,
                        total_items,
                    )
                    process_next_item()
                else:
                    append_log(
                        app, "Sync cancelled due to conversion failure.", COLORS["RED"]
                    )
                    app.restore_auto_sync_tab()
                return
            proc = SyncProcess(app)
            app._current_sync_process = proc
            if hasattr(app, "_batch_state"):
                app._batch_state["current_process"] = proc
            proc.signals.progress.connect(
                lambda msg, is_overwrite: append_log(app, msg, overwrite=is_overwrite)
            )
            proc.signals.error.connect(
                lambda msg: append_log(app, msg, COLORS["RED"], end="\n\n")
            )
            proc.signals.progress_percent.connect(
                lambda percent: (
                    update_progress(
                        app,
                        (
                            int(
                                (current_item_idx - 1) * 100 / total_items
                                + percent / total_items
                            )
                            if app.batch_mode_enabled and total_items > 1
                            else int(percent)
                        ),
                        (
                            current_item_idx
                            if app.batch_mode_enabled and total_items > 1
                            else None
                        ),
                        (
                            total_items
                            if app.batch_mode_enabled and total_items > 1
                            else None
                        ),
                    )
                    if percent is not None
                    else None
                )
            )

            def batch_completion_handler(ok, out):
                nonlocal batch_success_count, batch_fail_count
                if hasattr(app, "_batch_state") and app._batch_state.get(
                    "should_cancel", False
                ):
                    cleanup_files(converted_files_to_clean, extracted_folder_to_clean)
                    return
                ok = handle_completion(app, ok, out, original_sub_path)
                if ok:
                    batch_success_count += 1
                    cleanup_files(converted_files_to_clean, extracted_folder_to_clean)
                else:
                    batch_fail_count += 1
                    failed_pairs.append(
                        (original_idx, original_ref_path, original_sub_path)
                    )
                update_progress(
                    app,
                    int((original_idx + 1) * 100 / total_items),
                    original_idx + 1,
                    total_items,
                )
                app.log_window.handle_batch_completion(ok, out, process_next_item)

            def single_completion_handler(ok, out):
                ok = handle_completion(app, ok, out, original_sub_path)
                app.log_window.handle_sync_completion(ok, out)
                if ok:
                    cleanup_files(converted_files_to_clean, extracted_folder_to_clean)

            if app.batch_mode_enabled and len(items) > 1:
                proc.signals.finished.connect(batch_completion_handler)
            else:
                proc.signals.finished.connect(single_completion_handler)
            final_output_path = determine_output_path(
                app, original_ref_path, original_sub_path, subtitle_was_converted
            )
            proc.run_sync(reference_path, subtitle_path, tool, final_output_path)

        process_next_item()
    except Exception as e:
        logger.exception(f"Error starting sync: {e}")
        if hasattr(app, "_batch_state"):
            del app._batch_state


def determine_output_path(app, reference, subtitle, subtitle_was_converted=False):
    config = app.config
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
    if subtitle_was_converted:
        sub_ext = ".srt"
    if save_loc == "save_next_to_input_subtitle":
        out_dir, out_name = sub_dir, f"{prefix}{sub_name}{sub_ext}"
    elif save_loc == "overwrite_input_subtitle":
        out_dir, out_name = sub_dir, (
            sub_file if not subtitle_was_converted else f"{sub_name}{sub_ext}"
        )
    elif save_loc == "save_next_to_video":
        out_dir, out_name = ref_dir, f"{prefix}{sub_name}{sub_ext}"
    elif save_loc == "save_next_to_video_with_same_filename":
        out_dir, out_name = ref_dir, f"{ref_name}{sub_ext}"
    elif save_loc == "save_to_desktop":
        out_dir, out_name = (
            platformdirs.user_desktop_path(),
            f"{prefix}{sub_name}{sub_ext}",
        )
    elif save_loc == "select_destination_folder":
        folder = config.get("automatic_save_folder", "")
        out_dir = folder if folder and os.path.isdir(folder) else sub_dir
        out_name = f"{prefix}{sub_name}{sub_ext}"
    else:
        out_dir, out_name = sub_dir, f"{prefix}{sub_name}{sub_ext}"
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
