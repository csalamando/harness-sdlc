# Arnés SDLC — SDD + TDD con gobernanza de decisiones

Un arnés de agentes para gobernar el ciclo de vida completo del software (**SDLC**) combinando **Spec-Driven Development (SDD)** y **Test-Driven Development (TDD)**, implementado como un conjunto de **19 skills** que siguen el estándar abierto **Agent Skills** (SKILL.md + assets/references/scripts), ejecutables en Kimi, Claude Code, Antigravity, Codex, Cursor, Copilot, VS Code, Open WebUI y LiteLLM.

> **Principio rector:** la fuente de verdad es `spec/` versionada en Git. Si una decisión, aprobación o aprendizaje no está versionada, no existe.

---

## Tabla de contenidos

1. [Visión general](#1-visión-general)
2. [Las 19 skills](#2-las-19-skills)
3. [El pipeline y los gates](#3-el-pipeline-y-los-gates)
4. [Routing orgánico](#4-routing-orgánico)
5. [Receipts: confiar en evidencia, no en narración](#5-receipts-confiar-en-evidencia-no-en-narración)
6. [El sistema de memoria](#6-el-sistema-de-memoria)
7. [Gobernanza de decisiones (v2.0)](#7-gobernanza-de-decisiones-v20)
8. [Gestión de cambios de spec](#8-gestión-de-cambios-de-spec)
9. [Herramientas compartidas y propias](#9-herramientas-compartidas-y-propias)
10. [Créditos y referencias](#10-créditos-y-referencias)

---

## 1. Visión general

El arnés convierte a un agente de propósito general en un **equipo de desarrollo completo con roles especializados**, donde cada rol:

- tiene **entradas y salidas declaradas** (artefactos en `spec/`),
- cumple un **checklist de salida (DoD)** verificable por script,
- produce **evidencia auditable** (recibos criptográficos, memorias, trazabilidad),
- y no puede avanzar sin que los **gates** estén en verde.

Tres ideas lo diferencian de un pipeline de prompts:

1. **RDD (Receipt-Driven Development):** las aprobaciones no son narración del agente ("ya está revisado"), sino recibos SHA-256 vinculados al contenido exacto aprobado. Si el artefacto cambia un byte, el recibo se invalida solo.
2. **Memoria persistente con gobierno:** lo aprendido no muere al cerrar la sesión. Vive en Markdown versionado con tres scopes (proyecto, usuario, organización) y un flujo de políticas y desviaciones con aprobación humana.
3. **Gobernanza de decisiones:** las decisiones técnicas significativas siguen un proceso riguroso de 8 pasos con scorecard cuantitativa, advice process y firma del Arquitecto — proporcional al riesgo (Risk Tiers).

---

## 2. Las 19 skills

| Skill | Rol | Fase |
|---|---|---|
| `sdlc-orchestrator` | Orquestador del pipeline + 11 herramientas CLI | Todas |
| `sdlc-product-owner` | Visión, épicas, backlog priorizado (el QUÉ y el CUÁNDO) | 0 |
| `sdlc-business-analyst` | Historias de usuario + Gherkin + reglas de negocio | 1 |
| `sdlc-ux-designer` | Flujos UX + design system + tokens | 2 |
| `sdlc-software-architect` | Arquitectura + OpenAPI + ADRs + test-plan. **Decision Owner técnico (el CÓMO)** | 2-3 |
| `sdlc-decision-engine` | Motor de decisiones: 8 pasos, scorecard, Decision Packages | 2 |
| `sdlc-enterprise-architect` | Tech Radar, Principios, excepciones, Paved Roads | 2 (Tier 1) |
| `sdlc-security-engineer` | Threat modeling + SAST/DAST (GATE 2.5) | 2, 4, 5 |
| `sdlc-data-engineer` | Migraciones + gobierno de datos | 2 |
| `sdlc-backend-dev-tdd` | Backend con TDD estricto | 4 |
| `sdlc-frontend-dev-tdd` | Frontend con TDD + mocks desde OpenAPI | 4 |
| `sdlc-qa-automation` | E2E desde Gherkin + regresión + carga (GATE 2) | 5 |
| `sdlc-devops-engineer` | Setup + CI/CD + IaC + rollback | -1, 6 |
| `sdlc-cloud-engineer` | Infraestructura cloud + observabilidad | 6 |
| `sdlc-sre` | SLOs + incidentes + postmortems | 7 |
| `sdlc-product-analyst` | Medición de impacto → realimenta backlog | 7 |
| `sdlc-technical-writer` | Documentación doc-as-code (Wiki / Pages / Confluence) | 4-6 |
| `sdlc-memory` | Memoria persistente con scopes y gobierno (transversal) | Todas |
| `sdlc-diagrams` | Diagramas C4, cloud (AWS/Azure/GCP), secuencia, BPMN, Gantt, GitFlow vía drawio MCP | 1, 2, 6 |

Separación de autoridad: **el PO nunca aprueba decisiones técnicas; el Arquitecto de Software es el único rol que firma ADRs.**

---

## 3. El pipeline y los gates

```
FASE -1 Setup (DevOps + detect_stack) → FASE 0 PO → FASE 1 BA
→ FASE 2 UX + Architect (+ Decision Engine) + Security + Data
→ FASE 3 Spec consolidada [GATE 1 humano]
→ FASE 4 Dev Back ∥ Dev Front (TDD)
→ FASE 5 QA + Security DAST [GATE 2 / 2.5]
→ FASE 6 DevOps + Cloud [GATE 3] → PROD
→ FASE 7 SRE opera + Product Analyst mide → realimenta backlog
→ FASE 8 Archivo: merge de delta-specs + cierre del ciclo
```

| Gate | Qué exige |
|---|---|
| **GATE 1** (humano) | Spec consolidada aprobada + sin `conflicts_with` de memoria pendientes + `policy check` en verde (toda política org mandatory attestada o con desviación aprobada vigente) + **cada ADR Tier 1-2 con 8 pasos validados, Advice Log registrado, Tech Radar cruzado y firma vigente**. Sin esto, cero código. |
| **GATE 2** | Todas las historias verificadas E2E. Bug crítico → se devuelve al dev **con el test que lo reproduce** (una corrección acotada; si falla, escala a humano). |
| **GATE 2.5** | Ninguna vulnerabilidad crítica/alta abierta. |
| **GATE 3** | Staging validado + rollback probado. |

Todo gate que pasa **emite recibo**; todo consumo downstream **verifica recibo**.

---

## 4. Routing orgánico

No todo trabajo merece el pipeline completo. El orquestador elige la **ruta mínima** antes de empezar:

| Situación | Ruta |
|---|---|
| Cambio mecánico ya entendido, 1-3 archivos, spec intacta | **Directo**: dev con TDD + gate 2 |
| Se necesita explorar 4+ archivos para entender | **Exploración delegada**: sub-tarea acotada de lectura, luego decidir con evidencia |
| Bug en producción | **Hotfix**: QA reproduce con test → dev corrige (TDD) → gates 2 y 3 |
| Ambigüedad sustancial | **Full-pipeline**: proponer al usuario; iniciar solo tras aprobación |
| Cambio de alcance aprobado | **Change-request**: ver §8 |

Los gates de entrega (2, 2.5, 3) aplican **siempre**, sin importar la ruta.

---

## 5. Receipts: confiar en evidencia, no en narración

### El problema

Un agente puede *decir* "la spec está aprobada" o "los tests pasan". Esa afirmación no es verificable y puede quedar desactualizada en el momento en que alguien edita el archivo.

### La solución: recibos criptográficos

Cuando un gate pasa, `receipt.py emit` guarda en `spec/receipts/` un JSON con el **SHA-256 exacto del artefacto aprobado**, el gate, el rol y el timestamp:

```json
{
  "receipt_id": "RCP-GATE1-architecture",
  "artifact": "spec/architecture.md",
  "sha256": "bb5c683b...",
  "gate": "GATE-1",
  "status": "ACTIVE",
  "timestamp": "2026-08-20T..."
}
```

**Reglas del sistema:**

1. **Verificación antes de consumir.** Antes de que cualquier fase downstream use un artefacto, `receipt.py verify` recalcula el hash del archivo actual y lo compara con el recibo. Un byte de diferencia → recibo **INVALIDATED** y el gate debe re-ejecutarse. Nadie aprueba dos veces sin nueva evidencia.
2. **Revocación en cascada.** Un cambio de spec (`spec_diff_impact.py`) revoca automáticamente los recibos de todos los artefactos impactados downstream.
3. **Firma arquitectónica.** Variante especializada: `arch_signoff.py` emite `ARCH-xxx.json` firmado por el Arquitecto, con hash compuesto del ADR **y** de los artefactos de diseño (architecture.md, OpenAPI, modelo de datos, diagramas). Si el diseño diverge de lo firmado en Fase 4, el pipeline se detiene.
4. **Estados auditables.** `receipt.py status` muestra todos los recibos (ACTIVE / INVALIDATED / REVOKED) — un log de gobierno derivado de criptografía, no de memoria del agente.

```bash
python3 receipt.py emit --artifact spec/architecture.md --gate GATE-1
python3 receipt.py verify --artifact spec/architecture.md
python3 receipt.py status
python3 receipt.py revoke --artifact spec/architecture.md
```

*Inspiración: patrón de "receipts" y "trust derivable evidence" observado en el ecosistema de Gentleman-Programming (ver §10), reimplementado a nuestra medida sobre SHA-256 + Git.*

---

## 6. El sistema de memoria

### El problema

Los agentes olvidan todo al cerrar la sesión: decisiones y sus razones, bugs ya resueltos, aprendizajes del proyecto. Y las organizaciones no tienen forma de hacer cumplir sus lineamientos en un flujo de agentes.

### Arquitectura: Markdown es la verdad, SQLite es solo un índice

**La fuente de verdad son archivos Markdown** con frontmatter YAML y estructura What / Why / Where / Key details / Learned:

```
./spec/memory/entries/     # scope project — viaja en el repo del proyecto
~/.sdlcmem/user/entries/   # scope user    — compartida entre tus proyectos
~/.sdlcmem/org/entries/    # scope org     — lineamientos de la organización
```

Al ser Git-nativa, la memoria tiene **historial, diff, code review y resolución de conflictos gratis**. Junto a cada raíz existe un `index.db` (**SQLite con FTS5**) que solo acelera la búsqueda con ranking. Es **100% derivable**: se borra y se reconstruye con `mem.py reindex`. Nunca pierdes nada por tocar la DB.

```bash
# Consultar la memoria
python3 mem.py search "autenticación oauth"   # búsqueda federada en los 3 scopes
python3 mem.py get MEM-2026-0001
python3 mem.py timeline
# O directo sobre el índice:
sqlite3 spec/memory/index.db "SELECT id, title FROM memories_fts WHERE memories_fts MATCH 'oauth'"
```

Para agentes, `mem_mcp.py` expone las mismas 16 operaciones como **servidor MCP stdio** (`mem_save`, `mem_search`, `mem_policy_check`, ...).

### Scopes y precedencia

`project` < `user` < `org`. Una búsqueda consulta los tres y ordena por precedencia: la organización gana. La promoción (`mem.py promote MEM-x --to org`) lleva un patrón probado en un proyecto al nivel superior, registrando `derived_from`.

### Relaciones entre memorias

- **`supersedes`**: una memoria reemplaza a otra (la anterior queda como histórico).
- **`conflicts_with`**: dos memorias se contradicen → **bloquea GATE 1** hasta resolución humana (`conflicts resolve`).

### Gobierno organizacional: políticas y desviaciones

El caso que motivó el diseño: *"si en la organización hay prácticas y lineamientos que se deben cumplir, y un proyecto necesita cambiarlos, debe existir revisión y aprobación"*.

1. **Políticas** (`--type policy --enforcement mandatory|recommended`) se guardan en scope org. Antes de GATE 1, cada proyecto ejecuta `policy check` y `policy attest`: toda política mandatory debe estar **compliant** o tener una **desviación aprobada vigente**.
2. **Desviaciones** (`deviation request → approve|reject`): el proyecto solicita excepción con justificación; un humano aprueba con **fecha de expiración**. Mientras está *pending*, NO exime. Al expirar, el gate vuelve a bloquear. Las aprobaciones son irreversibles (auditoría).
3. **Filtro de secretos**: el scope org rechaza memorias que contengan credenciales (patrones de API keys, tokens, contraseñas) — la capa compartida nunca debe filtrar secretos.

```bash
python3 mem.py save --scope org --type policy --enforcement mandatory \
  --title "TLS 1.3 en toda comunicación externa" --what "..." --why "..."
python3 mem.py policy check          # exit 1 si hay violación → bloquea GATE 1
python3 mem.py deviation request --policy POL-1 --reason "..."
python3 mem.py deviation approve DEV-1 --approver "CISO" --expires 2026-12-31
```

*Inspiración: la separación memoria/herramientas y la idea de memoria persistente entre agentes de **Engram** (Gentleman-Programming) — se decidió conscientemente **no adoptarlo** y construir uno propio mejorado: Git-nativo, con scopes, gobierno de políticas y desviaciones, relaciones y MCP (ver §10).*

---

## 7. Gobernanza de decisiones (v2.0)

Basada en el **framework de 8 pasos de Sonya Natanzon**, el **Advice Process** y el **Tech Radar** (ver §10).

### Risk Tiering — gobernanza proporcional al riesgo

`decision_sizing.py` analiza la spec y clasifica:

| Tier | Ejemplos | Gobernanza |
|---|---|---|
| **1** (alto) | PII, pagos, autenticación, datos críticos | 8 pasos + Advice completo + revisión Enterprise Architect |
| **2** (medio) | Microservicios, APIs, integraciones | 8 pasos + Advice con peers |
| **3** (bajo) | Herramientas internas, UI, prototipos | ADR simplificado + registro en memoria |

### Los 8 pasos (skill `sdlc-decision-engine`)

1. **Problem Statement** sin soluciones prematuras — el gate rechaza *"Necesitamos usar Kafka"*; exige el problema real.
2. **Last Responsible Moment** — fecha límite real, restricciones, costo de reversa.
3. **Criterios ponderados** (mín. 3, pesos = 100%) definidos **antes** de ver opciones. Opcionalmente cargados de un **Decision Package** pre-aprobado.
4. **Opciones** (mín. 2, ideal 3, una radicalmente diferente); se marcan las **Paved Roads**.
5. **Advice Process** — `advisor.py` identifica stakeholders por impacto (datos → Data Engineer; seguridad → Security Engineer; Tier 1 → siempre Enterprise Architect). El consejo **no es vinculante**; omitir la consulta **sí bloquea** el gate. Todo consejo queda en el **Advice Log**: quién, cuándo, qué, si se aplicó y por qué.
6. **Scorecard cuantitativa** — `scorecard_calculator.py` pondera criterios × opciones; la opción elegida debe ser la ganadora o tener justificación explícita.
7. **Decisión** — con consecuencias positivas esperadas y **negativas aceptadas**, y qué NO se decidió.
8. **Re-evaluation triggers** — condiciones que obligan a revisar la decisión.

### Firma y Tech Radar

- **Firma:** `arch_signoff.py` emite el recibo `ARCH-xxx.json`. Un ADR firmado **no se modifica**: se supersedea con uno nuevo. Si cambia tras la firma, el gate detecta el recibo invalidado.
- **Tech Radar** (`sdlc-enterprise-architect`): **ADOPT** = Paved Road (pre-aprobado) · **TRIAL** = justificación · **ASSESS** = ADR de excepción · **HOLD** = bloquea el gate salvo excepción aprobada por el Architecture Board.
- El Enterprise Architect **gobierna por excepción**: asesora, no veta; solo interviene en Tier 1, principio mandatory violado o tecnología en HOLD.

---

## 8. Gestión de cambios de spec

1. Declarar la relación del cambio: **supersedes** (reemplaza — flujo normal) o **conflicts_with** (contradice — requiere resolución humana, bloquea GATE 1).
2. `spec_diff_impact.py --cambiado <artefacto> --relation <rel>` lista el downstream invalidado (grafo de dependencias de la spec).
3. `receipt.py revoke` sobre cada artefacto impactado; re-ejecutar **solo** las fases afectadas.
4. Nueva versión + entrada en CHANGELOG.

En **Fase 8 (Archivo)**: merge de delta-specs en la spec maestra, memorias superseded, trazabilidad y recibos en verde, sesión cerrada. La próxima iteración arranca desde spec consolidada.

---

## 9. Herramientas compartidas y propias

- **Compartidas (plataforma):** GitHub (repo del código **y** de la spec, versionados juntos; aprobar spec = mergear PR), Jira/GitHub Projects (backlog enlazado a `spec/`), Confluence/Wiki/Pages (documentación viva vía `sdlc-technical-writer`), drawio MCP (`sdlc-diagrams`).
- **Propias del arnés (CLI en `sdlc-orchestrator/scripts/`):** `gate_checker.py`, `receipt.py`, `context_packager.py` (contexto mínimo por rol), `spec_diff_impact.py`, `traceability_matrix.py` (HU → test → código), `detect_stack.py` (sin test runner, TDD queda en pausa), `harness_doctor.py` (health check), `decision_sizing.py`, `advisor.py`, `arch_signoff.py`.
- **Regla de gobierno:** toda herramienta debe producir o consumir un artefacto versionado. Si una decisión solo existe en una llamada, no existe.

---

## 10. Créditos y referencias

Este arnés es diseño e implementación propios, pero se apoya explícitamente en ideas publicadas por otros, a quienes damos crédito:

| Idea | Autor / Proyecto | Cómo la usamos |
|---|---|---|
| **Framework de decisiones de 8 pasos** | [Sonya Natanzon — Architectural Decision Framework](https://github.com/snatanzon/architectural-decision-framework) | Núcleo de `sdlc-decision-engine`: problem statement sin soluciones, criterios ponderados, scorecard, re-evaluation triggers |
| **Advice Process, Tech Radar, Principios, arquitectura conversacional** | [Martin Fowler / Andrew Harmel-Law — *Scaling Architecture Conversationally*](https://martinfowler.com/articles/scaling-architecture-conversationally.html) | Paso 5 (advice no vinculante pero obligatorio de registrar), Tech Radar con cuadrantes, gobernanza por excepción del Enterprise Architect |
| **Tech Radar (formato ADOPT/TRIAL/ASSESS/HOLD)** | ThoughtWorks | Estructura de `spec/tech-radar.yaml` y reglas de gate |
| **Architecture Decision Records** | Michael Nygard | Plantillas de ADR y ciclo de vida (Proposed → Adopted → Superseded) |
| **"Everything is a plugin" / capability seams** | [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) | Inspiración para skills descubribles y Decision Packages extensibles (el manifiesto dinámico quedó como trabajo futuro) |
| **Patrones de trabajo con agentes, memoria entre agentes, receipts** | [Gentleman-Programming — gentle-ai](https://github.com/Gentleman-Programming/gentle-ai) y [Engram](https://github.com/Gentleman-Programming/engram) | **Inspiración, no adopción**: estudiamos su forma de trabajar y reimplementamos a nuestra medida — memoria Git-nativa con scopes/gobierno (mejorada sobre Engram) y recibos SHA-256 |
| **Estándar Agent Skills** | Formato abierto SKILL.md (Anthropic y ecosistema) | Packaging, progressive disclosure (SKILL.md → references → scripts) |
| **Doc-as-code (Wiki/Pages/Confluence)** | GitHub Wiki, MkDocs Material, markdown-confluence | Publicación de `sdlc-technical-writer` |

Agradecimiento especial a los autores de las fuentes anteriores: este arnés no copia su código; adopta sus **ideas metodológicas** y las integra en un sistema coherente con recibos, memoria gobernada y gates automatizados.

---

## Licencia

MIT
