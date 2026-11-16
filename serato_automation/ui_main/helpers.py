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

def format_score(score) -> str:
    """Format a score value with at most 1 decimal place."""
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "-"
    return f"{int(s)}%" if s == int(s) else f"{s:.1f}%"
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


__all__ = ['format_score', 'move_to_recycle_bin', 'set_button_alt', '_vline', '_link_button', '_apply_button_font', '_fit_button_text']
