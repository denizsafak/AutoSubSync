import os
import re
import logging
import threading
import platformdirs
from PyQt6.QtCore import pyqtSignal, QObject
from constants import SYNC_TOOLS, COLORS, DEFAULT_OPTIONS
from utils import create_process, default_encoding

logger = logging.getLogger(__name__)

class SyncSignals(QObject):
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str, bool)  # message, is_overwrite
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
    def cancel(self):
        self.should_cancel = True
        if self.process:
            try:
                self.process.terminate()
            except Exception as e:
                logger.error(f"Error terminating process: {e}")
    def run_sync(self, reference, subtitle, tool="ffsubsync", output=None):
        # Print command arguments and append current pair to log window
        if hasattr(self.app, 'log_window'):
            self.app.log_window.append_message(f"Reference: ", end=""); self.app.log_window.append_message(reference, color=COLORS["GREEN"], bold=True)
            self.app.log_window.append_message(f"Subtitle: ", end=""); self.app.log_window.append_message(subtitle, color=COLORS["GREEN"], bold=True)
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
            cmd = self._build_cmd(tool, exe, reference, subtitle, output)
            self.process = create_process(cmd)

            buffer = b""
            while True:
                chunk = self.process.stdout.read(4096)
                if not chunk or self.should_cancel:
                    break
                buffer += chunk
                if b'\r' in buffer:
                    pieces = buffer.split(b'\r')
                    # all but last piece are complete overwrite segments
                    for part in pieces[:-1]:
                        cleaned_msg = self._process_output(part.decode(default_encoding, errors='replace'))
                        if cleaned_msg:  # Only emit if there's content after cleaning
                            self.signals.progress.emit(cleaned_msg, True)
                    buffer = pieces[-1]  # remainder for next iterations

            # any remaining buffer is a normal line
            if buffer and not self.should_cancel:
                cleaned_msg = self._process_output(buffer.decode(default_encoding, errors='replace').rstrip('\r\n'))
                if cleaned_msg:  # Only emit if there's content after cleaning
                    self.signals.progress.emit(cleaned_msg, False)

            rc = self.process.wait()
            if rc != 0 and not self.should_cancel:
                self.signals.error.emit(f"{tool} failed with code {rc}"); self.signals.finished.emit(False, None)
            elif self.should_cancel:
                self.signals.finished.emit(False, None)
            else:
                self.signals.finished.emit(True, output)
        except Exception as e:
            self.signals.error.emit(f"Error: {str(e)}"); self.signals.finished.emit(False, None)
    def _process_output(self, message):
        """Remove [HH:MM:SS] timestamps and align following lines accordingly."""
        if not message:
            return ""

        lines = message.split('\n')
        result = []
        ts_len = 0
        
        for line in lines:
            # Find and remove timestamp first, calculate its length
            match = re.match(r'^\[\d{2}:\d{2}:\d{2}\]\s?', line)
            if match:
                ts_len = len(match.group(0))
                line = line[ts_len:]
            elif ts_len > 0 and len(line) >= ts_len and line[:ts_len].isspace():
                # Remove same number of whitespace characters as timestamp
                line = line[ts_len:]
            
            # Special handling for ALASS - do this after timestamp removal
            if self.app.config.get("sync_tool") == "alass":
                if "[" in line and "]" in line:
                    line = shorten_progress_bar(line)
            
            line = line.rstrip()
            # Always add the line, even if empty, to preserve progress updates
            result.append(line)
        
        return '\n'.join(result)
    
    def _build_cmd(self, tool, exe, reference, subtitle, output):
        cmd_structure = SYNC_TOOLS[tool].get("cmd_structure")
        cmd_parts = [part.format(reference=reference, subtitle=subtitle, output=output) for part in cmd_structure]

        cmd = [exe] + cmd_parts
        cmd = self._append_opts(cmd, tool)
        return cmd
    def _append_opts(self, cmd, tool):
        config = self.app.config
        info = SYNC_TOOLS.get(tool, {})
        for name, opt in info.get("options", {}).items():
            arg = opt.get("argument"); default = opt.get("default")
            val = config.get(f"{tool}_{name}", default)
            if arg and val != default:
                if isinstance(default, bool): cmd.append(arg)
                else: cmd += [arg, str(val)]
        extra = config.get(f"{tool}_arguments", "").strip().split()
        if extra: cmd += extra
        return cmd

def start_sync_process(app):
    try:
        if hasattr(app, 'log_window'):
            app.log_window.reset_for_new_sync()
        items = ([{"reference_path": vp, "subtitle_path": sp} for vp, sp in app.batch_tree_view.get_all_valid_pairs()] if app.batch_mode_enabled else [{"reference_path": app.video_ref_input.file_path, "subtitle_path": app.subtitle_input.file_path}])
        if not items: return
        tool = app.config.get("sync_tool", DEFAULT_OPTIONS["sync_tool"])
        
        # For batch processing, we'll handle one item at a time (sequentially)
        current_item_idx = 0
        # Add counters for batch summary
        batch_success_count = 0
        batch_fail_count = 0
        total_items = len(items)
        failed_pairs = []  # Will store tuples: (original_idx, reference_path, subtitle_path)
        
        def process_next_item():
            nonlocal current_item_idx, batch_success_count, batch_fail_count, failed_pairs
            if current_item_idx >= len(items):
                # All done: show batch report if batch mode
                if app.batch_mode_enabled and total_items > 1:
                    app.log_window.append_message("Batch sync completed.", bold=True, color=COLORS["BLUE"])
                    app.log_window.append_message(f"Total pairs: {total_items}", color=COLORS["BLUE"])
                    app.log_window.append_message(f"Successful: {batch_success_count}", color=COLORS["GREEN"])
                    if batch_fail_count > 0:
                        app.log_window.append_message(f"Failed: {batch_fail_count}", color=COLORS["RED"], end="\n\n")
                        for fail_idx, v, s in failed_pairs:
                            # Print the pair index in default color, then the rest in red
                            app.log_window.append_message(f"Failed pair: [{fail_idx+1}/{total_items}]", color=COLORS["RED"])
                            app.log_window.append_message("Reference: ", end="")
                            app.log_window.append_message(v, color=COLORS["ORANGE"], end="\n")
                            app.log_window.append_message("Subtitle: ", end="")
                            app.log_window.append_message(s, color=COLORS["ORANGE"], end="\n\n")
                    app.log_window.finish_batch_sync()
                return  # All done
                
            it = items[current_item_idx]
            original_idx = current_item_idx  # Save the original index for reporting
            current_item_idx += 1
            
            # Print progress information for batch processing
            if app.batch_mode_enabled and len(items) > 1:
                app.log_window.append_message(f"Processing pair [{current_item_idx}/{len(items)}]", bold=True, color=COLORS["BLUE"])

            proc = SyncProcess(app)
            app._current_sync_process = proc
            proc.signals.progress.connect(lambda msg, is_overwrite: app.log_window.append_message(msg, overwrite=is_overwrite))
            proc.signals.error.connect(lambda msg: app.log_window.append_message(msg, color=COLORS["RED"], end="\n\n"))

            # When finished with this item, process the next one
            if app.batch_mode_enabled and len(items) > 1:
                def batch_completion_handler(ok, out):
                    nonlocal batch_success_count, batch_fail_count, failed_pairs
                    if ok:
                        batch_success_count += 1
                    else:
                        batch_fail_count += 1
                        failed_pairs.append((original_idx, it["reference_path"], it["subtitle_path"]))
                    # Inline _handle_batch_completion logic
                    app.log_window.handle_batch_completion(ok, out, process_next_item)
                proc.signals.finished.connect(batch_completion_handler)
            else:
                # Inline _handle_sync_completion logic
                proc.signals.finished.connect(lambda ok, out: app.log_window.handle_sync_completion(ok, out))
                
            app.log_window.cancel_clicked.disconnect()
            app.log_window.cancel_clicked.connect(proc.cancel)
            app.log_window.cancel_clicked.connect(app.restore_auto_sync_tab)
            out = determine_output_path(app, it["reference_path"], it["subtitle_path"])
            proc.run_sync(it["reference_path"], it["subtitle_path"], tool, out)
        
        # Start processing the first item
        process_next_item()
    except Exception as e:
        logger.exception(f"Error starting sync: {e}")

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
        if config.get("backup_subtitles_before_overwriting", DEFAULT_OPTIONS["backup_subtitles_before_overwriting"]):
            try:
                import shutil; shutil.copy2(subtitle, os.path.join(sub_dir, f"{sub_name}.bak{sub_ext}"))
            except Exception as e:
                logger.error(f"Failed to create backup: {e}")
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
    return os.path.join(out_dir, out_name)