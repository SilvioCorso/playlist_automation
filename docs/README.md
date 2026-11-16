# Documentazione — Serato Playlist Automation v4.5

| File | Pubblico | Descrizione |
|------|----------|-------------|
| [contesto.md](./contesto.md) | Sviluppatore / AI | **⭐ Contesto completo — leggi per prima cosa in ogni nuova sessione** |
| [documentazione_tecnica.md](./documentazione_tecnica.md) | Sviluppatore | Architettura, moduli, layout UI v4.5, config, pattern |
| [architettura_tecnica.md](./architettura_tecnica.md) | Sviluppatore | Diagramma flusso dati, threading, classi UI |
| [prompt_next_ia.md](./prompt_next_ia.md) | Sviluppatore / AI | Blocco prompt copia-incolla per nuove sessioni |
| [roadmap_miglioramenti.md](./roadmap_miglioramenti.md) | Product / Dev | Proposte future e sprint consigliati |
| [algoritmo_percentuali.md](./algoritmo_percentuali.md) | Utente / Dev | Algoritmo scoring % (apribile da UI) |
| [faq_troubleshooting.md](./faq_troubleshooting.md) | Utente | FAQ e risoluzione problemi |
| [audit_codice.md](./audit_codice.md) | Sviluppatore | Audit qualità codice |
| [articolo_blog.md](./articolo_blog.md) | Marketing | Template articolo blog |

- **Nuova sessione AI?** Leggi `contesto.md` + `prompt_next_ia.md`
- **Versione documentata:** v4.5

Indice dei file in questa cartella.

| File | Pubblico | Descrizione |
|------|----------|-------------|
| [istruzioni.docx](./istruzioni.docx) | Utente finale | Guida completa passo-passo (Word) |
| [faq_troubleshooting.md](./faq_troubleshooting.md) | Utente finale | Domande frequenti e risoluzione problemi |
| [algoritmo_percentuali.md](./algoritmo_percentuali.md) | Utente finale / Sviluppatore | Come viene calcolata la % di match (con esempi). Apribile dal bottone "Come si calcola la %" nell'app |
| [articolo_blog.md](./articolo_blog.md) | Marketing / blog | Articolo promozionale con focus ROI per DJ |
| [prompt_next_ia.md](./prompt_next_ia.md) | Sviluppatore / AI | Prompt di bootstrap per sessioni Cursor/ChatGPT |
| [architettura_tecnica.md](./architettura_tecnica.md) | Sviluppatore | Moduli, flussi, threading, estensioni |
| [audit_codice.md](./audit_codice.md) | Sviluppatore / AI | Audit qualità codice, refactoring e roadmap feature |
| [contesto.md](./contesto.md) | Sviluppatore / AI | **⭐ Contesto completo v4.3 — leggi per prima cosa in ogni nuova sessione** |

## Suggerimenti d'uso

- **Nuovo utente?** Inizia da `istruzioni.docx`, poi consulta la FAQ se qualcosa non funziona.
- **Nuova sessione AI per sviluppare?** Leggi `contesto.md` — contiene tutto: architettura, config, feature v4.3, pattern di sviluppo.
- **Post sul blog?** Personalizza CTA e link in `articolo_blog.md`.

## Note

- La versione documentata è **v4.3** (allineata al titolo finestra dell'app).
- `python-docx` serve solo per rigenerare `istruzioni.docx`; non è una dipendenza runtime dell'app.
