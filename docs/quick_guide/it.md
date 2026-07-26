# Serato Playlist Automation — Guida rapida

*Strumento professionale per DJ — by SirvioDJ*

---

## A cosa serve

Trasforma una **playlist cliente** (testo, file, URL YouTube/Spotify) in una **crate Serato** pronta per l'evento, indicando subito quali brani hai in libreria e quali mancano.

**Risparmio tipico:** da ore di ricerca manuale a pochi minuti di revisione guidata.

---

## Flusso in 4 passi

### ① Configura la libreria

1. Imposta la **cartella musica** (es. `F:/`)
2. Clicca **Scansiona Libreria** — la prima volta può richiedere qualche minuto; le scansioni successive usano la cache ed sono molto più veloci
3. Verifica lo stato verde: *"Libreria: N tracce"*

### ② Carica la playlist cliente

Tab **Playlist Cliente**:

- **Importa da URL** — YouTube o Spotify
- **Carica file** — `.txt`, `.csv`, `.m3u`
- Oppure **incolla direttamente** i titoli nel riquadro

Formato consigliato: `Artista - Titolo` (uno per riga).

### ③ Confronta e revisiona

Clicca **Confronta con Libreria** → tab **Risultati**:

| Colonna | Utilità |
|---------|---------|
| **Score %** | Quanto il brano trovato corrisponde alla richiesta |
| **Trovati** | Menu con candidati alternativi se ce ne sono più di uno |
| **🔒 Lock** | Blocca un match al 100% — non cambia più |
| **Player** | Ascolta il brano senza uscire dall'app |
| **Spunta** | Seleziona i brani da includere nella crate |

Usa **Spunta tutti ≥ X%** per selezionare in blocco solo i match sopra una certa soglia.

### ④ Esporta

- **Crea Crate Serato** — genera il file `.crate` (riavvia Serato per vederla)
- **Salva Mancanti** — lista `.txt` dei brani da acquistare o verificare

---

## Strumenti avanzati

### Manutenzione libreria (tab Editing)

| Funzione | Quando usarla |
|----------|---------------|
| **Pulisci Libreria** | Cerca parole nei metadati o individua mojibake (`PreparÃ3`) |
| **Trova differenze** | Brani in cartella ma non ancora in Serato → crea crate import |
| **Duplicati** | Stesso titolo+artista in più copie — elimina quelle in eccesso |
| **Aggiorna Serato** | Sincronizza metadati modificati nel database Serato (Serato chiuso) |

### Pulsante Guida rapida

Il pulsante **Guida rapida** apre sempre questo documento: panoramica completa delle funzioni e del flusso di lavoro.

### Algoritmo percentuali

Il pulsante nel footer spiega nel dettaglio come viene calcolato ogni score (penalità, parole speciali, esempi reali).

---

## Suggerimenti pro

- **Score ≥ 50%** è un buon punto di partenza per "Spunta tutti"; alza a 70–80% per eventi formali
- Usa il **Lock** sui match certi prima di cambiare candidati nelle righe ambigue
- Le righe **duplicate** (stesso file su più righe) si colorano di ciano
- **Schermo intero** nel tab Risultati/Editing per lavorare comodamente su playlist lunghe
- Dopo **Elimina** duplicati: chiudi Serato, poi riaprilo — le tracce spariscono dalla libreria

---

## Supporto

Feedback e licenza Pro: [sirviodj.it](https://sirviodj.it/blog/serato-playlist-automation-risparmia-tempo#formContato)
