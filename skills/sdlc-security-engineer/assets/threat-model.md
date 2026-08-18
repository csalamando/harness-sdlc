# Threat Model (STRIDE)

Versión: 0.1 | Fuente: architecture.md v<x>

| Componente/Flujo | S | T | R | I | E | D | Amenaza concreta | Riesgo | Mitigación | Dueño |
|---|---|---|---|---|---|---|---|---|---|---|
| API → DB | | ✓ | | | | | SQL injection | Alto | ORM + queries parametrizadas | Dev Back |

Leyenda: S=Spoofing, T=Tampering, R=Repudiation, I=Info Disclosure, E=Elevation, D=DoS
