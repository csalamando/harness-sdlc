# Propuesta de Arquitectura — <nombre de la iniciativa>

- **Fecha**: YYYY-MM-DD
- **Autor**: Solution Architect
- **Estado**: Borrador | En revisión | Aprobada (GATE 0)
- **Gate**: GATE 0 — requiere recibo `receipt.py emit --gate GATE-0`

## 1. Contexto y objetivo de negocio

<2-3 párrafos sin jerga: qué problema de negocio resuelve, por qué ahora, qué pasa si no se hace>

## 2. Restricciones

- Presupuesto: <techo CAPEX / OPEX mensual>
- Fecha objetivo: <...>
- Cumplimiento: <PII, regulatorio, residencia de datos>
- Nubes consideradas: AWS | Azure
- Tech Radar / Principios aplicables: <ADOPT relevantes, mandatory principles>

## 3. Opciones de arquitectura

### Opción A: <nombre>

- Diagrama: `spec/diagrams/proposal-opcion-a.drawio`
- Componentes: <...>
- Integraciones: <...>
- ADRs preliminares: ADR-P-001 <decisión de dirección>, ADR-P-002 <...>

### Opción B: <nombre>

- Diagrama: `spec/diagrams/proposal-opcion-b.drawio`
- Componentes: <...>
- Integraciones: <...>
- ADRs preliminares: ADR-P-003 <...>

## 4. Comparativa

| Criterio | Peso | Opción A | Opción B |
|---|---|---|---|
| Time-to-market | __% | | |
| Costo CAPEX | __% | ver §5 | ver §5 |
| Costo OPEX (anual) | __% | ver §5 | ver §5 |
| Riesgo técnico | __% | | |
| Reversibilidad | __% | | |
| Alineación Tech Radar | __% | | |
| **Total ponderado** | 100% | | |

> Verificar con `scorecard_calculator.py`. Los pesos suman 100%. Costo es criterio obligatorio.

## 5. Estimación de costos

Resumen integrado desde `spec/cost-estimation.md` (generado con `sdlc-cloud-pricing`):

| Opción | Nube | CAPEX | OPEX mensual (mín / esperado / pico) | TCO 3 años |
|---|---|---|---|---|
| A | | | | |
| B | | | | |

## 6. Recomendación

<opción recomendada + justificación referenciando la scorecard y el caso de negocio>

## 7. Supuestos y riesgos

| Supuesto/Riesgo | Impacto si falla | Trigger de re-evaluación |
|---|---|---|
| | | |

## 8. Aprobación (GATE 0)

- [ ] Propuesta con ≥2 opciones y comparativa cuantitativa
- [ ] Estimación de costos vigente (fecha de validez de precios)
- [ ] Aprobación de negocio: ______________  Fecha: ______
- [ ] Recibo GATE 0 emitido
