# Audit del codice — Serato Playlist Automation v4.2

*Generato il 20 giugno 2026 — revisione completa di tutto il codebase*

---

## Indice

1. [Giudizio generale](#1-giudizio-generale)
2. [Analisi per modulo](#2-analisi-per-modulo)
3. [Refactoring applicati (questa sessione)](#3-refactoring-applicati-questa-sessione)
4. [Refactoring valutati e scartati](#4-refactoring-valutati-e-scartati)
5. [Aree di rischio](#5-aree-di-rischio)
6. [Potenziali nuove feature](#6-potenziali-nuove-feature)

---

## 1. Giudizio generale

**Qualità complessiva: buona.** Il codebase è leggibile, ben commentato e mantiene una separazione delle responsabilità coerente. I moduli sono piccoli e focalizzati (config, log, parser, matcher, reader, crate, report). `ui_main.py` è l'unica eccezione: è un monolite intenzionale di ~2800 righe, una scelta architetturale documentata.

**Punti di forza:**

- Separazione chiara tra core (matching, parsing, reading) e UI
- Thread worker correttamente isolati con segnali Qt
- Meccanismo di lock doppio (composer metadata + JSON) robusto e portabile
- Motore di matching multi-pass con pipeline di scoring documentata
- Gestione dei path Windows (drive letter, UNC, doubled prefix) attenta e testata
- Cache della libreria via pickle con invalidation per hash della cartella

**Aree di miglioramento minori** (dettagliate nelle sezioni seguenti).

---

## 2. Analisi per modulo

### `main.py` (44 righe) — ✅ OK

Pulito. L'unica nota: `check_dependencies()` controlla solo PySide6. Le dipendenze `rapidfuzz` e `mutagen` non vengono verificate, ma entrambe hanno fallback nel codice (`try/except ImportError`), quindi la scelta è intenzionale.

### `config.py` (88 righe, dopo refactor) — ✅ OK

Pulito. La costante `DEFAULT_CONFIG` e le funzioni `load_config`/`save_config` sono corrette. Il path di config è risolto con doppia strategia (frozen exe vs sviluppo), senza magic strings sparse.

**Refactor applicato:** rimossa `get_serato_subcrates_path()` — era dead code, la logica di ricerca `_Serato_` vive correttamente in `crate_writer.find_serato_subcrates()` (che è molto più completa).

### `log_handler.py` (53 righe) — ✅ OK

Minimale e corretto. Il `mode='w'` sul FileHandler tronca il log ad ogni avvio: comportamento intenzionale (log recente, non storico). Nessuna issue.

### `playlist_parser.py` (244 righe, dopo refactor) — ✅ OK

Buona copertura dei formati (txt, csv, m3u, testo libero). L'euristica `_looks_like_csv` è sofisticata e robusta (gestisce il caso "Artist1, Artist2 - Title" che sembra CSV ma non lo è).

**Refactor applicato:** rimosso metodo `_parse_csv()` che era un wrapper di 2 righe intorno a `_parse_csv_content()`. La chiamata è ora diretta con `content.strip().split('\n')` inline.

**Nota minore:** `_read_dropped_file()` in `ui_main.py::DropTextEdit` contiene una logica di encoding-fallback identica a `PlaylistParser._read_file()`. In futuro si potrebbe estrarre in una funzione shared in un modulo utils leggero. Non urgente.

### `library_reader.py` (1100 righe, dopo refactor) — ✅ OK

Il modulo più lungo del core. La gestione multi-formato (MP3, FLAC, M4A, WAV, AIFF) è dettagliata e contiene buona diagnostica (log_detail per i primi 30 file).

**Refactor applicato:** `_get_tag()` e `_get_mp4_tag()` erano metodi identici byte per byte. Unificati: `_get_mp4_tag = _get_tag` (alias di classe). Nessun cambiamento funzionale.

**Nota:** il sistema `log_detail = self._file_counter <= 30` è efficace per il debug ma genera rumore nel log di produzione per librerie grandi. Un flag `verbose_scan` in `config.json` potrebbe permettere di disabilitarlo. Non urgente.

**Nota:** la duplicazione di `WAVE()` in `_extract_wav_metadata` (potenzialmente aperto due volte per lo stesso file nella terza sezione RIFF fallback) è innocua grazie alla guard `if not wav_tags_obj`, ma il codice è complesso da seguire. Non urgente modificare.

### `track_matcher.py` (1155 righe) — ✅ Ottimo

Il modulo più critico. La pipeline a 4 stadi (word penalty → title presence → title ordered → post-rules) è ben documentata e corretta. Il refactoring v4.0 ha prodotto un codice pulito.

**Osservazione:** il codice di word-coverage in `_find_alternatives()` (righe ~1050-1083) è quasi identico a `_pass_word_coverage()`. Non è stato refactorizzato perché i contesti sono diversi (il primo serve per i candidati alternativi, il secondo per il best match), e la differenza nel calcolo del `score` base è intenzionale. Mantenerli separati riduce il rischio di side effects.

**Osservazione:** `_lib_entries` viene costruito con una tupla `(normalize_string(artist), normalize_string(title), track)` ma `normalize_string(artist)` e `normalize_string(title)` sono anche calcolati in `_lib_keys` come `t.search_key = normalize_string(artist + " " + title)`. Esiste un leggero overhead di normalizzazione doppia. Su 10.000 tracce l'init del matcher dura comunque pochi ms; non vale la pena ottimizzare.

### `crate_writer.py` (441 righe) — ✅ OK

Il codice binario TLV è corretto e verificato su crate reali. La logica di validazione drive è robusta e ben commentata.

**Nota:** `_write_debug_log()` crea un file `*.paths.log` accanto ad ogni crate generata nella cartella `_Serato_/Subcrates/`. Questo file può essere fonte di confusione per l'utente (file strani nella cartella Serato). Considerare l'aggiunta di un flag `debug_crate_log` in `config.json` (default `false`) per disabilitarlo in produzione.

### `report_generator.py` (141 righe) — ✅ OK

Pulito. `generate_missing_tracks_report`, `generate_summary_report` e `generate_search_list` hanno responsabilità distinte e chiare.

**Nota:** il metodo `generate_missing_tracks_report` usa la label "TRACCE TROVATE MA ESCLUSE DALLA CRATE" per i risultati `is_effectively_matched`, ma in ui_main.py il metodo viene chiamato passando solo le righe non-spuntate (quindi già filtrate dall'UI). La logica interna del report è quindi ridondante per il caso d'uso attuale.

### `playlist_importer.py` (440 righe) — ⚠️ Fragile per design

Il modulo usa scraping HTML/embed — fragile per natura se YouTube o Spotify cambiano struttura. Questo è documentato come known issue.

**Nota tecnica:** SSL verification è disabilitato globalmente (`ctx.verify_mode = ssl.CERT_NONE`) per aggirare problemi con i certificati Windows. Soluzione pragmatica ma da monitorare. Non ci sono alternative semplici senza dipendenze extra.

**Osservazione:** `_extract_yt_titles_recursive()` e `_extract_spotify_tracks_recursive()` implementano la stessa logica di ricerca ricorsiva in JSON con leggere variazioni. Un refactoring futuro potrebbe estrarre un helper `_find_key_in_json(data, key, depth)` condiviso. Non urgente.

### `ui_main.py` (~2800 righe) — ✅ Monolite intenzionale

Conforme alle scelte architetturali documentate. Non è stato toccato dal refactoring.

**Osservazione:** `DropTextEdit._read_dropped_file()` è un metodo statico che legge il file e restituisce il contenuto, ma il chiamante (`dropEvent`) ignora il valore di ritorno. Il caricamento effettivo avviene tramite il segnale `file_dropped` che MainWindow gestisce separatamente. Il metodo è quindi vestigiale nel `dropEvent` attuale. Non provoca bug (è un no-op silenzioso), ma può creare confusione.

---

## 3. Refactoring applicati (questa sessione)

| # | File | Tipo | Descrizione | Impatto |
|---|------|------|-------------|---------|
| 1 | `library_reader.py` | Deduplication | `_get_tag` e `_get_mp4_tag` erano metodi identici. Sostituiti con alias di classe: `_get_mp4_tag = _get_tag`. | Zero funzionale; -12 righe |
| 2 | `playlist_parser.py` | Dead wrapper | `_parse_csv()` era un wrapper di 2 righe intorno a `_parse_csv_content()`. Rimosso; la chiamata è ora inline. | Zero funzionale; -5 righe |
| 3 | `config.py` | Dead code | `get_serato_subcrates_path()` non era chiamata da nessun punto del codebase. La logica corretta vive in `crate_writer.find_serato_subcrates()`. Rimossa. | Zero funzionale; -7 righe |

**Totale:** -24 righe di codice ridondante. Nessuna modifica funzionale. Nessun bump di versione necessario.

---

## 4. Refactoring valutati e scartati

| Proposta | Motivazione per scartare |
|----------|--------------------------|
| Estrarre path utils (crate/library) in modulo shared | Troppo invasivo: la logica in `crate_writer` gestisce edge case specifici del formato Serato, quella in `library_reader` è specifica per il walk del filesystem. Mischiare creerebbe coupling. |
| Estrarre helper JSON ricorsivo condiviso per importer | Bassa priorità: i due recursive-search sono simili ma non identici nei criteri; un helper troppo generico sarebbe meno leggibile dei due metodi specifici. |
| Refactoring `_find_alternatives` (dupl. word coverage) | Toccare il matcher è ad alto rischio di regressione sullo scoring. Il comportamento duplicato è intenzionale (contesto diverso). |
| Spezzare `ui_main.py` in moduli separati | Esplicitamente out of scope per policy del progetto (il file è monolitico per scelta). |

---

## 5. Aree di rischio

| Gravità | Area | Descrizione |
|---------|------|-------------|
| 🔴 Alta | `playlist_importer.py` | Scraping HTML fragile: se YouTube/Spotify cambiano DOM o JSON structure, l'import smette di funzionare silenziosamente o con errore generico. Nessun test di regressione automatico. |
| 🟡 Media | `crate_writer._write_debug_log` | Crea file `*.paths.log` in `_Serato_/Subcrates/` — cartella visibile a Serato DJ. Se Serato cerca di caricare questi file come crate, potrebbe generare errori nell'interfaccia. |
| 🟡 Media | Thread safety | `_scan_count`, `_bpm_found`, etc. in `LibraryReader` sono incrementati da più thread in `ThreadPoolExecutor` senza lock. In Python (CPython) questo è generalmente safe per int grazie al GIL, ma è un pattern fragile che potrebbe causare contatori imprecisi su Python alternativo o versioni future. |
| 🟢 Bassa | `_JUNK_PATTERNS` in importer | I pattern sono compilati a livello di modulo (OK), ma potrebbero essere estesi facilmente. Non è un rischio immediato. |
| 🟢 Bassa | `title_locks.json` | Il file viene letto/scritto dal processo principale senza lock di file. Se due istanze dell'app girano in contemporanea (scenario improbabile) potrebbero corrompere il JSON. |

---

## 6. Potenziali nuove feature

*(Vedere risposta testuale dell'agente per la descrizione completa)*
