#!/usr/bin/env python3
"""arch_lint.py — linter de invariantes arquitectónicos del arnés SDLC (v2.21, N9).

Convierte la arquitectura de prosa en política binaria: si el proyecto declara
arquitectura por capas en `spec/architecture-rules.yaml`, este linter verifica
que el código la respete. Sin reglas declaradas no hay nada que verificar
(exit 0 — la regla es condicional a la arquitectura declarada).

Uso:
  python3 arch_lint.py [--root .] [--rules spec/architecture-rules.yaml]
                       [--spec-dir spec/]

Exit 0 = sin violaciones. Exit 1 = violaciones o configuración inválida.

Formato de las reglas (spec/architecture-rules.yaml, owner: software-architect):

  version: 1
  layers:
    - name: ui
      paths: ["frontend/", "src/web/"]
    - name: api
      paths: ["src/api/"]
    - name: domain
      paths: ["src/domain/"]
  forbidden:
    - "domain -> *"        # el dominio no importa a nadie del proyecto
    - "ui -> domain"       # la UI pasa por la API, nunca directa al dominio

Cada regla forbidden es "<origen> -> <destino>" con capas o "*". Violación =
un archivo de la capa origen importa un archivo de la capa destino.

Cobertura: Python vía `ast` (imports absolutos y relativos); JS/TS vía patrones
(`import ... from`, `require(...)`) sobre rutas relativas. Los imports que no
resuelven a archivos del proyecto (librerías externas) se ignoran.

Cada corrida registra un evento `arch_lint` en la memoria de auditoría
(ADR-004) cuando ésta existe: reglas (hash), archivos analizados y violaciones.
"""
import argparse
import ast
import fnmatch
import hashlib
import json
import os
import re
import sys

sys.dont_write_bytecode = True

PY_EXTS = {".py"}
JS_EXTS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist",
             "build", ".codeintel", ".next", "coverage", "spec"}

JS_IMPORT = re.compile(
    r"""^\s*(?:import\b[^'"]*|export\b[^'"]*from\s*|const\s+\w+\s*=\s*require\(|"""
    r"""require\(|import\()\s*['"]([^'"]+)['"]""")


def _audit(spec_dir, **fields):
    """Best-effort: anexa el hecho a la memoria de auditoría si existe."""
    try:
        from audit_log import append_event
        append_event(spec_dir, "arch_lint", **fields)
    except Exception:
        pass  # la auditoría nunca bloquea el lint; el verify de CI la cubre


def load_rules(path):
    """Carga y valida las reglas. Devuelve (layers, forbidden, error)."""
    if not os.path.isfile(path):
        return None, None, None
    try:
        import yaml
    except ImportError:
        return None, None, ("PyYAML no instalado: spec/architecture-rules.yaml existe "
                            "pero no se puede parsear. Instalar PyYAML o retirar las reglas — "
                            "un control que no se puede ejecutar no es control.")
    try:
        data = yaml.safe_load(open(path, encoding="utf-8").read()) or {}
    except Exception as e:
        return None, None, f"architecture-rules.yaml inválido: {e}"
    layers = data.get("layers") or []
    forbidden = data.get("forbidden") or []
    names = set()
    for l in layers:
        if not l.get("name") or not l.get("paths"):
            return None, None, f"capa sin name/paths: {l!r}"
        names.add(l["name"])
    rules = []
    for f in forbidden:
        m = re.match(r"^\s*([\w*]+)\s*->\s*([\w*]+)\s*$", str(f))
        if not m:
            return None, None, f"regla forbidden inválida (formato 'capa -> capa'): {f!r}"
        a, b = m.group(1), m.group(2)
        for x in (a, b):
            if x != "*" and x not in names:
                return None, None, f"regla '{a} -> {b}' cita capa no declarada: '{x}'"
        rules.append((a, b))
    return layers, rules, None


def layer_of(relpath, layers):
    """Capa de un archivo (ruta relativa con '/'): primer prefijo que calza."""
    rel = relpath.replace(os.sep, "/")
    for l in layers:
        for p in l["paths"]:
            p = p.replace("\\", "/")
            if rel.startswith(p.rstrip("/") + "/") or fnmatch.fnmatch(rel, p):
                return l["name"]
    return None


def iter_sources(root):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            ext = os.path.splitext(f)[1]
            if ext in PY_EXTS | JS_EXTS:
                yield os.path.join(base, f)


# ── Resolución de imports a archivos del proyecto ────────────────────────────

def _module_to_path(root, module):
    """'a.b.c' -> <root>/a/b/c.py (o paquete), probando también bajo src/."""
    parts = module.split(".")
    for base in (root, os.path.join(root, "src")):
        p = os.path.join(base, *parts)
        if os.path.isfile(p + ".py"):
            return p + ".py"
        if os.path.isfile(os.path.join(p, "__init__.py")):
            return os.path.join(p, "__init__.py")
    return None


def py_imports(root, path):
    """Imports de un .py resueltos a rutas de archivo del proyecto."""
    try:
        tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
    except (SyntaxError, OSError):
        return
    for node in ast.walk(tree):
        target = None
        if isinstance(node, ast.Import):
            for a in node.names:
                t = _module_to_path(root, a.name)
                if t:
                    yield t
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relativo: from .x import y / from .. import z
                pkg = os.path.dirname(path)
                for _ in range(node.level - 1):
                    pkg = os.path.dirname(pkg)
                target = os.path.join(pkg, *(node.module or "").split(".")) \
                    if node.module else pkg
                for cand in (target + ".py", os.path.join(target, "__init__.py")):
                    if os.path.isfile(cand):
                        yield cand
                        break
            elif node.module:
                t = _module_to_path(root, node.module)
                if t:
                    yield t


def js_imports(root, path):
    """Imports relativos de un JS/TS resueltos a archivos del proyecto."""
    try:
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        return
    exts = ["", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
            "/index.js", "/index.ts", "/index.tsx"]
    for ln in lines:
        m = JS_IMPORT.match(ln)
        if not m or not m.group(1).startswith("."):
            continue  # librerías externas: fuera del invariante
        base = os.path.normpath(os.path.join(os.path.dirname(path), m.group(1)))
        for e in exts:
            cand = base + e
            if os.path.isfile(cand):
                yield cand
                break


def main():
    ap = argparse.ArgumentParser(description="Linter de invariantes arquitectónicos (N9)")
    ap.add_argument("--root", default=".", help="raíz del código del proyecto")
    ap.add_argument("--rules", default=None,
                    help="ruta a architecture-rules.yaml (default: <spec-dir>/architecture-rules.yaml)")
    ap.add_argument("--spec-dir", default="spec/", help="directorio de la spec")
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    rules_path = a.rules or os.path.join(a.spec_dir, "architecture-rules.yaml")

    layers, forbidden, err = load_rules(rules_path)
    if err:
        print(f"FALLO (config): {err}")
        sys.exit(1)
    if layers is None:
        print("arch_lint: sin architecture-rules.yaml — el proyecto no declara "
              "arquitectura por capas; nada que verificar.")
        sys.exit(0)
    if not forbidden:
        print("arch_lint: reglas declaradas sin lista 'forbidden' — "
              "una política sin prohibiciones no controla nada.")
        sys.exit(1)

    violations, scanned = [], 0
    for f in iter_sources(root):
        rel = os.path.relpath(f, root)
        src_layer = layer_of(rel, layers)
        if not src_layer:
            continue
        scanned += 1
        imports = py_imports(root, f) if f.endswith(".py") else js_imports(root, f)
        for t in imports or ():
            tlayer = layer_of(os.path.relpath(t, root), layers)
            if not tlayer or tlayer == src_layer:
                continue
            for fa, fb in forbidden:
                if (fa in (src_layer, "*")) and (fb in (tlayer, "*")):
                    violations.append(
                        f"{rel} ({src_layer}) importa {os.path.relpath(t, root)} ({tlayer})"
                        f" — prohibido por '{fa} -> {fb}'")

    rules_hash = ""
    try:
        rules_hash = hashlib.sha256(open(rules_path, "rb").read()).hexdigest()[:16]
    except OSError:
        pass
    _audit(a.spec_dir, reglas=os.path.basename(rules_path), sha256=rules_hash,
           archivos=str(scanned), violaciones=str(len(violations)),
           resultado="fallo" if violations else "ok")

    if violations:
        print(f"ARCH LINT: {len(violations)} violación(es) de los invariantes "
              f"declarados ({os.path.basename(rules_path)} sha256:{rules_hash}):")
        for v in sorted(set(violations)):
            print(f"  - {v}")
        print("La arquitectura aprobada no lo permite: mueve el código, ajusta el "
              "import, o cambia las reglas vía PR con recibo del software-architect.")
        sys.exit(1)
    print(f"ARCH LINT OK: {scanned} archivos en capas, 0 violaciones "
          f"({os.path.basename(rules_path)} sha256:{rules_hash}).")
    sys.exit(0)


if __name__ == "__main__":
    main()
