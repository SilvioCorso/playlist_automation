# Serato Playlist Automation
# Main UI Module — PySide6 desktop application
#
# v4.4:
#   - UX: Reorganised layout — branded header, library/tools sections, footer bar
#   - NEW: Feedback link (sirviodj.it) + Pro upgrade dialog (one-time license)
#   - NEW: branding.py — centralised URLs, version, open_url helper
#   - UX: Playlist toolbar reordered (Import URL first); library status in config row
# v4.3:
#   - NEW: Dark theme + theme switch via Settings panel
#   - NEW: SettingsDialog — theme, column visibility, BPM penalty
#   - NEW: QuickGuideDialog — product guide (replaces step-by-step wizard)
#   - NEW: BPM penalty rule in TrackMatcher (disabled by default)
#   - NEW: Column visibility per-session configurable
#   - UX: Improved APP_STYLESHEET with gradients and modern look
#   - FIX: Slider click-to-seek — use QStyle.sliderValueFromPosition for accurate
#     groove mapping; fallback to widget rect when style groove is empty
#   - FIX: Row highlight border — RowHighlightOverlay widget drawn ON TOP of cell
#     widgets (paintEvent on the table was hidden beneath Lock/Found/Player widgets);
#     event filters on all cell widgets + children so clicks anywhere update highlight
# v4.1:
#   - FIX: 0%-score rows are now treated as 'missing' everywhere (no filename,
#     no player widget, no lock button, not counted as duplicate, pink background).
#     New MatchResult.is_effectively_matched property = (is_matched AND score > 0)
#     used by UI, crate_writer, report_generator. Stats now count 0% as missing.
#   - FIX: Row highlight border follows ONLY actual mouse clicks — removed the
#     currentCellChanged connection that fired on hover/keyboard/focus changes
#     (Titolo Richiesto QLabel selection was triggering spurious highlights).
#     mousePressEvent is now the sole driver of the black border.
#   - FIX: Slider seek works in every interaction (click-on-groove, drag-groove,
#     drag-handle) — added sliderReleased connection as safety net for
#     handle-drag (sliderMoved alone may not fire in some Qt versions),
#     added sliderReleased.emit() in ClickableSlider.mouseReleaseEvent, and
#     _player_seek now accepts any playback state (Playing/Paused/Stopped).
# v4.0:
#   - FIX: Slider click-to-seek now actually seeks (emit sliderMoved after setValue)
#     + drag-on-groove support (mouseMoveEvent) for continuous seek while dragging
#   - FIX: Row highlight border — thicker 3px black border, mousePressEvent override
#     captures clicks on widget cells too (Lock/Found/Player) so highlight follows
#     the click even when the cell widget consumes the mouse event
#   - FIX: Duplicate filename cyan highlighting — simplified condition (only matched
#     rows with real filepath are counted; "mancante" / "-" rows never counted as
#     dupes) AND re-applied after candidate switch (Found dropdown) and lock toggle
#     so the cyan survives the score-colour repaint
#   - FIX: "Mancante" → "-" everywhere (display_label in track_matcher.py)
#   - FIX: BPM / Comment cells now show "-" (was empty string) for unmatched rows
#     and for matched rows with missing metadata, for consistency with other cells
#   - FIX: Found column always shows >=1 when is_matched (uses max(n_above, 1))
#     — a matched row with all candidates below FOUNDDROP_MIN_SCORE=47 still
#     shows "1" because a match exists; sort key aligned with display logic
# v3.9:
#   - FIX: Slider click-to-seek (click anywhere on groove, not just drag)
#   - FIX: Found column always shows >=1 when is_matched (was showing 0 for scores<47%)
#   - FIX: Row border highlight (black border on clicked/active row)
#   - FIX: "Mancante" replaced with "-" everywhere
#   - FIX: Player column shows "-" for unmatched rows
#   - FIX: Duplicate filename highlighting only counts displayed (non-missing) rows
# v3.8:
#   - NEW: Integrated mini audio player column (play/pause + seek slider)
#     - Shared QMediaPlayer + QAudioOutput in MainWindow
#     - PlayerCellWidget per row with play/pause button and seek slider
#     - Auto-stop previous row when playing a different row
#     - Updates correctly when Found candidate is changed
#     - Handles rows without filepath, no match, multiple candidates
#     - Player column sorting disabled
#     - Clean shutdown (no leaks/crashes)
# v3.7:
#   - FIX: 0% score + Found=0 → no matched file shown (treated as missing)
#   - FIX: Copy table now correctly reads Found column (cellWidget handling)
#   - FIX: Default candidate is always highest score (track_matcher v4.5)
#   - FIX: Found column sort by displayed value (n_visible)
#   - FIX: Big centered progress dialog on close-rescan
#   - NEW: Duplicate filenames highlighted in cyan
#   - Removed: launch_silently.vbs
# v3.6:
#   - FIX: _color_single_row() no longer accumulates stylesheet (BUG-004)
#   - FIX: Ctrl+A shortcut removed (conflicted with Spunta Tutti, BUG-007)
#   - FIX: _library_cache_loaded correctly set after save (BUG-006)
#   - FIX: closeEvent waits for running workers (BUG-014)
#   - FIX: get_stats uses scan worker counters (BUG-015)
# v3.3:
#   - FIX: "Salva Mancanti" button now updates on manual checkbox changes
#   - NEW: Lock persistence via audio file composer metadata ([lock] tag)
#     - Writes [lock] to TCOM (MP3), composer (FLAC), ©wrt (M4A), TCOM (WAV)
#     - Composer lock checked BEFORE JSON lock (highest priority in matcher)
#     - JSON title_locks kept as backup
#   - NEW: LibraryTrack.composer field extracted during library scan
# v3.2:
#   - NEW: Dropdown percentuale (0-90%) per filtro "Spunta Tutti"
#   - FIX: "Spunta Tutti" ora rispetta la percentuale selezionata
#   - FIX: "Salva Mancanti" sempre abilitato, disabilitato solo se tutte spuntate
#   - FIX: Lock (lucchetto) = vero 100%: ordinamento, colore verde, display
#   - FIX: Persistenza lock migliorata con salvataggio su chiusura
# v3.1:
#   - FIX: NameError crash durante matching ("name 't' is not defined")
#   - FIX: Rimossi metodi duplicati nella classe ResultsTable
# v3.0:
#   - NEW: Per-row Lock button — blocca/sblocca match direttamente sulla riga
#   - FIX: "Copia Ultima Spuntata" ora copia l'ultima cronologicamente spuntata
#   - NEW: "Crea Crate e Pulisci" button
#   - FIX: "Copia Tabella" ora copia SEMPRE le righe spuntate
# v2.8:
#   - FIX: _set_editable_item crash on populate
# v2.7:
#   - REFACTORING: extracted _setup_ui into focused sub-methods,
#     moved stylesheet to module constant, cleaner organisation
#   - NEW: Strict ordered title validation (via track_matcher v4.0)
# v2.5:
#   - Apertura a schermo intero
#   - Score display: max 1 decimal place
#   - Copy table copies ALL selected rows
#   - Library cache: faster startup
#   - Found dropdown: hide candidates < 47%

import os
import sys
import re
import json
import html as html_module
import pickle
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


from .config import load_config, save_config, get_config_dir
from .i18n import tr, init_language, set_language, get_column_headers, detect_os_language
from .playlist_parser import PlaylistParser, PlaylistTrack
from .library_reader import LibraryReader, normalize_string
from .track_matcher import (
    TrackMatcher, MatchResult, MatchConfidence, CandidateMatch, compute_word_colors,
)
from .crate_writer import (
    CrateWriter, find_serato_subcrates, validate_crate_drive, get_drive_letter,
    get_volume_label, remap_path_to_current_drive,
)
from . import serato_database
from . import branding
from . import ui_theme
from .log_handler import setup_logging, get_log_file_path


# ===================================================================
# Column definitions
# ===================================================================

COL_LOCK = 0
COL_SELECT = 1
COL_SCORE = 2
COL_FOUND = 3
COL_TITOLO_RICHIESTO = 4
COL_FILENAME = 5
COL_ARTISTA_SERATO = 6
COL_SONG_SERATO = 7
COL_GENRE = 8
COL_BPM = 9
COL_COMMENT = 10
COL_PLAYER = 11
COL_HOTCUE = 12
NUM_COLS = 13

# Editing tab columns
E_COL_FILE = 0
E_COL_TITLE = 1
E_COL_ARTIST = 2
E_COL_ALBUM = 3
E_COL_GENRE = 4
E_COL_HOTCUE = 5
E_COL_LOCATION = 6
E_COL_ACTION = 7
E_COL_DELETE = 8
E_NUM_COLS = 9
E_EDITABLE_COLS = (E_COL_TITLE, E_COL_ARTIST, E_COL_ALBUM, E_COL_GENRE)

DJ_SOFTWARE_OPTIONS = [
    ("serato", "Serato DJ Pro"),
    ("rekordbox", "Rekordbox"),
    ("virtualdj", "VirtualDJ"),
    ("traktor", "Traktor Pro 4"),
    ("djay", "djay Pro"),
    ("engine", "Engine DJ"),
    ("mixxx", "Mixxx"),
]

AUTO_SELECT_THRESHOLD = 55
FOUNDDROP_MIN_SCORE = 47

# QTableWidgetItem user role: list of (token, color_hex) for title word highlighting
ROLE_WORD_COLORS = Qt.ItemDataRole.UserRole + 10


# ===================================================================
# Helpers
# ===================================================================

def format_score(score) -> str:
    """Format a score value with at most 1 decimal place."""
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "-"
    return f"{int(s)}%" if s == int(s) else f"{s:.1f}%"


# Module-level flag: set True when dark theme is active.
# Updated by MainWindow._apply_theme() — read by score_to_bg/text_color and row highlighters.
_DARK_THEME_ACTIVE: bool = False


def move_to_recycle_bin(path: str) -> None:
    """Move a file to the OS trash / Recycle Bin (undoable delete).

    Prefers the 'send2trash' package; on Windows it falls back to the native
    SHFileOperation API so no extra dependency is strictly required. Raises on
    failure so callers can report it.
    """
    try:
        from send2trash import send2trash
        send2trash(os.path.abspath(path))
        return
    except ImportError:
        pass

    if sys.platform.startswith("win"):
        import ctypes
        from ctypes import wintypes

        class SHFILEOPSTRUCTW(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND),
                ("wFunc", wintypes.UINT),
                ("pFrom", wintypes.LPCWSTR),
                ("pTo", wintypes.LPCWSTR),
                ("fFlags", ctypes.c_uint16),
                ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", ctypes.c_void_p),
                ("lpszProgressTitle", wintypes.LPCWSTR),
            ]

        FO_DELETE = 3
        FOF_ALLOWUNDO = 0x0040
        FOF_NOCONFIRMATION = 0x0010
        FOF_SILENT = 0x0004
        FOF_NOERRORUI = 0x0400

        op = SHFILEOPSTRUCTW()
        op.wFunc = FO_DELETE
        op.pFrom = os.path.normpath(os.path.abspath(path)) + "\x00\x00"
        op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
        res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
        if res != 0:
            raise OSError(f"SHFileOperation error code {res}")
        return

    raise RuntimeError(
        "Recycle Bin not available: install the 'send2trash' package."
    )


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


def score_to_bg_color(score: int) -> QColor:
    """Map a match score to a background colour — adapts to current theme."""
    score = max(0, min(100, score))
    if _DARK_THEME_ACTIVE:
        if score <= 50:
            return QColor(72, 22, 22)
        t = (score - 50) / 50.0
        return QColor(int(72 - 47 * t), int(22 + 48 * t), int(22 + 13 * t))
    # Light theme
    if score <= 50:
        return QColor(255, 195, 195)
    t = (score - 50) / 50.0
    return QColor(int(255 - 55 * t), int(200 + 45 * t), int(180 + 20 * t))


def score_to_text_color(score: int) -> QColor:
    if _DARK_THEME_ACTIVE:
        if score >= 75:
            return QColor("#5deb9a")
        if score >= 55:
            return QColor("#ffaa40")
        return QColor("#ff7070")
    if score >= 75:
        return QColor("#1e8449")
    if score >= 55:
        return QColor("#d35400")
    return QColor("#c0392b")


# ===================================================================
# Application stylesheets — Light (default) and Dark
# ===================================================================

APP_STYLESHEET = """
QMainWindow { background-color: #f0f2f5; }
QDialog { background-color: #eceef2; }
QGroupBox {
    font-weight: bold; font-size: 11px; color: #4927af;
    border: 1px solid #d0c8e8; border-radius: 8px;
    margin-top: 10px; padding-top: 18px; background-color: #ffffff;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #4927af; }
QLabel { font-size: 11px; color: #2c3e50; }
QLineEdit {
    padding: 6px 10px; border: 1px solid #c0c5cc; border-radius: 5px;
    font-size: 11px; color: #2c3e50; background: white;
}
QLineEdit:focus { border-color: #4927af; border-width: 2px; }
QLineEdit::placeholder { color: #aaa; }
QLineEdit:read-only {
    background: transparent; border: 1px solid transparent;
    selection-background-color: #d4c5f9;
}
QTextEdit {
    border: 2px dashed #c0c5cc; border-radius: 8px; padding: 8px;
    font-size: 11px; color: #2c3e50; background: white;
}
QTextEdit:focus { border-color: #4927af; border-style: solid; }
QTextEdit::placeholder { color: #aaa; }
QPushButton {
    padding: 7px 14px; border: 1px solid #bdc3cb; border-radius: 6px;
    font-size: 11px; font-weight: bold; color: #2c3e50; background: #ffffff;
    min-height: 18px;
}
QPushButton:hover { background: #f0ecfa; border-color: #9b7de0; color: #4927af; }
QPushButton:pressed { background: #e4d9f8; }
QPushButton:disabled { background: #f5f5f5; color: #bbb; border-color: #ddd; }
QPushButton#primaryBtn {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #5a37c9, stop:1 #4927af);
    color: white; border: none; padding: 7px 22px; border-radius: 6px;
}
QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #6b4fd4, stop:1 #5a37c9);
}
QPushButton#primaryBtn:disabled { background: #c4b5e0; color: #fff; }
QPushButton#successBtn {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #27ae60, stop:1 #1e8449);
    color: white; border: none; padding: 7px 22px; border-radius: 6px;
}
QPushButton#successBtn:hover {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #2ecc71, stop:1 #27ae60);
}
QPushButton#successBtn:disabled { background: #a9dfbf; color: #fff; }
QPushButton#copyBtn {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #2e86c1, stop:1 #2471a3);
    color: white; border: none; padding: 7px 16px; border-radius: 6px;
}
QPushButton#copyBtn:hover {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #3498db, stop:1 #2e86c1);
}
QPushButton#copyBtn:disabled { background: #aed6f1; color: #fff; }
QPushButton#importBtn {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #e67e22, stop:1 #d35400);
    color: white; border: none; padding: 7px 16px; border-radius: 6px;
}
QPushButton#importBtn:hover {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #f39c12, stop:1 #e67e22);
}
QPushButton#guideBtn {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #9b59b6, stop:1 #8e44ad);
    color: white; border: none; padding: 7px 16px; border-radius: 6px;
}
QPushButton#guideBtn:hover {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #af7ac5, stop:1 #9b59b6);
}
QPushButton#settingsBtn {
    background: #f5f0fc; color: #4927af; border: 1px solid #c8b8e8;
    padding: 7px 14px; border-radius: 6px; font-weight: bold;
}
QPushButton#settingsBtn:hover { background: #ece4f7; border-color: #9b7de0; }
QPushButton#wizardBtn {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #3498db, stop:1 #2471a3);
    color: white; border: none; padding: 7px 16px; border-radius: 6px; font-weight: bold;
}
QPushButton#wizardBtn:hover {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #5dade2, stop:1 #3498db);
}
QFrame#selectThresholdGroup {
    border: 1px solid #c8b8e8; border-radius: 6px; background: #f5f0fc;
}
QLabel#selectGroupTitle { font-weight: bold; color: #4927af; font-size: 10px; }
QLabel#selectGroupArrow { color: #4927af; font-weight: bold; padding: 0 2px; }
QPushButton#selectAllBtn {
    background: #ece4f7; color: #4927af; border: 1px solid #c8b8e8;
}
QPushButton#selectAllBtn:hover { background: #ddd0f5; border-color: #9b7de0; }
QProgressBar {
    border: 1px solid #bdc3cb; border-radius: 5px; text-align: center;
    height: 20px; max-width: 300px; color: #2c3e50; font-weight: bold; background: #eee;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #4927af, stop:1 #7c5cbf);
    border-radius: 4px;
}
QTableWidget {
    gridline-color: #d8dde5; selection-background-color: #d4c5f9;
    selection-color: #2c3e50; color: #2c3e50; background: white;
    border: 1px solid #c8ced6; border-radius: 5px;
}
QTableWidget::item { padding: 2px 6px; color: #2c3e50; }
QTableWidget::indicator { width: 15px; height: 15px; }
QTableWidget::item:hover { background-color: #ede4f8; }
QHeaderView::section {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #edf0f5, stop:1 #dce0e8);
    color: #2c3e50; padding: 6px; border: 1px solid #c0c5cc;
    font-weight: bold; font-size: 10px;
}
QStatusBar {
    background-color: #e8ebf0; color: #2c3e50; padding: 4px;
    font-size: 10px; border-top: 1px solid #c8ced6;
}
QTabWidget::pane { border: 1px solid #c8ced6; border-radius: 5px; background: #fff; }
QTabBar::tab {
    background: #e8ebf0; color: #2c3e50; padding: 8px 20px;
    border: 1px solid #c8ced6; border-bottom: none;
    border-top-left-radius: 6px; border-top-right-radius: 6px;
    font-weight: bold; font-size: 11px; margin-right: 2px;
}
QTabBar::tab:selected { background: #ffffff; color: #4927af; border-bottom: 2px solid #4927af; }
QTabBar::tab:hover { background: #ece4f7; }
QFrame[frameShape="4"] { color: #c8ced6; max-width: 1px; margin: 0 4px; }
QComboBox {
    padding: 4px 8px; border: 1px solid #c0c5cc; border-radius: 5px;
    font-size: 11px; color: #2c3e50; background: white; min-height: 18px;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox::down-arrow {
    image: none; border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-top: 6px solid #2c3e50; margin-right: 5px;
}
QComboBox QAbstractItemView {
    background: white; color: #2c3e50; border: 1px solid #c0c5cc;
    selection-background-color: #d4c5f9; selection-color: #2c3e50;
}
QMessageBox { background-color: #f8f9fa; }
QMessageBox QLabel { color: #2c3e50; font-size: 12px; }
QMessageBox QPushButton { min-width: 80px; }
QCheckBox { color: #2c3e50; font-size: 11px; }
QCheckBox::indicator {
    width: 15px; height: 15px; border: 1px solid #bdc3cb;
    background: white; border-radius: 3px;
}
QCheckBox::indicator:checked { background: #4927af; border-color: #4927af; }
QSpinBox {
    padding: 4px 8px; border: 1px solid #c0c5cc; border-radius: 5px;
    font-size: 11px; color: #2c3e50; background: white;
}
QSpinBox::up-button, QSpinBox::down-button { background: #f0f2f5; border: none; width: 16px; }
QScrollBar:vertical { background: #f0f2f5; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #c0c5cc; border-radius: 5px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #9b7de0; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #f0f2f5; height: 10px; margin: 0; }
QScrollBar::handle:horizontal { background: #c0c5cc; border-radius: 5px; min-width: 20px; }
QScrollBar::handle:horizontal:hover { background: #9b7de0; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QWidget#headerBar {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #4927af, stop:1 #6b4fd4);
    border-radius: 10px; padding: 4px 8px;
}
QWidget#footerBar {
    background: #ffffff; border: 1px solid #d8dde5; border-radius: 8px;
    padding: 2px 6px;
}
QPushButton#proBtn {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #f1c40f, stop:1 #d4ac0d);
    color: #1a1a1a; border: none; padding: 7px 18px; border-radius: 6px; font-weight: bold;
}
QPushButton#proBtn:hover {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #f7dc6f, stop:1 #f1c40f);
}
QPushButton#linkBtn {
    background: transparent; color: #4927af; border: none;
    padding: 4px 10px; font-weight: bold; text-decoration: underline;
}
QPushButton#linkBtn:hover { color: #6b4fd4; background: #f0ecfa; border-radius: 4px; }
QLabel#headerTitle { color: #ffffff; font-size: 15px; font-weight: bold; }
QLabel#headerTagline { color: rgba(255,255,255,0.95); font-size: 11px; font-style: italic; }
QLabel#versionBadge {
    background: rgba(255,255,255,0.22); color: #ffffff; border-radius: 4px;
    padding: 2px 8px; font-size: 10px; font-weight: bold;
}
QLabel#footerBrand { color: #5a6a7a; font-size: 11px; font-weight: bold; }
QLabel#sectionLabel { color: #4927af; font-size: 11px; font-weight: bold; }
QLabel#statusBadge {
    background: #eef0f4; color: #2c3e50; border: 1px solid #d0c8e8;
    border-radius: 6px; padding: 4px 10px; font-weight: bold; font-size: 11px;
}
QWidget#toolSection { background: #f8f9fb; border-radius: 6px; }
QWidget#fullscreenBar {
    background: #ffffff; border: 1px solid #d8dde5; border-radius: 8px;
    padding: 2px 4px;
}
QLabel#sectionHint { color: #7f8c8d; font-size: 10px; font-style: italic; }
"""

DARK_APP_STYLESHEET = """
QMainWindow, QDialog { background-color: #1a1d23; }
QWidget { background-color: #1a1d23; color: #e0e4ef; }
QGroupBox {
    font-weight: bold; font-size: 11px; color: #9b7de0;
    border: 1px solid #3d4255; border-radius: 8px;
    margin-top: 10px; padding-top: 18px; background-color: #22262e;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #9b7de0; }
QLabel { font-size: 11px; color: #c5cae0; }
QLineEdit {
    padding: 6px 10px; border: 1px solid #4d5268; border-radius: 5px;
    font-size: 11px; color: #e0e4ef; background: #2a2d38;
}
QLineEdit:focus { border-color: #7c5cbf; border-width: 2px; }
QLineEdit::placeholder { color: #666; }
QLineEdit:read-only {
    background: transparent; border: 1px solid transparent;
    selection-background-color: #4a3670;
}
QTextEdit {
    border: 2px dashed #4d5268; border-radius: 8px; padding: 8px;
    font-size: 11px; color: #e0e4ef; background: #2a2d38;
}
QTextEdit:focus { border-color: #7c5cbf; border-style: solid; }
QTextEdit::placeholder { color: #555; }
QPushButton {
    padding: 7px 14px; border: 1px solid #4d5268; border-radius: 6px;
    font-size: 11px; font-weight: bold; color: #e0e4ef; background: #2e3240;
    min-height: 18px;
}
QPushButton:hover { background: #393d4f; border-color: #7c5cbf; color: #c5a8ff; }
QPushButton:pressed { background: #252837; }
QPushButton:disabled { background: #22252f; color: #555; border-color: #363948; }
QPushButton#primaryBtn {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #6b4fd4, stop:1 #5a3fbf);
    color: white; border: none; padding: 7px 22px; border-radius: 6px;
}
QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #7c60e0, stop:1 #6b4fd4);
}
QPushButton#primaryBtn:disabled { background: #3d3060; color: #9988cc; }
QPushButton#successBtn {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #22854b, stop:1 #1a6b3c);
    color: white; border: none; padding: 7px 22px; border-radius: 6px;
}
QPushButton#successBtn:hover {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #27ae60, stop:1 #22854b);
}
QPushButton#successBtn:disabled { background: #1a3325; color: #669977; }
QPushButton#copyBtn {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #1e5d8f, stop:1 #1a4d78);
    color: white; border: none; padding: 7px 16px; border-radius: 6px;
}
QPushButton#copyBtn:hover {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #2471a3, stop:1 #1e5d8f);
}
QPushButton#copyBtn:disabled { background: #162a3d; color: #558ab5; }
QPushButton#importBtn {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #a6591a, stop:1 #8b4a15);
    color: white; border: none; padding: 7px 16px; border-radius: 6px;
}
QPushButton#importBtn:hover {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #c07022, stop:1 #a6591a);
}
QPushButton#guideBtn {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #6b3690, stop:1 #5a2d7a);
    color: white; border: none; padding: 7px 16px; border-radius: 6px;
}
QPushButton#guideBtn:hover {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #7d42a8, stop:1 #6b3690);
}
QPushButton#settingsBtn {
    background: #2a2d3e; color: #9b7de0; border: 1px solid #4a3670;
    padding: 7px 14px; border-radius: 6px; font-weight: bold;
}
QPushButton#settingsBtn:hover { background: #333650; border-color: #7c5cbf; }
QPushButton#wizardBtn {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #2e86c1, stop:1 #1f618d);
    color: white; border: none; padding: 7px 16px; border-radius: 6px; font-weight: bold;
}
QPushButton#wizardBtn:hover {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #3498db, stop:1 #2e86c1);
}
QFrame#selectThresholdGroup {
    border: 1px solid #4a3670; border-radius: 6px; background: #2a2540;
}
QLabel#selectGroupTitle { font-weight: bold; color: #b8a0e8; font-size: 10px; }
QLabel#selectGroupArrow { color: #b8a0e8; font-weight: bold; padding: 0 2px; }
QPushButton#selectAllBtn {
    background: #3d2e6e; color: #d4c5f9; border: 1px solid #5a3fbf;
}
QPushButton#selectAllBtn:hover { background: #4a3670; border-color: #7c5cbf; }
QProgressBar {
    border: 1px solid #4d5268; border-radius: 5px; text-align: center;
    height: 20px; max-width: 300px; color: #e0e4ef; font-weight: bold; background: #22262e;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #5a3fbf, stop:1 #7c5cbf);
    border-radius: 4px;
}
QTableWidget {
    gridline-color: #3d4255; selection-background-color: #3d2e6e;
    selection-color: #e0e4ef; color: #e0e4ef; background: #22262e;
    border: 1px solid #3d4255; border-radius: 5px;
}
QTableWidget::item { padding: 2px 6px; color: #e0e4ef; }
QTableWidget::indicator { width: 15px; height: 15px; }
QTableWidget::item:hover { background-color: #2e3265; }
QHeaderView::section {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #2e3240, stop:1 #252932);
    color: #c5cae0; padding: 6px; border: 1px solid #3d4255;
    font-weight: bold; font-size: 10px;
}
QStatusBar {
    background-color: #252932; color: #a0a8b8; padding: 4px;
    font-size: 10px; border-top: 1px solid #3d4255;
}
QTabWidget::pane { border: 1px solid #3d4255; border-radius: 5px; background: #22262e; }
QTabBar::tab {
    background: #252932; color: #a0a8b8; padding: 8px 20px;
    border: 1px solid #3d4255; border-bottom: none;
    border-top-left-radius: 6px; border-top-right-radius: 6px;
    font-weight: bold; font-size: 11px; margin-right: 2px;
}
QTabBar::tab:selected { background: #22262e; color: #9b7de0; border-bottom: 2px solid #7c5cbf; }
QTabBar::tab:hover { background: #2e3240; }
QFrame[frameShape="4"] { color: #3d4255; max-width: 1px; margin: 0 4px; }
QComboBox {
    padding: 4px 8px; border: 1px solid #4d5268; border-radius: 5px;
    font-size: 11px; color: #e0e4ef; background: #2a2d38; min-height: 18px;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox::down-arrow {
    image: none; border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-top: 6px solid #c5cae0; margin-right: 5px;
}
QComboBox QAbstractItemView {
    background: #2a2d38; color: #e0e4ef; border: 1px solid #4d5268;
    selection-background-color: #3d2e6e; selection-color: #e0e4ef;
}
QMessageBox { background-color: #22262e; }
QMessageBox QLabel { color: #e0e4ef; font-size: 12px; }
QMessageBox QPushButton { min-width: 80px; }
QCheckBox { color: #c5cae0; font-size: 11px; }
QCheckBox::indicator {
    width: 15px; height: 15px; border: 1px solid #4d5268;
    background: #2a2d38; border-radius: 3px;
}
QCheckBox::indicator:checked { background: #5a3fbf; border-color: #7c5cbf; }
QSpinBox {
    padding: 4px 8px; border: 1px solid #4d5268; border-radius: 5px;
    font-size: 11px; color: #e0e4ef; background: #2a2d38;
}
QSpinBox::up-button, QSpinBox::down-button { background: #2e3240; border: none; width: 16px; }
QScrollBar:vertical { background: #1e2128; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #4d5268; border-radius: 5px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #7c5cbf; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #1e2128; height: 10px; margin: 0; }
QScrollBar::handle:horizontal { background: #4d5268; border-radius: 5px; min-width: 20px; }
QScrollBar::handle:horizontal:hover { background: #7c5cbf; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QWidget#headerBar {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #3d2e6e, stop:1 #5a3fbf);
    border-radius: 10px; padding: 4px 8px;
}
QWidget#footerBar {
    background: #22262e; border: 1px solid #3d4255; border-radius: 8px;
    padding: 2px 6px;
}
QPushButton#proBtn {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #c9a227, stop:1 #a68519);
    color: #1a1a1a; border: none; padding: 7px 18px; border-radius: 6px; font-weight: bold;
}
QPushButton#proBtn:hover {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #dbb42e, stop:1 #c9a227);
}
QPushButton#linkBtn {
    background: transparent; color: #9b7de0; border: none;
    padding: 4px 10px; font-weight: bold;
}
QPushButton#linkBtn:hover { color: #c5a8ff; background: #2a2d3e; border-radius: 4px; }
QLabel#headerTitle { color: #ffffff; font-size: 15px; font-weight: bold; }
QLabel#headerTagline { color: rgba(255,255,255,0.95); font-size: 11px; font-style: italic; }
QLabel#versionBadge {
    background: rgba(255,255,255,0.15); color: #e0e4ef; border-radius: 4px;
    padding: 2px 8px; font-size: 10px; font-weight: bold;
}
QLabel#footerBrand { color: #b0b8d0; font-size: 11px; font-weight: bold; }
QLabel#sectionLabel { color: #9b7de0; font-size: 11px; font-weight: bold; }
QLabel#statusBadge {
    background: #2a2d38; color: #e0e4ef; border: 1px solid #4d5268;
    border-radius: 6px; padding: 4px 10px; font-weight: bold; font-size: 11px;
}
QWidget#toolSection { background: #252830; border-radius: 6px; }
QWidget#fullscreenBar {
    background: #22262e; border: 1px solid #3d4255; border-radius: 8px;
    padding: 2px 4px;
}
QLabel#sectionHint { color: #888ea8; font-size: 10px; font-style: italic; }
"""


def _make_stylesheet(theme: str, font_size: int = 11) -> str:
    """Build the application stylesheet for the given theme and font size."""
    base = DARK_APP_STYLESHEET if theme == "dark" else APP_STYLESHEET
    if font_size != 11:
        base = base.replace("font-size: 11px", f"font-size: {font_size}px")
        base = base.replace("font-size: 12px", f"font-size: {font_size + 1}px")
        base = base.replace("font-size: 10px", f"font-size: {max(8, font_size - 1)}px")
    if font_size >= 17:
        pad_y, pad_x, min_h = 10, 20, 30
        base += (
            "\nQTableWidget::item { font-weight: bold; }"
            "\nQLineEdit { font-weight: bold; }"
            "\nQComboBox { font-weight: bold; }"
            f"\nQPushButton {{ padding: {pad_y}px {pad_x}px; min-height: {min_h}px; }}"
            f"\nQPushButton#primaryBtn {{ padding: {pad_y}px {pad_x + 4}px; }}"
            f"\nQPushButton#successBtn {{ padding: {pad_y}px {pad_x + 4}px; }}"
            f"\nQPushButton#copyBtn {{ padding: {pad_y}px {pad_x}px; }}"
            f"\nQPushButton#importBtn {{ padding: {pad_y}px {pad_x}px; }}"
            f"\nQPushButton#guideBtn {{ padding: {pad_y}px {pad_x}px; }}"
            f"\nQPushButton#settingsBtn {{ padding: {pad_y}px {pad_x}px; }}"
            f"\nQPushButton#wizardBtn {{ padding: {pad_y}px {pad_x}px; }}"
            f"\nQPushButton#proBtn {{ padding: {pad_y}px {pad_x}px; }}"
            f"\nQPushButton#selectAllBtn {{ padding: {pad_y}px {pad_x}px; }}"
        )
    elif font_size >= 13:
        pad_y, pad_x, min_h = 7, 14, 24
        base += (
            f"\nQPushButton {{ padding: {pad_y}px {pad_x}px; min-height: {min_h}px; }}"
            f"\nQPushButton#primaryBtn {{ padding: {pad_y}px {pad_x + 2}px; }}"
            f"\nQPushButton#successBtn {{ padding: {pad_y}px {pad_x + 2}px; }}"
            f"\nQPushButton#copyBtn {{ padding: {pad_y}px {pad_x}px; }}"
            f"\nQPushButton#importBtn {{ padding: {pad_y}px {pad_x}px; }}"
            f"\nQPushButton#guideBtn {{ padding: {pad_y}px {pad_x}px; }}"
            f"\nQPushButton#settingsBtn {{ padding: {pad_y}px {pad_x}px; }}"
            f"\nQPushButton#wizardBtn {{ padding: {pad_y}px {pad_x}px; }}"
            f"\nQPushButton#proBtn {{ padding: {pad_y}px {pad_x}px; }}"
            f"\nQPushButton#selectAllBtn {{ padding: {pad_y}px {pad_x}px; }}"
        )
    elif font_size <= 10:
        base += "\nQPushButton { padding: 4px 8px; min-height: 18px; }"
    return base


def set_button_alt(btn: QPushButton, tooltip_key: str, **fmt) -> None:
    """Set tooltip and accessibility description (alt text) for a button."""
    desc = tr(tooltip_key, **fmt) if fmt else tr(tooltip_key)
    btn.setToolTip(desc)
    btn.setAccessibleDescription(desc)
    if btn.text():
        btn.setAccessibleName(btn.text())


def _vline() -> QFrame:
    """Thin vertical separator for toolbar rows."""
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.VLine)
    sep.setStyleSheet("color: #bdc3c7;")
    return sep


def _link_button(text: str, url: str, tooltip_key: str = "") -> QPushButton:
    """Flat link-style button that opens *url* in the default browser."""
    btn = QPushButton(text)
    btn.setObjectName("linkBtn")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if tooltip_key:
        set_button_alt(btn, tooltip_key)
    btn.clicked.connect(lambda: branding.open_url(url))
    return btn


def _apply_button_font(btn: QPushButton, font_size: int, bold: bool = False) -> None:
    """Apply the user's chosen font size to a button — never shrink below it.

    Inline font-size overrides the global QPushButton rule so the setting
    actually takes effect on toolbar buttons. SizePolicy.Minimum lets each
    button grow to fit its label instead of clipping or shrinking text.
    """
    if not btn:
        return
    weight = " font-weight: bold;" if bold else ""
    btn.setStyleSheet(f"font-size: {font_size}px;{weight}")
    btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    btn.setMinimumHeight(font_size + 14)
    btn.updateGeometry()


def _fit_button_text(btn: QPushButton, font_size: int, bold: bool = False) -> None:
    """Backward-compatible alias — applies font without shrinking."""
    _apply_button_font(btn, font_size, bold=bold)


# AI prompt for cleaning playlists
AI_CLEANUP_PROMPT = """You are a playlist formatting assistant for a professional DJ using Serato DJ software.

Your ONLY task is to clean up and standardize a raw playlist into the EXACT format required:

OUTPUT FORMAT RULES:
- One track per line
- Separator: " - " (space, hyphen, space)
- Order: ARTIST first, then TITLE
- If only a title is known, output just the title (no separator)
- Capitalize properly (Title Case)
- Remove ALL of the following: track numbers, timestamps, URLs, [brackets], version tags like (remix), (radio edit), (extended), (remaster), (clean), (explicit), (live), (acoustic), (instrumental), (original mix), (club mix), etc.
- Remove "feat.", "ft.", "vs." indicators - keep only the main artist and title
- Remove duplicate entries
- Do NOT add any numbering, headers, or extra text
- Do NOT include any explanations or commentary in the output

EXAMPLE INPUT:
1. david guetta feat. sia - titanium (radio edit)
https://youtu.be/JRfuAukYTKg
Calvin Harris - Summer (Extended Mix) [Remastered 2019]
3) AVICII   wake me up

EXAMPLE OUTPUT:
David Guetta - Titanium
Calvin Harris - Summer
Avicii - Wake Me Up

Now format this playlist:"""


# ===================================================================
# Worker threads
# ===================================================================

class WorkerThread(QThread):
    progress = Signal(int, int, str)
    finished = Signal(object)
    error = Signal(str)


class LibraryScanWorker(WorkerThread):
    def __init__(self, folder: str, config: dict):
        super().__init__()
        self.folder = folder
        self.config = config

    def run(self):
        try:
            reader = LibraryReader(self.config)
            tracks = reader.scan_folder(
                self.folder,
                progress_callback=lambda c, t: self.progress.emit(c, t, f"Scansione: {c}/{t}..."),
            )
            self.progress.emit(0, 0, f"Indicizzazione completata: {len(tracks)} tracce")
            self.finished.emit(tracks)
        except Exception as e:
            self.error.emit(f"Errore scansione: {str(e)}")


class MatchWorker(WorkerThread):
    def __init__(self, playlist_tracks, library_tracks, thresholds=None,
                 title_locks=None, bpm_penalty_enabled=False, bpm_reference=0):
        super().__init__()
        self.playlist_tracks = playlist_tracks
        self.library_tracks = library_tracks
        self.thresholds = thresholds
        self.title_locks = title_locks or {}
        self.bpm_penalty_enabled = bpm_penalty_enabled
        self.bpm_reference = bpm_reference

    def run(self):
        try:
            matcher = TrackMatcher(self.library_tracks, self.thresholds,
                                   title_locks=self.title_locks,
                                   bpm_penalty_enabled=self.bpm_penalty_enabled,
                                   bpm_reference=self.bpm_reference)
            results = matcher.match_playlist(
                self.playlist_tracks,
                progress_callback=lambda c, t: self.progress.emit(c, t, f"Matching: {c}/{t} brani..."),
            )
            matched = sum(1 for r in results if r.is_effectively_matched)
            self.progress.emit(0, 0, f"Matching completato: {matched}/{len(results)}")
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(f"Errore matching: {str(e)}")


class ImportWorker(WorkerThread):
    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            from .playlist_importer import import_playlist_from_url
            source, tracks = import_playlist_from_url(self.url)
            self.progress.emit(0, len(tracks), f"Importazione completata: {len(tracks)} brani da {source}")
            self.finished.emit((source, tracks))
        except Exception as e:
            self.error.emit(str(e))


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

    def __init__(self, row: int, parent=None):
        super().__init__(parent)
        self.row = row
        self._is_playing = False
        self._has_file = False
        self._track_name = ""

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
        """Update slider from QMediaPlayer position."""
        if duration_ms > 0:
            self.slider.blockSignals(True)
            self.slider.setRange(0, duration_ms)
            self.slider.setValue(position_ms)
            self.slider.blockSignals(False)
        else:
            self.slider.blockSignals(True)
            self.slider.setValue(0)
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
                f"color: {'#9b7de0' if _DARK_THEME_ACTIVE else '#4927af'}; "
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
            item.setForeground(QColor("#c5cae0" if _DARK_THEME_ACTIVE else "#95a5a6"))
            item.setFont(self._cell_font())
            self.setItem(row, COL_FOUND, item)
        else:
            # No match at all — show "0"
            item = QTableWidgetItem("0")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(QColor("#ff7070" if _DARK_THEME_ACTIVE else "#c0392b"))
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
            bg = QColor(72, 22, 22) if _DARK_THEME_ACTIVE else QColor(255, 195, 195)
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
            player_widget = PlayerCellWidget(row)
            player_widget.set_has_file(True)
            track_name = result.library_track.display_name or os.path.basename(filepath)
            player_widget.set_track_name(track_name)
            # Connect signals to main window player controller
            mw = self._main_window_ref
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
        cyan = QColor(20, 55, 72) if _DARK_THEME_ACTIVE else QColor(179, 229, 252)
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

class FormatGuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("guide_title"))
        self.setMinimumSize(650, 620)
        self.resize(700, 650)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel(tr("guide_heading"))
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #4927af;")
        layout.addWidget(title)

        guide = QLabel(tr("guide_body_detailed"))
        guide.setWordWrap(True)
        guide.setTextFormat(Qt.TextFormat.RichText)
        guide.setStyleSheet(
            "background: #f0ecfa; border: 1px solid #c8b8e8; "
            "border-radius: 6px; padding: 12px; font-size: 11px;"
        )
        layout.addWidget(guide)

        prompt_title = QLabel(tr("guide_prompt_title"))
        prompt_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        prompt_title.setStyleSheet("color: #2c3e50; margin-top: 6px;")
        layout.addWidget(prompt_title)

        desc = QLabel(tr("guide_prompt_desc"))
        desc.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlainText(AI_CLEANUP_PROMPT)
        self.prompt_edit.setFont(QFont("Consolas", 9))
        self.prompt_edit.setReadOnly(True)
        self.prompt_edit.setStyleSheet(
            "border: 1px solid #c8ced6; border-radius: 4px; padding: 8px; "
            "background: #fafafa; font-size: 10px;"
        )
        layout.addWidget(self.prompt_edit, stretch=1)

        btn_row = QHBoxLayout()
        btn_copy = QPushButton(tr("btn_copy_prompt"))
        set_button_alt(btn_copy, "btn_copy_prompt_tt")
        btn_copy.setObjectName("primaryBtn")
        btn_copy.clicked.connect(self._copy_prompt)
        btn_row.addWidget(btn_copy)
        btn_close = QPushButton(tr("btn_close"))
        set_button_alt(btn_close, "btn_close_tt")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _copy_prompt(self):
        QApplication.clipboard().setText(AI_CLEANUP_PROMPT)
        QMessageBox.information(
            self, tr("title_saved"),
            tr("msg_prompt_copied"),
        )


# ===================================================================
# Clean Library search dialog
# ===================================================================

class CleanLibraryDialog(QDialog):
    """Ask for a search word and whether to auto-detect mojibake problems.

    Exposes ``search_word`` (str) and ``detect_mojibake`` (bool) after accept.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("clean_lib_dialog_title"))
        self.setMinimumWidth(480)
        self.search_word = ""
        self.detect_mojibake = True

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel(tr("clean_lib_search_label")))
        self._input = QLineEdit()
        self._input.setPlaceholderText(tr("clean_lib_search_ph"))
        self._input.returnPressed.connect(self.accept)
        layout.addWidget(self._input)

        self._chk_moji = QCheckBox(tr("clean_lib_detect_moji"))
        self._chk_moji.setChecked(True)
        layout.addWidget(self._chk_moji)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton(tr("btn_close"))
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_ok = QPushButton(tr("clean_lib_search_btn"))
        btn_ok.setObjectName("primaryBtn")
        btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

        self._input.setFocus()

    def accept(self):
        self.search_word = self._input.text().strip()
        self.detect_mojibake = self._chk_moji.isChecked()
        super().accept()


class ReplaceDialog(QDialog):
    """Find/replace across the editable fields of the Editing table.

    ``find_text`` is pre-filled with the last searched word; ``replace_text``
    may be left empty to simply delete every occurrence.
    """

    def __init__(self, parent=None, find_default=""):
        super().__init__(parent)
        self.setWindowTitle(tr("replace_dialog_title"))
        self.setMinimumWidth(460)
        self.find_text = ""
        self.replace_text = ""

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        layout.addWidget(QLabel(tr("replace_find_label")))
        self._find = QLineEdit(find_default)
        layout.addWidget(self._find)

        layout.addWidget(QLabel(tr("replace_with_label")))
        self._replace = QLineEdit()
        self._replace.returnPressed.connect(self.accept)
        layout.addWidget(self._replace)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton(tr("btn_close"))
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_ok = QPushButton(tr("replace_btn_ok"))
        btn_ok.setObjectName("primaryBtn")
        btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def accept(self):
        self.find_text = self._find.text()
        self.replace_text = self._replace.text()
        super().accept()


# ===================================================================
# Algorithm Documentation Dialog
# ===================================================================

class AlgorithmDialog(QDialog):
    """Renders localized docs/algorithm/<lang>.md (how the % score is computed)."""

    def __init__(self, parent=None, theme: str = "light"):
        super().__init__(parent)
        self.setWindowTitle(tr("algo_doc_title"))
        self.setMinimumSize(720, 640)
        self.resize(840, 720)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(True)
        layout.addWidget(self._browser, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton(tr("btn_close"))
        set_button_alt(btn_close, "btn_close_tt")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        self._load_doc()
        self._apply_theme(theme)

    def _load_doc(self):
        from serato_automation.doc_paths import resolve_localized_doc
        doc_path = resolve_localized_doc("algorithm")
        try:
            with open(doc_path, "r", encoding="utf-8") as f:
                content = f.read()
            if hasattr(self._browser, "setMarkdown"):
                self._browser.setMarkdown(content)
            else:
                self._browser.setPlainText(content)
        except OSError:
            self._browser.setPlainText(tr("algo_doc_not_found", path=doc_path))

    def _apply_theme(self, theme: str):
        dark = theme == "dark"
        ui_theme.apply_themed_dialog(self, dark)
        p = ui_theme.palette(dark)
        self._browser.document().setDefaultStyleSheet(f"""
            body, p, li {{ font-family: Georgia, 'Times New Roman', serif;
                font-size: 13px; line-height: 1.55; color: {p['text']}; }}
            h1, h2, h3 {{ font-family: 'Segoe UI', sans-serif; color: {p['accent']}; }}
            strong, b {{ font-family: 'Segoe UI', sans-serif; color: {p['accent']}; }}
            a {{ color: {p['accent']}; }}
            table {{ font-family: 'Segoe UI', sans-serif; font-size: 12px; }}
            th, td {{ border: 1px solid {p['border']}; padding: 4px 8px; }}
        """)
        self._browser.setStyleSheet(
            f"border: 1px solid {p['border']}; border-radius: 6px; padding: 12px;"
            f" background: {p['panel_alt']};"
        )


# ===================================================================
# Import URL Dialog
# ===================================================================

class ImportUrlDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("import_title"))
        self.setMinimumSize(550, 200)
        self.resize(600, 220)
        self.imported_tracks: List[str] = []
        self._source = ""
        self._worker = None

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel(tr("import_heading"))
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #4927af;")
        layout.addWidget(title)

        desc = QLabel(tr("import_desc"))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        layout.addWidget(desc)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(tr("import_url_ph"))
        layout.addWidget(self.url_input)

        btn_row = QHBoxLayout()
        self.btn_import = QPushButton(tr("btn_import"))
        set_button_alt(self.btn_import, "btn_import_tt")
        self.btn_import.setObjectName("primaryBtn")
        self.btn_import.clicked.connect(self._start_import)
        btn_row.addWidget(self.btn_import)
        self.btn_cancel = QPushButton(tr("btn_cancel"))
        set_button_alt(self.btn_cancel, "btn_cancel_tt")
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        layout.addWidget(self.status_label)

    def _start_import(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, tr("title_attention"), tr("msg_enter_url"))
            return
        if not any(
            x in url for x in
            ("youtube.com", "youtu.be", "spotify.com", "music.amazon.")
        ) and not ("amazon." in url and "/music/" in url):
            QMessageBox.warning(self, tr("title_attention"), tr("msg_unsupported_url"))
            return

        self.btn_import.setEnabled(False)
        self.status_label.setText(tr("import_in_progress"))
        self.status_label.setStyleSheet("color: #4927af; font-size: 10px;")

        self._worker = ImportWorker(url)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, current, total, message):
        self.status_label.setText(message)

    def _on_finished(self, result):
        self._source, self.imported_tracks = result
        self.status_label.setText(tr("import_done", count=len(self.imported_tracks), source=self._source))
        self.status_label.setStyleSheet("color: #1e8449; font-size: 10px; font-weight: bold;")
        self.btn_import.setEnabled(True)
        self.accept()

    def _on_error(self, message):
        self.status_label.setText(tr("import_error_status"))
        self.status_label.setStyleSheet("color: #c0392b; font-size: 10px;")
        self.btn_import.setEnabled(True)
        QMessageBox.critical(self, tr("title_import_error"), message)

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait(2000)
        event.accept()


# ===================================================================
# Settings Dialog
# ===================================================================

class SettingsDialog(QDialog):
    """Application settings organised in thematic tabs."""

    APP_VERSION = branding.APP_VERSION

    COLUMN_KEYS = [
        "lock", "select", "score", "found", "titolo_richiesto",
        "filename", "artista_serato", "song_serato", "genre", "bpm", "comment", "player",
    ]
    COLUMN_LABELS = {
        "artista_serato": "col_lbl_artista_serato",
        "song_serato": "col_lbl_song_serato",
        "genre": "col_lbl_genre",
        "bpm": "col_lbl_bpm",
        "comment": "col_lbl_comment",
        "player": "col_lbl_player",
        "hotcue": "col_lbl_hotcue",
    }
    ALWAYS_VISIBLE = frozenset({"lock", "select", "score", "found", "titolo_richiesto", "filename"})
    DEFAULT_HIDDEN = frozenset({"hotcue"})
    FONT_SIZE_KEYS = [
        ("font_small", 10), ("font_normal", 11), ("font_large", 13),
        ("font_xlarge", 15), ("font_giant", 17),
    ]

    @classmethod
    def _language_options(cls):
        return [
            ("auto", tr("lang_auto")),
            ("en",   "English"),
            ("it",   "Italiano"),
            ("es",   "Español"),
            ("fr",   "Français"),
            ("de",   "Deutsch"),
            ("ru",   "Русский"),
            ("zh",   "中文"),
        ]

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("settings_title"))
        self.setMinimumSize(540, 460)
        saved_size = config.get("settings_dialog_size") or {}
        self.resize(
            int(saved_size.get("width", 560)),
            int(saved_size.get("height", 500)),
        )
        self._cfg = dict(config)
        self._applied = None
        self._size_save_timer = QTimer(self)
        self._size_save_timer.setSingleShot(True)
        self._size_save_timer.timeout.connect(self._persist_dialog_size)

        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        self._tabs.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        root.addWidget(self._tabs, stretch=1)

        self._tabs.addTab(self._build_tab_aspetto(),       tr("tab_appearance"))
        self._tabs.addTab(self._build_tab_matching(),      tr("tab_matching"))
        self._tabs.addTab(self._build_tab_lingua(),        tr("tab_language"))
        self._tabs.addTab(self._build_tab_updates(),       tr("tab_updates"))
        self._tabs.addTab(self._build_tab_comportamento(), tr("tab_behavior"))
        self._tabs.addTab(self._build_tab_account(),       tr("tab_account"))

        footer = QWidget()
        foot = QHBoxLayout(footer)
        foot.setContentsMargins(16, 10, 16, 10)
        self._btn_reset = QPushButton(tr("btn_reset_defaults"))
        set_button_alt(self._btn_reset, "btn_reset_defaults_tt")
        self._btn_reset.clicked.connect(self._reset_defaults)
        foot.addWidget(self._btn_reset)
        foot.addStretch()
        self._btn_cancel = QPushButton(tr("btn_cancel"))
        set_button_alt(self._btn_cancel, "btn_cancel_tt")
        self._btn_cancel.clicked.connect(self.reject)
        foot.addWidget(self._btn_cancel)
        self._btn_ok = QPushButton(tr("btn_apply"))
        set_button_alt(self._btn_ok, "btn_apply_tt")
        self._btn_ok.setObjectName("primaryBtn")
        self._btn_ok.clicked.connect(self._on_apply)
        foot.addWidget(self._btn_ok)
        root.addWidget(footer)

    # ------------------------------------------------------------------ Aspetto
    def _build_tab_aspetto(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(12)

        # Theme
        theme_grp = QGroupBox(tr("grp_theme"))
        tg = QHBoxLayout(theme_grp)
        tg.addWidget(QLabel(tr("lbl_theme")))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems([tr("theme_light"), tr("theme_dark")])
        self.theme_combo.setCurrentIndex(1 if self._cfg.get("theme") == "dark" else 0)
        self.theme_combo.setMaximumWidth(140)
        tg.addWidget(self.theme_combo)
        tg.addStretch()
        lay.addWidget(theme_grp)

        # Font size
        font_grp = QGroupBox(tr("grp_font_size"))
        fg = QHBoxLayout(font_grp)
        fg.addWidget(QLabel(tr("lbl_font_size")))
        self.font_combo = QComboBox()
        for label_key, _ in self.FONT_SIZE_KEYS:
            self.font_combo.addItem(tr(label_key))
        cur_size = self._cfg.get("font_size", 11)
        idx = next((i for i, (_, s) in enumerate(self.FONT_SIZE_KEYS) if s == cur_size), 1)
        self.font_combo.setCurrentIndex(idx)
        self.font_combo.setMaximumWidth(170)
        fg.addWidget(self.font_combo)
        fg.addStretch()
        fn = QLabel(tr("font_note"))
        fn.setStyleSheet("font-size: 10px; color: #7f8c8d;")
        lay.addWidget(font_grp)
        lay.addWidget(fn)

        # Column visibility
        col_grp = QGroupBox(tr("grp_columns"))
        col_v = QVBoxLayout(col_grp)
        col_v.setSpacing(8)
        col_grid = QGridLayout()
        col_grid.setSpacing(8)
        vis = self._cfg.get("visible_columns", {})
        self._col_checks = {}
        for key in self.ALWAYS_VISIBLE:
            self._col_checks[key] = None
        configurable = [k for k in self.COLUMN_LABELS if k not in self.ALWAYS_VISIBLE]
        for i, key in enumerate(configurable):
            cb = QCheckBox(tr(self.COLUMN_LABELS[key]))
            cb.setChecked(vis.get(key, key not in self.DEFAULT_HIDDEN))
            self._col_checks[key] = cb
            col_grid.addWidget(cb, i // 2, i % 2)
        col_v.addLayout(col_grid)
        lay.addWidget(col_grp)

        # Horizontal scroll lock
        scroll_grp = QGroupBox(tr("grp_table_display"))
        sg = QVBoxLayout(scroll_grp)
        self.fit_columns_check = QCheckBox(tr("table_fit_columns_check"))
        self.fit_columns_check.setChecked(self._cfg.get("table_fit_columns", False))
        self.fit_columns_check.setToolTip(tr("table_fit_columns_tt"))
        sg.addWidget(self.fit_columns_check)
        lay.addWidget(scroll_grp)

        lay.addStretch()
        return w

    # ------------------------------------------------------------------ Matching
    def _build_tab_matching(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(12)

        bpm_grp = QGroupBox(tr("grp_bpm_penalty"))
        bpm_v = QVBoxLayout(bpm_grp)
        self.bpm_check = QCheckBox(tr("bpm_check"))
        self.bpm_check.setChecked(self._cfg.get("bpm_penalty_enabled", False))
        self.bpm_check.setToolTip(tr("bpm_check_tt"))
        bpm_v.addWidget(self.bpm_check)
        bpm_ref_row = QHBoxLayout()
        bpm_ref_row.addWidget(QLabel(tr("lbl_bpm_ref")))
        self.bpm_spin = QSpinBox()
        self.bpm_spin.setRange(0, 300)
        self.bpm_spin.setValue(int(self._cfg.get("bpm_reference", 0)))
        self.bpm_spin.setSpecialValueText(tr("bpm_not_set"))
        self.bpm_spin.setMaximumWidth(130)
        self.bpm_spin.setEnabled(self.bpm_check.isChecked())
        bpm_ref_row.addWidget(self.bpm_spin)
        bpm_ref_row.addWidget(QLabel(tr("col_bpm")))
        bpm_ref_row.addStretch()
        bpm_v.addLayout(bpm_ref_row)
        note = QLabel(tr("bpm_example"))
        note.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        bpm_v.addWidget(note)
        self.bpm_check.toggled.connect(self.bpm_spin.setEnabled)
        lay.addWidget(bpm_grp)
        lay.addStretch()
        return w

    # ------------------------------------------------------------------ Lingua
    def _build_tab_lingua(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(12)

        lang_grp = QGroupBox(tr("grp_ui_language"))
        lg = QVBoxLayout(lang_grp)
        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel(tr("lbl_language")))
        self.lang_combo = QComboBox()
        languages = self._language_options()
        for code, label in languages:
            self.lang_combo.addItem(label, userData=code)
        cur_lang = self._cfg.get("language", "auto")
        idx = next((i for i, (c, _) in enumerate(languages) if c == cur_lang), 0)
        self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.setMaximumWidth(220)
        lang_row.addWidget(self.lang_combo)
        lang_row.addStretch()
        lg.addLayout(lang_row)

        detected = detect_os_language()
        lang_names = {c: n for c, n in languages if c != "auto"}
        detected_name = lang_names.get(detected, "English")
        info = QLabel(tr("lang_info", detected=detected_name))
        info.setWordWrap(True)
        info.setStyleSheet(
            "background: #f5f0fc; border: 1px solid #d4c5f9; border-radius: 5px; "
            "padding: 10px; font-size: 10px; color: #555;"
        )
        lg.addWidget(info)
        lay.addWidget(lang_grp)
        lay.addStretch()
        return w

    # ------------------------------------------------------------------ Aggiornamenti
    def _build_tab_updates(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(12)

        ver_grp = QGroupBox(tr("grp_version"))
        vg = QVBoxLayout(ver_grp)
        ver_lbl = QLabel(tr("lbl_version", version=self.APP_VERSION))
        ver_lbl.setTextFormat(Qt.TextFormat.RichText)
        vg.addWidget(ver_lbl)
        ver_note = QLabel(tr("version_note"))
        ver_note.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        vg.addWidget(ver_note)
        lay.addWidget(ver_grp)

        upd_grp = QGroupBox(tr("grp_auto_update"))
        ug = QVBoxLayout(upd_grp)
        self.auto_update_check = QCheckBox(tr("auto_update_check"))
        self.auto_update_check.setChecked(self._cfg.get("auto_update", False))
        ug.addWidget(self.auto_update_check)
        upd_note = QLabel(tr("auto_update_note"))
        upd_note.setWordWrap(True)
        upd_note.setStyleSheet(
            "background: #fef9e7; border: 1px solid #f9e79f; border-radius: 5px; "
            "padding: 9px; font-size: 10px; color: #555;"
        )
        ug.addWidget(upd_note)
        lay.addWidget(upd_grp)
        lay.addStretch()
        return w

    # ------------------------------------------------------------------ Comportamento
    def _build_tab_comportamento(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(12)

        close_grp = QGroupBox(tr("grp_close_dialog"))
        cg = QVBoxLayout(close_grp)
        desc = QLabel(tr("close_dialog_desc"))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #555; font-size: 10px;")
        cg.addWidget(desc)

        self.skip_rescan_check = QCheckBox(tr("skip_rescan_check"))
        self.skip_rescan_check.setChecked(self._cfg.get("skip_rescan_dialog", False))
        cg.addWidget(self.skip_rescan_check)

        default_row = QHBoxLayout()
        default_row.addWidget(QLabel(tr("lbl_default_answer")))
        self.rescan_answer_combo = QComboBox()
        self.rescan_answer_combo.addItems([tr("rescan_yes"), tr("rescan_no")])
        cur_ans = self._cfg.get("default_rescan_answer", "yes")
        self.rescan_answer_combo.setCurrentIndex(0 if cur_ans == "yes" else 1)
        self.rescan_answer_combo.setEnabled(self.skip_rescan_check.isChecked())
        default_row.addWidget(self.rescan_answer_combo)
        default_row.addStretch()
        cg.addLayout(default_row)
        self.skip_rescan_check.toggled.connect(self.rescan_answer_combo.setEnabled)
        lay.addWidget(close_grp)

        dj_grp = QGroupBox(tr("grp_dj_software"))
        dg = QVBoxLayout(dj_grp)
        dj_row = QHBoxLayout()
        dj_row.addWidget(QLabel(tr("lbl_dj_software")))
        self.dj_software_combo = QComboBox()
        for code, label in DJ_SOFTWARE_OPTIONS:
            self.dj_software_combo.addItem(label, userData=code)
        cur_dj = self._cfg.get("dj_software", "serato")
        dj_idx = next(
            (i for i, (c, _) in enumerate(DJ_SOFTWARE_OPTIONS) if c == cur_dj), 0
        )
        self.dj_software_combo.setCurrentIndex(dj_idx)
        self.dj_software_combo.setMaximumWidth(260)
        dj_row.addWidget(self.dj_software_combo)
        dj_row.addStretch()
        dg.addLayout(dj_row)
        dj_note = QLabel(tr("dj_software_note"))
        dj_note.setWordWrap(True)
        dj_note.setStyleSheet(
            "background: #f5f0fc; border: 1px solid #d4c5f9; border-radius: 5px; "
            "padding: 9px; font-size: 10px; color: #555;"
        )
        dg.addWidget(dj_note)
        lay.addWidget(dj_grp)
        lay.addStretch()
        return w

    # ------------------------------------------------------------------ Account
    def _build_tab_account(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(12)

        acc_grp = QGroupBox(tr("grp_user_profile"))
        ag = QGridLayout(acc_grp)
        ag.setSpacing(10)
        fields = [
            (tr("acc_name"),         "DJ Pro User"),
            (tr("acc_email"),        "djpro@example.com"),
            (tr("acc_plan"),        "Pro"),
            (tr("acc_expiry"),     "—"),
            (tr("acc_registered"), "—"),
        ]
        for row, (label, value) in enumerate(fields):
            ag.addWidget(QLabel(f"<b>{label}</b>"), row, 0)
            val_lbl = QLabel(value)
            val_lbl.setTextFormat(Qt.TextFormat.RichText)
            ag.addWidget(val_lbl, row, 1)
        lay.addWidget(acc_grp)

        note = QLabel(tr("account_note"))
        note.setWordWrap(True)
        note.setStyleSheet(
            "background: #eaf4fb; border: 1px solid #aed6f1; border-radius: 5px; "
            "padding: 10px; font-size: 10px; color: #555;"
        )
        lay.addWidget(note)
        lay.addStretch()
        return w

    # ------------------------------------------------------------------ Logic
    def _reset_defaults(self):
        self.theme_combo.setCurrentIndex(0)
        self.font_combo.setCurrentIndex(1)
        for cb in self._col_checks.values():
            if cb is not None:
                cb.setChecked(True)
        self.bpm_check.setChecked(False)
        self.bpm_spin.setValue(0)
        self.lang_combo.setCurrentIndex(0)
        self.auto_update_check.setChecked(False)
        self.skip_rescan_check.setChecked(False)
        self.rescan_answer_combo.setCurrentIndex(0)
        self.fit_columns_check.setChecked(False)
        dj_idx = next(
            (i for i, (c, _) in enumerate(DJ_SOFTWARE_OPTIONS) if c == "serato"), 0
        )
        self.dj_software_combo.setCurrentIndex(dj_idx)

    def _persist_dialog_size(self):
        size = {"width": self.width(), "height": self.height()}
        self._cfg["settings_dialog_size"] = size
        parent = self.parent()
        if parent is not None and hasattr(parent, "config"):
            parent.config["settings_dialog_size"] = size
            save_config(parent.config)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._size_save_timer.start(300)

    def _on_apply(self):
        vis = {k: (True if cb is None else cb.isChecked()) for k, cb in self._col_checks.items()}
        self._cfg["theme"] = "dark" if self.theme_combo.currentIndex() == 1 else "light"
        self._cfg["font_size"] = self.FONT_SIZE_KEYS[self.font_combo.currentIndex()][1]
        self._cfg["visible_columns"] = vis
        self._cfg["bpm_penalty_enabled"] = self.bpm_check.isChecked()
        self._cfg["bpm_reference"] = self.bpm_spin.value()
        self._cfg["language"] = self.lang_combo.currentData()
        self._cfg["auto_update"] = self.auto_update_check.isChecked()
        self._cfg["skip_rescan_dialog"] = self.skip_rescan_check.isChecked()
        self._cfg["default_rescan_answer"] = "yes" if self.rescan_answer_combo.currentIndex() == 0 else "no"
        self._cfg["dj_software"] = self.dj_software_combo.currentData()
        self._cfg["table_fit_columns"] = self.fit_columns_check.isChecked()
        self._persist_dialog_size()
        self._applied = dict(self._cfg)
        self.accept()

    def get_config(self) -> dict:
        return self._applied or self._cfg


# ===================================================================
# Quick Guide Dialog (replaces the old step-by-step wizard)
# ===================================================================

class QuickGuideDialog(QDialog):
    """Renders localized docs/quick_guide/<lang>.md — product overview and feature guide."""

    def __init__(self, parent=None, theme: str = "light"):
        super().__init__(parent)
        self.setWindowTitle(tr("guide_quick_title"))
        self.setMinimumSize(760, 680)
        self.resize(880, 760)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(True)
        layout.addWidget(self._browser, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton(tr("btn_close"))
        set_button_alt(btn_close, "btn_close_tt")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        self._load_doc()
        self._apply_theme(theme)

    def _load_doc(self):
        from serato_automation.doc_paths import resolve_localized_doc
        doc_path = resolve_localized_doc("quick_guide")
        try:
            with open(doc_path, "r", encoding="utf-8") as f:
                content = f.read()
            if hasattr(self._browser, "setMarkdown"):
                self._browser.setMarkdown(content)
            else:
                self._browser.setPlainText(content)
        except OSError:
            self._browser.setPlainText(tr("guide_quick_not_found", path=doc_path))

    def _apply_theme(self, theme: str):
        dark = theme == "dark"
        ui_theme.apply_themed_dialog(self, dark)
        p = ui_theme.palette(dark)
        self._browser.document().setDefaultStyleSheet(f"""
            body, p, li {{ font-family: Georgia, 'Times New Roman', serif;
                font-size: 13px; line-height: 1.55; color: {p['text']}; }}
            h1, h2, h3 {{ font-family: 'Segoe UI', sans-serif; color: {p['accent']};
                margin-top: 14px; }}
            h1 {{ font-size: 20px; }}
            h2 {{ font-size: 16px; }}
            strong, b {{ font-family: 'Segoe UI', sans-serif; color: {p['accent']}; }}
            a {{ color: {p['accent']}; }}
            table {{ font-family: 'Segoe UI', sans-serif; font-size: 12px; }}
            th, td {{ border: 1px solid {p['border']}; padding: 4px 8px; }}
        """)
        self._browser.setStyleSheet(
            f"border: 1px solid {p['border']}; border-radius: 6px; padding: 12px;"
            f" background: {p['panel_alt']};"
        )



# ===================================================================
# Pro upgrade dialog (placeholder — licensing backend TBD)
# ===================================================================

class ProUpgradeDialog(QDialog):
    """Inform the user about the one-time Pro license and open the purchase page."""

    def __init__(self, parent=None, theme: str = "light"):
        super().__init__(parent)
        self._theme = theme
        self.setWindowTitle(tr("pro_dialog_title"))
        self.setMinimumWidth(480)
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 18, 20, 18)

        self._title_lbl = QLabel(tr("pro_dialog_heading"))
        self._title_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self._title_lbl.setWordWrap(True)
        lay.addWidget(self._title_lbl)

        self._desc_lbl = QLabel(tr("pro_dialog_desc"))
        self._desc_lbl.setWordWrap(True)
        lay.addWidget(self._desc_lbl)

        self._benefits_lbl = QLabel(tr("pro_dialog_benefits"))
        self._benefits_lbl.setWordWrap(True)
        lay.addWidget(self._benefits_lbl)

        self._price_lbl = QLabel(tr("pro_dialog_price"))
        self._price_lbl.setWordWrap(True)
        lay.addWidget(self._price_lbl)

        foot = QHBoxLayout()
        foot.addStretch()
        btn_close = QPushButton(tr("btn_close"))
        btn_close.clicked.connect(self.reject)
        foot.addWidget(btn_close)
        btn_buy = QPushButton(tr("pro_dialog_buy"))
        btn_buy.setObjectName("proBtn")
        set_button_alt(btn_buy, "pro_dialog_buy_tt")
        btn_buy.clicked.connect(self._open_purchase)
        foot.addWidget(btn_buy)
        lay.addLayout(foot)

        self._apply_dialog_theme(theme)

    def _apply_dialog_theme(self, theme: str):
        dark = theme == "dark"
        ui_theme.apply_themed_dialog(self, dark)
        self._benefits_lbl.setStyleSheet(ui_theme.panel_box_style(dark))
        self._price_lbl.setStyleSheet(ui_theme.accent_label_style(dark))

    def _open_purchase(self):
        branding.open_url(branding.URL_PRO_UPGRADE)
        self.accept()


# ===================================================================
# Main Window
# ===================================================================

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self._logger = setup_logging()
        self._log_path = get_log_file_path()
        self._logger.info(branding.log_startup_message())

        self.config = load_config()
        init_language(self.config.get("language", "auto"))
        self.library_tracks: List = []
        self.match_results: List[MatchResult] = []
        self.current_crate_path: Optional[str] = None
        self._library_cache_loaded = False
        self._scan_worker = None
        self._match_worker = None
        self._title_locks = self._load_title_locks()
        self._locks_changed_in_session = False
        self._current_theme = self.config.get("theme", "light")
        self.serato_subcrates = None
        self._tab_fullscreen_index: Optional[int] = None

        # --- Audio player (shared single QMediaPlayer) ---
        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(0.7)
        self._player_current_row = -1
        self._player.positionChanged.connect(self._on_player_position_changed)
        self._player.playbackStateChanged.connect(self._on_player_state_changed)

        self._build_ui()
        self._restore_settings()
        self._check_serato()
        self._auto_load_library()

    # ------------------------------------------------------------------
    # Audio Player (shared QMediaPlayer + QAudioOutput)
    # ------------------------------------------------------------------

    def _player_play_row(self, row: int):
        """Play audio for the given row — stop previous row first."""
        # Same row already active: either resume from pause or do nothing (already playing)
        if self._player_current_row == row:
            if self._player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
                self._player.play()
            return

        # Stop previous row if playing a different row
        if self._player_current_row >= 0:
            self._player_stop_current()

        if row < 0 or row >= len(self.match_results):
            return

        result = self.match_results[row]
        if not result.is_effectively_matched or not result.library_track:
            return

        filepath = result.library_track.filepath
        if not filepath or not os.path.isfile(filepath):
            return

        self._player_current_row = row

        url = QUrl.fromLocalFile(os.path.abspath(filepath))
        self._player.setSource(url)
        self._player.play()

    def _player_pause(self):
        """Pause the currently playing track."""
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()

    def _player_stop_current(self):
        """Stop playback and reset the player widget for current row."""
        if self._player_current_row >= 0:
            pw = self.results_table.get_player_widget(self._player_current_row)
            if pw:
                pw.set_playing(False)
        self._player.stop()
        self._player_current_row = -1

    def _player_seek(self, position: int):
        """Seek to the given position (ms) in the current track.

        Accepts the seek in any playback state (Playing, Paused, Stopped).
        If the player is currently Stopped (no source loaded yet, or finished),
        we still apply the position because the media may already be loaded —
        Qt will honour setPosition() and resume from there on next play().
        """
        # Only seek if there is an active row AND a media source is loaded.
        # (We can't seek when nothing is loaded.)
        if self._player_current_row < 0:
            return
        # setPosition works in Playing/Paused/Stopped as long as a source is set
        self._player.setPosition(position)

    def _on_player_position_changed(self, position: int):
        """Update the slider of the currently playing row."""
        if self._player_current_row < 0:
            return
        pw = self.results_table.get_player_widget(self._player_current_row)
        if pw:
            duration = self._player.duration()
            pw.update_position(position, duration)

    def _on_player_state_changed(self, state):
        """Update play/pause button when playback state changes."""
        if self._player_current_row < 0:
            return
        pw = self.results_table.get_player_widget(self._player_current_row)
        if not pw:
            return

        if state == QMediaPlayer.PlaybackState.PlayingState:
            pw.set_playing(True)
        elif state == QMediaPlayer.PlaybackState.PausedState:
            pw.set_playing(False)
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            pw.set_playing(False)
            pw.update_position(0, 0)

    def _player_cleanup(self):
        """Stop player and reset all player widgets — called on close."""
        self._player.stop()
        self._player.setSource(QUrl())
        self._player_current_row = -1

    # ------------------------------------------------------------------
    # UI construction (decomposed into focused builders)
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.setWindowTitle(branding.window_title())
        self.setMinimumSize(1100, 800)
        self.resize(1300, 900)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(10)
        root.setContentsMargins(12, 8, 12, 8)

        self._header_bar = self._build_header_bar()
        root.addWidget(self._header_bar)
        root.addWidget(self._build_config_group())
        root.addWidget(self._build_tools_group())
        self._fs_bar = self._build_fullscreen_bar()
        root.addWidget(self._fs_bar)
        self.tabs = self._build_tab_widget()
        root.addWidget(self.tabs, stretch=1)
        self._footer_bar = self._build_footer_bar()
        root.addWidget(self._footer_bar)

        self._fs_escape = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._fs_escape.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._fs_escape.activated.connect(self._exit_tab_fullscreen)
        self._fs_escape.setEnabled(False)

        self.statusBar().showMessage(tr("status_ready"))
        self._apply_theme(self._current_theme)

    def _build_header_bar(self) -> QWidget:
        """Branded top bar: title, version, quick access to Pro / Wizard / Settings."""
        bar = QWidget()
        bar.setObjectName("headerBar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(14, 8, 14, 8)
        row.setSpacing(10)

        left = QVBoxLayout()
        left.setSpacing(2)
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self._lbl_app_title = QLabel(branding.APP_NAME)
        self._lbl_app_title.setObjectName("headerTitle")
        title_row.addWidget(self._lbl_app_title)
        self._lbl_version = QLabel(f"v{branding.APP_VERSION}")
        self._lbl_version.setObjectName("versionBadge")
        title_row.addWidget(self._lbl_version)
        title_row.addStretch()
        left.addLayout(title_row)
        self._lbl_tagline = QLabel(tr("app_tagline"))
        self._lbl_tagline.setObjectName("headerTagline")
        left.addWidget(self._lbl_tagline)
        row.addLayout(left, stretch=1)

        self._btn_pro = QPushButton(tr("btn_pro_upgrade"))
        self._btn_pro.setObjectName("proBtn")
        set_button_alt(self._btn_pro, "btn_pro_upgrade_tt")
        self._btn_pro.clicked.connect(self._open_pro_dialog)
        self._btn_pro.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        row.addWidget(self._btn_pro)

        self._btn_wizard = QPushButton(tr("btn_wizard"))
        self._btn_wizard.setObjectName("wizardBtn")
        self._btn_wizard.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        set_button_alt(self._btn_wizard, "btn_wizard_tt")
        self._btn_wizard.clicked.connect(self._open_quick_guide)
        row.addWidget(self._btn_wizard)

        self._btn_settings = QPushButton(tr("btn_settings"))
        self._btn_settings.setObjectName("settingsBtn")
        self._btn_settings.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        set_button_alt(self._btn_settings, "btn_settings_tt")
        self._btn_settings.clicked.connect(self._open_settings)
        row.addWidget(self._btn_settings)

        return bar

    def _build_footer_bar(self) -> QWidget:
        """Bottom bar: feedback, website, help links, vendor branding."""
        bar = QWidget()
        bar.setObjectName("footerBar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(10, 4, 10, 4)
        row.setSpacing(4)

        self._btn_feedback = _link_button(
            tr("btn_feedback"), branding.URL_FEEDBACK, "btn_feedback_tt"
        )
        row.addWidget(self._btn_feedback)

        self._btn_website = _link_button(
            tr("btn_website"), branding.URL_WEBSITE, "btn_website_tt"
        )
        row.addWidget(self._btn_website)

        row.addStretch()

        self._lbl_footer_brand = QLabel(tr("footer_brand", vendor=branding.APP_VENDOR))
        self._lbl_footer_brand.setObjectName("footerBrand")
        self._lbl_footer_brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(self._lbl_footer_brand)

        row.addStretch()

        self._btn_algo_doc = QPushButton(tr("btn_algo_doc"))
        self._btn_algo_doc.setObjectName("guideBtn")
        set_button_alt(self._btn_algo_doc, "btn_algo_doc_tt")
        self._btn_algo_doc.clicked.connect(self._show_algorithm_doc)
        row.addWidget(self._btn_algo_doc)

        self._btn_open_log = QPushButton(tr("btn_open_log"))
        set_button_alt(self._btn_open_log, "btn_open_log_tt", path=self._log_path)
        self._btn_open_log.clicked.connect(self._open_log_file)
        row.addWidget(self._btn_open_log)

        return bar

    def _open_pro_dialog(self):
        ProUpgradeDialog(self, theme=self._current_theme).exec()

    def _build_fullscreen_bar(self) -> QWidget:
        """Top bar shown in tab fullscreen mode: menu + title + exit."""
        bar = QWidget()
        bar.setObjectName("fullscreenBar")
        bar.setVisible(False)
        row = QHBoxLayout(bar)
        row.setContentsMargins(8, 4, 8, 4)
        row.setSpacing(8)

        self._fs_menu_btn = QToolButton()
        self._fs_menu_btn.setText(tr("btn_fs_menu"))
        self._fs_menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._fs_menu_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._fs_menu = QMenu(self)
        self._fs_menu_btn.setMenu(self._fs_menu)
        row.addWidget(self._fs_menu_btn)

        self._fs_title = QLabel("")
        self._fs_title.setStyleSheet("font-weight: bold;")
        row.addWidget(self._fs_title, stretch=1)
        return bar

    def _toggle_tab_fullscreen(self, tab_index: int):
        if self._tab_fullscreen_index == tab_index:
            self._exit_tab_fullscreen()
        else:
            self._enter_tab_fullscreen(tab_index)

    def _enter_tab_fullscreen(self, tab_index: int):
        if self._tab_fullscreen_index is not None:
            return
        if not self.tabs.isTabEnabled(tab_index):
            return
        self._tab_fullscreen_index = tab_index
        self._header_bar.setVisible(False)
        self.grp_config.setVisible(False)
        self.grp_tools.setVisible(False)
        self._footer_bar.setVisible(False)
        self.tabs.tabBar().hide()
        self._fs_bar.setVisible(True)
        self.tabs.setCurrentIndex(tab_index)
        titles = {1: tr("tab_results"), 2: tr("tab_editing")}
        self._fs_title.setText(titles.get(tab_index, ""))
        self._populate_fs_menu(tab_index)
        self._fs_escape.setEnabled(True)
        self.statusBar().showMessage(tr("fs_status_hint"))
        self._update_fs_button_labels()

    def _exit_tab_fullscreen(self):
        if self._tab_fullscreen_index is None:
            return
        self._tab_fullscreen_index = None
        self._header_bar.setVisible(True)
        self.grp_config.setVisible(True)
        self.grp_tools.setVisible(True)
        self._footer_bar.setVisible(True)
        self.tabs.tabBar().show()
        self._fs_bar.setVisible(False)
        self._fs_escape.setEnabled(False)
        self.statusBar().showMessage(tr("status_ready"))
        self._update_fs_button_labels()

    def _update_fs_button_labels(self):
        """Toggle toolbar fullscreen buttons between enter/exit labels."""
        for tab_index, btn in ((1, self._btn_results_fs), (2, self._btn_editing_fs)):
            if btn is None:
                continue
            active = self._tab_fullscreen_index == tab_index
            btn.setText(tr("btn_exit_fullscreen") if active else tr("btn_fullscreen"))
            set_button_alt(btn, "btn_exit_fullscreen_tt" if active else "btn_fullscreen_tt")
            if active:
                btn.setObjectName("primaryBtn")
            else:
                btn.setObjectName("")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _populate_fs_menu(self, tab_index: int):
        self._fs_menu.clear()
        if tab_index == 1:
            for key, slot in (
                ("btn_clean_library", self._clean_library),
                ("btn_find_diff", self._find_differences),
                ("btn_duplicates", self._find_duplicates),
            ):
                self._fs_menu.addAction(tr(key), slot)
            self._fs_menu.addSeparator()
            self._fs_menu.addAction(tr("btn_create_crate"), self._create_crate)
            self._fs_menu.addAction(tr("btn_create_crate_clean"), self._create_crate_and_clean)
            self._fs_menu.addAction(tr("btn_save_missing"), self._save_missing)
            self._fs_menu.addSeparator()
            self._fs_menu.addAction(tr("btn_settings"), self._open_settings)
        elif tab_index == 2:
            self._fs_menu.addAction(tr("edit_search_btn"), self._clean_library)
            self._fs_menu.addAction(tr("btn_duplicates"), self._find_duplicates)
            self._fs_menu.addSeparator()
            self._fs_menu.addAction(tr("edit_save_all_btn"), self._editing_save_all)
            self._fs_menu.addAction(tr("edit_update_serato_btn"), self._update_serato_database)
            self._fs_menu.addAction(tr("edit_replace_btn"), self._editing_replace)
            self._fs_menu.addAction(tr("edit_copy_list_btn"), self._editing_copy_list)
            self._fs_menu.addSeparator()
            self._fs_menu.addAction(tr("btn_find_diff"), self._find_differences)
            self._fs_menu.addAction(tr("btn_settings"), self._open_settings)

    def _update_scan_button_text(self):
        if self.library_tracks:
            self.btn_scan.setText(tr("btn_rescan_library"))
        else:
            self.btn_scan.setText(tr("btn_scan_library"))

    def _refresh_library_status(self):
        fs = self.config.get("font_size", 11)
        p = ui_theme.palette()
        badge_base = (
            f"border-radius: 6px; padding: 4px 10px; font-weight: bold;"
            f" font-size: {fs}px; background: {p['panel_alt']};"
            f" border: 1px solid {p['border']};"
        )
        if self._scan_worker and self._scan_worker.isRunning():
            self.library_status.setText(tr("library_scanning"))
            self.library_status.setStyleSheet(badge_base + f" color: {p['accent']};")
            return
        if not self.library_tracks:
            self.library_status.setText(tr("library_not_loaded"))
            self.library_status.setStyleSheet(badge_base + f" color: {p['text_muted']};")
            self.library_status.setToolTip("")
            return
        if self._library_cache_loaded:
            self.library_status.setText(tr("library_cache", count=len(self.library_tracks)))
            self.library_status.setToolTip(tr("library_cache_tt"))
        else:
            self.library_status.setText(tr("library_loaded", count=len(self.library_tracks)))
            self.library_status.setToolTip("")
        self.library_status.setStyleSheet(badge_base + f" color: {p['success']};")

    def _retranslate_ui(self):
        """Refresh all visible UI strings after a language change."""
        self.setWindowTitle(branding.window_title())
        self._lbl_tagline.setText(tr("app_tagline"))
        self._btn_pro.setText(tr("btn_pro_upgrade"))
        set_button_alt(self._btn_pro, "btn_pro_upgrade_tt")
        self.grp_config.setTitle(tr("grp_config"))
        self.grp_tools.setTitle(tr("grp_tools"))
        self._lbl_music_folder.setText(tr("lbl_music_folder"))
        self.music_folder_input.setPlaceholderText(tr("ph_music_folder"))
        self.btn_browse.setText(tr("btn_browse"))
        set_button_alt(self.btn_browse, "btn_browse_tt")
        self._update_scan_button_text()
        set_button_alt(self.btn_scan, "btn_scan_tt")
        self._btn_clean_library.setText(tr("btn_clean_library"))
        set_button_alt(self._btn_clean_library, "btn_clean_library_tt")
        self._btn_find_diff.setText(tr("btn_find_diff"))
        set_button_alt(self._btn_find_diff, "btn_find_diff_tt")
        self._btn_duplicates.setText(tr("btn_duplicates"))
        set_button_alt(self._btn_duplicates, "btn_duplicates_tt")
        self._btn_wizard.setText(tr("btn_wizard"))
        set_button_alt(self._btn_wizard, "btn_wizard_tt")
        self._btn_settings.setText(tr("btn_settings"))
        set_button_alt(self._btn_settings, "btn_settings_tt")
        self._btn_serato.setText(tr("btn_serato_folder"))
        set_button_alt(self._btn_serato, "btn_serato_folder_tt")
        self._lbl_crate_name.setText(tr("lbl_crate_name"))
        self._btn_feedback.setText(tr("btn_feedback"))
        set_button_alt(self._btn_feedback, "btn_feedback_tt")
        self._btn_website.setText(tr("btn_website"))
        set_button_alt(self._btn_website, "btn_website_tt")
        self._lbl_footer_brand.setText(tr("footer_brand", vendor=branding.APP_VENDOR))
        self._btn_open_log.setText(tr("btn_open_log"))
        set_button_alt(self._btn_open_log, "btn_open_log_tt", path=self._log_path)
        self._btn_algo_doc.setText(tr("btn_algo_doc"))
        set_button_alt(self._btn_algo_doc, "btn_algo_doc_tt")
        self._btn_load_playlist.setText(tr("btn_load_file"))
        set_button_alt(self._btn_load_playlist, "btn_load_file_tt")
        self._btn_clear_playlist.setText(tr("btn_clear"))
        set_button_alt(self._btn_clear_playlist, "btn_clear_tt")
        self._btn_import_url.setText(tr("btn_import_url"))
        set_button_alt(self._btn_import_url, "btn_import_url_tt")
        self._btn_format_guide.setText(tr("btn_format_guide"))
        set_button_alt(self._btn_format_guide, "btn_format_guide_tt")
        self.btn_match.setText(tr("btn_match"))
        set_button_alt(self.btn_match, "btn_match_tt")
        self._lbl_min_pct.setText(tr("lbl_min_score"))
        self.score_threshold_combo.setToolTip(tr("score_threshold_tt"))
        if hasattr(self, "_lbl_select_group"):
            self._lbl_select_group.setText(tr("grp_select_by_score"))
        self._update_select_all_button_label()
        self.btn_desel.setText(tr("btn_deselect"))
        set_button_alt(self.btn_desel, "btn_deselect_tt")
        self.btn_inv.setText(tr("btn_invert"))
        set_button_alt(self.btn_inv, "btn_invert_tt")
        self.btn_copy.setText(tr("btn_copy_table"))
        set_button_alt(self.btn_copy, "btn_copy_table_tt")
        self.btn_copy_last.setText(tr("btn_copy_last"))
        set_button_alt(self.btn_copy_last, "btn_copy_last_tt")
        self.btn_create_crate.setText(tr("btn_create_crate"))
        set_button_alt(self.btn_create_crate, "btn_create_crate_tt")
        self.btn_create_crate_clean.setText(tr("btn_create_crate_clean"))
        set_button_alt(self.btn_create_crate_clean, "btn_create_crate_clean_tt")
        self.btn_save_missing.setText(tr("btn_save_missing"))
        set_button_alt(self.btn_save_missing, "btn_save_missing_tt")
        if hasattr(self, "_btn_results_fs"):
            self._update_fs_button_labels()
        if hasattr(self, "_fs_menu_btn"):
            self._fs_menu_btn.setText(tr("btn_fs_menu"))
        self.tabs.setTabText(0, tr("tab_playlist"))
        self.tabs.setTabText(1, tr("tab_results"))
        self.tabs.setTabText(2, tr("tab_editing"))
        self.results_table.retranslate_headers()
        if self.match_results:
            self.results_table.retranslate_content()
        if hasattr(self, "editing_table"):
            self.editing_table.setHorizontalHeaderLabels(self._editing_headers())
            self._btn_edit_search.setText(tr("edit_search_btn"))
            self._btn_edit_replace.setText(tr("edit_replace_btn"))
            self._btn_edit_copy.setText(tr("edit_copy_list_btn"))
            self._btn_edit_save_all.setText(tr("edit_save_all_btn"))
            self._btn_update_serato.setText(tr("edit_update_serato_btn"))
            set_button_alt(self._btn_update_serato, "edit_update_serato_tt")
            if self.editing_table.rowCount() == 0:
                self.editing_status.setText(tr("edit_status_empty"))
            else:
                self.editing_status.setText(
                    tr("edit_status_count", count=self.editing_table.rowCount())
                )
        self.playlist_input.setPlaceholderText(tr("ph_playlist_input"))
        if hasattr(self, "_rl_row1"):
            self._rebuild_results_toolbar(self.config.get("font_size", 11))
        self._update_font_scaled_widgets(self.config.get("font_size", 11))
        self._fit_toolbar_buttons()
        self._update_serato_label()
        self._refresh_library_status()
        self._refresh_stats()
        if not self.match_results and not self.library_tracks:
            self.statusBar().showMessage(tr("status_ready"))

    def _build_config_group(self) -> QGroupBox:
        """Step 1 — music library: folder path, browse, scan, status."""
        group = QGroupBox(tr("grp_config"))
        self.grp_config = group
        layout = QHBoxLayout(group)

        self._lbl_music_folder = QLabel(tr("lbl_music_folder"))
        layout.addWidget(self._lbl_music_folder)
        self.music_folder_input = QLineEdit(self.config.get("music_folder", ""))
        self.music_folder_input.setPlaceholderText(tr("ph_music_folder"))
        layout.addWidget(self.music_folder_input, stretch=1)

        self.btn_browse = QPushButton(tr("btn_browse"))
        set_button_alt(self.btn_browse, "btn_browse_tt")
        self.btn_browse.clicked.connect(self._browse_music_folder)
        layout.addWidget(self.btn_browse)

        btn_scan = QPushButton(tr("btn_scan_library"))
        btn_scan.setObjectName("primaryBtn")
        btn_scan.clicked.connect(self._scan_library)
        set_button_alt(btn_scan, "btn_scan_tt")
        layout.addWidget(btn_scan)
        self.btn_scan = btn_scan

        self.library_status = QLabel(tr("library_not_loaded"))
        self.library_status.setObjectName("statusBadge")
        layout.addWidget(self.library_status)

        return group

    def _build_tools_group(self) -> QGroupBox:
        """Library maintenance (row 1) + Serato export config (row 2)."""
        group = QGroupBox(tr("grp_tools"))
        self.grp_tools = group
        outer = QVBoxLayout(group)
        outer.setSpacing(8)

        maint_w = QWidget()
        maint_w.setObjectName("toolSection")
        row1 = QHBoxLayout(maint_w)
        row1.setContentsMargins(10, 6, 10, 6)
        lbl_maint = QLabel(tr("tools_section_maint"))
        lbl_maint.setObjectName("sectionLabel")
        row1.addWidget(lbl_maint)
        row1.addWidget(_vline())

        self._btn_clean_library = QPushButton(tr("btn_clean_library"))
        self._btn_clean_library.setObjectName("guideBtn")
        set_button_alt(self._btn_clean_library, "btn_clean_library_tt")
        self._btn_clean_library.clicked.connect(self._clean_library)
        row1.addWidget(self._btn_clean_library)

        self._btn_find_diff = QPushButton(tr("btn_find_diff"))
        self._btn_find_diff.setObjectName("guideBtn")
        set_button_alt(self._btn_find_diff, "btn_find_diff_tt")
        self._btn_find_diff.clicked.connect(self._find_differences)
        row1.addWidget(self._btn_find_diff)

        self._btn_duplicates = QPushButton(tr("btn_duplicates"))
        self._btn_duplicates.setObjectName("guideBtn")
        set_button_alt(self._btn_duplicates, "btn_duplicates_tt")
        self._btn_duplicates.clicked.connect(self._find_duplicates)
        row1.addWidget(self._btn_duplicates)
        row1.addStretch()
        outer.addWidget(maint_w)

        serato_w = QWidget()
        serato_w.setObjectName("toolSection")
        row2 = QHBoxLayout(serato_w)
        row2.setContentsMargins(10, 6, 10, 6)
        lbl_serato = QLabel(tr("tools_section_serato"))
        lbl_serato.setObjectName("sectionLabel")
        row2.addWidget(lbl_serato)
        row2.addWidget(_vline())

        self.serato_label = QLabel(tr("serato_not_detected"))
        self.serato_label.setStyleSheet("font-style: italic;")
        row2.addWidget(self.serato_label)

        self._btn_serato = QPushButton(tr("btn_serato_folder"))
        set_button_alt(self._btn_serato, "btn_serato_folder_tt")
        self._btn_serato.clicked.connect(self._browse_serato_folder)
        row2.addWidget(self._btn_serato)

        self._lbl_crate_name = QLabel(tr("lbl_crate_name"))
        row2.addWidget(self._lbl_crate_name)
        self.crate_name_input = QLineEdit("Evento_" + datetime.now().strftime("%Y-%m-%d"))
        self.crate_name_input.setMinimumWidth(180)
        self.crate_name_input.setMaximumWidth(280)
        row2.addWidget(self.crate_name_input)
        row2.addStretch()
        outer.addWidget(serato_w)

        return group

    def _build_tab_widget(self) -> QTabWidget:
        tabs = QTabWidget()
        tabs.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))

        # --- Playlist tab ---
        playlist_tab = QWidget()
        pl_layout = QVBoxLayout(playlist_tab)
        pl_layout.setContentsMargins(6, 6, 6, 6)

        pl_toolbar = QHBoxLayout()

        self._btn_import_url = QPushButton(tr("btn_import_url"))
        self._btn_import_url.setObjectName("importBtn")
        set_button_alt(self._btn_import_url, "btn_import_url_tt")
        self._btn_import_url.clicked.connect(self._import_from_url)
        pl_toolbar.addWidget(self._btn_import_url)

        self._btn_load_playlist = QPushButton(tr("btn_load_file"))
        set_button_alt(self._btn_load_playlist, "btn_load_file_tt")
        self._btn_load_playlist.clicked.connect(self._load_playlist_file)
        pl_toolbar.addWidget(self._btn_load_playlist)

        pl_toolbar.addWidget(_vline())

        self._btn_format_guide = QPushButton(tr("btn_format_guide"))
        self._btn_format_guide.setObjectName("guideBtn")
        set_button_alt(self._btn_format_guide, "btn_format_guide_tt")
        self._btn_format_guide.clicked.connect(self._show_format_guide)
        pl_toolbar.addWidget(self._btn_format_guide)

        pl_toolbar.addStretch()

        self._btn_clear_playlist = QPushButton(tr("btn_clear"))
        set_button_alt(self._btn_clear_playlist, "btn_clear_tt")
        self._btn_clear_playlist.clicked.connect(self._clear_playlist)
        pl_toolbar.addWidget(self._btn_clear_playlist)
        pl_layout.addLayout(pl_toolbar)

        self.playlist_input = DropTextEdit()
        self.playlist_input.setMinimumHeight(200)
        pl_layout.addWidget(self.playlist_input, stretch=1)

        match_row = QHBoxLayout()
        self.btn_match = QPushButton(tr("btn_match"))
        set_button_alt(self.btn_match, "btn_match_tt")
        self.btn_match.setObjectName("primaryBtn")
        self.btn_match.clicked.connect(self._run_matching)
        self.btn_match.setEnabled(False)
        match_row.addWidget(self.btn_match)

        self.match_progress = QProgressBar()
        self.match_progress.setVisible(False)
        match_row.addWidget(self.match_progress)
        match_row.addStretch()
        pl_layout.addLayout(match_row)

        tabs.addTab(playlist_tab, tr("tab_playlist"))

        # --- Results tab ---
        results_tab = QWidget()
        rl_layout = QVBoxLayout(results_tab)
        rl_layout.setContentsMargins(6, 6, 6, 6)

        # Adaptive toolbar: 1 row (small/normal fonts) or 2 rows (large fonts)
        self._rl_toolbar_container = QWidget()
        _rl_outer = QVBoxLayout(self._rl_toolbar_container)
        _rl_outer.setContentsMargins(0, 0, 0, 0)
        _rl_outer.setSpacing(2)

        self._rl_row1_widget = QWidget()
        self._rl_row1 = QHBoxLayout(self._rl_row1_widget)
        self._rl_row1.setContentsMargins(0, 0, 0, 0)

        self._rl_row2_widget = QWidget()
        self._rl_row2 = QHBoxLayout(self._rl_row2_widget)
        self._rl_row2.setContentsMargins(0, 0, 0, 0)

        self._rl_row3_widget = QWidget()
        self._rl_row3 = QHBoxLayout(self._rl_row3_widget)
        self._rl_row3.setContentsMargins(0, 0, 0, 0)

        _rl_outer.addWidget(self._rl_row1_widget)
        _rl_outer.addWidget(self._rl_row2_widget)
        _rl_outer.addWidget(self._rl_row3_widget)
        rl_layout.addWidget(self._rl_toolbar_container)

        # Create toolbar widgets (parents assigned when added to row layouts)
        self._btn_results_fs = QPushButton(tr("btn_fullscreen"))
        set_button_alt(self._btn_results_fs, "btn_fullscreen_tt")
        self._btn_results_fs.clicked.connect(lambda: self._toggle_tab_fullscreen(1))

        self.result_stats = QLabel("")
        self.result_stats.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 11px;")

        self._lbl_min_pct = QLabel(tr("lbl_min_score"))
        self.score_threshold_combo = QComboBox()
        self.score_threshold_combo.addItems(["0%", "30%", "50%", "60%", "70%", "80%", "90%"])
        self.score_threshold_combo.setCurrentText("50%")
        self.score_threshold_combo.setMaximumWidth(65)
        self.score_threshold_combo.setToolTip(tr("score_threshold_tt"))
        self.score_threshold_combo.currentTextChanged.connect(self._update_select_all_button_label)

        self.btn_sel_all = QPushButton("")
        self.btn_sel_all.setObjectName("selectAllBtn")
        self.btn_sel_all.clicked.connect(self._on_select_all)
        self.btn_sel_all.setEnabled(False)
        self._update_select_all_button_label(self.score_threshold_combo.currentText())

        self._select_threshold_group = QFrame()
        self._select_threshold_group.setObjectName("selectThresholdGroup")
        sg_lay = QHBoxLayout(self._select_threshold_group)
        sg_lay.setContentsMargins(8, 4, 8, 4)
        sg_lay.setSpacing(6)
        self._lbl_select_group = QLabel(tr("grp_select_by_score"))
        self._lbl_select_group.setObjectName("selectGroupTitle")
        self._lbl_select_arrow = QLabel("→")
        self._lbl_select_arrow.setObjectName("selectGroupArrow")
        sg_lay.addWidget(self._lbl_select_group)
        sg_lay.addWidget(self._lbl_min_pct)
        sg_lay.addWidget(self.score_threshold_combo)
        sg_lay.addWidget(self._lbl_select_arrow)
        sg_lay.addWidget(self.btn_sel_all)

        for text_key, slot, attr, tt_key in [
            ("btn_deselect", self._on_deselect_all, "btn_desel", "btn_deselect_tt"),
            ("btn_invert", self._on_invert_selection, "btn_inv", "btn_invert_tt"),
        ]:
            btn = QPushButton(tr(text_key))
            set_button_alt(btn, tt_key)
            btn.clicked.connect(slot)
            btn.setEnabled(False)
            setattr(self, attr, btn)

        self._rl_sep2 = QFrame()
        self._rl_sep2.setFrameShape(QFrame.Shape.VLine)
        self._rl_sep2.setStyleSheet("color: #bdc3c7;")

        self.btn_copy = QPushButton(tr("btn_copy_table"))
        set_button_alt(self.btn_copy, "btn_copy_table_tt")
        self.btn_copy.setObjectName("copyBtn")
        self.btn_copy.clicked.connect(self._on_copy)
        self.btn_copy.setEnabled(False)

        self.btn_copy_last = QPushButton(tr("btn_copy_last"))
        set_button_alt(self.btn_copy_last, "btn_copy_last_tt")
        self.btn_copy_last.setObjectName("copyBtn")
        self.btn_copy_last.clicked.connect(self._on_copy_last)
        self.btn_copy_last.setEnabled(False)

        self._rl_sep3 = QFrame()
        self._rl_sep3.setFrameShape(QFrame.Shape.VLine)
        self._rl_sep3.setStyleSheet("color: #bdc3c7;")

        self.btn_create_crate = QPushButton(tr("btn_create_crate"))
        set_button_alt(self.btn_create_crate, "btn_create_crate_tt")
        self.btn_create_crate.setObjectName("successBtn")
        self.btn_create_crate.clicked.connect(self._create_crate)
        self.btn_create_crate.setEnabled(False)

        self.btn_create_crate_clean = QPushButton(tr("btn_create_crate_clean"))
        set_button_alt(self.btn_create_crate_clean, "btn_create_crate_clean_tt")
        self.btn_create_crate_clean.setObjectName("successBtn")
        self.btn_create_crate_clean.clicked.connect(self._create_crate_and_clean)
        self.btn_create_crate_clean.setEnabled(False)

        self.btn_save_missing = QPushButton(tr("btn_save_missing"))
        set_button_alt(self.btn_save_missing, "btn_save_missing_tt")
        self.btn_save_missing.clicked.connect(self._save_missing)
        self.btn_save_missing.setEnabled(False)

        self._rebuild_results_toolbar(self.config.get("font_size", 11))

        self.results_table = ResultsTable(title_locks=self._title_locks, main_window=self)
        self.results_table.selection_changed_signal.connect(self._on_table_selection_changed)
        self.results_table.lock_changed_signal.connect(self._on_lock_changed)
        rl_layout.addWidget(self.results_table, stretch=1)

        tabs.addTab(results_tab, tr("tab_results"))
        tabs.setTabEnabled(1, False)

        # --- Editing tab (library cleanup) ---
        tabs.addTab(self._build_editing_tab(), tr("tab_editing"))
        tabs.setTabEnabled(2, False)

        return tabs

    def _build_editing_tab(self) -> QWidget:
        editing_tab = QWidget()
        ed_layout = QVBoxLayout(editing_tab)
        ed_layout.setContentsMargins(6, 6, 6, 6)

        top = QHBoxLayout()

        self._btn_editing_fs = QPushButton(tr("btn_fullscreen"))
        set_button_alt(self._btn_editing_fs, "btn_fullscreen_tt")
        self._btn_editing_fs.clicked.connect(lambda: self._toggle_tab_fullscreen(2))
        top.addWidget(self._btn_editing_fs)

        top.addWidget(_vline())

        self._btn_edit_search = QPushButton(tr("edit_search_btn"))
        self._btn_edit_search.setObjectName("primaryBtn")
        self._btn_edit_search.clicked.connect(self._clean_library)
        top.addWidget(self._btn_edit_search)

        self._btn_edit_replace = QPushButton(tr("edit_replace_btn"))
        self._btn_edit_replace.clicked.connect(self._editing_replace)
        self._btn_edit_replace.setEnabled(False)
        top.addWidget(self._btn_edit_replace)

        self._btn_edit_copy = QPushButton(tr("edit_copy_list_btn"))
        self._btn_edit_copy.setObjectName("copyBtn")
        self._btn_edit_copy.clicked.connect(self._editing_copy_list)
        self._btn_edit_copy.setEnabled(False)
        top.addWidget(self._btn_edit_copy)

        self._btn_edit_save_all = QPushButton(tr("edit_save_all_btn"))
        self._btn_edit_save_all.setObjectName("successBtn")
        self._btn_edit_save_all.clicked.connect(self._editing_save_all)
        self._btn_edit_save_all.setEnabled(False)
        top.addWidget(self._btn_edit_save_all)

        self._btn_update_serato = QPushButton(tr("edit_update_serato_btn"))
        set_button_alt(self._btn_update_serato, "edit_update_serato_tt")
        self._btn_update_serato.clicked.connect(self._update_serato_database)
        self._btn_update_serato.setEnabled(False)
        top.addWidget(self._btn_update_serato)

        self.editing_status = QLabel(tr("edit_status_empty"))
        self.editing_status.setStyleSheet("color: #7f8c8d; font-weight: bold;")
        top.addWidget(self.editing_status)
        top.addStretch()
        ed_layout.addLayout(top)

        note = QLabel(tr("edit_serato_note"))
        note.setWordWrap(True)
        note.setStyleSheet("color: #7f8c8d; font-size: 10px; font-style: italic;")
        ed_layout.addWidget(note)

        self.editing_table = QTableWidget()
        self.editing_table.setColumnCount(len(self._editing_headers()))
        self.editing_table.setHorizontalHeaderLabels(self._editing_headers())
        self.editing_table.verticalHeader().setVisible(False)
        # Edit only on double-click / typing — never on hover.
        self.editing_table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.EditKeyPressed
            | QTableWidget.EditTrigger.AnyKeyPressed
        )
        self.editing_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.editing_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        hh = self.editing_table.horizontalHeader()
        for c in range(E_NUM_COLS):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.Interactive)
        hh.setStretchLastSection(False)
        hh.setSectionsClickable(True)
        hh.setSortIndicatorShown(True)
        hh.sectionClicked.connect(self._sort_editing)
        self.editing_table.setColumnWidth(E_COL_FILE, 200)
        self.editing_table.setColumnWidth(E_COL_TITLE, 230)
        self.editing_table.setColumnWidth(E_COL_ARTIST, 170)
        self.editing_table.setColumnWidth(E_COL_ALBUM, 170)
        self.editing_table.setColumnWidth(E_COL_GENRE, 130)
        self.editing_table.setColumnWidth(E_COL_HOTCUE, 70)
        self.editing_table.setColumnWidth(E_COL_LOCATION, 260)
        self.editing_table.setColumnWidth(E_COL_ACTION, 90)
        self.editing_table.setColumnWidth(E_COL_DELETE, 100)
        self._editing_sort = (None, True)
        ed_layout.addWidget(self.editing_table, stretch=1)

        return editing_tab

    @staticmethod
    def _editing_headers() -> list:
        return [
            tr("edit_col_file"),
            tr("edit_col_title"),
            tr("edit_col_artist"),
            tr("edit_col_album"),
            tr("edit_col_genre"),
            tr("edit_col_hotcue"),
            tr("edit_col_location"),
            tr("edit_col_action"),
            tr("edit_col_delete"),
        ]

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    def _restore_settings(self):
        mf = self.config.get("music_folder", "")
        if mf and os.path.isdir(mf):
            self.music_folder_input.setText(mf)

    # ------------------------------------------------------------------
    # Theme & column visibility
    # ------------------------------------------------------------------

    def _apply_theme(self, theme: str):
        """Apply light or dark stylesheet to the whole application."""
        global _DARK_THEME_ACTIVE
        self._current_theme = theme
        _DARK_THEME_ACTIVE = (theme == "dark")
        ui_theme.set_dark_active(_DARK_THEME_ACTIVE)
        font_size = self.config.get("font_size", 11)
        QApplication.instance().setStyleSheet(_make_stylesheet(theme, font_size))
        self._update_dynamic_label_fonts(font_size)
        if hasattr(self, "results_table"):
            self.results_table.apply_font_size(font_size)
        if hasattr(self, "library_status"):
            self._refresh_library_status()
        if hasattr(self, "serato_label"):
            self._update_serato_label()
        if hasattr(self, "_rl_row1"):
            self._rebuild_results_toolbar(font_size)
        self._update_font_scaled_widgets(font_size)
        if hasattr(self, "editing_status"):
            p = ui_theme.palette()
            self.editing_status.setStyleSheet(
                f"color: {p['text_muted']}; font-weight: bold;"
            )
        QTimer.singleShot(0, self._fit_toolbar_buttons)

    def _update_dynamic_label_fonts(self, font_size: int) -> None:
        """Refresh inline font-size on labels that use custom stylesheets."""
        small = max(8, font_size - 1)
        stats_color = "#e0e4ef" if _DARK_THEME_ACTIVE else "#2c3e50"
        self.result_stats.setStyleSheet(
            f"font-weight: bold; color: {stats_color}; font-size: {font_size}px;"
        )
        self._lbl_footer_brand.setStyleSheet(
            f"color: {ui_theme.palette()['footer_text']}; font-size: {small}px; font-weight: bold;"
        )

    def _fit_toolbar_buttons(self) -> None:
        """Apply chosen font size to toolbar buttons (never shrink below setting)."""
        font_size = self.config.get("font_size", 11)
        bold = font_size >= 17
        buttons = [
            self._btn_pro, self._btn_wizard, self._btn_settings,
            self.btn_browse, self.btn_scan, self._btn_clean_library,
            self._btn_find_diff, self._btn_duplicates,
            self._btn_serato, self._btn_feedback, self._btn_website,
            self._btn_open_log, self._btn_algo_doc,
            self._btn_results_fs, self._btn_editing_fs,
            self._btn_load_playlist,
            self._btn_clear_playlist, self._btn_import_url, self._btn_format_guide,
            self.btn_match, self.btn_sel_all, self.btn_desel, self.btn_inv,
            self.btn_copy, self.btn_copy_last, self.btn_create_crate,
            self.btn_create_crate_clean, self.btn_save_missing,
        ]
        for btn in buttons:
            if btn is not None:
                _apply_button_font(btn, font_size, bold=bold)

    def _update_font_scaled_widgets(self, font_size: int) -> None:
        """Widen combo boxes and labels that need extra room at large font sizes."""
        if hasattr(self, "score_threshold_combo"):
            self.score_threshold_combo.setMinimumWidth(max(65, font_size * 5))
            self.score_threshold_combo.setMaximumWidth(max(80, font_size * 6))
        if hasattr(self, "_select_threshold_group"):
            self._select_threshold_group.setSizePolicy(
                QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
            )

    def _rebuild_results_toolbar(self, font_size: int) -> None:
        """Redistribute toolbar: 1 row (≤11), 2 rows (12–14), 3 rows (≥15)."""
        for row in (self._rl_row1, self._rl_row2, self._rl_row3):
            while row.count():
                row.takeAt(0)

        if font_size <= 11:
            self._rl_row1.addWidget(self._btn_results_fs)
            self._rl_row1.addWidget(self.result_stats)
            self._rl_row1.addStretch()
            self._rl_row1.addWidget(self._select_threshold_group)
            self._rl_row1.addWidget(self.btn_desel)
            self._rl_row1.addWidget(self.btn_inv)
            self._rl_row1.addWidget(self._rl_sep2)
            self._rl_row1.addWidget(self.btn_copy)
            self._rl_row1.addWidget(self.btn_copy_last)
            self._rl_row1.addWidget(self._rl_sep3)
            self._rl_row1.addWidget(self.btn_create_crate)
            self._rl_row1.addWidget(self.btn_create_crate_clean)
            self._rl_row1.addWidget(self.btn_save_missing)
            self._rl_sep2.show()
            self._rl_sep3.show()
            self._rl_row2_widget.setVisible(False)
            self._rl_row3_widget.setVisible(False)
        elif font_size <= 14:
            self._rl_row1.addWidget(self._btn_results_fs)
            self._rl_row1.addWidget(self.result_stats)
            self._rl_row1.addStretch()
            self._rl_row1.addWidget(self._select_threshold_group)
            self._rl_row1.addWidget(self.btn_desel)
            self._rl_row1.addWidget(self.btn_inv)
            self._rl_row2.addWidget(self.btn_copy)
            self._rl_row2.addWidget(self.btn_copy_last)
            self._rl_row2.addWidget(self._rl_sep3)
            self._rl_row2.addWidget(self.btn_create_crate)
            self._rl_row2.addWidget(self.btn_create_crate_clean)
            self._rl_row2.addWidget(self.btn_save_missing)
            self._rl_row2.addStretch()
            self._rl_sep2.hide()
            self._rl_sep3.show()
            self._rl_row2_widget.setVisible(True)
            self._rl_row3_widget.setVisible(False)
        else:
            self._rl_row1.addWidget(self._btn_results_fs)
            self._rl_row1.addWidget(self.result_stats)
            self._rl_row1.addStretch()
            self._rl_row2.addWidget(self._select_threshold_group)
            self._rl_row2.addWidget(self.btn_desel)
            self._rl_row2.addWidget(self.btn_inv)
            self._rl_row2.addStretch()
            self._rl_row3.addWidget(self.btn_copy)
            self._rl_row3.addWidget(self.btn_copy_last)
            self._rl_row3.addWidget(self._rl_sep3)
            self._rl_row3.addWidget(self.btn_create_crate)
            self._rl_row3.addWidget(self.btn_create_crate_clean)
            self._rl_row3.addWidget(self.btn_save_missing)
            self._rl_row3.addStretch()
            self._rl_sep2.hide()
            self._rl_sep3.show()
            self._rl_row2_widget.setVisible(True)
            self._rl_row3_widget.setVisible(True)

    def _apply_column_visibility(self):
        """Show/hide table columns based on config visible_columns."""
        vis = self.config.get("visible_columns", {})
        col_map = [
            (COL_LOCK, "lock"), (COL_SELECT, "select"), (COL_SCORE, "score"),
            (COL_FOUND, "found"), (COL_TITOLO_RICHIESTO, "titolo_richiesto"),
            (COL_FILENAME, "filename"), (COL_ARTISTA_SERATO, "artista_serato"),
            (COL_SONG_SERATO, "song_serato"), (COL_GENRE, "genre"),
            (COL_BPM, "bpm"), (COL_COMMENT, "comment"), (COL_PLAYER, "player"),
            (COL_HOTCUE, "hotcue"),
        ]
        default_hidden = {"hotcue"}
        for col_idx, key in col_map:
            hidden = not vis.get(key, key not in default_hidden)
            self.results_table.setColumnHidden(col_idx, hidden)
        self.results_table._fit_columns_to_viewport()

    # ------------------------------------------------------------------
    # Settings & Guide
    # ------------------------------------------------------------------

    def _open_settings(self):
        dlg = SettingsDialog(self.config, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_cfg = dlg.get_config()
            old_theme = self.config.get("theme", "light")
            old_size = self.config.get("font_size", 11)
            old_lang = self.config.get("language", "auto")
            old_fit = self.config.get("table_fit_columns", False)
            self.config.update(new_cfg)
            if dlg._cfg.get("settings_dialog_size"):
                self.config["settings_dialog_size"] = dlg._cfg["settings_dialog_size"]
            save_config(self.config)
            if new_cfg.get("theme") != old_theme or new_cfg.get("font_size") != old_size:
                self._apply_theme(new_cfg["theme"])
            self._apply_column_visibility()
            self.results_table.refresh_hotcue_column()
            if new_cfg.get("table_fit_columns", False) != old_fit:
                self.results_table.apply_fit_columns(new_cfg.get("table_fit_columns", False))
            if new_cfg.get("language") != old_lang:
                set_language(new_cfg["language"])
                self._retranslate_ui()

    def _open_quick_guide(self):
        QuickGuideDialog(self, theme=self._current_theme).exec()

    def _auto_load_library(self):
        mf = self.music_folder_input.text().strip()
        if mf and os.path.isdir(mf):
            self._logger.info("Auto-caricamento libreria: %s", mf)
            QTimer.singleShot(100, lambda: self._load_or_scan_library(mf))

    # ------------------------------------------------------------------
    # Serato detection
    # ------------------------------------------------------------------

    def _update_serato_label(self):
        fs = self.config.get("font_size", 11)
        p = ui_theme.palette()
        base = f"font-weight: bold; font-size: {fs}px; font-style: italic;"
        if self.serato_subcrates:
            serato_drive = get_drive_letter(self.serato_subcrates)
            music_drive = get_drive_letter(self.music_folder_input.text().strip())
            if serato_drive and music_drive and serato_drive != music_drive:
                self.serato_label.setText(
                    tr("serato_wrong_drive", serato=serato_drive, music=music_drive)
                )
                self.serato_label.setStyleSheet(base + f" color: {p['danger']};")
            else:
                self.serato_label.setText(tr("serato_ok", path=self.serato_subcrates))
                self.serato_label.setStyleSheet(base.replace("italic;", "") + f" color: {p['success']};")
        else:
            self.serato_label.setText(tr("serato_not_detected_full"))
            self.serato_label.setStyleSheet(base + f" color: {p['danger']};")

    def _resolve_paths_by_volume_label(self):
        """Auto-remap saved paths when the external HDD drive letter changed.

        Called early in startup. If the saved music_folder or serato_folder
        no longer exist (because the user plugged the external HDD into a
        different USB port and Windows assigned a different drive letter),
        try to find a drive with the same Windows volume label and update
        both the config and the in-memory state.

        Returns True if at least one path was remapped.
        """
        remapped_any = False

        # --- Music folder ---
        saved_music = self.config.get("music_folder", "")
        saved_music_label = self.config.get("music_folder_volume_label", "")
        if saved_music and not os.path.isdir(saved_music) and saved_music_label:
            new_music = remap_path_to_current_drive(saved_music, saved_music_label)
            if new_music and new_music != saved_music:
                old_letter = get_drive_letter(saved_music)
                new_letter = get_drive_letter(new_music)
                self._logger.info(
                    "Music folder auto-remapped by volume label '%s': '%s' -> '%s'",
                    saved_music_label, saved_music, new_music
                )
                # Migrate the library cache file from the old path hash
                # to the new one, so the user doesn't have to re-scan
                # a 6000-track library just because they plugged the HDD
                # into a different USB port.
                try:
                    old_cache = self._get_cache_path(saved_music)
                    new_cache = self._get_cache_path(new_music)
                    if os.path.exists(old_cache) and not os.path.exists(new_cache):
                        import shutil
                        shutil.move(old_cache, new_cache)
                        self._logger.info(
                            "Library cache migrated: %s -> %s",
                            os.path.basename(old_cache),
                            os.path.basename(new_cache),
                        )
                except Exception as e:
                    self._logger.warning("Cache migration failed (non-fatal): %s", e)

                self.config["music_folder"] = new_music
                self.music_folder_input.setText(new_music)
                self.statusBar().showMessage(
                    f"Disco esterno rilevato su {new_letter}: (era {old_letter}:)"
                )
                save_config(self.config)
                remapped_any = True

        # --- Serato folder ---
        saved_serato = self.config.get("serato_folder", "")
        saved_serato_label = self.config.get("serato_folder_volume_label", "")
        if saved_serato and not os.path.isdir(saved_serato) and saved_serato_label:
            new_serato = remap_path_to_current_drive(saved_serato, saved_serato_label)
            if new_serato and new_serato != saved_serato:
                self._logger.info(
                    "Serato folder auto-remapped by volume label '%s': '%s' -> '%s'",
                    saved_serato_label, saved_serato, new_serato
                )
                self.config["serato_folder"] = new_serato
                self.serato_subcrates = new_serato
                save_config(self.config)
                remapped_any = True

        # Also handle the case where music_folder was remapped but serato_folder
        # was set to the OLD music drive — in that case, re-derive serato subcrates
        # from the NEW music folder. This handles the common case where the user
        # had both on the same external HDD and never set serato_folder explicitly.
        if saved_music and not saved_serato:
            new_music_now = self.config.get("music_folder", "")
            if new_music_now and new_music_now != saved_music:
                # The music folder was just remapped — re-detect Serato
                detected = find_serato_subcrates(new_music_now)
                if detected:
                    self._logger.info(
                        "Serato folder re-detected on new music drive: %s",
                        detected
                    )
                    self.serato_subcrates = detected
                    self.config["serato_folder"] = detected
                    self.config["serato_folder_volume_label"] = get_volume_label(detected)
                    save_config(self.config)
                    remapped_any = True

        return remapped_any

    def _check_serato(self):
        # First, try to auto-remap paths if drive letters have changed
        # (external HDD plugged into a different USB port).
        self._resolve_paths_by_volume_label()

        self.serato_subcrates = find_serato_subcrates(
            self.config.get("music_folder", "")
        )
        if not self.serato_subcrates and self.config.get("serato_folder"):
            path = self.config["serato_folder"]
            if os.path.isdir(path):
                self.serato_subcrates = path
        self._update_serato_label()

    def _browse_serato_folder(self):
        # Default the file dialog to the current music folder's drive, so
        # the user lands on the right external HDD when picking the Serato
        # subcrates folder.
        start_dir = self.music_folder_input.text().strip() or ""
        if not start_dir or not os.path.isdir(start_dir):
            start_dir = os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(
            self, tr("dlg_select_serato"), start_dir,
            QFileDialog.Option.ShowDirsOnly,
        )
        if folder:
            self.serato_subcrates = folder
            self.config["serato_folder"] = folder
            # Save the volume label so we can auto-remap on next launch
            # if the drive letter changes.
            self.config["serato_folder_volume_label"] = get_volume_label(folder)
            save_config(self.config)
            self._update_serato_label()

    # ------------------------------------------------------------------
    # Library management
    # ------------------------------------------------------------------

    def _browse_music_folder(self):
        # Start the file dialog on the current music folder (or home if empty)
        # so the user can re-pick the same drive after a USB port change.
        start_dir = self.music_folder_input.text().strip() or ""
        if not start_dir or not os.path.isdir(start_dir):
            start_dir = os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(
            self, tr("dlg_select_music"), start_dir,
        )
        if folder:
            self.music_folder_input.setText(folder)
            self.config["music_folder"] = folder
            # Save the volume label of the drive hosting this folder.
            # On Windows, this lets us auto-remap the path on next launch
            # if the external HDD is plugged into a different USB port and
            # gets assigned a new drive letter.
            self.config["music_folder_volume_label"] = get_volume_label(folder)
            # If the music folder is on a different drive than the saved
            # serato_folder, reset serato_folder so it gets re-detected
            # on the new music drive (otherwise we'd keep showing the
            # "WRONG DRIVE" warning).
            saved_serato = self.config.get("serato_folder", "")
            if saved_serato:
                serato_drive = get_drive_letter(saved_serato)
                music_drive = get_drive_letter(folder)
                if serato_drive and music_drive and serato_drive != music_drive:
                    self._logger.info(
                        "Music folder changed drive (%s -> %s); resetting serato_folder",
                        serato_drive, music_drive
                    )
                    self.config["serato_folder"] = ""
                    self.config["serato_folder_volume_label"] = ""
            save_config(self.config)
            self.statusBar().showMessage(tr("status_folder", folder=folder))
            self._library_cache_loaded = False
            self._update_scan_button_text()
            # Re-detect Serato subcrates on the new music drive
            self._check_serato()

    def _get_cache_path(self, folder: str) -> str:
        folder_hash = hashlib.md5(folder.encode("utf-8")).hexdigest()[:12]
        return os.path.join(get_config_dir(), f"library_cache_{folder_hash}.pkl")

    def _save_library_cache(self, tracks: list, folder: str):
        try:
            cache_data = {
                "folder": folder,
                "timestamp": datetime.now().isoformat(),
                "track_count": len(tracks),
                "tracks": tracks,
            }
            with open(self._get_cache_path(folder), "wb") as f:
                pickle.dump(cache_data, f, protocol=pickle.HIGHEST_PROTOCOL)
            self._logger.info("Cache libreria salvata: %d tracce", len(tracks))
        except Exception as e:
            self._logger.warning("Impossibile salvare cache: %s", e)

    def _load_library_cache(self, folder: str) -> Optional[list]:
        try:
            path = self._get_cache_path(folder)
            if not os.path.exists(path):
                return None
            with open(path, "rb") as f:
                data = pickle.load(f)
            if data.get("folder") != folder:
                return None
            tracks = data.get("tracks", [])
            if not tracks:
                return None
            self._logger.info(
                "Cache libreria caricata: %d tracce (salvata: %s)",
                len(tracks), data.get("timestamp", "sconosciuto"),
            )
            return tracks
        except Exception as e:
            self._logger.warning("Impossibile caricare cache: %s", e)
            return None

    def _load_or_scan_library(self, folder: str):
        cached = self._load_library_cache(folder)
        if cached is not None:
            self.library_tracks = cached
            self._library_cache_loaded = True
            self._refresh_library_status()
            self.btn_match.setEnabled(True)
            self._update_scan_button_text()
            self._check_serato()
            self.statusBar().showMessage(tr("status_library_cache", count=len(cached)))
            return
        self._scan_library()

    def _scan_library(self):
        folder = self.music_folder_input.text().strip()
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self, tr("title_attention"), tr("msg_select_music_folder"))
            return

        fs = self.config.get("font_size", 11)
        self.library_status.setText(tr("library_scanning"))
        self.library_status.setStyleSheet(
            f"color: #4927af; font-weight: bold; font-size: {fs}px;"
        )
        self.btn_match.setEnabled(False)
        self.match_progress.setVisible(True)
        self.match_progress.setValue(0)

        self._scan_worker = LibraryScanWorker(folder, self.config)
        self._scan_worker.progress.connect(self._on_scan_progress)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.error.connect(self._on_scan_error)
        self._scan_worker.start()
        self.statusBar().showMessage(tr("status_scanning"))
        self._show_busy(tr("busy_scanning"))

    def _on_scan_progress(self, current, total, message):
        if total > 0:
            self.match_progress.setMaximum(total)
            self.match_progress.setValue(current)
        self.statusBar().showMessage(message)

    def _on_scan_finished(self, tracks):
        self._hide_busy()
        self._hotcue_cache = {}  # library changed: invalidate hotcue counts
        folder = self.music_folder_input.text().strip()
        self.library_tracks = tracks
        self._library_cache_loaded = False
        self._refresh_library_status()
        self.btn_match.setEnabled(True)
        self.match_progress.setVisible(False)
        self._update_scan_button_text()
        self._check_serato()
        self._save_library_cache(tracks, folder)
        self._library_cache_loaded = True

        total_size = sum(t.file_size for t in tracks) / (1024 * 1024)
        # Use scan worker's reader for accurate stats (BUG-015 fix)
        scan_reader = getattr(self._scan_worker, '_reader', None) or LibraryReader(self.config)
        stats = scan_reader.get_stats()
        self.statusBar().showMessage(
            f"Libreria: {len(tracks)} tracce ({total_size:.0f} MB) | "
            f"BPM: {stats['has_bpm']} | Key: {stats['has_key']} | Comment: {stats['has_comment']}"
        )

        if not getattr(self, "_auto_scan_done", False):
            self._auto_scan_done = True
            QMessageBox.information(
                self, tr("title_library_loaded"),
                tr(
                    "msg_library_loaded",
                    tracks=len(tracks),
                    bpm=stats['has_bpm'],
                    key=stats['has_key'],
                    comment=stats['has_comment'],
                ),
            )

    def _on_scan_error(self, message):
        self._hide_busy()
        fs = self.config.get("font_size", 11)
        self.library_status.setText(tr("library_scan_error"))
        self.library_status.setStyleSheet(
            f"color: #c0392b; font-weight: bold; font-size: {fs}px;"
        )
        self.match_progress.setVisible(False)
        QMessageBox.critical(self, tr("title_error"), message)

    # ------------------------------------------------------------------
    # Playlist management
    # ------------------------------------------------------------------

    def _load_playlist_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Carica Playlist", os.path.expanduser("~"),
            "Playlist (*.txt *.csv *.m3u *.m3u8);;All (*)",
        )
        if not filepath:
            return
        for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                with open(filepath, "r", encoding=enc) as f:
                    self.playlist_input.setPlainText(f.read())
                break
            except UnicodeDecodeError:
                continue

    def _clear_playlist(self):
        self.playlist_input.clear()
        self.results_table.setRowCount(0)
        self.match_results = []
        self._update_action_buttons(False)
        self.tabs.setTabEnabled(1, False)

    def _import_from_url(self):
        dialog = ImportUrlDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.imported_tracks:
            current = self.playlist_input.toPlainText().strip()
            new_lines = "\n".join(dialog.imported_tracks)
            self.playlist_input.setPlainText(
                f"{current}\n{new_lines}" if current else new_lines
            )
            total = len(self.playlist_input.toPlainText().strip().splitlines())
            self.statusBar().showMessage(
                f"Importati {len(dialog.imported_tracks)} brani da {dialog._source}. "
                f"Totale righe: {total}"
            )

    def _show_format_guide(self):
        FormatGuideDialog(self).exec()

    def _show_algorithm_doc(self):
        AlgorithmDialog(self, theme=self._current_theme).exec()

    def _clean_library(self):
        """Open the clean-library search dialog and fill the Editing tab.

        Search logic (OR): a track is listed when it contains the searched word
        (in title / artist / album / filename) OR — when the checkbox is on — it
        carries mojibake markers in any of those tag fields.
        """
        if not self.library_tracks:
            QMessageBox.warning(self, tr("title_attention"), tr("msg_scan_first"))
            return

        dialog = CleanLibraryDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self._last_search_word = dialog.search_word
        word = dialog.search_word.lower()
        detect = dialog.detect_mojibake
        if not word and not detect:
            QMessageBox.information(
                self, tr("clean_lib_title"), tr("clean_lib_need_criteria")
            )
            return

        def work():
            matches = []
            for t in self.library_tracks:
                fields = (t.title or "", t.artist or "", t.album or "")
                fname = os.path.basename(t.filepath or "")
                has_moji = detect and any(("Ã" in f or "Â" in f) for f in fields)
                has_word = bool(word) and any(
                    word in f.lower() for f in (fields + (fname,))
                )
                if has_moji or has_word:
                    matches.append(t)
            if not matches:
                return None
            for t in matches:
                self._hotcue_count(t.filepath or "")  # warm cache while busy
            self._populate_editing_table(matches)
            return matches

        matches = self._run_busy(tr("busy_clean_lib"), work)
        if not matches:
            QMessageBox.information(
                self, tr("clean_lib_title"), tr("clean_lib_none_found")
            )
            return

        self._editing_mode = "clean"
        self.tabs.setTabEnabled(2, True)
        self.tabs.setCurrentIndex(2)

    def _find_differences(self):
        """List tracks that are in the music folder but NOT in the Serato library."""
        if not self.library_tracks:
            QMessageBox.warning(self, tr("title_attention"), tr("msg_scan_first"))
            return

        folder = self.music_folder_input.text().strip()
        db_path = serato_database.find_database_file(folder)
        if not db_path:
            QMessageBox.warning(
                self, tr("find_diff_title"), tr("find_diff_no_db")
            )
            return

        total = len(self.library_tracks)

        def work():
            serato_set = serato_database.read_database_normalized_set(db_path)
            return [
                t for t in self.library_tracks
                if serato_database.normalize_rel_path(t.filepath or "") not in serato_set
            ]

        try:
            missing = self._run_busy(tr("busy_find_diff"), work)
        except Exception as e:
            QMessageBox.critical(self, tr("title_error"), str(e))
            return

        if not missing:
            QMessageBox.information(
                self, tr("find_diff_title"), tr("find_diff_none", total=total)
            )
            return

        # Show the missing tracks in the RESULTS tab so the user can reuse the
        # existing "Create crate" action to import them into Serato in one go.
        results = []
        for t in missing:
            if t.artist and t.title:
                disp = f"{t.artist} - {t.title}"
            else:
                disp = t.title or os.path.basename(t.filepath or "")
            pt = PlaylistTrack(artist=t.artist or "", title=t.title or "", original_line=disp)
            cand = CandidateMatch(library_track=t, score=100, confidence=MatchConfidence.EXACT)
            results.append(MatchResult(playlist_track=pt, candidates=[cand]))

        self.match_results = results
        self.results_table._original_order = {}
        self.results_table.populate(results)
        self._apply_column_visibility()
        self._refresh_stats()
        self.tabs.setTabEnabled(1, True)
        self.tabs.setCurrentIndex(1)
        self._update_action_buttons(True)
        self.statusBar().showMessage(
            tr("find_diff_status", count=len(missing), total=total)
        )

    def _find_duplicates(self):
        """Show tracks that appear more than once (same title + artist)."""
        if not self.library_tracks:
            QMessageBox.warning(self, tr("title_attention"), tr("msg_scan_first"))
            return

        def work():
            groups = {}
            for t in self.library_tracks:
                # Ignore parenthetical descriptors: "(Original Mix)" etc.
                key = (normalize_string(t.title), normalize_string(t.artist))
                if not key[0] and not key[1]:
                    continue  # no identity -> can't judge duplication
                groups.setdefault(key, []).append(t)

            dups = []
            for _key, items in groups.items():
                if len(items) > 1:
                    dups.extend(items)
            if not dups:
                return None

            dups.sort(key=lambda t: (
                (t.title or "").lower(),
                (t.artist or "").lower(),
                (t.filepath or "").lower(),
            ))
            for t in dups:
                self._hotcue_count(t.filepath or "")  # warm cache while busy
            self._last_search_word = ""
            self._populate_editing_table(dups)
            return dups

        dups = self._run_busy(tr("busy_duplicates"), work)
        if not dups:
            self._editing_mode = ""
            self.editing_status.setText(tr("dup_none"))
            QMessageBox.information(self, tr("btn_duplicates"), tr("dup_none"))
            return

        self._editing_mode = "duplicates"
        self.editing_status.setText(tr("dup_status", count=len(dups)))
        self.tabs.setTabEnabled(2, True)
        self.tabs.setCurrentIndex(2)

    def _populate_editing_table(self, tracks):
        """Fill the Editing table from a fresh list of library tracks."""
        self._editing_saved_paths = set()
        self._editing_sort = (None, True)
        self.editing_table.horizontalHeader().setSortIndicatorShown(False)
        entries = [
            {"track": t, "title": t.title or "", "artist": t.artist or "",
             "album": t.album or "", "genre": t.genre or ""}
            for t in tracks
        ]
        self._populate_editing_entries(entries)
        self.editing_table.horizontalHeader().setSortIndicatorShown(True)

    def _populate_editing_entries(self, entries):
        """(Re)build the Editing table rows from entry dicts.

        Used by the initial fill and by column sorting (which re-reads the current
        cell values, sorts them, and rebuilds so the button columns stay aligned).
        """
        table = self.editing_table
        table.setRowCount(0)
        table.setRowCount(len(entries))
        self._row_tracks = [e["track"] for e in entries]
        saved = getattr(self, "_editing_saved_paths", set())
        saved_hex = "#1a3325" if self._is_dark_theme() else "#eafaf1"

        for row, entry in enumerate(entries):
            track = entry["track"]
            fname = os.path.basename(track.filepath or "")
            file_item = QTableWidgetItem(fname)
            file_item.setToolTip(track.filepath or "")
            file_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            table.setItem(row, E_COL_FILE, file_item)

            for col, field in ((E_COL_TITLE, "title"), (E_COL_ARTIST, "artist"),
                               (E_COL_ALBUM, "album"), (E_COL_GENRE, "genre")):
                item = QTableWidgetItem(entry.get(field, "") or "")
                item.setFlags(
                    Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsEditable
                )
                table.setItem(row, col, item)

            hc = self._hotcue_count(track.filepath or "")
            hc_item = QTableWidgetItem("?" if hc is None else str(hc))
            hc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            hc_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            table.setItem(row, E_COL_HOTCUE, hc_item)

            if (track.filepath or "") in saved:
                color = QColor(saved_hex)
                for col in (E_COL_FILE,) + E_EDITABLE_COLS:
                    it = table.item(row, col)
                    if it is not None:
                        it.setBackground(color)

            path = track.filepath or ""
            loc_btn = QPushButton(path)
            loc_btn.setToolTip(path + "\n" + tr("edit_open_location_tt"))
            loc_btn.setStyleSheet("text-align: left; padding: 1px 8px;")
            loc_btn.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            loc_btn.clicked.connect(lambda _=False, p=path: self._open_file_location(p))
            table.setCellWidget(row, E_COL_LOCATION, loc_btn)

            btn = QPushButton(tr("edit_confirm_btn"))
            btn.setObjectName("successBtn")
            btn.clicked.connect(
                lambda _=False, r=row, t=track: self._editing_confirm_row(r, t)
            )
            table.setCellWidget(row, E_COL_ACTION, btn)

            del_btn = QPushButton(tr("edit_delete_btn"))
            del_btn.setStyleSheet(
                "QPushButton { background: #c0392b; color: #fff; border: none;"
                " border-radius: 4px; padding: 3px 8px; }"
                " QPushButton:hover { background: #e74c3c; }"
            )
            del_btn.clicked.connect(
                lambda _=False, t=track: self._editing_delete_row(t)
            )
            table.setCellWidget(row, E_COL_DELETE, del_btn)
            table.setRowHeight(row, 34)

        has_rows = len(entries) > 0
        self._btn_edit_save_all.setEnabled(has_rows)
        self._btn_edit_replace.setEnabled(has_rows)
        self._btn_edit_copy.setEnabled(has_rows)
        self._btn_update_serato.setEnabled(has_rows)
        self.editing_status.setText(tr("edit_status_count", count=len(entries)))

    def _capture_editing_entries(self):
        """Read the current cell values (including unsaved edits) into entries."""
        table = self.editing_table
        entries = []
        for row in range(table.rowCount()):
            def _txt(col):
                it = table.item(row, col)
                return it.text() if it is not None else ""
            entries.append({
                "track": self._row_tracks[row],
                "title": _txt(E_COL_TITLE), "artist": _txt(E_COL_ARTIST),
                "album": _txt(E_COL_ALBUM), "genre": _txt(E_COL_GENRE),
            })
        return entries

    def _sort_editing(self, col):
        """Sort the Editing table alphabetically by a column (except 'Action')."""
        if col in (E_COL_ACTION, E_COL_DELETE) or self.editing_table.rowCount() == 0:
            return
        prev_col, prev_asc = getattr(self, "_editing_sort", (None, True))
        ascending = (not prev_asc) if prev_col == col else True

        entries = self._capture_editing_entries()

        def sort_key(e):
            t = e["track"]
            if col == E_COL_FILE:
                return os.path.basename(t.filepath or "").lower()
            if col == E_COL_TITLE:
                return (e["title"] or "").lower()
            if col == E_COL_ARTIST:
                return (e["artist"] or "").lower()
            if col == E_COL_ALBUM:
                return (e["album"] or "").lower()
            if col == E_COL_GENRE:
                return (e["genre"] or "").lower()
            if col == E_COL_HOTCUE:
                c = self._hotcue_count(t.filepath or "")
                return c if isinstance(c, int) else -1
            return (t.filepath or "").lower()   # E_COL_LOCATION

        entries.sort(key=sort_key, reverse=not ascending)
        self._editing_sort = (col, ascending)
        self._populate_editing_entries(entries)
        order = Qt.SortOrder.AscendingOrder if ascending else Qt.SortOrder.DescendingOrder
        self.editing_table.horizontalHeader().setSortIndicator(col, order)

    def _row_values(self, row):
        table = self.editing_table
        def _txt(col):
            it = table.item(row, col)
            return it.text() if it is not None else ""
        return (_txt(E_COL_TITLE), _txt(E_COL_ARTIST),
                _txt(E_COL_ALBUM), _txt(E_COL_GENRE))

    def _hotcue_count(self, path):
        """Number of Serato hotcues for a file (cached). None if unknown."""
        if not path:
            return None
        if not hasattr(self, "_hotcue_cache"):
            self._hotcue_cache = {}
        if path not in self._hotcue_cache:
            try:
                self._hotcue_cache[path] = LibraryReader.count_hotcues(path)
            except Exception:
                self._hotcue_cache[path] = None
        return self._hotcue_cache[path]

    def _open_file_location(self, path: str):
        """Open the containing folder with the file selected (like Explorer)."""
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, tr("title_attention"), path or "")
            return
        try:
            if sys.platform.startswith("win"):
                import subprocess
                subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", "-R", path])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", os.path.dirname(path)])
        except Exception:
            try:
                os.startfile(os.path.dirname(path))  # type: ignore[attr-defined]
            except Exception:
                pass

    def _write_editing_row(self, row, track):
        """Write one row's tags to disk and refresh its visuals.

        Returns ``(ok, msg)``; does NOT touch the cache or show dialogs so it can
        be reused both by the per-row button and the 'Save all' action.
        """
        new_title, new_artist, new_album, new_genre = self._row_values(row)

        # Release the audio player if it currently holds this file (Windows would
        # otherwise lock it and the tag write would fail).
        try:
            if self._player.source() == QUrl.fromLocalFile(track.filepath):
                self._player.stop()
                self._player.setSource(QUrl())
        except Exception:
            pass

        ok, msg = LibraryReader.set_tags(
            track.filepath, title=new_title, artist=new_artist,
            album=new_album, genre=new_genre
        )
        if not ok:
            return (False, msg)

        track.title = new_title
        track.artist = new_artist
        track.album = new_album
        track.genre = new_genre
        if not hasattr(self, "_editing_saved_paths"):
            self._editing_saved_paths = set()
        self._editing_saved_paths.add(track.filepath or "")

        table = self.editing_table
        color = QColor("#1a3325" if self._is_dark_theme() else "#eafaf1")
        for col in (E_COL_FILE,) + E_EDITABLE_COLS:
            it = table.item(row, col)
            if it is not None:
                it.setBackground(color)
        return (True, msg)

    def _save_editing_cache(self):
        folder = self.music_folder_input.text().strip()
        if folder:
            try:
                self._save_library_cache(self.library_tracks, folder)
            except Exception:
                pass

    def _editing_confirm_row(self, row, track):
        ok, msg = self._write_editing_row(row, track)
        if not ok:
            QMessageBox.critical(
                self, tr("title_error"), tr("edit_saved_err", error=msg)
            )
            return
        self._save_editing_cache()
        name = f"{track.artist} - {track.title}".strip(" -")
        self.statusBar().showMessage(tr("edit_saved_ok", name=name))

    def _editing_delete_row(self, track):
        """Send the track's file to the Recycle Bin and purge it from Serato.

        Cleans Serato thoroughly: removes the entry from the ``database V2`` AND
        from every ``.crate`` file, so the track never reappears (e.g. in the
        Duplicates view). Serato must be closed. Files that are already in the
        Recycle Bin are treated as deleted and the Serato clean-up still runs.
        """
        path = getattr(track, "filepath", "") or ""
        if not path:
            return

        if QMessageBox.question(
            self, tr("edit_delete_btn"),
            tr("edit_delete_confirm", name=os.path.basename(path)),
        ) != QMessageBox.StandardButton.Yes:
            return

        # We are going to edit Serato's database/crates, which requires Serato to
        # be closed (otherwise it would rewrite them on exit and undo our work).
        folder = self.music_folder_input.text().strip()
        if serato_database.is_serato_running():
            QMessageBox.warning(
                self, tr("edit_delete_btn"), tr("update_serato_running")
            )
            return

        # Release the audio player if it currently holds this file.
        try:
            if self._player.source() == QUrl.fromLocalFile(path):
                self._player.stop()
                self._player.setSource(QUrl())
        except Exception:
            pass

        # Move to the Recycle Bin. If the file is missing or already sitting in a
        # trash folder, treat it as already deleted and keep cleaning Serato.
        already_trashed = ("$recycle.bin" in path.lower()
                           or "/.trash" in path.lower().replace("\\", "/"))
        if os.path.exists(path) and not already_trashed:
            try:
                move_to_recycle_bin(path)
            except Exception as e:
                QMessageBox.critical(
                    self, tr("title_error"), tr("edit_delete_err", error=str(e))
                )
                return

        # Purge from Serato thoroughly: EVERY 'database V2' (the home/master library
        # plus each per-drive one) AND every .crate file. Serato's browser reads
        # from the master DB too, so cleaning only the music-drive DB left the
        # track visible. Back up once per session.
        first = not getattr(self, "_delete_backup_done", False)
        try:
            serato_database.remove_from_all_databases(folder, [path], backup=first)
        except Exception:
            pass
        try:
            serato_database.remove_from_crates(folder, [path])
        except Exception:
            pass
        self._delete_backup_done = True

        # Drop from the in-memory library + cache so it won't reappear (e.g. in
        # the Duplicates view) without needing a rescan.
        try:
            self.library_tracks = [t for t in self.library_tracks if t is not track]
        except Exception:
            pass
        self._save_editing_cache()

        self.statusBar().showMessage(
            tr("edit_deleted", name=os.path.basename(path))
        )

        # In the Duplicates view, re-run the duplicate scan so the table always
        # reflects the current library (a track may stop being a duplicate once
        # its twin is deleted). Otherwise just drop this row from the table.
        if getattr(self, "_editing_mode", "") == "duplicates":
            self._find_duplicates()
        else:
            entries = [e for e in self._capture_editing_entries()
                       if e["track"] is not track]
            self._populate_editing_entries(entries)

    def _editing_save_all(self):
        tracks = getattr(self, "_row_tracks", [])
        if not tracks:
            return
        total = len(tracks)
        if QMessageBox.question(
            self, tr("clean_lib_title"), tr("edit_save_all_confirm", total=total)
        ) != QMessageBox.StandardButton.Yes:
            return

        ok_count = 0
        failures = []
        for row in range(self.editing_table.rowCount()):
            track = self._row_tracks[row]
            ok, msg = self._write_editing_row(row, track)
            if ok:
                ok_count += 1
            else:
                failures.append(f"  • {os.path.basename(track.filepath or '')}: {msg}")

        self._save_editing_cache()

        if failures:
            QMessageBox.warning(
                self, tr("clean_lib_title"),
                tr(
                    "edit_save_all_errors",
                    ok=ok_count, total=total,
                    failed=len(failures), details="\n".join(failures[:15]),
                ),
            )
        else:
            QMessageBox.information(
                self, tr("clean_lib_title"),
                tr("edit_save_all_done", ok=ok_count, total=total),
            )

    def _update_serato_database(self):
        """Write the metadata of the *saved* table rows into Serato's DB.

        Requires Serato to be closed. Only the tracks whose edits were actually
        saved to disk (green rows) are synced, using their in-memory tag values so
        the database stays consistent with the files.
        """
        tracks = getattr(self, "_row_tracks", [])
        if not tracks:
            return

        # Only tracks that have been saved to disk in this session.
        saved_paths = getattr(self, "_editing_saved_paths", set())
        saved_tracks = [t for t in tracks if (t.filepath or "") in saved_paths]
        if not saved_tracks:
            QMessageBox.information(
                self, tr("edit_update_serato_btn"), tr("update_serato_no_saved")
            )
            return

        if serato_database.is_serato_running():
            QMessageBox.warning(
                self, tr("edit_update_serato_btn"), tr("update_serato_running")
            )
            return

        folder = self.music_folder_input.text().strip()
        if not serato_database.find_all_database_files(folder):
            QMessageBox.warning(
                self, tr("edit_update_serato_btn"), tr("update_serato_no_db")
            )
            return

        if QMessageBox.question(
            self, tr("edit_update_serato_btn"),
            tr("update_serato_confirm", count=len(saved_tracks)),
        ) != QMessageBox.StandardButton.Yes:
            return

        updates = {}
        for track in saved_tracks:
            rel = serato_database.normalize_rel_path(track.filepath or "")
            if rel:
                updates[rel] = {
                    "title": track.title or "",
                    "artist": track.artist or "",
                    "album": track.album or "",
                    "genre": track.genre or "",
                }

        try:
            updated, backup = self._run_busy(
                tr("busy_update_serato"),
                lambda: serato_database.update_all_databases_metadata(folder, updates),
            )
        except Exception as e:
            QMessageBox.critical(self, tr("title_error"), str(e))
            return

        if updated == 0:
            QMessageBox.information(
                self, tr("edit_update_serato_btn"), tr("update_serato_none")
            )
        else:
            QMessageBox.information(
                self, tr("edit_update_serato_btn"),
                tr("update_serato_done", count=updated, backup=backup),
            )

    def _editing_replace(self):
        tracks = getattr(self, "_row_tracks", [])
        if not tracks:
            return
        dialog = ReplaceDialog(self, find_default=getattr(self, "_last_search_word", ""))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        find = dialog.find_text
        if not find:
            QMessageBox.information(
                self, tr("replace_dialog_title"), tr("replace_need_find")
            )
            return
        replacement = dialog.replace_text

        pattern = re.compile(re.escape(find), re.IGNORECASE)
        changed = 0
        table = self.editing_table
        for row in range(table.rowCount()):
            for col in E_EDITABLE_COLS:
                it = table.item(row, col)
                if it is None:
                    continue
                old = it.text()
                new = pattern.sub(replacement, old)
                if new != old:
                    new = re.sub(r"\s{2,}", " ", new).strip()
                    it.setText(new)
                    changed += 1

        QMessageBox.information(
            self, tr("replace_dialog_title"), tr("replace_done", count=changed)
        )

    def _editing_copy_list(self):
        tracks = getattr(self, "_row_tracks", [])
        if not tracks:
            return
        menu = QMenu(self)
        act_files = menu.addAction(tr("edit_copy_filenames"))
        act_titles = menu.addAction(tr("edit_copy_titles"))
        chosen = menu.exec(self._btn_edit_copy.mapToGlobal(
            self._btn_edit_copy.rect().bottomLeft()
        ))
        if chosen is None:
            return

        if chosen == act_files:
            lines = [os.path.basename(t.filepath or "") for t in tracks]
        else:
            table = self.editing_table
            lines = []
            for row in range(table.rowCount()):
                it = table.item(row, E_COL_TITLE)
                lines.append(it.text() if it is not None else "")

        QApplication.clipboard().setText("\n".join(lines))
        self.statusBar().showMessage(tr("edit_copied", count=len(lines)))

    def _is_dark_theme(self) -> bool:
        return getattr(self, "_current_theme", "light") == "dark"

    # ------------------------------------------------------------------
    # Busy indicator (blocks input during long operations)
    # ------------------------------------------------------------------

    def _show_busy(self, message: str):
        """Grey out the UI and show a modal 'please wait' dialog."""
        existing = getattr(self, "_busy_dialog", None)
        if existing is not None:
            existing.set_message(message)
            QApplication.processEvents()
            return
        central = self.centralWidget()
        if central is not None:
            central.setEnabled(False)
        dlg = BusyDialog(message, self)
        self._busy_dialog = dlg
        dlg.show()
        dlg.raise_()
        # Centre over the main window.
        try:
            geo = self.frameGeometry()
            dlg.move(
                geo.center().x() - dlg.width() // 2,
                geo.center().y() - dlg.height() // 2,
            )
        except Exception:
            pass
        QApplication.processEvents()

    def _hide_busy(self):
        dlg = getattr(self, "_busy_dialog", None)
        if dlg is not None:
            dlg.close()
            dlg.deleteLater()
            self._busy_dialog = None
        central = self.centralWidget()
        if central is not None:
            central.setEnabled(True)

    def _run_busy(self, message: str, work_fn):
        """Run a synchronous callable while showing the busy dialog.

        Returns whatever ``work_fn`` returns; always removes the busy state, even
        if the callable raises.
        """
        self._show_busy(message)
        try:
            return work_fn()
        finally:
            self._hide_busy()

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------

    def _run_matching(self):
        text = self.playlist_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, tr("title_attention"), tr("msg_enter_playlist"))
            return
        if not self.library_tracks:
            QMessageBox.warning(self, tr("title_attention"), tr("msg_scan_first"))
            return

        parser = PlaylistParser()
        playlist_tracks = parser.parse(text)
        if not playlist_tracks:
            QMessageBox.warning(self, tr("title_attention"), tr("msg_no_tracks"))
            return

        self.match_progress.setVisible(True)
        self.match_progress.setValue(0)
        self.btn_match.setEnabled(False)
        self._update_action_buttons(False)

        self._match_worker = MatchWorker(
            playlist_tracks, self.library_tracks,
            self.config.get("match_thresholds", {}),
            title_locks=self._title_locks,
            bpm_penalty_enabled=self.config.get("bpm_penalty_enabled", False),
            bpm_reference=self.config.get("bpm_reference", 0),
        )
        self._match_worker.progress.connect(self._on_match_progress)
        self._match_worker.finished.connect(self._on_match_finished)
        self._match_worker.error.connect(self._on_match_error)
        self._match_worker.start()

    def _on_match_progress(self, current, total, message):
        if total > 0:
            self.match_progress.setMaximum(total)
            self.match_progress.setValue(current)
        self.statusBar().showMessage(message)

    def _on_match_finished(self, results):
        self.match_results = results
        matched = sum(1 for r in results if r.is_effectively_matched)
        missing = sum(1 for r in results if not r.is_effectively_matched)

        self.results_table._original_order = {}
        self.results_table.populate(results)
        self._apply_column_visibility()
        self._refresh_stats()
        self.match_progress.setVisible(False)
        self.btn_match.setEnabled(True)

        self.tabs.setTabEnabled(1, True)
        self.tabs.setCurrentIndex(1)
        self._update_action_buttons(True)
        self.statusBar().showMessage(
            f"Matching: {matched} trovati, {missing} mancanti. "
            f"Log dettagliato in serato_debug.log"
        )

    def _on_match_error(self, message):
        self.match_progress.setVisible(False)
        self.btn_match.setEnabled(True)
        QMessageBox.critical(self, tr("title_error"), message)

    # ------------------------------------------------------------------
    # Selection & stats
    # ------------------------------------------------------------------

    def _update_select_all_button_label(self, pct_text: str = ""):
        if not hasattr(self, "btn_sel_all"):
            return
        if not pct_text:
            pct_text = self.score_threshold_combo.currentText()
        pct = pct_text.replace("%", "").strip()
        self.btn_sel_all.setText(tr("btn_select_all_ge", pct=pct))
        set_button_alt(self.btn_sel_all, "btn_select_all_tt", pct=pct)

    def _on_select_all(self):
        threshold = self.score_threshold_combo.currentText().replace("%", "")
        try:
            threshold_val = int(threshold)
        except (ValueError, TypeError):
            threshold_val = 50
        self.results_table.select_all_rows(threshold=threshold_val)
        self._refresh_stats()
        self._update_action_buttons(True)

    def _on_deselect_all(self):
        self.results_table.deselect_all_rows()
        self._refresh_stats()
        self._update_action_buttons(True)

    def _on_invert_selection(self):
        self.results_table.invert_selection()
        self._refresh_stats()
        self._update_action_buttons(True)

    def _on_table_selection_changed(self):
        self._refresh_stats()
        self._update_action_buttons(True)

    def _on_copy(self):
        self.results_table.copy_selection()
        self.statusBar().showMessage("Tabella copiata negli appunti.")

    def _on_copy_last(self):
        self.results_table.copy_last_checked()
        self.statusBar().showMessage("Ultima riga spuntata copiata negli appunti.")

    def _refresh_stats(self):
        if not self.match_results:
            self.result_stats.setText("")
            return
        matched = sum(1 for r in self.match_results if r.is_effectively_matched)
        missing = sum(1 for r in self.match_results if not r.is_effectively_matched)
        for_crate = len(self.results_table.get_selected_for_crate())
        for_missing = len(self.results_table.get_selected_for_missing())
        multi = sum(1 for r in self.match_results if r.num_candidates > 1)
        n_locks = len(self._title_locks)
        lock_info = tr("stats_locks", count=n_locks) if n_locks else ""
        self.result_stats.setText(
            tr(
                "stats_line",
                matched=matched,
                missing=missing,
                selected=for_crate,
                excluded=for_missing - missing,
                multi=multi,
                locks=lock_info,
            )
        )

    def _update_action_buttons(self, has_results: bool):
        has_selected = has_results and bool(self.results_table.get_selected_for_crate())
        self.btn_create_crate.setEnabled(has_selected)
        self.btn_create_crate_clean.setEnabled(has_selected)

        # "Salva Mancanti": enabled whenever there are results, disabled only if ALL checked
        if has_results and self.results_table.rowCount() > 0:
            all_checked = all(
                (item := self.results_table.item(i, COL_SELECT))
                and item.checkState() == Qt.CheckState.Checked
                for i in range(self.results_table.rowCount())
            )
            self.btn_save_missing.setEnabled(not all_checked)
        else:
            self.btn_save_missing.setEnabled(False)

        self.btn_copy.setEnabled(has_results)
        self.btn_copy_last.setEnabled(has_results)
        self.btn_sel_all.setEnabled(has_results)
        self.btn_desel.setEnabled(has_results)
        self.btn_inv.setEnabled(has_results)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _create_crate(self):
        selected = self.results_table.get_selected_for_crate()
        if not selected:
            QMessageBox.information(self, tr("title_info"), tr("msg_no_crate_selection"))
            return

        crate_name = self.crate_name_input.text().strip()
        if not crate_name:
            QMessageBox.warning(self, tr("title_attention"), tr("msg_enter_crate_name"))
            return

        music_folder = self.music_folder_input.text().strip()
        if self.serato_subcrates and os.path.isdir(self.serato_subcrates):
            output_dir = self.serato_subcrates
        else:
            output_dir = self.config.get("output_folder", os.path.expanduser("~"))

        is_valid, msg = validate_crate_drive(music_folder, output_dir)
        if not is_valid:
            reply = QMessageBox.critical(
                self, tr("title_wrong_drive"),
                tr("msg_wrong_drive_prompt", msg=msg),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._browse_serato_folder()
                if self.serato_subcrates and os.path.isdir(self.serato_subcrates):
                    is_valid2, msg2 = validate_crate_drive(music_folder, self.serato_subcrates)
                    if not is_valid2:
                        QMessageBox.critical(self, tr("title_error"), tr("msg_wrong_drive_again", msg=msg2))
                        return
                    output_dir = self.serato_subcrates
                else:
                    return
            else:
                return

        writer = CrateWriter()
        crate_path = writer.create_crate_from_results(selected, crate_name, output_dir)

        if crate_path:
            crate_drive = get_drive_letter(output_dir)
            music_drive = get_drive_letter(music_folder)
            drive_info = ""
            if crate_drive and music_drive:
                if crate_drive == music_drive:
                    drive_info = tr("msg_drive_ok", drive=crate_drive)
                else:
                    drive_info = tr("msg_drive_warn", crate=crate_drive, music=music_drive)
            QMessageBox.information(
                self, tr("title_crate_created"),
                tr("msg_crate_ok", name=crate_name, count=len(selected), path=crate_path, drive_info=drive_info),
            )
        else:
            QMessageBox.critical(
                self, tr("title_error"),
                tr("msg_crate_failed"),
            )

    def _save_missing(self):
        missing = self.results_table.get_selected_for_missing()
        if not missing:
            QMessageBox.information(self, tr("title_info"), tr("msg_no_missing"))
            return

        event_name = self.crate_name_input.text().strip() or "Playlist"
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        default_dir = self.config.get("output_folder", os.path.join(os.path.expanduser("~"), "Desktop"))
        if not os.path.isdir(default_dir):
            default_dir = os.path.expanduser("~")

        filepath, _ = QFileDialog.getSaveFileName(
            self, tr("dlg_save_missing"),
            os.path.join(default_dir, f"Brani_Mancanti_{event_name}_{timestamp}.txt"),
            tr("filter_text"),
        )
        if not filepath:
            return

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                for r in missing:
                    line = r.playlist_track.original_line
                    if line:
                        f.write(line + "\n")
            QMessageBox.information(self, tr("title_saved"), tr("msg_saved_missing", path=filepath, count=len(missing)))
        except Exception as e:
            QMessageBox.critical(self, tr("title_error"), str(e))

    # ------------------------------------------------------------------
    # Title Locks — persistent match confirmations
    # ------------------------------------------------------------------

    def _get_title_locks_path(self) -> str:
        return os.path.join(get_config_dir(), "title_locks.json")

    def _load_title_locks(self) -> dict:
        """Load saved title→filepath mappings from JSON file."""
        path = self._get_title_locks_path()
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                locks = data.get("locks", {})
                if isinstance(locks, dict):
                    self._logger.info("Title locks caricati: %d", len(locks))
                    return locks
        except Exception as e:
            self._logger.warning("Impossibile caricare title locks: %s", e)
        return {}

    def _on_lock_changed(self):
        """Called when a lock is toggled — save and track session change."""
        self._locks_changed_in_session = True
        self._save_title_locks()

    def _save_title_locks(self):
        """Persist title→filepath mappings to JSON file."""
        path = self._get_title_locks_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"locks": self._title_locks}, f, indent=2, ensure_ascii=False)
            self._logger.info("Title locks salvati: %d", len(self._title_locks))
        except Exception as e:
            self._logger.warning("Impossibile salvare title locks: %s", e)

    def _create_crate_and_clean(self):
        """Create crate AND remove processed rows from results and playlist."""
        selected = self.results_table.get_selected_for_crate()
        if not selected:
            QMessageBox.information(self, tr("title_info"), tr("msg_no_crate_selection"))
            return

        crate_name = self.crate_name_input.text().strip()
        if not crate_name:
            QMessageBox.warning(self, tr("title_attention"), tr("msg_enter_crate_name"))
            return

        music_folder = self.music_folder_input.text().strip()
        if self.serato_subcrates and os.path.isdir(self.serato_subcrates):
            output_dir = self.serato_subcrates
        else:
            output_dir = self.config.get("output_folder", os.path.expanduser("~"))

        is_valid, msg = validate_crate_drive(music_folder, output_dir)
        if not is_valid:
            reply = QMessageBox.critical(
                self, tr("title_wrong_drive"),
                tr("msg_wrong_drive_prompt", msg=msg),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._browse_serato_folder()
                if self.serato_subcrates and os.path.isdir(self.serato_subcrates):
                    is_valid2, msg2 = validate_crate_drive(music_folder, self.serato_subcrates)
                    if not is_valid2:
                        QMessageBox.critical(self, tr("title_error"), tr("msg_wrong_drive_again", msg=msg2))
                        return
                    output_dir = self.serato_subcrates
                else:
                    return
            else:
                return

        writer = CrateWriter()
        crate_path = writer.create_crate_from_results(selected, crate_name, output_dir)

        if not crate_path:
            QMessageBox.critical(
                self, tr("title_error"),
                tr("msg_crate_failed"),
            )
            return

        # --- Clean: remove selected rows from results AND playlist text ---
        remove_ids = {id(r) for r in selected}
        originals_to_remove = {
            r.playlist_track.original_line.strip()
            for r in selected
            if r.playlist_track.original_line and r.playlist_track.original_line.strip()
        }

        # Remove from match_results
        self.match_results = [r for r in self.match_results if id(r) not in remove_ids]

        # Remove from playlist text
        text = self.playlist_input.toPlainText()
        lines = text.split("\n")
        remaining = [l for l in lines if l.strip() not in originals_to_remove]
        self.playlist_input.setPlainText("\n".join(remaining))

        # Refresh table
        self.results_table._original_order = {}
        self.results_table.populate(self.match_results)
        self._refresh_stats()
        self._update_action_buttons(True)

        n_removed = len(selected)
        QMessageBox.information(
            self, tr("title_crate_clean"),
            tr("msg_crate_clean_ok", name=crate_name, count=n_removed, path=crate_path, removed=n_removed),
        )

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _open_log_file(self):
        if os.path.exists(self._log_path):
            try:
                os.startfile(self._log_path)
            except AttributeError:
                import subprocess
                subprocess.Popen(["notepad", self._log_path])
        else:
            QMessageBox.information(self, tr("title_log"), tr("msg_log_not_found", path=self._log_path))

    def closeEvent(self, event):
        # Stop audio player before closing (no leaks)
        self._player_cleanup()
        # Wait for running workers before closing (BUG-014 fix)
        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.terminate()
            self._scan_worker.wait(2000)
        if self._match_worker and self._match_worker.isRunning():
            self._match_worker.terminate()
            self._match_worker.wait(2000)
        mf = self.music_folder_input.text().strip()
        if mf:
            self.config["music_folder"] = mf
        if hasattr(self, "results_table"):
            self.results_table._save_column_layout()
        save_config(self.config)
        # Ensure title locks are saved before closing
        self._save_title_locks()

        # If locks were changed in this session, offer rescan before closing
        if self._locks_changed_in_session and mf and os.path.isdir(mf):
            if self.config.get("skip_rescan_dialog", False):
                # Use saved default answer — no dialog shown
                if self.config.get("default_rescan_answer", "yes") == "yes":
                    event.ignore()
                    self._rescan_and_close()
                    return
                # else: fall through to event.accept()
            else:
                reply = QMessageBox.question(
                    self,
                    tr("title_rescan"),
                    tr("msg_rescan_close"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    event.ignore()
                    self._rescan_and_close()
                    return

        event.accept()

    def _rescan_and_close(self):
        """Rescan the library with a big centered progress dialog, then close."""
        mf = self.music_folder_input.text().strip()
        if not mf or not os.path.isdir(mf):
            self.close()
            return

        # Prevent closeEvent from asking again after rescan
        self._locks_changed_in_session = False
        self.setEnabled(False)

        # Big centered progress dialog
        self._close_progress = QProgressDialog(
            tr("msg_rescan_progress"),
            None, 0, 100, self,
        )
        self._close_progress.setWindowTitle(tr("title_rescan_close"))
        self._close_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._close_progress.setMinimumDuration(0)
        self._close_progress.setCancelButton(None)
        self._close_progress.setAutoClose(False)
        self._close_progress.setAutoReset(False)
        self._close_progress.setStyleSheet("""
            QProgressDialog {
                background-color: #f0f2f5;
                border: 2px solid #4927af;
                border-radius: 10px;
                padding: 20px;
            }
            QProgressDialog QLabel {
                color: #2c3e50;
                font-size: 13px;
                font-weight: bold;
            }
            QProgressBar {
                border: 1px solid #4927af;
                border-radius: 6px;
                text-align: center;
                height: 25px;
                max-width: 100%;
                color: #2c3e50;
                font-weight: bold;
                font-size: 12px;
                background: #e8e0f5;
            }
            QProgressBar::chunk {
                background-color: #4927af;
                border-radius: 5px;
            }
        """)
        self._close_progress.show()
        self._close_progress.setValue(0)

        self._scan_worker = LibraryScanWorker(mf, self.config)
        self._scan_worker.progress.connect(self._on_rescan_close_progress)
        self._scan_worker.finished.connect(self._on_rescan_for_close_finished)
        self._scan_worker.error.connect(self._on_rescan_for_close_error)
        self._scan_worker.start()

    def _on_rescan_close_progress(self, current, total, message):
        if total > 0:
            self._close_progress.setMaximum(total)
            self._close_progress.setValue(current)

    def _on_rescan_for_close_finished(self, tracks):
        folder = self.music_folder_input.text().strip()
        self.library_tracks = tracks
        self._save_library_cache(tracks, folder)
        self._logger.info("Rescan pre-chiusura completato: %d tracce", len(tracks))
        if hasattr(self, '_close_progress') and self._close_progress:
            self._close_progress.close()
            self._close_progress = None
        self.close()

    def _on_rescan_for_close_error(self, message):
        self._logger.warning("Rescan pre-chiusura fallito: %s", message)
        if hasattr(self, '_close_progress') and self._close_progress:
            self._close_progress.close()
            self._close_progress = None
        self.close()


# ===================================================================
# Application entry point
# ===================================================================

def run_app():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("Serato Playlist Automation")

    window = MainWindow()
    window.showMaximized()

    for mod_name, dep_key in [("rapidfuzz", "dep_rapidfuzz"), ("mutagen", "dep_mutagen")]:
        try:
            __import__(mod_name)
        except ImportError:
            QMessageBox.warning(
                window, tr("title_dependency"),
                tr("msg_dep_missing", mod=mod_name, display=tr(dep_key)),
            )

    sys.exit(app.exec())