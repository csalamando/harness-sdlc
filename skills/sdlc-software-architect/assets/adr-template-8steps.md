# ADR-{ID}: {Título de la Decisión}

## Metadata
- **Status**: Draft | Proposed | Adopted | Superseded | Retired
- **Risk Tier**: 1 | 2 | 3
- **Decision Owner**: {Nombre del Arquitecto de Software}
- **Date Proposed**: {YYYY-MM-DD}
- **Date Adopted**: {YYYY-MM-DD}
- **Last Responsible Moment**: {YYYY-MM-DD}
- **Decision Package**: {pkg-name o "N/A"}
- **Supersedes**: {ADR-xxx o "N/A"}
- **Superseded By**: {ADR-xxx o "N/A"}

## Paso 1: Problem Statement
{Describe el problema real: un "bad thing happening" o un "good thing not happening".
NO menciones tecnologías, frameworks ni soluciones.}

## Paso 2: Last Responsible Moment
- **Fecha límite**: {YYYY-MM-DD}
- **Razón**: {Por qué esta es la fecha límite real}
- **Costo de reversa**: {Bajo | Medio | Alto}
- **Restricciones**:
  - Presupuesto: {monto o "N/A"}
  - Headcount: {número o "N/A"}
  - Regulatorias: {normativa aplicable o "N/A"}
  - Dependencias externas: {lista o "N/A"}

## Paso 3: Criterios de Evaluación
| Criterio | Peso | Métrica | Umbral Mínimo |
|----------|------|---------|---------------|
| {Criterio 1} | {peso}% | {métrica} | {umbral} |
| {Criterio 2} | {peso}% | {métrica} | {umbral} |
| {Criterio 3} | {peso}% | {métrica} | {umbral} |
| **TOTAL** | **100%** | | |

**Fuente de criterios**: {Decision Package pkg-xxx o "Definidos por el Arquitecto"}

## Paso 4: Opciones Consideradas

### Opción A: {Nombre}
- **Descripción**: {Descripción técnica}
- **Paved Road**: {Sí/No}
- **Tecnologías**: {lista}
- **Esfuerzo estimado**: {semanas}
- **Riesgos**: {lista}

### Opción B: {Nombre}
- **Descripción**: {Descripción técnica}
- **Paved Road**: {Sí/No}
- **Tecnologías**: {lista}
- **Esfuerzo estimado**: {semanas}
- **Riesgos**: {lista}

### Opción C: {Nombre} (Opcional)
- **Descripción**: {Descripción técnica}
- **Paved Road**: {Sí/No}
- **Tecnologías**: {lista}
- **Esfuerzo estimado**: {semanas}
- **Riesgos**: {lista}

## Paso 5: Advice Log

### Stakeholders Consultados
| Rol | Nombre | Fecha | Consejo | Aplicado |
|-----|--------|-------|---------|----------|
| {Rol} | {Nombre} | 2026-01-15 | {Resumen del consejo} | {Sí/No} |

### Detalle del Consejo
#### {Rol} — {Fecha}
> {Consejo textual del stakeholder}

**Respuesta del Arquitecto**: {Si se aplicó o no, y por qué}

## Paso 6: Scorecard de Trade-Offs

| Criterio | Peso | Opción A | Opción B | Opción C |
|----------|------|----------|----------|----------|
| {Criterio 1} | {peso}% | {puntaje} | {puntaje} | {puntaje} |
| {Criterio 2} | {peso}% | {puntaje} | {puntaje} | {puntaje} |
| {Criterio 3} | {peso}% | {puntaje} | {puntaje} | {puntaje} |
| **TOTAL** | **100%** | **{total}** | **{total}** | **{total}** |

**Opción ganadora**: {Opción X}
**Justificación si no es la de mayor puntaje**: {Explicación o "N/A"}

## Paso 7: Decisión

### Decisión Adoptada
{Declaración clara de la decisión en una frase}

### Razones Principales
1. {Razón 1}
2. {Razón 2}
3. {Razón 3}

### Consecuencias Positivas Esperadas
- {Consecuencia 1}
- {Consecuencia 2}

### Consecuencias Negativas Aceptadas
- {Consecuencia 1}
- {Consecuencia 2}

### Qué NO se Decidió
- {Alternativa rechazada y por qué}

## Paso 8: Re-evaluation Triggers
- {Condición 1 que obliga a re-evaluar}
- {Condición 2 que obliga a re-evaluar}
- {Fecha de revisión programada: YYYY-MM-DD}

## Firma Arquitectónica
- **Arquitecto**: {Nombre}
- **Rol**: Software Architect
- **Fecha de firma**: {YYYY-MM-DD HH:MM:SS UTC}
- **Receipt ID**: {ARCH-xxx}
- **SHA-256 de artefactos**: {hash}
