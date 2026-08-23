# ADR-002: Dashboard HTML vivo del proyecto (`spec/dashboard.html`)

**Estado:** PROPUESTA (pendiente de decisión para v2.12) · **Fecha:** 2026-08-23 · **Risk Tier:** 2

## 1. Problem Statement

El grafo del pipeline (`docs/graph.html`, v2.11) describe el **arnés** — es estático, derivado del manifiesto, y sirve para explicar el proceso. No responde la pregunta que un equipo se hace cada día: **¿en qué fase está MI proyecto, qué gates faltan, cuántos sprints llevamos y cómo vamos vs. antes?**

Hoy esa respuesta exige cruzar tres artefactos de texto: `spec/METRICS.md` (tablero vivo), `spec/reports/sprint-review-NN.md` (snapshots con tendencias) y los recibos de `receipts/`. La información existe y está gobernada; falta la **capa de presentación** que la haga legible de un vistazo — en particular para steering no técnico.

## 2. Decisión propuesta

**Un solo archivo HTML vivo por proyecto: `spec/dashboard.html`**, generado por un modo nuevo de la herramienta existente:

```bash
python3 harness_graph.py --proyecto <dir>   # genera/actualiza spec/dashboard.html
python3 harness_graph.py --proyecto <dir> --check   # exit 1 si quedó atrás (CI)
```

### Principios de diseño (acordados con el dueño del arnés)

1. **UN archivo, siempre "el ahora"** — NO se crea un HTML por sprint. El dashboard se sobrescribe en cada regeneración, igual que `METRICS.md` e `INDEX.md` (artefactos derivados vivos).
2. **La historia la siguen guardando los `sprint-review-NN.md`** — el dashboard los *lee* para mostrar tendencias (sprints completados, releases, lead time por gate, trabajo rehecho), no los duplica ni los reemplaza.
3. **Markdown sigue siendo la fuente canónica** — diff-able en PRs, revisable en GitHub. El HTML es un render derivado, nunca editado a mano (anti-drift con `--check`, mismo patrón que el grafo del arnés).
4. **Cero narración manual** — todo el contenido se deriva de fuentes ya gobernadas (recibos, spec, sprint reviews, memorias). El dashboard es **visualización, no evidencia**: la evidencia siguen siendo los recibos.

### Contenido y fuentes

| Sección | Fuente (ya existe) |
|---|---|
| Grafo del pipeline con gates pintados (verde/ámbar/rojo) y fase actual | `receipts/` (recibos válidos por gate) + artefactos presentes en `spec/` |
| Contadores: sprints completados, releases (GATE 3), HU en curso/cerradas | `sprint-review-NN.md` + `traceability_matrix.py` |
| Tendencias por sprint: lead time por gate, recibos invalidados (retrabajo) | serie histórica de `sprint-review-NN.md` |
| Arcos de feedback resaltados (bug activo 5→4, hotfix 6→4) | recibos de invalidación del periodo |
| Acciones propuestas / aprendizajes recientes | memorias `learning` del periodo |

### Ciclo de actualización

- Se regenera al cerrar sprint (`sprint_review.py`), al emitir/invalidar un recibo, y en CI post-merge (corre en milisegundos).
- `--check` falla en CI si el HTML quedó atrás del estado de `receipts/` + `spec/`.

## 3. Opciones consideradas

1. **Un HTML por sprint** (`sprint-review-NN.html`) — DESCARTADA por el dueño: acumula archivos y pierde la vista "ahora". Los snapshots históricos ya los cumple el MD.
2. **Reemplazar el sprint review MD por HTML** — DESCARTADA: el MD es diff-able en PRs y es la fuente de la serie histórica; reemplazarlo rompería las tendencias y la revisión en GitHub.
3. **Solo grafo `--proyecto` sin métricas** — DESCARTADA: responde "dónde estamos" pero no "cómo vamos"; el valor está en combinar ambas en UN tablero.
4. **Herramienta nueva `pipeline_status.py`** — DESCARTADA: el 70% del motor (grafo, render, drift check) ya existe en `harness_graph.py`; un modo `--proyecto` lo reutiliza.

## 4. Consecuencias y trabajo requerido

- **Matriz de autoridad**: `spec/dashboard.html` entra como artefacto nuevo. Dueño propuesto: `sdlc-orchestrator` (con datos de `sdlc-product-analyst` y `sdlc-qa-automation`). Requiere actualizar frontmatter `harness-owns` y regenerar el manifiesto.
- **Regla de frescura**: el dashboard desactualizado **no bloquea gates**, solo alerta vía `--check` en CI — es presentación, no evidencia.
- **Self-test**: sumar check de drift del dashboard en un proyecto de prueba (fixtures).
- **Dependencias**: ninguna externa — el HTML es self-contained (mismo patrón que `docs/graph.html`).

## 5. Criterios de éxito (si se implementa en v2.12)

1. Un stakeholder abre `spec/dashboard.html` y en <30 segundos sabe: fase actual, gates faltantes, sprints y releases acumulados, y si el lead time mejora o empeora.
2. Nadie edita el HTML a mano en 3 sprints consecutivos (el `--check` no habría fallado).
3. Los `sprint-review-NN.md` siguen generándose idénticos (el dashboard no toca la fuente canónica).
