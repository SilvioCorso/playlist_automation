"""JSON library cache — round-trip, schema mismatch, corruption safety.

Validates the fix for audit issue 4.4: pickle.load was replaced by json.load,
so a tampered cache cannot execute code and a corrupt cache degrades to None
(full rescan) instead of crashing.
"""
import os

from serato_automation import cache
from serato_automation.library_reader import LibraryTrack


def test_save_load_round_trip(tmp_path):
    folder = str(tmp_path / "music")
    os.makedirs(folder)
    tracks = [
        LibraryTrack(title="Titanium", artist="David Guetta",
                     filepath=os.path.join(folder, "a.mp3"), bpm="128"),
        LibraryTrack(title="Levels", artist="Avicii",
                     filepath=os.path.join(folder, "b.flac"), file_size=9999),
    ]
    cache.save_library_cache(folder, tracks)
    loaded = cache.load_library_cache(folder)
    assert loaded is not None
    assert len(loaded) == 2
    assert loaded[0].title == "Titanium" and loaded[0].bpm == "128"
    assert loaded[1].artist == "Avicii" and loaded[1].file_size == 9999


def test_load_missing_returns_none(tmp_path):
    assert cache.load_library_cache(str(tmp_path / "nope")) is None


def test_corrupt_cache_returns_none(tmp_path):
    folder = str(tmp_path / "music")
    os.makedirs(folder)
    cache.save_library_cache(folder, [LibraryTrack(title="X", artist="Y")])
    p = cache.get_cache_path(folder)
    with open(p, "w", encoding="utf-8") as f:
        f.write("{this is not json")
    assert cache.load_library_cache(folder) is None


def test_folder_mismatch_returns_none(tmp_path):
    folder = str(tmp_path / "music")
    os.makedirs(folder)
    cache.save_library_cache(folder, [LibraryTrack(title="X", artist="Y")])
    # Same cache file, but queried with a different folder path.
    assert cache.load_library_cache(folder + "_other") is None


def test_no_pickle_exec_surface(tmp_path):
    """The cache file is plain JSON text, never pickle bytecode."""
    folder = str(tmp_path / "music")
    os.makedirs(folder)
    cache.save_library_cache(folder, [LibraryTrack(title="X", artist="Y")])
    with open(cache.get_cache_path(folder), "rb") as f:
        head = f.read(4)
    # Pickle streams start with b'\x80\x04' (protocol 2+) — JSON starts with '{'.
    assert head == b"{\n  " or head.startswith(b"{")
