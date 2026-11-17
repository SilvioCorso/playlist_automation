# Serato Playlist Automation
# Advanced duplicate finder — substring-based title clustering.
#
# Two tracks are duplicates when one track's normalised title is a SUBSTRING
# (contiguous) of the other's. The accordion title is that shared string — by
# construction it is literally FOUND IN the song titles of every member.
#
# This replaces the old "longest segment" rule (which was nonsense: it split on
# ' - ' and tie-broke on STRING LENGTH, so the artist 'adonis fr' could become
# the 'longest' segment of a track whose song title had the same token count,
# then united 20 different Adonis FR songs into one bogus group).
#
# Validation (rule 2): after clustering, the accordion title (the shortest
# normalised title in the cluster) MUST be a substring of EVERY member's title.
# If it is not, the cluster is a transitivity artefact (A⊆B and C⊆B united A
# and C even though they share nothing) and is discarded.
#
# Step 1 (artist-name exclusion, kept): if the accordion title matches the
# artist of any member, the group is artist-keyed, not song-keyed -> skip.

from collections import defaultdict
import re
import unicodedata
from typing import Dict, List, Tuple

from .library_reader import LibraryTrack, normalize_string, repair_mojibake

import logging
logger = logging.getLogger("serato.dupfinder")

MIN_TOKENS = 2
_PAREN_RE = re.compile(r"\s*\([^)]*\)")
_PARENS_RE = re.compile(r"[()]")


def _dup_norm(s: str) -> str:
    """Normalise a title for duplicate matching.

    Lowercase, repair mojibake, strip accents, underscores -> spaces, remove
    dashes (so 'On My Mind - Diplo' -> 'on my mind diplo'), and ALWAYS strip
    parentheticals ('(MK Remix)', '(128kbit_AAC)', '(Official Video)', '(v2)').
    Consistent stripping is required so two rips of the same song with DIFFERENT
    parenthetical tags still normalise to the same string.
    """
    s = s.lower()
    try:
        s = repair_mojibake(s)
    except Exception:
        pass
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.replace("_", " ").replace("-", " ")
    s = _PAREN_RE.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _tokens(s: str) -> List[str]:
    return [t for t in s.split() if re.search(r"[a-z0-9]", t)]


def _segments_normalized(raw_title: str) -> set:
    """Split a RAW title on '-' and normalise each segment.

    Returns the set of normalised segment strings (parentheticals stripped,
    accents/mojibake repaired, lowercased). Used by rule 3: the accordion
    string must EXACTLY equal one of these segments in every member's title.
    """
    segs = set()
    for part in (raw_title or "").split("-"):
        s = _dup_norm(part)
        if s:
            segs.add(s)
    return segs


_VERSION_RE = re.compile(r"\(\s*v\s*\d+\s*\)", re.IGNORECASE)


def _is_versioned_group(raw_titles: List[str]) -> bool:
    """A group is 'versioned duplicates' when every member's title differs
    ONLY by a (vN) version tag — i.e. after stripping '(v1)','(v2)',... the
    titles normalise to the same string. Such groups are intentional versions
    (the user deliberately kept multiple rips), not real duplicates.

    The check runs on the RAW titles because _dup_norm already strips ALL
    parentheticals (including the version tag), so the (vN) marker would be
    gone by the time we look at the normalised form.
    """
    if not raw_titles:
        return False
    # At least one member must carry a (vN) version tag.
    if not any(_VERSION_RE.search(rt or "") for rt in raw_titles):
        return False
    stripped = [_dup_norm(_VERSION_RE.sub("", rt or "")) for rt in raw_titles]
    first = stripped[0]
    if not first:
        return False
    return all(s == first for s in stripped)


def find_advanced_duplicates(
    tracks: List[LibraryTrack],
    min_similarity: int = 75,
    show_versioned: bool = False,
) -> List[Dict]:
    """Cluster *tracks* whose normalised title is a substring of another's.

    Returns groups with >= 2 members, each::
        { "representative_title": str, "count": int,
          "tracks": [(LibraryTrack, int)] }
    """
    # 1) Normalise each title; keep tracks with a >=2-token normalised title.
    items: List[Tuple[LibraryTrack, str]] = []  # (track, norm_title)
    for t in tracks:
        raw = (t.title or "").strip()
        if not raw:
            continue
        nt = _dup_norm(raw)
        if nt and len(_tokens(nt)) >= MIN_TOKENS:
            items.append((t, nt))
    n = len(items)
    if n < 2:
        return []

    # 2) Inverted index: token -> tracks whose norm_title CONTAINS that token.
    #    A substring must share every token with the superset, so we block on
    #    the RAREST token of each track's title to find candidate supersets.
    inv: Dict[str, List[int]] = defaultdict(list)
    for i, (_t, nt) in enumerate(items):
        for tok in set(_tokens(nt)):
            inv[tok].append(i)

    # 3) Union-find; union i and j when norm_title(i) is a substring of
    #    norm_title(j) or vice versa (contiguous substring, Python 'in').
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

    for i in range(n):
        si = items[i][1]
        sitoks = _tokens(si)
        if not sitoks:
            continue
        # candidates = tracks containing the rarest token of si (smallest block).
        rarest = min(sitoks, key=lambda t: len(inv.get(t, [])))
        for j in inv.get(rarest, []):
            if j == i:
                continue
            nj = items[j][1]
            if si == nj:
                union(i, j)  # identical normalised titles
                continue
            # Determine shorter / longer normalised title.
            if len(si) <= len(nj):
                short_norm, long_track = si, items[j][0]
            else:
                short_norm, long_track = nj, items[i][0]
            long_norm = long_track and (nj if len(si) <= len(nj) else si)
            # Rule 2 + Rule 3 at PAIR level: union only if the shorter title is
            # a SUBSTRING of the longer AND is an EXACT dash-segment of the
            # longer's raw title. This prevents 'my mind' unioning with
            # 'on my mind' (substring yes, but 'my mind' is not an exact segment
            # of 'on my mind' which splits to ['on my mind']) while still
            # unioning 'On My Mind' with 'On My Mind - Diplo & SIDEPIECE'
            # ('On My Mind' is an exact segment of the latter).
            if short_norm in long_norm and short_norm in _segments_normalized(long_track.title):
                union(i, j)

    # 4) Build clusters (>= 2 members).
    clusters: Dict[int, List[int]] = defaultdict(list)
    for i in range(n):
        clusters[find(i)].append(i)

    groups: List[Dict] = []
    for members in clusters.values():
        if len(members) < 2:
            continue
        # Accordion title = the SHORTEST norm_title in the cluster (the common
        # substring that is contained in every other member's title).
        members_by_len = sorted(members, key=lambda m: len(items[m][1]))
        rep = members_by_len[0]
        rep_norm = items[rep][1]

        # Rule 2 — validation: the accordion string MUST be a substring of EVERY
        # member's title. If some member does not contain it, the cluster is a
        # transitivity artefact -> discard it.
        if not all(rep_norm in items[m][1] for m in members):
            continue

        # Rule 3 — exact-segment match: the accordion string must EXACTLY equal
        # one of the dash-separated segments of EVERY member's title. This
        # rejects 'my mind' clustering with 'on my mind' / 'take my mind': the
        # titles split to ['on my mind'] / ['take my mind'], and 'my mind' is
        # not an exact segment of either. It KEEPS 'On My Mind' with
        # 'On My Mind - Diplo & SIDEPIECE' (splits to ['On My Mind', 'Diplo &
        # SIDEPIECE'] -> 'On My Mind' is an exact segment).
        if not all(rep_norm in _segments_normalized(items[m][0].title) for m in members):
            continue

        # Step 1 — artist-name exclusion: if the accordion string matches the
        # artist (normalised) of any member, this is an artist-keyed group -> skip.
        artist_norms = {_dup_norm(items[m][0].artist or "") for m in members}
        artist_norms.discard("")
        if rep_norm in artist_norms:
            continue

        # Display title: the raw title of the rep, with trailing parentheticals
        # stripped; fall back to the norm string.
        rep_raw = items[rep][0].title or ""
        rep_title = _PAREN_RE.sub("", rep_raw).strip() or rep_raw or rep_norm

        members_scored: List[Tuple[LibraryTrack, int]] = []
        for m in members:
            t = items[m][0]
            if m == rep:
                score = 100
            elif items[m][1] == rep_norm:
                score = 100
            else:
                score = 95
            members_scored.append((t, score))
        members_scored.sort(key=lambda x: -x[1])

        # Versioned-duplicates exclusion: if every member differs only by a
        # (vN) version tag, the group is intentional versions, not real
        # duplicates -> skip unless the user opted to show them.
        if not show_versioned:
            member_raws = [items[m][0].title or "" for m in members]
            if _is_versioned_group(member_raws):
                continue

        groups.append({
            "representative_title": rep_title,
            "count": len(members_scored),
            "tracks": members_scored,
        })

    groups.sort(key=lambda g: (-g["count"], g["representative_title"].lower()))
    logger.info("Duplicati avanzati: %d gruppi su %d tracce analizzate",
                len(groups), n)
    return groups
