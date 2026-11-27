# ADR-005: Routing híbrido de diagramas — IR, Mermaid, Diagrams y KubeDiagrams

**Estado:** ACEPTADA · **Fecha:** 2026-11-26 · **Risk Tier:** 2  
**Enmienda:** ADR-003, únicamente sus referencias históricas a coexistencia con Draw.io.

## 1. Problem Statement

El catálogo PLT-01 mezcla ocho preguntas arquitectónicas distintas. Python Diagrams aporta iconografía y layout Graphviz para infraestructura, pero no cubre la semántica C4, DFD, STRIDE o compensaciones de secuencia que el arnés necesita. A la vez, el IR actual carece de iconos reconocibles y de una ruta de importación Kubernetes.

La decisión no debe crear fuentes paralelas editables (IR + Python + Mermaid para el mismo diagrama), ni reactivar Draw.io, retirado en v2.20.

## 2. Decisión

**El arnés usa routing por pregunta arquitectónica. El IR JSON sigue siendo la fuente gobernada para siete de los ocho diagramas; D4 conserva Mermaid. Diagrams es un proveedor opcional de iconos y un futuro backend de exportación. KubeDiagrams será un adaptador de fuentes Kubernetes hacia el IR, no otra fuente de verdad.**

La matriz canónica vive en `skills/sdlc-diagrams/assets/catalogo-arquitectura.json`; `diagram_catalog.py` deriva la referencia humana y verifica su anti-drift.

| Diagrama | Fuente principal | Apoyo |
|---|---|---|
| D1 · Contexto | IR `context` | HTML interactivo; exportación de imagen derivada |
| D2 · Contenedores | IR `container` | Iconos Diagrams; exportación Diagrams opcional |
| D3 · Despliegue | IR `deployment` | Iconos Diagrams; KubeDiagrams→IR para Kubernetes |
| D4 · Flujos funcionales | Mermaid `sequenceDiagram` | Renderer de wiki o `diagram_render.py` |
| D5 · Integración | IR `integration` | Iconos opcionales; matriz de integración complementaria |
| D6 · Datos | IR `dataflow` | Tabla de clasificación/almacenes complementaria |
| D7 · Componentes | IR `component` | Drill-down desde D2 |
| D8 · Seguridad | IR `threat-model` | STRIDE + trust boundaries; iconos opcionales |

### Reglas

1. **Una fuente por diagrama.** No se mantiene a mano un Python Diagrams o Mermaid equivalente cuando el diagrama ya tiene IR.
2. **Draw.io permanece retirado.** No se regeneran `.drawio`, no se usa su MCP y no se reintroduce como exportación obligatoria.
3. **Archify sigue siendo inspiración de interacción, no dependencia.** Foco, lens, detalle e insights permanecen en el renderer IR.
4. **Iconos sin red.** `diagram_icons.py sync` copia solo los iconos referenciados desde una instalación fijada de Diagrams a `spec/diagrams/icons/`; el HTML los incrusta como `data:` y puede regenerarse después sin el paquete instalado.
5. **Dependencias opcionales.** Ni Graphviz ni Diagrams son necesarios para validar/renderizar un IR sin iconos o con su caché ya sincronizada.
6. **Kubernetes derivado y separado.** El IR importado representa lo observado/declarado en manifiestos; no sobrescribe el IR de diseño. La primera integración será offline; leer un clúster requerirá opt-in y sanitización.
7. **Aprobación sobre la fuente.** El recibo se emite sobre el IR (o el Mermaid de D4); HTML/SVG/PNG/PDF no reciben recibo propio.

## 3. Opciones consideradas

1. **Reemplazar todo por Python Diagrams — DESCARTADA.** Duplicaría la semántica ya validada, dejaría D4/D6/D8 sin sus construcciones específicas y haría Graphviz obligatorio.
2. **Mantener Mermaid para D1/D6/D7 — DESCARTADA como vía principal.** Son diagramas vivos de seguimiento y se benefician de foco, lens, validación y drill-down.
3. **Integrar el visor/WebApp de KubeDiagrams — DESCARTADA.** Duplicaría el portal y crearía otra experiencia de navegación.
4. **Routing híbrido con IR como contrato — ADOPTADA.** Conserva gobierno y añade cada herramienta solo donde aporta una capacidad diferencial.

## 4. Consecuencias

- Se añade `icono` opcional a nodos `flow`; los ID usan rutas canónicas como `aws.compute.ec2` o `k8s.compute.deploy`.
- Se añade el tipo semántico `integration` para D5; los IR anteriores permanecen válidos.
- La validación rechaza iconos mal formados/no resolubles y nodos/participantes con ID duplicados.
- `manifest_check.py` vigila las afirmaciones documentales sobre Draw.io y el generador IaC retirado.
- Los exports estáticos mediante Diagrams y el adaptador KubeDiagrams quedan explícitamente **planificados**, no se anuncian como disponibles en este incremento.

## 5. Criterios de éxito

1. La consulta `diagram_catalog.py route --diagrama D1..D8` devuelve una única fuente principal y sus apoyos.
2. Un IR con `icono` genera HTML autocontenido, sin URL externa, y pasa `check` con la caché versionada.
3. Un IR sin iconos conserva exactamente su ruta stdlib anterior.
4. La matriz, la referencia, las skills y la guía no contienen instrucciones vigentes contradictorias sobre Draw.io o `iac_to_diagram.py`.
5. La regresión completa del arnés permanece en verde.
