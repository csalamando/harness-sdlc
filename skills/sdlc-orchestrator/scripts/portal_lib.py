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

PORTAL_VERSION = "1.5.1"

# Taxonomía por ROL QUE GOBIERNA el artefacto (quién lo crea, lo aprueba y
# responde por su vigencia), no por tipo de documento. Sin categoría genérica
# "Documentos": el fallback es "procesos" y check() lo señala.
CATEGORIAS = [
    ("inicio", "Inicio", "🏠"),
    ("negocio", "Negocio", "💼"),
    ("arquitectura", "Arquitectura", "🏛️"),
    ("desarrollo", "Desarrollo", "💻"),
    ("qa", "QA", "🧪"),
    ("agilidad", "Agilidad (Métricas)", "📊"),
    ("procesos", "Procesos", "🔄"),
    ("uiux", "UI/UX", "🎨"),
    ("devsecops", "DevSecOps", "🔐"),
    ("plataforma", "Plataforma", "☁️"),
    ("auditoria", "Auditoría y Trazabilidad", "🧾"),
]
_CAT_ORDEN = {c[0]: i for i, c in enumerate(CATEGORIAS)}

# ── Tokens visuales: fuente única de verdad ───────────────────────────────────
# docs/design-system/tokens.json → design_tokens.py emite el bloque `:root`.
# PROHIBIDO hardcodear el bloque de tokens aquí (self_test lo verifica).
try:
    import design_tokens
    TOKENS_CSS = design_tokens.tokens_css("all")
except ImportError:  # pragma: no cover - instalación mínima sin design_tokens
    TOKENS_CSS = ""

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
    ".pnote{color:var(--muted-aa);font-size:.78rem;margin-bottom:1rem}"
    # scrollbars integradas con el tema: riel invisible, thumb sutil del panel
    "html{scrollbar-width:thin;scrollbar-color:var(--panel-bd) transparent}"
    "::-webkit-scrollbar{width:9px;height:9px}"
    "::-webkit-scrollbar-track{background:transparent}"
    "::-webkit-scrollbar-thumb{background:var(--panel-bd);border-radius:5px;"
    "border:2px solid transparent;background-clip:padding-box}"
    "::-webkit-scrollbar-thumb:hover{background:var(--muted);border:2px solid transparent;"
    "background-clip:padding-box}"
    # contrato de accesibilidad (design-system.md §7)
    ":focus-visible{outline:2px solid var(--focus);outline-offset:2px;border-radius:4px}"
    "@media (prefers-reduced-motion: reduce){*,*::before,*::after{transition:none!important;animation:none!important}}"
)

# JS compartido por TODAS las páginas del portal: aplica el tema guardado,
# escucha cambios de tema del shell (postMessage) y, si la página declara
# data-page-id, avisa al shell qué página se abrió (navegación interna).
PAGE_JS = r"""
(function(){
  var root=document.documentElement;
  function saved(){try{return localStorage.getItem('dir-tema');}catch(e){return null;}}
  function apl(t){root.dataset.theme=t||(matchMedia('(prefers-color-scheme: light)').matches?'claro':'oscuro');}
  /* ?tema=claro|oscuro en la URL gana sobre lo guardado (capturas, enlaces) */
  var q=null;try{q=new URLSearchParams(location.search).get('tema');}catch(e){}
  apl(q==='claro'||q==='oscuro'?q:saved());
  window.addEventListener('message',function(e){var d=e.data||{};if(d.portal==='tema'){apl(d.tema);}});
  var pid=document.body&&document.body.getAttribute('data-page-id');
  if(pid&&window.parent!==window){
    try{window.parent.postMessage({portal:'abierto',id:pid},'*');}catch(e){}
  }
  /* Ctrl+K dentro del iframe: la tecla nunca llega al shell (el navegador se
     la queda) — la página la consume y la reenvía por postMessage. */
  document.addEventListener('keydown',function(e){
    if(window.parent===window)return;
    var tag=(e.target&&e.target.tagName||'').toLowerCase();
    var typing=tag==='input'||tag==='textarea'||tag==='select'||(e.target&&e.target.isContentEditable);
    if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){
      e.preventDefault();
      try{window.parent.postMessage({portal:'hotkey-search'},'*');}catch(e2){}
    }else if(e.key==='/'&&!typing){
      e.preventDefault();
      try{window.parent.postMessage({portal:'hotkey-search'},'*');}catch(e2){}
    }
  },true);
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
    # Reglas por rol gobernante. Orden: primero lo más específico para que
    # keywords genéricas ("report", "pipeline") no capturen artefactos ajenos.
    # v2.29: pipeline-state es evidencia derivada de recibos + cadena de
    # auditoría (owner: orchestrator, junto a spec/audit/) → auditoria.
    ("auditoria", ("audit", "auditoria", "auditoría", "receipt", "recibo",
                   "changelog", "memory", "memoria", "session", "learning",
                   "handoff", "wiki", "traceability", "trazabilidad",
                   "pipeline-state")),
    ("devsecops", ("threat", "security", "seguridad", "pipeline-cicd",
                   "sast", "dast", "secret", "checklist")),
    ("agilidad", ("metric", "metricas", "métricas", "sprint", "reporte-gerencial",
                  "executive-report", "reports")),
    ("uiux", ("ux-", "ux_", "design-system", "design_system", "tokens",
              "screen-inventory", "prototipo", "wireframe")),
    # v2.29: arquitectura antes que plataforma — un ADR cuyo título menciona
    # "despliegue" (p. ej. ADR-010) es decisión de arquitectura, no operación.
    # v2.30: el diseño detallado de los devs es Desarrollo, no Arquitectura
    # (regla específica antes que la genérica "technical-design").
    ("desarrollo", ("technical-design-back", "technical-design-front", "dev-log")),
    ("arquitectura", ("adr", "architect", "arquitect", "diagram", "c4-",
                      "decision", "api-contract", "openapi", "data-model",
                      "data_model", "tech-radar", "tech_radar", "principles",
                      "principios", "exception-log", "tech-debt", "tech_debt",
                      "technical-stories", "technical-design", "governance",
                      "gobernanza")),
    ("plataforma", ("cloud", "deploy", "despliegue", "release", "slo",
                    "incident", "postmortem", "runbook", "oncall", "costs",
                    "cost-estimation", "cost-assumptions")),
    ("qa", ("test", "qa", "e2e", "cobertura", "coverage", "pact", "k6")),
    ("desarrollo", ("guia", "guide", "onboarding", "readme", "dev-docs",
                    "msw", "mocks")),
    ("negocio", ("vision", "backlog", "user-stories", "user_stories", "glossary",
                 "glosario", "epic", "personas", "stakeholder",
                 "business-rules", "business_rules", "gap", "impact-report")),
    ("procesos", ("authority", "risk-tier", "risk_tier",
                  "process-definition", "roles", "index")),
]


def infer_categoria(nombre, kind=""):
    """Categoría del portal a partir del nombre/ruta y el kind del generador."""
    if kind == "inicio":
        return "inicio"
    if kind == "metrica":
        return "agilidad"
    if kind == "diagrama":
        return "arquitectura"
    n = (nombre or "").lower()
    for cat, keys in _REGLES:
        if any(k in n for k in keys):
            return cat
    # Sin categoría genérica "Documentos": lo no clasificado es proceso del
    # arnés y check() lo advierte para que el skill gobernante lo reclame.
    return "procesos"


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
            reg = json.load(open(p, encoding="utf-8"))
        except Exception:
            pass
        else:
            _migrar_categorias(reg)
            return reg
    return {"portal_version": PORTAL_VERSION, "items": []}


_CAT_IDS = {c[0] for c in CATEGORIAS}


def _migrar_categorias(reg):
    """Re-clasifica items registrados con la taxonomía vieja (portal < 1.3).

    Los items cuya categoría ya no existe se re-infireren por ruta/kind; la
    vieja categoría "memoria" además se conserva como subgrupo plegable.
    """
    for it in reg.get("items", []):
        cat = it.get("categoria", "")
        if cat in _CAT_IDS:
            continue
        if cat == "memoria" and not it.get("grupo"):
            it["grupo"] = "memoria"
        it["categoria"] = infer_categoria(it.get("ruta", ""), it.get("kind", ""))


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
    # Advertencia: items caídos en el fallback "procesos" — su rol gobernante
    # debería reclamarlos con categoria= explícita o una keyword en _REGLES.
    huespedes = [i["id"] for i in m["items"]
                 if i.get("categoria") == "procesos" and not i.get("oculto")]
    if huespedes:
        print("portal: items en categoría fallback 'procesos' (revisar gobierno): "
              + ", ".join(huespedes), file=sys.stderr)
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
__TOKENS__
*{box-sizing:border-box}
/* contrato de accesibilidad (design-system.md §7): foco visible en todo
   interactivo + respeto a prefers-reduced-motion */
:focus-visible{outline:2px solid var(--focus);outline-offset:2px;border-radius:4px}
@media (prefers-reduced-motion: reduce){*,*::before,*::after{transition:none!important;animation:none!important}}
html{font-size:15px}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--fg);font-family:system-ui,'Segoe UI',sans-serif;
display:flex;flex-direction:column;overflow:hidden}
#topbar{display:flex;align-items:center;gap:.45rem;padding:.45rem .8rem;background:var(--panel-bg);
border-bottom:1px solid var(--panel-bd);flex:none}
#topbar button{background:var(--card-bg);border:1px solid var(--panel-bd);color:var(--fg);
border-radius:8px;padding:.28rem .55rem;cursor:pointer;font-size:.84rem;font-weight:650;white-space:nowrap}
#topbar button:hover{border-color:var(--accent)}
#brand{font-weight:800;font-size:.95rem;white-space:nowrap;display:flex;align-items:baseline;gap:.5rem}
#brand .ver{color:var(--muted-aa);font-weight:500;font-size:.73rem}
#searchbox{position:relative;flex:1;max-width:520px;margin:0 auto;display:flex;gap:.35rem;align-items:center}
#searchbox button{flex:none}
#q{flex:1;width:100%;background:var(--card-bg);border:1px solid var(--panel-bd);color:var(--fg);
border-radius:8px;padding:.35rem .7rem;font-size:.87rem}
#q:focus{outline:none;border-color:var(--accent)}
#qres{position:absolute;top:110%;left:0;right:0;background:var(--panel-bg);border:1px solid var(--panel-bd);
border-radius:10px;box-shadow:0 12px 40px var(--shadow);display:none;max-height:62vh;overflow-y:auto;z-index:60;
scrollbar-width:thin;scrollbar-color:var(--panel-bd) transparent}
#qres::-webkit-scrollbar{width:8px}
#qres::-webkit-scrollbar-thumb{background:var(--panel-bd);border-radius:4px}
.qhead{font-size:.7rem;color:var(--muted-aa);text-transform:uppercase;letter-spacing:.06em;
padding:.45rem .8rem .2rem}
.qempty{padding:.7rem .8rem;color:var(--sub);font-size:.84rem;font-style:italic}
#helpwrap{position:relative}
#helpbox{position:absolute;top:110%;right:0;width:340px;background:var(--panel-bg);border:1px solid var(--panel-bd);
border-radius:10px;box-shadow:0 12px 40px var(--shadow);display:none;z-index:60;padding:.9rem 1.1rem;font-size:.84rem}
#helpbox h3{margin:0 0 .5rem;font-size:.87rem;color:var(--txt)}
#helpbox ul{margin:0;padding-left:1.1rem;color:var(--sub);line-height:1.55}
#helpbox li{margin:.3rem 0}
#helpbox b{color:var(--fg)}
#crumbs{display:flex;align-items:center;gap:.45rem;padding:.28rem .8rem;background:var(--panel-bg);
border-bottom:1px solid var(--panel-bd);font-size:.77rem;color:var(--muted-aa);flex:none;white-space:nowrap;
overflow:hidden;text-overflow:ellipsis}
#crumbs button{background:var(--card-bg);border:1px solid var(--panel-bd);color:var(--fg);border-radius:6px;
padding:.05rem .45rem;cursor:pointer;font-size:.8rem;line-height:1.3}
#crumbs button:hover{border-color:var(--accent)}
#crumbs .hsep{width:1px;height:14px;background:var(--panel-bd);margin:0 .15rem;flex:none}
#crumbs a{color:var(--sub);text-decoration:none}
#crumbs a:hover{color:var(--txt);text-decoration:underline}
#crumbs .sep{color:var(--sub);font-weight:700;margin:0 .1rem}
#crumbs b{color:var(--fg);font-weight:650}
.qr{padding:.5rem .8rem;border-bottom:1px solid var(--panel-bd);cursor:pointer}
.qr:last-child{border-bottom:none}
.qr:hover,.qr.sel{background:var(--card-bg)}
.qr b{font-size:.87rem;color:var(--txt)}
.qc{font-size:.7rem;color:var(--accent);margin-left:.5rem;text-transform:uppercase;letter-spacing:.05em}
.qx{font-size:.77rem;color:var(--sub);margin-top:.15rem;line-height:1.35}
mark{background:rgba(245,158,11,.35);color:inherit;border-radius:2px;padding:0 1px}
#layout{flex:1;display:flex;min-height:0;position:relative}
#side{width:272px;flex:none;background:var(--panel-bg);border-right:1px solid var(--panel-bd);
overflow-y:auto;padding:.6rem .55rem;transition:width .18s,margin-left .18s;
scrollbar-width:thin;scrollbar-color:transparent transparent}
#side:hover{scrollbar-color:var(--panel-bd) transparent}
#side::-webkit-scrollbar{width:8px}
#side::-webkit-scrollbar-track{background:transparent}
#side::-webkit-scrollbar-thumb{background:transparent;border-radius:4px}
#side:hover::-webkit-scrollbar-thumb{background:var(--panel-bd)}
/* riel de iconos: colapsado NO desaparece — queda un rail de 54px con los
   iconos de categoría; al pasar el cursor se despliega como flyout (overlay,
   sin empujar el contenido) */
body.side-off #side{position:absolute;z-index:40;top:0;bottom:0;left:0;width:54px;
padding:.6rem .3rem;overflow:hidden}
body.side-off #main{margin-left:54px}
body.side-off #side:hover{width:272px;overflow-y:auto;box-shadow:8px 0 30px var(--shadow)}
body.side-off #side:not(:hover) #nav summary{font-size:0;gap:0;justify-content:center;padding:.5rem 0}
body.side-off #side:not(:hover) #nav summary>span:first-child{font-size:1.05rem}
body.side-off #side:not(:hover) #nav summary::before,
body.side-off #side:not(:hover) #nav summary .cnt,
body.side-off #side:not(:hover) #nav .grp,
body.side-off #side:not(:hover) #nav a.ni,
body.side-off #side:not(:hover) #nav details.menu-grupo{display:none}
#nav details.cat{margin-bottom:.25rem}
#nav summary{cursor:pointer;list-style:none;display:flex;align-items:center;gap:.45rem;
padding:.42rem .5rem;border-radius:8px;font-size:.9rem;font-weight:700;color:var(--txt);user-select:none}
#nav summary:hover{background:var(--card-bg)}
#nav summary::-webkit-details-marker{display:none}
#nav summary::before{content:"▸";color:var(--accent);transition:.15s;font-size:.67rem}
#nav details[open]>summary::before{transform:rotate(90deg)}
#nav summary .cnt{margin-left:auto;font-size:.67rem;color:var(--muted-aa);background:var(--card-bg);
border:1px solid var(--panel-bd);border-radius:8px;padding:0 6px}
#nav .grp{font-size:.73rem;text-transform:uppercase;letter-spacing:.07em;color:var(--sub);margin:.55rem .5rem .15rem}
#nav details.menu-grupo{margin:0 0 0 .6rem}
#nav details.menu-grupo>summary{font-size:.8rem;font-weight:600;color:var(--sub);padding:.28rem .5rem}
#nav details.menu-grupo>summary::before{font-size:.6rem;color:var(--muted-aa)}
#nav details.menu-grupo .grp-t{text-transform:uppercase;letter-spacing:.07em;font-size:.67rem;color:var(--sub)}
#nav details.menu-grupo a.ni{padding-left:2.2rem}
#nav a.ni{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;
padding:.3rem .5rem .3rem 1.6rem;border-radius:7px;color:var(--sub);
text-decoration:none;font-size:.9rem;line-height:1.25}
#nav a.ni:hover{background:var(--card-bg);color:var(--txt)}
#nav a.ni.act{background:color-mix(in srgb, var(--accent) 18%, transparent);color:var(--txt);font-weight:650}
#main{flex:1;min-width:0;position:relative;background:var(--bg)}
#frame{border:none;width:100%;height:100%;transform-origin:0 0;display:block}
/* estado loading del iframe (PANT-08): spinner del shell hasta que carga la página */
#loadstate{position:absolute;inset:0;display:none;align-items:center;justify-content:center;gap:.7rem;
background:var(--bg);color:var(--sub);font-size:.87rem;z-index:10}
#loadstate.on{display:flex}
#loadstate .spin{width:18px;height:18px;border-radius:50%;border:2px solid var(--panel-bd);
border-top-color:var(--accent);animation:spin 1s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
#welcome{position:absolute;inset:0;overflow-y:auto;padding:3rem;max-width:760px;display:none}
#welcome h1{font-size:1.5rem}
#welcome p{color:var(--sub);line-height:1.6}
#welcome code{background:var(--card-bg);border:1px solid var(--panel-bd);border-radius:5px;padding:.1em .4em;font-size:.88em}
@media(max-width:860px){
#side{position:absolute;z-index:50;height:100%;box-shadow:8px 0 30px var(--shadow)}
body.side-off #side{display:none}
body.side-off #main{margin-left:0}
#brand .ver{display:none}}
</style>
</head>
<body>
<header id="topbar">
  <button id="btn-side" aria-label="Contraer el menú a un riel de iconos o expandirlo" title="Contraer el menú a un riel de iconos / expandirlo">☰</button>
  <div id="brand" title="portal v__PVERSION__ · arnés v__HVERSION__">◈ <span>__PROYECTO__</span></div>
  <div id="searchbox"><button id="btn-search" aria-label="Buscar en todo el portal" title="Buscar en todo el portal (Ctrl+K o /)">🔍</button><input id="q" type="search" aria-label="Buscar en todo el portal" placeholder="Buscar en todo el portal… (Ctrl+K o /)" autocomplete="off" spellcheck="false"><div id="qres" role="listbox" aria-label="Resultados de búsqueda"></div></div>
  <span id="topxtra"></span>
  <div id="helpwrap"><button id="btn-help" aria-label="Ayuda: cómo navegar el portal" title="Ayuda — cómo navegar el portal" aria-expanded="false">?</button>
    <div id="helpbox"><h3>Cómo navegar este portal</h3><ul>
      <li><b>Menú lateral</b>: todo el contenido agrupado por el rol que gobierna cada artefacto — negocio, arquitectura, desarrollo, QA, agilidad (métricas), procesos, UI/UX, DevSecOps, plataforma y auditoría. El botón ☰ lo contrae a un <b>riel de iconos</b>; pasa el cursor sobre el riel para desplegarlo.</li>
      <li><b>Ctrl+K</b> o <b>/</b>: búsqueda global en títulos y contenido de todas las páginas (funciona también con el foco dentro del contenido). El botón 🔍 hace lo mismo.</li>
      <li><b>A− / A / A+</b> y <b>☀/☾</b>: tamaño de fuente (afecta también al menú) y tema claro/oscuro, compartidos con los diagramas interactivos.</li>
      <li>Las páginas se abren dentro del portal; los enlaces internos actualizan el menú solos.</li>
      <li>La evidencia son los recibos; este portal es solo visualización (artefacto derivado).</li>
    </ul></div>
  </div>
  <button id="btn-zmenos" aria-label="Reducir tamaño de fuente" title="Reducir tamaño de fuente">A−</button>
  <button id="btn-zreset" aria-label="Restablecer tamaño de fuente" title="Tamaño original">A</button>
  <button id="btn-zmas" aria-label="Aumentar tamaño de fuente" title="Aumentar tamaño de fuente">A+</button>
  <button id="btn-tema" aria-label="Cambiar tema claro u oscuro" title="Tema claro/oscuro">☀️</button>
</header>
<div id="crumbs"><button id="btn-back" aria-label="Atrás en el historial del portal" title="Atrás (historial del portal)">‹</button><button id="btn-fwd" aria-label="Adelante en el historial del portal" title="Adelante (historial del portal)">›</button><span class="hsep"></span><span id="crumb-path"></span></div>
<div id="layout">
  <aside id="side"><nav id="nav" aria-label="Secciones del portal"></nav></aside>
  <div id="main">
    <iframe id="frame" title="Contenido del portal"></iframe>
    <div id="loadstate" role="status" aria-live="polite"><div class="spin"></div><span>Cargando página…</span></div>
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
function temaEf(){try{var q=new URLSearchParams(location.search).get('tema');if(q==='claro'||q==='oscuro')return q;}catch(e){}return temaActual()||(matchMedia('(prefers-color-scheme: light)').matches?'claro':'oscuro');}
function aplTema(t){root.dataset.theme=t;
  try{localStorage.setItem('dir-tema',t);}catch(e){}
  document.getElementById('btn-tema').textContent=t==='claro'?'\u263E':'\u2600';
  try{if(frame.contentWindow)frame.contentWindow.postMessage({portal:'tema',tema:t},'*');}catch(e){}}
document.getElementById('btn-tema').onclick=function(){aplTema(temaEf()==='claro'?'oscuro':'claro');};
frame.addEventListener('load',function(){
  document.getElementById('loadstate').classList.remove('on');
  try{if(frame.contentWindow)frame.contentWindow.postMessage({portal:'tema',tema:temaEf()},'*');}catch(e){}});

/* zoom compartido (dir-zoom): escala TODO el chrome (root rem) y además el
   iframe con scale() para que los SVG de los diagramas aprovechen el espacio */
var z=parseFloat(localStorage.getItem('dir-zoom')||'1');
function aplZoom(){z=Math.min(1.8,Math.max(0.6,z));
  try{localStorage.setItem('dir-zoom',String(z));}catch(e){}
  root.style.fontSize=(15*z)+'px';
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
    h+='<details class="cat" open><summary title="'+esc(c.label)+'"><span>'+c.icono+'</span><span class="lbl">'+esc(c.label)
      +'</span><span class="cnt">'+items.length+'</span></summary>';
    /* sub-grupos del registry: con >6 items en la categoría se pliegan
       (p. ej. 14 sprint reviews -> grupo "reports" colapsado) */
    var plegable=items.length>6, g=null, openGrp=false;
    items.forEach(function(it){
      var gr=it.grupo||'';
      if(gr!==g){
        if(openGrp)h+='</details>';
        g=gr;openGrp=false;
        if(g){
          var gn=items.filter(function(x){return (x.grupo||'')===g;}).length;
          if(plegable&&gn>1){
            h+='<details class="menu-grupo"><summary><span class="grp-t">'+esc(g)
              +'</span><span class="cnt">'+gn+'</span></summary>';
            openGrp=true;
          }else h+='<div class="grp">'+esc(g)+'</div>';
        }
      }
      h+='<a class="ni" data-id="'+it.id+'" href="#/id/'+it.id+'" title="'+esc(it.titulo)+'">'+esc(it.titulo)+'</a>';
    });
    if(openGrp)h+='</details>';
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
    var open=hb.style.display!=='block';hb.style.display=open?'block':'none';
    this.setAttribute('aria-expanded',open?'true':'false');};
  document.addEventListener('click',function(e){if(!e.target.closest('#helpwrap'))hb.style.display='none';});
  document.addEventListener('keydown',function(e){if(e.key==='Escape')hb.style.display='none';});
})();

/* routing por hash #/id/<slug> (funciona desde file://) */
function curId(){var m=/#\/id\/([A-Za-z0-9\-_]+)/.exec(location.hash||'');return m?m[1]:null;}
function mark(id){nav.querySelectorAll('.ni').forEach(function(a){
  var on=a.dataset.id===id;a.classList.toggle('act',on);
  if(on){a.setAttribute('aria-current','page');var d=a.closest('details');if(d&&!d.open)d.open=true;}
  else{a.removeAttribute('aria-current');}});}
/* miga de pan + título + última página visitada (persistida por proyecto) */
var crumbPath=document.getElementById('crumb-path');
function catLabel(id){var c=M.categorias.filter(function(x){return x.id===id;})[0];
  return c?c.icono+' '+c.label:id;}
function paint(id){
  mark(id);
  var it=byId[id],home=null;
  M.items.forEach(function(x){if(!home&&x.categoria==='inicio')home=x;});
  if(!it){crumbPath.innerHTML='<b>Inicio</b>';return;}
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
  if(frame.dataset.cur!==it.ruta){frame.dataset.cur=it.ruta;frame.src=it.ruta;
    document.getElementById('loadstate').classList.add('on');}
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
    paint(d.id);}
  /* Ctrl+K o / reenviados desde la página dentro del iframe */
  if(d.portal==='hotkey-search'){q.focus();q.select();}});

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
  var qt=q.value.trim();
  if(!res.length){
    if(qt.length>=2){
      qres.innerHTML='<div class="qempty">Sin resultados para «'+esc(qt)+'»</div>';
      qres.style.display='block';
    }else{qres.style.display='none';qres.innerHTML='';}
    return;}
  qres.innerHTML='<div class="qhead">'+res.length+' resultado'+(res.length!==1?'s':'')+'</div>'
    +res.map(function(e,i){var it=byId[e.id]||{};
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
document.getElementById('btn-search').onclick=function(){q.focus();q.select();};
document.addEventListener('keydown',function(e){
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();q.focus();q.select();return;}
  if(e.key==='/'&&!e.ctrlKey&&!e.metaKey&&!e.altKey){
    var t=document.activeElement,tag=t&&t.tagName?t.tagName.toLowerCase():'';
    if(tag!=='input'&&tag!=='textarea'&&tag!=='select'&&!(t&&t.isContentEditable)){
      e.preventDefault();q.focus();}}});
document.addEventListener('click',function(e){if(!e.target.closest('#searchbox'))cerrarRes();});

buildNav();aplTema(temaEf());aplZoom();aplSide();route();
})();
</script>
</body>
</html>
"""


def build_shell(m):
    """index.html del portal a partir del manifiesto (tokens desde design_tokens)."""
    return (_SHELL
            .replace("__PROYECTO__", html.escape(m.get("proyecto") or "proyecto"))
            .replace("__HVERSION__", html.escape(m.get("harness_version") or "?"))
            .replace("__PVERSION__", PORTAL_VERSION)
            .replace("__GENERADO__", html.escape(m.get("generado") or ""))
            .replace("__TOKENS__", TOKENS_CSS))


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
