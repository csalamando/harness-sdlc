#!/usr/bin/env python3
"""
code_intel.py — mini motor de inteligencia de codigo del arnes SDLC.

Inspirado en Gortex (https://github.com/zzet/gortex), reimplementado a nuestra
medida bajo la filosofia del arnes: Python 3 stdlib puro, sin daemon, indice
SQLite derivable (se gitignora y se reconstruye), salidas compactas para
ahorrar contexto del agente.

Comandos:
  index    [--root .]            Indexa/reindexa incremental (por sha256).
  symbol   NAME                  Definiciones de un simbolo (archivo:linea).
  context  TARGET                Simbolo: cuerpo exacto + calls. Archivo: esqueleto.
  impact   TARGET [--depth 3]    Blast radius: quien depende de esto (BFS inverso).
  tests    TARGET                Tests candidatos a correr para un simbolo/archivo.
  search   QUERY [--limit 10]    Busqueda FTS5 sobre nombres/firmas/docstrings.
  map                            Resumen por directorio (comunidades ligeras).
  stats                          Conteos del indice.

Sin dependencias externas. El indice vive en <root>/.codeintel/index.db.
"""
import argparse
import ast
import hashlib
import os
import re
import sqlite3
import sys

DB_DIR = ".codeintel"
DB_NAME = "index.db"
IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
    ".index", ".codeintel", ".next", "target", "out", ".idea", ".vscode",
}
PY_EXT = ".py"
REGEX_LANGS = {
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".go": "go", ".java": "java", ".kt": "kotlin", ".rs": "rust",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp", ".cc": "cpp",
    ".rb": "ruby", ".php": "php", ".cs": "csharp", ".swift": "swift",
}
TEST_PAT = re.compile(
    r"(^|/)(tests?/|__tests__/|specs?/)|(_test\.|\.test\.|\.spec\.|^test_|_test$)"
)
CALL_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
NOISE_CALLS = {
    "if", "for", "while", "switch", "catch", "return", "sizeof", "function",
    "func", "def", "fn", "class", "new", "else", "do", "elif", "print",
    "len", "str", "int", "float", "list", "dict", "set", "tuple", "type",
    "isinstance", "range", "enumerate", "zip", "open", "super", "self",
}

DEF_PATTERNS = [
    (re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)"), "function"),
    (re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[\w$]+)\s*=>"), "function"),
    (re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)\s*\("), "function"),          # go
    (re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_]\w*)"), "function"),           # rust
    (re.compile(r"^\s*def\s+([A-Za-z_]\w*)"), "function"),                                   # ruby
    (re.compile(r"^\s*(?:export\s+)?(?:abstract\s+)?(?:final\s+)?class\s+([A-Za-z_]\w*)"), "class"),
    (re.compile(r"^\s*(?:export\s+)?interface\s+([A-Za-z_]\w*)"), "interface"),
    (re.compile(r"^\s*(?:public|private|protected|internal)\s+(?:static\s+)?(?:async\s+)?[\w<>\[\],.? ]+?\s+([A-Za-z_]\w*)\s*\("), "method"),  # java/c#
    (re.compile(r"^\s*(?:public\s+)?(?:static\s+)?function\s+([A-Za-z_]\w*)\s*\("), "function"),  # php
]
IMPORT_PATTERNS = [
    re.compile(r"^\s*import\s+.*?\sfrom\s+['\"]([^'\"]+)"),
    re.compile(r"^\s*import\s+['\"]([^'\"]+)"),
    re.compile(r"^\s*import\s+([\w.]+)"),
    re.compile(r"require\(\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"^\s*use\s+([\w:]+)"),
    re.compile(r"^\s*#include\s+[<\"]([^>\"]+)"),
    re.compile(r"^\s*require\s+['\"]([^'\"]+)['\"]"),
    re.compile(r"^\s*using\s+([\w.]+)\s*;"),
]

# ---------------------------------------------------------------- extraction

def _mk_sym(path, name, kind, line_start, line_end, signature, doc):
    return (path, name, kind, line_start, line_end, signature.strip(), (doc or "")[:300])


def extract_python(src, path):
    syms, calls, imports = [], set(), set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return syms, calls, imports
    lines = src.splitlines()

    class V(ast.NodeVisitor):
        def __init__(self):
            self.stack = []

        def visit_ClassDef(self, node):
            sig = lines[node.lineno - 1] if node.lineno - 1 < len(lines) else ""
            syms.append(_mk_sym(path, node.name, "class", node.lineno,
                                node.end_lineno or node.lineno, sig,
                                ast.get_docstring(node)))
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_FunctionDef(self, node):
            self._fn(node)

        def visit_AsyncFunctionDef(self, node):
            self._fn(node)

        def _fn(self, node):
            kind = "method" if self.stack else "function"
            sig = lines[node.lineno - 1] if node.lineno - 1 < len(lines) else ""
            syms.append(_mk_sym(path, node.name, kind, node.lineno,
                                node.end_lineno or node.lineno, sig,
                                ast.get_docstring(node)))
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_Call(self, node):
            f = node.func
            if isinstance(f, ast.Name):
                calls.add(f.id)
            elif isinstance(f, ast.Attribute):
                calls.add(f.attr)
            self.generic_visit(node)

        def visit_Import(self, node):
            for a in node.names:
                imports.add(a.name)

        def visit_ImportFrom(self, node):
            if node.module:
                imports.add(node.module)
            for a in node.names:
                imports.add(a.name)

    V().visit(tree)
    return syms, calls - NOISE_CALLS, imports


def extract_generic(src, path):
    syms, calls, imports = [], set(), set()
    lines = src.splitlines()
    open_def = None  # index into syms awaiting an end line
    for i, line in enumerate(lines, start=1):
        if open_def is not None:
            prev = list(syms[open_def])
            prev[4] = i - 1
            syms[open_def] = tuple(prev)
            open_def = None
        for pat, kind in DEF_PATTERNS:
            m = pat.match(line)
            if m:
                syms.append(_mk_sym(path, m.group(1), kind, i, i, line, ""))
                open_def = len(syms) - 1
                break
        for pat in IMPORT_PATTERNS:
            m = pat.match(line)
            if m:
                imports.add(m.group(1))
                break
    for m in CALL_RE.finditer(src):
        calls.add(m.group(1))
    return syms, calls - NOISE_CALLS, imports


def extract(path, src):
    if path.endswith(PY_EXT):
        return extract_python(src, path)
    return extract_generic(src, path)


# ---------------------------------------------------------------- index

SCHEMA = """
CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, sha TEXT, lang TEXT, mtime REAL);
CREATE TABLE IF NOT EXISTS symbols(file TEXT, name TEXT, kind TEXT,
                                   line_start INT, line_end INT, signature TEXT, doc TEXT);
CREATE INDEX IF NOT EXISTS idx_sym_name ON symbols(name);
CREATE INDEX IF NOT EXISTS idx_sym_file ON symbols(file);
CREATE TABLE IF NOT EXISTS edges(file TEXT, kind TEXT, target TEXT);
CREATE INDEX IF NOT EXISTS idx_edge_file ON edges(file);
CREATE INDEX IF NOT EXISTS idx_edge_target ON edges(target);
"""


def db_path(root):
    return os.path.join(root, DB_DIR, DB_NAME)


def connect(root):
    os.makedirs(os.path.join(root, DB_DIR), exist_ok=True)
    con = sqlite3.connect(db_path(root))
    con.executescript(SCHEMA)
    con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS symbols_fts USING fts5(name, signature, doc)")
    return con


def lang_of(path):
    if path.endswith(PY_EXT):
        return "python"
    return REGEX_LANGS.get(os.path.splitext(path)[1], "")


def iter_sources(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for fn in filenames:
            ext = os.path.splitext(fn)[1]
            if ext == PY_EXT or ext in REGEX_LANGS:
                full = os.path.join(dirpath, fn)
                yield os.path.relpath(full, root), full


def _drop_file(con, rel):
    rowids = [r[0] for r in con.execute("SELECT rowid FROM symbols WHERE file=?", (rel,))]
    for rid in rowids:
        con.execute("DELETE FROM symbols_fts WHERE rowid=?", (rid,))
    con.execute("DELETE FROM symbols WHERE file=?", (rel,))
    con.execute("DELETE FROM edges WHERE file=?", (rel,))
    con.execute("DELETE FROM files WHERE path=?", (rel,))


def cmd_index(root, quiet=False):
    con = connect(root)
    seen, changed, removed, total_syms = set(), 0, 0, 0
    for rel, full in iter_sources(root):
        seen.add(rel)
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as fh:
                src = fh.read()
        except OSError:
            continue
        sha = hashlib.sha256(src.encode("utf-8")).hexdigest()
        row = con.execute("SELECT sha FROM files WHERE path=?", (rel,)).fetchone()
        if row and row[0] == sha:
            continue
        _drop_file(con, rel)
        syms, calls, imports = extract(rel, src)
        con.execute("INSERT INTO files VALUES (?,?,?,?)",
                    (rel, sha, lang_of(rel), os.path.getmtime(full)))
        for s in syms:
            cur = con.execute(
                "INSERT INTO symbols(file,name,kind,line_start,line_end,signature,doc) "
                "VALUES (?,?,?,?,?,?,?)", s)
            con.execute("INSERT INTO symbols_fts(rowid,name,signature,doc) VALUES (?,?,?,?)",
                        (cur.lastrowid, s[1], s[5], s[6]))
        for c in calls:
            con.execute("INSERT INTO edges VALUES (?,?,?)", (rel, "call", c))
        for im in imports:
            con.execute("INSERT INTO edges VALUES (?,?,?)", (rel, "import", im))
        changed += 1
        total_syms += len(syms)
    stale = {r[0] for r in con.execute("SELECT path FROM files")} - seen
    for rel in stale:
        _drop_file(con, rel)
        removed += 1
    con.commit()
    nfiles = con.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    nsyms = con.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]
    nedges = con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    con.close()
    if not quiet:
        print(f"INDEX OK — {nfiles} archivos, {nsyms} simbolos, {nedges} aristas "
              f"(reindexados {changed}, eliminados {removed})")
    return 0

# ---------------------------------------------------------------- queries

def _resolve_import(con, target):
    """Mapea un string de import a rutas indexadas (basename / sufijo)."""
    last = target.rstrip("/").split("/")[-1].split(".")[-1]
    if not last:
        return []
    q = "%/" + last + ".%"
    rows = con.execute(
        "SELECT path FROM files WHERE path LIKE ? OR path LIKE ?",
        (q, last + ".%")).fetchall()
    out = [r[0] for r in rows]
    if not out:  # sufijo completo (rutas tipo app/services/user)
        cand = target.replace(".", "/")
        out = [r[0] for r in con.execute(
            "SELECT path FROM files WHERE path LIKE ?", ("%" + cand + ".%",))]
    return out


def _dependents(con, fileset):
    """Archivos que dependen de cualquiera de fileset (import o call)."""
    deps = {}
    for f, t in con.execute("SELECT file, target FROM edges WHERE kind='import'"):
        for p in _resolve_import(con, t):
            if p in fileset and f not in fileset:
                deps.setdefault(f, set()).add(f"importa {p}")
    marks = ",".join("?" * len(fileset))
    q = f"""SELECT DISTINCT e.file, e.target, s.file FROM edges e
            JOIN symbols s ON s.name = e.target
            WHERE e.kind='call' AND s.file IN ({marks})
            AND NOT EXISTS (SELECT 1 FROM symbols s2
                            WHERE s2.name = e.target AND s2.file = e.file)"""
    for ef, name, sf in con.execute(q, tuple(fileset)):
        if ef not in fileset:
            deps.setdefault(ef, set()).add(f"llama {name}() ({sf})")
    return deps


def _target_files(con, target):
    if con.execute("SELECT 1 FROM files WHERE path=?", (target,)).fetchone():
        return {target}, None
    rows = con.execute("SELECT DISTINCT file FROM symbols WHERE name=?",
                       (target,)).fetchall()
    return {r[0] for r in rows}, rows


def cmd_symbol(con, name):
    rows = con.execute(
        "SELECT file, kind, line_start, signature FROM symbols WHERE name=? "
        "ORDER BY file", (name,)).fetchall()
    if not rows:
        print(f"SIN RESULTADOS: simbolo '{name}' no esta en el indice.")
        return 1
    for f, k, ln, sig in rows:
        print(f"{f}:{ln}  [{k}]  {sig}")
    return 0


def cmd_context(root, con, target):
    rows = con.execute(
        "SELECT file, name, kind, line_start, line_end, signature, doc "
        "FROM symbols WHERE name=? OR file=? ORDER BY file, line_start",
        (target, target)).fetchall()
    if not rows:
        print(f"SIN RESULTADOS: '{target}' ni es simbolo ni archivo indexado.")
        return 1
    by_file = {}
    for r in rows:
        by_file.setdefault(r[0], []).append(r)
    for f, syms in by_file.items():
        is_file_query = target == f
        print(f"== {f} ==")
        try:
            with open(os.path.join(root, f), encoding="utf-8", errors="replace") as fh:
                lines = fh.read().splitlines()
        except OSError:
            lines = []
        for _, name, kind, ls, le, sig, doc in syms:
            if is_file_query:  # esqueleto: solo firmas
                print(f"  {ls:>4} [{kind}] {sig}")
            else:            # simbolo: cuerpo exacto
                print(f"-- {name} [{kind}] {f}:{ls}-{le}")
                if doc:
                    print(f'   """{doc.splitlines()[0]}"""')
                if lines and f.endswith(PY_EXT):
                    for ln in range(ls, min(le, ls + 60) + 1):
                        if ln - 1 < len(lines):
                            print(lines[ln - 1])
        if not is_file_query:
            called = [r[0] for r in con.execute(
                "SELECT DISTINCT target FROM edges WHERE file=? AND kind='call'",
                (f,))]
            known = [c for c in called if con.execute(
                "SELECT 1 FROM symbols WHERE name=? AND file != ? LIMIT 1",
                (c, f)).fetchone()]
            if known:
                print(f"   calls: {', '.join(sorted(known)[:15])}")
    return 0


def cmd_impact(con, target, depth):
    seeds, rows = _target_files(con, target)
    if not seeds:
        print(f"SIN RESULTADOS: '{target}' no esta en el indice.")
        return 1
    print(f"BLAST RADIUS de '{target}' (profundidad {depth}):")
    frontier, seen, total = set(seeds), set(seeds), 0
    for lvl in range(1, depth + 1):
        deps = _dependents(con, frontier)
        nuevos = {f: why for f, why in deps.items() if f not in seen}
        if not nuevos:
            break
        print(f"  nivel {lvl}:")
        for f, why in sorted(nuevos.items()):
            print(f"    {f}  ({'; '.join(sorted(why))})")
        seen |= set(nuevos)
        frontier = set(nuevos)
        total += len(nuevos)
    print(f"  TOTAL: {total} archivo(s) impactados; {len(seeds)} semilla(s): "
          + ", ".join(sorted(seeds)))
    return 0


def cmd_tests(con, target):
    seeds, _ = _target_files(con, target)
    if not seeds:
        print(f"SIN RESULTADOS: '{target}' no esta en el indice.")
        return 1
    stems = {os.path.splitext(os.path.basename(f))[0] for f in seeds}
    nivel1 = _dependents(con, seeds)
    nivel2 = _dependents(con, set(nivel1) | seeds) if nivel1 else {}
    deps = dict(nivel1)
    deps.update(nivel2)
    scored = {}
    for (tf,) in con.execute("SELECT path FROM files"):
        base = os.path.basename(tf)
        if not TEST_PAT.search("/" + tf) and not TEST_PAT.search(base):
            continue
        score = 0
        tstem = (base.replace("test_", "").replace("_test", "")
                 .replace(".test", "").replace(".spec", ""))
        tstem = os.path.splitext(tstem)[0]
        if tstem in stems:
            score += 1
        if tf in deps:
            score += 2
        if score:
            scored[tf] = score
    if not scored:
        print(f"SIN TESTS CANDIDATOS para '{target}'.")
        return 0
    print(f"TESTS CANDIDATOS para '{target}':")
    for f, s in sorted(scored.items(), key=lambda kv: -kv[1]):
        print(f"  [{s}] {f}")
    return 0


def cmd_search(con, query, limit):
    try:
        rows = con.execute(
            "SELECT s.file, s.name, s.kind, s.line_start, s.signature "
            "FROM symbols_fts f JOIN symbols s ON s.rowid = f.rowid "
            "WHERE symbols_fts MATCH ? LIMIT ?",
            (query, limit)).fetchall()
    except sqlite3.OperationalError:
        like = f"%{query}%"
        rows = con.execute(
            "SELECT file, name, kind, line_start, signature FROM symbols "
            "WHERE name LIKE ? OR signature LIKE ? LIMIT ?",
            (like, like, limit)).fetchall()
    if not rows:
        print(f"SIN RESULTADOS para '{query}'.")
        return 1
    for f, n, k, ln, sig in rows:
        print(f"{f}:{ln}  [{k}] {n}  —  {sig[:90]}")
    return 0


def cmd_map(con):
    print("MAPA DEL REPO (directorio / archivos / simbolos / mas llamados):")
    dirs = {}
    for f, n in con.execute("SELECT file, name FROM symbols"):
        d = os.path.dirname(f) or "."
        dirs.setdefault(d, {"files": set(), "syms": 0})
        dirs[d]["files"].add(f)
        dirs[d]["syms"] += 1
    top_calls = {}
    for (t,) in con.execute("SELECT target FROM edges WHERE kind='call'"):
        top_calls[t] = top_calls.get(t, 0) + 1
    hot = sorted(top_calls.items(), key=lambda kv: -kv[1])[:8]
    for d in sorted(dirs, key=lambda k: -dirs[k]["syms"]):
        v = dirs[d]
        print(f"  {d:<40} {len(v['files']):>3} archivos  {v['syms']:>4} simbolos")
    if hot:
        print("  mas llamados: " + ", ".join(f"{n}({c})" for n, c in hot))
    return 0


def cmd_stats(con):
    for label, q in [("archivos", "SELECT COUNT(*) FROM files"),
                     ("simbolos", "SELECT COUNT(*) FROM symbols"),
                     ("aristas", "SELECT COUNT(*) FROM edges")]:
        print(f"  {label}: {con.execute(q).fetchone()[0]}")
    return 0


# ---------------------------------------------------------------- cli

def main():
    ap = argparse.ArgumentParser(prog="code_intel.py")
    ap.add_argument("--root", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("index")
    p = sub.add_parser("symbol"); p.add_argument("name")
    p = sub.add_parser("context"); p.add_argument("target")
    p = sub.add_parser("impact"); p.add_argument("target"); p.add_argument("--depth", type=int, default=3)
    p = sub.add_parser("tests"); p.add_argument("target")
    p = sub.add_parser("search"); p.add_argument("query"); p.add_argument("--limit", type=int, default=10)
    sub.add_parser("map")
    sub.add_parser("stats")
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    if a.cmd == "index":
        return cmd_index(root)
    con = connect(root)
    try:
        if a.cmd == "symbol":
            return cmd_symbol(con, a.name)
        if a.cmd == "context":
            return cmd_context(root, con, a.target)
        if a.cmd == "impact":
            return cmd_impact(con, a.target, a.depth)
        if a.cmd == "tests":
            return cmd_tests(con, a.target)
        if a.cmd == "search":
            return cmd_search(con, a.query, a.limit)
        if a.cmd == "map":
            return cmd_map(con)
        if a.cmd == "stats":
            return cmd_stats(con)
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
