# Propuesta: Portal del proyecto con auditoría y trazabilidad (v2.23)

Fecha: 2026-09-09 · Arnés base: v2.22.1 · Origen: revisión completa de `portal_lib.py` + `harness_graph.py` tras adoptar la memoria de auditoría (ADR-004). Reemplaza y amplía el alcance de la historia S19-AR-02 (que quedó por error en el backlog de TopBirdsColombia — es una feature del arnés, beneficia a todo proyecto gobernado).

## 1. Diagnóstico del portal actual (v2.20–v2.22)

### Cómo funciona hoy
- `portal_lib.py` es la librería: registry (`registry.json`), shell (`index.html`), manifiesto (`manifest.js`), búsqueda (`search-index.js`), `--check` anti-drift.
- `harness_graph.py --proyecto` emite 5 páginas densas (inicio, métricas, arquitectura, memoria, glosario oculto) + sweep de diagramas.
- `mdview.py build` renderiza **cada `.md` de spec/ como página individual** en `paginas/docs/`.
- Menú lateral: 8 categorías fijas — Inicio, Métricas, Arquitectura, Negocio, Calidad, Operación, Documentos, Memoria.

### Problemas observados (evidencia: portal real de TopBirdsColombia)

| # | Problema | Causa raíz |
|---|---|---|
| P1 | **"Documentos" y "Operación" se inundan**: 14 sprint reviews como 14 ítems de menú, ADRs sueltos, CHANGELOG, INDEX… | `mdview` registra cada `.md` como ítem de primer nivel; `infer_categoria()` por palabra clave en el nombre es frágil ("report" → operación aunque sea un sprint review) |
| P2 | **La auditoría no se ve**: `spec/audit/events.jsonl` existe desde v2.22 (emits, revocaciones, arch_lint, contract_diff, aprobador, harness_version) y el portal no lee ni un solo evento | El portal se diseñó en v2.20, antes de ADR-004 |
| P3 | **La métrica de revocados no tiene cara**: `harness_graph` ya calcula retrabajo desde recibos (`estado in invalidado/revocado`), pero no hay vista de *qué* se revocó, *quién* lo aprobó al re-emitir, ni *cuándo* | Los recibos cuentan el qué; la auditoría tiene el quién/cuándo/por-qué y nadie la consulta |
| P4 | **Categorías por tipo de archivo, no por pregunta del usuario**: "¿el proyecto va bien?" (inicio), "¿quién aprobó esto?" (no existe), "¿qué decidimos?" (mezclado entre Arquitectura y Documentos) | `_REGLES` clasifica por keywords del nombre de archivo |
| P5 | **`grupo` existe pero no se usa en el menú**: el registry ya soporta `grupo` (mdview pasa el directorio: `adr`, `reports`) y el ordenamiento lo respeta, pero el shell no renderiza sub-agrupaciones | Falta UI, no datos |

## 2. Propuesta

### 2.1 Reorganización del menú: de "tipos de archivo" a "preguntas"

```
🏠 Inicio          — cómo va el proyecto (igual que hoy)
📊 Métricas        — tendencias, tiempos, retrabajo (igual)
🛡 Gobernanza      — NUEVA: Auditoría · Recibos y gates · ADRs · Tech Radar
🏛 Arquitectura    — diagramas vivos + propuesta (sin ADRs: se mudan a Gobernanza)
💼 Negocio         — visión, backlog, historias, glosario
🧪 Calidad         — test plan, QA report, E2E
🚀 Operación       — despliegue, SLO, incidentes, pipeline CI/CD
📚 Documentos      — SOLO docs que no encajan arriba; con sub-grupos plegables
🧠 Memoria         — aprendizajes y handoffs (igual)
```

Reglas:
1. **ADR y receipts dejan de ser "docs"**: son gobernanza. `infer_categoria()` añade `("gobernanza", ("adr", "receipt", "authority", "audit", "threat", "security", "tech-radar"))` antes que arquitectura/operación.
2. **Sprint reviews → sub-grupo único "Sprints"** dentro de Operación (o su propia categoría solo si >5 ítems). `mdview` pasa `grupo=dirname`; el shell renderiza grupos plegables (`<details>`) cuando una categoría tiene >6 ítems: se ve el grupo, no 14 filas.
3. **CHANGELOG e INDEX de spec no van al menú**: se registran con `oculto=True` (buscables, no en el lateral). Criterio: páginas de índice/log puro no merecen espacio de menú.

### 2.2 Página nueva: Auditoría (la estrella de v2.23)

`paginas/gobernanza-auditoria.html`, generada por `harness_graph` (o `audit_verify --portal`), 100% derivada de `spec/audit/events.jsonl` — nada narrado:

- **Línea de tiempo** de eventos (más reciente primero): icono por tipo (✅ emit, ↩️ revoke, 🛡 arch_lint, 📜 contract_diff, 🚀 bootstrap), artefacto, gate, rol, **aprobador humano**, harness_version, ts.
- **Contadores**: recibos emitidos, **revocados/invalidados (la métrica que siempre estaba en cero — ahora con fuente)**, corridas de arch_lint, contract_diffs con breaking changes.
- **Salud de la cadena**: resultado de `audit_verify` (N eventos, cadena íntegra) con timestamp de verificación.
- **Tabla de revocaciones**: artefacto, recibo anterior → nuevo hash, quién aprobó el cambio, evento de invalidación downstream derivada (N2) si aplica.

Criterios de aceptación:
1. Todo número de la página es recomputable desde `events.jsonl` (un test del self-test re-deriva los contadores y los compara).
2. Si no existe `spec/audit/`, la página muestra el empty-state con el comando de inicialización (`init_project.py`) — no desaparece del menú.
3. La página queda registrada vía `register(..., kind="metrica", categoria="gobernanza")` y `--check` la cubre como cualquier derivado.

### 2.3 Bloque de gobernanza en Inicio

El panel "Acumulado del proyecto" gana 3 contadores derivados de la auditoría: `recibos vigentes`, `revocaciones`, `última verificación de cadena ✓/✗`. La promesa "auditable" deja de ser invisible.

### 2.4 Qué NO cambia

- El shell (búsqueda Ctrl+K, temas, zoom) — funciona bien.
- El modelo registry + generadores independientes — es la modularidad correcta.
- `--check` anti-drift — se extiende a las páginas nuevas sin cambios de mecanismo.

## 3. Plan de implementación (TDD, self-test primero)

1. **Red**: checks en `tests/self_test.py` — fixture con `events.jsonl` (emit×3, revoke×1, arch_lint×1) → portal generado debe contener página de auditoría con contadores exactos (revocados=1), categoría `gobernanza` presente, sprint reviews agrupados, CHANGELOG/INDEX ocultos.
2. **Green**: `portal_lib` (categoría gobernanza + grupos plegables en shell + `oculto` para índices) → `harness_graph` (página auditoría + bloque inicio) → `mdview` (grupo por dirname, ocultar CHANGELOG/INDEX).
3. **Refactor**: extraer `_REGLES` a tabla documentada en la SKILL (la clasificación deja de ser folklore).
4. Regenerar portal del fixture + manifiesto/grafo; actualizar README §4i y CHANGELOG (v2.23.0 MINOR — retrocompatible: proyectos sin auditoría ven empty-state).

## 4. Riesgos

- **Shell con grupos plegables**: el `_SHELL` es string plano con tokens; añadir `<details>` por grupo es contenido pero toca el JS de render del menú. Mitigación: self-test valida estructura del manifiesto, no el JS; se verifica abriendo el portal generado en navegador headless antes de release.
- **Re-clasificación mueve ítems de categoría en proyectos existentes**: aceptable (el portal es derivado; basta regenerar), se documenta en el CHANGELOG como cambio visible.
