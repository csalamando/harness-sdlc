# BPMN 2.0 en drawio (XML nativo)

draw.io tiene librería BPMN 2.0 completa (General, Events, Gateways, Activities...). Ruta nativa: los pools/lanes y gateways necesitan control de layout que Mermaid no da.

## Cuándo lo usa el arnés

Business Analyst (Fase 1) para procesos de negocio que trascienden una sola HU: aprobaciones multi-rol, procesos con intervención manual, integraciones con actores externos. Complementa, no reemplaza, los Gherkin.

## Shapes principales (resolver variantes con `search_shapes "bpmn <nombre>"`)

| Elemento | Style base |
|---|---|
| Pool | `shape=table;childLayout=poolLayout;horizontal=1;startSize=30;fillColor=none;container=1;collapsible=0;html=1;` |
| Lane | `shape=swimlane;horizontal=1;startSize=30;fillColor=none;container=1;collapsible=0;html=1;` |
| Tarea | `rounded=1;whiteSpace=wrap;html=1;arcSize=10;fillColor=#ffffff;strokeColor=#000000;` |
| Evento inicio (círculo fino) | `ellipse;html=1;shape=startEvent;outline=standard;` o genérico: `ellipse;whiteSpace=wrap;html=1;aspect=fixed;strokeWidth=1.5;` |
| Evento fin (círculo grueso) | `ellipse;whiteSpace=wrap;html=1;aspect=fixed;strokeWidth=4;` |
| Evento intermedio (doble círculo) | `ellipse;whiteSpace=wrap;html=1;aspect=fixed;strokeWidth=1.5;double=1;` |
| Gateway exclusivo (X) | `shape=mxgraph.bpmn.gateway;html=1;verticalAlign=top;align=center;perimeter=rhombusPerimeter;background=mxgraph.bpmn.gateway_exclusive;outlineConnect=0;` (o `rhombus;whiteSpace=wrap;html=1;` con label `X`) |
| Gateway paralelo (+) | igual con `background=mxgraph.bpmn.gateway_parallel` |
| Subproceso | tarea + `outline=standard;symbol=plus` (resolver con search_shapes) |
| Sequence flow | `edgeStyle=orthogonalEdgeStyle;html=1;endArrow=block;endFill=1;` (línea sólida) |
| Message flow | igual + `dashed=1;startArrow=oval;endArrow=open;` entre pools distintos |
| Data object / annotation | shapes BPMN de la librería (search_shapes) |

## Convenciones del arnés

1. Un pool por actor organizacional (Cliente, Sistema, Proveedor externo); lanes para roles internos.
2. Flujo de izquierda a derecha; gateways con etiqueta de pregunta (`¿Pago aprobado?`) y salidas etiquetadas (`sí`/`no`).
3. Tareas en verbo+objeto (`Validar identidad`, no `Validación`).
4. Toda tarea que ejecuta el sistema referencia su HU: `Validar identidad [HU-004]`.
5. Eventos de borde (timeout, error) como eventos intermedios de borde cuando el proceso debe modelarlos — enlazan con los estados de error del UX Designer.
6. El `.drawio` se guarda en `spec/diagrams/bpmn-<proceso>.drawio`; si el BA ya modeló en Bizagi, exportar BPMN 2.0 XML de Bizagi y **importar** en draw.io (Archivo → Importar) en vez de redibujar.

## Ejemplo mínimo (pool + inicio → tarea → gateway → fines)

```xml
<mxCell id="pool" value="Proceso de onboarding" style="shape=table;childLayout=poolLayout;horizontal=1;startSize=30;fillColor=none;container=1;collapsible=0;html=1;" vertex="1" parent="1">
  <mxGeometry x="40" y="80" width="880" height="240" as="geometry"/>
</mxCell>
<mxCell id="start" value="" style="ellipse;whiteSpace=wrap;html=1;aspect=fixed;strokeWidth=1.5;" vertex="1" parent="pool">
  <mxGeometry x="60" y="100" width="32" height="32" as="geometry"/>
</mxCell>
<mxCell id="t1" value="Registrar solicitud&#10;[HU-001]" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;fillColor=#ffffff;strokeColor=#000000;" vertex="1" parent="pool">
  <mxGeometry x="140" y="90" width="120" height="60" as="geometry"/>
</mxCell>
<mxCell id="g1" value="" style="rhombus;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#000000;" vertex="1" parent="pool">
  <mxGeometry x="320" y="92" width="50" height="50" as="geometry"/>
</mxCell>
<!-- edges start->t1->g1->... con value "sí"/"no" en las salidas del gateway -->
```
