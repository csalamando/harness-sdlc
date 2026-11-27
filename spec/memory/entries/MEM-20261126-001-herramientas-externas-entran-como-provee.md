---
id: MEM-20261126-001
type: learning
project: harness-sdlc
created: 2026-11-26T21:49:17
session: SES-20261126-213157
tags: [arquitectura,diagramas,integracion,gobernanza]
links: [ADR-005,ADR-003,MEM-20260913-002]
supersedes: []
---
# Herramientas externas entran como proveedores detras del contrato, nunca como fuente paralela

**What**: Al integrar Python Diagrams (iconos) y evaluar KubeDiagrams (K8s) para el catalogo PLT-01, la tentacion era darles fuentes propias editables por diagrama. ADR-005 decidio routing por pregunta arquitectonica: el IR JSON sigue siendo la fuente gobernada unica por diagrama (D1-D3, D5-D8; D4 conserva Mermaid), y cada herramienta externa aporta solo una capacidad diferencial detras de ese contrato (iconos como cache local con lock SHA-256, K8s como futuro adaptador ->IR, nunca <-). Los recibos se emiten sobre la fuente, no sobre exports (HTML/PNG/PDF no reciben recibo propio).

**Why**: Fuentes paralelas editables (IR + Python + Mermaid para el mismo diagrama) son drift garantizado: dos artefactos que narran lo mismo y se desactualizan en silencio, exactamente el tipo de artefacto que el arnes prohibe. Ademas las dependencias externas (Graphviz, Diagrams, red) deben ser opcionales: validar/renderizar funciona sin ellas con la cache sincronizada (degradacion elegante, MEM-20260913-002).

**Where**: -

**Key details**: -

**Learned**: Toda integracion de herramienta externa se decide con tres preguntas: 1) cual es la fuente gobernada unica (una por diagrama/artefacto); 2) que capacidad diferencial aporta la herramienta y entra solo como proveedor detras del contrato; 3) sigue funcionando el arnes si la dependencia no esta instalada (cache/lock/degradacion). Aplicado en v2.34.0 a Diagrams y KubeDiagrams; reutilizable para cualquier futura integracion (Penpot MCP, wiki, etc).
