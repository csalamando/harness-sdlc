# Estilos C4 y cloud para drawio XML

Referencia de style strings para generar XML válido. **Regla de oro: antes de usar un icono no listado aquí, resolverlo con `search_shapes`** y copiar el style exacto que devuelve.

## Estructura mínima de un .drawio

```xml
<mxfile host="app.diagrams.net" agent="sdlc-diagrams-c4" version="24.0.0">
  <diagram id="c4-container" name="C4-Container">
    <mxGraphModel dx="800" dy="600" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1169" pageHeight="827" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <!-- nodos y edges aquí -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

Vértice: `<mxCell id="n1" value="Nombre" style="..." vertex="1" parent="1"><mxGeometry x="40" y="40" width="160" height="90" as="geometry"/></mxCell>`
Edge: `<mxCell id="e1" style="..." edge="1" parent="1" source="n1" target="n2"><mxGeometry relative="1" as="geometry"/></mxCell>`

## Paleta C4 (colores oficiales del modelo)

| Elemento | fillColor | fontColor |
|---|---|---|
| Person | #08427B | #ffffff |
| Software System (propio) | #1168BD | #ffffff |
| Software System (externo) | #999999 | #ffffff |
| Container | #438DD5 | #ffffff |
| Component | #85BBF0 | #000000 |
| Boundary (grupo) | sin fill, stroke #444444 dashed | #444444 |

### Person

```
rounded=1;whiteSpace=wrap;html=1;fillColor=#08427B;strokeColor=#052E56;fontColor=#ffffff;arcSize=30;verticalAlign=bottom;labelPosition=center;verticalLabelPosition=bottom;align=center;spacingTop=6;
```
(Variante oficial de la librería C4: `shape=mxgraph.c4.person2` con `metaEdit=1` — resolver con `search_shapes "c4 person"` si está disponible.)

### Software System / Container / Component

Mismo rectángulo redondeado cambiando fillColor; la convención C4 pone **nombre, [tecnología] y descripción** en el label con saltos HTML:

```
value="<b>API Gateway</b><br>[Azure API Management]<br><br>Enruta, autentica y limita las llamadas de los clientes"
style="rounded=1;whiteSpace=wrap;html=1;fillColor=#438DD5;strokeColor=#2E6295;fontColor=#ffffff;arcSize=6;fontSize=12;verticalAlign=middle;align=center;"
```

### Boundary (System/Container boundary)

```
rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#444444;dashed=1;fontColor=#444444;align=left;verticalAlign=top;spacingLeft=8;fontSize=12;container=1;collapsible=0;
```
El boundary es `container=1`: los hijos llevan `parent="<idBoundary>"` y coordenadas relativas.

### Relación C4 (edge con protocolo)

```
edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;jettySize=auto;strokeColor=#444444;fontSize=11;align=center;verticalAlign=middle;endArrow=block;endFill=1;
value="Consume API<br>[HTTPS/JSON]"
```

## Iconos AWS (librería mxgraph.aws4)

Patrón general:

```
sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;fillColor=#D05C17;strokeColor=none;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=11;fontStyle=0;aspect=fixed;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.lambda;
```

Cambiar `resIcon` y `fillColor` por categoría:

| Servicio | resIcon | fillColor (grupo) |
|---|---|---|
| Lambda | mxgraph.aws4.lambda | #ED7100 |
| EC2 / ECS / EKS | mxgraph.aws4.ec2 / .ecs / .eks | #ED7100 |
| S3 | mxgraph.aws4.s3 | #569A31 (usa `resIcon=mxgraph.aws4.s3` con shape resourceIcon y fillColor=#569A31) |
| RDS / DynamoDB | mxgraph.aws4.rds / .dynamodb | #C925D1 |
| API Gateway | mxgraph.aws4.api_gateway | #8C4FFF |
| SQS / SNS / EventBridge | mxgraph.aws4.sqs / .sns / .eventbridge | #E7157B |
| VPC / CloudFront / Route53 | mxgraph.aws4.vpc / .cloudfront / .route_53 | #8C4FFF |
| Cognito / IAM | mxgraph.aws4.cognito / .identity_and_access_management | #DD344C |

Grupo VPC (boundary): `fillColor=none;strokeColor=#248814;gradientColor=none;dashed=0;html=1;shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_vpc2;strokeColor=#248814;verticalAlign=top;align=left;spacingLeft=8;fontColor=#AAB7B8;container=1;collapsible=0;`

## Iconos Azure (librería azure2, rutas img/lib)

Patrón general (imagen + etiqueta debajo):

```
aspect=fixed;html=1;points=[];align=center;image;fontSize=11;image=img/lib/azure2/compute/Function_Apps.svg;verticalLabelPosition=bottom;verticalAlign=top;whiteSpace=wrap;
```

| Servicio | image |
|---|---|
| Azure Functions | img/lib/azure2/compute/Function_Apps.svg |
| App Service | img/lib/azure2/compute/App_Services.svg |
| AKS | img/lib/azure2/compute/Kubernetes_Services.svg |
| Azure SQL | img/lib/azure2/databases/SQL_Server.svg |
| Cosmos DB | img/lib/azure2/databases/Cosmos_Db.svg |
| Storage Account | img/lib/azure2/storage/Storage_Accounts.svg |
| Service Bus | img/lib/azure2/integration/Service_Bus.svg |
| API Management | img/lib/azure2/integration/API_Management_Services.svg |
| Key Vault | img/lib/azure2/security/Key_Vaults.svg |
| Application Insights | img/lib/azure2/monitor/Application_Insights.svg |
| Entra ID | img/lib/azure2/identity/Entra_ID.svg |
| VNet | img/lib/azure2/networking/Virtual_Networks.svg |

> Las rutas azure2 cambian entre versiones de draw.io — si un icono no renderiza, `search_shapes "azure <servicio>"` y usar el style devuelto.

## Iconos GCP

```
shape=mxgraph.gcp2.<servicio>;fillColor=#4284F3;html=1;verticalLabelPosition=bottom;align=center;
```
Ej.: `mxgraph.gcp2.cloud_functions`, `mxgraph.gcp2.cloud_sql`, `mxgraph.gcp2.gke`. Resolver con `search_shapes "gcp <servicio>"`.

## Reglas de layout

- Grid de 10px; containers en filas lógicas (clientes arriba, edge/gateway, servicios, datos abajo).
- Máximo ~12 nodos por página; más nodos ⇒ nueva página (multipágina = niveles C4).
- Boundaries con título arriba-izquierda; nodos dentro con `parent` al boundary.
- Edges ortogonales con etiqueta de protocolo; evitar cruces (usar `routing=libavoid` del tool server si el diagrama se densifica).
- Siempre incluir una leyenda pequeña (qué significa cada color) en la esquina inferior derecha.
