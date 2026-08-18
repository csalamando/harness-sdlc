# Pipeline SDLC detallado

## Fases y roles

| Fase | Rol | Entradas | Salidas | Gate |
|---|---|---|---|---|
| -1 Setup | DevOps + Orquestador | Idea | repo, spec/, pipelines vacíos, tablero | - |
| 0 Visión | Product Owner | Idea del usuario | vision.md, backlog.md | Métrica de éxito por épica |
| 1 Discovery | Business Analyst | vision.md, backlog.md | user-stories.md (Gherkin), business-rules.md, glossary.md | Toda historia testeable |
| 2 Diseño | UX Designer | user-stories.md | ux-flows.md, design-system.md, tokens.json | Estados error/vacío cubiertos |
| 2 Diseño | Software Architect | user-stories, ux-flows, business-rules | architecture.md, api-contract.yaml, data-model.md, adr/ | Todo endpoint con contrato |
| 2 Diseño | Security Engineer | architecture, data-model | threat-model.md, security-requirements.md | STRIDE completo |
| 2 Diseño | Data Engineer (condicional) | data-model, business-rules | data-governance.md, migraciones | Estrategia backup/anonimización |
| 3 Spec | Architect (consolida) | Todo lo anterior | spec/ coherente + test-plan.md | GATE 1 (humano) |
| 4 Build | Dev Backend | spec/, api-contract, test-plan | código + tests unit/contract, cobertura | tests verdes |
| 4 Build | Dev Frontend | spec/, design-system, api-contract | componentes + tests, build | tests verdes, design system |
| 5 Verify | QA Automation | builds, test-plan, Gherkin | suite E2E, qa-report.md | GATE 2 |
| 5 Verify | Security Engineer | staging | reporte DAST | GATE 2.5 |
| 6 Deploy | DevOps | código verificado | pipelines/, infra/, runbook.md | - |
| 6 Deploy | Cloud Engineer | infra/, NFRs | infra desplegada, dashboards, alertas | GATE 3 |
| 7 Operate | SRE | SLOs, infra | slo.md, playbooks, postmortems | - |
| 7 Operate | Product Analyst | visión, analítica | impact-report.md → backlog PO | - |

## Flujos paralelos

- Mientras se construye el sprint N, PO + BA refinan el N+1.
- Tech Writer documenta en paralelo a fases 4-6.

## Gestión de deuda técnica

El Architect mantiene `spec/tech-debt.md`. Cada refactor postergado en TDD se registra con costo estimado; el PO lo prioriza como épica.

## Retrospectiva del sistema

Periódicamente revisar: ¿qué artefacto generó más retrabajo? ¿qué gate dejó pasar defectos? Actualizar checklists y skills en consecuencia.

## Fase 8: Archivo (cierre del ciclo)

Al verificarse el sprint: merge de delta-specs en la spec maestra, memorias superseded, traceability en verde, receipt status limpio, sesión de memoria cerrada con resumen. La próxima iteración arranca desde spec consolidada.
