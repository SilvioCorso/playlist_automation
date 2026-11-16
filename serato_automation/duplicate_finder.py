# Serato Playlist Automation
# Advanced duplicate finder — longest-segment title clustering.
#
# Two tracks are duplicates when they share the SONG-TITLE SEGMENT, where the
# song-title segment is the LONGEST segment (by token count) of the title after
# splitting on " - " and normalising (parentheticals / accents / mojibake
# stripped). The artist / detail segment is almost always SHORTER than the song
# title segment, so it is never the longest and never triggers clustering.
#
# This fixes the artist over-clustering that defeated the rarity filter:
# "Eiffel 65 - Move Your Body", "Eiffel 65 - Blue", "Eiffel 65 - Enjoy the
# Silence" all shared the segment "eiffel 65" (the artist, 2 tokens) and were
# wrongly collapsed into one 18-track group. With the longest-segment rule:
#   "Eiffel 65 - Move Your Body"  longest seg = "move your body" (3 tok)
#   "Eiffel 65 - Blue"            longest seg = "blue" (1 tok -> dropped)
#   -> they share NO longest segment -> NOT clustered.
#   "Move Your Body (128kbit)"    longest seg = "move your body" (3 tok)
#   -> shares "move your body" with the Eiffel track -> CLUSTER (same song).
#
# "On My Mind" / "On My Mind (MK Remix)" / "On My Mind - Diplo & SIDEPIECE"
# all have "on my mind" as their longest segment -> CLUSTER.
# "my mind" / "on my mind" / "take my mind" have DIFFERENT longest segments
# ("my mind", "on my mind", "take my mind") -> NOT clustered.
#
# Single-token segments are dropped (a one-word title like "Love" is too
# generic). When a track's longest segment has < 2 tokens it can't cluster.

from collections import defaultdict
import re
import unicodedata
from typing import Dict, List, Optional, Tuple

from .library_reader import LibraryTrack, normalize_string, repair_mojibake

import logging
logger = logging.getLogger("serato.dupfinder")

MIN_TOKENS = 2
_PAREN_RE = re.compile(r"\s*\([^)]*\)")
_PARENS_RE = re.compile(r"[()]")


def _dup_norm(s: str) -> str:
    """Normalise a title segment for duplicate matching.

    Lowercase, repair mojibake, strip accents, underscores -> spaces. Then
    strip parentheticals — BUT if the result has fewer than MIN_TOKENS tokens
    (e.g. 'Blue (Da Ba Dee)' -> 'blue', 1 token), retry keeping the parenthetical
    content ('blue da ba dee', 4 tokens) so the song title is not lost and the
    artist segment does not become the longest.
    """
    s = s.lower()
    try:
        s = repair_mojibake(s)
    except Exception:
        pass
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.replace("_", " ")

    stripped = _PAREN_RE.sub("", s)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    toks = [t for t in stripped.split() if re.search(r"[a-z0-9]", t)]
    if len(toks) >= MIN_TOKENS:
        return stripped
    # Too short after stripping parentheticals — keep the parenthetical content
    # (just remove the bracket characters themselves).
    kept = _PARENS_RE.sub("", s)
    kept = re.sub(r"\s+", " ", kept).strip()
    return kept


def _segment_tokens(seg: str) -> set:
    """Tokens of a segment (drops pure-punctuation tokens like '-')."""
    return {t for t in seg.split() if re.search(r"[a-z0-9]", t)}


def _title_segments(raw_title: str) -> List[Tuple[str, str]]:
    """Split a RAW title on ' - ' and normalise each segment.

    Returns (raw_segment, normalized_segment) pairs for segments with at least
    MIN_TOKENS tokens. The split happens BEFORE normalisation because the dash
    would otherwise be lost. Uses _dup_norm (adaptive parenthetical stripping)
    instead of normalize_string so a title like 'Blue (Da Ba Dee)' keeps its
    subtitle instead of collapsing to a single token.
    """
    out = []
    for raw in raw_title.split(" - "):
        norm = _dup_norm(raw)
        if norm and len(_segment_tokens(norm)) >= MIN_TOKENS:
            out.append((raw.strip(), norm))
    return out


def _longest_segment(segs: List[Tuple[str, str]]) -> Optional[Tuple[str, str]]:
    """Return the (raw, norm) segment with the most tokens; tie-break by length."""
    if not segs:
        return None
    return max(segs, key=lambda rs: (len(_segment_tokens(rs[1])), len(rs[1])))


def find_advanced_duplicates(
    tracks: List[LibraryTrack],
    min_similarity: int = 75,
) -> List[Dict]:
    """Cluster *tracks* that share a song-title (longest) segment.

    Returns a list of groups, each::
        {
          "representative_title": str,
          "count": int,
          "tracks": [(LibraryTrack, int)],
        }
    Groups have >= 2 members, sorted by count desc then title.
    """
    # 1) Segment each title; compute its longest segment (the song title).
    items: List[Tuple[LibraryTrack, str, List[Tuple[str, str]], Optional[Tuple[str, str]]]] = []
    for t in tracks:
        raw = (t.title or "").strip()
        if not raw:
            continue
        segs = _title_segments(raw)
        if not segs:
            continue
        longest = _longest_segment(segs)
        if longest is None:
            continue
        nt = normalize_string(raw).strip()
        items.append((t, nt, segs, longest))
    n = len(items)
    if n < 2:
        return []

    # 2) Step 1 — artist-name exclusion.
    #    A segment that coincides EXACTLY (normalised) with the artist of ANY
    #    track that contains it is an ARTIST NAME, not a song title. Such
    #    segments are NEVER treated as song keys -> they don't drive clustering
    #    (an artist must not unite different songs, and a group whose title
    #    would be the artist is not reported as a duplicate).
    all_inv: Dict[str, List[int]] = defaultdict(list)
    for i, (_t, _nt, segs, _longest) in enumerate(items):
        for _r, norm in segs:
            all_inv[norm].append(i)
    artist_segments: set = set()
    for s, idxs in all_inv.items():
        for i in idxs:
            if _dup_norm(items[i][0].artist or "") == s:
                artist_segments.add(s)
                break

    # 3) A segment is a "song-title key" when it is the LONGEST segment of at
    #    least one track AND it is not an artist-name segment.
    song_keys: set = set()
    for _t, _nt, _segs, longest in items:
        if longest is not None and longest[1] not in artist_segments:
            song_keys.add(longest[1])

    # 4) Inverted index: normalized song-key segment -> list of item indices.
    inv: Dict[str, List[int]] = defaultdict(list)
    for i, (_t, _nt, segs, _longest) in enumerate(items):
        for _r, norm in segs:
            if norm in song_keys:
                inv[norm].append(i)

    # 5) Union-find; union tracks that share a song-key segment.
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for seg, idxs in inv.items():
        if len(idxs) < 2:
            continue
        base = idxs[0]
        for other in idxs[1:]:
            union(base, other)

    # 5) Build clusters (>= 2 members).
    clusters: Dict[int, List[int]] = defaultdict(list)
    for i in range(n):
        clusters[find(i)].append(i)

    groups: List[Dict] = []
    for members in clusters.values():
        if len(members) < 2:
            continue
        # Representative = the member whose longest segment is shared by the
        # most other members (the defining song title). Fall back to the
        # member with the shortest full title.
        seg_count: Dict[str, int] = defaultdict(int)
        for m in members:
            seg_count[items[m][3][1]] += 1
        defining_norm = max(seg_count, key=seg_count.get)

        # --- Step 1: artist-name exclusion -------------------------------
        # If the defining segment (the accordion title) coincides EXACTLY with
        # any track's artist (normalised), the group is keyed on an ARTIST name,
        # not a song title -> skip it. The goal is song duplicates, not artist
        # duplicates (e.g. an "Vasco Rossi" accordion where every row's artist is
        # "Vasco Rossi" must NOT be reported).
        artist_norms = {_dup_norm(items[m][0].artist or "") for m in members}
        artist_norms.discard("")
        if defining_norm in artist_norms:
            continue

        # Pick the raw form of the defining segment: the SHORTEST raw among
        # members that have it, with trailing parentheticals stripped.
        import re as _re
        raws = []
        for m in members:
            for r, norm in items[m][2]:
                if norm == defining_norm:
                    cleaned = _re.sub(r"\s*\([^)]*\)", "", r).strip() or r
                    raws.append(cleaned)
                    break
        rep_title = min(raws, key=len) if raws else items[members[0]][0].title or ""

        rep = min(members, key=lambda m: (len(items[m][1]), len(items[m][2])))
        rep_norm = items[rep][1]
        rep_longest_norm = items[rep][3][1]

        members_scored: List[Tuple[LibraryTrack, int]] = []
        for m in members:
            t = items[m][0]
            if m == rep:
                score = 100
            elif items[m][1] == rep_norm:
                score = 100
            elif items[m][3][1] == rep_longest_norm:
                score = 95
            else:
                score = 85
            members_scored.append((t, score))
        members_scored.sort(key=lambda x: -x[1])
        groups.append({
            "representative_title": rep_title,
            "count": len(members_scored),
            "tracks": members_scored,
        })

    groups.sort(key=lambda g: (-g["count"], g["representative_title"].lower()))
    logger.info("Duplicati avanzati: %d gruppi su %d tracce analizzate",
                len(groups), n)
    return groups
