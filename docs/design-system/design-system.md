# Sistema de Diseño — HTML del arnés SDLC

> **Versión 1.0.0** · Fuente única de verdad: [tokens.json](tokens.json) ·
> Emisor canónico: `skills/sdlc-orchestrator/scripts/design_tokens.py` ·
> Aplicable a: portal (`portal_lib.py`), inicio/dashboard (`harness_graph.py`),
> diagramas (`diagram_ir.py`), grafo de código (`code_graph.py`), visor md (`mdview.py`).

## 1. Principios

1. **Ningún color fuera de un token.** Los generadores emiten el bloque `:root` desde
   `design_tokens.py`; hardcodear `#rrggbb` en un generador es un bug de gobierno.
2. **Tema dual obligatorio.** Toda superficie funciona en `oscuro` y `claro` derivando
   de variables; un componente que no cambia de tema con el toggle es un bug.
3. **AA mínimo** para texto (4.5:1) y componentes de UI (3.0:1). Los pares auditados
   viven en `tokens.json → audit.pairs-aa` y se verifican con `design_tokens.py --check`.
4. **Fuente system-ui.** Cero dependencias externas; los portales deben verse bien
   offline. La escala vive en `tokens.json → font`.
5. **Los cuatro estados son contrato**: toda superficie con datos define
   loading / empty / error / success. Un flujo sin estado de error es un bug futuro.

## 2. Color

### 2.1 Roles semánticos (temas `oscuro` / `claro`)

| Token | Oscuro | Claro | Rol |
|---|---|---|---|
| `--bg` | `#0b1220` | `#eef2f7` | Fondo de aplicación |
| `--fg` | `#e2e8f0` | `#1e293b` | Texto principal |
| `--txt` | `#f1f5f9` | `#0f172a` | Máximo énfasis (títulos) |
| `--sub` | `#8ea0b8` | `#5b6b80` | Texto secundario |
| `--muted-aa` | `#8a99b0` | `#5b6b80` | Texto terciario **(AA)** |
| `--muted` | `#64748b` | `#64748b` | **Solo decorativo** (bordes/iconos). Nunca texto. |
| `--panel-bg` / `--panel-bd` | `#0f172a` / `#1e293b` | `#ffffff` / `#e2e8f0` | Paneles (topbar, sidebar, modales) |
| `--card-bg` | `#111c33` | `#f8fafc` | Tarjetas, inputs, botones |
| `--accent` | `#3b82f6` | `#2563eb` | Enlaces, activo, selección |
| `--accent-strong` | `#2563eb` | `#2563eb` | Relleno de botón primario |
| `--on-accent` | `#ffffff` | `#ffffff` | Texto sobre `--accent-strong` |
| `--ok` / `--warn` / `--bad` | `#22c55e` / `#f59e0b` / `#ef4444` | `#16a34a` / `#d97706` / `#dc2626` | Semáforo de estado |
| `--warn-text` | `#f59e0b` | `#92400e` | Texto de advertencia **(AA)** |
| `--tier` | `#f97316` | `#ea580c` | Nivel de riesgo |
| `--focus` | `#3b82f6` | `#2563eb` | Anillo `:focus-visible` |
| `--shadow` | `rgba(0,0,0,.35)` | `rgba(15,23,42,.12)` | Sombra base |

Grupos específicos: `--gline`/`--gnode` (grafos) y `--edge-label`, `--chip-bg`,
`--chip-bd`, `--life`, `--act-bg`, `--act-bd`, `--seq-msg`, `--seq-ret` (diagramas IR).

### 2.2 Contraste verificado (selección; el set completo lo audita `--check`)

| Par | Ratio | AA |
|---|---|---|
| osc: `--fg` sobre `--bg` | 15.2 | ✅ |
| osc: `--sub` sobre `--bg` | 7.0 | ✅ |
| osc: `--muted-aa` sobre `--bg` | 6.5 | ✅ |
| osc: `--muted` sobre `--bg` | 3.9 | ❌ → por eso es decorativo |
| osc: blanco sobre `--accent-strong` | 5.2 | ✅ |
| claro: `--accent` sobre `--bg` | 4.6 | ✅ |
| claro: `--warn-text` sobre `--bg` | ~5.9 | ✅ |
| claro: `--warn` (`#d97706`) sobre `--bg` | 2.8 | ❌ → como texto usar `--warn-text` |

## 3. Tipografía

Familia: `system-ui, 'Segoe UI', sans-serif` · Mono: `ui-monospace, 'Cascadia Code', Consolas, monospace`.
Base: `html { font-size: 15px }`; todo en `rem` para que el zoom A−/A+ escale **todo** el chrome.

| Token | rem | px | Uso |
|---|---|---|---|
| `font.size.2xs` | .67rem | 10 | Contadores, etiquetas de grupo |
| `font.size.xs` | .73rem | 11 | Migas, metadatos, tooltips |
| `font.size.sm` | .80rem | 12 | Texto auxiliar, resultados de búsqueda |
| `font.size.md` | .87rem | 13 | Botones, inputs, nav |
| `font.size.base` | 1rem | 15 | Cuerpo de documento |
| `font.size.lg` | 1.08rem | 16 | h2 |
| `font.size.xl` | 1.35rem | 20 | h1 / título de página |

Pesos: 400 regular · 500 medium · 600 semibold (botones, labels) · 700 bold · 800 extrabold (brand).

## 4. Espaciado, radios, sombras, motion

- **Espaciado** (base 4px): 1=.25rem · 2=.45rem (gap compacto) · 3=.7rem (padding inputs) · 4=1rem · 5=1.5rem (padding página) · 6=1.8rem · 7=3rem.
- **Radios**: sm=4px (chips) · md=6px (botones pequeños) · lg=8px (botones, inputs, nav) · xl=10px (pre) · 2xl=12px (paneles, tarjetas).
- **Sombras**: `shadow.sm` = `0 1px 2px var(--shadow)` · `shadow.md` = `0 4px 14px var(--shadow)` (dropdowns).
- **Motion**: fast=120ms · base=150ms · ease estándar. **Toda transición respeta `prefers-reduced-motion`.**

## 5. Catálogo de componentes

Contrato por componente: variantes × estados (default / hover / focus-visible / active /
disabled). Implementación de referencia en `portal_lib.py`; cada superficie nueva debe
derivar de estos tokens.

### 5.1 Botón (topbar/shell)
- Fondo `var(--card-bg)`, borde 1px `var(--panel-bd)`, radio lg, texto `font.size.md` w600.
- **hover**: borde `var(--accent)`.
- **focus-visible**: anillo 2px `var(--focus)` + offset 2px (regla global, §7).
- **disabled**: opacidad .5, cursor not-allowed, sin hover.
- **primary** (acción principal, p. ej. "regenerar"): fondo `var(--accent-strong)`, texto `var(--on-accent)`, borde transparente.

### 5.2 Input de búsqueda (`#q`)
- Fondo `var(--card-bg)`, borde `var(--panel-bd)`, radio lg, texto `font.size.md`.
- **focus**: borde `var(--accent)`, sin outline nativo (el anillo lo da focus-visible).
- **placeholder**: `var(--muted-aa)`.

### 5.3 Nav-item (menú lateral)
- Texto `font.size.md`, padding 3, radio lg.
- **hover**: fondo `var(--card-bg)`.
- **active** (`aria-current="page"`): borde izquierdo 2px `var(--accent)`, texto `var(--txt)`.
- **focus-visible**: anillo `var(--focus)`.

### 5.4 Chip / badge de contador
- Fondo `var(--card-bg)`, borde `var(--panel-bd)`, radio sm, `font.size.2xs`.
- Variantes de estado: ok=`--ok`, warn=`--warn`, bad=`--bad`, info=`--accent` (como borde+texto, no relleno).

### 5.5 Tarjeta
- Fondo `var(--card-bg)` o `--panel-bg`, borde `var(--panel-bd)`, radio 2xl, padding 4.

### 5.6 Tabla (documentos)
- Borde inferior de fila `var(--panel-bd)`; header `font.size.sm` mayúsculas `var(--sub)`.
- **fila hover**: fondo `var(--card-bg)`.

### 5.7 Migas (crumbs)
- Separador `var(--sub)`; actual `var(--txt)` w650; botones ‹ › agrupados visualmente con el panel.

### 5.8 Resultado de búsqueda (`.qr`)
- Fila con hover `var(--card-bg)`; categoría `font.size.2xs` `var(--accent)` mayúsculas.

### 5.9 Bloque de código
- `pre`: fondo `var(--panel-bg)`, borde `var(--panel-bd)`, radio xl, mono.
- `code` inline: fondo `var(--card-bg)`, radio sm.

### 5.10 Scrollbar
- Riel transparente; thumb `var(--panel-bd)` (hover `var(--muted)`); 8–9px; integrada al tema.

## 6. Los cuatro estados (contrato por superficie)

| Superficie | Loading | Empty | Error | Success |
|---|---|---|---|---|
| Búsqueda (Ctrl+K) | debounce 120ms | "Sin resultados para '…'" | — | contador "N de M" |
| Página de documento | esqueleto/spinner mínimo | "Documento sin contenido" | "Error al cargar: <acción reintentar>" | contenido |
| Inicio/dashboard | shimmer en nodos del grafo | "Sin fases registradas" | banner `--bad` con detalle | grafo + panel |
| Diagrama IR | spinner | "Sin elementos que mostrar" | lista de errores de validación IR | diagrama |
| Iframe del portal | spinner en el shell mientras carga | página con estado vacío | mensaje con enlace al doc fuente | — |

Regla: el estado **error** siempre ofrece una acción (reintentar, abrir fuente, copiar detalle).

## 7. Accesibilidad (contrato)

- `:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px }` en **todo** elemento interactivo (botones, inputs, enlaces, summary, nav-items, ‹ ›).
- `@media (prefers-reduced-motion: reduce)` anula transiciones y animaciones.
- Shell con landmarks: `<nav aria-label="Secciones">`, `aria-current` en el ítem activo, `aria-expanded` en grupos `<details>`, `aria-label` en botones de icono (☰ 🔍 🌞).
- Texto de error accionable; placeholders nunca sustituyen labels visibles.
- Zoom A−/A+ escala **todo** el chrome (base rem en `html`).

## 8. Gobierno

- Cambiar un color = editar `tokens.json` + subir `meta.version` + regenerar snapshot
  (`design_tokens.py`) + `design_tokens.py --check` + regenerar superficies afectadas.
- `tests/self_test.py` verifica: paridad snapshot↔archivo, que los generadores emiten
  desde `design_tokens` (sin bloques hardcodeados) y los pares AA.
- El prototipo Penpot (`PANT-xx`) consume estos mismos tokens; un cambio de token exige
  re-sincronizar el TokenSet de Penpot.
