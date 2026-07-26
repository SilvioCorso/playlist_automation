# Come viene calcolata la percentuale di match

Questo documento spiega **passo per passo** come il software assegna la
percentuale (colonna **Valore**) a ogni brano della playlist quando lo confronta
con la tua libreria musicale. Alla fine trovi diversi **esempi concreti** con il
calcolo dettagliato.

> In breve: per ogni brano richiesto il software cerca il miglior candidato nella
> libreria con una **cascata di tecniche di confronto**. Poi, se il **titolo
> richiesto è interamente presente** nel brano trovato, calcola il punteggio con
> un **modello a contabilità**: parte da **100%** e sottrae penalità ben precise.
> Se invece il titolo è solo parzialmente presente, entrano in gioco dei
> **cancelli severi** che limitano molto il punteggio.

---

## 1. La priorità assoluta: i lucchetti (100% garantito)

Prima di qualsiasi confronto, il software controlla se il brano è **bloccato**.
Se lo è, il punteggio è **100% fisso** e tutto il resto viene saltato.

Esistono due tipi di lucchetto:

1. **Composer lock** — il tag `[lock]` è scritto **dentro i metadati del file
   audio** (campo compositore). È il più robusto: sopravvive a spostamenti del
   file e cambi di computer.
2. **Title lock** — una corrispondenza *titolo → file* che hai confermato tu,
   salvata nel file `title_locks.json`.

In entrambi i casi basta che il titolo richiesto sia **contenuto** nel titolo del
brano bloccato. Per togliere il 100%, clicca sul lucchetto della riga per
sbloccarla: il punteggio verrà ricalcolato normalmente.

---

## 2. La cascata di ricerca

Se il brano **non** è bloccato, il software cerca il miglior candidato provando
in ordine queste tecniche. **Si ferma alla prima che dà un risultato valido.**

| # | Passata | Cosa fa |
|---|---------|---------|
| 1 | **Exact** | Artista+titolo *normalizzati* identici |
| 2 | **Word coverage** | Tutte le parole della richiesta sono presenti nel brano |
| 3 | **Composite** | Somiglianza pesata: **artista 30%** + **titolo 70%** |
| 4 | **Fuzzy** | Somiglianza "sfocata" tollerante a ordine e varianti |
| 5 | **Title partial** | Somiglianza parziale sul solo titolo |
| 6 | **Filename** | Confronto con il **nome del file** (utile se i tag sono vuoti) |

### La struttura "Artista - Titolo"

Se la richiesta usa la struttura **`Artista - Titolo`** (con il trattino, oppure
`:`, `|`, `/`), il software separa i due elementi e li usa in modo distinto: sa
qual è l'artista e qual è il titolo. Questo rende il calcolo più accurato (vedi il
modello a contabilità, §3).

### Cos'è la "normalizzazione"

Prima di confrontare, i testi vengono ripuliti in modo che differenze irrilevanti
non contino:

- tutto in **minuscolo**;
- **riparazione della codifica (mojibake)**: testi salvati con doppia codifica
  UTF-8 vengono ripristinati, quindi `PreparÃ³` viene letto come `Preparó`;
- **accenti** rimossi (`Beyoncé` → `beyonce`, `Preparó` → `preparo`);
- **underscore trattati come spazi** (`Bellini_Music_Official` →
  `bellini music official`);
- **punteggiatura** trasformata in spazi;
- **contenuto tra parentesi tonde rimosso** ai fini del confronto — es.
  `Titanium (Extended Mix)` → `titanium` (ma le parole tra parentesi vengono poi
  valutate a parte, vedi §4);
- articoli iniziali (`the`, `a`, `an`) e **anni a 4 cifre** rimossi.

Grazie alla riparazione mojibake e alla rimozione degli accenti, `Preparó` e
`PreparÃ³` sono considerati **la stessa parola**.

### Tolleranza per testi corrotti (mojibake) + verifica sul nome file

A volte un tag è corrotto in modo **non ricostruibile** automaticamente (per
esempio `PreparÃ3`, con una cifra al posto dell'accento). In questi casi il
software **non** conta subito quella parola come "diversa": se nel **titolo
Serato** compaiono simboli sospetti (`Ã`/`Â`), va a fare un **confronto sul nome
file**. Se la parola giusta e "pulita" è presente nel filename (es. `preparo`), il
software capisce che il token corrotto è in realtà la stessa parola e **non
applica nessuna penalità**. Il nome file fa quindi da "fonte di verità".

---

## 3. I due regimi di punteggio

Dopo aver scelto il candidato, il software verifica se **tutte le parole del
titolo richiesto** compaiono **nello stesso ordine** (come sottosequenza) nel
**titolo Serato** oppure nel **nome file**.

- **Titolo interamente presente** → si usa il **modello a contabilità** (§4):
  base **100%** meno penalità precise.
- **Titolo solo parziale** → si usano i **cancelli severi** (§5): il punteggio
  viene limitato a valori bassi (0%, 44% o 50%).

---

## 4. Il modello a contabilità (titolo interamente trovato)

Si parte da **100%** e si sottraggono le penalità qui sotto. **Tutte le penalità
si sommano.**

| Situazione | Effetto |
|------------|---------|
| L'**artista** è nella richiesta ma **non compare in nessuna colonna** del brano trovato (Artista, Song, Filename) | **tetto massimo 70%** |
| **Parola di TITOLO in più** nel brano trovato (parola vera, non richiesta, non a bassa rilevanza) | **−20% ciascuna** |
| **Parola di ARTISTA in più** nel brano trovato (parola vera, non richiesta) | **−5% totale** |
| **Parola a bassa rilevanza** fuori dalle parentesi (remix, official, video, music…) non richiesta | **−5% totale** |
| Qualsiasi parola **tra parentesi tonde** (descrittore o parola non richiesta) | **−1% totale** |
| Una parola del **titolo richiesto** trovata **solo nel nome file** (non nella Song né nell'Artista) | **−1%** |

Note importanti:

- Una **parola di titolo in più** (es. la richiesta è *"Everything"* ma il brano
  trovato è *"Everything **she wants**"*) indica che il titolo è di fatto diverso:
  per questo pesa molto (**−20% a parola**).
- Una **parola di artista in più** pesa poco (**−5% totale**), perché spesso è solo
  il nome di chi ha caricato il brano o una variante (es. `ImagineDragons` scritto
  tutto attaccato, o un canale come `After Party82`).
- Le parole **tra parentesi tonde** hanno rilevanza ancora più bassa: qualunque
  cosa ci sia dentro costa al massimo **−1% totale**.
- La verifica della **presenza dell'artista** è "tollerante" (`ImagineDragons`
  soddisfa `imagine`), mentre il conteggio delle **parole in più** è "esatto"
  (quindi `ImagineDragons` attaccato conta comunque come una parola di artista in
  più).

---

## 5. I cancelli severi (titolo solo parziale)

Quando il titolo richiesto **non** è interamente presente in ordine, il match è
poco affidabile e valgono questi limiti:

- **Parole mancanti**: se una parola significativa della richiesta non compare nel
  brano → **max 50%**.
- **Presenza del titolo**: se le parole del titolo non compaiono in nessun campo →
  **max 45%**.
- **Titolo in ordine**: le parole del titolo devono comparire nello stesso ordine
  nel nome file o nel titolo Serato:
  - nessuna parola trovata → **0%** (riga trattata come *mancante*);
  - trovate ma parziali / in ordine sbagliato → **max 44%**.
- **Bonus contenimento**: se il titolo richiesto è comunque contenuto in quello
  trovato, il punteggio sale ad almeno **62%**.
- **Aggiustamento PSYTRANCE** e **penalità BPM** (quest'ultima opzionale) possono
  intervenire come rifiniture.

---

## 6. Parole a "bassa rilevanza"

Sono descrittori di versione/formato/media che **non cambiano davvero il brano**.
Quando compaiono nel brano trovato ma non nella richiesta, non fanno crollare il
punteggio: costano solo **−5% totale** (fuori parentesi) o **−1% totale** (se
sono tra parentesi):

`remix`, `mashup`, `dub`, `vip`, `flip`, `bootleg`, `rework`, `discomix`,
`mashboot`, `remake`, `revibe`, `reloaded`, `original`, `extended`, `edit`,
`mix`, `version`, `radio`, `club`, `clean`, `dirty`, `official`, `oficial`,
`ufficiale`, `music`, `video`, `audio`, `mv`, `clip`, `lyric`, `lyrics`,
`visualizer`, e sigle di bitrate come `128kbit_AAC`, `320 kbps`.

---

## 7. Esempi commentati (con calcolo)

Tutti gli esempi seguenti rientrano nel **modello a contabilità** (il titolo
richiesto è interamente presente nel brano trovato).

| Richiesta | Brano trovato (Song / Artista) | Valore | Calcolo |
|-----------|--------------------------------|--------|---------|
| `Michael Bublé - Everything` | *Everything she wants (…Bootleg Remix)* / Wham | **~29%** | Artista "Michael Bublé" **assente ovunque** → tetto **70%**; *"she"* e *"wants"* sono 2 parole di titolo in più → **−40%** (−20% ciascuna); contenuto tra parentesi → **−1%** |
| `Bellini - Carnaval (Original Version)` | *Bellini - Carnaval (Original Version)* / After Party82 | **94%** | Artista "bellini" presente nella Song; artista in più "After Party82" → **−5%**; `(Original Version)` tra parentesi → **−1%** |
| `Bellini - Samba De Janeiro` | *Bellini - Samba De Janeiro* / Bellini_Music_Official | **95%** | Titolo identico; `music`/`official` sono a bassa rilevanza fuori parentesi → **−5%** |
| `Imagine Dragons - On Top Of The World` | *…On Top Of The World (Official Music Video)* / ImagineDragons | **94%** | Artista "ImagineDragons" (attaccato) conta come artista in più → **−5%**; `(Official Music Video)` tra parentesi → **−1%** |
| `KING ÁFRICA "EL CAMALEÓN"` | *KING ÁFRICA "EL CAMALEÓN"* / YouMoreTv - Espectáculo | **95%** | Titolo identico; artista in più "YouMoreTv Espectáculo" → **−5%** |
| `Ozuna - Se Preparó (Video Oficial) \| Odisea` | Song: *Ozuna - Se PreparÃ3…* (corrotto) · Filename: *Ozuna - Se Preparó…* (pulito) | **99%** | Il titolo Serato è corrotto (`PreparÃ3`), ma la parola pulita `preparo` è nel nome file → il token corrotto viene riconosciuto e **non penalizzato**; resta solo `(Video Oficial)` tra parentesi → **−1%** |
| `Ricky Martin - La Mordidita ft. Yotuel` | *Ricky Martin - La Mordidita* / Ricky Martin | **99%** | Tutte le parole del titolo ci sono; *"yotuel"* è presente **solo nel nome file** → **−1%** |

---

## 8. Da punteggio a colore ed etichetta

Il punteggio finale determina il **colore** della riga e il livello di confidenza:

| Punteggio | Confidenza | Colore riga (tema chiaro) |
|-----------|-----------|---------------------------|
| 95–100% | Esatto | verde pieno |
| 75–94% | Alta | verde |
| 55–74% | Media | arancione/giallo |
| 1–54% | Bassa | rosso chiaro |
| 0% | Mancante | rosa/rosso (trattata come non trovata) |

Colori speciali:

- **Ciano/azzurro**: due o più righe della playlist puntano allo **stesso file**
  (possibile duplicato nella richiesta). Se cambi versione dal menu della colonna
  **Trovati** e i duplicati spariscono, il colore torna normale.
- **▼ con numero** nella colonna **Trovati**: ci sono più candidati sopra la
  soglia — clicca per scegliere la versione giusta.

---

## 9. Riepilogo del flusso

```
Brano richiesto
   │
   ├─ Bloccato (composer/title lock)? ── sì ─▶ 100%
   │                                    no
   ▼
Cascata: Exact ▶ Word coverage ▶ Composite ▶ Fuzzy ▶ Title partial ▶ Filename
   │
   ▼
Il titolo richiesto è interamente presente (in ordine) nella Song o nel Filename?
   │
   ├─ SÌ ─▶ Modello a contabilità: 100%
   │          − 30% tetto se artista assente (base scende a 70%)
   │          − 20% per ogni parola di TITOLO in più
   │          − 5%  se c'è una parola di ARTISTA in più
   │          − 5%  parola a bassa rilevanza fuori parentesi
   │          − 1%  qualcosa tra parentesi tonde
   │          − 1%  parola di titolo trovata solo nel nome file
   │
   └─ NO ─▶ Cancelli severi:
              parole mancanti → max 50%
              presenza titolo → max 45%
              titolo in ordine → 0% oppure max 44%
              (+ bonus contenimento, PSYTRANCE, BPM)
   ▼
Punteggio finale (0–100%) ▶ colore + etichetta confidenza
```

---

*Documento generato per Serato Playlist Automation. Le soglie e le liste di
parole vivono in `serato_automation/track_matcher.py`.*
