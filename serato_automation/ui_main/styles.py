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

# Module-level flag: set True when dark theme is active.
# Updated by MainWindow._apply_theme() — read by score_to_bg/text_color and row highlighters.
_DARK_THEME_ACTIVE: bool = False
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


__all__ = ['_DARK_THEME_ACTIVE', 'score_to_bg_color', 'score_to_text_color', 'APP_STYLESHEET', 'DARK_APP_STYLESHEET', '_make_stylesheet']
