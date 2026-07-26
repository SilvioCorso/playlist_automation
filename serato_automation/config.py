# Serato Playlist Automation
# Configuration module - centralized settings

import json
import os
import sys
from pathlib import Path

DEFAULT_CONFIG = {
    "music_folder": "",
    "serato_folder": "",
    "output_folder": "",
    "match_thresholds": {
        "exact": 100,
        "token_sort": 85,
        "token_set": 75,
        "partial": 60
    },
    "audio_extensions": [
        ".mp3", ".flac", ".m4a", ".wav", ".aiff", ".ogg", ".wma", ".aac"
    ],
    "fuzzy_cache_enabled": True,
    "theme": "light",
    "visible_columns": {
        "lock": True, "select": True, "score": True, "found": True,
        "titolo_richiesto": True, "filename": True, "artista_serato": True,
        "song_serato": True, "genre": True, "bpm": True, "comment": True, "player": True,
    },
    "bpm_penalty_enabled": False,
    "bpm_reference": 0,
    "font_size": 11,
    "language": "auto",
    "dj_software": "serato",
    "settings_dialog_size": {"width": 560, "height": 500},
    "auto_update": False,
    "skip_rescan_dialog": False,
    "default_rescan_answer": "yes",
    "results_table_columns": {
        "order": [],
        "widths": {},
    },
    "table_fit_columns": False,
    "license_pro": False,          # placeholder — set True when licensing backend validates
}

# Default paths for Windows
if sys.platform == 'win32' or sys.platform == 'cygwin':
    _user_home = os.path.expanduser("~")
    DEFAULT_CONFIG["music_folder"] = "E:/"
    # Output folder defaults to Desktop
    DEFAULT_CONFIG["output_folder"] = os.path.join(_user_home, "Desktop")

CONFIG_PATH = None


def get_config_dir():
    """Get the configuration directory (next to the executable or in user home)."""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        # Base is the project root (where main.py lives)
        base = os.path.dirname(os.path.abspath(__file__))
        # If inside serato_automation/, go up one level
        if os.path.basename(base) == 'serato_automation':
            base = os.path.dirname(base)
    return base


def get_default_config_path():
    """Get the default path for config.json."""
    config_dir = get_config_dir()
    return os.path.join(config_dir, "config.json")


def load_config(config_path=None):
    """Load configuration from JSON file. Create default if not exists."""
    global CONFIG_PATH
    if config_path is None:
        config_path = get_default_config_path()
    CONFIG_PATH = config_path

    config = dict(DEFAULT_CONFIG)
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                config.update(user_config)
        except (json.JSONDecodeError, IOError):
            pass
    return config


def save_config(config, config_path=None):
    """Save configuration to JSON file."""
    if config_path is None:
        config_path = CONFIG_PATH or get_default_config_path()
    config_dir = os.path.dirname(config_path)
    if config_dir:
        os.makedirs(config_dir, exist_ok=True)
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_music_folder(config):
    """Get the configured music folder path."""
    return config.get("music_folder", "")
