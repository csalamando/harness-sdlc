# Publicación doc-as-code (GitHub Wiki, Pages, Confluence)

El Technical Writer produce Markdown versionado en `docs/` (fuente de verdad). La **publicación es derivada**: mismo contenido, varios destinos. Prioridad del arnés: Wiki primero (mínimo esfuerzo), Pages después (sitio completo), Confluence como integración empresarial posterior.

## Matriz de destinos

| Destino | Qué publicar | Cuándo | Mecanismo |
|---|---|---|---|
| **GitHub Wiki** | Guías de contribución, decisiones, onboarding-dev, runbooks | Desde el primer sprint | La Wiki ES un repo Git: `<repo-url>.wiki.git`. Clonar, copiar .md, push |
| **GitHub Pages** | Sitio completo: user-guide, api-reference, docs/ | Cuando haya usuarios externos o stakeholders sin acceso al repo | MkDocs (recomendado) o Jekyll/Docusaurus + GitHub Actions |
| **Confluence** | Espacios corporativos (audiencia no técnica) | Cuando la org lo pida | Action `markdown-confluence` o API REST vía pipeline |

Restricciones GitHub (verificar vigencia al configurar): Pages gratis en repos públicos y privados; sitios ≤1GB recomendado, archivos <100MB, ~10 builds/hora; en repo privado el sitio Pages puede quedar público salvo plan Enterprise con access control — **no publicar spec interna sensible en Pages de repo privado sin verificar visibilidad**.

## 1. GitHub Wiki (prioridad 1)

La Wiki es un repositorio Git independiente: `https://github.com/<org>/<repo>.wiki.git`.

```bash
git clone https://github.com/<org>/<repo>.wiki.git wiki-publish/
cp docs/onboarding-dev.md docs/runbook.md wiki-publish/
# Home.md = índice; _Sidebar.md = navegación lateral
cd wiki-publish && git add . && git commit -m "docs: sync sprint N" && git push
```

Convención del arnés:
- `Home.md`: índice generado desde `docs/` (script `scripts/build_wiki_index.py` o manual).
- `_Sidebar.md`: navegación fija (Home, Onboarding, Runbook, ADRs destacados).
- Solo documentación *de colaborador*: la Wiki NO recibe la spec completa ni documentos de usuario final (eso va a Pages).
- Sync por sprint (manual o workflow), no por commit: evitar ruido.
- Alternativa sin terminal: la Wiki se edita también vía web, pero el arnés prefiere el push Git para mantener docs/ como fuente única.

## 2. GitHub Pages con MkDocs (prioridad 2)

Asset base: `assets/mkdocs.yml` + workflow `assets/gh-pages-docs.yml`.

```bash
pip install mkdocs mkdocs-material
# mkdocs.yml en la raíz apunta docs_dir: docs
mkdocs build        # validación local
# El workflow publica a gh-pages en cada push a main que toque docs/**
```

- `nav` del mkdocs.yml se deriva de la estructura de `docs/`; la API reference se regenera desde `api-contract.yaml` (Redoc) **en el pipeline**, no se commitea el HTML.
- Diagramas: referenciar los `.drawio` exportados a SVG (exportar en CI con drawio-desktop headless o incluir el PNG exportado por la skill sdlc-diagrams) — nunca screenshots.
- Versionado del sitio con `mike` (opcional) cuando el producto tenga releases.

## 3. Confluence (fase posterior)

Sin prisa: activarlo cuando la audiencia corporativa lo justifique. Dos vías documentadas en `assets/confluence-sync.yml`:

1. **GitHub Action `markdown-confluence`** (o similar del Marketplace): en push a `main` que toque `docs/**`, convierte y publica/actualiza páginas en el espacio Confluence usando API token de Atlassian (secretos `CONFLUENCE_TOKEN`, `CONFLUENCE_BASE_URL`, `CONFLUENCE_SPACE`).
2. **Script propio contra la API REST** (`POST /wiki/rest/api/content`): más control sobre jerarquía de páginas y labels; útil si hay que mapear `docs/` a un árbol de espacio específico.

Regla: Confluence es **espejo de solo-escritura-desde-Git** — se publica desde el repo, jamás se edita en Confluence y se copia de vuelta (rompería la fuente única). Las ediciones manuales en Confluence se pierden en el próximo sync: dejarlo explícito con un banner en la plantilla de página.

## Orquestación con otras skills del arnés

| Skill | Qué aporta a la publicación |
|---|---|
| `sdlc-diagrams` | Diagramas C4/cloud exportados a SVG/PNG que se referencian desde las guías |
| `wiki` (base de conocimiento) | Estructura de páginas interconectadas si la doc crece a conocimiento acumulativo |
| `sdlc-devops-engineer` | Los workflows de publicación viven en `pipelines/` y son suyos: el TW define el contenido, DevOps el mecanismo |
| `sdlc-orchestrator` | Si `api-contract.yaml` o `ux-flows.md` cambian, `spec_diff_impact` marca la doc publicada como impactada → re-publicar en el mismo PR del cambio |
