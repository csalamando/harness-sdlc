#!/usr/bin/env python3
"""harness_graph.py — genera el grafo interactivo del arnés (docs/graph.html)
y el dashboard vivo de un proyecto (spec/dashboard.html, ADR-002).

El grafo es un artefacto DERIVADO: los nodos (macro-fases), las skills por nodo,
sus gates y sus flujos in/out salen del manifiesto (frontmatter harness-*) y del
grafo de dependencias de spec_diff_impact.py. Nunca se edita el HTML a mano.

Uso:
  python3 harness_graph.py --write    # regenera docs/graph.html
  python3 harness_graph.py --check    # exit 1 si el HTML versionado tiene drift
  python3 harness_graph.py --proyecto <dir> [--json] [--check]
                                      # dashboard vivo del proyecto (ADR-002):
                                      # UN archivo spec/dashboard.html, "el ahora"

Los bordes de feedback (sprints, bug-red, hotfix, delta-spec) son la única parte
declarativa: son decisiones de diseño del pipeline, no derivables de la spec.
"""
import argparse, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from manifest_check import derive, SKILLS_DIR
from spec_diff_impact import DEPENDS_ON

OUT_HTML = os.path.normpath(os.path.join(HERE, "..", "..", "..", "docs", "graph.html"))

# Macro-fases del grafo (presentación) -> fases finas del manifiesto
MACRO = [
    {"id": 1, "title": "Setup & Visión",  "phases": ["-1", "0"], "x": 9,
     "gate": "GATE 0", "desc": "Visión, propuesta con opciones, pricing cloud y caso de negocio. Sin GATE 0 aprobado no hay pipeline."},
    {"id": 2, "title": "Discovery",       "phases": ["1"], "x": 26,
     "gate": None, "desc": "Historias Gherkin, reglas de negocio, catálogo de roles gobernado y PDD (AS-IS) si automatiza procesos."},
    {"id": 3, "title": "Arquitectura",    "phases": ["2", "3"], "x": 44,
     "gate": "GATE 1", "desc": "Contratos duros (OpenAPI), ADRs de 8 pasos firmados, threat modeling, prototipo de pantallas. GATE 1 habilita el paralelismo real."},
    {"id": 4, "title": "Strict TDD",      "phases": ["4"], "x": 63, "loop": "sprints",
     "gate": None, "desc": "Backend y frontend en paralelo consumiendo mocks del contrato. Tests antes que código, siempre."},
    {"id": 5, "title": "QA & Seguridad",  "phases": ["5"], "x": 80,
     "gate": "GATE 2 / 2.5", "desc": "E2E desde Gherkin, regresión, carga y DAST. Un bug vuelve al dev con el test exacto que lo reproduce."},
    {"id": 6, "title": "Release & Operación", "phases": ["6", "7"], "x": 94, "loop": "continuo",
     "gate": "GATE 3", "desc": "Deploy con rollback probado, diagramas derivados con recibo, SLOs, postmortems y medición de impacto que realimenta el backlog."},
]

# Bordes de feedback (diseño del pipeline, no derivables): (desde_id, hasta_id, etiqueta)
LOOPS = [
    (4, 4, "sprints (TDD red→green)"),
    (5, 4, "TDD QA Bug (Red)"),
    (6, 4, "Hotfix Prod"),
    (3, 4, "Delta-Spec Replan (spec_diff)"),
    (6, 1, "impact-report → backlog"),
]

ROLE_NAMES = {  # nombre corto de presentación por skill
    "sdlc-backend-dev-tdd": "Backend TDD", "sdlc-frontend-dev-tdd": "Frontend TDD",
    "sdlc-technical-writer": "Technical Writer", "sdlc-qa-automation": "QA Automation",
    "sdlc-security-engineer": "Security Engineer", "sdlc-software-architect": "Software Architect",
    "sdlc-enterprise-architect": "Enterprise Architect", "sdlc-decision-engine": "Decision Engine",
    "sdlc-ux-designer": "UX Designer", "sdlc-data-engineer": "Data Engineer",
    "sdlc-business-analyst": "Business Analyst", "sdlc-product-owner": "Product Owner",
    "sdlc-solution-architect": "Solution Architect", "sdlc-cloud-pricing": "Cloud Pricing",
    "sdlc-devops-engineer": "DevOps Engineer", "sdlc-cloud-engineer": "Cloud Engineer",
    "sdlc-sre": "SRE", "sdlc-product-analyst": "Product Analyst",
    "sdlc-orchestrator": "Orquestador", "sdlc-memory": "Memoria", "sdlc-diagrams": "Diagramas",
}


def base(p):
    return os.path.basename(p.rstrip("/")) or p


def build_data(skills):
    """Deriva el modelo del grafo desde el manifiesto + grafo de dependencias."""
    nodes = []
    for m in MACRO:
        members = [s for s in skills if any(p in s["phases"] for p in m["phases"])]
        skill_models = []
        for s in members:
            outs = [base(a) for a in s["owns"]]
            ins = sorted({base(d) for a in s["owns"] for d in DEPENDS_ON.get(base(a), [])})
            skill_models.append({
                "id": s["name"], "name": ROLE_NAMES.get(s["name"], s["role"]),
                "in": ins, "out": outs, "gates": s["gates"],
                "conditional": s["conditional"],
            })
        nodes.append({**m, "skills": skill_models})
    transversal = [s for s in skills if "transversal" in s["phases"]]
    return nodes, transversal


def render_html(nodes, transversal, total_skills):
    import json
    data = json.dumps({"nodes": nodes, "loops": LOOPS,
                       "transversal": [{"id": s["name"], "name": ROLE_NAMES.get(s["name"], s["role"]),
                                        "gates": s["gates"]} for s in transversal]},
                      ensure_ascii=False)
    return TEMPLATE.replace("/*__DATA__*/null", data).replace("__TOTAL__", str(total_skills))


TEMPLATE = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Arnés SDLC — Grafo del pipeline (generado)</title>
<style>
  :root { color-scheme: dark; }
  body { background:#0b1220; color:#e2e8f0; font-family:system-ui,sans-serif; margin:0; padding:2rem; }
  h1 { font-size:1.3rem; } .sub { color:#94a3b8; font-size:.85rem; margin-bottom:1.5rem; }
  .canvas { position:relative; height:540px; background:#0f172a; border:1px solid #1e293b; border-radius:12px; overflow:hidden; }
  svg.edges { position:absolute; inset:0; width:100%; height:100%; }
  .node { position:absolute; transform:translate(-50%,-50%); cursor:pointer; text-align:center; width:150px; }
  .node .dot { width:56px; height:56px; border-radius:50%; margin:0 auto; background:#1e293b; border:2px solid #3b82f6;
               display:flex; align-items:center; justify-content:center; font-weight:700; font-size:1.15rem; transition:.15s; }
  .node:hover .dot, .node.active .dot { border-color:#f59e0b; transform:scale(1.15); }
  .node .lbl { font-size:.85rem; margin-top:.45rem; color:#cbd5e1; font-weight:600; }
  .node .cnt { font-size:.7rem; color:#64748b; }
  .node .gate { position:absolute; top:-18px; left:50%; transform:translateX(-50%); font-size:.62rem;
                background:#7c2d12; color:#fdba74; border:1px solid #ea580c; border-radius:4px; padding:1px 6px; white-space:nowrap; }
  .loop-tag { font-size:.78rem; fill:#fbbf24; font-weight:600; }
  #panel { margin-top:1.5rem; background:#0f172a; border:1px solid #1e293b; border-radius:12px; padding:1.2rem; display:none; }
  #panel h2 { margin:.2rem 0; font-size:1.1rem; } #panel .desc { color:#94a3b8; font-size:.85rem; max-width:60ch; }
  .cards { display:grid; grid-template-columns:repeat(auto-fill,minmax(230px,1fr)); gap:.7rem; margin-top:1rem; }
  .card { background:#111c33; border:1px solid #1e293b; border-radius:8px; padding:.7rem; font-size:.75rem; }
  .card b { font-size:.85rem; } .card code { color:#818cf8; font-size:.65rem; }
  .badge { display:inline-block; font-size:.6rem; border-radius:4px; padding:1px 5px; margin:1px; }
  .in { background:#0f172a; color:#94a3b8; border:1px solid #334155; }
  .out { background:#052e1b; color:#6ee7b7; border:1px solid #065f46; }
  .gate-b { background:#451a03; color:#fdba74; border:1px solid #9a3412; }
  .cond { color:#fbbf24; font-size:.62rem; }
  .trans { margin-top:1.5rem; font-size:.8rem; color:#94a3b8; }
  .trans b { color:#cbd5e1; }
  footer { margin-top:2rem; font-size:.7rem; color:#475569; }
</style></head><body>
<h1>🧭 Arnés SDLC — Grafo del pipeline</h1>
<div class="sub">__TOTAL__ skills · generado desde el manifiesto (harness-manifest.yaml) — clic en una fase para ver sus skills y flujos</div>
<div class="canvas" id="canvas"><svg class="edges" id="edges"></svg></div>
<div id="panel"></div>
<div class="trans" id="trans"></div>
<footer>Artefacto derivado — regenerar con <code>manifest_check/harness_graph.py --write</code>. No editar a mano (el drift lo detecta el self-test y el CI).</footer>
<script>
const DATA = /*__DATA__*/null;
const canvas = document.getElementById('canvas'), svg = document.getElementById('edges');
const panel = document.getElementById('panel');
function edges() {
  const W = canvas.clientWidth, H = canvas.clientHeight, y = H/2;
  let s = '';
  const X = id => DATA.nodes.find(n=>n.id===id).x/100*W;
  for (let i=0;i<DATA.nodes.length-1;i++)
    s += `<line x1="${X(DATA.nodes[i].id)}" y1="${y}" x2="${X(DATA.nodes[i+1].id)}" y2="${y}" stroke="#334155" stroke-width="2" marker-end="url(#a)"/>`;
  for (const [f,t,lbl] of DATA.loops) {
    if (f===t) { const x=X(f); s += `<path d="M ${x-24} ${y-28} C ${x-60} ${y-110}, ${x+60} ${y-110}, ${x+24} ${y-28}" fill="none" stroke="#f59e0b" stroke-dasharray="4 3" marker-end="url(#loop-arrow)"/>
      <text class="loop-tag" x="${x}" y="${y-100}" text-anchor="middle">${lbl}</text>`; continue; }
    const x1=X(f), x2=X(t), span=Math.abs(f-t);
    const r=34;                                      // radio del nodo: el arco termina en su borde, no tapado
    const ex = x2 + (f>t ? r : -r);
    const lift = 80 + 45*span;                       // arcos largos van más afuera: no se pisan
    const my = f>t ? y+lift : y-lift;
    const apex = (y+my)/2;                           // punto medio real de la curva Bézier
    s += `<path d="M ${x1} ${y} Q ${(x1+x2)/2} ${my}, ${ex} ${y}" fill="none" stroke="#f59e0b" stroke-dasharray="4 3" marker-end="url(#loop-arrow)"/>
          <text class="loop-tag" x="${(x1+x2)/2}" y="${apex + (f>t?18:-8)}" text-anchor="middle">↺ ${lbl}</text>`;
  }
  svg.innerHTML = `<defs>
    <marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#334155"/></marker>
    <marker id="loop-arrow" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#f59e0b"/></marker>
  </defs>` + s;
}
function nodes() {
  document.querySelectorAll('.node').forEach(e=>e.remove());
  for (const n of DATA.nodes) {
    const d = document.createElement('div');
    d.className = 'node'; d.style.left = n.x+'%'; d.style.top = '50%';
    d.innerHTML = `${n.gate?`<span class="gate">⛔ ${n.gate}</span>`:''}
      <div class="dot">${n.id}</div>
      <div class="lbl">${n.title}${n.loop?` <span style="color:#f59e0b">↺${n.loop}</span>`:''}</div>
      <div class="cnt">${n.skills.length} skills</div>`;
    d.onclick = () => show(n, d);
    canvas.appendChild(d);
  }
}
function show(n, el) {
  document.querySelectorAll('.node').forEach(e=>e.classList.remove('active'));
  el.classList.add('active');
  panel.style.display = 'block';
  panel.innerHTML = `<h2>Fase ${n.phase||''} · ${n.title}</h2><div class="desc">${n.desc}</div>
    <div class="cards">` + n.skills.map(s=>`<div class="card"><b>${s.name}</b> <code>${s.id}</code>
      ${s.conditional?`<div class="cond">◆ condicional: ${s.conditional}</div>`:''}
      ${s.gates.length?`<div>${s.gates.map(g=>`<span class="badge gate-b">gate: ${g}</span>`).join('')}</div>`:''}
      <div style="margin-top:4px">${s.in.map(i=>`<span class="badge in">IN ${i}</span>`).join('')}${s.out.map(o=>`<span class="badge out">OUT ${o}</span>`).join('')}</div>
    </div>`).join('') + '</div>';
}
document.getElementById('trans').innerHTML =
  '⚙️ <b>Transversales (todas las fases):</b> ' + DATA.transversal.map(s=>s.name).join(' · ');
edges(); nodes(); addEventListener('resize', edges);
</script></body></html>
"""


# ══════════════════════════════════════════════════════════════════════════════
# MODO PROYECTO (ADR-002): dashboard vivo — UN archivo spec/dashboard.html.
# Todo deriva de fuentes gobernadas (recibos, sprint reviews, memorias).
# Cero narración manual; el HTML es visualización, la evidencia son los recibos.
# ══════════════════════════════════════════════════════════════════════════════

# Gate del recibo -> macro-fase que cierra
GATE_MACRO = {"GATE 0": 1, "GATE 1": 3, "GATE 2": 5, "GATE 2.5": 5, "GATE 3": 6}
# Invalidación de un gate -> loop de feedback que se activa
LOOP_BY_GATE = {"GATE 1": (3, 4), "GATE 2": (5, 4), "GATE 2.5": (5, 4), "GATE 3": (6, 4)}
# Gate que falta -> fase de trabajo actual (GATE 2 se trabaja en fase 4, etc.)
WORK_PHASE = {"GATE 0": 1, "GATE 1": 3, "GATE 2": 4, "GATE 2.5": 4, "GATE 3": 5}


def _span_minutes(s):
    """'3 days, 2:00:00' o '0:30:00' -> minutos."""
    import re as _re
    days = 0
    m = _re.match(r"(\d+) days?, ", s)
    if m:
        days = int(m.group(1)); s = s[m.end():]
    try:
        h, mi, _ = s.split(":")
        return days * 1440 + int(h) * 60 + int(mi)
    except ValueError:
        return None


def _fmt_span(mins):
    if mins is None:
        return "-"
    if mins >= 1440:
        return f"{mins/1440:.1f} d"
    if mins >= 60:
        return f"{mins/60:.1f} h"
    return f"{mins} min"


def parse_reviews(spec_dir):
    """Serie histórica desde los snapshots sprint-review-NN.md (fuente canónica)."""
    import glob, re
    out = []
    for p in sorted(glob.glob(os.path.join(spec_dir, "reports", "sprint-review-*.md"))):
        m = re.search(r"sprint-review-(\d+)", p)
        if not m:
            continue
        try:
            text = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue

        def kpi(k):
            r = re.search(r"<!--\s*" + re.escape(k) + r":\s*([\d.,%]+)\s*-->", text)
            return r.group(1).rstrip("%").replace(",", "") if r else None

        r = re.search(r"Trabajo rehecho \(recibos invalidados/revocados\): \*\*(\d+)\*\*", text)
        lead = {}
        for row in re.finditer(r"^\| (GATE [\d.]+) \| [^|]+ \| [^|]+ \| \d+ \| ([^|]+) \|$",
                               text, re.M):
            mins = _span_minutes(row.group(2).strip())
            if mins is not None:
                lead[row.group(1)] = mins
        out.append({"sprint": int(m.group(1)),
                    "artefactos": int(kpi("Artefactos aprobados") or 0),
                    "gates_1er": int(float(kpi("Gates al primer intento") or 0)),
                    "rehechos": int(r.group(1)) if r else 0,
                    "lead": lead})
    return out


def recent_learnings(spec_dir, limit=4):
    """Títulos de las memorias learning más recientes (degrada a [] si no hay)."""
    d = os.path.join(spec_dir, "memory", "entries")
    if not os.path.isdir(d):
        return []
    found = []
    for f in os.listdir(d):
        if not f.endswith(".md"):
            continue
        p = os.path.join(d, f)
        try:
            head = open(p, encoding="utf-8", errors="replace").read(600)
        except OSError:
            continue
        if "type: learning" not in head:
            continue
        title = None
        for line in head.splitlines():
            if line.startswith("# "):
                title = line[2:].strip(); break
        found.append((os.path.getmtime(p), title or f[:-3]))
    return [t for _, t in sorted(found, reverse=True)[:limit]]


def derive_project(project_dir):
    """Modelo del dashboard: todo derivado de receipts/ + spec/ + sprint reviews."""
    import skill_metrics
    try:
        from traceability_matrix import collect_ids
    except ImportError:
        collect_ids = None
    spec_dir = os.path.join(project_dir, "spec")
    recs = skill_metrics.load_receipts(spec_dir)
    vigentes = [r for r in recs if r.get("estado") == "vigente"]
    rehechos = [r for r in recs if r.get("estado") in ("invalidado", "revocado")]

    # Estado de cada macro-fase según los recibos de su gate
    gate_status = {}   # macro -> {"estado": ok|warn|none, "gate": str, "vigentes": n, "rehechos": n}
    for m in MACRO:
        gates = [g for g, mac in GATE_MACRO.items() if mac == m["id"]]
        if not gates:
            continue
        rv = [r for r in vigentes if r.get("gate") in gates]
        rr = [r for r in rehechos if r.get("gate") in gates]
        estado = "ok" if rv else ("warn" if rr else "none")
        gate_status[m["id"]] = {"estado": estado, "gate": " / ".join(gates),
                                "vigentes": len(rv), "rehechos": len(rr)}

    # Fase actual: la fase de trabajo del primer gate no cubierto por recibos vigentes
    current = 6
    for g in ["GATE 0", "GATE 1", "GATE 2", "GATE 2.5", "GATE 3"]:
        mac = GATE_MACRO[g]
        if gate_status.get(mac, {}).get("estado") != "ok":
            current = WORK_PHASE[g]
            break

    # Loops activos: invalidaciones por gate + sprints + impact-report
    active = {}
    for r in rehechos:
        loop = LOOP_BY_GATE.get(r.get("gate"))
        if loop:
            active[loop] = active.get(loop, 0) + 1
    reviews = parse_reviews(spec_dir)
    if reviews:
        active[(4, 4)] = 0  # el loop de sprints corre desde el sprint 1
    if os.path.isfile(os.path.join(spec_dir, "impact-report.md")):
        active[(6, 1)] = 0

    # HU: historias con test y código (degrada a None si no hay estructura)
    hu = None
    if collect_ids:
        root = os.path.abspath(project_dir)
        us = os.path.join(spec_dir, "user-stories.md")
        stories = collect_ids(us if os.path.isfile(us) else spec_dir, [".md"])
        tests = collect_ids(os.path.join(root, "tests"), [".py", ".ts", ".tsx", ".js", ".java", ".cs", ".feature"])
        code = collect_ids(os.path.join(root, "src"), [".py", ".ts", ".tsx", ".js", ".java", ".cs"])
        if stories:
            hu = {"total": len(stories), "cerradas": len(stories & tests & code)}

    nombre = os.path.basename(os.path.abspath(project_dir))
    return {
        "proyecto": nombre,
        "generado": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "gate_status": gate_status, "fase_actual": current,
        "loops_activos": {f"{f}->{t}": n for (f, t), n in sorted(active.items())},
        "contadores": {
            "sprints": len(reviews),
            "releases": sum(1 for r in vigentes if r.get("gate") == "GATE 3"),
            "hu": hu,
            "recibos_vigentes": len(vigentes), "recibos_rehechos": len(rehechos),
            "gates_1er": reviews[-1]["gates_1er"] if reviews else None,
        },
        "tendencias": reviews,
        "aprendizajes": recent_learnings(spec_dir),
    }


# ── Render del dashboard (self-contained, sin JS ni dependencias) ─────────────

DASH_CSS = """
  :root { color-scheme: dark; }
  body { background:#0b1220; color:#e2e8f0; font-family:system-ui,sans-serif; margin:0; padding:2rem; max-width:1200px; margin-inline:auto; }
  h1 { font-size:1.3rem; margin-bottom:.2rem; }
  .sub { color:#94a3b8; font-size:.85rem; margin-bottom:1.5rem; }
  .panel { background:#0f172a; border:1px solid #1e293b; border-radius:12px; padding:1.2rem; margin-bottom:1.5rem; }
  .panel h2 { font-size:1rem; margin:0 0 1rem; color:#cbd5e1; }
  .legend { display:flex; gap:1.2rem; font-size:.75rem; color:#94a3b8; margin-top:.6rem; flex-wrap:wrap; }
  .legend span::before { content:"\\25CF"; margin-right:.35rem; }
  .lg-ok::before { color:#22c55e; } .lg-warn::before { color:#f59e0b; } .lg-none::before { color:#475569; }
  .lg-cur::before { color:#3b82f6; }
  .kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:.8rem; }
  .kpi { background:#111c33; border:1px solid #1e293b; border-radius:10px; padding:.9rem; }
  .kpi .v { font-size:1.7rem; font-weight:700; }
  .kpi .k { font-size:.72rem; color:#94a3b8; margin-top:.2rem; }
  table { border-collapse:collapse; width:100%; font-size:.8rem; }
  th, td { text-align:left; padding:.45rem .6rem; border-bottom:1px solid #1e293b; }
  th { color:#94a3b8; font-weight:600; font-size:.72rem; text-transform:uppercase; letter-spacing:.04em; }
  .bar { height:8px; border-radius:4px; background:#3b82f6; display:inline-block; vertical-align:middle; margin-right:.4rem; }
  .bar.bad { background:#f59e0b; }
  .learn { font-size:.82rem; color:#cbd5e1; margin:.4rem 0; }
  .warn-line { font-size:.75rem; color:#fbbf24; margin-top:.6rem; }
  .empty { color:#475569; font-size:.82rem; font-style:italic; }
  footer { font-size:.7rem; color:#475569; margin-top:1rem; }
"""

_STATUS_COLOR = {"ok": "#22c55e", "warn": "#f59e0b", "none": "#475569"}
_STATUS_TXT = {"ok": "recibo vigente", "warn": "recibo invalidado", "none": "sin recibo"}


def _dash_graph_svg(model):
    """Grafo del pipeline pintado con el estado del proyecto (SVG puro, viewBox fijo)."""
    W, H, Y = 1140, 420, 210
    X = lambda m: m["x"] / 100 * W
    parts = ['<defs>'
             '<marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">'
             '<path d="M0,0 L8,4 L0,8 z" fill="#334155"/></marker>'
             '<marker id="la" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto">'
             '<path d="M0,0 L9,4.5 L0,9 z" fill="#f59e0b"/></marker></defs>']
    for i in range(len(MACRO) - 1):
        parts.append(f'<line x1="{X(MACRO[i]):.0f}" y1="{Y}" x2="{X(MACRO[i+1]):.0f}" y2="{Y}" '
                     f'stroke="#334155" stroke-width="2" marker-end="url(#a)"/>')
    active = model["loops_activos"]
    for (f, t, lbl) in LOOPS:
        n = active.get(f"{f}->{t}")
        on = n is not None
        op = '1' if on else '.25'
        tag = lbl + (f" — ACTIVO: {n}" if on and n else "")
        if f == t:
            x = X(MACRO[f - 1])
            parts.append(f'<path d="M {x-24:.0f} {Y-28} C {x-60:.0f} {Y-110}, {x+60:.0f} {Y-110}, {x+24:.0f} {Y-28}" '
                         f'fill="none" stroke="#f59e0b" stroke-opacity="{op}" stroke-dasharray="4 3" marker-end="url(#la)"/>')
            parts.append(f'<text x="{x:.0f}" y="{Y-100}" text-anchor="middle" font-size="12.5" font-weight="600" '
                         f'fill="#fbbf24" fill-opacity="{op}">{tag}</text>')
            continue
        x1, x2 = X(MACRO[f - 1]), X(MACRO[t - 1])
        span = abs(f - t)
        lift = 80 + 45 * span
        my = Y + lift if f > t else Y - lift
        apex = (Y + my) / 2
        ex = x2 + (34 if f > t else -34)
        w = '2.5' if on else '1.5'
        parts.append(f'<path d="M {x1:.0f} {Y} Q {(x1+x2)/2:.0f} {my}, {ex:.0f} {Y}" fill="none" stroke="#f59e0b" '
                     f'stroke-opacity="{op}" stroke-width="{w}" stroke-dasharray="4 3" marker-end="url(#la)"/>')
        parts.append(f'<text x="{(x1+x2)/2:.0f}" y="{apex + (18 if f>t else -8):.0f}" text-anchor="middle" '
                     f'font-size="12.5" font-weight="600" fill="#fbbf24" fill-opacity="{op}">↺ {tag}</text>')
    for m in MACRO:
        st = model["gate_status"].get(str(m["id"])) or model["gate_status"].get(m["id"])
        estado = st["estado"] if st else "none"
        color = "#3b82f6" if m["id"] == model["fase_actual"] else _STATUS_COLOR[estado]
        ring = ('<circle cx="{x:.0f}" cy="{y}" r="36" fill="none" stroke="#3b82f6" '
                'stroke-opacity=".35" stroke-width="6"/>') if m["id"] == model["fase_actual"] else ""
        x = X(m)
        gate_txt = ""
        if st:
            badge_color = _STATUS_COLOR[st["estado"]]
            gate_txt = (f'<text x="{x:.0f}" y="{Y-58}" text-anchor="middle" font-size="10" fill="{badge_color}">'
                        f'⛔ {st["gate"]} — {_STATUS_TXT[st["estado"]]}</text>')
        here = ' ← estás aquí' if m["id"] == model["fase_actual"] else ""
        parts.append(f'{ring}<circle cx="{x:.0f}" cy="{Y}" r="28" fill="#1e293b" stroke="{color}" stroke-width="3"/>'
                     f'<text x="{x:.0f}" y="{Y+6}" text-anchor="middle" font-size="17" font-weight="700" fill="#e2e8f0">{m["id"]}</text>'
                     f'<text x="{x:.0f}" y="{Y+52}" text-anchor="middle" font-size="13.5" font-weight="600" fill="#cbd5e1">{m["title"]}{here}</text>'
                     f'{gate_txt}')
    return (f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;display:block">'
            + "".join(parts) + "</svg>")


def render_dashboard_html(model, state_json=""):
    import html as _html
    esc = _html.escape
    c = model["contadores"]

    kpis = [("Sprints completados", c["sprints"]),
            ("Releases (GATE 3)", c["releases"]),
            ("HU cerradas", f'{c["hu"]["cerradas"]}/{c["hu"]["total"]}' if c["hu"] else None),
            ("Recibos vigentes", c["recibos_vigentes"]),
            ("Recibos rehechos", c["recibos_rehechos"]),
            ("Gates al primer intento", f'{c["gates_1er"]}%' if c["gates_1er"] is not None else None)]
    kpi_html = "".join(
        f'<div class="kpi"><div class="v">{esc(str(v))}</div><div class="k">{esc(k)}</div></div>'
        for k, v in kpis if v is not None) or '<div class="empty">Sin datos aún — el dashboard se llena con los primeros recibos.</div>'

    # Tendencias: lead time y retrabajo por sprint (serie de sprint-review-NN.md)
    gates_lt = sorted({g for s in model["tendencias"] for g in s["lead"]})
    if model["tendencias"]:
        max_lt = max((v for s in model["tendencias"] for v in s["lead"].values()), default=1) or 1
        max_rh = max((s["rehechos"] for s in model["tendencias"]), default=1) or 1
        rows = ""
        for s in model["tendencias"]:
            cells = "".join(
                (f'<td><span class="bar" style="width:{int(90*s["lead"][g]/max_lt)}px"></span>{_fmt_span(s["lead"][g])}</td>'
                 if g in s["lead"] else "<td>-</td>")
                for g in gates_lt)
            rows += (f'<tr><td>{s["sprint"]}</td>{cells}'
                     f'<td><span class="bar bad" style="width:{int(60*s["rehechos"]/max_rh)}px"></span>{s["rehechos"]}</td>'
                     f'<td>{s["artefactos"]}</td><td>{s["gates_1er"]}%</td></tr>')
        # Alerta: algún gate empeora entre los dos últimos sprints
        alert = ""
        if len(model["tendencias"]) >= 2:
            a, b = model["tendencias"][-2]["lead"], model["tendencias"][-1]["lead"]
            peores = [g for g in gates_lt if g in a and g in b and b[g] > a[g] * 1.15]
            if peores:
                alert = ('<div class="warn-line">⚠ Empeora el lead time de '
                         + ", ".join(f"{g} ({_fmt_span(a[g])} → {_fmt_span(b[g])})" for g in peores)
                         + " — candidato a acción del próximo sprint.</div>")
        trends = (f"<table><tr><th>Sprint</th>{''.join(f'<th>{esc(g)}</th>' for g in gates_lt)}"
                  f"<th>Retrabajo</th><th>Artefactos vigentes</th><th>Gates 1er intento</th></tr>{rows}</table>{alert}")
    else:
        trends = '<div class="empty">Sin sprint reviews aún — las tendencias aparecen desde el primer <code>sprint_review.py</code>.</div>'

    if model["aprendizajes"]:
        learns = "".join(f'<div class="learn">📚 {esc(t)}</div>' for t in model["aprendizajes"])
    else:
        learns = '<div class="empty">Sin memorias learning registradas.</div>'

    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dashboard — {esc(model["proyecto"])}</title>
<style>{DASH_CSS}</style></head><body>
<h1>📊 Dashboard — {esc(model["proyecto"])}</h1>
<div class="sub">Generado: {model["generado"]} · spec/dashboard.html (artefacto derivado — no editar a mano)</div>

<div class="panel"><h2>Pipeline — estado actual</h2>
{_dash_graph_svg(model)}
<div class="legend"><span class="lg-ok">gate con recibo vigente</span><span class="lg-warn">recibo invalidado / retrabajo</span><span class="lg-none">sin recibo aún</span><span class="lg-cur">fase actual</span></div>
</div>

<div class="panel"><h2>Acumulado del proyecto</h2><div class="kpis">{kpi_html}</div></div>

<div class="panel"><h2>Tendencias (serie de sprint-review-NN.md)</h2>{trends}</div>

<div class="panel"><h2>Aprendizajes recientes (memorias learning)</h2>{learns}</div>

<footer>Artefacto derivado de receipts/ + spec/ + sprint-review-NN.md (ADR-002) — regenerar: <code>harness_graph.py --proyecto .</code> · drift: <code>--check</code> en CI · La evidencia son los recibos; este tablero es solo visualización.</footer>
<!-- dashboard-state: __STATE__ -->
</body></html>
""".replace("__STATE__", state_json)


def main_proyecto(a):
    import json, re
    project_dir = os.path.abspath(a.proyecto)
    spec_dir = os.path.join(project_dir, "spec")
    if not os.path.isdir(spec_dir):
        print(f"ERROR: {spec_dir} no existe — el proyecto no tiene spec/ gobernada.")
        sys.exit(1)
    model = derive_project(project_dir)

    if a.json:
        print(json.dumps(model, indent=2, ensure_ascii=False))
        sys.exit(0)

    # El timestamp hace irreproducible el HTML; el estado derivado (sin timestamp)
    # viaja incrustado como comentario en el propio dashboard y es lo que --check compara.
    out = os.path.join(spec_dir, "dashboard.html")
    state = {k: v for k, v in model.items() if k != "generado"}
    state_json = json.dumps(state, ensure_ascii=False, sort_keys=True)

    if a.check:
        prev = None
        if os.path.isfile(out):
            m = re.search(r"<!-- dashboard-state: (.*?) -->",
                          open(out, encoding="utf-8", errors="replace").read(), re.S)
            if m:
                prev = m.group(1).strip()
        if prev != state_json:
            print("DRIFT: spec/dashboard.html falta o quedó atrás del estado de "
                  "receipts/ + spec/ (regenerar: harness_graph.py --proyecto .)")
            sys.exit(1)
        print("DASHBOARD CHECK OK: spec/dashboard.html al día con el proyecto.")
        sys.exit(0)

    html = render_dashboard_html(model, state_json)
    open(out, "w", encoding="utf-8", newline="\n").write(html)
    print(f"Dashboard generado: {out}")
    print(f"  fase actual: {model['fase_actual']} · sprints: {model['contadores']['sprints']} "
          f"· recibos vigentes: {model['contadores']['recibos_vigentes']}")
    sys.exit(0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--skills-dir", default=SKILLS_DIR)
    ap.add_argument("--out", default=OUT_HTML)
    ap.add_argument("--proyecto", metavar="DIR",
                    help="modo dashboard (ADR-002): DIR es la raíz del proyecto (usa DIR/spec)")
    ap.add_argument("--json", action="store_true", help="imprime el modelo derivado (debug)")
    a = ap.parse_args()
    if not a.proyecto and not (a.write or a.check):
        ap.error("se requiere --write, --check o --proyecto DIR")

    if a.proyecto:
        return main_proyecto(a)

    skills = derive(os.path.abspath(a.skills_dir))
    nodes, transversal = build_data(skills)
    html = render_html(nodes, transversal, len(skills))

    if a.write:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        open(a.out, "w", encoding="utf-8", newline="\n").write(html)
        print(f"Grafo generado: {a.out} ({len(nodes)} nodos, {len(skills)} skills)")
        sys.exit(0)

    drift = not os.path.isfile(a.out) or open(a.out, encoding="utf-8").read() != html
    if drift:
        print(f"DRIFT: {a.out} no coincide con el manifiesto (regenerar: harness_graph.py --write)")
        sys.exit(1)
    print(f"GRAPH CHECK OK: {os.path.basename(a.out)} al día con el manifiesto.")


if __name__ == "__main__":
    main()
