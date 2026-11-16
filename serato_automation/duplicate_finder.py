# Serato Playlist Automation
# Advanced duplicate finder — segment-based title clustering with similarity.
#
# Two titles are duplicates when they share the same SONG-TITLE SEGMENT,
# where a segment is the part of the title between " - " separators (after
# normalize_string has stripped parentheticals / accents / mojibake). The dash
# almost always separates the song title from an artist or detail that we want
# to IGNORE for duplicate detection.
#
# Examples (user-reported):
#   CLUSTER (same song):
#     "On My Mind"                          -> segments: {"on my mind"}
#     "On My Mind (MK Remix)"               -> normalize strips (MK Remix)
#                                            -> segments: {"on my mind"}
#     "On My Mind - Diplo & SIDEPIECE"      -> split on " - "
#                                            -> segments: {"on my mind", "diplo & sidepiece"}
#                                            -> shares "on my mind" -> CLUSTER
#   DO NOT CLUSTER (different songs, different words):
#     "my mind"        -> segments: {"my mind"}
#     "on my mind"     -> segments: {"on my mind"}
#     "take my mind"   -> segments: {"take my mind"}
#     (no common segment -> not duplicates)
#
# Single-token segments ("Love", "Batman") are excluded — a one-word title is
# too generic to be a duplicate signal ("Love" appears 1000+ times and is NOT
# the same song).
#
# Scalability: an inverted index maps each normalized segment string to the
# list of tracks that have it; tracks sharing a segment are unioned. O(N) in
# the number of segments, no pairwise fuzzy comparisons needed.

from collections import defaultdict
from typing import Dict, List, Tuple

from .library_reader import LibraryTrack, normalize_string

import logging
logger = logging.getLogger("serato.dupfinder")

MIN_TOKENS = 2          # a segment needs >= this many tokens to be a duplicate key


def _segment_tokens(seg: str) -> set:
    """Tokens of a segment (drops pure-punctuation tokens like '-')."""
    import re
    return {t for t in seg.split() if re.search(r"[a-z0-9]", t)}


def _title_segments(raw_title: str) -> List[str]:
    """Split a RAW title on ' - ' and normalise each segment, keeping those with
    at least MIN_TOKENS tokens.

    The split MUST happen before normalisation: normalize_string strips dashes,
    so splitting the already-normalised string would merge artist and title into
    one segment. Parentheticals / accents / mojibake are stripped per-segment by
    normalize_string; the dash separates the song title from artist/detail,
    which we ignore for duplicate detection.
    """
    segs = []
    for raw in raw_title.split(" - "):
        s = normalize_string(raw).strip()
        if s and len(_segment_tokens(s)) >= MIN_TOKENS:
            segs.append(s)
    return segs


def find_advanced_duplicates(
    tracks: List[LibraryTrack],
    min_similarity: int = 75,
) -> List[Dict]:
    """Cluster *tracks* that share a song-title segment.

    Returns a list of groups, each::
        {
          "representative_title": str,
          "count": int,
          "tracks": [(LibraryTrack, int)],  # (track, vicinanza_pct to rep)
        }
    Groups have >= 2 members, sorted by count desc then title.
    """
    # 1) Normalize + segment each title (split on ' - ' BEFORE normalising so
    #    the artist/detail side of the dash is a separate segment).
    items: List[Tuple[LibraryTrack, str, List[str]]] = []
    for t in tracks:
        raw = (t.title or "").strip()
        if not raw:
            continue
        segs = _title_segments(raw)
        if segs:  # skip tracks whose title has no >=2-token segment (e.g. "Love")
            nt = normalize_string(raw).strip()
            items.append((t, nt, segs))
    n = len(items)
    if n < 2:
        return []

    # 2) Inverted index: normalized segment string -> list of item indices.
    inv: Dict[str, List[int]] = defaultdict(list)
    for i, (_t, _nt, segs) in enumerate(items):
        for s in set(segs):  # dedupe segments within the same track
            inv[s].append(i)

    # 3) Union-find; union every pair that shares a segment.
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

    # 4) Build clusters (>= 2 members).
    clusters: Dict[int, List[int]] = defaultdict(list)
    for i in range(n):
        clusters[find(i)].append(i)

    groups: List[Dict] = []
    for members in clusters.values():
        if len(members) < 2:
            continue
        # Representative = the member with the FEWEST segments and the shortest
        # title (the cleanest "song title", e.g. "On My Mind" rather than
        # "On My Mind - Diplo & SIDEPIECE").
        def _key(m):
            return (len(items[m][2]), len(items[m][1]))
        rep = min(members, key=_key)
        rep_norm = items[rep][1]
        rep_segs = set(items[rep][2])
        rep_track = items[rep][0]
        members_scored: List[Tuple[LibraryTrack, int]] = []
        for m in members:
            t = items[m][0]
            if m == rep:
                score = 100
            elif items[m][1] == rep_norm:
                score = 100  # identical normalized title
            elif rep_segs & set(items[m][2]):
                score = 95   # shares the rep's song-title segment
            else:
                score = 85   # joined transitively via another member's segment
            members_scored.append((t, score))
        members_scored.sort(key=lambda x: -x[1])
        groups.append({
            "representative_title": rep_track.title or "",
            "count": len(members_scored),
            "tracks": members_scored,
        })

    groups.sort(key=lambda g: (-g["count"], g["representative_title"].lower()))
    logger.info("Duplicati avanzati: %d gruppi su %d tracce analizzate",
                len(groups), n)
    return groups
