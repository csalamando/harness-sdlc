# ADR-003: Diagramas interactivos derivados de IR (`diagram_ir.py`)

**Estado:** ACEPTADA (v2.17) · **Fecha:** 2026-09-05 · **Risk Tier:** 2

## 1. Problem Statement

El arnés genera diagramas formales con draw.io (`.drawio` editables) y los deriva desde IaC/pipelines. Pero los diagramas que más se consultan día a día —arquitectura runtime, flujo CI/CD, ciclo de vida de una HU, dataflow, secuencias de integración— tienen tres problemas:

1. **No se mantienen**: se dibujan una vez en Fase 2 y quedan congelados mientras la spec evoluciona.
2. **Cuestan tokens**: pedir al agente que dibuje/edite XML de drawio a mano en cada cambio es caro y propenso a errores de layout.
3. **No son explorable**: un PNG estático no responde "¿qué es este nodo?" ni "¿qué pasa si solo miro la capa de seguridad?".

Referencia externa: [archify](https://github.com/tt-a1i/archify) (tt-a1i/archify) demuestra el valor de una experiencia uniforme — 5 tipos de diagrama con la misma interacción (foco + detalle al clic, leyenda lens, tarjetas de insights). Se evaluó como adopción y se descarta: requiere runtime Node, un daemon de análisis y que el agente escriba diagramas a mano. **Se toma como inspiración, no como dependencia** (mismo patrón que engram → `mem.py` y gortex → `code_intel.py`).

## 2. Decisión

**Un archivo IR (Intermediate Representation) JSON versionado en `spec/diagrams/*.ir.json` + un renderer determinista stdlib (`diagram_ir.py`) que genera HTML/SVG interactivo auto-contenido.**

```
spec/diagrams/login.seq.ir.json   ← fuente de verdad (diff-able en PR, la edita el rol)
spec/diagrams/login.seq.html      ← vista derivada (NUNCA editada a mano)
```

### Principios

1. **El IR es la fuente, el HTML es derivado** — mismo patrón que `spec/dashboard.html` (ADR-002): markdown/JSON diff-able en PRs; HTML regenerado en milisegundos, anti-drift con `--check`.
2. **Cero tokens en el render** — el layout, routing de aristas e interacción son deterministas (Python stdlib + SVG + JS inline). El agente solo edita el IR (pequeño, estructurado).
3. **Interacción uniforme en los 5 tipos** — architecture, workflow, dataflow, lifecycle (motor de flujo común) y sequence: clic en elemento → foco + panel de detalle; leyenda clicable tipo *lens* (hasta 2 tipos); estado compartible por URL (`#focus=`, `#lens=`).
4. **Estructura visual por tipo** — hulls por grupo (architecture), carriles horizontales (workflow/lifecycle), columnas de etapa (dataflow), lifelines con barras de activación (sequence).
5. **Insights gobernados** — las tarjetas de lectura bajo el diagrama viven en el IR (`insights`), no las escribe el agente en HTML; el `diff` detecta cuando un insight queda desalineado del grafo.
6. **Cambios con evidencia** — `diagram_ir.py diff --old --new` produce el Before/After (nodos/aristas agregados, eliminados, modificados) que acompaña el recibo de aprobación.

### Subcomandos

```bash
python diagram_ir.py render   --ir <file.ir.json> --out <file.html>
python diagram_ir.py validate --ir <file.ir.json>          # esquema + referencias
python diagram_ir.py diff     --old <a.ir.json> --new <b.ir.json>
python diagram_ir.py check    --ir <file.ir.json> --out <file.html>   # exit 1 si drift
```

## 3. Opciones consideradas

1. **Adoptar archify como dependencia** — DESCARTADA: runtime Node + daemon; el análisis estático que aporta ya lo cubre `code_intel.py`; nos encadenaría a su modelo de datos.
2. **Seguir solo con draw.io MCP** — INSUFICIENTE: el `.drawio` editable sigue siendo el formato para diagramas formales con stakeholders (C4, BPMN, cloud con iconos oficiales), pero no da exploración interactiva ni render sin tokens.
3. **Mermaid embebido en Markdown** — SE MANTIENE para bocetos, pero no soporta foco/lens/detalle ni layout controlado (los back-edges cruzan nodos).
4. **Que el agente escriba SVG a mano** — DESCARTADA: tokens altísimos y layouts inconsistentes entre iteraciones.

## 4. Consecuencias

- **Matriz de autoridad**: `spec/diagrams/*.ir.json` los crea/edita el rol dueño del dominio (architecture → `sdlc-software-architect`, workflow CI/CD → `sdlc-devops-engineer`, lifecycle de HU → `sdlc-orchestrator`, dataflow → `sdlc-data-engineer`, sequence → `sdlc-software-architect`). El HTML es derivado sin recibo propio; el recibo se emite sobre el IR.
- **Coexistencia**: los `.drawio` siguen para diagramas formales editables; los `.ir.json` para diagramas vivos de seguimiento. Un mismo sistema puede tener ambos.
- **Self-test**: render+validate+diff+check con IR de prueba.
- **Sin dependencias**: Python stdlib; el HTML resultante no hace llamadas de red.

## 5. Criterios de éxito

1. Actualizar un diagrama tras un cambio de spec cuesta <200 tokens (editar el IR) + 0 tokens de render.
2. `check` en CI detecta HTML desactualizado en <1s.
3. Un stakeholder explora foco/lens/detalle sin instalar nada (el HTML es auto-contenido).
