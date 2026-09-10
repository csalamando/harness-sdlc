# Changelog

Todas las novedades relevantes del arnés se documentan aquí. Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y versionado [SemVer](https://semver.org/lang/es/).

**Regla de versionado del arnés:**
- **MAJOR** (x.0.0): cambios incompatibles en gates, recibos o formato de spec (rompen pipelines existentes).
- **MINOR** (2.x.0): skills nuevas, gates nuevos, features retrocompatibles.
- **PATCH** (2.1.x): correcciones en scripts, plantillas o documentación.

## [2.22.0] - 2026-09-09

**"El arranque y el cambio son deterministas."** v2.22 abre con N4: el "mínimo para iniciar un proyecto" deja de ser interpretación y pasa a ser ejecución — mismo scaffold, mismos controles, auditoría desde el primer minuto; y los gates de entrega dejan de leerse en prosa para verificarse agregados con `gate_verify.py`. Nace del [diagnóstico de brechas](docs/diagnostico-brechas-promesa-valor.md) (proyectos que inician cada uno con archivos y controles distintos).

### Added
- **`init_project.py`**: scaffold determinista e idempotente — estructura `spec/` completa, matriz de autoridad, roster y tech radar copiados desde los assets del arnés, memoria de auditoría inicializada con génesis + evento `bootstrap` (modo y flags del arranque registrados). **Nunca sobrescribe** un archivo existente (lo reporta como saltado). `--capas` scaffolda `architecture-rules.yaml` (activa `arch_lint`); `--sin-ui/--sin-datos/--sin-procesos` ajustan el scaffold al routing.
- **`gate_verify.py --gate "GATE N"`**: verificación agregada del gate — para cada artefacto exigible: presencia + `gate_checker --tipo` + recibo vigente con hash coincidente; transversal: memoria de auditoría íntegra (sin auditoría no hay gate) y, en GATE 2, `arch_lint` en verde si hay reglas declaradas. Respeta los condicionales del routing (`--sin-ui` etc. excluyen lo que no aplica). Catálogo GATE 0/1/2/2.5/3 y `SPRINT-N` (sprint-review); rechaza gates fuera del catálogo N3. Exit 1 lista cada faltante.

### Changed
- Matriz de autoridad: nuevas entradas `spec/architecture-rules.yaml` (owner `software-architect`) y `spec/audit/` (owner `orchestrator`) — los artefactos de gobierno de v2.21 quedan bajo la misma autoridad que el resto.
- `EVENTOS_NUCLEO` de la auditoría incluye `arch_lint` y `contract_diff` (eventos de v2.21 promovidos a núcleo).

### Notas
- Self-test: sección [10f] — scaffold completo, idempotencia, génesis+bootstrap con versión y fecha, GATE 0 fallando sin artefactos y pasando con recibos, edición post-recibo rompiendo el gate, condicionales de routing. 203 checks.
- Roadmap v2.22: N2 (hash compuesto de dependencias + `spec_diff_impact --apply`), N5 (`check-vendored`), N7 (pipeline-state derivado), N11 (circuit breaker + blast_radius_check). [Núcleo recomendado](docs/nucleo-recomendado-control.md).

## [2.21.0] - 2026-09-09

**"La auditoría es un hecho, no una promesa."** v2.21 abre la memoria de auditoría del arnés (ADR-004): una traza append-only de hechos de gobierno, separada de la memoria de trabajo, que hace estructuralmente imposible que el retrabajo desaparezca de las métricas al re-aprobar un artefacto. Nace del [diagnóstico de brechas de la promesa de valor](docs/diagnostico-brechas-promesa-valor.md) (B-01: los recibos revocados se sobrescribían y la métrica de retrabajo estaba condenada a cero).

### Added
- **Memoria de auditoría (`audit_log.py`, ADR-004)**: `spec/audit/events.jsonl` append-only con **cadena de hash** (`prev_hash` por evento, génesis `"0"*64`) — tamper-evident antes de Git. Todo evento lleva `ts` **UTC ISO-8601 con zona** y `harness_version` obligatorios. Eventos núcleo: `audit_init` (génesis), `emit`, `invalidado`, `revocado`, `use`, `bootstrap`, `harness_upgrade`, `freestyle`. CLI: `init --proyecto` (una sola vez; falla si el log ya existe) y `append --evento ...`.
- **`audit_verify.py`**: verifica la integridad de la traza (JSON válido, campos obligatorios, `ts` con zona, `seq` monotónico desde 1, génesis `audit_init`, cadena `prev_hash`→`hash` continua y recalculable). Exit 1 listando cada manipulación. Para CI y Fase 8.
- **`receipt.py` escribe en la auditoría automáticamente**: `emit` registra `emit` (con `approved_by` opcional y nota de *re-emisión* cuando el recibo previo no estaba vigente — el retrabajo queda explícito); `verify` registra `invalidado` con hashes anterior/nuevo; `revoke` registra `revocado` con razón, relación y aprobador. Los eventos guardan el artefacto con **ruta relativa y separadores `/`** (portable, sin filtrar rutas locales).
- **`receipt.py emit --approved-by <identidad>`**: los gates humanos (0/1/3) pueden registrar quién aprobó — la aprobación humana deja de ser solo narración.
- **Catálogo cerrado de gates (N3)**: `audit_log.gate_valido()` define el catálogo — fijos `GATE 0/1/2/2.5/3` + dinámicos `SPRINT-N`/`FASE-N` — con normalización (`GATE-0` ≡ `GATE 0`). `receipt.py emit` **rechaza gates fuera del catálogo** (adiós a `gate2` inventado que colaba texto libre al pipeline).
- **`--approved-by` exigible en gates humanos (N3)**: `GATE 0`, `GATE 1`, `GATE 3` y `SPRINT-*` son gates de decisión humana — `emit` falla con exit 1 si no declara aprobador ("el agente no puede auto-aprobarse"). Gates automáticos (`GATE 2/2.5`, `FASE-N`) no lo exigen.
- **`receipt.py status --strict`**: veredicto ejecutable para CI — exit 1 si hay recibos no vigentes, artefactos faltantes o hashes que no coinciden. Sin `--strict`, `status` sigue siendo solo informativo.
- **Gates de diagramas IR exigibles (N6)** — los diagramas vuelven a ser parte fundamental y *verificable* de la propuesta de arquitectura:
  - `diagram_ir.py validate` reconoce el campo top-level `"tipo"` (`architecture|sequence|workflow|dataflow|lifecycle`) y, en `architecture`, **exige `ubicacion` en todo nodo/participante** — cada componente declara dónde corre. IRs sin `tipo` (pre-v2.21) siguen validando.
  - `gate_checker.py --tipo architecture`: el patrón `mermaid` se reemplaza por verificación real — exige ≥1 IR referenciado (`diagrams/*.ir.json`), que exista, que pase `validate`, y —si el proyecto ya gobierna con recibos— que tenga **recibo vigente con hash coincidente** (un diagrama editado sin re-aprobar bloquea el gate).
  - `gate_checker.py --tipo architecture-proposal`: cada opción (A, B, …) debe referenciar su propio IR — comparar sin ver no es comparar.
  - Plantilla `architecture.md` migrada de bloque mermaid a IR referenciado, con IR mínimo de ejemplo en `assets/diagrams/architecture-c4.ir.json`; guías de `sdlc-software-architect` y `sdlc-diagrams` actualizadas (fuera la referencia obsoleta a draw.io MCP).
- **`arch_lint.py` (N9) — la arquitectura deja de ser prosa y pasa a ser política binaria**: si el proyecto declara `spec/architecture-rules.yaml` (capas + dependencias `forbidden` entre ellas, owner `software-architect`, con recibo), el linter verifica que el código la respete — Python vía `ast` (imports absolutos y relativos), JS/TS vía patrones sobre rutas relativas; librerías externas se ignoran. Exit 1 por violación o configuración inválida (capa sin paths, regla que cita capa no declarada, política sin `forbidden`); exit 0 si el proyecto no declara reglas (condicional). Cada corrida registra evento `arch_lint` en la memoria de auditoría (reglas + hash, archivos analizados, violaciones, resultado). GATE 2 lo exige en verde cuando las reglas existen. Plantilla de ejemplo en `assets/architecture-rules.yaml`.
- **`contract_diff.py` (N10) — la interfaz pública blindada**: compara el contrato OpenAPI viejo/nuevo y clasifica cada cambio (breaking: path/operación/parámetro eliminado, parámetro recién requerido, tipo cambiado, propiedad de respuesta eliminada; el resto compatible). **Breaking change sin bump de versión mayor en `info.version` = gate bloqueado.** Modos: `--old/--new` para CI y `--contra-git` contra HEAD; el gate `api-contract` lo aplica automáticamente cuando el contrato tiene versión previa en git. PyYAML requerido — si falta, exit 2 con mensaje claro (un control que no se ejecuta no es control). Cada comparación registra evento `contract_diff` en la auditoría.
- **ADR-004** (`docs/decisions/`): la decisión de las dos memorias (trabajo vs auditoría) y sus modelos de consistencia opuestos.

### Changed
- **`receipt.py revoke` exige `--reason`** (breaking menor): una revocación sin causa declarada no es auditoría. Acepta además `--relation supersedes|conflicts_with` y `--approved-by`.
- Si `audit_log.py` no acompaña a `receipt.py` (vendoring incompleto en proyectos), la emisión lo **advierte en consola** — el drift de scripts copiados queda visible hasta que `--check-vendored` (plan N5) lo vuelva bloqueante.
- **Métricas derivadas del log (N8)**: `skill_metrics.py` y `sprint_review.py` leen la memoria de auditoría como fuente primaria (fallback a archivos de recibo en proyectos pre-v2.21). Consecuencias directas del diagnóstico:
  - **"Trabajo rehecho" cuenta hechos** (eventos `invalidado`/`revocado`), no estados de archivo: re-aprobar ya no resetea la métrica a cero.
  - **"Gates al primer intento" con fórmula única** (emisiones con `attempts==1` / total de emisiones) en ambos reportes — antes METRICS y sprint review se contradecían.
  - **Catálogo único gate→fase** (`audit_log.gate_fase`): normaliza `GATE-1` ≡ `GATE 1`, mapea `SPRINT-*` → fase 8 y `FASE-N` → N; la fila "?" de falsos "adorno" desaparece.
  - Las activaciones auto-registradas por `receipt.py` quedan **también** como eventos `use` en el log (primer paso de la absorción de `usage.jsonl`); `skill_metrics` fusiona y deduplica ambas fuentes.
  - `sprint_review.py` endurecido para consolas Windows cp1252 (salida UTF-8 segura con `→`/`⚠`).
  - El **cierre guiado de sprint** de `sprint_review.py` ya no sugiere un gate inventado (`--gate gate2`): ahora imprime el comando real `--gate SPRINT-{NN} --tipo sprint-review --role orchestrator --approved-by <quien-cierra>` — la guía del arnés no puede contradecir su propio catálogo.

### Notas
- Retrocompatible salvo dos endurecimientos deliberados: el `--reason` de `revoke` y el `--approved-by` exigible en gates humanos (flujos que emitían `GATE 0/1/3` o `SPRINT-*` sin aprobador ahora fallan con un mensaje claro). `usage.jsonl` se mantiene (las métricas migran al log en la siguiente iteración del plan, N8); los `.receipt.json` siguen siendo el estado operativo y ahora son estado derivado del log.
- Self-test: memoria de auditoría + métricas sobre el log + catálogo de gates + gates de diagramas IR (validate con ubicacion exigible, architecture sin IR no pasa, IR editado tras recibo bloquea, propuesta exige diagrama por opción) + arch_lint (violaciones Python ast y JS, config inválida, política vacía, evento en auditoría) + contract_diff (breaking sin bump bloquea, bump declarado pasa, gate api-contract contra git, evento en auditoría). 190 checks.
- Roadmap del diagnóstico: v2.21 queda completa (auditoría, aprobador humano, métricas sobre el log, gates de diagramas IR, arch_lint, contract_diff); v2.22 traerá init/gate_verify, hash compuesto de dependencias, check-vendored, pipeline-state derivado y HITL portable ([núcleo recomendado](docs/nucleo-recomendado-control.md)).

## [2.20.1] - 2026-09-07

### Fixed
- **CI en verde (cross-platform)**: `harness_graph.py --proyecto` fallaba en Linux cuando un recibo traía la ruta absoluta del artefacto con separadores de Windows (`D:\...`) — `os.path.basename` no separa `\` en POSIX y el modelo derivaba nombres de artefacto incorrectos. Ahora `derive_project` normaliza ambos separadores al leer `artefacto` de los recibos. Nuevo check de regresión en el self-test con un recibo de ruta Windows (138 checks).

## [2.20.0] - 2026-09-07

**"El tablero se convierte en el centro de control."**  v2.20 reemplaza el dashboard monolítico por un **portal web único** del proyecto — navegable, buscable y con identidad visual compartida — y retira la generación `.drawio`, que no alcanzaba el nivel de detalle requerido.

### Added
- **Portal único del proyecto (`portal_lib.py`, stdlib puro)**: `harness_graph.py --proyecto` ahora emite `spec/portal/`:
  - **Shell** (`index.html`): menú lateral colapsable con árbol por categorías (🏠 Inicio, 📊 Métricas, 🏛 Arquitectura, 💼 Negocio, 🧪 Calidad, 🚀 Operación, 📚 Documentos, 🧠 Memoria) con contadores y subgrupos; routing por hash `#/id/<slug>` (funciona desde `file://`, sin servidor); **miga de pan** (Inicio › Categoría › Página) con botones ‹ › de historial — la navegación interna doc→doc empuja historial, así que "atrás" devuelve a donde estabas — y **última página visitada persistida por proyecto** (reabre donde te quedaste); estado persistente (sidebar, tema, zoom).
  - **Búsqueda global (Ctrl+K)**: índice de texto plano de todas las páginas (títulos, contenido de los `.md`, nodos e insights de diagramas), con resultados priorizados y resaltado.
  - **Tema claro/oscuro y zoom A−/A/A+ compartidos**: mismas variables CSS y mismas claves de `localStorage` (`dir-tema`, `dir-zoom`) que los diagramas IR; el shell propaga el tema al contenido por `postMessage` y cada página lo aplica al cargar.
  - **Páginas modulares y densas** (info relacionada en la misma pantalla, sin saltar entre páginas): `inicio` (pipeline compacto + acumulado — de entrada se ve cómo va el proyecto), `metricas` (tendencias + tiempos en dos columnas), `arquitectura` (tarjetas de diagramas vivos + ADRs ↔ Tech Radar **vinculados**: clic en un ADR resalta su tecnología en el radar y viceversa), `memoria` (aprendizajes + sesiones lado a lado). El **glosario** y la **ayuda** ("cómo navegar") viven en el menú superior derecho del shell, no ocupan páginas. Las páginas se auto-reportan al shell (`data-page-id` + `postMessage`), así los enlaces internos doc→doc actualizan el menú sin recargar; los artefactos del popup por fase abren el `.md` dentro del portal (no en pestaña nueva).
  - **Generación modular por registry**: cada generador (`harness_graph`, `mdview`, `diagram_ir`) solo **registra** lo suyo en `spec/portal/registry.json`; `rebuild_index()` poda entradas huérfanas y reescribe `manifest.js` + `search-index.js` + `index.html`. Añadir contenido nunca regenera el sitio completo a mano, y `portal_lib.py --check` detecta drift en CI. Items `oculto` (fuera del menú lateral, enrutables y buscables) y `topbar` configurable por el generador.
- **`mdview.py` v2.0**: los `.md` de la spec se renderizan a `spec/portal/paginas/docs/` con la identidad del portal (sin backlink al viejo dashboard), reescriben los enlaces `.md` internos a su página renderizada y se auto-registran con texto buscable y categoría inferida de la ruta (`adr/`→Arquitectura, `reports/`→Operación, `vision/backlog/user-stories`→Negocio, `memory/`→Memoria…).
- **`diagram_ir.py`**: auto-registro best-effort en el portal tras cada `render` (categoría Arquitectura, u Operación si el título es pipeline/CI-CD; texto de búsqueda con nodos e insights) y listener de tema del shell.
- **`spec/dashboard.html`** queda como redirect al portal pero conserva el comentario `dashboard-state`: `harness_graph.py --proyecto --check` sigue comparando exactamente lo mismo.

### Removed
- **Generación `.drawio` retirada**: `diagram_render.py` solo procesa Mermaid (`.mmd`/`.md` vía mmdc); los `.drawio` se rechazan con mensaje claro de retiro. La vía vigente para diagramas gobernados es el IR interactivo (`diagram_ir.py`, ADR-003) y Mermaid para renders de CI.
- **Retiro físico de la vía drawio**: eliminados `iac_to_diagram.py`, las referencias por familia (`c4-and-cloud-styles.md`, `bpmn.md`, `sequence-gantt-gitflow.md`), el asset `c4-contenedores-ejemplo.drawio` y los demos `.drawio`/`tfstate`. Referencias vivas actualizadas: matriz de autoridad y `arch_signoff.py` firman `despliegue.ir.json` (ya no `.drawio`), `harness_doctor.py` solo reporta mmdc, plantillas del solution-architect usan `.ir.json` y el technical-writer enlaza el HTML IR.

### Notas
- Retrocompatible: los proyectos existentes regeneran el portal con el mismo `harness_graph.py --proyecto .` de siempre; los recibos, gates y el `--check` del dashboard no cambian. `spec/docs-html/` (v2.18) queda sustituido por `spec/portal/` (puede borrarse a mano).
- Self-test: 138 checks verdes (sección [9d] reescrita para el portal y [9f] con 13 checks del shell, registry, páginas densas, vinculación ADR↔radar, poda y drift). El fixture demo incluye un diagrama vivo IR y PostgreSQL en HOLD para demostrar la vinculación.

## [2.19.0] - 2026-09-07

**"Un diagrama de arquitectura que no dice dónde corre cada cosa, no dice nada."**  v2.19 endurece la vista de los diagramas vivos IR: tema claro/oscuro, control de fuente, badges de ubicación de despliegue y textos que nunca desbordan su nodo.

### Added
- **`diagram_ir.py` v1.1 — tema claro/oscuro**: toda la vista migra a variables CSS (`:root[data-theme=claro]`); toggle ☀/🌙 en la toolbar superior, persistente en `localStorage`. Default: campo opcional `"tema": "claro"|"oscuro"` del IR, si no, `prefers-color-scheme` del navegador. Aplica a `flow` y `sequence`.
- **Control de tamaño de fuente**: botones `A− / A / A+` en la toolbar (zoom 0.6–1.8, persistente en `localStorage`).
- **Badge de ubicación de despliegue** (`"ubicacion"` en nodos y participantes): pill en la esquina superior del nodo con icono automático — ☁ nube (AWS/Azure/GCP/IBM/SaaS…), ⌂ on-premise/datacenter, ◈ otro. Visible también en el panel de detalle y comparable en `diff` (un cambio de ubicación aparece como nodo modificado). Pensado para diagramas de arquitectura: cada componente declara en qué nube/región/on-prem corre.
- **Textos sin desborde**: títulos con wrap determinista a máximo 2 líneas (reduce a 12.5px si no cabe a 13.5px) y subtítulos con elipsis, por estimación de ancho sin medir fuentes — el texto nunca sale del nodo. Aplica a nodos flow, rombos `decision` y cabeceras de participantes.
- Fixture de ejemplo `tests/fixtures/demo-arquitectura-ubicaciones.ir.json` (arquitectura multi-nube + on-prem con badges).
- **Lenguaje visual común en TODAS las vías de diagramas** (no solo el IR):
  - `pipeline_diagram.py`: `--tema auto|claro|oscuro` (directiva `%%{init: {'theme': ...}}%%` por bloque; `auto` deja que el renderer elija); ids de job largos se quiebran con `<br/>` para no desbordar el nodo; `check` detecta el tema grabado en el `.md`.
  - `diagram_render.py`: `--tema claro|oscuro` propagado a mmdc (`-t dark|default` + fondo `#0b1220`/blanco, coherente con la paleta del IR).

### Notas
- Retrocompatible: los IR existentes renderizan igual (tema oscuro por defecto); `ubicacion` y `tema` son opcionales. Los `.drawio`/`.md` derivados se regeneran con el mismo `generate` de siempre.
- Self-test: 128 checks verdes (nueva sección [9e] con 11 checks para los tres generadores).

## [2.18.0] - 2026-09-05

**"La spec se lee donde se mira."**  v2.18 convierte el dashboard en el punto de entrada de lectura del proyecto: los documentos Markdown de la spec y los diagramas vivos se abren desde el tablero, renderizados y sin servidor.

### Added
- **`sdlc-orchestrator/scripts/mdview.py`** (stdlib puro): visor Markdown estático estilo GitHub (tema oscuro acorde al dashboard). `mdview.py build --spec <dir>` genera `spec/docs-html/` con una página por documento (top-level, `reports/`, `adr/`, `diagrams/`, `memory/`) más un `index.html`; cada página enlaza de vuelta al dashboard. Cobertura: encabezados, tablas GFM, listas, citas, código, enlaces, imágenes; mermaid se muestra como código fuente (sin red). Inspirado en el patrón `grip --export` ([joeyespo/grip](https://github.com/joeyespo/grip)) pero **sin GitHub API ni dependencias** — offline y determinista.
- **Dashboard navegable**: botón **📄 Documentos** (índice de la spec renderizada), botón **🗺 Diagramas** (popup con los `spec/diagrams/*.html` vivos), y los artefactos `.md` del popup de fases ahora abren su **página renderizada** en vez del Markdown crudo.
- Self-test: sección [9d] (5 checks). Total: 116 checks.

### Changed
- `harness_graph.py --proyecto`: regenera `spec/docs-html/` en cada corrida (best-effort, nunca bloquea); el modelo incluye `diagramas`.

### Notas
- `spec/docs-html/` es artefacto derivado (como `dashboard.html`): se regenera, nunca se edita a mano. Recomendado versionarlo para lectura offline; quien prefiera no versionarlo puede ignorarlo en `.gitignore` y regenerarlo con `harness_graph.py --proyecto .`.

## [2.17.0] - 2026-09-05

**"El diagrama que se explora se mantiene; el que solo se mira, muere."**  v2.17 añade una vía de diagramas **vivos e interactivos** con render determinista de cero tokens, inspirada en [archify](https://github.com/tt-a1i/archify) (inspiración, no dependencia — mismo patrón que engram → `mem.py` en v2.16). Ver [ADR-003](docs/decisions/ADR-003-diagramas-ir-interactivos.md).

### Added
- **`sdlc-diagrams/scripts/diagram_ir.py`** (stdlib puro): renderer de diagramas interactivos desde IR JSON versionado en `spec/diagrams/*.ir.json`. El IR es la fuente de verdad (diff-able en PR, lo edita el rol dueño, recibe el recibo); el HTML/SVG auto-contenido es vista derivada que **nunca se edita a mano**. Subcomandos: `render`, `validate` (esquema + referencias), `diff` (Before/After: nodos/aristas/mensajes/insights agregados, eliminados, modificados — exit 2 si hay cambios), `check` (anti-drift, exit 1 si el HTML quedó atrás).
- **Dos motores de layout**: `flow` (architecture / workflow / dataflow / lifecycle según `bandas`: hulls, filas o columnas; rombos `decision`, `terminal` doble borde, back-edges rosa punteados enrutados por los huecos entre columnas) y `sequence` (lifelines, mensajes numerados, retornos punteados, barras de activación con margen, aire real entre cabeceras y primer mensaje).
- **Interacción uniforme estilo archify** en los 5 tipos: clic en elemento → foco + panel de detalle con relaciones; leyenda clicable tipo *lens* (hasta 2 tipos simultáneos); estado compartible por URL (`#focus=`, `#lens=`); tarjetas de **insights** bajo el diagrama (viven en el IR — el `diff` detecta cuándo un insight queda desalineado del grafo).
- Fixtures de ejemplo: `tests/fixtures/diagram-flow.ir.json` y `diagram-sequence.ir.json`.
- Self-test: sección [9c] con 11 checks (validate, render auto-contenido, drift on/off, diff vacío/con cambios, IR inválido). Total: 110 checks.

### Changed
- `sdlc-diagrams/SKILL.md`: nueva sección "Diagramas interactivos desde IR" con la tabla IR vs drawio y reglas de gobierno (recibo sobre el IR, HTML derivado).
- `sdlc-orchestrator/SKILL.md`: referencia a `diagram_ir.py` junto a los scripts de diagramas.

### Notas
- Los `.drawio` siguen siendo el formato para diagramas formales con stakeholders (C4, BPMN, cloud con iconos oficiales); los `.ir.json` son para diagramas vivos de seguimiento. Coexisten.
- Dueños del IR por tipo: architecture/sequence → `sdlc-software-architect`, workflow CI/CD → `sdlc-devops-engineer`, lifecycle de HU → `sdlc-orchestrator`, dataflow → `sdlc-data-engineer`.

## [2.16.0] - 2026-09-04

**"La memoria se cierra con evidencia, no con voluntad."**  v2.16 cierra brecha detectada sobre la disciplina de memoria/métricas estaba prescrita en texto pero nada la verificaba — proyectos con 14 sprints y **cero** memorias.

### Added
- **`mem.py close-check`** (gate verificable de cierre de ciclo, Fase 8): exit 1 si el sprint cierra sin memoria `learning` en la ventana, sin handoff de sesión, con sesiones abiertas o con `usage.jsonl` vacío. La ventana se deriva de la fecha del último sprint review (`--since` para override).
- **`mem.py save --topic_key`**: identidad estable por tema — re-guardar con la misma clave **auto-supersede** la memoria vigente anterior (mata los duplicados competidores tipo `tablas-nombres-...-p` / `...-m` de CATI). Columna `topic_key` en el índice con migración suave.
- **`mem.py context`**: digest mínimo de arranque para el orquestador (sesión activa, último handoff, memorias vigentes recientes, conflictos, políticas mandatory) — equivalente al `mem_context` de engram, en pocos tokens.
- **Handoff estructurado**: `mem.py session end --goal --done --next --files` escribe `sessions/SES-*.md` con secciones de handoff recuperables tras compactación; avisa si la sesión cierra sin memorias.
- **Sesiones en el dashboard**: `harness_graph.py` lee `spec/memory/sessions/` y muestra los últimos handoffs (botón "🕓 Sesiones") — el dashboard responde "qué se está trabajando", no solo "qué se ha generado".
- **Auto-registro de activaciones**: `receipt.py emit --role X` escribe la activación en `spec/metrics/usage.jsonl` como respaldo contra el olvido de `skill_metrics.py use`; `skill_metrics.py report` deduplica (el uso manual manda; los auto-registros colapsan a uno por skill+fase+día).

### Changed
- `sdlc-memory/SKILL.md`: protocolo actualizado (context al arrancar, topic_key, handoff estructurado, close-check en Fase 8).
- `sdlc-orchestrator/SKILL.md`: paso 7 del flujo y Fase 8 exigen handoff + `close-check` en verde antes de archivar el ciclo.

## [2.15.2] - 2026-09-02

### Fixed
- **`sdlc-technical-writer/assets/gh-pages-docs.yml`**: el `environment` del job `deploy` usaba un flow mapping con `${{ }}` dentro (`{ name: ..., url: ${{ ... }} }`), que es **YAML inválido** — GitHub no podía parsear el workflow y lo reportaba como run fallido (con la ruta del archivo como nombre) en *cada push*, aunque el trigger push estuviera comentado. Reescrito en block style. Detectado en CATI: el fallo "docs-pages" que parecía de Pages deshabilitado era en realidad este error de sintaxis. Validados todos los assets `.yml` del arnés con parser.
- **`authority-matrix.yaml` (asset)**: usaba dos claves en una línea (`- path: X  owner: Y`), YAML **inválido** que los scripts toleraban por parseo regex; cualquier consumidor con parser real (yq, CI) fallaba. Convertido a block style válido y actualizados los tres regex consumidores (`authority_check.py`, `manifest_check.py`, `self_test.py`). El self-test suma la sección [9b]: **todos los assets `.yml/.yaml` deben parsear como YAML válido** — la clase de bug queda cerrada estructuralmente. **Nota de adopción:** quien vendorice scripts debe actualizar también su `spec/authority-matrix.yaml` al formato nuevo (los scripts v2.15.2 esperan `path:` y `owner:` en líneas separadas).

## [2.15.1] - 2026-09-02

### Fixed
- **`ci-spec-governance.yml` (asset)**: el job `dashboard-freshness` solo regenera y commitea cuando `harness_graph.py --check` detecta **drift real** (la huella embebida ignora el timestamp; antes commiteaba en cada push a main por la sola diferencia de fecha de generación). Añadido `concurrency: dashboard-freshness` para evitar la carrera bot-vs-bot cuando dos push seguidos disparan el job (detectado en la adopción en CATI: un run quedaba rojo por push rechazado del otro).

## [2.15.0] - 2026-09-02

**"La visibilidad se gobierna, no se pide."** Hasta v2.14 la telemetría (métricas, sprint review, dashboard) vivía en la capa de convención: el agente debía *recordar* generarla y nada bloqueaba si no ocurría. v2.15 sube cada pieza a la capa más fuerte posible (gate, CI, git). Ver guía §5o "Qué controla el arnés y qué no".

### Added
- **Gate `sprint-review` con exigencia semántica** (`gate_checker.py --tipo sprint-review`): 8 checks de secciones + **obligatoriedad de memoria `learning` creada dentro del periodo del sprint**. Un sprint sin aprendizaje registrado ya no pasa el gate. El workflow CI aplica este gate a `spec/reports/*.md`.
- **`sprint_review.py` cierra el sprint por sí mismo**: regenera `spec/METRICS.md` siempre, **autogenera la memoria `learning`** cuando el sprint fue limpio (sin rehechos, gates 1er intento 100%, sin freestyle) y no había una, e imprime los 3 comandos de cierre (gate + recibo + dashboard).
- **Dashboard con frescura garantizada en CI** (`ci-spec-governance.yml`): en PR, step visible (warning) de drift con `harness_graph.py --check`; en push a main, **regenera y auto-commitea `spec/dashboard.html`** (`chore: dashboard regenerado [skip ci]`). `harness_doctor.py` alerta si el proyecto tiene workflows pero ninguno menciona `harness_graph`.
- **Dueños de la telemetría**: `spec/METRICS.md`, `spec/metrics/`, `spec/reports/` y `spec/dashboard.html` entran a la matriz de autoridad y a `CODEOWNERS-template` (owner: orchestrator) — dejan de ser tierra de nadie.
- **Tokens honestos**: sprint review y dashboard separan tokens **medidos** (reportados) de **estimados** (chars/4), muestran el **% de cobertura medida** y alertan cuando los estimados difieren >25% de los reportados. Nuevo KPI "Tokens medidos (cobertura)" en el dashboard.
- **`tdd_order_check.py`** (nuevo script, stdlib puro): por cada HU del rango de commits verifica en `git log` que el commit `test(HU-xxx): red` precede al `feat(HU-xxx): green`. El TDD intra-sesión no es observable; el orden de commits sí. Step CI en modo warning y KPI "HUs con orden TDD en commits" en el dashboard.
- **Convención de commits TDD** en `sdlc-backend-dev-tdd` y `sdlc-frontend-dev-tdd`: commits separados red→green con el formato que `tdd_order_check.py` verifica.
- **Self-test sección [9]**: gate sprint-review (positivo y negativo), dueños de telemetría en la matriz y detección de orden TDD invertido en repo sintético. Fixture `proyecto-demo` actualizado: sus reviews son ahora el ejemplo canónico que pasa el gate.

## [2.14.1] - 2026-08-25

### Added
- **`docs/gobernanza-github.md`**: especificación paso a paso para convertir la matriz de autoridad y los gates en fronteras duras nativas de GitHub — teams ↔ roles, branch protection con Code Owners y stale reviews, status checks requeridos, environments como aprobación de GATE 3, bypass de emergencia gobernado (learning obligatorio) y perfiles de adopción mínimo/completo.
- **Guía §5n "Distribución, versionado y gobierno a nivel GitHub"**: aclara el modelo de distribución — el agente ejecuta las skills instaladas en su ruta; la copia vendorizada en el proyecto es el registro de versión y lo que corre en CI. Referenciada desde §5d y CONTRIBUTING.

## [2.14.0] - 2026-08-24

### Added
- **Stepper superior en el dashboard**: fase actual en grande, **progreso por HU cerradas** (soporta alcances que crecen y productos en evolución continua; fallback a gates si no hay estructura HU) y chips de **ciclos ejecutados** (sprints, bugs QA→TDD, hotfixes, replans, impact-reports con ×N).
- **Gráficas de línea SVG** de tendencias (lead time por gate, % 1er intento, retrabajo/artefactos) a partir del 3er sprint review; con 1-2 sprints, **tarjetas delta** (valor + Δ vs sprint anterior).
- **Histórico completo por fecha**: serie acumulada derivada de los timestamps de los recibos — cubre los sprints anteriores al primer `sprint_review.py` (los recibos no mienten sobre cuándo pasó algo).
- **Tiempos de fase y de ciclo**: barras + tabla por gate (apertura, cierre, trabajo dentro del gate y **día del proyecto en que cerró** — muestra el orden real de cierre, incluida gobernanza retroactiva) y duración de cada sprint entre cierres de review.
- **Tech Radar como gráfica de radar** (columna por cuadrante con tooltip) + KPIs de ADRs adoptadas y tecnologías en radar.
- **Popup por fase** (clic en nodos del grafo o del stepper): descripción, gate, artefactos generados en el proyecto y **tarjetas por skill con entradas (IN) y salidas (OUT)** derivadas del manifiesto. Los chips con archivo existente son **hipervínculos `target="_blank"`** al `.md` real (0 bytes extra; el contenido no se incrusta para no inflar el dashboard).
- **Botones de cabecera "Aprendizajes" y "Glosario"** que abren popup (las secciones estáticas del final desaparecen).
- **Control de tamaño de fuente (A−/A+)** persistente (localStorage), disponible en el dashboard y dentro de cada popup.
- **Glosario del arnés** (14 términos: gate, recibo, Risk Tier, ADR, paved roads, drift, lead time, ciclo…).
- Secciones del dashboard **colapsables** (`<details>`).

### Changed
- KPI "Recibos rehechos" renombrado a **"Recibos invalidados"** (invalidados + revocados — nombre alineado con el mecanismo real de `receipt.py`).

### Fixed
- **Grafo del dashboard sin traslapes**: lienzo más alto, títulos de nodos en filas alternadas, etiquetas de gates compactas con tooltip (vigentes/rehechos), loops sin recorrer ya no muestran texto (arco tenue con tooltip; texto solo si tienen recorridos ×N o están activos), anclas de texto en nodos extremos.
- Etiquetas cortadas en la gráfica de radar y ADR con prefijo duplicado en la tabla de decisiones.

## [2.13.0] - 2026-08-24

### Added
- **Panel "Decisiones gobernadas" en el dashboard del proyecto**: ADRs parseados de `spec/adr/` (o `docs/decisions/`) con **estado** (Adopted/Proposed/Superseded con badges de color) y **Risk Tier** — el diferencial del arnés (decisiones de 8 pasos, excepciones Tier 1) ahora es visible de un vistazo. Conteo del **Tech Radar** por cuadrante (ADOPT/TRIAL/ASSESS/HOLD) desde `spec/tech-radar.yaml` — los paved roads sin abrir el YAML.
- **"Qué se ha generado por fase"**: nueva sección con los artefactos con recibo vigente agrupados por macro-fase, y contador "N artefactos ✓" bajo cada nodo del grafo.
- **Recorridos históricos en los loops del grafo**: cada arco muestra "×N" (sprints corridos, bugs devueltos, hotfixes, replans) siempre que N>0, independiente de si está activo ahora — un loop en ×0 queda tenue ("nunca hubo hotfix" también informa).
- **Banda de progreso** azul sobre la línea principal del pipeline: el tramo completado hasta la fase actual se ve sin leer etiquetas.

### Fixed
- `parse_radar`: el conteo por cuadrante ya no se "desborda" entre secciones con YAML real (líneas en blanco entre entradas) — verificado contra `spec/tech-radar.yaml` de un proyecto real.
- `parse_adrs`: archivos índice/consolidado sin número (`ADR-consolidados.md`) ya no rompen el parseo.

## [2.12.1] - 2026-08-23

### Added
- **Versión del arnés visible y estampada**: el orquestador declara `harness-version` en su frontmatter (fuente única); el manifiesto derivado la registra; los **recibos nuevos la estampan** (`harness_version`) — la evidencia queda autodescriptiva (la lección de CATI: gates `fase2` de una versión vieja se descubrieron por accidente); `harness_doctor.py` muestra la versión instalada y **alerta si el proyecto operó con una versión anterior**; el dashboard del proyecto y el grafo del arnés la muestran en su encabezado/pie. El self-test cruza que la versión declarada coincida con la última entrada del CHANGELOG — olvidar el bump rompe el build. Decisión: versión única del arnés (no por skill) mientras las skills se distribuyan juntas.

### Fixed
- **Dashboard con proyectos reales (lecciones de CATI)**: `norm_gate()` normaliza alias históricos de gates en recibos (`fase2` → `GATE 2`) — proyectos adoptados en versiones viejas ya no aparecen "sin recibos". El conteo de HU cerradas escanea múltiples layouts (`src/`, `backend/src`, `frontend/src`, `e2e/`, …) en vez de asumir `src/` + `tests/`, y ya no resta por id (bug que marcaba 0 HU cerradas en proyectos con tests correctos).

## [2.12.0] - 2026-08-23

### Added
- **Dashboard vivo del proyecto** (`harness_graph.py --proyecto <dir>`, [ADR-002](docs/decisions/ADR-002-dashboard-html-proyecto.md)): genera **un solo `spec/dashboard.html`, siempre "el ahora"** — pipeline con gates pintados según sus recibos, fase actual, loops de feedback activos resaltados (bug/hotfix según invalidaciones), contadores acumulados (sprints, releases, HU cerradas, gates al primer intento), tendencias por sprint con **alerta automática** cuando un lead time empeora >15%, y memorias `learning` recientes. Todo derivado de fuentes gobernadas (`receipts/` + `spec/` + `sprint-review-NN.md`); cero narración manual. El estado derivado viaja incrustado en el propio HTML (`<!-- dashboard-state -->`) y `--check` detecta drift sin archivos auxiliares. Regla de frescura: alerta en CI, **no bloquea gates** (visualización, no evidencia).
- `spec/dashboard.html` registrado en la matriz de autoridad (owner: orchestrator, como los diagramas derivados).
- Fixture `tests/fixtures/proyecto-demo` (2 sprints, recibos vigentes + 1 invalidado, 1 release, trazabilidad HU) + 5 checks nuevos en el self-test (85 total): modelo derivado, generación, drift y detección de drift al mutar un recibo.

## [2.11.1] - 2026-08-23

### Fixed
- **Grafo del pipeline más legible**: lienzo más alto (340 → 540 px), arcos de feedback escalonados por distancia (los loops largos van por fuera y ya no se pisan), etiquetas en el punto medio real de la curva Bézier, fuentes más grandes (fases .85 rem, loops .78 rem) y nodos de 56 px.
- **Flechas de dirección en los loops**: cada arco de feedback termina en una flecha ámbar en el **borde** del nodo destino (antes quedaba tapada por el círculo del nodo).

### Propuestas (backlog, no implementado)
- **Modo `--proyecto` para `harness_graph.py`** (candidato a v2.12): el mismo grafo alimentado del estado real de un proyecto — gates según recibos válidos de `receipt.py`, fase actual por artefactos presentes en `spec/`, avance de sprint desde `sprint_review.py` y `traceability_matrix.py`, arcos de feedback resaltados cuando hay bugs activos. Generaría `spec/pipeline-status.html` como tablero vivo regenerable en CI. Requiere ADR (Risk Tier 2): define un artefacto nuevo y su regla de frescura.

## [2.11.0] - 2026-08-23

### Added
- **`harness_graph.py` (herramienta CLI 18)**: grafo interactivo del pipeline en `docs/graph.html`, **derivado del manifiesto** y del grafo de dependencias de `spec_diff_impact.py` — nunca editado a mano. Las 6 macro-fases como nodos, las 21 skills agrupadas por fase (desde el frontmatter `harness-*`), y los loops de realimentación (sprints, TDD, hotfix, delta-spec, impact-report → backlog). HTML self-contained sin dependencias externas, ideal para explicar el arnés sin una pared de texto. Modos `--write` (regenera) y `--check` (exit 1 si el grafo quedó atrás del manifiesto — integrado al self-test, 80 checks).

## [2.10.1] - 2026-08-23

### Docs
- **README con diagramas Mermaid** (render nativo de GitHub, sin imágenes que mantener): el pipeline completo con gates coloreados por tipo (humanos vs automáticos, §3), el ciclo de vida de un recibo RDD como diagrama de estados (ACTIVE → INVALIDATED/REVOKED → re-gate, §5) y las tres capas de memoria con precedencia y promoción (§6). Dogfooding: la propia skill `sdlc-diagrams` predica doc-as-code con Mermaid.
- **Quick start de 2 minutos** al inicio del README (descargar ZIP → descomprimir `.skill` → "usa el orquestador SDLC"), antes solo en la guía.
- **Tabla de las 21 skills colapsable** (`<details>`) — la portada ya no la sufre quien no la necesita.

## [2.10.0] - 2026-08-23

### Added
- **Routing derivado del manifiesto**: `manifest_check.py --routing [--sin-ui] [--sin-datos] [--sin-procesos]` imprime los roles por fase que aplican a la iniciativa, con las capacidades condicionales **auto-excluidas** (sin UI → no hay prototipo `spec/ux/`; sin proceso que automatizar → no hay PDD; sin datos significativos → `sdlc-data-engineer` no participa). El orquestador lo ejecuta al iniciar (nueva sección "Routing desde el manifiesto" en su SKILL.md) — la tabla de routing deja de ser solo prosa interpretada.
- **`docs/decisions/ADR-001-skills-por-capas-rank.md`**: decisión **diferida** de las capas con rank estilo DeepSeek (proyecto > usuario > bundled). Requieren madurez alta en el uso de este tipo de herramientas (gobierno de variantes, precedencia, validez de recibos con skills divergentes) y el enfoque del arnés es **centralizar esas decisiones para que los equipos maduren sin asumir riesgos**. Con re-evaluation triggers concretos (demanda real de una organización, estándar Agent Skills con capas, madurez demostrada vía Sprint Reviews).
- `self_test.py`: 3 checks nuevos del routing derivado (sección [7] pasa de 3 a 6 checks).

## [2.9.0] - 2026-08-23

### Added
- **Manifiesto dinámico del arnés** (implementa la inspiración pendiente de DeepSeek Harness — "Everything is a plugin" / capability seams — adaptada a un estándar Markdown agnóstico de agente): cada skill declara sus metadatos en el frontmatter de su propio `SKILL.md` (`harness-role`, `harness-phases`, `harness-owns`, `harness-gates`, `harness-conditional`, `harness-optional-deps`) y el manifiesto pasa a ser un **artefacto derivado**, nunca editado a mano.
- **`manifest_check.py`** (orquestador, herramienta CLI 17): `--write` regenera `assets/harness-manifest.yaml` escaneando skills (metadatos + scripts en disco); `--check` falla (exit 1) ante drift o inconsistencias cruzadas — gate declarado que `gate_checker.py` no soporta, artefacto `owns` ausente de la matriz de autoridad, artefacto de la matriz sin skill que lo declare; `--summary` imprime la vista legible de las 21 skills.
- **`harness_doctor.py` consume el manifiesto**: las expectativas (qué skills y scripts deben existir) se leen de `harness-manifest.yaml` en vez de listas quemadas en el código — añadir una skill o script ya no requiere tocar el doctor (con fallback a listas mínimas históricas si el manifiesto no está instalado: degradación elegante).
- `self_test.py`: nueva sección [7] — manifiesto sin drift, frontmatter presente, doctor consumiendo el manifiesto.

### Por qué
Los bugs de v2.8.1 nacieron de listas quemadas en prosa ("espera 14 scripts", "16 herramientas", grafo de impacto literal). Con el manifiesto derivado, esa clase de bug queda cerrada estructuralmente: la próxima vez que una skill declare algo que no existe, el self-test y el CI fallan en rojo antes del release. Trabajo futuro documentado: skills por capas con rank (proyecto > usuario > bundled), análogo a los scopes de memoria.

## [2.8.2] - 2026-08-23

### Added
- **`tests/self_test.py`** (solo repo fuente — NO entra al ZIP de release ni es una skill): regresión de consistencia del arnés con 71 checks (compilación de scripts, las 13 plantillas pasan su propio gate, grafo de impacto completo, matriz de autoridad, roles end-to-end, validación cruzada sin depender del cwd). Red de seguridad para mantenedores, nacida de la revisión de v2.8.1.
- Guía de uso §5k: checklist de release para quienes **modifican** el arnés (self-test verde → CHANGELOG → tag → release), claramente separada del flujo de quienes solo lo usan.

## [2.8.1] - 2026-08-23

Revisión de calidad profunda sobre v2.8.0: las features de v2.7/v2.8 quedaron documentadas por encima de lo que los scripts realmente hacían. Esta versión cierra esa brecha — todo lo prometido en el CHANGELOG ahora está verificado ejecutando los scripts.

### Fixed
- **`spec_diff_impact.py`**: el grafo de dependencias quedó congelado en v2.2 y no conocía los artefactos nuevos — cambiar `roles.md` o `screen-inventory.md` devolvía "Artefacto desconocido" y **no revocaba nada**, contradiciendo v2.7 ("cambiar un rol revoca HU, UX, test-plan") y v2.8 (revocación de `spec/ux/`). Añadidos al grafo: `roles.md`, `process-definition.md`, `screen-inventory.md`, `epics.md`, `architecture-proposal.md`, `technical-stories.md`, `cost-estimation.md`, `adr`, `tech-radar.yaml` y `diagrams`, con sus aristas (p. ej. `user-stories.md` depende de `roles.md`; `src-frontend` de `screen-inventory.md`).
- **`screen-inventory-template.md` no pasaba su propio gate**: placeholders `HU-xxx`/`ROL-xx` no cumplen los patrones `HU-\d+`/`ROL-\d+`. Ahora usa `HU-001`/`HU-002`/`ROL-01`/`ROL-02` (9 checks OK).
- **Mismo defecto en otras 3 plantillas**: `backlog.md` (sin fila con `EP-\d+`), `qa-report.md` (sin `HU-\d+`) y `adr-template-8steps.md` (Advice Log con fecha placeholder `{YYYY-MM-DD}` que no cumple el patrón de fecha). Las cuatro plantillas de artefactos con gate ahora pasan su propio `gate_checker.py`.
- **Matriz de autoridad incompleta**: 8 artefactos con skill dueña pero sin owner declarado podían ser aprobados por cualquier rol ("SIN REGLA"). Añadidos: `spec/glossary.md` y `spec/security-requirements.md` (el más delicado: un dev podía aprobar sus propios requisitos de seguridad), `spec/data-governance.md` → data-engineer, `spec/tokens.json` → ux-designer, `spec/cloud-costs.md` → cloud-engineer, `spec/exception-log.md` → enterprise-architect, `spec/team-roster.yaml` y `spec/risk-tier.yaml` → orchestrator.
- **Doc vs código en roles (v2.7)**: el orquestador decía "si existe `roles.md`, toda HU debe citar ROL-xx definidos" pero el código solo validaba los ROL citados. `gate_checker.py` ahora exige que **toda HU** cite al menos un ROL-xx del catálogo cuando este existe (sin catálogo, degradación elegante: el gate pasa igual). Plantilla `user-stories.md` actualizada: `Como ROL-01 (...)`.
- **Validación cruzada silenciosa**: `check_roles_refs`/`check_screens_refs` usaban rutas relativas a cwd — ejecutados desde otro directorio se saltaban sin avisar. Nueva función `resolve_spec_path` que localiza `spec/` subiendo desde el artefacto; verificado funcionando desde un cwd ajeno.
- **Numeración de fases ambigua**: `pipeline.md` ponía Discovery en Fase 1 y el orquestador en Fase 0. Ahora el orquestador alinea: FASE 0 = Visión + Discovery de la iniciativa (PO + Solution Architect, GATE 0), FASE 1 = análisis BA.
- **`.gitignore`**: faltaba `.codeintel/` (índice derivable de v2.3) — el propio `harness_doctor.py` lo reportaba.

### Verificación
- 23/23 scripts compilan; 18/18 CLI responden; 13/13 tipos de gate probados contra plantillas; autoridad por rol probada por pares rol-artefacto (autorizado/rechazado); revocación de `roles.md` → 24 artefactos downstream.

## [2.8.0] - 2026-08-23

### Added
- **Prototipos de pantalla gobernados** (`spec/ux/`, owner `ux-designer`, condicional a iniciativas con UI): las pantallas con sus flujos de interacción pasan a ser un artefacto de validación temprana — negocio navega el prototipo antes de escribir código y su aprobación es el contrato visual del sprint. Estándar del arnés: **Penpot** (open-source MPL-2.0, diseños en estándares web SVG/CSS/JSON, design tokens nativos sincronizables con `spec/tokens.json`, prototipado interactivo, self-hostable, servidor MCP oficial para que el agente cree y modifique pantallas). El archivo de diseño se versiona en Git junto a la spec — fuente de verdad auditable, no un enlace a una nube propietaria.
- **Estructura gobernada**: `spec/ux/screen-inventory.md` (inventario PANT-xx: HU que cubre, ROL que la opera, estados loading/empty/error/success, interacciones con destino — plantilla `assets/screen-inventory-template.md`), `spec/ux/prototipo.penpot` (archivo versionado) y `spec/ux/exports/` (renders PNG/SVG para revisión en GATE 1 sin abrir la herramienta).
- **Gobierno**: GATE 1 exige inventario con recibo vigente para las pantallas del sprint — sin prototipo aprobado, el Dev Front no implementa esas pantallas. Cambios en HU/flujos/roles revocan el recibo de `spec/ux/` vía `spec_diff_impact.py` y las pantallas impactadas se re-aprueban. Sin MCP de Penpot disponible, el inventario y wireframes se entregan igualmente (degradación elegante). Alternativa Figma documentada: el artefacto gobernado es el export versionado, nunca el archivo vivo en la nube.
- `gate_checker.py`: tipo nuevo `screen-inventory` (9 checks) con validación cruzada — las HU-xx citadas en el inventario deben existir en `user-stories.md`.
- Matriz de autoridad: `spec/ux/` → `ux-designer`.

## [2.7.0] - 2026-08-23

### Added
- **Catálogo de roles gobernado** (`spec/roles.md`, plantilla `assets/roles-template.md` en `sdlc-business-analyst`): el "Como <rol>" de las historias deja de ser una palabra libre y pasa a ser referencia a un artefacto versionado. Un rol es nombre + acciones que habilita + contexto/condiciones + reglas que lo restringen (BR/SEC). Los conflictos de interés entre roles se declaran y su priorización la firma el PO; el Architect deriva el RBAC del diseño desde este artefacto.
- **PDD — Process Definition Document** (`spec/process-definition.md`, plantilla `assets/pdd-template.md`): captura del proceso **AS-IS** (disparadores, flujo, excepciones conocidas/desconocidas, volúmenes, SLA, aplicaciones, riesgos y supuestos) para iniciativas que automatizan o rediseñan procesos (RPA/BPM). Sin firma del Process Owner (recibo) no hay diseño TO-BE; una excepción descubierta en piloto re-emite y re-aprueba el PDD.
- `gate_checker.py`: tipos nuevos `roles` y `process-definition`; validación cruzada — los ROL-xx citados en `user-stories.md` deben existir en el catálogo (aplica también al tipo `user-stories` cuando existe `roles.md`).
- Matriz de autoridad: `spec/roles.md` y `spec/process-definition.md` → `business-analyst`.

## [2.6.0] - 2026-08-23

### Added
- **Diagramas como mecanismo de aceptación de cambios** (`sdlc-diagrams` gana `scripts/`): ningún diagrama cuenta como válido sin recibo de aprobación del rol dueño sobre su contenido. Dos direcciones con gobierno distinto:
  - **Derivados de fuente** (se recrean, nunca se editan a mano): la regeneración propone el cambio → el diff en Git se revisa → el rol dueño lo acepta con `receipt.py emit --role <rol>`.
  - **De diseño** (C4, BPMN, secuencia, Gantt, GitFlow): edición manual, pero si la spec que representan cambia, `spec_diff_impact.py` revoca su recibo y deben re-aprobarse.
- **`iac_to_diagram.py`** (generate/check): topología de despliegue derivada de `terraform.tfstate` (lo realmente desplegado) o ARM/Bicep compilado, con iconos oficiales AWS/Azure/GCP y clusters por módulo/resource group. Python stdlib puro — no ejecuta Terraform. `check` = drift detection (exit 1 si el diagrama difiere de la fuente).
- **`pipeline_diagram.py`** (generate/validate/check): flowchart Mermaid por workflow de GitHub Actions (triggers, jobs, `needs:`) + validación de `needs:` inexistentes y ciclos de dependencias sin binarios externos.
- **`diagram_render.py`** (render/render-dir/engines): render headless a SVG/PNG vía drawio-desktop CLI (el SVG embebe el fuente: la imagen sigue editable) o mmdc (renderiza bloques Mermaid dentro de Markdown y reescribe las referencias — doc-as-code). Motores opcionales con degradación elegante: sin ellos, el fuente versionado sigue siendo el entregable.
- Matriz de autoridad: `spec/diagrams/despliegue.drawio` → `cloud-engineer`; `spec/diagrams/pipeline-cicd.md` → `devops-engineer`.
- Orquestador: sección "Diagramas como mecanismo de aceptación"; GATE 3 exige diagramas derivados regenerados y con recibo vigente; Fase 8 verifica drift (`check`) en el cierre.

### Changed
- `harness_doctor.py`: compila los 3 scripts de `sdlc-diagrams` y reporta motores de render disponibles (informativo, nunca bloquea).

## [2.5.0] - 2026-08-23

### Added
- **Sprint Review** (`sprint_review.py`, script 16 del orquestador): reporte versionado de cierre de sprint en `spec/reports/sprint-review-NN.md` (un archivo por sprint → serie histórica). Secciones: resumen ejecutivo, avance del proyecto (aprobados por gate + recibos rehechos), desempeño del arnés (embebe las métricas de skills de v2.4), lead time por gate (timestamps de recibos), **tendencia vs sprint anterior** (KPIs embebidos como comentarios que el propio script relee) y aprendizajes/acciones.
- Relación de artefactos: `METRICS.md` = tablero vivo (se sobrescribe); `sprint-review-NN.md` = snapshot histórico; `impact-report.md` (product-analyst) = impacto de negocio — se enlaza, no se duplica.
- Fase 8: el paso de métricas ahora genera el Sprint Review (obligatorio al cerrar cada sprint).

### Changed
- `harness_doctor.py`: 14 scripts del orquestador (antes 13).

## [2.4.0] - 2026-08-23

### Added
- **Telemetría de skills** (`skill_metrics.py`, script 15 del orquestador): medición del aporte y la disciplina de las skills sin meter telemetría en el contexto del agente (escritura por CLI en comandos existentes; lectura bajo demanda).
  - `use --skill <rol> --fase <N>`: registro append-only de activaciones en `spec/metrics/usage.jsonl`.
  - `report` → `spec/METRICS.md` con tres vistas: **aporte** (artefactos con recibo, % gates al primer intento, tokens por skill), **cobertura** (detector de *freestyle*: rol con artefactos sin activación registrada = trabajo fuera de la skill; activación sin artefactos = skill de adorno) y **señales** accionables para mejorar skills.
- `receipt.py emit`: telemetría opcional `--tokens-in/-out --tokens-src reportado|estimado --attempts K`. Tokens exactos cuando la plataforma del agente los expone; estimación chars/4 calculada por el script cuando no — nunca depende de la narración del agente.
- Fase 8: el orquestador genera `METRICS.md` y guarda las señales como memoria `learning` (mejora continua de las skills).

### Changed
- `harness_doctor.py`: 13 scripts del orquestador (antes 12).
- README §4d y Guía §5f documentan la versión.

## [2.3.1] - 2026-08-23

### Added
- `spec_index.py`: el `spec/INDEX.md` generado incluye ahora un bloque "Cómo leer este repo" (4 reglas: spec como fuente de verdad, recibos SHA-256, consultar `.codeintel` antes de leer código, memorias con `--brief`) — el proyecto se auto-explica a cualquier agente que aterrice en el repo, sin archivos de instrucciones adicionales (sin AGENTS.md) ni contexto permanente extra.

### Fixed
- `spec_index.py`: el resumen de artefactos no detectaba encabezados markdown en archivos multilínea (faltaba `re.M` en el patrón) y caía al fallback de primera línea.

## [2.3.0] - 2026-08-22

### Added
- **`code_intel.py`** (orquestador): mini motor de inteligencia de código propio (inspirado en Gortex, reimplementado a medida). Grafo de símbolos en SQLite derivable (`.codeintel/index.db`, gitignored, incremental por SHA-256), Python stdlib puro, sin daemon. Extracción por niveles: `ast` para Python (fidelidad total) + patrones para 15 lenguajes más. Comandos: `index`, `symbol`, `context` (cuerpo exacto del símbolo o esqueleto del archivo), `impact` (blast radius BFS con razón por arista), `tests` (tests candidatos, evidencia para GATE 2), `search` (FTS5 sobre firmas/docstrings), `map`, `stats`.
- **`spec_index.py`** (orquestador): genera `spec/INDEX.md`, digest de una página con sha256, tamaño y resumen por artefacto — el agente se orienta leyendo un archivo y solo abre lo que necesita (verificando recibo).
- **`context_packager.py`**: antepone `spec/INDEX.md` al paquete y, para roles de desarrollo con índice disponible, instruye consultar símbolos vía `code_intel.py` en vez de leer archivos completos (`--code-root`).
- **`mem.py search --brief`**: una línea por memoria (id + título); abrir con `mem.py get` solo la relevante.
- Orquestador: sección "Contexto mínimo e inteligencia de código"; GATE 2 acepta `code_intel.py tests` como evidencia de cobertura de tests; change-request combina `spec_diff_impact.py` (spec) + `code_intel.py impact` (código).

### Changed
- `harness_doctor.py`: 12 scripts del orquestador (antes 10), chequea `.codeintel/` en `.gitignore` y existencia del índice.

## [2.2.0] - 2026-08-20

### Added
- **Matriz de autoridad** (`spec/authority-matrix.yaml`, plantilla en `sdlc-orchestrator/assets/`): un rol dueño por artefacto de la spec; cambiarla requiere PR (gobierno auditado).
- **Recibos con rol**: `receipt.py emit --role <rol>` rechaza la emisión si el rol no es el owner declarado; `verify` re-valida el rol contra la matriz vigente; `status` muestra el rol emisor.
- **`authority_check.py`** (orquestador): validación standalone de autoría (`--role` o `--author` + `spec/team-roster.yaml`) para CI.
- Plantillas `CODEOWNERS-template` (frontera dura en Git con branch protection), `team-roster-template.yaml` y workflow `ci-spec-governance.yml` (autoridad + gates por PR).

## [2.1.0] - 2026-08-20

### Added
- **`sdlc-solution-architect`** (Fases 0-2): el arquitecto de la iniciativa. Acompaña a negocio/PO/BA a detallar historias, escribe historias técnicas (`spec/technical-stories.md`: enablers, deuda, spikes, NFRs) y elabora la propuesta de arquitectura con opciones, ADRs preliminares y scorecard. Plantillas: `technical-story-template.md`, `architecture-proposal-template.md`.
- **`sdlc-cloud-pricing`** (Fases 0 y 6): estimación CAPEX/OPEX/TCO a 3 años en AWS y Azure, en 3 escenarios (mínimo viable / crecimiento esperado / pico), con supuestos versionados en YAML y fecha de validez de precios. Scripts: `cost_estimator.py`, `unit_prices.py`.
- **GATE 0** (aprobación de la iniciativa): gate humano previo a GATE 1 con tres tipos nuevos en `gate_checker.py` — `architecture-proposal`, `technical-stories`, `cost-estimation`. Los tres artefactos emiten recibo SHA-256.
- **Routing "discovery"**: iniciativa nueva o evolución de producto → PO + BA + Solution Architect + Cloud Pricing → GATE 0.
- Versionado formal del repo con releases: los 21 `.skill` se adjuntan como assets instalables en cada release.

### Changed
- `harness_doctor.py`: espera 21 skills.
- Pipeline: Fase 0 pasa a ser Discovery (PO + BA + Solution Architect + pricing).
- README: licencia con nombre completo del autor; crédito de Engram como "diferencial"; descripción precisa "arnés para agentes".

## [2.0.0] - 2026-08-13

### Added
- **`sdlc-decision-engine`**: framework de decisiones de 8 pasos (Natanzon) con `decision_engine.py` (validación + Decision Packages) y `scorecard_calculator.py`.
- **`sdlc-enterprise-architect`**: Tech Radar (ADOPT/TRIAL/ASSESS/HOLD), Principios Arquitectónicos, gobernanza por excepción, Paved Roads.
- **Risk Tiering** (`decision_sizing.py`): clasifica el Risk Tier (1/2/3) y fija el nivel de gobernanza.
- **Advice Process** (`advisor.py`): stakeholders por impacto; el consejo no es vinculante pero omitirlo bloquea GATE 1.
- **Firma arquitectónica** (`arch_signoff.py`): recibo `ARCH-xxx.json` con hash compuesto ADR + artefactos de diseño.
- `gate_checker.py --tipo adr`: validación semántica de los 8 pasos, Tech Radar y firma vigente.

## [1.1.0] - 2026-08-08

### Added
- **Receipts** (`receipt.py`): recibos SHA-256 emit/verify/status/revoke; invalidación automática al cambiar el artefacto.
- **Routing orgánico**: rutas directo / exploración delegada / hotfix / full-pipeline / change-request.
- **Fase 8 — Archivo**: merge de delta-specs, cierre del ciclo.
- `harness_doctor.py` (health check) y `detect_stack.py` (TDD en pausa sin test runner).
- Perfiles de modelo por fase (`references/model-profiles.md`).

## [1.0.0] - 2026-08-01

### Added
- Versión inicial: 15 skills de roles + `sdlc-memory` (Git-nativa, 3 scopes, políticas y desviaciones, MCP), pipeline Fases -1 a 7, gates 1/2/2.5/3, SDD + TDD.
