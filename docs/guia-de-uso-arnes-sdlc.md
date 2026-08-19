# Guía de Uso — Arnés SDLC (SDD + TDD)

Esta guía explica cómo instalar y usar las 21 skills del arnés SDLC en cualquier agente compatible con el estándar abierto **Agent Skills** (Kimi, Claude Code, Google Antigravity, OpenAI Codex, Cursor, GitHub Copilot, entre otros).

---

## 1. Qué contiene el paquete

| Skill | Rol | Fase |
|---|---|---|
| `sdlc-orchestrator` | Orquestador del pipeline + 12 herramientas CLI | Todas |
| `sdlc-product-owner` | Visión y backlog priorizado | 0 |
| `sdlc-solution-architect` | Arquitecto de la iniciativa: apoya a PO/BA con historias, historias técnicas, propuesta de arquitectura con opciones (GATE 0) | 0-2 |
| `sdlc-cloud-pricing` | Estimación CAPEX/OPEX/TCO por escenario en AWS y Azure — caso de negocio (GATE 0) y estimación fina | 0, 6 |
| `sdlc-business-analyst` | Historias de usuario + Gherkin + reglas de negocio | 1 |
| `sdlc-ux-designer` | Flujos UX + design system + tokens.json | 2 |
| `sdlc-software-architect` | Arquitectura + OpenAPI + ADRs + test-plan | 2-3 |
| `sdlc-security-engineer` | Threat modeling + SAST/DAST (GATE 2.5) | 2, 4, 5 |
| `sdlc-data-engineer` | Migraciones + gobierno de datos (condicional) | 2 |
| `sdlc-backend-dev-tdd` | Backend con TDD estricto | 4 |
| `sdlc-frontend-dev-tdd` | Frontend con TDD + mocks desde OpenAPI | 4 |
| `sdlc-qa-automation` | E2E desde Gherkin + regresión + carga (GATE 2) | 5 |
| `sdlc-devops-engineer` | Setup + CI/CD + IaC + rollback | -1, 6 |
| `sdlc-cloud-engineer` | Infraestructura cloud + observabilidad | 6 |
| `sdlc-sre` | SLOs + incidentes + postmortems | 7 |
| `sdlc-product-analyst` | Medición de impacto → realimenta backlog | 7 |
| `sdlc-technical-writer` | Documentación + publicación doc-as-code (Wiki/Pages/Confluence) | 4-6 |
| `sdlc-memory` | Memoria persistente entre sesiones (transversal) | Todas |
| `sdlc-diagrams` | Diagramas C4, cloud, secuencia, BPMN, Gantt, GitFlow vía drawio MCP | 1, 2, 6 |
| `sdlc-decision-engine` | Motor de decisiones: 8 pasos de Natanzon, scorecard, Decision Packages | 2 |
| `sdlc-enterprise-architect` | Tech Radar, Principios Arquitectónicos, excepciones, Paved Roads | 2 (Tier 1) |

Cada archivo `.skill` es un ZIP con la estructura estándar:

```
sdlc-<rol>/
├── SKILL.md        # Instrucciones del rol (obligatorio)
├── assets/         # Plantillas de artefactos (vision.md, api-contract.yaml, etc.)
├── references/     # Documentación de apoyo (solo orquestador)
└── scripts/        # Herramientas CLI (solo orquestador, requieren Python 3)
```

---

## 2. Instalación según agente / IDE

Un archivo `.skill` es un ZIP: para instalarlo manualmente, **descomprímelo y copia la carpeta** (la que contiene `SKILL.md`) al directorio de skills de tu agente.

### Kimi (este asistente)

1. En una conversación, adjunta los archivos `.skill` que quieras instalar y pide: *"Instala estas skills"*.
2. Se instalan en tu espacio personal de skills y quedan disponibles en todas tus conversaciones futuras.
3. Alternativa manual (entornos con acceso al filesystem): copiar cada carpeta a `/app/.user/skills/<nombre>/`.

### Claude Code

| Nivel | Ruta | Alcance |
|---|---|---|
| Personal | `~/.claude/skills/<skill-name>/` | Todos tus proyectos |
| Proyecto | `.claude/skills/<skill-name>/` | Solo ese repo (recomendado: versionar con el equipo) |

```bash
# Ejemplo: instalar todo el arnés a nivel de proyecto
cd mi-proyecto
for f in ~/descargas/*.skill; do
  unzip -q "$f" -d .claude/skills/
done
```

- Invocación explícita: `/sdlc-orchestrator`, `/sdlc-business-analyst`, etc.
- Invocación implícita: basta con pedir *"ejecuta la fase de discovery del pipeline SDLC"* y Claude activa la skill cuya descripción coincide.
- Claude Code detecta cambios en skills en caliente, sin reiniciar.

### Google Antigravity (AGY / AGY IDE / AGY CLI)

| Nivel | Ruta |
|---|---|
| Workspace (funciona en las 3 variantes) | `<workspace-root>/.agents/skills/<skill-name>/` |
| Global (única ruta reconocida por las 3 variantes) | `~/.gemini/config/skills/<skill-name>/` |

```bash
for f in ~/descargas/*.skill; do
  unzip -q "$f" -d .agents/skills/
done
```

> Nota: la documentación oficial menciona otras rutas globales (`~/.gemini/antigravity/skills/`, `~/.gemini/skills/`), pero solo `~/.gemini/config/skills/` es reconocida por AGY, AGY CLI y AGY IDE simultáneamente. Evita las demás.

### OpenAI Codex CLI

| Nivel | Ruta |
|---|---|
| Global | `~/.codex/skills/<skill-name>/` |
| Proyecto | `.agents/skills/<skill-name>/` |

```bash
for f in ~/descargas/*.skill; do
  unzip -q "$f" -d ~/.codex/skills/
done
```

- Tras instalar, **reinicia Codex** para que reindexe las skills.
- Invocación explícita: `$sdlc-orchestrator` dentro de la sesión.
- También puedes usar el instalador integrado: `$skill-installer`.

### Cursor

| Nivel | Ruta |
|---|---|
| Global | `~/.cursor/skills/<skill-name>/` |
| Proyecto | `.cursor/skills/<skill-name>/` |

### GitHub Copilot

| Nivel | Ruta |
|---|---|
| Global | `~/.github/skills/<skill-name>/` |
| Proyecto | `.github/skills/<skill-name>/` |

### Visual Studio Code (GitHub Copilot en el editor)

VS Code soporta Agent Skills de forma nativa en el chat y en agent mode (es el mismo estándar abierto, así que las 21 skills del arnés funcionan sin cambios).

| Nivel | Rutas reconocidas |
|---|---|
| Proyecto (versionable con el equipo) | `.github/skills/`, `.claude/skills/`, `.agents/skills/` |
| Personal | `~/.copilot/skills/`, `~/.claude/skills/`, `~/.agents/skills/` |

```bash
# Instalación a nivel proyecto
cd mi-proyecto
for f in ~/descargas/*.skill; do
  unzip -q "$f" -d .github/skills/
done
```

Formas de uso dentro de VS Code:

- **Automática**: Copilot lee `name` + `description` de cada SKILL.md y activa la skill relevante para tu petición (p. ej. pides "genera las historias de usuario del sprint" y activa `sdlc-business-analyst`).
- **Explícita**: escribe `/sdlc-orchestrator` (o el rol que necesites) en el input del chat, como slash command.
- **Gestión visual**: teclea `/skills` o abre **Configure Chat → pestaña Skills** para ver, crear, habilitar o deshabilitar skills.
- **Rutas adicionales**: si quieres mantener las skills en otra carpeta (p. ej. `sdlc-harness/skills/`), agrégala en el setting `chat.agentSkillsLocations`. En monorepos, activa `chat.useCustomizationsInParentRepositories`.
- **Contexto aislado (experimental)**: para skills pesadas como el orquestador, puedes añadir `context: fork` al frontmatter y VS Code la ejecutará en un subagente dedicado, devolviendo solo el resultado final a tu conversación (requiere el setting `github.copilot.chat.skillTool.enabled`). Muy útil para no ensuciar el contexto principal durante una fase larga del pipeline.

Notas específicas del arnés en VS Code:
- Los scripts del orquestador corren con el terminal tool de Copilot; revisa el auto-approve/allow-list de comandos para permitir `python3 <skill-dir>/scripts/*.py`.
- Como las skills viven en `.github/skills/` dentro del repo, todo el equipo comparte la misma versión del arnés vía Git.

### Open WebUI

Open WebUI soporta el estándar de skills como **carpetas en el filesystem** (sin UI compleja): el servidor escanea un directorio de skills, extrae el metadata de cada `SKILL.md`, los registra en su base de datos y los expone a los modelos.

#### Instalación (Docker, la vía más común)

```bash
# 1. Descomprimir el arnés en una carpeta del host
mkdir -p ~/openwebui-data/skills
for f in ~/descargas/*.skill; do
  unzip -q "$f" -d ~/openwebui-data/skills/
done

# 2. Montar la carpeta en el contenedor y reiniciar
docker run -d \
  -v ~/openwebui-data/skills:/app/backend/data/skills \
  -v open-webui:/app/backend/data \
  -p 3000:8080 \
  --name open-webui \
  ghcr.io/open-webui/open-webui:main
docker restart open-webui
```

Tras el reinicio, Open WebUI descubre las 21 skills automáticamente. Flujo: **instalar → montar → reiniciar**.

#### Uso

- Menciona una skill en el chat con `$` (p. ej. `$sdlc-orchestrator ejecuta el pipeline para...`) — también aparecen con `/`.
- En **Workspace → Skills** (o el panel de administración correspondiente) puedes ver las skills descubiertas y habilitarlas/deshabilitarlas por modelo.
- Si el modelo tiene habilitada la ejecución de código, los scripts del orquestador (`gate_checker.py`, etc.) pueden correr en ese entorno; si no, el agente seguirá las instrucciones del SKILL.md pero sin gates automáticos.

#### Requisitos y alternativas

- El soporte de skills es reciente: verifica que tu versión de Open WebUI lo incluya. Si estás en una versión anterior, actualiza la imagen.
- **Fallback sin soporte nativo**: si tu despliegue no soporta skills aún, puedes (a) crear un *Model* personalizado en Workspace → Models cuyo System Prompt sea el contenido del SKILL.md del orquestador, y adjuntar las plantillas de `assets/` como Knowledge, o (b) subir los artefactos a una colección de Knowledge y referenciarlos con `#`. Es menos elegante (sin carga progresiva ni scripts), pero el pipeline se puede seguir manualmente.

### Instalador multiplataforma (skills.sh)

Si trabajas con varios agentes a la vez, el gestor de paquetes `skills` detecta los agentes instalados y coloca cada skill en la ruta correcta:

```bash
# Publica el arnés en un repo Git y luego:
npx skills add <tu-usuario>/sdlc-harness --all
# o solo para agentes específicos:
npx skills add <tu-usuario>/sdlc-harness -a claude-code -a codex
```

### Recomendación de nivel

- **Nivel proyecto** (`.claude/skills/`, `.agents/skills/`, etc.): recomendado para el arnés completo — se versiona en Git junto al código y todo el equipo (humano o agente) usa la misma versión.
- **Nivel global/personal**: útil si usas el arnés en muchos proyectos distintos.

---

## 3. Cómo usar el arnés (para el usuario)

### Flujo recomendado: el orquestador manda

No invoques roles sueltos salvo que sepas lo que haces. El punto de entrada es siempre el orquestador:

```
"Usando la skill sdlc-orchestrator, ejecuta el pipeline SDLC completo
para esta idea: <describe tu producto>. Modo: full-pipeline."
```

El agente con la skill del orquestador:

1. Crea `spec/pipeline-state.md` y activa la Fase -1 (setup) y Fase 0 (PO + Solution Architect: propuesta de arquitectura, historias técnicas y estimación CAPEX/OPEX).
2. Se detiene en **GATE 0** (aprobación humana de la iniciativa): revisas la propuesta con opciones y el caso de negocio con costos antes de comprometer construcción.
3. Antes de activar cada rol, corre `context_packager.py` para darle solo el contexto mínimo.
4. Al recibir cada artefacto, corre `gate_checker.py` — si falla, el artefacto se devuelve al rol.
5. Se detiene en **GATE 1** (aprobación humana de la spec consolidada): aquí tú revisas `spec/` antes de que se escriba código.
6. Continúa con build (TDD), QA, seguridad y despliegue, deteniéndose en los gates 2, 2.5 y 3.

### Modos de operación

| Situación | Prompt sugerido |
|---|---|
| Producto nuevo | *"Ejecuta el pipeline SDLC en modo full-pipeline para…"* |
| Bug en producción | *"Modo hotfix: QA reproduce el bug con un test, el dev lo corrige con TDD y se despliega. Bug: …"* |
| Cambio de alcance | *"Modo change-request: el usuario quiere cambiar <historia>. Actualiza la spec y re-ejecuta solo lo impactado usando spec_diff_impact.py."* |

### Invocar un rol individual (uso avanzado)

```
"Actúa con la skill sdlc-business-analyst: lee spec/vision.md y spec/backlog.md
y genera las historias de usuario con Gherkin del sprint 1."
```

### Requisitos de las herramientas CLI del orquestador

Los scripts (`gate_checker.py`, `receipt.py`, `decision_sizing.py`, `advisor.py`, `arch_signoff.py`, etc.) solo necesitan **Python 3** (sin dependencias externas). El agente los ejecuta directamente; en entornos sandbox asegúrate de que el agente tenga permiso de ejecutar Python.

---

## 4. Sistema de memoria (`sdlc-memory`)

La spec guarda *qué* se decidió construir; la memoria guarda *por qué*, qué se aprendió y qué no debe repetirse — entre sesiones, agentes e IDEs. Es transversal a las skills de roles.

### Diseño

- **Git-nativo**: cada memoria es un markdown con frontmatter en `spec/memory/entries/` (fuente de verdad, versionada con la spec). El índice SQLite+FTS5 en `.index/` es derivado: agrégalo a `.gitignore` y reconstrúyelo con `reindex` tras cada clone/pull.
- **Estructura contractual**: What / Why / Where / Key details / Learned. Sin `Why` no se guarda.
- **Conflictos tipados**: al guardar, FTS detecta memorias similares como candidatas; se resuelven como `supersedes` (reemplaza), `conflicts_with` (contradice — bloquea GATE 1 sin resolver) o `unrelated`.
- **Trazabilidad**: el campo `links` conecta cada memoria con HU-xxx, EP-x, ADR-xxx, BR-xxx, SEC-xxx.
- **Sesiones**: `session start` abre trabajo; `session end --summary` deja el resumen que lee la próxima sesión.

### Scopes: memoria compartida por capas (v1.2)

La memoria existe en tres alcances con precedencia (lo específico vence a lo general):

| Scope | Ubicación | Compartida por | Contenido |
|---|---|---|---|
| `project` | `./spec/memory` (Git del repo) | Equipo del proyecto | Decisiones y contexto del producto |
| `user` | `~/.sdlcmem/user` | El dev en todos sus proyectos | Aprendizajes y preferencias personales |
| `org` | `~/.sdlcmem/org` | Toda la organización | Patrones promovidos + políticas |

- Guardar con `--scope user|org` (default `project`); buscar sin `--scope` consulta los tres y etiqueta el origen.
- **Promoción**: `mem.py promote MEM-xxx --to org` convierte una memoria de proyecto en patrón organizacional, registrando `derived_from` sin borrar el original.
- **Compartir org entre usuarios**: hacer de `~/.sdlcmem/org` un clone de un repo Git corporativo; tras push/pull, `reindex`. Overrides: `SDLCMEM_USER_ROOT` / `SDLCMEM_ORG_ROOT`.
- El scope org rechaza automáticamente contenido con patrones de secretos/credenciales.

### Gobierno de políticas (v1.2)

Las prácticas y lineamientos de la organización son memorias de tipo `policy` en scope org, con `enforcement: mandatory|recommended`:

```bash
# La org publica lineamientos (solo en scope org)
python3 scripts/mem.py save --scope org --type policy --title "APIs públicas exigen OAuth2+PKCE" \
    --what "..." --why "estándar corporativo" --enforcement mandatory

# En cada proyecto, ANTES del GATE 1:
python3 scripts/mem.py policy check      # VIOLATION => exit 1, bloquea el gate
python3 scripts/mem.py policy attest POL-xxx --status compliant --by architect

# Si el proyecto necesita excepción: revisión y aprobación humana
python3 scripts/mem.py deviation request --policy POL-xxx --title "API batch m2m" \
    --justification "..." --risk "..." --mitigation "mTLS + allowlist" --expires 2026-12-31
python3 scripts/mem.py deviation approve DEV-xxx --approver "Architecture Board" --note "..."
python3 scripts/mem.py policy check      # ahora WAIVED hasta la expiración
```

Reglas del flujo: una solicitud `pending` **no exime**; solo aprueba un humano designado (`--approver` obligatorio); la aprobación tiene **expiración** — al vencer, el check vuelve a bloquear; una desviación rechazada obliga a cumplir la política; la decisión es irreversible (condiciones nuevas = solicitud nueva). El GATE 1 del orquestador exige `policy check` en verde: toda política mandatory attestada `compliant` o con desviación aprobada vigente.

### Vía CLI (cualquier agente con terminal)

```bash
python3 scripts/mem.py session start --project mi-app
python3 scripts/mem.py save --type decision --title "JWT con refresh rotation" \
    --what "Access 15min + refresh rotativo" --why "SEC-001 exige expiración corta" \
    --links HU-003,SEC-001 --tags auth
python3 scripts/mem.py search "refresh token" --any
python3 scripts/mem.py conflicts list
python3 scripts/mem.py conflicts resolve MEM-...-002 MEM-...-001 --relation supersedes
python3 scripts/mem.py session end --summary "Fase 2 cerrada"
python3 scripts/mem.py reindex   # tras git pull/clone
python3 scripts/mem.py doctor    # salud del sistema
```

Raíz por defecto: `./spec/memory` (override: `--root` o variable `SDLCMEM_ROOT`). Sin dependencias externas: Python 3 stdlib.

### Vía MCP (Claude Code, VS Code, Cursor, Antigravity, Codex)

El servidor stdio `mem_mcp.py` expone 16 herramientas (`mem_save`, `mem_search`, `mem_get`, `mem_timeline`, `mem_conflicts_list`, `mem_conflicts_resolve`, `mem_session_start`, `mem_session_end`, `mem_doctor`, `mem_promote`, `mem_policy_list`, `mem_policy_check`, `mem_policy_attest`, `mem_deviation_request`, `mem_deviation_decide`, `mem_deviation_list`). Registro típico:

```json
{ "mcpServers": { "sdlc-memory": {
    "command": "python3",
    "args": ["<ruta>/sdlc-memory/scripts/mem_mcp.py"],
    "env": { "SDLCMEM_ROOT": "<proyecto>/spec/memory" } } } }
```

- **Claude Code**: agrégalo en `.mcp.json` del proyecto (queda versionado para el equipo).
- **VS Code**: `mcp.json` en el workspace o vía Command Palette → "MCP: Add Server".
- **Cursor**: Settings → MCP → New MCP Server.
- **Codex**: bloque `[mcp_servers.sdlc-memory]` en `~/.codex/config.toml`.
- **Antigravity**: `mcp_config.json` en `~/.gemini/antigravity/`.

### Reglas del pipeline

1. El orquestador abre sesión al iniciar y busca memoria relevante antes de activar cada fase.
2. Cada rol guarda decisiones/aprendizajes con `links` a sus artefactos al cerrar su fase.
3. Un `conflicts_with` sin resolver bloquea el GATE 1, igual que una contradicción en la spec.
4. Si un artefacto cambia (change-request), las memorias con `links` afectados se marcan superseded.

---

## 4b. Diagramas (`sdlc-diagrams`)

Genera todas las familias de diagramas del arnés como `.drawio` editables versionados en `spec/diagrams/`: C4, arquitectura/despliegue cloud con iconos oficiales AWS/Azure/GCP, secuencia UML, BPMN 2.0, Gantt, GitFlow y flujos de proceso. Una sola skill con una referencia por familia (carga bajo demanda). Sirve al Architect (Fase 2), Cloud Engineer (Fase 6), BA (BPMN, Fase 1), DevOps (GitFlow, Fase -1) y PO (Gantt/roadmap).

**Decisión clave por familia**: XML nativo para C4, cloud y BPMN (control fino, iconos exactos vía `search_shapes`); importación Mermaid (`open_drawio_mermaid`) para secuencia, Gantt y GitFlow (sintaxis declarativa, el importador hace el layout).

### Requisito: MCP oficial de draw.io

```json
// .vscode/mcp.json / .cursor/mcp.json / Claude Code: claude mcp add drawio -- npx -y @drawio/mcp
{ "servers": { "drawio": { "command": "npx", "args": ["-y", "@drawio/mcp"] } } }
```

- **Tool server** (`npx @drawio/mcp`, stdio): `open_drawio_xml`, `search_shapes` (~10.000 shapes: AWS, Azure, GCP, K8s...), `open_drawio_mermaid`, y edición de páginas (`list_pages`/`get_page`/`set_page`). Abre el editor en el navegador. Recomendada para IDEs.
- **App server** (`https://mcp.draw.io/mcp`, remoto): `create_diagram` con preview inline en chat (Claude.ai, Cursor con MCP Apps).
- Sin MCP disponible: la skill genera igualmente el `.drawio` en disco (editable en app.diagrams.net) — el MCP es el visor, no una dependencia del entregable.

### Flujo

1. Elegir nivel C4; un `.drawio` multipágina, una página por nivel.
2. **Resolver iconos con `search_shapes` antes de escribir XML** — nunca inventar rutas; la skill incluye style strings listos para C4 y los servicios más usados de AWS (`mxgraph.aws4.*`), Azure (`img/lib/azure2/**.svg`) y GCP.
3. Construir XML con convenciones C4 (colores oficiales, boundary como contenedor, edges con protocolo, leyenda).
4. `open_drawio_xml` para previsualizar/editar; persistir en `spec/diagrams/` con trazabilidad a HU/EP en el nombre de página.
5. La skill trae `assets/c4-contenedores-ejemplo.drawio` (Azure: APIM + Functions + SQL + Key Vault) como plantilla de partida.

Los diagramas de despliegue reflejan el IaC: si `infra/` cambia, el orquestador marca el diagrama como impactado vía `spec_diff_impact`.

---

## 5. Novedades v1.1 (patrones RDD)

La versión 1.1 incorpora patrones de Receipt-Driven Development, adaptados al arnés:

- **Recibos con hash (`receipt.py`)**: al pasar un gate se emite un recibo con el SHA-256 del artefacto en `spec/receipts/`. Las fases downstream verifican el recibo antes de consumir: si el contenido cambió un byte desde la aprobación, el recibo se invalida solo y el gate se re-ejecuta. *Confiar en evidencia derivable, no en la narración del agente.* Comandos: `emit`, `verify`, `status`, `revoke`.
- **Routing orgánico**: el orquestador elige la ruta mínima antes de empezar — cambio mecánico de 1-3 archivos va directo a TDD; exploración amplia va a una sub-tarea acotada; el pipeline completo solo arranca con ambigüedad sustancial y aprobación del usuario.
- **Relaciones en cambios de spec**: `spec_diff_impact.py --relation supersedes|conflicts_with` — un `conflicts_with` bloquea el GATE 1 hasta resolución humana.
- **Fase 8 — Archivo**: al cerrar el sprint, merge de delta-specs en la spec maestra, memorias superseded, trazabilidad y recibos en verde, sesión cerrada. La próxima iteración arranca desde spec consolidada.
- **`harness_doctor.py`**: health check read-only del arnés instalado (skills, scripts compilables, estructura spec/, .gitignore).
- **`detect_stack.py`** (Fase -1): detecta stack y test runner; sin runner (exit 2) los gates de cobertura no son exigibles y Strict TDD queda en pausa hasta configurarlo.
- **Perfiles de modelo por fase** (`references/model-profiles.md` del orquestador): tier económico/intermedio/potente por rol, con ejemplo de `model_list` para LiteLLM.

---

## 5b. Novedades v2.0 (gobernanza de decisiones)

Basada en el framework de 8 pasos de Sonya Natanzon, el Advice Process y el Tech Radar de ThoughtWorks/Fowler:

- **Risk Tiering (`decision_sizing.py`)**: en Fase 2 clasifica la decisión en Tier 1 (crítico: PII, pagos, auth), Tier 2 (estándar) o Tier 3 (ligero), y fija el nivel de gobernanza. Tier 3 → ADR simplificado; Tier 1-2 → proceso completo.
- **`sdlc-decision-engine`**: guía los 8 pasos por decisión significativa — Problem Statement sin soluciones prematuras, Last Responsible Moment, criterios ponderados (pesos = 100%), opciones, Advice Process, scorecard cuantitativa, decisión con consecuencias aceptadas y re-evaluation triggers. Scripts: `decision_engine.py --validate|--load-package` y `scorecard_calculator.py`.
- **Advice Process (`advisor.py`)**: identifica stakeholders por áreas de impacto del ADR (datos → Data Engineer, seguridad → Security Engineer, etc.; Tier 1 siempre incluye al Enterprise Architect). El consejo **no es vinculante**, pero omitir la consulta bloquea GATE 1; todo consejo queda en el Advice Log del ADR.
- **Firma arquitectónica (`arch_signoff.py`)**: el Arquitecto de Software (único Decision Owner técnico) firma el ADR generando `spec/receipts/ARCH-xxx.json` con SHA-256 del ADR y los artefactos de diseño. Si el ADR cambia tras la firma, el gate lo detecta como recibo invalidado. Un ADR firmado no se modifica: se supersedea.
- **`sdlc-enterprise-architect`**: guardián del **Tech Radar** (ADOPT/TRIAL/ASSESS/HOLD) y los **Principios Arquitectónicos**. Gobierna por excepción: solo interviene en Tier 1, violación de principio mandatory o tecnología en HOLD. **Paved Roads**: tecnología ADOPT = aprobación pre-autorizada; HOLD bloquea el gate salvo ADR de excepción aprobado por el Architecture Board.
- **Decision Packages** (`sdlc-decision-engine/assets/decision-packages/`): criterios, paved roads y constraints pre-aprobados para decisiones recurrentes (ej. `pkg-auth`, `pkg-database-selection`), inyectables en el ADR con `--load-package`.
- **`gate_checker.py --tipo adr`**: valida las 8 secciones, ausencia de soluciones prematuras, pesos = 100%, Advice Log registrado (Tier 1-2), cruce con Tech Radar y firma vigente — todo en un solo gate.

---

## 5c. Novedades v2.1 (arquitectura de la iniciativa + pricing cloud)

El arquitecto ya no aparece solo en Fase 2: participa desde la concepción de la iniciativa, donde las decisiones de costo y forma determinan si el negocio aprueba construir.

- **`sdlc-solution-architect` (Fases 0-2)**: el "arquitecto de la iniciativa". Acompaña a negocio/PO/BA a detallar historias (detecta NFRs implícitos y dependencias técnicas), escribe directamente **historias técnicas** (`spec/technical-stories.md`: enablers, deuda, spikes con timebox, NFRs medibles — cada una con origen, aceptación verificable y costo de omisión) y elabora la **propuesta de arquitectura** (`spec/architecture-proposal.md`): ≥2 opciones con diagramas (vía `sdlc-diagrams`), ADRs preliminares de dirección, comparativa cuantitativa y recomendación con scorecard. Frontera clara con `sdlc-software-architect`: el Solution Architect decide **si y con qué forma se construye**; el Software Architect diseña el detalle de la opción aprobada y firma los ADRs.
- **`sdlc-cloud-pricing` (Fases 0 y 6)**: estimación **CAPEX** (ingeniería + one-time) y **OPEX** mensual en 3 escenarios (mínimo viable / crecimiento esperado / pico) para **AWS y Azure**, con TCO a 3 años, supuestos versionados en YAML y fecha de validez de precios. `scripts/cost_estimator.py` genera `spec/cost-estimation.md` desde `spec/cost-assumptions.yaml`; los precios unitarios de referencia pueden sobreescribirse tras verificar las calculadoras oficiales. En Fase 6 el Cloud Engineer la reutiliza para la estimación fina (desviación > 20% → change-request).
- **GATE 0 (aprobación de la iniciativa)**: nuevo gate humano previo a GATE 1. Exige propuesta con opciones + recomendación, historias técnicas y estimación de costos vigente — los tres con recibo SHA-256. Tipos nuevos del gate: `gate_checker.py <artefacto> --tipo architecture-proposal|technical-stories|cost-estimation`. Sin GATE 0 no hay pipeline de construcción; el costo entra como criterio ponderado obligatorio en la scorecard de la propuesta.
- **Routing "discovery"**: iniciativa nueva o evolución de producto → ruta PO + BA + Solution Architect + Cloud Pricing → GATE 0, antes de cualquier full-pipeline.

---

## 5d. Novedades v2.2 (autoridad por rol)

¿Cómo garantizar que un dev no "apruebe" decisiones de arquitectura, o que un arquitecto no escriba las historias de usuario? No prohibiendo la participación (el Advice Process la exige), sino haciendo que **el artefacto no autorizado no cuente**:

- **Matriz de autoridad** (`spec/authority-matrix.yaml`, plantilla en `sdlc-orchestrator/assets/`): declara UN rol dueño por artefacto (`spec/adr/` → software-architect, `spec/user-stories.md` → business-analyst, `spec/technical-stories.md` → solution-architect, etc.). Versionada en Git: cambiar quién manda requiere PR y queda auditado.
- **Recibos con rol (`receipt.py emit --role <rol>`)**: si el artefacto tiene owner en la matriz, el rol emisor debe coincidir — si no, el recibo se rechaza y el gate no reconoce la aprobación. El rol queda grabado en el recibo y `verify` lo re-valida contra la matriz vigente.
- **`authority_check.py`**: validación standalone (`--role`, o `--author <usuario-git> --team spec/team-roster.yaml`) para usar en CI; incluye plantilla de workflow `assets/ci-spec-governance.yml` que en cada PR verifica autoría + gates de los artefactos tocados.
- **CODEOWNERS (frontera dura)**: plantilla `assets/CODEOWNERS-template` — con branch protection, un PR que toca `spec/adr/` no se mergea sin revisión del Arquitecto.

Jerarquía de garantías: convención (SKILL.md) → gate (recibo con rol) → CI (`authority_check.py`) → Git (CODEOWNERS + branch protection). Las dos últimas son las que realmente bloquean; las dos primeras hacen que el incumplimiento sea visible e inútil.

---

## 6. Uso con LiteLLM

LiteLLM soporta las skills de dos maneras, según lo que necesites:

| Vía | Cuándo usarla |
|---|---|
| **A. Skills API (passthrough a Anthropic)** | Quieres subir/usar las skills programáticamente contra la API de Anthropic, con el proxy gestionando auth, costos y logging. |
| **B. Skills Gateway / Skill Hub** | Quieres publicar el arnés una vez y que todo el equipo lo instale desde un hub central (p. ej. en Claude Code). |

> Importante: la Skills API de LiteLLM sigue el estándar de Anthropic y hoy solo soporta el provider `anthropic` — los modelos deben tener acceso al entorno de ejecución de código (Code Execution) de Anthropic para que las skills se activen. Las versiones `1.83.7+` del proxy incluyen parches de seguridad relevantes; no uses versiones anteriores en producción.

### A. Skills API vía LiteLLM

#### Opción A1 — Python SDK

Los archivos `.skill` del arnés son ZIPs válidos, así que se suben directamente (renombrando a `.zip`):

```python
from litellm import create_skill, list_skills
import glob, shutil, os

# 1. Subir las 21 skills del arnés
skill_ids = {}
for f in sorted(glob.glob("./sdlc-*.skill")):
    zip_path = f.replace(".skill", ".zip")
    shutil.copy(f, zip_path)  # .skill es un zip estándar
    resp = create_skill(
        display_title=os.path.basename(f).replace(".skill", ""),
        files=[open(zip_path, "rb")],
        custom_llm_provider="anthropic",
        api_key="sk-ant-...",
    )
    skill_ids[resp.display_title] = resp.id
    print(f"Creada: {resp.display_title} -> {resp.id}")

# 2. Verificar
for s in list_skills(custom_llm_provider="anthropic", api_key="sk-ant-...").data:
    print(s.display_title, s.id)
```

Luego las usas en una llamada Messages referenciando los IDs en el contenedor de ejecución:

```python
import anthropic

client = anthropic.Anthropic()
resp = client.beta.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=4096,
    betas=["code-execution-2025-08-25", "skills-2025-10-02"],
    container={
        "skills": [
            {"type": "custom", "skill_id": skill_ids["sdlc-orchestrator"], "version": "latest"},
            {"type": "custom", "skill_id": skill_ids["sdlc-product-owner"], "version": "latest"},
            # ...agregar los roles que la fase requiera
        ]
    },
    tools=[{"type": "code_execution_20250825", "name": "code_execution"}],
    messages=[{"role": "user", "content":
        "Ejecuta el pipeline SDLC en modo full-pipeline para: <tu idea>"}],
)
```

> Recomendación: no subas las 21 skills al contenedor a la vez. Carga el orquestador + los roles de la fase en curso (la metadata de cada skill consume contexto).

#### Opción A2 — LiteLLM Proxy (curl)

```bash
# Subir una skill (el .skill renombrado a .zip)
curl "http://0.0.0.0:4000/v1/skills?beta=true" \
  -X POST \
  -H "X-Api-Key: sk-1234" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: skills-2025-10-02" \
  -F "display_title=sdlc-orchestrator" \
  -F "files[]=@sdlc-orchestrator.zip"

# Listar / obtener / eliminar
curl "http://0.0.0.0:4000/v1/skills?beta=true" -H "X-Api-Key: sk-1234" \
  -H "anthropic-version: 2023-06-01" -H "anthropic-beta: skills-2025-10-02"
curl "http://0.0.0.0:4000/v1/skills/<skill_id>?beta=true" -X DELETE -H "X-Api-Key: sk-1234" \
  -H "anthropic-version: 2023-06-01" -H "anthropic-beta: skills-2025-10-02"
```

Con varias cuentas de Anthropic, agrega `-F "model=<model_name>"` para enrutar según el `model_list` de tu `config.yaml`.

### B. Skills Gateway / Skill Hub (distribución organizacional)

Si el arnés lo va a usar todo un equipo, publícalo una vez en el hub del proxy:

```bash
# 1. Registrar el repo del arnés (sube la carpeta sdlc-harness/skills a un repo Git)
curl -X POST https://tu-proxy/claude-code/plugins \
  -H "Authorization: Bearer $LITELLM_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sdlc-orchestrator",
    "source": {
      "source": "git-subdir",
      "url": "https://github.com/tu-org/sdlc-harness",
      "path": "skills/sdlc-orchestrator"
    },
    "description": "Orquestador del pipeline SDLC con SDD+TDD",
    "domain": "Engineering",
    "namespace": "sdlc"
  }'
# (repetir por cada una de las 21 skills)

# 2. Publicar en el hub
curl -X POST https://tu-proxy/claude-code/plugins/sdlc-orchestrator/enable \
  -H "Authorization: Bearer $LITELLM_ADMIN_KEY"
```

Cada desarrollador apunta su Claude Code al marketplace del proxy una sola vez:

```json
// ~/.claude/settings.json
{
  "extraKnownMarketplaces": {
    "mi-org": {
      "source": "url",
      "url": "https://tu-proxy/claude-code/marketplace.json"
    }
  }
}
```

```bash
/plugin marketplace add sdlc-orchestrator
```

Ventajas de esta vía: una sola fuente de verdad para las skills, actualizaciones centralizadas (actualizas el repo Git y el equipo reinstala), y descubrimiento vía UI (`AI Hub → Skill Hub`) o API pública (`GET /public/skill_hub`).

### Limitaciones a tener en cuenta con LiteLLM

- Las skills **solo se activan en modelos Anthropic** con Code Execution habilitado; para otros providers (OpenAI, Gemini…) LiteLLM enruta el texto, pero no ejecuta el mecanismo de skills — en ese caso usa la vía de agentes locales (sección 2) o inyección manual del SKILL.md en el system prompt.
- Los scripts del orquestador (`gate_checker.py`, etc.) corren dentro del entorno de ejecución del contenedor de Anthropic: verifica que `python3` esté disponible allí (lo está en el entorno estándar de Code Execution).
- Los gates humanos (GATE 1 y 3) siguen siendo humanos: estructura tu aplicación para pausar el loop y pedir aprobación entre llamadas.

---

## 7. Notas para agentes que consuman estas skills

- La fuente de verdad es el directorio `spec/` del proyecto, versionado en Git junto al código. Nunca generes artefactos sueltos fuera de esa estructura.
- Usa siempre las plantillas de `assets/` de cada skill; no reinventes formatos.
- TDD no es opcional en las skills de desarrollo: los tests preceden al código y deben ser verificables en el historial de commits.
- Todo bug encontrado en QA se devuelve al dev **con el test que lo reproduce** (TDD de bugs).
- Ante un artefacto de entrada faltante o incoherente: detenerse y reportar al orquestador, no improvisar.
- Mantener trazabilidad: cada commit/test referencia su HU-xxx; cada historia su épica EP-xxx.
