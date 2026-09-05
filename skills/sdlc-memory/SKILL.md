---
name: sdlc-memory
description: "Sistema de memoria persistente Git-nativa para el arnés SDLC con scopes project/user/org y gobierno de políticas. Usar para guardar y recuperar decisiones, aprendizajes, bugs y contexto entre sesiones y agentes: memorias estructuradas What/Why/Where/Learned en markdown versionado, búsqueda federada FTS5 por scopes, conflictos (supersedes/conflicts_with), sesiones con resumen, trazabilidad a HU/EP/ADR, promoción de patrones cross-proyecto, políticas org mandatory con attestation y flujo de desviaciones con aprobación humana que bloquean GATE 1, servidor MCP stdio y CLI. Dispara ante: memoria persistente, recordar decisiones, mem_save, políticas de organización, desviaciones de lineamientos, contexto entre sesiones."
harness-role: memory
harness-phases: "transversal"
---

# Sistema de Memoria del Arnés SDLC

Memoria persistente, Git-nativa y agent-agnostic para el pipeline SDLC. Complementa la spec: la spec guarda *qué* se decidió construir; la memoria guarda *por qué* se decidió, qué se aprendió y qué no debe repetirse — entre sesiones, agentes e IDEs.

## Principios de diseño

1. **Git-nativo**: cada memoria es un markdown con frontmatter en `spec/memory/entries/` — fuente de verdad, versionada y con code review junto a la spec. El índice SQLite+FTS5 (`.index/`) es derivado: se borra y se reconstruye con `reindex`. Agregar `.index/` al `.gitignore`.
2. **Estructura contractual**: What / Why / Where / Key details / Learned. Sin `Why` no se guarda.
3. **Relaciones tipadas**: `supersedes` (reemplaza), `conflicts_with` (contradice, requiere humano), detectadas por similitud FTS al guardar y resueltas explícitamente.
4. **Trazabilidad nativa**: el campo `links` conecta la memoria con HU-xxx, EP-x, ADR-xxx, BR-xxx.
5. **Dos transportes**: CLI directo (`mem.py`, cualquier agente con terminal) y MCP stdio (`mem_mcp.py`, agentes compatibles con MCP). Misma lógica, mismo storage.
6. **Scopes con precedencia** (v1.2): `project` (`./spec/memory`, versionada en Git), `user` (`~/.sdlcmem/user`, personal cross-proyecto), `org` (`~/.sdlcmem/org`, patrones y políticas de la organización). Búsqueda federada en los tres; lo específico vence a lo general.
7. **Gobierno de políticas** (v1.2): tipo `policy` en scope org con `enforcement: mandatory|recommended`. Toda policy mandatory debe estar attestada `compliant` o tener desviación **aprobada y vigente** antes del GATE 1 (`policy check`). Las desviaciones siguen flujo `request → approve|reject` con aprobador humano designado y fecha de expiración. El scope org rechaza contenido con patrones de secretos.
8. **Identidad estable por tema** (v1.3): `save --topic_key "catalogos/fk-chips"` da al tema una clave estable; al guardar de nuevo con la misma clave, la memoria vigente anterior queda **auto-supersedida** — los temas evolutivos se actualizan en vez de acumular duplicados competidores.
9. **Cierre verificable** (v1.3): `close-check` es el gate de la Fase 8 — falla (exit 1) si el ciclo cierra sin memoria `learning`, sin handoff de sesión, con sesiones abiertas o con `usage.jsonl` vacío en la ventana del sprint. La disciplina deja de ser texto: se verifica.
10. **Handoff estructurado** (v1.3): `session end --goal --done --next --files` deja un handoff recuperable (tras compactación o cambio de agente); el dashboard del proyecto muestra las últimas sesiones ("qué se está trabajando").

## Cuándo guardar memoria (y cuándo no)

Guardar: decisiones no triviales y su motivación, bugs cuya causa raíz costó encontrar, aprendizajes sobre el stack/dominio, incidentes, contexto que la próxima sesión necesitará.
NO guardar: nada que ya esté en la spec (la memoria enlaza a la spec, no la duplica), secretos/credenciales, ruido transitorio.

## Protocolo en el pipeline

- **session start**: el orquestador abre sesión al iniciar trabajo en el proyecto; antes, corre `mem.py context` (digest de arranque: sesión activa, último handoff, memorias vigentes, conflictos y políticas — pocos tokens) y hace `mem_search` de las fases/artefactos que va a tocar.
- **Durante cada fase**: el rol guarda decisiones y aprendizajes relevantes con `links` a sus artefactos. Para temas evolutivos, usar `--topic_key` estable y re-guardar sobre la misma clave en vez de crear memorias competidoras.
- **Al guardar**: si aparecen candidatos a conflicto, resolverlos antes de seguir (`conflicts list` → `conflicts resolve`). Un `conflicts_with` sin resolver **bloquea el GATE 1** igual que una contradicción en la spec.
- **session end**: handoff estructurado obligatorio: `--goal --done --next --files` — es la primera lectura de la próxima sesión y alimenta la vista de sesiones del dashboard.
- **Cierre de ciclo (Fase 8)**: `close-check` debe salir en verde **antes** de archivar el sprint; si falta evidencia (learning, handoff, métricas), el ciclo no se archiva.
- **Cambio de spec**: si un artefacto cambia, verificar memorias con `links` afectados y marcarlas superseded si el cambio las invalida.
- **Antes de GATE 1**: correr `policy check`. Debe salir todo `COMPLIANT` o `WAIVED`; un `VIOLATION` bloquea el gate igual que una contradicción en la spec.

## Scopes y compartición

| Scope | Ubicación | Compartida por | Contenido |
|---|---|---|---|
| project | `./spec/memory` (Git del repo) | Equipo del proyecto | Decisiones y contexto del producto |
| user | `~/.sdlcmem/user` | El dev, en todos sus proyectos | Aprendizajes y preferencias personales |
| org | `~/.sdlcmem/org` (repo Git aparte o servidor) | Toda la organización | Patrones promovidos + **políticas** |

- Guardar con `--scope user|org` (default `project`). Buscar sin `--scope` consulta los tres y etiqueta origen.
- **Promoción**: `promote MEM-xxx --to org` copia la memoria con `derived_from` — el original queda intacto.
- Compartir la capa org entre usuarios: hacer de `~/.sdlcmem/org` un clone de un repo Git corporativo (push/pull periódico; tras pull, `reindex`). Overrides: `SDLCMEM_USER_ROOT`, `SDLCMEM_ORG_ROOT`.

## Gobierno de políticas

```
# La org publica lineamientos (solo en scope org)
python3 scripts/mem.py save --scope org --type policy --title "APIs públicas exigen OAuth2+PKCE" \
    --what "..." --why "estándar corporativo" --enforcement mandatory

# En el proyecto, antes de GATE 1:
python3 scripts/mem.py policy list
python3 scripts/mem.py policy check        # VIOLATION bloquea (exit 1)
python3 scripts/mem.py policy attest POL-... --status compliant --by architect

# Si el proyecto necesita excepción — flujo con aprobación:
python3 scripts/mem.py deviation request --policy POL-... --title "API batch m2m" \
    --justification "..." --risk "..." --mitigation "mTLS + allowlist" --expires 2026-12-31
python3 scripts/mem.py deviation list      # pending NO exime
python3 scripts/mem.py deviation approve DEV-... --approver "Architecture Board" --note "..."
python3 scripts/mem.py policy check        # ahora WAIVED hasta la expiración
```

Reglas: solo humanos designados aprueban (`--approver` obligatorio); la desviación tiene expiración y al vencer vuelve a bloquear; una desviación rechazada obliga a cumplir la policy; `rejected`/`approved` es irreversible (nueva solicitud si cambian las condiciones).

## CLI (mem.py)

```
python3 scripts/mem.py session start --project mi-app
python3 scripts/mem.py save --type decision --title "JWT con refresh rotation" \
    --what "Access tokens de 15min + refresh rotativo" \
    --why "SEC-001 exige expiración corta; rotación mitiga robo de refresh" \
    --links HU-003,SEC-001,ADR-004 --tags auth,seguridad
python3 scripts/mem.py search "refresh token" [--any] [--type decision]
python3 scripts/mem.py get MEM-20260808-001
python3 scripts/mem.py timeline MEM-20260808-001
python3 scripts/mem.py conflicts list
python3 scripts/mem.py conflicts resolve MEM-...-002 MEM-...-001 --relation supersedes --note "la nueva reemplaza"
python3 scripts/mem.py session end --summary "Fase 2 cerrada; auth definida con JWT rotativo" \
    --goal "cerrar Fase 2" --done "auth JWT rotativo definida" --next "Fase 4: implementar" --files "spec/architecture.md"
python3 scripts/mem.py context        # digest de arranque (sesión, handoff, memorias vigentes, conflictos)
python3 scripts/mem.py close-check    # gate de cierre de ciclo (exit 1 si falta evidencia)
python3 scripts/mem.py reindex      # reconstruye el índice desde markdown (tras pull/clone)
python3 scripts/mem.py doctor       # salud del sistema
python3 scripts/mem.py export       # dump JSON completo
```

Raíz: `./spec/memory` por defecto; override con `--root <ruta>` o variable `SDLCMEM_ROOT`.

## MCP (mem_mcp.py)

Servidor stdio JSON-RPC, stdlib pura. Registro típico en el agente:

```json
{ "mcpServers": { "sdlc-memory": {
    "command": "python3",
    "args": ["<ruta>/sdlc-memory/scripts/mem_mcp.py"],
    "env": { "SDLCMEM_ROOT": "<proyecto>/spec/memory" } } } }
```

Herramientas expuestas: `mem_save`, `mem_search`, `mem_get`, `mem_timeline`, `mem_conflicts_list`, `mem_conflicts_resolve`, `mem_session_start`, `mem_session_end`, `mem_doctor`.

## Archivos de apoyo

- `assets/memory-entry.md`: plantilla de entrada (la que usa mem.py).
- `assets/gitignore-snippet`: qué ignorar en Git (`.index/`).
- `references/schema.md`: modelo de datos completo (frontmatter, relaciones, sesiones, tablas del índice) y criterios de tipado de memorias.
