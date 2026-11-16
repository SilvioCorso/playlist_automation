"""Round-trip + defaults tests for the config module (atomic writes)."""
import json
import os

from serato_automation.config import load_config, save_config, DEFAULT_CONFIG


def test_load_missing_file_returns_defaults(tmp_path):
    p = tmp_path / "absent.json"
    cfg = load_config(str(p))
    # Every default key is present.
    for key in ("music_folder", "serato_folder", "match_thresholds",
                "audio_extensions", "theme", "language"):
        assert key in cfg
    # Default music_folder is empty (issue 4.8 — no hard-coded E:/).
    assert cfg["music_folder"] == ""


def test_save_then_load_round_trip(tmp_path):
    p = tmp_path / "c.json"
    cfg = dict(DEFAULT_CONFIG)
    cfg["music_folder"] = "/tmp/music"
    cfg["theme"] = "dark"
    cfg["bpm_penalty_enabled"] = True
    save_config(cfg, str(p))
    # Atomic write must not leave a .tmp behind.
    assert not os.path.exists(str(p) + ".tmp")
    reloaded = load_config(str(p))
    assert reloaded["music_folder"] == "/tmp/music"
    assert reloaded["theme"] == "dark"
    assert reloaded["bpm_penalty_enabled"] is True


def test_save_is_atomic_no_partial_file(tmp_path):
    """The output file is valid JSON after save (not truncated mid-write)."""
    p = tmp_path / "c.json"
    save_config({"music_folder": "", "output_folder": ""}, str(p))
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["music_folder"] == ""


def test_corrupt_file_falls_back_to_defaults(tmp_path):
    p = tmp_path / "c.json"
    p.write_text("{not valid json", encoding="utf-8")
    cfg = load_config(str(p))
    # Corrupt JSON must NOT crash — defaults are returned silently.
    assert cfg["music_folder"] == ""
