# Serato Playlist Automation
# Crate writer module - creates Serato .crate files
# v2.2: Volume-label based drive detection
#   - When an external HDD is plugged into a different USB port, Windows
#     assigns a different drive letter (e.g. E: -> F:). The previous code
#     would show "DISCO SBAGLIATO" because the saved config paths no longer
#     matched. We now use the Windows volume label (e.g. "DJ MUSIC") as a
#     stable identifier — when the saved path's drive letter doesn't exist
#     anymore, we scan all drives and find the one with the same volume
#     label, then rewrite the path with the new drive letter.
# v2.1: Fixed critical drive mismatch bug
#   - Crate MUST be created in _Serato_/Subcrates on the SAME DRIVE as music files
#   - If crate is on C: but music is on E:, Serato resolves relative paths to C: → "track not found"
#   - Added get_drive_letter(), validate_crate_drive(), improved find_serato_subcrates()
#   - NO fallback to ~/Music/_Serato_ when music is on a different drive
# v1.8: MATCHES EXACT Serato format from real crate analysis:
#   - NO BOM in text values (confirmed: vrsn starts with 00 31, not FE FF)
#   - NO null terminator (confirmed: vrsn ends with 00 65, no trailing 00 00)
#   - Path WITHOUT drive letter (confirmed: Users/... not C:/Users/...)
#   - 8 column definitions: song, artist, bpm, key, album, length, comment
#   - Column widths as text strings: "250" (not "0")

import os
import re
import sys
import struct
import logging
import string
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .track_matcher import MatchResult

logger = logging.getLogger('serato.crate')


# ---------------------------------------------------------------------------
# Volume label / drive identification (Windows)
# ---------------------------------------------------------------------------
#
# The fundamental problem we're solving here:
#   - User saves config.json with music_folder="E:/DJ Music" and
#     serato_folder="E:/_Serato_/Subcrates"
#   - Next day they plug the external HDD into a different USB port
#   - Windows assigns F: as the drive letter (E: is no longer present)
#   - The app reads the saved paths, sees E: doesn't exist, and the
#     "Match with Library" button is disabled because os.path.isdir()
#     returns False for E:/DJ Music
#
# Solution: identify the drive by its VOLUME SERIAL NUMBER — a 32-bit
# hexadecimal ID that Windows assigns to EVERY formatted partition,
# regardless of whether the user has set a custom volume label.
# The serial number is:
#   - Always present (even on disks without a label)
#   - Stable across reboots and USB port changes
#   - Unique per partition with very high probability
#   - Re-rolled only when the user reformats the partition
#
# As an additional fallback we also support matching by volume label,
# but the serial number is the primary identifier because it works
# even when the user has not personalized the disk name.

def _get_volume_info(drive_or_path: str) -> Optional[Tuple[str, str]]:
    """Return (volume_label, serial_hex) for a Windows drive or path.

    The serial_hex is always returned when possible, even if the volume
    label is empty (the user didn't name the disk). This is the key
    improvement that lets us auto-remap paths on disks WITHOUT a label.

    Returns None on non-Windows platforms or if the drive can't be queried.
    """
    if not sys.platform.startswith('win'):
        return None
    if not drive_or_path:
        return None
    try:
        import ctypes
    except ImportError:
        return None

    # Normalize to a drive root path like "F:\\" — GetVolumeInformationW
    # accepts any path on the target drive, but the root is most reliable.
    drive_letter = get_drive_letter(drive_or_path)
    if not drive_letter:
        return None
    root = f"{drive_letter}:\\"
    if not os.path.exists(root):
        return None

    try:
        kernel32 = ctypes.windll.kernel32
        volume_name_buf = ctypes.create_unicode_buffer(1024)
        fs_name_buf = ctypes.create_unicode_buffer(1024)
        serial = ctypes.c_uint32(0)
        max_len = ctypes.c_uint32(0)
        flags = ctypes.c_uint32(0)

        ok = kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(root),
            volume_name_buf,
            ctypes.sizeof(volume_name_buf),
            ctypes.byref(serial),
            ctypes.byref(max_len),
            ctypes.byref(flags),
            fs_name_buf,
            ctypes.sizeof(fs_name_buf),
        )
        if not ok:
            return None
        label = volume_name_buf.value or ""
        # Always format the serial as 8-digit uppercase hex, even if 0
        # (a serial of 0 is rare but possible on some FAT32 partitions,
        # and we still want to identify the disk somehow)
        serial_hex = f"{serial.value:08X}"
        return (label, serial_hex)
    except Exception as e:
        logger.debug("GetVolumeInformationW failed for %s: %s", root, e)
        return None


def get_volume_label(drive_or_path: str) -> str:
    """Return the volume label of the drive containing the given path.

    Returns empty string if not on Windows, if the drive can't be queried,
    or if the disk has no label set by the user.
    """
    info = _get_volume_info(drive_or_path)
    return info[0] if info else ""


def get_volume_serial(drive_or_path: str) -> str:
    """Return the volume serial number (8-char hex) of the drive containing
    the given path.

    Returns empty string if not on Windows or if the drive can't be queried.
    The serial is always present on a formatted Windows partition, so this
    is the most reliable way to identify a disk across USB port changes.
    """
    info = _get_volume_info(drive_or_path)
    return info[1] if info else ""


def get_volume_identifier(drive_or_path: str) -> str:
    """Return a stable identifier for the drive hosting the given path.

    Preference order:
      1. Volume serial number (always present on formatted partitions)
      2. Volume label (only if the user has set one)
      3. Empty string (gave up — caller should fall back to manual selection)

    The serial is preferred because it works even on disks that have no
    user-set label. The label is kept as a secondary identifier for
    backward-compat with configs saved before the serial-number support
    was added.
    """
    info = _get_volume_info(drive_or_path)
    if not info:
        return ""
    label, serial = info
    if serial and serial != "00000000":
        return f"serial:{serial}"
    if label and label.strip():
        return f"label:{label.strip()}"
    return ""


def find_drive_by_volume_label(label: str) -> Optional[str]:
    """Scan all available drives and return the drive letter whose volume
    label matches the given label (case-insensitive).

    Returns None if no match, or on non-Windows platforms.
    Kept for backward compatibility — new code should use
    find_drive_by_identifier() which checks serial first, then label.
    """
    if not sys.platform.startswith('win'):
        return None
    if not label:
        return None

    label_norm = (label or "").strip().lower()
    if not label_norm:
        return None

    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if not os.path.exists(root):
            continue
        info = _get_volume_info(letter + ":")
        if not info:
            continue
        vol_label = info[0]
        if vol_label and vol_label.strip().lower() == label_norm:
            logger.info(
                "Volume label '%s' matched drive %s: (serial %s)",
                label, letter, info[1]
            )
            return letter
    return None


def find_drive_by_serial(serial_hex: str) -> Optional[str]:
    """Scan all available drives and return the drive letter whose volume
    serial number matches the given hex string (case-insensitive).

    Returns None if no match, or on non-Windows platforms.
    The serial is the most reliable identifier: it is always present on
    a formatted partition (even without a label) and is stable across
    reboots and USB port changes.
    """
    if not sys.platform.startswith('win'):
        return None
    if not serial_hex:
        return None

    serial_norm = serial_hex.strip().upper().lstrip("0") or "0"
    # Also compare without leading zeros since "00000001" == "1"
    # Some Windows versions pad with zeros, some don't.

    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if not os.path.exists(root):
            continue
        info = _get_volume_info(letter + ":")
        if not info:
            continue
        drive_serial = info[1]
        drive_serial_norm = drive_serial.strip().upper().lstrip("0") or "0"
        if drive_serial_norm == serial_norm:
            logger.info(
                "Volume serial %s matched drive %s: (label %r)",
                serial_hex, letter, info[0]
            )
            return letter
    return None


def find_drive_by_identifier(identifier: str) -> Optional[str]:
    """Find a drive by its identifier (as returned by get_volume_identifier).

    Accepts identifiers in the form:
      - "serial:ABCD1234" — match by volume serial number (preferred)
      - "label:DJ MUSIC"  — match by volume label (fallback)
      - "DJ MUSIC"        — bare label, treated as "label:..." for compat

    Returns the matched drive letter, or None if no match.
    """
    if not identifier:
        return None

    ident = identifier.strip()
    if ident.lower().startswith("serial:"):
        serial = ident[len("serial:"):]
        return find_drive_by_serial(serial)
    if ident.lower().startswith("label:"):
        label = ident[len("label:"):]
        return find_drive_by_volume_label(label)
    # Backward compat: bare label
    return find_drive_by_volume_label(ident)


def remap_path_to_current_drive(saved_path: str, saved_identifier: str) -> Optional[str]:
    """If `saved_path` no longer exists (drive letter changed), try to find
    a drive with the same volume identifier and return the path with the
    new drive letter.

    The identifier is what get_volume_identifier() returned when the path
    was originally saved — typically "serial:ABCD1234" for new saves, or
    "label:DJ MUSIC" / bare "DJ MUSIC" for old configs.

    Returns:
      - The remapped path (str) if a matching drive was found
      - The original path (str) if it still exists (no remap needed)
      - None if the path doesn't exist AND no matching drive was found
    """
    if not saved_path:
        return None
    # Fast path: the saved path still works (drive letter unchanged)
    if os.path.exists(saved_path):
        return saved_path
    # Saved path doesn't exist — try to remap by identifier
    if not saved_identifier:
        return None
    new_letter = find_drive_by_identifier(saved_identifier)
    if not new_letter:
        return None
    # Reconstruct the path with the new drive letter
    # Preserve everything after the drive letter
    saved_letter = get_drive_letter(saved_path)
    if not saved_letter:
        return None
    # Replace "<old>:" with "<new>:" at the start of the path
    suffix = saved_path[len(saved_letter) + 1:]  # skip "X:"
    # Handle both "X:/foo" and "X:\\foo"
    if suffix.startswith(":"):
        suffix = suffix[1:]
    new_path = f"{new_letter}:{suffix}"
    if os.path.exists(new_path):
        logger.info(
            "Remapped path by identifier %r: '%s' -> '%s'",
            saved_identifier, saved_path, new_path
        )
        return new_path
    # Even with the right drive, the sub-path changed — give up
    logger.warning(
        "Identifier %r matched drive %s: but path '%s' still doesn't exist",
        saved_identifier, new_letter, new_path
    )
    return None


# ---------------------------------------------------------------------------
# Drive letter helpers (legacy, kept for backward compat)
# ---------------------------------------------------------------------------


@dataclass
class CrateLocationInfo:
    """Information about where a crate will be created."""
    path: str
    drive_letter: str
    music_drive: str
    is_same_drive: bool
    source: str  # 'auto', 'config', 'manual', 'fallback'
    warning: str = ""


def get_drive_letter(path: str) -> str:
    """Extract drive letter from a Windows path. Returns '' if no drive letter."""
    if not path:
        return ""
    p = os.path.normpath(path)
    if len(p) >= 2 and p[1] == ':':
        return p[0].upper()
    # Handle paths like "E:/" directly
    if len(path) >= 2 and path[1] == ':':
        return path[0].upper()
    return ""


def validate_crate_drive(music_folder: str, crate_output_dir: str) -> Tuple[bool, str]:
    """Check if the crate output directory is on the same drive as the music files.

    Returns:
        (is_valid, message) — is_valid is True if drives match or can't be determined
    """
    music_drive = get_drive_letter(music_folder)
    crate_drive = get_drive_letter(crate_output_dir)

    if not music_drive:
        return True, "Impossibile determinare l'unita' della musica (path non Windows)"
    if not crate_drive:
        return True, f"Impossibile determinare l'unita' della crate"

    if music_drive != crate_drive:
        return False, (
            f"ERRORE CRITICO: La crate verra' creata sul disco {crate_drive}: "
            f"ma la tua musica e' sul disco {music_drive}: !\n\n"
            f"Serato risolvera' i percorsi relativi delle canzoni sul disco {crate_drive}: "
            f"invece che su {music_drive}:, e le canzoni NON saranno trovate!\n\n"
            f"La crate deve essere creata in:\n"
            f"  {music_drive}:\\_Serato_\\Subcrates\\\n\n"
            f"Non in:\n"
            f"  {crate_output_dir}"
        )
    return True, f"OK - Crate e musica entrambi sul disco {music_drive}:"


def _sanitize_crate_path(raw_path: str) -> str:
    """Sanitize path for Serato crate format.

    Serato stores paths RELATIVE to the drive root, without drive letter.
    Example: 'E:/selezioni/Reggaeton/file.mp3' becomes 'selezioni/Reggaeton/file.mp3'
    Forward slashes are used on all platforms.
    """
    if not raw_path:
        return raw_path

    p = raw_path.strip()
    original = p

    # Strip UNC prefix
    if p.startswith('\\\\?\\'):
        p = p[4:]
    elif p.startswith('//?/'):
        p = p[4:]

    # Strip ALL leading slashes/backslashes
    while p and p[0] in ('/', '\\'):
        p = p[1:]

    # Fix doubled drive letters
    while True:
        new_p = re.sub(r'^([A-Za-z]:[\\/])\1', r'\1', p)
        if new_p == p:
            break
        p = new_p

    # Normalize
    p = os.path.normpath(p)

    # Safety: strip leading separator before drive
    while p and len(p) >= 3 and p[0] in ('/', '\\') and p[1].isalpha() and p[2] == ':':
        p = p[1:]
        p = os.path.normpath(p)

    # Final: fix doubled drive again after normpath
    while True:
        new_p = re.sub(r'^([A-Za-z]:[\\/])\1', r'\1', p)
        if new_p == p:
            break
        p = new_p

    # Convert to forward slashes
    p = p.replace('\\', '/')

    # CRITICAL: Remove the drive letter prefix!
    # Serato crate format uses paths relative to the drive root.
    # 'E:/selezioni/file.mp3' → 'selezioni/file.mp3'
    drive_match = re.match(r'^([A-Za-z]:)/', p)
    if drive_match:
        p = p[len(drive_match.group(0)):]
        logger.info("  Drive letter removed: '%s' -> '%s'", drive_match.group(0), p)

    if p != original:
        logger.info("  Crate path: '%s' -> '%s'", original, p)

    logger.info("  Final crate path (no drive): '%s'", p)

    return p


def _write_debug_log(crate_path: str, paths: list, crate_drive: str = "",
                     music_drive: str = ""):
    """Write debug log of crate paths."""
    try:
        log_path = crate_path + ".paths.log"
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(f"Crate: {crate_path}\n")
            f.write(f"Tracks: {len(paths)}\n")
            f.write(f"Crate drive: {crate_drive or 'N/A'}\n")
            f.write(f"Music drive: {music_drive or 'N/A'}\n")
            f.write("=" * 60 + "\n")
            for i, p in enumerate(paths):
                f.write(f"{i+1}. {p}\n")
    except Exception:
        pass


def _tlv(tag: str, value: bytes) -> bytes:
    return tag.encode('ascii') + struct.pack('>I', len(value)) + value

def _t_text(value: str) -> bytes:
    """Encode string as UTF-16-BE.

    Matches EXACT Serato crate format:
    - NO BOM (confirmed by analyzing real crateFromSerato.crate)
    - NO null terminator (confirmed: vrsn value ends with last char, no padding)
    """
    return value.encode('utf-16-be')

def _t_uint(value: int) -> bytes:
    return struct.pack('>I', value)

def _t_bool(value: bool) -> bytes:
    return b'\x01' if value else b'\x00'

def _container(entries: list) -> bytes:
    buf = bytearray()
    for tag, val in entries:
        buf.extend(_tlv(tag, val))
    return bytes(buf)


SERATO_VERSION = "1.0/Serato ScratchLive Crate"
# Match Serato's exact column list with correct widths
DEFAULT_COLUMNS = [
    ("song", "250"),
    ("artist", "250"),
    ("bpm", "30"),
    ("key", "30"),
    ("album", "250"),
    ("length", "250"),
    ("comment", "250"),
]


class CrateWriter:

    def __init__(self, use_pyserato=False):
        self.use_pyserato = use_pyserato

    def create_crate(self, track_paths: List[str], crate_name: str,
                     output_dir: str) -> Optional[str]:
        if not track_paths:
            return None

        os.makedirs(output_dir, exist_ok=True)
        crate_filename = f"{crate_name}.crate"
        crate_path = os.path.join(output_dir, crate_filename)

        # Determine drives for debug log
        crate_drive = get_drive_letter(output_dir)
        music_drive = get_drive_letter(track_paths[0]) if track_paths else ""

        logger.info("CREAZIONE CRATE: %s (%d tracce)", crate_name, len(track_paths))
        logger.info("  Output dir: %s (drive %s:)", output_dir, crate_drive or '?')
        logger.info("  Music drive: %s:", music_drive or '?')

        clean_paths = []
        for p in track_paths:
            # Per-track existence stat removed — it was only used for logging and
            # costs one syscall per track (slow on SMB/NFS shares for big crates).
            logger.debug("  Traccia orig: '%s'", p)
            sanitized = _sanitize_crate_path(p)
            logger.debug("  Traccia sanit: '%s'", sanitized)
            clean_paths.append(sanitized)

        # Deduplicate
        seen = set()
        unique = []
        for p in clean_paths:
            if p not in seen:
                seen.add(p)
                unique.append(p)
        clean_paths = unique

        if not clean_paths:
            logger.error("NESSUN percorso valido dopo sanificazione!")
            return None

        _write_debug_log(crate_path, clean_paths, crate_drive, music_drive)
        success = self._write_binary(clean_paths, crate_path)
        if success:
            logger.info("Crate creata: %s", crate_path)
        else:
            logger.error("Errore scrittura crate: %s", crate_path)
        return crate_path if success else None

    def create_crate_from_results(self, results: List[MatchResult],
                                  crate_name: str,
                                  output_dir: str) -> Optional[str]:
        paths = []
        for r in results:
            if r.is_effectively_matched and r.library_track:
                paths.append(r.library_track.filepath)
        return self.create_crate(paths, crate_name, output_dir)

    def _write_binary(self, paths: List[str], filepath: str) -> bool:
        try:
            data = bytearray()

            # vrsn
            data.extend(_tlv('vrsn', _t_text(SERATO_VERSION)))

            # Column definitions (ovct) — match Serato's exact format
            # NO osrt tag — Serato's crate doesn't have it
            for col_name, col_width in DEFAULT_COLUMNS:
                ovct = _container([
                    ('tvcn', _t_text(col_name)),
                    ('tvcw', _t_text(col_width))
                ])
                data.extend(_tlv('ovct', ovct))

            # Tracks (otrk > ptrk)
            for path in paths:
                otrk = _container([('ptrk', _t_text(path))])
                data.extend(_tlv('otrk', otrk))

            # Log crate info
            logger.info("  Crate binary: %d bytes, %d tracks", len(data), len(paths))
            if paths:
                try:
                    idx = bytes(data).find(b'otrk')
                    if idx >= 0:
                        otrk_len = int.from_bytes(data[idx+4:idx+8], 'big')
                        otrk_data = bytes(data[idx+8:idx+8+min(200, otrk_len)])
                        ptrk_idx = otrk_data.find(b'ptrk')
                        if ptrk_idx >= 0:
                            ptrk_len = int.from_bytes(otrk_data[ptrk_idx+4:ptrk_idx+8], 'big')
                            ptrk_bytes = otrk_data[ptrk_idx+8:ptrk_idx+8+ptrk_len]
                            try:
                                decoded = ptrk_bytes.decode('utf-16-be')
                                logger.info("  First ptrk decoded: '%s'", decoded)
                            except Exception as de:
                                logger.info("  ptrk decode error: %s", de)
                except Exception:
                    pass

            with open(filepath, 'wb') as f:
                f.write(bytes(data))
            return True
        except Exception as e:
            logger.error("Errore scrittura: %s", e)
            import traceback
            traceback.print_exc()
            return False


def _get_available_drives() -> list:
    """Get list of available drive letters on Windows."""
    import string
    drives = []
    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\"
        if os.path.exists(drive):
            drives.append(letter)
    return drives


def find_serato_subcrates(music_folder: str = "") -> Optional[str]:
    """Find the Serato _Serato_/Subcrates directory.

    CRITICAL: The crate MUST be in _Serato_/Subcrates on the SAME DRIVE as music files.
    Serato resolves relative crate paths from the drive where the crate file lives.
    If music is on E: and crate is on C:, Serato looks for files on C: → "track not found"!

    Search strategy (ordered by priority):
    1. If music_folder is provided, look for _Serato_ on the SAME DRIVE as music
       - Check drive_root/_Serato_/Subcrates
       - Check drive_root/_Serato_/ (and create Subcrates if missing)
    2. If config provides an explicit serato_folder, use that
    3. Scan ALL available drives for _Serato_/Subcrates
    4. If no _Serato_ found on music drive, return None (DO NOT fall back to wrong drive!)
    """
    # Determine which drive the music files are on
    music_drive = None
    if music_folder:
        mf = os.path.normpath(music_folder)
        if len(mf) >= 2 and mf[1] == ':':
            music_drive = mf[0].upper()
        elif len(music_folder) >= 2 and music_folder[1] == ':':
            music_drive = music_folder[0].upper()

    if music_drive:
        logger.info("Music folder drive: %s:", music_drive)
    else:
        logger.info("Music folder: no drive letter detected in '%s'", music_folder)

    # Strategy 1: Check same drive as music folder (HIGHEST PRIORITY)
    if music_drive:
        drive_root = f"{music_drive}:\\"
        serato_on_drive = os.path.join(drive_root, "_Serato_")
        subcrates = os.path.join(serato_on_drive, "Subcrates")

        if os.path.isdir(subcrates):
            logger.info("Found _Serato_/Subcrates on music drive %s: %s",
                        music_drive, subcrates)
            return subcrates

        if os.path.isdir(serato_on_drive):
            logger.info("Found _Serato_ (no Subcrates dir) on music drive %s: %s",
                        music_drive, serato_on_drive)
            # Create Subcrates directory if _Serato_ exists but Subcrates doesn't
            try:
                os.makedirs(subcrates, exist_ok=True)
                logger.info("Created Subcrates dir: %s", subcrates)
                return subcrates
            except Exception as e:
                logger.warning("Could not create Subcrates dir: %s", e)
                return serato_on_drive

        # Drive exists but _Serato_ doesn't exist at all
        if os.path.exists(drive_root):
            logger.warning(
                "Drive %s: exists but _Serato_ folder NOT found at %s",
                music_drive, serato_on_drive
            )
            logger.warning(
                "ASSICURATI che Serato abbia scansionato il disco %s: almeno una volta. "
                "Apri Serato, vai su Setup > Library + Display e aggiungi il disco %s:.",
                music_drive, music_drive
            )

    # Strategy 2: Scan ALL drives for _Serato_/Subcrates
    available_drives = _get_available_drives()
    logger.info("Available drives: %s", available_drives)

    other_drive_found = None
    for letter in available_drives:
        if letter == music_drive:
            continue  # Already checked above
        drive_root = f"{letter}:\\"
        serato_on_drive = os.path.join(drive_root, "_Serato_")
        subcrates = os.path.join(serato_on_drive, "Subcrates")
        if os.path.isdir(subcrates):
            other_drive_found = (letter, subcrates)
            logger.info("Found _Serato_ on OTHER drive %s: %s", letter, subcrates)
            break

    # If we found _Serato_ on a different drive than music, this is DANGEROUS
    if other_drive_found and music_drive:
        letter, path = other_drive_found
        logger.warning(
            "ATTENZIONE: Trovato _Serato_ sul disco %s: (%s) ma la musica e' sul disco %s:! "
            "La crate NON funzionera' perche' Serato cerchera' le canzoni sul disco sbagliato. "
            "NON verra' usato questo percorso.",
            letter, path, music_drive
        )
        # DO NOT return this path! Return None to force user to fix the issue.
        return None

    if other_drive_found and not music_drive:
        # No music drive detected but found _Serato_ somewhere — use it as fallback
        letter, path = other_drive_found
        logger.info("No music drive detected, using _Serato_ from drive %s: %s",
                    letter, path)
        return path

    # Strategy 3: If we have a music drive but _Serato_ doesn't exist there,
    # DO NOT fall back to ~/Music/_Serato_ (that's on C: and would break paths!)
    if music_drive:
        logger.error(
            "Nessuna cartella _Serato_ trovata sul disco %s:. "
            "La crate NON puo' essere creata sulla posizione corretta. "
            "Apri Serato e assicurati che il disco %s: sia stato scansionato.",
            music_drive, music_drive
        )
        return None

    # No music drive at all — try user home as last resort
    for music_dir in [
        os.path.join(os.path.expanduser("~"), "Music"),
        os.path.join(os.path.expanduser("~"), "Musica"),
    ]:
        serato_dir = os.path.join(music_dir, "_Serato_")
        if os.path.isdir(serato_dir):
            subcrates = os.path.join(serato_dir, "Subcrates")
            return subcrates if os.path.isdir(subcrates) else serato_dir

    logger.info("No _Serato_ folder found on any drive or home directory")
    return None
