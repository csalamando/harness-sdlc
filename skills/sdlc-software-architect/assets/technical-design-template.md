# Plantilla — Historia Técnica de Construcción (Nivel 1, alto nivel)

> v2.30 — la usa el **Software Architect** en `spec/technical-design.md` (Fase 2-3).
> Nivel 0 (decisión de iniciativa): `technical-stories.md` del Solution Architect (GATE 0).
> Nivel 2 (diseño detallado): `technical-design-backend.md` / `technical-design-frontend.md`
> de los devs (Fase 4) — **deriva de este documento**; si una HU no está cubierta aquí,
> el dev escala al Architect en vez de improvisar.

```markdown
## TD-001: <título imperativo>

- **Tipo**: enabler | integración | datos | seguridad | observabilidad | performance
- **Deriva de**: <TS-xxx del Nivel 0 que origina, si aplica>
- **Cubre**: <HU-xxx / BR-xxx / EP-xx que habilita>
- **Base arquitectónica**: <sección de architecture.md / endpoint del api-contract.yaml / entidad del data-model.md / ADR-xxx que la sustenta>
- **Autor**: Software Architect
- **Estado**: propuesta | aprobada | entregada
- **Fecha**: YYYY-MM-DD

**Como** <componente/capa del sistema>,
**necesito** <capacidad técnica de construcción>,
**para** <qué historia de negocio o NFR habilita>.

### Alcance técnico
- Componentes/capas involucrados: <...>
- Contratos afectados: <endpoints OpenAPI / eventos / tablas>
- Decisiones aplicables: <ADR-xxx que la gobiernan>

### Criterio de aceptación (verificable)
- Dado <contexto>, cuando <acción>, entonces <resultado medible>
- Métrica: <p95 | cobertura | tiempo de ejecución | cero errores de contrato | ...>

### Costo de NO hacerla
<qué se bloquea o degrada si se posterga>

### Handoff a Nivel 2
- Backend: <qué debe detallar el dev back en technical-design-backend.md>
- Frontend: <qué debe detallar el dev front en technical-design-frontend.md>
- N/A si el nivel de detalle ya es suficiente para codificar con TDD.
```

## Reglas

1. **El Architect genera y aprueba**: ninguna TD-xxx entra al sprint sin estado `aprobada` por el Software Architect (recibo si el gate del sprint lo exige).
2. **Trazabilidad completa**: toda TD enlaza su base arquitectónica (architecture.md / api-contract / data-model / ADR) y las HU/BR que cubre. Una TD sin base es diseño improvisado.
3. **Nivel de detalle correcto**: el Nivel 1 define *qué* se construye y *con qué restricciones*; el *cómo exacto* (funciones, estrategia de tests, mocks) es Nivel 2 y lo escriben los devs.
4. **Cobertura del sprint**: toda HU del sprint debe estar cubierta por al menos una TD o declararse explícitamente "sin diseño técnico adicional requerido" — el silencio no es una opción.
5. Cambios a una TD aprobada en pleno sprint = change-request, no edición silenciosa.
