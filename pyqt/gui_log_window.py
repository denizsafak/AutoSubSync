import os
import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QHBoxLayout, QSizePolicy, QPushButton
from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtGui import QTextCursor, QColor, QFont, QTextCharFormat, QFontDatabase
from constants import DEFAULT_OPTIONS, COLORS, SYNC_TOOLS, AUTOMATIC_SAVE_MAP
from utils import get_resource_path

logger = logging.getLogger(__name__)

class LogSignalRelay(QObject):
    append_message_signal = pyqtSignal(str, bool, object)

class LogWindow(QWidget):
    cancel_clicked = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self._config_printed = False
        self.signal_relay = LogSignalRelay()
        self.signal_relay.append_message_signal.connect(self.append_message)
        self._setup_ui()
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        self.log_text = QTextEdit(readOnly=True)

        # Set custom font
        try:
            font_path = get_resource_path("autosubsync.assets.fonts", "hack.ttf")
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                family = QFontDatabase.applicationFontFamilies(font_id)[0]
                self.log_text.setFont(QFont(family))
                logger.info(f"Loaded custom font: \"{family}\" for log window.")
            else:
                font = QFont()
                font.setFamilies(["Consolas", "Monospace"])
                self.log_text.setFont(font)
                logger.warning(f"Failed to load custom font, using fallback.")
        except Exception as e:
            font = QFont()
            font.setFamilies(["Consolas", "Monospace"])
            self.log_text.setFont(font)
            logger.error(f"Exception loading custom font: {e}. Using fallback.")

        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.log_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.log_text, 1)

        # floating scroll-to-bottom button
        self.scroll_button = QPushButton("↓", self.log_text)
        self.scroll_button.setVisible(False)
        self.scroll_button.setFixedSize(35, 35)
        self.scroll_button.clicked.connect(lambda: self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum()))
        self.log_text.verticalScrollBar().valueChanged.connect(self._update_scroll_button)
        self.log_text.verticalScrollBar().rangeChanged.connect(self._update_scroll_button)

        self.default_char_format = self.log_text.currentCharFormat()
        bottom = QHBoxLayout()
        self.cancel_button = self.parent()._button("Cancel")
        self.cancel_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.cancel_button.clicked.connect(self.cancel_clicked.emit)
        bottom.addWidget(self.cancel_button)
        layout.addLayout(bottom)

    def print_config(self, app):
        if self._config_printed: return
        self.log_text.clear()
        cfg = app.config
        get = lambda k: cfg.get(k, DEFAULT_OPTIONS.get(k))
        sync_tool = get("sync_tool")
        self.append_message("Configuration:", bold=True)
        if app.batch_mode_enabled:
            pairs = getattr(app, 'batch_tree_view', None)
            n = len(pairs.get_all_valid_pairs()) if pairs else 0
            self.append_message("Mode: ", end=""); self.append_message("Batch", bold=True, color=COLORS["GREEN"])
            self.append_message("Total pairs: ", end=""); self.append_message(str(n), bold=True, color=COLORS["GREEN"])
        else:
            self.append_message("Mode: ", end=""); self.append_message("Normal", bold=True, color=COLORS["GREEN"])
        self.append_message("Sync tool: ", end=""); self.append_message(sync_tool, bold=True, color=COLORS["GREEN"])
        tool_info = SYNC_TOOLS.get(sync_tool)
        if tool_info and "options" in tool_info:
            opts = tool_info["options"]
            for i, (k, v) in enumerate(opts.items()):
                prefix = "└─ " if i == len(opts)-1 else "├─ "
                val = cfg.get(f"{sync_tool}_{k}", v.get("default"))
                self.append_message(f"{prefix}{v.get('label', k)}: ", end=""); self.append_message(str(val), bold=True, color=COLORS["GREEN"])
        else:
            self.append_message("Unknown sync tool. No options available.", color=COLORS["ORANGE"])
        self.append_message("Add 'autosync' prefix: ", end=""); self.append_message(str(get("add_autosync_prefix")), bold=True, color=COLORS["GREEN"])
        self.append_message("Backup subtitles before overwriting: ", end=""); self.append_message(str(get("backup_subtitles_before_overwriting")), bold=True, color=COLORS["GREEN"])
        self.append_message("Keep extracted subtitles: ", end=""); self.append_message(str(get("keep_extracted_subtitles")), bold=True, color=COLORS["GREEN"])
        self.append_message("Keep converted subtitles: ", end=""); self.append_message(str(get("keep_converted_subtitles")), bold=True, color=COLORS["GREEN"])
        loc = get("automatic_save_location")
        # Get display text for the save location (mapping is now key:internal -> value:display)
        save_location_message = AUTOMATIC_SAVE_MAP.get(loc, loc)
        self.append_message("Save location: ", end=""); self.append_message(save_location_message, bold=True, color=COLORS["GREEN"])
        if loc == "select_destination_folder":
            self.append_message("Folder: ", end=""); self.append_message(cfg.get('automatic_save_folder', ''), bold=True, color=COLORS["GREEN"])
        
        args = cfg.get(f"{sync_tool}_arguments")
        if args:
            self.append_message("\nAdditional arguments: ", end=""); self.append_message(args, bold=True, color=COLORS["GREEN"])
        self.append_message("\nSync started:\n", bold=True)
        self._config_printed = True
    def append_message(self, message, bold=False, color=None, end="\n"):
        txt = self.log_text
        cursor = txt.textCursor()
        was_at_bottom = txt.verticalScrollBar().value() >= txt.verticalScrollBar().maximum() - 2
        
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat(self.default_char_format)
        if bold:
            fmt.setFontWeight(QFont.Weight.Bold)
        if color:
            fmt.setForeground(QColor(color))
        
        cursor.setCharFormat(fmt)
        cursor.insertText(str(message or "None") + end)
        
        if was_at_bottom:
            txt.verticalScrollBar().setValue(txt.verticalScrollBar().maximum())

    def clear(self):
        self.log_text.clear(); self._config_printed = False

    def _position_scroll_button(self):
        margin = 10
        lw = self.log_text.width()
        lh = self.log_text.height()
        sw = self.scroll_button.width()
        sh = self.scroll_button.height()
        sb = self.log_text.verticalScrollBar()
        scrollbar_width = sb.sizeHint().width()
        self.scroll_button.move(lw - sw - margin - scrollbar_width, lh - sh - margin)

    def _update_scroll_button(self):
        sb = self.log_text.verticalScrollBar()
        at_bottom = sb.value() >= sb.maximum() - 2
        if at_bottom:
            self.scroll_button.hide()
        else:
            self._position_scroll_button()
            self.scroll_button.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_scroll_button()

class LogWindowHandler(logging.Handler):
    def __init__(self, log_window):
        super().__init__()
        self.log_window = log_window
        self.setFormatter(logging.Formatter('%(message)s'))
    def emit(self, record):
        msg = self.format(record)
        color = bold = None
        if record.levelno >= logging.ERROR:
            color = COLORS["RED"]; bold = True
        elif record.levelno >= logging.WARNING:
            color = COLORS["ORANGE"]; bold = False
        self.log_window.signal_relay.append_message_signal.emit(msg, bool(bold), color)