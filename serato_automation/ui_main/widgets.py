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

class BusyDialog(QDialog):
    """A small, application-modal 'please wait' dialog with a spinning bar.

    Being application-modal, it blocks input to every other window while a
    long-running operation is in progress. It intentionally has no buttons so it
    cannot be dismissed by the user before the task completes.
    """

    def __init__(self, message: str, parent=None):
        super().__init__(parent)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setMinimumWidth(320)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        self._label = QLabel(message)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)
        self._label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self._label)

        bar = QProgressBar()
        bar.setRange(0, 0)  # indeterminate (animated) progress
        bar.setTextVisible(False)
        bar.setFixedHeight(14)
        layout.addWidget(bar)

    def set_message(self, message: str):
        self._label.setText(message)
# ===================================================================
# Drop-enabled TextEdit
# ===================================================================

class DropTextEdit(QTextEdit):
    file_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setPlaceholderText(tr("ph_playlist_input"))
        self.setFont(QFont("Segoe UI", 10))

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasText() or event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText() or event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                filepath = url.toLocalFile()
                if os.path.isfile(filepath):
                    self.file_dropped.emit(filepath)
                    self._read_dropped_file(filepath)
                    break
        elif event.mimeData().hasText():
            self.insertPlainText(event.mimeData().text())

    @staticmethod
    def _read_dropped_file(filepath: str):
        """Read a dropped file with encoding fallback."""
        for enc in ("utf-8", "latin-1"):
            try:
                with open(filepath, "r", encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        return None


# ===================================================================
# Text Selection Delegate (double-click to select/copy cell text)
# ===================================================================

class TextSelectionDelegate(QStyledItemDelegate):
    """Double-click to select/copy cell text (default Qt painting)."""

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setReadOnly(True)
        editor.setFrame(False)
        editor.selectAll()
        return editor

    def setEditorData(self, editor, index):
        text = index.model().data(index, Qt.ItemDataRole.DisplayRole) or ""
        editor.setText(str(text))
        QTimer.singleShot(0, editor.selectAll)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class TitleColorDelegate(TextSelectionDelegate):
    """Title column: per-word match colours; spacing/font match other cells."""

    def paint(self, painter, option, index):
        word_colors = index.data(ROLE_WORD_COLORS)
        if not word_colors:
            super().paint(painter, option, index)
            return

        self.initStyleOption(option, index)
        painter.save()
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        elif option.backgroundBrush.style() != Qt.BrushStyle.NoBrush:
            painter.fillRect(option.rect, option.backgroundBrush)

        # Match QTableWidget::item padding (2px 6px)
        content = option.rect.adjusted(6, 2, -6, -2)
        if content.width() <= 0:
            painter.restore()
            return

        html_body = "".join(
            f'<span style="color:{color};">{html_module.escape(token)}</span>'
            for token, color in word_colors
        )
        html = f'<span style="white-space:pre;">{html_body}</span>'

        doc = QTextDocument()
        doc.setDefaultFont(option.font)
        doc.setDocumentMargin(0)
        doc.setHtml(html)
        # Do NOT call setTextWidth: it enables word-wrap which at large font sizes
        # makes the document taller than the cell, breaking vertical centering.
        # The clip rect already handles horizontal overflow.

        # Vertically centre using QFontMetrics.height() — this matches how Qt
        # centres the plain single-line text in the neighbouring columns, so the
        # coloured title aligns row-for-row with them. Rows are sized from the
        # document height (see _row_height_for_font) so the document always fits;
        # clipping to the full row rect then guarantees no descender is cropped.
        fm = QFontMetrics(option.font)
        y = option.rect.top() + max(0.0, (option.rect.height() - fm.height()) / 2.0)
        painter.translate(content.left(), y)
        painter.setClipRect(0, 0, content.width(), option.rect.height())
        doc.drawContents(painter)
        painter.restore()


class ElidingHeaderView(QHeaderView):
    """Standard header rendering with elided labels on narrow columns."""

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMouseTracking(True)
        self._tip_section = -1
        self._full_labels: List[str] = []

    def set_full_labels(self, labels: List[str]):
        self._full_labels = list(labels)
        self._update_elided_labels()

    def _update_elided_labels(self):
        if not self.model() or not self._full_labels:
            return
        orient = self.orientation()
        for i, full in enumerate(self._full_labels):
            if i >= self.count():
                break
            width = self.sectionSize(i)
            elided = self.fontMetrics().elidedText(
                full, Qt.TextElideMode.ElideRight, max(0, width - 10)
            )
            self.model().setHeaderData(
                i, orient, elided, Qt.ItemDataRole.DisplayRole
            )
        self.viewport().update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elided_labels()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        idx = self.logicalIndexAt(pos)
        if idx != self._tip_section:
            self._tip_section = idx
            if 0 <= idx < len(self._full_labels):
                full = self._full_labels[idx]
                width = self.sectionSize(idx)
                elided = self.fontMetrics().elidedText(
                    full, Qt.TextElideMode.ElideRight, max(0, width - 10)
                )
                if elided != full:
                    QToolTip.showText(event.globalPosition().toPoint(), full, self)
                else:
                    QToolTip.hideText()
            else:
                QToolTip.hideText()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._tip_section = -1
        QToolTip.hideText()
        super().leaveEvent(event)


# ===================================================================
# Clickable Slider (click anywhere on groove to seek)
# ===================================================================

class ClickableSlider(QSlider):
    """QSlider that responds to clicking anywhere on the groove, not just dragging the handle.

    Supports:
      * Click on groove → seek to that position (and emit sliderMoved so the player seeks)
      * Drag on groove   → continuously seek while dragging
      * Click/drag on handle → default Qt behaviour
    """

    def __init__(self, orientation=Qt.Orientation.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self._groove_dragging = False

    def _value_from_event(self, event) -> Optional[int]:
        """Compute slider value from a mouse event's x position. Returns None if on handle."""
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        groove_rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, opt,
            QStyle.SubControl.SC_SliderGroove, self,
        )
        handle_rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, opt,
            QStyle.SubControl.SC_SliderHandle, self,
        )
        pt = event.position().toPoint()
        if handle_rect.isValid() and handle_rect.contains(pt):
            return None
        if groove_rect.width() <= 0:
            groove_rect = self.rect()
        pos_in_groove = pt.x() - groove_rect.x()
        if self.invertedAppearance():
            pos_in_groove = groove_rect.width() - pos_in_groove
        pos_in_groove = max(0, min(groove_rect.width(), pos_in_groove))
        return QStyle.sliderValueFromPosition(
            self.minimum(), self.maximum(),
            pos_in_groove, groove_rect.width(),
            opt.upsideDown,
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            val = self._value_from_event(event)
            if val is not None:
                # Click on groove: set value AND emit sliderMoved (sliderReleased
                # is NOT emitted for click-only interactions, so emit here too).
                self.setValue(val)
                self.sliderMoved.emit(val)
                self._groove_dragging = True
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._groove_dragging:
            val = self._value_from_event(event)
            if val is not None:
                self.setValue(val)
                self.sliderMoved.emit(val)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._groove_dragging:
            self._groove_dragging = False
            # Emit sliderReleased so any listener relying on it (handle-drag
            # pattern) is notified. This guarantees the final position is
            # applied to the player even if sliderMoved was throttled.
            self.sliderReleased.emit()
            return
        super().mouseReleaseEvent(event)


# ===================================================================
# Player Cell Widget (mini audio player per row)
# ===================================================================

class PlayerCellWidget(QWidget):
    """Compact play/pause + seek slider for a single table row."""

    play_requested = Signal(int)   # row
    pause_requested = Signal()
    seek_requested = Signal(int)   # position (ms)

    def __init__(self, row: int, parent=None, main_window=None):
        super().__init__(parent)
        self.row = row
        self._is_playing = False
        self._has_file = False
        self._track_name = ""
        # Weak-ish ref to the MainWindow so the widget can register itself as
        # the active player widget BEFORE emitting play_requested. This avoids
        # relying on Qt's sender() inside a lambda slot (which returns None for
        # accordion group tables — the Advanced Duplicates player was broken
        # exactly because of that).
        self._main_window = main_window

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 4, 0)
        layout.setSpacing(3)

        self.btn_play = QPushButton("\u25B6")
        self.btn_play.setFixedSize(20, 18)
        self.btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        set_button_alt(self.btn_play, "player_play_pause")
        self.btn_play.setStyleSheet("""
            QPushButton {
                border: 1px solid #bbb; border-radius: 3px;
                background: #f8f8f8; font-size: 10px; color: #2c3e50;
                padding: 0px; min-height: 0; max-height: 18px;
            }
            QPushButton:hover { background: #e0e0e0; }
            QPushButton:pressed { background: #ccc; }
        """)
        layout.addWidget(self.btn_play)

        self.slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.setValue(0)
        self.slider.setFixedHeight(14)
        self.slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none; height: 4px; background: #ddd; border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #4927af; width: 10px; margin: -3px 0;
                border-radius: 5px;
            }
            QSlider::handle:horizontal:hover { background: #3d1d99; }
            QSlider::sub-page:horizontal {
                background: #4927af; border-radius: 2px;
            }
        """)
        layout.addWidget(self.slider, stretch=1)

        self.btn_play.clicked.connect(self._on_play_clicked)
        # Slider seek signals — connect BOTH so seek works in every interaction:
        #   * sliderMoved → fires while dragging the handle OR while clicking/dragging
        #     the groove (ClickableSlider emits it on click and during drag).
        #   * sliderReleased → fires when the user releases the mouse after dragging
        #     the handle. sliderMoved alone may NOT fire on pure handle-drag in some
        #     Qt versions, so sliderReleased is the safety net that ensures the
        #     final position is always applied to the player.
        self.slider.sliderMoved.connect(self._on_slider_moved)
        self.slider.sliderReleased.connect(self._on_slider_released)

    def _on_play_clicked(self):
        if not self._has_file:
            return
        if self._is_playing:
            self.pause_requested.emit()
        else:
            # Stash a reference to ourselves BEFORE emitting play_requested.
            # The controller reads it AFTER _player_stop_current (which clears
            # _player_active_widget) and assigns it as the active widget — so
            # state/position updates reach this widget without relying on
            # sender() (which returns None through the lambda slot used by
            # Advanced Duplicates accordion tables — the accordion player was
            # broken because of exactly that).
            mw = self._main_window
            if mw is not None:
                try:
                    mw._pending_player_widget = self
                except Exception:
                    pass
            self.play_requested.emit(self.row)

    def _on_slider_moved(self, position):
        self.seek_requested.emit(position)

    def _on_slider_released(self):
        """Final safety net: when the handle is released after a drag, ensure
        the player seeks to the slider's current position. In some Qt/OS combos
        sliderMoved does not fire reliably during handle drag, so this guarantees
        the seek always happens at the end of the interaction.
        """
        self.seek_requested.emit(self.slider.value())

    def retranslate_tooltips(self):
        if self._has_file and self._track_name:
            self.setToolTip(tr("player_play_track", name=self._track_name))
            self.setAccessibleDescription(tr("player_play_track", name=self._track_name))
        elif self._has_file:
            set_button_alt(self.btn_play, "player_play_pause")
        else:
            set_button_alt(self.btn_play, "player_no_file")

    def set_track_name(self, name: str):
        self._track_name = name
        if self._has_file:
            self.setToolTip(tr("player_play_track", name=name))

    def set_playing(self, playing: bool):
        self._is_playing = playing
        self.btn_play.setText("\u23F8" if playing else "\u25B6")

    def set_has_file(self, has: bool):
        self._has_file = has
        if not has:
            self.btn_play.setEnabled(False)
            self.btn_play.setText("\u25B6")
            set_button_alt(self.btn_play, "player_no_file")
            self.slider.setValue(0)
            self._is_playing = False
        else:
            self.btn_play.setEnabled(True)
            set_button_alt(self.btn_play, "player_play_pause")

    def update_position(self, position_ms: int, duration_ms: int):
        """Update slider from QMediaPlayer position.

        If duration is not yet known (0), do NOTHING — leaving the slider range
        and value untouched. Resetting the value to 0 here would clobber a
        previously-set range and make seek clicks map wrong until the real
        duration arrives (via durationChanged)."""
        if duration_ms <= 0:
            return
        self.slider.blockSignals(True)
        self.slider.setRange(0, duration_ms)
        self.slider.setValue(position_ms)
        self.slider.blockSignals(False)

    def reset(self):
        """Reset to initial state (no file)."""
        self._is_playing = False
        self._has_file = False
        self.btn_play.setText("\u25B6")
        self.btn_play.setEnabled(False)
        self.slider.blockSignals(True)
        self.slider.setRange(0, 1000)
        self.slider.setValue(0)
        self.slider.blockSignals(False)


# ===================================================================
# Row highlight overlay (drawn above cell widgets)
# ===================================================================

class RowHighlightOverlay(QWidget):
    """Transparent overlay on the table viewport — draws the active-row border on top."""

    def __init__(self, table: 'ResultsTable'):
        super().__init__(table.viewport())
        self._table = table
        self._row = -1
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.hide()

    def show_row(self, row: int):
        self._row = row
        self._sync_geometry()
        if self._row < 0:
            self.hide()
            return
        self.show()
        self.raise_()
        self.update()

    def _sync_geometry(self):
        row = self._row
        if not (0 <= row < self._table.rowCount()):
            self.hide()
            return
        y = self._table.rowViewportPosition(row)
        h = self._table.rowHeight(row)
        if h <= 0:
            self.hide()
            return
        self.setGeometry(0, y, self._table.viewport().width(), h)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        pen = QPen(QColor(0, 0, 0), 3)
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        w, h = self.width(), self.height()
        painter.drawRect(1, 1, max(0, w - 3), max(0, h - 3))
        painter.end()


# ===================================================================
# Results Table
# ===================================================================



__all__ = ['BusyDialog', 'DropTextEdit', 'TextSelectionDelegate', 'TitleColorDelegate', 'ElidingHeaderView', 'ClickableSlider', 'PlayerCellWidget', 'RowHighlightOverlay']
