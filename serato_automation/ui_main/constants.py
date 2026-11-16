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
E_COL_PLAYER = 9
E_NUM_COLS = 10
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

# --- Matching UI thresholds (tuned empirically on real DJ libraries) ---
# AUTO_SELECT_THRESHOLD: rows at or above this score are auto-checkboxed after a
#   match (the DJ trusts them by default). 55 (not higher) because the v5 scoring
#   model already applies heavy penalties for wrong artist/title, so a 55 here
#   means "title confirmed, minor descriptor mismatch" — a safe auto-pick.
AUTO_SELECT_THRESHOLD = 55
# FOUNDDROP_MIN_SCORE: candidates below this score are hidden from the per-row
#   "Found" dropdown to keep it uncluttered. 47 because below ~47% the matcher
#   is usually matching on filename only (low confidence) and showing those
#   alternatives would drown the real candidate. A matched row always shows
#   ">=1" regardless (see ResultsTable), so this only filters the dropdown list.
FOUNDDROP_MIN_SCORE = 47

# QTableWidgetItem user role: list of (token, color_hex) for title word highlighting
ROLE_WORD_COLORS = Qt.ItemDataRole.UserRole + 10
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


__all__ = ['COL_LOCK', 'COL_SELECT', 'COL_SCORE', 'COL_FOUND', 'COL_TITOLO_RICHIESTO', 'COL_FILENAME', 'COL_ARTISTA_SERATO', 'COL_SONG_SERATO', 'COL_GENRE', 'COL_BPM', 'COL_COMMENT', 'COL_PLAYER', 'COL_HOTCUE', 'NUM_COLS', 'E_COL_FILE', 'E_COL_TITLE', 'E_COL_ARTIST', 'E_COL_ALBUM', 'E_COL_GENRE', 'E_COL_HOTCUE', 'E_COL_LOCATION', 'E_COL_ACTION', 'E_COL_DELETE', 'E_COL_PLAYER', 'E_NUM_COLS', 'E_EDITABLE_COLS', 'DJ_SOFTWARE_OPTIONS', 'AUTO_SELECT_THRESHOLD', 'FOUNDDROP_MIN_SCORE', 'ROLE_WORD_COLORS', 'AI_CLEANUP_PROMPT']
