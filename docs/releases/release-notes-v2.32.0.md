Toda la UI HTML que genera el arnés (portal, inicio/dashboard, diagramas IR, grafo de pipeline y de código) pasa a derivar de **tokens canónicos únicos** en `docs/design-system/tokens.json`, con contraste WCAG AA verificado por script. Adiós a los ~285 colores hardcodeados y a las 4 copias del bloque `:root`.

### Added
- `docs/design-system/tokens.json` (v1.0.0) — fuente única (Style Dictionary simplificado): color dual-tema, tipografía system-ui, espaciado, radios, sombras, motion, paletas dataviz; `audit.pairs-aa` con 19 pares verificados
- `docs/design-system/design-system.md` — principios, catálogo de componentes, los 4 estados por superficie, contrato de accesibilidad
- `skills/sdlc-orchestrator/scripts/design_tokens.py` — emite `:root` por subset (core/graph/diagram/all); `--check` valida estructura, paridad y AA
- `docs/design-system/ux/` — inventario PANT-01..08, styleguide vivo, renders de revisión
- Portal v1.5.1: focus-visible, prefers-reduced-motion, ARIA, estado loading, `--muted-aa`, soporte `?tema=`
- Self-test `[9i]`: 14 checks nuevos — **329 checks OK, 0 fallos**

### Changed
- `portal_lib.py`, `harness_graph.py` (dual-tema, 0 hex fuera de tokens), `diagram_ir.py`, `code_graph.py` consumen tokens con fallbacks verificados
- `?tema=claro|oscuro` funciona en todo (portal, diagramas, grafo)

### Fixed
- `gate_checker.check_sprint_learning`: memoria anclada al proyecto del artefacto, no al cwd
- 5 pares que fallaban AA migrados a `--muted-aa` (3.9:1 → 6.5:1)

**Instalación:** descomprime cada `.skill` del ZIP en el directorio de skills de tu agente (Kimi → Skills · Claude Code → `.claude/skills/` · Cursor → `.cursor/skills/` · Codex → `~/.codex/skills/`).
