---
name: sdlc-diagrams
description: "Generador de diagramas del arnés SDLC. Vía principal: DIAGRAMAS VIVOS INTERACTIVOS desde IR JSON (diagram_ir.py: architecture, context C4 L1, container C4 L2, component C4 L3 con drill-down, capability-map BIAN, deployment con hulls anidados región→VPC→subnet, entidad-relación con cardinalidades, stakeholder/onion, threat-model STRIDE con trust boundaries, workflow, dataflow, lifecycle, sequence) con foco/lens/detalle/insights, tema claro/oscuro, control de fuente, badges de ubicación cloud/on-prem, pills de madurez de capacidades, textos sin desborde, diff Before/After y check anti-drift — cero tokens de render, HTML auto-contenido (ADR-003). Además: pipeline CI/CD DERIVADO de workflows de GitHub en Mermaid (pipeline_diagram.py, con validación de needs y ciclos), plantillas Mermaid para secuencia/Gantt/GitFlow embebidas en la spec, y render headless a SVG/PNG vía mmdc (diagram_render.py). Todo con aprobación humana por recibo — el diagrama regenerado propone el cambio y un humano lo acepta. Desde v2.20 el arnés NO genera drawio (retirado: no daba el nivel de detalle requerido). Usar cuando cualquier rol necesite diagramas: Architect (C4/arquitectura vía IR), Solution/Enterprise Architect (mapa de capacidades BIAN), Cloud Engineer (despliegue/red vía IR), Security Engineer (threat model STRIDE), Data Engineer (ER), BA (flujos, stakeholders), DevOps (pipelines, GitFlow), PO (Gantt/roadmap). Dispara ante: diagrama de arquitectura, C4, diagrama de contexto, diagrama de contenedores, diagrama de componentes, mapa de capacidades BIAN, capability map, diagrama de despliegue, diagrama de red/topología, diagrama entidad-relación, ER, diagrama de stakeholders, onion diagram, threat model, STRIDE, modelo de amenazas, trust boundary, diagrama de secuencia, Gantt, GitFlow, diagrama desde workflows, pipeline CI/CD, drift de diagramas, renderizar mermaid a svg/png, diagrama interactivo, IR de diagrama, diagrama vivo de seguimiento, ubicación en nube de componentes."
harness-role: diagrams
harness-phases: "transversal"
harness-optional-deps: "mmdc"
---

# Diagramas del arnés (IR interactivo)

La vía principal del arnés son los **diagramas vivos interactivos**: un IR JSON versionado (`spec/diagrams/*.ir.json`, fuente de verdad diff-able en PR) + renderer determinista stdlib de cero tokens (`diagram_ir.py`). La vista es un HTML auto-contenido (sin red, sin dependencias) con foco, lens, detalle e insights. Inspirado en [archify](https://github.com/tt-a1i/archify) (inspiración, no dependencia — no requiere Node).

Sirve a: Architect (C4/arquitectura), Cloud Engineer (despliegue), BA (flujos), DevOps (GitFlow, pipelines CI/CD), Orquestador (Gantt del roadmap junto al PO).

## Decisión clave: ¿qué ruta por familia?

| Familia | Ruta | Por qué |
|---|---|---|
| **C4 / arquitectura** (Context/Container/Component) | IR `flow` (`bandas: hulls`, `tipo: context|container|component`) | Boundaries por grupos, badges de ubicación, drill-down ↗ entre niveles, foco/lens |
| **Despliegue cloud / on-prem / red** | IR `flow` (`tipo: deployment`, hulls anidados + `ubicacion`) | Mostrar DÓNDE corre cada componente es obligatorio; región→VPC→subnet via `anidados` |
| **ER / datos** | IR `flow` (`tipo: er`) | Cardinalidades exigibles en ambos extremos |
| **Stakeholders (onion)** | IR `flow` (`tipo: stakeholder`, anillos via `anidados`) | Cercanía al producto como anillos concéntricos |
| **Threat model (STRIDE)** | IR `flow` (`tipo: threat-model`, `trust` + `amenaza`) | Trust boundaries rojos y flujos con amenaza etiquetada |
| **Secuencia (UML)** | IR `sequence` | Lifelines, mensajes numerados, retornos, activaciones |
| **Workflow / dataflow / lifecycle** | IR `flow` (`bandas: filas|columnas`) | Carriles y etapas, back-edges |
| **Pipeline CI/CD** | `pipeline_diagram.py` (Mermaid derivado) | Se deriva de los workflows; nunca se dibuja a mano |
| **Gantt / GitFlow / bocetos** | Mermaid embebido en los `.md` de la spec | Declarativo y corto; render opcional vía `diagram_render.py` (mmdc) |

> **v2.20 — drawio retirado**: el arnés ya no genera `.drawio` ni usa el MCP de draw.io (no alcanzaba el nivel de detalle requerido ni daba valor frente al IR). Los scripts/referencias drawio quedan en el historial de Git. Mermaid embebido en `.md` sigue válido para bocetos.

## Tipos soportados (`kind` en el IR)

- `flow` — architecture / workflow / dataflow / lifecycle según `bandas`: `hulls` (grupos), `filas` (carriles), `columnas` (etapas). Soporta `decision` (rombo), `terminal` (doble borde) y back-edges (`"back": true`, rosa punteado, enrutados por los huecos entre columnas).
- `sequence` — participantes con lifelines, mensajes numerados, retornos punteados (`"retorno": true`), barras de activación.

**Interacción uniforme** (la genera el renderer, no se escribe a mano): clic en elemento → foco + panel de detalle; leyenda clicable tipo *lens* (hasta 2 tipos); estado por URL (`#focus=`, `#lens=`); tarjetas de `insights` bajo el diagrama (viven en el IR, no en el HTML).

**Vista (v1.1 del renderer)**:
- **Tema claro/oscuro**: toggle ☀/🌙 en la toolbar; persiste en `localStorage`. Default: campo opcional `"tema": "claro"|"oscuro"` del IR, si no, `prefers-color-scheme` del navegador.
- **Tamaño de fuente**: botones `A− / A / A+` en la toolbar (zoom 0.6–1.8, persiste en `localStorage`).
- **Ubicación de despliegue** (`"ubicacion"` en nodos/participantes): pill en la esquina superior del nodo con icono automático — ☁ nube (AWS/Azure/GCP/IBM/SaaS…), ⌂ on-premise/datacenter, ◈ otro. **Exigible por validate en diagramas de arquitectura** (v2.21): si el IR declara `"tipo": "architecture"`, todo nodo/participante sin `ubicacion` es error de validación — cada componente declara DÓNDE corre. También aparece en el panel de detalle y en el `diff`.
- **Categoría del diagrama** (campo top-level opcional `"tipo"`): `architecture` | `sequence` | `workflow` | `dataflow` | `lifecycle` | `context` | `container` | `capability-map`. `validate` rechaza valores fuera del catálogo; `architecture` y `container` activan la regla de `ubicacion`.
- **Tipos con reglas propias** (v1.2 del renderer, v2.24 del arnés):
  - `context` (C4 L1): exige exactamente **1 nodo con `"central": true`** (el sistema bajo descripción, dibujado con doble anillo) y que **toda arista toque el sistema central** — en contexto, ninguna relación externa lo salta. Tipos de nodo nuevos: `actor` (☺) y `external` (⬡).
  - `container` (C4 L2): exige `"bandas": "hulls"` y que **todo nodo caiga dentro de un boundary** (`grupo` declarado); además hereda la regla de `ubicacion` obligatoria.
  - `capability-map` (mapa de capacidades, p. ej. BIAN): exige `"bandas": "columnas"` (cada columna = un dominio), que toda capacidad tenga `grupo` y un `"estado"` del catálogo `adoptar|madurar|mantener|retirar`, dibujado como **pill de madurez** coloreado en la esquina inferior del nodo (y en el panel de detalle y el `diff`). Las aristas son opcionales. Además `validate` exige que cada dominio ocupe exactamente una columna (mismo `rank` en todas sus capacidades).
- **Tipos v1.3 del renderer (v2.25 del arnés)** — todos exigen `"bandas": "hulls"` y `grupo` en cada nodo:
  - `deployment`: zonas de despliegue con **hulls anidados** (`"anidados": {"hijo": "padre"}` — región→VPC→subnet; el padre envuelve al hijo; ciclos rechazados por validate). Hereda la regla de `ubicacion` obligatoria. Cubre también topología de red.
  - `component` (C4 L3): componentes dentro del boundary de un contenedor. Un nodo puede declarar `"ir": "otro.ir.json"` → **drill-down**: marcador ↗ en el nodo y enlace a la vista de detalle en el panel.
  - `er` (Entidad-Relación): entidades tipo `entity|db|store`; toda arista exige `card_d` y `card_h` del catálogo `1|N|M|0..1|0..N|1..N|1..1|N..M`, dibujadas junto a cada extremo.
  - `stakeholder` (onion): anillos concéntricos via `anidados` (equipo núcleo → negocio → externos); nodos tipo `role`.
  - `threat-model` (STRIDE/DFD): **trust boundaries** — grupos listados en `"trust": [...]` se dibujan con borde rojo grueso y ⛨; las aristas pueden declarar `"amenaza": "S|T|R|I|D|E"` (validada contra STRIDE) y se etiquetan `⚠X · label`.
- **Textos sin desborde**: los títulos hacen wrap a máximo 2 líneas y los subtítulos usan elipsis, calculado de forma determinista (sin medir fuentes); el texto nunca sale del nodo.

```bash
python diagram_ir.py validate --ir spec/diagrams/x.ir.json      # esquema + referencias
python diagram_ir.py render   --ir spec/diagrams/x.ir.json --out spec/diagrams/x.html
python diagram_ir.py diff     --old a.ir.json --new b.ir.json   # Before/After (exit 2 si hay cambios)
python diagram_ir.py check    --ir x.ir.json --out x.html       # exit 1 si el HTML quedó atrás
```

**Reglas**: el HTML NUNCA se edita a mano (el `check` lo detecta); el recibo de aprobación se emite sobre el **IR** (`receipt.py emit --artifact spec/diagrams/x.ir.json --role <rol dueño>`); el `diff` acompaña el recibo como evidencia del cambio. Dueños del IR por tipo: architecture/context/container/component/sequence → `sdlc-software-architect`, deployment → `sdlc-cloud-engineer`, er → `sdlc-data-engineer`, threat-model → `sdlc-security-engineer`, stakeholder → `sdlc-business-analyst`, capability-map → `sdlc-solution-architect` (o `sdlc-enterprise-architect` si el mapa es corporativo), workflow CI/CD → `sdlc-devops-engineer`, lifecycle de HU → `sdlc-orchestrator`, dataflow → `sdlc-data-engineer`. Fixtures de ejemplo: `tests/fixtures/diagram-flow.ir.json`, `diagram-sequence.ir.json`, `diagram-context.ir.json` (C4 L1), `diagram-container.ir.json` (C4 L2), `diagram-component.ir.json` (C4 L3 con drill-down ↗), `diagram-capability-map.ir.json` (mapa BIAN), `diagram-deployment.ir.json` (hulls anidados región→VPC→subnet + on-prem), `diagram-er.ir.json` (cardinalidades), `diagram-stakeholder.ir.json` (onion concéntrico), `diagram-threat-model.ir.json` (trust boundaries + STRIDE) y `demo-arquitectura-ubicaciones.ir.json` (arquitectura multi-nube/on-prem con badges de `ubicacion`).

## Reglas del arnés

- Todo nodo usa el término canónico de `spec/glossary.md`; toda relación declara protocolo/etiqueta.
- Los diagramas de despliegue reflejan `infra/` (IaC): si el IaC cambia, el IR queda impactado (el orquestador lo marca vía `spec_diff_impact`).
- Mermaid embebido en los `.md` de la spec sigue válido para bocetos (Gantt, GitFlow, secuencias rápidas); los IR son para diagramas vivos de seguimiento y presentación a stakeholders. **Desde v2.21, el gate de `architecture.md` exige IR referenciado, válido y con recibo vigente** — un bloque mermaid suelto ya no cumple el gate, y la propuesta de arquitectura (GATE 0) exige un IR referenciado por opción.

## Dos direcciones y aprobación (v2.6)

Los diagramas son también un **mecanismo de aceptación de cambios**: ningún diagrama cuenta como válido sin recibo de aprobación humana sobre su contenido.

| Dirección | Familias | Cómo se crea | Quién aprueba (recibo con rol) |
|---|---|---|---|
| **Diseño** (manual) | Arquitectura/C4, secuencia, flujos, Gantt, GitFlow | El rol edita el IR (o el Mermaid embebido) | Su rol dueño (C4 → `software-architect`, flujos → `business-analyst`, Gantt → `product-owner`, GitFlow → `devops-engineer`) |
| **Derivado** (desde fuente, NUNCA editado a mano) | Pipeline CI/CD, vistas HTML de los IR | `pipeline_diagram.py` desde `.github/workflows/`, `diagram_ir.py render` desde `*.ir.json` | `devops-engineer` (pipeline), rol dueño del IR — revisan el diff en Git y aprueban con `receipt.py emit` |

Flujo de aceptación de un diagrama derivado:

1. La fuente cambia (push que toca workflows, edición del IR).
2. El script regenera el diagrama → **propuesta de cambio**; el diff en Git muestra exactamente qué cambió.
3. El humano/rol dueño revisa el contenido y lo acepta con `receipt.py emit --artifact <diagrama> --role <rol>` — sin recibo, el cambio NO está aceptado.
4. `check` (exit 1 si el diagrama difiere de la fuente) detecta **drift** en CI o en gates: regenerar o investigar.

### Scripts (Python 3 stdlib puro)

Todos comparten el **lenguaje visual común del arnés** (v2.19): tema claro/oscuro, textos que nunca desbordan su nodo, y la misma paleta que el portal (v2.20).

- `diagram_ir.py validate|render|diff|check` — renderer de los diagramas vivos IR (ver arriba).
- `pipeline_diagram.py generate|validate|check --workflows-dir .github/workflows --out spec/diagrams/pipeline-cicd.md [--tema auto|claro|oscuro]`: flowchart Mermaid por workflow (triggers, jobs, `needs:`) + validación de `needs:` inexistentes y ciclos de dependencias. `--tema` fija la directiva `%%{init: {'theme': ...}}%%` por bloque (`auto` = el renderer elige, p. ej. GitHub sigue el modo del usuario); ids de job largos se quiebran con `<br/>`. `validate` exit 1 si el pipeline está roto; `check` = drift detection (detecta el tema grabado).
- `diagram_render.py render <.mmd|.md>|engines [--tema claro|oscuro]`: render headless de bloques Mermaid a SVG/PNG vía mmdc (con un `.md` renderiza cada bloque y reescribe las referencias — ideal para doc-as-code). `--tema` se propaga a mmdc (`-t dark|default` + fondo `#0b1220`/blanco, coherente con el IR). Motor opcional: sin mmdc informa y el fuente versionado sigue siendo el entregable (nunca bloquea).

Los SVG/PNG renderizados son **vistas derivadas**: se regeneran tras cada aprobación y los referencia `sdlc-technical-writer` en la documentación. No reciben recibo propio; el recibo es del fuente.
