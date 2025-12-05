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
from pathlib import Path
import texts
from PyQt6.QtCore import pyqtSignal, QObject, QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QCheckBox,
)
from constants import SYNC_TOOLS, COLORS, DEFAULT_OPTIONS, SUBTITLE_EXTENSIONS
from utils import (
    create_process,
    create_backup,
    default_encoding,
    detect_encoding,
    find_closest_encoding,
    match_subtitle_encoding,
    update_config,
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


def _has_brackets(path):
    return bool(path and ("[" in path and "]" in path))


def _rename_path_components(path):
    path = os.path.normpath(path)
    p = Path(path)
    anchor = Path(p.anchor) if p.anchor else Path()
    current = anchor
    renamed = False
    parts = p.parts[len(anchor.parts) :]
    for part in parts:
        safe_part = part.replace("[", "(").replace("]", ")")
        next_path = current / part
        safe_path = current / safe_part
        if part != safe_part:
            renamed = True
            if not next_path.exists() and safe_path.exists():
                next_path = safe_path
            elif next_path.exists() and not safe_path.exists():
                os.rename(next_path, safe_path)
                logger.info(
                    f"Renamed '{next_path}' to '{safe_path}' for ALASS compatibility"
                )
                next_path = safe_path
            elif not next_path.exists() and not safe_path.exists():
                next_path = safe_path
            else:
                next_path = safe_path
        current = next_path
    return os.path.normpath(str(current)), renamed


def _update_ui_paths_after_rename(app, old_ref, new_ref, old_sub, new_sub):
    """Update UI elements (input boxes and batch tree) after paths are renamed.

    This also updates any other files that were affected by folder renames.
    For example, if a folder [Anime] was renamed to (Anime), all files
    within that folder will have their paths updated in the UI.
    """
    from PyQt6.QtCore import Qt

    def get_renamed_path(old_path):
        """Calculate what the new path would be after bracket-to-parenthesis rename."""
        if not old_path:
            return old_path
        return old_path.replace("[", "(").replace("]", ")")

    def needs_update(old_path):
        """Check if a path contains brackets and would be affected by rename."""
        return bool(old_path and ("[" in old_path or "]" in old_path))

    # Update normal mode input boxes
    if not app.batch_mode_enabled:
        if hasattr(app, "video_ref_input") and app.video_ref_input.file_path:
            current_path = app.video_ref_input.file_path
            if needs_update(current_path):
                new_path = get_renamed_path(current_path)
                if os.path.exists(new_path):
                    app.video_ref_input.set_file(new_path)
                    logger.info(
                        f"Updated video_ref_input path from '{current_path}' to '{new_path}'"
                    )
        if hasattr(app, "subtitle_input") and app.subtitle_input.file_path:
            current_path = app.subtitle_input.file_path
            if needs_update(current_path):
                new_path = get_renamed_path(current_path)
                if os.path.exists(new_path):
                    app.subtitle_input.set_file(new_path)
                    logger.info(
                        f"Updated subtitle_input path from '{current_path}' to '{new_path}'"
                    )

    # Update batch tree view items - update ALL items that might be affected
    if hasattr(app, "batch_tree_view") and app.batch_tree_view:
        from PyQt6.QtWidgets import QFileIconProvider
        from PyQt6.QtCore import QFileInfo

        tree = app.batch_tree_view
        icon_provider = QFileIconProvider()
        paths_updated = False
        # Iterate through all top-level items (reference files)
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            if not item:
                continue
            item_path = item.data(0, Qt.ItemDataRole.UserRole)
            # Update reference path if it contains brackets
            if item_path and needs_update(item_path):
                new_path = get_renamed_path(item_path)
                if os.path.exists(new_path):
                    item.setData(0, Qt.ItemDataRole.UserRole, new_path)
                    item.setText(0, os.path.basename(new_path))
                    item.setIcon(0, icon_provider.icon(QFileInfo(new_path)))
                    logger.info(
                        f"Updated batch tree reference path from '{item_path}' to '{new_path}'"
                    )
                    paths_updated = True
            # Check children (subtitle files)
            for j in range(item.childCount()):
                child = item.child(j)
                if not child:
                    continue
                child_path = child.data(0, Qt.ItemDataRole.UserRole)
                if child_path and needs_update(child_path):
                    new_path = get_renamed_path(child_path)
                    if os.path.exists(new_path):
                        child.setData(0, Qt.ItemDataRole.UserRole, new_path)
                        child.setText(0, os.path.basename(new_path))
                        child.setIcon(0, icon_provider.icon(QFileInfo(new_path)))
                        logger.info(
                            f"Updated batch tree subtitle path from '{child_path}' to '{new_path}'"
                        )
                        paths_updated = True
        # Trigger UI update to rebuild pair cache if any paths were updated
        if paths_updated:
            tree._schedule_ui_update()


def _ask_rename_for_alass(app):
    dlg = QDialog(app)
    dlg.setWindowTitle(texts.ALASS_RENAME_DIALOG_TITLE)
    layout = QVBoxLayout(dlg)
    body = QLabel(texts.ALASS_RENAME_DIALOG_BODY, dlg)
    body.setWordWrap(True)
    layout.addWidget(body)
    timer_label = QLabel(dlg)
    timer_label.setStyleSheet("color: {}".format(COLORS["ORANGE"]))
    layout.addWidget(timer_label)
    remember_box = QCheckBox(texts.ALASS_RENAME_ALWAYS, dlg)
    remember_box.setChecked(
        app.config.get(
            "auto_rename_bracket_paths", DEFAULT_OPTIONS["auto_rename_bracket_paths"]
        )
    )
    layout.addWidget(remember_box)
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No,
        dlg,
    )
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    layout.addWidget(buttons)
    remaining = 30
    timer_label.setText(texts.ALASS_RENAME_TIMER.format(time=remaining))
    timer = QTimer(dlg)

    def tick():
        nonlocal remaining
        remaining -= 1
        if remaining <= 0:
            timer.stop()
            dlg.reject()
        else:
            timer_label.setText(texts.ALASS_RENAME_TIMER.format(time=remaining))

    timer.timeout.connect(tick)
    timer.start(1000)
    result = dlg.exec()
    timer.stop()
    return result == QDialog.DialogCode.Accepted, remember_box.isChecked()


def _ensure_alass_safe_paths(app, reference_path, subtitle_path):
    ref = os.path.normpath(reference_path) if reference_path else reference_path
    sub = os.path.normpath(subtitle_path) if subtitle_path else subtitle_path
    original_ref, original_sub = ref, sub
    if not (_has_brackets(ref) or _has_brackets(sub)):
        return True, ref, sub
    auto = app.config.get(
        "auto_rename_bracket_paths", DEFAULT_OPTIONS["auto_rename_bracket_paths"]
    )
    if not auto:
        accepted, remember = _ask_rename_for_alass(app)
        if remember:
            update_config(app, "auto_rename_bracket_paths", True)
            if hasattr(app, "auto_rename_bracket_paths_action"):
                app.auto_rename_bracket_paths_action.setChecked(True)
        if not accepted:
            return True, ref, sub
    try:
        new_ref, ref_renamed = _rename_path_components(ref)
        new_sub, sub_renamed = _rename_path_components(sub)
        if ref_renamed or sub_renamed:
            append_log(app, texts.ALASS_RENAME_COMPLETED, COLORS["BLUE"])
            # Update UI elements with renamed paths
            _update_ui_paths_after_rename(
                app, original_ref, new_ref, original_sub, new_sub
            )
        return True, new_ref, new_sub
    except Exception as e:
        logger.error(f"Failed to rename paths for ALASS: {e}")
        return False, ref, sub


def _mark_item_as_processed(app, reference_path):
    """Mark a reference file as processed in the Smart Deduplication database."""
    try:
        # Check if skip feature is enabled
        if not app.config.get("skip_previously_processed_videos", True):
            return

        # Only mark video files (not subtitle references)
        ref_ext = os.path.splitext(reference_path)[1].lower()
        if ref_ext in SUBTITLE_EXTENSIONS:
            return

        from processed_items_manager import get_processed_items_manager

        manager = get_processed_items_manager()
        if manager.mark_as_processed(reference_path):
            # Log the addition to the database in blue
            append_log(
                app, str(texts.SYNC_TRACKING_ADDED_TO_DATABASE), color=COLORS["BLUE"]
            )
            # Update the batch tree view cache if available
            if hasattr(app, "batch_tree_view") and app.batch_tree_view:
                norm_path = os.path.normpath(reference_path)
                app.batch_tree_view._processed_items_cache[norm_path] = True
    except Exception as e:
        logger.warning(f"Failed to mark item as processed: {e}")


def handle_completion(app, ok, out, in_path):
    if ok and (not out or not os.path.exists(out)):
        ok = False
        append_log(app, texts.SYNC_FAILED_CHECK_LOGS, COLORS["RED"])
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
            self.app.log_window.append_message(f"{texts.REFERENCE_LABEL} ", end="")
            self.app.log_window.append_message(reference, color=COLORS["GREY"])
            self.app.log_window.append_message(f"{texts.SUBTITLE_LABEL} ", end="")
            self.app.log_window.append_message(subtitle, color=COLORS["GREY"])
            self.app.log_window.append_message("")
            self.app.log_window.cancel_button.setEnabled(True)
        threading.Thread(
            target=self._run, args=(reference, subtitle, tool, output), daemon=True
        ).start()

    def _run(self, reference, subtitle, tool, output):
        try:
            if not os.path.exists(reference) and not os.path.exists(subtitle):
                self.signals.error.emit(texts.SKIPPING_BOTH_FILES_DO_NOT_EXIST)
                self.signals.finished.emit(False, None)
                return
            elif not os.path.exists(reference):
                self.signals.error.emit(texts.SKIPPING_REFERENCE_FILE_DOES_NOT_EXIST)
                self.signals.finished.emit(False, None)
                return
            elif not os.path.exists(subtitle):
                self.signals.error.emit(texts.SKIPPING_SUBTITLE_FILE_DOES_NOT_EXIST)
                self.signals.finished.emit(False, None)
                return
            if tool not in SYNC_TOOLS:
                self.signals.error.emit(texts.UNKNOWN_SYNC_TOOL.format(tool=tool))
                return
            tool_info, tool_type = SYNC_TOOLS[tool], SYNC_TOOLS[tool].get(
                "type", "executable"
            )
            # Use local variables for tool fallback logic
            current_tool = tool
            current_tool_info = tool_info
            current_tool_type = tool_type
            supports_sub_ref = current_tool_info.get(
                "supports_subtitle_as_reference", True
            )
            ref_ext = os.path.splitext(reference)[1].lower()
            is_video_ref = ref_ext not in SUBTITLE_EXTENSIONS
            if not supports_sub_ref and not is_video_ref:
                default_tool = DEFAULT_OPTIONS["sync_tool"]
                append_log(
                    self.app,
                    texts.TOOL_DOES_NOT_SUPPORT_SUBTITLE_REFERENCE.format(
                        tool=current_tool, fallback=default_tool
                    ),
                    COLORS["ORANGE"],
                )
                logger.info(
                    f"{current_tool} does not support subtitle files as reference. Falling back to {default_tool}."
                )
                current_tool = default_tool
                current_tool_info = SYNC_TOOLS[current_tool]
                current_tool_type = current_tool_info.get("type", "executable")
            rc = None
            # --- BACKUP LOGIC (moved here, before running sync for all tool types) ---
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
            # --- END BACKUP LOGIC ---

            # --- AUTOSUBSYNC TEMP-OUTPUT TO AVOID OVERWRITE ---
            effective_output = output
            use_temp_output = False
            temp_output_path = None
            try:
                if current_tool == "autosubsync" and os.path.abspath(
                    output
                ) == os.path.abspath(subtitle):
                    base, ext = os.path.splitext(output)
                    temp_output_path = f"{base}.autosubsync-tmp{ext}"
                    counter = 2
                    while os.path.exists(temp_output_path):
                        temp_output_path = f"{base}.autosubsync-tmp-{counter}{ext}"
                        counter += 1
                    effective_output = temp_output_path
                    use_temp_output = True
                    logger.info(
                        "Autosubsync overwrite avoided: using temp output '%s'",
                        effective_output,
                    )
            except Exception as e:
                logger.warning(f"Failed to prepare temp output for autosubsync: {e}")
            # --- END AUTOSUBSYNC TEMP-OUTPUT ---

            if current_tool_type == "module":
                module_name = current_tool_info.get("module")
                idx, total = getattr(self.app, "_current_batch_idx", None), getattr(
                    self.app, "_current_batch_total", None
                )
                cmd_args = self._build_cmd(
                    current_tool, None, reference, subtitle, effective_output
                )[1:]
                # Print and log what is executing
                exec_msg = f"Executing: {module_name} {' '.join(cmd_args)}"
                logger.info(exec_msg)
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
                exe_info = current_tool_info["executable"]
                current_os = platform.system()
                exe = (
                    exe_info.get(current_os) if isinstance(exe_info, dict) else exe_info
                )
                if not exe:
                    self.signals.error.emit(
                        texts.NO_EXECUTABLE_FOUND.format(
                            tool=current_tool, os=current_os
                        )
                    )
                    self.signals.finished.emit(False, None)
                    return
                cmd = self._build_cmd(
                    current_tool, exe, reference, subtitle, effective_output
                )
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
            # --- POST-PROCESS FOR AUTOSUBSYNC TEMP-OUTPUT ---
            if rc == 0 and use_temp_output and not self.should_cancel:
                try:
                    if not os.path.exists(temp_output_path):
                        self.signals.error.emit(
                            "Autosubsync did not produce an output file."
                        )
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
                    self.signals.error.emit(f"Failed to replace original subtitle: {e}")
                    logger.error("Replacement failed: %s", e)
                    rc = 1
            if (
                (rc != 0 or self.should_cancel)
                and use_temp_output
                and temp_output_path
                and os.path.exists(temp_output_path)
            ):
                try:
                    os.remove(temp_output_path)
                    logger.info("Removed temp output '%s'", temp_output_path)
                except Exception:
                    logger.warning(
                        "Failed to remove temp output '%s'", temp_output_path
                    )
            # --- END POST-PROCESS ---

            if rc != 0 and not self.should_cancel:
                self.signals.error.emit(
                    texts.TOOL_FAILED_WITH_CODE.format(tool=tool, code=rc)
                )
                self.signals.finished.emit(False, None)
            elif self.should_cancel:
                self.signals.finished.emit(False, None)
            else:
                self.signals.finished.emit(True, output)
        except Exception as e:
            if not self.should_cancel:
                error_msg = texts.ERROR_PREFIX + " " + str(e)
                if tool == "alass" and "could not convert string to float" in str(e):
                    if any(c in reference or c in subtitle for c in ["[", "]"]):
                        error_msg += "\n\n" + texts.ALASS_BRACKETS_ERROR
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
                    texts.CANCEL_BATCH_SYNC_TITLE,
                    texts.CANCEL_BATCH_SYNC_PROMPT,
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
            converted_files_to_clean = []
            if hasattr(app, "_batch_state") and app._batch_state.get(
                "should_cancel", False
            ):
                logger.info("Batch sync cancelled by user")
                if hasattr(app, "_batch_state"):
                    del app._batch_state
                return
            if current_item_idx >= len(items):
                if app.batch_mode_enabled and total_items > 1:
                    append_log(app, texts.BATCH_SYNC_COMPLETED, COLORS["BLUE"], True)
                    append_log(
                        app, f"{texts.TOTAL_PAIRS_LABEL} {total_items}", COLORS["BLUE"]
                    )
                    append_log(
                        app,
                        texts.BATCH_SYNC_SUCCESSFUL.format(count=batch_success_count),
                        COLORS["GREEN"],
                    )
                    if batch_fail_count > 0:
                        append_log(
                            app,
                            texts.BATCH_SYNC_FAILED.format(count=batch_fail_count),
                            COLORS["RED"],
                            end="\n\n",
                        )
                        for fail_idx, v, s in failed_pairs:
                            append_log(
                                app,
                                texts.BATCH_SYNC_FAILED_PAIR.format(
                                    idx=fail_idx + 1, total=total_items
                                ),
                                COLORS["RED"],
                            )
                            append_log(app, f"{texts.REFERENCE_LABEL} ", end="")
                            append_log(app, v, COLORS["ORANGE"], end="\n")
                            append_log(app, f"{texts.SUBTITLE_LABEL} ", end="")
                            append_log(app, s, COLORS["ORANGE"], end="\n\n")
                    app.log_window.finish_batch_sync()
                if hasattr(app, "_batch_state"):
                    del app._batch_state
                return
            it = items[current_item_idx]
            original_idx = current_item_idx
            original_ref_path, original_sub_path = (
                (
                    os.path.normpath(it["reference_path"])
                    if it.get("reference_path")
                    else it.get("reference_path")
                ),
                (
                    os.path.normpath(it["subtitle_path"])
                    if it.get("subtitle_path")
                    else it.get("subtitle_path")
                ),
            )
            if tool == "alass":
                ok_paths, original_ref_path, original_sub_path = (
                    _ensure_alass_safe_paths(app, original_ref_path, original_sub_path)
                )
                if not ok_paths:
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
                        app.restore_auto_sync_tab()
                    return
            if app.batch_mode_enabled and len(items) > 1:
                append_log(
                    app,
                    texts.BATCH_SYNC_PROCESSING_PAIR.format(
                        idx=current_item_idx + 1, total=len(items)
                    ),
                    COLORS["BLUE"],
                    True,
                )
            output_dir = os.path.dirname(
                determine_output_path(app, original_ref_path, original_sub_path)
            )

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
                        texts.CONVERSION_FAILED_FOR_FILE.format(
                            filename=os.path.basename(file_path)
                        ),
                        COLORS["RED"],
                    )
                    return None
                return file_path

            # Convert subtitle file first if needed
            subtitle_path = convert_if_needed(original_sub_path)
            subtitle_was_converted = (
                subtitle_path != original_sub_path and subtitle_path is not None
            )

            # Then check for embedded subtitles in video if applicable
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
                    app, texts.CHECKING_VIDEO_FOR_EMBEDDED_SUBTITLES, COLORS["GREY"]
                )
                extraction_result, extraction_done, log_lock = (
                    [None, None, []],
                    threading.Event(),
                    threading.Lock(),
                )

                def run_extraction():
                    try:
                        result = extract_subtitles(
                            original_ref_path, subtitle_path, output_dir
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
                            extraction_result[2].append(
                                texts.EXTRACTION_FAILED_PREFIX + str(e)
                            )
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
                        texts.EXTRACTION_SELECTED_WITH_TIMESTAMP.format(
                            filename=filename, score=extraction_score
                        ),
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
                        app, texts.EXTRACTION_NO_COMPATIBLE_SUBTITLES, COLORS["ORANGE"]
                    )

            reference_to_process = (
                extracted_subtitle_path
                if extracted_subtitle_path
                else original_ref_path
            )
            reference_path = convert_if_needed(reference_to_process)
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
                        app, texts.SYNC_CANCELLED_CONVERSION_FAILURE, COLORS["RED"]
                    )
                    app.restore_auto_sync_tab()
                return
            final_output_path = determine_output_path(
                app, original_ref_path, original_sub_path, subtitle_was_converted
            )
            tool_local, tool_info, tool_type = get_tool_with_fallback(
                app, reference_path
            )
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
                # Pass sync tracking callback to be called after success message but before saved to
                post_success_cb = (
                    (lambda: _mark_item_as_processed(app, original_ref_path))
                    if ok
                    else None
                )
                app.log_window.handle_batch_completion(
                    ok, out, process_next_item, post_success_cb
                )

            def single_completion_handler(ok, out):
                ok = handle_completion(app, ok, out, original_sub_path)
                if ok:
                    cleanup_files(converted_files_to_clean, extracted_folder_to_clean)
                # Pass sync tracking callback to be called after success message but before saved to
                post_success_cb = (
                    (lambda: _mark_item_as_processed(app, original_ref_path))
                    if ok
                    else None
                )
                app.log_window.handle_sync_completion(ok, out, post_success_cb)

            if app.batch_mode_enabled and len(items) > 1:
                proc.signals.finished.connect(batch_completion_handler)
            else:
                proc.signals.finished.connect(single_completion_handler)
            proc.run_sync(reference_path, subtitle_path, tool_local, final_output_path)

        process_next_item()
    except Exception as e:
        logger.exception(f"Error starting sync: {e}")
        if hasattr(app, "_batch_state"):
            del app._batch_state


def get_tool_with_fallback(app, ref_path):
    t = app.config.get("sync_tool", DEFAULT_OPTIONS["sync_tool"])
    info = SYNC_TOOLS[t]
    t_type = info.get("type", "executable")
    supports_sub_ref = info.get("supports_subtitle_as_reference", True)
    ref_ext = os.path.splitext(ref_path)[1].lower()
    is_video = ref_ext not in SUBTITLE_EXTENSIONS
    if not supports_sub_ref and not is_video:
        fallback = DEFAULT_OPTIONS["sync_tool"]
        append_log(
            app,
            texts.TOOL_DOES_NOT_SUPPORT_SUBTITLE_REFERENCE.format(
                tool=t, fallback=fallback
            ),
            COLORS["ORANGE"],
        )
        logger.info(
            f"{t} does not support subtitle files as reference. Falling back to {fallback}."
        )
        t = fallback
        info = SYNC_TOOLS[t]
        t_type = info.get("type", "executable")
    return t, info, t_type


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
