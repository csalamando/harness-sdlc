# ADR-004: Dos memorias — memoria de trabajo y memoria de auditoría (`audit_log.py`)

**Estado:** ACEPTADA (v2.21) · **Fecha:** 2026-09-09 · **Risk Tier:** 1

## 1. Problem Statement

La promesa de auditoría del arnés no está garantizada por un proceso. La auditoría de v2.20.1
([diagnóstico](../diagnostico-brechas-promesa-valor.md), brecha B-01) encontró:

1. **Los recibos revocados/invalidados se sobrescriben**: `receipt.py revoke` muta el archivo del
   recibo y `emit` lo sobrescribe al re-aprobar. La métrica "trabajo rehecho" de `sprint_review.py`
   cuenta recibos *actualmente* inválidos — tras re-emitir vuelve a cero. Evidencia: TopBirdsColombia
   documenta ≥4 supersedes con "recibos re-emitidos" y su sprint review 18 reporta **0**.
2. **El único log append-only (`usage.jsonl`) cubre solo activaciones**; los hechos de gobierno
   (emisiones, invalidaciones, revocaciones con su razón) no quedan registrados en ninguna parte.
3. **Fechas y versiones inconsistentes**: `receipt.py` guarda hora local sin zona; `arch_signoff.py`
   UTC con zona; `harness_version` solo existe desde v2.12.1. Un hecho sin cuándo ni bajo qué versión
   de las reglas ocurrió no es auditable.
4. La **memoria de trabajo** (`sdlc-memory`: decisiones, aprendizajes, handoffs) es *evolutiva* por
   diseño (se supersedea y se resuelve) — no puede servir como traza de hechos.

## 2. Decisión

**Separar formalmente dos memorias con modelos de consistencia opuestos:**

| | Memoria de trabajo (`sdlc-memory`, existente) | **Memoria de auditoría (nueva)** |
|---|---|---|
| Guarda | Conocimiento evolutivo (decisiones, learnings, handoffs, políticas) | Hechos de gobierno (emit/invalidado/revocado/use/bootstrap/harness_upgrade) |
| Consistencia | Mutable: supersedes/conflicts_with | **Append-only**: un hecho nunca se edita; corrección = evento compensatorio |
| Responde | "¿dónde me quedé y qué sé?" | "¿qué pasó, cuándo, quién aprobó y por qué?" |
| Alimenta | `mem.py context`, handoffs, close-check | METRICS.md, sprint reviews, portal, verificación de gates |

Implementación: `spec/audit/events.jsonl` (JSONL append-only) con estas reglas:

1. **Cadena de hash** (`prev_hash` por evento, stdlib `hashlib`; génesis = `"0"*64`): tamper-evident
   antes de Git; reescribir el pasado rompe la cadena y `audit_verify.py` falla.
2. **`ts` UTC ISO-8601 con zona** y **`harness_version`** obligatorios en todo evento; sin ellos el
   evento es inválido y la verificación falla.
3. **El ciclo de vida del arnés es evento**: `audit_init` (génesis), `harness_upgrade`
   (versión anterior → nueva, fecha), `bootstrap` (futuro, N4 del plan).
4. **Absorbe `usage.jsonl`**: las activaciones se registran también como eventos `use`;
   `usage.jsonl` se mantiene en esta versión por compatibilidad y se retira cuando las métricas
   lean del log (plan N8).
5. **Los `.receipt.json` quedan como estado derivado** (último evento por artefacto); la verdad
   histórica es el log.
6. **Migración honesta** (futuro, `harness_migrate.py`): eventos reconstruidos desde Git con
   `source: git-history`, `ts` = fecha del commit, `harness_version` del recibo histórico
   (o `pre-2.12.1`) — evidencia reconstruida se distingue de evidencia vivida.

### Scripts

```bash
python audit_log.py init --proyecto <nombre>     # evento génesis (falla si el log ya existe)
python audit_log.py append --evento <tipo> [--artefacto ... --gate ... --rol ...
                           --reason ... --relation ... --approved-by ... --nota ...]
python audit_verify.py                            # cadena + campos obligatorios; exit 1 si falla
```

`receipt.py emit|verify(invalida)|revoke` escriben el evento correspondiente automáticamente.
`revoke` ahora **exige `--reason`**: una revocación sin causa declarada no es auditoría, es ruido.

## 3. Opciones consideradas

1. **Historial dentro del propio recibo** (lista de estados por archivo) — INSUFICIENTE: `emit`
   seguiría sobrescribiendo; no hay orden global de eventos ni cadena de hash.
2. **Confiar en Git como única traza** — INSUFICIENTE: las métricas no consultan `git log` (costoso
   y frágil); el recibo borrado de TopBirds ("queda en historial git") demuestra que nadie lo hace.
3. **Meter la traza en `sdlc-memory`** — DESCARTADA: su modelo es evolutivo (supersedes); mezclar
   hechos inmutables con conocimiento mutable rompe ambos.
4. **Base de datos (SQLite como code_intel)** — DESCARTADA para la traza: JSONL es diff-able en PR,
   legible y apendable sin transacciones; la cadena de hash da la integridad que SQLite no muestra en diff.

## 4. Consecuencias

- **Breaking menor**: `receipt.py revoke` sin `--reason` ahora falla (exit 1).
- Todo consumidor de métricas migra después (N8) de estados de archivo a eventos del periodo —
  esta versión solo **añade** la traza; nada existente se retira excepto el revoke sin razón.
- Los eventos guardan el artefacto con **ruta relativa al proyecto y separadores `/`** (lección
  v2.20.1: rutas Windows rompían el portal en Linux) — portátil y sin filtrar rutas locales.
- Si `audit_log.py` no está junto a `receipt.py` (vendoring incompleto), la emisión lo advierte en
  consola — el drift de scripts vendorados se hace visible hasta que N5 lo vuelva bloqueante.
- **Self-test**: sección dedicada (génesis, encadenamiento, tamper-evidence, revoke sin razón,
  eventos de emit/invalidación).

## 5. Criterios de éxito

1. En un proyecto operado con v2.21+, `audit_verify.py` pasa en CI y la métrica de retrabajo
   (cuando N8 la mueva al log) refleja todas las re-emisiones — nunca vuelve a cero tras re-aprobar.
2. Toda revocación tiene razón declarada; todo gate humano puede registrar `approved_by`.
3. Reescribir o reordenar cualquier evento pasado rompe `audit_verify.py` en <1s, stdlib puro.
4. La historia multi-versión del arnés en un proyecto queda explícita como eventos `harness_upgrade`.
