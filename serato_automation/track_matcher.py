# Serato Playlist Automation
# Track matcher module - v5.1 (controlled malus when title + artist confirmed)
#
# v5.1:
#   - NEW: When the requested title is fully found AND at least one requested
#     artist token is present, "controlled malus" applies instead of harsh −20%
#     per extra word:
#       * featuring / album suffix / artist-segment extras → −3% each
#       * low-relevance descriptors (remix, official, 128kbit_aac, …) → −1% each
#       * words that extend the song title AFTER the requested title (wrong song)
#         still use −20% each (protects e.g. "Everything" vs "Everything she wants")
#     Floors: ≥75% when title confirmed; ≥85% when artist also confirmed, unless
#     strict title-extension penalties fired.
#   - NEW: When the title is found but NO requested artist token matches, strict
#     −20% per wrong-artist token (richest single source) and per extra title word;
#     floor ≥25% (replaces the old 70% base cap).
# v5.0:
#   - NEW: "accounting" scoring model for fully-title-matched candidates.
#     When every requested title word is found (in order) in the Song Serato or
#     Filename, the score starts at 100 and subtracts explicit penalties:
#       * artist present in the request but absent from every found column → cap 70%
#       * extra real word in the found TITLE  → -20% each
#       * extra real word in the found ARTIST → -5% total
#       * low-relevance descriptor outside parentheses (remix/official/video…) → -5%
#       * anything inside parentheses (descriptor or unrequested word) → -1%
#       * requested title word matched only via the Filename → -1%
#     Partially-matched titles keep the strict legacy gates (0% / 44% / 50%).
#   - NEW: mojibake repair in normalize_string ('PreparÃ³' == 'Preparó') and
#     underscores treated as word separators ('Bellini_Music' → 'bellini music').
#
# v4.6:
#   - NEW: MatchResult.is_effectively_matched property = (is_matched AND score > 0)
#     UI uses this to treat 0%-score rows (pipeline-rejected) as 'missing':
#     no filename, no player, no lock button, not counted as duplicate.
# v4.5:
#   - FIX: All candidates sorted by score descending — selected_index=0 is always highest
# v4.4:
#   - FIX: _check_composer_lock() now uses pre-indexed list (O(M) instead of O(N))
#     where M = number of composer-locked tracks (typically < 100)
#   - This fixes catastrophic O(N*M) performance on large libraries
# v4.3:
#   - NEW: Composer lock — tracks with [lock] in composer field match at 100%
#   - _check_composer_lock() runs BEFORE _check_title_lock() (highest priority)
#   - Title containment: requested title must be contained in locked track's title
# v4.2:
#   - FIX: NameError "name 't' is not defined" in _filepath_index dict comprehension
# v4.1:
#   - NEW: Title lock support — user-confirmed matches always return 100%
#   - _check_title_lock() runs before the 6-pass cascade
#   - Accepts title_locks dict and builds filepath index at init
# v4.0:
#   - COMPLETE REFACTORING: cleaner structure, extracted pipeline,
#     better naming, eliminated duplication, modular post-rules
#   - NEW RULE: Strict ordered title validation — requested title words
#     must appear IN ORDER in Filename or Song Serato. Violations:
#       * No words found       → 0%
#       * Partial / wrong order → max 44%
#   - Remix cap (70%) applied to ALL scores including 100% exact matches
#   - Extra words cap uses normalize_string (no false positives from filenames)
#   - Found column count reflects only visible candidates (>= FOUNDDROP_MIN_SCORE)
#
# Scoring pipeline (applied to every pass result):
#   If the requested title is fully found (all words, in order, in Song/Filename):
#       → accounting model: 100 - penalties (see _score_accounting)
#         When ≥1 requested artist token is also present, controlled malus applies
#         (−3% featuring/album extras, −1% low-relevance words; −20% only for
#         title extensions after the requested title). Floors: 75% / 85%.
#   Otherwise (partial title match):
#       1. Word penalty (missing query words → cap 50%)
#       2. Title presence (title words missing from any field → cap 45%)
#       3. Title ordered validation (title words not in order → 0% or 44%)
#       4. Post-rules (containment bonus, PSYTRANCE, BPM)
#
# Matching passes (in priority order):
#   Pass 1: Exact match (normalize both sides)
#   Pass 2: Word coverage (all query words found in library)
#   Pass 3: Composite (weighted artist + title)
#   Pass 4: Fuzzy (token_sort_ratio, token_set_ratio)
#   Pass 5: Title partial (partial_ratio on title only)
#   Pass 6: Filename match

import re
import logging
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum

from .playlist_parser import PlaylistTrack
from .library_reader import LibraryTrack, normalize_string, repair_mojibake

logger = logging.getLogger("serato.matcher")

# rapidfuzz is imported once at module load (previously re-imported inside hot
# loops, once per library track). Falls back to a pure-Python implementation.
try:
    from rapidfuzz import fuzz, process
    _HAS_RAPIDFUZZ = True
except ImportError:  # pragma: no cover - exercised only without rapidfuzz
    fuzz = None
    process = None
    _HAS_RAPIDFUZZ = False

# ===================================================================
# Constants
# ===================================================================

MIN_CANDIDATE_SCORE = 40
MAX_CANDIDATES = 10
# Controlled malus (title fully found + ≥1 requested artist token present)
_CONTROLLED_EXTRA_WORD_PENALTY = 3
_CONTROLLED_LOW_RELEVANCE_PENALTY = 1
_STRICT_EXTRA_TITLE_PENALTY = 20
_ACCOUNTING_FLOOR_TITLE = 75
_ACCOUNTING_FLOOR_TITLE_ARTIST = 85
# Title found but requested artist completely absent (wrong track/version)
_ACCOUNTING_FLOOR_WRONG_ARTIST = 25
DEFAULT_THRESHOLDS = {
    "exact": 100,
    "token_sort": 85,
    "token_set": 75,
    "partial": 60,
}

_PSYTRANCE_PATTERN = re.compile(r"\bpsy\b", re.IGNORECASE)

# Matches a parenthesised segment, e.g. "(Original Mix)" — used to detect words
# that live inside parentheses (treated as even lower relevance).
_PAREN_RE = re.compile(r"\(([^)]*)\)")

# "Low relevance" descriptor words: when one of these appears in the FOUND track
# but not in the request, it must NOT cap the score to 70% (as a real extra word
# would). Instead it costs a small, capped penalty:
#   - at most -5% total when present outside parentheses
#   - at most -1% total when present only inside parentheses
# The list is intentionally normalised (lowercase, no punctuation) so multi-word
# phrases from the user's list (e.g. "OFFICIAL MUSIC VIDEO", "CLUB MIX") are
# covered token by token.
_LOW_RELEVANCE_WORDS = frozenset({
    # remix / version family (treated as low relevance per product decision)
    "remix", "mashup", "dub", "vip", "flip", "bootleg", "rework",
    "reworked", "reedit", "discomix", "mashboot", "remake", "revibe",
    "reloaded",
    # version / format descriptors
    "original", "extended", "edit", "mix", "version", "radio", "club",
    "clean", "dirty",
    # media descriptors (English + Spanish/Italian variants)
    "official", "oficial", "ufficiale", "music", "video", "audio",
    "spanish", "english", "french", "italian", "german",
    "mv", "clip", "lyric", "lyrics", "visualizer",
    # bitrate / encoding tokens (usually parenthetical)
    "aac", "kbps", "kbit", "128kbit_aac", "152kbit", "320kbps",
})

# Common stop words excluded from "meaningful words" analysis
_STOP_WORDS = frozenset({
    "the", "a", "an", "of", "in", "on", "at", "to", "for", "and",
    "or", "by", "is", "it", "my", "me", "we", "de", "la", "le",
    "il", "lo", "un", "una", "del", "della", "di", "ed", "ft",
    "feat", "vs", "remix", "edit", "mix", "original", "version",
    "radio", "club", "extended", "instrumental", "acoustic",
})


# ===================================================================
# Data structures
# ===================================================================

class MatchConfidence(Enum):
    EXACT = "exact"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


@dataclass
class CandidateMatch:
    library_track: LibraryTrack
    score: int = 0
    confidence: MatchConfidence = MatchConfidence.NONE


@dataclass
class MatchResult:
    """Multi-candidate match result for a single playlist track."""

    playlist_track: PlaylistTrack
    candidates: List[CandidateMatch] = field(default_factory=list)
    selected_index: int = 0

    # -- Convenience properties (operate on the *selected* candidate) --

    @property
    def library_track(self) -> Optional[LibraryTrack]:
        if self.candidates and 0 <= self.selected_index < len(self.candidates):
            return self.candidates[self.selected_index].library_track
        return None

    @property
    def score(self) -> int:
        if self.candidates and 0 <= self.selected_index < len(self.candidates):
            return self.candidates[self.selected_index].score
        return 0

    @property
    def confidence(self) -> MatchConfidence:
        if self.candidates and 0 <= self.selected_index < len(self.candidates):
            return self.candidates[self.selected_index].confidence
        return MatchConfidence.NONE

    @property
    def is_matched(self) -> bool:
        return len(self.candidates) > 0

    @property
    def is_effectively_matched(self) -> bool:
        """A row is considered 'effectively matched' (and shown with full UI:
        filename, player, etc.) when there is at least one candidate AND the
        selected candidate's score is greater than 0.

        A row with score=0 means the matching pipeline rejected the candidate
        (e.g. title-ordered validation failed) — the row should be treated as
        'missing' for display purposes: no filename, no player, no duplicates.
        """
        return self.is_matched and self.score > 0

    @property
    def num_candidates(self) -> int:
        return len(self.candidates)

    @property
    def display_confidence(self) -> str:
        return {
            MatchConfidence.EXACT: "#27ae60",
            MatchConfidence.HIGH: "#2ecc71",
            MatchConfidence.MEDIUM: "#f39c12",
            MatchConfidence.LOW: "#e74c3c",
            MatchConfidence.NONE: "#95a5a6",
        }.get(self.confidence, "#95a5a6")

    @property
    def display_label(self) -> str:
        return {
            MatchConfidence.EXACT: "Esatto",
            MatchConfidence.HIGH: "Alta",
            MatchConfidence.MEDIUM: "Media",
            MatchConfidence.LOW: "Bassa",
            MatchConfidence.NONE: "-",
        }.get(self.confidence, "-")

    def __str__(self) -> str:
        if self.is_matched and self.library_track:
            return f"[{self.score}%] {self.playlist_track.display_name} -> {self.library_track.display_name}"
        return f"[MANCA] {self.playlist_track.display_name}"


# ===================================================================
# Word-level utilities
# ===================================================================

def extract_words(text: str, min_len: int = 2) -> List[str]:
    """Extract lowercase words from *text*, stripping accents and punctuation."""
    if not text:
        return []
    text = unicodedata.normalize("NFKD", text.lower())
    text = re.sub(r"[\u0300-\u036f]", "", text)
    cleaned = re.sub(r"[^\w\s]", " ", text)
    return [w for w in cleaned.split() if len(w) >= min_len]


def extract_meaningful_words(text: str) -> List[str]:
    """Like extract_words but filters out common stop words."""
    return [w for w in extract_words(text, min_len=2) if w not in _STOP_WORDS]


def _relevance_tokens(text: str) -> List[str]:
    """Tokenise *text* for extra/low-relevance word analysis.

    Mirrors ``normalize_string`` (repair mojibake, lowercase, strip accents,
    split underscores, drop 4-digit years) BUT keeps parenthesised content, so
    the caller can distinguish words inside parentheses from words outside.
    Returns tokens with length >= 2.
    """
    if not text:
        return []
    # Repair mojibake before lowercasing (same reason as normalize_string)
    text = repair_mojibake(text)
    text = unicodedata.normalize("NFKD", text.lower())
    text = re.sub(r"[\u0300-\u036f]", "", text)
    text = text.replace("_", " ")
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\b\d{4}\b", " ", text)
    return [w for w in text.split() if len(w) >= 2]


def _split_paren_tokens(text: str) -> Tuple[set, set]:
    """Split *text* tokens into (outside_parentheses, inside_parentheses) sets.

    Words inside parentheses are considered even lower relevance than the same
    word outside, so callers penalise them more gently.
    """
    if not text:
        return set(), set()
    outside = set(_relevance_tokens(_PAREN_RE.sub(" ", text)))
    paren: set = set()
    for seg in _PAREN_RE.findall(text):
        paren.update(_relevance_tokens(seg))
    return outside, paren


def _outside_tokens_ordered(text: str) -> List[str]:
    """Tokenise *text* outside parentheses, preserving order."""
    if not text:
        return []
    return _relevance_tokens(_PAREN_RE.sub(" ", text))


def _split_song_title_segments(title: str) -> Tuple[str, str, str]:
    """Split a Serato ``Artist - Title | Album`` field into three parts."""
    if not title:
        return "", "", ""
    if "|" in title:
        main, pipe_suffix = title.split("|", 1)
    else:
        main, pipe_suffix = title, ""
    if " - " in main:
        artist_seg, title_seg = main.split(" - ", 1)
    else:
        artist_seg, title_seg = "", main
    return artist_seg.strip(), title_seg.strip(), pipe_suffix.strip()


def _similar_token(a: str, b: str) -> bool:
    """True when two tokens are near-identical.

    Used only to recognise a **mojibake-corrupted** token as the same word as a
    clean one — e.g. ``prepara3`` (from ``PreparÃ3``) vs ``preparo``. The test is
    intentionally forgiving of a couple of corrupted trailing characters:

    * identical → yes;
    * a long shared prefix (≥ 4 chars, within 2 chars of the shorter token) → yes;
    * otherwise a high fuzzy ratio (≥ 80) when rapidfuzz is available.
    """
    if a == b:
        return True
    if len(a) < 3 or len(b) < 3:
        return False
    common = 0
    for ca, cb in zip(a, b):
        if ca != cb:
            break
        common += 1
    if common >= 4 and common >= min(len(a), len(b)) - 2:
        return True
    if _HAS_RAPIDFUZZ:
        try:
            return fuzz.ratio(a, b) >= 80
        except Exception:
            return False
    return False


def word_matches_pool(word: str, pool: set, min_len: int = 3) -> bool:
    """Check if *word* matches any entry in *pool* (exact or prefix)."""
    if word in pool:
        return True
    if len(word) >= min_len:
        for pw in pool:
            if len(pw) >= min_len and (pw.startswith(word) or word.startswith(pw)):
                return True
    return False


def ordered_subsequence_length(needle: List[str], haystack: List[str]) -> int:
    """Count how many *needle* words appear **in order** inside *haystack*.

    This is a standard sub-sequence check: each needle word must be found
    before the next one, but gaps between matches are allowed.
    """
    if not needle or not haystack:
        return 0
    ni = 0
    matched = 0
    for hw in haystack:
        if ni < len(needle) and needle[ni] == hw:
            matched += 1
            ni += 1
    return matched


# ===================================================================
# Word-level colour analysis (for UI highlighting)
# ===================================================================

def compute_word_colors(
    requested_text: str, library_track: Optional[LibraryTrack]
) -> List[Tuple[str, str]]:
    """Return (token, colour_hex) pairs for per-word highlighting.

    GREEN  — word found (exact)
    RED    — word not found anywhere
    YELLOW — partial / prefix match
    DEFAULT — punctuation, whitespace, or no library track

    Uses dual normalisation to handle dotted acronyms (D.A.N.C.E.)
    and apostrophes (D'Agostino) correctly.
    """
    GREEN = "#27ae60"
    RED = "#e74c3c"
    YELLOW = "#f39c12"
    DEFAULT = "#2c3e50"

    if not library_track or not requested_text:
        return [(requested_text or "", DEFAULT)]

    # Build word pool from library track (dual normalisation)
    pool_parts = [library_track.artist, library_track.title, library_track.filename_stem]
    pool_words: set = set()

    # Strategy 1: normalize_string (same as matching pipeline)
    for part in pool_parts:
        if part:
            normed = normalize_string(part)
            if normed:
                pool_words.update(normed.split())

    # Strategy 2: gentle normalisation (dots/apostrophes removed, words kept joined)
    for part in pool_parts:
        if not part:
            continue
        gentle = part.lower()
        gentle = re.sub(r"\([^)]*\)", "", gentle)
        gentle = unicodedata.normalize("NFKD", gentle)
        gentle = re.sub(r"[\u0300-\u036f]", "", gentle)
        gentle = re.sub(r"[^\w\s]", "", gentle)
        for w in gentle.split():
            if len(w) >= 2:
                pool_words.add(w)

    result: List[Tuple[str, str]] = []
    for token in re.split(r"(\s+)", requested_text):
        if not token.strip():
            result.append((token, DEFAULT))
            continue

        # Normalise token with both strategies
        norm_split = normalize_string(token).split()
        meaningful_norm = [w for w in norm_split if len(w) >= 2]

        gentle = token.lower()
        gentle = unicodedata.normalize("NFKD", gentle)
        gentle = re.sub(r"[\u0300-\u036f]", "", gentle)
        gentle = re.sub(r"[^\w\s]", "", gentle)
        gentle_parts = [w for w in gentle.split() if len(w) >= 2]
        if len(gentle) >= 2 and gentle not in gentle_parts:
            gentle_parts.append(gentle)

        all_sub = list(set(meaningful_norm + gentle_parts))
        if not all_sub:
            result.append((token, DEFAULT))
            continue

        found = sum(1 for sw in all_sub if sw in pool_words)
        partial = sum(
            1
            for sw in all_sub
            if sw not in pool_words
            and any(len(pw) >= 3 and (pw.startswith(sw) or sw.startswith(pw)) for pw in pool_words)
        )
        total = len(all_sub)

        if found == total:
            result.append((token, GREEN))
        elif found > 0 or partial > 0:
            result.append((token, YELLOW))
        else:
            result.append((token, RED))

    return result


# ===================================================================
# Track Matcher — core scoring engine
# ===================================================================

class TrackMatcher:
    """Matches playlist tracks against a scanned music library.

    The scoring pipeline for each candidate is:
        raw_score → word_penalty → title_presence → title_ordered → post_rules
    """

    ARTIST_WEIGHT = 0.3
    TITLE_WEIGHT = 0.7
    WORD_PENALTY_CAP = 50

    def __init__(self, library: List[LibraryTrack], thresholds: dict = None,
                 title_locks: dict = None, bpm_penalty_enabled: bool = False,
                 bpm_reference: int = 0):
        self.library = library
        self.thresholds = dict(DEFAULT_THRESHOLDS)
        if thresholds:
            self.thresholds.update(thresholds)

        # Title locks: {"normalized_title": "filepath"} → always 100%
        self._title_locks = title_locks or {}
        self._filepath_index = {track.filepath: track for track in library}

        # BPM penalty settings
        self._bpm_penalty_enabled = bpm_penalty_enabled
        self._bpm_reference = int(bpm_reference) if bpm_reference else 0

        # Pre-index composer-locked tracks (BUG-001 fix: avoid O(N) per query)
        self._composer_locked_tracks = [t for t in library if t.is_composer_locked]

        # Pre-compute per-library-track search keys (done once at init)
        self._lib_keys = [t.search_key for t in library]
        # O(1) exact-match lookup (BUG-002 fix: was an O(N) linear scan per query).
        # First occurrence wins so behaviour matches the previous linear scan.
        self._lib_key_to_idx = {}
        for idx, key in enumerate(self._lib_keys):
            if key and key not in self._lib_key_to_idx:
                self._lib_key_to_idx[key] = idx
        self._lib_entries = [
            (normalize_string(t.artist), normalize_string(t.title), t)
            for t in library
        ]
        # Reuse the already-computed search_key instead of normalising twice.
        self._lib_word_sets = [
            set(key.split()) if key else set()
            for key in self._lib_keys
        ]
        self._lib_filename_keys = [t.filename_search_key for t in library]

        logger.info("TrackMatcher initialised: %d library tracks, %d title locks, %d composer locks, bpm_penalty=%s ref=%d",
                     len(library), len(self._title_locks), len(self._composer_locked_tracks),
                     bpm_penalty_enabled, self._bpm_reference)

    # ---------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------

    def match_playlist(
        self, tracks: List[PlaylistTrack], progress_callback=None
    ) -> List[MatchResult]:
        """Match an entire playlist. Returns one MatchResult per track."""
        results: List[MatchResult] = []
        for i, track in enumerate(tracks):
            result = self._match_with_candidates(track)
            results.append(result)

            best = result.candidates[0] if result.candidates else None
            logger.info(
                "MATCH #%d: query='%s' -> %s (%d%%) [candidates=%d]",
                i + 1,
                track.display_name,
                best.library_track.display_name if best else "MANCANTE",
                best.score if best else 0,
                len(result.candidates),
            )
            if progress_callback:
                progress_callback(i + 1, len(tracks))
        return results

    def set_thresholds(self, thresholds: dict):
        self.thresholds.update(thresholds)

    # ---------------------------------------------------------------
    # Single-track matching (returns multi-candidate result)
    # ---------------------------------------------------------------

    def _match_with_candidates(self, playlist_track: PlaylistTrack) -> MatchResult:
        """Find best + alternative candidates for one playlist track."""
        best_track, best_score, best_conf = self._find_best_match(playlist_track)

        if best_track is None:
            return MatchResult(playlist_track=playlist_track, candidates=[])

        candidates = [CandidateMatch(best_track, best_score, best_conf)]
        alternatives = self._find_alternatives(playlist_track, best_track, best_score)
        candidates.extend(alternatives)

        # Sort ALL candidates by score descending so index 0 is always highest
        candidates.sort(key=lambda c: c.score, reverse=True)

        return MatchResult(
            playlist_track=playlist_track,
            candidates=candidates,
            selected_index=0,
        )

    # ---------------------------------------------------------------
    # Best match finder (6-pass cascade)
    # ---------------------------------------------------------------

    def _find_best_match(
        self, playlist_track: PlaylistTrack
    ) -> Tuple[Optional[LibraryTrack], int, MatchConfidence]:
        """Run the 6-pass cascade and return the best (track, score, confidence)."""
        if not playlist_track.artist and not playlist_track.title:
            return (None, 0, MatchConfidence.NONE)

        # -- Composer lock check (highest priority: [lock] in audio metadata) --
        composer_result = self._check_composer_lock(playlist_track)
        if composer_result:
            logger.info("    COMPOSER LOCK: '%s' -> locked track", playlist_track.title[:40])
            return composer_result

        # -- Title lock check (JSON-based, second priority) --
        lock_result = self._check_title_lock(playlist_track)
        if lock_result:
            logger.info("    TITLE LOCK: '%s' -> locked track", playlist_track.title[:40])
            return lock_result

        query_full = f"{playlist_track.artist} {playlist_track.title}".strip()
        query_words = extract_meaningful_words(query_full)
        query_key = normalize_string(query_full)

        logger.debug(
            "  Query: '%s' | artist='%s' | title='%s' | words=%s",
            query_full, playlist_track.artist, playlist_track.title, query_words,
        )

        # PASS 1 — Exact normalised match
        result = self._pass_exact(query_key)
        if result:
            track, score = result
            score = self._apply_full_pipeline(score, query_words, playlist_track, track)
            return (track, score, self._confidence(score))

        # PASS 2 — Word coverage (all query words found)
        if query_words:
            result = self._pass_word_coverage(query_words, query_key)
            if result:
                track, score = result
                score = self._apply_full_pipeline(score, query_words, playlist_track, track)
                return (track, score, self._confidence(score))

        # PASS 3 — Composite (weighted artist + title)
        has_artist = bool(playlist_track.artist and len(playlist_track.artist.strip()) > 1)
        has_title = bool(playlist_track.title)
        if has_artist and has_title:
            result = self._pass_composite(
                normalize_string(playlist_track.artist),
                normalize_string(playlist_track.title),
            )
            if result:
                track, score = result
                score = self._apply_full_pipeline(score, query_words, playlist_track, track)
                return (track, score, self._confidence(score))

        # PASS 4 — Fuzzy (token_sort, token_set)
        for scorer_name in ("token_sort_ratio", "token_set_ratio"):
            result = self._pass_fuzzy(
                query_key, scorer_name, self.thresholds.get(scorer_name.replace("_ratio", ""), 75)
            )
            if result:
                track, score = result
                score = self._apply_full_pipeline(score, query_words, playlist_track, track)
                return (track, score, self._confidence(score))

        # PASS 5 — Title partial
        if has_title:
            result = self._pass_fuzzy(
                normalize_string(playlist_track.title),
                "partial_ratio",
                self.thresholds["partial"],
            )
            if result:
                track, score = result
                score = self._apply_full_pipeline(score, query_words, playlist_track, track)
                return (track, score, self._confidence(score))

        # PASS 6 — Filename match
        result = self._pass_filename(playlist_track.artist, playlist_track.title)
        if result:
            track, score = result
            score = self._apply_full_pipeline(score, query_words, playlist_track, track)
            return (track, score, self._confidence(score))

        return (None, 0, MatchConfidence.NONE)

    # ---------------------------------------------------------------
    # Title lock check (before cascade)
    # ---------------------------------------------------------------

    def _check_title_lock(
        self, playlist_track: PlaylistTrack
    ) -> Optional[Tuple[LibraryTrack, int, MatchConfidence]]:
        """If the requested title matches a user-confirmed lock, return at 100%."""
        if not self._title_locks or not playlist_track.title:
            return None

        title_norm = normalize_string(playlist_track.title)
        if not title_norm:
            return None

        for lock_key, lock_path in self._title_locks.items():
            if not lock_key or not lock_path:
                continue
            # Match if lock key is contained in title or vice versa
            if lock_key in title_norm or title_norm in lock_key:
                track = self._filepath_index.get(lock_path)
                if track:
                    return (track, 100, MatchConfidence.EXACT)

        return None

    # ---------------------------------------------------------------
    # Composer lock check (audio metadata: [lock] in composer field)
    # ---------------------------------------------------------------

    def _check_composer_lock(
        self, playlist_track: PlaylistTrack
    ) -> Optional[Tuple[LibraryTrack, int, MatchConfidence]]:
        """If any library track has [lock] in composer AND the requested title
        is contained in the track's title, return at 100%.

        This is the most solid lock mechanism because the [lock] tag lives
        inside the audio file metadata and survives across sessions/computers.
        """
        if not playlist_track.title:
            return None

        title_norm = normalize_string(playlist_track.title)
        if not title_norm:
            return None

        # Check only pre-indexed composer-locked tracks (O(M) instead of O(N))
        for track in self._composer_locked_tracks:
            if not track.is_composer_locked:
                continue

            # The requested title must be contained in the found track's title
            track_title_norm = normalize_string(track.title or "")
            if not track_title_norm:
                continue

            # Title containment check (bidirectional)
            if title_norm in track_title_norm or track_title_norm in title_norm:
                logger.info(
                    "    COMPOSER LOCK MATCH: '%s' -> '%s' (composer=[lock])",
                    playlist_track.title[:40], track.title[:40],
                )
                return (track, 100, MatchConfidence.EXACT)

        return None

    # ---------------------------------------------------------------
    # Scoring passes — each returns (LibraryTrack, raw_score) or None
    # ---------------------------------------------------------------

    def _pass_exact(self, query_key: str) -> Optional[Tuple[LibraryTrack, int]]:
        idx = self._lib_key_to_idx.get(query_key)
        if idx is not None:
            return (self.library[idx], 100)
        return None

    def _pass_word_coverage(
        self, query_words: List[str], query_key: str
    ) -> Optional[Tuple[LibraryTrack, int]]:
        best_track: Optional[LibraryTrack] = None
        best_score = 0
        n_query = len(query_words)

        for idx, (lib_artist, lib_title, track) in enumerate(self._lib_entries):
            if not lib_artist and not lib_title:
                continue
            word_set = self._lib_word_sets[idx]
            if not word_set:
                continue

            found = sum(1 for w in query_words if word_matches_pool(w, word_set))
            coverage = found / n_query

            if coverage >= 1.0:
                sim = 0
                set_sim = 0
                if _HAS_RAPIDFUZZ:
                    try:
                        sim = fuzz.token_sort_ratio(query_key, self._lib_keys[idx])
                        set_sim = fuzz.token_set_ratio(query_key, self._lib_keys[idx])
                    except Exception:
                        pass

                density_bonus = min(n_query, 5)
                sim_bonus = max(0, (max(sim, set_sim) - 70) // 5)
                score = min(85 + density_bonus + sim_bonus, 95)

                logger.debug(
                    "    WordCov: q='%s' lib='%s' cov=100%% sim=%d score=%d",
                    query_key, self._lib_keys[idx], sim, score,
                )
                if score > best_score:
                    best_score = score
                    best_track = track

            elif coverage >= 0.8 and best_score < 75:
                score = int(70 + (coverage - 0.8) * 70)
                if score > best_score:
                    best_score = score
                    best_track = track

            elif coverage >= 0.5 and best_score < 45:
                score = int(35 + coverage * 15)
                if score > best_score:
                    best_score = score
                    best_track = track

        return (best_track, best_score) if best_track and best_score >= 45 else None

    def _pass_composite(
        self, query_artist: str, query_title: str
    ) -> Optional[Tuple[LibraryTrack, int]]:
        best_track: Optional[LibraryTrack] = None
        best_score = 0

        for lib_artist, lib_title, track in self._lib_entries:
            if not lib_artist and not lib_title:
                continue

            artist_score = (
                self._similarity(query_artist, lib_artist, "token_sort_ratio")
                if lib_artist and query_artist
                else 0
            )
            title_score = (
                self._similarity(query_title, lib_title, "token_sort_ratio")
                if lib_title and query_title
                else 0
            )

            # Cross-match when library artist/title is empty or placeholder
            if (not lib_artist or len(lib_artist) < 3) and lib_title and query_artist:
                cross = self._similarity(query_artist, lib_title, "partial_ratio")
                artist_score = max(artist_score, int(cross * 0.8))

            if (not lib_title or len(lib_title) < 3) and lib_artist and query_title:
                cross = self._similarity(query_title, lib_artist, "partial_ratio")
                title_score = max(title_score, int(cross * 0.8))

            if artist_score < 30 and title_score < 40:
                continue

            combined = int(artist_score * self.ARTIST_WEIGHT + title_score * self.TITLE_WEIGHT)
            if combined > best_score:
                best_score = combined
                best_track = track

        return (best_track, best_score) if best_track and best_score >= 40 else None

    def _pass_fuzzy(
        self, query: str, scorer_name: str, min_score: int
    ) -> Optional[Tuple[LibraryTrack, int]]:
        if _HAS_RAPIDFUZZ:
            try:
                scorer = getattr(fuzz, scorer_name, fuzz.token_sort_ratio)
                results = process.extract(query, self._lib_keys, scorer=scorer, limit=3)
                for _key, score, idx in results:
                    if score >= min_score:
                        return (self.library[idx], score)
            except Exception:
                pass
            return None

        # Pure-Python fallback (rapidfuzz not installed)
        for idx, lib_key in enumerate(self._lib_keys):
            score = self._manual_similarity(query, lib_key, scorer_name)
            if score >= min_score:
                return (self.library[idx], score)
        return None

    def _pass_filename(
        self, artist: str, title: str
    ) -> Optional[Tuple[LibraryTrack, int]]:
        parts = [p for p in [artist, title] if p]
        if not parts:
            return None
        return self._pass_fuzzy(normalize_string(" ".join(parts)), "token_sort_ratio", 50)

    # ---------------------------------------------------------------
    # Full scoring pipeline (applied after every pass)
    # ---------------------------------------------------------------

    def _apply_full_pipeline(
        self, raw_score: int, query_words: List[str],
        playlist_track: PlaylistTrack, lib_track: LibraryTrack,
    ) -> int:
        """Turn a raw pass score into the final score.

        There are two regimes:

        * **Title fully found** — every word of the requested title appears, in
          order, in the found Song Serato OR Filename. This is a trustworthy
          match, so the score is computed with the *accounting model*
          (:meth:`_score_accounting`): start at 100 and subtract well-defined
          penalties for the extra artist, extra title words, low-relevance
          descriptors and encoding quirks.

        * **Title only partially found** — the stricter legacy gates apply
          (word penalty → title presence → ordered validation → post-rules),
          which cap the score aggressively (0%, 44% or 50%).
        """
        if self._title_fully_matched(playlist_track.title, lib_track):
            return self._score_accounting(playlist_track, lib_track)

        score = self._apply_word_penalty(raw_score, query_words, lib_track)
        score = self._validate_title_presence(playlist_track.title, score, lib_track)
        score = self._validate_title_ordered(playlist_track.title, score, lib_track)
        score = self._apply_post_rules(score, playlist_track, lib_track)
        return score

    # ---------------------------------------------------------------
    # Accounting scoring model (used when the title is fully matched)
    # ---------------------------------------------------------------

    def _title_fully_matched(self, title: str, lib_track: LibraryTrack) -> bool:
        """True when every requested title word appears, in order, in the found
        Filename or Song Serato (parentheses ignored, accents/mojibake folded).
        """
        if not title or not lib_track:
            return False
        title_words = [w for w in normalize_string(title).split() if len(w) >= 2]
        if not title_words:
            return False
        for field_val in (lib_track.filename_stem, lib_track.title):
            fn = normalize_string(field_val or "")
            if fn and ordered_subsequence_length(title_words, fn.split()) == len(title_words):
                return True
        return False

    def _score_accounting(
        self, playlist_track: PlaylistTrack, lib_track: LibraryTrack
    ) -> int:
        """Score a fully-title-matched candidate as ``100 - penalties``.

        **Strict mode** (requested artist absent from every field): −20% per wrong
        artist token (Artist tag / ``Artist - Title`` segments) and per extra title
        word. Base 100 (no 70% cap). Floor **25%** when the title was still found.

        **Controlled mode** (title fully found + ≥1 requested artist token): soft
        penalties for featuring/album suffix/low-relevance descriptors; −20% only
        for words that extend the song title *after* the requested title sequence
        (different song, e.g. "Everything she wants").
        """
        req_artist = playlist_track.artist or ""
        req_title = playlist_track.title or ""
        req_all = set(_relevance_tokens(f"{req_artist} {req_title}"))

        a_out, a_par = _split_paren_tokens(lib_track.artist or "")
        t_out, t_par = _split_paren_tokens(lib_track.title or "")
        f_out, f_par = _split_paren_tokens(lib_track.filename_stem or "")
        filename_tokens = f_out | f_par
        found_all = a_out | a_par | t_out | t_par | filename_tokens

        def _is_extra(w: str) -> bool:
            return (
                w not in _STOP_WORDS
                and w not in _LOW_RELEVANCE_WORDS
                and w not in req_all
            )

        raw_title = lib_track.title or ""
        title_suspicious = ("Ã" in raw_title or "Â" in raw_title)
        req_title_words = {
            w for w in _relevance_tokens(req_title) if w not in _STOP_WORDS
        }
        req_title_ordered = _outside_tokens_ordered(req_title)
        req_confirmed_in_filename = {
            r for r in req_title_words if word_matches_pool(r, filename_tokens)
        }

        def _recovered_by_filename(w: str) -> bool:
            return title_suspicious and any(
                _similar_token(w, r) for r in req_confirmed_in_filename
            )

        req_artist_tokens = {
            w for w in _relevance_tokens(req_artist) if w not in _STOP_WORDS
        }
        artist_matched = bool(
            req_artist_tokens
            and any(word_matches_pool(w, found_all) for w in req_artist_tokens)
        )
        artist_absent = bool(req_artist_tokens and not artist_matched)
        controlled_mode = artist_matched

        base = 100
        penalties = 0
        strict_title_extension = False

        if controlled_mode:
            artist_seg, title_seg, pipe_suffix = _split_song_title_segments(raw_title)

            # Featuring / wrong-field artist tokens before " - " → soft −3% each
            soft_extras: set = set()
            for w in _relevance_tokens(artist_seg):
                if _is_extra(w) and not _recovered_by_filename(w):
                    soft_extras.add(w)

            # Album / suffix after "|" → soft −3% each
            for w in _relevance_tokens(pipe_suffix):
                if _is_extra(w) and not _recovered_by_filename(w):
                    soft_extras.add(w)

            # Words after the requested title subsequence → strict −20% (wrong song)
            title_out_ordered = _outside_tokens_ordered(title_seg)
            if req_title_ordered and title_out_ordered:
                ni = 0
                subseq_end = 0
                for idx, hw in enumerate(title_out_ordered):
                    if ni < len(req_title_ordered) and hw == req_title_ordered[ni]:
                        ni += 1
                        subseq_end = idx + 1
                if ni == len(req_title_ordered):
                    for w in title_out_ordered[subseq_end:]:
                        if _is_extra(w) and not _recovered_by_filename(w):
                            penalties += _STRICT_EXTRA_TITLE_PENALTY
                            strict_title_extension = True

            penalties += _CONTROLLED_EXTRA_WORD_PENALTY * len(soft_extras)

            # Low-relevance descriptors anywhere → −1% each (remix, official, …)
            low_rel_tokens: set = set()
            for w in a_out | t_out | a_par | t_par | f_out | f_par:
                if w in _LOW_RELEVANCE_WORDS and w not in req_all:
                    low_rel_tokens.add(w)
            penalties += _CONTROLLED_LOW_RELEVANCE_PENALTY * len(low_rel_tokens)

            if not artist_absent and any(_is_extra(w) for w in a_out):
                penalties += 5

        else:
            # Strict: wrong artist(s) + extra title words → −20% each
            extra_title = {
                w for w in t_out if _is_extra(w) and not _recovered_by_filename(w)
            }
            penalties += _STRICT_EXTRA_TITLE_PENALTY * len(extra_title)

            # Wrong artist tokens — count from the richest single source (Artist tag,
            # Song ``Artist - Title`` prefix, or filename prefix) without double-count
            # the same string twice (e.g. tag and filename both listing the same names).
            title_artist_seg, _, _ = _split_song_title_segments(raw_title)
            fn_artist_seg, _, _ = _split_song_title_segments(
                lib_track.filename_stem or ""
            )
            wrong_artist_count = 0
            for part in (lib_track.artist or "", title_artist_seg, fn_artist_seg):
                if not part:
                    continue
                count = sum(
                    1
                    for w in _relevance_tokens(part)
                    if _is_extra(w) and not _recovered_by_filename(w)
                )
                wrong_artist_count = max(wrong_artist_count, count)
            penalties += _STRICT_EXTRA_TITLE_PENALTY * wrong_artist_count

            low_outside = any(
                w in _LOW_RELEVANCE_WORDS and w not in req_all
                for w in (a_out | t_out)
            )
            if low_outside:
                penalties += 5

            paren_hit = any(
                (w in _LOW_RELEVANCE_WORDS) or _is_extra(w)
                for w in (a_par | t_par | f_par)
            )
            if paren_hit:
                penalties += 1

        # Title word matched only via the filename (not Song/Artist) → −1%
        song_artist = a_out | a_par | t_out | t_par
        filename_only = False
        for w in req_title_words:
            if word_matches_pool(w, song_artist):
                continue
            if not word_matches_pool(w, filename_tokens):
                continue
            if title_suspicious and any(_similar_token(tok, w) for tok in t_out):
                continue
            filename_only = True
            break
        if filename_only:
            penalties += 1

        score = max(0, base - penalties)
        score = self._rule_bpm_penalty(score, lib_track)

        if artist_absent:
            score = max(score, _ACCOUNTING_FLOOR_WRONG_ARTIST)
        elif controlled_mode and not strict_title_extension:
            score = max(score, _ACCOUNTING_FLOOR_TITLE)
            if artist_matched:
                score = max(score, _ACCOUNTING_FLOOR_TITLE_ARTIST)

        logger.debug(
            "    Accounting: base=%d controlled=%s artist_matched=%s "
            "strict_ext=%s penalties=%d -> %d",
            base, controlled_mode, artist_matched, strict_title_extension,
            penalties, score,
        )
        return score

    # ---------------------------------------------------------------
    # Pipeline stage 1: Word penalty
    # ---------------------------------------------------------------

    def _apply_word_penalty(
        self, score: int, query_words: List[str], lib_track: LibraryTrack
    ) -> int:
        """If any meaningful query word is missing from the library track, cap at 50%."""
        if not query_words or not lib_track:
            return score

        pool_parts = [
            normalize_string(lib_track.artist),
            normalize_string(lib_track.title),
        ]
        pool_words: set = set()
        for part in pool_parts:
            if part:
                pool_words.update(part.split())
        if not pool_words:
            return score

        missing = [w for w in query_words if not word_matches_pool(w, pool_words)]
        if missing:
            logger.debug("    Word penalty: missing=%s", missing)
            return min(score, self.WORD_PENALTY_CAP)

        return max(score, 60)

    # ---------------------------------------------------------------
    # Pipeline stage 2: Title presence (any field, any order)
    # ---------------------------------------------------------------

    def _validate_title_presence(
        self, title: str, score: int, lib_track: LibraryTrack
    ) -> int:
        """If title words are missing from any library field, cap at 45%."""
        if not title or score < 50:
            return score

        title_words = extract_meaningful_words(title)
        if not title_words:
            return score

        pool_parts = [
            normalize_string(lib_track.artist),
            normalize_string(lib_track.title),
            normalize_string(lib_track.filename_stem),
        ]
        pool: set = set()
        for part in pool_parts:
            if part:
                pool.update(part.split())
        if not pool:
            return score

        missing = [w for w in title_words if not word_matches_pool(w, pool)]
        if missing:
            logger.debug(
                "    Title presence FAILED: title='%s' missing=%s -> cap 45%%",
                title[:40], missing,
            )
            return min(score, 45)

        return score

    # ---------------------------------------------------------------
    # Pipeline stage 3: Title ordered match in Filename / Song Serato
    # ---------------------------------------------------------------

    def _validate_title_ordered(
        self, title: str, score: int, lib_track: LibraryTrack
    ) -> int:
        """Strict ordered validation of the requested title against Filename and Song Serato.

        ALL words from the requested title must appear **in exact order** as a
        subsequence in at least ONE of:
          - the normalised Filename (``filename_stem``)
          - the normalised Song Serato (``title`` metadata field)

        Penalties:
          - No title words found at all  → 0%
          - Partial / wrong order       → max 44%
          - Full ordered match          → no change

        This is the final quality gate that prevents false positives where
        the artist name matches but the song title is completely different.
        """
        if not title or not lib_track or score < 30:
            return score

        # Normalise the requested title and extract words (>= 2 chars)
        title_norm = normalize_string(title)
        title_words = [w for w in title_norm.split() if len(w) >= 2]
        if not title_words:
            return score

        # Build the fields to check (normalised)
        fields: List[str] = []
        if lib_track.filename_stem:
            fn_norm = normalize_string(lib_track.filename_stem)
            if fn_norm:
                fields.append(fn_norm)
        if lib_track.title:
            song_norm = normalize_string(lib_track.title)
            if song_norm:
                fields.append(song_norm)

        if not fields:
            return score

        # Find the best ordered sub-sequence ratio across all fields
        best_ratio = 0.0
        for field_text in fields:
            field_words = field_text.split()
            match_len = ordered_subsequence_length(title_words, field_words)
            ratio = match_len / len(title_words)
            best_ratio = max(best_ratio, ratio)

        # Apply penalties
        if best_ratio == 0:
            logger.debug(
                "    Title ordered: NO words found in Filename/Song -> 0%% (title='%s')",
                title[:40],
            )
            return 0

        if best_ratio < 1.0:
            logger.debug(
                "    Title ordered: partial %.0f%% -> cap 44%% (title='%s')",
                best_ratio * 100,
                title[:40],
            )
            return min(score, 44)

        return score

    # ---------------------------------------------------------------
    # Pipeline stage 4: Post-rules
    # ---------------------------------------------------------------

    def _apply_post_rules(
        self, score: int, playlist_track: PlaylistTrack, lib_track: LibraryTrack
    ) -> int:
        """Apply post-matching adjustments for *partially* matched titles.

        (Fully-title-matched candidates are scored by :meth:`_score_accounting`
        and never reach this method.)

        Rule B — Title containment bonus: requested title fully inside found → ≥ 62%
        Rule C — PSYTRANCE genre adjustment: many extra words → 60-65%
        Rule D — BPM penalty (optional, disabled by default)
        """
        if not lib_track or score < 40:
            return score

        req_title_norm = normalize_string(playlist_track.title or "")
        found_title_norm = normalize_string(lib_track.title or "")

        # Rule B: Title containment bonus
        score = self._rule_containment_bonus(score, req_title_norm, found_title_norm)

        # Rule C: PSYTRANCE genre adjustment
        score = self._rule_psytrance_adjustment(
            score, lib_track.genre, req_title_norm, found_title_norm
        )

        # Rule D: BPM penalty (optional, disabled by default)
        score = self._rule_bpm_penalty(score, lib_track)

        return score

    def _rule_containment_bonus(
        self, score: int, req_title_norm: str, found_title_norm: str
    ) -> int:
        """If the requested title is fully contained in the found title, raise to ≥ 62%."""
        if req_title_norm and found_title_norm and req_title_norm in found_title_norm:
            if score < 60:
                return 62
        return score

    def _rule_psytrance_adjustment(
        self, score: int, genre: Optional[str],
        req_title_norm: str, found_title_norm: str,
    ) -> int:
        """PSYTRANCE tracks with many extra words get capped at 60-65%."""
        genre_upper = (genre or "").upper()
        if "PSYTRANCE" not in genre_upper and "PSY" not in genre_upper:
            return score
        if not (req_title_norm and found_title_norm and req_title_norm in found_title_norm):
            return score

        req_words = set(req_title_norm.split())
        found_words = set(found_title_norm.split())
        if len(found_words - req_words) > 3:
            return max(60, min(score, 65))
        return score

    def _rule_bpm_penalty(self, score: int, lib_track: LibraryTrack) -> int:
        """Subtract 1% per BPM difference from the reference BPM (capped at -30).

        Only active when bpm_penalty_enabled=True and bpm_reference > 0.
        Tracks with no BPM metadata are not penalised.
        """
        if not self._bpm_penalty_enabled or self._bpm_reference <= 0 or not lib_track:
            return score
        try:
            lib_bpm = float(lib_track.bpm) if lib_track.bpm else 0.0
            if lib_bpm <= 0:
                return score
            diff = abs(lib_bpm - self._bpm_reference)
            penalty = min(int(diff), 30)
            if penalty > 0:
                logger.debug(
                    "    BPM penalty: lib_bpm=%.0f ref=%d diff=%.0f penalty=%d",
                    lib_bpm, self._bpm_reference, diff, penalty,
                )
            return max(0, score - penalty)
        except (ValueError, TypeError):
            return score

    # ---------------------------------------------------------------
    # Alternative matches finder
    # ---------------------------------------------------------------

    def _find_alternatives(
        self,
        playlist_track: PlaylistTrack,
        best_track: LibraryTrack,
        best_score: int,
    ) -> List[CandidateMatch]:
        """Find alternative candidates beyond the best match."""
        query_full = f"{playlist_track.artist} {playlist_track.title}".strip()
        query_key = normalize_string(query_full)
        query_words = extract_meaningful_words(query_full)

        alternatives: List[CandidateMatch] = []
        seen_paths = {best_track.filepath}

        if _HAS_RAPIDFUZZ:

            for scorer_name in ("token_sort_ratio", "token_set_ratio", "partial_ratio"):
                scorer = getattr(fuzz, scorer_name, fuzz.token_sort_ratio)
                min_score = 45 if scorer_name == "partial_ratio" else 50

                try:
                    results = process.extract(
                        query_key, self._lib_keys, scorer=scorer,
                        limit=MAX_CANDIDATES + 5,
                    )
                except Exception:
                    continue

                for _key, raw_score, idx in results:
                    track = self.library[idx]
                    if track.filepath in seen_paths or raw_score < min_score:
                        continue

                    score = self._apply_full_pipeline(
                        raw_score, query_words, playlist_track, track
                    )

                    if score >= MIN_CANDIDATE_SCORE:
                        alternatives.append(CandidateMatch(
                            library_track=track, score=score,
                            confidence=self._confidence(score),
                        ))
                        seen_paths.add(track.filepath)
                        if len(alternatives) >= MAX_CANDIDATES:
                            break

                if len(alternatives) >= MAX_CANDIDATES:
                    break

        else:
            # Fallback: manual scoring (rapidfuzz not installed)
            for idx, lib_key in enumerate(self._lib_keys):
                track = self.library[idx]
                if track.filepath in seen_paths:
                    continue
                score = self._manual_similarity(query_key, lib_key, "token_sort_ratio")
                if score < MIN_CANDIDATE_SCORE:
                    continue
                score = self._apply_full_pipeline(score, query_words, playlist_track, track)
                if score >= MIN_CANDIDATE_SCORE:
                    alternatives.append(CandidateMatch(
                        library_track=track, score=score,
                        confidence=self._confidence(score),
                    ))
                    seen_paths.add(track.filepath)
                    if len(alternatives) >= MAX_CANDIDATES:
                        break

        # Also scan via word coverage for matches fuzzy might miss
        if query_words:
            for idx, (_la, _lt, track) in enumerate(self._lib_entries):
                if track.filepath in seen_paths or not self._lib_word_sets[idx]:
                    continue
                word_set = self._lib_word_sets[idx]
                found = sum(1 for w in query_words if word_matches_pool(w, word_set))
                coverage = found / len(query_words)
                if coverage < 0.5:
                    continue

                if coverage >= 1.0:
                    score = 85
                    if _HAS_RAPIDFUZZ:
                        try:
                            sim = fuzz.partial_ratio(query_key, self._lib_keys[idx])
                            density_bonus = min(len(query_words), 5)
                            sim_bonus = max(0, (sim - 70) // 5)
                            score = min(85 + density_bonus + sim_bonus, 95)
                        except Exception:
                            pass
                elif coverage >= 0.8:
                    score = int(70 + (coverage - 0.8) * 70)
                else:
                    score = int(35 + coverage * 15)

                score = self._apply_full_pipeline(score, query_words, playlist_track, track)

                if score >= MIN_CANDIDATE_SCORE:
                    alternatives.append(CandidateMatch(
                        library_track=track, score=score,
                        confidence=self._confidence(score),
                    ))
                    seen_paths.add(track.filepath)

        alternatives.sort(key=lambda c: c.score, reverse=True)
        return alternatives[:MAX_CANDIDATES]

    # ---------------------------------------------------------------
    # Fuzzy similarity helpers
    # ---------------------------------------------------------------

    def _similarity(self, s1: str, s2: str, method: str) -> int:
        if not s1 or not s2:
            return 0
        if not _HAS_RAPIDFUZZ:
            return self._manual_similarity(s1, s2, method)
        try:
            return int(getattr(fuzz, method, fuzz.token_sort_ratio)(s1, s2))
        except Exception:
            return 0

    @staticmethod
    def _manual_similarity(s1: str, s2: str, method: str) -> int:
        """Pure-Python fallback when rapidfuzz is unavailable."""
        if not s1 or not s2:
            return 0

        def _bigram_ratio(a: str, b: str) -> int:
            if not a or not b:
                return 0
            bg1 = set(a[i : i + 2] for i in range(len(a) - 1))
            bg2 = set(b[i : i + 2] for i in range(len(b) - 1))
            if not bg1 or not bg2:
                return 0
            return int(len(bg1 & bg2) / len(bg1 | bg2) * 100)

        def _partial(a: str, b: str) -> int:
            if not a or not b:
                return 0
            short, long_ = (a, b) if len(a) <= len(b) else (b, a)
            if len(long_) < len(short):
                return 0
            return max(
                _bigram_ratio(short, long_[i : i + len(short)])
                for i in range(len(long_) - len(short) + 1)
            )

        if method == "token_sort_ratio":
            return _bigram_ratio(
                " ".join(sorted(s1.split())), " ".join(sorted(s2.split()))
            )
        if method == "token_set_ratio":
            set1, set2 = set(s1.split()), set(s2.split())
            inter = set1 & set2
            if not inter:
                return 0
            union = inter | (set1 - set2) | (set2 - set1)
            return _bigram_ratio(
                " ".join(sorted(inter)), " ".join(sorted(union))
            )
        if method == "partial_ratio":
            return _partial(s1, s2)
        return 0

    # ---------------------------------------------------------------
    # Utilities
    # ---------------------------------------------------------------

    @staticmethod
    def _confidence(score: int) -> MatchConfidence:
        if score >= 95:
            return MatchConfidence.EXACT
        if score >= 75:
            return MatchConfidence.HIGH
        if score >= 55:
            return MatchConfidence.MEDIUM
        return MatchConfidence.LOW