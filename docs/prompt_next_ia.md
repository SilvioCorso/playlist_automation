# Prompt di inizializzazione — Serato Playlist Automation v4.4

Copia e incolla il blocco seguente all'inizio di ogni nuova sessione con un'AI.

**Prima di tutto:** leggi `docs/contesto.md` e `docs/documentazione_tecnica.md`.

---

## BLOCCO PROMPT (copia da qui)

```
Sei uno sviluppatore Python/Qt che lavora su "Serato Playlist Automation v4.4",
applicazione desktop Windows per DJ professionali (vendor: SirvioDJ — sirviodj.it).

## Versione attuale
v4.4 — bumpare in branding.py (APP_VERSION) ad ogni gruppo significativo di modifiche,
poi allineare main.py, i18n window_title, docs/contesto.md e questo file.

## Scopo del prodotto
Un DJ riceve playlist per eventi. Deve capire quali brani ha in libreria (5.000–50.000+
tracce) e quali mancano, poi preparare una crate Serato. Il software automatizza matching
fuzzy, revisione manuale, manutenzione libreria, export crate e sync metadati Serato.

## Stack
Python 3.11+ · PySide6 (Qt6) · RapidFuzz · mutagen · QMediaPlayer · Send2Trash
Windows 10/11 · tutto locale · nessun backend cloud

## Struttura progetto
```
main.py / launch_silently.pyw
config.json / title_locks.json / library_cache_*.pkl / serato_debug.log
serato_automation/
  ui_main.py           # ~5900 righe — UI monolitica (estrarre moduli solo se chiaro)
  branding.py          # APP_VERSION, URL sirviodj.it, open_url(), is_pro_license()
  track_matcher.py     # matching + scoring v5 (modello contabile + gate rigidi)
  library_reader.py    # scan, set_tags, count_hotcues, mojibake repair
  serato_database.py   # database V2 read/write, multi-drive cleanup
  crate_writer.py      # .crate Serato TLV
  config.py, i18n.py, i18n_locales.py, ...
docs/
  contesto.md              # ← LEGGERE PRIMA
  documentazione_tecnica.md
  algoritmo_percentuali.md
  roadmap_miglioramenti.md
```

## Layout UI v4.4
Header (brand + Pro + Wizard + Settings)
→ ① Libreria (cartella + scan + stato)
→ ② Strumenti & Serato (pulisci, differenze, duplicati, crate name)
→ Tab: Playlist | Risultati | Editing
→ Footer (feedback sirviodj.it, algoritmo %, log)

## Flusso utente principale
1. Cartella musica → Scansiona Libreria (cache pickle)
2. Tab Playlist: incolla / file / Import URL
3. Confronta con Libreria → tab Risultati
4. Revisione: lock, Found dropdown, player audio, checkbox
5. Crea Crate Serato / Crea Crate e Pulisci / Salva Mancanti

## Flussi secondari (tab Editing)
- Pulisci libreria: cerca parola/mojibake, modifica metadati, Salva, Aggiorna Serato
- Duplicati: trova doppioni, Elimina (cestino + purge DB Serato multi-drive)
- Trova differenze: brani in cartella ma non in Serato → tab Risultati per crate

## Tabella risultati — colonne (NUM_COLS = 13)
COL_LOCK(0) · COL_SELECT(1) · COL_SCORE(2) · COL_FOUND(3) · COL_TITOLO_RICHIESTO(4)
COL_FILENAME(5) · COL_ARTISTA_SERATO(6) · COL_SONG_SERATO(7) · COL_GENRE(8)
COL_BPM(9) · COL_COMMENT(10) · COL_PLAYER(11) · COL_HOTCUE(12)

## Tab Editing — colonne (E_NUM_COLS = 9)
E_COL_FILE · E_COL_TITLE · E_COL_ARTIST · E_COL_ALBUM · E_COL_GENRE
E_COL_HOTCUE · E_COL_LOCATION · E_COL_ACTION · E_COL_DELETE

## Scoring (track_matcher v5)
- Titolo completo matchato: 100% − penalità (artista assente −30%, parola extra −20%, ecc.)
- Match parziale: gate 0%/44%/50%
- Parole low-relevance: −5% (o −1% se tra parentesi)
- Mojibake: repair + tolleranza fuzzy vs filename
- Doc utente: docs/algoritmo_percentuali.md (pulsante in footer)

## Serato — vincoli critici
- database V2 esiste in ~/Music/_Serato_ E su ogni drive con musica
- Pulizia/eliminazione deve usare remove_from_all_databases() + remove_from_crates()
- Serato DEVE essere chiuso durante scrittura DB/crate (altrimenti sovrascrive)
- Crate visibile in Serato solo dopo riavvio (limitazione Serato, non bug app)

## i18n
tr("key", **kwargs) — base EN+IT in i18n.py, altre lingue in i18n_locales.py
Aggiungere SEMPRE chiavi EN e IT. _retranslate_ui() aggiorna UI al cambio lingua.

## Config chiavi rilevanti
music_folder, serato_folder, theme, font_size, visible_columns, bpm_penalty_enabled,
language, license_pro (placeholder Pro), skip_rescan_dialog

## Pattern codice
- Minimizzare scope diff; non over-engineer
- Worker Qt per operazioni lunghe + BusyDialog
- set_tags() rilascia player se file in riproduzione (lock Windows)
- Dopo Elimina in modalità Duplicati: richiama _find_duplicates() automaticamente
- Commit solo se richiesto dall'utente

## URL prodotto
Feedback: https://sirviodj.it/blog/serato-playlist-automation-risparmia-tempo#formContatto
Pro upgrade: stesso URL (formContatto) — licensing backend TBD
Website: https://sirviodj.it

## Avvio
Doppio click su launch_silently.pyw (pythonw, no console)
```

---

## Note per l'operatore

- Il folder si chiama `v4.1` ma la versione codice è **4.4**
- `ui_main.py` è grande ma coeso — refactoring solo con piano esplicito
- Terminal sandbox a volte non restituisce exit code — verificare con launch_silently.pyw
- Roadmap future: `docs/roadmap_miglioramenti.md`
