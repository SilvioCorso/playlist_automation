# Serato Playlist Automation
# Advanced duplicate finder — fuzzy title clustering with similarity scores.
#
# "Easy" duplicates groups by an EXACT normalized (title, artist) key, so it
# only catches identical tags. Real DJ libraries have near-duplicates it
# misses (the artist name embedded in the title, extra descriptor words):
#   "A Sky Full Of Stars (v2)"                               artist: Coldplay
#   "Coldplay - A Sky Full Of Stars (Official Video)"        artist: Coldplay
#   "coldplay - A Sky Full Of Stars - originale"             artist: (empty)
#   "A Sky Full Of Stars (v3)"                               artist: Coldplay
#
# Matching strategy (mirrors the "Confronta con libreria" accounting model):
# two titles are duplicates when the SMALLER title's token set is a SUBSET of
# the larger's, the smaller has >= 2 tokens (single-word titles like "Love" or
# "Batman" are too generic to cluster — "Love" appears 1000+ times and is NOT
# a duplicate signal), and the larger has at most a few extra tokens (artist
# name / descriptor). The vicinanza % is 100 minus a penalty per extra token.
#
# This avoids the over-clustering of raw token_set_ratio, which returns 100%
# whenever one title is a subset of the other regardless of how many extra
# words the larger has — so "Love" matched "Love Me Do", "Love Is All", ...
# and produced a 1671-track "LOVE" cluster.
#
# Scalability: O(N^2) subset checks on 50k tracks is too slow, so we block via
# an inverted index on significant tokens (len >= 3, stop-word-filtered) and
# only check candidate pairs that share at least one significant token.

from collections import defaultdict
from typing import Dict, List, Tuple

from .library_reader import LibraryTrack, normalize_string

import logging
logger = logging.getLogger("serato.dupfinder")

# --- tuning ---------------------------------------------------------------
MIN_SIMILARITY = 75      # vicinanza % required to cluster a pair
MAX_EXTRA_TOKENS = 3     # max extra tokens in the larger title (beyond the smaller)
EXTRA_PENALTY = 10       # % subtracted per extra token
MIN_TOKENS = 2           # smaller title must have >= this many tokens (skip "Love")
MAX_BLOCK = 400          # skip token blocks larger than this (perf)


def _tokens(norm_title: str) -> set:
    """All tokens of a normalized title (lowercased, parentheticals already
    stripped by normalize_string). Short tokens ('a', 'of') are KEPT — they're
    part of the song identity — but only len>=3 tokens are used for blocking.
    Pure-punctuation tokens ('-', '/') are dropped so they don't inflate the
    'extra words' penalty.
    """
    import re
    return {t for t in norm_title.split() if re.search(r"[a-z0-9]", t)}


def _dup_score(a_tokens: set, b_tokens: set) -> int:
    """Similarity % between two title token sets.

    Returns 100 only for identical token sets. If the smaller set is a subset
    of the larger, returns 100 - EXTRA_PENALTY per extra token (the larger
    title has extra words like the artist name or a descriptor). Returns 0
    when the smaller has < MIN_TOKENS tokens (single-word titles are too
    generic) or when the sets aren't in a subset relation (different song).
    """
    if a_tokens == b_tokens:
        return 100
    if not a_tokens or not b_tokens:
        return 0
    if len(a_tokens) <= len(b_tokens):
        small, large = a_tokens, b_tokens
    else:
        small, large = b_tokens, a_tokens
    if len(small) < MIN_TOKENS:
        return 0
    if not small <= large:  # not a subset -> different song
        return 0
    extra = len(large) - len(small)
    if extra > MAX_EXTRA_TOKENS:
        return 0
    return max(0, 100 - extra * EXTRA_PENALTY)


def find_advanced_duplicates(
    tracks: List[LibraryTrack],
    min_similarity: int = MIN_SIMILARITY,
) -> List[Dict]:
    """Cluster *tracks* by fuzzy title similarity (subset + extra-word penalty).

    Returns a list of groups, each::
        {
          "representative_title": str,
          "count": int,
          "tracks": [(LibraryTrack, int)],  # (track, vicinanza_pct to rep)
        }
    Groups have >= 2 members and are sorted by count desc, then title.
    """
    # 1) Normalize + tokenize; keep tracks with a non-empty title.
    items: List[Tuple[LibraryTrack, str, set]] = []
    for t in tracks:
        nt = normalize_string(t.title or "").strip()
        if not nt:
            continue
        items.append((t, nt, _tokens(nt)))
    n = len(items)
    if n < 2:
        return []

    # 2) Inverted index on significant tokens (len >= 3) for blocking.
    token_count: Dict[str, int] = defaultdict(int)
    for _, _, toks in items:
        for tok in toks:
            if len(tok) >= 3:
                token_count[tok] += 1
    # Skip stop-word-like tokens that appear in too many tracks.
    common_cutoff = max(50, int(n * 0.05))

    inv: Dict[str, List[int]] = defaultdict(list)
    for i, (_, _, toks) in enumerate(items):
        for tok in toks:
            if len(tok) >= 3 and token_count[tok] <= common_cutoff:
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

    # 4) For each candidate pair (sharing a significant token), score via the
    #    subset rule; union if >= min_similarity.
    pair_sim: Dict[int, Dict[int, int]] = defaultdict(dict)
    for tok, idxs in inv.items():
        if len(idxs) < 2 or len(idxs) > MAX_BLOCK:
            continue
        for a in range(len(idxs)):
            ia = idxs[a]
            ta = items[ia][2]
            for b in range(a + 1, len(idxs)):
                ib = idxs[b]
                score = _dup_score(ta, items[ib][2])
                if score >= min_similarity:
                    union(ia, ib)
                    # keep the best score seen for the pair
                    prev = pair_sim[ia].get(ib, 0)
                    if score > prev:
                        pair_sim[ia][ib] = score
                        pair_sim[ib][ia] = score

    # 5) Build clusters (>= 2 members).
    clusters: Dict[int, List[int]] = defaultdict(list)
    for i in range(n):
        clusters[find(i)].append(i)

    groups: List[Dict] = []
    for members in clusters.values():
        if len(members) < 2:
            continue
        # Representative = the member with the FEWEST title tokens (the "base"
        # title, e.g. "A Sky Full Of Stars" rather than the one with "Coldplay"
        # embedded). Tie-break by highest average similarity.
        def _key(m):
            toks = items[m][2]
            sims = [pair_sim[m].get(o, 0) for o in members if o != m]
            avg = (sum(sims) / len(sims)) if sims else 0.0
            return (len(toks), -avg)
        rep = min(members, key=_key)
        rep_toks = items[rep][2]
        rep_track = items[rep][0]
        members_scored: List[Tuple[LibraryTrack, int]] = []
        for m in members:
            t = items[m][0]
            score = 100 if m == rep else _dup_score(rep_toks, items[m][2])
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
