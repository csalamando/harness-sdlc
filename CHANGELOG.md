# Changelog

Todas las novedades relevantes del arnés se documentan aquí. Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y versionado [SemVer](https://semver.org/lang/es/).

**Regla de versionado del arnés:**
- **MAJOR** (x.0.0): cambios incompatibles en gates, recibos o formato de spec (rompen pipelines existentes).
- **MINOR** (2.x.0): skills nuevas, gates nuevos, features retrocompatibles.
- **PATCH** (2.1.x): correcciones en scripts, plantillas o documentación.

## [2.1.0] - 2026-08-20

### Added
- **`sdlc-solution-architect`** (Fases 0-2): el arquitecto de la iniciativa. Acompaña a negocio/PO/BA a detallar historias, escribe historias técnicas (`spec/technical-stories.md`: enablers, deuda, spikes, NFRs) y elabora la propuesta de arquitectura con opciones, ADRs preliminares y scorecard. Plantillas: `technical-story-template.md`, `architecture-proposal-template.md`.
- **`sdlc-cloud-pricing`** (Fases 0 y 6): estimación CAPEX/OPEX/TCO a 3 años en AWS y Azure, en 3 escenarios (mínimo viable / crecimiento esperado / pico), con supuestos versionados en YAML y fecha de validez de precios. Scripts: `cost_estimator.py`, `unit_prices.py`.
- **GATE 0** (aprobación de la iniciativa): gate humano previo a GATE 1 con tres tipos nuevos en `gate_checker.py` — `architecture-proposal`, `technical-stories`, `cost-estimation`. Los tres artefactos emiten recibo SHA-256.
- **Routing "discovery"**: iniciativa nueva o evolución de producto → PO + BA + Solution Architect + Cloud Pricing → GATE 0.
- Versionado formal del repo con releases: los 21 `.skill` se adjuntan como assets instalables en cada release.

### Changed
- `harness_doctor.py`: espera 21 skills.
- Pipeline: Fase 0 pasa a ser Discovery (PO + BA + Solution Architect + pricing).
- README: licencia con nombre completo del autor; crédito de Engram como "diferencial"; descripción precisa "arnés para agentes".

## [2.0.0] - 2026-08-13

### Added
- **`sdlc-decision-engine`**: framework de decisiones de 8 pasos (Natanzon) con `decision_engine.py` (validación + Decision Packages) y `scorecard_calculator.py`.
- **`sdlc-enterprise-architect`**: Tech Radar (ADOPT/TRIAL/ASSESS/HOLD), Principios Arquitectónicos, gobernanza por excepción, Paved Roads.
- **Risk Tiering** (`decision_sizing.py`): Tier 1/2/3 con gobernanza proporcional al riesgo.
- **Advice Process** (`advisor.py`): stakeholders por impacto; el consejo no es vinculante pero omitirlo bloquea GATE 1.
- **Firma arquitectónica** (`arch_signoff.py`): recibo `ARCH-xxx.json` con hash compuesto ADR + artefactos de diseño.
- `gate_checker.py --tipo adr`: validación semántica de los 8 pasos, Tech Radar y firma vigente.

## [1.1.0] - 2026-08-08

### Added
- **Receipts** (`receipt.py`): recibos SHA-256 emit/verify/status/revoke; invalidación automática al cambiar el artefacto.
- **Routing orgánico**: rutas directo / exploración delegada / hotfix / full-pipeline / change-request.
- **Fase 8 — Archivo**: merge de delta-specs, cierre del ciclo.
- `harness_doctor.py` (health check) y `detect_stack.py` (TDD en pausa sin test runner).
- Perfiles de modelo por fase (`references/model-profiles.md`).

## [1.0.0] - 2026-08-01

### Added
- Versión inicial: 15 skills de roles + `sdlc-memory` (Git-nativa, 3 scopes, políticas y desviaciones, MCP), pipeline Fases -1 a 7, gates 1/2/2.5/3, SDD + TDD.
