"""serato_automation.ui_main — UI package (formerly the ui_main.py monolith).

Submodules:
    constants      — column indices, thresholds, DJ-software list, AI prompt
    styles         — light/dark stylesheets, score->colour mappers, theme flag
    helpers        — small UI helpers (format_score, button alt-text, recycle-bin)
    workers        — Qt worker threads (library scan / match / URL import)
    widgets        — reusable Qt widgets (BusyDialog, PlayerCellWidget, ...)
    results_table  — the main results QTableWidget
    dialogs        — secondary dialogs (settings, import URL, pro upgrade, ...)
    main_window    — MainWindow controller + run_app() entry point

Public API (preserved for backward compatibility):
    run_app, MainWindow, ResultsTable, and every other former top-level name.
"""
from .constants import *
from .styles import *
from .helpers import *
from .workers import *
from .widgets import *
from .results_table import *
from .dialogs import *
from .main_window import *

__all__ = (
    ["run_app", "MainWindow", "ResultsTable"]
    + ["WorkerThread", "LibraryScanWorker", "MatchWorker", "ImportWorker"]
    + ["BusyDialog", "DropTextEdit", "TextSelectionDelegate", "TitleColorDelegate",
       "ElidingHeaderView", "ClickableSlider", "PlayerCellWidget", "RowHighlightOverlay"]
    + ["FormatGuideDialog", "CleanLibraryDialog", "ReplaceDialog", "AlgorithmDialog",
       "ImportUrlDialog", "SettingsDialog", "QuickGuideDialog", "ProUpgradeDialog"]
    + ["COL_LOCK", "COL_SELECT", "COL_SCORE", "COL_FOUND", "COL_TITOLO_RICHIESTO",
       "COL_FILENAME", "COL_ARTISTA_SERATO", "COL_SONG_SERATO", "COL_GENRE",
       "COL_BPM", "COL_COMMENT", "COL_PLAYER", "COL_HOTCUE", "NUM_COLS"]
)
