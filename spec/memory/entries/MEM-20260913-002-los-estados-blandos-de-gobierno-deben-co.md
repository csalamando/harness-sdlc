---
id: MEM-20260913-002
type: learning
project: harness-sdlc
created: 2026-09-13T19:12:14
session: SES-20260913-191214
tags: [gobierno,fase-1,gates,v2.33.3]
links: []
supersedes: []
topic_key: estados-blandos-verificables
---
# Los estados blandos de gobierno deben convertirse en checks verificables, no quedarse como prosa

**What**: Fase -1 tenia dos estados blandos: el roster podia quedarse como plantilla intacta y la pausa de Strict TDD era narrativa (TopBirds continuo sin runner). Ambos pasaron a ser verificables: gate_verify falla en GATE 0/1 con roster plantilla y en GATE 2 sin runner o waiver aprobado

**Why**: Un estado de gobierno que nadie verifica tiende a romperse en silencio; la leccion general del arnes (evidencia, no narracion) aplica tambien a sus propias fases de setup

**Where**: skills/sdlc-orchestrator/scripts/gate_verify.py (transversales 3 y 4), v2.33.3

**Key details**: -

**Learned**: Al disenar una fase de setup, preguntar: que puede quedar 'a medias' sin que nadie lo note? Cada respuesta es candidata a un check en gate_verify con su waiver gobernado
