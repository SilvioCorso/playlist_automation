# Serato Playlist Automation
# Library reader module - scans music folders and extracts metadata
#
# v1.9:
#   - FIX: FLAC composer lock now writes list value (Vorbis comment format)
# v1.8:
#   - NEW: composer field added to LibraryTrack (extracted from TCOM/Vorbis/©wrt)
#   - NEW: is_composer_locked property on LibraryTrack
#   - NEW: set_composer_lock() — safely writes/removes [lock] tag from audio metadata
#   - Supports MP3 (TCOM), FLAC (composer), M4A (©wrt), WAV (TCOM ID3)
# v1.7 fixes:
#   - WAV: fixed ID3 tags from WAVE().tags (TBPM, TIT2, TPE1, TKEY)
#     Previous code looked for RIFF keys (INAM, IART) but these WAV files
#     store metadata as ID3v2 frames accessible via WAVE().tags
#   - Much more verbose logging: raw tag values, each extraction step
#   - Path verification at scan-time: if path doesn't exist, auto-fix it
#   - Folder path sanitization before os.walk

import os
import re
import logging
import unicodedata
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger('serato.library')

# Directory names to skip while scanning (OS trash + system folders). Compared
# case-insensitively; '.trash*' prefixes are handled separately.
_EXCLUDED_SCAN_DIRS = frozenset({
    '$recycle.bin', 'recycler', 'system volume information',
    'found.000', '.trashes', '_serato_',
})


@dataclass
class LibraryTrack:
    """Represents a single track in the music library."""
    title: str = ""
    artist: str = ""
    album: str = ""
    genre: str = ""
    bpm: str = ""
    key: str = ""
    comment: str = ""
    composer: str = ""
    year: str = ""
    duration: float = 0.0
    filepath: str = ""
    file_size: int = 0
    bitrate: int = 0

    @property
    def is_composer_locked(self) -> bool:
        """Check if this track has the [lock] tag in its composer field."""
        return bool(self.composer and "[lock]" in self.composer.lower())

    @property
    def display_name(self):
        if self.artist and self.title:
            return f"{self.artist} - {self.title}"
        return self.title or os.path.basename(self.filepath)

    @property
    def search_key(self):
        return normalize_string(f"{self.artist} {self.title}")

    @property
    def filename_stem(self):
        return os.path.splitext(os.path.basename(self.filepath))[0]

    @property
    def filename_search_key(self):
        return normalize_string(self.filename_stem)

    def __str__(self):
        return self.display_name


def repair_mojibake(s: str) -> str:
    """Repair classic double-encoded UTF-8 text (e.g. 'PreparÃ³' -> 'Preparó').

    Some taggers / Serato store UTF-8 bytes that were later decoded as
    cp1252/latin-1, producing sequences such as 'Ã©', 'Ã³', 'Ã¨'. We reverse
    that by re-encoding to cp1252 and decoding again as UTF-8.

    It is only attempted when a typical marker character ('Ã' or 'Â') is
    present, and the result is discarded if the round-trip fails — so plain
    ASCII / already-correct strings pass through untouched.
    """
    if not s or ('Ã' not in s and 'Â' not in s):
        return s
    try:
        return s.encode('cp1252').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def normalize_string(s: str) -> str:
    """Normalize a string for fuzzy matching.

    Steps:
    - Repair double-encoded UTF-8 (mojibake) so 'PreparÃ³' == 'Preparó'
    - Strip accents / combining marks via NFKD ('ó' -> 'o', 'é' -> 'e')
    - Treat underscores as word separators ('Bellini_Music' -> 'bellini music')
    - Remove parenthetical content like (128kbit_AAC), (Radio Edit), (Original Mix)
    - Drop leading articles and 4-digit year numbers
    """
    if not s:
        return ""
    # Repair mojibake BEFORE lowercasing (lowercasing corrupts the cp1252 round-trip)
    s = repair_mojibake(s)
    s = s.lower().strip()
    # Strip parenthetical content first: (128kbit_AAC), (Radio Edit), etc.
    s = re.sub(r'\([^)]*\)', '', s)
    # NFKD decomposition separates base chars from combining marks
    s = unicodedata.normalize('NFKD', s)
    # Strip combining diacritical marks (U+0300 to U+036F range)
    s = re.sub(r'[\u0300-\u036f]', '', s)
    for article in ['the ', 'a ', 'an ']:
        if s.startswith(article):
            s = s[len(article):]
    # Underscores are word separators (common in exported filenames)
    s = s.replace('_', ' ')
    s = re.sub(r'[^\w\s]', ' ', s)
    s = re.sub(r'\b\d{4}\b', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def _sanitize_folder_path(folder_path: str) -> str:
    """Strip leading slashes and fix doubled drive letters."""
    p = folder_path.strip()
    while p and p[0] in ('/', '\\'):
        p = p[1:]
    while True:
        new_p = re.sub(r'^([A-Za-z]:[\\/])\1', r'\1', p)
        if new_p == p:
            break
        p = new_p
    p = os.path.normpath(p)
    while p and len(p) >= 3 and p[0] in ('/', '\\') and p[1].isalpha() and p[2] == ':':
        p = p[1:]
        p = os.path.normpath(p)
    return p


def _verify_and_fix_path(filepath: str) -> str:
    """If path doesn't exist, try common fixes for path doubling."""
    if os.path.exists(filepath):
        return filepath

    logger.warning("  PATH NON ESISTENTE: %s", filepath)

    # Fix 1: strip leading slashes
    fixed = filepath.lstrip('/\\')
    if os.path.exists(fixed):
        logger.info("  PATH FIX (strip slashes): %s -> %s", filepath, fixed)
        return fixed

    # Fix 2: doubled drive letter C:\C:\ -> C:\
    fixed = re.sub(r'^([A-Za-z]:[\\/])\1', r'\1', filepath)
    if os.path.exists(fixed):
        logger.info("  PATH FIX (double drive): %s -> %s", filepath, fixed)
        return fixed

    # Fix 3: strip + normpath
    fixed = os.path.normpath(filepath.lstrip('/\\'))
    if os.path.exists(fixed):
        logger.info("  PATH FIX (normpath): %s -> %s", filepath, fixed)
        return fixed

    # Fix 4: UNC prefix
    if filepath.startswith('\\\\?\\') or filepath.startswith('//?/'):
        fixed = filepath[4:]
        if os.path.exists(fixed):
            logger.info("  PATH FIX (UNC strip): %s -> %s", filepath, fixed)
            return fixed

    logger.warning("  PATH IMPOSSIBILE DA FIXARE: %s", filepath)
    return filepath


class LibraryReader:
    """Scans music folders and builds an indexed library."""

    def __init__(self, config=None):
        self.tracks: List[LibraryTrack] = []
        self._index: Dict[str, int] = {}
        self._paths: Set[str] = set()
        self._scan_count = 0
        self._error_count = 0
        self._file_counter = 0
        self._bpm_found = 0
        self._key_found = 0
        self._comment_found = 0
        self.config = config or {}

    def scan_folder(self, folder_path: str, extensions=None,
                    progress_callback=None, max_workers=4) -> List[LibraryTrack]:
        if not folder_path or not os.path.isdir(folder_path):
            logger.error("Cartella non valida: %s", folder_path)
            return []

        raw_folder = folder_path
        folder_path = _sanitize_folder_path(folder_path)
        logger.info("SCAN CARTELLA")
        logger.info("  Raw path:  '%s'", raw_folder)
        logger.info("  Clean path: '%s'", folder_path)
        logger.info("  Exists: %s", os.path.exists(folder_path))

        if extensions is None:
            extensions = self.config.get("audio_extensions", [
                ".mp3", ".flac", ".m4a", ".wav", ".aiff", ".ogg", ".wma", ".aac"
            ])

        ext_set = set(e.lower() for e in extensions)
        self.tracks = []
        self._index = {}
        self._paths = set()
        self._scan_count = 0
        self._error_count = 0
        self._file_counter = 0
        self._bpm_found = 0
        self._key_found = 0
        self._comment_found = 0

        # Collect files via os.walk.
        # Prune OS trash / system folders so files sent to the Recycle Bin (which
        # lives on the same drive, e.g. 'E:\\$RECYCLE.BIN') are never re-scanned
        # and never reappear as library entries or duplicates.
        audio_files = []
        for root, dirs, files in os.walk(folder_path):
            dirs[:] = [
                d for d in dirs
                if d.lower() not in _EXCLUDED_SCAN_DIRS
                and not d.lower().startswith('.trash')
            ]
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext in ext_set:
                    full_path = os.path.join(root, fname)
                    # VERIFY path at scan time
                    full_path = _verify_and_fix_path(full_path)
                    audio_files.append(full_path)

        total = len(audio_files)
        if total == 0:
            logger.warning("NESSUN file audio trovato in: %s", folder_path)
            return []

        logger.info("File audio trovati: %d", total)

        # Log first 5 paths collected
        for i, p in enumerate(audio_files[:5]):
            exists = os.path.exists(p)
            logger.info("  Esempio #%d: %s [esiste=%s]", i + 1, p, exists)

        # Scan with thread pool
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._scan_single_file, fp): fp for fp in audio_files}
            for future in as_completed(futures):
                self._scan_count += 1
                if progress_callback and self._scan_count % 100 == 0:
                    progress_callback(self._scan_count, total)
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception:
                    self._error_count += 1

        results.sort(key=lambda t: (t.artist.lower(), t.title.lower()))
        self.tracks = results
        for i, track in enumerate(results):
            key = track.search_key
            if key and key not in self._index:
                self._index[key] = i

        if progress_callback:
            progress_callback(total, total)

        logger.info("SCAN COMPLETATO: %d tracce", len(results))
        logger.info("  BPM trovati:    %d / %d", self._bpm_found, len(results))
        logger.info("  Key trovati:    %d / %d", self._key_found, len(results))
        logger.info("  Comment trovati: %d / %d", self._comment_found, len(results))
        logger.info("  Errori:          %d", self._error_count)

        return self.tracks

    def _scan_single_file(self, filepath: str) -> Optional[LibraryTrack]:
        try:
            return self._extract_metadata(filepath)
        except Exception as e:
            self._error_count += 1
            logger.debug("Errore lettura %s: %s", filepath, e)
            return None

    def _extract_metadata(self, filepath: str) -> Optional[LibraryTrack]:
        """Extract metadata with aggressive per-file logging."""
        self._file_counter += 1
        log_detail = self._file_counter <= 30  # Log details for first 30 files

        try:
            from mutagen import File as MutagenFile
            from mutagen.easyid3 import EasyID3
            from mutagen.mp4 import MP4
            from mutagen.flac import FLAC
        except ImportError:
            logger.warning("mutagen NON INSTALLATO! Metadati BPM/Key non disponibili.")
            return LibraryTrack(
                title=Path(filepath).stem,
                filepath=filepath,
                file_size=os.path.getsize(filepath)
            )

        ext = os.path.splitext(filepath)[1].lower()
        info = {
            'title': '', 'artist': '', 'album': '', 'genre': '',
            'bpm': '', 'key': '', 'comment': '', 'composer': '', 'year': '',
            'duration': 0.0, 'bitrate': 0
        }

        try:
            if ext == '.mp3':
                self._extract_mp3_metadata(filepath, info, log_detail)
            elif ext == '.flac':
                self._extract_flac_metadata(filepath, info, log_detail)
            elif ext in ('.m4a', '.mp4'):
                self._extract_mp4_metadata(filepath, info, log_detail)
            elif ext == '.wav':
                self._extract_wav_metadata(filepath, info, log_detail)
            elif ext in ('.aiff', '.aif'):
                self._extract_wav_metadata(filepath, info, log_detail)
            else:
                if log_detail:
                    logger.debug("  [#%d] Formato non gestito: %s", self._file_counter, ext)
        except Exception as e:
            logger.debug("  [#%d] Errore metadati: %s -> %s", self._file_counter, filepath, e)

        # Fallback: use filename if no title
        if not info['title']:
            info['title'] = Path(filepath).stem
            name = info['title']
            parts = re.split(r'\s*[-\u2013\u2014]\s*', name, maxsplit=1)
            if len(parts) == 2:
                info['artist'] = parts[0].strip()
                info['title'] = parts[1].strip()

        # Count found metadata
        if info['bpm']:
            self._bpm_found += 1
        if info['key']:
            self._key_found += 1
        if info['comment']:
            self._comment_found += 1

        # Log details for first 30 files or files with BPM/Key/Comment
        if log_detail or info['bpm'] or info['key'] or info['comment']:
            logger.info(
                "  [#%d] '%s' | title='%s' | artist='%s' | BPM='%s' | Key='%s' | Comment='%s'",
                self._file_counter, os.path.basename(filepath)[:40],
                info['title'][:40], info['artist'][:40],
                info['bpm'], info['key'],
                (info['comment'][:30] + '...') if info['comment'] and len(info['comment']) > 30 else info['comment']
            )

        return LibraryTrack(
            title=info['title'], artist=info['artist'], album=info['album'],
            genre=info['genre'], bpm=info['bpm'], key=info['key'],
            comment=info['comment'], composer=info['composer'], year=info['year'],
            duration=info['duration'], filepath=filepath,
            file_size=os.path.getsize(filepath), bitrate=info['bitrate']
        )

    # ------------------------------------------------------------------
    # MP3
    # ------------------------------------------------------------------

    def _extract_mp3_metadata(self, filepath: str, info: dict, log_detail: bool):
        """MP3: raw_id3 init SEPARATE from tag reads."""
        raw_id3 = None

        # STEP 1: Open raw ID3 (always try, never cascade-fail)
        id3_error = None
        try:
            from mutagen.id3 import ID3
            raw_id3 = ID3(filepath)
            if log_detail:
                available_frames = sorted(raw_id3.keys())
                logger.debug("  [#%d] ID3 frames: %s", self._file_counter, available_frames)
        except Exception as e:
            id3_error = str(e)
            if log_detail:
                logger.debug("  [#%d] ID3 FALLITO: %s", self._file_counter, id3_error)
            raw_id3 = None

        # STEP 2: Read basic tags (each independently)
        if raw_id3:
            info['title'] = self._read_id3_text(raw_id3, 'TIT2')
            info['artist'] = self._read_id3_text(raw_id3, 'TPE1')
            info['album'] = self._read_id3_text(raw_id3, 'TALB')
            info['genre'] = self._read_id3_text(raw_id3, 'TCON')
            info['year'] = self._read_id3_text(raw_id3, 'TDRC')
        else:
            # Fallback EasyID3
            try:
                from mutagen.easyid3 import EasyID3
                audio = EasyID3(filepath)
                info['title'] = self._get_tag(audio, 'title')
                info['artist'] = self._get_tag(audio, 'artist')
                info['album'] = self._get_tag(audio, 'album')
                info['genre'] = self._get_tag(audio, 'genre')
                info['year'] = self._get_tag(audio, 'date')
            except Exception:
                pass

        # STEP 3: Audio info
        try:
            from mutagen.mp3 import MP3
            mp3 = MP3(filepath)
            info['duration'] = mp3.info.length if mp3.info else 0
            info['bitrate'] = int(mp3.info.bitrate / 1000) if mp3.info and hasattr(mp3.info, 'bitrate') else 0
        except Exception:
            pass

        # STEP 4: BPM (always try if raw_id3 available)
        bpm = self._read_bpm_id3(raw_id3, filepath, log_detail)
        if bpm:
            info['bpm'] = bpm

        # STEP 5: Key
        info['key'] = self._read_key_id3(raw_id3)

        # STEP 6: Comment
        info['comment'] = self._read_comment_id3(raw_id3)

        # STEP 7: Composer
        info['composer'] = self._read_composer_id3(raw_id3)

    # ------------------------------------------------------------------
    # FLAC
    # ------------------------------------------------------------------

    def _extract_flac_metadata(self, filepath: str, info: dict, log_detail: bool):
        try:
            from mutagen.flac import FLAC
            audio = FLAC(filepath)
        except Exception:
            return

        info['title'] = self._get_tag(audio, 'title')
        info['artist'] = self._get_tag(audio, 'artist')
        info['album'] = self._get_tag(audio, 'album')
        info['genre'] = self._get_tag(audio, 'genre')
        info['year'] = self._get_tag(audio, 'date')
        info['duration'] = audio.info.length if audio.info else 0
        info['bitrate'] = int(audio.info.bitrate / 1000) if audio.info and hasattr(audio.info, 'bitrate') else 0

        if log_detail:
            logger.debug("  [#%d] FLAC tags: %s", self._file_counter, sorted(audio.keys()))

        if not info['bpm']:
            for tag in ['bpm', 'BPM']:
                if tag in audio:
                    try:
                        info['bpm'] = str(audio[tag][0]).strip()
                        break
                    except (IndexError, AttributeError):
                        pass

        if not info['key']:
            for tag in ['initialkey', 'INITIALKEY', 'KEY', 'key']:
                if tag in audio:
                    try:
                        info['key'] = str(audio[tag][0]).strip()
                        break
                    except (IndexError, AttributeError):
                        pass

        if not info['comment']:
            for tag in ['description', 'comment', 'COMMENT']:
                if tag in audio:
                    try:
                        info['comment'] = str(audio[tag][0]).strip()
                        break
                    except (IndexError, AttributeError):
                        pass

        if not info['composer']:
            for tag in ['composer', 'COMPOSER']:
                if tag in audio:
                    try:
                        info['composer'] = str(audio[tag][0]).strip()
                        break
                    except (IndexError, AttributeError):
                        pass

    # ------------------------------------------------------------------
    # M4A
    # ------------------------------------------------------------------

    def _extract_mp4_metadata(self, filepath: str, info: dict, log_detail: bool):
        try:
            from mutagen.mp4 import MP4
            audio = MP4(filepath)
        except Exception:
            return

        info['title'] = self._get_mp4_tag(audio, '\xa9nam')
        info['artist'] = self._get_mp4_tag(audio, '\xa9ART')
        info['album'] = self._get_mp4_tag(audio, '\xa9alb')
        info['genre'] = self._get_mp4_tag(audio, '\xa9gen')
        info['year'] = self._get_mp4_tag(audio, '\xa9day')
        info['duration'] = audio.info.length if audio.info else 0
        info['bitrate'] = int(audio.info.bitrate / 1000) if audio.info and hasattr(audio.info, 'bitrate') else 0

        if log_detail:
            logger.debug("  [#%d] M4A tags: %s", self._file_counter, sorted(str(k) for k in audio.keys()))

        if not info['bpm']:
            if 'tmpo' in audio:
                try:
                    info['bpm'] = str(audio['tmpo'][0]).strip()
                except (IndexError, AttributeError):
                    pass
            if not info['bpm']:
                for tag in ['----:com.apple.iTunes:BPM', '----:com.apple.iTunes:bpm']:
                    if tag in audio:
                        try:
                            info['bpm'] = str(audio[tag][0]).strip()
                            break
                        except (IndexError, AttributeError):
                            pass

        if not info['key']:
            for tag in ['----:com.apple.iTunes:initialkey',
                        '----:com.apple.iTunes:INITIALKEY',
                        '----:com.apple.iTunes:KEY']:
                if tag in audio:
                    try:
                        info['key'] = str(audio[tag][0]).strip()
                        break
                    except (IndexError, AttributeError):
                        pass

        if not info['comment']:
            info['comment'] = self._get_mp4_tag(audio, '\xa9cmt')

        if not info['composer']:
            info['composer'] = self._get_mp4_tag(audio, '\xa9wrt')

    # ------------------------------------------------------------------
    # Tag helpers
    # ------------------------------------------------------------------

    def _get_tag(self, audio, key: str) -> str:
        try:
            val = audio.get(key, [])
            if isinstance(val, list) and val:
                return str(val[0])
            return str(val) if val else ""
        except (KeyError, TypeError, AttributeError):
            return ""

    _get_mp4_tag = _get_tag

    def _read_id3_text(self, raw_id3, frame_id: str) -> str:
        if not raw_id3:
            return ""
        try:
            if frame_id in raw_id3:
                frame = raw_id3[frame_id]
                if frame.text:
                    return str(frame.text[0]).strip()
        except (IndexError, AttributeError, TypeError):
            pass
        return ""

    # ------------------------------------------------------------------
    # WAV / AIFF metadata extraction
    # ------------------------------------------------------------------

    def _extract_wav_metadata(self, filepath: str, info: dict, log_detail: bool):
        """Extract metadata from WAV/AIFF files.

        WAV files can store metadata via:
        1. ID3v2 tags (same as MP3 - TBPM, TKEY, TIT2, TPE1, etc.)
        2. RIFF INFO chunks (INAM=title, IART=artist, etc.)
        3. BWF bext chunk (can contain description)
        """
        raw_id3 = None

        # WAV files can have ID3 tags either:
        #   a) Starting at offset 0 (standard ID3) — read via mutagen.id3.ID3()
        #   b) After the RIFF header — accessible via mutagen.wave.WAVE().tags
        # Both produce ID3 objects with frame keys like TBPM, TIT2, TPE1, TKEY.

        wav_tags_obj = None  # Will hold the ID3 tag object from WAVE().tags

        # STEP 1: Try direct ID3 (file starts with ID3 header)
        id3_error = None
        try:
            from mutagen.id3 import ID3
            raw_id3 = ID3(filepath)
            if log_detail:
                available_frames = sorted(raw_id3.keys())
                logger.info("  [#%d] WAV direct ID3 OK, frames: %s", self._file_counter, available_frames)
        except Exception as e:
            id3_error = str(e)
            if log_detail:
                logger.info("  [#%d] WAV no direct ID3: %s", self._file_counter, id3_error)
            raw_id3 = None

        # STEP 2: If no direct ID3, try WAVE().tags (ID3 after RIFF header)
        if not raw_id3:
            try:
                from mutagen.wave import WAVE
                audio = WAVE(filepath)
                if audio.info:
                    info['duration'] = audio.info.length if hasattr(audio.info, 'length') else 0
                wav_tags_obj = audio.tags if hasattr(audio, 'tags') and audio.tags else None
                if wav_tags_obj:
                    tag_keys = sorted(wav_tags_obj.keys())
                    if log_detail:
                        logger.info("  [#%d] WAV WAVE().tags keys: %s", self._file_counter, tag_keys)
                    # Log raw values for each important tag
                    if log_detail:
                        for tk in tag_keys:
                            try:
                                frame = wav_tags_obj[tk]
                                raw_val = getattr(frame, 'text', None)
                                if raw_val:
                                    logger.info("  [#%d]   TAG '%s' raw text: %s", self._file_counter, tk, [str(t) for t in raw_val[:3]])
                                else:
                                    # GEOB or other binary tags
                                    data_val = getattr(frame, 'data', None)
                                    logger.info("  [#%d]   TAG '%s' type=%s data_len=%s", self._file_counter, tk, type(frame).__name__, len(data_val) if data_val else 'N/A')
                            except Exception as te:
                                logger.info("  [#%d]   TAG '%s' err: %s", self._file_counter, tk, te)
            except Exception as e:
                if log_detail:
                    logger.info("  [#%d] WAV WAVE() error: %s", self._file_counter, e)

        # Choose the ID3 source: direct ID3 or WAVE().tags
        id3_source = raw_id3 or wav_tags_obj
        if id3_source:
            source_name = 'direct ID3' if raw_id3 else 'WAVE().tags'
            if log_detail:
                logger.info("  [#%d] WAV reading tags from: %s (has %d keys)", self._file_counter, source_name, len(id3_source))

            # Read all ID3 tags from whichever source we have
            info['title'] = self._read_id3_text(id3_source, 'TIT2')
            info['artist'] = self._read_id3_text(id3_source, 'TPE1')
            info['album'] = self._read_id3_text(id3_source, 'TALB')
            info['genre'] = self._read_id3_text(id3_source, 'TCON')
            info['year'] = self._read_id3_text(id3_source, 'TDRC')
            info['bpm'] = self._read_bpm_id3(id3_source, filepath, log_detail)
            info['key'] = self._read_key_id3(id3_source)
            info['comment'] = self._read_comment_id3(id3_source)
            info['composer'] = self._read_composer_id3(id3_source)

            if log_detail:
                logger.info(
                    "  [#%d] WAV ID3 result: title='%s' artist='%s' bpm='%s' key='%s'",
                    self._file_counter, info['title'][:40], info['artist'][:40],
                    info['bpm'], info['key']
                )
        else:
            if log_detail:
                logger.info("  [#%d] WAV NO ID3 tags found anywhere, falling back to filename", self._file_counter)

        # STEP 3: Try RIFF INFO chunks as additional fallback
        if not info['title'] or not info['artist']:
            try:
                from mutagen.wave import WAVE
                audio = WAVE(filepath)
                if not wav_tags_obj:
                    # Only if we didn't already open it above
                    if audio.info:
                        info['duration'] = audio.info.length if hasattr(audio.info, 'length') else 0
                # Read RIFF INFO tags (different from ID3 frames)
                riff_tags = audio.tags if hasattr(audio, 'tags') and audio.tags else {}
                if riff_tags and not wav_tags_obj:
                    if log_detail:
                        logger.info("  [#%d] WAV RIFF-only tags: %s", self._file_counter, sorted(riff_tags.keys()))
                    if not info['title']:
                        for key in ['title', 'INAM', 'IPRD', 'TIT2']:
                            if key in riff_tags:
                                try:
                                    val = riff_tags[key]
                                    if hasattr(val, 'text') and val.text:
                                        info['title'] = str(val.text[0]).strip()
                                    else:
                                        info['title'] = str(val).strip()
                                except Exception:
                                    pass
                                if info['title']:
                                    break
                    if not info['artist']:
                        for key in ['artist', 'IART', 'TPE1']:
                            if key in riff_tags:
                                try:
                                    val = riff_tags[key]
                                    if hasattr(val, 'text') and val.text:
                                        info['artist'] = str(val.text[0]).strip()
                                    else:
                                        info['artist'] = str(val).strip()
                                except Exception:
                                    pass
                                if info['artist']:
                                    break
                    if not info['bpm']:
                        for key in ['IBPM', 'TBPM']:
                            if key in riff_tags:
                                try:
                                    val = riff_tags[key]
                                    if hasattr(val, 'text') and val.text:
                                        raw_bpm = str(val.text[0]).strip()
                                    else:
                                        raw_bpm = str(val).strip()
                                    if raw_bpm:
                                        info['bpm'] = str(int(float(raw_bpm)))
                                except Exception:
                                    pass
                                if info['bpm']:
                                    break
            except Exception as e:
                if log_detail:
                    logger.info("  [#%d] WAV RIFF fallback: %s", self._file_counter, e)

        if log_detail:
            logger.info(
                "  [#%d] WAV FINAL: title='%s' artist='%s' bpm='%s' key='%s' comment='%s'",
                self._file_counter, info['title'][:50], info['artist'][:50],
                info['bpm'], info['key'], (info['comment'][:30] + '...') if info['comment'] and len(info['comment']) > 30 else (info['comment'] or '-')
            )

    # ------------------------------------------------------------------
    # BPM
    # ------------------------------------------------------------------

    def _read_bpm_id3(self, raw_id3, filepath: str = "", log_detail: bool = False) -> str:
        if not raw_id3:
            if log_detail:
                logger.info("  [#%d] BPM: id3_source=None, skip", self._file_counter)
            return ""

        # 1. TBPM
        try:
            if 'TBPM' in raw_id3:
                frame = raw_id3['TBPM']
                if log_detail:
                    logger.info("  [#%d] BPM TBPM frame: type=%s text=%s", self._file_counter, type(frame).__name__, getattr(frame, 'text', 'NO_TEXT_ATTR'))
                if frame.text:
                    raw_val = str(frame.text[0]).strip()
                    if raw_val:
                        try:
                            bpm = str(int(float(raw_val)))
                            if log_detail:
                                logger.info("  [#%d] BPM found via TBPM: '%s' -> %s", self._file_counter, raw_val, bpm)
                            return bpm
                        except ValueError:
                            if log_detail:
                                logger.info("  [#%d] BPM TBPM non-numeric: '%s'", self._file_counter, raw_val)
                            return raw_val
                else:
                    if log_detail:
                        logger.info("  [#%d] BPM TBPM frame has NO .text attribute", self._file_counter)
        except Exception as e:
            if log_detail:
                logger.info("  [#%d] BPM TBPM error: %s", self._file_counter, e)

        # 2. TXXX frames
        try:
            for frame in raw_id3.values():
                desc = getattr(frame, 'desc', '')
                if not desc:
                    continue
                desc_lower = str(desc).lower()
                if desc_lower not in ('bpm', 'tbpm', '@bpm', 'tempo'):
                    continue
                try:
                    text = str(frame.text[0]).strip() if frame.text else ''
                    if text:
                        try:
                            bpm = str(int(float(text)))
                        except ValueError:
                            bpm = text
                        if log_detail:
                            logger.info("  [#%d] BPM found via TXXX(%s): %s", self._file_counter, desc_lower, bpm)
                        return bpm
                except (IndexError, AttributeError, TypeError):
                    continue
        except Exception:
            pass

        # 3. Try EasyID3 as last resort
        try:
            from mutagen.easyid3 import EasyID3
            if filepath:
                audio = EasyID3(filepath)
                bpm = self._get_tag(audio, 'bpm')
                if bpm:
                    if log_detail:
                        logger.info("  [#%d] BPM found via EasyID3: %s", self._file_counter, bpm)
                    return bpm
        except Exception:
            pass

        if log_detail:
            logger.info("  [#%d] BPM NOT FOUND in any tag", self._file_counter)
        return ""

    # ------------------------------------------------------------------
    # Key
    # ------------------------------------------------------------------

    def _read_key_id3(self, raw_id3) -> str:
        if not raw_id3:
            return ""
        try:
            if 'TKEY' in raw_id3:
                frame = raw_id3['TKEY']
                if frame.text:
                    val = str(frame.text[0]).strip()
                    if val:
                        logger.info("  [#%d] Key found: '%s'", self._file_counter, val)
                        return val
        except Exception as e:
            logger.info("  [#%d] Key TKEY error: %s", self._file_counter, e)
        try:
            for frame in raw_id3.values():
                desc = getattr(frame, 'desc', '')
                if not desc:
                    continue
                desc_lower = str(desc).lower()
                if desc_lower in ('key', 'initial key', 'initialkey', 'tkey'):
                    try:
                        text = str(frame.text[0]).strip() if frame.text else ''
                        if text:
                            return text
                    except (IndexError, AttributeError, TypeError):
                        continue
        except Exception:
            pass
        return ""

    # ------------------------------------------------------------------
    # Comment
    # ------------------------------------------------------------------

    def _read_comment_id3(self, raw_id3) -> str:
        if not raw_id3:
            return ""
        try:
            if 'COMM' in raw_id3:
                frame = raw_id3['COMM']
                if frame.text:
                    text_parts = [str(t).strip() for t in frame.text if t]
                    if text_parts:
                        val = ' '.join(text_parts)
                        if len(val) > 5:
                            logger.info("  [#%d] Comment found: '%s...'", self._file_counter, val[:50])
                        return val
        except Exception:
            pass
        try:
            for frame in raw_id3.values():
                desc = getattr(frame, 'desc', '')
                if not desc:
                    continue
                desc_lower = str(desc).lower()
                if desc_lower in ('comment', 'comments', 'description'):
                    try:
                        text = str(frame.text[0]).strip() if frame.text else ''
                        if text:
                            return text
                    except (IndexError, AttributeError, TypeError):
                        continue
        except Exception:
            pass
        return ""

    # ------------------------------------------------------------------
    # Composer
    # ------------------------------------------------------------------

    def _read_composer_id3(self, raw_id3) -> str:
        """Read composer from TCOM ID3 frame."""
        if not raw_id3:
            return ""
        try:
            if 'TCOM' in raw_id3:
                frame = raw_id3['TCOM']
                if frame.text:
                    # TCOM can have multiple values (list of composers)
                    text_parts = [str(t).strip() for t in frame.text if t]
                    if text_parts:
                        return ' / '.join(text_parts)
        except Exception:
            pass
        return ""

    # ------------------------------------------------------------------
    # Lock tag writing
    # ------------------------------------------------------------------

    LOCK_TAG = "[lock]"

    @staticmethod
    def set_composer_lock(filepath: str, lock: bool = True) -> tuple:
        """Add or remove [lock] tag from the composer field of an audio file.

        Returns (success: bool, message: str).
        Safe: preserves existing composer content, only adds/removes [lock].
        """
        tag = LibraryReader.LOCK_TAG
        ext = os.path.splitext(filepath)[1].lower()

        try:
            if ext == '.mp3':
                return LibraryReader._set_lock_mp3(filepath, lock, tag)
            elif ext == '.flac':
                return LibraryReader._set_lock_flac(filepath, lock, tag)
            elif ext in ('.m4a', '.mp4'):
                return LibraryReader._set_lock_mp4(filepath, lock, tag)
            elif ext in ('.wav', '.aiff', '.aif'):
                return LibraryReader._set_lock_wav(filepath, lock, tag)
            else:
                return (False, f"Formato non supportato per lock: {ext}")
        except Exception as e:
            logger.error("Errore scrittura lock su %s: %s", filepath, e)
            return (False, f"Errore: {e}")

    @staticmethod
    def _set_lock_mp3(filepath: str, lock: bool, tag: str) -> tuple:
        """Write [lock] to MP3 TCOM frame via mutagen ID3."""
        from mutagen.id3 import ID3, TCOM
        from mutagen.mp3 import MP3

        audio = MP3(filepath)
        if audio.tags is None:
            audio.add_tags()

        # Read current composer(s)
        current = ""
        if 'TCOM' in audio.tags:
            try:
                frame = audio.tags['TCOM']
                parts = [str(t).strip() for t in (frame.text or []) if t]
                current = ' / '.join(parts)
            except Exception:
                pass

        if lock:
            if tag.lower() not in current.lower():
                new_val = f"{current} {tag}".strip() if current else tag
            else:
                return (True, "Lock gia presente nel composer")
        else:
            # Remove [lock] (case-insensitive)
            import re as _re
            new_val = _re.sub(r'\[lock\]', '', current, flags=_re.IGNORECASE).strip()
            new_val = _re.sub(r'\s{2,}', ' ', new_val).strip()
            if not new_val:
                new_val = ""

        if new_val:
            audio.tags['TCOM'] = TCOM(encoding=3, text=new_val.split(' / '))
        elif 'TCOM' in audio.tags:
            del audio.tags['TCOM']

        audio.save()
        return (True, f"Composer aggiornato: '{new_val}'" if new_val else "Lock rimosso dal composer")

    @staticmethod
    def _set_lock_flac(filepath: str, lock: bool, tag: str) -> tuple:
        """Write [lock] to FLAC composer Vorbis comment."""
        from mutagen.flac import FLAC
        import re as _re

        audio = FLAC(filepath)
        current = ""
        if 'composer' in audio:
            try:
                current = str(audio['composer'][0]).strip()
            except (IndexError, AttributeError):
                pass

        if lock:
            if tag.lower() not in current.lower():
                new_val = f"{current} {tag}".strip() if current else tag
            else:
                return (True, "Lock gia presente nel composer")
        else:
            new_val = _re.sub(r'\[lock\]', '', current, flags=_re.IGNORECASE).strip()
            new_val = _re.sub(r'\s{2,}', ' ', new_val).strip()
            if not new_val:
                new_val = ""

        if new_val:
            audio['composer'] = [new_val]  # Vorbis comment requires list
        elif 'composer' in audio:
            del audio['composer']

        audio.save()
        return (True, f"Composer aggiornato: '{new_val}'" if new_val else "Lock rimosso dal composer")

    @staticmethod
    def _set_lock_mp4(filepath: str, lock: bool, tag: str) -> tuple:
        """Write [lock] to M4A ©wrt (composer) atom."""
        from mutagen.mp4 import MP4
        import re as _re

        audio = MP4(filepath)
        current = ""
        if '\xa9wrt' in audio:
            try:
                current = str(audio['\xa9wrt'][0]).strip()
            except (IndexError, AttributeError):
                pass

        if lock:
            if tag.lower() not in current.lower():
                new_val = f"{current} {tag}".strip() if current else tag
            else:
                return (True, "Lock gia presente nel composer")
        else:
            new_val = _re.sub(r'\[lock\]', '', current, flags=_re.IGNORECASE).strip()
            new_val = _re.sub(r'\s{2,}', ' ', new_val).strip()
            if not new_val:
                new_val = ""

        if new_val:
            audio['\xa9wrt'] = [new_val]
        elif '\xa9wrt' in audio:
            del audio['\xa9wrt']

        audio.save()
        return (True, f"Composer aggiornato: '{new_val}'" if new_val else "Lock rimosso dal composer")

    @staticmethod
    def _set_lock_wav(filepath: str, lock: bool, tag: str) -> tuple:
        """Write [lock] to WAV TCOM ID3 frame."""
        from mutagen.id3 import ID3, TCOM
        from mutagen.wave import WAVE
        import re as _re

        audio = WAVE(filepath)

        # Try to get ID3 tags
        id3_tags = None
        if hasattr(audio, 'tags') and audio.tags:
            id3_tags = audio.tags
        else:
            # Try direct ID3
            try:
                id3_tags = ID3(filepath)
            except Exception:
                id3_tags = None

        if id3_tags is None:
            if not lock:
                return (True, "Nessun tag ID3 trovato, nessun lock da rimuovere")
            # Create ID3 tags for the WAV file
            id3_tags = ID3()

        # Read current composer
        current = ""
        if 'TCOM' in id3_tags:
            try:
                frame = id3_tags['TCOM']
                parts = [str(t).strip() for t in (frame.text or []) if t]
                current = ' / '.join(parts)
            except Exception:
                pass

        if lock:
            if tag.lower() not in current.lower():
                new_val = f"{current} {tag}".strip() if current else tag
            else:
                return (True, "Lock gia presente nel composer")
        else:
            new_val = _re.sub(r'\[lock\]', '', current, flags=_re.IGNORECASE).strip()
            new_val = _re.sub(r'\s{2,}', ' ', new_val).strip()
            if not new_val:
                new_val = ""

        if new_val:
            id3_tags['TCOM'] = TCOM(encoding=3, text=new_val.split(' / '))
        elif 'TCOM' in id3_tags:
            del id3_tags['TCOM']

        # Save via WAVE object if it has tags, otherwise save ID3 directly
        if hasattr(audio, 'tags') and audio.tags is id3_tags:
            audio.tags = id3_tags
            audio.save()
        else:
            id3_tags.save(filepath)

        return (True, f"Composer aggiornato: '{new_val}'" if new_val else "Lock rimosso dal composer")

    # ------------------------------------------------------------------
    # Metadata writing (title / artist / album)
    # ------------------------------------------------------------------

    _ID3_FRAME_MAP = {"title": "TIT2", "artist": "TPE1", "album": "TALB", "genre": "TCON"}
    _MP4_TAG_MAP = {"title": "\xa9nam", "artist": "\xa9ART", "album": "\xa9alb", "genre": "\xa9gen"}

    @staticmethod
    def set_tags(filepath: str, title=None, artist=None, album=None, genre=None) -> tuple:
        """Overwrite the title/artist/album/genre tags of an audio file.

        Only the fields passed as non-``None`` are written (an empty string is a
        valid value and will blank the tag). Returns ``(success, message)``.

        The audio stream itself is never touched — mutagen only rewrites the tag
        block — so this is the same safe mechanism used by the composer-lock.
        """
        fields = {
            k: v for k, v in (("title", title), ("artist", artist),
                              ("album", album), ("genre", genre))
            if v is not None
        }
        if not fields:
            return (True, "Nessuna modifica")

        ext = os.path.splitext(filepath)[1].lower()
        try:
            if ext == '.mp3':
                return LibraryReader._set_tags_mp3(filepath, fields)
            elif ext == '.flac':
                return LibraryReader._set_tags_flac(filepath, fields)
            elif ext in ('.m4a', '.mp4'):
                return LibraryReader._set_tags_mp4(filepath, fields)
            elif ext in ('.wav', '.aiff', '.aif'):
                return LibraryReader._set_tags_wav(filepath, fields)
            else:
                return (False, f"Formato non supportato: {ext}")
        except Exception as e:
            logger.error("Errore scrittura tag su %s: %s", filepath, e)
            return (False, f"Errore: {e}")

    @staticmethod
    def _set_tags_mp3(filepath: str, fields: dict) -> tuple:
        from mutagen.id3 import TIT2, TPE1, TALB, TCON
        from mutagen.mp3 import MP3

        audio = MP3(filepath)
        if audio.tags is None:
            audio.add_tags()
        frame_cls = {"title": TIT2, "artist": TPE1, "album": TALB, "genre": TCON}
        for f, val in fields.items():
            audio.tags[LibraryReader._ID3_FRAME_MAP[f]] = frame_cls[f](encoding=3, text=[val])
        audio.save()
        return (True, "Tag aggiornati")

    @staticmethod
    def _set_tags_flac(filepath: str, fields: dict) -> tuple:
        from mutagen.flac import FLAC

        audio = FLAC(filepath)
        for f, val in fields.items():
            audio[f] = [val]
        audio.save()
        return (True, "Tag aggiornati")

    @staticmethod
    def _set_tags_mp4(filepath: str, fields: dict) -> tuple:
        from mutagen.mp4 import MP4

        audio = MP4(filepath)
        for f, val in fields.items():
            audio[LibraryReader._MP4_TAG_MAP[f]] = [val]
        audio.save()
        return (True, "Tag aggiornati")

    @staticmethod
    def _set_tags_wav(filepath: str, fields: dict) -> tuple:
        from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCON

        ext = os.path.splitext(filepath)[1].lower()
        audio = None
        try:
            if ext == '.wav':
                from mutagen.wave import WAVE
                audio = WAVE(filepath)
            else:
                from mutagen.aiff import AIFF
                audio = AIFF(filepath)
        except Exception:
            audio = None

        id3_tags = None
        if audio is not None and getattr(audio, 'tags', None):
            id3_tags = audio.tags
        else:
            try:
                id3_tags = ID3(filepath)
            except Exception:
                id3_tags = ID3()

        frame_cls = {"title": TIT2, "artist": TPE1, "album": TALB, "genre": TCON}
        for f, val in fields.items():
            id3_tags[LibraryReader._ID3_FRAME_MAP[f]] = frame_cls[f](encoding=3, text=[val])

        if audio is not None and getattr(audio, 'tags', None) is not None:
            audio.tags = id3_tags
            audio.save()
        else:
            id3_tags.save(filepath)
        return (True, "Tag aggiornati")

    # ------------------------------------------------------------------
    # Serato hotcues ("Serato Markers2" tag) — count only
    # ------------------------------------------------------------------

    @staticmethod
    def count_hotcues(filepath: str):
        """Return how many Serato hotcues (CUE markers) are saved for a track.

        Reads the "Serato Markers2" tag embedded in the audio file (GEOB for
        ID3/MP3/WAV/AIFF, VORBIS_COMMENT for FLAC/OGG, freeform atom for MP4/M4A)
        and counts its ``CUE`` entries. Returns an ``int`` (0 when none are set),
        or ``None`` when the count cannot be determined for that file/format.
        """
        ext = os.path.splitext(filepath)[1].lower()
        try:
            if ext in ('.mp3', '.wav', '.wave', '.aif', '.aiff', '.aifc'):
                return LibraryReader._hotcues_id3(filepath)
            if ext == '.flac':
                return LibraryReader._hotcues_vorbis(filepath, 'flac')
            if ext in ('.ogg', '.oga', '.opus'):
                return LibraryReader._hotcues_vorbis(filepath, 'ogg')
            if ext in ('.m4a', '.mp4', '.aac', '.alac', '.m4b'):
                return LibraryReader._hotcues_mp4(filepath)
        except Exception:
            return None
        return None

    @staticmethod
    def _b64decode_loose(data) -> bytes:
        import base64
        if isinstance(data, str):
            data = data.encode('ascii', 'ignore')
        data = data.replace(b'\n', b'').replace(b'\r', b'')
        pad = b'=' * (-len(data) % 4)
        return base64.b64decode(data + pad)

    @staticmethod
    def _markers2_payload(geob_data: bytes):
        """Decode a raw "Serato Markers2" object (version + base64 + padding)."""
        import base64
        if not geob_data or geob_data[:2] != b'\x01\x01':
            return None
        try:
            end = geob_data.index(b'\x00', 2)
        except ValueError:
            end = len(geob_data)
        b64 = geob_data[2:end].replace(b'\n', b'').replace(b'\r', b'')
        pad = b'A==' if len(b64) % 4 == 1 else b'=' * (-len(b64) % 4)
        try:
            return base64.b64decode(b64 + pad)
        except Exception:
            return None

    @staticmethod
    def _count_cue_entries(payload: bytes) -> int:
        """Count CUE entries in a decoded Markers2 payload (starts 0x01 0x01)."""
        if not payload or payload[:2] != b'\x01\x01':
            return 0
        body = payload[2:]
        i, n, count = 0, len(body), 0
        while i < n:
            j = body.find(b'\x00', i)
            if j == -1:
                break
            name = body[i:j]
            i = j + 1
            if not name:  # trailing null terminator
                break
            if i + 4 > n:
                break
            length = int.from_bytes(body[i:i + 4], 'big')
            i += 4
            if length < 0 or i + length > n:
                break
            if name == b'CUE':
                count += 1
            i += length
        return count

    @staticmethod
    def _count_from_envelope(env: bytes) -> int:
        """Count CUEs from a FLAC/MP4 envelope (contains a nested Markers2 blob)."""
        marker = b'Serato Markers2\x00'
        idx = env.find(marker)
        inner = env[idx + len(marker):] if idx != -1 else env
        payload = LibraryReader._markers2_payload(inner)
        return LibraryReader._count_cue_entries(payload) if payload else 0

    @staticmethod
    def _hotcues_id3(filepath: str):
        from mutagen.id3 import ID3, ID3NoHeaderError
        try:
            tags = ID3(filepath)
        except ID3NoHeaderError:
            return 0
        for geob in tags.getall('GEOB'):
            if getattr(geob, 'desc', '') == 'Serato Markers2':
                payload = LibraryReader._markers2_payload(bytes(geob.data))
                if payload is not None:
                    return LibraryReader._count_cue_entries(payload)
        return 0

    @staticmethod
    def _hotcues_vorbis(filepath: str, kind: str):
        if kind == 'flac':
            from mutagen.flac import FLAC
            audio = FLAC(filepath)
        else:
            from mutagen.oggvorbis import OggVorbis
            audio = OggVorbis(filepath)
        vals = None
        for key in ('SERATO_MARKERS_V2', 'serato_markers_v2', 'Serato Markers2'):
            if audio.get(key):
                vals = audio.get(key)
                break
        if not vals:
            return 0
        env = LibraryReader._b64decode_loose(vals[0])
        return LibraryReader._count_from_envelope(env)

    @staticmethod
    def _hotcues_mp4(filepath: str):
        from mutagen.mp4 import MP4
        audio = MP4(filepath)
        tags = audio.tags or {}
        vals = tags.get('----:com.serato.dj:markersv2')
        if not vals:
            return 0
        env = LibraryReader._b64decode_loose(bytes(vals[0]))
        return LibraryReader._count_from_envelope(env)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str, limit=10) -> List[LibraryTrack]:
        normalized = normalize_string(query)
        results = []
        for track in self.tracks:
            if normalized in track.search_key:
                results.append(track)
                if len(results) >= limit:
                    break
        return results

    def get_stats(self) -> dict:
        return {
            'total_tracks': len(self.tracks),
            'total_size_mb': sum(t.file_size for t in self.tracks) / (1024 * 1024),
            'scan_errors': self._error_count,
            'formats': self._count_formats(),
            'has_bpm': self._bpm_found,
            'has_key': self._key_found,
            'has_comment': self._comment_found,
        }

    def _count_formats(self) -> dict:
        counts = {}
        for t in self.tracks:
            ext = os.path.splitext(t.filepath)[1].lower()
            counts[ext] = counts.get(ext, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))
