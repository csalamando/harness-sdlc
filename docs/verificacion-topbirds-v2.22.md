# Verificación de TopBirdsColombia contra el arnés v2.22.0

Fecha: 2026-09-09 · Arnés: v2.22.0 (tag `v2.22.0`) · Proyecto: clone local de `csalamando/TopBirdsColombia` (analizado en `.analysis/TopBirdsColombia`, sin modificar el original).

Método: se ejecutaron los verificadores ejecutables del núcleo de control sobre la `spec/` del proyecto — `gate_verify.py` para los cinco gates, más inspección de auditoría, diagramas, métricas y skills vendored. El proyecto fue construido con versiones anteriores del arnés, así que los hallazgos son exactamente las brechas que v2.21/v2.22 vinieron a cerrar.

## Resultado por gate (gate_verify.py)

| Gate | Verificados | Incumplidos | Detalle |
|---|---|---|---|
| GATE 0 | 2 | 2 | `architecture-proposal.md` tiene Opción C sin diagrama IR referenciado; sin memoria de auditoría |
| GATE 1 | 13 | 3 | `process-definition.md` no existe; `architecture.md` no referencia ningún `diagrams/*.ir.json`; sin memoria de auditoría |
| GATE 2 | 0 | 2 | `qa-report.md` no contiene sección de bugs (patrón `[Bb]ugs`); sin memoria de auditoría |
| GATE 2.5 | 2 | 1 | Solo falta la memoria de auditoría |
| GATE 3 | 1 | 1 | Solo falta la memoria de auditoría |

## Hallazgos estructurales (no dependen de un gate)

1. **Sin memoria de auditoría** — no existe `spec/audit/events.jsonl`. Es el faltante transversal: aparece en los 5 gates. Sin ella no hay traza de quién aprobó qué, ni registro de revocaciones, ni hash-chain verificable con `audit_verify.py`.
2. **Métrica de recibos revocados sin fuente** — `spec/METRICS.md` no contiene ninguna mención a recibos revocados y `spec/metrics/usage.jsonl` solo registra eventos `use` de skills. Si hubo revocaciones (las hubo: decisiones que cambiaron definiciones ya implementadas), no quedaron registradas en ningún sitio. La métrica siempre estará en cero porque **no existe el proceso que la alimenta** — exactamente la brecha que motivó ADR-004 / N4.
3. **Diagramas IR huérfanos** — existen 4 diagramas IR bien formados (`contenedores`, `despliegue`, `flujo-datos`, `secuencia-ronda`) en `spec/diagrams/`, pero ni `architecture.md` ni `architecture-proposal.md` los referencian (0 menciones de `ir.json` en ambos). El trabajo se hizo pero no está atado al artefacto que lo exige: confirma que al quitar drawio la obligatoriedad se perdió en la práctica — ahora `gate_checker` la hace cumplir.
4. **`process-definition.md` ausente** — el routing del proyecto debió declarar `--sin-procesos` o producir el artefacto; quedó en tierra de nadie.
5. **`qa-report.md` sin sección de bugs** — el gate exige reportar bugs encontrados (aunque sea "0 bugs"); el reporte actual no cumple el formato mínimo.
6. **Sin skills vendored** — el proyecto no incluye copia del arnés (`skills/`), así que nada garantiza qué versión de las reglas se aplicó en cada recibo. Con `check-vendored` + vendoring, la versión del gobernante queda fijada y protegida.
7. **Sin `architecture-rules.yaml`** — `arch_lint` no puede ejecutarse: no hay invariantes de arquitectura declarados que verificar.

## Lo que sí está bien

- 51 recibos en `spec/receipts/`, y los artefactos centrales (visión, backlog, historias, contrato API, threat model, test plan, SLO, costos) pasan presencia + tipo + recibo vigente con hash coincidente.
- `usage.jsonl` registra el uso de skills desde 2026-09-01: hay materia prima de telemetría.
- Estructura de `spec/` completa y reconocible: el proyecto está a pocos pasos de cumplir.

## Plan de remediación (en orden, todo ejecutable)

```bash
# 1. Inicializar memoria de auditoría (registra versión del arnés + fecha bootstrap)
python skills/sdlc-orchestrator/scripts/init_project.py --proyecto TopBirdsColombia --dir <repo> --capas
#    (idempotente: no sobrescribe nada existente; completa process-definition si aplica)

# 2. Atar los diagramas IR existentes a la arquitectura
#    - referenciar diagrams/contenedores.ir.json (y los otros 3) en architecture.md
#    - referenciar el diagrama de la Opción C en architecture-proposal.md
#    - re-emitir recibos de ambos (audit_log.py registra la revocación del anterior)

# 3. Completar qa-report.md con la sección de bugs y re-emitir su recibo

# 4. Declarar invariantes y vendorar el arnés
#    - crear spec/architecture-rules.yaml (scaffold ya generado por --capas)
#    - copiar skills/ del arnés v2.22.0 al repo → check-vendored los protege

# 5. Verificar
python skills/sdlc-orchestrator/scripts/gate_verify.py --gate "GATE 1" --root <repo>
python skills/sdlc-memory/scripts/audit_verify.py --spec-dir <repo>/spec
```

Después de los pasos 1–4, los cinco gates deberían quedar en verde y la métrica de revocaciones pasará a alimentarse sola: cada re-emisión de recibo en los pasos 2–3 quedará registrada como revocación en la memoria de auditoría.
