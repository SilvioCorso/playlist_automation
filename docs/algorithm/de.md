# Wie der Match-Prozentsatz berechnet wird

Dieses Dokument erklärt **Schritt für Schritt**, wie die Software den
Prozentsatz (Spalte **Wert**) jedem Titel der Playlist zuweist, wenn sie ihn
mit Ihrer Musikbibliothek vergleicht. Am Ende finden Sie mehrere **konkrete Beispiele** mit
detaillierter Berechnung.

> Kurz gesagt: Für jeden angeforderten Titel sucht die Software den besten Kandidaten in der
> Bibliothek mit einer **Kaskade von Vergleichstechniken**. Wenn dann der **angeforderte Titel
> vollständig enthalten** ist im gefundenen Titel, berechnet sie die Punktzahl mit
> einem **Buchführungsmodell**: Ausgangspunkt **100%**, abzüglich präziser Strafen.
> Ist der Titel nur teilweise enthalten, greifen **strenge Schwellen**, die
> die Punktzahl stark begrenzen.

---

## 1. Absolute Priorität: Sperren (100% garantiert)

Vor jedem Vergleich prüft die Software, ob der Titel **gesperrt** ist.
Wenn ja, beträgt die Punktzahl **fest 100%** und alles andere wird übersprungen.

Es gibt zwei Arten von Sperren:

1. **Composer lock** — das Tag `[lock]` steht **in den Metadaten der Audiodatei**
   (Komponistenfeld). Es ist am robustesten: überlebt Dateiverschiebungen und
   Computerwechsel.
2. **Title lock** — eine von Ihnen bestätigte Zuordnung *Titel → Datei*,
   gespeichert in der Datei `title_locks.json`.

In beiden Fällen reicht es, dass der angeforderte Titel **enthalten** ist im Titel des
gesperrten Titels. Um die 100% zu entfernen, klicken Sie auf das Schloss-Symbol der Zeile, um
sie zu entsperren: Die Punktzahl wird normal neu berechnet.

---

## 2. Die Suchkaskade

Ist der Titel **nicht** gesperrt, sucht die Software den besten Kandidaten, indem sie
diese Techniken der Reihe nach ausprobiert. **Sie stoppt bei der ersten, die ein gültiges Ergebnis liefert.**

| # | Durchlauf | Was er tut |
|---|-----------|------------|
| 1 | **Exact** | *Normalisierter* Künstler+Titel identisch |
| 2 | **Word coverage** | Alle Wörter der Anfrage sind im Titel vorhanden |
| 3 | **Composite** | Gewichtete Ähnlichkeit: **Künstler 30%** + **Titel 70%** |
| 4 | **Fuzzy** | „Unscharfe" Ähnlichkeit, tolerant gegenüber Reihenfolge und Varianten |
| 5 | **Title partial** | Teilweise Ähnlichkeit nur am Titel |
| 6 | **Filename** | Vergleich mit dem **Dateinamen** (nützlich bei leeren Tags) |

### Die Struktur „Künstler - Titel"

Verwendet die Anfrage die Struktur **`Künstler - Titel`** (mit Bindestrich oder
`:`, `|`, `/`), trennt die Software die beiden Elemente und nutzt sie getrennt: Sie weiß,
welcher Teil Künstler und welcher Titel ist. Das macht die Berechnung genauer (siehe
Buchführungsmodell, §3).

### Was „Normalisierung" bedeutet

Vor dem Vergleich werden Texte bereinigt, damit irrelevante Unterschiede
nicht zählen:

- alles in **Kleinbuchstaben**;
- **Kodierungsreparatur (mojibake)**: Texte mit doppelter UTF-8-Kodierung
  werden wiederhergestellt, also wird `PreparÃ³` als `Preparó` gelesen;
- **Akzente** entfernt (`Beyoncé` → `beyonce`, `Preparó` → `preparo`);
- **Unterstriche als Leerzeichen behandelt** (`Bellini_Music_Official` →
  `bellini music official`);
- **Interpunktion** in Leerzeichen umgewandelt;
- **Inhalt in runden Klammern entfernt** für den Vergleich — z. B.
  `Titanium (Extended Mix)` → `titanium` (Wörter in Klammern werden aber
  separat bewertet, siehe §4);
- führende Artikel (`the`, `a`, `an`) und **4-stellige Jahreszahlen** entfernt.

Dank Mojibake-Reparatur und Akzententfernung gelten `Preparó` und
`PreparÃ³` als **dasselbe Wort**.

### Toleranz für beschädigten Text (mojibake) + Dateinamenprüfung

Manchmal ist ein Tag **nicht automatisch rekonstruierbar** beschädigt (z. B.
`PreparÃ3`, mit einer Ziffer statt Akzent). In diesen Fällen zählt die
Software dieses Wort **nicht** sofort als „anders": Enthält der **Serato-Titel**
verdächtige Symbole (`Ã`/`Â`), führt sie einen **Vergleich mit dem Dateinamen** durch.
Ist das richtige „saubere" Wort im Dateinamen vorhanden (z. B. `preparo`), erkennt die
Software, dass das beschädigte Token dasselbe Wort ist, und **wendet keine Strafe an**.
Der Dateiname dient also als „Quelle der Wahrheit".

---

## 3. Die zwei Bewertungsregime

Nach der Kandidatenwahl prüft die Software, ob **alle Wörter des angeforderten Titels**
**in derselben Reihenfolge** (als Teilsequenz) im **Serato-Titel** oder im **Dateinamen** vorkommen.

- **Titel vollständig vorhanden** → **Buchführungsmodell** (§4):
  Basis **100%** abzüglich präziser Strafen.
- **Titel nur teilweise** → **strenge Schwellen** (§5): Die Punktzahl
  ist auf niedrige Werte begrenzt (0%, 44% oder 50%).

---

## 4. Das Buchführungsmodell (Titel vollständig gefunden)

Ausgangspunkt **100%**, abzüglich der unten stehenden Strafen. **Alle Strafen
addieren sich.**

| Situation | Wirkung |
|-----------|---------|
| Der **Künstler** steht in der Anfrage, **erscheint aber in keiner Spalte** des gefundenen Titels (Artist, Song, Filename) | **Obergrenze 70%** |
| **Zusätzliches TITEL-Wort** im gefundenen Titel (echtes Wort, nicht angefordert, nicht geringe Relevanz) | **−20% je Wort** |
| **Zusätzliches KÜNSTLER-Wort** im gefundenen Titel (echtes Wort, nicht angefordert) | **−5% gesamt** |
| **Wort geringer Relevanz** außerhalb von Klammern (remix, official, video, music…) nicht angefordert | **−5% gesamt** |
| Beliebiges Wort **in runden Klammern** (Deskriptor oder nicht angefordertes Wort) | **−1% gesamt** |
| Ein Wort aus dem **angeforderten Titel** nur im **Dateinamen** gefunden (nicht in Song oder Artist) | **−1%** |

Wichtige Hinweise:

- Ein **zusätzliches Titelwort** (z. B. Anfrage *„Everything"*, gefundener Titel
  *„Everything **she wants**"*) zeigt, dass der Titel faktisch anders ist:
  deshalb wiegt es schwer (**−20% pro Wort**).
- Ein **zusätzliches Künstlerwort** wiegt wenig (**−5% gesamt**), weil es oft nur
  der Name des Uploaders oder eine Variante ist (z. B. `ImagineDragons` zusammengeschrieben
  oder ein Kanal wie `After Party82`).
- Wörter **in runden Klammern** haben noch geringere Relevanz: Was auch immer
  darin steht, kostet höchstens **−1% gesamt**.
- Die **Künstlerpräsenz** ist „tolerant" (`ImagineDragons`
  erfüllt `imagine`), während die Zählung **zusätzlicher Wörter** „exakt" ist
  (also zählt `ImagineDragons` zusammen trotzdem als zusätzliches Künstlerwort).

---

## 5. Strenge Schwellen (Titel nur teilweise)

Ist der angeforderte Titel **nicht** vollständig in Reihenfolge vorhanden, ist der Match
unzuverlässig und diese Grenzen gelten:

- **Fehlende Wörter**: Fehlt ein bedeutungsvolles Wort der Anfrage im
  Titel → **max. 50%**.
- **Titelpräsenz**: Erscheinen die Titelwörter in keinem Feld →
  **max. 45%**.
- **Titel in Reihenfolge**: Die Titelwörter müssen in derselben Reihenfolge
  im Dateinamen oder Serato-Titel vorkommen:
  - keine Wörter gefunden → **0%** (Zeile als *fehlend* behandelt);
  - gefunden, aber teilweise / falsche Reihenfolge → **max. 44%**.
- **Containment-Bonus**: Ist der angeforderte Titel dennoch im gefundenen enthalten,
  steigt die Punktzahl auf mindestens **62%**.
- **PSYTRANCE-Anpassung** und **BPM-Strafe** (letztere optional) können
  als Feinabstimmung eingreifen.

---

## 6. Wörter „geringer Relevanz"

Das sind Versions-/Format-/Medien-Deskriptoren, die **den Titel wirklich nicht ändern**.
Erscheinen sie im gefundenen Titel, aber nicht in der Anfrage, stürzt die Punktzahl nicht ab:
Sie kosten nur **−5% gesamt** (außerhalb von Klammern) oder **−1% gesamt** (innerhalb von Klammern):

`remix`, `mashup`, `dub`, `vip`, `flip`, `bootleg`, `rework`, `discomix`,
`mashboot`, `remake`, `revibe`, `reloaded`, `original`, `extended`, `edit`,
`mix`, `version`, `radio`, `club`, `clean`, `dirty`, `official`, `oficial`,
`ufficiale`, `music`, `video`, `audio`, `mv`, `clip`, `lyric`, `lyrics`,
`visualizer`, und Bitrate-Kürzel wie `128kbit_AAC`, `320 kbps`.

---

## 7. Kommentierte Beispiele (mit Berechnung)

Alle folgenden Beispiele fallen unter das **Buchführungsmodell** (der angeforderte Titel
ist vollständig im gefundenen Titel enthalten).

| Anfrage | Gefundener Titel (Song / Artist) | Wert | Berechnung |
|---------|----------------------------------|------|------------|
| `Michael Bublé - Everything` | *Everything she wants (…Bootleg Remix)* / Wham | **~29%** | Künstler „Michael Bublé" **nirgends vorhanden** → Obergrenze **70%**; *„she"* und *„wants"* sind 2 zusätzliche Titelwörter → **−40%** (−20% je); Inhalt in Klammern → **−1%** |
| `Bellini - Carnaval (Original Version)` | *Bellini - Carnaval (Original Version)* / After Party82 | **94%** | Künstler „bellini" in Song vorhanden; zusätzlicher Künstler „After Party82" → **−5%**; `(Original Version)` in Klammern → **−1%** |
| `Bellini - Samba De Janeiro` | *Bellini - Samba De Janeiro* / Bellini_Music_Official | **95%** | Identischer Titel; `music`/`official` geringe Relevanz außerhalb Klammern → **−5%** |
| `Imagine Dragons - On Top Of The World` | *…On Top Of The World (Official Music Video)* / ImagineDragons | **94%** | Künstler „ImagineDragons" (zusammen) zählt als zusätzlicher Künstler → **−5%**; `(Official Music Video)` in Klammern → **−1%** |
| `KING ÁFRICA "EL CAMALEÓN"` | *KING ÁFRICA "EL CAMALEÓN"* / YouMoreTv - Espectáculo | **95%** | Identischer Titel; zusätzlicher Künstler „YouMoreTv Espectáculo" → **−5%** |
| `Ozuna - Se Preparó (Video Oficial) \| Odisea` | Song: *Ozuna - Se PreparÃ3…* (beschädigt) · Filename: *Ozuna - Se Preparó…* (sauber) | **99%** | Serato-Titel beschädigt (`PreparÃ3`), aber sauberes Wort `preparo` im Dateinamen → beschädigtes Token erkannt und **nicht bestraft**; nur `(Video Oficial)` in Klammern → **−1%** |
| `Ricky Martin - La Mordidita ft. Yotuel` | *Ricky Martin - La Mordidita* / Ricky Martin | **99%** | Alle Titelwörter vorhanden; *„yotuel"* nur im **Dateinamen** → **−1%** |

---

## 8. Von Punktzahl zu Farbe und Bezeichnung

Die Endpunktzahl bestimmt die **Farbe** der Zeile und das Vertrauensniveau:

| Punktzahl | Vertrauen | Zeilenfarbe (helles Theme) |
|-----------|-----------|----------------------------|
| 95–100% | Exakt | Vollgrün |
| 75–94% | Hoch | Grün |
| 55–74% | Mittel | Orange/Gelb |
| 1–54% | Niedrig | Hellrot |
| 0% | Fehlend | Rosa/Rot (als nicht gefunden behandelt) |

Sonderfarben:

- **Cyan/Hellblau**: Zwei oder mehr Playlist-Zeilen verweisen auf **dieselbe Datei**
  (mögliches Duplikat in der Anfrage). Wenn Sie die Version über das Menü der Spalte **Gefunden**
  ändern und die Duplikate verschwinden, kehrt die Farbe zur Normalität zurück.
- **▼ mit Zahl** in der Spalte **Gefunden**: Es gibt mehrere Kandidaten über der
  Schwelle — klicken Sie, um die richtige Version zu wählen.

---

## 9. Ablaufübersicht

```
Angeforderter Titel
   │
   ├─ Gesperrt (composer/title lock)? ── ja ─▶ 100%
   │                                    nein
   ▼
Kaskade: Exact ▶ Word coverage ▶ Composite ▶ Fuzzy ▶ Title partial ▶ Filename
   │
   ▼
Ist der angeforderte Titel vollständig (in Reihenfolge) in Song oder Filename?
   │
   ├─ JA ─▶ Buchführungsmodell: 100%
   │          − 30% Obergrenze bei fehlendem Künstler (Basis fällt auf 70%)
   │          − 20% pro zusätzlichem TITEL-Wort
   │          − 5%  bei zusätzlichem KÜNSTLER-Wort
   │          − 5%  Wort geringer Relevanz außerhalb Klammern
   │          − 1%  etwas in runden Klammern
   │          − 1%  Titelwort nur im Dateinamen gefunden
   │
   └─ NEIN ─▶ Strenge Schwellen:
              fehlende Wörter → max. 50%
              Titelpräsenz → max. 45%
              Titel in Reihenfolge → 0% oder max. 44%
              (+ Containment-Bonus, PSYTRANCE, BPM)
   ▼
Endpunktzahl (0–100%) ▶ Farbe + Vertrauensbezeichnung
```

---

*Dokument erstellt für Serato Playlist Automation. Schwellen und Wortlisten
befinden sich in `serato_automation/track_matcher.py`.*
