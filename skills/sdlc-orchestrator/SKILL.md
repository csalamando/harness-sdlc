---
name: sdlc-orchestrator
description: "Orquestador del arnés SDLC con SDD+TDD. Usar para coordinar el pipeline completo de desarrollo: activar roles en orden (PO, BA, UX, Architect, Security, Data, Dev Back, Dev Front, QA, DevOps, Cloud, SRE), elegir la ruta mínima adecuada (routing orgánico), verificar gates con recibos vinculados al contenido, gestionar cambios de spec con relaciones supersedes/conflicts_with, archivar sprints, empaquetar contexto mínimo por rol, consultar el código por símbolos (blast radius, tests candidatos) con code_intel, generar el digest de la spec, medir el aporte y la disciplina de las skills (skill_metrics), emitir el sprint review de cierre, garantizar la aceptación de cambios vía diagramas derivados con recibo y mantener trazabilidad código-test-historia. Dispara ante: ejecutar pipeline SDLC, coordinar equipo de agentes, verificar gates, gestionar cambio de spec, modos full-pipeline/hotfix/change-request, health check del arnés, blast radius, qué tests correr, reducir contexto del agente, sprint review, drift de diagramas, catálogo de roles, PDD, prototipo de pantallas UX."
harness-role: orchestrator
harness-phases: "transversal"
harness-owns: "spec/authority-matrix.yaml, spec/team-roster.yaml, spec/risk-tier.yaml"
---


# SDLC Orchestrator

Coordina el pipeline SDLC basado en SDD (spec-driven) y TDD. No produce artefactos de negocio: activa roles, verifica gates y mantiene el estado del pipeline.

## Pipeline (ver references/pipeline.md para el detalle completo)

```
FASE -1 Setup (DevOps + detect_stack)
→ FASE 0 Visión + Discovery de la iniciativa: PO + Solution Architect (propuesta + pricing) [GATE 0: aprobación de la iniciativa]
→ FASE 1 BA (historias, reglas, roles, PDD) → FASE 2 UX + Architect + Security + Data
→ FASE 3 Spec consolidada [GATE 1 humano] → FASE 4 Dev Back ∥ Dev Front (TDD)
→ FASE 5 QA + Security DAST [GATE 2/2.5] → FASE 6 DevOps + Cloud [GATE 3] → PROD
→ FASE 7 SRE opera + Product Analyst mide → realimenta backlog del PO
→ FASE 8 Archivo: merge de delta-specs + sprint review + cierre del ciclo
```

## Routing orgánico: elegir la ruta mínima adecuada

No todo trabajo merece el pipeline completo. Evaluar tamaño y ambigüedad ANTES de decidir la ruta; el tamaño por sí solo nunca activa el pipeline completo — solo una petición explícita o una propuesta aceptada.

| Situación | Ruta |
|---|---|
| Cambio mecánico ya entendido, 1-3 archivos, spec intacta | **Directo**: dev con TDD + gate 2. Sin tocar fases 0-3 |
| Se necesita explorar 4+ archivos para entender, o investigación amplia | **Exploración delegada**: una sub-tarea acotada de lectura; luego se decide la ruta con evidencia |
| Bug en producción | **Hotfix**: QA reproduce con test → dev corrige (TDD) → gates 2 y 3 |
| Iniciativa o evolución de producto nueva (sin propuesta aprobada) | **Discovery**: PO + BA + `sdlc-solution-architect` + `sdlc-cloud-pricing` → propuesta de arquitectura con opciones, historias técnicas y estimación CAPEX/OPEX → GATE 0 |
| Ambigüedad sustancial (requisitos, diseño o alcance poco claros) | **Full-pipeline**: proponer al usuario; iniciar solo tras aprobación |
| Cambio de alcance aprobado | **Change-request**: ver Gestión de cambios |

Independientemente de la ruta, los gates de entrega (2, 2.5, 3) siempre aplican.

## Gobernanza de decisiones (Risk Tiering + Firma Arquitectónica)

El Arquitecto de Software es el **Decision Owner técnico**: el PO define el QUÉ/CUÁNDO y nunca aprueba decisiones técnicas; el Arquitecto define el CÓMO y firma. En Fase 2:

1. **Risk Triage**: ejecutar `decision_sizing.py --spec spec/ --output spec/risk-tier.yaml`.
   - **Tier 3** (bajo): ADR simplificado, gate automático.
   - **Tier 2** (medio): 8 pasos de Natanzon + Advice Process con peers.
   - **Tier 1** (alto: PII, pagos, auth, datos críticos): 8 pasos + Advice Process completo + revisión del Enterprise Architect.
2. **Decision Engine**: cada decisión significativa usa la skill `sdlc-decision-engine` y la plantilla `assets/adr-template-8steps.md` del Arquitecto.
3. **Advice Process**: `advisor.py --adr <adr> --risk-tier N` identifica stakeholders por impacto (Tier 1 siempre incluye Enterprise Architect). El consejo no es vinculante, pero omitir la consulta bloquea GATE 1.
4. **Paved Roads**: tecnología ADOPT del Tech Radar (`spec/tech-radar.yaml`, mantenido por el Enterprise Architect) = aprobación pre-autorizada. TRIAL requiere justificación; ASSESS/HOLD requieren ADR de excepción (HOLD además aprobación del Architecture Board).
5. **Firma**: `arch_signoff.py --adr <adr> --architect "Nombre"` emite `spec/receipts/ARCH-xxx.json`. Un ADR firmado no se modifica: se supersedea. Si el ADR cambia tras la firma, `gate_checker.py --tipo adr` detecta el recibo invalidado.

## Responsabilidades

1. Mantener `spec/pipeline-state.md`: artefacto, fase, rol dueño, estado, gate pendiente, resultado de `detect_stack.py` y Risk Tier vigente.
2. Antes de invocar un rol, verificar su DoR: entradas presentes **y con recibo vigente** (ver Recibos). Registrar la activación con `skill_metrics.py use --skill <rol> --fase <N>` (telemetría v2.4: sin este registro, el trabajo del rol cuenta como *freestyle* en METRICS.md).
3. Al recibir un artefacto, ejecutar `gate_checker.py`; si pasa, **emitir recibo** con `receipt.py emit`, incluyendo telemetría si está disponible: `--tokens-in/-out --tokens-src reportado` cuando la plataforma del agente expone el consumo, o `--tokens-src estimado` (chars/4, lo calcula el script) cuando no; `--attempts K` si el gate necesitó reintentos.
4. Armar el paquete de contexto mínimo por rol con `context_packager.py` — nunca pasar toda la spec a todos. Si existe `spec/INDEX.md` va primero (orientación de una página).
5. Ante cambio de spec: declarar relación (supersedes/conflicts_with), correr `spec_diff_impact.py` (impacto en spec) **y** `code_intel.py impact <artefacto/símbolo>` (impacto en código), revocar recibos impactados, re-ejecutar solo fases afectadas.
6. Mantener trazabilidad con `traceability_matrix.py`: historia → Gherkin → test → código.
7. Sesiones de memoria: abrir con la skill sdlc-memory al iniciar trabajo, buscar memoria relevante por fase, cerrar con resumen. Un `conflicts_with` de memoria sin resolver bloquea GATE 1.
8. Health check del arnés con `harness_doctor.py` al instalar o cuando algo falle.
9. Recomendar perfiles de modelo por fase según `references/model-profiles.md`.

## Autoridad por rol (matriz de autoridad)

Cada artefacto de `spec/` tiene **un solo rol dueño**, declarado en `spec/authority-matrix.yaml` (plantilla: `assets/authority-matrix.yaml`). Un dev puede *opinar* sobre un ADR (vía Advice Process), pero no puede *emitirlo*:

- `receipt.py emit --role <rol>`: si el artefacto tiene owner en la matriz, el rol debe coincidir o **el gate no reconoce la aprobación** (un dev emitiendo un ADR → recibo rechazado; un arquitecto emitiendo user-stories → rechazado). El rol queda registrado en el recibo y `verify` lo re-valida contra la matriz vigente.
- `authority_check.py <artefacto> --role <rol>` o `--author <usuario-git> --team spec/team-roster.yaml`: validación standalone para CI (plantilla de workflow: `assets/ci-spec-governance.yml`; roster: `assets/team-roster-template.yaml`).
- **Frontera dura en Git**: `assets/CODEOWNERS-template` + branch protection con "Require review from Code Owners" — un PR que toca `spec/adr/` no se mergea sin el Arquitecto.
- Cambiar la matriz es un cambio de gobierno: owner `orchestrator`, requiere PR y queda auditado.
- **Roles y PDD del BA (v2.7)**: `spec/roles.md` (catálogo gobernado: nombre + acciones habilitadas + contexto + restricciones) y `spec/process-definition.md` (PDD AS-IS firmado por el Process Owner, condicional a iniciativas que automatizan/rediseñan procesos) son artefactos con owner `business-analyst`. `gate_checker.py --tipo roles` valida la estructura y que los ROL-xx citados en `user-stories.md` existan en el catálogo; `--tipo process-definition` valida el PDD. Si existe `roles.md`, toda HU debe citar ROL-xx definidos.
- **Prototipo de pantallas del UX (v2.8)**: `spec/ux/` (inventario `screen-inventory.md` con PANT-xx + archivo de diseño Penpot versionado + exports PNG/SVG) es artefacto con owner `ux-designer`, condicional a iniciativas con UI. Es el **mecanismo de validación temprana con negocio**: GATE 1 exige el inventario con recibo vigente para las pantallas del sprint — sin prototipo aprobado, el Dev Front no implementa esas pantallas. `gate_checker.py --tipo screen-inventory` valida la estructura y que las HU-xx citadas existan en `user-stories.md`. Si cambian HU/flujos/roles que tocan pantallas, `spec_diff_impact.py` revoca el recibo de `spec/ux/` y las pantallas se re-aprueban.

## Recibos: confiar en evidencia, no en narración

Cuando un gate pasa, `receipt.py emit` guarda el SHA-256 exacto del artefacto en `spec/receipts/`. Antes de que cualquier fase downstream consuma ese artefacto, `receipt.py verify` comprueba que el contenido no cambió ni un byte desde la aprobación. Si cambió, el recibo se invalida solo y el gate debe re-ejecutarse. Un cambio de spec (`spec_diff_impact.py`) implica revocar los recibos de todos los artefactos impactados. Un artefacto nunca se aprueba dos veces sin nueva evidencia; una sola corrección acotada por gate antes de escalar a humano.

## Gestión de cambios de spec

1. Declarar la relación del cambio: **supersedes** (reemplaza a la versión anterior — flujo normal) o **conflicts_with** (contradice — requiere resolución humana antes de continuar, bloquea GATE 1).
2. `spec_diff_impact.py --cambiado <artefacto> --relation <rel>` lista el downstream invalidado.
3. `receipt.py revoke` sobre cada artefacto impactado; re-ejecutar solo sus fases.
4. Nueva versión de spec + entrada en CHANGELOG.

## Fase 8: Archivo (cierre del ciclo SDD)

Al completarse y verificarse un sprint/incremento:
1. Verificar que los recibos de gates 2/2.5/3 están vigentes.
2. Fusionar los cambios de spec aprobados durante el sprint (delta-specs) en la spec maestra; la versión anterior queda como histórico.
3. Marcar memorias superseded según corresponda; resolver conflictos pendientes.
4. `traceability_matrix.py` final en verde + `receipt.py status` en `spec/receipts/` + drift de diagramas en verde (`iac_to_diagram.py check` y `pipeline_diagram.py check` si existen las fuentes).
5. Generar el **Sprint Review** con `sprint_review.py --sprint <N>` (snapshot versionado en `spec/reports/sprint-review-NN.md`: avance, desempeño del arnés con las métricas de skills, lead times, tendencia vs sprint anterior y aprendizajes) y guardar una memoria `tipo: learning` con las señales relevantes (skills con rechazos de gate, tokens altos, freestyle detectado) — la retroalimentación de mejora queda institucionalizada. `METRICS.md` queda como tablero vivo entre sprints; el sprint review es el registro histórico.
6. Cerrar sesión de memoria con resumen del sprint. El ciclo queda cerrado y la próxima iteración arranca desde una spec consolidada.

## Telemetría de skills (v2.4) y Sprint Review (v2.5)

La disciplina no se narra, se mide — sin meter telemetría en el contexto del agente (escritura por CLI en comandos que ya existen; lectura bajo demanda). `spec/METRICS.md` responde:

1. **Aporte**: qué generó cada skill (artefactos con recibo), tasa de gates al primer intento (`--attempts`) y tokens por skill — separando fuente `reportada` (telemetría exacta de la plataforma) de `estimada` (chars/4 del artefacto, sin depender del agente).
2. **Cobertura (freestyle detector)**: cruza fases con las activaciones en `spec/metrics/usage.jsonl`. Un rol con artefactos pero sin activación registrada = **trabajo fuera de la skill**; una activación sin artefactos = skill de adorno. Es la evidencia de que el agente trabaja *a través* del arnés y no por fuera de él.
3. **Señales**: candidatas accionables para mejorar skills (rechazos de gate repetidos, costo por artefacto alto, skills sin uso).

Regla: `METRICS.md` nunca se inyecta en paquetes de contexto; se consulta en Fase 8 o cuando el humano lo pida. Al cerrar el sprint, `sprint_review.py` lo embebe como sección 3 del **Sprint Review** versionado en `spec/reports/`, junto con avance, lead times, tendencia vs sprint anterior y aprendizajes.

## Contexto mínimo e inteligencia de código (v2.3)

El contexto del agente es un recurso gobernado, no infinito. Tres mecanismos:

1. **`spec_index.py`**: genera `spec/INDEX.md`, un digest de una página con hash + resumen de cada artefacto. Regenerar al abrir sesión y tras cada artefacto aprobado (es barato). El agente lee el digest y solo abre lo que necesita, verificando recibo.
2. **`code_intel.py`**: índice de símbolos del código (Python vía `ast`, 15 lenguajes más por patrones) en SQLite derivable (`<proyecto>/.codeintel/index.db`, gitignored, incremental por SHA-256). Sin daemon ni dependencias. Regla para roles de desarrollo: **no leer archivos completos** — usar `context` (cuerpo exacto del símbolo o esqueleto del archivo), `impact` (blast radius antes de editar), `tests` (tests candidatos a correr), `search` (firmas/docstrings). Reindexar al abrir sesión (`index` es incremental, ~ms sin cambios).
3. **`mem.py search --brief`**: una línea por memoria (id + título); abrir con `mem.py get <id>` solo la relevante.

En GATE 2, `code_intel.py tests <símbolo>` es evidencia de qué tests debían correr. Si el índice no existe, el arnés degrada a lectura normal de archivos (como drawio sin MCP: la capacidad es opcional, nunca bloquea).

## Scripts

Ejecutar con `python3 scripts/<nombre>.py`:

- `gate_checker.py <artefacto> --tipo <tipo>`: valida checklist de salida de un artefacto. Exit 0 = pasa gate.
- `receipt.py emit|verify|status|revoke`: recibos de aprobación vinculados al SHA-256 del artefacto. `emit` acepta telemetría opcional: `--tokens-in/-out --tokens-src reportado|estimado --attempts K`.
- `skill_metrics.py use|report`: telemetría de skills — `use` registra la activación de un rol (append-only en `spec/metrics/usage.jsonl`); `report` genera `spec/METRICS.md` (tablero vivo) con aporte, cobertura (freestyle detector) y señales.
- `sprint_review.py --sprint <N>`: genera `spec/reports/sprint-review-NN.md` al cerrar el sprint — snapshot versionado con avance, desempeño del arnés, lead times por gate, tendencia vs sprint anterior y aprendizajes.
- `context_packager.py --rol <rol> --spec-dir spec/`: lista mínima de archivos que ese rol necesita.
- `spec_diff_impact.py --cambiado <artefacto> [--relation supersedes|conflicts_with]`: impacto downstream de un cambio.
- `traceability_matrix.py --spec-dir spec/ --tests-dir tests/ --src-dir src/`: matriz historia → test → código; detecta brechas.
- `detect_stack.py [--project-dir <ruta>]`: detecta stack, test runner y disponibilidad de Strict TDD (Fase -1). Exit 2 si no hay runner.
- `harness_doctor.py [--skills-dir <ruta>] [--project-dir <ruta>]`: health check read-only del arnés (skills, scripts, estructura spec/).
- `decision_sizing.py --spec spec/ --output spec/risk-tier.yaml`: clasifica el Risk Tier (1/2/3) y fija el nivel de gobernanza.
- `advisor.py --adr <adr> --risk-tier N [--output <json>]`: identifica stakeholders del Advice Process por áreas de impacto.
- `arch_signoff.py --adr <adr> --architect "Nombre"`: firma arquitectónica; genera recibo ARCH-xxx.json con SHA-256 del ADR y artefactos de diseño.
- `authority_check.py <artefacto> --role <rol> | --author <usuario> --team spec/team-roster.yaml`: valida que quien emite/firma un artefacto sea su rol dueño según `spec/authority-matrix.yaml`. Exit 1 si no está autorizado.
- `code_intel.py --root <proyecto> index|symbol|context|impact|tests|search|map|stats`: inteligencia de código local (grafo de símbolos en SQLite, incremental, sin daemon). `context` evita leer archivos completos; `impact` calcula blast radius; `tests` lista tests candidatos para GATE 2.
- `spec_index.py [--spec-dir spec/]`: regenera `spec/INDEX.md`, digest de una página con hash y resumen por artefacto.
- `manifest_check.py --write|--check|--summary` (v2.9): deriva el manifiesto del arnés (`assets/harness-manifest.yaml`) desde el frontmatter `harness-*` de cada SKILL.md y la lista de scripts en disco. `--check` falla si hay drift o inconsistencias cruzadas (gate declarado inexistente, artefacto `owns` fuera de la matriz de autoridad). El manifiesto es derivado — nunca se edita a mano; `harness_doctor.py` lee de él sus expectativas.

Los scripts de diagramas viven en `sdlc-diagrams/scripts/`: `iac_to_diagram.py`, `pipeline_diagram.py`, `diagram_render.py` (ver Diagramas como mecanismo de aceptación).

## Gates

- **GATE 0** (humano — aprobación de la iniciativa): propuesta de arquitectura con ≥2 opciones y recomendación justificada (`gate_checker.py spec/architecture-proposal.md --tipo architecture-proposal`), historias técnicas registradas (`--tipo technical-stories`) y estimación CAPEX/OPEX vigente (`--tipo cost-estimation`). Los tres artefactos emiten recibo GATE 0. Sin iniciativa aprobada, no hay pipeline de construcción.
- **GATE 1** (humano): spec consolidada aprobada + sin conflicts_with de memoria pendientes + `policy check` en verde (toda política org mandatory attestada compliant o con desviación aprobada vigente) + **para cada ADR Tier 1-2**: `gate_checker.py --tipo adr` en verde (8 pasos, scorecard, Advice Log, Tech Radar, firma `arch_signoff.py` vigente). Si la iniciativa tiene UI: inventario de pantallas `spec/ux/screen-inventory.md` con recibo vigente (`--tipo screen-inventory`) — sin prototipo aprobado, el Dev Front no implementa esas pantallas. Sin esto, cero código.
- **GATE 2**: todas las historias verificadas E2E. Si hay índice `code_intel`, los tests corridos deben cubrir lo reportado por `code_intel.py tests` para los símbolos tocados. Bug crítico → devuelve artefacto al dev con el test que lo reproduce (una corrección acotada; si falla, escala).
- **GATE 2.5** (Security): ninguna vulnerabilidad crítica/alta abierta.
- **GATE 3**: staging validado + rollback probado + diagramas derivados (`spec/diagrams/`) regenerados desde su fuente (IaC / workflows) y con recibo vigente del rol dueño — un diagrama sin recibo vigente es un cambio de infraestructura o pipeline NO aceptado.

Todo gate que pasa emite recibo; todo consumo downstream verifica recibo.

## Diagramas como mecanismo de aceptación de cambios (v2.6)

Los diagramas no son solo documentación: son un punto de control. Regla rectora por dirección (detalle y scripts en `sdlc-diagrams`):

- **Derivados de fuente** (despliegue desde `terraform.tfstate`/ARM; pipeline CI/CD desde `.github/workflows/`): **se recrean, nunca se editan a mano**. El script regenera → el diff en Git es la propuesta de cambio → el rol dueño revisa el contenido y lo **acepta con recibo** (`receipt.py emit --role cloud-engineer|devops-engineer`). Modo `check` (exit 1 = drift) en CI y en Fase 8.
- **De diseño** (C4, secuencia, BPMN, Gantt, GitFlow): se editan a mano, pero si la spec que representan cambia (ADR supersedeado, `architecture.md`, reglas de negocio), `spec_diff_impact.py` revoca el recibo del diagrama y debe actualizarse y re-aprobarse antes de que el downstream continúe.
- El render SVG/PNG (`diagram_render.py`) es una vista derivada sin recibo propio; se regenera tras cada aprobación para doc-as-code.

## Definition of Ready / Done

Usar los checklists de `references/dor-dod.md` en cada gate. Un artefacto sin DoD cumplido no avanza de fase.
