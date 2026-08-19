---
name: sdlc-decision-engine
description: "Motor de decisiones arquitectónicas del arnés SDLC basado en el framework de 8 pasos de Sonya Natanzon. Usar en Fase 2 junto al Arquitecto de Software para toda decisión técnica significativa: problem statement sin soluciones prematuras, last responsible moment, criterios ponderados, opciones, advice process, scorecard cuantitativa, decisión y re-evaluation triggers. Soporta Decision Packages pre-aprobados (assets/decision-packages/) y Paved Roads del Tech Radar. Dispara ante: decisión arquitectónica, ADR, scorecard, trade-off analysis, decision package, build vs buy, selección de tecnología."
---

# Decision Engine — Framework de 8 Pasos (Natanzon)

Motor transversal que guía al Arquitecto de Software por un proceso riguroso de decisión, evitando sesgos cognitivos y solucionismo prematuro. Lo invoca `sdlc-software-architect` (o el orquestador) para cada decisión significativa; las decisiones triviales (bajo costo de reversa Y bajas consecuencias) se documentan en `sdlc-memory` y se avanza sin el proceso completo.

## Pre-Check: ¿amerita el proceso completo?

Evalúa: (1) costo de reversa en 6 meses, (2) consecuencias si falla. Si ambas son bajas → memoria tipo `decision` y continuar. Si alguna es alta → 8 pasos completos. El nivel de gobernanza lo fija `decision_sizing.py` (Risk Tier 1/2/3) en el orquestador.

## Los 8 pasos

1. **Problem Statement**: describir el problema real SIN mencionar tecnologías, frameworks ni soluciones. Anti-patrón: "Necesitamos usar Kafka". Correcto: "Necesitamos desacoplar la ingesta de eventos de alto volumen para que los picos no degraden la experiencia del usuario". `gate_checker.py --check problem-statement` rechaza statements con nombres de tecnología.
2. **Last Responsible Moment**: fecha límite real, restricciones (presupuesto, headcount, ventanas regulatorias, dependencias externas) y costo de reversa.
3. **Criterios de evaluación**: definir ANTES de ver opciones. Mínimo 3 criterios, cada uno con peso, métrica y umbral mínimo; los pesos deben sumar 100%. Si existe un Decision Package aplicable, cargar sus criterios: se pueden ajustar pesos pero no eliminar criterios.
4. **Opciones de solución**: mínimo 2, idealmente 3; al menos una radicalmente diferente (ej. relacional vs NoSQL vs servicio gestionado). Marcar como **Paved Road** las opciones que usan tecnología ADOPT del Tech Radar.
5. **Advice Process**: ejecutar `advisor.py` para identificar stakeholders según impacto. Registrar en el Advice Log del ADR: quién aconsejó, cuándo, qué aconsejó, si se aplicó y por qué. El consejo NO es vinculante; la omisión de la consulta SÍ bloquea el gate.
6. **Trade-off analysis (scorecard)**: `scorecard_calculator.py` pondera criterios × opciones. La opción elegida debe tener el mayor puntaje o una justificación explícita (ej. requisito regulatorio no negociable).
7. **Decisión**: declaración en una frase, razones principales, consecuencias positivas esperadas, consecuencias negativas aceptadas y qué NO se decidió.
8. **Re-evaluation triggers**: condiciones que obligan a revisar (umbrales de volumen, EOL de tecnología, cambios regulatorios, fecha de revisión programada).

## Scripts

```bash
# Validar un ADR contra los 8 pasos (estructura, pesos, advice log)
python3 scripts/decision_engine.py --validate --adr spec/adr/ADR-001.md

# Inyectar criterios/paved roads/constraints de un package en el ADR
python3 scripts/decision_engine.py --load-package pkg-database-selection --adr spec/adr/ADR-001.md

# Calcular la scorecard ponderada y verificar la opción ganadora
python3 scripts/scorecard_calculator.py --adr spec/adr/ADR-001.md
```

## Decision Packages

Configuraciones pre-aprobadas para decisiones recurrentes, en `assets/decision-packages/` (ejemplos: `pkg-auth.yaml`, `pkg-database-selection.yaml`). Estructura:

```yaml
name: pkg-auth
description: "Decisión de mecanismo de autenticación para APIs"
version: "1.0"
risk_tier_min: 1
criteria:
  - name: "Seguridad"
    weight: 40
    metric: "Cumplimiento OAuth2/OIDC, MFA"
    threshold: "100%"
paved_roads:
  - technology: "Proveedor OIDC gestionado"
    quadrant: "ADOPT"
    pre_approved: true
constraints:
  - "MFA obligatorio para operaciones sensibles"
required_advice:
  - "Security Engineer"
```

El Enterprise Architect mantiene los packages alineados con el Tech Radar; los equipos pueden proponer nuevos packages vía el flujo normal de cambio de spec.

## Integración

- El resultado se redacta con la plantilla `sdlc-software-architect/assets/adr-template-8steps.md`.
- Al completarse y cerrarse el Advice Process, el Arquitecto firma con `arch_signoff.py` (recibo `ARCH-xxx.json` en `spec/receipts/`). Un ADR firmado no se modifica: se supersedea con uno nuevo.
- GATE 1 exige ADR validado (`--validate`) + firma vigente + `policy check` en verde.
