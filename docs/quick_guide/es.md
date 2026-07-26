# Serato Playlist Automation — Guía rápida

*Herramienta profesional para DJ — by SirvioDJ*

---

## Para qué sirve

Convierte una **playlist del cliente** (texto, archivo, URL de YouTube/Spotify) en una **crate de Serato** lista para el evento, mostrando al instante qué pistas tienes en la biblioteca y cuáles faltan.

**Ahorro típico:** de horas de búsqueda manual a unos minutos de revisión guiada.

---

## Flujo en 4 pasos

### ① Configura la biblioteca

1. Establece la **carpeta de música** (p. ej. `F:/`)
2. Clic en **Escanear biblioteca** — el primer escaneo puede tardar; los siguientes usan caché
3. Comprueba el estado verde: *«Biblioteca: N pistas»*

### ② Carga la playlist del cliente

Pestaña **Playlist del cliente**:

- **Importar desde URL** — YouTube o Spotify
- **Cargar archivo** — `.txt`, `.csv`, `.m3u`
- O **pega los títulos** directamente

Formato recomendado: `Artista - Título` (uno por línea).

### ③ Compara y revisa

**Coincidir con biblioteca** → pestaña **Resultados**:

| Columna | Utilidad |
|---------|----------|
| **Score %** | Qué tan bien coincide la pista encontrada |
| **Encontrado** | Menú con candidatos alternativos |
| **🔒 Lock** | Fija un match al 100 % |
| **Player** | Escucha sin salir de la app |
| **Seleccionar** | Elige pistas para la crate |

Usa **Seleccionar todo ≥ X %** para marcar solo matches por encima del umbral.

### ④ Exporta

- **Crear crate Serato** — genera el `.crate` (reinicia Serato)
- **Guardar faltantes...** — lista `.txt` de pistas a comprar o verificar

---

## Herramientas avanzadas

### Mantenimiento (pestaña Edición)

| Función | Cuándo usarla |
|---------|---------------|
| **Limpiar biblioteca** | Buscar palabras o mojibake (`PreparÃ3`) |
| **Encontrar diferencias** | Pistas en disco pero no en Serato |
| **Duplicados** | Mismo título+artista varias veces |
| **Actualizar Serato** | Sincronizar metadatos (Serato cerrado) |

### Botón Guía rápida

**Guía rápida** abre siempre este documento.

### Algoritmo de porcentaje

El botón del pie explica cómo se calcula cada score.

---

## Consejos pro

- **Score ≥ 50 %** como punto de partida; sube a 70–80 % en eventos formales
- Usa **Lock** en matches seguros antes de cambiar candidatos
- Filas **duplicadas** (mismo archivo) en cian
- **Pantalla completa** en Resultados/Edición para playlists largas
- Tras **Eliminar** duplicados: cierra y reabre Serato

---

## Soporte

Feedback y licencia Pro: [sirviodj.it](https://sirviodj.it/blog/serato-playlist-automation-risparmia-tempo#formContato)
