---
id: MEM-20260913-003
type: learning
project: harness-sdlc
created: 2026-09-13T21:16:02
session: SES-20260913-211602
tags: [gobierno,derivados,codeowners,v2.33.4]
links: []
supersedes: []
topic_key: derivar-nunca-duplicar
---
# Las plantillas copiadas a mano que replican una fuente de verdad son drift garantizado: derivar, nunca duplicar

**What**: CODEOWNERS-template era una copia manual de la matriz de autoridad con nombres inventados; al revisarla para v2.33.4 ya estaba desactualizada (cost-estimation, roles.md, tdd-waiver). Se reemplazo por codeowners_gen.py que la deriva de matriz+roster con --check anti-drift

**Why**: Toda copia manual de una fuente gobernada diverge en silencio; el arnés ya aplica este principio a diagramas y pipeline-state, y faltaba en la frontera de Git

**Where**: skills/sdlc-orchestrator/scripts/codeowners_gen.py, v2.33.4

**Key details**: -

**Learned**: Antes de crear una plantilla que copia datos de otro artefacto gobernado, escribir el generador; si no se puede generar, anotar la dependencia en spec_diff_impact para que el cambio la revoque
