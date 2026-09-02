# Changelog

Todas las novedades relevantes del arnés se documentan aquí. Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y versionado [SemVer](https://semver.org/lang/es/).

**Regla de versionado del arnés:**
- **MAJOR** (x.0.0): cambios incompatibles en gates, recibos o formato de spec (rompen pipelines existentes).
- **MINOR** (2.x.0): skills nuevas, gates nuevos, features retrocompatibles.
- **PATCH** (2.1.x): correcciones en scripts, plantillas o documentación.

## [2.15.2] - 2026-09-02

### Fixed
- **`sdlc-technical-writer/assets/gh-pages-docs.yml`**: el `environment` del job `deploy` usaba un flow mapping con `${{ }}` dentro (`{ name: ..., url: ${{ ... }} }`), que es **YAML inválido** — GitHub no podía parsear el workflow y lo reportaba como run fallido (con la ruta del archivo como nombre) en *cada push*, aunque el trigger push estuviera comentado. Reescrito en block style. Detectado en CATI: el fallo "docs-pages" que parecía de Pages deshabilitado era en realidad este error de sintaxis. Validados todos los assets `.yml` del arnés con parser.
- **`authority-matrix.yaml` (asset)**: usaba dos claves en una línea (`- path: X  owner: Y`), YAML **inválido** que los scripts toleraban por parseo regex; cualquier consumidor con parser real (yq, CI) fallaba. Convertido a block style válido y actualizados los tres regex consumidores (`authority_check.py`, `manifest_check.py`, `self_test.py`). El self-test suma la sección [9b]: **todos los assets `.yml/.yaml` deben parsear como YAML válido** — la clase de bug queda cerrada estructuralmente. **Nota de adopción:** quien vendorice scripts debe actualizar también su `spec/authority-matrix.yaml` al formato nuevo (los scripts v2.15.2 esperan `path:` y `owner:` en líneas separadas).

## [2.15.1] - 2026-09-02

### Fixed
- **`ci-spec-governance.yml` (asset)**: el job `dashboard-freshness` solo regenera y commitea cuando `harness_graph.py --check` detecta **drift real** (la huella embebida ignora el timestamp; antes commiteaba en cada push a main por la sola diferencia de fecha de generación). Añadido `concurrency: dashboard-freshness` para evitar la carrera bot-vs-bot cuando dos push seguidos disparan el job (detectado en la adopción en CATI: un run quedaba rojo por push rechazado del otro).

## [2.15.0] - 2026-09-02

**"La visibilidad se gobierna, no se pide."** Hasta v2.14 la telemetría (métricas, sprint review, dashboard) vivía en la capa de convención: el agente debía *recordar* generarla y nada bloqueaba si no ocurría. v2.15 sube cada pieza a la capa más fuerte posible (gate, CI, git). Ver guía §5o "Qué controla el arnés y qué no".

### Added
- **Gate `sprint-review` con exigencia semántica** (`gate_checker.py --tipo sprint-review`): 8 checks de secciones + **obligatoriedad de memoria `learning` creada dentro del periodo del sprint**. Un sprint sin aprendizaje registrado ya no pasa el gate. El workflow CI aplica este gate a `spec/reports/*.md`.
- **`sprint_review.py` cierra el sprint por sí mismo**: regenera `spec/METRICS.md` siempre, **autogenera la memoria `learning`** cuando el sprint fue limpio (sin rehechos, gates 1er intento 100%, sin freestyle) y no había una, e imprime los 3 comandos de cierre (gate + recibo + dashboard).
- **Dashboard con frescura garantizada en CI** (`ci-spec-governance.yml`): en PR, step visible (warning) de drift con `harness_graph.py --check`; en push a main, **regenera y auto-commitea `spec/dashboard.html`** (`chore: dashboard regenerado [skip ci]`). `harness_doctor.py` alerta si el proyecto tiene workflows pero ninguno menciona `harness_graph`.
- **Dueños de la telemetría**: `spec/METRICS.md`, `spec/metrics/`, `spec/reports/` y `spec/dashboard.html` entran a la matriz de autoridad y a `CODEOWNERS-template` (owner: orchestrator) — dejan de ser tierra de nadie.
- **Tokens honestos**: sprint review y dashboard separan tokens **medidos** (reportados) de **estimados** (chars/4), muestran el **% de cobertura medida** y alertan cuando los estimados difieren >25% de los reportados. Nuevo KPI "Tokens medidos (cobertura)" en el dashboard.
- **`tdd_order_check.py`** (nuevo script, stdlib puro): por cada HU del rango de commits verifica en `git log` que el commit `test(HU-xxx): red` precede al `feat(HU-xxx): green`. El TDD intra-sesión no es observable; el orden de commits sí. Step CI en modo warning y KPI "HUs con orden TDD en commits" en el dashboard.
- **Convención de commits TDD** en `sdlc-backend-dev-tdd` y `sdlc-frontend-dev-tdd`: commits separados red→green con el formato que `tdd_order_check.py` verifica.
- **Self-test sección [9]**: gate sprint-review (positivo y negativo), dueños de telemetría en la matriz y detección de orden TDD invertido en repo sintético. Fixture `proyecto-demo` actualizado: sus reviews son ahora el ejemplo canónico que pasa el gate.

## [2.14.1] - 2026-08-25

### Added
- **`docs/gobernanza-github.md`**: especificación paso a paso para convertir la matriz de autoridad y los gates en fronteras duras nativas de GitHub — teams ↔ roles, branch protection con Code Owners y stale reviews, status checks requeridos, environments como aprobación de GATE 3, bypass de emergencia gobernado (learning obligatorio) y perfiles de adopción mínimo/completo.
- **Guía §5n "Distribución, versionado y gobierno a nivel GitHub"**: aclara el modelo de distribución — el agente ejecuta las skills instaladas en su ruta; la copia vendorizada en el proyecto es el registro de versión y lo que corre en CI. Referenciada desde §5d y CONTRIBUTING.

## [2.14.0] - 2026-08-24

### Added
- **Stepper superior en el dashboard**: fase actual en grande, **progreso por HU cerradas** (soporta alcances que crecen y productos en evolución continua; fallback a gates si no hay estructura HU) y chips de **ciclos ejecutados** (sprints, bugs QA→TDD, hotfixes, replans, impact-reports con ×N).
- **Gráficas de línea SVG** de tendencias (lead time por gate, % 1er intento, retrabajo/artefactos) a partir del 3er sprint review; con 1-2 sprints, **tarjetas delta** (valor + Δ vs sprint anterior).
- **Histórico completo por fecha**: serie acumulada derivada de los timestamps de los recibos — cubre los sprints anteriores al primer `sprint_review.py` (los recibos no mienten sobre cuándo pasó algo).
- **Tiempos de fase y de ciclo**: barras + tabla por gate (apertura, cierre, trabajo dentro del gate y **día del proyecto en que cerró** — muestra el orden real de cierre, incluida gobernanza retroactiva) y duración de cada sprint entre cierres de review.
- **Tech Radar como gráfica de radar** (columna por cuadrante con tooltip) + KPIs de ADRs adoptadas y tecnologías en radar.
- **Popup por fase** (clic en nodos del grafo o del stepper): descripción, gate, artefactos generados en el proyecto y **tarjetas por skill con entradas (IN) y salidas (OUT)** derivadas del manifiesto. Los chips con archivo existente son **hipervínculos `target="_blank"`** al `.md` real (0 bytes extra; el contenido no se incrusta para no inflar el dashboard).
- **Botones de cabecera "Aprendizajes" y "Glosario"** que abren popup (las secciones estáticas del final desaparecen).
- **Control de tamaño de fuente (A−/A+)** persistente (localStorage), disponible en el dashboard y dentro de cada popup.
- **Glosario del arnés** (14 términos: gate, recibo, Risk Tier, ADR, paved roads, drift, lead time, ciclo…).
- Secciones del dashboard **colapsables** (`<details>`).

### Changed
- KPI "Recibos rehechos" renombrado a **"Recibos invalidados"** (invalidados + revocados — nombre alineado con el mecanismo real de `receipt.py`).

### Fixed
- **Grafo del dashboard sin traslapes**: lienzo más alto, títulos de nodos en filas alternadas, etiquetas de gates compactas con tooltip (vigentes/rehechos), loops sin recorrer ya no muestran texto (arco tenue con tooltip; texto solo si tienen recorridos ×N o están activos), anclas de texto en nodos extremos.
- Etiquetas cortadas en la gráfica de radar y ADR con prefijo duplicado en la tabla de decisiones.

## [2.13.0] - 2026-08-24

### Added
- **Panel "Decisiones gobernadas" en el dashboard del proyecto**: ADRs parseados de `spec/adr/` (o `docs/decisions/`) con **estado** (Adopted/Proposed/Superseded con badges de color) y **Risk Tier** — el diferencial del arnés (decisiones de 8 pasos, excepciones Tier 1) ahora es visible de un vistazo. Conteo del **Tech Radar** por cuadrante (ADOPT/TRIAL/ASSESS/HOLD) desde `spec/tech-radar.yaml` — los paved roads sin abrir el YAML.
- **"Qué se ha generado por fase"**: nueva sección con los artefactos con recibo vigente agrupados por macro-fase, y contador "N artefactos ✓" bajo cada nodo del grafo.
- **Recorridos históricos en los loops del grafo**: cada arco muestra "×N" (sprints corridos, bugs devueltos, hotfixes, replans) siempre que N>0, independiente de si está activo ahora — un loop en ×0 queda tenue ("nunca hubo hotfix" también informa).
- **Banda de progreso** azul sobre la línea principal del pipeline: el tramo completado hasta la fase actual se ve sin leer etiquetas.

### Fixed
- `parse_radar`: el conteo por cuadrante ya no se "desborda" entre secciones con YAML real (líneas en blanco entre entradas) — verificado contra `spec/tech-radar.yaml` de un proyecto real.
- `parse_adrs`: archivos índice/consolidado sin número (`ADR-consolidados.md`) ya no rompen el parseo.

## [2.12.1] - 2026-08-23

### Added
- **Versión del arnés visible y estampada**: el orquestador declara `harness-version` en su frontmatter (fuente única); el manifiesto derivado la registra; los **recibos nuevos la estampan** (`harness_version`) — la evidencia queda autodescriptiva (la lección de CATI: gates `fase2` de una versión vieja se descubrieron por accidente); `harness_doctor.py` muestra la versión instalada y **alerta si el proyecto operó con una versión anterior**; el dashboard del proyecto y el grafo del arnés la muestran en su encabezado/pie. El self-test cruza que la versión declarada coincida con la última entrada del CHANGELOG — olvidar el bump rompe el build. Decisión: versión única del arnés (no por skill) mientras las skills se distribuyan juntas.

### Fixed
- **Dashboard con proyectos reales (lecciones de CATI)**: `norm_gate()` normaliza alias históricos de gates en recibos (`fase2` → `GATE 2`) — proyectos adoptados en versiones viejas ya no aparecen "sin recibos". El conteo de HU cerradas escanea múltiples layouts (`src/`, `backend/src`, `frontend/src`, `e2e/`, …) en vez de asumir `src/` + `tests/`, y ya no resta por id (bug que marcaba 0 HU cerradas en proyectos con tests correctos).

## [2.12.0] - 2026-08-23

### Added
- **Dashboard vivo del proyecto** (`harness_graph.py --proyecto <dir>`, [ADR-002](docs/decisions/ADR-002-dashboard-html-proyecto.md)): genera **un solo `spec/dashboard.html`, siempre "el ahora"** — pipeline con gates pintados según sus recibos, fase actual, loops de feedback activos resaltados (bug/hotfix según invalidaciones), contadores acumulados (sprints, releases, HU cerradas, gates al primer intento), tendencias por sprint con **alerta automática** cuando un lead time empeora >15%, y memorias `learning` recientes. Todo derivado de fuentes gobernadas (`receipts/` + `spec/` + `sprint-review-NN.md`); cero narración manual. El estado derivado viaja incrustado en el propio HTML (`<!-- dashboard-state -->`) y `--check` detecta drift sin archivos auxiliares. Regla de frescura: alerta en CI, **no bloquea gates** (visualización, no evidencia).
- `spec/dashboard.html` registrado en la matriz de autoridad (owner: orchestrator, como los diagramas derivados).
- Fixture `tests/fixtures/proyecto-demo` (2 sprints, recibos vigentes + 1 invalidado, 1 release, trazabilidad HU) + 5 checks nuevos en el self-test (85 total): modelo derivado, generación, drift y detección de drift al mutar un recibo.

## [2.11.1] - 2026-08-23

### Fixed
- **Grafo del pipeline más legible**: lienzo más alto (340 → 540 px), arcos de feedback escalonados por distancia (los loops largos van por fuera y ya no se pisan), etiquetas en el punto medio real de la curva Bézier, fuentes más grandes (fases .85 rem, loops .78 rem) y nodos de 56 px.
- **Flechas de dirección en los loops**: cada arco de feedback termina en una flecha ámbar en el **borde** del nodo destino (antes quedaba tapada por el círculo del nodo).

### Propuestas (backlog, no implementado)
- **Modo `--proyecto` para `harness_graph.py`** (candidato a v2.12): el mismo grafo alimentado del estado real de un proyecto — gates según recibos válidos de `receipt.py`, fase actual por artefactos presentes en `spec/`, avance de sprint desde `sprint_review.py` y `traceability_matrix.py`, arcos de feedback resaltados cuando hay bugs activos. Generaría `spec/pipeline-status.html` como tablero vivo regenerable en CI. Requiere ADR (Risk Tier 2): define un artefacto nuevo y su regla de frescura.

## [2.11.0] - 2026-08-23

### Added
- **`harness_graph.py` (herramienta CLI 18)**: grafo interactivo del pipeline en `docs/graph.html`, **derivado del manifiesto** y del grafo de dependencias de `spec_diff_impact.py` — nunca editado a mano. Las 6 macro-fases como nodos, las 21 skills agrupadas por fase (desde el frontmatter `harness-*`), y los loops de realimentación (sprints, TDD, hotfix, delta-spec, impact-report → backlog). HTML self-contained sin dependencias externas, ideal para explicar el arnés sin una pared de texto. Modos `--write` (regenera) y `--check` (exit 1 si el grafo quedó atrás del manifiesto — integrado al self-test, 80 checks).

## [2.10.1] - 2026-08-23

### Docs
- **README con diagramas Mermaid** (render nativo de GitHub, sin imágenes que mantener): el pipeline completo con gates coloreados por tipo (humanos vs automáticos, §3), el ciclo de vida de un recibo RDD como diagrama de estados (ACTIVE → INVALIDATED/REVOKED → re-gate, §5) y las tres capas de memoria con precedencia y promoción (§6). Dogfooding: la propia skill `sdlc-diagrams` predica doc-as-code con Mermaid.
- **Quick start de 2 minutos** al inicio del README (descargar ZIP → descomprimir `.skill` → "usa el orquestador SDLC"), antes solo en la guía.
- **Tabla de las 21 skills colapsable** (`<details>`) — la portada ya no la sufre quien no la necesita.

## [2.10.0] - 2026-08-23

### Added
- **Routing derivado del manifiesto**: `manifest_check.py --routing [--sin-ui] [--sin-datos] [--sin-procesos]` imprime los roles por fase que aplican a la iniciativa, con las capacidades condicionales **auto-excluidas** (sin UI → no hay prototipo `spec/ux/`; sin proceso que automatizar → no hay PDD; sin datos significativos → `sdlc-data-engineer` no participa). El orquestador lo ejecuta al iniciar (nueva sección "Routing desde el manifiesto" en su SKILL.md) — la tabla de routing deja de ser solo prosa interpretada.
- **`docs/decisions/ADR-001-skills-por-capas-rank.md`**: decisión **diferida** de las capas con rank estilo DeepSeek (proyecto > usuario > bundled). Requieren madurez alta en el uso de este tipo de herramientas (gobierno de variantes, precedencia, validez de recibos con skills divergentes) y el enfoque del arnés es **centralizar esas decisiones para que los equipos maduren sin asumir riesgos**. Con re-evaluation triggers concretos (demanda real de una organización, estándar Agent Skills con capas, madurez demostrada vía Sprint Reviews).
- `self_test.py`: 3 checks nuevos del routing derivado (sección [7] pasa de 3 a 6 checks).

## [2.9.0] - 2026-08-23

### Added
- **Manifiesto dinámico del arnés** (implementa la inspiración pendiente de DeepSeek Harness — "Everything is a plugin" / capability seams — adaptada a un estándar Markdown agnóstico de agente): cada skill declara sus metadatos en el frontmatter de su propio `SKILL.md` (`harness-role`, `harness-phases`, `harness-owns`, `harness-gates`, `harness-conditional`, `harness-optional-deps`) y el manifiesto pasa a ser un **artefacto derivado**, nunca editado a mano.
- **`manifest_check.py`** (orquestador, herramienta CLI 17): `--write` regenera `assets/harness-manifest.yaml` escaneando skills (metadatos + scripts en disco); `--check` falla (exit 1) ante drift o inconsistencias cruzadas — gate declarado que `gate_checker.py` no soporta, artefacto `owns` ausente de la matriz de autoridad, artefacto de la matriz sin skill que lo declare; `--summary` imprime la vista legible de las 21 skills.
- **`harness_doctor.py` consume el manifiesto**: las expectativas (qué skills y scripts deben existir) se leen de `harness-manifest.yaml` en vez de listas quemadas en el código — añadir una skill o script ya no requiere tocar el doctor (con fallback a listas mínimas históricas si el manifiesto no está instalado: degradación elegante).
- `self_test.py`: nueva sección [7] — manifiesto sin drift, frontmatter presente, doctor consumiendo el manifiesto.

### Por qué
Los bugs de v2.8.1 nacieron de listas quemadas en prosa ("espera 14 scripts", "16 herramientas", grafo de impacto literal). Con el manifiesto derivado, esa clase de bug queda cerrada estructuralmente: la próxima vez que una skill declare algo que no existe, el self-test y el CI fallan en rojo antes del release. Trabajo futuro documentado: skills por capas con rank (proyecto > usuario > bundled), análogo a los scopes de memoria.

## [2.8.2] - 2026-08-23

### Added
- **`tests/self_test.py`** (solo repo fuente — NO entra al ZIP de release ni es una skill): regresión de consistencia del arnés con 71 checks (compilación de scripts, las 13 plantillas pasan su propio gate, grafo de impacto completo, matriz de autoridad, roles end-to-end, validación cruzada sin depender del cwd). Red de seguridad para mantenedores, nacida de la revisión de v2.8.1.
- Guía de uso §5k: checklist de release para quienes **modifican** el arnés (self-test verde → CHANGELOG → tag → release), claramente separada del flujo de quienes solo lo usan.

## [2.8.1] - 2026-08-23

Revisión de calidad profunda sobre v2.8.0: las features de v2.7/v2.8 quedaron documentadas por encima de lo que los scripts realmente hacían. Esta versión cierra esa brecha — todo lo prometido en el CHANGELOG ahora está verificado ejecutando los scripts.

### Fixed
- **`spec_diff_impact.py`**: el grafo de dependencias quedó congelado en v2.2 y no conocía los artefactos nuevos — cambiar `roles.md` o `screen-inventory.md` devolvía "Artefacto desconocido" y **no revocaba nada**, contradiciendo v2.7 ("cambiar un rol revoca HU, UX, test-plan") y v2.8 (revocación de `spec/ux/`). Añadidos al grafo: `roles.md`, `process-definition.md`, `screen-inventory.md`, `epics.md`, `architecture-proposal.md`, `technical-stories.md`, `cost-estimation.md`, `adr`, `tech-radar.yaml` y `diagrams`, con sus aristas (p. ej. `user-stories.md` depende de `roles.md`; `src-frontend` de `screen-inventory.md`).
- **`screen-inventory-template.md` no pasaba su propio gate**: placeholders `HU-xxx`/`ROL-xx` no cumplen los patrones `HU-\d+`/`ROL-\d+`. Ahora usa `HU-001`/`HU-002`/`ROL-01`/`ROL-02` (9 checks OK).
- **Mismo defecto en otras 3 plantillas**: `backlog.md` (sin fila con `EP-\d+`), `qa-report.md` (sin `HU-\d+`) y `adr-template-8steps.md` (Advice Log con fecha placeholder `{YYYY-MM-DD}` que no cumple el patrón de fecha). Las cuatro plantillas de artefactos con gate ahora pasan su propio `gate_checker.py`.
- **Matriz de autoridad incompleta**: 8 artefactos con skill dueña pero sin owner declarado podían ser aprobados por cualquier rol ("SIN REGLA"). Añadidos: `spec/glossary.md` y `spec/security-requirements.md` (el más delicado: un dev podía aprobar sus propios requisitos de seguridad), `spec/data-governance.md` → data-engineer, `spec/tokens.json` → ux-designer, `spec/cloud-costs.md` → cloud-engineer, `spec/exception-log.md` → enterprise-architect, `spec/team-roster.yaml` y `spec/risk-tier.yaml` → orchestrator.
- **Doc vs código en roles (v2.7)**: el orquestador decía "si existe `roles.md`, toda HU debe citar ROL-xx definidos" pero el código solo validaba los ROL citados. `gate_checker.py` ahora exige que **toda HU** cite al menos un ROL-xx del catálogo cuando este existe (sin catálogo, degradación elegante: el gate pasa igual). Plantilla `user-stories.md` actualizada: `Como ROL-01 (...)`.
- **Validación cruzada silenciosa**: `check_roles_refs`/`check_screens_refs` usaban rutas relativas a cwd — ejecutados desde otro directorio se saltaban sin avisar. Nueva función `resolve_spec_path` que localiza `spec/` subiendo desde el artefacto; verificado funcionando desde un cwd ajeno.
- **Numeración de fases ambigua**: `pipeline.md` ponía Discovery en Fase 1 y el orquestador en Fase 0. Ahora el orquestador alinea: FASE 0 = Visión + Discovery de la iniciativa (PO + Solution Architect, GATE 0), FASE 1 = análisis BA.
- **`.gitignore`**: faltaba `.codeintel/` (índice derivable de v2.3) — el propio `harness_doctor.py` lo reportaba.

### Verificación
- 23/23 scripts compilan; 18/18 CLI responden; 13/13 tipos de gate probados contra plantillas; autoridad por rol probada por pares rol-artefacto (autorizado/rechazado); revocación de `roles.md` → 24 artefactos downstream.

## [2.8.0] - 2026-08-23

### Added
- **Prototipos de pantalla gobernados** (`spec/ux/`, owner `ux-designer`, condicional a iniciativas con UI): las pantallas con sus flujos de interacción pasan a ser un artefacto de validación temprana — negocio navega el prototipo antes de escribir código y su aprobación es el contrato visual del sprint. Estándar del arnés: **Penpot** (open-source MPL-2.0, diseños en estándares web SVG/CSS/JSON, design tokens nativos sincronizables con `spec/tokens.json`, prototipado interactivo, self-hostable, servidor MCP oficial para que el agente cree y modifique pantallas). El archivo de diseño se versiona en Git junto a la spec — fuente de verdad auditable, no un enlace a una nube propietaria.
- **Estructura gobernada**: `spec/ux/screen-inventory.md` (inventario PANT-xx: HU que cubre, ROL que la opera, estados loading/empty/error/success, interacciones con destino — plantilla `assets/screen-inventory-template.md`), `spec/ux/prototipo.penpot` (archivo versionado) y `spec/ux/exports/` (renders PNG/SVG para revisión en GATE 1 sin abrir la herramienta).
- **Gobierno**: GATE 1 exige inventario con recibo vigente para las pantallas del sprint — sin prototipo aprobado, el Dev Front no implementa esas pantallas. Cambios en HU/flujos/roles revocan el recibo de `spec/ux/` vía `spec_diff_impact.py` y las pantallas impactadas se re-aprueban. Sin MCP de Penpot disponible, el inventario y wireframes se entregan igualmente (degradación elegante). Alternativa Figma documentada: el artefacto gobernado es el export versionado, nunca el archivo vivo en la nube.
- `gate_checker.py`: tipo nuevo `screen-inventory` (9 checks) con validación cruzada — las HU-xx citadas en el inventario deben existir en `user-stories.md`.
- Matriz de autoridad: `spec/ux/` → `ux-designer`.

## [2.7.0] - 2026-08-23

### Added
- **Catálogo de roles gobernado** (`spec/roles.md`, plantilla `assets/roles-template.md` en `sdlc-business-analyst`): el "Como <rol>" de las historias deja de ser una palabra libre y pasa a ser referencia a un artefacto versionado. Un rol es nombre + acciones que habilita + contexto/condiciones + reglas que lo restringen (BR/SEC). Los conflictos de interés entre roles se declaran y su priorización la firma el PO; el Architect deriva el RBAC del diseño desde este artefacto.
- **PDD — Process Definition Document** (`spec/process-definition.md`, plantilla `assets/pdd-template.md`): captura del proceso **AS-IS** (disparadores, flujo, excepciones conocidas/desconocidas, volúmenes, SLA, aplicaciones, riesgos y supuestos) para iniciativas que automatizan o rediseñan procesos (RPA/BPM). Sin firma del Process Owner (recibo) no hay diseño TO-BE; una excepción descubierta en piloto re-emite y re-aprueba el PDD.
- `gate_checker.py`: tipos nuevos `roles` y `process-definition`; validación cruzada — los ROL-xx citados en `user-stories.md` deben existir en el catálogo (aplica también al tipo `user-stories` cuando existe `roles.md`).
- Matriz de autoridad: `spec/roles.md` y `spec/process-definition.md` → `business-analyst`.

## [2.6.0] - 2026-08-23

### Added
- **Diagramas como mecanismo de aceptación de cambios** (`sdlc-diagrams` gana `scripts/`): ningún diagrama cuenta como válido sin recibo de aprobación del rol dueño sobre su contenido. Dos direcciones con gobierno distinto:
  - **Derivados de fuente** (se recrean, nunca se editan a mano): la regeneración propone el cambio → el diff en Git se revisa → el rol dueño lo acepta con `receipt.py emit --role <rol>`.
  - **De diseño** (C4, BPMN, secuencia, Gantt, GitFlow): edición manual, pero si la spec que representan cambia, `spec_diff_impact.py` revoca su recibo y deben re-aprobarse.
- **`iac_to_diagram.py`** (generate/check): topología de despliegue derivada de `terraform.tfstate` (lo realmente desplegado) o ARM/Bicep compilado, con iconos oficiales AWS/Azure/GCP y clusters por módulo/resource group. Python stdlib puro — no ejecuta Terraform. `check` = drift detection (exit 1 si el diagrama difiere de la fuente).
- **`pipeline_diagram.py`** (generate/validate/check): flowchart Mermaid por workflow de GitHub Actions (triggers, jobs, `needs:`) + validación de `needs:` inexistentes y ciclos de dependencias sin binarios externos.
- **`diagram_render.py`** (render/render-dir/engines): render headless a SVG/PNG vía drawio-desktop CLI (el SVG embebe el fuente: la imagen sigue editable) o mmdc (renderiza bloques Mermaid dentro de Markdown y reescribe las referencias — doc-as-code). Motores opcionales con degradación elegante: sin ellos, el fuente versionado sigue siendo el entregable.
- Matriz de autoridad: `spec/diagrams/despliegue.drawio` → `cloud-engineer`; `spec/diagrams/pipeline-cicd.md` → `devops-engineer`.
- Orquestador: sección "Diagramas como mecanismo de aceptación"; GATE 3 exige diagramas derivados regenerados y con recibo vigente; Fase 8 verifica drift (`check`) en el cierre.

### Changed
- `harness_doctor.py`: compila los 3 scripts de `sdlc-diagrams` y reporta motores de render disponibles (informativo, nunca bloquea).

## [2.5.0] - 2026-08-23

### Added
- **Sprint Review** (`sprint_review.py`, script 16 del orquestador): reporte versionado de cierre de sprint en `spec/reports/sprint-review-NN.md` (un archivo por sprint → serie histórica). Secciones: resumen ejecutivo, avance del proyecto (aprobados por gate + recibos rehechos), desempeño del arnés (embebe las métricas de skills de v2.4), lead time por gate (timestamps de recibos), **tendencia vs sprint anterior** (KPIs embebidos como comentarios que el propio script relee) y aprendizajes/acciones.
- Relación de artefactos: `METRICS.md` = tablero vivo (se sobrescribe); `sprint-review-NN.md` = snapshot histórico; `impact-report.md` (product-analyst) = impacto de negocio — se enlaza, no se duplica.
- Fase 8: el paso de métricas ahora genera el Sprint Review (obligatorio al cerrar cada sprint).

### Changed
- `harness_doctor.py`: 14 scripts del orquestador (antes 13).

## [2.4.0] - 2026-08-23

### Added
- **Telemetría de skills** (`skill_metrics.py`, script 15 del orquestador): medición del aporte y la disciplina de las skills sin meter telemetría en el contexto del agente (escritura por CLI en comandos existentes; lectura bajo demanda).
  - `use --skill <rol> --fase <N>`: registro append-only de activaciones en `spec/metrics/usage.jsonl`.
  - `report` → `spec/METRICS.md` con tres vistas: **aporte** (artefactos con recibo, % gates al primer intento, tokens por skill), **cobertura** (detector de *freestyle*: rol con artefactos sin activación registrada = trabajo fuera de la skill; activación sin artefactos = skill de adorno) y **señales** accionables para mejorar skills.
- `receipt.py emit`: telemetría opcional `--tokens-in/-out --tokens-src reportado|estimado --attempts K`. Tokens exactos cuando la plataforma del agente los expone; estimación chars/4 calculada por el script cuando no — nunca depende de la narración del agente.
- Fase 8: el orquestador genera `METRICS.md` y guarda las señales como memoria `learning` (mejora continua de las skills).

### Changed
- `harness_doctor.py`: 13 scripts del orquestador (antes 12).
- README §4d y Guía §5f documentan la versión.

## [2.3.1] - 2026-08-23

### Added
- `spec_index.py`: el `spec/INDEX.md` generado incluye ahora un bloque "Cómo leer este repo" (4 reglas: spec como fuente de verdad, recibos SHA-256, consultar `.codeintel` antes de leer código, memorias con `--brief`) — el proyecto se auto-explica a cualquier agente que aterrice en el repo, sin archivos de instrucciones adicionales (sin AGENTS.md) ni contexto permanente extra.

### Fixed
- `spec_index.py`: el resumen de artefactos no detectaba encabezados markdown en archivos multilínea (faltaba `re.M` en el patrón) y caía al fallback de primera línea.

## [2.3.0] - 2026-08-22

### Added
- **`code_intel.py`** (orquestador): mini motor de inteligencia de código propio (inspirado en Gortex, reimplementado a medida). Grafo de símbolos en SQLite derivable (`.codeintel/index.db`, gitignored, incremental por SHA-256), Python stdlib puro, sin daemon. Extracción por niveles: `ast` para Python (fidelidad total) + patrones para 15 lenguajes más. Comandos: `index`, `symbol`, `context` (cuerpo exacto del símbolo o esqueleto del archivo), `impact` (blast radius BFS con razón por arista), `tests` (tests candidatos, evidencia para GATE 2), `search` (FTS5 sobre firmas/docstrings), `map`, `stats`.
- **`spec_index.py`** (orquestador): genera `spec/INDEX.md`, digest de una página con sha256, tamaño y resumen por artefacto — el agente se orienta leyendo un archivo y solo abre lo que necesita (verificando recibo).
- **`context_packager.py`**: antepone `spec/INDEX.md` al paquete y, para roles de desarrollo con índice disponible, instruye consultar símbolos vía `code_intel.py` en vez de leer archivos completos (`--code-root`).
- **`mem.py search --brief`**: una línea por memoria (id + título); abrir con `mem.py get` solo la relevante.
- Orquestador: sección "Contexto mínimo e inteligencia de código"; GATE 2 acepta `code_intel.py tests` como evidencia de cobertura de tests; change-request combina `spec_diff_impact.py` (spec) + `code_intel.py impact` (código).

### Changed
- `harness_doctor.py`: 12 scripts del orquestador (antes 10), chequea `.codeintel/` en `.gitignore` y existencia del índice.

## [2.2.0] - 2026-08-20

### Added
- **Matriz de autoridad** (`spec/authority-matrix.yaml`, plantilla en `sdlc-orchestrator/assets/`): un rol dueño por artefacto de la spec; cambiarla requiere PR (gobierno auditado).
- **Recibos con rol**: `receipt.py emit --role <rol>` rechaza la emisión si el rol no es el owner declarado; `verify` re-valida el rol contra la matriz vigente; `status` muestra el rol emisor.
- **`authority_check.py`** (orquestador): validación standalone de autoría (`--role` o `--author` + `spec/team-roster.yaml`) para CI.
- Plantillas `CODEOWNERS-template` (frontera dura en Git con branch protection), `team-roster-template.yaml` y workflow `ci-spec-governance.yml` (autoridad + gates por PR).

## [2.1.0] - 2026-08-20

### Added
- **`sdlc-solution-architect`** (Fases 0-2): el arquitecto de la iniciativa. Acompaña a negocio/PO/BA a detallar historias, escribe historias técnicas (`spec/technical-stories.md`: enablers, deuda, spikes, NFRs) y elabora la propuesta de arquitectura con opciones, ADRs preliminares y scorecard. Plantillas: `technical-story-template.md`, `architecture-proposal-template.md`.
- **`sdlc-cloud-pricing`** (Fases 0 y 6): estimación CAPEX/OPEX/TCO a 3 años en AWS y Azure, en 3 escenarios (mínimo viable / crecimiento esperado / pico), con supuestos versionados en YAML y fecha de validez de precios. Scripts: `cost_estimator.py`, `unit_prices.py`.
- **GATE 0** (aprobación de la iniciativa): gate humano previo a GATE 1 con tres tipos nuevos en `gate_checker.py` — `architecture-proposal`, `technical-stories`, `cost-estimation`. Los tres artefactos emiten recibo SHA-256.
- **Routing "discovery"**: iniciativa nueva o evolución de producto → PO + BA + Solution Architect + Cloud Pricing → GATE 0.
- Versionado formal del repo con releases: los 21 `.skill` se adjuntan como assets instalables en cada release.

### Changed
- `harness_doctor.py`: espera 21 skills.
- Pipeline: Fase 0 pasa a ser Discovery (PO + BA + Solution Architect + pricing).
- README: licencia con nombre completo del autor; crédito de Engram como "diferencial"; descripción precisa "arnés para agentes".

## [2.0.0] - 2026-08-13

### Added
- **`sdlc-decision-engine`**: framework de decisiones de 8 pasos (Natanzon) con `decision_engine.py` (validación + Decision Packages) y `scorecard_calculator.py`.
- **`sdlc-enterprise-architect`**: Tech Radar (ADOPT/TRIAL/ASSESS/HOLD), Principios Arquitectónicos, gobernanza por excepción, Paved Roads.
- **Risk Tiering** (`decision_sizing.py`): clasifica el Risk Tier (1/2/3) y fija el nivel de gobernanza.
- **Advice Process** (`advisor.py`): stakeholders por impacto; el consejo no es vinculante pero omitirlo bloquea GATE 1.
- **Firma arquitectónica** (`arch_signoff.py`): recibo `ARCH-xxx.json` con hash compuesto ADR + artefactos de diseño.
- `gate_checker.py --tipo adr`: validación semántica de los 8 pasos, Tech Radar y firma vigente.

## [1.1.0] - 2026-08-08

### Added
- **Receipts** (`receipt.py`): recibos SHA-256 emit/verify/status/revoke; invalidación automática al cambiar el artefacto.
- **Routing orgánico**: rutas directo / exploración delegada / hotfix / full-pipeline / change-request.
- **Fase 8 — Archivo**: merge de delta-specs, cierre del ciclo.
- `harness_doctor.py` (health check) y `detect_stack.py` (TDD en pausa sin test runner).
- Perfiles de modelo por fase (`references/model-profiles.md`).

## [1.0.0] - 2026-08-01

### Added
- Versión inicial: 15 skills de roles + `sdlc-memory` (Git-nativa, 3 scopes, políticas y desviaciones, MCP), pipeline Fases -1 a 7, gates 1/2/2.5/3, SDD + TDD.
