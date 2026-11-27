---
name: sdlc-diagrams
description: "Generador de diagramas del arnés SDLC. Routing canónico PLT-01 D1–D8 (ADR-005): IR JSON interactivo para contexto C4 L1, contenedores C4 L2, despliegue, integración/mensajería, dataflow/DFD, componentes C4 L3 con drill-down y threat-model STRIDE; Mermaid sequenceDiagram para flujos funcionales D4. Iconos opcionales de Python Diagrams 0.25.1 sincronizados a caché local con SHA-256 e incrustados en HTML sin red ni Graphviz. IR con foco/lens/detalle/insights, tema claro/oscuro, badges de ubicación, validación, diff Before/After y anti-drift. También soporta capability-map BIAN, ER, stakeholder/onion, workflow, lifecycle y sequence simple; pipeline CI/CD derivado de GitHub Actions; Mermaid para Gantt/GitFlow y render headless opcional vía mmdc. KubeDiagrams→IR y exports estáticos mediante Diagrams están planificados, no disponibles todavía. Draw.io está retirado. Usar para arquitectura, C4, infraestructura, Kubernetes, integración, DFD, STRIDE, secuencias, pipelines y diagramas vivos gobernados con recibo."
harness-role: diagrams
harness-phases: "transversal"
harness-optional-deps: "mmdc, diagrams==0.25.1"
---

# Diagramas del arnés (routing híbrido gobernado)

La vía principal es un **IR JSON versionado** (`spec/diagrams/*.ir.json`) y un renderer determinista stdlib (`diagram_ir.py`) que deriva HTML/SVG interactivo y autocontenido. La excepción del catálogo PLT-01 es D4: sus flujos funcionales usan Mermaid `sequenceDiagram`.

Archify permanece como **inspiración de foco, lens, detalle e insights**, no como dependencia. Python Diagrams aporta iconografía opcional; KubeDiagrams será un adaptador hacia IR. Ninguno crea una segunda fuente editable para el mismo diagrama.

## Routing canónico PLT-01 (D1–D8)

La fuente legible por máquina es `assets/catalogo-arquitectura.json`; `references/catalogo-arquitectura.md` se deriva de ella. Consulta la ruta antes de crear o cambiar un diagrama:

| ID | Pregunta / diagrama | Fuente única | Vista y apoyo |
|---|---|---|---|
| **D1** | Contexto de negocio y usuarios | IR `context` | HTML interactivo; un sistema central y toda relación conectada a él |
| **D2** | Contenedores y servicios C4 N2 | IR `container` | Boundaries, stack, protocolos, ubicación, drill-down e iconos opcionales |
| **D3** | Despliegue e infraestructura | IR `deployment` | Hulls región→VPC→subnet, ubicación e iconos; adaptador Kubernetes planificado |
| **D4** | Flujos funcionales principales | Mermaid `sequenceDiagram` | Autonumber, notas, errores y compensaciones; SVG/PNG opcional vía `mmdc` |
| **D5** | Integración y mensajería | IR `integration` | Foco por integración, iconos opcionales y matriz complementaria |
| **D6** | Flujo de datos DFD | IR `dataflow` | Fuentes, transformaciones, almacenes y clasificación; tabla complementaria |
| **D7** | Componentes internos C4 N3 | IR `component` | Boundary del contenedor y drill-down desde D2 |
| **D8** | Seguridad y fronteras de confianza | IR `threat-model` | STRIDE, trust boundaries, controles e iconos opcionales |

```bash
python diagram_catalog.py list
python diagram_catalog.py route --diagrama D3 --kubernetes
python diagram_catalog.py render   # deriva references/catalogo-arquitectura.md
python diagram_catalog.py check    # exit 1 si la referencia quedó atrás
```

**D4 en Azure DevOps:** con Mermaid 8.13.9 usar la valla `::: mermaid`, `graph` en flowcharts y ningún comentario inicial. Para secuencias simples que necesiten foco/lens sigue disponible IR `sequence`, pero no se duplica el mismo D4 en dos fuentes.

> **Draw.io permanece retirado.** No se generan `.drawio` ni se usa su MCP. Los exports estáticos mediante Python Diagrams y el adaptador KubeDiagrams→IR son trabajo **planificado**, no capacidades disponibles en este incremento.

## Contrato del IR

- `kind: flow` — architecture, context, container, component, deployment, integration, capability-map, er, stakeholder, threat-model, workflow, dataflow y lifecycle.
- `kind: sequence` — secuencias simples con lifelines, mensajes numerados, retornos y activaciones.
- `bandas` — `hulls` para grupos/boundaries, `filas` para carriles y `columnas` para etapas/dominios.
- Interacción derivada: clic → foco + detalle; leyenda lens (hasta dos tipos); estado por URL `#focus=`/`#lens=`; `insights` gobernados en el IR.
- Vista: tema claro/oscuro, zoom de fuente, textos con wrap/elipsis y badges `ubicacion` para nube/on-prem/otro.
- `architecture`, `container` y `deployment` exigen `ubicacion` en cada nodo/participante.
- `context` exige exactamente un nodo `central: true`; `container` exige hulls y `grupo` en todos los nodos.
- `component` admite `ir: "otro.ir.json"` para drill-down ↗; `deployment`/`stakeholder` usan `anidados` y rechazan ciclos.
- `capability-map` exige columnas, dominio en una sola columna y `estado: adoptar|madurar|mantener|retirar`.
- `er` exige cardinalidades `card_d`/`card_h`; `threat-model` valida límites y `amenaza: S|T|R|I|D|E`.
- Los IDs de nodos y participantes deben ser únicos.

```bash
python diagram_ir.py validate --ir spec/diagrams/x.ir.json
python diagram_ir.py render   --ir spec/diagrams/x.ir.json --out spec/diagrams/x.html
python diagram_ir.py diff     --old a.ir.json --new b.ir.json   # exit 2 si hay cambios
python diagram_ir.py check    --ir x.ir.json --out x.html       # exit 1 si hay drift
```

## Iconos Python Diagrams opcionales (renderer IR v1.5)

Un nodo `flow` puede declarar `icono` con el ID canónico `provider.categoria.recurso`:

```json
{
  "id": "api",
  "titulo": "API de pagos",
  "tipo": "service",
  "ubicacion": "AWS · producción",
  "icono": "aws.compute.ec2"
}
```

Ejemplos: `aws.compute.ec2`, `azure.compute.function-app`, `gcp.run.run`, `k8s.compute.deploy`. El ID debe corresponder a un PNG real de Diagrams **0.25.1**; no se inventan rutas. Los nodos `decision` y los participantes `sequence` no admiten todavía esta propiedad.

```bash
python diagram_icons.py sync  --ir spec/diagrams/x.ir.json
python diagram_icons.py check --ir spec/diagrams/x.ir.json
python diagram_ir.py render   --ir spec/diagrams/x.ir.json --out spec/diagrams/x.html
```

1. `sync` copia solo los recursos referenciados a `<directorio IR>/icons/<provider>/<categoria>/` y deriva `icons/index.json` con versión, ruta relativa y SHA-256. Conserva entradas de otros IR que comparten la caché.
2. Diagrams 0.25.1 solo se requiere cuando hay recursos ausentes o desactualizados que sincronizar. No se descarga nada y no se ejecuta Graphviz.
3. `validate`, `render` y `check` usan la caché versionada; el PNG se incrusta como `data:image/png;base64,...`. Sin iconos, la ruta stdlib permanece intacta.
4. `diagram_icons.py check` exige lock, PNG y hash coincidentes; no importa Diagrams. Versionar el IR, los PNG referenciados y `icons/index.json` juntos.

## Gobierno y aprobación

- **Una fuente por diagrama.** HTML, SVG, PNG, PDF y la referencia del catálogo son vistas derivadas; nunca se editan a mano.
- El recibo se emite sobre el **IR** o sobre el Markdown Mermaid de D4, no sobre la imagen. `diff` acompaña el cambio y `check` detecta drift en CI/gates.
- Todo nodo usa `spec/glossary.md`; las relaciones declaran protocolo/etiqueta. Los iconos no sustituyen responsables, clasificación, controles, ficha INI/ambiente/fecha ni tablas complementarias.
- Si cambia `infra/`, `spec_diff_impact.py` marca el IR de despliegue impactado. El futuro IR importado desde Kubernetes será separado del IR de diseño aprobado.
- Dueños: architecture/context/container/component/integration/sequence → `sdlc-software-architect`; deployment → `sdlc-cloud-engineer`; er/dataflow → `sdlc-data-engineer`; threat-model → `sdlc-security-engineer`; stakeholder → `sdlc-business-analyst`; capability-map → `sdlc-solution-architect` o `sdlc-enterprise-architect`; pipelines → `sdlc-devops-engineer`; lifecycle de HU → `sdlc-orchestrator`.
- El gate de `architecture.md` exige IR referenciado, válido y con recibo vigente. Un bloque Mermaid suelto no cumple ese gate, salvo la fuente D4 gobernada en su propio artefacto.

## Scripts

- `diagram_catalog.py list|route|render|check` — routing D1–D8 y referencia derivada.
- `diagram_ir.py validate|render|diff|check` — validación, vista interactiva, Before/After y anti-drift.
- `diagram_icons.py sync|check` — caché autocontenida y verificable de iconos Diagrams.
- `pipeline_diagram.py generate|validate|check` — Mermaid derivado de `.github/workflows/`, con validación de `needs` y ciclos.
- `diagram_render.py render|engines` — SVG/PNG headless de Mermaid vía `mmdc`, opcional y con degradación elegante.

Fixtures: `tests/fixtures/diagram-flow.ir.json`, `diagram-sequence.ir.json`, `diagram-context.ir.json`, `diagram-container.ir.json`, `diagram-component.ir.json`, `diagram-capability-map.ir.json`, `diagram-deployment.ir.json`, `diagram-er.ir.json`, `diagram-stakeholder.ir.json`, `diagram-threat-model.ir.json` y `demo-arquitectura-ubicaciones.ir.json`.

## Siguiente incremento planificado

1. **KubeDiagrams→IR `deployment`:** entrada offline de manifiestos/Helm/Kustomize; salida separada del diseño. Lectura de clúster únicamente con opt-in, minimización y sanitización.
2. **Exports mediante Diagrams:** generación opcional de PNG/SVG/PDF desde el IR gobernado, sin mantener código Python paralelo. Requerirá Graphviz solo para esa exportación.
