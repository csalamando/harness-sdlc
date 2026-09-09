# Núcleo recomendado — control real con cero dependencias externas

> Fecha: 2026-09-09 · Filtra el [diagnóstico de brechas](diagnostico-brechas-promesa-valor.md) y las 6 ideas de mejora externas.
> Criterios de corte aplicados: **(1)** da control verificable (no prosa), **(2)** garantiza la oferta de valor (determinismo, trazabilidad, auditoría, gobierno, anti-freestyle), **(3)** stdlib + Git únicamente — nada que instalar, degradación elegante cuando una capacidad opcional falta.

---

## 1. La decisión estructural: DOS memorias con modelos de consistencia distintos

La revisión confirma que hoy el arnés mezcla dos cosas de naturaleza opuesta:

| | **Memoria de trabajo** (ya existe: `sdlc-memory`) | **Memoria de auditoría** (NO existe — es la brecha B-01) |
|---|---|---|
| Qué guarda | Conocimiento evolutivo: decisiones, aprendizajes, handoffs, políticas | Hechos: recibos emitidos/invalidados/revocados, gates pasados/fallados, activaciones, cambios de spec, freestyle, escapes de blast radius, bootstrap |
| Consistencia | **Mutable**: se supersedea, se contradice, se resuelve | **Append-only**: un hecho nunca se edita; una corrección es un evento compensatorio nuevo (como en contabilidad) |
| Pregunta que responde | "¿Dónde me quedé y qué sé?" | "¿Qué pasó exactamente, cuándo, quién aprobó y por qué?" |
| Fuente para | `mem.py context`, handoffs, close-check | METRICS.md, sprint reviews, portal, verificación de gates |
| Estado actual | ✅ Implementada y gobernada (sessions, handoff, close-check, políticas) | ❌ Inexistente: los recibos se sobrescriben, `usage.jsonl` es el único log y solo cubre activaciones; la métrica de retrabajo está condenada a cero |

**Recomendación: sí, separar formalmente.** La memoria de trabajo sigue igual. La memoria de auditoría nace como `spec/audit/events.jsonl` con estas reglas:

1. **Append-only con cadena de hash** (`prev_hash` por evento, stdlib `hashlib`): tamper-evident incluso antes de que Git lo versione; cualquier reescritura del pasado rompe la cadena y es detectable con `audit_verify.py`.
2. **Todo evento registra versión del arnés y fecha con formato estricto**: `ts` en **UTC ISO-8601 con zona** (`2026-09-09T15:38:00+00:00` — nunca hora local naive) y `harness_version` leída del frontmatter del orquestador (mismo mecanismo que `receipt.py`, que hoy lo hace solo desde v2.12.1 y con fechas locales — se corrige de paso). Sin estos dos campos el evento es inválido y `audit_verify.py` falla: *un hecho sin cuándo ni bajo qué versión de las reglas ocurrió, no es auditable*.
3. **El ciclo de vida del arnés también es evento**: `audit_init` (evento génesis del log: proyecto, fecha, versión del arnés), `harness_upgrade` (versión anterior → nueva, fecha — cada cambio de versión que gobierna los hechos queda registrado; la historia multi-versión de TopBirds 2.15.2→2.20.1 habría quedado explícita) y `bootstrap` (N4) abren la traza.
4. **Absorbe `usage.jsonl`** (activaciones pasan a ser eventos `tipo: use`) y los eventos de recibo (`emit | invalidado | revocado` con `reason`, `relation`, `approved_by`, hashes anterior/nuevo).
5. **Los archivos `.receipt.json` quedan como estado derivado** (vista del último evento por artefacto); la verdad histórica es el log. `sprint_review.py`, `skill_metrics.py` y el portal leen **eventos del periodo**, no estados de archivo — la métrica de retrabajo se vuelve estructuralmente incapaz de mentir.
6. **Migración**: `harness_migrate.py` reconstruye el log histórico de proyectos existentes desde Git (los recibos re-emitidos de TopBirds son recuperables del historial) — el retrabajo pasado deja de ser invisible. Los eventos reconstruidos llevan `source: git-history`, `ts` = fecha del commit y `harness_version` = la registrada en el recibo histórico (o `pre-2.12.1` si no hay), distinguiendo evidencia reconstruida de evidencia vivida.
7. `close-check` (Fase 8) exige el log no vacío en la ventana del sprint, igual que hoy exige `usage.jsonl`.

Esta pieza es la que **ordena todo lo demás**: cada capacidad siguiente nace escribiendo sus hechos en el log.

---

## 2. El núcleo recomendado (único que se implementa)

### Del diagnóstico original — sobreviven 8 de 22 brechas como trabajo real

| # | Capacidad | Control que da | Filosofía |
|---|---|---|---|
| N1 | **Memoria de auditoría** (§1) | Auditoría real: nada se borra, todo hecho tiene razón y aprobador | stdlib + Git |
| N2 | **Recibos con hash compuesto de dependencias** + `spec_diff_impact.py --apply`: un cambio de spec invalida *derivadamente* los recibos downstream (el grafo `DEPENDS_ON` se mueve al manifiesto; precedente: `composite_hash` de `arch_signoff.py`) | Determinismo: la revocación deja de depender de la memoria del agente | stdlib |
| N3 | **Aprobador humano registrado** (`--approved-by` obligatorio en gates humanos, `--pr` opcional vinculante) + `--gate` validado contra catálogo del manifiesto + `--tipo` obligatorio salvo excepciones + `receipt.py status --strict` (exit 1) en CI | Gobierno: el agente ya no puede auto-aprobarse con recibo criptográfico; CI falla ante recibos inválidos | stdlib |
| N4 | **`init_project.py` + `gate_verify.py --gate N`**: scaffold idéntico de todo proyecto (estructura, matriz de autoridad, roster, radar, reglas de arquitectura, pipeline-state derivado, evento bootstrap) y verificación agregada de gate (presencia + tipo + recibo vigente de todo lo exigible, con condicionales del routing) | Determinismo de arranque: "lo mínimo" deja de interpretarse y se ejecuta | stdlib |
| N5 | **`harness_doctor --check-vendored`**: SHA-256 de cada script copiado al proyecto contra la release del arnés; drift o patch local = fallo de CI | El gobernado ya no puede editar al gobernante | stdlib |
| N6 | **Gates de diagramas migrados a IR**: `gate_checker` exige IR referenciado con recibo vigente (ya no patrón `mermaid`); `architecture-proposal` exige diagrama por opción; `diagram_ir.py validate` exige `ubicacion` en arquitectura; guía de uso actualizada | Los diagramas vuelven a ser parte fundamental y *exigible* de la propuesta | stdlib |
| N7 | **`pipeline_state.py` derivado**: el estado del pipeline se genera desde recibos + manifiesto (como METRICS.md), con `--check` anti-drift | Fin del estado narrado (y de certificar narración con recibo) | stdlib |
| N8 | **Consistencia de métricas y convenciones**: fórmula única de "gates al primer intento" (attempts==1/total, desde el log), catálogo único gate→fase en el manifiesto (adiós fila "?"), normalización de nombres de sprint review, `harness_migrate.py` | Métricas que no se contradicen entre reportes | stdlib |

### De las 6 ideas externas — sobreviven 3

| # | Capacidad | Forma adoptada | Por qué sí |
|---|---|---|---|
| N9 | **Linter de invariantes arquitectónicos** (idea 4) | `arch_lint.py`: `ast` para Python + patrones para otros lenguajes (mismo enfoque que `code_intel`); reglas en `spec/architecture-rules.yaml` (owner `software-architect`, con recibo; scaffolded por N4); condicional a arquitectura por capas declarada; falla GATE 2 y CI | Convierte la arquitectura de prosa en política binaria — control directo, barato, cero dependencias |
| N10 | **Compatibilidad de contratos** (idea 5) | `contract_diff.py`: compara `api-contract.yaml` viejo/nuevo (PyYAML si está, degradación con mensaje claro si no — mismo patrón que `check_tech_radar`); breaking change no declarado como versión mayor = gate bloqueado + revocación downstream vía N2 | Blindar la interfaz pública es SDD puro; cierra el agujero de "cambio rupturista que nadie declaró" |
| N11 | **HITL por excepción portable** (idea 6, la mitad enforceable) | (a) Circuit breaker con estado (`spec/run-state.yaml`: reintentos, congelamiento, traza) — formaliza lo que hoy es prosa; (b) `blast_radius_check.py` en gate/CI: `git diff --name-only` ⊆ lista autorizada del change-request; escape = fallo de gate + evento en el log | El confinamiento *en tiempo de edición* no es portable entre las 9+ plataformas del arnés; el confinamiento *verificado sobre el diff* sí lo es y bloquea igual |

---

## 3. Lo descartado y por qué (explícito, para no reabrir)

| Idea | Veredicto | Razón |
|---|---|---|
| **Mutation testing** (idea 3) | ❌ Fuera del core | Requiere mutmut/Stryker: rompe la filosofía cero-dependencias. **Sustituto stdlib parcial**: gate de calidad de tests en `gate_checker`/`code_intel` — tests sin aserciones, tests que no invocan el símbolo de su HU, cobertura del runner detectado por `detect_stack`. Mutation testing queda documentado como integración opcional del proyecto, nunca exigible por el arnés |
| **AST Skeletonizer con tree-sitter** (idea 1) | ❌ Como subsistema; ✅ como mejora menor | tree-sitter es dependencia externa; y el 80 % ya existe: `code_intel.py context` da esqueleto de archivo (firmas) y `impact` el blast radius. Se reduce a `code_intel.py pack --cambio <símbolo>` (stdlib, prioridad baja): es eficiencia, no control — no entra al núcleo |
| **Proposal Diff interactivo en tiempo de edición** (idea 6, otra mitad) | ⚠️ Prosa, no garantía | Interceptar ediciones no es portable; queda como comportamiento del orquestador donde la plataforma lo soporte. La garantía real es N11(b) sobre el diff |
| **Git Worktrees transaccionales** (idea 2, completa) | ❌ Fuera del core | Su garantía central ("toda edición corre dentro del sandbox") no es enforceable en las 9+ plataformas del arnés — sería cumplimiento por prosa, justo lo que estamos erradicando. El valor real (repo limpio tras loops fallidos, rollback ordenado) ya lo cubren ramas + branch protection + el circuit breaker con `run-state` (N11a). Y su costo ataca el núcleo: rutas de sandbox en recibos, log de auditoría e índice de `code_intel`. Complejidad alta en el centro por comodidad periférica |
| **Squash atómico** (parte de idea 2) | ❌ | Destruye la evidencia `test(HU)`→`feat(HU)` que `tdd_order_check.py` verifica en `git log` |
| Brechas B-05/B-13.3/E menores del diagnóstico | Absorbidas | Rutas relativas en recibos y evento `freestyle` quedan cubiertas por N1/N3; no son línea aparte |

---

## 4. Secuencia de implementación

**v2.21 — "La auditoría es un hecho, no una promesa"**
N1 (memoria de auditoría + cadena de hash + migración desde Git) → N3 (aprobador humano, gates válidos, status --strict) → N8 (métricas consistentes sobre el log) → N6 (gates de diagramas IR) → N9 (arch_lint) → N10 (contract_diff).
*Todo stdlib; cada capacidad escribe en el log desde su primer commit.*

**v2.22 — "El arranque y el cambio son deterministas"**
N4 (init + gate_verify) → N2 (hash compuesto de dependencias + --apply) → N5 (check-vendored) → N7 (pipeline-state derivado) → N11 (circuit breaker + blast_radius_check).

**Definición de hecho transversal** (sin excepciones): cada capacidad entrega (a) script con exit codes, (b) checks nuevos en `tests/self_test.py`, (c) template de CI actualizado, (d) eventos en el log de auditoría, (e) guía actualizada — y se demuestra sobre TopBirdsColombia migrado, donde la métrica de retrabajo debe dejar de ser 0 con datos reales reconstruidos.
