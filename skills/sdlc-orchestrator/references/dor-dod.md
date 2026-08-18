# Definition of Ready (DoR) y Definition of Done (DoD)

## DoR — para activar un rol

- [ ] Todas las entradas del rol existen en `spec/` y pasaron su gate
- [ ] El artefacto de entrada está en su versión aprobada (no hay cambios pendientes)
- [ ] El rol tiene su paquete de contexto (solo lo que necesita)

## DoD — checklist global de artefactos

- [ ] Usa la plantilla oficial del rol
- [ ] Referencia sus artefactos de entrada (trazabilidad hacia arriba)
- [ ] Checklist específico del rol cumplido (ver cada SKILL.md)
- [ ] Gate automático (`gate_checker.py`) en verde
- [ ] Versionado en el repo junto al código

## DoD de código (TDD)

- [ ] Tests escritos ANTES del código (verificable en historial de commits)
- [ ] Suite completa en verde
- [ ] Cobertura ≥ umbral del proyecto (definido en test-plan.md)
- [ ] Sin warnings de linter críticos
- [ ] Contract tests validados contra api-contract.yaml
