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
                cancel_check=self.isInterruptionRequested,
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
                cancel_check=self.isInterruptionRequested,
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
            from serato_automation.playlist_importer import import_playlist_from_url
            source, tracks = import_playlist_from_url(self.url)
            self.progress.emit(0, len(tracks), f"Importazione completata: {len(tracks)} brani da {source}")
            self.finished.emit((source, tracks))
        except Exception as e:
            self.error.emit(str(e))


__all__ = ['WorkerThread', 'LibraryScanWorker', 'MatchWorker', 'ImportWorker']
