#!/usr/bin/env python3
"""mdview.py — visor Markdown estático para la spec (v2.18, portal v2.20).

Convierte los .md gobernados de spec/ en paginas HTML auto-contenidas y SIN
red, publicadas dentro del portal unico del proyecto (spec/portal/paginas/docs/)
con la identidad visual compartida (tokens claro/oscuro de portal_lib) y
registradas en el indice/buscador global del portal.

Inspirado en el patron `grip --export` (joeyespo/grip), pero sin GitHub API:
renderer propio stdlib — offline, cero dependencias, determinista.

Uso:
  python mdview.py build --spec <dir_spec> [--out <dir_spec/portal/paginas/docs>]

Genera una pagina por .md (top-level de spec/, spec/reports/, spec/adr/,
spec/diagrams/*.md y spec/memory/*.md), reescribe los enlaces .md internos a
su pagina renderizada y registra cada pagina en el portal (categoria inferida
de la ruta fuente). El indice visual es el shell del portal; ya no genera un
index.html propio. Es artefacto derivado: se regenera en cada
`harness_graph.py --proyecto`; nunca se edita a mano.

Cobertura Markdown (suficiente para doc-as-code de la spec): encabezados ATX,
parrafos, negrita/cursiva/codigo inline, enlaces, imagenes, listas ul/ol
anidadas por indentacion, tablas GFM, citas, reglas horizontales y bloques de
codigo con resaltado neutro (mermaid se muestra como codigo, sin render).
"""
import argparse, glob, html, os, re, sys

VERSION = "2.0.0"

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

# ── pagina completa (portal) ─────────────────────────────────────────────────

def doc_name(relpath):
    """Nombre de pagina unico por ruta relativa: reports/x.md -> reports__x.html"""
    return re.sub(r"\.md$", "", relpath, flags=re.I).replace("/", "__").replace("\\", "__") + ".html"

def collect(spec_dir):
    pats = ["*.md", "reports/*.md", "adr/*.md", "diagrams/*.md", "memory/*.md"]
    files = []
    for pat in pats:
        files += glob.glob(os.path.join(spec_dir, pat))
    return sorted({os.path.relpath(f, spec_dir).replace(os.sep, "/") for f in files
                   if "docs-html" not in f and "portal" not in f})

def _rewrite_links(body, rel, rels):
    """Enlaces .md internos -> pagina renderizada del portal (mismo directorio)."""
    base = os.path.dirname(rel)
    def rep(m):
        href, anchor = m.group(1), m.group(2) or ""
        if re.match(r"^[a-z]+://", href, re.I) or href.startswith("#"):
            return m.group(0)
        tgt = os.path.normpath(os.path.join(base, href)).replace(os.sep, "/")
        if tgt.lower().endswith(".md") and tgt in rels:
            return f'href="{doc_name(tgt)}{anchor}"'
        return m.group(0)
    return re.sub(r'href="([^"]+?)(#[^"]*)?"', rep, body)

def build(spec_dir, out_dir=None):
    """Renderiza los .md de la spec al portal y los registra. Devuelve nº docs."""
    import portal_lib
    out_dir = out_dir or os.path.join(portal_lib.paginas_dir(spec_dir), "docs")
    rels = collect(spec_dir)
    os.makedirs(out_dir, exist_ok=True)
    # limpieza de paginas derivadas anteriores (se regeneran todas)
    for viejo in glob.glob(os.path.join(out_dir, "*.html")):
        os.remove(viejo)
    nota = "Render derivado de spec/ (mdview) — no editar a mano; la fuente es el .md"
    n = 0
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
        body = _rewrite_links(render_md(text), rel, set(rels))
        nombre = doc_name(rel)
        ruta = "paginas/docs/" + nombre
        pid = portal_lib.slug(ruta)
        open(os.path.join(out_dir, nombre), "w", encoding="utf-8", newline="\n").write(
            portal_lib.page_wrap(titulo, body, page_id=pid, note=nota))
        portal_lib.register(spec_dir, origen="mdview", kind="doc", ruta=ruta,
                            titulo=titulo, grupo=os.path.dirname(rel) or "spec",
                            tags=[rel], texto=text)
        n += 1
    return n

def main(argv=None):
    ap = argparse.ArgumentParser(description="Visor Markdown estatico de la spec (portal v2.20)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("build")
    p.add_argument("--spec", required=True)
    p.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    n = build(a.spec, a.out)
    print(f"mdview: {n} documentos renderizados en el portal")
    return 0

if __name__ == "__main__":
    sys.exit(main())
