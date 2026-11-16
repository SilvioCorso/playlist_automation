# Serato Playlist Automation
# Library cache module — safe JSON persistence (replaces the former pickle cache).
#
# Why JSON instead of pickle:
#   pickle.load() on a user-writable file is an arbitrary-code-execution risk
#   (a maliciously crafted .pkl could import/execute anything on load). JSON is
#   data-only and cannot execute code, so a tampered cache is at worst corrupt,
#   never dangerous. The cache holds only primitive LibraryTrack fields.
#
# Writes are atomic (tmp file + os.replace on the same volume) so a crash /
# blackout / antivirus lock mid-write cannot leave a half-written cache that
# would silently reset the user's library on next launch.

import json
import hashlib
import logging
import os
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import List, Optional

from .config import get_config_dir
from .library_reader import LibraryTrack

logger = logging.getLogger("serato.cache")

# Bump when the on-disk schema changes — old caches are ignored (full rescan).
CACHE_SCHEMA_VERSION = 2


def get_cache_path(folder: str) -> str:
    """Return the JSON cache path for *folder* (hashed so paths with odd chars
    still produce a safe filename)."""
    folder_hash = hashlib.md5(folder.encode("utf-8")).hexdigest()[:12]
    return os.path.join(get_config_dir(), f"library_cache_{folder_hash}.json")


def _serialize_tracks(tracks: List[LibraryTrack]) -> list:
    out = []
    for t in tracks:
        if is_dataclass(t):
            out.append(asdict(t))
        else:  # pragma: no cover - defensive
            out.append({"filepath": str(getattr(t, "filepath", "")),
                        "title": str(getattr(t, "title", "")),
                        "artist": str(getattr(t, "artist", ""))})
    return out


def _deserialize_tracks(data: list) -> List[LibraryTrack]:
    tracks: List[LibraryTrack] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        # Keep only fields that exist on LibraryTrack (forward-compat: extra
        # keys from a newer schema are ignored, missing keys fall back to defaults).
        known = {f.name for f in __fields(LibraryTrack)}
        kwargs = {k: v for k, v in item.items() if k in known}
        try:
            tracks.append(LibraryTrack(**kwargs))
        except TypeError:
            # A field changed type between versions — skip the bad row.
            continue
    return tracks


def __fields(cls):
    from dataclasses import fields as _fields
    return _fields(cls)


def save_library_cache(folder: str, tracks: List[LibraryTrack]) -> None:
    """Atomically write the library cache as JSON. Never raises."""
    try:
        cache_data = {
            "schema_version": CACHE_SCHEMA_VERSION,
            "folder": folder,
            "timestamp": datetime.now().isoformat(),
            "track_count": len(tracks),
            "tracks": _serialize_tracks(tracks),
        }
        path = get_cache_path(folder)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False)
        os.replace(tmp, path)  # atomic on the same volume
        logger.info("Cache libreria salvata: %d tracce", len(tracks))
    except Exception as e:
        logger.warning("Impossibile salvare cache: %s", e)


def load_library_cache(folder: str) -> Optional[List[LibraryTrack]]:
    """Load the JSON library cache for *folder*. Returns None if missing,
    schema-mismatched, or corrupt (caller will fall back to a full rescan)."""
    try:
        path = get_cache_path(folder)
        if not os.path.exists(path):
            # Silently ignore any legacy pickle cache — loading it would be the
            # exact RCE risk this module exists to remove.
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("folder") != folder:
            return None
        if data.get("schema_version") != CACHE_SCHEMA_VERSION:
            logger.info("Cache schema %s != %s — rescan richiesto",
                        data.get("schema_version"), CACHE_SCHEMA_VERSION)
            return None
        raw_tracks = data.get("tracks", [])
        if not raw_tracks:
            return None
        tracks = _deserialize_tracks(raw_tracks)
        if not tracks:
            return None
        logger.info("Cache libreria caricata: %d tracce (salvata: %s)",
                    len(tracks), data.get("timestamp", "sconosciuto"))
        return tracks
    except (json.JSONDecodeError, OSError, ValueError) as e:
        logger.warning("Cache corrotta, verrà ignorata: %s", e)
        return None
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("Impossibile caricare cache: %s", e)
        return None
