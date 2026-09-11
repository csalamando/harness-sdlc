---
name: sdlc-orchestrator
description: "Orquestador del arnés SDLC con SDD+TDD. Usar para coordinar el pipeline completo de desarrollo: activar roles en orden (PO, BA, UX, Architect, Security, Data, Dev Back, Dev Front, QA, DevOps, Cloud, SRE), elegir la ruta mínima adecuada (routing orgánico), verificar gates con recibos vinculados al contenido, gestionar cambios de spec con relaciones supersedes/conflicts_with, archivar sprints, empaquetar contexto mínimo por rol, consultar el código por símbolos (blast radius, tests candidatos) con code_intel, generar el digest de la spec, medir el aporte y la disciplina de las skills (skill_metrics), emitir el sprint review de cierre, garantizar la aceptación de cambios vía diagramas derivados con recibo y mantener trazabilidad código-test-historia. Dispara ante: ejecutar pipeline SDLC, coordinar equipo de agentes, verificar gates, gestionar cambio de spec, modos full-pipeline/hotfix/change-request, health check del arnés, blast radius, qué tests correr, reducir contexto del agente, sprint review, drift de diagramas, catálogo de roles, PDD, prototipo de pantallas UX."
harness-role: orchestrator
harness-phases: "transversal"
harness-owns: "spec/authority-matrix.yaml, spec/team-roster.yaml, spec/risk-tier.yaml, spec/dashboard.html, spec/METRICS.md, spec/metrics/, spec/reports/, spec/audit/, spec/pipeline-state.md"
harness-version: "2.27.1"
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

1. `spec/pipeline-state.md` es **derivado** (v2.22, N7): lo regenera `pipeline_state.py` desde la matriz de autoridad + recibos + memoria de auditoría + `detect_stack.py`. Nunca se edita a mano ni recibe recibo (certificar narración era la brecha B-14); `--check` en CI falla si hay drift.
2. Antes de invocar un rol, verificar su DoR: entradas presentes **y con recibo vigente** (ver Recibos). Registrar la activación con `skill_metrics.py use --skill <rol> --fase <N>` (telemetría v2.4: sin este registro, el trabajo del rol cuenta como *freestyle* en METRICS.md). Desde v2.16 `receipt.py emit` auto-registra la activación como respaldo contra el olvido (deduplicada contra el uso manual), pero el registro manual **antes** de activar sigue siendo la fuente primaria.
3. Al recibir un artefacto, ejecutar `gate_checker.py`; si pasa, **emitir recibo** con `receipt.py emit`, incluyendo telemetría si está disponible: `--tokens-in/-out --tokens-src reportado` cuando la plataforma del agente expone el consumo, o `--tokens-src estimado` (chars/4, lo calcula el script) cuando no; `--attempts K` si el gate necesitó reintentos.
4. Armar el paquete de contexto mínimo por rol con `context_packager.py` — nunca pasar toda la spec a todos. Si existe `spec/INDEX.md` va primero (orientación de una página).
5. Ante cambio de spec: declarar relación (supersedes/conflicts_with) y correr `spec_diff_impact.py --cambiado <art> --apply` (v2.22, N2) — la herramienta invalida derivadamente los recibos downstream y los audita; ya no depende de la memoria del agente. Además los recibos guardan el hash de sus dependencias upstream: `receipt.py verify` invalida derivadamente aunque el `--apply` se haya olvidado. Complementar con `code_intel.py impact <artefacto/símbolo>` (impacto en código) y re-ejecutar solo fases afectadas.
6. Mantener trazabilidad con `traceability_matrix.py`: historia → Gherkin → test → código.
7. Sesiones de memoria: abrir con la skill sdlc-memory al iniciar trabajo (`mem.py context` da el digest de arranque: sesión activa, último handoff, memorias vigentes, conflictos), buscar memoria relevante por fase, cerrar con handoff estructurado (`session end --goal --done --next --files`). Temas evolutivos: re-guardar con `--topic_key` estable (auto-supersede) en vez de crear duplicados. Un `conflicts_with` de memoria sin resolver bloquea GATE 1.
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

**Memoria de auditoría (v2.21, ADR-004):** toda emisión, invalidación y revocación deja un hecho append-only en `spec/audit/events.jsonl` (cadena de hash SHA-256, `ts` UTC con zona, `harness_version` obligatorios) — separada de la memoria de trabajo (`sdlc-memory`, evolutiva). Los `.receipt.json` son el estado derivado; la verdad histórica es el log: una re-aprobación ya no borra el retrabajo. Reglas: `revoke` exige `--reason` (y `--relation` cuando el motivo es un cambio de spec); los gates humanos registran `--approved-by`; inicializar una vez por proyecto con `audit_log.py init --proyecto <nombre>`; verificar la traza en CI y Fase 8 con `audit_verify.py` (exit 1 si la cadena se reescribió).

## Gestión de cambios de spec

1. Declarar la relación del cambio: **supersedes** (reemplaza a la versión anterior — flujo normal) o **conflicts_with** (contradice — requiere resolución humana antes de continuar, bloquea GATE 1).
2. `spec_diff_impact.py --cambiado <artefacto> --relation <rel>` lista el downstream invalidado.
3. `receipt.py revoke --reason "<causa>" [--relation supersedes|conflicts_with]` sobre cada artefacto impactado; re-ejecutar solo sus fases. La revocación queda en la memoria de auditoría (v2.21).
4. Nueva versión de spec + entrada en CHANGELOG.

## Fase 8: Archivo (cierre del ciclo SDD)

Al completarse y verificarse un sprint/incremento:
1. Verificar que los recibos de gates 2/2.5/3 están vigentes.
2. Fusionar los cambios de spec aprobados durante el sprint (delta-specs) en la spec maestra; la versión anterior queda como histórico.
3. Marcar memorias superseded según corresponda; resolver conflictos pendientes.
4. `traceability_matrix.py` final en verde + `receipt.py status` en `spec/receipts/` + drift de diagramas en verde (`pipeline_diagram.py check` si existe la fuente).
5. Generar el **Sprint Review** con `sprint_review.py --sprint <N>` (snapshot versionado en `spec/reports/sprint-review-NN.md`: avance, desempeño del arnés con las métricas de skills, lead times, tendencia vs sprint anterior y aprendizajes) y guardar una memoria `tipo: learning` con las señales relevantes (skills con rechazos de gate, tokens altos, freestyle detectado) — la retroalimentación de mejora queda institucionalizada. `METRICS.md` queda como tablero vivo entre sprints; el sprint review es el registro histórico.
6. Regenerar el **dashboard vivo** con `harness_graph.py --proyecto .` (v2.12, ADR-002: UN `spec/dashboard.html` — gates pintados por recibos, fase actual, loops activos, tendencias leídas de los sprint reviews, últimas sesiones/handoffs desde v2.16). También se regenera tras emitir/invalidar un recibo; `--check` en CI. Es visualización, no evidencia: no bloquea gates.
7. Cerrar sesión de memoria con handoff estructurado (`mem.py session end --goal --done --next --files`) y verificar el cierre con `mem.py close-check` (v2.16): si falta la memoria `learning`, el handoff o las activaciones en `usage.jsonl`, **el ciclo NO se archiva** (exit 1) — la disciplina de memoria y métricas deja de ser opcional. Con el cierre verificado, la próxima iteración arranca desde una spec consolidada.

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

**Grafo de código derivado (`code_graph.py`, v2.27)**: el índice SQLite es un grafo (símbolos + aristas de llamada) y esta vista lo hace visible. Gobierno — **dónde**: vive junto a `code_intel.py`; emite `<proyecto>/spec/diagrams/grafo-codigo.html` (interactivo: nodos=archivos coloreados por directorio, tamaño=nº de símbolos, filtros, top hubs) y `grafo-modulos.html` (SVG estático: acoplamiento medido entre módulos, grosor=aristas que cruzan). Ambas usan los **TOKENS_CSS del portal** y la clave compartida `dir-tema`: el toggle ☀/☾ del shell las retema en vivo (día/noche), como los diagramas IR. **Garantía de inclusión**: `harness_graph.py --proyecto` las regenera ANTES del sweep de diagramas (best-effort, nunca bloquea) y `emit_portal` las registra automáticamente en la página **Arquitectura** del portal. **Cuándo**: tras cada `code_intel.py index` (regla: reindexar al abrir sesión) y en cada regeneración del portal; `code_graph.py check` es el anti-drift (fingerprint del índice embebido en el HTML). **Quién**: lo ejecuta el rol de desarrollo/orquestador al reindexar; consume el Arquitecto (vista módulos → `spec/architecture/`) y cualquier dev (hubs, acoplamiento, archivos aislados). Matiz honesto: las aristas del índice son a nivel archivo, no símbolo→símbolo; el grafo interactivo es de archivos y el ranking de hubs de símbolos es por in-degree — no se inventa atribución. Tests, cobertura y ruido de frameworks (`describe`/`it`/`expect`) se excluyen por defecto (`--include-tests` para incluirlos).

## Scripts

Ejecutar con `python3 scripts/<nombre>.py`:

- `gate_checker.py <artefacto> --tipo <tipo>`: valida checklist de salida de un artefacto. Exit 0 = pasa gate.
- `receipt.py emit|verify|status|revoke`: recibos de aprobación vinculados al SHA-256 del artefacto. `emit` acepta telemetría opcional: `--tokens-in/-out --tokens-src reportado|estimado --attempts K`; los gates humanos registran `--approved-by` (v2.21). `revoke` exige `--reason` y acepta `--relation` (v2.21, ADR-004).
- `audit_log.py init|append` (v2.21, ADR-004): memoria de auditoría append-only (`spec/audit/events.jsonl`) con cadena de hash, `ts` UTC con zona y `harness_version` por evento. `init --proyecto` una sola vez por proyecto; los scripts del arnés anexan sus hechos automáticamente.
- `audit_verify.py [--spec-dir spec/]` (v2.21): verifica la integridad de la traza (cadena de hash, campos obligatorios, seq monotónico, génesis válido). Exit 1 = traza reescrita o incompleta. Correr en CI y en Fase 8.
- `skill_metrics.py use|report`: telemetría de skills — `use` registra la activación de un rol (append-only en `spec/metrics/usage.jsonl`); `report` genera `spec/METRICS.md` (tablero vivo) con aporte, cobertura (freestyle detector) y señales.
- `sprint_review.py --sprint <N>`: genera `spec/reports/sprint-review-NN.md` al cerrar el sprint — snapshot versionado con avance, desempeño del arnés, lead times por gate, tendencia vs sprint anterior y aprendizajes.
- `context_packager.py --rol <rol> --spec-dir spec/`: lista mínima de archivos que ese rol necesita.
- `spec_diff_impact.py --cambiado <artefacto> [--relation supersedes|conflicts_with]`: impacto downstream de un cambio.
- `traceability_matrix.py --spec-dir spec/ --tests-dir tests/ --src-dir src/`: matriz historia → test → código; detecta brechas.
- `detect_stack.py [--project-dir <ruta>]`: detecta stack, test runner y disponibilidad de Strict TDD (Fase -1). Exit 2 si no hay runner.
- `harness_doctor.py [--skills-dir <ruta>] [--project-dir <ruta>]`: health check read-only del arnés (skills, scripts, estructura spec/). `--check-vendored [dir]` (v2.22, N5): compara por SHA-256 los scripts vendorados del proyecto (convención `scripts/`) contra la release instalada — drift, patch local o script ajeno a la release = exit 1. El gobernado no puede editar al gobernante; correr primero en CI.
- `decision_sizing.py --spec spec/ --output spec/risk-tier.yaml`: clasifica el Risk Tier (1/2/3) y fija el nivel de gobernanza.
- `advisor.py --adr <adr> --risk-tier N [--output <json>]`: identifica stakeholders del Advice Process por áreas de impacto.
- `arch_signoff.py --adr <adr> --architect "Nombre"`: firma arquitectónica; genera recibo ARCH-xxx.json con SHA-256 del ADR y artefactos de diseño.
- `authority_check.py <artefacto> --role <rol> | --author <usuario> --team spec/team-roster.yaml`: valida que quien emite/firma un artefacto sea su rol dueño según `spec/authority-matrix.yaml`. Exit 1 si no está autorizado.
- `code_intel.py --root <proyecto> index|symbol|context|impact|tests|search|map|stats`: inteligencia de código local (grafo de símbolos en SQLite, incremental, sin daemon). `context` evita leer archivos completos; `impact` calcula blast radius; `tests` lista tests candidatos para GATE 2.
- `code_graph.py emit|check|stats [--root <proyecto>] [--include-tests]` (v2.27): vistas derivadas del índice code_intel — grafo interactivo de archivos y grafo estático de módulos en `spec/diagrams/` (los recoge el portal en Arquitectura). Ejecutar tras cada reindex; `check` falla si las vistas quedan atrás del índice.
- `arch_lint.py [--root .] [--rules spec/architecture-rules.yaml]` (v2.21, N9): linter de invariantes arquitectónicos — si el proyecto declara arquitectura por capas, verifica que el código la respete (`ast` para Python, patrones para JS/TS). Exit 1 por violación o config inválida; registra el hecho en la memoria de auditoría. Sin reglas declaradas, exit 0 (condicional).
- `contract_diff.py --old f --new f | --contra-git <contrato>` (v2.21, N10): compatibilidad de contratos OpenAPI — detecta breaking changes (path/operación/parámetro eliminado, parámetro recién requerido, tipos cambiados, propiedades de respuesta eliminadas) y bloquea si la versión mayor (`info.version`) no subió. El gate `api-contract` lo aplica automáticamente contra HEAD cuando hay versión previa en git.
- `spec_index.py [--spec-dir spec/]`: regenera `spec/INDEX.md`, digest de una página con hash y resumen por artefacto.
- `manifest_check.py --write|--check|--summary` (v2.9): deriva el manifiesto del arnés (`assets/harness-manifest.yaml`) desde el frontmatter `harness-*` de cada SKILL.md y la lista de scripts en disco. `--check` falla si hay drift o inconsistencias cruzadas (gate declarado inexistente, artefacto `owns` fuera de la matriz de autoridad). El manifiesto es derivado — nunca se edita a mano; `harness_doctor.py` lee de él sus expectativas. `--routing [--sin-ui] [--sin-datos] [--sin-procesos]` (v2.10): imprime el routing por fases derivado del manifiesto, excluyendo las capacidades condicionales que no aplican a la iniciativa.
- `init_project.py --proyecto <nombre> [--capas] [--sin-ui|--sin-datos|--sin-procesos]` (v2.22, N4): scaffold determinista — todo proyecto arranca con la misma estructura `spec/`, matriz de autoridad, roster, tech radar y memoria de auditoría con génesis + evento `bootstrap`. Idempotente: nunca sobrescribe. `--capas` scaffolda además `architecture-rules.yaml` (activa arch_lint).
- `gate_verify.py --gate "GATE N" [--sin-ui|--sin-datos|--sin-procesos]` (v2.22, N4): verificación agregada — presencia + tipo (gate_checker) + recibo vigente con hash coincidente de todo lo exigible del gate, auditoría íntegra (audit_verify) y, en GATE 2, arch_lint en verde si hay reglas. Respeta los condicionales del routing. Exit 1 lista cada faltante.
- `pipeline_state.py [--check]` (v2.22, N7): deriva `spec/pipeline-state.md` desde matriz de autoridad + recibos + auditoría + `detect_stack.py`. El estado del pipeline se genera de hechos — nunca se edita a mano ni recibe recibo; `--check` (anti-drift, ignora la línea de timestamp) en CI.
- `circuit_breaker.py fail|ok|unfreeze|status` (v2.22, N11a): reintentos de gate con estado en `spec/run-state.yaml` — superado `--max` (default 1) el artefacto se CONGELA y solo un humano lo descongela (`unfreeze --approved-by`). Todo queda en la auditoría. `status` exit 1 con congelados (para CI/gates).
- `blast_radius_check.py --allowed <globs> | --cr <change-request>` (v2.22, N11b): el diff de git (incluidos archivos nuevos sin trackear) debe calzar con el alcance autorizado — escape = exit 1 + evento en la auditoría. Los artefactos de gobierno escritos por scripts (auditoría, run-state, pipeline-state, METRICS, portal) están exentos.

## Routing desde el manifiesto (v2.10)

Al iniciar una iniciativa, el routing ya no se interpreta solo de la prosa de esta skill: se deriva del manifiesto.

1. **Identificar condiciones de la iniciativa** (preguntar o inferir de la visión): ¿tiene UI? ¿maneja datos significativos? ¿automatiza/rediseña un proceso existente?
2. **Ejecutar** `manifest_check.py --routing` con los flags que correspondan (`--sin-ui`, `--sin-datos`, `--sin-procesos`). La salida es la lista de roles por fase que aplican — las capacidades condicionales que no aplican vienen marcadas como EXCLUIDAS y **no se activan** (ej. sin UI no hay prototipo `spec/ux/`; sin proceso que automatizar no hay PDD; sin datos significativos `sdlc-data-engineer` no participa).
3. **Elegir la ruta mínima** (routing orgánico §4a del README: directo / exploración / hotfix / discovery / full-pipeline) sobre ese conjunto activo. Los gates de entrega (2, 2.5, 3) aplican siempre.
4. Añadir una skill al arnés = crearla con su frontmatter `harness-*` y regenerar el manifiesto — aparece en el routing sin editar esta skill.

Los scripts de diagramas viven en `sdlc-diagrams/scripts/`: `pipeline_diagram.py`, `diagram_render.py` (solo Mermaid; la generación `.drawio` se retiró en v2.20) y `diagram_ir.py` (v2.17: diagramas vivos interactivos desde IR JSON — architecture/workflow/dataflow/lifecycle/sequence con foco, lens, detalle e insights; el IR `spec/diagrams/*.ir.json` es la fuente con recibo, el HTML es vista derivada con `check` anti-drift; ver ADR-003). La lectura del proyecto la resuelve el **portal único** (v2.20, `portal_lib.py`): `harness_graph.py --proyecto` emite `spec/portal/` — shell con menú lateral por categorías, búsqueda global (Ctrl+K), tema claro/oscuro y zoom compartidos con los diagramas — donde cada generador registra solo lo suyo en `registry.json` (`mdview.py` publica los `.md` en `paginas/docs/`, `harness_graph` las páginas de métricas y el inicio, `diagram_ir` auto-registra sus diagramas). `spec/dashboard.html` queda como redirect al portal conservando el `dashboard-state` del `--check`.

## Gates

- **GATE 0** (humano — aprobación de la iniciativa): propuesta de arquitectura con ≥2 opciones y recomendación justificada (`gate_checker.py spec/architecture-proposal.md --tipo architecture-proposal`), historias técnicas registradas (`--tipo technical-stories`) y estimación CAPEX/OPEX vigente (`--tipo cost-estimation`). Los tres artefactos emiten recibo GATE 0. Sin iniciativa aprobada, no hay pipeline de construcción.
- **GATE 1** (humano): spec consolidada aprobada + sin conflicts_with de memoria pendientes + `policy check` en verde (toda política org mandatory attestada compliant o con desviación aprobada vigente) + **para cada ADR Tier 1-2**: `gate_checker.py --tipo adr` en verde (8 pasos, scorecard, Advice Log, Tech Radar, firma `arch_signoff.py` vigente). Si la iniciativa tiene UI: inventario de pantallas `spec/ux/screen-inventory.md` con recibo vigente (`--tipo screen-inventory`) — sin prototipo aprobado, el Dev Front no implementa esas pantallas. Sin esto, cero código.
- **GATE 2**: todas las historias verificadas E2E. Si hay índice `code_intel`, los tests corridos deben cubrir lo reportado por `code_intel.py tests` para los símbolos tocados. Si el proyecto declara `spec/architecture-rules.yaml`, `arch_lint.py` debe estar en verde — el código que viola las capas aprobadas no pasa el gate. Si el contrato API cambió, `contract_diff.py --contra-git` debe pasar — breaking change exige bump de versión mayor declarado. Bug crítico → devuelve artefacto al dev con el test que lo reproduce (una corrección acotada; si falla, escala).
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
