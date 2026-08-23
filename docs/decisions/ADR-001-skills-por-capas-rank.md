# ADR-001: Skills por capas con rank (proyecto > usuario > bundled)

**Estado:** DIFERIDA (no se incorpora) · **Fecha:** 2026-08-23 · **Risk Tier:** 2

## 1. Problem Statement

DeepSeek Harness descubre skills desde múltiples raíces ordenadas por rank (la capa más cercana al proyecto gana duplicados: proyecto > usuario > bundled). El arnés SDLC podría adoptar el mismo patrón — análogo a los scopes de memoria (`org > user > project`) — para que una organización o proyecto sobreescriba skills oficiales sin hacer fork (p. ej. un `sdlc-business-analyst` corporativo con plantillas sectoriales).

## 2. Decisión

**No se incorpora por ahora.** Queda registrada como trabajo futuro con revisión condicionada (§3).

**Justificación (del dueño del arnés):** las capas con rank requieren **madurez alta en el uso de este tipo de herramientas** — gobierno de variantes, precedencia entre capas, validez de recibos cuando la skill "ux-designer" de un proyecto difiere de la oficial. Nuestro enfoque es **centralizar este tipo de decisiones en el arnés oficial**, de modo que los equipos puedan ir madurando en su uso **sin asumir riesgos** de divergencia ni de gobierno distribuido prematuro.

Además (análisis técnico): la capa proyecto/usuario se instala distinto en cada plataforma (Kimi, Claude Code, Cursor, Codex...), lo que exigiría un contrato de descubrimiento por plataforma que hoy no existe en el estándar Agent Skills.

## 3. Re-evaluation triggers

Reabrir esta decisión cuando se cumpla **alguna** de:

1. Una organización real adopte el arnés y pida variantes propias de roles (demanda, no especulación).
2. El estándar Agent Skills defina un mecanismo de capas/precedencia soportado por las plataformas principales.
3. El arnés acumule ≥2 sprints con Sprint Review en verde en un equipo que ya opere gates, recibos y manifiesto sin fricción (madurez demostrada con datos, no con intuición).

## 4. Qué SÍ cubre la necesidad hoy

- Personalización sin fork: **Decision Packages** pre-aprobados (`sdlc-decision-engine/assets/decision-packages/`), Tech Radar y principios por organización (`spec/tech-radar.yaml` vía memoria org), y políticas org mandatory con desviaciones (`sdlc-memory`).
- Extensibilidad: añadir una skill oficial nueva solo exige su frontmatter `harness-*` + regenerar el manifiesto (v2.9/v2.10).
