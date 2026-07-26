# Serato Playlist Automation — Kurzanleitung

*Professionelles DJ-Tool — by SirvioDJ*

---

## Wofür es da ist

Verwandelt eine **Kunden-Playlist** (Text, Datei, YouTube-/Spotify-URL) in eine **Serato-Crate** für das Event und zeigt sofort, welche Titel in der Bibliothek sind und welche fehlen.

**Typische Zeitersparnis:** von Stunden manueller Suche auf wenige Minuten geführter Überprüfung.

---

## Ablauf in 4 Schritten

### ① Bibliothek einrichten

1. **Musikordner** festlegen (z. B. `F:/`)
2. **Bibliothek scannen** — der erste Scan kann einige Minuten dauern; spätere Scans nutzen den Cache
3. Grünen Status prüfen: *„Bibliothek: N Titel“*

### ② Kunden-Playlist laden

Tab **Kunden-Playlist**:

- **Von URL importieren** — YouTube oder Spotify
- **Datei laden** — `.txt`, `.csv`, `.m3u`
- Oder Titel **direkt einfügen**

Empfohlenes Format: `Künstler - Titel` (eine Zeile pro Titel).

### ③ Abgleichen und prüfen

**Mit Bibliothek abgleichen** → Tab **Ergebnisse**:

| Spalte | Nutzen |
|--------|--------|
| **Score %** | Wie gut der gefundene Titel zur Anfrage passt |
| **Gefunden** | Menü mit Alternativen bei mehreren Kandidaten |
| **🔒 Lock** | Match auf 100 % fixieren |
| **Player** | Anhören ohne die App zu verlassen |
| **Auswahl** | Titel für die Crate markieren |

**Alle ≥ X % markieren** wählt nur Matches über einer Schwelle.

### ④ Export

- **Serato-Crate erstellen** — erzeugt die `.crate`-Datei (Serato neu starten)
- **Fehlende speichern...** — `.txt`-Liste der fehlenden Titel

---

## Erweiterte Werkzeuge

### Bibliothekswartung (Tab Bearbeitung)

| Funktion | Wann nutzen |
|----------|-------------|
| **Bibliothek bereinigen** | Wörter in Metadaten oder Mojibake (`PreparÃ3`) |
| **Unterschiede finden** | Titel auf der Festplatte, aber nicht in Serato |
| **Duplikate** | Gleicher Titel+Künstler mehrfach — Exemplare löschen |
| **Serato aktualisieren** | Geänderte Metadaten in die Serato-Datenbank (Serato geschlossen) |

### Schaltfläche Kurzanleitung

**Kurzanleitung** öffnet immer dieses Dokument.

### Prozent-Algorithmus

Die Fußzeilen-Schaltfläche erklärt die Score-Berechnung im Detail.

---

## Profi-Tipps

- **Score ≥ 50 %** als Start für „Alle markieren“; 70–80 % für formelle Events
- **Lock** bei sicheren Matches vor dem Wechseln bei unklaren Zeilen
- **Duplikat**-Zeilen (gleiche Datei mehrfach) erscheinen in Cyan
- **Vollbild** in Ergebnisse/Bearbeitung für lange Playlists
- Nach **Löschen** von Duplikaten: Serato schließen und neu öffnen

---

## Support

Feedback und Pro-Lizenz: [sirviodj.it](https://sirviodj.it/blog/serato-playlist-automation-risparmia-tempo#formContato)
