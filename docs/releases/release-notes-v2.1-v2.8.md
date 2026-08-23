# Release Notes — Arnés SDLC

Texto listo para pegar en GitHub → Releases → Draft a new release. Orden: la más reciente primero.

---

## v2.8.0 — Prototipos de pantalla gobernados (Penpot)

**Tag sugerido:** `v2.8.0` · **Título:** `v2.8.0 — Prototipos de pantalla gobernados`

Las pantallas con sus flujos de interacción pasan a ser un artefacto de validación temprana: negocio ve y navega el prototipo **antes** de escribir código, y su aprobación es el contrato visual del sprint. Sin prototipo aprobado, el Dev Front no implementa — cero sorpresas en la demo.

### Added
- **Estándar Penpot** (open-source MPL-2.0, self-hostable): diseños en estándares web (SVG/CSS/JSON), prototipado interactivo nativo, design tokens sincronizables con `spec/tokens.json` y servidor MCP oficial para que el agente cree y modifique pantallas. La razón de gobierno: el archivo es exportable y **versionable en Git** — la fuente de verdad vive en `spec/ux/`, no en una nube propietaria.
- **Estructura gobernada `spec/ux/`** (owner `ux-designer`, condicional a iniciativas con UI): `screen-inventory.md` (inventario PANT-xx: HU que cubre, ROL que la opera, estados loading/empty/error/success, interacciones con destino), `prototipo.penpot` (archivo versionado) y `exports/` (renders PNG/SVG para revisión en GATE 1).
- **Gobierno**: GATE 1 exige inventario con recibo vigente para las pantallas del sprint; cambios en HU/flujos/roles revocan el recibo vía `spec_diff_impact.py` y las pantallas se re-aprueban. Sin MCP disponible, inventario y wireframes se entregan igualmente (degradación elegante). Alternativa Figma documentada: el artefacto gobernado es el export versionado, nunca el archivo vivo en la nube.
- **Plantilla** `sdlc-ux-designer/assets/screen-inventory-template.md`.
- **`gate_checker.py --tipo screen-inventory`**: 9 checks + validación cruzada — las HU-xx citadas en el inventario deben existir en `user-stories.md`.
- **Matriz de autoridad**: `spec/ux/` → `ux-designer`.

### Changed
- `sdlc-ux-designer/SKILL.md`: sección "Prototipos de pantalla gobernados (condicional, v2.8)", DoD con inventario + recibo, herramientas propias con Penpot como estándar.
- `sdlc-orchestrator/SKILL.md`: autoridad sobre `spec/ux/` y regla de GATE 1.
- README (UX con prototipo gobernado, §4b) y Guía de uso (§5j) documentan la versión.

**Asset:** `sdlc-harness-v2.8.0-skills.zip` — las 21 skills `.skill` actualizadas (instalación: descomprimir cada `.skill` en el directorio de skills de tu agente; ver Guía de uso §2).

---

## v2.7.0 — Roles gobernados + PDD

**Tag sugerido:** `v2.7.0` · **Título:** `v2.7.0 — Roles gobernados + PDD`

Dos huecos de la Fase 1 quedan cerrados con artefactos versionados y con dueño, sin skills ni gates nuevos: el "Como <rol>" de las historias deja de ser una palabra libre, y las iniciativas que automatizan procesos existentes (RPA/BPM) ya no pueden diseñar el TO-BE sin la firma del Process Owner sobre el AS-IS.

### Added
- **Catálogo de roles gobernado (`spec/roles.md`)**: cada rol (`ROL-xx`) declara **acciones que habilita + contexto/condiciones + reglas que lo restringen** (BR/SEC referenciadas). Los conflictos de interés entre roles se declaran en el catálogo y su priorización la firma el PO. El Architect deriva la matriz de permisos/RBAC del diseño desde este artefacto. Cambiar un rol revoca los recibos de lo que dependa de él (HU, UX, test-plan) vía `spec_diff_impact.py`.
- **PDD — Process Definition Document (`spec/process-definition.md`, condicional)**: para iniciativas que automatizan o rediseñan un proceso existente (RPA, BPM, modernización). Captura el proceso **AS-IS**: disparadores, flujo (detalle en BPMN con lanes por ROL-xx vía `sdlc-diagrams`), reglas BR-xxx, **catálogo de excepciones** (conocidas/desconocidas), volúmenes y SLA, aplicaciones involucradas, riesgos y supuestos. **Sin firma del Process Owner (recibo SHA-256) no hay diseño TO-BE**.
- **Plantillas** en `sdlc-business-analyst/assets/`: `roles-template.md` y `pdd-template.md`.
- **`gate_checker.py`**: nuevos tipos `roles` y `process-definition`; validación cruzada — todo ROL-xx citado en `user-stories.md` debe existir en el catálogo (también al validar `--tipo user-stories` cuando existe `roles.md`).
- **Matriz de autoridad**: `spec/roles.md` y `spec/process-definition.md` → `business-analyst`.

### Changed
- `sdlc-business-analyst/SKILL.md`: gobierna dos artefactos condicionales más; DoD exige que toda historia cite un ROL-xx existente y, si la iniciativa automatiza un proceso, PDD firmado por el Process Owner.
- `sdlc-orchestrator/SKILL.md`: sección de autoridad con roles y PDD del BA.
- README (BA con roles gobernados y PDD, §4b) y Guía de uso (§5i) documentan la versión.

**Asset:** `sdlc-harness-v2.7.0-skills.zip` — las 21 skills `.skill` actualizadas (instalación: descomprimir cada `.skill` en el directorio de skills de tu agente; ver Guía de uso §2).

---

## v2.6.0 — Diagramas como mecanismo de aceptación de cambios

**Tag sugerido:** `v2.6.0` · **Título:** `v2.6.0 — Diagramas como mecanismo de aceptación`

Los diagramas dejan de ser solo documentación: son un **punto de control de gobierno**. Ningún diagrama cuenta como válido sin recibo de aprobación del rol dueño sobre su contenido — un cambio de IaC o de pipeline sin diagrama aprobado **no está aceptado**.

### Added
- **Dos direcciones con gobierno distinto:**
  - **Derivados de fuente** (se recrean, NUNCA se editan a mano): la regeneración *propone* el cambio → el diff en Git se revisa → el rol dueño lo *acepta* con `receipt.py emit --role <rol>`.
  - **De diseño** (C4, BPMN, secuencia, Gantt, GitFlow): edición manual, pero si la spec que representan cambia, `spec_diff_impact.py` revoca su recibo y deben re-aprobarse.
- **`iac_to_diagram.py`** (nuevo, `sdlc-diagrams/scripts/`): topología de despliegue derivada de `terraform.tfstate` (lo *realmente* desplegado) o ARM/Bicep compilado. Iconos oficiales AWS/Azure/GCP, clusters por módulo/resource group. Python stdlib puro — no ejecuta Terraform. `check` = **drift detection** (exit 1 si el diagrama difiere de la fuente).
- **`pipeline_diagram.py`**: flowchart Mermaid por workflow de GitHub Actions (triggers, jobs, `needs:`) + validación de `needs:` inexistentes y ciclos — sin binarios externos. `validate` / `check`.
- **`diagram_render.py`**: render headless a SVG/PNG vía drawio-desktop CLI (el SVG embebe el fuente: la imagen sigue editable) o mmdc (renderiza bloques Mermaid dentro de Markdown — doc-as-code). Motores opcionales con degradación elegante.
- **Matriz de autoridad**: `spec/diagrams/despliegue.drawio` → `cloud-engineer`; `spec/diagrams/pipeline-cicd.md` → `devops-engineer`.
- **Gates**: GATE 3 exige diagramas derivados regenerados con recibo vigente; Fase 8 corre los `check` de drift; en CI, un job con `check` falla el PR si hay drift.

### Changed
- `harness_doctor.py`: compila los 3 scripts de `sdlc-diagrams` y reporta motores de render disponibles (informativo, nunca bloquea).
- `sdlc-orchestrator/SKILL.md`: sección "Diagramas como mecanismo de aceptación"; GATE 3 y Fase 8 ampliados.
- README §4e y Guía de uso §5h documentan la versión.

**Asset:** `sdlc-harness-v2.6.0-skills.zip` — las 21 skills `.skill` actualizadas (instalación: descomprimir cada `.skill` en el directorio de skills de tu agente; ver Guía de uso §2).

---

## v2.5.0 — Sprint Review

**Tag sugerido:** `v2.5.0` · **Título:** `v2.5.0 — Sprint Review`

El arnés cierra el ciclo con datos: al terminar cada sprint se genera un **Sprint Review** versionado con el avance del proyecto, el desempeño del propio arnés y la tendencia respecto al sprint anterior — la base para ajustar skills y proceso con evidencia, no con intuición.

### Added
- **`sprint_review.py`** (orquestador, herramienta CLI 16): genera `spec/reports/sprint-review-NN.md` — un archivo por sprint (no se sobrescribe → serie histórica). Secciones, todas derivadas de fuentes gobernadas (recibos, usage.jsonl, memorias — cero narración del agente):
  1. **Resumen ejecutivo**: artefactos aprobados, % de gates al primer intento, trabajo rehecho, tokens, memorias learning.
  2. **Avance del proyecto**: recibos vigentes y rehechos por gate (un "rehecho" creciente señala gates débiles o change-requests frecuentes).
  3. **Desempeño del arnés**: embebe las métricas de skills de v2.4 (aporte, cobertura/freestyle, señales).
  4. **Tiempos del pipeline**: lead time por gate según timestamps de los recibos.
  5. **Tendencia vs sprint anterior**: los KPIs se embeben como comentarios HTML en cada review y el propio script los relee para comparar (`sprint-review-01` vs `02` vs ...).
  6. **Aprendizajes y acciones**: memorias `learning` del período + acciones derivadas de las señales.
- **Fase 8**: generar el Sprint Review es ahora paso obligatorio del cierre de sprint; las señales se guardan como memoria `tipo: learning` — la mejora del arnés se retroalimenta sola.
- **Trío de artefactos de reporte** (sin duplicación): `METRICS.md` = tablero vivo entre sprints (se sobrescribe) · `sprint-review-NN.md` = snapshot histórico · `impact-report.md` (Product Analyst, Fase 7) = impacto de negocio.

> Nota: las cifras son acumuladas al cierre del sprint (los recibos no llevan etiqueta de sprint); la tendencia compara esos snapshots.

### Changed
- `harness_doctor.py`: espera 14 scripts del orquestador (antes 13).
- `sdlc-orchestrator/SKILL.md`: Fase 8 paso 5 = Sprint Review; sección de telemetría ampliada; lista de scripts.
- README §4d y Guía de uso §5g documentan la versión.

**Asset:** `sdlc-harness-v2.5.0-skills.zip` — las 21 skills `.skill` actualizadas (instalación: descomprimir cada `.skill` en el directorio de skills de tu agente; ver Guía de uso §2).

---

## v2.4.0 — Telemetría de skills

**Tag sugerido:** `v2.4.0` · **Título:** `v2.4.0 — Telemetría de skills`

La disciplina no se narra, se mide: cuánto aporta cada skill, cuántos tokens consume y — lo más importante — **si el agente de verdad trabaja a través de las skills** o las usa de adorno. Sin meter telemetría en el contexto: la escritura es un flag en comandos que ya existen; la lectura es bajo demanda.

### Added
- **`skill_metrics.py`** (orquestador, herramienta CLI 15):
  - `use --skill <rol> --fase <N>`: el orquestador registra cada activación (append-only en `spec/metrics/usage.jsonl`).
  - `report` → `spec/METRICS.md` con tres vistas:
    1. **Aporte**: artefactos con recibo por skill, % de gates al primer intento, tokens por skill.
    2. **Cobertura (detector de freestyle)**: cruza fases con activaciones — un rol con artefactos pero sin activación registrada = el agente trabajó por fuera de la skill; una activación sin artefactos = skill de adorno.
    3. **Señales**: accionables para mejorar skills (rechazos de gate repetidos, costo alto por artefacto, skills sin uso).
- **`receipt.py emit` con telemetría**: `--tokens-in/-out --tokens-src reportado|estimado --attempts K`. Fuente `reportada` = telemetría exacta de la plataforma del agente; fuente `estimada` = chars/4 del artefacto, calculada por el script — nunca depende de que el agente "se acuerde".
- **Cierre del loop**: en Fase 8 el orquestador genera `METRICS.md` y guarda las señales como memoria `learning`.

### Changed
- `harness_doctor.py`: 13 scripts del orquestador (antes 12).
- README §4d y Guía §5f documentan la versión. `METRICS.md` nunca se inyecta en paquetes de contexto.

**Asset:** usar el ZIP de v2.5.0 (incluye todo lo de v2.4) o regenerar desde este tag.

---

## v2.3.0 — Contexto mínimo e inteligencia de código

**Tag sugerido:** `v2.3.0` · **Título:** `v2.3.0 — Contexto mínimo e inteligencia de código`

El contexto del agente pasa a ser un recurso gobernado: el agente lee solo lo que necesita, con acceso rápido a spec, código y memorias. Inspirado en [Gortex](https://github.com/zzet/gortex) pero reimplementado a medida: **Python stdlib puro, sin daemon, sin dependencias**.

### Added
- **`code_intel.py`** (orquestador): motor de inteligencia de código con índice SQLite derivable en `.codeintel/index.db` (gitignored, reindex incremental por SHA-256 en milisegundos). Extracción por niveles: `ast` para Python y patrones para 15 lenguajes más (JS/TS/Go/Java/Rust/C/C++/Ruby/PHP/C#/Kotlin/Swift). Comandos: `index`, `context` (esqueleto o cuerpo exacto de un símbolo — sin leer archivos completos), `impact` (blast radius con razón por arista), `tests` (tests candidatos, transitivos, como evidencia para GATE 2), `search` (FTS5 sobre firmas/docstrings), `map`, `stats`, `symbol`.
- **`spec_index.py`** (orquestador): genera `spec/INDEX.md`, digest de una página (sha256 + tamaño + resumen por artefacto). El agente se orienta con el digest y abre solo lo necesario.
- `context_packager.py`: antepone `spec/INDEX.md` e inyecta instrucciones de `code_intel` para roles de código (`backend-dev`, `frontend-dev`, `qa`, `sre`) cuando el índice existe (`--code-root`).
- `mem.py search --brief`: una línea por memoria; abrir con `mem.py get <id>` solo la relevante.
- Change-request con impacto total: `spec_diff_impact.py` (spec) + `code_intel.py impact` (código).
- GATE 2: si hay índice, los tests corridos deben cubrir lo reportado por `code_intel.py tests` para los símbolos tocados.
- Degradación elegante: sin índice, el arnés opera con lectura normal (capacidad opcional, como drawio sin MCP).

### Changed
- `harness_doctor.py`: 12 scripts del orquestador; verifica `.codeintel/` en `.gitignore` y existencia del índice.
- `sdlc-orchestrator/SKILL.md`: nueva sección "Contexto mínimo e inteligencia de código (v2.3)".
- README §4c y Guía de uso §5e documentan la versión.

**Asset:** `sdlc-harness-v2.3.0-skills.zip` — las 21 skills `.skill` actualizadas (instalación: descomprimir cada `.skill` en el directorio de skills de tu agente; ver Guía de uso §2).

---

## v2.2.0 — Autoridad por rol

**Tag sugerido:** `v2.2.0` · **Título:** `v2.2.0 — Autoridad por rol`

¿Cómo garantizar que un dev no "apruebe" decisiones de arquitectura o que un arquitecto no escriba las historias de usuario? No prohibiendo la participación (el Advice Process la exige), sino haciendo que **el artefacto no autorizado no cuente**.

### Added
- **Matriz de autoridad** (`spec/authority-matrix.yaml`, plantilla en `sdlc-orchestrator/assets/`): un rol dueño por artefacto, versionada en Git.
- **Recibos con rol** (`receipt.py emit --role <rol>`): si el artefacto tiene owner, el rol emisor debe coincidir o el recibo se rechaza; `verify` re-valida contra la matriz vigente.
- **`authority_check.py`**: validación standalone (`--role` o `--author <usuario-git> --team spec/team-roster.yaml`) para CI; incluye plantilla de workflow `assets/ci-spec-governance.yml`.
- **CODEOWNERS** (plantilla `assets/CODEOWNERS-template`): con branch protection, un PR que toca `spec/adr/` no se mergea sin revisión del Arquitecto.

Jerarquía de garantías: convención (SKILL.md) → gate (recibo con rol) → CI → Git (CODEOWNERS + branch protection).

---

## v2.1.0 — Arquitectura de la iniciativa + pricing cloud

**Tag sugerido:** `v2.1.0` · **Título:** `v2.1.0 — Solution Architect, Cloud Pricing y GATE 0`

El arquitecto participa desde la concepción de la iniciativa, donde las decisiones de costo y forma determinan si el negocio aprueba construir.

### Added
- **`sdlc-solution-architect`** (skill 20): historias técnicas (enablers, deuda, spikes, NFRs), propuesta de arquitectura con ≥2 opciones, ADRs preliminares y scorecard.
- **`sdlc-cloud-pricing`** (skill 21): CAPEX/OPEX/TCO en 3 escenarios para AWS y Azure, con `cost_estimator.py` y supuestos versionados en YAML.
- **GATE 0**: aprobación humana de la iniciativa (propuesta + historias técnicas + costos, con recibos SHA-256). Tipos nuevos de gate: `architecture-proposal`, `technical-stories`, `cost-estimation`.
- Routing "discovery": PO + BA + Solution Architect + Cloud Pricing → GATE 0.

**Asset:** `sdlc-harness-v2.1.0-skills.zip` (ya generado).
