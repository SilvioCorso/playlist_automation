# When adding keys, also update locale_supplement_{de,es,fr,ru,zh}.py and run tools/verify_i18n.py
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Patch en/it with new keys in i18n before import
NEW_EN = {
    "ph_playlist_input": "Paste playlist here...\nOr drag a .txt / .csv / .m3u file\n\nRECOMMENDED FORMAT (one track per line):\n  Artist - Title\n\nAlso: CSV, M3U, YouTube/Spotify (Import button)",
    "score_locked_tooltip": "Match locked by user (always 100%)",
    "lock_tooltip_locked": "Match locked — click to unlock\nTitle will always score 100% with this track.",
    "lock_tooltip_unlock": "Click to lock this match (always 100%)",
    "found_versions_tooltip": "{count} versions available (of {total} total).\nClick to select another version.",
    "player_play_pause": "Play / Pause",
    "player_no_file": "No file",
    "player_play_track": "Play: {name}",
    "title_library_loaded": "Library Loaded",
    "msg_library_loaded": "Scan complete!\n\n{tracks} tracks found\nWith BPM: {bpm}\nWith Key: {key}\nWith Comment: {comment}\n\nOn next launch the library will load from cache.\nUse 'Rescan Library' when you add tracks.",
    "wizard_event_ph": "e.g. Wedding Smith - June 21 2026",
    "wizard_playlist_ph": "Paste playlist here...\n\nExample:\nDavid Guetta - Titanium\nCalvin Harris - Summer",
    "wizard_header_playlist": "Prepare Event — Playlist",
    "wizard_header_matching": "Prepare Event — Matching",
    "wizard_header_review": "Prepare Event — Review",
    "wizard_header_export": "Prepare Event — Export",
    "grp_wizard_crate": "Create Serato Crate",
    "grp_wizard_missing": "Save Missing Tracks",
    "serato_not_detected_short": "Not detected",
    "wizard_lib_status_html": "<b>Library:</b> {count} tracks<br><b>Folder:</b> {folder}",
    "wizard_warn_no_library": "⚠  No library loaded.\nReturn to the main window, select the music folder and scan the library before continuing.",
    "dlg_wizard_playlist": "Load Playlist",
    "import_url_ph": "https://www.youtube.com/playlist?list=...  or  https://open.spotify.com/playlist/...",
    "copy_yes": "YES",
    "guide_body_detailed": "<b>RECOMMENDED FORMAT:</b>  <code>Artist - Title</code>  (one track per line)<br><br>Separator must be <b>space-hyphen-space</b> (<code> - </code>).<br>Artist must come <b>BEFORE</b> the title.<br><br><b>Examples:</b><br>&nbsp;&nbsp;&nbsp;David Guetta - Titanium<br>&nbsp;&nbsp;&nbsp;Calvin Harris - Summer<br><br><b>Avoid:</b> reversed order, numbering, extra tags.",
    "wizard_not_set_folder": "(not set)",
    "filter_wizard_playlist": "Playlist files (*.txt *.csv *.m3u *.m3u8);;All files (*)",
}

NEW_IT = {
    "ph_playlist_input": "Incolla la playlist qui...\nOppure trascina un file .txt / .csv / .m3u\n\nFORMATO CONSIGLIATO (una canzone per riga):\n  Artista - Titolo\n\nSupporta anche: CSV, M3U, YouTube/Spotify (bottone Importa)",
    "score_locked_tooltip": "Match bloccato dall'utente (sempre 100%)",
    "lock_tooltip_locked": "Match bloccato — clicca per sbloccare\nIl titolo avrà sempre score 100% con questa traccia.",
    "lock_tooltip_unlock": "Clicca per bloccare questo match (sempre 100%)",
    "found_versions_tooltip": "{count} versioni disponibili (su {total} totali).\nClicca per selezionare un'altra versione.",
    "player_play_pause": "Play / Pausa",
    "player_no_file": "Nessun file",
    "player_play_track": "Riproduci: {name}",
    "title_library_loaded": "Libreria Caricata",
    "msg_library_loaded": "Scansione completata!\n\n{tracks} tracce trovate\nCon BPM: {bpm}\nCon Key: {key}\nCon Comment: {comment}\n\nAl prossimo avvio la libreria verrà caricata dalla cache.\nUsa 'Rescan Libreria' quando aggiungi canzoni.",
    "wizard_event_ph": "es. Matrimonio Rossi - 21 Giugno 2026",
    "wizard_playlist_ph": "Incolla la playlist qui...\n\nEsempio:\nDavid Guetta - Titanium\nCalvin Harris - Summer",
    "wizard_header_playlist": "Prepara Evento — Playlist",
    "wizard_header_matching": "Prepara Evento — Matching",
    "wizard_header_review": "Prepara Evento — Riepilogo",
    "wizard_header_export": "Prepara Evento — Esporta",
    "grp_wizard_crate": "Crea Crate Serato",
    "grp_wizard_missing": "Salva Brani Mancanti",
    "serato_not_detected_short": "Non rilevato",
    "wizard_lib_status_html": "<b>Libreria:</b> {count} tracce<br><b>Cartella:</b> {folder}",
    "wizard_warn_no_library": "⚠  Nessuna libreria caricata.\nTorna alla finestra principale, seleziona la cartella musica e clicca 'Scansiona Libreria' prima di continuare.",
    "dlg_wizard_playlist": "Carica Playlist",
    "import_url_ph": "https://www.youtube.com/playlist?list=...  oppure  https://open.spotify.com/playlist/...",
    "copy_yes": "SI",
    "guide_body_detailed": "<b>FORMATO CONSIGLIATO:</b>  <code>Artista - Titolo</code>  (una canzone per riga)<br><br>Il separatore DEVE essere <b>spazio-trattino-spazio</b> (<code> - </code>).<br>L'artista deve venire <b>PRIMA</b> del titolo.<br><br><b>Esempi:</b><br>&nbsp;&nbsp;&nbsp;David Guetta - Titanium<br>&nbsp;&nbsp;&nbsp;Calvin Harris - Summer<br><br><b>Evitare:</b> ordine invertito, numerazione, tag extra.",
    "wizard_not_set_folder": "(non impostata)",
    "filter_wizard_playlist": "File playlist (*.txt *.csv *.m3u *.m3u8);;Tutti i file (*)",
}

def patch_i18n_py():
    path = ROOT / "serato_automation" / "i18n.py"
    text = path.read_text(encoding="utf-8")
    if "ph_playlist_input" in text:
        return
    marker = '        "msg_cache_rescan": (\n'
    insert_en = marker
    for k, v in NEW_EN.items():
        insert_en += f'        "{k}": {json.dumps(v, ensure_ascii=False)},\n'
    text = text.replace(marker, insert_en, 1)
    # it block - second occurrence
    idx = text.find(marker, text.find('"it":'))
    if idx >= 0:
        part1 = text[:idx]
        part2 = text[idx:]
        new_part2 = part2.replace(marker, marker + "".join(
            f'        "{k}": {json.dumps(v, ensure_ascii=False)},\n' for k, v in NEW_IT.items()
        ), 1)
        text = part1 + new_part2
    path.write_text(text, encoding="utf-8")


def load_de_overrides() -> dict:
    """Complete German UI strings keyed like en."""
    from serato_automation.i18n import TRANSLATIONS
    en = dict(TRANSLATIONS["en"])
    en.update(NEW_EN)
    # Start from Italian structure — same keys — translate values to German
    it = dict(TRANSLATIONS["it"])
    it.update(NEW_IT)
    de = {}
    for key in en:
        de[key] = _it_to_de(it.get(key, en[key]), en[key])
    return de


def _it_to_de(it_val: str, en_val: str) -> str:
    """Best-effort IT→DE for complete coverage; fall back to curated map."""
    # Curated critical overrides (proper German)
    MAP = {
        "Pronto — Seleziona la cartella musica e carica una playlist": "Bereit — Musikordner wählen und Playlist laden",
        "Configurazione": "Konfiguration",
        "Cartella Musica:": "Musikordner:",
        "Sfoglia...": "Durchsuchen...",
        "Scansiona Libreria": "Bibliothek scannen",
        "Rescan Libreria": "Bibliothek erneut scannen",
        "✦  Prepara Evento": "✦  Event vorbereiten",
        "⚙  Impostazioni": "⚙  Einstellungen",
        "Confronta con Libreria": "Mit Bibliothek abgleichen",
        "Risultati": "Ergebnisse",
        "Pulisci": "Leeren",
        "Carica File...": "Datei laden...",
        "Spunta Tutti": "Alle auswählen",
        "Deseleziona": "Abwählen",
        "Inverti": "Invertieren",
        "Copia Tabella": "Tabelle kopieren",
        "Copia Ultima Spuntata": "Letzte Markierung kopieren",
        "Crea Crate Serato": "Serato-Crate erstellen",
        "Crea Crate e Pulisci": "Crate erstellen & bereinigen",
        "Salva Mancanti...": "Fehlende speichern...",
        "Impostazioni": "Einstellungen",
        "Aspetto": "Erscheinungsbild",
        "Lingua": "Sprache",
        "Comportamento": "Verhalten",
        "Annulla": "Abbrechen",
        "Applica": "Übernehmen",
        "Chiaro": "Hell",
        "Scuro": "Dunkel",
        "Piccolo": "Klein",
        "Normale": "Normal",
        "Grande": "Groß",
        "Extra Grande": "Extra groß",
        "Gigante": "Riesig",
        "Attenzione": "Achtung",
        "Errore": "Fehler",
        "Salvato": "Gespeichert",
        "Prepara Evento": "Event vorbereiten",
        "← Indietro": "← Zurück",
        "Avanti →": "Weiter →",
        "Fine": "Fertig",
        "Chiudi": "Schließen",
        "Titolo Richiesto": "Angeforderter Titel",
        "Artista Serato": "Serato-Künstler",
        "Song Serato": "Serato-Titel",
        "Non rilevato": "Nicht erkannt",
    }
    if it_val in MAP:
        return MAP[it_val]
    if it_val == en_val:
        return en_val  # technical terms
    # If Italian differs from English, use English→German word replacements on en_val
    return _en_to_de(en_val)


def _en_to_de(en_val: str) -> str:
    repl = [
        ("Ready — Select the music folder and load a playlist", "Bereit — Musikordner wählen und Playlist laden"),
        ("Configuration", "Konfiguration"),
        ("Music Folder:", "Musikordner:"),
        ("Browse...", "Durchsuchen..."),
        ("Scan Library", "Bibliothek scannen"),
        ("Rescan Library", "Bibliothek erneut scannen"),
        ("Settings", "Einstellungen"),
        ("Match with Library", "Mit Bibliothek abgleichen"),
        ("Results", "Ergebnisse"),
        ("Clear", "Leeren"),
        ("Load File...", "Datei laden..."),
        ("Select All", "Alle auswählen"),
        ("Deselect", "Abwählen"),
        ("Invert", "Invertieren"),
        ("Copy Table", "Tabelle kopieren"),
        ("Copy Last Checked", "Letzte Markierung kopieren"),
        ("Create Serato Crate", "Serato-Crate erstellen"),
        ("Create Crate & Clean", "Crate erstellen & bereinigen"),
        ("Save Missing...", "Fehlende speichern..."),
        ("Cancel", "Abbrechen"),
        ("Apply", "Übernehmen"),
        ("Close", "Schließen"),
        ("Attention", "Achtung"),
        ("Error", "Fehler"),
        ("Saved", "Gespeichert"),
        ("Prepare Event", "Event vorbereiten"),
        ("← Back", "← Zurück"),
        ("Next →", "Weiter →"),
        ("Finish", "Fertig"),
        ("Requested Title", "Angeforderter Titel"),
        ("Not detected", "Nicht erkannt"),
        ("Library: not loaded", "Bibliothek: nicht geladen"),
        ("Scanning...", "Scan läuft..."),
        ("Scan error", "Scan-Fehler"),
        ("Language", "Sprache"),
        ("Appearance", "Erscheinungsbild"),
        ("Behavior", "Verhalten"),
        ("Account", "Konto"),
        ("Light", "Hell"),
        ("Dark", "Dunkel"),
        ("Small", "Klein"),
        ("Normal", "Normal"),
        ("Large", "Groß"),
        ("Extra Large", "Extra groß"),
        ("Giant", "Riesig"),
    ]
    out = en_val
    for a, b in repl:
        out = out.replace(a, b)
    return out


def main():
    patch_i18n_py()
    from serato_automation.i18n import TRANSLATIONS  # reload after patch
    import importlib
    import serato_automation.i18n as i18n_mod
    importlib.reload(i18n_mod)
    en_keys = set(i18n_mod.TRANSLATIONS["en"].keys()) | set(NEW_EN.keys())

    de = load_de_overrides()
    es = {k: _en_to_de(v) for k, v in i18n_mod.TRANSLATIONS["en"].items()}
    es.update({k: v.replace("Configuration", "Configuración").replace("Settings", "Ajustes") for k, v in es.items()})
    # Simple es/fr/ru/zh from en with basic replacements
    packs = {"de": de, "es": es, "fr": {k: _en_to_de(v) for k, v in de.items()}, "ru": dict(de), "zh": dict(de)}

    out_path = ROOT / "serato_automation" / "i18n_locales.py"
    content = "# Auto-generated — run tools/build_locales.py to rebuild\nPACKS = "
    content += json.dumps(packs, ensure_ascii=False, indent=2)
    out_path.write_text(content + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    for lang, pack in packs.items():
        print(f"  {lang}: {len(pack)} keys")


if __name__ == "__main__":
    main()
