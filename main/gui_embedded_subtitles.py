"""UI workflow and selection dialog for extracting embedded video subtitles."""

import logging
import os
from typing import Optional

from PyQt6.QtCore import QEventLoop, QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

import texts
from constants import PROGRAM_NAME, is_video_extension
from subtitle_extractor import (
    EmbeddedSubtitleStream,
    SubtitleProbeResult,
    SubtitleSelectionExtractionResult,
    extract_selected_embedded_subtitles,
    probe_embedded_subtitles,
)
from utils import terminate_process_safely

logger = logging.getLogger(__name__)


class _ProbeWorker(QThread):
    """Background worker that probes a video file for embedded subtitle streams."""

    finished_probe = pyqtSignal(object)

    def __init__(self, video_path: str, cancelled_flag: dict, process_holder: dict, parent=None):
        """Initialize the probe worker with shared cancellation and process state."""
        super().__init__(parent)
        self.video_path = video_path
        self.cancelled_flag = cancelled_flag
        self.process_holder = process_holder

    def run(self):
        """Run ffprobe off the GUI thread and emit the SubtitleProbeResult."""
        result = probe_embedded_subtitles(
            self.video_path,
            is_cancelled=lambda: bool(self.cancelled_flag.get("cancelled")),
            process_holder=self.process_holder,
        )
        self.finished_probe.emit(result)


class _ExtractWorker(QThread):
    """Background worker that extracts selected subtitle streams via ffmpeg."""

    progress_changed = pyqtSignal(float)
    finished_extract = pyqtSignal(object)

    def __init__(
        self,
        video_path: str,
        streams: list[EmbeddedSubtitleStream],
        duration_sec: Optional[float],
        cancelled_flag: dict,
        process_holder: dict,
        parent=None,
    ):
        """Initialize the extraction worker for the chosen streams."""
        super().__init__(parent)
        self.video_path = video_path
        self.streams = streams
        self.duration_sec = duration_sec
        self.cancelled_flag = cancelled_flag
        self.process_holder = process_holder

    def run(self):
        """Execute ffmpeg stream extraction and emit completion status."""
        result = extract_selected_embedded_subtitles(
            self.video_path,
            self.streams,
            duration_sec=self.duration_sec,
            on_progress=self.progress_changed.emit,
            is_cancelled=lambda: bool(self.cancelled_flag.get("cancelled")),
            process_holder=self.process_holder,
        )
        self.finished_extract.emit(result)


class _SubtitleStreamTree(QTreeWidget):
    """Tree widget supporting full-row click toggling for checkable subtitle items."""

    def mouseReleaseEvent(self, event):
        """Toggle column 0's checkbox when clicking anywhere on a checkable row."""
        item = self.itemAt(event.position().toPoint())
        before = item.checkState(0) if item is not None else None
        super().mouseReleaseEvent(event)
        if (
            item is not None
            and event.button() == Qt.MouseButton.LeftButton
            and bool(item.flags() & Qt.ItemFlag.ItemIsUserCheckable)
            and item.checkState(0) == before
        ):
            new_state = (
                Qt.CheckState.Unchecked
                if before == Qt.CheckState.Checked
                else Qt.CheckState.Checked
            )
            item.setCheckState(0, new_state)


def _format_stream_flags(stream: EmbeddedSubtitleStream) -> str:
    """Format Default / Forced stream flags using existing translations."""
    flags = []
    if stream.is_default:
        flags.append(str(texts.DEFAULT_LABEL))
    if stream.is_forced:
        flags.append(str(texts.FORCED_LABEL))
    return ", ".join(flags) if flags else "-"


def _create_scanning_dialog(parent, on_cancel):
    """Create a cancellable modal progress dialog for slow ffprobe scans."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(str(texts.USE_EMBEDDED_SUBTITLES))
    dialog.setWindowFlags(
        dialog.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
    )
    dialog.setWindowModality(
        Qt.WindowModality.WindowModal if parent else Qt.WindowModality.ApplicationModal
    )
    dialog.setMinimumWidth(380)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(18, 18, 18, 18)
    layout.setSpacing(12)

    label = QLabel(str(texts.CHECKING_VIDEO_FOR_EMBEDDED_SUBTITLES), dialog)
    label.setWordWrap(True)
    layout.addWidget(label)

    progress_bar = QProgressBar(dialog)
    progress_bar.setRange(0, 0)
    progress_bar.setTextVisible(False)
    layout.addWidget(progress_bar)

    button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel, dialog)
    cancel_btn = button_box.button(QDialogButtonBox.StandardButton.Cancel)
    if cancel_btn is not None:
        cancel_btn.setText(str(texts.CANCEL))

    def handle_cancel():
        """Disable Cancel and notify the caller to terminate the running probe."""
        if cancel_btn is not None:
            cancel_btn.setEnabled(False)
        on_cancel()

    button_box.rejected.connect(handle_cancel)
    dialog.rejected.connect(handle_cancel)
    layout.addWidget(button_box)
    return dialog


def _probe_video_with_progress(
    parent, video_path: str
) -> Optional[SubtitleProbeResult]:
    """Scan video_path in a background thread, showing progress if not instant."""
    cancelled_flag = {"cancelled": False}
    process_holder: dict = {}
    result_holder: dict[str, SubtitleProbeResult] = {}
    loop = QEventLoop(parent)

    scan_dialog = None

    def cancel_probe():
        """Mark the probe cancelled and terminate the active ffprobe process."""
        cancelled_flag["cancelled"] = True
        proc = process_holder.get("process")
        if proc is not None:
            terminate_process_safely(proc)

    def show_delayed_dialog():
        """Show the scanning dialog only if ffprobe takes longer than the delay."""
        nonlocal scan_dialog, cursor_active
        if "result" in result_holder or cancelled_flag["cancelled"]:
            return
        if cursor_active:
            QApplication.restoreOverrideCursor()
            cursor_active = False
        scan_dialog = _create_scanning_dialog(parent, cancel_probe)
        scan_dialog.show()

    show_timer = QTimer(parent)
    show_timer.setSingleShot(True)
    show_timer.setInterval(150)
    show_timer.timeout.connect(show_delayed_dialog)

    worker = _ProbeWorker(video_path, cancelled_flag, process_holder)

    def on_probe_finished(probe_result: SubtitleProbeResult):
        """Capture the probe result, dismiss any scan dialog, and exit the loop."""
        result_holder["result"] = probe_result
        if show_timer.isActive():
            show_timer.stop()
        if scan_dialog is not None:
            scan_dialog.hide()
            scan_dialog.deleteLater()
        loop.quit()

    worker.finished_probe.connect(on_probe_finished)
    cursor_active = True
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        show_timer.start()
        worker.start()
        loop.exec()
        worker.wait(5000)
    finally:
        if show_timer.isActive():
            show_timer.stop()
        if cursor_active:
            QApplication.restoreOverrideCursor()

    return result_holder.get("result")


class EmbeddedSubtitlesDialog(QDialog):
    """Modal dialog for choosing embedded subtitle stream(s) to extract."""

    STREAM_ROLE = Qt.ItemDataRole.UserRole + 1

    def __init__(
        self,
        video_path: str,
        streams: list[EmbeddedSubtitleStream],
        *,
        allow_multiple: bool = False,
        duration_sec: Optional[float] = None,
        parent=None,
    ):
        """Build the embedded subtitle selection and extraction dialog."""
        super().__init__(parent)
        self.video_path = video_path
        self.streams = list(streams)
        self.allow_multiple = bool(allow_multiple)
        self.duration_sec = duration_sec
        self._extracted_files: list[str] = []
        self._extract_worker: Optional[_ExtractWorker] = None
        self._cancelled_flag = {"cancelled": False}
        self._process_holder: dict = {}

        title_text = (
            texts.USE_EMBEDDED_SUBTITLES
            if self.allow_multiple
            else texts.USE_EMBEDDED_SUBTITLE
        )
        self.setWindowTitle(f"{PROGRAM_NAME} - {title_text}")
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self.resize(620, 380)
        self.setMinimumSize(460, 280)

        self._init_ui()
        self._populate_streams()
        self._update_extract_button_state()

    def _init_ui(self):
        """Construct the dialog widgets, stream table, progress area, and buttons."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        video_label = QLabel(os.path.basename(self.video_path), self)
        video_label.setToolTip(self.video_path)
        video_label.setWordWrap(True)
        video_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(video_label)

        prompt_text = (
            texts.SELECT_EMBEDDED_SUBTITLES_PROMPT
            if self.allow_multiple
            else texts.SELECT_EMBEDDED_SUBTITLE_PROMPT
        )
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        prompt_label = QLabel(str(prompt_text), self)
        prompt_label.setWordWrap(True)
        header_row.addWidget(prompt_label, 1)

        self.select_all_checkbox = QCheckBox(str(texts.SELECT_ALL), self)
        self.select_all_checkbox.setTristate(False)
        self.select_all_checkbox.clicked.connect(self._on_select_all_clicked)
        self.select_all_checkbox.setVisible(self.allow_multiple)
        header_row.addWidget(self.select_all_checkbox)
        layout.addLayout(header_row)

        self.stream_tree = _SubtitleStreamTree(self)
        self.stream_tree.setColumnCount(5)
        self.stream_tree.setHeaderLabels(
            [
                str(texts.TRACK_LABEL),
                str(texts.LANGUAGE),
                str(texts.TITLE_LABEL),
                str(texts.FORMAT_LABEL),
                str(texts.FLAGS_LABEL),
            ]
        )
        self.stream_tree.setRootIsDecorated(False)
        self.stream_tree.setAlternatingRowColors(True)
        self.stream_tree.setStyleSheet("QTreeView::item { height: 30px; }")
        self.stream_tree.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
            if self.allow_multiple
            else QAbstractItemView.SelectionMode.SingleSelection
        )

        header = self.stream_tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        self.stream_tree.itemSelectionChanged.connect(self._update_extract_button_state)
        self.stream_tree.itemChanged.connect(self._update_extract_button_state)
        if not self.allow_multiple:
            self.stream_tree.itemDoubleClicked.connect(
                lambda *_args: self._on_extract_clicked()
            )
        layout.addWidget(self.stream_tree, 1)

        self.progress_label = QLabel(str(texts.EXTRACTING_EMBEDDED_SUBTITLES), self)
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        self.btn_extract = button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.btn_extract.setText(str(texts.EXTRACT_BUTTON))
        self.btn_cancel = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        self.btn_cancel.setText(str(texts.CANCEL))

        button_box.accepted.connect(self._on_extract_clicked)
        button_box.rejected.connect(self._on_cancel_clicked)
        layout.addWidget(button_box)

    def _populate_streams(self):
        """Populate the tree widget with the discovered extractable subtitle streams."""
        default_item = None
        for stream in self.streams:
            fmt_display = (stream.extension or stream.codec_name).upper()
            item = QTreeWidgetItem(
                [
                    str(stream.subtitle_order),
                    stream.language or "-",
                    stream.title or "-",
                    fmt_display,
                    _format_stream_flags(stream),
                ]
            )
            item.setData(0, self.STREAM_ROLE, stream)
            if self.allow_multiple:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                initial_check = (
                    Qt.CheckState.Checked
                    if len(self.streams) == 1
                    else Qt.CheckState.Unchecked
                )
                item.setCheckState(0, initial_check)
            else:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            self.stream_tree.addTopLevelItem(item)
            if stream.is_default and default_item is None:
                default_item = item

        if not self.allow_multiple and self.stream_tree.topLevelItemCount() > 0:
            target = default_item or self.stream_tree.topLevelItem(0)
            target.setSelected(True)
            self.stream_tree.setCurrentItem(target)
        self._sync_select_all_state()

    def selected_streams(self) -> list[EmbeddedSubtitleStream]:
        """Return the streams currently chosen by the user."""
        chosen: list[EmbeddedSubtitleStream] = []
        if self.allow_multiple:
            for i in range(self.stream_tree.topLevelItemCount()):
                item = self.stream_tree.topLevelItem(i)
                if item and item.checkState(0) == Qt.CheckState.Checked:
                    stream = item.data(0, self.STREAM_ROLE)
                    if stream is not None:
                        chosen.append(stream)
        else:
            for item in self.stream_tree.selectedItems():
                stream = item.data(0, self.STREAM_ROLE)
                if stream is not None:
                    chosen.append(stream)
                    break
        return chosen

    def get_extracted_files(self) -> list[str]:
        """Return the list of subtitle file paths extracted during this dialog."""
        return list(self._extracted_files)

    def _sync_select_all_state(self):
        """Synchronize the Select All checkbox with individual row check states."""
        if not self.allow_multiple or not hasattr(self, "select_all_checkbox"):
            return
        total = self.stream_tree.topLevelItemCount()
        checked = sum(
            1
            for i in range(total)
            if self.stream_tree.topLevelItem(i).checkState(0) == Qt.CheckState.Checked
        )
        if total > 0 and checked == total:
            target_state = Qt.CheckState.Checked
        elif checked == 0:
            target_state = Qt.CheckState.Unchecked
        else:
            target_state = Qt.CheckState.PartiallyChecked

        self.select_all_checkbox.blockSignals(True)
        try:
            self.select_all_checkbox.setCheckState(target_state)
        finally:
            self.select_all_checkbox.blockSignals(False)

    def _on_select_all_clicked(self):
        """Toggle all subtitle rows between checked and unchecked."""
        if not self.allow_multiple:
            return
        total = self.stream_tree.topLevelItemCount()
        if total == 0:
            return
        all_checked = all(
            self.stream_tree.topLevelItem(i).checkState(0) == Qt.CheckState.Checked
            for i in range(total)
        )
        target_state = (
            Qt.CheckState.Unchecked if all_checked else Qt.CheckState.Checked
        )
        self.stream_tree.blockSignals(True)
        try:
            for i in range(total):
                item = self.stream_tree.topLevelItem(i)
                if item is not None:
                    item.setCheckState(0, target_state)
        finally:
            self.stream_tree.blockSignals(False)
        self._update_extract_button_state()

    def _update_extract_button_state(self, *_args):
        """Enable Extract only when at least one stream is selected and not busy."""
        self._sync_select_all_state()
        is_busy = self._extract_worker is not None and self._extract_worker.isRunning()
        self.btn_extract.setEnabled(not is_busy and bool(self.selected_streams()))

    def _set_extracting_ui(self, extracting: bool):
        """Toggle progress widgets and input controls while extraction runs."""
        self.stream_tree.setEnabled(not extracting)
        if hasattr(self, "select_all_checkbox"):
            self.select_all_checkbox.setEnabled(not extracting)
        self.btn_extract.setEnabled(not extracting and bool(self.selected_streams()))
        self.progress_label.setVisible(extracting)
        self.progress_bar.setVisible(extracting)
        if extracting:
            self.progress_label.setText(str(texts.EXTRACTING_EMBEDDED_SUBTITLES))
            if self.duration_sec and self.duration_sec > 0:
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(0)
                self.progress_bar.setTextVisible(True)
            else:
                self.progress_bar.setRange(0, 0)
                self.progress_bar.setTextVisible(False)
        else:
            self.btn_cancel.setEnabled(True)

    def _on_extract_progress(self, percent: float):
        """Update the progress bar percentage during ffmpeg extraction."""
        pct = min(100, max(0, int(percent)))
        if self.progress_bar.maximum() != 100:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setTextVisible(True)
        self.progress_bar.setValue(pct)

    def _on_extract_clicked(self):
        """Start extracting the selected embedded subtitle stream(s)."""
        if self._extract_worker is not None and self._extract_worker.isRunning():
            return
        streams = self.selected_streams()
        if not streams:
            return

        self._cancelled_flag = {"cancelled": False}
        self._process_holder = {}
        self._set_extracting_ui(True)

        worker = _ExtractWorker(
            self.video_path,
            streams,
            self.duration_sec,
            self._cancelled_flag,
            self._process_holder,
            self,
        )
        self._extract_worker = worker
        worker.progress_changed.connect(self._on_extract_progress)
        worker.finished_extract.connect(self._on_extract_finished)
        worker.start()

    def _on_extract_finished(self, result: SubtitleSelectionExtractionResult):
        """Handle completion, cancellation, or failure of the extraction worker."""
        worker = self._extract_worker
        if worker is not None:
            worker.wait(5000)
        self._extract_worker = None
        self._set_extracting_ui(False)

        if result.cancelled or self._cancelled_flag.get("cancelled"):
            super().reject()
            return

        if result.error or not result.extracted_files:
            QMessageBox.warning(
                self,
                str(texts.ERROR),
                str(result.error or texts.EXTRACTION_FAILED_PREFIX),
            )
            return

        self._extracted_files = list(result.extracted_files)
        super().accept()

    def _cancel_active_extraction(self):
        """Request cooperative cancellation of an active extraction worker."""
        self._cancelled_flag["cancelled"] = True
        self.btn_cancel.setEnabled(False)
        proc = self._process_holder.get("process")
        if proc is not None:
            terminate_process_safely(proc)

    def _on_cancel_clicked(self):
        """Cancel active extraction or close the dialog immediately if idle."""
        if self._extract_worker is not None and self._extract_worker.isRunning():
            self._cancel_active_extraction()
            return
        super().reject()

    def reject(self):
        """Intercept Escape/reject so active extraction terminates before closing."""
        if self._extract_worker is not None and self._extract_worker.isRunning():
            self._cancel_active_extraction()
            return
        super().reject()

    def closeEvent(self, event):
        """Prevent destroying a running QThread if the user closes the window."""
        if self._extract_worker is not None and self._extract_worker.isRunning():
            self._cancel_active_extraction()
            event.ignore()
            return
        super().closeEvent(event)


def extract_embedded_subtitles_workflow(
    parent,
    video_path: str,
    *,
    allow_multiple: bool = False,
) -> Optional[list[str]]:
    """Scan ``video_path`` for embedded subtitles, prompt selection, and extract.

    Args:
        parent: Parent QWidget for modal dialogs and warnings.
        video_path: Path to the local video file to scan.
        allow_multiple: True for multi-select (batch mode), False for single-select.

    Returns:
        List of extracted subtitle file paths next to ``video_path``, or ``None``
        if cancelled, invalid, or no compatible embedded subtitles were found.
    """
    if not video_path or not os.path.isfile(video_path):
        QMessageBox.warning(
            parent,
            str(texts.FILE_NOT_FOUND_TITLE),
            str(texts.FILE_NOT_FOUND_MESSAGE),
        )
        return None

    if not is_video_extension(video_path):
        QMessageBox.warning(
            parent,
            str(texts.INVALID_FILE_TYPE_TITLE),
            str(texts.INVALID_FILE_TYPE_MESSAGE),
        )
        return None

    probe_result = _probe_video_with_progress(parent, video_path)
    if probe_result is None or probe_result.cancelled:
        return None

    if probe_result.error:
        QMessageBox.warning(parent, str(texts.ERROR), str(probe_result.error))
        return None

    extractable = probe_result.extractable_streams
    if not extractable:
        title_text = (
            texts.USE_EMBEDDED_SUBTITLES
            if allow_multiple
            else texts.USE_EMBEDDED_SUBTITLE
        )
        QMessageBox.information(
            parent,
            str(title_text),
            str(texts.NO_EXTRACTABLE_EMBEDDED_SUBTITLES),
        )
        return None

    dialog = EmbeddedSubtitlesDialog(
        video_path,
        extractable,
        allow_multiple=allow_multiple,
        duration_sec=probe_result.duration_sec,
        parent=parent,
    )
    try:
        if dialog.exec() == QDialog.DialogCode.Accepted:
            extracted = dialog.get_extracted_files()
            return extracted if extracted else None
        return None
    finally:
        dialog.deleteLater()
