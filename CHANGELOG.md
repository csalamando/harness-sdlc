# Changelog

Todas las novedades relevantes del arnés se documentan aquí. Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y versionado [SemVer](https://semver.org/lang/es/).

**Regla de versionado del arnés:**
- **MAJOR** (x.0.0): cambios incompatibles en gates, recibos o formato de spec (rompen pipelines existentes).
- **MINOR** (2.x.0): skills nuevas, gates nuevos, features retrocompatibles.
- **PATCH** (2.1.x): correcciones en scripts, plantillas o documentación.

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
