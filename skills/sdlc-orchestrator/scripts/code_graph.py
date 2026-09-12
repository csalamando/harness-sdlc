#!/usr/bin/env python3
"""
code_graph.py — grafo de llamadas del proyecto como vistas derivadas del
indice code_intel (<root>/.codeintel/index.db), integradas al portal.

Filosofia del arnes: Python 3 stdlib puro, salida HTML/SVG autocontenida
(sin CDN — el portal debe funcionar offline), artefactos derivados y
regenerables (nunca se editan a mano), capacidad opcional: si no hay indice,
informa y sale 0.

Integracion visual (v2.27): ambas vistas usan los TOKENS_CSS del portal
(portal_lib) y la clave compartida `dir-tema` — el toggle ☀/☾ del shell
(o de los diagramas IR) las retema en vivo via postMessage; el canvas del
grafo reacciona con un MutationObserver sobre data-theme. Si portal_lib no
esta disponible (script suelto), se incrusta una copia de los tokens.

Gobierno (donde/cuando/quien):
  DONDE   vive en sdlc-orchestrator/scripts/ junto a code_intel.py.
          Emite <proyecto>/spec/diagrams/grafo-codigo.html (interactivo).
          El sweep de harness_graph.emit_portal lo registra en la categoria
          Auditoria y Trazabilidad del portal (subgrupo "codigo");
          main_proyecto lo regenera ANTES del sweep, en la misma pasada
          (garantia de inclusion, best-effort, nunca bloquea).
          (La vista grafo-modulos.html se retiro del arnes: emit_views la
          borra si un proyecto aun la tiene.)
  CUANDO  tras cada reindex (`code_intel.py index`, regla: al abrir sesion)
          y en cada `harness_graph.py --proyecto`. `check` falla si la
          vista quedo atras del indice (anti-drift, fingerprint SHA-256
          embebido en el HTML, como los demas derivados del arnes).
  QUIEN   lo ejecuta el rol de desarrollo / orquestador al reindexar.
          Lo consume cualquier dev (hubs, acoplamiento, aislados).

Matiz del esquema: las aristas del indice son a NIVEL ARCHIVO
(archivo -> nombre llamado/importado). Por eso el grafo interactivo usa
nodos=archivos (tamano = nº de simbolos) y el ranking de hubs es de
simbolos por in-degree; no se inventa atribucion simbolo->simbolo.

Comandos:
  emit   [--root .] [--out <dir>] [--include-tests]
  check  [--root .] [--out <dir>]      # anti-drift: ¿vistas al dia?
  stats  [--root .]                    # conteos y top hubs (texto)
"""
import argparse
import hashlib
import html
import json
import os
import re
import sqlite3
import sys

DB_DIR = ".codeintel"
DB_NAME = "index.db"

# Tokens del design system (tema claro/oscuro). Fuente de verdad:
# docs/design-system/tokens.json → design_tokens.py → portal_lib.TOKENS_CSS.
try:  # vendorado junto a portal_lib.py (mismo directorio)
    import portal_lib as _pl
    TOKENS_CSS = _pl.TOKENS_CSS
except Exception:
    try:
        import design_tokens as _dt
        TOKENS_CSS = _dt.tokens_css("graph")
    except Exception:  # última red de respaldo — mantener sincronizada (self_test lo verifica)
        TOKENS_CSS = (
            ":root{--bg:#0b1220;--fg:#e2e8f0;--txt:#f1f5f9;--muted:#64748b;--sub:#8ea0b8;--edge:#94a3b8;"
            "--panel-bg:#0f172a;--panel-bd:#1e293b;--card-bg:#111c33;--accent:#3b82f6;--ok:#22c55e;"
            "--warn:#f59e0b;--bad:#ef4444;--tier:#f97316;--shadow:rgba(0,0,0,.35);color-scheme:dark}"
            ":root[data-theme=claro]{--bg:#eef2f7;--fg:#1e293b;--txt:#0f172a;--muted:#64748b;--sub:#5b6b80;"
            "--edge:#64748b;--panel-bg:#ffffff;--panel-bd:#e2e8f0;--card-bg:#f8fafc;--accent:#2563eb;"
            "--ok:#16a34a;--warn:#d97706;--bad:#dc2626;--tier:#ea580c;--shadow:rgba(15,23,42,.12);color-scheme:light}"
        )

# JS de tema compartido: misma clave dir-tema y mismo postMessage que el
# shell del portal y los diagramas IR (tema dia/noche en vivo).
THEME_JS = r"""
(function(){
  var root=document.documentElement;
  function saved(){try{return localStorage.getItem('dir-tema');}catch(e){return null;}}
  function apl(t){root.dataset.theme=t||(matchMedia('(prefers-color-scheme: light)').matches?'claro':'oscuro');}
  apl(saved());
  window.addEventListener('message',function(e){var d=e.data||{};if(d.portal==='tema'){apl(d.tema);}});
  /* Ctrl+K o / dentro del iframe: reenviar al shell del portal (si lo hay) */
  document.addEventListener('keydown',function(e){
    if(window.parent===window)return;
    var tag=(e.target&&e.target.tagName||'').toLowerCase();
    var typing=tag==='input'||tag==='textarea'||tag==='select'||(e.target&&e.target.isContentEditable);
    if(((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k')||(e.key==='/'&&!typing)){
      e.preventDefault();
      try{window.parent.postMessage({portal:'hotkey-search'},'*');}catch(e2){}}
  },true);
})();
"""

# Directorios/ruido que ensucian el grafo (cobertura, vendors, tests).
EXCLUDE_SEGMENTS = {
    "coverage", "dist", "build", "out", "node_modules", "__pycache__",
    ".next", "target", "vendor", ".venv", "venv",
}
TEST_PAT = re.compile(
    r"(^|[/\\])(tests?|__tests__|specs?)([/\\])|(_test\.|\.test\.|\.spec\.|"
    r"^test_|_test$)", re.I)
NOISE_CALLS = {
    "describe", "it", "expect", "test", "beforeEach", "afterEach", "beforeAll",
    "afterAll", "vi", "jest", "mock", "require", "assert", "console",
    "setTimeout", "setInterval", "Promise", "fetch", "JSON", "Object",
    "Array", "String", "Number", "Boolean", "Math", "Error", "Map", "Set",
}
try:
    import design_tokens as _dt
    PALETTE = list(_dt.doc()["dataviz"]["palette-graph"]["value"])
except Exception:  # respaldo sincronizado con tokens.json (self_test lo verifica)
    PALETTE = ["#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#a855f7", "#06b6d4",
               "#f97316", "#84cc16", "#ec4899", "#14b8a6", "#eab308", "#6366f1"]


# ------------------------------------------------------------------ extraccion

def norm(p):
    return p.replace("\\", "/")


def is_noise_file(path):
    segs = set(norm(path).lower().split("/"))
    return bool(segs & EXCLUDE_SEGMENTS)


def module_of(path, depth=2):
    segs = norm(path).split("/")[:-1]
    return "/".join(segs[:depth]) if segs else "(raiz)"


def load_graph(db_path, include_tests=False):
    """Lee el indice y devuelve (files, edges_file, hubs, unresolved)."""
    db = sqlite3.connect(db_path)
    symbols = [tuple(r) for r in db.execute(
        "SELECT file, name, kind, line_start, line_end, signature FROM symbols")]
    edges = [tuple(r) for r in db.execute(
        "SELECT file, kind, target FROM edges")]

    keep = {}
    for f, name, kind, ls, le, sig in symbols:
        if is_noise_file(f) or (not include_tests and TEST_PAT.search(norm(f))):
            continue
        keep.setdefault(f, []).append(
            {"name": name, "kind": kind, "line": ls, "sig": sig})

    name2files = {}
    for f, syms in keep.items():
        for s in syms:
            name2files.setdefault(s["name"], set()).add(f)

    edges_file = {}
    indeg = {}
    unresolved = 0
    for f, kind, target in edges:
        if f not in keep:
            continue
        if kind == "call":
            if target in NOISE_CALLS:
                continue
            dsts = name2files.get(target)
            if not dsts:
                unresolved += 1
                continue
            indeg[target] = indeg.get(target, 0) + 1
            for d in dsts:
                if d == f:
                    continue
                e = edges_file.setdefault((f, d), {"call": 0, "import": 0})
                e["call"] += 1
        elif kind == "import":
            t = norm(target).split("/")[-1].split(".")[0]
            if not t:
                continue
            for d in keep:
                stem = norm(d).rsplit("/", 1)[-1].split(".")[0]
                if d != f and (stem == t or norm(d).endswith(norm(target))):
                    e = edges_file.setdefault((f, d), {"call": 0, "import": 0})
                    e["import"] += 1
                    break

    defs_count = {}
    for f, syms in keep.items():
        for s in syms:
            defs_count[s["name"]] = defs_count.get(s["name"], 0) + 1
    hubs = sorted(
        ((n, defs_count.get(n, 0), d) for n, d in indeg.items()),
        key=lambda x: -x[2])
    db.close()
    return keep, edges_file, hubs, unresolved


def fingerprint(keep, edges_file):
    h = hashlib.sha256()
    for f in sorted(keep):
        h.update(f.encode())
        for s in keep[f]:
            h.update(f'{s["name"]}:{s["kind"]}:{s["line"]}'.encode())
    for (a, b), e in sorted(edges_file.items()):
        h.update(f"{a}>{b}:{e['call']},{e['import']}".encode())
    return h.hexdigest()[:16]


# ------------------------------------------------------------------ HTML interactivo

def render_interactive(keep, edges_file, hubs, fp):
    dirs = sorted({module_of(f) for f in keep})
    dcolor = {d: PALETTE[i % len(PALETTE)] for i, d in enumerate(dirs)}
    nodes = []
    idx = {}
    for i, f in enumerate(sorted(keep)):
        idx[f] = i
        d = module_of(f)
        nodes.append({"id": i, "file": norm(f), "dir": d,
                      "color": dcolor[d], "nsyms": len(keep[f]),
                      "syms": sorted(s["name"] for s in keep[f])[:40]})
    links = [{"s": idx[a], "t": idx[b], "w": e["call"] + e["import"],
              "calls": e["call"], "imports": e["import"]}
             for (a, b), e in sorted(edges_file.items()) if a in idx and b in idx]
    data = {"nodes": nodes, "links": links, "dirs": dirs, "colors": dcolor,
            "hubs": [{"name": n, "defs": c, "indeg": d} for n, c, d in hubs[:25]]}
    payload = json.dumps(data, ensure_ascii=False)
    return (_TEMPLATE_INTERACTIVE
            .replace("__DATA__", payload)
            .replace("__FP__", fp)
            .replace("__TOKENS__", TOKENS_CSS)
            .replace("__THEME_JS__", THEME_JS))


_TEMPLATE_INTERACTIVE = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Grafo de codigo — llamadas entre archivos (derivado)</title>
<!-- codeintel-fingerprint: __FP__ — derivado de .codeintel/index.db; regenerar: code_graph.py emit -->
<style>
  __TOKENS__
  body { background:var(--bg); color:var(--fg); font-family:system-ui,sans-serif; margin:0; display:flex; height:100vh; overflow:hidden; }
  #side { width:280px; min-width:280px; background:var(--panel-bg); border-right:1px solid var(--panel-bd); padding:1rem; overflow-y:auto; font-size:.8rem; }
  #side h1 { font-size:1rem; margin:.2rem 0 .5rem; color:var(--txt); }
  #side .sub { color:var(--muted); font-size:.7rem; margin-bottom:.8rem; }
  #side h2 { font-size:.8rem; margin:1rem 0 .4rem; color:var(--sub); text-transform:uppercase; letter-spacing:.05em; }
  .dirf { display:flex; align-items:center; gap:.4rem; padding:2px 0; cursor:pointer; user-select:none; color:var(--fg); }
  .dirf.off { opacity:.35; }
  .dot { width:10px; height:10px; border-radius:50%; flex:none; }
  #search { width:100%; box-sizing:border-box; background:var(--card-bg); border:1px solid var(--panel-bd); color:var(--txt); border-radius:6px; padding:.35rem .5rem; font-size:.8rem; }
  #hublist div { padding:1px 0; color:var(--fg); }
  #hublist b { color:var(--warn); }
  #hublist .n { color:var(--muted); }
  #main { flex:1; position:relative; }
  canvas { display:block; width:100%; height:100%; cursor:grab; }
  #tip { position:absolute; pointer-events:none; background:var(--panel-bg); border:1px solid var(--panel-bd); color:var(--txt); border-radius:6px; padding:.35rem .6rem; font-size:.72rem; display:none; max-width:340px; box-shadow:0 4px 14px var(--shadow); }
  #detail { position:absolute; right:0; top:0; bottom:0; width:300px; background:var(--panel-bg); border-left:1px solid var(--panel-bd); padding:1rem; font-size:.78rem; overflow-y:auto; display:none; color:var(--fg); }
  #detail h3 { margin:.2rem 0; font-size:.9rem; word-break:break-all; color:var(--txt); }
  #detail .k { color:var(--muted); } #detail ul { padding-left:1.1rem; max-height:300px; overflow:auto; }
  #stats { position:absolute; left:.8rem; bottom:.6rem; color:var(--muted); font-size:.68rem; }
</style></head><body>
<div id="side">
  <h1>🕸 Grafo de codigo</h1>
  <div class="sub">Nodos = archivos (tamano = nº de simbolos) · aristas = llamadas/imports resueltos · derivado de .codeintel/index.db — no editar a mano; regenerar: code_graph.py emit</div>
  <input id="search" placeholder="buscar archivo o simbolo…">
  <h2>Directorios</h2><div id="dirlist"></div>
  <h2>Top hubs (simbolos mas llamados)</h2><div id="hublist"></div>
</div>
<div id="main"><canvas id="cv"></canvas><div id="tip"></div><div id="detail"></div><div id="stats"></div></div>
<script>__THEME_JS__</script>
<script>
const D = __DATA__;
const cv = document.getElementById('cv'), ctx = cv.getContext('2d');
const tip = document.getElementById('tip'), det = document.getElementById('detail');
let W, H, cam = {x:0, y:0, k:1};
function resize(){ W = cv.width = cv.clientWidth*devicePixelRatio; H = cv.height = cv.clientHeight*devicePixelRatio; }
addEventListener('resize', resize); resize();

// Colores desde los tokens CSS del portal: el canvas se retema con data-theme.
function cssVar(n){ return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }

// --- estado de simulacion (force-directed simple, stdlib JS)
const N = D.nodes.length;
D.nodes.forEach((n,i)=>{ const a = i*2.399963; n.x = Math.cos(a)*50*(1+i/N); n.y = Math.sin(a)*50*(1+i/N); n.vx=0; n.vy=0; });
const active = new Set(D.dirs);
function sim(steps){
  for(let s=0;s<steps;s++){
    for(let i=0;i<N;i++){ const a=D.nodes[i]; if(!active.has(a.dir)) continue;
      for(let j=i+1;j<N;j++){ const b=D.nodes[j]; if(!active.has(b.dir)) continue;
        let dx=a.x-b.x, dy=a.y-b.y, d2=dx*dx+dy*dy+0.01, f=Math.min(900/d2,8);
        dx*=f/Math.sqrt(d2); dy*=f/Math.sqrt(d2);
        a.vx+=dx; a.vy+=dy; b.vx-=dx; b.vy-=dy; } }
    for(const l of D.links){ const a=D.nodes[l.s], b=D.nodes[l.t];
      if(!active.has(a.dir)||!active.has(b.dir)) continue;
      let dx=b.x-a.x, dy=b.y-a.y, d=Math.sqrt(dx*dx+dy*dy)+0.01, f=(d-60)*0.005;
      dx*=f/d; dy*=f/d; a.vx+=dx; a.vy+=dy; b.vx-=dx; b.vy-=dy; }
    for(const n of D.nodes){ if(!active.has(n.dir)) continue;
      n.vx-=n.x*0.002; n.vy-=n.y*0.002; n.vx*=0.85; n.vy*=0.85; n.x+=n.vx; n.y+=n.vy; }
  }
}
sim(300);

let hover=null, sel=null, query='';
function visNode(n){ return active.has(n.dir) && (!query || n.file.toLowerCase().includes(query) || n.syms.some(s=>s.toLowerCase().includes(query))); }
function draw(){
  const cBg=cssVar('--bg'), cEdge=cssVar('--edge'), cWarn=cssVar('--warn'), cTxt=cssVar('--txt'), cMuted=cssVar('--muted');
  ctx.setTransform(cam.k*devicePixelRatio,0,0,cam.k*devicePixelRatio,(W/2+cam.x)*devicePixelRatio,(H/2+cam.y)*devicePixelRatio);
  ctx.fillStyle=cBg; ctx.fillRect(-1e5,-1e5,2e5,2e5);
  for(const l of D.links){ const a=D.nodes[l.s], b=D.nodes[l.t];
    if(!visNode(a)||!visNode(b)) continue;
    const hot = sel && (l.s===sel.id||l.t===sel.id);
    ctx.strokeStyle = hot ? cWarn : cEdge;
    ctx.globalAlpha = hot ? .9 : Math.min(.10 + l.w*0.04, .5);
    ctx.lineWidth = Math.min(0.6 + l.w*0.25, 5)/cam.k;
    ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke(); }
  ctx.globalAlpha=1;
  for(const n of D.nodes){ if(!visNode(n)) continue;
    const r = 4 + Math.sqrt(n.nsyms)*2.2;
    ctx.beginPath(); ctx.arc(n.x,n.y,r,0,7);
    ctx.fillStyle = n.color; ctx.globalAlpha = (hover===n||sel===n)?1:.85; ctx.fill();
    if(hover===n||sel===n){ ctx.strokeStyle=cTxt; ctx.lineWidth=1.5/cam.k; ctx.stroke(); }
    ctx.globalAlpha=1;
    if(cam.k>1.4 || hover===n){ ctx.fillStyle=cMuted; ctx.font=`${10/cam.k}px system-ui`;
      ctx.fillText(n.file.split('/').pop(), n.x+r+2, n.y+3/cam.k); } }
}
function loop(){ draw(); requestAnimationFrame(loop); } loop();

// --- interaccion: pan/zoom/hover/click
let drag=null;
function evWorld(e){ const r=cv.getBoundingClientRect();
  const px=(e.clientX-r.left)*devicePixelRatio, py=(e.clientY-r.top)*devicePixelRatio;
  return {x:(px - (W/2+cam.x)*devicePixelRatio)/(cam.k*devicePixelRatio), y:(py - (H/2+cam.y)*devicePixelRatio)/(cam.k*devicePixelRatio)}; }
cv.addEventListener('mousedown', e=>{ drag={x:e.clientX,y:e.clientY,cx:cam.x,cy:cam.y,moved:false}; });
addEventListener('mousemove', e=>{
  if(drag){ const dx=(e.clientX-drag.x), dy=(e.clientY-drag.y);
    if(Math.abs(dx)+Math.abs(dy)>3) drag.moved=true;
    cam.x=drag.cx+dx; cam.y=drag.cy+dy; return; }
  const w=evWorld(e); hover=null;
  for(const n of D.nodes){ if(!visNode(n)) continue;
    const r=4+Math.sqrt(n.nsyms)*2.2;
    if((n.x-w.x)**2+(n.y-w.y)**2 < (r+3)**2){ hover=n; break; } }
  if(hover){ tip.style.display='block';
    tip.style.left=(e.clientX+12)+'px'; tip.style.top=(e.clientY+12)+'px';
    tip.innerHTML=`<b>${hover.file}</b><br>${hover.nsyms} simbolos · ${hover.dir}`;
    cv.style.cursor='pointer';
  } else { tip.style.display='none'; cv.style.cursor=drag?'grabbing':'grab'; }
});
addEventListener('mouseup', e=>{
  if(drag && !drag.moved && hover){ sel=hover; showDetail(); }
  drag=null; });
cv.addEventListener('wheel', e=>{ e.preventDefault();
  const f = e.deltaY<0 ? 1.15 : 1/1.15; cam.k=Math.min(Math.max(cam.k*f,.15),8); }, {passive:false});
function showDetail(){ if(!sel){det.style.display='none';return;}
  const inc = D.links.filter(l=>l.t===sel.id), out = D.links.filter(l=>l.s===sel.id);
  det.style.display='block';
  det.innerHTML=`<h3>${sel.file}</h3><div class="k">${sel.dir} · ${sel.nsyms} simbolos</div>
    <p>→ llama a ${out.length} archivos · ← llamado por ${inc.length}</p>
    <b>Simbolos</b><ul>${sel.syms.map(s=>`<li>${s}</li>`).join('')}</ul>
    <b>Depende de</b><ul>${out.map(l=>`<li>${D.nodes[l.t].file} (${l.w})</li>`).join('')}</ul>
    <b>Dependen de el</b><ul>${inc.map(l=>`<li>${D.nodes[l.s].file} (${l.w})</li>`).join('')}</ul>`;
}
// --- filtros y busqueda
const dl=document.getElementById('dirlist');
D.dirs.forEach(d=>{ const el=document.createElement('div'); el.className='dirf';
  el.innerHTML=`<span class="dot" style="background:${D.colors[d]}"></span>${d}`;
  el.onclick=()=>{ active.has(d)?active.delete(d):active.add(d);
    el.classList.toggle('off'); sim(120); };
  dl.appendChild(el); });
document.getElementById('hublist').innerHTML =
  D.hubs.map(h=>`<div><b>${h.indeg}</b> × ${h.name} <span class="n">(${h.defs} def)</span></div>`).join('');
document.getElementById('search').oninput = e=>{ query=e.target.value.trim().toLowerCase(); };
document.getElementById('stats').textContent =
  `${D.nodes.length} archivos · ${D.links.length} aristas · fingerprint __FP__`;
</script></body></html>
"""


# ------------------------------------------------------------------ comandos

def resolve_db(a):
    if getattr(a, "db", None):
        return a.db
    return os.path.join(a.root, DB_DIR, DB_NAME)


def out_dir(a):
    return a.out or os.path.join(a.root, "spec", "diagrams")


def emit_views(root, out=None, include_tests=False):
    """API para otros scripts del arnes (harness_graph la llama best-effort).

    Devuelve (ruta_interactivo, n_archivos, n_aristas, unresolved, fp) o
    None si no hay indice. Limpia el retirado grafo-modulos.html (v2.27
    lo emitía; se eliminó del arnés por decisión de gobierno).
    """
    db = os.path.join(root, DB_DIR, DB_NAME)
    if not os.path.isfile(db):
        return None
    keep, edges_file, hubs, unresolved = load_graph(db, include_tests)
    fp = fingerprint(keep, edges_file)
    od = out or os.path.join(root, "spec", "diagrams")
    os.makedirs(od, exist_ok=True)
    p1 = os.path.join(od, "grafo-codigo.html")
    viejo = os.path.join(od, "grafo-modulos.html")
    if os.path.isfile(viejo):
        os.remove(viejo)
    open(p1, "w", encoding="utf-8", newline="\n").write(
        render_interactive(keep, edges_file, hubs, fp))
    return p1, len(keep), len(edges_file), unresolved, fp


def cmd_emit(a):
    r = emit_views(os.path.abspath(a.root) if not a.db else a.root,
                   out=a.out, include_tests=a.include_tests) if not a.db else None
    if a.db:
        # modo --db directo (analisis fuera de un proyecto gobernado)
        if not os.path.isfile(a.db):
            print(f"SIN ÍNDICE: {a.db} no existe (capacidad opcional, nada que hacer).")
            return 0
        keep, edges_file, hubs, unresolved = load_graph(a.db, a.include_tests)
        fp = fingerprint(keep, edges_file)
        od = out_dir(a)
        os.makedirs(od, exist_ok=True)
        p1 = os.path.join(od, "grafo-codigo.html")
        open(p1, "w", encoding="utf-8", newline="\n").write(
            render_interactive(keep, edges_file, hubs, fp))
        r = (p1, len(keep), len(edges_file), unresolved, fp)
    if not r:
        print(f"SIN ÍNDICE: {resolve_db(a)} no existe — correr primero: "
              f"code_intel.py index (capacidad opcional, nada que hacer).")
        return 0
    p1, nf, ne, unresolved, fp = r
    print(f"Grafo emitido (fingerprint {fp}):")
    print(f"  {p1}  — {nf} archivos, {ne} aristas "
          f"(interactivo; {unresolved} llamadas no resueltas a símbolos indexados)")
    print("  El portal lo recoge en Auditoría y Trazabilidad al regenerar: "
          "harness_graph.py --proyecto .")
    return 0


def cmd_check(a):
    db = resolve_db(a)
    p1 = os.path.join(out_dir(a), "grafo-codigo.html")
    if not os.path.isfile(db):
        print("CODE_GRAPH CHECK OK: sin índice code_intel (capacidad opcional).")
        return 0
    keep, edges_file, _, _ = load_graph(db, a.include_tests)
    fp = fingerprint(keep, edges_file)
    prev = None
    if os.path.isfile(p1):
        m = re.search(r"codeintel-fingerprint: ([0-9a-f]+)",
                      open(p1, encoding="utf-8", errors="replace").read(4096))
        if m:
            prev = m.group(1)
    if prev != fp:
        print("DRIFT: spec/diagrams/grafo-*.html falta o quedó atrás del índice "
              "(regenerar: code_graph.py emit)")
        return 1
    print(f"CODE_GRAPH CHECK OK: vistas al día con el índice ({fp}).")
    return 0


def cmd_stats(a):
    db = resolve_db(a)
    if not os.path.isfile(db):
        print(f"SIN ÍNDICE: {db}")
        return 0
    keep, edges_file, hubs, unresolved = load_graph(db, a.include_tests)
    print(f"archivos: {len(keep)} · símbolos: {sum(len(v) for v in keep.values())} "
          f"· aristas archivo→archivo: {len(edges_file)} · no resueltas: {unresolved}")
    print("top hubs (símbolos más llamados):")
    for n, c, d in hubs[:15]:
        print(f"  {d:4d} × {n} ({c} def)")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["emit", "check", "stats"])
    ap.add_argument("--root", default=".", help="raíz del proyecto gobernado")
    ap.add_argument("--db", help="ruta directa al index.db (omite --root)")
    ap.add_argument("--out", help="directorio de salida (default <root>/spec/diagrams)")
    ap.add_argument("--include-tests", action="store_true",
                    help="incluir archivos de test (por defecto se excluyen: ruido)")
    a = ap.parse_args()
    sys.exit({"emit": cmd_emit, "check": cmd_check, "stats": cmd_stats}[a.cmd](a))


if __name__ == "__main__":
    main()
