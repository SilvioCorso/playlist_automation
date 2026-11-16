# Serato Playlist Automation
# Advanced duplicate finder — segment-based title clustering with similarity.
#
# Two titles are duplicates when they share the same SONG-TITLE SEGMENT,
# where a segment is the part of the title between " - " separators (after
# normalize_string has stripped parentheticals / accents / mojibake). The dash
# almost always separates the song title from an artist or detail that we want
# to IGNORE for duplicate detection.
#
# CRUCIAL — artist exclusion: an artist name appears as a segment in EVERY
# track by that artist ("Depeche Mode - Precious", "Depeche Mode - Enjoy the
# Silence", ...) so all 25 Depeche Mode songs shared the segment "depeche mode"
# and were wrongly clustered into one 25-track group. The fix: a segment is
# only usable for clustering when it is RARE — i.e. it co-occurs with FEW
# distinct other segments. The artist segment co-occurs with many different
# song titles (one per song) so it is flagged common and skipped; the
# song-title segment co-occurs with few (remix/descriptor variants of the SAME
# song) so it is kept.
#
# Examples:
#   CLUSTER (same song, share the rare song-title segment):
#     "On My Mind"                      segs: {on my mind}
#     "On My Mind (MK Remix)"           segs: {on my mind}
#     "On My Mind - Diplo & SIDEPIECE"  segs: {on my mind, diplo sidepiece}
#       -> share "on my mind" (rare) -> CLUSTER
#   DO NOT CLUSTER (different songs, only share the common artist segment):
#     "Depeche Mode - Precious"            segs: {depeche mode*, precious}
#     "Depeche Mode - Enjoy the Silence"   segs: {depeche mode*, enjoy the silence}
#       -> only shared segment is "depeche mode" (common -> artist) -> NO CLUSTER
#
# Single-token segments ("Love", "Batman") are excluded — a one-word title is
# too generic to be a duplicate signal.

from collections import defaultdict
from typing import Dict, List, Tuple

from .library_reader import LibraryTrack, normalize_string

import logging
logger = logging.getLogger("serato.dupfinder")

MIN_TOKENS = 2          # a segment needs >= this many tokens to be a key
MAX_CO_SEGMENTS = 8     # a segment co-occurring with > this many distinct other
                        # segments is an artist / common name, not a song title


def _segment_tokens(seg: str) -> set:
    """Tokens of a segment (drops pure-punctuation tokens like '-')."""
    import re
    return {t for t in seg.split() if re.search(r"[a-z0-9]", t)}


def _title_segments(raw_title: str) -> List[Tuple[str, str]]:
    """Split a RAW title on ' - ' and normalise each segment.

    Returns a list of (raw_segment, normalized_segment) for segments that have
    at least MIN_TOKENS tokens. The split MUST happen before normalisation
    (normalize_string strips dashes, so splitting the normalised string would
    merge artist and title into one segment).
    """
    out = []
    for raw in raw_title.split(" - "):
        norm = normalize_string(raw).strip()
        if norm and len(_segment_tokens(norm)) >= MIN_TOKENS:
            out.append((raw.strip(), norm))
    return out


def find_advanced_duplicates(
    tracks: List[LibraryTrack],
    min_similarity: int = 75,
) -> List[Dict]:
    """Cluster *tracks* that share a rare song-title segment.

    Returns a list of groups, each::
        {
          "representative_title": str,
          "count": int,
          "tracks": [(LibraryTrack, int)],  # (track, vicinanza_pct to rep)
        }
    Groups have >= 2 members, sorted by count desc then title.
    """
    # 1) Segment each title (split on ' - ' BEFORE normalising).
    items: List[Tuple[LibraryTrack, str, List[str], Dict[str, str]]] = []
    for t in tracks:
        raw = (t.title or "").strip()
        if not raw:
            continue
        seg_pairs = _title_segments(raw)
        if not seg_pairs:
            continue  # no >=2-token segment (e.g. "Love") -> can't cluster
        norm_segs = [n for _r, n in seg_pairs]
        raw_map = {n: r for r, n in seg_pairs}
        nt = normalize_string(raw).strip()
        items.append((t, nt, norm_segs, raw_map))
    n = len(items)
    if n < 2:
        return []

    # 2) Inverted index: normalized segment -> list of item indices.
    inv: Dict[str, List[int]] = defaultdict(list)
    for i, (_t, _nt, segs, _rm) in enumerate(items):
        for s in set(segs):
            inv[s].append(i)

    # 3) Rarity filter: a segment is an ARTIST / common name if the tracks that
    #    contain it co-occur with MANY distinct OTHER segments (i.e. the segment
    #    does not pin down a single song — it's shared across different songs).
    #    Such segments are excluded from clustering.
    song_like: Dict[str, bool] = {}
    for s, idxs in inv.items():
        co = set()
        for i in idxs:
            for s2 in items[i][2]:
                if s2 != s:
                    co.add(s2)
        song_like[s] = len(co) <= MAX_CO_SEGMENTS

    # 4) Union-find; union tracks that share a song-like segment.
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

    # shared_song_like[a] = set of song-like segments a has (for rep scoring)
    shared_song_like: Dict[int, set] = {i: {s for s in items[i][2] if song_like.get(s)}
                                        for i in range(n)}
    pair_shared: Dict[int, set] = defaultdict(set)  # for scoring (not all pairs)

    for s, idxs in inv.items():
        if not song_like.get(s):
            continue  # artist / common — skip
        if len(idxs) < 2:
            continue
        base = idxs[0]
        for other in idxs[1:]:
            union(base, other)
            pair_shared[base].add(s)
            pair_shared[other].add(s)

    # 5) Build clusters (>= 2 members).
    clusters: Dict[int, List[int]] = defaultdict(list)
    for i in range(n):
        clusters[find(i)].append(i)

    groups: List[Dict] = []
    for members in clusters.values():
        if len(members) < 2:
            continue
        # Defining segment = the song-like segment shared by the most members.
        seg_member_count: Dict[str, int] = defaultdict(int)
        for m in members:
            for s in shared_song_like[m]:
                seg_member_count[s] += 1
        if seg_member_count:
            defining = max(seg_member_count, key=seg_member_count.get)
        else:
            defining = None

        # Representative = member with the fewest segments + shortest title
        # (the cleanest "song title"). Its title is used for the accordion
        # header, falling back to the defining segment's raw form.
        def _key(m):
            return (len(items[m][2]), len(items[m][1]))
        rep = min(members, key=_key)
        rep_track = items[rep][0]

        if defining and defining in items[rep][3]:
            rep_title = items[rep][3][defining]
        elif defining:
            # use the raw form of the defining segment from any member
            rep_title = defining
            for m in members:
                if defining in items[m][3]:
                    rep_title = items[m][3][defining]
                    break
        else:
            rep_title = rep_track.title or ""

        # Clean the display title: pick the SHORTEST raw form of the defining
        # segment among members (a version without extra descriptors is cleaner)
        # and strip trailing parentheticals like "(v2)" / "(Remix)" so the
        # accordion header shows the bare song title.
        if defining:
            raws = [items[m][3][defining] for m in members if defining in items[m][3]]
            if raws:
                import re as _re
                cleaned = [_re.sub(r"\s*\([^)]*\)", "", r).strip() or r for r in raws]
                rep_title = min(cleaned, key=len)

        members_scored: List[Tuple[LibraryTrack, int]] = []
        rep_norm = items[rep][1]
        rep_sls = shared_song_like[rep]
        for m in members:
            t = items[m][0]
            if m == rep:
                score = 100
            elif items[m][1] == rep_norm:
                score = 100
            elif rep_sls & shared_song_like[m]:
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
