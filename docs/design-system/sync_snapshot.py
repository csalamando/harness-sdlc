#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sync_snapshot.py — Inyecta tokens.json como snapshot embebido de design_tokens.py.

Tras editar docs/design-system/tokens.json hay que:
  1. subir meta.version si el cambio lo amerita
  2. correr este script (regenera el snapshot embebido)
  3. design_tokens.py --check  (valida estructura, paridad y contraste AA)

Uso:  python docs/design-system/sync_snapshot.py
"""

import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[2]
TOKENS = RAIZ / "docs" / "design-system" / "tokens.json"
TARGET = RAIZ / "skills" / "sdlc-orchestrator" / "scripts" / "design_tokens.py"

INICIO = "_SNAPSHOT_JSON = r'''\n"
FIN = "\n'''"


def main() -> int:
    doc = json.dumps(json.loads(TOKENS.read_text(encoding="utf-8")),
                     ensure_ascii=False, indent=1)
    s = TARGET.read_text(encoding="utf-8")
    i = s.index(INICIO) + len(INICIO)
    j = s.index(FIN, i)
    s = s[:i] + doc + s[j:]
    TARGET.write_text(s, encoding="utf-8")
    print(f"snapshot sincronizado: {TARGET.name} <- tokens.json "
          f"v{json.loads(doc)['meta']['version']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
