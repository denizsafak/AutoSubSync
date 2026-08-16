import os
import re
import logging
import threading
import time
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
    match_subtitle_encoding,
    update_config,
)
import sync_core
from sync_core import (
    module_worker,
    shorten_progress_bar,
)
from subtitle_converter import convert_to_srt
from subtitle_extractor import (
    cleanup_extracted_subtitles,
    prepare_sync_reference,
)

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

    dont_ask_again_box = QCheckBox(texts.ALASS_RENAME_DONT_ASK_AGAIN, dlg)
    dont_ask_again_box.setChecked(
        app.config.get("disable_alass_rename_prompt", False)
    )
    layout.addWidget(dont_ask_again_box)

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
    return (
        result == QDialog.DialogCode.Accepted,
        remember_box.isChecked(),
        dont_ask_again_box.isChecked(),
    )


def _ensure_alass_safe_paths(app, reference_path, subtitle_path):
    ref = os.path.normpath(reference_path) if reference_path else reference_path
    sub = os.path.normpath(subtitle_path) if subtitle_path else subtitle_path
    original_ref, original_sub = ref, sub
    if not (_has_brackets(ref) or _has_brackets(sub)):
        return True, ref, sub
    auto = app.config.get(
        "auto_rename_bracket_paths", DEFAULT_OPTIONS["auto_rename_bracket_paths"]
    )
    disable_prompt = app.config.get(
        "disable_alass_rename_prompt",
        DEFAULT_OPTIONS["disable_alass_rename_prompt"],
    )
    if disable_prompt:
        logger.info("ALASS rename prompt disabled, skipping rename prompt")
        return True, ref, sub
    if not auto:
        accepted, remember, dont_ask_again = _ask_rename_for_alass(app)
        if remember or (dont_ask_again and accepted):
            update_config(app, "auto_rename_bracket_paths", True)
            if hasattr(app, "auto_rename_bracket_paths_action"):
                app.auto_rename_bracket_paths_action.setChecked(True)
        if dont_ask_again and not accepted:
            update_config(app, "disable_alass_rename_prompt", True)
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


class SyncProcess:
    """Qt adapter around sync_core.run_sync().

    Preserves the original signal-based public API used by the GUI: run_sync()
    spawns a worker thread, emits progress/error/finished signals, and supports
    cancel() from the UI thread.
    """

    def __init__(self, app):
        self.app = app
        self.signals = SyncSignals()
        self.should_cancel = False
        self._process_lock = threading.Lock()
        self._process_holder = {}  # populated by sync_core: {"process": Popen, "module_proc": Process}

    # Back-compat aliases for any external readers (no external consumers found,
    # but kept to avoid surprising attribute access on the legacy class shape).
    @property
    def process(self):
        return self._process_holder.get("process")

    @property
    def _module_proc(self):
        return self._process_holder.get("module_proc")

    def cancel(self):
        self.should_cancel = True

        def _cancel():
            try:
                with self._process_lock:
                    proc = self._process_holder.get("process")
                    if proc and hasattr(proc, "poll") and proc.poll() is None:
                        from utils import terminate_process_safely

                        terminate_process_safely(proc)
                        for _ in range(10):
                            if proc.poll() is not None:
                                break
                            time.sleep(0.1)
                    mproc = self._process_holder.get("module_proc")
                    if mproc and mproc.is_alive():
                        mproc.terminate()
                        mproc.join(timeout=1)
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
        cb = sync_core.SyncCallbacks(
            on_log=lambda msg, color: append_log(
                self.app, msg, COLORS.get(color.upper()) if color else None
            ),
            on_progress=lambda percent: self.signals.progress_percent.emit(percent),
            on_subprocess_line=lambda line, is_overwrite: self.signals.progress.emit(
                line, is_overwrite
            ),
            on_error=lambda msg: self.signals.error.emit(msg),
            is_cancelled=lambda: self.should_cancel,
        )
        result = sync_core.run_sync(
            reference,
            subtitle,
            tool=tool,
            output=output,
            config=self.app.config,
            callbacks=cb,
            process_holder=self._process_holder,
        )
        self.signals.finished.emit(result.ok, result.output_path)


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

            # Prepare the reference through the shared GUI/CLI extraction workflow.
            extraction_result, extraction_done = [None], threading.Event()

            if subtitle_path:
                def run_extraction():
                    try:
                        extraction_result[0] = prepare_sync_reference(
                            original_ref_path,
                            subtitle_path,
                            output_dir,
                            tool=tool,
                            config=app.config,
                        )
                    except Exception as e:
                        logger.exception(f"Extraction failed: {e}")
                    finally:
                        extraction_done.set()

                threading.Thread(target=run_extraction, daemon=True).start()
                while not extraction_done.is_set():
                    QApplication.processEvents()
                    time.sleep(0.05)
                for message in extraction_result[0].messages:
                    append_log(app, f"{message}", COLORS["GREY"])

            extraction = extraction_result[0]
            reference_to_process = (
                extraction.effective_reference if extraction else original_ref_path
            )
            reference_path = convert_if_needed(reference_to_process)
            current_item_idx += 1
            if not reference_path or not subtitle_path:
                cleanup_extracted_subtitles(extraction)
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
                    cleanup_files(converted_files_to_clean)
                    cleanup_extracted_subtitles(extraction)
                    return
                ok = handle_completion(app, ok, out, original_sub_path)
                if ok:
                    batch_success_count += 1
                else:
                    batch_fail_count += 1
                    failed_pairs.append(
                        (original_idx, original_ref_path, original_sub_path)
                    )
                cleanup_files(converted_files_to_clean)
                cleanup_extracted_subtitles(extraction)
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
                cleanup_files(converted_files_to_clean)
                cleanup_extracted_subtitles(extraction)
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
    """GUI-facing wrapper that routes the orange fallback log through append_log."""
    cb = sync_core.SyncCallbacks(
        on_log=lambda msg, color: append_log(
            app, msg, COLORS.get(color.upper()) if color else None
        ),
    )
    return sync_core.get_tool_with_fallback(ref_path, config=app.config, callbacks=cb)


def determine_output_path(app, reference, subtitle, subtitle_was_converted=False):
    return sync_core.determine_output_path(
        reference,
        subtitle,
        config=app.config,
        subtitle_was_converted=subtitle_was_converted,
    )
