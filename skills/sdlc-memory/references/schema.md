# Esquema del sistema de memoria

## Entrada (markdown, fuente de verdad)

Frontmatter: id (MEM-YYYYMMDD-NNN, secuencial por día), type, project, created, session,
tags[], links[], supersedes[]. Cuerpo: título H1 + secciones What/Why/Where/Key details/Learned.

## Tipos y criterio de uso

| type | Cuándo |
|---|---|
| decision | Elección entre alternativas con motivación (complementa el ADR: el ADR es formal, la memoria es el porqué conversacional) |
| bug | Causa raíz costosa de encontrar; enlazar el test que lo reproduce |
| learning | Conocimiento sobre stack, dominio o tooling que ahorra tiempo futuro |
| architecture | Hitos arquitectónicos que no ameritan ADR completo |
| incident | Evento en operación (complementa postmortem del SRE) |
| context | Estado del proyecto necesario para la próxima sesión |

## Relaciones

| relation | Significado | Quién la crea |
|---|---|---|
| supersedes | src reemplaza a dst; dst queda histórica | Declarada al guardar o al resolver |
| conflicts_with | src contradice a dst; requiere resolución humana | Solo al resolver (bloquea GATE 1 sin resolver) |
| candidate | Par detectado por similitud FTS, pendiente de juicio | Automática al guardar |

Flujo: save → candidatos FTS → `conflicts list` → `conflicts resolve` (supersedes / conflicts_with / unrelated).

## Sesiones

sessions/: una sesión abierta por vez; `session end` genera `sessions/SES-*.md` con conteo de memorias y resumen.
La primera acción de una sesión nueva: leer el resumen de la anterior + `mem_search` del tema a trabajar.

## Índice SQLite (.index/mem.db — derivado, gitignored)

- entries(id, title, type, project, created, session, file, tags, links)
- fts (FTS5: id, title, body)
- relations(src, dst, relation, status, note)
- sessions(id, project, started, ended, summary)

Tras `git pull` o clone: `mem.py reindex` reconstruye todo desde markdown.

## Scopes (v1.2)

project (./spec/memory, Git) | user (~/.sdlcmem/user) | org (~/.sdlcmem/org, repo Git corporativo o servidor).
Overrides: SDLCMEM_ROOT, SDLCMEM_USER_ROOT, SDLCMEM_ORG_ROOT. Precedencia: project > user > org.
Cada scope tiene su propia estructura entries/ + .index/ + sessions/.

## Politicas y desviaciones (v1.2)

- type=policy solo en scope org. Frontmatter extra: enforcement (mandatory|recommended), applies_to.
- Attestations por proyecto: spec/memory/policy-attestations.json {POL-id: {status, note, by, date}}.
- Desviaciones: spec/memory/deviations/DEV-*.md con status pending|approved|rejected, approver, expires.
  pending no exime; approved exime hasta expires; rejected obliga a cumplir. Decision irreversible.
- policy check: mandatory sin attestation compliant y sin desviacion aprobada vigente => VIOLATION, exit 1 (bloquea GATE 1).
- Filtro de secretos: save/promote a scope org rechaza contenido con patrones de credenciales.
