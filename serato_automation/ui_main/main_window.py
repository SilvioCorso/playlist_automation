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
from .workers import *
from .widgets import *
from .results_table import *
from .dialogs import *

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
        # Constructed defensively: on Windows Server / RDP sessions without
        # audio, or machines with the audio service disabled, QAudioOutput can
        # fail. We degrade gracefully (player column disabled) instead of crashing.
        # NOTE: errorOccurred is connected in its own try/except so a PySide6
        # version without that signal (or a signature change) does NOT disable
        # the whole player — playback/seek/position must keep working.
        self._player_available = False
        self._player_current_row = -1
        # Which table owns the playing row: "results" | "editing" | None.
        # Lets the shared QMediaPlayer drive PlayerCellWidgets in BOTH tables.
        self._player_current_source = None
        # Direct reference to the PlayerCellWidget currently playing. Captured
        # via sender() at play time so state/position updates reach the widget
        # WITHOUT any row/source lookup (which could miss on edge cases and
        # leave the button stuck on 'play' / the slider without a duration).
        self._player_active_widget = None
        try:
            self._player = QMediaPlayer(self)
            self._audio_output = QAudioOutput(self)
            self._player.setAudioOutput(self._audio_output)
            self._audio_output.setVolume(0.7)
            self._player.positionChanged.connect(self._on_player_position_changed)
            self._player.playbackStateChanged.connect(self._on_player_state_changed)
            try:
                self._player.durationChanged.connect(self._on_player_duration_changed)
            except Exception:
                pass  # older Qt: no durationChanged — positionChanged carries duration
            try:
                self._player.errorOccurred.connect(self._on_player_error)
            except Exception:
                pass  # signal absent on some PySide6 builds — non-fatal
            self._player_available = True
        except Exception as e:
            self._logger.warning("Audio player non disponibile: %s", e)
            self._player = None
            self._audio_output = None

        self._build_ui()
        self._restore_settings()
        self._check_serato()
        self._auto_load_library()

    # ------------------------------------------------------------------
    # Audio Player (shared QMediaPlayer + QAudioOutput)
    # ------------------------------------------------------------------

    def _on_player_error(self, error, error_string):
        """Handle QMediaPlayer errors without crashing — log and keep going."""
        self._logger.warning("QMediaPlayer error: %s (%s)", error_string, error)

    def _on_player_duration_changed(self, duration):
        """Media duration became known (may arrive AFTER playback starts on
        Windows). Force the active row's slider range to the real duration so
        seek-clicks map to the right position and the bar reflects track length.
        """
        if not self._player_available or duration <= 0:
            return
        pw = getattr(self, "_player_active_widget", None) or self._get_active_player_widget()
        if pw:
            pw.update_position(self._player.position(), duration)

    def _get_active_player_widget(self):
        """Return the PlayerCellWidget for the row currently playing.

        The active row may live in the Results table OR the Editing table
        (self._player_current_source tells us which). Centralising this lookup
        keeps the shared QMediaPlayer in sync across both tables.

        Fallback: if the source-aware lookup misses (e.g. source flag out of
        sync after an edge case), scan both tables at the current row before
        giving up — so state/position updates always reach the widget that's
        actually playing.
        """
        from serato_automation.ui_main.widgets import PlayerCellWidget
        row = self._player_current_row
        if row < 0:
            return None
        src = self._player_current_source
        if src == "editing" and hasattr(self, "editing_table"):
            w = self.editing_table.cellWidget(row, E_COL_PLAYER)
            if isinstance(w, PlayerCellWidget):
                return w
        elif src == "results":
            w = self.results_table.get_player_widget(row)
            if w:
                return w
        # Fallback scan: try results first, then editing.
        w = self.results_table.get_player_widget(row)
        if w:
            return w
        if hasattr(self, "editing_table"):
            w = self.editing_table.cellWidget(row, E_COL_PLAYER)
            if isinstance(w, PlayerCellWidget):
                return w
        return None

    def _player_play_row(self, row: int):
        """Play audio for the given RESULTS-table row — stop previous first."""
        if not self._player_available:
            return
        # Same results row already active: resume from pause or do nothing.
        if (self._player_current_source == "results"
                and self._player_current_row == row):
            if self._player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
                self._player.play()
            return
        # Stop whatever is playing in EITHER table first.
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
        self._player_current_source = "results"
        # Capture the widget directly (sender() = the PlayerCellWidget that
        # emitted play_requested) so state/position updates don't depend on a
        # row/source lookup that could miss.
        self._player_active_widget = self.sender() or self.results_table.get_player_widget(row)
        url = QUrl.fromLocalFile(os.path.abspath(filepath))
        self._player.setSource(url)
        self._player.play()

    def _player_play_editing_row(self, row: int):
        """Play audio for the given EDITING-table row (main editing table)."""
        self._player_play_editing_tracks(row, getattr(self, "_row_tracks", []))

    def _player_play_editing_tracks(self, row: int, tracks):
        """Play audio for *row* in the EDITING context, using an explicit
        *tracks* list (so each Advanced-Duplicates accordion group can play its
        own rows without touching the global self._row_tracks).
        """
        if not self._player_available:
            return
        if (self._player_current_source == "editing"
                and self._player_current_row == row
                and getattr(self, "_player_editing_tracks", None) is tracks):
            if self._player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
                self._player.play()
            return
        if self._player_current_row >= 0:
            self._player_stop_current()
        if row < 0 or row >= len(tracks):
            return
        track = tracks[row]
        filepath = getattr(track, "filepath", "") or ""
        if not filepath or not os.path.isfile(filepath):
            return
        self._player_editing_tracks = tracks
        self._player_current_row = row
        self._player_current_source = "editing"
        # Capture the widget directly (sender() = the PlayerCellWidget that
        # emitted play_requested — works for the main editing table AND for any
        # Advanced-Duplicates accordion group table).
        self._player_active_widget = self.sender()
        url = QUrl.fromLocalFile(os.path.abspath(filepath))
        self._player.setSource(url)
        self._player.play()

    def _player_pause(self):
        """Pause the currently playing track."""
        if not self._player_available:
            return
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()

    def _player_stop_current(self):
        """Stop playback and reset the player widget for the current row
        (whichever table it lives in)."""
        if not self._player_available:
            return
        # Use the direct widget reference first (always correct); fall back to
        # the source-aware lookup only if the reference was lost.
        pw = getattr(self, "_player_active_widget", None) or self._get_active_player_widget()
        if pw:
            pw.set_playing(False)
        self._player.stop()
        self._player_current_row = -1
        self._player_current_source = None
        self._player_active_widget = None

    def _player_seek(self, position: int):
        """Seek to *position* (ms) AND resume playback from there.

        Clicking the slider groove (mid-bar) must both reposition to the right
        second AND play — 'se clicco a metà della barretta deve posizionarmi e
        riprodurre'. If a track is loaded we always resume after setPosition so
        the DJ hears the audio from the clicked point. If nothing is loaded
        (no active row), do nothing.
        """
        if not self._player_available:
            return
        if self._player_current_row < 0:
            return
        # setPosition works in Playing/Paused/Stopped as long as a source is set.
        self._player.setPosition(position)
        # Resume from the new position unless we're already playing.
        if self._player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            self._player.play()

    def _on_player_position_changed(self, position: int):
        """Update the slider of the currently playing row."""
        if not self._player_available:
            return
        pw = getattr(self, "_player_active_widget", None) or self._get_active_player_widget()
        if pw:
            duration = self._player.duration()
            pw.update_position(position, duration)

    def _on_player_state_changed(self, state):
        """Update play/pause button when playback state changes."""
        if not self._player_available:
            return
        pw = getattr(self, "_player_active_widget", None) or self._get_active_player_widget()
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
        if not self._player_available:
            return
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
            self._fs_menu.addAction(tr("btn_duplicates_advanced"), self._find_advanced_duplicates)
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
        self._btn_duplicates_adv.setText(tr("btn_duplicates_advanced"))
        set_button_alt(self._btn_duplicates_adv, "btn_duplicates_advanced_tt")
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

        self._btn_duplicates_adv = QPushButton(tr("btn_duplicates_advanced"))
        self._btn_duplicates_adv.setObjectName("guideBtn")
        set_button_alt(self._btn_duplicates_adv, "btn_duplicates_advanced_tt")
        self._btn_duplicates_adv.clicked.connect(self._find_advanced_duplicates)
        row1.addWidget(self._btn_duplicates_adv)
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
        self.editing_table.setColumnWidth(E_COL_PLAYER, 141)
        self._editing_sort = (None, True)

        # Restore saved column widths (user resizing persists across launches).
        self._restoring_editing_cols = True
        try:
            saved_w = (self.config.get("editing_table_columns") or {}).get("widths") or {}
            for col_str, w in saved_w.items():
                try:
                    col = int(col_str)
                    if 0 <= col < E_NUM_COLS and int(w) > 10:
                        self.editing_table.setColumnWidth(col, int(w))
                except (ValueError, TypeError):
                    continue
        finally:
            self._restoring_editing_cols = False
        # Debounced save on resize — same pattern as the Results table.
        self._editing_cols_timer = QTimer(self)
        self._editing_cols_timer.setSingleShot(True)
        self._editing_cols_timer.timeout.connect(self._save_editing_column_layout)
        hh.sectionResized.connect(lambda *_: self._schedule_save_editing_columns())

        # Stacked container: page 0 = the flat editing table (used by Easy
        # Duplicates / Clean Library / Find Differences); page 1 = the Advanced
        # Duplicates accordion (one collapsible group per fuzzy title cluster).
        self._editing_stack = QStackedWidget()
        self._editing_stack.addWidget(self.editing_table)          # page 0
        self._dup_accordion_scroll = QScrollArea()
        self._dup_accordion_scroll.setWidgetResizable(True)
        self._dup_accordion_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._dup_accordion_container = QWidget()
        self._dup_accordion_vlayout = QVBoxLayout(self._dup_accordion_container)
        self._dup_accordion_vlayout.setContentsMargins(0, 0, 0, 0)
        self._dup_accordion_vlayout.setSpacing(6)
        self._dup_accordion_vlayout.addStretch()  # groups inserted above the stretch
        self._dup_accordion_scroll.setWidget(self._dup_accordion_container)
        self._editing_stack.addWidget(self._dup_accordion_scroll)  # page 1
        self._editing_stack.setCurrentIndex(0)
        ed_layout.addWidget(self._editing_stack, stretch=1)

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
            tr("edit_col_player"),
        ]

    def _schedule_save_editing_columns(self, *_args):
        if getattr(self, "_restoring_editing_cols", False):
            return
        if hasattr(self, "_editing_cols_timer"):
            self._editing_cols_timer.start(250)

    def _save_editing_column_layout(self):
        """Persist the editing-table column widths so the user's resizing
        survives across launches (same UX as the Results table)."""
        if getattr(self, "_restoring_editing_cols", False):
            return
        if not hasattr(self, "editing_table"):
            return
        header = self.editing_table.horizontalHeader()
        widths = {str(c): header.sectionSize(c) for c in range(E_NUM_COLS)}
        self.config["editing_table_columns"] = {"widths": widths}
        try:
            save_config(self.config)
        except Exception:
            pass

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
        # ui_theme is the SINGLE source of truth for the dark flag — styles.py
        # score_to_bg_color and results_table row colours read ui_theme.is_dark().
        # (The old `global _DARK_THEME_ACTIVE` wrote to this module's namespace
        #  and never reached styles.py after the package split.)
        self._current_theme = theme
        ui_theme.set_dark_active(theme == "dark")
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
        stats_color = "#e0e4ef" if ui_theme.is_dark() else "#2c3e50"
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
        try to find a drive with the same volume identifier and update
        both the config and the in-memory state.

        The volume identifier is preferred over the bare volume label
        because the serial number is ALWAYS present on a formatted Windows
        partition — even if the user has not set a custom volume label.
        This means the auto-remap now works for disks that have no label.

        Backward compatibility: if an old config has only the
        `*_volume_label` field (no `*_volume_identifier`), we use the
        label as the identifier. New saves always include the identifier.

        Returns True if at least one path was remapped.
        """
        remapped_any = False

        # --- Music folder ---
        saved_music = self.config.get("music_folder", "")
        # Prefer the new *_volume_identifier (serial-based); fall back to
        # the legacy *_volume_label for configs saved before this update.
        saved_music_id = (
            self.config.get("music_folder_volume_identifier") or
            self.config.get("music_folder_volume_label") or
            ""
        )
        if saved_music and not os.path.isdir(saved_music) and saved_music_id:
            new_music = remap_path_to_current_drive(saved_music, saved_music_id)
            if new_music and new_music != saved_music:
                old_letter = get_drive_letter(saved_music)
                new_letter = get_drive_letter(new_music)
                self._logger.info(
                    "Music folder auto-remapped by identifier %r: '%s' -> '%s'",
                    saved_music_id, saved_music, new_music
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
                # Refresh the volume identifier with the new drive's value
                # in case the serial changed (rare, but possible if the
                # user replaced the disk with one that has the same label).
                self.config["music_folder_volume_identifier"] = get_volume_identifier(new_music)
                self.config["music_folder_volume_label"] = get_volume_label(new_music)
                self.music_folder_input.setText(new_music)
                self.statusBar().showMessage(
                    f"Disco esterno rilevato su {new_letter}: (era {old_letter}:)"
                )
                save_config(self.config)
                remapped_any = True

        # --- Serato folder ---
        saved_serato = self.config.get("serato_folder", "")
        saved_serato_id = (
            self.config.get("serato_folder_volume_identifier") or
            self.config.get("serato_folder_volume_label") or
            ""
        )
        if saved_serato and not os.path.isdir(saved_serato) and saved_serato_id:
            new_serato = remap_path_to_current_drive(saved_serato, saved_serato_id)
            if new_serato and new_serato != saved_serato:
                self._logger.info(
                    "Serato folder auto-remapped by identifier %r: '%s' -> '%s'",
                    saved_serato_id, saved_serato, new_serato
                )
                self.config["serato_folder"] = new_serato
                self.config["serato_folder_volume_identifier"] = get_volume_identifier(new_serato)
                self.config["serato_folder_volume_label"] = get_volume_label(new_serato)
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
                    self.config["serato_folder_volume_identifier"] = get_volume_identifier(detected)
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
            # Save BOTH the volume identifier (preferred — works even
            # when the disk has no label) and the legacy volume_label
            # (for backward compat with older builds that only read it).
            self.config["serato_folder_volume_identifier"] = get_volume_identifier(folder)
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
            # Save BOTH the volume identifier (preferred — uses the volume
            # serial number which is always present on a formatted partition,
            # so it works even when the user has not set a custom volume label)
            # and the legacy volume_label (for backward compat with configs
            # saved by older builds that only read the label).
            self.config["music_folder_volume_identifier"] = get_volume_identifier(folder)
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
                    self.config["serato_folder_volume_identifier"] = ""
            save_config(self.config)
            self.statusBar().showMessage(tr("status_folder", folder=folder))
            self._library_cache_loaded = False
            self._update_scan_button_text()
            # Re-detect Serato subcrates on the new music drive
            self._check_serato()

    def _get_cache_path(self, folder: str) -> str:
        # Delegated to the cache module (returns the .json path).
        from serato_automation import cache as _cache
        return _cache.get_cache_path(folder)

    def _save_library_cache(self, tracks: list, folder: str):
        from serato_automation import cache as _cache
        _cache.save_library_cache(folder, tracks)

    def _load_library_cache(self, folder: str) -> Optional[list]:
        from serato_automation import cache as _cache
        return _cache.load_library_cache(folder)

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
        status_msg = tr("status_library_loaded",
                        count=len(tracks), size=total_size,
                        bpm=stats['has_bpm'], keys=stats['has_key'], comment=stats['has_comment'])
        failed = stats.get('failed_files') or []
        if failed:
            # Surface skipped files so the DJ knows the crate may be incomplete.
            status_msg += tr("status_scan_errors_suffix", count=len(failed))
            self._logger.warning("%d file saltati durante la scansione (vedi log)", len(failed))
        self.statusBar().showMessage(status_msg)

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
            self, tr("dlg_load_playlist"), os.path.expanduser("~"),
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
                tr("status_imported_from_url",
                   count=len(dialog.imported_tracks), source=dialog._source, total=total)
            )

    def _show_format_guide(self):
        FormatGuideDialog(self, theme=self._current_theme).exec()

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
            return matches or None

        matches = self._run_busy(tr("busy_clean_lib"), work)
        if not matches:
            QMessageBox.information(
                self, tr("clean_lib_title"), tr("clean_lib_none_found")
            )
            return
        # GUI-side warm + populate (kept off the worker thread — widget access).
        for t in matches:
            self._hotcue_count(t.filepath or "")
        self._populate_editing_table(matches)

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
            return dups

        dups = self._run_busy(tr("busy_duplicates"), work)
        if not dups:
            self._editing_mode = ""
            self.editing_status.setText(tr("dup_none"))
            QMessageBox.information(self, tr("btn_duplicates"), tr("dup_none"))
            return
        # GUI-side warm + populate (kept off the worker thread — widget access).
        for t in dups:
            self._hotcue_count(t.filepath or "")
        self._last_search_word = ""
        self._populate_editing_table(dups)

        self._editing_mode = "duplicates"
        self.editing_status.setText(tr("dup_status", count=len(dups)))
        self.tabs.setTabEnabled(2, True)
        self.tabs.setCurrentIndex(2)

    # ------------------------------------------------------------------
    # Advanced Duplicates (fuzzy title clustering + accordion UI)
    # ------------------------------------------------------------------

    def _find_advanced_duplicates(self):
        """Cluster the library by fuzzy title similarity and show one accordion
        group per cluster (all collapsed), with a similarity % per track."""
        if not self.library_tracks:
            QMessageBox.warning(self, tr("title_attention"), tr("msg_scan_first"))
            return

        def work():
            from serato_automation.duplicate_finder import find_advanced_duplicates
            return find_advanced_duplicates(self.library_tracks, min_similarity=80)

        groups = self._run_busy(tr("dup_adv_busy"), work)
        if not groups:
            self._editing_mode = ""
            self.editing_status.setText(tr("dup_adv_none"))
            QMessageBox.information(
                self, tr("btn_duplicates_advanced"), tr("dup_adv_none"))
            return

        self._build_duplicate_accordion(groups)
        total_tracks = sum(g["count"] for g in groups)
        self._editing_mode = "duplicates_adv"
        self.editing_status.setText(
            tr("dup_adv_status", groups=len(groups), tracks=total_tracks))
        # Accordion view (page 1) — the flat-table toolbar (Save All / Replace /
        # Copy / Update Serato) does not apply here: each group has its own
        # per-row Save / Delete / Player, exactly like the flat editing table.
        self._editing_stack.setCurrentIndex(1)
        for btn in (self._btn_edit_save_all, self._btn_edit_replace,
                    self._btn_edit_copy, self._btn_update_serato):
            btn.setEnabled(False)
        self.tabs.setTabEnabled(2, True)
        self.tabs.setCurrentIndex(2)

    def _clear_duplicate_accordion(self):
        """Remove all group widgets from the accordion container."""
        vlay = self._dup_accordion_vlayout
        while vlay.count() > 1:  # keep the trailing stretch item
            item = vlay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def _build_duplicate_accordion(self, groups):
        """Populate the accordion with one collapsible group per cluster.

        Each group header shows '▶ title (count)'; clicking expands/collapses an
        inline editing table (same columns as the flat Editing table + a trailing
        'Vicinanza' column). All groups start collapsed.

        Tables are built LAZILY: only the header is created up-front (so the
        accordion appears instantly even for hundreds of groups); the table for
        a group is populated the first time the user expands it. The table height
        is set to fit ALL its rows so there is no inner scrollbar — the outer
        accordion scroll handles the page.
        """
        self._clear_duplicate_accordion()
        vlay = self._dup_accordion_vlayout
        p = ui_theme.palette()

        for g in groups:
            group_widget = QWidget()
            group_layout = QVBoxLayout(group_widget)
            group_layout.setContentsMargins(0, 0, 0, 0)
            group_layout.setSpacing(0)

            # Header button (toggle).
            title = g["representative_title"] or "(?)"
            count = g["count"]
            header = QPushButton(f"▶  {title}   ({count})")
            header.setCheckable(True)
            header.setStyleSheet(
                "QPushButton { text-align: left; padding: 8px 12px;"
                f" background: {p['panel_alt']}; color: {p['text']};"
                f" border: 1px solid {p['border']}; border-radius: 6px;"
                " font-weight: bold; }"
                f" QPushButton:hover {{ background: {p['panel']}; }}"
            )
            header.setCursor(Qt.CursorShape.PointingHandCursor)

            # Content container — table is built on first expand (lazy).
            content = QWidget()
            content_layout = QVBoxLayout(content)
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(0)
            content.setVisible(False)
            # Stash the group data on the content widget for the lazy builder.
            content._dup_group = g
            content._dup_table_built = False

            def _toggle(checked, hdr=header, cnt=content, ttl=title, c=count):
                if checked and not cnt._dup_table_built:
                    self._build_one_dup_group_table(cnt)
                    cnt._dup_table_built = True
                cnt.setVisible(checked)
                arrow = "▼" if checked else "▶"
                hdr.setText(f"{arrow}  {ttl}   ({c})")

            header.toggled.connect(_toggle)
            group_layout.addWidget(header)
            group_layout.addWidget(content)

            vlay.insertWidget(vlay.count() - 1, group_widget)  # before the stretch

    def _build_one_dup_group_table(self, content):
        """Lazily build the editing table for one accordion group (on first
        expand). Sizing: the table height fits ALL rows so there is no inner
        scrollbar."""
        g = content._dup_group
        content_layout = content.layout()
        group_table = QTableWidget()
        ncols = E_NUM_COLS + 1  # +1 for the trailing Vicinanza column
        group_table.setColumnCount(ncols)
        headers = MainWindow._editing_headers() + [tr("edit_col_vicinanza")]
        group_table.setHorizontalHeaderLabels(headers)
        group_table.verticalHeader().setVisible(False)
        group_table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.EditKeyPressed
        )
        group_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        group_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        gh = group_table.horizontalHeader()
        gh.setStretchLastSection(False)
        group_table.setColumnWidth(E_COL_FILE, 200)
        group_table.setColumnWidth(E_COL_TITLE, 230)
        group_table.setColumnWidth(E_COL_ARTIST, 170)
        group_table.setColumnWidth(E_COL_ALBUM, 170)
        group_table.setColumnWidth(E_COL_GENRE, 130)
        group_table.setColumnWidth(E_COL_HOTCUE, 70)
        group_table.setColumnWidth(E_COL_LOCATION, 260)
        group_table.setColumnWidth(E_COL_ACTION, 90)
        group_table.setColumnWidth(E_COL_DELETE, 100)
        group_table.setColumnWidth(E_COL_PLAYER, 141)
        vicinanza_col = E_NUM_COLS
        group_table.setColumnWidth(vicinanza_col, 90)

        group_tracks = [t for t, _s in g["tracks"]]
        entries = [
            {"track": t, "title": t.title or "", "artist": t.artist or "",
             "album": t.album or "", "genre": t.genre or ""}
            for t, _s in g["tracks"]
        ]
        play_handler = lambda r, T=group_tracks: self._player_play_editing_tracks(r, T)
        self._populate_editing_entries(
            entries, table=group_table, play_handler=play_handler, set_global=False)
        for row, (_t, score) in enumerate(g["tracks"]):
            vitem = QTableWidgetItem(f"{score}%")
            vitem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            vitem.setForeground(score_to_text_color(score))
            vitem.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            group_table.setItem(row, vicinanza_col, vitem)

        # Fit the table height to ALL rows — no inner scrollbar. The outer
        # accordion scroll handles the page. Cap at a sane max so a 100-row
        # group doesn't take the whole screen (it then scrolls internally).
        n_rows = group_table.rowCount()
        hh_h = group_table.horizontalHeader().height() + 2
        total_h = n_rows * 34 + hh_h
        group_table.setMinimumHeight(min(total_h, 600))
        group_table.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded if total_h > 600
            else Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content_layout.addWidget(group_table)

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
        # Flat-table view (page 0) — make sure the accordion is hidden and the
        # editing toolbar is enabled.
        if hasattr(self, "_editing_stack"):
            self._editing_stack.setCurrentIndex(0)
            for btn in (self._btn_edit_save_all, self._btn_edit_replace,
                        self._btn_edit_copy, self._btn_update_serato):
                btn.setEnabled(len(entries) > 0)

    def _populate_editing_entries(self, entries, table=None, play_handler=None,
                                  set_global=True):
        """(Re)build the Editing table rows from entry dicts.

        Used by the initial fill and by column sorting (which re-reads the current
        cell values, sorts them, and rebuilds so the button columns stay aligned).
        Pass *table* to populate a table other than self.editing_table (used by
        the Advanced Duplicates accordion groups). *play_handler* is the callable
        used for the per-row PlayerCellWidget.play_requested signal (the accordion
        passes a closure bound to that group's track list). When *set_global* is
        False the method does NOT touch self._row_tracks / toolbar buttons.
        """
        table = table or self.editing_table
        # Repopulate destroys every cell widget — stop the player first so the
        # shared QMediaPlayer is not left pointing at a destroyed widget (which
        # would make _on_player_state_changed find None and silently break).
        if getattr(self, "_player_current_source", None) == "editing":
            self._player_stop_current()
        table.setRowCount(0)
        table.setRowCount(len(entries))
        if set_global:
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
                lambda _=False, r=row, t=track, tbl=table: self._editing_confirm_row(r, t, tbl)
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

            # Player column — same PlayerCellWidget as the Results table, wired
            # to the SAME shared QMediaPlayer (so playing a row here stops any
            # row playing in the Results table, and vice versa).
            epath = track.filepath or ""
            if epath and os.path.isfile(epath):
                pw = PlayerCellWidget(row)
                pw.set_has_file(True)
                pw.set_track_name(track.display_name or os.path.basename(epath))
                pw.play_requested.connect(play_handler or self._player_play_editing_row)
                pw.pause_requested.connect(self._player_pause)
                pw.seek_requested.connect(self._player_seek)
                table.setCellWidget(row, E_COL_PLAYER, pw)
            else:
                pitem = QTableWidgetItem("-")
                pitem.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                pitem.setForeground(QColor("#bbb"))
                pitem.setFlags(Qt.ItemFlag.NoItemFlags)
                table.setItem(row, E_COL_PLAYER, pitem)

            table.setRowHeight(row, 34)

        if set_global:
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

    def _row_values(self, row, table=None):
        table = table or self.editing_table
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

    def _write_editing_row(self, row, track, table=None):
        """Write one row's tags to disk and refresh its visuals.

        Returns ``(ok, msg)``; does NOT touch the cache or show dialogs so it can
        be reused both by the per-row button and the 'Save all' action. Pass
        *table* when the row lives in a table other than self.editing_table
        (e.g. an Advanced Duplicates accordion group).
        """
        new_title, new_artist, new_album, new_genre = self._row_values(row, table)

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

        table = table or self.editing_table
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

    def _editing_confirm_row(self, row, track, table=None):
        ok, msg = self._write_editing_row(row, track, table)
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
        mode = getattr(self, "_editing_mode", "")
        if mode == "duplicates":
            self._find_duplicates()
        elif mode == "duplicates_adv":
            # Re-cluster and rebuild the accordion (the deleted track may have
            # broken a cluster or reduced it below the 2-member threshold).
            self._find_advanced_duplicates()
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
        """Run a synchronous callable off the GUI thread while showing the busy dialog.

        The callable runs in a worker QThread; a local QEventLoop pumps events so
        the BusyDialog's progress bar animates and the window stays responsive
        while the (file-IO-heavy) work proceeds. The API stays synchronous: the
        caller's next line receives work_fn's return value, or its exception is
        re-raised. work_fn must NOT touch Qt widgets directly (only data / files).
        """
        from PySide6.QtCore import QEventLoop, QThread, Signal

        dlg = BusyDialog(message, self)
        dlg.show()

        class _Worker(QThread):
            done = Signal(object)
            def __init__(self, fn):
                super().__init__()
                self._fn = fn
            def run(self):
                try:
                    self.done.emit(("ok", self._fn()))
                except Exception as e:
                    self.done.emit(("err", e))

        worker = _Worker(work_fn)
        loop = QEventLoop()
        result = {}
        def _on_done(payload):
            result["payload"] = payload
            loop.quit()
        worker.done.connect(_on_done)
        worker.start()
        loop.exec()          # pumps events while the worker runs → dialog animates
        worker.wait(5000)
        dlg.close()

        payload = result.get("payload")
        if payload and payload[0] == "err":
            raise payload[1]
        return payload[1] if payload else None

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
            tr("status_matching_summary", matched=matched, missing=missing)
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
        """Persist title→filepath mappings to JSON file (atomic write)."""
        path = self._get_title_locks_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"locks": self._title_locks}, f, indent=2, ensure_ascii=False)
            os.replace(tmp, path)
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
        if not os.path.exists(self._log_path):
            QMessageBox.information(self, tr("title_log"), tr("msg_log_not_found", path=self._log_path))
            return
        # Windows: open with the associated app (os.startfile). On macOS/Linux
        # (unsupported but defensive) fall back to the platform opener / editor.
        try:
            if sys.platform.startswith("win"):
                os.startfile(self._log_path)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", self._log_path])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", self._log_path])
        except Exception:
            QMessageBox.information(self, tr("title_log"), self._log_path)

    def closeEvent(self, event):
        # Stop audio player before closing (no leaks)
        self._player_cleanup()
        # Cooperative cancellation of running workers — never hard-terminate
        # (QThread.terminate() can leave half-written Serato files / locks).
        # Request interruption, then give each worker up to 5 s to finish.
        for worker in (self._scan_worker, self._match_worker):
            if worker and worker.isRunning():
                worker.requestInterruption()
                worker.wait(5000)
        mf = self.music_folder_input.text().strip()
        if mf:
            self.config["music_folder"] = mf
        if hasattr(self, "results_table"):
            self.results_table._save_column_layout()
        if hasattr(self, "editing_table"):
            self._save_editing_column_layout()
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

__all__ = ['MainWindow', 'run_app']
