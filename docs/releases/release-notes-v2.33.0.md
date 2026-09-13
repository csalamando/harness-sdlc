El inventario de pantallas PANT-01..08 del portal deja de ser degradación elegante: las 8 pantallas están **construidas y verificadas en Penpot** (proyecto «Arnes SDLC — Portal», instancia autoalojada, MCP oficial), con interacciones navegables conectadas, y el artefacto gobernado queda cerrado con el `.penpot` versionado y **recibo GATE 1 vigente** (aprobado por csalamando, 9 checks OK).

### Added
- Prototipo Penpot PANT-01..08 sobre `docs/design-system/tokens.json` (colores y tipografía reales del DS), verificado visualmente pantalla a pantalla
- Interacciones navegables conectadas: PANT-01 → PANT-02, overlays de búsqueda/ayuda (PANT-03/04), resultados → documento
- `docs/design-system/ux/exports/` — 8 renders PNG de revisión reales (sustituyen a los ilustrativos)
- `docs/design-system/ux/prototipo.penpot` — export versionado del proyecto (zip validado, mismo file-id)
- Identificadores canónicos de adaptación (tabla PANT → HU-xx capacidad / ROL-xx rol) para que `gate_checker --tipo screen-inventory` valide el inventario adaptado
- Log de auditoría inicializado (`spec/audit/events.jsonl`)

### Notas
- El `.penpot` se descargó desde la UI (File → Exportar): el RPC de exportación de la instancia local rechazaba la petición y el MCP no exporta archivos. El recibo se re-emitió tras anotarlo en el inventario (revoca el SHA anterior por diseño).
- Sin cambios en skills ni gates: la 2.32.0 ya instalada sigue siendo compatible; este release cierra la Fase 2 (prototipo gobernado) del sistema de diseño.

**Instalación:** descomprime cada `.skill` del ZIP en el directorio de skills de tu agente (Kimi → Skills · Claude Code → `.claude/skills/` · Cursor → `.cursor/skills/` · Codex → `~/.codex/skills/`).
