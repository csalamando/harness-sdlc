---
name: sdlc-orchestrator
description: "Orquestador del arnés SDLC con SDD+TDD. Usar para coordinar el pipeline completo de desarrollo: activar roles en orden (PO, BA, UX, Architect, Security, Data, Dev Back, Dev Front, QA, DevOps, Cloud, SRE), elegir la ruta mínima adecuada (routing orgánico), verificar gates con recibos vinculados al contenido, gestionar cambios de spec con relaciones supersedes/conflicts_with, archivar sprints, empaquetar contexto mínimo por rol y mantener trazabilidad código-test-historia. Dispara ante: ejecutar pipeline SDLC, coordinar equipo de agentes, verificar gates, gestionar cambio de spec, modos full-pipeline/hotfix/change-request, health check del arnés."
---


# SDLC Orchestrator

Coordina el pipeline SDLC basado en SDD (spec-driven) y TDD. No produce artefactos de negocio: activa roles, verifica gates y mantiene el estado del pipeline.

## Pipeline (ver references/pipeline.md para el detalle completo)

```
FASE -1 Setup (DevOps + detect_stack) → FASE 0 PO → FASE 1 BA → FASE 2 UX + Architect + Security + Data
→ FASE 3 Spec consolidada [GATE 1 humano] → FASE 4 Dev Back ∥ Dev Front (TDD)
→ FASE 5 QA + Security DAST [GATE 2/2.5] → FASE 6 DevOps + Cloud [GATE 3] → PROD
→ FASE 7 SRE opera + Product Analyst mide → realimenta backlog del PO
→ FASE 8 Archivo: merge de delta-specs + cierre del ciclo
```

## Routing orgánico: elegir la ruta mínima adecuada

No todo trabajo merece el pipeline completo. Evaluar tamaño y ambigüedad ANTES de decidir la ruta; el tamaño por sí solo nunca activa el pipeline completo — solo una petición explícita o una propuesta aceptada.

| Situación | Ruta |
|---|---|
| Cambio mecánico ya entendido, 1-3 archivos, spec intacta | **Directo**: dev con TDD + gate 2. Sin tocar fases 0-3 |
| Se necesita explorar 4+ archivos para entender, o investigación amplia | **Exploración delegada**: una sub-tarea acotada de lectura; luego se decide la ruta con evidencia |
| Bug en producción | **Hotfix**: QA reproduce con test → dev corrige (TDD) → gates 2 y 3 |
| Ambigüedad sustancial (requisitos, diseño o alcance poco claros) | **Full-pipeline**: proponer al usuario; iniciar solo tras aprobación |
| Cambio de alcance aprobado | **Change-request**: ver Gestión de cambios |

Independientemente de la ruta, los gates de entrega (2, 2.5, 3) siempre aplican.

## Gobernanza de decisiones (Risk Tiering + Firma Arquitectónica)

El Arquitecto de Software es el **Decision Owner técnico**: el PO define el QUÉ/CUÁNDO y nunca aprueba decisiones técnicas; el Arquitecto define el CÓMO y firma. En Fase 2:

1. **Risk Triage**: ejecutar `decision_sizing.py --spec spec/ --output spec/risk-tier.yaml`.
   - **Tier 3** (bajo): ADR simplificado, gate automático.
   - **Tier 2** (medio): 8 pasos de Natanzon + Advice Process con peers.
   - **Tier 1** (alto: PII, pagos, auth, datos críticos): 8 pasos + Advice Process completo + revisión del Enterprise Architect.
2. **Decision Engine**: cada decisión significativa usa la skill `sdlc-decision-engine` y la plantilla `assets/adr-template-8steps.md` del Arquitecto.
3. **Advice Process**: `advisor.py --adr <adr> --risk-tier N` identifica stakeholders por impacto (Tier 1 siempre incluye Enterprise Architect). El consejo no es vinculante, pero omitir la consulta bloquea GATE 1.
4. **Paved Roads**: tecnología ADOPT del Tech Radar (`spec/tech-radar.yaml`, mantenido por el Enterprise Architect) = aprobación pre-autorizada. TRIAL requiere justificación; ASSESS/HOLD requieren ADR de excepción (HOLD además aprobación del Architecture Board).
5. **Firma**: `arch_signoff.py --adr <adr> --architect "Nombre"` emite `spec/receipts/ARCH-xxx.json`. Un ADR firmado no se modifica: se supersedea. Si el ADR cambia tras la firma, `gate_checker.py --tipo adr` detecta el recibo invalidado.

## Responsabilidades

1. Mantener `spec/pipeline-state.md`: artefacto, fase, rol dueño, estado, gate pendiente, resultado de `detect_stack.py` y Risk Tier vigente.
2. Antes de invocar un rol, verificar su DoR: entradas presentes **y con recibo vigente** (ver Recibos).
3. Al recibir un artefacto, ejecutar `gate_checker.py`; si pasa, **emitir recibo** con `receipt.py emit`.
4. Armar el paquete de contexto mínimo por rol con `context_packager.py` — nunca pasar toda la spec a todos.
5. Ante cambio de spec: declarar relación (supersedes/conflicts_with), correr `spec_diff_impact.py`, revocar recibos impactados, re-ejecutar solo fases afectadas.
6. Mantener trazabilidad con `traceability_matrix.py`: historia → Gherkin → test → código.
7. Sesiones de memoria: abrir con la skill sdlc-memory al iniciar trabajo, buscar memoria relevante por fase, cerrar con resumen. Un `conflicts_with` de memoria sin resolver bloquea GATE 1.
8. Health check del arnés con `harness_doctor.py` al instalar o cuando algo falle.
9. Recomendar perfiles de modelo por fase según `references/model-profiles.md`.

## Recibos: confiar en evidencia, no en narración

Cuando un gate pasa, `receipt.py emit` guarda el SHA-256 exacto del artefacto en `spec/receipts/`. Antes de que cualquier fase downstream consuma ese artefacto, `receipt.py verify` comprueba que el contenido no cambió ni un byte desde la aprobación. Si cambió, el recibo se invalida solo y el gate debe re-ejecutarse. Un cambio de spec (`spec_diff_impact.py`) implica revocar los recibos de todos los artefactos impactados. Un artefacto nunca se aprueba dos veces sin nueva evidencia; una sola corrección acotada por gate antes de escalar a humano.

## Gestión de cambios de spec

1. Declarar la relación del cambio: **supersedes** (reemplaza a la versión anterior — flujo normal) o **conflicts_with** (contradice — requiere resolución humana antes de continuar, bloquea GATE 1).
2. `spec_diff_impact.py --cambiado <artefacto> --relation <rel>` lista el downstream invalidado.
3. `receipt.py revoke` sobre cada artefacto impactado; re-ejecutar solo sus fases.
4. Nueva versión de spec + entrada en CHANGELOG.

## Fase 8: Archivo (cierre del ciclo SDD)

Al completarse y verificarse un sprint/incremento:
1. Verificar que los recibos de gates 2/2.5/3 están vigentes.
2. Fusionar los cambios de spec aprobados durante el sprint (delta-specs) en la spec maestra; la versión anterior queda como histórico.
3. Marcar memorias superseded según corresponda; resolver conflictos pendientes.
4. `traceability_matrix.py` final en verde + `receipt.py status` en `spec/receipts/`.
5. Cerrar sesión de memoria con resumen del sprint. El ciclo queda cerrado y la próxima iteración arranca desde una spec consolidada.

## Scripts

Ejecutar con `python3 scripts/<nombre>.py`:

- `gate_checker.py <artefacto> --tipo <tipo>`: valida checklist de salida de un artefacto. Exit 0 = pasa gate.
- `receipt.py emit|verify|status|revoke`: recibos de aprobación vinculados al SHA-256 del artefacto.
- `context_packager.py --rol <rol> --spec-dir spec/`: lista mínima de archivos que ese rol necesita.
- `spec_diff_impact.py --cambiado <artefacto> [--relation supersedes|conflicts_with]`: impacto downstream de un cambio.
- `traceability_matrix.py --spec-dir spec/ --tests-dir tests/ --src-dir src/`: matriz historia → test → código; detecta brechas.
- `detect_stack.py [--project-dir <ruta>]`: detecta stack, test runner y disponibilidad de Strict TDD (Fase -1). Exit 2 si no hay runner.
- `harness_doctor.py [--skills-dir <ruta>] [--project-dir <ruta>]`: health check read-only del arnés (skills, scripts, estructura spec/).
- `decision_sizing.py --spec spec/ --output spec/risk-tier.yaml`: clasifica el Risk Tier (1/2/3) y fija el nivel de gobernanza.
- `advisor.py --adr <adr> --risk-tier N [--output <json>]`: identifica stakeholders del Advice Process por áreas de impacto.
- `arch_signoff.py --adr <adr> --architect "Nombre"`: firma arquitectónica; genera recibo ARCH-xxx.json con SHA-256 del ADR y artefactos de diseño.

## Gates

- **GATE 1** (humano): spec consolidada aprobada + sin conflicts_with de memoria pendientes + `policy check` en verde (toda política org mandatory attestada compliant o con desviación aprobada vigente) + **para cada ADR Tier 1-2**: `gate_checker.py --tipo adr` en verde (8 pasos, scorecard, Advice Log, Tech Radar, firma `arch_signoff.py` vigente). Sin esto, cero código.
- **GATE 2**: todas las historias verificadas E2E. Bug crítico → devuelve artefacto al dev con el test que lo reproduce (una corrección acotada; si falla, escala).
- **GATE 2.5** (Security): ninguna vulnerabilidad crítica/alta abierta.
- **GATE 3**: staging validado + rollback probado.

Todo gate que pasa emite recibo; todo consumo downstream verifica recibo.

## Definition of Ready / Done

Usar los checklists de `references/dor-dod.md` en cada gate. Un artefacto sin DoD cumplido no avanza de fase.
