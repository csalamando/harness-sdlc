# Flujos de Usuario

Versión: 0.1 | Fuente: user-stories.md v<x>

## Flujo: <nombre> (HU-001)

```mermaid
flowchart TD
    A[Inicio] --> B{¿Sesión activa?}
    B -->|Sí| C[Pantalla principal]
    B -->|No| D[Login]
    D -->|Error| E[Estado error: mensaje + reintento]
```

### Estados por pantalla
| Pantalla | Loading | Empty | Error | Success |
|---|---|---|---|---|
| <nombre> | <qué se muestra> | <qué se muestra> | <mensaje + acción> | <contenido> |
