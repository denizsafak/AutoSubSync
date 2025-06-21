import os
import re
import logging
import threading
import time
import platform
import platformdirs
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
import threading

logger = logging.getLogger(__name__)


class SyncSignals(QObject):
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str, bool)  # message, is_overwrite
    progress_percent = pyqtSignal(float)
    error = pyqtSignal(str)


def shorten_progress_bar(line):
    """Shorten the progress bar to 30 characters"""
    start = line.find("[")
    end = line.find("]", start)
    if start != -1 and end != -1:
        progress_bar = line[start : end + 1]
        percent_start = line.find(" ", end) + 1
        percent_end = line.find("%", percent_start)
        percent = float(line[percent_start:percent_end])
        width = 25  # New shorter width
        filled = int(width * percent / 100)
        if filled < width:
            new_progress_bar = (
                "[" + "=" * (filled - 1) + ">" + "-" * (width - filled) + "]"
            )
        else:
            new_progress_bar = "[" + "=" * width + "]"
        return line[:start] + new_progress_bar + line[end + 1 :]
    return line


class SyncProcess:
    def __init__(self, app):
        self.app = app
        self.signals = SyncSignals()
        self.process = None
        self.should_cancel = False
        self._process_lock = threading.Lock()

    def cancel(self):
        """Cancel the current sync process safely using threading."""
        self.should_cancel = True

        def _cancel_process():
            try:
                with self._process_lock:
                    if self.process and self.process.poll() is None:
                        logger.info("Terminating sync process...")
                        from utils import terminate_process_safely

                        terminate_process_safely(self.process)
                        # Wait a bit for the process to terminate
                        for _ in range(10):  # Wait up to 1 second
                            if self.process.poll() is not None:
                                break
                            time.sleep(0.1)
                        logger.info("Sync process terminated")
            except Exception as e:
                logger.error(f"Error canceling process: {e}")

        # Run cancellation in a separate thread to avoid blocking UI
        threading.Thread(target=_cancel_process, daemon=True).start()

    def run_sync(self, reference, subtitle, tool="ffsubsync", output=None):
        # Print command arguments and append current pair to log window
        if hasattr(self.app, "log_window"):
            self.app.log_window.append_message(f"Reference: ", end="")
            self.app.log_window.append_message(reference, color=COLORS["GREY"])
            self.app.log_window.append_message(f"Subtitle: ", end="")
            self.app.log_window.append_message(subtitle, color=COLORS["GREY"])
            # add new line
            self.app.log_window.append_message("")
            # Enable the cancel button now that sync is starting
            self.app.log_window.cancel_button.setEnabled(True)
        threading.Thread(
            target=self._run, args=(reference, subtitle, tool, output), daemon=True
        ).start()

    def _run(self, reference, subtitle, tool, output):
        try:
            # Check if both files exist before starting sync
            reference_exists = os.path.exists(reference)
            subtitle_exists = os.path.exists(subtitle)

            if not reference_exists and not subtitle_exists:
                self.signals.error.emit("Skipping: Both files does not exist")
                self.signals.finished.emit(False, None)
                return
            elif not reference_exists:
                self.signals.error.emit("Skipping: Reference file does not exist")
                self.signals.finished.emit(False, None)
                return
            elif not subtitle_exists:
                self.signals.error.emit("Skipping: Subtitle file does not exist")
                self.signals.finished.emit(False, None)
                return

            if tool not in SYNC_TOOLS:
                self.signals.error.emit(f"Unknown sync tool: {tool}")
                return

            # Get OS-specific executable
            exe_info = SYNC_TOOLS[tool]["executable"]
            current_os = platform.system()
            if isinstance(exe_info, dict):
                exe = exe_info.get(current_os)
                if not exe:
                    self.signals.error.emit(
                        f"No executable found for {tool} on {current_os}"
                    )
                    return

            if not output:
                output = determine_output_path(self.app, reference, subtitle)
            # Backup output subtitle if needed
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
            last_was_cr = False  # Track if last processed delimiter was \r
            while True:
                if self.should_cancel:
                    break

                chunk = self.process.stdout.read(128)
                if not chunk:
                    break
                buffer += chunk

                # Process complete lines efficiently
                while b"\r" in buffer or b"\n" in buffer:
                    cr_pos = buffer.find(b"\r")
                    lf_pos = buffer.find(b"\n")

                    # Determine which delimiter comes first
                    if cr_pos != -1 and (lf_pos == -1 or cr_pos < lf_pos):
                        # Carriage return case (overwrite)
                        part, buffer = buffer[:cr_pos], buffer[cr_pos + 1 :]
                        is_overwrite = True
                        last_was_cr = True
                    elif lf_pos != -1:
                        # Newline case - check if this follows a \r
                        part, buffer = buffer[:lf_pos], buffer[lf_pos + 1 :]
                        is_overwrite = (
                            last_was_cr  # If last was \r, this content should overwrite
                        )
                        last_was_cr = False
                    else:
                        break

                    # Process the part even if it's empty (for newlines)
                    cleaned_msg, percent = self._process_output(
                        part.decode(default_encoding, errors="replace")
                    )
                    if cleaned_msg or not part:  # Emit empty lines too
                        self.signals.progress.emit(cleaned_msg, is_overwrite)
                    if percent is not None:
                        self.signals.progress_percent.emit(percent)

            # Process remaining buffer
            if buffer and not self.should_cancel:
                cleaned_msg, percent = self._process_output(
                    buffer.decode(default_encoding, errors="replace").rstrip("\r\n")
                )
                if cleaned_msg:
                    # If the last processed delimiter was \r, remaining content should overwrite
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
                self.signals.error.emit(f"Error: {str(e)}")
                self.signals.finished.emit(False, None)
            else:
                self.signals.finished.emit(False, None)

    def _process_output(self, message):
        """Process output message, extract percentage and format for display."""
        # Handle empty messages (newlines)
        if not message:
            return "", None

        # Extract percentage
        percent_match = re.search(r"(\d{1,2}(?:\.\d{1,2})?)\s*%", message)
        percent = float(percent_match.group(1)) if percent_match else None

        sync_tool = self.app.config.get("sync_tool", DEFAULT_OPTIONS["sync_tool"])
        lines = message.split("\n")

        if sync_tool == "ffsubsync":
            # Optimize ffsubsync processing
            result = []
            for line in lines:
                # Remove timestamps and format
                line = re.sub(r"\[\d{2}:\d{2}:\d{2}\]\s*", "", line).lstrip()
                if not re.search(r"\b(INFO|WARNING|CRITICAL|ERROR)\b", line):
                    # Add only 2 spaces for progress lines (containing %), 9 spaces for others
                    line = line if "%" in line else "         " + line
                result.append((" " + line).rstrip())
        elif sync_tool == "alass":
            # Optimize ALASS processing
            result = [
                (
                    shorten_progress_bar(line)
                    if "[" in line and "]" in line
                    else line.rstrip()
                )
                for line in lines
            ]
        else:
            # Default processing
            result = [line.rstrip() for line in lines]

        return "\n".join(result), percent

    def _build_cmd(self, tool, exe, reference, subtitle, output):
        cmd_structure = SYNC_TOOLS[tool].get("cmd_structure")
        cmd = [exe] + [
            part.format(reference=reference, subtitle=subtitle, output=output)
            for part in cmd_structure
        ]

        # Add encoding arguments for ALASS
        if tool == "alass":
            # Detect encoding for subtitle file
            try:
                subtitle_encoding = detect_encoding(subtitle)
                if subtitle_encoding not in enc_list:
                    subtitle_encoding = find_closest_encoding(subtitle_encoding)
                    logger.warning(
                        f"Encoding not found in ALASS encodings, using the closest: {subtitle_encoding}"
                    )
                cmd.extend(["--encoding-inc", subtitle_encoding])
                logger.info(f"Using subtitle encoding: {subtitle_encoding}")
            except Exception as e:
                logger.warning(f"Failed to detect subtitle encoding: {e}")

            # Check if reference is a subtitle file and add encoding argument
            ref_ext = os.path.splitext(reference)[1].lower()
            if ref_ext in SUBTITLE_EXTENSIONS:
                try:
                    ref_encoding = detect_encoding(reference)
                    if ref_encoding not in enc_list:
                        ref_encoding = find_closest_encoding(ref_encoding)
                        logger.warning(
                            f"Encoding not found in ALASS encodings, using the closest: {ref_encoding}"
                        )
                    cmd.extend(["--encoding-ref", ref_encoding])
                    logger.info(f"Using reference encoding: {ref_encoding}")
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
                # Special handling for ALASS split penalty
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


def start_sync_process(app):
    try:
        if hasattr(app, "log_window"):
            app.log_window.reset_for_new_sync()

        # Get items to process
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

        # Batch processing state
        current_item_idx = 0
        batch_success_count = 0
        batch_fail_count = 0
        total_items = len(items)
        failed_pairs = []

        # Store the batch state to allow cancellation
        app._batch_state = {"should_cancel": False, "current_process": None}

        # Setup cancellation immediately for batch mode
        if app.batch_mode_enabled and len(items) > 1:
            # For batch mode, cancel the entire batch
            def cancel_batch():
                # Show confirmation dialog if there are more than 5 pairs
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
                # Show cancellation message and save logs
                if hasattr(app, "log_window"):
                    # Give a small delay to ensure the message is displayed before saving
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
            # For single item mode, setup basic cancellation
            def cancel_single():
                if hasattr(app, "_current_sync_process"):
                    app._current_sync_process.cancel()
                app.restore_auto_sync_tab()

            app.log_window.cancel_clicked.disconnect()
            app.log_window.cancel_clicked.connect(cancel_single)

        def process_next_item():
            nonlocal current_item_idx, batch_success_count, batch_fail_count, failed_pairs

            # Check if batch should be cancelled
            if hasattr(app, "_batch_state") and app._batch_state.get(
                "should_cancel", False
            ):
                logger.info("Batch sync cancelled by user")
                # Clean up batch state when cancelled
                if hasattr(app, "_batch_state"):
                    del app._batch_state
                return

            if current_item_idx >= len(items):
                # Batch complete - show summary
                if app.batch_mode_enabled and total_items > 1:
                    app.log_window.append_message(
                        "Batch sync completed.", bold=True, color=COLORS["BLUE"]
                    )
                    app.log_window.append_message(
                        f"Total pairs: {total_items}", color=COLORS["BLUE"]
                    )
                    app.log_window.append_message(
                        f"Successful: {batch_success_count}", color=COLORS["GREEN"]
                    )
                    if batch_fail_count > 0:
                        app.log_window.append_message(
                            f"Failed: {batch_fail_count}",
                            color=COLORS["RED"],
                            end="\n\n",
                        )
                        for fail_idx, v, s in failed_pairs:
                            app.log_window.append_message(
                                f"Failed pair: [{fail_idx+1}/{total_items}]",
                                color=COLORS["RED"],
                            )
                            app.log_window.append_message("Reference: ", end="")
                            app.log_window.append_message(
                                v, color=COLORS["ORANGE"], end="\n"
                            )
                            app.log_window.append_message("Subtitle: ", end="")
                            app.log_window.append_message(
                                s, color=COLORS["ORANGE"], end="\n\n"
                            )
                    app.log_window.finish_batch_sync()
                # Clear batch state
                if hasattr(app, "_batch_state"):
                    del app._batch_state
                return

            # Process current item
            it = items[current_item_idx]
            original_idx = current_item_idx

            original_ref_path = it["reference_path"]
            original_sub_path = it["subtitle_path"]

            # Update progress display immediately for batch mode
            if app.batch_mode_enabled and len(items) > 1:
                app.log_window.append_message(
                    f"Processing pair [{current_item_idx+1}/{len(items)}]",
                    bold=True,
                    color=COLORS["BLUE"],
                )

            # Determine output path early for potential conversions
            output_path = determine_output_path(
                app, original_ref_path, original_sub_path
            )
            output_dir = os.path.dirname(output_path)

            # Check if we should extract subtitles from video
            check_video_subs = app.config.get(
                f"{tool}_check_video_for_subtitles",
                SYNC_TOOLS[tool]
                .get("options", {})
                .get("check_video_for_subtitles", {})
                .get("default", False),
            )
            extracted_subtitle_path = None
            extracted_folder_to_clean = None

            if check_video_subs:
                # Try to extract subtitles from video file
                app.log_window.append_message(
                    "Checking video for embedded subtitles...", color=COLORS["GREY"]
                )

                # Setup for extraction in thread with real-time updates
                extraction_result = [None, None, []]  # [subtitle_path, score, logs]
                extraction_done = threading.Event()
                log_lock = threading.Lock()

                # Define a custom log handler that updates UI in real-time
                def log_handler(message):
                    with log_lock:
                        extraction_result[2].append(message)

                def run_extraction():
                    try:
                        result = extract_subtitles(
                            original_ref_path, original_sub_path, output_dir
                        )
                        subtitle_path, score, logs = result
                        extraction_result[0] = subtitle_path
                        extraction_result[1] = score

                        # Add logs to our shared list
                        with log_lock:
                            extraction_result[2].extend(logs)
                    except Exception as e:
                        logger.exception(f"Extraction failed: {e}")
                        with log_lock:
                            extraction_result[2].append(f"Extraction failed: {str(e)}")
                    finally:
                        extraction_done.set()

                # Start extraction in background thread
                threading.Thread(target=run_extraction, daemon=True).start()

                # Process UI and display logs during extraction
                last_log_count = 0
                while not extraction_done.is_set():
                    with log_lock:
                        # Display any new log messages
                        while last_log_count < len(extraction_result[2]):
                            app.log_window.append_message(
                                f"{extraction_result[2][last_log_count]}",
                                color=COLORS["GREY"],
                            )
                            last_log_count += 1

                    # Keep UI responsive
                    QApplication.processEvents()
                    time.sleep(0.05)  # Small sleep to prevent CPU overuse

                # Show any remaining logs
                with log_lock:
                    for i in range(last_log_count, len(extraction_result[2])):
                        app.log_window.append_message(
                            f"{extraction_result[2][i]}", color=COLORS["GREY"]
                        )

                # Get final results
                extracted_subtitle_path, extraction_score = (
                    extraction_result[0],
                    extraction_result[1],
                )

                if extracted_subtitle_path:
                    filename = os.path.basename(extracted_subtitle_path)
                    app.log_window.append_message(
                        f"Selected: {filename} with timestamp difference: {extraction_score}",
                        color=COLORS["BLUE"],
                    )

                    # Store extraction folder for potential cleanup
                    if not app.config.get(
                        "keep_extracted_subtitles",
                        DEFAULT_OPTIONS["keep_extracted_subtitles"],
                    ):
                        extracted_folder_to_clean = os.path.dirname(
                            extracted_subtitle_path
                        )
                else:
                    app.log_window.append_message(
                        "No compatible subtitles found to extract, using video...",
                        color=COLORS["ORANGE"],
                    )

            # Determine output path early for potential conversions
            output_path = determine_output_path(
                app, original_ref_path, original_sub_path
            )
            output_dir = os.path.dirname(output_path)

            converted_files_to_clean = []

            def convert_if_needed(file_path):
                ext = os.path.splitext(file_path)[-1].lower()
                supported = SYNC_TOOLS[tool].get("supported_formats", [])
                if ext in SUBTITLE_EXTENSIONS and ext not in supported:
                    msgs = []
                    converted, msgs = convert_to_srt(file_path, output_dir)
                    for msg in msgs:
                        app.log_window.append_message(msg, color=COLORS["GREY"])
                    if converted:
                        if not app.config.get(
                            "keep_converted_subtitles",
                            DEFAULT_OPTIONS["keep_converted_subtitles"],
                        ):
                            converted_files_to_clean.append(converted)
                        return converted
                    app.log_window.append_message(
                        f"Conversion failed for {os.path.basename(file_path)}",
                        color=COLORS["RED"],
                    )
                    return None
                return file_path

            # Use extracted subtitle as reference if available, otherwise use original reference
            reference_to_process = (
                extracted_subtitle_path
                if extracted_subtitle_path
                else original_ref_path
            )
            reference_path = convert_if_needed(reference_to_process)
            subtitle_path = convert_if_needed(original_sub_path)

            # Check if subtitle was converted to determine output extension
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
                    app.log_window.update_progress(
                        int((original_idx + 1) * 100 / total_items),
                        original_idx + 1,
                        total_items,
                    )
                    process_next_item()  # Move to next item
                else:
                    app.log_window.append_message(
                        "Sync cancelled due to conversion failure.", color=COLORS["RED"]
                    )
                    app.restore_auto_sync_tab()
                return

            def cleanup_converted_files():
                for f in converted_files_to_clean:
                    try:
                        if os.path.exists(f):
                            os.remove(f)
                            logger.info(f"Removed converted file: {f}")
                    except OSError as e:
                        logger.error(f"Failed to remove converted file {f}: {e}")

                # Clean up extracted subtitle folder if needed
                if extracted_folder_to_clean and os.path.exists(
                    extracted_folder_to_clean
                ):
                    try:
                        import shutil

                        shutil.rmtree(extracted_folder_to_clean)
                        logger.info(
                            f"Removed extracted subtitles folder: {extracted_folder_to_clean}"
                        )
                    except OSError as e:
                        logger.error(
                            f"Failed to remove extracted subtitles folder {extracted_folder_to_clean}: {e}"
                        )

            # Progress already shown at start of processing each item, no need to show again

            proc = SyncProcess(app)
            app._current_sync_process = proc

            # Store current process in batch state for cancellation
            if hasattr(app, "_batch_state"):
                app._batch_state["current_process"] = proc

            # Connect signals
            proc.signals.progress.connect(
                lambda msg, is_overwrite: app.log_window.append_message(
                    msg, overwrite=is_overwrite
                )
            )
            proc.signals.error.connect(
                lambda msg: app.log_window.append_message(
                    msg, color=COLORS["RED"], end="\n\n"
                )
            )
            proc.signals.progress_percent.connect(
                lambda percent: app.log_window.update_progress(
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
                    total_items if app.batch_mode_enabled and total_items > 1 else None,
                )
            )

            # Handle completion
            if app.batch_mode_enabled and len(items) > 1:

                def batch_completion_handler(ok, out):
                    nonlocal batch_success_count, batch_fail_count, failed_pairs

                    # Check if batch was cancelled
                    if hasattr(app, "_batch_state") and app._batch_state.get(
                        "should_cancel", False
                    ):
                        cleanup_converted_files()
                        return

                    # Check if output file exists, otherwise treat as error
                    if ok and (not out or not os.path.exists(out)):
                        ok = False
                        if hasattr(app, "log_window"):
                            app.log_window.append_message(
                                "Sync failed. Please check the logs.",
                                color=COLORS["RED"],
                            )

                    # Match encoding if sync was successful
                    if ok and out and os.path.exists(out):
                        try:
                            # Get encoding setting from config
                            encoding_setting = app.config.get(
                                "output_subtitle_encoding",
                                DEFAULT_OPTIONS["output_subtitle_encoding"],
                            )

                            if encoding_setting == "disabled":
                                # Don't change encoding, just log success
                                logger.info(
                                    "Output encoding disabled, not modifying output"
                                )
                            elif encoding_setting == "same_as_input":
                                # Match input encoding
                                match_subtitle_encoding(
                                    original_sub_path,
                                    out,
                                    (
                                        app.log_window
                                        if hasattr(app, "log_window")
                                        else None
                                    ),
                                )
                            else:
                                # Use specific encoding
                                match_subtitle_encoding(
                                    original_sub_path,
                                    out,
                                    (
                                        app.log_window
                                        if hasattr(app, "log_window")
                                        else None
                                    ),
                                    encoding_setting,
                                )
                        except Exception as e:
                            logger.warning(f"Failed to match subtitle encoding: {e}")

                    if ok:
                        batch_success_count += 1
                        cleanup_converted_files()
                    else:
                        batch_fail_count += 1
                        failed_pairs.append(
                            (original_idx, original_ref_path, original_sub_path)
                        )

                    app.log_window.update_progress(
                        int((original_idx + 1) * 100 / total_items),
                        original_idx + 1,
                        total_items,
                    )
                    app.log_window.handle_batch_completion(ok, out, process_next_item)

                proc.signals.finished.connect(batch_completion_handler)
            else:

                def single_completion_handler(ok, out):
                    if ok and (not out or not os.path.exists(out)):
                        ok = False
                        if hasattr(app, "log_window"):
                            app.log_window.append_message(
                                "Sync failed. Please check the logs.",
                                color=COLORS["RED"],
                            )

                    # Match encoding if sync was successful
                    if ok and out and os.path.exists(out):
                        try:
                            # Get encoding setting from config
                            encoding_setting = app.config.get(
                                "output_subtitle_encoding",
                                DEFAULT_OPTIONS["output_subtitle_encoding"],
                            )

                            if encoding_setting == "disabled":
                                # Don't change encoding, just log success
                                logger.info(
                                    "Output encoding disabled, not modifying output"
                                )
                            elif encoding_setting == "same_as_input":
                                # Match input encoding
                                match_subtitle_encoding(
                                    original_sub_path,
                                    out,
                                    (
                                        app.log_window
                                        if hasattr(app, "log_window")
                                        else None
                                    ),
                                )
                            else:
                                # Use specific encoding
                                match_subtitle_encoding(
                                    original_sub_path,
                                    out,
                                    (
                                        app.log_window
                                        if hasattr(app, "log_window")
                                        else None
                                    ),
                                    encoding_setting,
                                )
                        except Exception as e:
                            logger.warning(f"Failed to match subtitle encoding: {e}")

                    app.log_window.handle_sync_completion(ok, out)
                    if ok:
                        cleanup_converted_files()

                proc.signals.finished.connect(single_completion_handler)

            # Start sync
            final_output_path = determine_output_path(
                app, original_ref_path, original_sub_path, subtitle_was_converted
            )
            proc.run_sync(reference_path, subtitle_path, tool, final_output_path)

        # Start processing items
        process_next_item()
    except Exception as e:
        logger.exception(f"Error starting sync: {e}")
        # Clean up batch state on error
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

    # If subtitle was converted, output should be .srt
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
    # Add numeric suffix if file exists and not in excluded save locations
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
