# Cómo se calcula el porcentaje de coincidencia

Este documento explica **paso a paso** cómo el software asigna el
porcentaje (columna **Valor**) a cada pista de la playlist al compararla
con tu biblioteca musical. Al final encontrarás varios **ejemplos concretos** con el
cálculo detallado.

> En resumen: para cada pista solicitada el software busca el mejor candidato en la
> biblioteca con una **cascada de técnicas de comparación**. Luego, si el **título
> solicitado está completamente presente** en la pista encontrada, calcula la puntuación con
> un **modelo contable**: parte de **100%** y resta penalizaciones precisas.
> Si en cambio el título está solo parcialmente presente, entran en juego **umbrales estrictos**
> que limitan mucho la puntuación.

---

## 1. Prioridad absoluta: los candados (100% garantizado)

Antes de cualquier comparación, el software comprueba si la pista está **bloqueada**.
Si lo está, la puntuación es **100% fija** y todo lo demás se omite.

Existen dos tipos de candado:

1. **Composer lock** — la etiqueta `[lock]` está escrita **dentro de los metadatos del archivo
   de audio** (campo compositor). Es la más robusta: sobrevive a movimientos del
   archivo y cambios de ordenador.
2. **Title lock** — una correspondencia *título → archivo* que has confirmado tú,
   guardada en el archivo `title_locks.json`.

En ambos casos basta con que el título solicitado esté **contenido** en el título de la
pista bloqueada. Para quitar el 100%, haz clic en el candado de la fila para
desbloquearla: la puntuación se recalculará con normalidad.

---

## 2. La cascada de búsqueda

Si la pista **no** está bloqueada, el software busca el mejor candidato probando
en orden estas técnicas. **Se detiene en la primera que da un resultado válido.**

| # | Pasada | Qué hace |
|---|--------|----------|
| 1 | **Exact** | Artista+título *normalizados* idénticos |
| 2 | **Word coverage** | Todas las palabras de la solicitud están presentes en la pista |
| 3 | **Composite** | Similitud ponderada: **artista 30%** + **título 70%** |
| 4 | **Fuzzy** | Similitud "difusa" tolerante al orden y variantes |
| 5 | **Title partial** | Similitud parcial solo en el título |
| 6 | **Filename** | Comparación con el **nombre del archivo** (útil si los tags están vacíos) |

### La estructura "Artista - Título"

Si la solicitud usa la estructura **`Artista - Título`** (con el guion, o
`:`, `|`, `/`), el software separa los dos elementos y los usa de forma distinta: sabe
cuál es el artista y cuál el título. Esto hace el cálculo más preciso (véase el
modelo contable, §3).

### Qué es la "normalización"

Antes de comparar, los textos se limpian para que las diferencias irrelevantes
no cuenten:

- todo en **minúsculas**;
- **reparación de codificación (mojibake)**: textos guardados con doble codificación
  UTF-8 se restauran, por lo que `PreparÃ³` se lee como `Preparó`;
- **acentos** eliminados (`Beyoncé` → `beyonce`, `Preparó` → `preparo`);
- **guiones bajos tratados como espacios** (`Bellini_Music_Official` →
  `bellini music official`);
- **puntuación** convertida en espacios;
- **contenido entre paréntesis redondos eliminado** a efectos de comparación — p. ej.
  `Titanium (Extended Mix)` → `titanium` (pero las palabras entre paréntesis se evalúan
  aparte, véase §4);
- artículos iniciales (`the`, `a`, `an`) y **años de 4 cifras** eliminados.

Gracias a la reparación mojibake y a la eliminación de acentos, `Preparó` y
`PreparÃ³` se consideran **la misma palabra**.

### Tolerancia para textos corruptos (mojibake) + verificación en el nombre de archivo

A veces un tag está corrupto de forma **no reconstruible** automáticamente (por
ejemplo `PreparÃ3`, con un dígito en lugar del acento). En estos casos el
software **no** cuenta de inmediato esa palabra como "diferente": si en el **título
Serato** aparecen símbolos sospechosos (`Ã`/`Â`), hace una **comparación con el nombre
del archivo**. Si la palabra correcta y "limpia" está presente en el filename (p. ej. `preparo`), el
software entiende que el token corrupto es en realidad la misma palabra y **no
aplica ninguna penalización**. El nombre del archivo actúa así como "fuente de verdad".

---

## 3. Los dos regímenes de puntuación

Tras elegir el candidato, el software comprueba si **todas las palabras del
título solicitado** aparecen **en el mismo orden** (como subsecuencia) en el
**título Serato** o en el **nombre del archivo**.

- **Título completamente presente** → se usa el **modelo contable** (§4):
  base **100%** menos penalizaciones precisas.
- **Título solo parcial** → se usan **umbrales estrictos** (§5): la puntuación
  se limita a valores bajos (0%, 44% o 50%).

---

## 4. El modelo contable (título completamente encontrado)

Se parte de **100%** y se restan las penalizaciones siguientes. **Todas las penalizaciones
se suman.**

| Situación | Efecto |
|-----------|--------|
| El **artista** está en la solicitud pero **no aparece en ninguna columna** de la pista encontrada (Artist, Song, Filename) | **tope máximo 70%** |
| **Palabra de TÍTULO extra** en la pista encontrada (palabra real, no solicitada, no de baja relevancia) | **−20% cada una** |
| **Palabra de ARTISTA extra** en la pista encontrada (palabra real, no solicitada) | **−5% total** |
| **Palabra de baja relevancia** fuera de paréntesis (remix, official, video, music…) no solicitada | **−5% total** |
| Cualquier palabra **entre paréntesis redondos** (descriptor o palabra no solicitada) | **−1% total** |
| Una palabra del **título solicitado** encontrada **solo en el nombre del archivo** (no en Song ni Artist) | **−1%** |

Notas importantes:

- Una **palabra de título extra** (p. ej. la solicitud es *"Everything"* pero la pista
  encontrada es *"Everything **she wants**"*) indica que el título es de hecho distinto:
  por eso pesa mucho (**−20% por palabra**).
- Una **palabra de artista extra** pesa poco (**−5% total**), porque a menudo es solo
  el nombre de quien subió la pista o una variante (p. ej. `ImagineDragons` escrito
  junto, o un canal como `After Party82`).
- Las palabras **entre paréntesis redondos** tienen relevancia aún más baja: lo que
  haya dentro cuesta como máximo **−1% total**.
- La comprobación de **presencia del artista** es "tolerante" (`ImagineDragons`
  satisface `imagine`), mientras que el recuento de **palabras extra** es "exacto"
  (por lo tanto `ImagineDragons` junto cuenta igual como palabra de artista extra).

---

## 5. Umbrales estrictos (título solo parcial)

Cuando el título solicitado **no** está completamente presente en orden, la coincidencia es
poco fiable y valen estos límites:

- **Palabras faltantes**: si una palabra significativa de la solicitud no aparece en la
  pista → **máx. 50%**.
- **Presencia del título**: si las palabras del título no aparecen en ningún campo →
  **máx. 45%**.
- **Título en orden**: las palabras del título deben aparecer en el mismo orden
  en el nombre del archivo o el título Serato:
  - ninguna palabra encontrada → **0%** (fila tratada como *faltante*);
  - encontradas pero parciales / en orden incorrecto → **máx. 44%**.
- **Bonus de contención**: si el título solicitado está contenido en el encontrado,
  la puntuación sube al menos a **62%**.
- El **ajuste PSYTRANCE** y la **penalización BPM** (esta última opcional) pueden
  intervenir como refinamientos.

---

## 6. Palabras de "baja relevancia"

Son descriptores de versión/formato/medio que **no cambian realmente la pista**.
Cuando aparecen en la pista encontrada pero no en la solicitud, no hacen caer la
puntuación: cuestan solo **−5% total** (fuera de paréntesis) o **−1% total** (si
están entre paréntesis):

`remix`, `mashup`, `dub`, `vip`, `flip`, `bootleg`, `rework`, `discomix`,
`mashboot`, `remake`, `revibe`, `reloaded`, `original`, `extended`, `edit`,
`mix`, `version`, `radio`, `club`, `clean`, `dirty`, `official`, `oficial`,
`ufficiale`, `music`, `video`, `audio`, `mv`, `clip`, `lyric`, `lyrics`,
`visualizer`, y siglas de bitrate como `128kbit_AAC`, `320 kbps`.

---

## 7. Ejemplos comentados (con cálculo)

Todos los ejemplos siguientes entran en el **modelo contable** (el título
solicitado está completamente presente en la pista encontrada).

| Solicitud | Pista encontrada (Song / Artist) | Valor | Cálculo |
|-----------|----------------------------------|-------|---------|
| `Michael Bublé - Everything` | *Everything she wants (…Bootleg Remix)* / Wham | **~29%** | Artista "Michael Bublé" **ausente en todas partes** → tope **70%**; *"she"* y *"wants"* son 2 palabras de título extra → **−40%** (−20% cada una); contenido entre paréntesis → **−1%** |
| `Bellini - Carnaval (Original Version)` | *Bellini - Carnaval (Original Version)* / After Party82 | **94%** | Artista "bellini" presente en Song; artista extra "After Party82" → **−5%**; `(Original Version)` entre paréntesis → **−1%** |
| `Bellini - Samba De Janeiro` | *Bellini - Samba De Janeiro* / Bellini_Music_Official | **95%** | Título idéntico; `music`/`official` son de baja relevancia fuera de paréntesis → **−5%** |
| `Imagine Dragons - On Top Of The World` | *…On Top Of The World (Official Music Video)* / ImagineDragons | **94%** | Artista "ImagineDragons" (junto) cuenta como artista extra → **−5%**; `(Official Music Video)` entre paréntesis → **−1%** |
| `KING ÁFRICA "EL CAMALEÓN"` | *KING ÁFRICA "EL CAMALEÓN"* / YouMoreTv - Espectáculo | **95%** | Título idéntico; artista extra "YouMoreTv Espectáculo" → **−5%** |
| `Ozuna - Se Preparó (Video Oficial) \| Odisea` | Song: *Ozuna - Se PreparÃ3…* (corrupto) · Filename: *Ozuna - Se Preparó…* (limpio) | **99%** | El título Serato está corrupto (`PreparÃ3`), pero la palabra limpia `preparo` está en el nombre del archivo → el token corrupto se reconoce y **no se penaliza**; solo queda `(Video Oficial)` entre paréntesis → **−1%** |
| `Ricky Martin - La Mordidita ft. Yotuel` | *Ricky Martin - La Mordidita* / Ricky Martin | **99%** | Todas las palabras del título están presentes; *"yotuel"* está presente **solo en el nombre del archivo** → **−1%** |

---

## 8. De puntuación a color y etiqueta

La puntuación final determina el **color** de la fila y el nivel de confianza:

| Puntuación | Confianza | Color de fila (tema claro) |
|------------|-----------|----------------------------|
| 95–100% | Exacta | verde sólido |
| 75–94% | Alta | verde |
| 55–74% | Media | naranja/amarillo |
| 1–54% | Baja | rojo claro |
| 0% | Faltante | rosa/rojo (tratada como no encontrada) |

Colores especiales:

- **Cian/azul claro**: dos o más filas de la playlist apuntan al **mismo archivo**
  (posible duplicado en la solicitud). Si cambias la versión desde el menú de la columna
  **Encontrados** y los duplicados desaparecen, el color vuelve a la normalidad.
- **▼ con número** en la columna **Encontrados**: hay más candidatos por encima del
  umbral — haz clic para elegir la versión correcta.

---

## 9. Resumen del flujo

```
Pista solicitada
   │
   ├─ ¿Bloqueada (composer/title lock)? ── sí ─▶ 100%
   │                                    no
   ▼
Cascada: Exact ▶ Word coverage ▶ Composite ▶ Fuzzy ▶ Title partial ▶ Filename
   │
   ▼
¿El título solicitado está completamente presente (en orden) en Song o Filename?
   │
   ├─ SÍ ─▶ Modelo contable: 100%
   │          − 30% tope si artista ausente (base baja a 70%)
   │          − 20% por cada palabra de TÍTULO extra
   │          − 5%  si hay palabra de ARTISTA extra
   │          − 5%  palabra de baja relevancia fuera de paréntesis
   │          − 1%  algo entre paréntesis redondos
   │          − 1%  palabra de título encontrada solo en el nombre del archivo
   │
   └─ NO ─▶ Umbrales estrictos:
              palabras faltantes → máx. 50%
              presencia del título → máx. 45%
              título en orden → 0% o máx. 44%
              (+ bonus contención, PSYTRANCE, BPM)
   ▼
Puntuación final (0–100%) ▶ color + etiqueta de confianza
```

---

*Documento generado para Serato Playlist Automation. Los umbrales y las listas de
palabras están en `serato_automation/track_matcher.py`.*
