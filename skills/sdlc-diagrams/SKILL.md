---
name: sdlc-diagrams
description: "Generador de diagramas del arnés SDLC con el servidor MCP oficial de draw.io (npx @drawio/mcp o mcp.draw.io). Cubo todas las familias: C4 (Context/Container/Component), arquitectura y despliegue cloud con iconos oficiales AWS/Azure/GCP, diagramas de secuencia UML, BPMN 2.0, Gantt, GitFlow/Git graph y flujos de proceso — eligiendo la ruta correcta por familia: XML nativo drawio (C4, cloud, BPMN) o importación Mermaid (secuencia, Gantt, GitFlow) vía open_drawio_mermaid. Salida .drawio editable versionada en spec/diagrams/. Además DERIVO diagramas desde fuentes (despliegue desde terraform.tfstate/ARM, pipeline CI/CD desde workflows de GitHub) y los renderizo headless a SVG/PNG (drawio-desktop CLI / mmdc), con detección de drift y aprobación humana por recibo — el diagrama regenerado propone el cambio y un humano lo acepta. Usar cuando cualquier rol necesite diagramas formales: Architect, Cloud Engineer, BA (BPMN), DevOps (GitFlow, pipelines CI/CD), PO (Gantt/roadmap). Dispara ante: diagrama C4, diagrama de arquitectura, diagrama AWS/Azure/GCP, drawio, diagrama de secuencia, BPMN, Gantt, GitFlow, diagrama de despliegue, iconos de nube, diagrama desde terraform, diagrama de pipeline CI/CD, drift de diagramas, renderizar diagrama a svg/png."
harness-role: diagrams
harness-phases: "transversal"
harness-optional-deps: "drawio-mcp, drawio-desktop, mmdc"
---

# Diagramas con drawio MCP (skill general del arnés)

Genera diagramas editables y versionados con el servidor MCP oficial de draw.io: C4, despliegue cloud (AWS/Azure/GCP), secuencia, BPMN 2.0, Gantt, GitFlow, flujos UX y mapas de proceso. Salida: `.drawio` en `spec/diagrams/` (fuente de verdad, Git); los PNG/SVG son derivados.

Sirve a: Architect (C4, cloud), Cloud Engineer (despliegue), BA (BPMN, flujos), DevOps (GitFlow, pipelines), Orquestador (Gantt del roadmap junto al PO).

## Requisito: drawio MCP

| Variante | Instalación | Herramientas clave | Salida |
|---|---|---|---|
| **Tool server** (IDEs) | `npx @drawio/mcp` (stdio) | `open_drawio_xml`, `open_drawio_mermaid`, `open_drawio_csv`, `search_shapes`, `list_pages`/`get_page`/`set_page` | Abre el editor draw.io en el navegador |
| **App server** (chat inline) | remote `https://mcp.draw.io/mcp` | `create_diagram`, `search_shapes` | Preview inline (MCP Apps: Claude.ai, Cursor) |

```json
{ "servers": { "drawio": { "command": "npx", "args": ["-y", "@drawio/mcp"] } } }
```

Sin MCP disponible: generar igualmente el `.drawio` en disco (válido y editable en app.diagrams.net). El MCP es el visor; el artefacto versionado es el entregable.

## Decisión clave: ¿XML nativo o Mermaid→drawio?

No todo se dibuja igual. Elegir la ruta según la familia ANTES de generar:

| Familia | Ruta recomendada | Por qué |
|---|---|---|
| **C4** (Context/Container/Component) | XML nativo | Control fino de boundaries, colores C4, layout |
| **Cloud** (Azure/AWS/GCP deployment) | XML nativo | Iconos oficiales exactos vía `search_shapes` |
| **Secuencia (UML)** | Mermaid → `open_drawio_mermaid` | Sintaxis de lifelines/mensajes es declarativa y corta; el importador hace el layout |
| **Gantt** | Mermaid → `open_drawio_mermaid` | El Gantt en XML manual es muy laborioso; Mermaid lo deriva de fechas |
| **GitFlow / Git graph** | Mermaid → `open_drawio_mermaid` | Ramas/merges se declaran, no se dibujan |
| **BPMN 2.0** | XML nativo con shapes BPMN | Pools/lanes, gateways y eventos tienen shapes dedicados; layout manual da control |
| **Flujos UX / mapas de proceso** | XML nativo o Mermaid, según complejidad | — |
| **Datos tabulares** (org charts, listas) | CSV → `open_drawio_csv` | El CSV importer genera el grafo desde datos |

Si Mermaid cubre el 90% del diagrama pero faltan detalles: importar con `open_drawio_mermaid` y terminar de editar en el editor (o con `set_page`).

## Flujo de trabajo (obligatorio)

1. **Elegir familia y ruta** según la tabla anterior. Cargar SOLO la referencia necesaria:
   - `references/c4-and-cloud-styles.md` — C4 + iconos AWS/Azure/GCP (style strings listos).
   - `references/sequence-gantt-gitflow.md` — plantillas Mermaid para `open_drawio_mermaid`.
   - `references/bpmn.md` — shapes y convenciones BPMN 2.0 en XML.
2. **Resolver shapes no listados con `search_shapes`** (p. ej. `search_shapes "azure functions"`, `"bpmn gateway"`) y copiar el style exacto devuelto. Nunca inventar rutas de iconos.
3. **Construir** el XML (ruta nativa) o el código Mermaid (ruta importación).
4. **Abrir/previsualizar**: `open_drawio_xml` u `open_drawio_mermaid`. Para editar una página existente: `list_pages` → `get_page` → `set_page`.
5. **Persistir** en `spec/diagrams/<familia>-<nombre>.drawio`, multipágina si hay varios niveles/vistas.
6. **Trazabilidad**: el nombre de página o un `userObject` referencia las HU/EP/artefactos cubiertos.

## Reglas del arnés

- Todo nodo usa el término canónico de `spec/glossary.md`; toda relación declara protocolo/etiqueta.
- Los diagramas cloud de despliegue reflejan `infra/` (IaC): si el IaC cambia, el diagrama queda impactado (el orquestador lo marca vía `spec_diff_impact`).
- Mermaid embebido en los `.md` de la spec sigue válido para bocetos; los `.drawio` son para diagramas formales que requieren edición visual o presentación a stakeholders.
- `assets/c4-contenedores-ejemplo.drawio`: plantilla C4 Container (Azure) lista para duplicar.

## Dos direcciones y aprobación (v2.6)

Los diagramas son también un **mecanismo de aceptación de cambios**: ningún diagrama cuenta como válido sin recibo de aprobación humana sobre su contenido.

| Dirección | Familias | Cómo se crea | Quién aprueba (recibo con rol) |
|---|---|---|---|
| **Diseño** (manual) | C4, secuencia, BPMN, Gantt, GitFlow, flujos | El rol lo dibuja con el MCP drawio / XML / Mermaid | Su rol dueño (C4 → `software-architect`, BPMN → `business-analyst`, Gantt → `product-owner`, GitFlow → `devops-engineer`) |
| **Derivado** (desde fuente, NUNCA editado a mano) | Despliegue cloud/red, pipeline CI/CD | Script desde `terraform.tfstate`/ARM o `.github/workflows/` | `cloud-engineer` (despliegue), `devops-engineer` (pipeline) — revisan el diff en Git y aprueban con `receipt.py emit` |

Flujo de aceptación de un diagrama derivado:

1. La fuente cambia (apply de Terraform, push que toca workflows).
2. El script regenera el diagrama → **propuesta de cambio**; el diff en Git muestra exactamente qué cambió.
3. El humano/rol dueño revisa el contenido y lo acepta con `receipt.py emit --artifact <diagrama> --role <rol>` — sin recibo, el cambio NO está aceptado.
4. `check` (exit 1 si el diagrama difiere de la fuente) detecta **drift** en CI o en gates: regenerar o investigar.

### Scripts (Python 3 stdlib puro)

- `iac_to_diagram.py generate|check --tfstate terraform.tfstate|--arm template.json --out spec/diagrams/despliegue.drawio`: topología de despliegue desde el estado real de Terraform (lo REALMENTE desplegado) o ARM/Bicep compilado, con iconos oficiales AWS/Azure/GCP y clusters por módulo/resource group. `check` = drift detection.
- `pipeline_diagram.py generate|validate|check --workflows-dir .github/workflows --out spec/diagrams/pipeline-cicd.md`: flowchart Mermaid por workflow (triggers, jobs, `needs:`) + validación de `needs:` inexistentes y ciclos de dependencias. `validate` exit 1 si el pipeline está roto; `check` = drift detection.
- `diagram_render.py render <.drawio|.mmd|.md>|render-dir|engines`: render headless a SVG/PNG vía drawio-desktop CLI (el SVG embebe el fuente — la imagen sigue editable) o mmdc (incluye bloques Mermaid dentro de Markdown, reescribiendo las referencias — ideal para doc-as-code). Motores opcionales: sin ellos informa y el fuente versionado sigue siendo el entregable (nunca bloquea).

Los SVG/PNG renderizados son **vistas derivadas**: se regeneran tras cada aprobación y los referencia `sdlc-technical-writer` en la documentación. No reciben recibo propio; el recibo es del fuente.
