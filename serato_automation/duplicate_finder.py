# Serato Playlist Automation
# Advanced duplicate finder — fuzzy title clustering with similarity scores.
#
# The "easy" duplicates view (MainWindow._find_duplicates) groups tracks by an
# EXACT normalized (title, artist) key, so it only catches identical tags.
# Real DJ libraries have near-duplicates the exact match misses, e.g.:
#   "A Sky Full Of Stars (v2)"          artist: Coldplay
#   "Coldplay - A Sky Full Of Stars (Official Video)"   artist: Coldplay
#   "coldplay - A Sky Full Of Stars - originale"        artist: (empty)
#   "A Sky Full Of Stars (v3)"          artist: Coldplay
# After normalize_string these titles differ (the artist name is embedded in
# the title, extra words like "originale"), so the exact key splits them.
#
# token_set_ratio handles this: it compares the SET of tokens, so
# "a sky full of stars" is a 100% subset of "coldplay a sky full of stars" ->
# they cluster together.
#
# Scalability: O(N^2) token_set_ratio on 50k tracks is too slow, so we block
# via an inverted index on significant tokens (len >= 3, not stop-word-common)
# and only fuzzy-compare pairs that share at least one significant token.

from collections import defaultdict
from typing import Dict, List, Tuple

from .library_reader import LibraryTrack, normalize_string

try:
    from rapidfuzz import fuzz
    _HAS_RAPIDFUZZ = True
except ImportError:  # pragma: no cover
    fuzz = None
    _HAS_RAPIDFUZZ = False

import logging
logger = logging.getLogger("serato.dupfinder")


def _title_tokens(norm_title: str) -> List[str]:
    """Significant tokens of a normalized title (len >= 3)."""
    return [t for t in norm_title.split() if len(t) >= 3]


def find_advanced_duplicates(
    tracks: List[LibraryTrack],
    min_similarity: int = 80,
    max_block: int = 400,
) -> List[Dict]:
    """Cluster *tracks* by fuzzy title similarity.

    Returns a list of groups, each::
        {
          "representative_title": str,   # the title of the representative track
          "count": int,                  # number of tracks in the group
          "tracks": [(LibraryTrack, int)],  # (track, vicinanza_pct to rep)
        }
    Groups have >= 2 members and are sorted by count desc, then title.
    """
    if not _HAS_RAPIDFUZZ:
        logger.warning("rapidfuzz non disponibile — duplicati avanzati disabilitati")
        return []

    # 1) Normalize titles; keep only tracks with a non-empty normalized title.
    items: List[Tuple[LibraryTrack, str]] = []
    for t in tracks:
        nt = normalize_string((t.title or "") + " " + (t.artist or "")).strip()
        # Use the TITLE only for clustering (artist is too noisy: covers by
        # different artists would wrongly merge). Normalized title already
        # strips parentheticals, accents, mojibake.
        nt_title = normalize_string(t.title or "").strip()
        if nt_title:
            items.append((t, nt_title))
    n = len(items)
    if n < 2:
        return []

    # 2) Inverted index: significant token -> list of item indices.
    token_count: Dict[str, int] = defaultdict(int)
    for _, nt in items:
        for tok in set(_title_tokens(nt)):
            token_count[tok] += 1
    # Skip tokens that appear in too many tracks (stop-word-like: "love",
    # "remix", "original"). They'd create huge blocks and add noise.
    common_cutoff = max(50, int(n * 0.05))

    inv: Dict[str, List[int]] = defaultdict(list)
    for i, (_, nt) in enumerate(items):
        for tok in set(_title_tokens(nt)):
            if token_count[tok] <= common_cutoff:
                inv[tok].append(i)

    # 3) Union-find.
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

    # 4) Within each block, compare pairs with token_set_ratio; union if similar.
    pair_sim: Dict[int, Dict[int, int]] = defaultdict(dict)
    for tok, idxs in inv.items():
        if len(idxs) < 2 or len(idxs) > max_block:
            continue
        for a in range(len(idxs)):
            ia = idxs[a]
            nta = items[ia][1]
            for b in range(a + 1, len(idxs)):
                ib = idxs[b]
                sim = fuzz.token_set_ratio(nta, items[ib][1])
                if sim >= min_similarity:
                    union(ia, ib)
                    pair_sim[ia][ib] = sim
                    pair_sim[ib][ia] = sim

    # 5) Build clusters (>= 2 members only).
    clusters: Dict[int, List[int]] = defaultdict(list)
    for i in range(n):
        clusters[find(i)].append(i)

    groups: List[Dict] = []
    for members in clusters.values():
        if len(members) < 2:
            continue
        # Representative = member with the highest average similarity to the
        # others (falls back to the first if no sim recorded — e.g. all exact).
        rep, best_avg = members[0], -1.0
        for m in members:
            sims = [pair_sim[m].get(o, 100 if items[m][1] == items[o][1] else 0)
                    for o in members if o != m]
            avg = (sum(sims) / len(sims)) if sims else 0.0
            if avg > best_avg:
                best_avg, rep = avg, m
        rep_track = items[rep][0]
        rep_norm = items[rep][1]
        members_scored: List[Tuple[LibraryTrack, int]] = []
        for m in members:
            t = items[m][0]
            if m == rep:
                score = 100
            else:
                score = int(fuzz.token_set_ratio(rep_norm, items[m][1]))
            members_scored.append((t, max(0, min(100, score))))
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
