"""PlaylistParser — text / CSV / M3U parsing."""
import os

from serato_automation.playlist_parser import PlaylistParser, PlaylistTrack


def test_parse_text_artist_dash_title():
    text = "David Guetta - Titanium\nCalvin Harris - Summer\nAvicii - Levels"
    tracks = PlaylistParser().parse(text)
    assert len(tracks) == 3
    assert tracks[0].artist == "David Guetta"
    assert tracks[0].title == "Titanium"
    assert tracks[2].artist == "Avicii"
    assert tracks[2].title == "Levels"


def test_parse_strips_leading_numbers():
    text = "1. David Guetta - Titanium\n2) Avicii - Levels\n3 - Calvin Harris - Summer"
    tracks = PlaylistParser().parse(text)
    assert len(tracks) == 3
    assert tracks[0].artist == "David Guetta"
    assert tracks[2].title == "Summer"


def test_parse_alternate_separators():
    # colon also splits artist/title
    tracks = PlaylistParser().parse("Beatles : Yesterday")
    assert tracks[0].title == "Yesterday"
    # A slash is a listed separator, so 'AC/DC - Thunderstruck' splits at the
    # first '/'. This is a known parser limitation (artist names containing
    # slashes are ambiguous); the test documents the actual behaviour.
    tracks = PlaylistParser().parse("AC/DC - Thunderstruck")
    assert tracks[0].artist == "AC"
    assert "Thunderstruck" in tracks[0].title


def test_parse_csv_file(tmp_path):
    # Headerless CSV (the parser does not skip a header row).
    csv = "David Guetta,Titanium\nAvicii,Levels\n"
    p = tmp_path / "pl.csv"
    p.write_text(csv, encoding="utf-8")
    tracks = PlaylistParser().parse(str(p), is_file=True)
    assert len(tracks) == 2
    assert tracks[0].artist == "David Guetta"
    assert tracks[0].title == "Titanium"


def test_parse_m3u_file(tmp_path):
    m3u = "#EXTM3U\n#EXTINF:200,David Guetta - Titanium\n/Music/a.mp3\n#EXTINF:180,Avicii - Levels\n/Music/b.mp3\n"
    p = tmp_path / "pl.m3u"
    p.write_text(m3u, encoding="utf-8")
    tracks = PlaylistParser().parse(str(p), is_file=True)
    assert len(tracks) == 2
    assert tracks[0].title == "Titanium"


def test_parse_empty_returns_empty():
    assert PlaylistParser().parse("") == []
    assert PlaylistParser().parse("   \n\n  ") == []
