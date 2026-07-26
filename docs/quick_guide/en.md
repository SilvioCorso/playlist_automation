# Serato Playlist Automation — Quick Guide

*Professional DJ tool — by SirvioDJ*

---

## What it does

Turns a **client playlist** (text, file, YouTube/Spotify URL) into a **Serato crate** ready for the event, showing immediately which tracks are in your library and which are missing.

**Typical time saved:** from hours of manual searching to a few minutes of guided review.

---

## 4-step workflow

### ① Set up your library

1. Set the **music folder** (e.g. `F:/`)
2. Click **Scan Library** — the first scan may take a few minutes; later scans use the cache and are much faster
3. Check the green status: *"Library: N tracks"*

### ② Load the client playlist

**Client Playlist** tab:

- **Import from URL** — YouTube or Spotify
- **Load file** — `.txt`, `.csv`, `.m3u`
- Or **paste titles directly** into the text area

Recommended format: `Artist - Title` (one per line).

### ③ Match and review

Click **Match with Library** → **Results** tab:

| Column | Purpose |
|--------|---------|
| **Score %** | How well the found track matches the request |
| **Found** | Menu with alternative candidates when several exist |
| **🔒 Lock** | Lock a match at 100% — it will not change |
| **Player** | Listen without leaving the app |
| **Select** | Choose tracks to include in the crate |

Use **Check all ≥ X%** to bulk-select only matches above a threshold.

### ④ Export

- **Create Serato Crate** — generates the `.crate` file (restart Serato to see it)
- **Save Missing...** — `.txt` list of tracks to buy or verify

---

## Advanced tools

### Library maintenance (Editing tab)

| Feature | When to use it |
|---------|----------------|
| **Clean Library** | Search words in metadata or find mojibake (`PreparÃ3`) |
| **Find differences** | Tracks on disk but not yet in Serato → create import crate |
| **Duplicates** | Same title+artist in multiple copies — delete extras |
| **Update Serato** | Sync edited metadata to the Serato database (Serato closed) |

### Quick Guide button

The **Quick Guide** button always opens this document: full overview of features and workflow.

### Match percentage algorithm

The footer button explains in detail how each score is calculated (penalties, special words, real examples).

---

## Pro tips

- **Score ≥ 50%** is a good starting point for "Check all"; raise to 70–80% for formal events
- Use **Lock** on certain matches before changing candidates on ambiguous rows
- **Duplicate** rows (same file on multiple lines) are highlighted in cyan
- **Full screen** on Results/Editing tabs for long playlists
- After **Delete** on duplicates: close Serato, then reopen — tracks disappear from the library

---

## Support

Feedback and Pro license: [sirviodj.it](https://sirviodj.it/blog/serato-playlist-automation-risparmia-tempo#formContato)
