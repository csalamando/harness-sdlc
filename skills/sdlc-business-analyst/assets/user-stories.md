# Historias de Usuario

Versión: 0.1 | Sprint: N | Fuente: backlog.md v<x>

## HU-001 — <título>
**Épica:** EP-<n> | **Prioridad:** <MoSCoW>

Como ROL-01 (<nombre del rol del catálogo `spec/roles.md`>) quiero <acción> para <valor de negocio>.

### Criterios de aceptación (Gherkin)

```gherkin
Escenario: camino feliz
  Dado <contexto inicial>
  Cuando <acción>
  Entonces <resultado observable>

Escenario: error de validación
  Dado <contexto>
  Cuando <entrada inválida>
  Entonces <mensaje específico y comportamiento>

Escenario: caso borde
  Dado <límite: vacío, máximo, concurrencia...>
  Cuando <acción>
  Entonces <comportamiento esperado>
```

### Reglas de negocio aplicables
BR-001, BR-00x

### Dependencias
<APIs externas, otras HU, procesos manuales>
