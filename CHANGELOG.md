# Changelog

Todas las novedades relevantes del arnés se documentan aquí. Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y versionado [SemVer](https://semver.org/lang/es/).

**Regla de versionado del arnés:**
- **MAJOR** (x.0.0): cambios incompatibles en gates, recibos o formato de spec (rompen pipelines existentes).
- **MINOR** (2.x.0): skills nuevas, gates nuevos, features retrocompatibles.
- **PATCH** (2.1.x): correcciones en scripts, plantillas o documentación.

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
- **Risk Tiering** (`decision_sizing.py`): Tier 1/2/3 con gobernanza proporcional al riesgo.
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
