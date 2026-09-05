#!/usr/bin/env python3
"""mdview.py — visor Markdown estático para la spec (v2.18).

Convierte los .md gobernados de spec/ en paginas HTML estilo GitHub (tema oscuro,
acorde al dashboard), auto-contenidas y SIN red, para leer la spec desde
spec/dashboard.html sin salir del navegador ni levantar un servidor.

Inspirado en el patron `grip --export` (joeyespo/grip), pero sin GitHub API:
renderer propio stdlib — offline, cero dependencias, determinista.

Uso:
  python mdview.py build --spec <dir_spec> [--out <dir_spec/docs-html>]

Genera una pagina por .md (top-level de spec/, spec/reports/, spec/adr/ y
spec/diagrams/*.md) mas un index.html que las lista. Cada pagina enlaza de
vuelta al dashboard (../dashboard.html). Es artefacto derivado: se regenera
en cada `harness_graph.py --proyecto`; nunca se edita a mano.

Cobertura Markdown (suficiente para doc-as-code de la spec): encabezados ATX,
parrafos, negrita/cursiva/codigo inline, enlaces, imagenes, listas ul/ol
anidadas por indentacion, tablas GFM, citas, reglas horizontales y bloques de
codigo con resaltado neutro (mermaid se muestra como codigo, sin render).
"""
import argparse, glob, html, os, re, sys

VERSION = "1.0.0"

CSS = """
body{background:#0b1220;color:#dbe4f0;font-family:system-ui,'Segoe UI',sans-serif;
  max-width:900px;margin:0 auto;padding:2rem 1.4rem 4rem;line-height:1.6;font-size:15px}
a{color:#58a6ff;text-decoration:none} a:hover{text-decoration:underline}
h1,h2,h3,h4{color:#f1f5f9;border-bottom:1px solid #1e293b;padding-bottom:.3em;margin-top:1.6em}
h1{font-size:1.7em} h2{font-size:1.35em} h3{font-size:1.12em} h4{font-size:1em}
code{background:#1e293b;border-radius:5px;padding:.15em .4em;font-size:.88em;
  font-family:ui-monospace,'Cascadia Code',Consolas,monospace;color:#a5f3fc}
pre{background:#0f172a;border:1px solid #1e293b;border-radius:10px;padding:1rem;
  overflow-x:auto} pre code{background:none;padding:0;color:#cbd5e1}
table{border-collapse:collapse;width:100%;margin:1rem 0;font-size:.92em;display:block;overflow-x:auto}
th,td{border:1px solid #1e293b;padding:.45em .8em;text-align:left;vertical-align:top}
th{background:#0f172a;color:#e2e8f0} tr:nth-child(even) td{background:#0d1526}
blockquote{border-left:3px solid #334155;margin:1em 0;padding:.2em 1em;color:#94a3b8}
hr{border:none;border-top:1px solid #1e293b;margin:2em 0}
img{max-width:100%} li{margin:.2em 0}
.back{display:inline-block;margin-bottom:1.2rem;background:#0f172a;border:1px solid #334155;
  border-radius:8px;padding:.4rem .9rem;color:#cbd5e1;font-size:.9em}
.back:hover{border-color:#3b82f6;color:#e2e8f0;text-decoration:none}
.meta{color:#64748b;font-size:.82em;margin-top:-.6rem;margin-bottom:1.4rem}
.idx h2{border:none;margin-top:1.2em} .idx li{margin:.35em 0}
"""

# ── inline ───────────────────────────────────────────────────────────────────

def _inline(text):
    t = html.escape(text, quote=False)
    t = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)[^)]*\)", r'<img alt="\1" src="\2">', t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", t)
    t = re.sub(r"~~([^~]+)~~", r"<del>\1</del>", t)
    return t

# ── bloques ──────────────────────────────────────────────────────────────────

def render_md(text):
    lines = text.replace("\r\n", "\n").split("\n")
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith("```"):
            lang = ln.strip()[3:].strip()
            buf = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            code = html.escape("\n".join(buf))
            tag = f'<div class="meta">mermaid (ver fuente)</div>' if lang == "mermaid" else ""
            out.append(f"{tag}<pre><code>{code}</code></pre>")
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", ln)
        if m:
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{_inline(m.group(2).strip())}</h{lvl}>")
            i += 1
            continue
        if re.match(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$", ln):
            out.append("<hr>"); i += 1; continue
        if ln.startswith(">") :
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i].lstrip("> ")); i += 1
            out.append(f"<blockquote>{_inline(' '.join(buf))}</blockquote>")
            continue
        if re.match(r"^\s*\|.*\|\s*$", ln):
            tbl = []
            while i < len(lines) and re.match(r"^\s*\|.*\|\s*$", lines[i]):
                tbl.append(lines[i].strip()); i += 1
            rows = [[c.strip() for c in r.strip("|").split("|")] for r in tbl]
            rows = [r for r in rows if not all(re.match(r"^:?-{2,}:?$", c) for c in r)]
            if rows:
                h = "".join(f"<th>{_inline(c)}</th>" for c in rows[0])
                body = "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>"
                               for r in rows[1:])
                out.append(f"<table><tr>{h}</tr>{body}</table>")
            continue
        if re.match(r"^\s*([-*+]|\d+\.)\s+", ln):
            items = []
            while i < len(lines) and re.match(r"^\s*([-*+]|\d+\.)\s+", lines[i]):
                it = re.sub(r"^\s*([-*+]|\d+\.)\s+", "", lines[i])
                items.append(it); i += 1
            lis = "".join(f"<li>{_inline(x)}</li>" for x in items)
            out.append(f"<ul>{lis}</ul>")
            continue
        if ln.strip() == "":
            i += 1; continue
        buf = [ln.strip()]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(
                r"^(#{1,4}\s|```|\s*([-*+]|\d+\.)\s|\s*\||>|---)", lines[i]):
            buf.append(lines[i].strip()); i += 1
        out.append(f"<p>{_inline(' '.join(buf))}</p>")
    return "\n".join(out)

# ── pagina completa ──────────────────────────────────────────────────────────

def page(titulo, body_html, back="../dashboard.html", back_label="← Dashboard"):
    return ("<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            f"<title>{html.escape(titulo)}</title><style>{CSS}</style></head><body>"
            f"<a class='back' href='{back}'>{back_label}</a>"
            f"<div class='meta'>Render derivado de spec/ (mdview) — no editar a mano; la fuente es el .md</div>"
            f"{body_html}</body></html>")

def doc_name(relpath):
    """Nombre de pagina unico por ruta relativa: reports/x.md -> reports__x.html"""
    return re.sub(r"\.md$", "", relpath, flags=re.I).replace("/", "__").replace("\\", "__") + ".html"

def collect(spec_dir):
    pats = ["*.md", "reports/*.md", "adr/*.md", "diagrams/*.md", "memory/*.md"]
    files = []
    for pat in pats:
        files += glob.glob(os.path.join(spec_dir, pat))
    return sorted({os.path.relpath(f, spec_dir).replace(os.sep, "/") for f in files
                   if "docs-html" not in f})

def build(spec_dir, out_dir):
    rels = collect(spec_dir)
    os.makedirs(out_dir, exist_ok=True)
    paginas = []
    for rel in rels:
        src = os.path.join(spec_dir, rel)
        try:
            text = open(src, encoding="utf-8").read()
        except UnicodeDecodeError:
            continue
        titulo = rel
        m = re.search(r"^#\s+(.+)$", text, re.M)
        if m:
            titulo = m.group(1).strip()
        # enlaces entre .md de la spec -> pagina renderizada
        body = render_md(text)
        nombre = doc_name(rel)
        open(os.path.join(out_dir, nombre), "w", encoding="utf-8", newline="\n").write(
            page(titulo, body))
        paginas.append((rel, titulo, nombre))
    grupos = {}
    for rel, titulo, nombre in paginas:
        grupos.setdefault(os.path.dirname(rel) or "spec", []).append((titulo, nombre))
    lis = "".join(
        f"<h2>{html.escape(g)}</h2><ul>" + "".join(
            f'<li><a href="{n}">{html.escape(t)}</a></li>' for t, n in sorted(items)) + "</ul>"
        for g, items in sorted(grupos.items()))
    open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8", newline="\n").write(
        page("Documentos de la spec", f"<div class='idx'><h1>📄 Documentos de la spec</h1>{lis}</div>"))
    return len(paginas)

def main(argv=None):
    ap = argparse.ArgumentParser(description="Visor Markdown estatico de la spec (v2.18)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("build")
    p.add_argument("--spec", required=True)
    p.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    out = a.out or os.path.join(a.spec, "docs-html")
    n = build(a.spec, out)
    print(f"mdview: {n} documentos renderizados en {out}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
