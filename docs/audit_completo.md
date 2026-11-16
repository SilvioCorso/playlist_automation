# Audit Completo del Software — Serato Playlist Automation v4.4

> **STATO RISOLUZIONE (v4.5):** la maggior parte delle 39 issue di questo audit
> è stata risolta nella release v4.5. Vedi `docs/contesto.md` §3 per il riepilogo.
> Stato dettagliato per priorità:
> - **Critiche (5):** 3.1 token — ignorata per esplicita richiesta utente;
>   3.2 config.json untracked ✅; 3.3 cache pickle untracked + pickle→JSON ✅;
>   3.4 SSL verificato via certifi ✅; 3.5 LICENSE MIT ✅.
> - **Alte (12):** 4.1 monolite→package ✅; 4.2 .pyc untracked ✅; 4.3 junk untracked ✅;
>   4.4 pickle→JSON cache.py ✅; 4.5 terminate()→cooperativo ✅; 4.6 _run_busy QThread ✅;
>   4.7 Python 3.10 ovunque ✅; 4.8 music_folder default "" ✅; 4.9 requirements split ✅;
>   4.10 test suite (28 test) ✅; 4.11 I/O error handling (log) ✅; 4.12 .gitignore ✅.
> - **Medie (13):** 5.1 URL strict ✅; 5.2 except-Exception (3 siti critici loggati;
>   sweep completo dei restanti ~17 siti = backlog) ◐; 5.3 scritture atomiche ✅;
>   5.4 RotatingFileHandler ✅; 5.5 locale.getlocale ✅; 5.6 QMediaPlayer error handling ✅;
>   5.7 stringhe IT→tr() (4 stringhe) ✅; 5.8 set_composer_lock su QThread = backlog ◐;
>   5.9 guardie cross-platform ✅; 5.10 split _import_amazon_music = backlog ◐;
>   5.11 track failed scan files ✅; 5.12 crate_writer exists-check ✅; 5.13 versioni allineate ✅.
> - **Basse (9):** 6.1 magic numbers commentati ✅; 6.5 clientVersion comment+fallback ✅;
>   6.2/6.3/6.4/6.6/6.7/6.8/6.9 = backlog quality.
>
> Il corpo dell'audit qui sotto è lo snapshot originale (v4.4) e va letto come
> storia, non come stato corrente.

**Data audit:** 26 agosto 2026
**Versione auditata:** v4.4 (commit `a4e5d83`)
**Autore audit:** AI code review
**Scopo:** Valutazione pre-vendita del software come prodotto commerciale

---

## Indice

1. [Sintesi esecutiva](#1-sintesi-esecutiva)
2. [Metodologia e scope](#2-metodologia-e-scope)
3. [Problemi critici (bloccanti per la commercializzazione)](#3-problemi-critici-bloccanti-per-la-commercializzazione)
4. [Problemi alti (devono essere risolti prima della vendita)](#4-problemi-alti-devono-essere-risolti-prima-della-vendita)
5. [Problemi medi (risolvere nei primi 2 mesi)](#5-problemi-medi-risolvere-nei-primi-2-mesi)
6. [Problemi bassi (backlog di quality)](#6-problemi-bassi-backlog-di-quality)
7. [Roadmap di risoluzione](#7-roadmap-di-risoluzione)
8. [Checklist pre-release](#8-checklist-pre-release)
9. [Appendice: metriche del codice](#9-appendice-metriche-del-codice)

---

## 1. Sintesi esecutiva

Il progetto è **funzionalmente solido** — l'algoritmo di matching, la scrittura crate Serato, l'import da YouTube/Spotify/Amazon Music sono operativi e testati manualmente. L'architettura modulare e il sistema di i18n (7 lingue) sono degni di nota.

Tuttavia, **l'attuale stato del repository NON è pronto per la commercializzazione**. Sono presenti **5 problemi critici** di sicurezza e distribuzione che devono essere risolti prima di ogni vendita:

- Un **token GitHub personale (PAT)** è committato in chiaro nel remote URL
- I **dati personali dello sviluppatore** (config.json con path Windows `C:\Users\fulvi\...`, cache pickle da 1.4 MB con 6.192 tracce reali del suo DJ set) sono nel repo pubblico
- La **verifica SSL è disabilitata** per tutte le richieste HTTP a YouTube/Spotify/Amazon — vulnerabilità MITM
- Il **file `pickle.load()`** su un file utente è una superficie di attacco reale (RCE se un utente malintenzionato riesce a scrivere un `.pkl` malevolo)
- **Nessun file LICENSE** — il codice è di fatto "all rights reserved" nonostante il badge MIT nel README

Sono stati identificati anche **12 problemi alti** (architettura God module, nessun test automatico per i percorsi critici, file spazzatura committati, dipendenza Playwright installata anche per chi non la usa), **13 medi** e **9 bassi**.

**Tempo stimato per portare il prodotto a uno stato vendibile:** 2-3 giorni di lavoro concentrato (principalmente pulizia repo e fix di sicurezza), più 1 settimana per i test automatici essenziali.

---

## 2. Metodologia e scope

### File analizzati

| File | LOC | Categoria |
|------|-----|-----------|
| `serato_automation/ui_main.py` | 5.873 | UI principale (God module) |
| `serato_automation/track_matcher.py` | 1.506 | Algoritmo di matching |
| `serato_automation/library_reader.py` | 1.380 | Lettura libreria musicale |
| `serato_automation/playlist_importer.py` | 992 | Import YouTube/Spotify/Amazon |
| `serato_automation/i18n.py` | 927 | Sistema i18n (EN/IT) |
| `serato_automation/crate_writer.py` | 440 | Scrittura crate Serato |
| `serato_automation/serato_database.py` | 453 | Parsing/writing database V2 Serato |
| `serato_automation/playlist_parser.py` | 248 | Parser M3U/CSV/text |
| `serato_automation/config.py` | 106 | Gestione config |
| `serato_automation/log_handler.py` | 52 | Handler logging |
| `serato_automation/report_generator.py` | 140 | Generatore report |
| `main.py` | 55 | Entry point |
| `launch_silently.pyw` | 302 | Launcher bootstrap (appena refactorato) |
| **Totale Python** | **~12.170** | |

### File di supporto ispezionati

- Tutti i file `.bat` (install.bat, start.bat, run.bat, build.bat)
- `.gitignore`
- `README.md`, `docs/audit_codice.md`, `docs/architettura_tecnica.md`
- `requirements.txt`
- `tests/test_i18n.py` (unico file di test, 3 test)

### Categorie di analisi

1. Sicurezza & Robustezza
2. Architettura & Qualità codice
3. Distribuzione & Commercializzazione
4. Dipendenze & Compatibilità
5. Testing & QA
6. User Experience

### Totali finding

| Severity | Numero | Stato |
|----------|--------|-------|
| 🔴 Critico | 5 | Bloccanti per la vendita |
| 🟠 Alto | 12 | Da risolvere prima del rilascio 1.0 |
| 🟡 Medio | 13 | Risolvere nei primi 2 mesi post-rilascio |
| 🟢 Basso | 9 | Backlog quality |
| **TOTALE** | **39** | |

---

## 3. Problemi critici (bloccanti per la commercializzazione)

### 3.1 🔴 Token GitHub Personale committato nel remote URL

**File:** `.git/config` (riga remote URL)
**Categoria:** Sicurezza / Distribuzione

**Problema:**
Il remote origin contiene un PAT embedded:
```
https://SilvioCorso:ghp_xxxxxxxxxxxx@github.com/SilvioCorso/playlist_automation.git
```

Questo token è:
- Visibile in chiaro con `git remote -v` da qualsiasi clone del repo
- Persistente in qualsiasi backup/ZIP della cartella progetto
- Sufficiente per fare push (e potenzialmente altro, a seconda degli scope) sul repository

Anche se il repo è pubblico, il token potrebbe avere scope aggiuntivi (`delete_repo`, `workflow`, `gist`, ecc.) che espongono altri progetti dell'account.

**Soluzione:**
```bash
# 1. Revoca IMMEDIATAMENTE il token su GitHub
#    https://github.com/settings/tokens

# 2. Cambia il remote URL (rimuovi le credenziali)
cd /path/to/playlist_automation
git remote set-url origin https://github.com/SilvioCorso/playlist_automation.git

# 3. Usa git credential manager (built-in su Windows)
#    al primo push chiederà le credenziali una tantum

# 4. Verifica che il token non sia mai apparso nei commit
git log --all -p | grep -E 'ghp_|github_pat_'
```

**Priorità:** Massima — entro 30 minuti dalla lettura di questo audit.

---

### 3.2 🔴 `config.json` con path Windows personali committato nel repo

**File:** `config.json` (committato in git)
**Categoria:** Sicurezza / Distribuzione / Privacy

**Problema:**
Il file `config.json` è tracciato in git e contiene:
```json
{
  "music_folder": "E:/",
  "output_folder": "C:\\Users\\fulvi\\Desktop",
  ...
}
```

Il path `C:\Users\fulvi\...` rivela lo username del sistema dello sviluppatore. Il path `E:/` non esiste sul 99% dei PC degli utenti finali. Ogni utente che scarica il source code parte con la configurazione personale dello sviluppatore.

Peggio: ogni volta che l'utente esegue l'app, scrive su `config.json` (tracciato), generando `git diff` confusi e rischiano di committare il proprio path con `git commit -am`.

**Soluzione:**
```bash
# 1. Rimuovi dal tracking (mantiene il file locale)
git rm --cached config.json

# 2. Aggiungi a .gitignore
echo "config.json" >> .gitignore

# 3. Crea un template
cp config.json config.example.json
# Edit config.example.json: imposta music_folder="" e output_folder=""

# 4. Verifica che config.py crei default se manca
#    (già presente in config.py:load_config)
```

---

### 3.3 🔴 Cache pickle da 1.4 MB con 6.192 tracce reali del DJ committata nel repo

**File:** `library_cache_885cc87fac2d.pkl` (1.4 MB, committuto)
**Categoria:** Sicurezza / Distribuzione / Privacy

**Problema:**
Questo file pickle contiene 6.192 oggetti `LibraryTrack` della libreria musicale personale dello sviluppatore, inclusi:
- **Nomi file reali** (es. `#SOLD# NF Type Beat - Made For This (128kbit_AAC)`)
- Path assoluti su `E:/`
- Dimensioni file, durate, BPM, generi, commenti
- Metadati personali che potrebbero contenere info sensibili (note, hotcue, ecc.)

Questo è:
- **Privacy leak** — dati personali nello spazio pubblico
- **Bloat** — 1.4 MB di binario inutile per chiunque altro
- **Rischio funzionale** — l'app carica automaticamente il file se l'hash MD5 del folder path coincide. Se un utente ha casualmente una cartella `E:/` con lo stesso hash, vedrebbe apparire 6.192 tracce non sue.

**Soluzione:**
```bash
# 1. Rimuovi dal tracking
git rm --cached library_cache_885cc87fac2d.pkl

# 2. Aggiungi pattern a .gitignore
echo "library_cache_*.pkl" >> .gitignore

# 3. (Opzionale) Crea un fixture per testing
#    tests/fixtures/library_cache_test.pkl con 10-20 tracce fittizie
```

---

### 3.4 🔴 Verifica SSL disabilitata per tutte le richieste a YouTube/Spotify/Amazon

**File:** `serato_automation/playlist_importer.py:53-57` (funzione `_fetch_url`) e `440-443` (YouTube innertube API)
**Categoria:** Sicurezza

**Problema:**
```python
def _fetch_url(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={...})
    ctx = ssl.create_default_context()
    ctx.check_hostname = False                    # ❌ pericoloso
    ctx.verify_mode = ssl.CERT_NONE                # ❌ pericoloso
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
        return response.read().decode('utf-8', errors='replace')
```

La verifica SSL è disabilitata per tutte le richieste HTTPS verso YouTube, Spotify e Amazon Music. Il commento storico v1.9.2 dice "SSL fix: uses unverified SSL context for urllib (Windows cert issue)".

**Impatto:**
- Un attaccante su Wi-Fi pubblica, ISP malevolo o proxy aziendale può **intercettare e modificare** le risposte
- Può iniettare contenuti malevoli nelle playlist (es. titoli traccia che sfruttano vulnerabilità parsing)
- Può spoofare interamente gli endpoint YouTube/Spotify/Amazon

Il commento "Windows cert issue" è datato — Python moderno su Windows usa automaticamente il certificate store di sistema. Il problema reale (se mai c'è stato) era probabilmente l'assenza di `certifi`.

**Soluzione:**
```python
# In requirements.txt aggiungere:
certifi>=2024.0.0

# In playlist_importer.py sostituire _fetch_url:
import certifi

def _fetch_url(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 ...',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    ctx = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
        return response.read().decode('utf-8', errors='replace')
```

Applicare la stessa correzione a `_fetch_youtube_continuation` (righe 435-440) e a `_import_amazon_music` (Playwright già verifica SSL di default).

---

### 3.5 🔴 Nessun file LICENSE nonostante il badge MIT nel README

**File:** root del repo (file mancante), `README.md:6`
**Categoria:** Distribuzione / Legale

**Problema:**
Il README mostra il badge `![License](https://img.shields.io/badge/License-MIT-yellow)` ma non esiste alcun file `LICENSE` nel repo. Senza un file LICENSE esplicito con il testo completo della licenza, il codice è **"All Rights Reserved" di default** nella maggior parte delle giurisdizioni.

Questo significa che tecnicamente:
- Nessuno può legalmente copiare, modificare o ridistribuire il codice
- Un utente che lo "compra" non ha garanzie legali di cosa sta comprando
- Per un prodotto commerciale questo è un **bloccante legale**

**Soluzione:**
```bash
# Crea file LICENSE con testo MIT completo
# Sostituire <copyright-holder> con il nome legale (es. "Silvio Corso" o "SirvioDJ")
# Esempio: https://opensource.org/licenses/MIT
```

Contenuto del file `LICENSE`:
```
MIT License

Copyright (c) 2026 <copyright-holder>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 4. Problemi alti (devono essere risolti prima della vendita)

### 4.1 🟠 `ui_main.py` è un God Module da 5.873 righe con 22+ classi

**File:** `serato_automation/ui_main.py`
**Categoria:** Architettura

**Problema:**
Il file `ui_main.py` contiene, in un singolo file:
- `MainWindow` (classe principale UI)
- `ResultsTable` (tabella risultati)
- `PlayerCellWidget`, `RowHighlightOverlay`, `ClickableSlider`, `ElidingHeaderView` (widget custom)
- 9 `QDialog` subclasses: `ImportUrlDialog`, `SettingsDialog`, `QuickGuideDialog`, `ProUpgradeDialog`, `FormatGuideDialog`, `CleanLibraryDialog`, `ReplaceDialog`, `AlgorithmDialog`, `BusyDialog`
- `DropTextEdit`, `TextSelectionDelegate`, `TitleColorDelegate` (delegates)
- 3 `WorkerThread` subclasses
- Helper di tema, colori, etc.

Il file `docs/audit_codice.md` lo chiamava "monolite intenzionale di ~2.800 righe" — ora è **5.873 righe, più del doppio**.

**Impatto:**
- Impossibile navigare senza go-to-symbol
- Difficile da revieware
- Disincentiva contributi esterni
- Testing impossibile (le classi sono accoppiate a livello di modulo)

**Soluzione:**
Suddividere in un package `serato_automation/ui/`:
```
serato_automation/ui/
├── __init__.py          # re-export run_app
├── main_window.py       # MainWindow (~1.500 LOC)
├── widgets.py           # PlayerCellWidget, RowHighlightOverlay, ecc. (~800 LOC)
├── dialogs.py           # Tutti i 9 QDialog (~1.500 LOC)
├── workers.py           # WorkerThread + sottoclassi (~500 LOC)
├── theme.py             # Stylesheet + colori (~300 LOC)
└── results_table.py     # ResultsTable (~800 LOC)
```

Mantenere `ui_main.py` come shim che re-export `run_app` per backward compatibility.

**Sforzo:** 2-3 giorni di refactor meccanico (nessun cambio di logica).

---

### 4.2 🟠 23 file `.pyc` committuti nel repo

**File:** `serato_automation/__pycache__/*.pyc`
**Categoria:** Distribuzione / Igiene

**Problema:**
Sono presenti 23 file `.pyc` (es. `ui_main.cpython-314.pyc`) tracciati in git. Sono:
- Compilati per CPython 3.14 — inutilizzabili su Python 3.11/3.12/3.13
- File binari che producono diff inutili
- Stale — ogni modifica al `.py` corrispondente li rende obsoleti
- Sono stati committuti prima dell'aggiunta di `__pycache__/` al `.gitignore`

**Soluzione:**
```bash
git rm -r --cached serato_automation/__pycache__/
# Il .gitignore esistente impedirà di riaggiungerli
```

---

### 4.3 🟠 File spazzatura committuti nel repo

**File:** `ggg`, `_it_check.txt`, `_gen_i18n_locales.py`, `playlist_automation.iml`, `docs/istruzioni.docx`, `playlist_esempio.txt`
**Categoria:** Distribuzione / Igiene

**Problema:**
File che non dovrebbero essere in un repo commerciale:

| File | Descrizione | Cosa fare |
|------|-------------|-----------|
| `ggg` | File 5 byte con letteralmente `ggggg\n` — test commit GitHub web UI | Elimina |
| `_it_check.txt` | Log errori PowerShell con path `C:\Users\fulvi\...` | Elimina |
| `_gen_i18n_locales.py` | Script one-off con hardcoded `C:\Users\fulvi\...` e uso di `deep_translator` | Sposta in `tools/` o elimina |
| `playlist_automation.iml` | File IntelliJ IDEA machine-specific | Elimina, aggiungi a `.gitignore` |
| `docs/istruzioni.docx` | Documento Word binario in repo Markdown | Converti in `docs/istruzioni.md` ed elimina |
| `playlist_esempio.txt` | File playlist di esempio | Sposta in `docs/examples/` |

**Soluzione:**
```bash
git rm ggg _it_check.txt _gen_i18n_locales.py playlist_automation.iml
git rm docs/istruzioni.docx
git mv playlist_esempio.txt docs/examples/playlist_esempio.txt

# Aggiungi a .gitignore:
cat >> .gitignore << 'EOF'
*.iml
_*.py
_*.txt
.idea/
.vscode/
.DS_Store
Thumbs.db
EOF
```

---

### 4.4 🟠 `pickle.load()` su file utente — RCE potenziale

**File:** `serato_automation/ui_main.py:4497-4498` (`_load_library_cache`)
**Categoria:** Sicurezza

**Problema:**
```python
with open(cache_path, 'rb') as f:
    self.library_tracks = pickle.load(f)
```

`pickle.load()` esegue codice Python arbitrario durante la deserializzazione (via `__reduce__`). Se un attaccante riesce a scrivere un file `library_cache_<hash_conosciuto>.pkl` malevolo nella cartella del software (es. con un malware scaricato apparentemente per altri scopi), al primo avvio dell'app il codice viene eseguito con i privilegi dell'utente.

Il rischio è reale per un prodotto desktop distribuito a DJ non tecnici.

**Soluzione:**
Sostituire pickle con JSON. `LibraryTrack` è già una dataclass, basta `dataclasses.asdict`:

```python
# In un nuovo modulo cache.py:
import json
import dataclasses
from typing import List

def save_library_cache(path: str, tracks: List['LibraryTrack']):
    data = [dataclasses.asdict(t) for t in tracks]
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump({'version': 1, 'tracks': data}, f, ensure_ascii=False)
    os.replace(tmp, path)  # atomic

def load_library_cache(path: str) -> List['LibraryTrack']:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    from serato_automation.library_reader import LibraryTrack
    return [LibraryTrack(**t) for t in data.get('tracks', [])]
```

Vantaggi aggiuntivi: il file diventa human-readable (debug più facile), 30% più piccolo, atomic write contro corruzione.

---

### 4.5 🟠 `QThread.terminate()` in `closeEvent` può corrompere file Serato

**File:** `serato_automation/ui_main.py:5730-5735` e `2807-2811`
**Categoria:** Robustezza

**Problema:**
In `closeEvent()`, se i worker `_scan_worker` o `_match_worker` stanno girando, il codice chiama `terminate()` poi `wait(2000)`. `QThread.terminate()` è un hard kill che interrompe il thread in qualsiasi punto senza rilasciare risorse.

Se il worker è a metà di:
- `_save_library_cache()` → file pickle corrotto → al prossimo avvio crash
- `serato_database.update_database_metadata()` → **database V2 Serato corrotto** → l'utente perde l'intera libreria Serato

La documentazione Qt dice esplicitamente: *"Warning: This function is dangerous and its use is discouraged."*

**Soluzione:**
Aggiungere cancellazione cooperativa:

```python
# Nei worker:
import threading

class ScanWorker(QThread):
    def __init__(self, ...):
        super().__init__()
        self._cancel = threading.Event()
    
    def cancel(self):
        self._cancel.set()
    
    def run(self):
        for filepath in self._files:
            if self._cancel.is_set():
                return
            self._process_file(filepath)

# In closeEvent:
def closeEvent(self, event):
    if self._scan_worker and self._scan_worker.isRunning():
        self._scan_worker.cancel()
        if not self._scan_worker.wait(10000):  # 10 secondi
            # Solo come ultima risorsa
            self._scan_worker.terminate()
            self._scan_worker.wait()
    event.accept()
```

Per `serato_database.py`, il pattern `tmp_path` + `os.replace()` già presente alle righe 301-304 garantisce atomicità — manterlo ma assicurarsi che i worker controllino il cancel flag tra le operazioni.

---

### 4.6 🟠 `_run_busy` blocca la GUI — BusyDialog non si anima

**File:** `serato_automation/ui_main.py:5300-5345`
**Categoria:** Robustezza / UX

**Problema:**
`_show_busy` mostra un `BusyDialog` (non-modale), chiama `QApplication.processEvents()` una volta, poi `_run_busy` esegue `work_fn()` in modo sincrono sul thread GUI. Da quel momento:
- L'event loop è bloccato
- La `QProgressBar` indeterminata del BusyDialog non si anima
- La finestra non viene ridisegnata
- Su Windows dopo ~5 secondi appare "(Not Responding)" nella title bar

Operazioni come `_update_serato_database` (che riscrive tutto il `database V2`) possono richiedere molto più di 5 secondi su librerie grandi.

**Soluzione:**
Spostare `work_fn` su un `QThread`:

```python
def _run_busy(self, message, work_fn, on_done=None):
    dlg = BusyDialog(message, self)
    dlg.show()
    
    class Worker(QThread):
        done = Signal(object)
        def run(self):
            try:
                result = work_fn()
                self.done.emit(result)
            except Exception as e:
                self.done.emit(('error', str(e)))
    
    worker = Worker()
    worker.done.connect(lambda r: (
        dlg.accept(),
        on_done(r) if on_done else None
    ))
    worker.start()
    # Non bloccare — il dialog si chiude quando il worker finisce
```

Se il refactor completo è troppo per v1, almeno inserire `QApplication.processEvents()` ogni 100ms dentro `work_fn` (ma la soluzione corretta è il threading).

---

### 4.7 🟠 Versioni Python richieste inconsistenti tra file

**File:** `install.bat:13`, `start.bat:14`, `README.md`, `launch_silently.pyw:44`
**Categoria:** Distribuzione / Compatibilità

**Problema:**
- `install.bat` dice "Python 3.11 o superiore è richiesto"
- `start.bat` dice "Python 3.11 o superiore è richiesto"
- `README.md` mostra badge `Python-3.11+`
- `launch_silently.pyw` definisce `MIN_PY = (3, 10)` e cerca installazioni `3.10`, `3.11`, `3.12`, `3.13`
- `main.py` non controlla la versione Python, solo i moduli installati

Un utente con Python 3.10 verrà bloccato da `install.bat` ma non da `launch_silently.pyw` — comportamento incoerente.

**Soluzione:**
Scegliere **una** versione minima (3.10 è ragionevole — nessuna sintassi del codice richiede 3.11+). Allineare tutti i file:

```bash
# install.bat riga 13: "Python 3.10 o superiore è richiesto"
# start.bat riga 14:   stesso
# README.md badge:     Python-3.10+
# launch_silently.pyw: MIN_PY = (3, 10)  ← già corretto

# Aggiungere CI matrix su GitHub Actions:
# Python 3.10, 3.11, 3.12, 3.13 × Windows-latest
```

---

### 4.8 🟠 Hardcoded default `"music_folder": "E:/"` rovina la prima esperienza

**File:** `serato_automation/config.py:49`, `config.json:2`
**Categoria:** UX / Distribuzione

**Problema:**
`DEFAULT_CONFIG["music_folder"] = "E:/"` — la maggior parte degli utenti non ha un drive E:. Al primo avvio:
1. L'app tenta `_load_or_scan_library("E:/")`
2. `os.path.isdir("E:/")` ritorna False
3. Compare un `QMessageBox.warning` "Seleziona una cartella musica valida"
4. L'utente è confuso: non ha fatto nulla di male, ma l'app gli mostra già un errore

Peggio: il `config.json` committuto ha `E:/` hardcoded, quindi **ogni nuovo utente** parte con questo problema.

**Soluzione:**
```python
# config.py
DEFAULT_CONFIG = {
    "music_folder": "",          # vuoto = l'utente deve selezionare
    "output_folder": "",         # vuoto = usa Documents/Serato Automation
    ...
}
```

UI: quando `music_folder` è vuoto, mostrare un placeholder chiaro "Seleziona cartella musica..." nel QLineEdit. In `QFileDialog.getExistingDirectory`, usare `os.path.expanduser("~/Music")` come directory di partenza su Windows.

---

### 4.9 🟠 Playwright come dipendenza hard anche per chi non la usa

**File:** `requirements.txt`
**Categoria:** Distribuzione / Compatibilità

**Problema:**
`requirements.txt` lista `playwright>=1.40.0` incondizionatamente. Ma `playlist_importer.py:770-780` lo importa lazy e gestisce la sua assenza con un `ValueError` user-friendly.

Risultato: ogni installazione scarica ~150 MB di Playwright + ~250 MB di Chromium, anche per utenti che useranno solo YouTube/Spotify.

Per un prodotto commerciale dove l'utente finale paga per l'esperienza, questo è inaccettabile.

**Soluzione:**
Dividere in due file:

`requirements.txt` (core, ~50 MB totali):
```
PySide6>=6.6.0
rapidfuzz>=3.0.0
mutagen>=1.47.0
Send2Trash>=1.8.0
certifi>=2024.0.0
```

`requirements-amazon.txt` (opzionale, ~400 MB):
```
-r requirements.txt
playwright>=1.40.0
```

In `install.bat`, chiedere all'utente:
```batch
set /p WANT_AMAZON="Vuoi abilitare l'import da Amazon Music? (richiede ~400MB download) [s/N]: "
if /i "%WANT_AMAZON%"=="s" (
    pip install -r requirements-amazon.txt
    playwright install chromium
) else (
    pip install -r requirements.txt
)
```

Documentare in README la differenza.

---

### 4.10 🟠 Copertura test essenzialmente zero

**File:** `tests/test_i18n.py` (3 test)
**Categoria:** Testing

**Problema:**
L'unico file di test ha 3 test banali su i18n string lookup. **Nessun test** per:
- `serato_database._iter_tlv` (parsing binario del `database V2` Serato — tocca il file reale dell'utente)
- `crate_writer._write_binary` (un byte sbagliato e Serato rifiuta la crate)
- `track_matcher.match_playlist` (tutto il valore di business del prodotto)
- `playlist_parser` per M3U/CSV/text
- Import URL da YouTube/Spotify/Amazon (con mock fixture)
- Path sanitization (`_sanitize_crate_path`, `_sanitize_folder_path`)
- `config.load_config`/`save_config` round-trip

Nessun CI/CD: nessun `.github/workflows/`, nessun `pytest.ini`, nessun `conftest.py`.

**Soluzione:**
Aggiungere test minimi per i percorsi critici:

```
tests/
├── conftest.py                  # fixtures: tmp_path, sample tracks
├── test_i18n.py                 # (esistente)
├── test_serato_database.py      # golden binary in/out per _iter_tlv
├── test_crate_writer.py         # round-trip: write→read-back→verify
├── test_track_matcher.py        # 20 casi playlist→library con score atteso
├── test_playlist_parser.py      # parsing M3U/CSV/text per ogni formato
├── test_playlist_importer.py    # mock urllib per YouTube/Spotify
├── test_config.py               # round-trip save/load + defaults
└── test_url_routing.py          # routing URL→source (già parzialmente fatto)
```

CI su GitHub Actions:
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: windows-latest
    strategy:
      matrix:
        python: ['3.10', '3.11', '3.12', '3.13']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      - run: pip install -r requirements.txt pytest
      - run: pytest tests/ -v
```

---

### 4.11 🟠 Error handling insufficiente su file I/O

**File:** `serato_automation/ui_main.py:4605-4618` (`_load_playlist_file`), `serato_automation/report_generator.py:32,79,132`
**Categoria:** Robustezza

**Problema:**
`_load_playlist_file` cattura solo `UnicodeDecodeError` nel loop di encoding fallback. Se l'utente seleziona un file senza permessi di lettura (network share, file locked), `open()` solleva `PermissionError` che arriva fino a `QApplication.exec()` e **crasha l'app**.

Stesso pattern in `ReportGenerator`: nessun try/except, qualsiasi errore di I/O crasha il chiamante.

**Soluzione:**
```python
def _load_playlist_file(self):
    filepath, _ = QFileDialog.getOpenFileName(...)
    if not filepath:
        return
    
    encodings = ['utf-8', 'utf-8-sig', 'cp1252', 'latin-1']
    content = None
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue
        except OSError as e:
            QMessageBox.warning(
                self, tr("title_error"),
                tr("msg_cannot_read_file", path=filepath, error=str(e))
            )
            return
    
    if content is None:
        QMessageBox.warning(
            self, tr("title_error"),
            tr("msg_unsupported_encoding", path=filepath)
        )
        return
    # ... resto
```

---

### 4.12 🟠 `.gitignore` incompleto

**File:** `.gitignore`
**Categoria:** Distribuzione

**Problema:**
L'attuale `.gitignore` è di 5 righe e non include:
- `config.json` (config utente)
- `title_locks.json` (stato utente)
- `library_cache_*.pkl` (cache pickle)
- `*.iml` (IntelliJ)
- `dist/`, `build/`, `*.spec` (PyInstaller)
- `.idea/`, `.vscode/` (IDE)
- `.DS_Store`, `Thumbs.db` (OS)
- `*.bak_*` (backup Serato DB creati da `serato_database.py`)

**Soluzione:**
```gitignore
# === User state — MAI committare ===
config.json
title_locks.json
library_cache_*.pkl
serato_debug.log

# === Python ===
__pycache__/
*.pyc
*.pyo
venv/
.bootstrap_done

# === Build artifacts ===
dist/
build/
*.spec

# === IDE ===
*.iml
.idea/
.vscode/

# === OS ===
.DS_Store
Thumbs.db

# === Serato backup files (creati da serato_database.py) ===
*.bak_*

# === Stray dev files ===
_*.py
_*.txt
```

---

## 5. Problemi medi (risolvere nei primi 2 mesi)

### 5.1 🟡 Validazione URL per substring — no schema/hostname check

**File:** `serato_automation/playlist_importer.py:36-50`
**Categoria:** Sicurezza

**Problema:**
`import_playlist_from_url` fa dispatch basandosi su `'youtube.com' in url`. Un URL come `https://attacker.com/path?x=youtube.com` verrebbe riconosciuto come YouTube. Per YouTube l'impatto è limitato (la regex estrae comunque un playlist ID valido). Per Spotify, invece, l'URL originale viene fetchato direttamente — un URL come `https://open.spotify.com.evil.tld/playlist/abc` verrebbe scaricato così com'è.

**Soluzione:**
```python
from urllib.parse import urlparse

def import_playlist_from_url(url: str) -> Tuple[str, List[str]]:
    url = url.strip()
    parsed = urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Schema URL non supportato. Usa http:// o https://")
    
    if len(url) > 2048:
        raise ValueError("URL troppo lungo")
    
    host = parsed.netloc.lower()
    
    if host in ('www.youtube.com', 'youtube.com', 'youtu.be', 'music.youtube.com'):
        return ('YouTube', _import_youtube(url))
    elif host in ('open.spotify.com', 'spotify.com'):
        return ('Spotify', _import_spotify(url))
    elif host.endswith('.amazon.com') or host.endswith('.amazon.it') or host.endswith('.amazon.de') \
         or host.endswith('.amazon.fr') or host.endswith('.amazon.es') or host.endswith('.amazon.co.uk'):
        if host.startswith('music.'):
            return ('Amazon Music', _import_amazon_music(url))
    else:
        raise ValueError(f"URL non supportata. Hostname '{host}' non riconosciuto.")
```

---

### 5.2 🟡 20+ `except Exception:` silenziosi nel codice

**File:** `serato_automation/library_reader.py:418, 510, 798, 848, 884, 905`; `serato_automation/serato_database.py:174, 219, 324, 420, 444`; `serato_automation/track_matcher.py:359, 784, 863, 1357, 1419, 1449`
**Categoria:** Robustezza

**Problema:**
Decine di `except Exception: pass` o `except Exception: continue` che swallow errori senza log né feedback. Esempi critici:
- `library_reader.py:418` — `except Exception: pass` dopo `EasyID3(filepath)` fallback — i metadati MP3 spariscono silenziosamente
- `library_reader.py:510` — `except Exception: return` in `_extract_mp4_metadata` — fallimento silenzioso su una traccia
- `serato_database.py:420` — `except Exception: continue` quando legge un crate — corruzione silenziosa
- `track_matcher.py:1357` — `except Exception: continue` — uno scorer fallisce e viene saltato

**Impatto:** L'utente ottiene risultati errati nelle crate e non sa perché.

**Soluzione:**
Per ogni `except Exception:`:
1. Sostituire con eccezioni specifiche (`except (KeyError, IndexError, AttributeError, TypeError):`)
2. Almeno log a WARNING con il filepath/track identifier
3. Per operazioni user-facing (scrittura crate, update DB), propagare l'errore alla UI

Esempio:
```python
# Prima:
try:
    audio = EasyID3(filepath)
except Exception:
    pass  # silent

# Dopo:
try:
    audio = EasyID3(filepath)
except (mutagen.id3.ID3NoHeaderError, mutagen.MutagenError) as e:
    logger.warning("Cannot read ID3 from %s: %s", filepath, e)
    audio = {}
```

---

### 5.3 🟡 Scritture file non atomiche — crash corrompe dati utente

**File:** `serato_automation/config.py:93-101` (`save_config`), `ui_main.py:4478-4490` (`_save_library_cache`), `ui_main.py:5624-5633` (`_save_title_locks`)
**Categoria:** Robustezza

**Problema:**
Tutte e tre le funzioni di salvataggio fanno:
```python
with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f)
```

Tra `open(..., 'w')` (che tronca il file a 0 byte) e `json.dump()` che completa, c'è una finestra in cui il processo può essere killato (Windows crash, blackout, antivirus aggressivo). Risultato: file vuoto o parzialmente scritto, al prossimo avvio `json.load()` fallisce e cade sui default — **l'utente perde la configurazione, i lock confermati, o la cache library**.

**Soluzione:**
Pattern atomic write (lo stesso usato da `serato_database.py:301-304`):

```python
def save_config(config: dict, path: str = None):
    path = path or CONFIG_PATH
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)  # atomic on same volume
```

`os.replace()` è atomico su Windows per rename sullo stesso volume.

---

### 5.4 🟡 Log file troncato ad ogni avvio — nessuna cronologia crash

**File:** `serato_automation/log_handler.py:33, 39`
**Categoria:** Testing / Supporto

**Problema:**
```python
FileHandler(log_path, mode='w', encoding='utf-8')
```

`mode='w'` tronca `serato_debug.log` a 0 byte ad ogni avvio. Se l'app crasha, il traceback viene scritto; al riavvio successivo il log viene azzerato e il crash è perso.

Per un prodotto commerciale, i ticket di supporto "è crashato ieri" non possono essere debuggati dal log.

**Soluzione:**
```python
import logging.handlers

# In log_handler.py:
handler = logging.handlers.RotatingFileHandler(
    log_path,
    mode='a',                          # append, non truncate
    maxBytes=5_000_000,                # 5 MB
    backupCount=3,                     # mantieni 3 file di rotazione
    encoding='utf-8',
)
```

In alternativa: `TimedRotatingFileHandler(when='midnight', backupCount=7)` per log giornalieri.

---

### 5.5 🟡 `locale.getdefaultlocale()` deprecato — rimosso in Python 3.15

**File:** `serato_automation/i18n.py:27`
**Categoria:** Compatibilità

**Problema:**
`locale.getdefaultlocale()` è deprecato in Python 3.11 e sarà rimosso in 3.15. Emette `DeprecationWarning` in produzione.

**Soluzione:**
```python
# Prima:
import locale
lang = locale.getdefaultlocale()[0] or 'en'

# Dopo:
def _detect_locale():
    try:
        loc = locale.getlocale()[0]
    except (ValueError, TypeError):
        loc = None
    if not loc:
        loc = os.environ.get('LANG', 'en')
    return loc.split('_')[0].lower() or 'en'
```

---

### 5.6 🟡 `QMediaPlayer`/`QAudioOutput` senza error handling — crash su macchine senza audio

**File:** `serato_automation/ui_main.py:3371-3378`
**Categoria:** Robustezza

**Problema:**
`MainWindow.__init__` costruisce `QMediaPlayer(self)` e `QAudioOutput(self)` senza try/except. Su Windows Server, in sessioni RDP senza audio, o su macchine con servizio audio disabilitato, `QAudioOutput` può fallire. Il primo `setSource(url)` crasherà.

**Soluzione:**
```python
try:
    self._player = QMediaPlayer(self)
    self._audio_output = QAudioOutput(self)
    self._player.setAudioOutput(self._audio_output)
    self._player.errorOccurred.connect(self._on_player_error)
    self._player_available = True
except Exception as e:
    logger.warning("Audio player not available: %s", e)
    self._player_available = False

def _on_player_error(self, error, error_string):
    logger.warning("QMediaPlayer error: %s (%s)", error_string, error)
    # Non crashare — disabilita silenziosamente il player
```

---

### 5.7 🟡 Stringhe user-facing hardcoded in Italiano — bypassano l'i18n

**File:** `serato_automation/ui_main.py:4607, 4574, 4637, 5405`
**Categoria:** UX / i18n

**Problema:**
Nonostante il sistema `tr()` supporti 7 lingue, alcune stringhe sono hardcoded in Italiano:
- Linea 4607: `"Carica Playlist"` (titolo dialog)
- Linea 4574: `f"Libreria: {len(tracks)} tracce ({total_size:.0f} MB) | BPM: ..."` (status bar)
- Linea 4637: `f"Importati {len(dialog.imported_tracks)} brani da {dialog._source}."`
- Linea 5405: `f"Matching: {matched} trovati, {missing} mancanti."`

Queste appaiono in Italiano anche con lingua selezionata English/Español/ecc.

**Soluzione:**
Aggiungere chiavi a `i18n.py`:
```python
"dlg_load_playlist": "Load Playlist" / "Carica Playlist" / ...
"status_library_loaded": "Library: {count} tracks ({size:.0f} MB) | BPM: {bpm}" / ...
"status_imported_from_url": "Imported {count} tracks from {source}." / ...
"status_matching_summary": "Matching: {matched} found, {missing} missing." / ...
```

Sostituire gli f-string hardcoded con `tr(...)`.

---

### 5.8 🟡 Scrittura metadati sincrona su GUI thread — UI freeze

**File:** `serato_automation/ui_main.py:2342-2403` (`_on_lock_row_clicked`)
**Categoria:** UX / Robustezza

**Problema:**
Click sul pulsante lock → `LibraryReader.set_composer_lock(filepath, lock=True)` in modo sincrono. Apre il file audio con mutagen, legge/scrive tag, salva. Per MP3/FLAC è <100ms, ma per WAV grandi o share di rete può richiedere 1-2 secondi. Durante questo tempo:
- UI completamente frozen
- Il pulsante lock non si aggiorna visivamente
- "(Not Responding)" può apparire su Windows

**Soluzione:**
Spostare su QThread:
```python
class LockWriteWorker(QThread):
    done = Signal(str, bool)  # filepath, success
    
    def __init__(self, reader, filepath, lock):
        super().__init__()
        self.reader = reader
        self.filepath = filepath
        self.lock = lock
    
    def run(self):
        try:
            self.reader.set_composer_lock(self.filepath, self.lock)
            self.done.emit(self.filepath, True)
        except Exception as e:
            logger.error("Lock write failed: %s", e)
            self.done.emit(self.filepath, False)
```

UI: mostrare pulsante in stato "Saving..." (disabilitato + icona spinner) finché `done` non arriva.

---

### 5.9 🟡 Comandi Windows-only senza fallback cross-platform

**File:** `serato_automation/ui_main.py:5722, 4970, 4973, 4976`
**Categoria:** Compatibilità

**Problema:**
- `_open_log_file()`: `os.startfile()` (Windows-only) con fallback a `subprocess.Popen(["notepad", ...])` (Windows-only)
- `_open_file_location()`: ha branch per Windows/macOS/Linux, ma macOS e Linux non sono mai stati testati (no CI)

Un utente Mac che apre il source code crasha con `AttributeError` (no `os.startfile`).

**Soluzione:**
Poiché il prodotto è Windows-only attualmente, mettere un guard:
```python
def _open_log_file(self):
    if not sys.platform.startswith('win'):
        QMessageBox.information(self, tr("title_info"),
            "Log file path: " + self._log_path)
        return
    try:
        os.startfile(self._log_path)
    except OSError:
        subprocess.Popen(["notepad", self._log_path])
```

Se la cross-platform è desiderata, testare i branch macOS/Linux in CI.

---

### 5.10 🟡 `_import_amazon_music` — metodo da 234 righe

**File:** `serato_automation/playlist_importer.py:757-990`
**Categoria:** Architettura

**Problema:**
Singolo metodo da 234 righe che fa: dispatch URL, launch browser, render pagina, scroll loop, estrazione dati, riordino, cleanup. Difficile da testare (richiede un browser Amazon Music reale), qualsiasi cambiamento layout Amazon rompe tutto silenziosamente.

**Soluzione:**
Estrarre in funzioni più piccole:
```python
def _import_amazon_music(url: str) -> List[str]:
    tracks_data = _launch_amazon_browser_and_scroll(url)
    return _extract_tracks_in_order(tracks_data)

def _launch_amazon_browser_and_scroll(url: str) -> Dict[str, dict]:
    # ... scroll logic

def _extract_tracks_in_order(tracks_data: Dict[str, dict]) -> List[str]:
    # ... ordering logic
```

Aggiungere un test fixture con snapshot HTML/JSON per testare `_extract_tracks_in_order` senza browser reale.

---

### 5.11 🟡 `ThreadPoolExecutor` per metadata read con errori silenziosi

**File:** `serato_automation/library_reader.py:263-275`
**Categoria:** Robustezza

**Problema:**
`scan_folder` usa `ThreadPoolExecutor(max_workers=4)` e cattura `Exception` incrementando `_error_count`. L'utente non vede quali file sono falliti né perché. Su una libreria di 6.000 tracce con 1% di errore, 60 file vengono silenziosamente saltati — magari proprio quelli che servono per l'evento.

**Soluzione:**
```python
self._failed_files: List[Tuple[str, str]] = []  # (filepath, error_msg)

# Nel worker:
def _read_metadata(filepath):
    try:
        # ... existing logic
        return track
    except Exception as e:
        return ('error', filepath, str(e))

# Dopo la scan:
for result in results:
    if isinstance(result, tuple) and result[0] == 'error':
        self._failed_files.append((result[1], result[2]))

# UI: mostrare nella status bar
if self._failed_files:
    self.statusBar().showMessage(
        f"Library: {len(tracks)} tracks ({len(self._failed_files)} errors)"
    )
    # Aggiungere pulsante "View errors" che apre il log
```

---

### 5.12 🟡 `os.path.exists(p)` per ogni traccia in `create_crate` — lento su network share

**File:** `serato_automation/crate_writer.py:222-225`
**Categoria:** Performance

**Problema:**
Per ogni traccia nella crate, `_write_binary` logga `"Traccia orig: '%s' [esiste=%s]"` chiamando `os.path.exists(p)`. Per una crate da 200 tracce sono 200 syscall stat(). Su locale SSD è istantaneo, su share SMB/NFS può richiedere secondi.

L'esistenza è usata solo per log, non per skip nel file binario.

**Soluzione:**
```python
# Prima:
logger.info("Traccia orig: '%s' [esiste=%s]", p, os.path.exists(p))

# Dopo:
if logger.isEnabledFor(logging.INFO):
    logger.info("Traccia orig: '%s'", p)
# (rimosso exists check — non serve)
```

---

### 5.13 🟡 Versioni inconsistenti tra file

**File:** `README.md:1` (v1.0), `start.bat:4-5` (v3.4), `main.py:2,25` (v4.4), `serato_automation/branding.py:10` (4.4), `docs/audit_codice.md` (v4.2)
**Categoria:** Distribuzione

**Problema:**
Versioni sparse tra v1.0, v3.4, v4.2, v4.4. Gli utenti che riportano bug possono citare "v3.4" dal `start.bat` quando il codice è v4.4 — confonde il supporto.

**Soluzione:**
Centralizzare su `branding.APP_VERSION` (già esiste, attualmente `4.4`):
```python
# branding.py
APP_VERSION = "4.5"  # bump per audit-fix release
```

Aggiornare tutti i riferimenti:
```bash
# main.py: usare from serato_automation.branding import APP_VERSION
# start.bat, run.bat: leggere da branding.py via python -c
# README.md: hardcodare "v4.5"
```

Verificare con: `grep -rn 'v3\.[0-9]\|v4\.[0-3]\|v1\.0'`

---

## 6. Problemi bassi (backlog di quality)

### 6.1 🟢 Magic numbers `AUTO_SELECT_THRESHOLD = 55` e `FOUNDDROP_MIN_SCORE = 47`

**File:** `serato_automation/ui_main.py:197, 198`
**Problema:** Costanti di soglia critiche per il matching, senza commento che spieghi perché 55 e 47. Un maintainer che le cambia sposta silenziosamente l'UX.
**Soluzione:** Aggiungere commento con rationale. Meglio: renderle configurabili in `config.json`.

---

### 6.2 🟢 `import pickle` a livello modulo

**File:** `serato_automation/ui_main.py:120`
**Problema:** Pickle importato ma usato solo in 2 metodi. Rende la dipendenza da pickle più visibile del necessario.
**Soluzione:** Spostare import e metodi in `cache.py` dedicato (come da issue 4.4).

---

### 6.3 🟢 Global mutable state `_DARK_THEME_ACTIVE`

**File:** `serato_automation/ui_main.py:4234`
**Problema:** Variabile globale modificata da `MainWindow._apply_theme` e letta da `score_to_bg_color`. Più istanze MainWindow si sovrascriverebbero.
**Soluzione:** Passare theme esplicitamente a `score_to_bg_color(score, theme)` o usare `QApplication.instance().property("dark_theme")`.

---

### 6.4 🟢 `CONFIG_PATH` globale mutabile

**File:** `serato_automation/config.py:53`
**Problema:** `CONFIG_PATH = None` a livello modulo, settato da `load_config()` e letto da `save_config()`. Se due componenti chiamano `load_config` con path diversi, l'ultimo vince.
**Soluzione:** Rendere `load_config`/`save_config` funzioni pure che prendono il path esplicitamente. O usare una classe `Config` singleton.

---

### 6.5 🟢 `clientVersion` YouTube hardcoded — marcirà

**File:** `serato_automation/playlist_importer.py:417-420`
**Problema:** `"clientVersion": "2.20260101.00.00"` — versione futura finta. YouTube rifiuta richieste innertube con versione troppo vecchia o troppo nuova. Quando YouTube cambierà validazione, le continuation token smetteranno di funzionare silenziosamente — playlist lunghe troncate.
**Soluzione:** Fare della versione una costante con commento sulla fonte. Aggiungere fallback: se 3 chiamate continuation consecutive restituiscono 0 item, loggare warning e smettere (non fallire tutto l'import).

---

### 6.6 🟢 Check dipendenze dopo show window

**File:** `serato_automation/ui_main.py:5862-5873`
**Problema:** `run_app()` mostra la finestra PRIMA di controllare rapididfuzz/mutagen. L'utente vede UI rotta prima del warning.
**Soluzione:** Rimuovere il check post-show (già fatto in `main.py:check_dependencies`). Per Playwright, il check è già in `playlist_importer.py:770-780`.

---

### 6.7 🟢 Minimum window size 1100×800 — troppo per laptop 1366×768

**File:** `serato_automation/ui_main.py:3484`
**Problema:** `setMinimumSize(1100, 800)` esclude i laptop Windows più comuni (1366×768 con taskbar 40px = 696px utilizzabili). La toolbar in basso con i pulsanti "Crea Crate" è sempre off-screen.
**Soluzione:** `setMinimumSize(1000, 700)`. Aggiungere scrollbar se la finestra è più corta, o spostare le azioni critiche nel menu File.

---

### 6.8 🟢 `report_generator.py` senza error handling

**File:** `serato_automation/report_generator.py:32, 79, 132`
**Problema:** Ogni `generate_*` apre file senza try/except. Directory readonly o path invalido → `PermissionError` → crash Qt slot.
**Soluzione:** Wrap in try/except, return None on failure, callers mostrano `QMessageBox.critical(self, tr("title_error"), tr("msg_cannot_write_report", path=filepath, error=e))`.

---

### 6.9 🟢 `os.execv` su Windows non sostituisce il processo

**File:** `launch_silently.pyw:290, 301`
**Problema:** Commento dice "child replaces this process" ma su Windows `os.execv` spawn un nuovo processo e il genitore esce — non è una vera exec.
**Soluzione:** Correggere il commento. L'impatto pratico è minimo (il genitore esce pulitamente), ma la doc è fuorviante.

---

## 7. Roadmap di risoluzione

### Sprint 1 — Pre-vendita (2-3 giorni, bloccante)

Obiettivo: rendere il prodotto commercializzabile.

| # | Task | Issue | Tempo | Priorità |
|---|------|-------|-------|----------|
| 1 | Revoca GitHub PAT, cambia remote URL | 3.1 | 30 min | 🔴 Critico |
| 2 | Aggiungi file LICENSE (MIT completo) | 3.5 | 15 min | 🔴 Critico |
| 3 | Rimuovi dal tracking: `config.json`, `title_locks.json`, `library_cache_*.pkl`, `__pycache__/`, `*.iml`, file spazzatura (`ggg`, `_it_check.txt`, `_gen_i18n_locales.py`, `docs/istruzioni.docx`) | 3.2, 3.3, 4.2, 4.3 | 1 ora | 🔴 Critico |
| 4 | Aggiorna `.gitignore` comprehensivo | 4.12 | 15 min | 🟠 Alto |
| 5 | Riabilita SSL verification (`certifi`) | 3.4 | 30 min | 🔴 Critico |
| 6 | Sostituisci `pickle.load` con `json.load` (modulo `cache.py` dedicato) | 4.4 | 2 ore | 🟠 Alto |
| 7 | Default `music_folder=""` invece di `E:/` | 4.8 | 15 min | 🟠 Alto |
| 8 | Fix `closeEvent` con cancellazione cooperativa | 4.5 | 2 ore | 🟠 Alto |
| 9 | Crea `config.example.json` template | 3.2 | 15 min | 🔴 Critico |
| 10 | Allinea versioni Python richieste (3.10 ovunque) | 4.7 | 30 min | 🟠 Alto |
| 11 | Crea `requirements.txt` core + `requirements-amazon.txt` opzionale | 4.9 | 1 ora | 🟠 Alto |

**Output Sprint 1:** Repository pulito, sicuro, pronto per essere venduto.

### Sprint 2 — Stabilità (1 settimana, pre-rilascio 1.0)

| # | Task | Issue | Tempo |
|---|------|-------|-------|
| 12 | Wrap file I/O con error handling specifico | 4.11 | 3 ore |
| 13 | Atomic file writes per config/cache/locks | 5.3 | 2 ore |
| 14 | Sostituisci `except Exception: pass` con logging mirato | 5.2 | 4 ore |
| 15 | RotatingFileHandler invece di mode='w' | 5.4 | 1 ora |
| 16 | Fix `locale.getdefaultlocale()` | 5.5 | 30 min |
| 17 | Stringhe i18n hardcoded → tr() | 5.7 | 2 ore |
| 18 | `_run_busy` su QThread invece di bloccare GUI | 4.6 | 4 ore |
| 19 | `set_composer_lock` su QThread | 5.8 | 3 ore |
| 20 | Test suite essenziali (serato_database, crate_writer, track_matcher) | 4.10 | 3 giorni |
| 21 | GitHub Actions CI | 4.10 | 4 ore |

**Output Sprint 2:** Software robusto, testato, CI attiva.

### Sprint 3 — Refactor architetturale (2 settimane, post-rilascio 1.0)

| # | Task | Issue | Tempo |
|---|------|-------|-------|
| 22 | Split `ui_main.py` in package `serato_automation/ui/` | 4.1 | 3 giorni |
| 23 | Extract `_import_amazon_music` in funzioni più piccole | 5.10 | 1 giorno |
| 24 | URL routing con urlparse strict hostname | 5.1 | 1 ora |
| 25 | Track failed scan files in `library_reader` | 5.11 | 4 ore |
| 26 | QMediaPlayer error handling | 5.6 | 1 ora |
| 27 | Cross-platform guards per comandi Windows-only | 5.9 | 2 ore |

**Output Sprint 3:** Codebase mantenibile, pronto per feature future.

### Sprint 4 — Quality (ongoing)

Issue 6.1–6.9, magic numbers, dead imports, ecc.

---

## 8. Checklist pre-release

Prima di marcare una release come `1.0` commercializzabile, verificare:

### Sicurezza
- [ ] GitHub PAT revocato e rimosso dal remote URL
- [ ] Nessun file con dati personali utente nel repo (config.json, cache pickle, title_locks.json)
- [ ] SSL verification abilitata su tutte le richieste HTTPS
- [ ] `pickle.load` sostituito con `json.load`
- [ ] URL validation con hostname strict matching
- [ ] Nessun `eval()`/`exec()` su input utente

### Legale
- [ ] File `LICENSE` presente con testo completo
- [ ] Copyright holder corretto
- [ ] README allineato con la licenza effettiva
- [ ] Informativa privacy (se si raccogliono dati utente — attualmente non se ne raccolgono, ma documentarlo)

### Distribuzione
- [ ] `.gitignore` completo (venv, cache, IDE, OS, build artifacts)
- [ ] Nessun file binario inutile nel repo (.pyc, .pkl, .iml, .docx)
- [ ] Nessun file spazzatura (`ggg`, `_*.txt`)
- [ ] `config.example.json` con path vuoti
- [ ] `requirements.txt` core + `requirements-amazon.txt` opzionale
- [ ] `install.bat` chiede se serva Amazon Music
- [ ] `launch_silently.pyw` auto-bootstrappa dipendenze (✅ già fatto)
- [ ] Versioni allineate ovunque (README, .bat, main.py, branding.py)
- [ ] Python 3.10+ dichiarato ovunque

### Robustezza
- [ ] Cancellazione cooperativa worker thread (no `terminate()` hard kill)
- [ ] Atomic file writes per config/cache/locks
- [ ] Error handling su file I/O user-facing
- [ ] `RotatingFileHandler` invece di `mode='w'`
- [ ] `except Exception:` specificati o rimossi
- [ ] QMediaPlayer error handling

### UX
- [ ] Nessuna stringa hardcoded in Italiano (tutte via `tr()`)
- [ ] Default `music_folder=""` (non `E:/`)
- [ ] BusyDialog non blocca event loop (su QThread)
- [ ] Lock click non freeza UI (su QThread)
- [ ] Minimum window size 1000×700 o meno
- [ ] First-run experience: nessun errore predefinito

### Testing
- [ ] Test per `serato_database._iter_tlv` (golden binary)
- [ ] Test per `crate_writer._write_binary` (round-trip)
- [ ] Test per `track_matcher.match_playlist` (20+ casi)
- [ ] Test per `playlist_parser` per ogni formato
- [ ] Test per `config.load_config`/`save_config`
- [ ] GitHub Actions CI su Python 3.10, 3.11, 3.12, 3.13 × Windows

### Documentazione
- [ ] README aggiornato alla versione corretta
- [ ] `docs/istruzioni.md` (convertito da .docx)
- [ ] `docs/audit_completo.md` (questo file)
- [ ] Changelog `CHANGELOG.md`

---

## 9. Appendice: metriche del codice

### Distribuzione LOC per modulo

| Modulo | LOC | Note |
|--------|-----|------|
| `ui_main.py` | 5.873 | ⚠️ God module, da split |
| `track_matcher.py` | 1.506 | OK |
| `library_reader.py` | 1.380 | OK, ma molti `except Exception` |
| `playlist_importer.py` | 992 | OK, ma `_import_amazon_music` è 234 LOC |
| `i18n.py` | 927 | OK |
| `i18n_locales.py` | 1.292 | OK, generato/curato |
| `crate_writer.py` | 440 | OK |
| `serato_database.py` | 453 | OK, atomic writes già presenti |
| `playlist_parser.py` | 248 | OK |
| `report_generator.py` | 140 | Manca error handling |
| `config.py` | 106 | Globale mutabile `CONFIG_PATH` |
| `log_handler.py` | 52 | `mode='w'` da fix |
| `main.py` | 55 | OK |
| `launch_silently.pyw` | 302 | ✅ Appena refactorato con bootstrap |
| **Totale Python** | **~12.170** | |

### File non-Python nel repo

| File | Tipo | Stato |
|------|------|-------|
| `ggg` | Dev junk | ❌ Eliminare |
| `_it_check.txt` | Log dev | ❌ Eliminare |
| `_gen_i18n_locales.py` | Script dev | ❌ Spostare in `tools/` o eliminare |
| `playlist_automation.iml` | IDE | ❌ Eliminare, aggiungere a `.gitignore` |
| `docs/istruzioni.docx` | Binario Word | ❌ Convertire in `.md` |
| `playlist_esempio.txt` | Esempio | 🟡 Spostare in `docs/examples/` |
| `library_cache_885cc87fac2d.pkl` | Cache binaria 1.4 MB | ❌ Eliminare (dati personali) |
| `config.json` | Config utente | ❌ Rimuovere dal tracking |
| `title_locks.json` | Stato utente | ❌ Rimuovere dal tracking |
| `serato_automation/__pycache__/*.pyc` | Bytecode | ❌ Eliminare (23 file) |

### Test coverage attuale

| Modulo | Test | Coverage |
|--------|------|----------|
| `i18n.py` | `test_i18n.py` (3 test) | ~10% (solo lookup stringhe) |
| `playlist_importer.py` | Nessuno | 0% |
| `track_matcher.py` | Nessuno | 0% |
| `serato_database.py` | Nessuno | 0% |
| `crate_writer.py` | Nessuno | 0% |
| `library_reader.py` | Nessuno | 0% |
| `config.py` | Nessuno | 0% |
| **Totale coverage** | **3 test** | **~2%** |

### Lingue supportate

| Codice | Lingua | Stato i18n |
|--------|--------|------------|
| `en` | English | ✅ Completa |
| `it` | Italiano | ✅ Completa |
| `de` | Deutsch | ✅ Completa |
| `es` | Español | ✅ Completa |
| `fr` | Français | ✅ Completa |
| `ru` | Русский | ✅ Completa |
| `zh` | 中文 | ✅ Completa |

---

## Chiusura

Questo audit ha identificato **39 issue** (5 critiche, 12 alte, 13 medie, 9 basse). Le 5 critiche sono **bloccanti per la commercializzazione** e devono essere risolte prima di qualsiasi vendita.

Le **3 azioni più urgenti** (entro 24 ore):

1. **Revoca il GitHub PAT** dal tuo account GitHub → https://github.com/settings/tokens
2. **Pulisci il repository** dai file con dati personali (config.json, library_cache_*.pkl, title_locks.json) e file spazzatura
3. **Aggiungi il file LICENSE** con testo MIT completo

Dopo queste 3 azioni + il fix SSL + la sostituzione di `pickle.load` con `json.load`, il prodotto è tecnicamente vendibile. Il resto della roadmap (testing, refactor architetturale, UX fixes) può procedere in parallelo alle prime vendite.

**Tempo stimato totale per "commercially ready":** 2-3 giorni di lavoro concentrato.

---

*Fine audit.*
