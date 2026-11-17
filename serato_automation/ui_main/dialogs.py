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
from .workers import *

class FormatGuideDialog(QDialog):
    def __init__(self, parent=None, theme: str = "light"):
        super().__init__(parent)
        self.setWindowTitle(tr("guide_title"))
        self.setMinimumSize(650, 620)
        self.resize(700, 650)

        # Theme-aware colors so the dialog is readable in both light and dark mode.
        # Previous version used hardcoded gray (#7f8c8d) on white (#fafafa) which
        # was nearly invisible, especially in dark theme where the QTextEdit
        # inherited light-on-dark text but kept the white background.
        self._is_dark = (theme == "dark")
        p = ui_theme.palette()

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel(tr("guide_heading"))
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {p['accent']};")
        layout.addWidget(title)

        guide = QLabel(tr("guide_body_detailed"))
        guide.setWordWrap(True)
        guide.setTextFormat(Qt.TextFormat.RichText)
        # Use theme-aware colors so the rich-text label is readable in both themes.
        # The HTML in guide_body_detailed uses <b> and <code> tags whose colors
        # are inherited from the QLabel stylesheet.
        guide.setStyleSheet(
            f"background: {p['panel_alt']}; border: 1px solid {p['border']}; "
            f"border-radius: 6px; padding: 12px; font-size: 11px; "
            f"color: {p['text']};"
        )
        layout.addWidget(guide)

        prompt_title = QLabel(tr("guide_prompt_title"))
        prompt_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        prompt_title.setStyleSheet(
            f"color: {p['text']}; margin-top: 6px;"
        )
        layout.addWidget(prompt_title)

        desc = QLabel(tr("guide_prompt_desc"))
        desc.setStyleSheet(
            f"color: {p['text_muted']}; font-size: 10px;"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlainText(AI_CLEANUP_PROMPT)
        self.prompt_edit.setFont(QFont("Consolas", 9))
        self.prompt_edit.setReadOnly(True)
        # Use theme-aware background and an explicit text color so the
        # prompt is readable regardless of the app-wide stylesheet.
        self.prompt_edit.setStyleSheet(
            f"border: 1px solid {p['border']}; border-radius: 4px; padding: 8px; "
            f"background: {p['panel_alt']}; color: {p['text']}; font-size: 10px;"
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
        # Cooperative cancellation — no hard terminate (see MainWindow.closeEvent).
        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.wait(5000)
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



__all__ = ['FormatGuideDialog', 'CleanLibraryDialog', 'ReplaceDialog', 'AlgorithmDialog', 'ImportUrlDialog', 'SettingsDialog', 'QuickGuideDialog', 'ProUpgradeDialog']
