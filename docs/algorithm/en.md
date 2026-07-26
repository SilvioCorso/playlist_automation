# How the match percentage is calculated

This document explains **step by step** how the software assigns the
percentage (the **Value** column) to each track in the playlist when comparing it
against your music library. At the end you will find several **concrete examples** with
detailed calculations.

> In short: for each requested track the software searches for the best candidate in the
> library using a **cascade of comparison techniques**. Then, if the **requested title
> is fully present** in the track found, it calculates the score with
> an **accounting model**: starting from **100%** and subtracting precise penalties.
> If instead the title is only partially present, **strict gates** come into play that
> heavily limit the score.

---

## 1. Absolute priority: locks (100% guaranteed)

Before any comparison, the software checks whether the track is **locked**.
If it is, the score is a **fixed 100%** and everything else is skipped.

There are two types of lock:

1. **Composer lock** — the `[lock]` tag is written **inside the audio file
   metadata** (composer field). It is the most robust: it survives file moves and
   computer changes.
2. **Title lock** — a *title → file* match that you confirmed,
   saved in the `title_locks.json` file.

In both cases it is enough for the requested title to be **contained** in the title of the
locked track. To remove the 100%, click the lock icon on the row to
unlock it: the score will be recalculated normally.

---

## 2. The search cascade

If the track is **not** locked, the software searches for the best candidate by trying
these techniques in order. **It stops at the first one that yields a valid result.**

| # | Pass | What it does |
|---|------|--------------|
| 1 | **Exact** | *Normalized* artist+title are identical |
| 2 | **Word coverage** | All words from the request are present in the track |
| 3 | **Composite** | Weighted similarity: **artist 30%** + **title 70%** |
| 4 | **Fuzzy** | "Fuzzy" similarity tolerant of order and variants |
| 5 | **Title partial** | Partial similarity on the title only |
| 6 | **Filename** | Comparison with the **file name** (useful when tags are empty) |

### The "Artist - Title" structure

If the request uses the **`Artist - Title`** structure (with the hyphen, or
`:`, `|`, `/`), the software separates the two elements and uses them distinctly: it knows
which is the artist and which is the title. This makes the calculation more accurate (see the
accounting model, §3).

### What "normalization" means

Before comparing, texts are cleaned so that irrelevant differences
do not count:

- everything in **lowercase**;
- **encoding repair (mojibake)**: text saved with double UTF-8
  encoding is restored, so `PreparÃ³` is read as `Preparó`;
- **accents** removed (`Beyoncé` → `beyonce`, `Preparó` → `preparo`);
- **underscores treated as spaces** (`Bellini_Music_Official` →
  `bellini music official`);
- **punctuation** converted to spaces;
- **content in round parentheses removed** for comparison purposes — e.g.
  `Titanium (Extended Mix)` → `titanium` (but words in parentheses are then
  evaluated separately, see §4);
- leading articles (`the`, `a`, `an`) and **4-digit years** removed.

Thanks to mojibake repair and accent removal, `Preparó` and
`PreparÃ³` are considered **the same word**.

### Tolerance for corrupted text (mojibake) + filename verification

Sometimes a tag is corrupted in a way that is **not automatically reconstructible** (for
example `PreparÃ3`, with a digit instead of the accent). In these cases the
software does **not** immediately count that word as "different": if the **Serato
title** contains suspicious symbols (`Ã`/`Â`), it performs a **filename
comparison**. If the correct "clean" word is present in the filename (e.g. `preparo`), the
software understands that the corrupted token is actually the same word and **does not
apply any penalty**. The filename therefore acts as a "source of truth".

---

## 3. The two scoring regimes

After choosing the candidate, the software checks whether **all words of the
requested title** appear **in the same order** (as a subsequence) in the
**Serato title** or in the **filename**.

- **Title fully present** → the **accounting model** is used (§4):
  base **100%** minus precise penalties.
- **Title only partial** → **strict gates** are used (§5): the score
  is limited to low values (0%, 44% or 50%).

---

## 4. The accounting model (title fully found)

Starting from **100%**, the penalties below are subtracted. **All penalties
add up.**

| Situation | Effect |
|-----------|--------|
| The **artist** is in the request but **does not appear in any column** of the track found (Artist, Song, Filename) | **70% cap** |
| **Extra TITLE word** in the track found (real word, not requested, not low relevance) | **−20% each** |
| **Extra ARTIST word** in the track found (real word, not requested) | **−5% total** |
| **Low-relevance word** outside parentheses (remix, official, video, music…) not requested | **−5% total** |
| Any word **in round parentheses** (descriptor or word not requested) | **−1% total** |
| A word from the **requested title** found **only in the filename** (not in Song or Artist) | **−1%** |

Important notes:

- An **extra title word** (e.g. the request is *"Everything"* but the track
  found is *"Everything **she wants**"*) indicates that the title is effectively different:
  for this reason it weighs heavily (**−20% per word**).
- An **extra artist word** weighs little (**−5% total**), because it is often just
  the name of whoever uploaded the track or a variant (e.g. `ImagineDragons` written
  all together, or a channel like `After Party82`).
- Words **in round parentheses** have even lower relevance: whatever
  is inside costs at most **−1% total**.
- The **artist presence** check is "tolerant" (`ImagineDragons`
  satisfies `imagine`), while the count of **extra words** is "exact"
  (so `ImagineDragons` together still counts as an extra artist word).

---

## 5. Strict gates (title only partial)

When the requested title is **not** fully present in order, the match is
unreliable and these limits apply:

- **Missing words**: if a significant word from the request does not appear in the
  track → **max 50%**.
- **Title presence**: if the title words do not appear in any field →
  **max 45%**.
- **Title in order**: the title words must appear in the same order
  in the filename or Serato title:
  - no words found → **0%** (row treated as *missing*);
  - found but partial / wrong order → **max 44%**.
- **Containment bonus**: if the requested title is nevertheless contained in the one
  found, the score rises to at least **62%**.
- **PSYTRANCE adjustment** and **BPM penalty** (the latter optional) may
  intervene as refinements.

---

## 6. "Low-relevance" words

These are version/format/media descriptors that **do not really change the track**.
When they appear in the track found but not in the request, they do not crash the
score: they cost only **−5% total** (outside parentheses) or **−1% total** (if
inside parentheses):

`remix`, `mashup`, `dub`, `vip`, `flip`, `bootleg`, `rework`, `discomix`,
`mashboot`, `remake`, `revibe`, `reloaded`, `original`, `extended`, `edit`,
`mix`, `version`, `radio`, `club`, `clean`, `dirty`, `official`, `oficial`,
`ufficiale`, `music`, `video`, `audio`, `mv`, `clip`, `lyric`, `lyrics`,
`visualizer`, and bitrate abbreviations such as `128kbit_AAC`, `320 kbps`.

---

## 7. Annotated examples (with calculation)

All examples below fall under the **accounting model** (the requested title
is fully present in the track found).

| Request | Track found (Song / Artist) | Value | Calculation |
|---------|----------------------------|-------|-------------|
| `Michael Bublé - Everything` | *Everything she wants (…Bootleg Remix)* / Wham | **~29%** | Artist "Michael Bublé" **absent everywhere** → **70%** cap; *"she"* and *"wants"* are 2 extra title words → **−40%** (−20% each); content in parentheses → **−1%** |
| `Bellini - Carnaval (Original Version)` | *Bellini - Carnaval (Original Version)* / After Party82 | **94%** | Artist "bellini" present in Song; extra artist "After Party82" → **−5%**; `(Original Version)` in parentheses → **−1%** |
| `Bellini - Samba De Janeiro` | *Bellini - Samba De Janeiro* / Bellini_Music_Official | **95%** | Identical title; `music`/`official` are low relevance outside parentheses → **−5%** |
| `Imagine Dragons - On Top Of The World` | *…On Top Of The World (Official Music Video)* / ImagineDragons | **94%** | Artist "ImagineDragons" (joined) counts as extra artist → **−5%**; `(Official Music Video)` in parentheses → **−1%** |
| `KING ÁFRICA "EL CAMALEÓN"` | *KING ÁFRICA "EL CAMALEÓN"* / YouMoreTv - Espectáculo | **95%** | Identical title; extra artist "YouMoreTv Espectáculo" → **−5%** |
| `Ozuna - Se Preparó (Video Oficial) \| Odisea` | Song: *Ozuna - Se PreparÃ3…* (corrupted) · Filename: *Ozuna - Se Preparó…* (clean) | **99%** | Serato title is corrupted (`PreparÃ3`), but the clean word `preparo` is in the filename → the corrupted token is recognized and **not penalized**; only `(Video Oficial)` in parentheses remains → **−1%** |
| `Ricky Martin - La Mordidita ft. Yotuel` | *Ricky Martin - La Mordidita* / Ricky Martin | **99%** | All title words are present; *"yotuel"* is present **only in the filename** → **−1%** |

---

## 8. From score to color and label

The final score determines the **color** of the row and the confidence level:

| Score | Confidence | Row color (light theme) |
|-------|------------|-------------------------|
| 95–100% | Exact | solid green |
| 75–94% | High | green |
| 55–74% | Medium | orange/yellow |
| 1–54% | Low | light red |
| 0% | Missing | pink/red (treated as not found) |

Special colors:

- **Cyan/light blue**: two or more playlist rows point to the **same file**
  (possible duplicate in the request). If you change version from the **Found** column
  menu and the duplicates disappear, the color returns to normal.
- **▼ with number** in the **Found** column: there are multiple candidates above the
  threshold — click to choose the correct version.

---

## 9. Flow summary

```
Requested track
   │
   ├─ Locked (composer/title lock)? ── yes ─▶ 100%
   │                                    no
   ▼
Cascade: Exact ▶ Word coverage ▶ Composite ▶ Fuzzy ▶ Title partial ▶ Filename
   │
   ▼
Is the requested title fully present (in order) in Song or Filename?
   │
   ├─ YES ─▶ Accounting model: 100%
   │          − 30% cap if artist absent (base drops to 70%)
   │          − 20% for each extra TITLE word
   │          − 5%  if there is an extra ARTIST word
   │          − 5%  low-relevance word outside parentheses
   │          − 1%  something in round parentheses
   │          − 1%  title word found only in filename
   │
   └─ NO ─▶ Strict gates:
              missing words → max 50%
              title presence → max 45%
              title in order → 0% or max 44%
              (+ containment bonus, PSYTRANCE, BPM)
   ▼
Final score (0–100%) ▶ color + confidence label
```

---

*Document generated for Serato Playlist Automation. Thresholds and word
lists live in `serato_automation/track_matcher.py`.*
