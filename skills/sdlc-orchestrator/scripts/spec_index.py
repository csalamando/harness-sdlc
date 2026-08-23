#!/usr/bin/env python3
"""spec_index.py — digest de una pagina de la spec (spec/INDEX.md).

Proposito: que el agente se oriente leyendo UN archivo en vez de N. Cada
artefacto aparece con su hash (compatible con receipt.py verify), tamano y
primer encabezado como resumen. El agente solo abre el artefacto que necesita.

Uso: python3 spec_index.py [--spec-dir spec/] [--stdout]
Exit 0 siempre (herramienta informativa).
"""
import argparse
import hashlib
import os
import re

EXTS = (".md", ".yaml", ".yml", ".json")
SKIP_DIRS = {"memory", "receipts", ".index", ".codeintel"}
SKIP_FILES = {"INDEX.md"}
HEADING_RE = re.compile(r"^#{1,3}\s+(.+)$", re.M)


def summarize(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            head = fh.read(4000)
    except OSError:
        return ""
    m = HEADING_RE.search(head)
    if m:
        return m.group(1).strip()[:80]
    if path.endswith((".yaml", ".yml")):
        for line in head.splitlines():
            if line.strip() and not line.startswith("#"):
                return line.strip()[:80]
    for line in head.splitlines():
        if line.strip():
            return line.strip()[:80]
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec-dir", default="spec/")
    ap.add_argument("--stdout", action="store_true", help="no escribir INDEX.md, solo imprimir")
    a = ap.parse_args()
    spec = os.path.abspath(a.spec_dir)
    if not os.path.isdir(spec):
        print(f"NO EXISTE: {spec}")
        return 1
    rows = []
    n_mem = n_rcp = 0
    for dirpath, dirnames, filenames in os.walk(spec):
        rel_dir = os.path.relpath(dirpath, spec)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(filenames):
            if not fn.endswith(EXTS) or fn in SKIP_FILES:
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.normpath(os.path.join(rel_dir, fn)) if rel_dir != "." else fn
            data = open(full, "rb").read()
            sha = hashlib.sha256(data).hexdigest()[:12]
            lines = data.decode("utf-8", errors="replace").count("\n") + 1
            rows.append((rel.replace(os.sep, "/"), sha, lines, summarize(full)))
    mem_dir = os.path.join(spec, "memory", "entries")
    if os.path.isdir(mem_dir):
        n_mem = sum(1 for f in os.listdir(mem_dir) if f.endswith(".md"))
    rcp_dir = os.path.join(spec, "receipts")
    if os.path.isdir(rcp_dir):
        n_rcp = sum(1 for f in os.listdir(rcp_dir) if f.endswith(".json"))
    out = [
        "# INDEX — digest de la spec",
        "",
        "Lectura de orientacion: este digest resume cada artefacto. Abre solo el que necesites;",
        "antes de consumirlo downstream verifica su recibo (`receipt.py verify`) — el hash aqui",
        "debe coincidir con el recibo ACTIVE.",
        "",
        "Como leer este repo (para cualquier agente, con o sin el arnes instalado):",
        "- `spec/` es la fuente de verdad: no improvises artefactos fuera de esta estructura.",
        "- Toda aprobacion es un recibo SHA-256 en `spec/receipts/`; si el hash no coincide,",
        "  el artefacto cambio y el gate debe re-ejecutarse.",
        "- Si existe `.codeintel/index.db`, consulta simbolos (`code_intel.py context/impact/tests`)",
        "  en vez de leer archivos de codigo completos.",
        "- Las memorias explican el POR QUE de las decisiones; busca con `mem.py search --brief`",
        "  y abre solo la relevante con `mem.py get <id>`.",
        "",
        "| Artefacto | sha256[:12] | lineas | resumen |",
        "|---|---|---|---|",
    ]
    for rel, sha, lines, summ in sorted(rows):
        out.append(f"| `{rel}` | {sha} | {lines} | {summ} |")
    out += ["",
            f"Memorias: {n_mem} en `spec/memory/entries/` (buscar con `mem.py search --brief`).",
            f"Recibos: {n_rcp} en `spec/receipts/` (ver `receipt.py status`).",
            ""]
    text = "\n".join(out)
    print(text)
    if not a.stdout:
        with open(os.path.join(spec, "INDEX.md"), "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"INDEX.md actualizado ({len(rows)} artefactos).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
