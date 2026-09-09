# Arquitectura

Versión: 0.1 | Fuente: user-stories.md, business-rules.md v<x>

## Estilo y decisiones macro
<monolito modular / microservicios / serverless + justificación breve>

## Diagrama de contenedores (C4)

Diagrama vivo IR — **obligatorio** (v2.21): [`diagrams/architecture-c4.ir.json`](diagrams/architecture-c4.ir.json)

- Edita SOLO el IR; el HTML interactivo se regenera con `diagram_ir.py render --ir spec/diagrams/architecture-c4.ir.json --out spec/diagrams/architecture-c4.html`.
- Todo nodo declara `ubicacion` (dónde corre: nube/región/on-prem) — `diagram_ir.py validate` lo exige en diagramas `"tipo": "architecture"`.
- Antes de emitir el recibo de esta arquitectura, el IR debe tener **recibo vigente** propio: `receipt.py emit spec/diagrams/architecture-c4.ir.json --gate FASE-2 --role software-architect`.
- Mermaid inline es opcional y complementario; no sustituye al IR.

## Componentes y responsabilidades
| Componente | Responsabilidad | Reglas de negocio dueñas |
|---|---|---|

## Requisitos no funcionales
| NFR | Meta cuantificada | Cómo se verifica |
|---|---|---|
| Latencia | p95 < 300ms | k6 en GATE 2 |
| Disponibilidad | 99.9% | SLO del SRE |

## Riesgos técnicos
| Riesgo | Mitigación |
|---|---|
