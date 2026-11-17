# Serato Playlist Automation
# Serato "database V2" reader
#
# Serato stores its library in a binary TLV file called "database V2" inside the
# per-drive "_Serato_" folder (a sibling of the "Subcrates" folder). It uses the
# same tag/length/value layout as .crate files:
#     4-byte ASCII tag | 4-byte big-endian length | value
# Top level holds a "vrsn" header followed by one "otrk" entry per track. Each
# "otrk" value is itself a TLV stream with sub-fields such as "pfil" (file path,
# UTF-16-BE), "tsng" (title), "tart" (artist), "talb" (album), ...
#
# Two capabilities:
#   * READ  — list the files Serato already has (diff against the folder scan).
#   * WRITE — update the cached tsng/tart/talb of specific tracks so Serato shows
#             edited metadata without replaying each track. Writing preserves
#             every other byte, creates a timestamped backup first, and MUST be
#             done with Serato closed (otherwise Serato overwrites it on exit).

import os
import re
import sys
import struct
import logging
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger('serato.database')

DATABASE_FILENAME = "database V2"

# otrk sub-field tags that map to the editable metadata columns.
_FIELD_TAGS = {"title": "tsng", "artist": "tart", "album": "talb", "genre": "tgen",
               "label": "tlbl", "comment": "tcom"}


def _iter_tlv(data: bytes):
    """Yield (tag, value) tuples from a Serato TLV byte stream."""
    i = 0
    n = len(data)
    while i + 8 <= n:
        tag = data[i:i + 4].decode('ascii', 'replace')
        length = int.from_bytes(data[i + 4:i + 8], 'big')
        start = i + 8
        end = start + length
        if end > n:
            break
        yield tag, data[start:end]
        i = end


def _decode_text(value: bytes) -> str:
    try:
        return value.decode('utf-16-be')
    except Exception:
        return value.decode('utf-16-be', 'replace')


def _encode_text(value: str) -> bytes:
    """Encode a string exactly like Serato: UTF-16-BE, no BOM, no terminator."""
    return (value or "").encode('utf-16-be')


def _encode_tlv(tag: str, value: bytes) -> bytes:
    return tag.encode('ascii') + struct.pack('>I', len(value)) + value


def normalize_rel_path(path: str) -> str:
    """Normalize a path to a drive-relative, lowercase, forward-slash form.

    This makes library file paths and Serato 'pfil' values comparable regardless
    of drive letter, slash direction or case:
        'E:\\selezioni\\File.mp3'  -> 'selezioni/file.mp3'
        'selezioni/File.mp3'       -> 'selezioni/file.mp3'
    """
    if not path:
        return ""
    p = path.strip().replace('\\', '/')
    if p.startswith('//?/'):
        p = p[4:]
    p = re.sub(r'^[A-Za-z]:', '', p)   # drop drive letter
    p = p.lstrip('/')
    return p.lower()


def find_serato_folder(music_folder: str = "") -> Optional[str]:
    """Locate the '_Serato_' directory on the same drive as the music."""
    from .crate_writer import find_serato_subcrates
    subcrates = find_serato_subcrates(music_folder)
    if not subcrates:
        return None
    # subcrates == '<_Serato_>/Subcrates'; its parent is the _Serato_ folder.
    parent = os.path.dirname(subcrates)
    if os.path.basename(subcrates).lower() == "subcrates":
        return parent
    return subcrates


def find_database_file(music_folder: str = "") -> Optional[str]:
    """Return the path to the Serato 'database V2' file, or None if not found."""
    serato_folder = find_serato_folder(music_folder)
    if not serato_folder:
        return None
    db_path = os.path.join(serato_folder, DATABASE_FILENAME)
    return db_path if os.path.isfile(db_path) else None


def find_all_serato_folders(music_folder: str = "") -> List[str]:
    """Return every '_Serato_' folder relevant to the library.

    Serato keeps a *main* library database in the user's home
    ('~/Music/_Serato_') plus one '_Serato_' folder on every drive that holds
    music. A track can be listed in more than one of these, so any cleanup
    (removing deleted tracks, updating metadata) must touch all of them —
    otherwise the browser keeps showing entries read from a database we skipped.
    """
    candidates: List[str] = []

    # Same-drive folder as the music (Subcrates-based discovery).
    same_drive = find_serato_folder(music_folder)
    if same_drive:
        candidates.append(same_drive)

    # Home / master library folder.
    home = os.path.expanduser("~")
    candidates.append(os.path.join(home, "Music", "_Serato_"))
    candidates.append(os.path.join(home, "_Serato_"))

    # Every drive root on Windows; mounted volumes on macOS.
    if sys.platform.startswith('win'):
        import string
        for letter in string.ascii_uppercase:
            root = f"{letter}:\\"
            if os.path.exists(root):
                candidates.append(os.path.join(root, "_Serato_"))
    elif sys.platform == 'darwin':
        vol_root = "/Volumes"
        if os.path.isdir(vol_root):
            for name in os.listdir(vol_root):
                candidates.append(os.path.join(vol_root, name, "_Serato_"))

    seen = set()
    out: List[str] = []
    for folder in candidates:
        if folder and os.path.isdir(folder):
            key = os.path.normcase(os.path.abspath(folder))
            if key not in seen:
                seen.add(key)
                out.append(folder)
    return out


def find_all_database_files(music_folder: str = "") -> List[str]:
    """Return every 'database V2' file across all relevant '_Serato_' folders."""
    out: List[str] = []
    for folder in find_all_serato_folders(music_folder):
        db_path = os.path.join(folder, DATABASE_FILENAME)
        if os.path.isfile(db_path):
            out.append(db_path)
    return out


def remove_from_all_databases(music_folder: str,
                              rel_paths,
                              backup: bool = True) -> Tuple[int, List[str]]:
    """Remove tracks from *every* Serato 'database V2' (home + per-drive).

    Returns ``(total_removed, backup_paths)``.
    """
    total = 0
    backups: List[str] = []
    for db_path in find_all_database_files(music_folder):
        try:
            removed, bak = remove_database_entries(db_path, rel_paths, backup=backup)
        except Exception:
            logger.exception("Impossibile pulire il database: %s", db_path)
            continue
        total += removed
        if bak:
            backups.append(bak)
    return total, backups


def read_database_paths(db_path: str) -> List[str]:
    """Return every raw 'pfil' path stored in the given database file."""
    paths: List[str] = []
    with open(db_path, 'rb') as f:
        data = f.read()
    for tag, value in _iter_tlv(data):
        if tag != 'otrk':
            continue
        for sub_tag, sub_val in _iter_tlv(value):
            if sub_tag == 'pfil':
                paths.append(_decode_text(sub_val))
                break
    return paths


def read_database_normalized_set(db_path: str) -> set:
    """Return a set of normalized relative paths known to Serato."""
    return {normalize_rel_path(p) for p in read_database_paths(db_path)}


def read_database_label_comment(db_path: str) -> Dict[str, Dict[str, str]]:
    """Read label (tlbl) and comment (tcom) for every track in the Serato DB V2.

    Returns {normalized_rel_path: {"label": str, "comment": str}} — values
    are empty strings if the field is absent in the DB for that track.
    """
    tag_to_field = {v: k for k, v in _FIELD_TAGS.items()}
    # Only care about label and comment.
    wanted_tags = {"tlbl", "tcom"}
    results: Dict[str, Dict[str, str]] = {}
    try:
        with open(db_path, 'rb') as f:
            data = f.read()
    except OSError:
        return results
    for tag, value in _iter_tlv(data):
        if tag != 'otrk':
            continue
        rel_path = ""
        fields: Dict[str, str] = {}
        for sub_tag, sub_val in _iter_tlv(value):
            if sub_tag == 'pfil':
                rel_path = normalize_rel_path(_decode_text(sub_val))
            elif sub_tag in wanted_tags:
                field = tag_to_field.get(sub_tag)
                if field:
                    fields[field] = _decode_text(sub_val)
        if rel_path:
            results[rel_path] = {
                "label": fields.get("label", ""),
                "comment": fields.get("comment", ""),
            }
    return results


# ----------------------------------------------------------------------
# Is Serato running? (must be closed before we touch the database)
# ----------------------------------------------------------------------

def is_serato_running() -> bool:
    """Best-effort check whether a Serato app is currently running."""
    try:
        if sys.platform.startswith('win'):
            out = subprocess.run(
                ["tasklist"], capture_output=True, text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ).stdout.lower()
        elif sys.platform == 'darwin':
            out = subprocess.run(["ps", "-Ax"], capture_output=True, text=True).stdout.lower()
        else:
            out = subprocess.run(["ps", "-A"], capture_output=True, text=True).stdout.lower()
    except Exception:
        return False
    return ("serato dj" in out) or ("seratodj" in out) or ("scratchlive" in out)


# ----------------------------------------------------------------------
# Write: update cached metadata inside "database V2"
# ----------------------------------------------------------------------

def _update_otrk(value: bytes, updates: Dict[str, dict]) -> Tuple[bytes, bool]:
    """Return (new_otrk_value, changed) applying metadata updates by pfil."""
    subs = list(_iter_tlv(value))

    rel = None
    for tag, val in subs:
        if tag == 'pfil':
            rel = normalize_rel_path(_decode_text(val))
            break
    if rel is None or rel not in updates:
        return value, False

    upd = updates[rel]
    tag_to_field = {v: k for k, v in _FIELD_TAGS.items()}

    new_subs = []
    seen = set()
    changed = False
    for tag, val in subs:
        field = tag_to_field.get(tag)
        if field is not None and field in upd:
            new_val = _encode_text(upd[field])
            seen.add(tag)
            if new_val != val:
                changed = True
            new_subs.append((tag, new_val))
        else:
            new_subs.append((tag, val))

    # Add any target field the entry did not already have.
    for field, tag in _FIELD_TAGS.items():
        if field in upd and tag not in seen:
            new_subs.append((tag, _encode_text(upd[field])))
            changed = True

    if not changed:
        return value, False

    buf = bytearray()
    for tag, val in new_subs:
        buf.extend(_encode_tlv(tag, val))
    return bytes(buf), True


def update_database_metadata(db_path: str,
                             updates_by_relpath: Dict[str, dict]) -> Tuple[int, str]:
    """Rewrite 'database V2', updating tsng/tart/talb for the given tracks.

    ``updates_by_relpath`` maps ``normalize_rel_path(filepath)`` to a dict with
    optional 'title' / 'artist' / 'album' keys. Every other byte of the database
    is preserved verbatim. A timestamped backup is written next to the database
    before it is replaced.

    Returns ``(updated_track_count, backup_path)``.
    """
    with open(db_path, 'rb') as f:
        data = f.read()

    backup_path = f"{db_path}.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with open(backup_path, 'wb') as f:
        f.write(data)

    out = bytearray()
    updated = 0
    for tag, value in _iter_tlv(data):
        if tag == 'otrk':
            new_val, changed = _update_otrk(value, updates_by_relpath)
            out.extend(_encode_tlv('otrk', new_val))
            if changed:
                updated += 1
        else:
            out.extend(_encode_tlv(tag, value))

    tmp_path = db_path + ".tmp"
    with open(tmp_path, 'wb') as f:
        f.write(bytes(out))
    os.replace(tmp_path, db_path)

    logger.info("database V2 aggiornato: %d tracce (backup: %s)", updated, backup_path)
    return updated, backup_path


def update_all_databases_metadata(music_folder: str,
                                  updates_by_relpath: Dict[str, dict]
                                  ) -> Tuple[int, str]:
    """Update metadata in *every* Serato 'database V2' (home + per-drive).

    A track can be listed in more than one database, so writing only the
    music-drive one can leave stale metadata in the master library. Returns
    ``(total_updated, first_backup_path)``.
    """
    total = 0
    first_backup = ""
    for db_path in find_all_database_files(music_folder):
        try:
            updated, backup = update_database_metadata(db_path, updates_by_relpath)
        except Exception:
            logger.exception("Impossibile aggiornare il database: %s", db_path)
            continue
        total += updated
        if backup and not first_backup:
            first_backup = backup
    return total, first_backup


def remove_database_entries(db_path: str,
                            rel_paths,
                            backup: bool = True) -> Tuple[int, str]:
    """Drop every 'otrk' entry whose 'pfil' matches one of ``rel_paths``.

    ``rel_paths`` is any iterable of file paths (they are normalized internally).
    Every other byte of the database is preserved verbatim. When ``backup`` is
    True a timestamped copy is written next to the database before it is replaced.

    Returns ``(removed_track_count, backup_path)`` (``backup_path`` is '' when
    ``backup`` is False).
    """
    targets = {normalize_rel_path(p) for p in rel_paths if p}
    if not targets:
        return 0, ""

    with open(db_path, 'rb') as f:
        data = f.read()

    backup_path = ""
    if backup:
        backup_path = f"{db_path}.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        with open(backup_path, 'wb') as f:
            f.write(data)

    out = bytearray()
    removed = 0
    for tag, value in _iter_tlv(data):
        if tag == 'otrk':
            rel = None
            for sub_tag, sub_val in _iter_tlv(value):
                if sub_tag == 'pfil':
                    rel = normalize_rel_path(_decode_text(sub_val))
                    break
            if rel is not None and rel in targets:
                removed += 1
                continue  # skip -> entry removed from the library
            out.extend(_encode_tlv('otrk', value))
        else:
            out.extend(_encode_tlv(tag, value))

    tmp_path = db_path + ".tmp"
    with open(tmp_path, 'wb') as f:
        f.write(bytes(out))
    os.replace(tmp_path, db_path)

    logger.info("database V2: rimosse %d tracce (backup: %s)", removed, backup_path or "-")
    return removed, backup_path


def _list_crate_files(music_folder: str = "") -> List[str]:
    """Return every .crate file across all relevant Serato Subcrates folders."""
    out = []
    seen = set()
    for folder in find_all_serato_folders(music_folder):
        subcrates = os.path.join(folder, "Subcrates")
        if not os.path.isdir(subcrates):
            continue
        for name in os.listdir(subcrates):
            if name.lower().endswith('.crate'):
                path = os.path.join(subcrates, name)
                key = os.path.normcase(os.path.abspath(path))
                if key not in seen:
                    seen.add(key)
                    out.append(path)
    return out


def remove_from_crates(music_folder: str, rel_paths) -> int:
    """Remove the given tracks from every Serato .crate file.

    Crates store each track as an ``otrk`` entry containing a ``ptrk`` path
    (UTF-16-BE, drive-relative). Any ``otrk`` whose ``ptrk`` matches one of
    ``rel_paths`` is dropped; all other bytes are preserved. A timestamped backup
    is written for each crate that actually changes.

    Returns the total number of track references removed across all crates.
    """
    targets = {normalize_rel_path(p) for p in rel_paths if p}
    if not targets:
        return 0

    removed_total = 0
    for crate_path in _list_crate_files(music_folder):
        try:
            with open(crate_path, 'rb') as f:
                data = f.read()
        except OSError as e:
            logger.warning("Impossibile leggere crate %s: %s", crate_path, e)
            continue

        out = bytearray()
        removed = 0
        for tag, value in _iter_tlv(data):
            if tag == 'otrk':
                rel = None
                for sub_tag, sub_val in _iter_tlv(value):
                    if sub_tag == 'ptrk':
                        rel = normalize_rel_path(_decode_text(sub_val))
                        break
                if rel is not None and rel in targets:
                    removed += 1
                    continue
                out.extend(_encode_tlv('otrk', value))
            else:
                out.extend(_encode_tlv(tag, value))

        if removed:
            try:
                backup = f"{crate_path}.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                with open(backup, 'wb') as f:
                    f.write(data)
            except Exception:
                pass
            tmp_path = crate_path + ".tmp"
            with open(tmp_path, 'wb') as f:
                f.write(bytes(out))
            os.replace(tmp_path, crate_path)
            removed_total += removed
            logger.info("crate %s: rimosse %d tracce", os.path.basename(crate_path), removed)

    return removed_total
