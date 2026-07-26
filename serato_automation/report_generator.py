# Serato Playlist Automation
# Report generator module - generates missing tracks report

import os
from datetime import datetime
from typing import List, Optional

from .track_matcher import MatchResult


class ReportGenerator:
    """Generates reports for missing tracks and matching summaries."""

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.path.expanduser("~")

    def generate_missing_tracks_report(self, results: List[MatchResult],
                                       event_name: str = "Evento") -> str:
        """
        Generate a .txt file with all missing and excluded tracks.
        Results may include both truly missing (not in library) and
        excluded matched tracks (unchecked by user).
        Returns the path to the generated file.
        """
        truly_missing = [r for r in results if not r.is_effectively_matched]
        excluded_matched = [r for r in results if r.is_effectively_matched and r.library_track]

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        filename = f"Brani_Mancanti_{event_name}_{timestamp}.txt"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"=== BRANI MANCANTI - {event_name} ===\n")
            f.write(f"Generato: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
            f.write(f"Totale brani mancanti: {len(truly_missing)}\n")
            f.write(f"Tracce escluse dalla crate: {len(excluded_matched)}\n")
            f.write("=" * 50 + "\n\n")

            if truly_missing:
                f.write("--- BRANI NON TROVATI NELLA LIBRERIA ---\n\n")
                for i, r in enumerate(truly_missing, 1):
                    track = r.playlist_track
                    if track.artist:
                        f.write(f"{i}. {track.artist} - {track.title}\n")
                    else:
                        f.write(f"{i}. {track.title}\n")
                    if track.original_line and track.original_line != track.display_name:
                        f.write(f"   Richiesto: {track.original_line}\n")
                f.write("\n")

            if excluded_matched:
                f.write("--- TRACCE TROVATE MA ESCLUSE DALLA CRATE ---\n\n")
                for i, r in enumerate(excluded_matched, 1):
                    pt = r.playlist_track
                    lt = r.library_track
                    f.write(f"{i}. [{r.score}%] {pt.display_name}\n")
                    f.write(f"   File: {os.path.basename(lt.filepath)}\n")
                f.write("\n")

            f.write(f"{'=' * 50}\n")
            f.write(f"Totale: {len(truly_missing)} mancanti + {len(excluded_matched)} escluse = {len(results)}\n")

        return filepath

    def generate_summary_report(self, results: List[MatchResult],
                                 event_name: str = "Evento",
                                 crate_path: Optional[str] = None) -> str:
        """
        Generate a comprehensive summary report (matched + missing).
        Returns the path to the generated file.
        """
        matched = [r for r in results if r.is_effectively_matched]
        missing = [r for r in results if not r.is_effectively_matched]

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        filename = f"Report_Completo_{event_name}_{timestamp}.txt"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"=== REPORT COMPLETO - {event_name} ===\n")
            f.write(f"Generato: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
            f.write(f"Totale playlist: {len(results)} brani\n")
            f.write(f"Trovati nella libreria: {len(matched)}\n")
            f.write(f"Mancanti: {len(missing)}\n")
            if crate_path:
                f.write(f"Crate Serato: {crate_path}\n")
            f.write("=" * 50 + "\n\n")

            # Matched tracks
            f.write("--- BRANI TROVATI ---\n\n")
            for i, r in enumerate(matched, 1):
                pt = r.playlist_track
                lt = r.library_track
                f.write(f"{i}. [{r.score}%] {pt.display_name}\n")
                f.write(f"   -> File: {os.path.basename(lt.filepath)}\n")
                bpm_key_line = ""
                if lt.bpm:
                    bpm_key_line = f"   -> BPM: {lt.bpm}"
                if lt.key:
                    bpm_key_line = bpm_key_line + f"  Key: {lt.key}" if bpm_key_line else f"   -> Key: {lt.key}"
                if bpm_key_line:
                    f.write(bpm_key_line + "\n")

            f.write(f"\n{'-' * 40}\n\n")

            # Missing tracks
            f.write("--- BRANI MANCANTI ---\n\n")
            for i, r in enumerate(missing, 1):
                track = r.playlist_track
                if track.artist:
                    f.write(f"{i}. {track.artist} - {track.title}\n")
                else:
                    f.write(f"{i}. {track.title}\n")

            f.write(f"\n{'=' * 50}\n")
            f.write(f"Fine report\n")

        return filepath

    def generate_search_list(self, results: List[MatchResult],
                             event_name: str = "Evento") -> str:
        """
        Generate a clean search-friendly list for Beatport/juno/Traxsource.
        One line per track, optimized for copy-paste into search fields.
        """
        missing = [r for r in results if not r.is_effectively_matched]

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        filename = f"Da_Cercare_{event_name}_{timestamp}.txt"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            for r in missing:
                track = r.playlist_track
                if track.artist:
                    f.write(f"{track.artist} - {track.title}\n")
                else:
                    f.write(f"{track.title}\n")

        return filepath
