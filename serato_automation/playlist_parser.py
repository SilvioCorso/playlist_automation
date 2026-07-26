# Serato Playlist Automation
# Playlist parser module - supports multiple playlist formats

import re
import csv
import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PlaylistTrack:
    """Represents a single track in a playlist."""
    artist: str = ""
    title: str = ""
    original_line: str = ""
    duration: Optional[str] = None
    bpm: Optional[str] = None
    key: Optional[str] = None
    extra_info: str = ""

    @property
    def display_name(self):
        if self.artist and self.title:
            return f"{self.artist} - {self.title}"
        return self.title or self.original_line

    def __str__(self):
        return self.display_name


class PlaylistParser:
    """Parses playlists from various formats into a unified structure."""

    # Common separators in playlist entries
    SEPARATORS = re.compile(r'\s*[-\u2013\u2014:|/]\s*')

    # Patterns for cleaning text
    CLEANUP_PATTERNS = [
        (re.compile(r'^\d+[\.\)\-\s]+'), ''),        # Leading numbers: "1. ", "1) ", "1 - "
        (re.compile(r'\[.*?\]'), ''),                  # [brackets]
        (re.compile(r'\(.*?(?:remaster|remix|edit|clean|explicit|radio|extended|club|mix|dub|version|live|acoustic|instrumental|original).*?\)', re.IGNORECASE), ''),  # Version info in parens
        (re.compile(r'\{.*?\}'), ''),                  # {braces}
        (re.compile(r'[^\w\s\'\-\.&]'), ' '),      # Special chars to space
        (re.compile(r'\s+'), ' '),                      # Multiple spaces
    ]

    def __init__(self):
        self.tracks: List[PlaylistTrack] = []

    def parse(self, text_or_path: str, is_file=False) -> List[PlaylistTrack]:
        """Parse a playlist from text content or a file path."""
        self.tracks = []

        if is_file and os.path.exists(text_or_path):
            content = self._read_file(text_or_path)
            ext = os.path.splitext(text_or_path)[1].lower()
            if ext == '.csv':
                return self._parse_csv_content(content.strip().split('\n'))
            elif ext == '.m3u' or ext == '.m3u8':
                return self._parse_m3u(content)
        else:
            content = text_or_path

        # Detect format and parse
        lines = [l.strip() for l in content.strip().split('\n') if l.strip()]

        # Check if it looks like CSV data
        if self._looks_like_csv(lines):
            return self._parse_csv_content(lines)

        # Default: parse as text playlist
        return self._parse_text(lines)

    def _read_file(self, filepath: str) -> str:
        """Read file content with encoding detection."""
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
        for enc in encodings:
            try:
                with open(filepath, 'r', encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, IOError):
                continue
        return ""

    def _looks_like_csv(self, lines: List[str]) -> bool:
        """Check if lines look like CSV format.

        Heuristic: real CSV has consistent column counts per delimiter.
        If lines with commas also contain ' - ' separators, it's more likely
        a playlist where commas are part of artist names (e.g. 'Artist1, Artist2 - Title')
        than actual CSV data.
        """
        if not lines:
            return False
        sample = lines[:10]
        n = len(sample)

        # Tab-separated is almost always CSV (not natural text)
        tab_lines = sum(1 for l in sample if '\t' in l)
        if tab_lines >= n * 0.6:
            return True

        # Semicolon check
        semicolon_lines = sum(1 for l in sample if ';' in l)
        if semicolon_lines >= n * 0.6:
            # Verify consistent column count
            counts = [len(l.split(';')) for l in sample if ';' in l]
            if counts and (max(counts) - min(counts)) <= 1 and min(counts) >= 2:
                return True

        # Comma check — but with playlist-aware heuristics
        comma_lines = sum(1 for l in sample if ',' in l)
        if comma_lines >= n * 0.6:
            # If most lines with commas ALSO contain ' - ', it's likely
            # a playlist with "Artist1, Artist2 - Title" format, NOT CSV
            dash_lines = sum(1 for l in sample if ',' in l and ' - ' in l)
            if dash_lines >= comma_lines * 0.6:
                return False  # Playlist, not CSV

            # Check for consistent column counts (real CSV has ~same columns per row)
            counts = [len(l.split(',')) for l in sample if ',' in l]
            if counts and (max(counts) - min(counts)) <= 1 and min(counts) >= 2:
                # Also verify: if every line has exactly 2 comma-separated parts
                # AND they all contain ' - ', it's still a playlist
                if all(' - ' in p for p in [l for l in sample if ',' in l]):
                    return False
                return True

        return False

    def _parse_csv_content(self, lines: List[str]) -> List[PlaylistTrack]:
        """Parse CSV content lines."""
        self.tracks = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # Try multiple delimiters
            for delimiter in [',', ';', '\t']:
                parts = line.split(delimiter)
                if len(parts) >= 2:
                    track = self._create_track_from_parts(parts)
                    if track:
                        # Always preserve the original full line
                        track.original_line = line
                        self.tracks.append(track)
                        break
            else:
                # Single column - try to parse as "Artist - Title"
                track = self._parse_single_line(line)
                if track:
                    self.tracks.append(track)
        return self.tracks

    def _parse_m3u(self, content: str) -> List[PlaylistTrack]:
        """Parse M3U/M3U8 playlist format."""
        self.tracks = []
        lines = content.strip().split('\n')
        current_info = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith('#EXTINF:'):
                # Parse extended info: #EXTINF:duration,Artist - Title
                parts = line[8:]
                if ',' in parts:
                    info_part, name_part = parts.split(',', 1)
                    current_info['name'] = name_part.strip()
                    # Extract duration
                    try:
                        current_info['duration'] = info_part.split(',')[0].strip()
                    except (IndexError, ValueError):
                        pass
            elif not line.startswith('#'):
                track = self._parse_single_line(current_info.get('name', line))
                if track:
                    track.original_line = line
                    track.duration = current_info.get('duration')
                    self.tracks.append(track)
                current_info = {}

        return self.tracks

    def _parse_text(self, lines: List[str]) -> List[PlaylistTrack]:
        """Parse plain text playlist (one track per line)."""
        self.tracks = []
        for line in lines:
            track = self._parse_single_line(line)
            if track:
                track.original_line = line
                self.tracks.append(track)
        return self.tracks

    def _parse_single_line(self, line: str) -> Optional[PlaylistTrack]:
        """Parse a single line into a PlaylistTrack."""
        line = line.strip()
        if not line or line.startswith('#') or len(line) < 3:
            return None

        # Remove common prefixes/suffixes
        line = re.sub(r'^\d+[\.\)\-\s]+', '', line)
        line = line.strip()

        # Try splitting by common separators
        parts = self.SEPARATORS.split(line, maxsplit=1)
        if len(parts) == 2:
            artist = parts[0].strip()
            title = parts[1].strip()
            # Validate: both parts should have content
            if artist and title and len(artist) > 1 and len(title) > 1:
                return PlaylistTrack(artist=artist, title=title, original_line=line)

        # No separator found - treat as title only
        return PlaylistTrack(title=line, original_line=line)

    def _create_track_from_parts(self, parts: List[str]) -> Optional[PlaylistTrack]:
        """Create a PlaylistTrack from CSV/TSV parts."""
        parts = [p.strip().strip('"').strip("'") for p in parts if p.strip()]

        if len(parts) == 1:
            return self._parse_single_line(parts[0])
        elif len(parts) >= 2:
            # Try to identify artist and title columns
            # Common column orders: artist,title OR title,artist
            artist = parts[0]
            title = parts[1]
            extra = ', '.join(parts[2:]) if len(parts) > 2 else ""

            # Check if first column looks like a number (track number)
            if re.match(r'^\d+$', artist):
                if len(parts) >= 3:
                    artist = parts[1]
                    title = parts[2]
                    extra = ', '.join(parts[3:]) if len(parts) > 3 else ""

            return PlaylistTrack(
                artist=artist,
                title=title,
                extra_info=extra
            )
        return None

    def get_tracks(self) -> List[PlaylistTrack]:
        """Return the parsed tracks."""
        return self.tracks
