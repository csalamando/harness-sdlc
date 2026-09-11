# Diagnóstico UI/UX — Portal del proyecto CATI

> **ESTADO: IMPLEMENTADO (2026-09-11)** — las 10 mejoras quedaron aplicadas en el generador:
> `portal_lib.py` (PORTAL_VERSION 1.3.0 → **1.4.0**), `harness_graph.py` (inicio + paleta por variables CSS)
> y `diagram_ir.py` (reenvío de Ctrl+K// desde diagramas). Portal de CATI y fixture `proyecto-demo`
> regenerados; `harness_graph --check`, `portal_lib --check` y `tests/self_test.py` (291 checks) en verde.
> Capturas de verificación: `diagnostico-portal/new-*.png` (antes: `shot-*.png`).
> Los 8 diagramas de `spec/diagrams/` (7 IR + `grafo-codigo.html` vía `code_graph.py`, que también
> recibió el reenvío) ya están regenerados con el nuevo JS — Ctrl+K y `/` funcionan en todo el portal.

**Fecha:** 2026-09-11 · **Objeto:** `spec/portal/index.html` (portal v1.3.0, arnés v2.28.0)
**Principio rector:** el portal es un *artefacto derivado* — todas las mejoras se implementan en el generador
(`skills/sdlc-orchestrator/scripts/portal_lib.py`, plantilla `_SHELL`, y `harness_graph.py` para `inicio.html`),
nunca editando a mano los archivos generados. Tras cada cambio se sube `PORTAL_VERSION` y se regenera con
`harness_graph.py --proyecto .` / `portal_lib.py --spec . --rebuild`.

Capturas de evidencia en `diagnostico-portal/shot-*.png`.

---

## A. Problemas señalados por el usuario (confirmados con capturas y código)

### A1. El nombre del proyecto aparece demasiadas veces
- **Evidencia:** `shot-1-inicio.png` — "CATI" se lee 5 veces en la primera pantalla: brand del topbar,
  miga de pan (`Inicio — CATI`), ítem del menú (`Inicio — CATI`), `<h1>🏠 CATI</h1>` de la página de inicio
  y el subtítulo "Portal del proyecto · arnés v2.28.0".
- **Causa raíz:**
  - `portal_lib.py:490` — brand `◈ __PROYECTO__` en topbar.
  - `portal_lib.py:617` — crumb raíz pinta `M.proyecto`.
  - `harness_graph.py:1563` — título del ítem `Inicio — {proyecto}`.
  - `harness_graph.py:1564` y `1456` — `<h1>🏠 {proyecto}</h1>` + subtítulo con versión.
- **Propuesta:** dejar el nombre **una sola vez** (brand del topbar). Cambios en el generador:
  - `harness_graph.py`: título del ítem → `Inicio`; `<h1>` de inicio → `🏠 Estado del proyecto` (el subtítulo
    conserva versión/fecha, que sí es información útil y única).
  - `portal_lib.py` `paint()`: crumb raíz muestra `Inicio` en lugar del nombre del proyecto.
  - Mover `portal vX · arnés vY` del brand a un `title` (tooltip) o al pie de la página de inicio.

### A2. Scroll vertical del menú visible (gris, desentona con el fondo)
- **Evidencia:** captura del usuario (scrollbar clásico grueso gris de Windows sobre fondo `#0f172a`).
- **Causa raíz:** no hay ninguna regla de scrollbar en `_SHELL` (`portal_lib.py:453-455` solo define
  `overflow-y:auto`); el navegador usa el scrollbar nativo del SO.
- **Propuesta (solo CSS en la plantilla):**
  ```css
  #side{scrollbar-width:thin;scrollbar-color:transparent transparent}
  #side:hover{scrollbar-color:var(--panel-bd) transparent}
  #side::-webkit-scrollbar{width:8px}
  #side::-webkit-scrollbar-thumb{background:transparent;border-radius:4px}
  #side:hover::-webkit-scrollbar-thumb{background:var(--panel-bd)}
  ```
  El riel queda invisible en reposo y aparece sutilmente al pasar el cursor. Aplicar la misma regla a
  `#qres` y al CSS de las páginas de documento (`DOC_CSS`, `portal_lib.py:~69`).

### A3. Ctrl+K no funciona en Chrome (se activa la barra de direcciones)
- **Causa raíz (diagnóstico propio):** el listener está en el documento padre (`portal_lib.py:705-706`),
  pero el contenido vive en un `<iframe>`. **Cuando el foco está dentro del iframe, el evento `keydown`
  nunca llega al padre** y Chrome ejecuta su acción por defecto (omnibox). Es un bug real, no solo un
  conflicto de atajo.
- **Propuesta (compatible con el arnés, porque el arnés genera también las páginas hijas):**
  1. Inyectar en el JS compartido de las páginas generadas un reenviador:
     `keydown Ctrl+K → parent.postMessage({portal:'hotkey-search'},'*')`; el shell escucha ese mensaje
     y hace `q.focus(); q.select()`.
  2. Añadir un botón visible 🔍 en el topbar que enfoque la búsqueda (fallback accesible sin teclado).
  3. Añadir atajo alternativo `/` (estilo GitHub) cuando el foco no está en un input.
  4. Actualizar placeholder y caja de ayuda: "Buscar… (Ctrl+K o /)".

### A4. Fuente del menú muy pequeña y no responde al control A−/A+
- **Evidencia:** `shot-zoom.png` — con A+ ×2 solo escala el iframe; menú, topbar y migas quedan iguales.
- **Causa raíz:** el zoom es `transform: scale()` aplicado **solo a `#frame`** (`portal_lib.py:543-546`);
  el chrome del portal usa tamaños fijos en px (menú `12.5px`, subgrupos `11px`, etiquetas `10px` —
  `portal_lib.py:458,465,467,472`).
- **Propuesta:**
  1. Refactor del shell a unidades `rem` y zoom como `document.documentElement.style.fontSize = (15*z)+'px'`
     → escala todo el chrome (menú incluido) con los mismos botones A−/A+ y la misma clave `dir-zoom`.
  2. Subir la base del menú: ítems a `13.5px`, `summary` a `13.5px`, subgrupos a `12px`,
     etiquetas de grupo a `11px` (además heredan el zoom).
  3. Mantener el `scale()` del iframe como complemento (los diagramas SVG ya lo consumen).

### A5. Al colapsar, el menú desaparece en vez de mostrar iconos
- **Evidencia:** `shot-colapsado.png` — `body.side-off #side{margin-left:-272px}` (`portal_lib.py:455`)
  lo saca por completo de la pantalla.
- **Propuesta:** modo **riel de iconos** (icon rail), todo en la plantilla:
  ```css
  body.side-off #side{margin-left:0;width:52px;padding:.6rem .35rem}
  body.side-off #nav summary{justify-content:center;padding:.5rem 0}
  body.side-off #nav summary .lbl, body.side-off #nav summary .cnt,
  body.side-off #nav summary::before, body.side-off #nav .grp,
  body.side-off #nav a.ni, body.side-off #nav details.menu-grupo{display:none}
  body.side-off #side:hover{width:272px}  /* flyout al pasar el cursor */
  ```
  - El manifiesto ya tiene `c.icono` por categoría (`portal_lib.py:562`) — el riel muestra esos iconos
    con `title` (tooltip) y `aria-label`.
  - Al hacer hover el panel se expande temporalmente (flyout, patrón VS Code); ☰ sigue alternando
    el estado persistido en `dir-sidebar`. Cambio 100% CSS + un `span.lbl` en `buildNav()`.

---

## B. Hallazgos adicionales del diagnóstico propio

### B1. Tema claro con contraste deficiente en el contenido del iframe
- **Evidencia:** `shot-claro.png` — el chrome pasa a claro, pero la página de inicio conserva nodos
  oscuros con texto oscuro y etiquetas (`estás aquí`, `Discovery`, `Strict TDD`, leyendas de gates)
  casi ilegibles sobre fondo claro.
- **Causa probable:** la página embebida no aplica el tema `claro` en todos sus componentes (el
  `postMessage {portal:'tema'}` llega, pero los colores del grafo pipeline están parcialmente fijos).
- **Propuesta:** revisar en `harness_graph.py` la paleta del pipeline para que todos los textos/nodos
  deriven de las variables CSS (`--fg/--muted/--panel-bd`) en lugar de colores hardcodeados.

### B2. Títulos del menú truncados con "…"
- **Evidencia:** `shot-1-inicio.png` — "Arquitectura — diagramas y decisi…", "Estimación de Costos — Catálogo …".
- **Causa:** `white-space:nowrap;text-overflow:ellipsis` (`portal_lib.py:472`) con panel de 272px.
- **Propuesta:** permitir 2 líneas (`-webkit-line-clamp:2`) o ensanchar a 296px; el tooltip `title`
  ya existe, pero no basta para escaneo visual.

### B3. Etiquetas de grupo con contraste muy bajo
- Las etiquetas `SPEC`, `REPORTS`, `ADR`, `MEMORIA` usan `10px` y `--muted #64748b` sobre `#0f172a`
  (~3.1:1, por debajo de WCAG AA 4.5:1). Subir a `11px` y color `--sub #8ea0b8` (~5.9:1).

### B4. El botón "‹" de las migas se confunde con un colapsador del menú
- **Evidencia:** captura del usuario — el "‹" solitario bajo el topbar parece el control de colapso.
- **Propuesta:** agrupar "‹ ›" visualmente con las migas (fondo de panel, tooltip "Atrás/Adelante en el
  portal") o moverlos junto al ☰; hoy `title` existe pero el affordance es ambiguo.

### B5. Brand del topbar sobrecargado
- `◈ CATI  portal v1.3.0 · arnés v2.28.0` compite con la búsqueda. Dejar `◈ CATI` y llevar las versiones
  al tooltip del brand o al pie de la página de inicio (refuerza A1).

### B6. Búsqueda: resultados sin indicador de total ni "sin resultados"
- `shot-busqueda.png`: funciona bien, pero si no hay coincidencias el dropdown simplemente no aparece
  (`portal_lib.py:689`). Añadir fila "Sin resultados para '…'" y contador "12 de N". Mejora la
  percepción de que la búsqueda sí corrió.

---

## C. Plan de implementación sugerido (orden y esfuerzo)

| # | Mejora | Archivo del arnés | Esfuerzo | Impacto |
|---|--------|-------------------|----------|---------|
| 1 | A5 riel de iconos al colapsar | `portal_lib.py` `_SHELL` (CSS + `buildNav`) | Medio | Alto |
| 2 | A4 zoom global en rem + fuente menú | `portal_lib.py` (CSS + `aplZoom`) | Medio | Alto |
| 3 | A3 Ctrl+K reenviado desde iframe + botón 🔍 + `/` | `portal_lib.py` + JS compartido de páginas | Medio | Alto |
| 4 | A2 scrollbar invisible/sutil | `portal_lib.py` (CSS) | Bajo | Medio |
| 5 | A1 + B5 nombre una vez, versiones a tooltip | `portal_lib.py` + `harness_graph.py` (inicio) | Bajo | Medio |
| 6 | B1 contraste tema claro en pipeline | `harness_graph.py` (paleta grafo) | Medio | Medio |
| 7 | B2 menú 2 líneas / ancho | `portal_lib.py` (CSS) | Bajo | Bajo |
| 8 | B3 contraste etiquetas de grupo | `portal_lib.py` (CSS) | Bajo | Bajo |
| 9 | B4 affordance de ‹ › | `portal_lib.py` (CSS/markup) | Bajo | Bajo |
| 10 | B6 "sin resultados" + contador | `portal_lib.py` (`pinta()`) | Bajo | Bajo |

**Gobernanza:** cada cambio sube `PORTAL_VERSION` (hoy `1.3.0`), se regenera el portal de CATI y de
`tests/fixtures/proyecto-demo`, y se verifica con `portal_lib.py --spec . --check` (sin DRIFT) más una
captura headless por estado (base, colapsado, claro, zoom, búsqueda).
