# Plantilla — Historia Técnica

```markdown
## TS-001: <título imperativo>

- **Tipo**: enabler | debt | spike | nfr
- **Origen**: <épica/historia de negocio que la motiva, o riesgo que mitiga>
- **Autor**: Solution Architect
- **Fecha**: YYYY-MM-DD

**Como** <equipo/sistema>,
**necesito** <capacidad técnica>,
**para** <valor de negocio o riesgo evitado — en lenguaje que el PO pueda priorizar>.

### Criterio de aceptación (verificable)
- Dado <contexto>, cuando <acción>, entonces <resultado medible>
- Métrica: <p95 < 300ms con 500 RPS | cobertura | tiempo de migración | ...>

### Costo de NO hacerla
<qué pasa si se posterga: bloqueo, incidente, interés de deuda>

### Notas
- Spike: la pregunta que responde es <...> y su timebox es <N días>
- Dependencias: <TS-xxx / HU-xxx>
```

## Reglas

1. Todo spike define pregunta + timebox. Sin pregunta no hay spike, hay disfraz.
2. Toda historia NFR es medible. "Mejorar el rendimiento" no es historia; "p95 < 300ms con 500 RPS" sí.
3. Toda historia técnica justifica su valor o riesgo — compite por backlog con argumentos, no con autoridad.
4. Trazabilidad obligatoria: toda TS-xxx enlaza su épica/historia de negocio o el riesgo que mitiga.
