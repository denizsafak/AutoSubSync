import os
import logging
import threading
from PyQt6.QtCore import pyqtSignal, QObject
from constants import SYNC_TOOLS, COLORS, DEFAULT_OPTIONS
from utils import create_process

logger = logging.getLogger(__name__)

class SyncSignals(QObject):
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str)
    error = pyqtSignal(str)

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
    def run_sync(self, video, subtitle, tool="ffsubsync", output=None):
        # Print command arguments and append current pair to log window
        if hasattr(self.app, 'log_window'):
            self.app.log_window.append_message(f"Reference: ", end=""); self.app.log_window.append_message(video, color=COLORS["GREEN"], bold=True)
            self.app.log_window.append_message(f"Subtitle: ", end=""); self.app.log_window.append_message(subtitle, color=COLORS["GREEN"], bold=True)
        threading.Thread(target=self._run, args=(video, subtitle, tool, output), daemon=True).start()
    def _run(self, video, subtitle, tool, output):
        try:
            if tool not in SYNC_TOOLS:
                self.signals.error.emit(f"Unknown sync tool: {tool}"); return
            exe = SYNC_TOOLS[tool]["executable"]
            if not exe or not os.path.exists(exe):
                self.signals.error.emit(f"Executable for {tool} not found"); return
            if not output:
                output = determine_output_path(self.app, video, subtitle)
            cmd = self._build_cmd(tool, exe, video, subtitle, output)
            logger.info("[Running Command] %s", ' '.join(map(str, cmd)))
            self.process = create_process(cmd)
            for line in self.process.stdout:
                if self.should_cancel: break
                line = line.strip()
                if line: self.signals.progress.emit(line)
            rc = self.process.wait()
            if rc != 0 and not self.should_cancel:
                self.signals.error.emit(f"{tool} failed with code {rc}"); self.signals.finished.emit(False, None)
            elif self.should_cancel:
                self.signals.finished.emit(False, None)
            else:
                self.signals.finished.emit(True, output)
        except Exception as e:
            self.signals.error.emit(f"Error: {str(e)}"); self.signals.finished.emit(False, None)
    def _build_cmd(self, tool, exe, video, subtitle, output):
        cmd_structure = SYNC_TOOLS[tool].get("cmd_structure")
        cmd_parts = [part.format(video=video, subtitle=subtitle, output=output) for part in cmd_structure]

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
        items = ([{"video_path": it["video_path"], "subtitle_path": it["subtitle_path"]} for it in app.batch_tree_view.get_all_items()] if app.batch_mode_enabled else [{"video_path": app.video_ref_input.file_path, "subtitle_path": app.subtitle_input.file_path}])
        if not items: return
        tool = app.config.get("sync_tool", DEFAULT_OPTIONS["sync_tool"])
        for idx, it in enumerate(items, 1):
            proc = SyncProcess(app)
            app._current_sync_process = proc
            proc.signals.progress.connect(lambda msg: logger.info(msg))
            proc.signals.error.connect(lambda msg: logger.error(msg))
            proc.signals.finished.connect(lambda ok, out: _handle_sync_completion(app, ok, out))
            app.log_window.cancel_clicked.disconnect()
            app.log_window.cancel_clicked.connect(proc.cancel)
            app.log_window.cancel_clicked.connect(app.restore_auto_sync_tab)
            out = determine_output_path(app, it["video_path"], it["subtitle_path"])
            proc.run_sync(it["video_path"], it["subtitle_path"], tool, out)
            if not app.batch_mode_enabled: break
    except Exception as e:
        logger.exception(f"Error starting sync: {e}")

def determine_output_path(app, video, subtitle):
    config = app.config
    save_loc = config.get("automatic_save_location", DEFAULT_OPTIONS["automatic_save_location"])
    add_prefix = config.get("add_autosync_prefix", DEFAULT_OPTIONS["add_autosync_prefix"])
    sub_dir, sub_file = os.path.dirname(subtitle), os.path.basename(subtitle)
    sub_name, sub_ext = os.path.splitext(sub_file)
    vid_dir, vid_file = os.path.dirname(video), os.path.basename(video)
    vid_name, _ = os.path.splitext(vid_file)
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
    elif save_loc == "save_next_to_video":
        out_dir, out_name = vid_dir, f"{prefix}{sub_name}{sub_ext}"
    elif save_loc == "save_next_to_video_with_same_filename":
        out_dir, out_name = vid_dir, f"{prefix}{vid_name}{sub_ext}"
    elif save_loc == "save_to_desktop":
        out_dir, out_name = os.path.join(os.path.expanduser("~"), "Desktop"), f"{prefix}{sub_name}{sub_ext}"
    elif save_loc == "select_destination_folder":
        folder = config.get("automatic_save_folder", "")
        out_dir = folder if folder and os.path.isdir(folder) else sub_dir
        out_name = f"{prefix}{sub_name}{sub_ext}"
    else:
        out_dir, out_name = sub_dir, f"{prefix}{sub_name}{sub_ext}"
    return os.path.join(out_dir, out_name)

def _handle_sync_completion(app, success, output):
    if success:
        app.log_window.append_message(f"Synchronization completed successfully.\nSubtitle saved to: {output}", color=COLORS["GREEN"], bold=True)
    else:
        logger.error("Synchronization failed")
    app.log_window.cancel_button.setText("Go back")
    app.log_window.cancel_clicked.disconnect()
    app.log_window.cancel_clicked.connect(app.restore_auto_sync_tab)