---
id: MEM-20260912-001
type: learning
project: harness-sdlc
created: 2026-09-12T15:52:10
session: 
tags: [versioning,ci,self-test,changelog]
links: [ADR-004]
supersedes: []
---
# Bump de version: CHANGELOG y harness-version declarada van en el mismo commit

**What**: Al crear la entrada [2.31.1] del CHANGELOG (docs de CATI + diagramas IR) sin tocar la version declarada, el self-test fallo en CI: 'harness-version declarada y coincide con el CHANGELOG — declarada=2.31.0 changelog=2.31.1' (run de GitHub Actions en d5b9a8d)

**Why**: La version del arnes no es decorativa: se estampa en recibos y eventos de auditoria (receipt.py, audit_log.py FALLBACK_VERSION), y el self-test la exige consistente con el CHANGELOG. Tres fuentes deben moverse juntas: frontmatter harness-version de sdlc-orchestrator/SKILL.md, FALLBACK_VERSION en audit_log.py, y los derivados (harness-manifest.yaml, docs/graph.html) regenerados con manifest_check.py --write y harness_graph.py --write

**Where**: -

**Key details**: -

**Learned**: Toda entrada nueva de CHANGELOG exige en el MISMO commit: bump de harness-version en SKILL.md del orquestador + FALLBACK_VERSION + regenerar derivados + correr tests/self_test.py local antes de push. Fix aplicado en c5faa04: CI verde, 312 checks OK
