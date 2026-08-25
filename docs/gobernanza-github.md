# Gobierno del arnés a nivel GitHub

> **Para quién es esto:** administradores del repo del proyecto y el architecture board.
> No es necesario para *usar* el arnés — es la configuración que hace que la
> matriz de autoridad y los gates sean **fronteras duras** (no solo convención).
>
> Prerequisito: las skills del arnés vendorizadas en el repo
> (ver `docs/guia-de-uso-arnes-sdlc.md` → "Distribución y versionado").

El arnés gobierna *dentro* del repo (matriz de autoridad, recibos, gates).
Esta especificación conecta ese gobierno con los mecanismos nativos de GitHub
para que **saltarse una regla requiera un bypass explícito y auditado**, no un
simple `git push`.

---

## 1. Equipos GitHub ↔ roles del arnés

Crear un team por rol de la matriz de autoridad y referenciar **teams** (no
personas) en CODEOWNERS — la autoridad sobrevive rotaciones de personal:

| Team GitHub | Rol del arnés | Frontera principal |
|---|---|---|
| `architecture-board` | enterprise-architect / board | `tech-radar.yaml`, `authority-matrix.yaml`, `receipts/`, excepciones Tier 1 |
| `product-owners` | product-owner | `vision.md`, `epics.md`, `backlog.md` |
| `solution-architects` | solution-architect | `architecture-proposal.md`, `technical-stories.md`, costos |
| `business-analysts` | business-analyst | `user-stories.md`, `business-rules.md` |
| `ux-designers` | ux-designer | `ux-flows.md`, `design-system.md` |
| `software-architects` | software-architect | `architecture.md`, `api-contract.yaml`, `data-model.md`, `adr/`, `test-plan.md` |
| `security-engineers` | security-engineer | `threat-model.md`, `security-requirements.md` |
| `qa-leads` | qa-automation | `qa-report.md` |
| `sre-leads` | sre | `slo.md`, playbooks, postmortems |
| `product-analysts` | product-analyst | `impact-report.md` |

El `spec/team-roster.yaml` del proyecto se deriva de estos teams
(un usuario GitHub → su rol), y es la entrada de `authority_check.py --team`.

## 2. Branch protection en `main` (la frontera dura)

**Settings → Branches → Add rule** para `main`:

| Regla | Valor | Qué garantiza |
|---|---|---|
| Require a pull request | ✅ | Nadie modifica la spec sin revisión |
| Required approvals | 1 (2 si hay Tier 1 frecuente) | Mínimo el code owner |
| **Require review from Code Owners** | ✅ | Un PR que toca `spec/adr/` no mergea sin el Arquitecto |
| **Dismiss stale pull request approvals** | ✅ | Si el artefacto cambia tras aprobarse, la aprobación cae — igual que un recibo invalidado |
| **Require status checks** | ✅ `self-test` + `spec-governance` | Consistencia del arnés + autoría/gates/recibos en cada PR |
| Require branches up to date | ✅ | Los checks corren sobre el merge real |
| Require linear history | ✅ | Historia legible = auditoría legible |
| Require signed commits | ✅ (perfil completo) | Recibo sha256 + firma = evidencia no repudiable |
| Allow force pushes / deletions | ❌ | La evidencia es append-only |
| Do not allow bypassing | ✅ (admins incluidos) | El bypass de emergencia se documenta (§5) |

## 3. Status check `spec-governance`

Copiar la plantilla `skills/sdlc-orchestrator/assets/ci-spec-governance.yml` a
`.github/workflows/spec-governance.yml` y ajustar la ruta de las skills
vendorizadas. En cada PR que toque `spec/**` verifica:

1. **Autoridad**: cada archivo modificado lo toca su rol dueño
   (`authority_check.py --author <usuario> --team spec/team-roster.yaml`).
2. **Gates**: los artefactos modificados pasan su checklist
   (`gate_checker.py --tipo <tipo>`).
3. **Recibos**: los recibos de los artefactos tocados siguen vigentes.

Marcar el check como **required** en la branch protection (§2).

## 4. Environments: los gates de despliegue como aprobaciones

**Settings → Environments**:

| Environment | Required reviewers | Gate equivalente |
|---|---|---|
| `staging` | `qa-leads` | GATE 2 / 2.5 |
| `production` | `sre-leads` + `architecture-board` | GATE 3 |

Así GATE 3 deja de ser un comentario en un PR y se convierte en una
**aprobación de despliegue** registrada en el audit log de GitHub.
Opcional: *wait timer* en `production` para ventanas de despliegue.

## 5. Bypass de emergencia (gobernado, no prohibido)

Un incidente puede exigir mergear sin todas las aprobaciones. Regla:

1. El bypass lo ejecuta un admin con el motivo en el mensaje del merge.
2. **Obligatorio**: abrir issue `postmortem` + memoria `learning` en
   `spec/memory/` en las 24 h siguientes, explicando qué regla se saltó y por qué.
3. Si el mismo bypass se repite 2 veces, es un hueco del proceso → ADR.

El bypass frecuente sin learning es exactamente la señal que el dashboard
mide como retrabajo/loops.

## 6. Tabla de correspondencia arnés ↔ GitHub

| Mecanismo del arnés | Equivalente GitHub | Quién lo configura |
|---|---|---|
| Matriz de autoridad (`authority-matrix.yaml`) | CODEOWNERS + teams | Architecture board |
| Rol emisor del recibo | Required review del code owner | Repo admin |
| Gate aprobado | Status check `spec-governance` verde | CI |
| Recibo invalidado (artefacto cambió) | Stale review dismissed | Branch protection |
| GATE 3 (release) | Environment `production` approval | SRE lead |
| Tech radar / paved roads | CODEOWNERS del board sobre `tech-radar.yaml` | Architecture board |
| Excepción Tier 1 | Bypass documentado + memoria learning | Board |
| Evidencia no repudiable | Recibo sha256 + commits firmados | Repo admin |

## 7. Perfiles de adopción

**Mínimo (equipo pequeño, fase 0-2):**
CODEOWNERS + "Require review from Code Owners" + check `spec-governance`.
15 minutos de configuración.

**Completo (producto gobernado, fase 5+):**
todo lo anterior + stale reviews + signed commits + environments +
historia lineal + auditoría de bypass.

Regla práctica: adoptar el perfil completo a más tardar al primer release
(GATE 3) — antes de eso el costo de fricción supera al riesgo.
