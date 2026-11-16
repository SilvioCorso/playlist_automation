"""Auto-generated from the former ui_main.py monolith. See docs/contesto.md."""
import os
import sys
import re
import json
import html as html_module
import hashlib
from datetime import datetime
from typing import List, Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QGroupBox, QMessageBox, QFrame, QTabWidget, QSizePolicy,
    QDialog, QMenu, QStyledItemDelegate, QComboBox, QProgressDialog,
    QSlider, QStyle, QStyleOptionSlider, QSpinBox,
    QStackedWidget, QGridLayout, QScrollArea, QCheckBox, QToolTip,
    QTextBrowser, QToolButton,
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QUrl, QRect, QEvent
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QDragEnterEvent, QDropEvent,
                            QKeySequence, QShortcut, QPainter, QPen, QTextDocument)

from serato_automation.config import load_config, save_config, get_config_dir
from serato_automation.i18n import tr, init_language, set_language, get_column_headers, detect_os_language
from serato_automation.playlist_parser import PlaylistParser, PlaylistTrack
from serato_automation.library_reader import LibraryReader, normalize_string
from serato_automation.track_matcher import (
    TrackMatcher, MatchResult, MatchConfidence, CandidateMatch, compute_word_colors,
)
from serato_automation.crate_writer import (
    CrateWriter, find_serato_subcrates, validate_crate_drive, get_drive_letter,
    get_volume_label, get_volume_serial, get_volume_identifier,
    remap_path_to_current_drive,
)
from serato_automation import serato_database
from serato_automation import branding
from serato_automation import ui_theme
from serato_automation.log_handler import setup_logging, get_log_file_path

from .constants import *
from .styles import *
from .helpers import *
from .widgets import *

class ResultsTable(QTableWidget):
    selection_changed_signal = Signal()
    lock_changed_signal = Signal()

    def __init__(self, parent=None, title_locks=None, main_window=None):
        super().__init__(parent)
        self.results: List[MatchResult] = []
        self._original_order: dict = {}
        self._sort_column = -1
        self._sort_order = Qt.SortOrder.AscendingOrder
        self._title_locks = title_locks or {}
        self._main_window_ref = main_window
        self._last_checked_result_id = None
        self._select_threshold = 50  # Default threshold for "Spunta Tutti"
        self._highlight_row = -1
        self._font_size = 11
        self._restoring_columns = False
        self._fit_resize_connected = False
        self._save_columns_timer = QTimer(self)
        self._save_columns_timer.setSingleShot(True)
        self._save_columns_timer.timeout.connect(self._save_column_layout)
        if main_window is not None:
            self._font_size = int(main_window.config.get("font_size", 11))
        self._row_overlay = RowHighlightOverlay(self)
        self._init_table()
        self._init_shortcuts()
        self.itemChanged.connect(self._on_item_changed)
        self.viewport().installEventFilter(self)
        self.verticalScrollBar().valueChanged.connect(self._sync_row_overlay)
        self.horizontalScrollBar().valueChanged.connect(self._sync_row_overlay)
        # Row highlight follows ONLY actual mouse clicks (not hover/keyboard nav).
        # mousePressEvent handles plain cells; eventFilter on cell widgets handles
        # Lock / Found / Player / Titolo Richiesto widget cells.

    def _init_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+C"), self).activated.connect(self.copy_selection)

    # ------------------------------------------------------------------
    # Row highlight border (black border on active row)
    # ------------------------------------------------------------------

    def _set_highlight_row(self, row: int):
        """Update the highlighted row and reposition the overlay border."""
        if row == self._highlight_row:
            return
        self._highlight_row = row
        self._row_overlay.show_row(row)

    def _set_highlight_row_clear(self):
        """Clear the row highlight (no row active)."""
        self._set_highlight_row(-1)

    def _sync_row_overlay(self, *_args):
        """Keep overlay aligned when scrolling or resizing."""
        if self._highlight_row >= 0:
            self._row_overlay.show_row(self._highlight_row)

    def _set_cell_widget(self, row: int, col: int, widget: QWidget):
        """Set a cell widget and wire it (and its children) for row highlight on click."""
        self.setCellWidget(row, col, widget)
        widget.setProperty("_highlight_row", row)
        widget.installEventFilter(self)
        for child in widget.findChildren(QWidget):
            child.setProperty("_highlight_row", row)
            child.installEventFilter(self)
        if self._highlight_row == row:
            self._row_overlay.raise_()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                row = obj.property("_highlight_row")
                if row is not None:
                    self._set_highlight_row(int(row))
        elif obj is self.viewport() and event.type() == QEvent.Type.Resize:
            self._sync_row_overlay()
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        """Capture clicks on plain QTableWidgetItem cells (no embedded widget)."""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            idx = self.indexAt(pos)
            if idx.isValid():
                self._set_highlight_row(idx.row())
            else:
                self._set_highlight_row_clear()
        super().mousePressEvent(event)


    def retranslate_headers(self):
        labels = get_column_headers()
        header = self.horizontalHeader()
        if isinstance(header, ElidingHeaderView):
            self.setHorizontalHeaderLabels(labels)
            header.set_full_labels(labels)
        else:
            self.setHorizontalHeaderLabels(labels)

    def retranslate_content(self):
        """Refresh row tooltips and widgets after a language change."""
        for row in range(self.rowCount()):
            w = self.cellWidget(row, COL_PLAYER)
            if isinstance(w, PlayerCellWidget):
                w.retranslate_tooltips()
            lock_w = self.cellWidget(row, COL_LOCK)
            if lock_w is not None:
                btn = lock_w.findChild(QPushButton)
                if btn is not None:
                    locked = btn.text() == "\U0001F512"
                    btn.setToolTip(
                        tr("lock_tooltip_locked") if locked else tr("lock_tooltip_unlock")
                    )
            found_w = self.cellWidget(row, COL_FOUND)
            if found_w is not None and self.results and row < len(self.results):
                result = self.results[row]
                if result.is_effectively_matched and isinstance(found_w, QLabel):
                    n_total = len(result.all_matches) if result.all_matches else 1
                    display_count = min(n_total, 99)
                    found_w.setToolTip(
                        tr("found_versions_tooltip", count=display_count, total=n_total)
                    )

    def _cell_font(self, bold: bool = False) -> QFont:
        weight = QFont.Weight.Bold if bold or self._font_size >= 17 else QFont.Weight.Normal
        return QFont("Segoe UI", self._font_size, weight)

    def _row_height_for_font(self) -> int:
        """Row height that fully contains the TitleColorDelegate's QTextDocument.

        QTextDocument renders a single line taller than QFontMetrics.height()
        (e.g. 27px vs 23px at 17px bold). Sizing rows from the document height
        guarantees the coloured title text is never clipped at large fonts.
        """
        weight = QFont.Weight.Bold if self._font_size >= 17 else QFont.Weight.Normal
        probe = QTextDocument()
        probe.setDefaultFont(QFont("Segoe UI", self._font_size, weight))
        probe.setDocumentMargin(0)
        probe.setHtml("<span>Ag</span>")
        return max(22, int(probe.size().height()) + 6)

    def apply_font_size(self, font_size: int) -> None:
        """Apply config font size to table cells (except checkbox column) and row height."""
        self._font_size = int(font_size)
        header_pt = max(8, self._font_size - 1)
        self.horizontalHeader().setFont(
            QFont("Segoe UI", header_pt, QFont.Weight.Bold)
        )
        header = self.horizontalHeader()
        if isinstance(header, ElidingHeaderView):
            header._update_elided_labels()
        else:
            header.viewport().update()
        row_h = self._row_height_for_font()
        self.verticalHeader().setDefaultSectionSize(row_h)
        if self.results:
            saved_checks = self._save_checkbox_states()
            self.populate(self.results)
            self._restore_checkbox_states(saved_checks)

    def _init_table(self):
        self.setColumnCount(NUM_COLS)
        eliding_header = ElidingHeaderView(Qt.Orientation.Horizontal, self)
        self.setHorizontalHeader(eliding_header)
        # setHorizontalHeaderLabels creates QTableWidgetItem objects in the model;
        # without them, model().setHeaderData() in _update_elided_labels silently
        # fails and Qt falls back to showing column numbers (1, 2, 3…).
        self.setHorizontalHeaderLabels(get_column_headers())
        eliding_header.set_full_labels(get_column_headers())

        text_delegate = TextSelectionDelegate()
        self.setItemDelegateForColumn(COL_TITOLO_RICHIESTO, TitleColorDelegate())
        for col in (COL_FILENAME, COL_ARTISTA_SERATO,
                     COL_SONG_SERATO, COL_GENRE, COL_BPM, COL_COMMENT):
            self.setItemDelegateForColumn(col, text_delegate)

        header = self.horizontalHeader()
        for col in range(NUM_COLS):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.setSectionsMovable(True)
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self._on_header_clicked)
        header.sectionMoved.connect(self._schedule_save_column_layout)
        header.sectionResized.connect(self._on_header_section_resized)
        header.setSortIndicatorShown(True)

        # Default column widths (overridden by saved layout when present)
        widths = {COL_LOCK: 34, COL_SELECT: 50, COL_SCORE: 55, COL_FOUND: 50,
                  COL_TITOLO_RICHIESTO: 250, COL_FILENAME: 200,
                  COL_ARTISTA_SERATO: 180, COL_SONG_SERATO: 200,
                  COL_GENRE: 100, COL_BPM: 55, COL_COMMENT: 150,
                  COL_PLAYER: 160, COL_HOTCUE: 70}
        for col, w in widths.items():
            self.setColumnWidth(col, w)

        self._restore_column_layout()

        fit = (
            self._main_window_ref.config.get("table_fit_columns", False)
            if self._main_window_ref else False
        )
        self.apply_fit_columns(fit)

        self.setAlternatingRowColors(False)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(self._row_height_for_font())
        self.horizontalHeader().setFont(
            QFont("Segoe UI", max(8, self._font_size - 1), QFont.Weight.Bold)
        )

    def _schedule_save_column_layout(self, *_args):
        if self._restoring_columns:
            return
        self._save_columns_timer.start(250)

    def _on_header_section_resized(self, *_args):
        header = self.horizontalHeader()
        if isinstance(header, ElidingHeaderView):
            header._update_elided_labels()
        self._schedule_save_column_layout()

    def _save_column_layout(self):
        if self._restoring_columns or not self._main_window_ref:
            return
        header = self.horizontalHeader()
        order = [header.logicalIndex(visual) for visual in range(header.count())]
        widths = {str(logical): header.sectionSize(logical) for logical in range(header.count())}
        self._main_window_ref.config["results_table_columns"] = {
            "order": order,
            "widths": widths,
        }
        save_config(self._main_window_ref.config)

    def _restore_column_layout(self):
        if not self._main_window_ref:
            return
        saved = self._main_window_ref.config.get("results_table_columns") or {}
        order = saved.get("order") or []
        widths = saved.get("widths") or {}
        if not order and not widths:
            return

        self._restoring_columns = True
        try:
            header = self.horizontalHeader()
            for logical_str, width in widths.items():
                try:
                    logical = int(logical_str)
                    if 0 <= logical < header.count():
                        header.resizeSection(logical, int(width))
                except (TypeError, ValueError):
                    continue
            if order and len(order) == header.count():
                for target_visual, logical in enumerate(order):
                    if not (0 <= logical < header.count()):
                        continue
                    current_visual = header.visualIndex(logical)
                    if current_visual != target_visual:
                        header.moveSection(current_visual, target_visual)
            if isinstance(header, ElidingHeaderView):
                header._update_elided_labels()
        finally:
            self._restoring_columns = False

    def apply_fit_columns(self, fit: bool) -> None:
        """Toggle between free horizontal scroll and fit-to-window (no scroll)."""
        if fit:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            if not self._fit_resize_connected:
                self.horizontalHeader().sectionResized.connect(
                    self._on_section_resized_fit, Qt.ConnectionType.UniqueConnection
                )
                self._fit_resize_connected = True
            # Viewport width may not be final yet (during _init_table); defer.
            QTimer.singleShot(0, self._fit_columns_to_viewport)
        else:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            if self._fit_resize_connected:
                try:
                    self.horizontalHeader().sectionResized.disconnect(self._on_section_resized_fit)
                except RuntimeError:
                    pass
                self._fit_resize_connected = False

    def _last_visible_logical(self) -> int:
        header = self.horizontalHeader()
        for visual in range(header.count() - 1, -1, -1):
            lg = header.logicalIndex(visual)
            if not self.isColumnHidden(lg):
                return lg
        return -1

    def _fit_columns_to_viewport(self) -> None:
        """In fit mode: if the visible columns overflow the viewport, scale them
        down proportionally so the last column stays on screen (the horizontal
        scrollbar is disabled in this mode). When columns already fit,
        stretchLastSection fills any leftover space, so we leave widths alone.
        """
        if not self._fit_resize_connected:
            return
        header = self.horizontalHeader()
        vp = self.viewport().width()
        if vp <= 0:
            return
        visible = [c for c in range(header.count()) if not self.isColumnHidden(c)]
        if not visible:
            return
        total = sum(header.sectionSize(c) for c in visible)
        if total <= vp:
            return
        scale = vp / total
        self._restoring_columns = True
        try:
            acc = 0
            for c in visible[:-1]:
                new_w = max(20, int(header.sectionSize(c) * scale))
                header.resizeSection(c, new_w)
                acc += new_w
            header.resizeSection(visible[-1], max(20, vp - acc))
        finally:
            self._restoring_columns = False
        if isinstance(header, ElidingHeaderView):
            header._update_elided_labels()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._fit_resize_connected:
            self._fit_columns_to_viewport()

    def _on_section_resized_fit(self, logical_index: int, old_size: int, new_size: int):
        """When fit-columns mode is on and the user drags a column: shrink the
        last visible column to compensate so total width stays within the
        viewport (Excel-style)."""
        if self._restoring_columns:
            return
        header = self.horizontalHeader()
        last_logical = self._last_visible_logical()
        if last_logical < 0 or last_logical == logical_index:
            return
        delta = new_size - old_size
        if delta == 0:
            return
        current = header.sectionSize(last_logical)
        new_w = max(20, current - delta)
        if new_w != current:
            self._restoring_columns = True
            try:
                header.resizeSection(last_logical, new_w)
            finally:
                self._restoring_columns = False

    # ------------------------------------------------------------------
    # Sorting
    # ------------------------------------------------------------------

    def _on_header_clicked(self, logical_index: int):
        # Disable sorting on player column
        if logical_index == COL_PLAYER:
            return
        saved_checks = self._save_checkbox_states()

        if logical_index == self._sort_column:
            self._sort_order = (
                Qt.SortOrder.DescendingOrder
                if self._sort_order == Qt.SortOrder.AscendingOrder
                else Qt.SortOrder.AscendingOrder
            )
        else:
            self._sort_column = logical_index
            self._sort_order = Qt.SortOrder.AscendingOrder

        self.horizontalHeader().setSortIndicator(self._sort_column, self._sort_order)
        self._sort_results_by_column(self._sort_column, self._sort_order)
        self.populate(self.results)
        self._restore_checkbox_states(saved_checks)
        self.selection_changed_signal.emit()

    def _save_checkbox_states(self) -> dict:
        states = {}
        for i, r in enumerate(self.results):
            item = self.item(i, COL_SELECT)
            if item:
                states[id(r)] = item.checkState() == Qt.CheckState.Checked
        return states

    def _restore_checkbox_states(self, states: dict):
        self.blockSignals(True)
        for i, r in enumerate(self.results):
            if id(r) in states:
                item = self.item(i, COL_SELECT)
                if item:
                    item.setCheckState(
                        Qt.CheckState.Checked if states[id(r)]
                        else Qt.CheckState.Unchecked
                    )
        self.blockSignals(False)

    def _sort_results_by_column(self, column: int, order: Qt.SortOrder):
        def sort_key(result: MatchResult):
            if column == COL_SELECT:
                return self._original_order.get(id(result), 0)
            if column == COL_SCORE:
                return self._effective_score(result)
            if column == COL_FOUND:
                # Sort by displayed value (matches _set_found_cell logic):
                # effectively matched rows sort by max(n_above_threshold, 1);
                # non-effectively-matched rows (0% score or unmatched) sort by 0
                n_above = sum(1 for c in result.candidates if c.score >= FOUNDDROP_MIN_SCORE)
                return max(n_above, 1) if result.is_effectively_matched else 0
            if column == COL_TITOLO_RICHIESTO:
                return (result.playlist_track.original_line or "").lower()
            lt = result.library_track
            if not lt:
                return ""
            if column == COL_FILENAME:
                return os.path.basename(lt.filepath).lower()
            if column == COL_ARTISTA_SERATO:
                return (lt.artist or "").lower()
            if column == COL_SONG_SERATO:
                return (lt.title or "").lower()
            if column == COL_GENRE:
                return (lt.genre or "").lower()
            if column == COL_BPM:
                try:
                    return int(lt.bpm) if lt.bpm else 0
                except (ValueError, TypeError):
                    return 0
            if column == COL_COMMENT:
                return (lt.comment or "").lower()
            if column == COL_HOTCUE:
                if self._main_window_ref:
                    c = self._main_window_ref._hotcue_count(lt.filepath)
                    return c if isinstance(c, int) else -1
                return -1
            if column == COL_LOCK:
                return 0 if self._is_row_locked(result) else 1
            if column == COL_PLAYER:
                return 0  # No sorting on player column
            return ""

        self.results.sort(
            key=sort_key, reverse=(order == Qt.SortOrder.DescendingOrder)
        )

    # ------------------------------------------------------------------
    # Populate
    # ------------------------------------------------------------------

    def populate(self, results: List[MatchResult]):
        if not self._original_order:
            self._original_order = {id(r): i for i, r in enumerate(results)}
        self.results = results
        self.setRowCount(len(results))
        self.blockSignals(True)
        for i, result in enumerate(results):
            self._populate_row(i, result)
        self.blockSignals(False)
        # _highlight_duplicate_filenames() re-colours all rows first, so no need
        # for a separate _color_all_rows() call here.
        self._highlight_duplicate_filenames()
        if self._highlight_row >= 0:
            self._sync_row_overlay()
        self._fit_columns_to_viewport()

    def _populate_row(self, i: int, result: MatchResult):
        self._clear_row_widgets(i)
        self._set_select_cell(i, result)
        self._set_score_cell(i, result)
        self._set_found_cell(i, result)
        self._set_title_cell(i, result)
        self._set_track_detail_cells(i, result)
        self._set_hotcue_cell(i, result)
        self._set_lock_cell(i, result)
        self._set_player_cell(i, result)

    def _clear_row_widgets(self, row: int):
        for col in range(self.columnCount()):
            w = self.cellWidget(row, col)
            if w:
                self.removeCellWidget(row, col)

    def _set_select_cell(self, row: int, result: MatchResult):
        item = QTableWidgetItem()
        item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        # Only auto-check effectively matched rows (score > 0). A 0%-score row
        # behaves as 'missing' and should NOT be auto-checked.
        should_check = (
            result.is_effectively_matched
            and self._effective_score(result) > AUTO_SELECT_THRESHOLD
        )
        item.setCheckState(
            Qt.CheckState.Checked if should_check else Qt.CheckState.Unchecked
        )
        self.setItem(row, COL_SELECT, item)

    def _is_row_locked(self, result: MatchResult) -> bool:
        """Check if this result's match is title-locked by the user.

        Lock sources (any triggers lock):
        1. Composer metadata: found track has [lock] in composer field
        2. JSON title_locks: title→filepath mapping in title_locks dict
        """
        if not result.is_effectively_matched or not result.library_track:
            return False

        # Check 1: composer [lock] tag (survives restarts via audio metadata)
        if result.library_track.is_composer_locked:
            title_norm = normalize_string(result.playlist_track.title or "")
            track_title_norm = normalize_string(result.library_track.title or "")
            if title_norm and track_title_norm:
                if title_norm in track_title_norm or track_title_norm in title_norm:
                    return True

        # Check 2: JSON title_locks dict (in-memory + JSON file backup)
        if self._title_locks:
            title_norm = normalize_string(result.playlist_track.title or "")
            if not title_norm:
                return False
            fp = result.library_track.filepath
            for lock_key, lock_path in self._title_locks.items():
                if (lock_key in title_norm or title_norm in lock_key) and fp == lock_path:
                    return True

        return False

    def _effective_score(self, result: MatchResult) -> int:
        """Return 100 for locked rows, actual score otherwise."""
        if self._is_row_locked(result):
            return 100
        return result.score

    def _set_score_cell(self, row: int, result: MatchResult):
        if result.is_effectively_matched:
            eff = self._effective_score(result)
            item = QTableWidgetItem(format_score(eff))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(score_to_text_color(eff))
            item.setFont(self._cell_font(bold=True))
        else:
            item = QTableWidgetItem(format_score(0))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(QColor("#c0392b"))
            item.setFont(self._cell_font())
        self.setItem(row, COL_SCORE, item)

    def _set_found_cell(self, row: int, result: MatchResult):
        n_above = sum(1 for c in result.candidates if c.score >= FOUNDDROP_MIN_SCORE)
        n_total = result.num_candidates

        # Display value: only count candidates with score > 0 as 'found' (a 0%
        # candidate is a pipeline-rejected match, treated as missing for display).
        # When effectively matched, ensure at least 1.
        if result.is_effectively_matched:
            # Count candidates that are above the FOUNDDROP threshold OR are the
            # selected candidate (which is the active match even if below threshold).
            n_visible = sum(
                1 for j, c in enumerate(result.candidates)
                if c.score >= FOUNDDROP_MIN_SCORE or j == result.selected_index
            )
            display_count = max(n_visible, 1)
        else:
            display_count = 0
            n_above = 0  # treat as zero for dropdown decision

        # Dropdown only when MULTIPLE candidates are above threshold
        if n_above > 1:
            # Clear any old QTableWidgetItem before setting widget
            old = self.takeItem(row, COL_FOUND)
            label = QLabel(f"\u25BC {display_count}")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setCursor(Qt.CursorShape.PointingHandCursor)
            label.setToolTip(
                tr("found_versions_tooltip", count=display_count, total=n_total)
            )
            label.setProperty("_found_count", display_count)
            label.setStyleSheet(
                f"color: {'#9b7de0' if ui_theme.is_dark() else '#4927af'}; "
                f"font-weight: bold; font-size: {self._font_size}px; "
                "text-decoration: underline; padding: 0 2px; background: transparent;"
            )
            label.setProperty("_row", row)
            label.mousePressEvent = lambda event, r=row, lb=label: self._on_found_label_pressed(r, lb, event)
            self._set_cell_widget(row, COL_FOUND, label)
        elif display_count == 1:
            # Exactly 1 candidate (above or below threshold) — show "1"
            item = QTableWidgetItem("1")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(QColor("#c5cae0" if ui_theme.is_dark() else "#95a5a6"))
            item.setFont(self._cell_font())
            self.setItem(row, COL_FOUND, item)
        else:
            # No match at all — show "0"
            item = QTableWidgetItem("0")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(QColor("#ff7070" if ui_theme.is_dark() else "#c0392b"))
            item.setFont(self._cell_font())
            self.setItem(row, COL_FOUND, item)

    def _set_title_cell(self, row: int, result: MatchResult):
        req_text = result.playlist_track.original_line or result.playlist_track.title or ""
        item = QTableWidgetItem(req_text)
        item.setFont(self._cell_font())
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        if result.is_effectively_matched and result.library_track:
            item.setData(
                ROLE_WORD_COLORS,
                compute_word_colors(req_text, result.library_track),
            )
        else:
            item.setData(ROLE_WORD_COLORS, None)
        self.setItem(row, COL_TITOLO_RICHIESTO, item)

    def _set_track_detail_cells(self, row: int, result: MatchResult):
        # Only show real filename/metadata when the row is EFFECTIVELY matched
        # (is_matched AND score > 0). A 0% match is treated as 'missing' — all
        # detail cells show "-" and no player widget is created.
        if result.is_effectively_matched and result.library_track:
            lt = result.library_track
            self._set_editable_item(row, COL_FILENAME, os.path.basename(lt.filepath))
            self._set_editable_item(row, COL_ARTISTA_SERATO, lt.artist or "-")
            self._set_editable_item(row, COL_SONG_SERATO, lt.title or "-")
            self._set_editable_item(row, COL_GENRE, lt.genre or "-")
            bpm_item = self._set_editable_item(row, COL_BPM, lt.bpm or "-")
            if bpm_item:
                bpm_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            comment = lt.comment or "-"
            if len(comment) > 60:
                comment = comment[:60] + "..."
            self._set_editable_item(row, COL_COMMENT, comment)
        else:
            # Unmatched / 0%-match row: show "-" in every detail cell for consistency
            for col in (COL_FILENAME, COL_ARTISTA_SERATO, COL_SONG_SERATO,
                        COL_GENRE, COL_BPM, COL_COMMENT):
                self._set_editable_item(row, col, "-")

    def _set_editable_item(self, row: int, col: int, text: str) -> Optional[QTableWidgetItem]:
        item = QTableWidgetItem(text)
        item.setFont(self._cell_font())
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        self.setItem(row, col, item)
        return item

    def _hotcue_column_enabled(self) -> bool:
        mw = self._main_window_ref
        if mw is None:
            return False
        return bool(mw.config.get("visible_columns", {}).get("hotcue", False))

    def _set_hotcue_cell(self, row: int, result: MatchResult):
        """Set the Hotcue cell. Counts are computed only when the column is on."""
        text = "-"
        if (self._hotcue_column_enabled() and result.is_effectively_matched
                and result.library_track and self._main_window_ref):
            cnt = self._main_window_ref._hotcue_count(result.library_track.filepath)
            text = "?" if cnt is None else str(cnt)
        item = QTableWidgetItem(text)
        item.setFont(self._cell_font())
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self.setItem(row, COL_HOTCUE, item)

    def refresh_hotcue_column(self):
        """Recompute the Hotcue column for all rows (after enabling it)."""
        self.blockSignals(True)
        for row, result in enumerate(self.results):
            self._set_hotcue_cell(row, result)
        self.blockSignals(False)

    # ------------------------------------------------------------------
    # Found column — switch between candidates
    # ------------------------------------------------------------------

    def _on_found_label_pressed(self, row: int, label_widget, event):
        """Handle Found dropdown label click — highlight row then open menu."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._set_highlight_row(row)
        self._on_found_clicked(row, label_widget)

    def _on_found_clicked(self, row: int, label_widget):
        if row < 0 or row >= len(self.results):
            return
        result = self.results[row]
        if len(result.candidates) <= 1:
            return

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ font-size: {self._font_size}px; padding: 4px; min-width: 400px; }}
            QMenu::item {{ padding: 6px 20px 6px 10px; }}
            QMenu::item:selected {{ background-color: #d4c5f9; }}
        """)

        for j, cand in enumerate(result.candidates):
            if cand.score < FOUNDDROP_MIN_SCORE and j != result.selected_index:
                continue
            lt = cand.library_track
            display = f"{lt.artist} - {lt.title}" if lt.artist and lt.title else lt.display_name
            check = "\u2713 " if j == result.selected_index else "    "
            action = menu.addAction(f"{check}{format_score(cand.score)}  -  {display}")
            if j == result.selected_index:
                font = action.font()
                font.setBold(True)
                action.setFont(font)
            action.setData(j)

        label_pos = label_widget.mapToGlobal(label_widget.rect().bottomLeft())
        clicked_action = menu.exec_(label_pos)

        if clicked_action is not None:
            new_index = clicked_action.data()
            if new_index is not None and new_index != result.selected_index:
                result.selected_index = new_index
                self._populate_row(row, result)
                self._color_single_row(row)
                # Re-apply cyan duplicate highlighting — the candidate change may
                # have introduced or removed a duplicate filename (this row's new
                # filename, and possibly other rows that share it).
                self._highlight_duplicate_filenames()
                self.selection_changed_signal.emit()
                # Update player widget with new candidate filepath
                mw = self._main_window_ref
                if mw and mw._player_current_row == row:
                    mw._player_stop_current()

    # ------------------------------------------------------------------
    # Row colouring
    # ------------------------------------------------------------------

    def _color_all_rows(self):
        for i in range(len(self.results)):
            self._color_single_row(i)

    def _color_single_row(self, i: int):
        result = self.results[i]
        # Use is_effectively_matched so 0%-score rows get the 'missing' pink
        # background, consistent with the rest of the row treatment.
        eff = self._effective_score(result)
        if result.is_effectively_matched:
            bg = score_to_bg_color(eff)
        else:
            bg = QColor(72, 22, 22) if ui_theme.is_dark() else QColor(255, 195, 195)
        bg_css = f"background-color: {bg.name()};"
        for col in range(self.columnCount()):
            item = self.item(i, col)
            if item:
                item.setBackground(bg)
            widget = self.cellWidget(i, col)
            if isinstance(widget, (QLabel, QPushButton)):
                # Strip previous background-color to prevent accumulation
                existing_ss = widget.styleSheet()
                cleaned = re.sub(r'background-color:\s*#[0-9a-fA-F]+;\s*', '', existing_ss)
                widget.setStyleSheet(cleaned + bg_css)

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------

    def set_select_threshold(self, threshold: int):
        """Set the score threshold used by select_all_rows."""
        self._select_threshold = threshold

    def select_all_rows(self, threshold=None):
        """Check all effectively matched rows with score >= threshold."""
        if threshold is not None:
            self._select_threshold = threshold
        th = self._select_threshold
        self.blockSignals(True)
        for i, r in enumerate(self.results):
            if r.is_effectively_matched and self._effective_score(r) >= th:
                item = self.item(i, COL_SELECT)
                if item:
                    item.setCheckState(Qt.CheckState.Checked)
            else:
                item = self.item(i, COL_SELECT)
                if item:
                    item.setCheckState(Qt.CheckState.Unchecked)
        self.blockSignals(False)
        self.selection_changed_signal.emit()

    def deselect_all_rows(self):
        self.blockSignals(True)
        for i in range(self.rowCount()):
            item = self.item(i, COL_SELECT)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)
        self.blockSignals(False)
        self.selection_changed_signal.emit()

    def invert_selection(self):
        self.blockSignals(True)
        for i, r in enumerate(self.results):
            if r.is_effectively_matched:
                item = self.item(i, COL_SELECT)
                if item:
                    cur = item.checkState()
                    item.setCheckState(
                        Qt.CheckState.Unchecked if cur == Qt.CheckState.Checked
                        else Qt.CheckState.Checked
                    )
        self.blockSignals(False)
        self.selection_changed_signal.emit()

    def get_selected_for_crate(self) -> List[MatchResult]:
        return [
            r for i, r in enumerate(self.results)
            if r.is_effectively_matched
            and (item := self.item(i, COL_SELECT))
            and item.checkState() == Qt.CheckState.Checked
        ]

    def get_selected_for_missing(self) -> List[MatchResult]:
        out = []
        for i, r in enumerate(self.results):
            if not r.is_effectively_matched:
                out.append(r)
            elif (item := self.item(i, COL_SELECT)) and item.checkState() != Qt.CheckState.Checked:
                out.append(r)
        return out

    def copy_selection(self):
        """Copy table content to clipboard — always prefers checked rows."""
        # Always prefer checked rows
        rows = {
            i for i in range(self.rowCount())
            if (item := self.item(i, COL_SELECT))
            and item.checkState() == Qt.CheckState.Checked
        }
        if not rows:
            # Fallback to visual selection
            rows = {idx.row() for idx in self.selectedIndexes()}
        if not rows:
            return

        _headers = get_column_headers()
        _copy_headers = [_headers[c] for c in range(NUM_COLS) if c not in (COL_LOCK, COL_PLAYER)]
        lines = ["\t".join(_copy_headers)]
        for row in sorted(rows):
            cells = []
            for col in range(NUM_COLS):
                if col in (COL_LOCK, COL_PLAYER):
                    continue
                if col == COL_SELECT:
                    item = self.item(row, col)
                    cells.append("SI" if item and item.checkState() == Qt.CheckState.Checked else "")
                elif col == COL_FOUND:
                    # Handle cellWidget (dropdown "▼ N") vs item ("0", "1")
                    widget = self.cellWidget(row, col)
                    if widget and isinstance(widget, QLabel):
                        cells.append(str(widget.text()))
                    else:
                        item = self.item(row, col)
                        cells.append(item.text() if item else "")
                elif col == COL_TITOLO_RICHIESTO:
                    item = self.item(row, col)
                    cells.append(item.text() if item else "")
                else:
                    item = self.item(row, col)
                    cells.append(item.text() if item else "")
            lines.append("\t".join(cells))
        QApplication.clipboard().setText("\n".join(lines))

    def copy_last_checked(self):
        """Copy only the last chronologically checked row to clipboard."""
        if not self._last_checked_result_id:
            return
        last_row = -1
        for i, r in enumerate(self.results):
            if id(r) == self._last_checked_result_id:
                chk = self.item(i, COL_SELECT)
                if chk and chk.checkState() == Qt.CheckState.Checked:
                    last_row = i
                break
        if last_row < 0:
            return

        cells = []
        for col in range(NUM_COLS):
            if col in (COL_LOCK, COL_PLAYER):
                continue
            if col == COL_SELECT:
                cells.append("SI")
            elif col == COL_FOUND:
                widget = self.cellWidget(last_row, col)
                if widget and isinstance(widget, QLabel):
                    cells.append(str(widget.text()))
                else:
                    item = self.item(last_row, col)
                    cells.append(item.text() if item else "")
            elif col == COL_TITOLO_RICHIESTO:
                item = self.item(last_row, col)
                cells.append(item.text() if item else "")
            else:
                item = self.item(last_row, col)
                cells.append(item.text() if item else "")
        QApplication.clipboard().setText("\t".join(cells))

    # ------------------------------------------------------------------
    # Checkbox tracking (chronological)
    # ------------------------------------------------------------------

    def _on_item_changed(self, item):
        """Track the last chronologically checked row and notify UI updates."""
        if item.column() == COL_SELECT:
            row = item.row()
            if item.checkState() == Qt.CheckState.Checked:
                if 0 <= row < len(self.results):
                    self._last_checked_result_id = id(self.results[row])
            # Always notify so button states (Salva Mancanti, etc.) stay in sync
            self.selection_changed_signal.emit()

    # ------------------------------------------------------------------
    # Per-row Lock button
    # ------------------------------------------------------------------

    def _set_lock_cell(self, row: int, result: MatchResult):
        """Add a lock/unlock toggle button for effectively matched rows only.

        A 0%-score row (pipeline-rejected match) is treated as 'missing' — no
        lock button, just an empty non-interactive cell.
        """
        if result.is_effectively_matched and result.library_track:
            is_locked = self._is_row_locked(result)
            btn = QPushButton("\U0001f512" if is_locked else "\U0001f513")
            btn.setFixedSize(28, 22)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if is_locked:
                btn.setToolTip(tr("lock_tooltip_locked"))
                btn.setAccessibleDescription(tr("lock_tooltip_locked"))
                btn.setStyleSheet(
                    "QPushButton { border: 1px solid #4927af; font-size: 13px; "
                    "background: #d4c5f9; border-radius: 3px; padding: 0; }"
                    "QPushButton:hover { background: #b8a0e8; }"
                )
            else:
                btn.setToolTip(tr("lock_tooltip_unlock"))
                btn.setAccessibleDescription(tr("lock_tooltip_unlock"))
                btn.setStyleSheet(
                    "QPushButton { border: none; font-size: 13px; color: #bbb; "
                    "background: transparent; padding: 0; }"
                    "QPushButton:hover { color: #4927af; background: #f0ecfa; "
                    "border-radius: 3px; }"
                )
            btn.setProperty("_row", row)
            btn.clicked.connect(lambda checked, r=row: self._on_lock_row_clicked(r))
            self._set_cell_widget(row, COL_LOCK, btn)
        else:
            item = QTableWidgetItem("")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.setItem(row, COL_LOCK, item)

    def _on_lock_row_clicked(self, row: int):
        """Toggle the title lock for a specific row.
        
        Writes [lock] to the audio file's composer field for persistence.
        Also keeps the JSON title_locks as backup.
        """
        if row < 0 or row >= len(self.results):
            return
        result = self.results[row]
        if not result.is_effectively_matched or not result.library_track:
            return
        title_norm = normalize_string(result.playlist_track.title or "")
        if not title_norm:
            return
        filepath = result.library_track.filepath
        is_locked = self._is_row_locked(result)

        if is_locked:
            # UNLOCK: remove [lock] from composer + remove from JSON
            success, msg = LibraryReader.set_composer_lock(filepath, lock=False)
            if success:
                # Update in-memory library track composer
                result.library_track.composer = ""
                for track in self._main_window_ref.library_tracks:
                    if track.filepath == filepath:
                        track.composer = ""
                        break
            else:
                # Metadata write failed, still allow JSON unlock
                pass
            # Remove from JSON title_locks
            if title_norm in self._title_locks and self._title_locks[title_norm] == filepath:
                del self._title_locks[title_norm]
        else:
            # LOCK: write [lock] to composer + add to JSON
            success, msg = LibraryReader.set_composer_lock(filepath, lock=True)
            if success:
                # Update in-memory library track composer
                result.library_track.composer = "[lock]"
                for track in self._main_window_ref.library_tracks:
                    if track.filepath == filepath:
                        track.composer = "[lock]"
                        break
            # Always add to JSON as backup (even if metadata write failed)
            self._title_locks[title_norm] = filepath

        self._set_lock_cell(row, result)
        self._set_score_cell(row, result)
        self._color_single_row(row)
        # Re-apply cyan duplicate highlighting — _color_single_row above reset
        # the background to the score colour, so we must restore cyan for dupes.
        self._highlight_duplicate_filenames()
        self.lock_changed_signal.emit()

        # Log the operation
        action = "SBLOCCATO" if is_locked else "BLOCCATO"
        track_name = result.library_track.display_name if result.library_track else "?"
        self._main_window_ref._logger.info(
            "LOCK %s: '%s' -> '%s' (metadata=%s)",
            action, result.playlist_track.title[:40], track_name[:40],
            "OK" if success else "FALLITO",
        )

    # ------------------------------------------------------------------
    # Player cell — mini audio player
    # ------------------------------------------------------------------

    def _set_player_cell(self, row: int, result: MatchResult):
        """Create a PlayerCellWidget for effectively matched rows, or '-' otherwise.

        A 0%-score row is treated as 'missing' (no candidate shown, no player).
        Only matched rows with score > 0 AND a real file on disk get the player.
        """
        # Determine if this row has a playable file
        has_playable = False
        filepath = ""
        if result.is_effectively_matched and result.library_track:
            filepath = result.library_track.filepath
            if filepath and os.path.isfile(filepath):
                has_playable = True

        if has_playable:
            mw = self._main_window_ref
            player_widget = PlayerCellWidget(row, main_window=mw)
            player_widget.set_has_file(True)
            track_name = result.library_track.display_name or os.path.basename(filepath)
            player_widget.set_track_name(track_name)
            if mw:
                player_widget.play_requested.connect(mw._player_play_row)
                player_widget.pause_requested.connect(mw._player_pause)
                player_widget.seek_requested.connect(mw._player_seek)
            self._set_cell_widget(row, COL_PLAYER, player_widget)
        else:
            # No file — show "-"
            item = QTableWidgetItem("-")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(QColor("#bbb"))
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.setItem(row, COL_PLAYER, item)

    def get_player_widget(self, row: int) -> Optional['PlayerCellWidget']:
        """Get the PlayerCellWidget for a given row, or None."""
        w = self.cellWidget(row, COL_PLAYER)
        if isinstance(w, PlayerCellWidget):
            return w
        return None

    # ------------------------------------------------------------------
    # Duplicate filename detection
    # ------------------------------------------------------------------

    def _highlight_duplicate_filenames(self):
        """Highlight rows whose displayed filename appears more than once — cyan background.

        Only considers rows that are EFFECTIVELY matched (is_matched AND score > 0)
        AND have a real filepath. 0%-score rows (pipeline-rejected) and unmatched
        rows (which display '-') are NEVER counted as duplicates.
        """
        from collections import Counter

        # First restore every row to its score-based background. Without this,
        # rows that STOPPED being duplicates (e.g. after changing the selected
        # candidate from the "Trovati" dropdown, or after a lock toggle) would
        # keep their stale cyan colour. Re-colouring here makes the highlight
        # fully self-correcting regardless of the caller.
        self._color_all_rows()

        filename_counts: Counter = Counter()
        for r in self.results:
            # Only count effectively matched rows with a real filepath — this
            # excludes all 0%-score and unmatched rows from the comparison.
            if r.is_effectively_matched and r.library_track:
                fn = os.path.basename(r.library_track.filepath or "")
                if fn:
                    filename_counts[fn] += 1
        dupes = {fn for fn, cnt in filename_counts.items() if cnt > 1}
        if not dupes:
            return
        cyan = QColor(20, 55, 72) if ui_theme.is_dark() else QColor(179, 229, 252)
        for i, r in enumerate(self.results):
            if r.is_effectively_matched and r.library_track:
                fn = os.path.basename(r.library_track.filepath or "")
                if fn in dupes:
                    for col in range(self.columnCount()):
                        item = self.item(i, col)
                        if item:
                            item.setBackground(cyan)
                        widget = self.cellWidget(i, col)
                        if isinstance(widget, (QLabel, QPushButton)):
                            existing_ss = widget.styleSheet()
                            cleaned = re.sub(r'background-color:\s*#[0-9a-fA-F]+;\s*', '', existing_ss)
                            widget.setStyleSheet(cleaned + f"background-color: {cyan.name()};")


# ===================================================================
# Format Guide Dialog
# ===================================================================



__all__ = ['ResultsTable']
