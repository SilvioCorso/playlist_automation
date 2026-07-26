# Contesto completo — Serato Playlist Automation v4.4

*Documento di bootstrap per nuove sessioni AI. Aggiornato luglio 2026.*
*Da leggere PRIMA di qualsiasi intervento sul codice.*

---

## 1. Cos'è il progetto

Applicazione desktop **Windows** per DJ professionisti. Permette di:

1. Incollare/caricare una playlist cliente (txt, csv, m3u, YouTube/Spotify URL)
2. Confrontarla con la propria libreria musicale locale tramite matching fuzzy
3. Rivedere i risultati (score, candidati multipli, lock)
4. Esportare una **Serato Crate** (`.crate` binario) e un file dei brani mancanti

**Stack:** Python 3.11+, PySide6 (Qt6), RapidFuzz, Mutagen, QMediaPlayer integrato.
**OS target:** Windows 10/11 (path Windows, drive letter, formato Serato specifico).
**Architettura:** locale, nessun server/cloud. Tutto gira sul PC del DJ.

---

## 2. Struttura del progetto

```
Serato_Playlist_Automation_v4.1/
├── main.py                          # Entry point, check dipendenze
├── launch_silently.pyw              # Avvio senza console (produzione)
├── requirements.txt
├── config.json                      # Preferenze utente (generato a runtime)
├── title_locks.json                 # Lock titolo→filepath (generato a runtime)
├── serato_debug.log                 # Log debug (generato a runtime)
├── serato_automation/
│   ├── ui_main.py                   # UI monolitica (~4037 righe) — CUORE del progetto
│   ├── track_matcher.py             # Engine fuzzy matching multi-pass
│   ├── library_reader.py            # Scan cartella musica + estrazione metadati
│   ├── playlist_parser.py           # Parser playlist vari formati
│   ├── playlist_importer.py         # Scraping YouTube/Spotify
│   ├── crate_writer.py              # Scrittura .crate Serato (formato TLV binario)
│   ├── report_generator.py          # Generazione report mancanti/summary
│   ├── config.py                    # Caricamento/salvataggio config JSON
│   ├── i18n.py                      # Sistema traduzioni tr() + en/it
│   ├── i18n_locales.py              # Pacchetti de/es/fr/ru/zh
│   └── log_handler.py               # Configurazione logging
└── docs/
    ├── README.md
    ├── contesto.md                  ← QUESTO FILE
    ├── architettura_tecnica.md
    ├── audit_codice.md
    ├── faq_troubleshooting.md
    ├── prompt_next_ia.md
    └── articolo_blog.md
```

---

## 3. Versione corrente: v4.4

### Novità v4.4

| Area | Dettaglio |
|------|-----------|
| **UI** | Header brand, sezioni ① Libreria / ② Strumenti & Serato, footer con feedback sirviodj.it |
| **Pro** | Pulsante upgrade + dialog licenza one-time (backend TBD) |
| **branding.py** | APP_VERSION, URL, `open_url()`, `is_pro_license()` |
| **Serato DB** | Pulizia/eliminazione su tutti i database V2 (home + per-drive) |
| **Editing** | Colonna Genre; auto-refresh Duplicati dopo Elimina |

### Storico rilevante

| Versione | Novità principali |
|----------|-------------------|
| v4.0 | Refactor matching multi-pass, lock doppio (composer + JSON) |
| v4.1 | Player audio integrato (QMediaPlayer), overlay riga evidenziata |
| v4.2 | Cache libreria pickle, riscansione pre-chiusura, duplicate cyan |
| **v4.3** | Dark theme, SettingsDialog a tab, BPM penalty, PrepareEventWizard, font size dinamico, colori tabella adattivi |

### File da aggiornare ad ogni bump di versione

- `ui_main.py` → header commento, `setWindowTitle(...)`, `_logger.info("Avvio applicazione vX.Y")`
- `main.py` → commento header + `print("  Serato Playlist Automation vX.Y")`
- `docs/README.md` → "versione documentata"
- `docs/architettura_tecnica.md` → titolo e sezioni

---

## 4. CONFIG — chiavi complete v4.3

```python
DEFAULT_CONFIG = {
    "music_folder": "",           # Percorso cartella libreria musicale
    "serato_folder": "",          # Percorso _Serato_/Subcrates (override auto-detect)
    "output_folder": "",          # Cartella output (default Desktop)
    "match_thresholds": {         # Soglie matching (non esposte in UI)
        "exact": 100, "token_sort": 85, "token_set": 75, "partial": 60
    },
    "audio_extensions": [...],    # Estensioni audio scansionate
    "fuzzy_cache_enabled": True,
    # --- v4.3 ---
    "theme": "light",             # "light" | "dark"
    "visible_columns": {          # Colonne visibili nella tabella risultati
        "lock": True, "select": True, "score": True, "found": True,
        "titolo_richiesto": True, "filename": True,   # sempre True (non in UI)
        "artista_serato": True, "song_serato": True,  # configurabili
        "genre": True, "bpm": True, "comment": True, "player": True,
    },
    "bpm_penalty_enabled": False, # Penalità BPM nel matching
    "bpm_reference": 0,           # BPM di riferimento (0 = non impostato)
    "font_size": 11,              # 10 | 11 | 13 | 15 | 17 (Gigante = 17 + bold)
    "language": "auto",           # "auto"|"en"|"it"|"es"|"fr"|"de"|"ru"|"zh"
    "dj_software": "serato",      # Software DJ preferito (UI; export solo Serato attivo)
    "settings_dialog_size": {"width": 560, "height": 500},
    "results_table_columns": {"order": [], "widths": {}},  # layout tabella risultati
    "auto_update": False,         # Aggiornamenti automatici (predisposto, non attivo)
    "skip_rescan_dialog": False,  # Non mostrare dialog riscansione alla chiusura
    "default_rescan_answer": "yes", # "yes" | "no"
}
```

---

## 5. Architettura UI (ui_main.py)

### Costanti colonne tabella

```python
COL_LOCK = 0  COL_SELECT = 1  COL_SCORE = 2   COL_FOUND = 3
COL_TITOLO_RICHIESTO = 4  COL_FILENAME = 5
COL_ARTISTA_SERATO = 6  COL_SONG_SERATO = 7
COL_GENRE = 8  COL_BPM = 9  COL_COMMENT = 10  COL_PLAYER = 11
```

### Classi principali in ui_main.py

```
ClickableSlider(QSlider)          # click groove → seek audio
TextSelectionDelegate             # double-click copia testo cella
TitleColorDelegate                # colonna Titolo Richiesto: parole colorate (compute_word_colors)
ElidingHeaderView(QHeaderView)    # header tabella con ellipsis (NO paintSection custom)
PlayerCellWidget(QWidget)         # play/pause + slider per riga tabella
RowHighlightOverlay(QWidget)      # bordo giallo evidenzia riga attiva player
ResultsTable(QTableWidget)        # tabella risultati, lock, dropdown candidati
FormatGuideDialog(QDialog)        # guida formato playlist + prompt IA
ImportUrlDialog(QDialog)          # import da YouTube/Spotify URL
SettingsDialog(QDialog)           # pannello impostazioni a 6 tab  ← NUOVO v4.3
PrepareEventWizard(QDialog)       # wizard guidato 4 step           ← NUOVO v4.3
MainWindow(QMainWindow)           # controller principale
```

### Worker Qt (threading)

```
LibraryScanWorker(WorkerThread)   # scansione cartella musica
MatchWorker(WorkerThread)         # matching playlist ↔ libreria
ImportWorker(WorkerThread)        # scraping URL YouTube/Spotify
```

### Funzioni module-level importanti

```python
_DARK_THEME_ACTIVE: bool          # flag globale tema, letto da score_to_bg_color
score_to_bg_color(score)          # colore sfondo riga (adattivo light/dark)
score_to_text_color(score)        # colore testo score (adattivo light/dark)
_make_stylesheet(theme, font_size) # costruisce il CSS completo con font size iniettato
_detect_os_language()             # rileva lingua OS (2 lettere: "it", "en", ...)
```

---

## 6. Feature v4.3 — dettaglio implementazione

### 6.1 Dark Theme

- Due costanti: `APP_STYLESHEET` (light) e `DARK_APP_STYLESHEET` (dark)
- `_make_stylesheet(theme, font_size)` sostituisce `font-size: 11px` con il valore scelto
- `MainWindow._apply_theme(theme)` imposta `QApplication.instance().setStyleSheet(...)` + aggiorna `_DARK_THEME_ACTIVE` + ricolora le righe
- Switch istantaneo senza riavvio

### 6.2 BPM Penalty

- Regola post-scoring in `TrackMatcher._rule_bpm_penalty(score, lib_track)`
- `-1% per ogni BPM di differenza`, max -30 punti
- Attivata da `bpm_penalty_enabled` + `bpm_reference > 0`
- Brani senza metadati BPM non penalizzati
- `MatchWorker` accetta `bpm_penalty_enabled` e `bpm_reference` e li passa a `TrackMatcher`

### 6.3 SettingsDialog (6 tab)

| Tab | Contenuto |
|-----|-----------|
| **Aspetto** | Tema (Chiaro/Scuro), Dimensione testo (5 opzioni), Colonne opzionali |
| **Matching** | BPM penalty checkbox + spinbox BPM riferimento |
| **Lingua** | Combo 8 lingue + nota "in preparazione" + lingua OS rilevata |
| **Aggiornamenti** | Label versione v4.3 + checkbox auto-update (predisposto) |
| **Comportamento** | Skip rescan dialog + risposta default |
| **Account** | Dati utente hardcoded (pronto per integrazione futura) |

- Colonne "always visible" (lock, select, score, found, titolo_richiesto, filename) NON appaiono come checkbox (gestite come `None` in `_col_checks`)
- Bottone **↺ Predefiniti** resetta tutto
- Lingua: mostra `QMessageBox` "riavvio richiesto" se cambiata

### 6.4 PrepareEventWizard (4 step)

| Step | Azione utente |
|------|--------------|
| 1 — Playlist | Nome evento + incolla/carica playlist |
| 2 — Matching | Avvia matching (usa `MatchWorker` interno) con progress bar |
| 3 — Riepilogo | Stats (trovati/mancanti) + lista mancanti |
| 4 — Esporta | Crea Crate Serato + Salva Mancanti |

- Al termine popola automaticamente la finestra principale (playlist, crate name, tabella risultati, tab abilitato)
- Il wizard usa la libreria già caricata da `main_window.library_tracks`

### 6.5 Font Size dinamico

Opzioni: Piccolo (10px) · Normale (11px) · Grande (13px) · Extra Grande (15px) · **Gigante (17px, bold)**

Implementazione: `_make_stylesheet` fa `str.replace()` su tutte le occorrenze `font-size: 11px`.
Per Gigante (≥17px) appende regole globali `font-weight: bold` a QLabel, QTableWidget::item, QLineEdit, QComboBox.

### 6.6 Colori tabella adattativi

`score_to_bg_color(score)` e `score_to_text_color(score)` leggono `_DARK_THEME_ACTIVE`:

| Elemento | Light | Dark |
|----------|-------|------|
| Riga match 100% | verde pastello | verde scuro `#194623` |
| Riga match 50% | arancione pastello | rosso scuro `#481616` |
| Riga mancante | rosa | rosso scuro |
| Duplicato | ciano `#b3e5fc` | ciano scuro `#14374a` |
| Found multi (▼) | viola `#4927af` | viola chiaro `#9b7de0` |

### 6.7 i18n e tabella risultati (v4.3+)

- **i18n:** `tr(key)` + cambio lingua live da SettingsDialog; file `i18n.py` + `i18n_locales.py`
- **Header tabella:** `ElidingHeaderView` elide testo header stretto; tooltip con testo completo; rendering Qt standard
- **Titolo Richiesto:** `TitleColorDelegate` + `QTextDocument` (spacing/font identici alle altre colonne); colori parola da `compute_word_colors()`
- **Layout colonne:** ordine e larghezza persistiti in `results_table_columns`
- **Intestazioni IT:** Trovati / Selezione / Valore
- **Accessibilità:** `set_button_alt()` su tutti i QPushButton

---

## 7. Vincoli architetturali (NON violare)

1. **`ui_main.py` è monolitico per scelta** — non spezzare in moduli separati
2. **Formato Serato .crate** — binario TLV, path senza drive letter, stesso disco musica/crate.
   *Nota (verificata 2026):* Serato carica le crate in memoria all'avvio e le
   riscrive alla chiusura; **non** esiste hot-reload di crate scritte
   dall'esterno (nessun file-watcher/API/hotkey). Una crate creata dall'app è
   visibile solo dopo **riavvio** di Serato. Non tentare workaround runtime:
   è un limite architetturale di Serato. Vedi `faq_troubleshooting.md`.
3. **Windows-first** — i path assumono Windows; `os.path` e `os.startfile` usati
4. **Thread safety** — operazioni UI solo dal main thread; workers comunicano via segnali Qt
5. **No server/cloud** — tutto locale, nessuna chiamata API esterna (tranne import URL opzionale)
6. **Compatibilità PySide6** — no PyQt5/tkinter; solo API PySide6/Qt6

---

## 8. Pipeline di matching (track_matcher.py)

Ordine di applicazione:

1. **Composer lock** (`[lock]` nel tag composer audio) → score 100, skip pipeline
2. **Title lock** (JSON title_locks) → score 100, skip pipeline
3. **Pass 1: Exact** (artist+title normalizzato identico)
4. **Pass 2: Word coverage** (tutte le parole della richiesta nel found)
5. **Pass 3: Composite** (token_sort + token_set RapidFuzz)
6. **Pass 4: Fuzzy** (fuzz.ratio)
7. **Pass 5: Title partial** (solo titolo)
8. **Pass 6: Filename** (stemma del filename)
9. **Scoring finale** — due regimi (`_apply_full_pipeline`):
   - **Titolo interamente trovato** (tutte le parole del titolo richiesto in
     ordine nella Song o nel Filename) → **modello a contabilità**
     (`_score_accounting`): base 100 − penalità:
     - artista nella richiesta ma assente da ogni colonna del found → **cap 70%**
     - parola di **titolo** in più nel found (vera, non a bassa rilevanza) → **−20% ciascuna**
     - parola di **artista** in più nel found → **−5% totale**
     - descrittore a bassa rilevanza (`_LOW_RELEVANCE_WORDS`) fuori parentesi → **−5% totale**
     - qualsiasi cosa **tra parentesi** (descrittore o parola non richiesta) → **−1% totale**
     - parola del titolo trovata **solo nel filename** → **−1%**
     - **BPM penalty** (opzionale, −1% per BPM di diff, max −30)
     - **Tolleranza mojibake** (`_similar_token`): se il titolo Serato contiene
       marker di corruzione (`Ã`/`Â`) non ricostruibili, un token corrotto
       (es. `prepara3` da `PreparÃ3`) **non** viene contato come parola in più né
       fa scattare il "solo nel filename", a patto che la parola pulita
       corrispondente sia confermata nel nome file (il filename fa da verità).
   - **Titolo solo parziale** → cancelli severi:
     - Word penalty (parole della richiesta mancanti) → max 50%
     - Title presence → max 45%
     - Title ordered validation → 0% oppure max 44%
     - Containment bonus (→ ≥62%), PSYTRANCE adjustment, BPM penalty

   Normalizzazione (`normalize_string`): riparazione **mojibake**
   (`PreparÃ³`→`Preparó`), rimozione accenti, **underscore→spazio**, rimozione
   contenuto tra parentesi e anni a 4 cifre.

---

## 9. Persistenza

| File | Dove | Contenuto |
|------|------|-----------|
| `config.json` | root progetto | Preferenze utente (tutte le chiavi DEFAULT_CONFIG) |
| `title_locks.json` | root progetto | `{"locks": {"titolo_norm": "path/to/file.mp3"}}` |
| `library_cache_<md5>.pkl` | root progetto | Snapshot `List[LibraryTrack]` + timestamp |
| `serato_debug.log` | root progetto | Log debug (troncato ogni avvio) |

---

## 10. Prossimi sviluppi suggeriti

Questi punti erano stati identificati nell'audit o discussi nella sessione corrente:

### Alta priorità
- [ ] **Auto-update** — predisposto (config `auto_update`) ma non implementato
- [ ] **Export multi-DJ** — select `dj_software` in UI; implementare logica Rekordbox/VirtualDJ/Traktor/…

### Completato recentemente
- [x] **Traduzione UI** — i18n en/it/de/es/fr/ru/zh, cambio lingua senza restart
- [x] **Tabella:** persistenza colonne, header ellipsis, colorazione parole titolo, font size coerente
- [x] **Settings:** resize finestra persistito, select software DJ preferito (solo UI)
- [x] **Accessibilità bottoni** — tooltip + accessibleDescription su tutti i pulsanti

### Media priorità
- [ ] **Flag `debug_crate_log`** in config — disabilita i file `*.paths.log` in Subcrates (confondono Serato)
- [ ] **File System Watcher** — `QFileSystemWatcher` sulla cartella musica per aggiornamento automatico cache
- [ ] **Export multi-formato** — esporta in formato Rekordbox XML o Traktor NML oltre Serato (collegato a `dj_software`)

### Bassa priorità / refactoring
- [ ] Estrarre helper encoding-fallback shared tra `DropTextEdit._read_dropped_file` e `PlaylistParser._read_file`
- [ ] Flag `verbose_scan` in config per ridurre log di scansione librerie grandi
- [ ] Refactoring helper JSON ricorsivo condiviso in `playlist_importer.py`

---

## 11. Come sviluppare correttamente

### Prima di scrivere codice
1. Leggi questo file (`contesto.md`) + `architettura_tecnica.md`
2. Per modifiche a `ui_main.py`: leggi la sezione specifica che intendi toccare prima di editare
3. Verifica sempre con `python -c "from serato_automation.ui_main import ..."` che gli import funzionino

### Pattern da seguire
```python
# Aggiungere un nuovo bottone alla toolbar serato_row
btn = QPushButton("Testo Bottone")
btn.setObjectName("primaryBtn")   # usa objectName per stile CSS
btn.clicked.connect(self._metodo)
row.addWidget(btn)

# Aggiungere una nuova chiave config
# 1. Aggiungila a DEFAULT_CONFIG in config.py
# 2. Usala con self.config.get("chiave", valore_default) in MainWindow
# 3. Salvala con save_config(self.config) quando cambia

# Aggiungere una nuova regola post-matching
def _rule_nuova(self, score: int, lib_track: LibraryTrack) -> int:
    ...
    return score  # sempre ritornare int

# Chiamarla in _apply_post_rules DOPO le regole esistenti
score = self._rule_nuova(score, lib_track)
```

### Dopo ogni modifica a ui_main.py
```bash
python -c "from serato_automation.ui_main import MainWindow; print('OK')"
```

### Versioning
Ogni feature significativa → bump versione (4.3 → 4.4):
- `ui_main.py`: commento header + `setWindowTitle` + `_logger.info`
- `main.py`: commento + print banner
- `docs/README.md` e `docs/architettura_tecnica.md`: aggiorna numero versione

---

*Fine del documento di contesto — v4.3 — 20 giugno 2026*
