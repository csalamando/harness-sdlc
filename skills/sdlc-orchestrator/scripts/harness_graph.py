#!/usr/bin/env python3
"""harness_graph.py — genera el grafo interactivo del arnés (docs/graph.html).

El grafo es un artefacto DERIVADO: los nodos (macro-fases), las skills por nodo,
sus gates y sus flujos in/out salen del manifiesto (frontmatter harness-*) y del
grafo de dependencias de spec_diff_impact.py. Nunca se edita el HTML a mano.

Uso:
  python3 harness_graph.py --write    # regenera docs/graph.html
  python3 harness_graph.py --check    # exit 1 si el HTML versionado tiene drift

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


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    ap.add_argument("--skills-dir", default=SKILLS_DIR)
    ap.add_argument("--out", default=OUT_HTML)
    a = ap.parse_args()

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
