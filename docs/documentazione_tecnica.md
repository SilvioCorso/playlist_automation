# Documentazione tecnica — Serato Playlist Automation v4.4

*Aggiornata: luglio 2026. Per il bootstrap rapido leggere anche `contesto.md`.*

---

## 1. Panoramica

| Campo | Valore |
|-------|--------|
| **Prodotto** | Serato Playlist Automation |
| **Versione** | 4.4 |
| **Vendor** | SirvioDJ — https://sirviodj.it |
| **Piattaforma** | Windows 10/11 (primaria), macOS parziale |
| **Runtime** | Python 3.11+, PySide6 6.x |
| **Architettura** | Desktop monolitico locale, nessun backend cloud |

### Scopo

Automatizzare il flusso del DJ professionista:

1. Riceve una playlist cliente (testo, file, URL YouTube/Spotify)
2. La confronta con la libreria locale (5.000–50.000+ tracce)
3. Presenta risultati con score %, candidati alternativi, player integrato
4. Esporta crate Serato (`.crate`) e report brani mancanti

---

## 2. Struttura del repository

```
Serato_Playlist_Automation_v4.1/
├── main.py / launch_silently.pyw    # Entry point
├── config.json                      # Preferenze utente (runtime)
├── title_locks.json                 # Lock titolo→filepath (backup JSON)
├── library_cache_<hash>.pkl         # Cache scan libreria
├── serato_debug.log                 # Log sessione
│
├── serato_automation/
│   ├── ui_main.py          (~5.900 righe) UI completa PySide6
│   ├── branding.py         Versione, URL, open_url, license check
│   ├── track_matcher.py    Engine matching fuzzy + scoring v5
│   ├── library_reader.py   Scan cartella, mutagen, hotcue, set_tags
│   ├── serato_database.py  Read/write database V2 Serato (multi-drive)
│   ├── crate_writer.py     Scrittura .crate binario TLV
│   ├── playlist_parser.py  Parser txt/csv/m3u
│   ├── playlist_importer.py Scraping URL
│   ├── report_generator.py Report TXT mancanti
│   ├── config.py           DEFAULT_CONFIG + load/save
│   ├── i18n.py             tr(), EN + IT inline
│   ├── i18n_locales.py     DE/ES/FR/RU/ZH
│   └── log_handler.py      Logging file + console
│
└── docs/                   Documentazione (questo file, contesto, prompt IA, roadmap)
```

---

## 3. Layout UI (v4.4)

```
┌─ Header bar ─────────────────────────────────────────────────────┐
│  Serato Playlist Automation  v4.4          [Pro] [Wizard] [⚙]   │
│  Tagline professionale                                            │
├─ ① Libreria ─────────────────────────────────────────────────────┤
│  Cartella musica [________] [Sfoglia] [Scansiona] │ stato lib.  │
├─ ② Strumenti & Serato ───────────────────────────────────────────┤
│  Pulisci │ Differenze │ Duplicati │ Serato OK │ Crate name       │
├─ Tab: Playlist │ Risultati │ Editing ────────────────────────────┤
│  (contenuto principale)                                           │
├─ Footer ─────────────────────────────────────────────────────────┤
│  [Feedback] [sirviodj.it]     by SirvioDJ     [Algoritmo] [Log]  │
└──────────────────────────────────────────────────────────────────┘
 Status bar
```

### Tab principali

| Tab | Contenuto | Abilitazione |
|-----|-----------|--------------|
| **Playlist** | Input testo/file, Import URL, Match | Sempre |
| **Risultati** | Tabella match, selezione, crate export | Dopo matching |
| **Editing** | Metadati editabili, duplicati, pulizia | Dopo ricerca libreria |

---

## 4. Moduli core — dettaglio

### 4.1 `track_matcher.py`

- **Input:** `List[PlaylistTrack]`, `List[LibraryTrack]`
- **Output:** `List[MatchResult]` con candidati ordinati per score
- **Algoritmo:** Multi-pass RapidFuzz + modello contabile a due regimi
  - Titolo completamente matchato → 100% − penalità esplicite
  - Match parziale → gate rigidi (0%, 44%, 50%)
- **Penalità principali:** artista assente −30%, parola extra titolo −20%, descriptor low-relevance −5%/−1%
- **Lock:** JSON (`title_locks.json`) + tag composer `[lock]` nel file audio
- **Mojibake:** `repair_mojibake()` + tolleranza fuzzy vs filename

### 4.2 `library_reader.py`

- Scan ricorsivo con esclusione `$RECYCLE.BIN`, `_Serato_`, `.trash*`
- Estrazione metadati via Mutagen (MP3/FLAC/M4A/WAV/AIFF)
- `set_tags()` — scrittura title/artist/album/genre
- `count_hotcues()` — parsing tag `Serato Markers2`, conta entry `CUE`
- Cache pickle per avvio rapido

### 4.3 `serato_database.py`

- Formato `database V2`: TLV binario (stesso layout delle crate)
- **Lettura:** elenco path normalizzati per "Trova differenze"
- **Scrittura metadati:** `update_all_databases_metadata()` — home + per-drive
- **Rimozione tracce:** `remove_from_all_databases()` + `remove_from_crates()`
- **Vincolo:** Serato deve essere chiuso durante modifiche al DB

### 4.4 `crate_writer.py`

- Scrittura file `.crate` in `Subcrates/` sullo stesso drive della musica
- Path senza lettera drive (formato Serato)
- Validazione drive letter prima dell'export

### 4.5 `branding.py` (v4.4)

```python
APP_VERSION = "4.4"
URL_FEEDBACK = "https://sirviodj.it/blog/...#formContatto"
URL_PRO_UPGRADE = "..."  # stesso anchor form contatto/acquisto
open_url(url)            # webbrowser standard
is_pro_license(config)   # placeholder → config["license_pro"]
```

---

## 5. Threading Qt

| Worker | Classe | Segnali |
|--------|--------|---------|
| Scan libreria | `LibraryScanWorker` | progress, finished, error |
| Matching | `MatchWorker` | progress, finished |
| Import URL | `ImportWorker` | progress, finished, error |

- UI resta responsive; operazioni lunghe usano `BusyDialog` modale
- `closeEvent` attende worker attivi + opzionale rescan pre-chiusura

---

## 6. Configurazione (`config.json`)

| Chiave | Tipo | Descrizione |
|--------|------|-------------|
| `music_folder` | str | Root libreria musicale |
| `serato_folder` | str | Override manuale Subcrates |
| `theme` | light/dark | Tema interfaccia |
| `font_size` | 10–17 | Dimensione font globale |
| `visible_columns` | dict | Colonne tabella risultati |
| `bpm_penalty_enabled` | bool | Penalità BPM opzionale |
| `language` | auto/en/it/... | Lingua UI |
| `license_pro` | bool | Licenza Pro (placeholder) |
| `skip_rescan_dialog` | bool | Salta dialog rescan alla chiusura |

---

## 7. Formato Serato

### Crate (`.crate`)

```
vrsn (4 byte) + otrk entries...
  otrk → ptrk (path UTF-16-BE, relativo al drive)
```

### Database V2

```
vrsn + otrk entries...
  otrk → pfil (path), tsng (title), tart (artist), talb (album), tgen (genre)
```

**Limitazione architetturale:** Serato carica crate/DB in memoria all'avvio. Modifiche esterne richiedono riavvio Serato (o riproduzione traccia per refresh metadati singolo).

---

## 8. i18n

- Funzione `tr(key, **kwargs)` in `i18n.py`
- Base EN + IT inline; estensioni in `i18n_locales.py`
- `_retranslate_ui()` in MainWindow aggiorna tutta l'UI al cambio lingua
- Nuove chiavi v4.4: `app_tagline`, `grp_tools`, `btn_pro_upgrade`, `btn_feedback`, `pro_dialog_*`

---

## 9. Build & distribuzione

```batch
install.bat    # venv + pip install -r requirements.txt
start.bat      # install + run
run.bat        # run only
build.bat      # PyInstaller --onefile --windowed
```

Dipendenze: `PySide6`, `rapidfuzz`, `mutagen`, `Send2Trash`

---

## 10. Pattern di sviluppo

1. **Non spezzare `ui_main.py` senza piano** — è il monolite UI; estrarre moduli solo con confini chiari (`branding.py` è l'esempio)
2. **Serato chiuso** prima di scrivere database/crate
3. **Normalizzare path** con `serato_database.normalize_rel_path()` per confronti
4. **Bump versione** in `branding.py` + `main.py` + i18n `window_title` + docs
5. **Traduzioni** — aggiungere chiavi EN e IT in `i18n.py`
6. **Test manuale** — doppio click su `launch_silently.pyw`

---

## 11. File di log e debug

- `serato_debug.log` — log completo sessione (sovrascritto ad ogni avvio)
- Pulsante "Apri log" nel footer
- Livello default: INFO; errori mutagen/Serato loggati con stack trace

---

*Fine documentazione tecnica v4.4*
