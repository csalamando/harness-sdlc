---
id: MEM-20260913-001
type: learning
project: harness-sdlc
created: 2026-09-13T18:12:41
session: SES-20260913-181206
tags: [metricas,telemetria,receipt,v2.33.1]
links: []
supersedes: []
topic_key: metricas-fase-auto-registro
---
# Fase del auto-registro de activaciones: derivarla de harness-phases de la skill, no solo del gate

**What**: receipt.py emit auto-registraba la activacion con la fase del gate (audit_log.gate_fase); ux-designer (fase 2) emitiendo su recibo GATE 1 contaba fase 3 y distorsionaba la cobertura por fase de METRICS.md

**Why**: El gate de aprobacion y la fase de trabajo de la skill no siempre coinciden (una skill mono-fase aprueba en gates de otra fase); la metrica debe reflejar quien trabajo, no donde se aprobo

**Where**: skills/sdlc-orchestrator/scripts/receipt.py (_fase_de_activacion), v2.33.1

**Key details**: -

**Learned**: Toda metrica derivada automaticamente debe anclarse a la identidad/fase declarada del actor (frontmatter harness-phases), usando la del evento disparador solo cuando coincide; registrar la fuente (fase_src) para trazabilidad
