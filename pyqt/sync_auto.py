import os
import re
import logging
import threading
import time
import platformdirs
from PyQt6.QtCore import pyqtSignal, QObject
from constants import SYNC_TOOLS, COLORS, DEFAULT_OPTIONS
from utils import create_process, create_backup, default_encoding

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
        width = 30  # New shorter width
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
        if hasattr(self.app, 'log_window'):
            self.app.log_window.append_message(f"Reference: ", end=""); self.app.log_window.append_message(reference, color=COLORS["GREY"], bold=True)
            self.app.log_window.append_message(f"Subtitle: ", end=""); self.app.log_window.append_message(subtitle, color=COLORS["GREY"], bold=True)
            # add new line
            self.app.log_window.append_message("")
        threading.Thread(target=self._run, args=(reference, subtitle, tool, output), daemon=True).start()
    def _run(self, reference, subtitle, tool, output):
        try:
            if tool not in SYNC_TOOLS:
                self.signals.error.emit(f"Unknown sync tool: {tool}"); return
            exe = SYNC_TOOLS[tool]["executable"]
            if not exe or not os.path.exists(exe):
                self.signals.error.emit(f"Executable for {tool} not found"); return
            if not output:
                output = determine_output_path(self.app, reference, subtitle)
            # Backup output subtitle if needed
            config = self.app.config
            backup_enabled = config.get("backup_subtitles_before_overwriting", DEFAULT_OPTIONS["backup_subtitles_before_overwriting"])
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
                while b'\r' in buffer or b'\n' in buffer:
                    cr_pos = buffer.find(b'\r')
                    lf_pos = buffer.find(b'\n')
                    
                    # Determine which delimiter comes first
                    if cr_pos != -1 and (lf_pos == -1 or cr_pos < lf_pos):
                        # Carriage return case (overwrite)
                        part, buffer = buffer[:cr_pos], buffer[cr_pos+1:]
                        is_overwrite = True
                        last_was_cr = True
                    elif lf_pos != -1:
                        # Newline case - check if this follows a \r
                        part, buffer = buffer[:lf_pos], buffer[lf_pos+1:]
                        is_overwrite = last_was_cr  # If last was \r, this content should overwrite
                        last_was_cr = False
                    else:
                        break
                    
                    # Process the part even if it's empty (for newlines)
                    cleaned_msg, percent = self._process_output(part.decode(default_encoding, errors='replace'))
                    if cleaned_msg or not part:  # Emit empty lines too
                        self.signals.progress.emit(cleaned_msg, is_overwrite)
                    if percent is not None:
                        self.signals.progress_percent.emit(percent)

            # Process remaining buffer
            if buffer and not self.should_cancel:
                cleaned_msg, percent = self._process_output(buffer.decode(default_encoding, errors='replace').rstrip('\r\n'))
                if cleaned_msg:
                    # If the last processed delimiter was \r, remaining content should overwrite
                    self.signals.progress.emit(cleaned_msg, last_was_cr)
                if percent is not None:
                    self.signals.progress_percent.emit(percent)

            rc = self.process.wait() if not self.should_cancel else 1
            if rc != 0 and not self.should_cancel:
                self.signals.error.emit(f"{tool} failed with code {rc}"); self.signals.finished.emit(False, None)
            elif self.should_cancel:
                self.signals.finished.emit(False, None)
            else:
                self.signals.finished.emit(True, output)
        except Exception as e:
            if not self.should_cancel:
                self.signals.error.emit(f"Error: {str(e)}"); self.signals.finished.emit(False, None)
            else:
                self.signals.finished.emit(False, None)
    def _process_output(self, message):
        """Process output message, extract percentage and format for display."""
        # Handle empty messages (newlines)
        if not message:
            return "", None

        # Extract percentage
        percent_match = re.search(r'(\d{1,2}(?:\.\d{1,2})?)\s*%', message)
        percent = float(percent_match.group(1)) if percent_match else None

        sync_tool = self.app.config.get("sync_tool")
        lines = message.split('\n')
        
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
            result = [shorten_progress_bar(line) if "[" in line and "]" in line else line.rstrip() for line in lines]
        else:
            # Default processing
            result = [line.rstrip() for line in lines]
        
        return '\n'.join(result), percent
    
    def _build_cmd(self, tool, exe, reference, subtitle, output):
        cmd_structure = SYNC_TOOLS[tool].get("cmd_structure")
        cmd = [exe] + [part.format(reference=reference, subtitle=subtitle, output=output) for part in cmd_structure]
        return self._append_opts(cmd, tool)
    
    def _append_opts(self, cmd, tool):
        config = self.app.config
        info = SYNC_TOOLS.get(tool, {})
        for name, opt in info.get("options", {}).items():
            arg, default = opt.get("argument"), opt.get("default")
            val = config.get(f"{tool}_{name}", default)
            if arg and val != default:
                cmd.append(arg) if isinstance(default, bool) else cmd.extend([arg, str(val)])
        extra = config.get(f"{tool}_arguments", "").strip().split()
        return cmd + extra if extra else cmd

def start_sync_process(app):
    try:
        if hasattr(app, 'log_window'):
            app.log_window.reset_for_new_sync()
        
        # Get items to process
        items = ([{"reference_path": vp, "subtitle_path": sp} for vp, sp in app.batch_tree_view.get_all_valid_pairs()] 
                if app.batch_mode_enabled else [{"reference_path": app.video_ref_input.file_path, "subtitle_path": app.subtitle_input.file_path}])
        
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
        app._batch_state = {
            'should_cancel': False,
            'current_process': None
        }
        
        def process_next_item():
            nonlocal current_item_idx, batch_success_count, batch_fail_count, failed_pairs
            
            # Check if batch should be cancelled
            if hasattr(app, '_batch_state') and app._batch_state.get('should_cancel', False):
                logger.info("Batch sync cancelled by user")
                return
            
            if current_item_idx >= len(items):
                # Batch complete - show summary
                if app.batch_mode_enabled and total_items > 1:
                    app.log_window.append_message("Batch sync completed.", bold=True, color=COLORS["BLUE"])
                    app.log_window.append_message(f"Total pairs: {total_items}", color=COLORS["BLUE"])
                    app.log_window.append_message(f"Successful: {batch_success_count}", color=COLORS["GREEN"])
                    if batch_fail_count > 0:
                        app.log_window.append_message(f"Failed: {batch_fail_count}", color=COLORS["RED"], end="\n\n")
                        for fail_idx, v, s in failed_pairs:
                            app.log_window.append_message(f"Failed pair: [{fail_idx+1}/{total_items}]", color=COLORS["RED"])
                            app.log_window.append_message("Reference: ", end="")
                            app.log_window.append_message(v, color=COLORS["ORANGE"], end="\n")
                            app.log_window.append_message("Subtitle: ", end="")
                            app.log_window.append_message(s, color=COLORS["ORANGE"], end="\n\n")
                    app.log_window.finish_batch_sync()
                # Clear batch state
                if hasattr(app, '_batch_state'):
                    del app._batch_state
                return
                
            # Process current item
            it = items[current_item_idx]
            original_idx = current_item_idx
            current_item_idx += 1
            
            if app.batch_mode_enabled and len(items) > 1:
                app.log_window.append_message(f"Processing pair [{current_item_idx}/{len(items)}]", bold=True, color=COLORS["BLUE"])

            proc = SyncProcess(app)
            app._current_sync_process = proc
            
            # Store current process in batch state for cancellation
            if hasattr(app, '_batch_state'):
                app._batch_state['current_process'] = proc
            
            # Connect signals
            proc.signals.progress.connect(lambda msg, is_overwrite: app.log_window.append_message(msg, overwrite=is_overwrite))
            proc.signals.error.connect(lambda msg: app.log_window.append_message(msg, color=COLORS["RED"], end="\n\n"))
            proc.signals.progress_percent.connect(
                lambda percent: app.log_window.update_progress(
                    int((current_item_idx - 1) * 100 / total_items + percent / total_items) if app.batch_mode_enabled and total_items > 1 else int(percent),
                    current_item_idx if app.batch_mode_enabled and total_items > 1 else None,
                    total_items if app.batch_mode_enabled and total_items > 1 else None
                )
            )

            # Handle completion
            if app.batch_mode_enabled and len(items) > 1:
                def batch_completion_handler(ok, out):
                    nonlocal batch_success_count, batch_fail_count, failed_pairs
                    
                    # Check if batch was cancelled
                    if hasattr(app, '_batch_state') and app._batch_state.get('should_cancel', False):
                        return
                    
                    if ok:
                        batch_success_count += 1
                    else:
                        batch_fail_count += 1
                        failed_pairs.append((original_idx, it["reference_path"], it["subtitle_path"]))
                    
                    app.log_window.update_progress(int((original_idx + 1) * 100 / total_items), original_idx + 1, total_items)
                    app.log_window.handle_batch_completion(ok, out, process_next_item)
                proc.signals.finished.connect(batch_completion_handler)
            else:
                proc.signals.finished.connect(lambda ok, out: app.log_window.handle_sync_completion(ok, out))
                
            # Setup cancellation
            app.log_window.cancel_clicked.disconnect()
            if app.batch_mode_enabled and len(items) > 1:
                # For batch mode, cancel the entire batch
                def cancel_batch():
                    if hasattr(app, '_batch_state'):
                        app._batch_state['should_cancel'] = True
                        current_proc = app._batch_state.get('current_process')
                        if current_proc:
                            current_proc.cancel()
                    app.restore_auto_sync_tab()
                app.log_window.cancel_clicked.connect(cancel_batch)
            else:
                # For single item, just cancel the process
                app.log_window.cancel_clicked.connect(proc.cancel)
                app.log_window.cancel_clicked.connect(app.restore_auto_sync_tab)
            
            # Start sync
            out = determine_output_path(app, it["reference_path"], it["subtitle_path"])
            proc.run_sync(it["reference_path"], it["subtitle_path"], tool, out)
        
        process_next_item()
    except Exception as e:
        logger.exception(f"Error starting sync: {e}")
        # Clean up batch state on error
        if hasattr(app, '_batch_state'):
            del app._batch_state

def determine_output_path(app, reference, subtitle):
    config = app.config
    save_loc = config.get("automatic_save_location", DEFAULT_OPTIONS["automatic_save_location"])
    add_prefix = config.get("add_autosync_prefix", DEFAULT_OPTIONS["add_autosync_prefix"])
    sub_dir, sub_file = os.path.dirname(subtitle), os.path.basename(subtitle)
    sub_name, sub_ext = os.path.splitext(sub_file)
    ref_dir, vid_file = os.path.dirname(reference), os.path.basename(reference)
    ref_name, _ = os.path.splitext(vid_file)
    prefix = "autosync_" if add_prefix else ""
    if save_loc == "save_next_to_input_subtitle":
        out_dir, out_name = sub_dir, f"{prefix}{sub_name}{sub_ext}"
    elif save_loc == "overwrite_input_subtitle":
        out_dir, out_name = sub_dir, sub_file
    elif save_loc == "save_next_to_reference":
        out_dir, out_name = ref_dir, f"{prefix}{sub_name}{sub_ext}"
    elif save_loc == "save_next_to_reference_with_same_filename":
        out_dir, out_name = ref_dir, f"{prefix}{ref_name}{sub_ext}"
    elif save_loc == "save_to_desktop":
        out_dir, out_name = platformdirs.user_desktop_path(), f"{prefix}{sub_name}{sub_ext}"
    elif save_loc == "select_destination_folder":
        folder = config.get("automatic_save_folder", "")
        out_dir = folder if folder and os.path.isdir(folder) else sub_dir
        out_name = f"{prefix}{sub_name}{sub_ext}"
    else:
        out_dir, out_name = sub_dir, f"{prefix}{sub_name}{sub_ext}"

    output_path = os.path.join(out_dir, out_name)
    # Add numeric suffix if file exists and not in excluded save locations
    if save_loc not in ("save_next_to_reference_with_same_filename", "overwrite_input_subtitle"):
        base, ext = os.path.splitext(out_name)
        counter = 2
        while os.path.exists(output_path):
            out_name = f"{base}_{counter}{ext}"
            output_path = os.path.join(out_dir, out_name)
            counter += 1
    return output_path