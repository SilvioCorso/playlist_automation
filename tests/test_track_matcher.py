"""normalize_string + match_playlist core scenarios.

These cover the audit's 'track_matcher has 0 tests' gap with the highest-value
cases: mojibake repair, accent folding, underscore handling, exact match, and
missing-track detection. No Qt / no Serato required.
"""
from serato_automation.library_reader import LibraryTrack, normalize_string, repair_mojibake
from serato_automation.playlist_parser import PlaylistTrack
from serato_automation.track_matcher import TrackMatcher


def test_normalize_removes_accents():
    assert normalize_string("Preparación") == normalize_string("Preparacion")
    assert normalize_string("café") == normalize_string("cafe")


def test_normalize_underscore_to_space():
    assert normalize_string("Bellini_Music") == normalize_string("Bellini Music")


def test_repair_mojibake_double_encoded():
    # 'PreparÃ³' (cp1252 mis-decoded UTF-8) -> 'Preparó'
    assert repair_mojibake("PreparÃ³") == "Preparó"


def test_exact_match_scores_high():
    lib = [LibraryTrack(title="Titanium", artist="David Guetta", filepath="/m/a.mp3")]
    matcher = TrackMatcher(lib)
    pl = [PlaylistTrack(artist="David Guetta", title="Titanium")]
    results = matcher.match_playlist(pl)
    assert len(results) == 1
    r = results[0]
    assert r.is_effectively_matched
    assert r.score >= 85


def test_missing_track_not_effectively_matched():
    lib = [LibraryTrack(title="Titanium", artist="David Guetta", filepath="/m/a.mp3")]
    matcher = TrackMatcher(lib)
    pl = [PlaylistTrack(artist="Nobody", title="NoSuchSong")]
    results = matcher.match_playlist(pl)
    assert len(results) == 1
    # A track that doesn't exist in the library must not be "matched".
    assert not results[0].is_effectively_matched or results[0].score == 0


def test_match_playlist_progress_callback_and_cancel():
    lib = [LibraryTrack(title="Levels", artist="Avicii", filepath="/m/b.mp3")]
    matcher = TrackMatcher(lib)
    pl = [PlaylistTrack(artist="Avicii", title="Levels"),
          PlaylistTrack(artist="X", title="Y")]
    seen = []
    matcher.match_playlist(pl, progress_callback=lambda c, t: seen.append((c, t)))
    assert seen  # progress callback was invoked
    # Cancel after first track — second must not be processed.
    calls = {"n": 0}

    def cancel():
        calls["n"] += 1
        return calls["n"] > 1  # cancel before the 2nd track

    results = matcher.match_playlist(pl, cancel_check=cancel)
    assert len(results) < len(pl)  # interrupted before completing
