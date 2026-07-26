# Serato Playlist Automation v1.0

**Applicazione desktop per automatizzare il confronto tra playlist clienti e la tua libreria Serato DJ.**

![Windows](https://img.shields.io/badge/Platform-Windows-blue)
![Python](https://img.shields.io/badge/Python-3.11+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Cosa Fa

Quando ricevi una playlist per un evento:

1. **Inserisci la playlist** (incolla testo, carica file, o trascina .txt/.csv/.m3u)
2. **Confronta con la tua libreria** musicale locale
3. **Visualizza i risultati**: brani trovati con punteggio di confidenza e brani mancanti
4. **Crea automaticamente una Crate Serato** con tutti i brani trovati
5. **Esporta la lista dei brani mancanti** per acquistarli

---

## Requisiti

- **Windows 10/11**
- **Python 3.11 o superiore** (scarica da https://www.python.org/downloads/)
  - **IMPORTANTE**: durante l'installazione di Python, spunta la casella **"Add Python to PATH"**

---

## Installazione Rapida

### Opzione 1: File Batch (Consigliato)

1. **Estrai** la cartella `serato-playlist-automation` in una posizione qualsiasi (es. Desktop o Documenti)
2. **Doppio click** su `install.bat`
3. **Attendi** il completamento dell'installazione (alcuni secondi)
4. **Doppio click** su `run.bat` per avviare l'app

### Opzione 2: Manuale

Apri il Prompt dei Comandi (`cmd`) nella cartella del progetto ed esegui:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## Come Usare

### Passo 1: Configura la Libreria Musicale

1. Clicca **"Sfoglia..."** accanto al campo "Cartella Musica"
2. Seleziona la cartella principale che contiene tutta la tua musica
   (es. `D:\Musica` o `C:\Users\TuoNome\Musica`)
3. Clicca **"Scansiona Libreria"**
4. Attendi il completamento della scansione (veloce anche per migliaia di brani)

> **Tip**: devi fare questa operazione solo una volta per sessione. L'app
> ricorda l'ultima cartella usata.

### Passo 2: Carica la Playlist

Hai tre opzioni:

- **Incolla direttamente** il testo della playlist nell'area di testo
- **Clicca "Carica File..."** e seleziona un file .txt, .csv o .m3u
- **Trascina** un file nell'area di testo

**Formati supportati:**

```
Artista - Titolo
Artista: Titolo
Artista / Titolo

Da CSV con colonne
Da file M3U/M3U8
Da Spotify (copia il testo)
```

**Esempio di playlist valida:**

```
David Guetta - Titanium ft. Sia
Calvin Harris - Feel So Close
Avicii - Levels
Martin Garrix - Animals
Swedish House Mafia - Don't You Worry Child
```

### Passo 3: Confronta con la Libreria

1. Clicca **"Confronta con Libreria"**
2. La tabella dei risultati si popola automaticamente:
   - **Verde**: match esatto o alta confidenza (85%+)
   - **Giallo/Arancio**: match medio (70-85%)
   - **Rosso**: bassa confidenza o non trovato
3. Per ogni brano trovato vedrai: artista, titolo, punteggio, BPM e Key

### Passo 4: Crea la Crate Serato

1. Inserisci un **nome per la crate** nel campo "Crate Serato"
   (es. `Evento_Marco_2026-06-15`)
2. Clicca **"Crea Crate Serato"**
3. La crate viene creata automaticamente nella tua cartella `_Serato_\Subcrates\`
4. **Al prossimo avvio di Serato DJ**, troverai la crate pronta nella sidebar!

### Passo 5: Esporta i Mancanti

Clicca **"Salva Mancanti..."** per generare un file `.txt` con tutti i brani
che non hai nella libreria, pronti per essere cercati e acquistati su
Beatport, Juno, Traxsource o altri store.

---

## Struttura del Progetto

```
serato-playlist-automation/
  main.py                 # Entry point dell'applicazione
  requirements.txt        # Dipendenze Python
  install.bat             # Script di installazione automatica
  run.bat                # Script di avvio
  config.json            # Configurazione utente (generato automaticamente)
  serato_automation/
    __init__.py
    config.py             # Gestione configurazione
    playlist_parser.py    # Parsing playlist (txt, csv, m3u)
    library_reader.py     # Scansione libreria musicale + metadati
    track_matcher.py      # Motore di matching fuzzy multi-pass
    crate_writer.py       # Creazione file .crate per Serato DJ
    report_generator.py   # Generazione report mancanti
    ui_main.py            # Interfaccia grafica PySide6
```

---

## Come Funziona il Matching

Il motore di matching usa una strategia **multi-pass** con livelli di confidenza:

1. **Passo 1 - Esatto**: confronto normalizzato esatto (titolo + artista)
2. **Passo 2 - Token Sort** (85%+): gestisce inversioni ("Yesterday Beatles" vs "Beatles Yesterday")
3. **Passo 3 - Token Set** (75%+): gestisce token extra ("Beatles (Remastered)" vs "Beatles")
4. **Passo 4 - Parziale** (60%+): confronto solo del titolo
5. **Passo 5 - Composito**: artista e titolo confrontati separatamente

La libreria **RapidFuzz** (backend C++) garantisce velocita anche su librerie
con 50.000+ tracce.

---

## Configurazione

Il file `config.json` viene generato automaticamente al primo avvio.
Puoi modificarlo manualmente per personalizzare:

```json
{
  "music_folder": "D:\\Musica",
  "serato_folder": "",
  "output_folder": "C:\\Users\\Nome\\Documents\\SeratoReports",
  "match_thresholds": {
    "exact": 100,
    "token_sort": 85,
    "token_set": 75,
    "partial": 60
  },
  "audio_extensions": [".mp3", ".flac", ".m4a", ".wav", ".aiff", ".ogg"]
}
```

**Soglie di matching:**
- Aumenta i valori se trovi troppi falsi positivi (troppi match sbagliati)
- Riduci i valori se troppi brani vengono segnalati come mancanti

---

## Rilevamento Automatico Serato

L'app rileva automaticamente la cartella `_Serato_` nella posizione standard:
```
C:\Users\<tuo_username>\Music\_Serato_\Subcrates\
```

Se Serato DJ e installato in una posizione diversa, puoi specificarla
nel file `config.json` modificando il campo `serato_folder`.

---

## Risoluzione Problemi

### "Python non trovato"
Installa Python 3.11+ da https://www.python.org/downloads/
Assicurati di spuntare "Add Python to PATH" durante l'installazione.

### "Impossibile creare la crate"
- Verifica che i percorsi dei file musicali siano validi
- Verifica che la cartella `_Serato_\Subcrates\` sia accessibile e scrivibile
- Prova a modificare il campo `output_folder` in `config.json`

### "Libreria non caricata"
- Assicurati di aver selezionato la cartella corretta
- Verifica che contenga file audio (.mp3, .flac, .m4a, etc.)

### I risultati del matching non sono accurati
- Modifica le soglie in `config.json` (abbassa per piu match, alza per piu precisione)
- Assicurati che i metadati dei tuoi file siano completi e consistenti

### La crate non appare in Serato DJ
- **Chiudi e riapri Serato DJ** dopo aver creato la crate (Serato rileva le nuove crate solo all'avvio)
- Verifica che il file .crate sia nella cartella `_Serato_\Subcrates\`
- Il nome della crate non deve contenere caratteri speciali: `/ \ : * ? " < > |`

### Serato DJ deve essere chiuso durante l'uso?
**No, non e necessario chiudere Serato DJ** per usare questo software.
Il programma scrive direttamente i file .crate nella cartella `_Serato_\Subcrates\`
senza interferire con Serato. Tuttavia, per **vedere la crate** appena creata,
devi **chiudere e riaprire Serato DJ** (Serato carica le crate solo all'avvio).

---

## Tecnologie

| Componente | Tecnologia |
|---|---|
| Interfaccia | PySide6 (Qt6) |
| Matching | RapidFuzz (backend C++) |
| Metadati Audio | mutagen |
| Crate Serato | Binary writer + pyserato fallback |

---

## Licenza

MIT License - Libero per uso personale e commerciale.
