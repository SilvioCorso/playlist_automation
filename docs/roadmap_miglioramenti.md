# Roadmap — Proposte e implementazioni future

*Serato Playlist Automation v4.4 — SirvioDJ*
*Documento vivo: aggiornare ad ogni sprint o sessione di sviluppo.*

---

## Legenda priorità

| Simbolo | Significato |
|---------|-------------|
| 🔴 Alta | Impatto diretto sul workflow DJ quotidiano |
| 🟡 Media | Migliora qualità/efficienza, non bloccante |
| 🟢 Bassa | Nice-to-have, innovazione, marketing |
| ✅ Fatto | Implementato nella versione indicata |

---

## A. UX & Interfaccia

| # | Proposta | Priorità | Stato | Note |
|---|----------|----------|-------|------|
| A1 | Header brand + footer con link sirviodj.it | 🔴 | ✅ v4.4 | Header viola, footer feedback/website |
| A2 | Riorganizzazione bottoni per flusso logico (① Libreria → ② Tools → Tab) | 🔴 | ✅ v4.4 | Sezioni numerate |
| A3 | Pulsante Pro con dialog acquisto one-time | 🔴 | ✅ v4.4 | Licensing backend da collegare |
| A4 | Icone SVG al posto di emoji nei bottoni | 🟡 | ⏳ | Migliore resa su DPI alti |
| A5 | Tooltip contestuali al primo avvio (onboarding tour) | 🟡 | ⏳ | QToolTip + flag `onboarding_done` |
| A6 | Barra progresso globale unificata (non solo tab Playlist) | 🟡 | ⏳ | Stessa BusyDialog ovunque |
| A7 | Tema "Serato" (nero/giallo) oltre light/dark | 🟢 | ⏳ | Richiesto da utenti Serato |
| A8 | Drag & drop file audio direttamente nel tab Editing | 🟡 | ⏳ | Aggiunta rapida metadati |
| A9 | Scorciatoie da tastiera documentate (Ctrl+M match, Ctrl+S save) | 🟡 | ⏳ | QShortcut in MainWindow |
| A10 | Responsive layout per schermi < 1100px | 🟢 | ⏳ | Collapse sezioni tools |

---

## B. Matching & Scoring

| # | Proposta | Priorità | Stato | Note |
|---|----------|----------|-------|------|
| B1 | Modello contabile v5 con penalità granulari | 🔴 | ✅ v4.3+ | Doc in algoritmo_percentuali.md |
| B2 | Mojibake repair + tolleranza filename | 🔴 | ✅ v4.3+ | `_similar_token` in track_matcher |
| B3 | Penalità BPM opzionale configurabile | 🟡 | ✅ v4.3 | Settings → Matching |
| B4 | Match per ISRC / fingerprint audio (AcoustID) | 🟡 | ⏳ | Riduce falsi positivi remix |
| B5 | Regole custom per venue (es. "no explicit") | 🟢 | ⏳ | Filtro post-match |
| B6 | Batch re-score dopo modifica metadati libreria | 🟡 | ⏳ | Evita re-match completo |
| B7 | Export report match con breakdown penalità per riga | 🟡 | ⏳ | CSV per debug cliente |
| B8 | Supporto "Artista - Titolo" obbligatorio in parser | 🟡 | ⏳ | Migliora split artista/titolo |

---

## C. Libreria & Metadati

| # | Proposta | Priorità | Stato | Note |
|---|----------|----------|-------|------|
| C1 | Tab Editing con title/artist/album/genre editabili | 🔴 | ✅ v4.3+ | |
| C2 | Pulisci libreria (search + mojibake detect) | 🔴 | ✅ v4.3+ | |
| C3 | Duplicati + elimina cestino + purge Serato multi-DB | 🔴 | ✅ v4.4 | remove_from_all_databases |
| C4 | Hotcue count da Serato Markers2 | 🟡 | ✅ v4.3+ | Colonna opzionale risultati/editing |
| C5 | Riparazione mojibake automatica batch ("Pulisci tutto") | 🔴 | ⏳ | Previsto, UI in sospeso |
| C6 | Normalizzazione batch genre/BPM/key | 🟡 | ⏳ | Estensione tab Editing |
| C7 | Watch folder: auto-rescan su nuovi file | 🟡 | ⏳ | QFileSystemWatcher |
| C8 | Supporto Rekordbox XML export (oltre Serato crate) | 🟡 | ⏳ | dj_software già in config |
| C9 | Backup automatico tag prima di scrittura | 🟡 | ⏳ | Sidecar .bak JSON |
| C10 | Artwork embed preview in tab Editing | 🟢 | ⏳ | Thumbnail colonna |

---

## D. Integrazione Serato

| # | Proposta | Priorità | Stato | Note |
|---|----------|----------|-------|------|
| D1 | Aggiorna Serato DB (tsng/tart/talb/tgen) multi-drive | 🔴 | ✅ v4.4 | Solo righe salvate |
| D2 | Trova differenze (folder vs database V2) | 🔴 | ✅ v4.3+ | Output tab Risultati |
| D3 | Hot-reload crate in Serato senza riavvio | 🔴 | ❌ Impossibile | Limite architettura Serato |
| D4 | Sync Smart Crates / history / played count | 🟡 | ⏳ | Richiede reverse engineering |
| D5 | Notifica Windows toast "Crate creata — riavvia Serato" | 🟡 | ⏳ | Dopo export crate |
| D6 | Verifica integrità database V2 pre-scrittura | 🟡 | ⏳ | Checksum + rollback |
| D7 | Import crate esistente → tabella risultati | 🟢 | ⏳ | Inverso di crate_writer |

---

## E. Licenza Pro & Business

| # | Proposta | Priorità | Stato | Note |
|---|----------|----------|-------|------|
| E1 | Dialog Pro + link sirviodj.it | 🔴 | ✅ v4.4 | |
| E2 | Backend licensing (chiave serial / email) | 🔴 | ⏳ | `license_pro` in config placeholder |
| E3 | Feature gate: libreria > N tracce solo Pro | 🟡 | ⏳ | Es. 10.000 tracce free |
| E4 | Feature gate: batch editing / duplicati Pro | 🟡 | ⏳ | |
| E5 | Pagamento Stripe/PayPal integrato in-app | 🟡 | ⏳ | WebView o browser esterno |
| E6 | Trial 14 giorni con watermark export | 🟢 | ⏳ | Marketing |
| E7 | Telemetria opt-in crash report (Sentry) | 🟢 | ⏳ | Solo con consenso |

---

## F. Performance & Qualità codice

| # | Proposta | Priorità | Stato | Note |
|---|----------|----------|-------|------|
| F1 | Modulo branding.py (URL, versione) | 🟡 | ✅ v4.4 | |
| F2 | Estrarre stylesheet in ui/styles.py | 🟡 | ⏳ | ~300 righe da ui_main |
| F3 | Estrarre dialogs in ui/dialogs.py | 🟡 | ⏳ | Settings, Wizard, Pro, Clean |
| F4 | Estrarre ResultsTable in ui/results_table.py | 🟡 | ⏳ | ~1200 righe |
| F5 | Indice inverted per match O(1) lookup token | 🟡 | ⏳ | track_matcher hot path |
| F6 | Scan parallelo libreria (già max_workers=4) | 🟡 | ✅ | Tuning configurabile |
| F7 | Test pytest: track_matcher, normalize_string | 🔴 | ⏳ | Solo test_i18n esiste |
| F8 | CI GitHub Actions (lint + test + build exe) | 🟡 | ⏳ | |
| F9 | Type hints completi + mypy | 🟢 | ⏳ | |
| F10 | Logging strutturato JSON per supporto | 🟢 | ⏳ | |

---

## G. Import & Export

| # | Proposta | Priorità | Stato | Note |
|---|----------|----------|-------|------|
| G1 | Import YouTube/Spotify URL | 🔴 | ✅ | playlist_importer |
| G2 | Import Beatport / Traxsource wishlist | 🟡 | ⏳ | CSV/API |
| G3 | Export Excel/CSV risultati match | 🟡 | ⏳ | Per clienti corporate |
| G4 | Template playlist per generi evento (matrimonio, 18 anni) | 🟢 | ⏳ | Wizard step 0 |
| G5 | Invio report mancanti via email (SMTP config) | 🟢 | ⏳ | |
| G6 | Sync playlist verso Spotify (API ufficiale) | 🟢 | ⏳ | OAuth |

---

## H. Documentazione & Supporto

| # | Proposta | Priorità | Stato | Note |
|---|----------|----------|-------|------|
| H1 | Documentazione tecnica v4.4 | 🔴 | ✅ v4.4 | documentazione_tecnica.md |
| H2 | Prompt IA aggiornato | 🔴 | ✅ v4.4 | prompt_next_ia.md |
| H3 | Video tutorial embedded (link YouTube in app) | 🟡 | ⏳ | Pulsante Help |
| H4 | Changelog in-app (tab Updates) | 🟡 | ⏳ | Settings già predisposto |
| H5 | FAQ interattiva con ricerca | 🟡 | ⏳ | Da faq_troubleshooting.md |
| H6 | Manuale PDF export da docs | 🟢 | ⏳ | |

---

## Prossimi sprint consigliati

### Sprint 1 — Pro & stabilità (1–2 settimane)
1. Backend licensing base (chiave + validazione offline)
2. Test pytest per track_matcher (10 casi reali dallo screenshot utente)
3. Riparazione mojibake batch (C5)
4. Toast post-export crate (D5)

### Sprint 2 — Refactoring leggero (1 settimana)
1. Estrarre `ui/styles.py` e `ui/dialogs.py` (F2, F3)
2. Scorciatoie tastiera (A9)
3. Export CSV risultati (G3)

### Sprint 3 — Multi-DJ software (2 settimane)
1. Export Rekordbox XML (C8)
2. Feature gate Pro (E3, E4)
3. Onboarding tour (A5)

---

## Idee innovative (lungo termine)

- **AI Match Assistant:** suggerisce quale candidato scegliere spiegando le penalità in linguaggio naturale
- **Cloud sync opzionale:** backup config + lock + cache su account SirvioDJ (opt-in)
- **Plugin VST-style:** DLL per estendere parser playlist senza rebuild exe
- **Mobile companion:** app per scansionare QR playlist cliente → invia al PC
- **Serato DJ Pro integration:** monitor clipboard quando Serato copia tracce
- **Batch event processor:** cartella con 10 playlist → 10 crate automatiche overnight

---

*Contributi e priorità: feedback su https://sirviodj.it/blog/serato-playlist-automation-risparmia-tempo#formContatto*
