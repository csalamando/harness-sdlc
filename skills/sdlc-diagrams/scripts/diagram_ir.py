#!/usr/bin/env python3
"""diagram_ir.py — Renderer determinista de diagramas interactivos desde IR JSON (ADR-003).

El IR (*.ir.json) es la fuente de verdad versionada; el HTML/SVG es una vista
derivada auto-contenida (sin red, sin dependencias). Cero tokens en el render.

Subcomandos:
  render   --ir FILE.ir.json --out FILE.html     Genera la vista interactiva
  validate --ir FILE.ir.json                     Esquema + referencias (exit 1 si invalido)
  diff     --old A.ir.json --new B.ir.json       Before/After: agregados/eliminados/cambiados
  check    --ir FILE.ir.json --out FILE.html     exit 1 si el HTML quedo atras (drift)

Tipos: flow (architecture|workflow|dataflow|lifecycle via "bandas") y sequence.

Vista (v1.1):
  - Tema claro/oscuro con toggle en la toolbar (persiste en localStorage;
    default: campo "tema" del IR, si no prefers-color-scheme del navegador).
  - Controles de tamano de fuente A- / A / A+ (zoom del diagrama, persiste).
  - Campo opcional "ubicacion" en nodos/participantes: pill con icono
    (nube/on-prem) en la esquina superior — vital en diagramas de arquitectura
    para mostrar DONDE corre cada componente (AWS, Azure, GCP, on-premise...).
  - Los textos de los nodos NUNCA desbordan: titulo hasta 2 lineas con wrap y
    sub con elipsis, calculado de forma determinista (sin medir fuentes).

Python 3 stdlib puro.
"""
import argparse, html, json, sys

VERSION = "1.1.0"

TIPO_BASE = {
    "ui": ("#38bdf8", "◉"), "edge": ("#2dd4bf", "⇄"), "service": ("#a78bfa", "⟨⟩"),
    "security": ("#f59e0b", "⛨"), "db": ("#34d399", "⛁"), "job": ("#94a3b8", "⚙"),
    "decision": ("#f472b6", "◇"), "terminal": ("#e2e8f0", "◎"),
    "source": ("#38bdf8", "▤"), "transform": ("#a78bfa", "ƒ"), "store": ("#34d399", "⛁"),
    "consumer": ("#fbbf24", "▸"), "start": ("#2dd4bf", "▶"), "waiting": ("#fbbf24", "⏸"),
    "failure": ("#fb7185", "✖"),
}

# ════════════════════════ VALIDACION ════════════════════════

def load_ir(path):
    with open(path, encoding="utf-8") as f:
        ir = json.load(f)
    if "kind" not in ir:
        ir["kind"] = "sequence" if "participantes" in ir else "flow"
    return ir

def validate_ir(ir):
    errs = []
    if not ir.get("titulo"):
        errs.append("falta 'titulo'")
    if ir.get("tema") not in (None, "", "claro", "oscuro"):
        errs.append(f"tema '{ir.get('tema')}' invalido (claro|oscuro)")
    kind = ir.get("kind", "flow")
    if kind == "sequence":
        ids = set()
        for p in ir.get("participantes", []):
            if not p.get("id") or not p.get("titulo"):
                errs.append(f"participante sin id/titulo: {p!r}")
            ids.add(p.get("id"))
            if p.get("tipo") not in TIPO_BASE:
                errs.append(f"participante '{p.get('id')}' tipo desconocido '{p.get('tipo')}'")
        for i, m in enumerate(ir.get("mensajes", []), 1):
            if m.get("desde") not in ids or m.get("hasta") not in ids:
                errs.append(f"mensaje #{i} referencia participante inexistente: {m.get('desde')}→{m.get('hasta')}")
            if not m.get("label"):
                errs.append(f"mensaje #{i} sin label")
    else:
        ids = set()
        for n in ir.get("nodos", []):
            if not n.get("id") or not n.get("titulo"):
                errs.append(f"nodo sin id/titulo: {n!r}")
            ids.add(n.get("id"))
            if n.get("tipo") not in TIPO_BASE and n.get("tipo") not in (ir.get("tipos") or {}):
                errs.append(f"nodo '{n.get('id')}' tipo desconocido '{n.get('tipo')}'")
            g = n.get("grupo")
            if g and ir.get("grupos") and g not in ir["grupos"]:
                errs.append(f"nodo '{n.get('id')}' grupo '{g}' no declarado en 'grupos'")
        for e in ir.get("aristas", []):
            if e.get("desde") not in ids or e.get("hasta") not in ids:
                errs.append(f"arista referencia nodo inexistente: {e.get('desde')}→{e.get('hasta')}")
            if not e.get("label"):
                errs.append(f"arista {e.get('desde')}→{e.get('hasta')} sin label")
        if ir.get("bandas") not in (None, "hulls", "filas", "columnas"):
            errs.append(f"bandas '{ir.get('bandas')}' invalido (hulls|filas|columnas)")
    for c in ir.get("insights", []):
        if not c.get("titulo") or not c.get("bullets"):
            errs.append(f"insight sin titulo/bullets: {c!r}")
    return errs

# ════════════════════════ AJUSTE DE TEXTO (sin desborde) ════════════════════════

def _tw(t, fs):
    """Ancho aproximado del texto en px (determinista, sin medir fuentes)."""
    w = 0.0
    for ch in t:
        if ch in " iljI.,:;|'`":
            w += 0.30
        elif ch in "mwMW@":
            w += 0.82
        elif ch.isupper() or ch.isdigit():
            w += 0.60
        else:
            w += 0.50
    return w * fs

def _ellipsize(text, fs, max_w):
    if _tw(text, fs) <= max_w:
        return text
    t = text
    while t and _tw(t + "…", fs) > max_w:
        t = t[:-1]
    return t.rstrip() + "…"

def _wrap(text, fs, max_w, max_lines=2):
    """Envuelve por palabras; si excede max_lines, la ultima lleva elipsis."""
    if _tw(text, fs) <= max_w:
        return [text]
    lines, cur = [], ""
    for wd in text.split():
        trial = (cur + " " + wd).strip()
        if _tw(trial, fs) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        resto = " ".join(lines[max_lines - 1:])
        lines = lines[:max_lines - 1] + [_ellipsize(resto, fs, max_w)]
    return lines

# ════════════════════════ UBICACION (cloud / on-prem) ════════════════════════

def _ubi_icon(ub):
    u = ub.lower()
    if any(k in u for k in ("on-prem", "onprem", "on premise", "datacenter", "data center", "local", "edge")):
        return "⌂"
    if any(k in u for k in ("aws", "azure", "gcp", "google", "cloud", "ibm", "oracle", "oci",
                            "saas", "railway", "vercel", "render", "fly.io", "heroku", "akamai", "cloudflare")):
        return "☁"
    return "◈"

def _badge(x, y, w_node, ub, c):
    """Pill de ubicacion en la esquina superior derecha del nodo."""
    label = f"{_ubi_icon(ub)} {ub}"
    w = _tw(label, 9) + 16
    bx = x + w_node - w - 5
    return (f'<g class="ubadge"><rect x="{bx:.0f}" y="{y - 8}" width="{w:.0f}" height="16" rx="8" '
            f'style="fill:var(--chip-bg)" stroke="{c}" stroke-width="0.9"/>'
            f'<text x="{bx + w / 2:.0f}" y="{y + 3.4}" font-size="9" text-anchor="middle" '
            f'style="fill:var(--sub)">{html.escape(label)}</text></g>')

# ════════════════════════ MOTOR DE FLUJO ════════════════════════

NW, NH, RX, RY, MX, MY = 210, 68, 120, 95, 60, 135

def _ranks(ir):
    fwd = [e for e in ir["aristas"] if not e.get("back")]
    succ = {}
    for e in fwd:
        succ.setdefault(e["desde"], []).append(e["hasta"])
    memo = {n["id"]: n["rank"] for n in ir["nodos"] if "rank" in n}
    def solve(nid, seen=frozenset()):
        if nid in memo:
            return memo[nid]
        if nid in seen:
            return 0
        ups = [e["desde"] for e in fwd if e["hasta"] == nid]
        memo[nid] = 0 if not ups else 1 + max(solve(u, seen | {nid}) for u in ups)
        return memo[nid]
    for n in ir["nodos"]:
        solve(n["id"])
    for n in ir["nodos"]:
        nid = n["id"]
        if "rank" in n:
            continue
        ups = [e["desde"] for e in fwd if e["hasta"] == nid]
        if not ups and succ.get(nid):
            memo[nid] = max(0, min(memo[s] for s in succ[nid]) - 1)
    return memo

def _layout(ir):
    rk = _ranks(ir)
    orden = {}
    for n in ir["nodos"]:
        orden.setdefault(rk[n["id"]], []).append(n["id"])
    preds = {n["id"]: [e["desde"] for e in ir["aristas"] if e["hasta"] == n["id"] and not e.get("back")] for n in ir["nodos"]}
    succs = {n["id"]: [e["hasta"] for e in ir["aristas"] if e["desde"] == n["id"] and not e.get("back")] for n in ir["nodos"]}
    for _ in range(6):
        for k in sorted(orden):
            orden[k] = sorted(orden[k], key=lambda nid: (
                lambda bs: sum(bs) / len(bs) if bs else orden[k].index(nid))(
                [orden[rk[p]].index(p) for p in preds[nid] if rk.get(p, -1) < k and p in orden.get(rk.get(p), [])]))
        for k in sorted(orden, reverse=True):
            orden[k] = sorted(orden[k], key=lambda nid: (
                lambda bs: sum(bs) / len(bs) if bs else orden[k].index(nid))(
                [orden[rk[s]].index(s) for s in succs[nid] if rk.get(s, 99) > k and s in orden.get(rk.get(s), [])]))
    pos = {}
    for k, col in orden.items():
        for i, nid in enumerate(col):
            pos[nid] = (MX + k * (NW + RX), MY + i * (NH + RY))
    W = MX * 2 + (max(orden) + 1) * (NW + RX) - RX
    nback = sum(1 for e in ir["aristas"] if e.get("back") or rk[e["hasta"]] <= rk[e["desde"]])
    H = max(p[1] for p in pos.values()) + NH + 60 + nback * 30
    return pos, W, H, rk

def _hv(p1, p2):
    x1, y1 = p1; x2, y2 = p2
    if abs(y2 - y1) < 2:
        return f"M{x1},{y1} L{x2},{y2}"
    mx, r = x1 + max(36, (x2 - x1) / 2), 10
    sy = 1 if y2 > y1 else -1
    return f"M{x1},{y1} L{mx-r},{y1} Q{mx},{y1} {mx},{y1+sy*r} L{mx},{y2-sy*r} Q{mx},{y2} {mx+r},{y2} L{x2},{y2}"

def _vh(p1, p2):
    x1, y1 = p1; x2, y2 = p2
    if abs(x2 - x1) < 2:
        return f"M{x1},{y1} L{x2},{y2}"
    my, r = y1 + (1 if y2 > y1 else -1) * max(30, abs(y2 - y1) / 2), 10
    sx = 1 if x2 > x1 else -1
    sy = 1 if y2 > y1 else -1
    return f"M{x1},{y1} L{x1},{my-sy*r} Q{x1},{my} {x1+sx*r},{my} L{x2-sx*r},{my} Q{x2},{my} {x2},{my+sy*r} L{x2},{y2}"

def _bandas(ir, pos, W, H):
    modo = ir.get("bandas", "hulls")
    out = []
    for g, color in (ir.get("grupos") or {}).items():
        if modo == "columnas":
            xs = [pos[n["id"]][0] for n in ir["nodos"] if n.get("grupo") == g]
            if not xs:
                continue
            out.append(f'<g class="hull"><rect x="{min(xs)-30}" y="{MY-52}" width="{max(xs)-min(xs)+NW+60}" height="{H-MY+30}" rx="4" '
                       f'fill="{color}05" stroke="{color}66" stroke-width="1.1" stroke-dasharray="4 6"/>'
                       f'<text x="{min(xs)-14}" y="{MY-28}" fill="{color}" font-size="10.5" font-weight="700" letter-spacing="1.6">{html.escape(g).upper()}</text></g>')
        elif modo == "filas":
            ys = [pos[n["id"]][1] for n in ir["nodos"] if n.get("grupo") == g]
            if not ys:
                continue
            out.append(f'<g class="hull"><rect x="{MX-30}" y="{min(ys)-44}" width="{W-MX*2+60}" height="{max(ys)-min(ys)+NH+70}" rx="4" '
                       f'fill="{color}05" stroke="{color}66" stroke-width="1.1" stroke-dasharray="4 6"/>'
                       f'<text x="{MX-12}" y="{min(ys)-22}" fill="{color}" font-size="10.5" font-weight="700" letter-spacing="1.6">{html.escape(g).upper()}</text></g>')
        else:
            ns = [pos[n["id"]] for n in ir["nodos"] if n.get("grupo") == g]
            if not ns:
                continue
            x1 = min(p[0] for p in ns) - 26
            y1 = min(p[1] for p in ns) - 46
            out.append(f'<g class="hull"><rect x="{x1}" y="{y1}" width="{max(p[0] for p in ns)-x1+NW+26}" height="{max(p[1] for p in ns)-y1+NH+26}" rx="14" '
                       f'fill="{color}08" stroke="{color}" stroke-width="1.2" stroke-dasharray="6 5" opacity=".85"/>'
                       f'<text x="{x1+16}" y="{y1+24}" fill="{color}" font-size="11" font-weight="700" letter-spacing="2">{html.escape(g).upper()}</text></g>')
    return "".join(out)

_JS_FLOW = """
const DATOS=%s, RELS=%s, COLORES=%s;
let lens=[];
function aplicar(focus){
  const act=new Set(lens);
  document.querySelectorAll('.node').forEach(g=>{
    const id=g.dataset.id, t=g.dataset.tipo; let dim=false;
    if(act.size) dim=!act.has(t);
    if(focus) dim=!(id===focus||(RELS[focus]||[]).some(r=>r[1]===id));
    g.style.opacity=dim?.12:1;
    const card=g.querySelector('.card'); if(card) card.setAttribute('stroke-width', id===focus?2.6:1.4);
  });
  document.querySelectorAll('.edge').forEach(g=>{
    let dim=false;
    if(focus) dim=!(g.dataset.f===focus||g.dataset.t===focus);
    if(act.size&&!focus){const a=document.querySelector(`.node[data-id="${g.dataset.f}"]`).dataset.tipo,
      b=document.querySelector(`.node[data-id="${g.dataset.t}"]`).dataset.tipo; dim=!(act.has(a)&&act.has(b));}
    g.style.opacity=dim?.08:1;
  });
  document.querySelectorAll('.chip').forEach(c=>{
    c.style.opacity=(act.size&&!act.has(c.dataset.tipo))?.4:1;
    c.querySelector('rect').setAttribute('stroke-width', act.has(c.dataset.tipo)?2.4:1);
  });
  document.querySelectorAll('.hull').forEach(h=>h.style.opacity=focus?.25:.9);
}
function panel(id){
  const p=document.getElementById('det'), d=DATOS[id];
  if(!id){p.style.display='none';return;}
  const rel=(RELS[id]||[]).map(r=>`<li>${r[0]} <b>${DATOS[r[1]].titulo}</b> <span style="color:var(--muted)">· ${r[2]}</span></li>`).join('');
  p.innerHTML=`<div style="display:flex;justify-content:space-between;align-items:center">
    <b style="color:${COLORES[d.tipo]}">${d.titulo}</b>
    <span style="cursor:pointer;color:var(--muted)" onclick="foco(null)">✕</span></div>
    <div style="color:var(--sub);font-size:12px;margin:.2rem 0">${d.sub} — ${d.grupo||''} · tipo ${d.tipo}${d.ubicacion?' · 📍 '+d.ubicacion:''}</div>
    <div style="font-size:12.5px;margin:.4rem 0">${d.detalle||''}</div>
    <ul style="margin:.3rem 0 0;padding-left:1.1rem;font-size:12px;color:var(--fg)">${rel}</ul>`;
  p.style.display='block';
}
function foco(id){ window._f=id; aplicar(id); panel(id);
  history.replaceState(null,'',id?'#focus='+id:location.pathname); }
document.querySelectorAll('.node').forEach(g=>g.addEventListener('click',ev=>{
  ev.stopPropagation(); foco(window._f===g.dataset.id?null:g.dataset.id);}));
document.querySelectorAll('.chip').forEach(c=>c.addEventListener('click',()=>{
  const t=c.dataset.tipo, i=lens.indexOf(t);
  if(i>=0) lens.splice(i,1); else { lens.push(t); if(lens.length>2) lens.shift(); }
  aplicar(window._f);
  history.replaceState(null,'',lens.length?'#lens='+lens.join('~'):location.pathname);}));
document.body.addEventListener('click',()=>foco(null));
const h=location.hash;
if(h.startsWith('#focus=')) foco(h.slice(7));
if(h.startsWith('#lens=')){ lens=h.slice(6).split('~'); aplicar(null); }
"""

_CSS_BASE = (
    ":root{--bg:#0b1220;--fg:#e2e8f0;--txt:#f1f5f9;--muted:#64748b;--sub:#8ea0b8;--edge:#94a3b8;"
    "--edge-label:#a5b4c9;--chip-bg:#0b1220;--chip-bd:#1e293b;--panel-bg:#0f172a;--panel-bd:#1e293b;"
    "--life:#334155;--act-bg:#1e293b;--act-bd:#475569;--seq-msg:#cbd5e1;--seq-ret:#64748b;--shadow:rgba(0,0,0,.35)}"
    ":root[data-theme=claro]{--bg:#eef2f7;--fg:#1e293b;--txt:#0f172a;--muted:#64748b;--sub:#5b6b80;--edge:#64748b;"
    "--edge-label:#475569;--chip-bg:#ffffff;--chip-bd:#cbd5e1;--panel-bg:#ffffff;--panel-bd:#e2e8f0;"
    "--life:#cbd5e1;--act-bg:#e2e8f0;--act-bd:#94a3b8;--seq-msg:#334155;--seq-ret:#94a3b8;--shadow:rgba(15,23,42,.10)}"
    "body{background:var(--bg);margin:0;padding:2.2rem;font-family:system-ui;color:var(--fg)}"
    "svg{width:100%;max-width:1180px;height:auto;display:block;margin:0 auto}"
    ".node,.edge,.chip,.hull,.msg,.life,.act{transition:opacity .18s}"
    ".insights{display:flex;gap:1rem;max-width:1180px;margin:1.2rem auto 0;flex-wrap:wrap}"
    ".ins{flex:1;min-width:250px;background:var(--panel-bg);border:1px solid var(--panel-bd);border-radius:12px;padding:1rem 1.2rem}"
    ".ins b{display:flex;align-items:center;gap:.5rem;font-size:13.5px;color:var(--txt)}"
    ".ins .dot{width:9px;height:9px;border-radius:50%;flex:none}"
    ".ins ul{margin:.55rem 0 0;padding-left:1.1rem;font-size:12.5px;color:var(--sub);line-height:1.45}"
    ".ins li{margin:.28rem 0}"
    "#det{display:none;position:fixed;left:2rem;bottom:2rem;max-width:360px;background:var(--panel-bg);"
    "border:1px solid var(--panel-bd);border-radius:12px;padding:1rem 1.2rem;box-shadow:0 8px 30px var(--shadow);z-index:9}"
    "#toolbar{position:fixed;top:1rem;right:1rem;display:flex;gap:.35rem;z-index:10}"
    "#toolbar button{background:var(--panel-bg);border:1px solid var(--panel-bd);color:var(--fg);"
    "border-radius:8px;padding:.28rem .55rem;cursor:pointer;font-size:12.5px;font-weight:650}"
    "#toolbar button:hover{border-color:var(--edge)}")

_TOOLBAR = ("<div id='toolbar'>"
            "<button id='btn-tema' title='Tema claro/oscuro'>☀</button>"
            "<button id='btn-zmenos' title='Reducir tamano de fuente'>A−</button>"
            "<button id='btn-zreset' title='Tamano original'>A</button>"
            "<button id='btn-zmas' title='Aumentar tamano de fuente'>A+</button></div>")

_JS_UI = """
(function(){
  const root=document.documentElement;
  let tema=localStorage.getItem('dir-tema')||%s||(matchMedia('(prefers-color-scheme: light)').matches?'claro':'oscuro');
  let z=parseFloat(localStorage.getItem('dir-zoom')||'1');
  function aplTema(){root.dataset.theme=tema;
    document.getElementById('btn-tema').textContent=tema==='claro'?'🌙':'☀️';
    localStorage.setItem('dir-tema',tema);}
  function aplZoom(){document.getElementById('stage').style.zoom=z;localStorage.setItem('dir-zoom',z);}
  document.getElementById('btn-tema').onclick=ev=>{ev.stopPropagation();tema=tema==='claro'?'oscuro':'claro';aplTema();};
  document.getElementById('btn-zmas').onclick=ev=>{ev.stopPropagation();z=Math.min(1.8,+(z+0.1).toFixed(2));aplZoom();};
  document.getElementById('btn-zmenos').onclick=ev=>{ev.stopPropagation();z=Math.max(0.6,+(z-0.1).toFixed(2));aplZoom();};
  document.getElementById('btn-zreset').onclick=ev=>{ev.stopPropagation();z=1;aplZoom();};
  window.addEventListener('message',ev=>{const d=ev.data||{};
    if(d.portal==='tema'){tema=d.tema==='claro'?'claro':'oscuro';aplTema();}});
  aplTema();aplZoom();
})();
"""

def _insights_html(ir):
    ins = ir.get("insights") or []
    if not ins:
        return ""
    cards = []
    for c in ins:
        lis = "".join(f"<li>{html.escape(b)}</li>" for b in c["bullets"])
        cards.append(f'<div class="ins"><b><span class="dot" style="background:{c.get("color", "#38bdf8")}"></span>'
                     f'{html.escape(c["titulo"])}</b><ul>{lis}</ul></div>')
    return '<div class="insights">' + "".join(cards) + "</div>"

def _page(ir, svg, js, css_extra=""):
    js_ui = _JS_UI % json.dumps(ir.get("tema", ""))
    return ("<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'>"
            f"<title>{html.escape(ir['titulo'])}</title><style>" + _CSS_BASE + css_extra +
            "</style></head><body>" + _TOOLBAR + "<div id='stage'>" + svg + _insights_html(ir) +
            "</div><div id='det'></div><script>" + js_ui + js + "</script></body></html>")

def render_flow(ir):
    TIPO = {**TIPO_BASE, **(ir.get("tipos") or {})}
    pos, W, H, rk = _layout(ir)
    s = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="system-ui">']
    s.append('<defs><marker id="arr" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7.5" markerHeight="7.5" orient="auto-start-reverse">'
             '<path d="M0.5,0.5 L9.5,5 L0.5,9.5 z" style="fill:var(--edge)"/></marker>'
             '<marker id="arrb" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7.5" markerHeight="7.5" orient="auto-start-reverse">'
             '<path d="M0.5,0.5 L9.5,5 L0.5,9.5 z" fill="#f472b6"/></marker></defs>')
    s.append(f'<text x="{MX}" y="48" style="fill:var(--txt)" font-size="23" font-weight="700">{html.escape(ir["titulo"])}</text>')
    s.append(f'<text x="{MX}" y="70" style="fill:var(--muted)" font-size="12">derivado de {html.escape(ir.get("fuente", "IR"))} · no editar a mano · clic en un elemento para su detalle</text>')
    s.append(_bandas(ir, pos, W, H))
    backi = 0
    for e in ir["aristas"]:
        x1, y1 = pos[e["desde"]]
        x2, y2 = pos[e["hasta"]]
        if e.get("back") or rk[e["hasta"]] <= rk[e["desde"]]:
            backi += 1
            chan = max(p[1] for p in pos.values()) + NH + 14 + backi * 24
            xg1 = x1 - 22 if x2 <= x1 else x1 + NW + 22
            xg2 = x2 - 22 if x2 <= x1 else x2 + NW + 22
            ys = y1 + NH / 2
            yt = y2 + NH / 2
            r = 9
            s1 = -1 if xg1 < x1 else 1
            s2 = 1 if xg2 < x2 else -1
            d = (f"M{x1},{ys} L{xg1+s1*r},{ys} Q{xg1},{ys} {xg1},{ys+r} "
                 f"L{xg1},{chan-r} Q{xg1},{chan} {xg1+(1 if xg2 > xg1 else -1)*r},{chan} "
                 f"L{xg2-(1 if xg2 > xg1 else -1)*r},{chan} Q{xg2},{chan} {xg2},{chan-r} "
                 f"L{xg2},{yt+r} Q{xg2},{yt} {xg2+s2*r},{yt} L{x2},{yt}")
            w = len(e["label"]) * 6.2 + 14
            s.append(f'<g class="edge" data-f="{e["desde"]}" data-t="{e["hasta"]}">'
                     f'<path d="{d}" fill="none" stroke="#f472b6" stroke-width="1.5" stroke-dasharray="5 4" marker-end="url(#arrb)"/>'
                     f'<rect x="{(x1+x2)/2+NW/2-w/2:.0f}" y="{chan-9}" width="{w:.0f}" height="18" rx="9" style="fill:var(--chip-bg)" stroke="#f472b655"/>'
                     f'<text x="{(x1+x2)/2+NW/2:.0f}" y="{chan+4}" fill="#f9a8d4" font-size="10.5" text-anchor="middle">{html.escape(e["label"])}</text></g>')
            continue
        dx, dy = x2 - x1, y2 - y1
        if abs(dy) <= NH * 0.6 and dx > 0:
            p1, p2, o = (x1 + NW, y1 + NH / 2), (x2, y2 + NH / 2), "h"
        elif abs(dy) > abs(dx):
            p1, p2, o = ((x1 + NW / 2, y1 + NH), (x2 + NW / 2, y2), "v") if dy > 0 else ((x1 + NW / 2, y1), (x2 + NW / 2, y2 + NH), "v")
        else:
            p1, p2, o = (x1 + NW, y1 + NH / 2), (x2, y2 + NH / 2), "h"
        d = _hv(p1, p2) if o == "h" else _vh(p1, p2)
        dash = ' stroke-dasharray="5 4"' if e.get("dash") else ""
        mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        w = len(e["label"]) * 6.2 + 14
        s.append(f'<g class="edge" data-f="{e["desde"]}" data-t="{e["hasta"]}">'
                 f'<path d="{d}" fill="none" style="stroke:var(--edge)" stroke-width="1.5"{dash} marker-end="url(#arr)"/>'
                 f'<rect x="{mx-w/2:.0f}" y="{my-19}" width="{w:.0f}" height="18" rx="9" style="fill:var(--chip-bg);stroke:var(--chip-bd)"/>'
                 f'<text x="{mx:.0f}" y="{my-6}" style="fill:var(--edge-label)" font-size="10.5" text-anchor="middle">{html.escape(e["label"])}</text></g>')
    for n in ir["nodos"]:
        x, y = pos[n["id"]]
        c, icon = TIPO.get(n["tipo"], ("#a78bfa", "?"))
        if n["tipo"] == "decision":
            cxp, cyp = x + NW / 2, y + NH / 2
            tit = _ellipsize(n["titulo"], 12.5, NW - 64)
            sub = _ellipsize(n.get("sub", ""), 10.5, NW - 64)
            s.append(f'<g class="node" data-id="{n["id"]}" data-tipo="{n["tipo"]}" style="cursor:pointer">'
                     f'<polygon class="card" points="{cxp},{y} {x+NW},{cyp} {cxp},{y+NH} {x},{cyp}" fill="{c}14" stroke="{c}" stroke-width="1.5"/>'
                     f'<text x="{cxp}" y="{cyp-3}" style="fill:var(--txt)" font-size="12.5" font-weight="650" text-anchor="middle">{html.escape(tit)}</text>'
                     f'<text x="{cxp}" y="{cyp+15}" style="fill:var(--sub)" font-size="10.5" text-anchor="middle">{html.escape(sub)}</text></g>')
            continue
        outer = f'<rect x="{x-4}" y="{y-4}" width="{NW+8}" height="{NH+8}" rx="14" fill="none" stroke="{c}" stroke-width="1.2"/>' if n["tipo"] == "terminal" else ""
        g = [f'<g class="node" data-id="{n["id"]}" data-tipo="{n["tipo"]}" style="cursor:pointer">'
             f'<rect x="{x+2}" y="{y+3}" width="{NW}" height="{NH}" rx="12" style="fill:var(--shadow)"/>{outer}'
             f'<rect class="card" x="{x}" y="{y}" width="{NW}" height="{NH}" rx="12" fill="{c}14" stroke="{c}" stroke-width="1.4"/>'
             f'<circle cx="{x+22}" cy="{y+24}" r="11" fill="{c}26" stroke="{c}99"/>'
             f'<text x="{x+22}" y="{y+28.5}" fill="{c}" font-size="11" text-anchor="middle">{icon}</text>']
        lineas = _wrap(n["titulo"], 13.5, NW - 54, 2)
        fs_t = 13.5
        if len(lineas) > 1:
            lineas = _wrap(n["titulo"], 12.5, NW - 54, 2)
            fs_t = 12.5
        if len(lineas) == 1:
            g.append(f'<text x="{x+42}" y="{y+29}" style="fill:var(--txt)" font-size="{fs_t + 0.5}" font-weight="650">{html.escape(lineas[0])}</text>'
                     f'<text x="{x+42}" y="{y+50}" style="fill:var(--sub)" font-size="11.5">{html.escape(_ellipsize(n.get("sub", ""), 11.5, NW - 54))}</text>')
        else:
            g.append(f'<text x="{x+42}" y="{y+22}" style="fill:var(--txt)" font-size="12.5" font-weight="650">{html.escape(lineas[0])}</text>'
                     f'<text x="{x+42}" y="{y+37}" style="fill:var(--txt)" font-size="12.5" font-weight="650">{html.escape(lineas[1])}</text>'
                     f'<text x="{x+42}" y="{y+55}" style="fill:var(--sub)" font-size="10.5">{html.escape(_ellipsize(n.get("sub", ""), 10.5, NW - 54))}</text>')
        if n.get("ubicacion"):
            g.append(_badge(x, y, NW, n["ubicacion"], c))
        g.append("</g>")
        s.append("".join(g))
    usados = []
    for n in ir["nodos"]:
        if n["tipo"] not in usados:
            usados.append(n["tipo"])
    lx = W - MX - len(usados) * 96
    for t in usados:
        c, _icon = TIPO[t]
        n_ = sum(1 for n in ir["nodos"] if n["tipo"] == t)
        s.append(f'<g class="chip" data-tipo="{t}" style="cursor:pointer">'
                 f'<rect x="{lx-6}" y="58" width="15" height="15" rx="5" fill="{c}26" stroke="{c}"/>'
                 f'<text x="{lx+15}" y="70" style="fill:var(--sub)" font-size="11.5">{t} {n_}</text></g>')
        lx += 96
    s.append("</svg>")
    datos = {n["id"]: {k: n.get(k, "") for k in ("titulo", "sub", "tipo", "grupo", "detalle", "ubicacion")} for n in ir["nodos"]}
    rels = {}
    for e in ir["aristas"]:
        rels.setdefault(e["desde"], []).append(("→", e["hasta"], e["label"]))
        rels.setdefault(e["hasta"], []).append(("←", e["desde"], e["label"]))
    js = _JS_FLOW % (json.dumps(datos, ensure_ascii=False), json.dumps(rels, ensure_ascii=False),
                     json.dumps({k: v[0] for k, v in TIPO.items()}))
    return _page(ir, "".join(s), js)

# ════════════════════════ MOTOR DE SECUENCIA ════════════════════════

_JS_SEQ = """
const DATOS=%s, COLORES=%s;
let lens=[];
function aplicar(focus){
  const act=new Set(lens);
  document.querySelectorAll('.node,.life,.act').forEach(g=>{
    const id=g.dataset.id, t=g.dataset.tipo; let dim=false;
    if(act.size&&t) dim=!act.has(t);
    if(focus) dim=id!==focus;
    g.style.opacity=dim?.12:1;
    const card=g.querySelector('.card'); if(card) card.setAttribute('stroke-width', id===focus?2.6:1.4);
  });
  document.querySelectorAll('.msg').forEach(g=>{
    let dim=false;
    if(focus) dim=!(g.dataset.f===focus||g.dataset.t===focus);
    if(act.size&&!focus){const a=document.querySelector(`.node[data-id="${g.dataset.f}"]`).dataset.tipo,
      b=document.querySelector(`.node[data-id="${g.dataset.t}"]`).dataset.tipo; dim=!(act.has(a)&&act.has(b));}
    g.style.opacity=dim?.08:1;
  });
  document.querySelectorAll('.chip').forEach(c=>{
    c.style.opacity=(act.size&&!act.has(c.dataset.tipo))?.4:1;
    c.querySelector('rect').setAttribute('stroke-width', act.has(c.dataset.tipo)?2.4:1);
  });
}
function panel(id){
  const p=document.getElementById('det'), d=DATOS[id];
  if(!id){p.style.display='none';return;}
  const rel=[...document.querySelectorAll(`.msg[data-f="${id}"],.msg[data-t="${id}"]`)]
    .map(g=>{const i=[...document.querySelectorAll('.msg')].indexOf(g)+1;
      const o=g.dataset.f===id?g.dataset.t:g.dataset.f;
      return `<li><b>#${i}</b> ${g.dataset.f===id?'→':'←'} <b>${DATOS[o].titulo}</b></li>`;}).join('');
  p.innerHTML=`<div style="display:flex;justify-content:space-between;align-items:center">
    <b style="color:${COLORES[d.tipo]}">${d.titulo}</b>
    <span style="cursor:pointer;color:var(--muted)" onclick="foco(null)">✕</span></div>
    <div style="color:var(--sub);font-size:12px;margin:.2rem 0">${d.sub} · tipo ${d.tipo}${d.ubicacion?' · 📍 '+d.ubicacion:''}</div>
    <div style="font-size:12.5px;margin:.4rem 0">${d.detalle||''}</div>
    <ul style="margin:.3rem 0 0;padding-left:1.1rem;font-size:12px;color:var(--fg)">${rel}</ul>`;
  p.style.display='block';
}
function foco(id){ window._f=id; aplicar(id); panel(id);
  history.replaceState(null,'',id?'#focus='+id:location.pathname); }
document.querySelectorAll('.node').forEach(g=>g.addEventListener('click',ev=>{
  ev.stopPropagation(); foco(window._f===g.dataset.id?null:g.dataset.id);}));
document.querySelectorAll('.chip').forEach(c=>c.addEventListener('click',()=>{
  const t=c.dataset.tipo, i=lens.indexOf(t);
  if(i>=0) lens.splice(i,1); else { lens.push(t); if(lens.length>2) lens.shift(); }
  aplicar(window._f);
  history.replaceState(null,'',lens.length?'#lens='+lens.join('~'):location.pathname);}));
document.body.addEventListener('click',()=>foco(null));
const h=location.hash;
if(h.startsWith('#focus=')) foco(h.slice(7));
if(h.startsWith('#lens=')){ lens=h.slice(6).split('~'); aplicar(null); }
"""

PW_S, PH_S, GX_S, TOP_S, STEP_S, MX_S, HEAD_S = 200, 56, 130, 150, 64, 60, 64

def render_sequence(ir):
    TIPO = {**TIPO_BASE, **(ir.get("tipos") or {})}
    ids = [p["id"] for p in ir["participantes"]]
    cx = {pid: MX_S + i * (PW_S + GX_S) + PW_S / 2 for i, pid in enumerate(ids)}
    W = MX_S * 2 + len(ids) * (PW_S + GX_S) - GX_S
    H = TOP_S + HEAD_S + len(ir["mensajes"]) * STEP_S + 80
    s = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="system-ui">']
    s.append('<defs><marker id="a1" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7.5" markerHeight="7.5" orient="auto">'
             '<path d="M0.5,0.5 L9.5,5 L0.5,9.5 z" style="fill:var(--seq-msg)"/></marker>'
             '<marker id="a2" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7.5" markerHeight="7.5" orient="auto">'
             '<path d="M0.5,0.5 L9.5,5 L0.5,9.5 z" style="fill:var(--seq-ret)"/></marker></defs>')
    s.append(f'<text x="{MX_S}" y="48" style="fill:var(--txt)" font-size="23" font-weight="700">{html.escape(ir["titulo"])}</text>')
    s.append(f'<text x="{MX_S}" y="70" style="fill:var(--muted)" font-size="12">derivado de {html.escape(ir.get("fuente", "IR"))} · no editar a mano · clic en un participante para su detalle</text>')
    for p in ir["participantes"]:
        c, icon = TIPO.get(p["tipo"], ("#a78bfa", "?"))
        x = cx[p["id"]] - PW_S / 2
        tit = _ellipsize(p["titulo"], 13, PW_S - 50)
        sub = _ellipsize(p.get("sub", ""), 10.5, PW_S - 50)
        g = [f'<g class="node" data-id="{p["id"]}" data-tipo="{p["tipo"]}" style="cursor:pointer">'
             f'<rect x="{x+2}" y="{TOP_S-57}" width="{PW_S}" height="{PH_S}" rx="12" style="fill:var(--shadow)"/>'
             f'<rect class="card" x="{x}" y="{TOP_S-60}" width="{PW_S}" height="{PH_S}" rx="12" fill="{c}14" stroke="{c}" stroke-width="1.4"/>'
             f'<circle cx="{x+21}" cy="{TOP_S-38}" r="10" fill="{c}26" stroke="{c}99"/>'
             f'<text x="{x+21}" y="{TOP_S-34}" fill="{c}" font-size="10.5" text-anchor="middle">{icon}</text>'
             f'<text x="{x+40}" y="{TOP_S-34}" style="fill:var(--txt)" font-size="13" font-weight="650">{html.escape(tit)}</text>'
             f'<text x="{x+40}" y="{TOP_S-17}" style="fill:var(--sub)" font-size="10.5">{html.escape(sub)}</text>']
        if p.get("ubicacion"):
            g.append(_badge(x, TOP_S - 60, PW_S, p["ubicacion"], c))
        g.append("</g>")
        s.append("".join(g))
        s.append(f'<line class="life" data-id="{p["id"]}" x1="{cx[p["id"]]}" y1="{TOP_S-4}" x2="{cx[p["id"]]}" y2="{H-46}" style="stroke:var(--life)" stroke-width="1.2" stroke-dasharray="4 5"/>')
    activo = {}
    for i, m in enumerate(ir["mensajes"]):
        y = TOP_S + HEAD_S + i * STEP_S
        x1, x2 = cx[m["desde"]], cx[m["hasta"]]
        ret = m.get("retorno")
        if not ret and m["hasta"] not in activo:
            activo[m["hasta"]] = y
        color = "var(--seq-ret)" if ret else "var(--seq-msg)"
        dash = ' stroke-dasharray="5 4"' if ret else ""
        d_ = 1 if x2 > x1 else -1
        s.append(f'<g class="msg" data-f="{m["desde"]}" data-t="{m["hasta"]}">'
                 f'<line x1="{x1 + d_*9}" y1="{y}" x2="{x2 - d_*9}" y2="{y}" style="stroke:{color}" stroke-width="1.6"{dash} marker-end="url(#{"a2" if ret else "a1"})"/>')
        mx = (x1 + x2) / 2
        w = len(m["label"]) * 6.4 + 30
        s.append(f'<rect x="{mx-w/2:.0f}" y="{y-26}" width="{w:.0f}" height="19" rx="9.5" style="fill:var(--chip-bg);stroke:var(--chip-bd)"/>'
                 f'<circle cx="{mx-w/2+12:.0f}" cy="{y-16.5}" r="7.5" fill="#38bdf822" stroke="#38bdf8"/>'
                 f'<text x="{mx-w/2+12:.0f}" y="{y-13}" fill="#38bdf8" font-size="9.5" font-weight="700" text-anchor="middle">{i+1}</text>'
                 f'<text x="{mx-w/2+25:.0f}" y="{y-12.5}" style="fill:var(--edge-label)" font-size="10.5">{html.escape(m["label"].strip())}</text></g>')
    for pid, y0 in activo.items():
        yend = max(TOP_S + HEAD_S + i * STEP_S for i, m in enumerate(ir["mensajes"]) if m["desde"] == pid or m["hasta"] == pid)
        s.append(f'<rect class="act" data-id="{pid}" x="{cx[pid]-5}" y="{y0}" width="10" height="{yend-y0}" rx="3" style="fill:var(--act-bg);stroke:var(--act-bd)"/>')
    usados = sorted({p["tipo"] for p in ir["participantes"]})
    lx = MX_S
    for t in usados:
        c, _icon = TIPO[t]
        n_ = sum(1 for p in ir["participantes"] if p["tipo"] == t)
        s.append(f'<g class="chip" data-tipo="{t}" style="cursor:pointer">'
                 f'<rect x="{lx-6}" y="{H-34}" width="15" height="15" rx="5" fill="{c}26" stroke="{c}"/>'
                 f'<text x="{lx+15}" y="{H-22}" style="fill:var(--sub)" font-size="11.5">{t} {n_}</text></g>')
        lx += 96
    s.append("</svg>")
    datos = {p["id"]: {k: p.get(k, "") for k in ("titulo", "sub", "tipo", "detalle", "ubicacion")} for p in ir["participantes"]}
    js = _JS_SEQ % (json.dumps(datos, ensure_ascii=False),
                    json.dumps({k: v[0] for k, v in TIPO.items()}))
    return _page(ir, "".join(s), js)

# ════════════════════════ DIFF ════════════════════════

def _elements(ir):
    """Elementos comparables: {(clase, id): dict-normalizado}."""
    out = {}
    for n in ir.get("nodos", []) + ir.get("participantes", []):
        out[("nodo", n["id"])] = {k: n.get(k) for k in ("titulo", "sub", "tipo", "grupo", "detalle", "ubicacion")}
    for e in ir.get("aristas", []):
        out[("arista", f'{e["desde"]}→{e["hasta"]}:{e.get("label")}')] = {"dash": bool(e.get("dash")), "back": bool(e.get("back"))}
    for m in ir.get("mensajes", []):
        out[("mensaje", f'{m["desde"]}→{m["hasta"]}:{m.get("label")}')] = {"retorno": bool(m.get("retorno"))}
    for c in ir.get("insights", []):
        out[("insight", c["titulo"])] = {"bullets": tuple(c.get("bullets", []))}
    return out

def diff_ir(old, new):
    a, b = _elements(old), _elements(new)
    added = sorted(k for k in b if k not in a)
    removed = sorted(k for k in a if k not in b)
    changed = sorted(k for k in a if k in b and a[k] != b[k])
    return added, removed, changed

# ════════════════════════ CLI ════════════════════════

def render(ir):
    return render_sequence(ir) if ir.get("kind") == "sequence" else render_flow(ir)

def _portal_register(ir_path, out_path, ir):
    """Auto-registro en el portal del proyecto (v2.20), best-effort.

    Localiza spec/ subiendo desde --out (los diagramas viven en
    spec/diagrams/), importa portal_lib del arnés (sdlc-orchestrator/scripts)
    y registra la página para el menú lateral y el buscador global. Nunca
    bloquea el render: cualquier fallo se ignora (el HTML ya quedó escrito).
    """
    try:
        import re as _re
        parts = os.path.normpath(os.path.abspath(out_path)).split(os.sep)
        if "spec" not in parts:
            return
        spec_dir = os.sep.join(parts[:parts.index("spec") + 1]) or os.sep
        scripts = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                               "..", "..", "sdlc-orchestrator", "scripts"))
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        import portal_lib
        titulo = ir.get("titulo", os.path.basename(out_path))
        tipo = ir.get("kind", "flow")
        texto = " ".join(
            [titulo, tipo]
            + [d for n in ir.get("nodos", []) for d in (n.get("titulo", ""), n.get("detalle", ""))]
            + [b for c in ir.get("insights", []) for b in c.get("bullets", [])])
        cat = ("operacion" if _re.search(r"pipeline|ci.?cd|deploy|workflow", titulo, _re.I)
               else "arquitectura")
        pid = portal_lib.register(spec_dir, origen="diagram_ir", kind="diagrama",
                                  ruta=os.path.abspath(out_path), titulo=titulo,
                                  categoria=cat, grupo="diagramas",
                                  tags=[tipo, "diagrama"], texto=texto)
        portal_lib.rebuild_index(spec_dir)
        print(f"portal: registrado como '{pid}'")
    except Exception:
        pass


def main(argv=None):
    ap = argparse.ArgumentParser(description="Diagramas interactivos desde IR JSON (ADR-003)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("render", "validate", "check"):
        p = sub.add_parser(name)
        p.add_argument("--ir", required=True)
        if name != "validate":
            p.add_argument("--out", required=True)
    p = sub.add_parser("diff")
    p.add_argument("--old", required=True)
    p.add_argument("--new", required=True)
    args = ap.parse_args(argv)

    if args.cmd == "diff":
        old, new = load_ir(args.old), load_ir(args.new)
        added, removed, changed = diff_ir(old, new)
        print(f"## Diff de diagrama: {old.get('titulo', args.old)}")
        for label, items in (("Agregados", added), ("Eliminados", removed), ("Modificados", changed)):
            print(f"\n### {label} ({len(items)})")
            for clase, ident in items:
                print(f"- [{clase}] {ident}")
        return 0 if not (added or removed or changed) else 2

    ir = load_ir(args.ir)
    errs = validate_ir(ir)
    if args.cmd == "validate":
        if errs:
            print("IR INVALIDO:")
            for e in errs:
                print(f"- {e}")
            return 1
        print(f"IR valido: {ir['titulo']} (kind={ir['kind']})")
        return 0
    if errs:
        print("IR invalido, corregir antes de renderizar:", file=sys.stderr)
        for e in errs:
            print(f"- {e}", file=sys.stderr)
        return 1
    html_out = render(ir)
    if args.cmd == "render":
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(html_out)
        print(f"OK {args.out} ({len(html_out)} bytes)")
        _portal_register(args.ir, args.out, ir)
        return 0
    # check: drift
    try:
        with open(args.out, encoding="utf-8") as f:
            actual = f.read()
    except FileNotFoundError:
        print(f"DRIFT: {args.out} no existe; regenerar con 'render'", file=sys.stderr)
        return 1
    if actual != html_out:
        print(f"DRIFT: {args.out} difiere del IR; regenerar con 'render'", file=sys.stderr)
        return 1
    print(f"OK sin drift: {args.out}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
