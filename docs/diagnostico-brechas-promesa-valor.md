# Diagnóstico de brechas — promesa de valor del arnés (v2.20.1)

> Fecha: 2026-09-09 · Auditoría sobre el código del arnés (workspace `harness-sdlc`) y evidencia empírica del proyecto [TopBirdsColombia](https://github.com/csalamando/TopBirdsColombia) (operado con versiones 2.15.2 → 2.20.1).
>
> Promesa auditada: **determinismo, eficiencia, trazabilidad, auditoría y gobierno del SDLC; mínimo freestyle del agente / vibe coding humano.**
> Criterio de brecha: *toda promesa que hoy depende de prosa o de la memoria/disciplina del agente, sin un proceso/script/gate que la garantice siempre.*

---

## Resumen ejecutivo

El arnés tiene una base sólida (recibos SHA-256, manifiesto derivado, portal gobernado, close-check de memoria), pero la auditoría encontró **22 brechas**, de las cuales **7 son críticas** porque rompen directamente la promesa de valor:

| # | Brecha crítica | Promesa rota |
|---|---|---|
| B-01 | Los recibos revocados/invalidados se **sobrescriben**: no hay historial de auditoría | Auditoría |
| B-02 | La revocación downstream ante cambio de spec es **manual** (el script solo la "recomienda") | Determinismo / trazabilidad |
| B-03 | Los gates humanos (0/1/3) **no registran al humano**; el agente puede auto-aprobarse | Gobierno |
| B-04 | No existe **verificación agregada de gate** ni scaffold de proyecto: cada proyecto arranca distinto | Determinismo |
| B-05 | Los scripts del arnés se **vendoran y parchan dentro del proyecto gobernado** | Gobierno (el gobernado edita al gobernante) |
| B-06 | Los gates de diagramas quedaron **desconectados del mecanismo IR** (el gate aún exige Mermaid; la propuesta no exige diagramas) | Trazabilidad / propuesta de arquitectura |
| B-07 | El detector de freestyle **no bloquea**: el freestyle se "regulariza a posteriori" narrativamente | Anti-freestyle |

---

## A. Auditoría y recibos (RDD)

### B-01 · CRÍTICA — La revocación destruye la historia (el caso reportado)

**Evidencia (código):** `receipt.py::cmd_revoke` muta el mismo archivo (`estado: revocado`) y `cmd_emit` lo sobrescribe con `open(p, "w")` al re-aprobar. No existe log append-only de eventos de recibo. `skill_metrics.py` y `sprint_review.py` cuentan recibos **actualmente** en estado `invalidado/revocado` — tras re-emitir, el contador vuelve a cero.

**Evidencia (proyecto real):** `spec/CHANGELOG.md` de TopBirdsColombia documenta ≥ 4 cambios `supersedes` con "recibos re-emitidos" (Render→Railway, railway.toml→railway.ts, dataset v2→v3, thumbnails→imágenes originales), y sin embargo `sprint-review-18.md` reporta **"Trabajo rehecho: 0"**. El recibo del diagrama drawio retirado fue **borrado** ("queda en historial git"), ni siquiera revocado — ni siquiera Git es ya una fuente consultable por las métricas.

**Garantía propuesta:**
1. Event-sourcing de recibos: `spec/receipts/history.jsonl` **append-only** con un evento por `emit | invalidado | revocado`: `{ts, evento, artefacto, gate, rol, sha256_anterior, sha256_nuevo, reason, relation (supersedes|conflicts_with), change_ref}`.
2. `receipt.py revoke` exige `--reason` (y `--relation` cuando aplica); `emit` sobre un recibo no vigente registra el evento de re-emisión en lugar de sobrescribir en silencio (el archivo de estado sigue existiendo, pero el log es la fuente de verdad para métricas).
3. `sprint_review.py` y `harness_graph.py` cuentan **eventos del periodo**, no estados de archivo. Así la métrica "trabajo rehecho" es estructuralmente incapaz de quedarse en cero si hubo retrabajo.

### B-02 · CRÍTICA — La invalidación downstream depende de la memoria del agente

**Evidencia (código):** `spec_diff_impact.py` solo **imprime** "→ revocar recibo, re-validar gate…". Si el agente omite el `revoke`, nada lo detecta: el recibo de un artefacto downstream sigue "vigente" porque su propio hash no cambió (los recibos vinculan contenido del artefacto, **no el de sus dependencias**).

**Garantía propuesta:** recibos con **hash compuesto de dependencias** (precedente ya existente: `arch_signoff.py` firma un `composite_hash` sobre ADR + artefactos de diseño + `diagrams/*.ir.json`). `receipt.py verify` recalcula el hash del artefacto **y de su upstream** (según el grafo `DEPENDS_ON`, hoy quemado en `spec_diff_impact.py` — moverlo al manifiesto). Un cambio en `user-stories.md` invalida *derivadamente* los recibos de `test-plan.md`, `api-contract.yaml`, etc., sin intervención del agente. Además: `spec_diff_impact.py --apply` ejecuta la revocación (con evento en el log de B-01) en vez de recomendarla.

### B-03 · CRÍTICA — La aprobación humana es narración

**Evidencia:** GATE 0/1/3 se declaran "humanos", pero el recibo solo guarda el **rol del agente** que corrió el CLI. En TopBirdsColombia, la aprobación humana del GATE 1 vive como texto en `pipeline-state.md` ("aprobado por usuario el 2026-09-02…"). Peor: los sprints 5–13 tienen recibos con gate `SPRINT-N` emitidos **sin `--tipo`** (sin gate check) sobre documentos narrativos — el agente se auto-aprobó con recibo criptográfico.

**Garantía propuesta:**
1. `--approved-by <identidad>` obligatorio para gates marcados como humanos en el manifiesto; queda en el recibo y en el log.
2. `receipt.py emit` valida `--gate` contra el catálogo de gates del manifiesto (rechaza `SPRINT-5` inventado) y exige `--tipo` salvo excepciones explícitas.
3. Integración con la frontera dura ya especificada (`docs/gobernanza-github.md`): el recibo de un gate humano referencia el PR/review de GitHub que lo aprobó (`--pr <n>`), verificable vía API.

### B-04 — `receipt.py status` nunca falla

`cmd_status` imprime y retorna exit 0 siempre. El step de CI "Estado de recibos" (`ci-spec-governance.yml` del proyecto) es decorativo.

**Garantía:** `receipt.py status --strict` → exit 1 si hay recibos invalidados/revocados sin re-emitir, o artefactos de la matriz de autoridad sin recibo. El template de CI lo usa.

### B-05 — Ruta absoluta y colisión por basename en recibos

El recibo guarda `os.path.abspath(artefacto)` → filtra rutas locales (`D:\AI Projects\...`) a repos públicos y rompe la verificación al mover/clonar el proyecto. `receipt_path` usa solo `basename` → dos artefactos homónimos en directorios distintos comparten recibo.

**Garantía:** rutas relativas al root del proyecto en el recibo; nombre de archivo de recibo derivado de la ruta relativa normalizada.

---

## B. Diagramas post-drawio (v2.20)

### B-06 · CRÍTICA — Los gates no exigen los diagramas que la propuesta promete

Tres desconexiones concretas tras retirar drawio:

1. **`gate_checker.py --tipo architecture` sigue exigiendo el patrón `mermaid`.** La vía principal desde v2.20 es el IR (`diagram_ir.py`). Resultado: un `architecture.md` apoyado en diagramas IR **falla** el gate; uno con un boceto Mermaid y cero IR **pasa**. El gate premia la vía vieja y castiga la nueva.
2. **`--tipo architecture-proposal` (GATE 0) no verifica ningún diagrama.** La skill del Solution Architect promete "diagrama de contenedores por opción vía `sdlc-diagrams`" y su DoD dice "≥2 opciones, **diagramas** y comparativa", pero el gate pasa sin un solo diagrama. En TopBirdsColombia la propuesta aprobada no referencia ningún IR (los IR llegaron en fases posteriores).
3. **Nada exige que `spec/diagrams/` exista.** GATE 3 habla de diagramas derivados "con recibo vigente", pero si el agente nunca crea un diagrama, ningún check falla.

**Garantía propuesta:**
- Nuevo check semántico en `gate_checker`: para `architecture` y `architecture-proposal`, exigir ≥1 IR referenciado (`spec/diagrams/*.ir.json`, kind `flow`/architecture), con `diagram_ir.py validate` OK y **recibo vigente del IR** del rol dueño. El patrón `mermaid` se retira o se degrada a boceto opcional.
- GATE 3 agregado (ver B-08) incluye: IR de despliegue con recibo del cloud-engineer + `diagram_ir.py check` sin drift + `pipeline_diagram.py check` sin drift.

### B-07 — "Ubicación obligatoria" no se valida

La skill de diagramas declara "Obligatorio en diagramas de arquitectura: cada componente declara DÓNDE corre", pero `diagram_ir.py validate` no lo exige (solo lo renderiza).

**Garantía:** `diagram_ir.py validate` falla si un IR de arquitectura tiene nodos sin `ubicacion` (o flag `--require-ubicacion` que el gate invoca).

### B-08 — Documentación que promete lo retirado

`docs/guia-de-uso-arnes-sdlc.md` (línea ~339) aún afirma que la skill "genera todas las familias de diagramas como `.drawio` editables" — la fuente de la confusión sobre la obligatoriedad.

**Garantía:** actualizar la guía; añadir a `manifest_check.py --check` una regla de drift doc↔skill para claims estructurales (formatos soportados, gates, scripts).

---

## C. Bootstrap: el mínimo viable para iniciar un proyecto

### B-09 · CRÍTICA — No existe scaffold ni verificación agregada de gate

**Evidencia:** la Fase -1 es prosa en `sdlc-devops-engineer` ("inicializar repo con estructura…"). Ningún script crea la estructura ni instala `authority-matrix.yaml`, `team-roster.yaml`, `tech-radar.yaml`, `architectural-principles.yaml`. `harness_doctor.py` solo verifica 3 subdirectorios de `spec/`. Los gates son conjuntos de artefactos **definidos en prosa** — no existe `gate_checker --gate 1` que verifique presencia + tipo + recibo vigente de todo lo exigible.

**Evidencia (proyecto real):** TopBirdsColombia arrancó con `tests/` incompleto (solo `e2e/`; los tests unitarios viven en `src/backend/tests`, fuera de la estructura declarada) y con `detect_stack.py` en exit 2 ("sin test runner… Strict TDD en pausa") **y el proyecto continuó** — la pausa fue narrativa.

**Garantía propuesta:**
1. **`init_project.py`** (o `harness init`): crea la estructura mínima, copia las plantillas de gobierno desde `assets/`, genera el primer `pipeline-state.md` derivado, corre `detect_stack.py` y registra el evento `bootstrap` (versión del arnés) en el log. Salida: un proyecto que arranca **idéntico** siempre.
2. **`gate-requirements.yaml`** derivado del manifiesto: para cada gate, la lista de artefactos obligatorios (con las condicionales del routing v2.10: UI / datos / procesos). Nuevo comando `gate_verify.py --gate N` (o `gate_checker.py --gate N`): falla si falta cualquier artefacto, si algún gate de tipo no pasa, o si algún recibo no está vigente. Esto define **objetivamente** "lo mínimo" por gate — ya no se interpreta, se ejecuta. `--routing` alimenta las condicionales.
3. `harness_doctor.py --project-dir` endurecido: exige los artefactos de gobierno base (matriz, roster, radar, principios, pipeline-state, INDEX) con exit 1 — hoy son opcionales de facto.

### B-10 · CRÍTICA — Scripts vendorados y parchados dentro del proyecto gobernado

**Evidencia:** TopBirdsColombia copió los 30+ scripts del arnés a `scripts/` del proyecto — incluido `iac_to_diagram.py`, **retirado del arnés en v2.20** — y su `receipt.py` vendored contiene un *"Patch local"*. Su CI (`ci-spec-governance.yml`) ejecuta la copia vendored, no el arnés instalado. Consecuencias: (a) los fixes del arnés no llegan a los proyectos existentes; (b) un agente puede parchar el `gate_checker.py` local para que el gate pase — **el gobernado puede editar al gobernante**.

**Garantía propuesta:** los scripts se ejecutan desde la instalación de skills (ruta del agente), nunca copiados al repo. Si se vendoran por necesidad de CI, `harness_doctor --check-vendored` compara SHA-256 de cada script contra la release del arnés y falla ante drift o patch local. El CI del proyecto corre ese check primero.

---

## D. Métricas y detector de freestyle

### B-11 — Dos fórmulas contradictorias de "gates al primer intento"

`skill_metrics.py` calcula `artefactos/intentos` por skill (sensible a `--attempts`); `sprint_review.py` calcula `vigentes/total_recibos` (estructuralmente ~100 % salvo recibos *actualmente* inválidos). Evidencia: en TopBirds, `METRICS.md` muestra product-owner al 75 % (1 rechazo) y el sprint review global declara **100 %** en el mismo periodo.

**Garantía:** una sola definición — `recibos con attempts==1 / recibos del periodo` — calculada desde el log de eventos (B-01) y usada por ambos reportes.

### B-12 — Fase "?" y falsos positivos de "adorno"

`GATE_FASE` (en `receipt.py` y `skill_metrics.py`) no conoce los gates `FASE-*`/`SPRINT-*`; el auto-registro cae en fase `?`. Evidencia: el `METRICS.md` de TopBirds tiene una fila `?` que marca como "adorno" a **15 roles** — ruido que destruye la credibilidad del detector. Además la atribución recibo→fase usa "la primera fase donde el rol se activó" (arbitraria para roles multi-fase como security-engineer: 2, 4, 5).

**Garantía:** catálogo único de gates→fase en el manifiesto (una sola fuente); normalización de nombres (`GATE-1` ≡ `GATE 1`); el recibo registra la `fase` explícita en `emit`.

### B-13 · CRÍTICA — El freestyle se regulariza a posteriori, no se bloquea

**Evidencia literal** en `spec/CHANGELOG.md` de TopBirds: *"la implementación se adelantó al delta de spec (freestyle detectado); este changelog regulariza la trazabilidad a posteriori"*. El arnés lo detectó narrativamente y el propio agente escribió la regularización. Nada bloqueó el código sin spec.

**Garantía propuesta (por capas, de menor a mayor fricción):**
1. CI bloqueante ya existente pero no cableado: `tdd_order_check.py` en modo estricto (no `--warn`) como status check de PRs que tocan `src/`.
2. Regla "spec primero" en CI: un PR que toca `src/` debe tocar `spec/` o referenciar una HU con recibo vigente (`receipt.py verify spec/user-stories.md` + `traceability_matrix.py` sin brechas nuevas). El template `ci-spec-governance.yml` lo incluye comentado con criterios de exención (hotfix con label).
3. El evento de freestyle detectado se registra en `usage.jsonl` como evento `freestyle` (hoy solo hay `use`) para que la métrica lo cuente aunque se regularice.

### B-14 — `pipeline-state.md` es narración con recibo

En TopBirds la tabla está malformada (filas con pipes rotos: `|| reports/sprint-8…`, `|- **GATE 2.5…`) y los estados ("Recibo vigente") se escriben a mano. Un artefacto de **estado** mantenido por narración contradice el principio rector del arnés — y encima tiene recibo (se certifica la narración).

**Garantía:** `pipeline_state.py` que **deriva** el archivo desde recibos + manifiesto (mismo patrón que `METRICS.md` y el portal), con `--check` anti-drift en CI. El humano/agente no edita el estado; lo edita la evidencia.

---

## E. Consistencia entre versiones (proyectos migrados)

### B-15 — Convenciones cambiantes sin migración ni validación

TopBirds mezcla `sprint-5-review.md` (narrativo) con `sprint-review-15.md` (snapshot), y gates `GATE-1`/`GATE 1`/`FASE-2`/`SPRINT-10` en recibos. El portal tuvo que parchar el conteo de sprints a posteriori. Cada versión del arnés cambió convenciones sin un `migrate` ni un check de conformidad para proyectos existentes (el doctor solo *advierte* la diferencia de versión).

**Garantía:** `harness_migrate.py` (o `doctor --fix-conventions`): normaliza nombres de sprint reviews y de gates en recibos; `sprint_review.py` rechaza nombres fuera de patrón; el changelog del arnés declara por release las migraciones exigibles, y `harness_doctor` las lista como pendientes con exit 1.

---

## F. Lo que SÍ está garantizado hoy (no tocar)

Para no romper lo que ya cumple:

- Recibo vinculado a SHA-256 con auto-invalidación por cambio de contenido del propio artefacto.
- Autoridad por rol en emisión (`--role` contra `authority-matrix.yaml`) y frontera Git vía CODEOWNERS (documentada).
- `arch_signoff.py` firma hash compuesto incluyendo `diagrams/*.ir.json` (precedente a extender a todos los recibos, B-02).
- Auto-registro de activaciones en `usage.jsonl` al emitir recibo (v2.16) y `close-check` de memoria bloqueante en Fase 8.
- Manifiesto derivado del frontmatter con `--check` anti-drift, y portal regenerado con `--check` en CI.
- `tdd_order_check.py` (existe; falta hacerlo bloqueante).

---

## G. Plan de cierre propuesto (priorizado)

| Prioridad | Brechas | Esfuerzo | Release sugerida |
|---|---|---|---|
| P0 — Auditoría real | B-01 (log de eventos), B-03 (aprobador humano + gates válidos), B-04 (status --strict) | Medio | v2.21.0 (MINOR: formato de log nuevo, retrocompatible) |
| P0 — Gobierno del gobernante | B-10 (drift de scripts vendorados), B-09.2 (gate_verify agregado) | Medio | v2.21.0 |
| P1 — Determinismo | B-02 (hash compuesto de dependencias + `--apply`), B-14 (pipeline-state derivado) | Alto | v2.22.0 |
| P1 — Diagramas | B-06 (gates IR), B-07 (ubicacion), B-08 (docs) | Bajo | v2.21.0 |
| P2 — Métricas | B-11, B-12, B-13 (evento freestyle + tdd_order bloqueante) | Bajo | v2.21.0 |
| P2 — Migraciones | B-05, B-15 | Medio | v2.22.0 |

**Definición de hecho sugerida para esta iniciativa:** cada brecha P0/P1 cerrada con (a) script con exit codes, (b) check en `tests/self_test.py`, (c) template de CI actualizado, (d) entrada en la guía — y demostrada sobre TopBirdsColombia migrado (donde la métrica de retrabajo debe dejar de ser 0 retroactivamente al reconstruir el log desde el historial Git).
