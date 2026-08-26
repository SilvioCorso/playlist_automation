# FAQ e risoluzione problemi — Serato Playlist Automation v4.2

---

## Installazione e avvio

### Python non trovato
Installa Python 3.11+ da [python.org](https://www.python.org/downloads/). Durante l'installazione spunta **"Add Python to PATH"**. Poi esegui `install.bat`.

### PySide6 non installato
Esegui `install.bat` nella cartella del progetto oppure:
```bash
pip install -r requirements.txt
```

### Voglio avviare senza finestra nera CMD
Doppio click su `launch_silently.pyw` (usa `pythonw.exe`).

---

## Libreria musicale

### La scansione è lenta
La prima scansione di migliaia di brani richiede alcuni minuti (lettura metadati). Le sessioni successive usano la **cache** (`library_cache_*.pkl`) e sono molto più veloci.

### Non trova i miei file
Verifica che la cartella selezionata contenga file `.mp3`, `.flac`, `.m4a`, `.wav`, ecc. Controlla `audio_extensions` in `config.json`.

### Metadati vuoti (Artista/Titolo)
Il matching usa anche il **nome file**. Per risultati migliori, completa i tag ID3/Vorbis nei tuoi file.

---

## Matching e risultati

### Troppi falsi positivi (match sbagliati)
- Alza le soglie in `config.json` → `match_thresholds`
- Usa il **lucchetto** sui match corretti (impara per i prossimi eventi)
- Controlla la colonna Found se ci sono candidati migliori

### Troppi brani segnati come mancanti
- Abbassa leggermente le soglie in `config.json`
- Verifica che titolo/artista nella playlist siano leggibili (usa **Guida Formato / Prompt IA**)
- Controlla se il brano esiste con titolo molto diverso nei tag

### Score 0% o riga rosa con Found = 0
Riga trattata come **mancante**: validazione ordine titolo fallita o nessun candidato valido. Controlla che le parole del titolo richiesto compaiano **in ordine** nel filename o Song Serato.

### Colonna Found mostra ▼ con numero
Ci sono **più candidati** sopra la soglia 47%. Clicca per aprire il menu e scegliere la versione corretta.

### Righe cyan
Stesso **filename** usato da più righe della playlist (possibile duplicato nella richiesta cliente).

---

## Crate Serato

### La crate non appare in Serato DJ
**Chiudi e riapri Serato DJ.** Le crate nuove vengono caricate solo all'avvio.

**Perché non appare subito (limite di Serato, non dell'app)?**
Serato carica la libreria e tutte le crate **in memoria all'avvio** e riscrive i
file solo alla chiusura. Non esiste un meccanismo (file-watcher, API o hotkey)
per far rileggere a Serato la cartella `Subcrates` mentre è in esecuzione:

- Quando crei una crate *dentro* Serato appare subito perché Serato aggiorna il
  proprio modello in memoria e poi scrive il file. Una crate scritta
  *dall'esterno* (come fa questa app, o qualsiasi tool tipo CrateSync/serato-tools)
  bypassa quel modello, quindi Serato non la "vede" fino al riavvio.
- Il pulsante **Rescan ID3 Tags** di Serato **non** ricarica le crate: rilegge
  solo i tag dei brani già in libreria.
- Nessuno strumento di terze parti riesce a fare un "hot-reload": tutti
  richiedono il riavvio di Serato. È una scelta architetturale di Serato.

Conclusione: l'unico modo affidabile per vedere una crate creata dall'esterno è
**riavviare Serato**.

> ⚠️ **Attenzione (possibile perdita dati):** se Serato è **aperto** e crei/
> sovrascrivi una crate con un **nome già presente** in Serato, alla chiusura
> Serato riscrive quella crate dalla sua memoria e **le tue modifiche vanno
> perse**. Per le crate con **nome nuovo** il file sopravvive e appare al
> riavvio. Regola pratica: se devi rigenerare una crate esistente, **chiudi
> prima Serato**.

### Serato dice "track not found" per le tracce della crate
Causa frequente: **disco sbagliato**. Musica su `E:` ma crate scritta su `C:`. L'app mostra un avviso rosso se rileva disallineamento. Usa **Cartella Serato...** per puntare a `E:\_Serato_\Subcrates\` (stesso disco della musica).

### "DISCO SBAGLIATO! Crate su F: ma musica su E:" — ho cambiato porta USB
**Sintomo:** hai collegato il disco esterno in una porta USB diversa e ora Windows gli assegna una lettera diversa (es. `F:` invece di `E:`). L'app mostra il warning "DISCO SBAGLIATO".

**Soluzione automatica (dalla v4.5 in poi):** L'app rileva automaticamente il cambio di drive tramite il **numero di serie del volume** (volume serial number), un ID univoco a 32-bit che Windows assegna a **ogni partizione formattata**, anche se non ha un nome personalizzato. Al primo avvio dopo il cambio di porta USB:
1. L'app legge la `config.json` e vede che il path salvato non esiste più
2. Cerca tra tutti i drive montati quello con lo stesso volume serial number
3. Aggiorna automaticamente `music_folder` e `serato_folder` con la nuova lettera
4. Migrà anche la cache della libreria, così non devi re-scansionare tutto
5. Mostra nella status bar: "Disco esterno rilevato su F: (era E:)"

**NON serve assegnare un volume label al disco!** Il numero di serie è sempre presente su ogni disco formattato (NTFS, FAT32, exFAT).

**Quando il rilevamento automatico NON funziona:**
- Hai formattato il disco da zero (il serial cambia)
- Hai clonato il disco con un tool sector-by-sector (serial duplicato)
- Stai usando un disco su rete o NAS (non ha drive letter)

In questi rari casi, usa semplicemente il pulsante **"Scegli cartella musica"** per ri-selezionare la cartella sul nuovo disco.

### Il pulsante "Confronta con Libreria" è disabilitato
**Causa:** la cartella musica salvata non esiste più sul disco (es. `E:/Musica` ma `E:` non è più montato). L'app non può scansionare una cartella che non c'è.

**Soluzione:** vedi sopra — auto-remap via volume serial, oppure usa "Scegli cartella musica" per puntare al nuovo path.

### Devo chiudere Serato mentre uso l'app?
Per **creare** una crate con nome nuovo: no, l'app scrive il file `.crate` senza
interferire (poi serve riavviare Serato per vederla). Per **rigenerare/
sovrascrivere** una crate con lo stesso nome di una già caricata in Serato:
**sì, chiudi prima Serato** per evitare che venga riscritta alla chiusura
(vedi avviso sopra).

### Nome crate non valido
Evita caratteri: `/ \ : * ? " < > |`

---

## Player audio

### Il play non funziona
Solo righe con file esistente su disco hanno il player. Righe mancanti mostrano `-`.

### Lo slider non fa seek
Premi prima **Play** sulla stessa riga. Il seek agisce sul brano attualmente in riproduzione.

---

## Lock (lucchetto)

### Cosa fa
Blocca il match titolo→file a **100%** permanente. Scrive `[lock]` nei metadati audio e salva backup in `title_locks.json`.

### Come sblocco
Clicca di nuovo il lucchetto sulla riga. Il tag `[lock]` viene rimosso dal file audio.

---

## Export e selezione

### Salva Mancanti
Esporta brani **non spuntati**: sia quelli non trovati sia quelli trovati ma esclusi dalla crate.

### Spunta Tutti
Rispetta la soglia **Min %** selezionata. Righe lock contano come 100%.

### Copia Tabella / Copia Ultima Spuntata
Copia negli appunti per incollare in Excel, WhatsApp o documenti evento.

---

## Import URL

### YouTube / Spotify non funziona
L'import usa pagine embed pubbliche. Se Spotify/YouTube cambiano struttura, l'import può temporaneamente fallire. In alternativa: copia la lista brani manualmente o usa export da altri tool.

---

## Log e supporto

### Dove trovo il log
Pulsante **Apri Log** nella barra superiore, oppure file `serato_debug.log` nella cartella del progetto.

### Segnalare un bug
Allega estratto del log + screenshot + passi per riprodurre + versione app (titolo finestra: v4.2).

---

## Configurazione avanzata (config.json)

| Campo | Descrizione |
|-------|-------------|
| `music_folder` | Cartella radice musica |
| `serato_folder` | Path `_Serato_/Subcrates` (se auto-detect fallisce) |
| `output_folder` | Cartella export report mancanti |
| `match_thresholds` | Soglie fuzzy per pass di matching |
| `fuzzy_cache_enabled` | Cache interna matcher |

Modifica con l'app chiusa. Backup consigliato prima di editare a mano.
