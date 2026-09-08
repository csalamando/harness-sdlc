#!/usr/bin/env python3
"""portal_lib.py — núcleo del portal único del proyecto (v2.20).

El portal convierte spec/ en un centro de control navegable: un shell
(spec/portal/index.html) con menú lateral por categorías, búsqueda global
(Ctrl+K), tema claro/oscuro y zoom de fuente compartidos, que carga cada
página en un iframe con continuidad visual (mismos tokens CSS y mismas
claves de localStorage que los diagramas IR: dir-tema / dir-zoom).

Modelo modular: cada generador (harness_graph, mdview, diagram_ir, ...) solo
REGISTRA sus páginas con register(); al final se llama rebuild_index() una
vez, que poda entradas huérfanas y reescribe manifest.js + search-index.js
+ index.html a partir de registry.json. Añadir una página nunca exige tocar
el shell a mano, y cada skill/script sabe qué debe actualizar: lo suyo.

Todo es stdlib, offline y funciona desde file:// sin servidor: por eso el
índice se sirve como .js con window.PORTAL_MANIFEST (fetch no funciona en
file://). Determinista salvo el timestamp 'generado', que check() ignora.

Uso como librería:
  import portal_lib
  pid = portal_lib.register(spec_dir, origen="mdview", kind="doc",
                            ruta="paginas/docs/vision.html", titulo="Visión",
                            texto=texto_plano_del_md)
  portal_lib.rebuild_index(spec_dir, proyecto="mi-proyecto",
                           harness_version="2.20.0")

CLI:
  python portal_lib.py --spec <dir_spec> --rebuild | --check | --summary
"""
import argparse, html, json, os, re, sys
from datetime import datetime

PORTAL_VERSION = "1.1.0"

CATEGORIAS = [
    ("inicio", "Inicio", "🏠"),
    ("metricas", "Métricas", "📊"),
    ("arquitectura", "Arquitectura", "🏛️"),
    ("negocio", "Negocio", "💼"),
    ("calidad", "Calidad", "🧪"),
    ("operacion", "Operación", "🚀"),
    ("docs", "Documentos", "📚"),
    ("memoria", "Memoria", "🧠"),
]
_CAT_ORDEN = {c[0]: i for i, c in enumerate(CATEGORIAS)}

# ── Tokens visuales compartidos (mismo set que diagram_ir v1.1 + extras) ──────

TOKENS_CSS = (
    ":root{--bg:#0b1220;--fg:#e2e8f0;--txt:#f1f5f9;--muted:#64748b;--sub:#8ea0b8;--edge:#94a3b8;"
    "--panel-bg:#0f172a;--panel-bd:#1e293b;--card-bg:#111c33;--accent:#3b82f6;--ok:#22c55e;"
    "--warn:#f59e0b;--bad:#ef4444;--tier:#f97316;--shadow:rgba(0,0,0,.35);color-scheme:dark}"
    ":root[data-theme=claro]{--bg:#eef2f7;--fg:#1e293b;--txt:#0f172a;--muted:#64748b;--sub:#5b6b80;"
    "--edge:#64748b;--panel-bg:#ffffff;--panel-bd:#e2e8f0;--card-bg:#f8fafc;--accent:#2563eb;"
    "--ok:#16a34a;--warn:#d97706;--bad:#dc2626;--tier:#ea580c;--shadow:rgba(15,23,42,.12);color-scheme:light}"
)

# CSS base de las páginas de contenido (docs, métricas...). Todo con vars:
# el tema claro/oscuro lo cambia TOKENS_CSS sin tocar las páginas.
PAGE_CSS = (
    "body{background:var(--bg);color:var(--fg);font-family:system-ui,'Segoe UI',sans-serif;"
    "margin:0;padding:1.5rem 1.8rem 3rem;line-height:1.55;font-size:15px}"
    "h1{font-size:1.35rem;color:var(--txt);margin:.2rem 0 .8rem}"
    "h2{font-size:1.08rem;color:var(--txt);margin:1.4rem 0 .6rem}"
    "h3{font-size:.92rem;color:var(--sub);margin:1.1rem 0 .4rem}"
    "h4{font-size:.85rem;color:var(--sub);margin:1rem 0 .3rem}"
    "a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}"
    "code{background:var(--card-bg);border:1px solid var(--panel-bd);border-radius:5px;"
    "padding:.12em .4em;font-size:.88em;font-family:ui-monospace,'Cascadia Code',Consolas,monospace}"
    "pre{background:var(--panel-bg);border:1px solid var(--panel-bd);border-radius:10px;"
    "padding:1rem;overflow-x:auto}pre code{background:none;border:none;padding:0}"
    "table{border-collapse:collapse;width:100%;margin:1rem 0;font-size:.88em;display:block;overflow-x:auto}"
    "th,td{border-bottom:1px solid var(--panel-bd);padding:.45em .7em;text-align:left;vertical-align:top}"
    "th{color:var(--sub);font-size:.78em;text-transform:uppercase;letter-spacing:.04em}"
    "blockquote{border-left:3px solid var(--panel-bd);margin:1em 0;padding:.2em 1em;color:var(--sub)}"
    "hr{border:none;border-top:1px solid var(--panel-bd);margin:1.6em 0}"
    "img{max-width:100%}li{margin:.2em 0}"
    ".pnote{color:var(--muted);font-size:.78rem;margin-bottom:1rem}"
)

# JS compartido por TODAS las páginas del portal: aplica el tema guardado,
# escucha cambios de tema del shell (postMessage) y, si la página declara
# data-page-id, avisa al shell qué página se abrió (navegación interna).
PAGE_JS = r"""
(function(){
  var root=document.documentElement;
  function saved(){try{return localStorage.getItem('dir-tema');}catch(e){return null;}}
  function apl(t){root.dataset.theme=t||(matchMedia('(prefers-color-scheme: light)').matches?'claro':'oscuro');}
  apl(saved());
  window.addEventListener('message',function(e){var d=e.data||{};if(d.portal==='tema'){apl(d.tema);}});
  var pid=document.body&&document.body.getAttribute('data-page-id');
  if(pid&&window.parent!==window){
    try{window.parent.postMessage({portal:'abierto',id:pid},'*');}catch(e){}
  }
})();
"""


def page_wrap(titulo, body_html, page_id=None, extra_css="", note=""):
    """Página standalone del portal: tokens + CSS base + JS de tema/sincronía.

    page_id activa la sincronía con el shell (la página se auto-reporta al
    cargar y el menú lateral marca la entrada sin recargar el iframe).
    """
    pid = f' data-page-id="{html.escape(page_id)}"' if page_id else ""
    nota = f'<div class="pnote">{html.escape(note)}</div>' if note else ""
    return ("<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            f"<title>{html.escape(titulo)}</title>"
            f"<style>{TOKENS_CSS}{PAGE_CSS}{extra_css}</style></head>"
            f"<body{pid}>{nota}{body_html}<script>{PAGE_JS}</script></body></html>")


# ── Utilidades ────────────────────────────────────────────────────────────────

def slug(s):
    """id de portal a partir de una ruta: paginas/docs/adr__x.html -> docs-adr__x"""
    s = s.lower().replace("\\", "/")
    s = re.sub(r"\.html?$", "", s)
    s = re.sub(r"^(\.\./)+", "", s)
    s = re.sub(r"^paginas/", "", s)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "pagina"


def _plano(t):
    """Texto plano para el índice de búsqueda (sin HTML ni ruido Markdown)."""
    t = re.sub(r"<[^>]+>", " ", t or "")
    t = re.sub(r"[#*`|]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


_REGLES = [
    ("arquitectura", ("adr", "architect", "arquitect", "tech-radar", "tech_radar",
                      "diagram", "c4-", "decision")),
    ("negocio", ("vision", "backlog", "user-stories", "user_stories", "glossary",
                 "glosario", "epica", "personas", "stakeholder")),
    ("calidad", ("test", "qa", "e2e", "cobertura", "coverage")),
    ("operacion", ("reports", "report", "release", "pipeline", "deploy", "sprint",
                   "incident", "postmortem", "runbook", "slo", "oncall")),
    ("memoria", ("memory", "session", "learning", "handoff")),
]


def infer_categoria(nombre, kind=""):
    """Categoría del portal a partir del nombre/ruta y el kind del generador."""
    if kind == "inicio":
        return "inicio"
    if kind == "metrica":
        return "metricas"
    if kind == "diagrama":
        return "arquitectura"
    n = (nombre or "").lower()
    for cat, keys in _REGLES:
        if any(k in n for k in keys):
            return cat
    return "docs"


def portal_dir(spec_dir):
    return os.path.join(spec_dir, "portal")


def paginas_dir(spec_dir):
    return os.path.join(portal_dir(spec_dir), "paginas")


def _registry_path(spec_dir):
    return os.path.join(portal_dir(spec_dir), "registry.json")


def _load_registry(spec_dir):
    p = _registry_path(spec_dir)
    if os.path.isfile(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            pass
    return {"portal_version": PORTAL_VERSION, "items": []}


def _save_registry(spec_dir, reg):
    os.makedirs(portal_dir(spec_dir), exist_ok=True)
    with open(_registry_path(spec_dir), "w", encoding="utf-8", newline="\n") as f:
        json.dump(reg, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")


def register(spec_dir, origen, kind, ruta, titulo, categoria=None, grupo=None,
             tags=(), texto="", oculto=False):
    """Registra (o actualiza) una página del portal. Devuelve su id.

    ruta: absoluta o relativa al directorio del portal (spec/portal/). Las
    páginas generadas viven en paginas/...; los diagramas se referencian como
    ../diagrams/x.html sin copiarlos. oculto=True la excluye del menú lateral
    (sigue siendo enrutable y buscable — p. ej. el glosario va al topbar).
    """
    pd = portal_dir(spec_dir)
    if os.path.isabs(ruta):
        ruta = os.path.relpath(ruta, pd)
    ruta = ruta.replace(os.sep, "/").replace("\\", "/")
    reg = _load_registry(spec_dir)
    rutas = {i["id"]: i["ruta"] for i in reg["items"]}
    nid, n = slug(ruta), 2
    while nid in rutas and rutas[nid] != ruta:
        nid = f"{slug(ruta)}-{n}"
        n += 1
    item = {"id": nid, "ruta": ruta, "titulo": titulo, "kind": kind,
            "categoria": categoria or infer_categoria(ruta, kind),
            "grupo": grupo or "", "origen": origen,
            "tags": [str(t) for t in tags],
            "texto": _plano(texto)[:3000]}
    if oculto:
        item["oculto"] = True
    # Merge: un registro posterior con menos detalle no pisa el texto/tags
    # ricos que ya hubiera (p. ej. el sweep de harness_graph tras diagram_ir);
    # si no había texto previo, al menos indexa el título.
    prev = next((i for i in reg["items"] if i["id"] == nid), None)
    if prev:
        if not item["texto"]:
            item["texto"] = prev.get("texto", "")
        if not item["tags"]:
            item["tags"] = prev.get("tags", [])
        if not item["grupo"]:
            item["grupo"] = prev.get("grupo", "")
    if not item["texto"]:
        item["texto"] = _plano(titulo)
    reg["items"] = [i for i in reg["items"] if i["id"] != nid] + [item]
    _save_registry(spec_dir, reg)
    return nid


# ── Manifiesto e índice de búsqueda ───────────────────────────────────────────

def set_topbar(spec_dir, entries):
    """Botones extra del topbar del shell: [{id, icono, titulo}] → rutas del portal."""
    reg = _load_registry(spec_dir)
    reg["topbar"] = list(entries)
    _save_registry(spec_dir, reg)


def _manifiesto(spec_dir, proyecto="", harness_version=""):
    """Construye el manifiesto desde el registry, podando entradas huérfanas."""
    reg = _load_registry(spec_dir)
    pd = portal_dir(spec_dir)
    items = [it for it in reg["items"]
             if os.path.isfile(os.path.join(pd, it["ruta"].replace("/", os.sep)))]
    if len(items) != len(reg["items"]):
        reg["items"] = items
        _save_registry(spec_dir, reg)
    items.sort(key=lambda i: (_CAT_ORDEN.get(i["categoria"], 99),
                              i.get("grupo", ""), i["titulo"].lower()))
    visibles = [i for i in items if not i.get("oculto")]
    cats = [{"id": c, "label": l, "icono": ic,
             "count": sum(1 for i in visibles if i["categoria"] == c)}
            for c, l, ic in CATEGORIAS]
    return {"portal_version": PORTAL_VERSION,
            "proyecto": proyecto, "harness_version": harness_version,
            "generado": datetime.now().isoformat(timespec="seconds"),
            "categorias": cats,
            "topbar": reg.get("topbar", []),
            "items": [{k: it[k] for k in
                       ("id", "ruta", "titulo", "categoria", "grupo", "kind", "tags")
                       if k in it} | ({"oculto": True} if it.get("oculto") else {})
                      for it in items],
            "index": [{"id": it["id"], "t": it["titulo"], "c": it["categoria"],
                       "k": it.get("tags", []), "x": it.get("texto", "")[:1600]}
                      for it in items]}


def _meta_actual(spec_dir):
    """proyecto/harness_version del manifest.js vigente (para no pisarlos)."""
    p = os.path.join(portal_dir(spec_dir), "manifest.js")
    if os.path.isfile(p):
        mm = re.match(r"window\.PORTAL_MANIFEST=(.*);\s*$",
                      open(p, encoding="utf-8").read(), re.S)
        if mm:
            try:
                return json.loads(mm.group(1))
            except Exception:
                pass
    return {}


def rebuild_index(spec_dir, proyecto="", harness_version=""):
    """Reescribe manifest.js + search-index.js + index.html. Devuelve nº de items.

    Si no se pasan proyecto/harness_version, conserva los del manifiesto
    vigente (un auto-registro desde diagram_ir no debe pisar lo que escribió
    harness_graph --proyecto).
    """
    if not proyecto or not harness_version:
        prev = _meta_actual(spec_dir)
        proyecto = proyecto or prev.get("proyecto", "")
        harness_version = harness_version or prev.get("harness_version", "")
    m = _manifiesto(spec_dir, proyecto, harness_version)
    pd = portal_dir(spec_dir)
    os.makedirs(pd, exist_ok=True)
    pub = {k: v for k, v in m.items() if k != "index"}
    with open(os.path.join(pd, "manifest.js"), "w", encoding="utf-8", newline="\n") as f:
        f.write("window.PORTAL_MANIFEST=" + json.dumps(pub, ensure_ascii=False) + ";\n")
    with open(os.path.join(pd, "search-index.js"), "w", encoding="utf-8", newline="\n") as f:
        f.write("window.PORTAL_INDEX=" + json.dumps(m["index"], ensure_ascii=False) + ";\n")
    with open(os.path.join(pd, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(build_shell(m))
    return len(m["items"])


def check(spec_dir):
    """True si manifest.js + index.html están al día con registry.json.

    Ignora el timestamp 'generado' y los metadatos proyecto/harness_version
    (quien corre --check no los conoce; lo estructural son categorias+items).
    """
    _VOLATIL = ("index", "generado", "proyecto", "harness_version")
    m = _manifiesto(spec_dir)
    esperado = json.dumps({k: v for k, v in m.items() if k not in _VOLATIL},
                          ensure_ascii=False, sort_keys=True)
    p = os.path.join(portal_dir(spec_dir), "manifest.js")
    actual = ""
    if os.path.isfile(p):
        mm = re.match(r"window\.PORTAL_MANIFEST=(.*);\s*$",
                      open(p, encoding="utf-8").read(), re.S)
        if mm:
            try:
                d = json.loads(mm.group(1))
                for k in _VOLATIL:
                    d.pop(k, None)
                actual = json.dumps(d, ensure_ascii=False, sort_keys=True)
            except Exception:
                pass
    shell = os.path.join(portal_dir(spec_dir), "index.html")
    shell_ok = (os.path.isfile(shell)
                and f"portal-version: {PORTAL_VERSION}"
                in open(shell, encoding="utf-8").read())
    return bool(actual) and actual == esperado and shell_ok


# ── Shell del portal (spec/portal/index.html) ─────────────────────────────────
# String plano + .replace() de tokens: ni f-strings ni % (el JS usa llaves).

_SHELL = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__PROYECTO__ — Portal del proyecto</title>
<!-- portal-version: __PVERSION__ · arnés v__HVERSION__ · generado: __GENERADO__ (artefacto derivado — no editar a mano) -->
<style>
:root{--bg:#0b1220;--fg:#e2e8f0;--txt:#f1f5f9;--muted:#64748b;--sub:#8ea0b8;--edge:#94a3b8;
--panel-bg:#0f172a;--panel-bd:#1e293b;--card-bg:#111c33;--accent:#3b82f6;--ok:#22c55e;
--warn:#f59e0b;--bad:#ef4444;--shadow:rgba(0,0,0,.35);color-scheme:dark}
:root[data-theme=claro]{--bg:#eef2f7;--fg:#1e293b;--txt:#0f172a;--muted:#64748b;--sub:#5b6b80;
--edge:#64748b;--panel-bg:#ffffff;--panel-bd:#e2e8f0;--card-bg:#f8fafc;--accent:#2563eb;
--ok:#16a34a;--warn:#d97706;--bad:#dc2626;--shadow:rgba(15,23,42,.12);color-scheme:light}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--fg);font-family:system-ui,'Segoe UI',sans-serif;
display:flex;flex-direction:column;overflow:hidden}
#topbar{display:flex;align-items:center;gap:.45rem;padding:.45rem .8rem;background:var(--panel-bg);
border-bottom:1px solid var(--panel-bd);flex:none}
#topbar button{background:var(--card-bg);border:1px solid var(--panel-bd);color:var(--fg);
border-radius:8px;padding:.28rem .55rem;cursor:pointer;font-size:12.5px;font-weight:650;white-space:nowrap}
#topbar button:hover{border-color:var(--accent)}
#brand{font-weight:800;font-size:14px;white-space:nowrap;display:flex;align-items:baseline;gap:.5rem}
#brand .ver{color:var(--muted);font-weight:500;font-size:11px}
#searchbox{position:relative;flex:1;max-width:520px;margin:0 auto}
#q{width:100%;background:var(--card-bg);border:1px solid var(--panel-bd);color:var(--fg);
border-radius:8px;padding:.35rem .7rem;font-size:13px}
#q:focus{outline:none;border-color:var(--accent)}
#qres{position:absolute;top:110%;left:0;right:0;background:var(--panel-bg);border:1px solid var(--panel-bd);
border-radius:10px;box-shadow:0 12px 40px var(--shadow);display:none;max-height:62vh;overflow-y:auto;z-index:60}
#helpwrap{position:relative}
#helpbox{position:absolute;top:110%;right:0;width:340px;background:var(--panel-bg);border:1px solid var(--panel-bd);
border-radius:10px;box-shadow:0 12px 40px var(--shadow);display:none;z-index:60;padding:.9rem 1.1rem;font-size:12.5px}
#helpbox h3{margin:0 0 .5rem;font-size:13px;color:var(--txt)}
#helpbox ul{margin:0;padding-left:1.1rem;color:var(--sub);line-height:1.55}
#helpbox li{margin:.3rem 0}
#helpbox b{color:var(--fg)}
#crumbs{display:flex;align-items:center;gap:.45rem;padding:.28rem .8rem;background:var(--panel-bg);
border-bottom:1px solid var(--panel-bd);font-size:11.5px;color:var(--muted);flex:none;white-space:nowrap;
overflow:hidden;text-overflow:ellipsis}
#crumbs button{background:none;border:1px solid var(--panel-bd);color:var(--fg);border-radius:6px;
padding:.05rem .45rem;cursor:pointer;font-size:12px;line-height:1.3}
#crumbs button:hover{border-color:var(--accent)}
#crumbs a{color:var(--sub);text-decoration:none}
#crumbs a:hover{color:var(--txt);text-decoration:underline}
#crumbs .sep{color:var(--sub);font-weight:700;margin:0 .1rem}
#crumbs b{color:var(--fg);font-weight:650}
.qr{padding:.5rem .8rem;border-bottom:1px solid var(--panel-bd);cursor:pointer}
.qr:last-child{border-bottom:none}
.qr:hover,.qr.sel{background:var(--card-bg)}
.qr b{font-size:13px;color:var(--txt)}
.qc{font-size:10.5px;color:var(--accent);margin-left:.5rem;text-transform:uppercase;letter-spacing:.05em}
.qx{font-size:11.5px;color:var(--sub);margin-top:.15rem;line-height:1.35}
mark{background:rgba(245,158,11,.35);color:inherit;border-radius:2px;padding:0 1px}
#layout{flex:1;display:flex;min-height:0}
#side{width:272px;flex:none;background:var(--panel-bg);border-right:1px solid var(--panel-bd);
overflow-y:auto;padding:.6rem .55rem;transition:margin-left .18s}
body.side-off #side{margin-left:-272px}
#nav details.cat{margin-bottom:.25rem}
#nav summary{cursor:pointer;list-style:none;display:flex;align-items:center;gap:.45rem;
padding:.42rem .5rem;border-radius:8px;font-size:12.5px;font-weight:700;color:var(--txt);user-select:none}
#nav summary:hover{background:var(--card-bg)}
#nav summary::-webkit-details-marker{display:none}
#nav summary::before{content:"▸";color:var(--accent);transition:.15s;font-size:10px}
#nav details[open]>summary::before{transform:rotate(90deg)}
#nav summary .cnt{margin-left:auto;font-size:10px;color:var(--muted);background:var(--card-bg);
border:1px solid var(--panel-bd);border-radius:8px;padding:0 6px}
#nav .grp{font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin:.55rem .5rem .15rem}
#nav a.ni{display:block;padding:.3rem .5rem .3rem 1.6rem;border-radius:7px;color:var(--sub);
text-decoration:none;font-size:12.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#nav a.ni:hover{background:var(--card-bg);color:var(--txt)}
#nav a.ni.act{background:rgba(59,130,246,.18);color:var(--txt);font-weight:650}
#main{flex:1;min-width:0;position:relative;background:var(--bg)}
#frame{border:none;width:100%;height:100%;transform-origin:0 0;display:block}
#welcome{position:absolute;inset:0;overflow-y:auto;padding:3rem;max-width:760px;display:none}
#welcome h1{font-size:1.5rem}
#welcome p{color:var(--sub);line-height:1.6}
#welcome code{background:var(--card-bg);border:1px solid var(--panel-bd);border-radius:5px;padding:.1em .4em;font-size:.88em}
@media(max-width:860px){
#side{position:absolute;z-index:50;height:100%;box-shadow:8px 0 30px var(--shadow)}
body.side-off #side{margin-left:-280px}
#brand .ver{display:none}}
</style>
</head>
<body>
<header id="topbar">
  <button id="btn-side" title="Contraer/expandir el menú lateral">☰</button>
  <div id="brand">◈ <span>__PROYECTO__</span><span class="ver">portal v__PVERSION__ · arnés v__HVERSION__</span></div>
  <div id="searchbox"><input id="q" type="search" placeholder="Buscar en todo el portal… (Ctrl+K)" autocomplete="off" spellcheck="false"><div id="qres"></div></div>
  <span id="topxtra"></span>
  <div id="helpwrap"><button id="btn-help" title="Ayuda — cómo navegar el portal">?</button>
    <div id="helpbox"><h3>Cómo navegar este portal</h3><ul>
      <li><b>Menú lateral</b>: todo el contenido por categorías — métricas, arquitectura, negocio, calidad, operación, documentos y memoria. El botón ☰ lo contrae.</li>
      <li><b>Ctrl+K</b>: búsqueda global en títulos y contenido de todas las páginas.</li>
      <li><b>A− / A / A+</b> y <b>☀/☾</b>: zoom de fuente y tema claro/oscuro, compartidos con los diagramas interactivos.</li>
      <li>Las páginas se abren dentro del portal; los enlaces internos actualizan el menú solos.</li>
      <li>La evidencia son los recibos; este portal es solo visualización (artefacto derivado).</li>
    </ul></div>
  </div>
  <button id="btn-zmenos" title="Reducir tamaño de fuente">A−</button>
  <button id="btn-zreset" title="Tamaño original">A</button>
  <button id="btn-zmas" title="Aumentar tamaño de fuente">A+</button>
  <button id="btn-tema" title="Tema claro/oscuro">☀️</button>
</header>
<div id="crumbs"><button id="btn-back" title="Atrás (historial del portal)">‹</button><button id="btn-fwd" title="Adelante">›</button><span id="crumb-path"></span></div>
<div id="layout">
  <aside id="side"><nav id="nav"></nav></aside>
  <div id="main">
    <iframe id="frame" title="Contenido del portal"></iframe>
    <div id="welcome"><h1>Portal vacío</h1>
      <p>Aún no hay páginas registradas. El portal se llena solo: cada skill y script del arnés registra lo que genera.</p>
      <p>Regenera con <code>harness_graph.py --proyecto .</code>.</p></div>
  </div>
</div>
<script src="manifest.js"></script>
<script src="search-index.js"></script>
<script>
(function(){
var M=window.PORTAL_MANIFEST||{proyecto:'proyecto',items:[],categorias:[]};
var IX=window.PORTAL_INDEX||[];
var root=document.documentElement, body=document.body;
var frame=document.getElementById('frame'), nav=document.getElementById('nav');
var welcome=document.getElementById('welcome');
var byId={}; M.items.forEach(function(it){byId[it.id]=it;});
function esc(s){var d=document.createElement('div');d.textContent=String(s==null?'':s);return d.innerHTML;}

/* tema compartido con los diagramas IR (misma clave dir-tema) */
function temaActual(){try{return localStorage.getItem('dir-tema');}catch(e){return null;}
  return null;}
function temaEf(){return temaActual()||(matchMedia('(prefers-color-scheme: light)').matches?'claro':'oscuro');}
function aplTema(t){root.dataset.theme=t;
  try{localStorage.setItem('dir-tema',t);}catch(e){}
  document.getElementById('btn-tema').textContent=t==='claro'?'\u263E':'\u2600';
  try{if(frame.contentWindow)frame.contentWindow.postMessage({portal:'tema',tema:t},'*');}catch(e){}}
document.getElementById('btn-tema').onclick=function(){aplTema(temaEf()==='claro'?'oscuro':'claro');};
frame.addEventListener('load',function(){
  try{if(frame.contentWindow)frame.contentWindow.postMessage({portal:'tema',tema:temaEf()},'*');}catch(e){}});

/* zoom compartido (dir-zoom) */
var z=parseFloat(localStorage.getItem('dir-zoom')||'1');
function aplZoom(){z=Math.min(1.8,Math.max(0.6,z));
  try{localStorage.setItem('dir-zoom',String(z));}catch(e){}
  frame.style.transform=z===1?'none':'scale('+z+')';
  frame.style.width=(100/z)+'%';frame.style.height=(100/z)+'%';}
document.getElementById('btn-zmas').onclick=function(){z=+(z+0.1).toFixed(2);aplZoom();};
document.getElementById('btn-zmenos').onclick=function(){z=+(z-0.1).toFixed(2);aplZoom();};
document.getElementById('btn-zreset').onclick=function(){z=1;aplZoom();};

/* sidebar colapsable (dir-sidebar) */
function aplSide(){body.classList.toggle('side-off',localStorage.getItem('dir-sidebar')==='off');}
document.getElementById('btn-side').onclick=function(){
  localStorage.setItem('dir-sidebar',body.classList.contains('side-off')?'on':'off');aplSide();};

/* árbol de navegación por categorías (+ subgrupos); items ocultos no salen */
function buildNav(){
  var h='';
  M.categorias.forEach(function(c){
    var items=M.items.filter(function(it){return it.categoria===c.id&&!it.oculto;});
    if(!items.length)return;
    h+='<details class="cat" open><summary><span>'+c.icono+'</span>'+esc(c.label)
      +'<span class="cnt">'+items.length+'</span></summary>';
    var g=null;
    items.forEach(function(it){
      var gr=it.grupo||'';
      if(gr!==g){g=gr;if(g)h+='<div class="grp">'+esc(g)+'</div>';}
      h+='<a class="ni" data-id="'+it.id+'" href="#/id/'+it.id+'" title="'+esc(it.titulo)+'">'+esc(it.titulo)+'</a>';
    });
    h+='</details>';
  });
  nav.innerHTML=h||'<div class="grp">sin páginas registradas</div>';
}

/* botones extra del topbar (p. ej. glosario) + ayuda */
(function(){
  var x=document.getElementById('topxtra'),h='';
  (M.topbar||[]).forEach(function(b){
    h+='<button data-id="'+b.id+'" title="'+esc(b.titulo||'')+'">'+b.icono+' '+esc(b.titulo||'')+'</button>';
  });
  x.innerHTML=h;
  x.addEventListener('click',function(e){var b=e.target.closest('button[data-id]');if(b)ir(b.dataset.id);});
  var hb=document.getElementById('helpbox');
  document.getElementById('btn-help').onclick=function(e){e.stopPropagation();
    hb.style.display=hb.style.display==='block'?'none':'block';};
  document.addEventListener('click',function(e){if(!e.target.closest('#helpwrap'))hb.style.display='none';});
  document.addEventListener('keydown',function(e){if(e.key==='Escape')hb.style.display='none';});
})();

/* routing por hash #/id/<slug> (funciona desde file://) */
function curId(){var m=/#\/id\/([A-Za-z0-9\-_]+)/.exec(location.hash||'');return m?m[1]:null;}
function mark(id){nav.querySelectorAll('.ni').forEach(function(a){
  var on=a.dataset.id===id;a.classList.toggle('act',on);
  if(on){var d=a.closest('details');if(d&&!d.open)d.open=true;}});}
/* miga de pan + título + última página visitada (persistida por proyecto) */
var crumbPath=document.getElementById('crumb-path');
function catLabel(id){var c=M.categorias.filter(function(x){return x.id===id;})[0];
  return c?c.icono+' '+c.label:id;}
function paint(id){
  mark(id);
  var it=byId[id],home=null;
  M.items.forEach(function(x){if(!home&&x.categoria==='inicio')home=x;});
  if(!it){crumbPath.innerHTML='<b>'+esc(M.proyecto||'portal')+'</b>';return;}
  var h='';
  if(home&&it.id!==home.id){
    h+='<a href="#/id/'+home.id+'" data-id="'+home.id+'">'+esc(home.titulo)+'</a><span class="sep">›</span>';
    h+='<span>'+esc(catLabel(it.categoria))+'</span><span class="sep">›</span>';
  }else if(it.categoria!=='inicio'){
    h+='<span>'+esc(catLabel(it.categoria))+'</span><span class="sep">›</span>';
  }
  h+='<b>'+esc(it.titulo)+'</b>';
  crumbPath.innerHTML=h;
  document.title=it.titulo+' — '+(M.proyecto||'portal');
  try{localStorage.setItem('portal-last-'+(M.proyecto||''),id);}catch(e){}
}
document.getElementById('btn-back').onclick=function(){history.back();};
document.getElementById('btn-fwd').onclick=function(){history.forward();};
crumbPath.addEventListener('click',function(e){
  var a=e.target.closest('a[data-id]');if(!a)return;e.preventDefault();
  if(curId()===a.dataset.id)show(a.dataset.id);else location.hash='#/id/'+a.dataset.id;});
function show(id){
  var it=byId[id];if(!it){showWelcome();return;}
  welcome.style.display='none';frame.style.display='block';
  if(frame.dataset.cur!==it.ruta){frame.dataset.cur=it.ruta;frame.src=it.ruta;}
  paint(id);
}
function showWelcome(){
  frame.dataset.cur='';frame.style.display='none';frame.src='about:blank';
  welcome.style.display='block';paint(null);
}
function route(){
  var id=curId();
  if(id&&byId[id]){show(id);return;}
  /* sin ruta: vuelve a la última página visitada de este proyecto, si existe */
  var saved=null;
  try{saved=localStorage.getItem('portal-last-'+(M.proyecto||''));}catch(e){}
  if(saved&&byId[saved]){history.replaceState(null,'','#/id/'+saved);show(saved);return;}
  var home=null;
  M.items.forEach(function(it){if(!home&&it.categoria==='inicio')home=it;});
  home=home||M.items[0];
  if(home){if(curId()!==home.id)history.replaceState(null,'','#/id/'+home.id);show(home.id);}
  else showWelcome();
}
window.addEventListener('hashchange',route);
nav.addEventListener('click',function(e){
  var a=e.target.closest('a.ni');if(!a)return;e.preventDefault();
  if(curId()===a.dataset.id)show(a.dataset.id);else location.hash='#/id/'+a.dataset.id;});

/* las páginas avisan qué son al cargar (navegación interna doc→doc):
   empuja historial para que ‹ atrás devuelva a la página anterior */
window.addEventListener('message',function(e){var d=e.data||{};
  if(d.portal==='abierto'&&d.id&&byId[d.id]){
    if(curId()!==d.id)location.hash='#/id/'+d.id;
    paint(d.id);}});

/* búsqueda global (Ctrl+K) */
var q=document.getElementById('q'),qres=document.getElementById('qres'),sel=-1,res=[];
function resalta(s,qy){s=esc(s);qy=(qy||'').trim();if(!qy)return s;
  var i=s.toLowerCase().indexOf(qy.toLowerCase());
  if(i<0)return s;
  return s.slice(0,i)+'<mark>'+s.slice(i,i+qy.length)+'</mark>'+s.slice(i+qy.length);}
function buscar(s){
  s=s.trim().toLowerCase();if(s.length<2)return[];
  var out=[];
  IX.forEach(function(e){
    var t=(e.t||'').toLowerCase(),x=(e.x||'').toLowerCase(),k=(e.k||[]).join(' ').toLowerCase();
    var i=t.indexOf(s);
    if(i>=0)out.push([0,i,e]);
    else{var g=k.indexOf(s);if(g>=0)out.push([1,g,e]);
    else{var j=x.indexOf(s);if(j>=0)out.push([2,j,e]);}}});
  out.sort(function(a,b){return a[0]-b[0]||a[1]-b[1]||a[2].t.localeCompare(b[2].t);});
  return out.slice(0,12).map(function(r){return r[2];});
}
function pinta(){
  if(!res.length){qres.style.display='none';qres.innerHTML='';return;}
  qres.innerHTML=res.map(function(e,i){var it=byId[e.id]||{};
    return '<div class="qr'+(i===sel?' sel':'')+'" data-id="'+e.id+'"><b>'+resalta(e.t,q.value)+'</b>'
      +'<span class="qc">'+esc(it.categoria||'')+'</span>'
      +'<div class="qx">'+resalta((e.x||'').slice(0,150),q.value)+'…</div></div>';}).join('');
  qres.style.display='block';
}
function ir(id){if(curId()===id)show(id);else location.hash='#/id/'+id;}
function cerrarRes(){qres.style.display='none';}
q.addEventListener('input',function(){sel=-1;res=buscar(q.value);pinta();});
q.addEventListener('keydown',function(e){
  if(e.key==='ArrowDown'){e.preventDefault();sel=Math.min(sel+1,res.length-1);pinta();}
  else if(e.key==='ArrowUp'){e.preventDefault();sel=Math.max(sel-1,0);pinta();}
  else if(e.key==='Enter'){e.preventDefault();var r=res[sel>=0?sel:0];if(r){ir(r.id);cerrarRes();}}
  else if(e.key==='Escape'){cerrarRes();q.blur();}});
qres.addEventListener('click',function(e){var r=e.target.closest('.qr');if(r){ir(r.dataset.id);cerrarRes();}});
document.addEventListener('keydown',function(e){
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();q.focus();q.select();}});
document.addEventListener('click',function(e){if(!e.target.closest('#searchbox'))cerrarRes();});

buildNav();aplTema(temaEf());aplZoom();aplSide();route();
})();
</script>
</body>
</html>
"""


def build_shell(m):
    """index.html del portal a partir del manifiesto (tokens estáticos mínimos)."""
    return (_SHELL
            .replace("__PROYECTO__", html.escape(m.get("proyecto") or "proyecto"))
            .replace("__HVERSION__", html.escape(m.get("harness_version") or "?"))
            .replace("__PVERSION__", PORTAL_VERSION)
            .replace("__GENERADO__", html.escape(m.get("generado") or "")))


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv=None):
    ap = argparse.ArgumentParser(description="Portal único del proyecto (v2.20)")
    ap.add_argument("--spec", required=True, help="directorio spec/ del proyecto")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--rebuild", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--summary", action="store_true")
    ap.add_argument("--proyecto", default="")
    ap.add_argument("--harness-version", default="")
    a = ap.parse_args(argv)
    spec_dir = os.path.abspath(a.spec)

    if a.rebuild:
        n = rebuild_index(spec_dir, a.proyecto, a.harness_version)
        print(f"portal: {n} páginas registradas → {portal_dir(spec_dir)}")
        return 0
    if a.summary:
        m = _manifiesto(spec_dir)
        for c in m["categorias"]:
            if c["count"]:
                print(f"  {c['icono']} {c['label']}: {c['count']}")
        print(f"  total: {len(m['items'])} páginas")
        return 0
    if check(spec_dir):
        print("PORTAL CHECK OK: index/manifest al día con registry.json.")
        return 0
    print("DRIFT: portal desactualizado (regenerar: portal_lib.py --spec . --rebuild)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
