---
name: sdlc-cloud-pricing
description: "Estimador de costos cloud del arnés SDLC (AWS y Azure). Usar desde Fase 0 (con sdlc-solution-architect, para el caso de negocio y GATE 0) y en Fase 6 (con sdlc-cloud-engineer, estimación fina de staging/prod). Genera spec/cost-estimation.md con CAPEX (construcción/migración), OPEX mensual/anual por escenario (mínimo viable / crecimiento esperado / pico) y TCO, con supuestos explícitos y fecha de validez de precios. El costo alimenta como criterio ponderado las scorecards del sdlc-decision-engine. Dispara ante: pricing cloud, estimación de costos, CAPEX, OPEX, TCO, caso de negocio cloud, cuánto cuesta en AWS/Azure, comparativa de costos entre nubes."
---


# Cloud Pricing — estimación CAPEX/OPEX para el caso de negocio

El costo es una **decisión de arquitectura**: una opción técnicamente superior que quiebra el caso de negocio no es viable. Esta skill produce estimaciones **defendibles ante negocio**: supuestos explícitos, escenarios, validez de precios y recibo verificable.

## Principios

1. **Nunca un número solo**: toda estimación se entrega en 3 escenarios (mínimo viable / crecimiento esperado / pico). Un único número es una promesa falsa.
2. **Supuestos antes que precios**: los precios unitarios cambian; los supuestos (usuarios, RPS, GB, horas) son la parte auditable y reutilizable.
3. **CAPEX y OPEX por separado**: negocio los evalúa distinto (inversión vs. operación).
4. **Validez explícita**: toda estimación declara fecha y fuente de precios; vencida, se re-estima.
5. **Los precios de lista son un punto de partida**: verificar contra la calculadora oficial (AWS Pricing Calculator / Azure Pricing Calculator) antes de presentar a negocio, y registrar la URL/fecha de verificación.

## Flujo

### 1. Definir supuestos (`assets/assumptions-template.yaml`)

Copiar la plantilla a `spec/cost-assumptions.yaml` y llenarla por opción arquitectónica: usuarios activos, RPS promedio/pico, datos almacenados y su crecimiento, transferencia de red, ambientes (dev/staging/prod), horas de ingeniería para CAPEX.

### 2. Calcular

```bash
python3 scripts/cost_estimator.py --assumptions spec/cost-assumptions.yaml \
    --clouds aws,azure --out spec/cost-estimation.md
```

El script:
- Compone el OPEX mensual por servicio (cómputo, base de datos, almacenamiento, red, otros) usando la tabla de precios unitarios de referencia (`scripts/unit_prices.py`), por escenario.
- Calcula CAPEX = horas de ingeniería × tarifa + costos one-time (migración, setup).
- Proyecta **TCO a 3 años** = CAPEX + 36 × OPEX esperado.
- Escribe `spec/cost-estimation.md` con tabla comparativa por nube y escenario, supuestos usados y fecha de validez.

Para precios reales actualizados, sobreescribir cualquier precio unitario en el YAML de supuestos (`overrides:`) tras consultar la calculadora oficial — el script registra qué precios fueron sobreescritos.

### 3. Integrar

- **Fase 0 (Solution Architect)**: resumen CAPEX/OPEX/TCO por opción → sección 5 de `spec/architecture-proposal.md`; costo como criterio ponderado en la scorecard; GATE 0 exige el artefacto:

```bash
python3 gate_checker.py spec/cost-estimation.md --tipo cost-estimation
python3 receipt.py emit --artifact spec/cost-estimation.md --gate GATE-0
```

- **Fase 6 (Cloud Engineer)**: re-ejecutar con supuestos finos (instancias concretas, reservas/Savings Plans, multi-AZ) para validar que staging/prod caben en el OPEX aprobado; desviación > 20% → change-request.

## Checklist de salida (DoD)

- [ ] Supuestos en YAML versionado, con fuente de cada cifra de negocio
- [ ] OPEX en 3 escenarios × nube considerada (AWS y/o Azure)
- [ ] CAPEX separado (ingeniería + one-time)
- [ ] TCO 3 años por opción
- [ ] Fecha de validez y precios sobreescritos registrados
- [ ] Recibo emitido (GATE 0 o Fase 6)
