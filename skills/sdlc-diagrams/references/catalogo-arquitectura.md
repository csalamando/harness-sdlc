# Catálogo de diagramas de arquitectura — routing del arnés

<!-- GENERADO por diagram_catalog.py render; NO editar a mano. -->
<!-- Fuente: ../assets/catalogo-arquitectura.json -->

**Catálogo:** PLT-01 · **Versión del routing:** 1.0.0

> Una fuente gobernada por diagrama; toda imagen o documento generado es una vista derivada.

Esta referencia adapta la propuesta PLT-01 al arnés. Define la fuente y la herramienta; los atributos de contenido de la propuesta original siguen siendo exigibles por el rol dueño y la revisión del DAS.

## Decisión por diagrama

| # | Diagrama | Pregunta | Fuente principal | Vista / apoyo | Iconos Diagrams |
|---|---|---|---|---|---|
| D1 | Contexto de negocio y usuarios | ¿Quién usa esto y para qué existe? | IR `context` | diagram_ir.py → HTML interactivo; PNG/SVG derivado para la wiki | No |
| D2 | Contenedores y servicios (C4 N2) | ¿De qué piezas se compone y con qué stack? | IR `container` | diagram_ir.py → HTML interactivo con iconos; Diagrams opcional → PNG/SVG/PDF | Opcionales |
| D3 | Despliegue e infraestructura | ¿Dónde corre, en qué cuenta y a cargo de quién? | IR `deployment` | diagram_ir.py → HTML interactivo con iconos; Diagrams opcional → PNG/SVG/PDF | Opcionales |
| D4 | Flujos funcionales principales | ¿Cómo viaja la operación del usuario? | Mermaid | Renderer Mermaid de la wiki o diagram_render.py → SVG/PNG | No |
| D5 | Integración y mensajería | ¿Con qué sistemas habla, por qué protocolo y patrón? | IR `integration` | diagram_ir.py → HTML interactivo; matriz de integración como complemento | Opcionales |
| D6 | Flujo de datos (DFD) | ¿De dónde vienen los datos, a dónde van y cómo viajan protegidos? | IR `dataflow` | diagram_ir.py → HTML interactivo; tabla de clasificación y almacenes como complemento | No |
| D7 | Componentes internos (C4 N3) | ¿Cómo está armado por dentro el componente crítico? | IR `component` | diagram_ir.py → HTML interactivo con drill-down desde D2 | No |
| D8 | Seguridad y fronteras de confianza | ¿Dónde cruzan los datos zonas de distinta confianza y con qué controles? | IR `threat-model` | diagram_ir.py → HTML interactivo STRIDE; tabla de certificados/secretos sin valores como complemento | Opcionales |

## Fuentes y sintaxis

### D1 · Contexto de negocio y usuarios

- **Archivo/sintaxis:** `spec/diagrams/contexto.ir.json`
- **Por qué esta ruta:** C4 L1 exige un sistema central, actores y relaciones comprensibles por negocio; el foco y el detalle aportan más que iconos de productos.

### D2 · Contenedores y servicios (C4 N2)

- **Archivo/sintaxis:** `spec/diagrams/contenedores.ir.json`
- **Por qué esta ruta:** El IR conserva stack, protocolos, ubicación y drill-down; Diagrams aporta la iconografía cloud sin convertirse en otra fuente.

### D3 · Despliegue e infraestructura

- **Archivo/sintaxis:** `spec/diagrams/despliegue.ir.json`
- **Por qué esta ruta:** Los hulls anidados representan región→VPC→subnet y la ubicación es exigible; Kubernetes se importa sin reemplazar el diseño aprobado.
- **Adaptador kubernetes:** KubeDiagrams → IR deployment (planificado: manifiestos/Helm/Kustomize offline; clúster solo opt-in)

### D4 · Flujos funcionales principales

- **Archivo/sintaxis:** `sequenceDiagram embebido en la spec/wiki`
- **Por qué esta ruta:** Mermaid sequenceDiagram expresa mejor autonumber, notas, bloques de error y compensación; el IR sequence queda para secuencias simples que necesiten foco/lens.

### D5 · Integración y mensajería

- **Archivo/sintaxis:** `spec/diagrams/integracion.ir.json`
- **Por qué esta ruta:** Cada arista conserva protocolo, patrón, path BIAN y referencia C2 en datos estructurados; el foco permite explorar una integración sin saturar el mapa.

### D6 · Flujo de datos (DFD)

- **Archivo/sintaxis:** `spec/diagrams/flujo-datos.ir.json`
- **Por qué esta ruta:** La clasificación, minimización, modo, protocolo y cifrado son semántica gobernada, no decoración; el lens permite aislar fuentes, transformaciones y destinos.

### D7 · Componentes internos (C4 N3)

- **Archivo/sintaxis:** `spec/diagrams/componente-<nombre>.ir.json`
- **Por qué esta ruta:** El boundary del contenedor y el enlace ↗ entre niveles mantienen la navegación C4; solo se documentan componentes críticos justificados.

### D8 · Seguridad y fronteras de confianza

- **Archivo/sintaxis:** `spec/diagrams/seguridad-fronteras.ir.json`
- **Por qué esta ruta:** Trust boundaries, límites por rank y amenazas STRIDE ya tienen validación; los iconos son opcionales y nunca sustituyen los controles.

## Reglas comunes

1. **Draw.io permanece retirado.** No es una salida vigente del arnés.
2. **Una fuente por diagrama.** Las imágenes y esta referencia se derivan; no se mantiene una copia equivalente en otro lenguaje.
3. **IR interactivo:** conserva foco, lens, detalle, insights, validación, diff y recibos. Archify es inspiración de interacción, no dependencia.
4. **Mermaid en D4:** conservar `sequenceDiagram` para flujos con notas, error o compensación; en Azure DevOps 8.13.9 usar la valla `::: mermaid`, `graph` en flowcharts y sin comentario inicial.
5. **Diagrams:** sus iconos se sincronizan a `spec/diagrams/icons/` y se incrustan en HTML sin red. El backend de exports estáticos es opcional y está planificado.
6. **KubeDiagrams:** adaptador D3 planificado para entradas offline. El estado de un clúster solo se incorporará con opt-in, minimización y sanitización.
7. **Contenido mínimo:** nombres reales, ficha INI/ambiente/fecha/responsable y tablas complementarias se gobiernan en el DAS; ningún icono sustituye protocolos, clasificación, controles o responsables.
8. **Complementos, no fuentes ocultas:** una tabla complementaria debe derivarse del mismo IR o llevar referencia explícita a su fuente gobernada.

## Consulta y anti-drift

```bash
python diagram_catalog.py list
python diagram_catalog.py route --diagrama D3 --kubernetes
python diagram_catalog.py check
```

Decisión arquitectónica: `docs/decisions/ADR-005-routing-hibrido-diagramas.md`.
