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
from manifest_check import derive, SKILLS_DIR, harness_version
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
    return (TEMPLATE.replace("/*__DATA__*/null", data)
            .replace("__TOTAL__", str(total_skills))
            .replace("__VERSION__", harness_version() or "?"))


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
<footer>Artefacto derivado (arnés v__VERSION__) — regenerar con <code>manifest_check/harness_graph.py --write</code>. No editar a mano (el drift lo detecta el self-test y el CI).</footer>
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


def norm_gate(g):
    """Normaliza el gate de un recibo a 'GATE N' (alias históricos: 'fase2', 'fase 2', 'gate2')."""
    import re as _re
    m = _re.search(r"(\d+(?:\.\d+)?)", str(g or ""))
    return f"GATE {m.group(1)}" if m else str(g or "")


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
        fecha = re.search(r"Generado:\s*(\d{4}-\d{2}-\d{2})", text)
        lead = {}
        for row in re.finditer(r"^\| (GATE [\d.]+) \| [^|]+ \| [^|]+ \| \d+ \| ([^|]+) \|$",
                               text, re.M):
            mins = _span_minutes(row.group(2).strip())
            if mins is not None:
                lead[row.group(1)] = mins
        out.append({"sprint": int(m.group(1)),
                    "fecha": fecha.group(1) if fecha else None,
                    "artefactos": int(kpi("Artefactos aprobados") or 0),
                    "gates_1er": int(float(kpi("Gates al primer intento") or 0)),
                    "rehechos": int(r.group(1)) if r else 0,
                    "lead": lead})
    return out


def recent_sessions(spec_dir, limit=4):
    """Handoffs de sesión más recientes (degrada a [] si no hay)."""
    import re as _re
    d = os.path.join(spec_dir, "memory", "sessions")
    if not os.path.isdir(d):
        return []
    found = []
    for f in os.listdir(d):
        if not f.endswith(".md"):
            continue
        p = os.path.join(d, f)
        try:
            text = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        done = _re.search(r"\*\*Trabajo realizado\*\*:\s*(.+)", text)
        nxt = _re.search(r"\*\*Proximos pasos\*\*:\s*(.+)", text)
        res = _re.search(r"\*\*Resumen\*\*:\s*(.+)", text)
        found.append((os.path.getmtime(p), {
            "id": f[:-3],
            "done": (done.group(1).strip() if done else (res.group(1).strip() if res else "-"))[:180],
            "next": (nxt.group(1).strip() if nxt else "-")[:180],
        }))
    return [s for _, s in sorted(found, key=lambda x: x[0], reverse=True)[:limit]]


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


def parse_adrs(project_dir):
    """ADRs con estado y Risk Tier — spec/adr/ (proyectos) o docs/decisions/ (este repo)."""
    import glob, re
    for d in (os.path.join(project_dir, "spec", "adr"),
              os.path.join(project_dir, "docs", "decisions")):
        if not os.path.isdir(d):
            continue
        out = []
        for p in sorted(glob.glob(os.path.join(d, "ADR-*.md"))):
            try:
                text = open(p, encoding="utf-8", errors="replace").read(1500)
            except OSError:
                continue
            title = re.search(r"^#\s+(.+)$", text, re.M)
            status = re.search(r"\*\*(?:Status|Estado)\*\*[:\s]+([A-Za-zÁÉÍÓÚáéíóú ()]+)", text)
            tier = re.search(r"\*\*Risk Tier\*\*[:\s]+(\d)", text)
            aid = re.search(r"ADR-\d+", os.path.basename(p))
            if not aid:
                continue  # índices/consolidados no son ADRs
            ttl = (title.group(1).strip() if title else os.path.basename(p))
            ttl = re.sub(rf"^{re.escape(aid.group(0))}[:\s-]*", "", ttl)  # el ID ya va en su columna
            out.append({"id": aid.group(0),
                        "title": ttl,
                        "status": (status.group(1).strip() if status else "?"),
                        "tier": (tier.group(1) if tier else None)})
        if out:
            return out
    return []


def audit_summary(spec_dir):
    """Resumen de la memoria de auditoría (v2.23, ADR-004) para el portal.

    TODO se re-deriva de spec/audit/events.jsonl — el portal nunca narra.
    None si el log no existe (la página muestra empty-state accionable).
    """
    import json as _j
    p = os.path.join(spec_dir, "audit", "events.jsonl")
    if not os.path.isfile(p):
        return None
    eventos = []
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if line:
            try:
                eventos.append(_j.loads(line))
            except ValueError:
                pass
    if not eventos:
        return None
    por_tipo = {}
    for e in eventos:
        por_tipo[e.get("evento", "?")] = por_tipo.get(e.get("evento", "?"), 0) + 1
    revocaciones = [e for e in eventos if e.get("evento") in ("revoke", "invalidado")]
    aprobadores = sorted({e["approved_by"] for e in eventos if e.get("approved_by")})
    versiones = sorted({e["harness_version"] for e in eventos if e.get("harness_version")})
    return {
        "total": len(eventos),
        "por_tipo": por_tipo,
        "emits": por_tipo.get("emit", 0),
        "revocaciones": revocaciones,
        "n_revocaciones": len(revocaciones),
        "aprobadores": aprobadores,
        "versiones": versiones,
        "ultimo_ts": eventos[-1].get("ts", ""),
        "ultimo_hash": eventos[-1].get("hash", ""),
        "cadena_ok": all(e.get("prev_hash") and e.get("hash") for e in eventos),
        "eventos_recientes": list(reversed(eventos[-12:])),
    }


def parse_radar(spec_dir):
    """Tech radar por cuadrante: conteo y nombres (spec/tech-radar.yaml)."""
    import re
    p = os.path.join(spec_dir, "tech-radar.yaml")
    if not os.path.isfile(p):
        return None
    text = open(p, encoding="utf-8", errors="replace").read()
    counts, techs = {}, {}
    heads = list(re.finditer(r"^\s{2}(ADOPT|TRIAL|ASSESS|HOLD):\s*\n", text, re.M))
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        found = re.findall(r'-\s*technology:\s*"?([^"\n]+)"?', text[h.end():end])
        counts[h.group(1)] = len(found)
        techs[h.group(1)] = [t.strip() for t in found]
    for q in ("ADOPT", "TRIAL", "ASSESS", "HOLD"):
        counts.setdefault(q, 0)
        techs.setdefault(q, [])
    if not any(counts.values()):
        return None
    return {"counts": counts, "techs": techs}


def receipt_timeline(recs):
    """Serie histórica por fecha derivada de los timestamps de los recibos (v2.14).

    Los recibos no llevan etiqueta de sprint, así que los sprints pasados sin
    sprint-review no se pueden reconstruir como sprints — pero la serie por
    FECHA sí: acumulados de aprobados, rehechos y % al primer intento.
    """
    import collections
    eventos = collections.defaultdict(lambda: {"aprob": 0, "rehecho": 0, "intentos": 0})
    for r in recs:
        fecha = (r.get("emitido") or "")[:10]
        if not fecha:
            continue
        ev = eventos[fecha]
        if r.get("estado") == "vigente":
            ev["aprob"] += 1
        elif r.get("estado") in ("invalidado", "revocado"):
            ev["rehecho"] += 1
        ev["intentos"] += int(r.get("attempts") or 1)
    out = []
    aprob = rehecho = intentos = recibos = 0
    for fecha in sorted(eventos):
        ev = eventos[fecha]
        aprob += ev["aprob"]; rehecho += ev["rehecho"]
        intentos += ev["intentos"]; recibos += ev["aprob"] + ev["rehecho"]
        out.append({"fecha": fecha, "aprobados": aprob, "rehechos": rehecho,
                    "gates_1er": round(100 * aprob / max(recibos, 1))})
    return out


def phase_times(recs):
    """Tiempos por gate/fase derivados de los timestamps de los recibos (v2.14).

    - trabajo: span entre el primer y el último recibo emitido del gate.
    - cierre_dia: en qué día del proyecto cerró el gate (días desde el primer
      recibo del proyecto). Permite ver el orden real de cierre — si un gate
      cierra antes que el anterior (gobernanza retroactiva), se ve tal cual.
    """
    from datetime import datetime
    por_gate = {}
    t0 = None
    for r in recs:
        g = norm_gate(r.get("gate"))
        ts = (r.get("emitido") or "")[:19]
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts)
        except ValueError:
            continue
        t0 = dt if t0 is None else min(t0, dt)
        cur = por_gate.setdefault(g, [dt, dt])
        cur[0] = min(cur[0], dt); cur[1] = max(cur[1], dt)
    out = []
    for g in ("GATE 0", "GATE 1", "GATE 2", "GATE 2.5", "GATE 3"):
        if g not in por_gate:
            out.append({"gate": g, "macro": GATE_MACRO[g]})
            continue
        ini, fin = por_gate[g]
        out.append({"gate": g, "macro": GATE_MACRO[g],
                    "apertura": ini.date().isoformat(), "cierre": fin.date().isoformat(),
                    "trabajo_min": int((fin - ini).total_seconds() // 60),
                    "cierre_dia": round((fin - t0).total_seconds() / 86400, 1)})
    return out


def cycle_times(reviews, recs):
    """Duración de cada sprint/ciclo: días entre cierres de sprint review (v2.14).

    El sprint 1 se mide desde el primer recibo del proyecto (inicio real del
    trabajo gobernado). Un ciclo = un recorrido del loop 4→4 (sprints).
    """
    from datetime import date
    fechas_rec = sorted((r.get("emitido") or "")[:10] for r in recs if r.get("emitido"))
    inicio = date.fromisoformat(fechas_rec[0]) if fechas_rec else None
    out = []
    prev = inicio
    for rv in reviews:
        f = rv.get("fecha")
        if not f:
            out.append({"sprint": rv["sprint"]})
            continue
        d = date.fromisoformat(f)
        out.append({"sprint": rv["sprint"], "cierre": f,
                    "dias": (d - prev).days if prev else None,
                    "desde": prev.isoformat() if prev else None})
        prev = d
    return out


def tdd_commits(project_dir, rango="HEAD~60..HEAD"):
    """HUs con evidencia de orden TDD (test antes que código) según git log.
    Degrada a None si no hay repo git o ningún commit con la convención."""
    import subprocess as _sp
    r = _sp.run(["git", "log", "--reverse", "--format=%s", rango],
                capture_output=True, text=True, cwd=project_dir)
    if r.returncode != 0:
        return None
    import re as _re
    hu_re, kind_re = _re.compile(r"\b([A-Z]+-\d+)\b"), _re.compile(r"^(test|feat|fix)\(")
    por_hu = {}
    for msg in r.stdout.splitlines():
        m = kind_re.match(msg)
        if not m:
            continue
        for hu in hu_re.findall(msg):
            por_hu.setdefault(hu, []).append(m.group(1))
    verificables = {h: ks for h, ks in por_hu.items()
                    if "test" in ks and any(k in ("feat", "fix") for k in ks)}
    if not verificables:
        return None
    ok = sum(1 for ks in verificables.values()
             if ks.index("test") < min(i for i, k in enumerate(ks) if k in ("feat", "fix")))
    return {"ok": ok, "total": len(verificables)}


def tokens_honestos(recs):
    """Separa tokens medidos (reportados) de estimados y mide la cobertura.
    v2.15: alerta si el promedio estimado difiere >25% del reportado."""
    rep = [r for r in recs if r.get("tokens_src") == "reportado"]
    est = [r for r in recs if r.get("tokens_src") == "estimado"]
    tot = lambda rs: sum(int(r.get("tokens_in") or 0) + int(r.get("tokens_out") or 0) for r in rs)
    tok_rep, tok_est = tot(rep), tot(est)
    n = len(rep) + len(est)
    alerta = None
    if rep and est and tok_rep:
        diff = (tok_est / len(est) - tok_rep / len(rep)) / (tok_rep / len(rep))
        if abs(diff) > 0.25:
            alerta = f"estimados {diff:+.0%} vs reportados"
    return {"reportados": tok_rep, "estimados": tok_est,
            "cobertura": round(100 * len(rep) / n) if n else None,
            "alerta": alerta}


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

    # Estado de cada macro-fase según los recibos de su gate (normalizados)
    gate_status = {}   # macro -> {"estado": ok|warn|none, "gate": str, "vigentes": n, "rehechos": n}
    for m in MACRO:
        gates = [g for g, mac in GATE_MACRO.items() if mac == m["id"]]
        if not gates:
            continue
        rv = [r for r in vigentes if norm_gate(r.get("gate")) in gates]
        rr = [r for r in rehechos if norm_gate(r.get("gate")) in gates]
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
        loop = LOOP_BY_GATE.get(norm_gate(r.get("gate")))
        if loop:
            active[loop] = active.get(loop, 0) + 1
    reviews = parse_reviews(spec_dir)
    if reviews:
        active[(4, 4)] = 0  # el loop de sprints corre desde el sprint 1
    if os.path.isfile(os.path.join(spec_dir, "impact-report.md")):
        active[(6, 1)] = 0

    # Recorridos históricos de cada loop (v2.13): siempre visibles cuando > 0
    loops_count = {"4->4": len(reviews)}
    for (f, t), n in sorted(active.items()):
        if (f, t) != (4, 4):
            loops_count[f"{f}->{t}"] = n
    impact_reports = 0
    rep_dir = os.path.join(spec_dir, "reports")
    if os.path.isfile(os.path.join(spec_dir, "impact-report.md")):
        impact_reports = 1
    elif os.path.isdir(rep_dir):
        import glob as _g
        impact_reports = len(_g.glob(os.path.join(rep_dir, "impact-report*.md")))
    if impact_reports:
        loops_count["6->1"] = impact_reports

    # Artefactos con recibo vigente por macro-fase (qué se ha generado)
    artefactos_por_fase = {}
    artefactos_href = {}   # basename -> ruta relativa a spec/ (enlace desde el popup)
    for r in vigentes:
        art = r.get("artefacto", "")
        # Los recibos pueden traer rutas absolutas con separadores de otro SO
        # (fixture generado en Windows, CI en Linux): normalizar a '/'.
        a = (art or "").replace("\\", "/")
        b = a.rsplit("/", 1)[-1] if a else "?"
        if art:
            s = spec_dir.replace("\\", "/").rstrip("/") + "/"
            rel = a[len(s):] if a.startswith(s) else b
            # Los .md se enlazan a su pagina del portal (ruta hash del shell);
            # el resto (json, yaml...) va al archivo tal cual en otra pestaña.
            if rel.lower().endswith(".md"):
                import mdview, portal_lib
                pid = portal_lib.slug("paginas/docs/" + mdview.doc_name(rel))
                rel = "../index.html#/id/" + pid
            artefactos_href[b] = rel
        mac = GATE_MACRO.get(norm_gate(r.get("gate")))
        if mac:
            artefactos_por_fase.setdefault(mac, []).append(b)

    # Diagramas vivos IR + renders (v2.17/2.18): spec/diagrams/*.html
    import glob as _gd
    diagramas = []
    for p in sorted(_gd.glob(os.path.join(spec_dir, "diagrams", "*.html"))):
        diagramas.append({"id": os.path.splitext(os.path.basename(p))[0],
                          "href": "diagrams/" + os.path.basename(p)})

    # HU: historias con test y código (degrada a None si no hay estructura).
    # Los proyectos reales no siempre usan src/ + tests/: se exploran los
    # directorios candidatos que existan (backend/, frontend/, e2e/, etc.).
    hu = None
    if collect_ids:
        root = os.path.abspath(project_dir)
        us = os.path.join(spec_dir, "user-stories.md")
        stories = collect_ids(us if os.path.isfile(us) else spec_dir, [".md"])
        test_exts = [".py", ".ts", ".tsx", ".js", ".java", ".cs", ".feature"]
        code_exts = [".py", ".ts", ".tsx", ".js", ".java", ".cs"]
        tests, code = set(), set()
        for d in ("tests", "test", "e2e", "backend/e2e", "frontend/e2e", "backend/tests", "frontend/tests"):
            tests |= collect_ids(os.path.join(root, d), test_exts)
        # código: solo dirs de fuente (excluye e2e/tests y node_modules por construcción)
        for d in ("src", "backend/src", "frontend/src", "app", "lib", "poc/src"):
            code |= collect_ids(os.path.join(root, d), code_exts)
        if stories:
            hu = {"total": len(stories), "cerradas": len(stories & tests & code)}

    nombre = os.path.basename(os.path.abspath(project_dir))
    # Detalle por fase para el popup del dashboard: skills con entradas/salidas
    # derivadas del manifiesto (misma fuente que el grafo del arnés).
    try:
        nodes, _tr = build_data(derive(SKILLS_DIR))
        fases_detalle = [{"id": n["id"], "title": n["title"], "desc": n["desc"],
                          "gate": n.get("gate"), "skills": n["skills"]} for n in nodes]
    except Exception:
        fases_detalle = []
    return {
        "proyecto": nombre,
        "harness_version": harness_version() or "sin-declarar",
        "generado": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "gate_status": gate_status, "fase_actual": current,
        "loops_activos": {f"{f}->{t}": n for (f, t), n in sorted(active.items())},
        "loops_count": loops_count,
        "artefactos_por_fase": {str(k): sorted(v) for k, v in sorted(artefactos_por_fase.items())},
        "artefactos_href": artefactos_href,
        "diagramas": diagramas,
        "adrs": parse_adrs(project_dir),
        "radar": parse_radar(spec_dir),
        "contadores": {
            "sprints": len(reviews),
            "releases": sum(1 for r in vigentes if norm_gate(r.get("gate")) == "GATE 3"),
            "hu": hu,
            "recibos_vigentes": len(vigentes), "recibos_rehechos": len(rehechos),
            "gates_1er": reviews[-1]["gates_1er"] if reviews else None,
        },
        "tokens": tokens_honestos(recs),
        "tdd": tdd_commits(project_dir),
        "tendencias": reviews,
        "timeline": receipt_timeline(recs),
        "tiempos": {"fases": phase_times(recs), "ciclos": cycle_times(reviews, recs)},
        "fases_detalle": fases_detalle,
        "aprendizajes": recent_learnings(spec_dir),
        "sesiones": recent_sessions(spec_dir),
        "auditoria": audit_summary(spec_dir),
    }


# ── Render del dashboard (self-contained, sin JS ni dependencias) ─────────────

# CSS de las páginas de métricas del portal (v2.20): todo con las variables de
# portal_lib.TOKENS_CSS, así el tema claro/oscuro lo cambia el shell sin tocar
# las páginas. Antes era el CSS del dashboard monolítico con colores fijos.
DASH_CSS = """
  h1 { font-size:1.3rem; margin-bottom:.2rem; }
  .sub { color:var(--sub); font-size:.85rem; margin-bottom:1.5rem; }
  .panel { background:var(--panel-bg); border:1px solid var(--panel-bd); border-radius:12px; padding:1.2rem; margin-bottom:1.5rem; }
  .panel h2 { font-size:1rem; margin:0 0 1rem; color:var(--fg); }
  .legend { display:flex; gap:1.2rem; font-size:.75rem; color:var(--sub); margin-top:.6rem; flex-wrap:wrap; }
  .legend span::before { content:"\\25CF"; margin-right:.35rem; }
  .lg-ok::before { color:var(--ok); } .lg-warn::before { color:var(--warn); } .lg-none::before { color:var(--muted); }
  .lg-cur::before { color:var(--accent); }
  .kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:.8rem; }
  .kpi { background:var(--card-bg); border:1px solid var(--panel-bd); border-radius:10px; padding:.9rem; }
  .kpi .v { font-size:1.7rem; font-weight:700; }
  .kpi .k { font-size:.72rem; color:var(--sub); margin-top:.2rem; }
  table { border-collapse:collapse; width:100%; font-size:.8rem; }
  th, td { text-align:left; padding:.45rem .6rem; border-bottom:1px solid var(--panel-bd); }
  th { color:var(--sub); font-weight:600; font-size:.72rem; text-transform:uppercase; letter-spacing:.04em; }
  .bar { height:8px; border-radius:4px; background:var(--accent); display:inline-block; vertical-align:middle; margin-right:.4rem; }
  .bar.bad { background:var(--warn); }
  .learn { font-size:.82rem; color:var(--fg); margin:.4rem 0; }
  .warn-line { font-size:.75rem; color:var(--warn); margin-top:.6rem; }
  .empty { color:var(--muted); font-size:.82rem; font-style:italic; }
  footer { font-size:.7rem; color:var(--muted); margin-top:1rem; }
  .badge { display:inline-block; font-size:.72rem; border-radius:4px; padding:2px 7px; margin:2px; white-space:nowrap; }
  .st-ok { background:rgba(34,197,94,.14); color:var(--ok); border:1px solid rgba(34,197,94,.4); }
  .st-prop { background:rgba(59,130,246,.15); color:var(--accent); border:1px solid rgba(59,130,246,.45); }
  .st-sup { background:rgba(100,116,139,.15); color:var(--muted); border:1px solid rgba(100,116,139,.4); }
  .st-otro { background:var(--card-bg); color:var(--sub); border:1px solid var(--panel-bd); }
  .tier { background:rgba(249,115,22,.15); color:var(--tier); border:1px solid rgba(249,115,22,.45); }
  .art { background:var(--panel-bg); color:var(--sub); border:1px solid var(--panel-bd); }
  .quad { display:grid; grid-template-columns:repeat(auto-fit,minmax(120px,1fr)); gap:.6rem; margin-top:.8rem; }
  .quad .kpi .v { font-size:1.3rem; }
  [data-fase]:hover { opacity:.85; }
  .moverlay { display:none; position:fixed; inset:0; background:rgba(2,6,23,.78); z-index:50;
              align-items:flex-start; justify-content:center; padding:3rem 1rem; }
  .moverlay.open { display:flex; }
  .mbox { background:var(--panel-bg); border:1px solid var(--panel-bd); border-radius:14px; max-width:920px; width:100%;
          max-height:82vh; overflow-y:auto; padding:1.6rem 1.8rem; position:relative;
          box-shadow:0 20px 60px rgba(0,0,0,.6); }
  .mclose { position:absolute; top:.7rem; right:.9rem; background:none; border:none; color:var(--muted);
            font-size:1.6rem; cursor:pointer; line-height:1; }
  .mclose:hover { color:var(--fg); }
  .mbox h2 { font-size:1.15rem; margin:0 0 .3rem; color:var(--txt); }
  .mdesc { color:var(--sub); font-size:.92rem; margin:.2rem 0 .6rem; }
  .mgate { display:inline-block; font-size:.8rem; font-weight:600; color:var(--tier); background:rgba(249,115,22,.15);
           border:1px solid rgba(249,115,22,.45); border-radius:6px; padding:2px 10px; margin-bottom:.4rem; }
  .mbox h3 { font-size:.82rem; color:var(--sub); text-transform:uppercase; letter-spacing:.05em;
             margin:1.1rem 0 .5rem; }
  .sgrid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:.7rem; }
  .scard { background:var(--card-bg); border:1px solid var(--panel-bd); border-radius:10px; padding:.7rem .8rem; }
  .sname { font-weight:700; font-size:.95rem; color:var(--txt); }
  .sid { font-size:.75rem; color:var(--muted); margin:.1rem 0 .45rem; }
  .sio { font-size:.78rem; margin-top:.35rem; }
  .iol { color:var(--muted); font-weight:700; margin-right:.3rem; }
  .io-in { background:rgba(59,130,246,.15); color:var(--accent); border:1px solid rgba(59,130,246,.45); }
  .io-out { background:rgba(34,197,94,.14); color:var(--ok); border:1px solid rgba(34,197,94,.4); }
  .alink { text-decoration:none; cursor:pointer; font-size:.72rem; padding:3px 8px; }
  .alink:hover { color:var(--txt); border-color:var(--accent); }
  .home-cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:.8rem; margin:1rem 0 1.4rem; }
  .home-links li { margin:.35rem 0; }
  /* Layouts densos del portal (v2.20.1): info relacionada en la misma pantalla */
  .graph-wrap { max-width:920px; margin:0 auto; }
  .dense2 { display:grid; grid-template-columns:3fr 2fr; gap:1.4rem; align-items:start; }
  .dense2eq { display:grid; grid-template-columns:1fr 1fr; gap:1.4rem; align-items:start; }
  @media (max-width:1150px) { .dense2, .dense2eq { grid-template-columns:1fr; } }
  .diag-cards { display:grid; grid-template-columns:repeat(auto-fill,minmax(230px,1fr)); gap:.8rem; margin-bottom:1.2rem; }
  .dcard { display:flex; flex-direction:column; background:var(--card-bg); border:1px solid var(--panel-bd);
           border-radius:10px; padding:.8rem .9rem .55rem; color:var(--fg); }
  .dcard-head { display:flex; justify-content:space-between; align-items:baseline; gap:.5rem;
                font-size:.68rem; text-transform:uppercase; letter-spacing:.06em; color:var(--sub);
                border-bottom:1px solid var(--panel-bd); padding-bottom:.4rem; margin-bottom:.5rem; }
  .dcard-head b { color:var(--dcard-c, var(--accent)); font-weight:700; }
  .dcard-head .n { font-variant-numeric:tabular-nums; color:var(--muted); }
  .dcard-links { display:flex; flex-direction:column; gap:.3rem; flex:1; }
  .dcard-links a { font-size:.82rem; color:var(--txt); text-decoration:none; line-height:1.3;
                   padding:.15rem 0; }
  .dcard-links a:hover { color:var(--accent); text-decoration:underline; }
  .dcard-links a::before { content:"🗺 "; font-size:.75rem; }
  .dcard-foot { margin-top:.6rem; height:4px; border-radius:2px;
                background:var(--dcard-c, var(--accent)); opacity:.85; }
  .adr-row { cursor:pointer; }
  .adr-row:hover td { background:var(--card-bg); }
  .adr-row.hl td { background:rgba(59,130,246,.16); }
  [data-tech] { cursor:pointer; }
  [data-tech].hl circle { stroke:var(--accent); stroke-width:2.5; }
  [data-tech].hl text { fill:var(--accent); font-weight:700; }
  .radar-note { font-size:.72rem; color:var(--muted); margin-top:.3rem; }
"""

_STATUS_COLOR = {"ok": "#22c55e", "warn": "#f59e0b", "none": "#475569"}
_STATUS_TXT = {"ok": "recibo vigente", "warn": "recibo invalidado", "none": "sin recibo"}


def esc(s):
    """Escape HTML para etiquetas y tooltips del dashboard."""
    import html as _html
    return _html.escape(str(s))


def _dash_graph_svg(model):
    """Grafo del pipeline pintado con el estado del proyecto (SVG puro, viewBox fijo)."""
    W, H, Y = 1140, 560, 220
    X = lambda m: m["x"] / 100 * W
    parts = ['<defs>'
             '<marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">'
             '<path d="M0,0 L8,4 L0,8 z" fill="#334155"/></marker>'
             '<marker id="la" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto">'
             '<path d="M0,0 L9,4.5 L0,9 z" fill="#f59e0b"/></marker></defs>']
    for i in range(len(MACRO) - 1):
        parts.append(f'<line x1="{X(MACRO[i]):.0f}" y1="{Y}" x2="{X(MACRO[i+1]):.0f}" y2="{Y}" '
                     f'stroke="#334155" stroke-width="2" marker-end="url(#a)"/>')
    # Banda de progreso: tramo completado del pipeline en azul sobre la línea principal
    cur_x = X(MACRO[model["fase_actual"] - 1])
    if model["fase_actual"] == 6 and all(
            (model["gate_status"].get(str(g)) or {}).get("estado") == "ok" for g in (1, 3, 5, 6)):
        cur_x = X(MACRO[5]) + 30
    parts.append(f'<line x1="{X(MACRO[0]):.0f}" y1="{Y}" x2="{cur_x:.0f}" y2="{Y}" '
                 f'stroke="#3b82f6" stroke-opacity=".45" stroke-width="6" stroke-linecap="round"/>')
    active = model["loops_activos"]
    counts = model.get("loops_count", {})
    for (f, t, lbl) in LOOPS:
        n = active.get(f"{f}->{t}")
        hist = counts.get(f"{f}->{t}", 0)
        on = n is not None
        op = '1' if on else ('.6' if hist else '.25')
        tag = lbl + (f" ×{hist}" if hist else "") + (f" — ACTIVO: {n}" if on and n else "")
        # Loops sin recorrer y sin actividad: arco tenue con tooltip, sin texto
        # (evita la maraña de etiquetas; el nombre aparece al pasar el cursor).
        show_txt = on or hist
        tip = f'<title>{esc("↺ " + lbl)}</title>' if not show_txt else ""
        if f == t:
            x = X(MACRO[f - 1])
            parts.append(f'<path d="M {x-24:.0f} {Y-28} C {x-60:.0f} {Y-110}, {x+60:.0f} {Y-110}, {x+24:.0f} {Y-28}" '
                         f'fill="none" stroke="#f59e0b" stroke-opacity="{op}" stroke-dasharray="4 3" marker-end="url(#la)">{tip}</path>')
            if show_txt:
                parts.append(f'<text x="{x:.0f}" y="{Y-122}" text-anchor="middle" font-size="13" font-weight="600" '
                             f'fill="#fbbf24" fill-opacity="{op}">{tag}</text>')
            continue
        x1, x2 = X(MACRO[f - 1]), X(MACRO[t - 1])
        span = abs(f - t)
        lift = 90 + 50 * span
        my = Y + lift if f > t else Y - lift
        apex = (Y + my) / 2
        ex = x2 + (34 if f > t else -34)
        w = '2.5' if on else '1.5'
        parts.append(f'<path d="M {x1:.0f} {Y} Q {(x1+x2)/2:.0f} {my}, {ex:.0f} {Y}" fill="none" stroke="#f59e0b" '
                     f'stroke-opacity="{op}" stroke-width="{w}" stroke-dasharray="4 3" marker-end="url(#la)">{tip}</path>')
        if show_txt:
            parts.append(f'<text x="{(x1+x2)/2:.0f}" y="{apex + (20 if f>t else -10):.0f}" text-anchor="middle" '
                         f'font-size="13" font-weight="600" fill="#fbbf24" fill-opacity="{op}">↺ {tag}</text>')
    for m in MACRO:
        st = model["gate_status"].get(str(m["id"])) or model["gate_status"].get(m["id"])
        estado = st["estado"] if st else "none"
        color = "#3b82f6" if m["id"] == model["fase_actual"] else _STATUS_COLOR[estado]
        ring = ('<circle cx="{x:.0f}" cy="{y}" r="36" fill="none" stroke="#3b82f6" '
                'stroke-opacity=".35" stroke-width="6"/>') if m["id"] == model["fase_actual"] else ""
        x = X(m)
        # anclas: las etiquetas de los nodos de los extremos no se salen del viewBox
        anchor = "end" if x > W - 130 else ("start" if x < 130 else "middle")
        tx = x + (-10 if anchor == "end" else (10 if anchor == "start" else 0))
        gate_txt = ""
        if st:
            badge_color = _STATUS_COLOR[st["estado"]]
            mark = "✓" if st["estado"] == "ok" else ("⚠" if st["estado"] == "warn" else "·")
            gate_txt = (f'<text x="{tx:.0f}" y="{Y-56}" text-anchor="{anchor}" font-size="11.5" '
                        f'font-weight="600" fill="{badge_color}">'
                        f'⛔ {st["gate"]} {mark}<title>{esc(st["gate"])} — {esc(_STATUS_TXT[st["estado"]])}'
                        f' ({st["vigentes"]} vigentes, {st["rehechos"]} rehechos)</title></text>')
        here = ' ← estás aquí' if m["id"] == model["fase_actual"] else ""
        arts = (model.get("artefactos_por_fase") or {}).get(str(m["id"]), [])
        # Filas alternadas (impares arriba, pares abajo): los títulos y conteos
        # de nodos vecinos nunca comparten la misma línea horizontal.
        ty_t = Y + 56 + ((m["id"] - 1) % 2) * 40
        ty_a = ty_t + 20
        arts_txt = (f'<text x="{tx:.0f}" y="{ty_a}" text-anchor="{anchor}" font-size="11" fill="#64748b">'
                    f'{len(arts)} artefacto{"s" if len(arts) != 1 else ""} ✓</text>') if arts else ""
        parts.append(f'<g data-fase="{m["id"]}" style="cursor:pointer">'
                     f'<title>Ver skills, entradas y salidas de la fase {m["id"]}</title>'
                     f'{ring}<circle cx="{x:.0f}" cy="{Y}" r="28" fill="#1e293b" stroke="{color}" stroke-width="3"/>'
                     f'<text x="{x:.0f}" y="{Y+6}" text-anchor="middle" font-size="17" font-weight="700" fill="#e2e8f0">{m["id"]}</text>'
                     f'<text x="{tx:.0f}" y="{ty_t}" text-anchor="{anchor}" font-size="14.5" font-weight="600" fill="#cbd5e1">{m["title"]}{here}</text>'
                     f'{gate_txt}{arts_txt}</g>')
    return (f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto;display:block">'
            + "".join(parts) + "</svg>")


def _svg_line_chart(series_list, xlabels, fmt, w=520, h=190):
    """Gráfica de líneas SVG (self-contained) — series_list: [(nombre, [valores]), ...]."""
    colors = ["#3b82f6", "#f59e0b", "#22c55e", "#a78bfa"]
    series_list = [(n, vs) for n, vs in series_list if any(v is not None for v in vs)]
    if not series_list:
        return '<div class="empty">Sin datos de este indicador en los sprint reviews.</div>'
    pad_l, pad_b, pad_t, pad_r = 46, 30, 26, 52
    vals = [v for _, vs in series_list for v in vs if v is not None]
    vmax = max(vals) or 1
    n = len(xlabels)
    Xp = lambda i: pad_l + (w - pad_l - pad_r) * (i / max(n - 1, 1))
    Yp = lambda v: pad_t + (h - pad_b - pad_t) * (1 - v / vmax)
    parts = []
    for frac in (0, 0.5, 1):
        y = Yp(vmax * frac)
        parts.append(f'<line x1="{pad_l}" y1="{y:.0f}" x2="{w-pad_r+10}" y2="{y:.0f}" stroke="#1e293b"/>'
                     f'<text x="{pad_l-6}" y="{y+4:.0f}" text-anchor="end" font-size="10" fill="#64748b">{fmt(vmax*frac)}</text>')
    for i, lab in enumerate(xlabels):
        parts.append(f'<text x="{Xp(i):.0f}" y="{h-10}" text-anchor="middle" font-size="10" fill="#64748b">{lab}</text>')
    legend = ""
    for si, (name, vs) in enumerate(series_list):
        color = colors[si % len(colors)]
        pts = [(Xp(i), Yp(v)) for i, v in enumerate(vs) if v is not None]
        if len(pts) > 1:
            parts.append(f'<polyline points="{" ".join(f"{x:.0f},{y:.0f}" for x, y in pts)}" '
                         f'fill="none" stroke="{color}" stroke-width="2.5"/>')
        for x, y in pts:
            parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="3.5" fill="{color}"/>')
        last = next((v for v in reversed(vs) if v is not None), None)
        if pts and last is not None:
            x, y = pts[-1]
            parts.append(f'<text x="{min(x+7, w-pad_r+14):.0f}" y="{y+4:.0f}" font-size="10.5" font-weight="600" fill="{color}">{fmt(last)}</text>')
        legend += (f'<span style="color:{color};margin-right:.4rem">●</span>'
                   f'<span style="color:#94a3b8;margin-right:1rem">{name}</span>')
    return (f'<svg viewBox="0 0 {w} {h}" style="width:100%;height:auto;display:block">{"".join(parts)}</svg>'
            f'<div style="font-size:.72rem;margin-top:.2rem">{legend}</div>')


def _svg_barh(items, fmt, color="#3b82f6", row_h=30, label_w=110, w=520):
    """Barras horizontales SVG — items: [(etiqueta, valor_minutos_o_unidades), ...].

    Los valores None se omiten. El valor formateado va al final de cada barra.
    """
    items = [(lab, v) for lab, v in items if v is not None]
    if not items:
        return ""
    vmax = max(v for _, v in items) or 1
    h = row_h * len(items) + 8
    parts = []
    for i, (lab, v) in enumerate(items):
        y = 4 + i * row_h
        bw = max(2, (w - label_w - 60) * v / vmax)
        parts.append(f'<text x="{label_w-8}" y="{y+row_h/2+4:.0f}" text-anchor="end" font-size="11" fill="#94a3b8">{lab}</text>'
                     f'<rect x="{label_w}" y="{y+4}" width="{bw:.0f}" height="{row_h-10}" rx="4" fill="{color}" opacity=".85">'
                     f'<title>{lab}: {fmt(v)}</title></rect>'
                     f'<text x="{label_w+bw+7:.0f}" y="{y+row_h/2+4:.0f}" font-size="11" font-weight="600" fill="#e2e8f0">{fmt(v)}</text>')
    return f'<svg viewBox="0 0 {w} {h}" style="width:100%;max-width:640px;height:auto;display:block">{"".join(parts)}</svg>'


def _delta_card(titulo, prev, cur, fmt, invertir=False):
    """Tarjeta valor + Δ vs sprint anterior (para <3 sprints, cuando la línea aún no informa)."""
    if cur is None:
        return ""
    if prev is None or prev == cur:
        delta = '<span style="color:#64748b">= sin cambio</span>' if prev is not None else ""
    else:
        up = cur > prev
        peor = up if not invertir else not up
        arrow = "▲" if up else "▼"
        color = "#fca5a5" if peor else "#6ee7b7"
        delta = f'<span style="color:{color}">{arrow} {fmt(abs(cur - prev))} vs sprint anterior</span>'
    return (f'<div class="kpi"><div class="k">{titulo}</div><div class="v">{fmt(cur)}</div>'
            f'<div style="font-size:.72rem;margin-top:.3rem">{delta}</div></div>')


def _radar_chart_svg(techs):
    """Tech Radar como gráfica de cuadrantes 2×2 con blips por tecnología.

    Cada blip lleva data-tech con el nombre normalizado: la página de
    Arquitectura lo vincula con las filas de la tabla de ADRs (clic en uno
    resalta el otro).
    """
    qcolor = {"ADOPT": "#22c55e", "TRIAL": "#3b82f6", "ASSESS": "#f59e0b", "HOLD": "#ef4444"}
    maxn = max((len(v) for v in techs.values()), default=0)
    cell_w = 300
    cell_h = max(300, 70 + maxn * 26)          # crece si un cuadrante tiene muchas tecnologías
    qpos = {"TRIAL": (0, 0), "ADOPT": (cell_w, 0), "ASSESS": (0, cell_h), "HOLD": (cell_w, cell_h)}
    W, H = cell_w * 2, cell_h * 2
    parts = [f'<rect x="0" y="0" width="{W}" height="{H}" fill="var(--panel-bg)" rx="12"/>',
             f'<line x1="{cell_w}" y1="10" x2="{cell_w}" y2="{H-10}" stroke="var(--panel-bd)" stroke-width="2"/>',
             f'<line x1="10" y1="{cell_h}" x2="{W-10}" y2="{cell_h}" stroke="var(--panel-bd)" stroke-width="2"/>']
    for q, (qx, qy) in qpos.items():
        parts.append(f'<text x="{qx+18}" y="{qy+30}" font-size="13" font-weight="700" fill="{qcolor[q]}">{q}</text>')
        for i, t in enumerate(techs.get(q, [])):
            bx, by = qx + 26, qy + 52 + i * 26
            label = t if len(t) <= 38 else t[:36] + "…"
            key = _norm_tech(t)
            # <title> = tooltip con el nombre completo al pasar el mouse
            parts.append(f'<g data-tech="{key}"><title>{t}</title><circle cx="{bx}" cy="{by}" r="4.5" fill="{qcolor[q]}"/>'
                         f'<text x="{bx+10}" y="{by+4}" font-size="11" fill="var(--fg)">{label}</text></g>')
    return (f'<svg viewBox="0 0 {W} {H}" style="width:100%;max-width:520px;height:auto;display:block;margin-inline:auto">'
            + "".join(parts) + "</svg>")


def _norm_tech(s):
    """Clave normalizada para vincular tecnologías radar ↔ ADRs."""
    import re as _re, unicodedata as _u
    s = _u.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return _re.sub(r"[^a-z0-9]+", "", s.lower())


# Vinculación ADR ↔ Tech Radar (v2.20.1): clic en una fila de ADR resalta los
# blips de las tecnologías que menciona, y viceversa. Vanilla JS, sin red.
RADAR_LINK_JS = """
<script>
(function(){
  function clear(){document.querySelectorAll('.hl').forEach(function(e){e.classList.remove('hl');});}
  function mark(sel,keys){
    document.querySelectorAll(sel).forEach(function(e){
      var ks=(e.getAttribute('data-tech')||'').split(' ');
      if(keys.some(function(k){return ks.indexOf(k)>=0;}))e.classList.add('hl');
    });
  }
  document.querySelectorAll('tr.adr-row').forEach(function(r){
    r.addEventListener('click',function(){
      var was=r.classList.contains('hl');clear();
      if(was)return;
      var keys=(r.getAttribute('data-tech')||'').split(' ').filter(Boolean);
      r.classList.add('hl');mark('#radar g[data-tech]',keys);
    });
  });
  document.querySelectorAll('#radar g[data-tech]').forEach(function(g){
    g.addEventListener('click',function(){
      var was=g.classList.contains('hl');clear();
      if(was)return;
      var k=g.getAttribute('data-tech');
      g.classList.add('hl');mark('tr.adr-row',[k]);
    });
  });
})();
</script>
"""


GLOSARIO = [
    ("Gate (⛔)", "Punto de control del pipeline. Un artefacto no avanza de fase sin pasar su gate con evidencia."),
    ("Recibo (RDD)", "Registro firmado (sha256) de que un artefacto pasó su gate. Si el artefacto cambia, el recibo se invalida solo — confiar en evidencia, no en narración."),
    ("Recibo vigente / invalidado", "Vigente: el artefacto no cambió desde su aprobación. Invalidado: cambió y la aprobación debe repetirse (retrabajo)."),
    ("Risk Tier", "Clasificación de riesgo de una decisión: Tier 1 = alto riesgo (firma arquitectónica / board), Tier 2 = medio (ADR de 8 pasos), Tier 3 = bajo (decisión local documentada)."),
    ("ADR", "Architecture Decision Record: decisión tomada con el framework de 8 pasos, versionada en spec/adr/ con estado y Risk Tier."),
    ("Tech Radar / paved roads", "Catálogo de tecnologías por cuadrante. ADOPT = pre-aprobadas (camino pavimentado, sin fricción); TRIAL = requieren justificación; ASSESS/HOLD = exigen ADR de excepción."),
    ("Lead time", "Tiempo entre el primer y el último recibo de un gate. Si empeora entre sprints, el dashboard alerta."),
    ("Retrabajo", "Recibos invalidados o revocados en el periodo: aprobaciones que hubo que repetir. Creciente = gates débiles o cambios frecuentes de spec."),
    ("HU", "Historia de usuario. 'Cerrada' = tiene Gherkin en la spec + test + código (trazabilidad completa)."),
    ("Loop / arco de feedback", "Recorrido de retorno en el pipeline: bug de QA a TDD (5→4), hotfix de producción (6→4), replan de spec (3→4), sprints (4→4). ×N = cuántas veces se ha recorrido."),
    ("Drift", "Cuando un artefacto derivado (manifiesto, grafo, dashboard) queda desactualizado respecto a su fuente. El --check falla en CI hasta regenerarlo."),
    ("Sprint review", "Snapshot versionado del cierre de sprint (spec/reports/sprint-review-NN.md). La serie de snapshots alimenta las tendencias de este dashboard."),
    ("Cierre (día del proyecto)", "En qué día cerró cada gate, contado desde el primer recibo del proyecto. Muestra el orden real de cierre: si un gate cierra antes que el anterior (gobernanza retroactiva sobre una PoC), se ve tal cual."),
    ("Ciclo (sprint)", "Un recorrido del loop 4→4 (Strict TDD). Su duración son los días entre cierres de sprint review; el sprint 1 se mide desde el primer recibo del proyecto."),
]


# Popup por fase (v2.14): clic en un nodo del grafo o del stepper. Los datos
# (skills, entradas, salidas, artefactos generados) viajan incrustados como JSON.
# (v2.20: sin controles de zoom propios — el zoom y el tema los da el shell del
# portal de forma global y compartida con los diagramas.)
MODAL_HTML = """
<div id="fmodal" class="moverlay">
  <div class="mbox"><button class="mclose" onclick="closeF()" title="Cerrar">&times;</button>
  <div id="fbody"></div></div>
</div>
"""

MODAL_JS = """
document.querySelectorAll('[data-fase]').forEach(function(el){
  el.addEventListener('click',function(){openF(+el.getAttribute('data-fase'));});
});
var _fmodal=document.getElementById('fmodal');
_fmodal.addEventListener('click',function(e){if(e.target===_fmodal)closeF();});
document.addEventListener('keydown',function(e){if(e.key==='Escape')closeF();});
function _e(s){var d=document.createElement('div');d.textContent=String(s);return d.innerHTML;}
var _curF=null;
function _chip(name,cls){
  if(HREFS[name]){var h=HREFS[name],portal=h.indexOf('#/id/')>=0;
    return '<a class="badge '+cls+' alink" href="'+_e(h)+'"'
      +(portal?' target="_top" title="Abrir '+_e(name)+' dentro del portal"':' target="_blank" rel="noopener" title="Abrir '+_e(name)+' en otra pestaña"')
      +'>'+_e(name)+(portal?'':' &#8599;')+'</a>';}
  return '<span class="badge '+cls+'">'+_e(name)+'</span>';
}
function openF(id){
  var f=null;for(var i=0;i<FASES.length;i++){if(FASES[i].id===id){f=FASES[i];break;}}
  if(!f)return;
  _curF=id;
  var h='<h2>Fase '+f.id+' &middot; '+_e(f.title)+'</h2><p class="mdesc">'+_e(f.desc||'')+'</p>';
  if(f.gate)h+='<div class="mgate">&#x26D4; '+_e(f.gate)+'</div>';
  var arts=ARTS[String(id)]||[];
  if(arts.length){
    h+='<h3>Generado en este proyecto ('+arts.length+') &mdash; clic para abrirlo en el portal</h3><div>';
    for(var j=0;j<arts.length;j++)h+=_chip(arts[j],'art');
    h+='</div>';
  }
  h+='<h3>'+f.skills.length+' skills en esta fase &mdash; qué leen (IN) y qué generan (OUT)</h3><div class="sgrid">';
  for(var k=0;k<f.skills.length;k++){var s=f.skills[k];
    h+='<div class="scard"><div class="sname">'+_e(s.name)+'</div>'
      +'<div class="sid">'+_e(s.id)+(s.conditional?' &middot; condicional':'')+'</div>';
    if(s.in&&s.in.length){h+='<div class="sio"><span class="iol">IN</span>';
      for(var a=0;a<s.in.length;a++)h+=_chip(s.in[a],'io-in');h+='</div>';}
    if(s.out&&s.out.length){h+='<div class="sio"><span class="iol">OUT</span>';
      for(var b=0;b<s.out.length;b++)h+=_chip(s.out[b],'io-out');h+='</div>';}
    h+='</div>';
  }
  h+='</div>';
  document.getElementById('fbody').innerHTML=h;
  _fmodal.classList.add('open');
}
function closeF(){_fmodal.classList.remove('open');}
"""


def _stepper_html(model):
    """Stepper superior: fase actual, % de progreso por HU y checks de gates (v2.14).

    El progreso se mide en historias cerradas/abiertas (no en gates): soporta
    alcances que crecen y productos en evolución continua — el backlog es la
    verdad del avance; los gates muestran el estado del proceso, no el progreso.
    """
    import html as _html
    esc = _html.escape
    hu = model["contadores"].get("hu")
    if hu and hu["total"]:
        pct = round(100 * hu["cerradas"] / hu["total"])
        pct_label = f'{hu["cerradas"]}/{hu["total"]} HU'
    else:
        gates_ok = sum(1 for g in (1, 3, 5, 6)
                       if (model["gate_status"].get(str(g)) or {}).get("estado") == "ok")
        pct = round(100 * gates_ok / 4)
        pct_label = f"{gates_ok}/4 gates"
    cur = model["fase_actual"]
    cur_title = next(m["title"] for m in MACRO if m["id"] == cur)
    steps = ""
    for m in MACRO:
        st = (model["gate_status"].get(str(m["id"])) or {}).get("estado")
        done = st == "ok" if st else m["id"] < cur
        is_cur = m["id"] == cur
        dot_style = ("background:#22c55e;border-color:#22c55e;color:#052e1b" if done and not is_cur
                     else "background:#1e293b;border-color:#3b82f6;box-shadow:0 0 0 5px rgba(59,130,246,.25)" if is_cur
                     else "background:#1e293b;border-color:#475569")
        mark = "✓" if done and not is_cur else str(m["id"])
        steps += (f'<div data-fase="{m["id"]}" title="Ver skills, entradas y salidas de la fase" '
                  f'style="flex:1;text-align:center;position:relative;cursor:pointer">'
                  f'<div style="width:30px;height:30px;border-radius:50%;margin:0 auto;border:2px solid #475569;'
                  f'display:flex;align-items:center;justify-content:center;font-size:.8rem;font-weight:700;{dot_style}">{mark}</div>'
                  f'<div style="font-size:.68rem;color:#94a3b8;margin-top:.3rem">{esc(m["title"])}</div></div>')
    # Ciclos ejecutados (recorridos históricos de cada loop del pipeline)
    loop_names = {"4->4": "sprints", "5->4": "bugs QA→TDD", "6->4": "hotfixes",
                  "3->4": "replans", "6->1": "impact-reports"}
    counts = model.get("loops_count", {})
    chips = "".join(
        f'<span class="badge {"st-ok" if counts.get(k) else "st-otro"}">{v} ×{counts.get(k, 0)}</span>'
        for k, v in loop_names.items())
    return f"""
<div style="display:flex;align-items:baseline;justify-content:space-between;flex-wrap:wrap;gap:.5rem;margin-bottom:.8rem">
  <div><span style="font-size:1.25rem;font-weight:700">Fase {cur}: {esc(cur_title)}</span>
       <span style="color:#94a3b8;font-size:.8rem;margin-left:.6rem">estás aquí</span></div>
  <div style="font-size:.85rem;color:#94a3b8">PROGRESO (HU cerradas):
       <span style="font-size:1.15rem;font-weight:700;color:#22c55e">{pct}%</span>
       <span style="font-size:.75rem;color:#64748b"> · {esc(pct_label)}</span></div>
</div>
<div style="background:#1e293b;border-radius:6px;height:8px;margin-bottom:.6rem">
  <div style="background:linear-gradient(90deg,#3b82f6,#22c55e);height:8px;border-radius:6px;width:{pct}%"></div>
</div>
<div style="font-size:.72rem;color:#94a3b8;margin-bottom:1rem">Ciclos ejecutados: {chips}</div>
<div style="display:flex;gap:.2rem">{steps}</div>
"""


def _dashboard_blocks(model):
    """Bloques HTML del portal del proyecto (v2.20): antes era el dashboard
    monolítico; ahora cada bloque se publica como página del portal (emit_portal)."""
    import html as _html
    esc = _html.escape
    c = model["contadores"]

    adrs_count = model.get("adrs") or []
    adr_adopted = sum(1 for a in adrs_count
                      if "adopt" in a["status"].lower() or "acept" in a["status"].lower())
    radar_model = model.get("radar")
    radar_total = sum(radar_model["counts"].values()) if radar_model else None
    tok = model.get("tokens") or {}
    tok_kpi = None
    if tok.get("cobertura") is not None:
        tok_kpi = f'{tok["cobertura"]}%'
        if tok.get("alerta"):
            tok_kpi += " ⚠"
    kpis = [("Sprints completados", c["sprints"]),
            ("Releases (GATE 3)", c["releases"]),
            ("HU cerradas", f'{c["hu"]["cerradas"]}/{c["hu"]["total"]}' if c["hu"] else None),
            ("Recibos vigentes", c["recibos_vigentes"]),
            ("Recibos invalidados", c["recibos_rehechos"]),
            ("Gates al primer intento", f'{c["gates_1er"]}%' if c["gates_1er"] is not None else None),
            ("Tokens medidos (cobertura)", tok_kpi),
            ("HUs con orden TDD en commits",
             f'{model["tdd"]["ok"]}/{model["tdd"]["total"]}' if model.get("tdd") else None),
            ("ADRs (adoptadas)", f"{adr_adopted}/{len(adrs_count)}" if adrs_count else None),
            ("Tecnologías en radar", radar_total)]
    kpi_html = "".join(
        f'<div class="kpi"><div class="v">{esc(str(v))}</div><div class="k">{esc(k)}</div></div>'
        for k, v in kpis if v is not None) or '<div class="empty">Sin datos aún — el dashboard se llena con los primeros recibos.</div>'

    # Gobernanza (v2.23): contadores re-derivados de spec/audit/events.jsonl.
    # La promesa "auditable" deja de ser invisible — revocaciones con fuente.
    audit = model.get("auditoria")
    if audit:
        cadena = ('<span style="color:var(--ok)">✓ íntegra</span>' if audit["cadena_ok"]
                  else '<span style="color:var(--bad)">✗ rota</span>')
        gob_html = (
            '<div class="kpis">'
            f'<div class="kpi"><div class="v">{audit["emits"]}</div><div class="k">Recibos emitidos</div></div>'
            f'<div class="kpi"><div class="v">{audit["n_revocaciones"]}</div><div class="k">Revocaciones</div></div>'
            f'<div class="kpi"><div class="v">{audit["total"]}</div><div class="k">Eventos de auditoría</div></div>'
            f'<div class="kpi"><div class="v">{len(audit["aprobadores"])}</div><div class="k">Aprobadores humanos</div></div>'
            + "</div>"
            + f'<div style="font-size:.75rem;color:var(--muted)">Cadena de hash: {cadena}'
              f' · último evento {esc(audit["ultimo_ts"][:19])}'
              f' · harness {esc("/".join(audit["versiones"]) or "?")}</div>')
    else:
        gob_html = ('<div class="empty">Sin memoria de auditoría — inicializar con '
                    '<code>init_project.py</code> o <code>audit_log.py init</code>. '
                    'Sin auditoría no hay gate (v2.22).</div>')

    # Histórico completo por fecha (timestamps de recibos): cubre los sprints
    # anteriores al primer sprint-review — los recibos no mienten sobre cuándo pasó algo.
    timeline = model.get("timeline") or []
    hist_html = ""
    if len(timeline) >= 2:
        step = max(1, len(timeline) // 8)          # máximo ~8 etiquetas en el eje X
        xl = [t["fecha"][5:] if i % step == 0 or i == len(timeline) - 1 else ""
              for i, t in enumerate(timeline)]
        hist_html = ('<h3 style="font-size:.78rem;color:#94a3b8;margin:0 0 .3rem">'
                     'Histórico completo por fecha (derivado de los recibos — incluye los sprints sin review)</h3>'
                     + _svg_line_chart(
                         [("artefactos aprobados (acum)", [t["aprobados"] for t in timeline]),
                          ("retrabajo (acum)", [t["rehechos"] for t in timeline]),
                          ("% 1er intento (acum)", [t["gates_1er"] for t in timeline])],
                         xl, lambda v: f"{v:.0f}")
                     + '<div style="font-size:.7rem;color:#475569;margin-bottom:1rem">Los recibos no llevan etiqueta '
                       'de sprint: los puntos anteriores al primer sprint-review son la historia real por fecha, no por sprint.</div>')

    # Tendencias: lead time y retrabajo por sprint (serie de sprint-review-NN.md)
    alert = ""
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
        # Visualización de tendencias: con <3 sprints las líneas no informan —
        # tarjetas de delta vs sprint anterior; desde el sprint 3, gráficas de línea.
        if len(model["tendencias"]) < 3:
            cur, prev = model["tendencias"][-1], (model["tendencias"][-2] if len(model["tendencias"]) > 1 else {})
            cards = '<div class="kpis">'
            cards += _delta_card("Gates al primer intento", prev.get("gates_1er"), cur["gates_1er"],
                                 lambda v: f"{v:.0f}%")
            cards += _delta_card("Artefactos vigentes", prev.get("artefactos"), cur["artefactos"],
                                 lambda v: f"{v:.0f}")
            cards += _delta_card("Retrabajo (rehechos)", prev.get("rehechos"), cur["rehechos"],
                                 lambda v: f"{v:.0f}", invertir=True)
            for g in gates_lt:
                cards += _delta_card(f"Lead time {g}", prev["lead"].get(g), cur["lead"].get(g),
                                     _fmt_span, invertir=True)
            charts = (cards + '</div><div class="empty" style="margin-top:.6rem">Las gráficas de línea '
                              'por fecha aparecen desde el tercer sprint review — con 1-2 puntos no muestran tendencia.</div>')
        else:
            xlabels = [(s.get("fecha") or f'S{s["sprint"]}')[5:] for s in model["tendencias"]]
            charts = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:1rem;margin-bottom:1rem">'
            charts += ('<div><h3 style="font-size:.78rem;color:#94a3b8;margin:0 0 .3rem">Lead time por gate</h3>'
                       + _svg_line_chart([(g, [s["lead"].get(g) for s in model["tendencias"]]) for g in gates_lt],
                                         xlabels, _fmt_span) + "</div>")
            charts += ('<div><h3 style="font-size:.78rem;color:#94a3b8;margin:0 0 .3rem">Gates al primer intento</h3>'
                       + _svg_line_chart([("% 1er intento", [s["gates_1er"] for s in model["tendencias"]])],
                                         xlabels, lambda v: f"{v:.0f}%") + "</div>")
            charts += ('<div><h3 style="font-size:.78rem;color:#94a3b8;margin:0 0 .3rem">Retrabajo y artefactos vigentes</h3>'
                       + _svg_line_chart([("rehechos", [s["rehechos"] for s in model["tendencias"]]),
                                          ("artefactos vigentes", [s["artefactos"] for s in model["tendencias"]])],
                                         xlabels, lambda v: f"{v:.0f}") + "</div></div>")
        trends = (hist_html + charts
                  + f"<table><tr><th>Sprint</th>{''.join(f'<th>{esc(g)}</th>' for g in gates_lt)}"
                    f"<th>Retrabajo</th><th>Artefactos vigentes</th><th>Gates 1er intento</th></tr>{rows}</table>{alert}")
    else:
        trends = (hist_html
                  + '<div class="empty">Sin sprint reviews aún — la tabla de tendencias aparece desde el primer <code>sprint_review.py</code>.</div>')

    # Tiempos de fase y de ciclo (v2.14): tabla + barras, todo derivado de
    # timestamps de recibos y fechas de cierre de los sprint reviews.
    tiempos = model.get("tiempos") or {}
    fases_t, ciclos_t = tiempos.get("fases") or [], tiempos.get("ciclos") or []
    MACRO_TITLE = {m["id"]: m["title"] for m in MACRO}
    t_html = ""
    if any("cierre_dia" in f for f in fases_t):
        rows = ""
        for f in fases_t:
            tit = f'Fase {f["macro"]} · {MACRO_TITLE.get(f["macro"], "")}'
            if "cierre_dia" not in f:
                rows += (f'<tr><td><b>{esc(f["gate"])}</b></td><td>{esc(tit)}</td>'
                         f'<td colspan="4" style="color:#64748b">sin recibos aún</td></tr>')
                continue
            rows += (f'<tr><td><b>{esc(f["gate"])}</b></td><td>{esc(tit)}</td>'
                     f'<td>{esc(f["apertura"])}</td><td>{esc(f["cierre"])}</td>'
                     f'<td>{_fmt_span(f["trabajo_min"])}</td><td><b>día {f["cierre_dia"]:g}</b></td></tr>')
        t_html += ('<h3 style="font-size:.78rem;color:#94a3b8;margin:0 0 .3rem">Trabajo dentro de cada gate (primer → último recibo del gate)</h3>'
                   + _svg_barh([(f["gate"], f.get("trabajo_min")) for f in fases_t], _fmt_span)
                   + "<table><tr><th>Gate</th><th>Fase</th><th>Apertura</th><th>Cierre</th>"
                     "<th>Trabajo en el gate</th><th>Cierre (día del proyecto)</th></tr>"
                   + rows + "</table>")
    if any(c.get("dias") is not None for c in ciclos_t):
        rows = ""
        for c in ciclos_t:
            if c.get("dias") is None:
                rows += f'<tr><td><b>Sprint {c["sprint"]}</b></td><td colspan="3" style="color:#64748b">sin fecha de cierre</td></tr>'
                continue
            d = c["dias"]
            rows += (f'<tr><td><b>Sprint {c["sprint"]}</b></td><td>{esc(c.get("desde") or "inicio")} → {esc(c["cierre"])}</td>'
                     f'<td><b>{d} día{"s" if d != 1 else ""}</b></td></tr>')
        t_html += ('<h3 style="font-size:.78rem;color:#94a3b8;margin:1.2rem 0 .3rem">Duración de cada ciclo (sprint)</h3>'
                   + _svg_barh([(f'S{c["sprint"]}', c.get("dias")) for c in ciclos_t],
                               lambda v: f"{v:.0f} d", color="#22c55e")
                   + "<table><tr><th>Ciclo</th><th>Periodo</th><th>Duración</th></tr>" + rows + "</table>")
    if not t_html:
        t_html = '<div class="empty">Sin datos de tiempo aún — aparecen con los primeros recibos y sprint reviews.</div>'

    if model["aprendizajes"]:
        learns = "".join(f'<div class="learn">📚 {esc(t)}</div>' for t in model["aprendizajes"])
    else:
        learns = '<div class="empty">Sin memorias learning registradas.</div>'

    if model.get("sesiones"):
        sess = "".join(
            f'<div class="learn">🕓 <b>{esc(s["id"])}</b><br>'
            f'<span style="color:#94a3b8">hecho:</span> {esc(s["done"])}<br>'
            f'<span style="color:#94a3b8">sigue:</span> {esc(s["next"])}</div>'
            for s in model["sesiones"])
    else:
        sess = '<div class="empty">Sin handoffs de sesión — cerrar con mem.py session end.</div>'

    # Detalle por fase: ahora vive en el popup (clic en nodos del grafo o del
    # stepper) — los datos viajan incrustados como JSON para el modal.
    import json as _json
    def _js(obj):
        return _json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")
    modal_data = ("<script>const FASES=" + _js(model.get("fases_detalle") or [])
                  + ";const ARTS=" + _js(model.get("artefactos_por_fase") or {})
                  + ";const HREFS=" + _js(model.get("artefactos_href") or {})
                  + ";</script><script>" + MODAL_JS + "</script>")

    # Decisiones: ADRs (estado + Risk Tier) y Tech Radar por cuadrante (v2.13);
    # v2.20.1: filas y blips vinculados por tecnología (clic resalta el par).
    radar = model.get("radar")
    tech_keys = []
    if radar:
        tech_keys = sorted({_norm_tech(t) for ts in radar["techs"].values() for t in ts} - {""})
    adrs = model.get("adrs") or []
    if adrs:
        def st_class(s):
            s = s.lower()
            if "adopt" in s or "acept" in s:
                return "st-ok"
            if "prop" in s:
                return "st-prop"
            if "superseded" in s or "diferid" in s:
                return "st-sup"
            return "st-otro"
        rows = ""
        for a in adrs:
            tier_badge = (f'<span class="badge tier">Tier {a["tier"]}</span>'
                          if a["tier"] else "-")
            tnorm = _norm_tech(a["title"])
            keys = " ".join(k for k in tech_keys if k and k in tnorm)
            rows += (f'<tr class="adr-row" data-tech="{keys}" '
                     f'title="Clic para resaltar la tecnología en el radar (y viceversa)">'
                     f'<td><b>{esc(a["id"])}</b></td><td>{esc(a["title"])}</td>'
                     f'<td><span class="badge {st_class(a["status"])}">{esc(a["status"])}</span></td>'
                     f'<td>{tier_badge}</td></tr>')
        adr_html = (f"<table><tr><th>ADR</th><th>Decisión</th><th>Estado</th><th>Risk Tier</th></tr>{rows}</table>")
    else:
        adr_html = '<div class="empty">Sin ADRs en <code>spec/adr/</code> — las decisiones de 8 pasos aparecerán aquí.</div>'
    radar_html = ""
    if radar:
        qcolor = {"ADOPT": "#22c55e", "TRIAL": "#3b82f6", "ASSESS": "#f59e0b", "HOLD": "#ef4444"}
        radar_html = ('<div id="radar">'
                      + _radar_chart_svg(radar["techs"])
                      + '<div class="quad">'
                      + "".join(f'<div class="kpi"><div class="v" style="color:{qcolor[q]}">{radar["counts"][q]}</div>'
                                f'<div class="k">{q}</div></div>' for q in ("ADOPT", "TRIAL", "ASSESS", "HOLD"))
                      + "</div></div>"
                      + '<div class="radar-note">Clic en un ADR para resaltar su tecnología en el radar; '
                        'clic en una tecnología para resaltar sus ADRs.</div>'
                      + RADAR_LINK_JS)

    gloss = "".join(f'<tr><td style="white-space:nowrap"><b>{esc(t)}</b></td><td>{esc(d)}</td></tr>'
                    for t, d in GLOSARIO)

    pipeline = (_stepper_html(model) + _dash_graph_svg(model)
                + '<div class="legend"><span class="lg-ok">gate con recibo vigente</span>'
                  '<span class="lg-warn">recibo invalidado / retrabajo</span>'
                  '<span class="lg-none">sin recibo aún</span><span class="lg-cur">fase actual</span>'
                  '<span style="color:var(--muted)">clic en una fase (grafo o stepper) para ver sus skills, '
                  'entradas y salidas · loops tenues: pasa el cursor para ver su nombre</span></div>'
                + MODAL_HTML + modal_data)
    return {
        "pipeline": pipeline,
        "acumulado": f'<div class="kpis">{kpi_html}</div>',
        "tendencias": trends,
        "tiempos": t_html,
        "adrs": adr_html,
        "radar": radar_html,
        "aprendizajes": learns,
        "sesiones": sess,
        "glosario": f"<table>{gloss}</table>",
        "alerta": alert,
        "gobernanza": gob_html,
    }


_NOTA_DERIVADO = ("Artefacto derivado de receipts/ + spec/ + sprint-review-NN.md (ADR-002) — "
                  "no editar a mano; regenerar: harness_graph.py --proyecto .")


def emit_portal(model, spec_dir):
    """Emite las páginas del portal (spec/portal/paginas/) y las registra.

    Pocas páginas, densas (v2.20.1): info relacionada en la misma pantalla.
    Modular: cada página es un archivo independiente y cada generador registra
    solo lo suyo; rebuild_index() (lo llama main_proyecto) reescribe el menú,
    el buscador y el shell a partir del registry. Devuelve el nº de páginas
    emitidas/registradas en esta pasada.
    """
    import glob as _g
    import html as _html
    import portal_lib
    esc = _html.escape
    pag = portal_lib.paginas_dir(spec_dir)
    os.makedirs(pag, exist_ok=True)
    # Limpieza de las páginas propias de corridas anteriores (artefactos
    # derivados; docs/ lo limpia mdview). El registry poda entradas huérfanas.
    for viejo in _g.glob(os.path.join(pag, "*.html")):
        os.remove(viejo)
    blocks = _dashboard_blocks(model)
    alerta = blocks.get("alerta", "")
    sub = (f'<div class="sub">Portal del proyecto · arnés v{esc(model.get("harness_version", "?"))} · '
           f'generado {esc(model["generado"])}</div>')

    # Sweep de diagramas vivos (spec/diagrams/*.html): la página de
    # Arquitectura los enlaza. Si diagram_ir ya los registró con texto rico,
    # register() conserva ese texto (merge).
    diags = []
    for p in sorted(_g.glob(os.path.join(spec_dir, "diagrams", "*.html"))):
        name = os.path.basename(p)
        titulo = os.path.splitext(name)[0]
        tipo = ""
        ir = p[:-len(".html")] + ".ir.json"
        if os.path.isfile(ir):
            try:
                import json as _j
                ir_doc = _j.load(open(ir, encoding="utf-8"))
                titulo = ir_doc.get("titulo", titulo) or titulo
                tipo = ir_doc.get("tipo") or ""
            except Exception:
                pass
        pid = portal_lib.register(spec_dir, origen="harness_graph", kind="diagrama",
                                  ruta="../diagrams/" + name, titulo=titulo,
                                  categoria=("auditoria" if name == "grafo-codigo.html"
                                             else None),
                                  grupo=("codigo" if name == "grafo-codigo.html"
                                         else "diagramas"))
        diags.append((pid, titulo,
                      "codigo" if name == "grafo-codigo.html" else (tipo or "general")))

    # Cards agrupadas por tipo de diagrama: header = tipo + cantidad, cuerpo =
    # enlaces a los n diagramas del tipo, footer = línea de color del tipo.
    _DIAG_COLOR = {
        "architecture": "#3b82f6", "context": "#0ea5e9", "container": "#2563eb",
        "component": "#6366f1", "deployment": "#8b5cf6", "dataflow": "#06b6d4",
        "workflow": "#22c55e", "lifecycle": "#84cc16", "sequence": "#f59e0b",
        "er": "#ec4899", "capability-map": "#a855f7", "stakeholder": "#14b8a6",
        "threat-model": "#ef4444", "codigo": "#10b981", "general": "#94a3b8",
    }
    if diags:
        grupos = {}
        for pid, t, tipo in diags:
            grupos.setdefault(tipo, []).append((pid, t))
        cards = []
        for tipo in sorted(grupos, key=lambda k: (-len(grupos[k]), k)):
            items = grupos[tipo]
            color = _DIAG_COLOR.get(tipo, _DIAG_COLOR["general"])
            links = "".join(
                f'<a href="../index.html#/id/{esc(pid)}" target="_top">{esc(t)}</a>'
                for pid, t in items)
            cards.append(
                f'<div class="dcard" style="--dcard-c:{color}">'
                f'<div class="dcard-head"><b>{esc(tipo)}</b>'
                f'<span class="n">{len(items)} diagrama{"s" if len(items) != 1 else ""}</span></div>'
                f'<div class="dcard-links">{links}</div>'
                f'<div class="dcard-foot"></div></div>')
        diag_cards = '<div class="diag-cards">' + "".join(cards) + "</div>"
    else:
        diag_cards = ('<div class="empty">Sin diagramas en <code>spec/diagrams/</code> — '
                      'los diagramas vivos IR aparecerán aquí (skill sdlc-diagrams).</div>')

    # Página de Auditoría (v2.23): 100% derivada de spec/audit/events.jsonl
    audit = model.get("auditoria")
    if audit:
        _ICONO = {"emit": "✅", "revoke": "↩️", "invalidado": "⚠️", "arch_lint": "🛡",
                  "contract_diff": "📜", "bootstrap": "🚀", "audit_init": "🌱",
                  "use": "▸", "gate": "🚪"}
        tl_rows = "".join(
            f'<tr><td style="white-space:nowrap">{esc(e.get("ts", "")[:19])}</td>'
            f'<td>{_ICONO.get(e.get("evento", ""), "·")} {esc(e.get("evento", ""))}</td>'
            f'<td>{esc(e.get("artefacto", "") or e.get("nota", "") or "")}</td>'
            f'<td>{esc(e.get("gate", ""))}</td><td>{esc(e.get("rol", ""))}</td>'
            f'<td><b>{esc(e.get("approved_by", ""))}</b></td>'
            f'<td style="font-size:.7rem;color:var(--muted)">{esc(e.get("harness_version", ""))}</td></tr>'
            for e in audit["eventos_recientes"])
        rev_rows = "".join(
            f'<tr><td><code>{esc(e.get("artefacto", ""))}</code></td>'
            f'<td>{esc(e.get("reason", ""))}</td>'
            f'<td>{esc(e.get("relation", ""))}</td>'
            f'<td>{esc(e.get("ts", "")[:19])}</td>'
            f'<td><b>{esc(e.get("approved_by", ""))}</b></td></tr>'
            for e in audit["revocaciones"])
        cadena = ('<span style="color:var(--ok)">✓ íntegra</span>' if audit["cadena_ok"]
                  else '<span style="color:var(--bad)">✗ rota — revisar con audit_verify.py</span>')
        audit_body = ("<h1>🛡 Auditoría</h1>" + sub
                      + f'<div class="panel"><h2>Salud de la cadena</h2>{blocks["gobernanza"]}'
                        f'<p style="font-size:.78rem;color:var(--muted)">Verificación estructural: '
                        f'cadena de hash {cadena} · {audit["total"]} eventos · '
                        f'hash de cierre <code>{esc(audit["ultimo_hash"][:16])}…</code></p></div>'
                      + '<h2>Revocaciones e invalidaciones</h2>'
                      + (f'<div class="panel"><table><tr><th>Artefacto</th><th>Motivo</th>'
                         f'<th>Relación</th><th>Fecha</th><th>Aprobado por</th></tr>{rev_rows}</table></div>'
                         if rev_rows else
                         '<div class="empty">Sin revocaciones registradas — cuando un recibo se revoque, '
                         'quedará aquí con motivo y aprobador.</div>')
                      + '<h2>Línea de tiempo de eventos</h2>'
                      + f'<div class="panel"><table><tr><th>Fecha (UTC)</th><th>Evento</th>'
                        f'<th>Artefacto / nota</th><th>Gate</th><th>Rol</th><th>Aprobador</th>'
                        f'<th>Harness</th></tr>{tl_rows}</table></div>')
    else:
        audit_body = ("<h1>🛡 Auditoría</h1>" + sub
                      + '<div class="empty">Este proyecto aún no tiene memoria de auditoría '
                        '(<code>spec/audit/events.jsonl</code>). Inicialízala con '
                        '<code>init_project.py</code> o <code>audit_log.py init</code> — '
                        'sin auditoría no hay gate (v2.22).</div>')

    paginas = [
        # Inicio: de entrada, cómo va el proyecto (pipeline compacto + acumulado + gobernanza)
        ("inicio.html", f'Inicio — {model["proyecto"]}',
         f'<h1>🏠 {esc(model["proyecto"])}</h1>' + sub + alerta
         + '<div class="panel graph-wrap"><h2>Pipeline — estado actual</h2>'
         + blocks["pipeline"] + "</div>"
         + "<h2>Acumulado del proyecto</h2>" + blocks["acumulado"]
         + '<h2>🛡 Gobernanza</h2><div class="panel">' + blocks["gobernanza"] + "</div>",
         "inicio", "inicio", "", "home resumen pipeline fase progreso kpis gobernanza auditoría"),
        # Auditoría: quién aprobó qué, cuándo, con qué versión del arnés (v2.23)
        ("gobernanza-auditoria.html", "Auditoría — trazabilidad de decisiones",
         audit_body,
         "metrica", "auditoria", "",
         "auditoría eventos revocaciones recibos aprobador cadena hash harness trazabilidad"),
        # Métricas: tendencias + tiempos en dos columnas (densidad sin scroll)
        ("metricas.html", "Métricas del proyecto",
         "<h1>📊 Métricas del proyecto</h1>" + sub
         + '<div class="dense2"><div class="panel"><h2>Tendencias por sprint</h2>' + blocks["tendencias"]
         + '</div><div class="panel"><h2>Tiempos de fase y de ciclo</h2>' + blocks["tiempos"]
         + "</div></div>",
         "metrica", "agilidad", "",
         "lead time retrabajo gates primer intento gráficas duración ciclos sprints cierre apertura"),
        # Arquitectura: diagramas vivos + ADRs ↔ Tech Radar vinculados
        ("arquitectura.html", "Arquitectura — diagramas y decisiones",
         "<h1>🏛 Arquitectura</h1>" + sub
         + "<h2>Diagramas del proyecto</h2>" + diag_cards
         + '<div class="dense2eq"><div class="panel"><h2>ADRs — decisiones gobernadas</h2>' + blocks["adrs"]
         + '</div><div class="panel"><h2>Tech Radar (paved roads)</h2>' + blocks["radar"] + "</div></div>",
         "metrica", "arquitectura", "",
         "adr risk tier tech radar adopt trial assess hold diagramas c4 decisiones"),
        # Memoria: aprendizajes + sesiones lado a lado (subgrupo de Auditoría)
        ("memoria.html", "Memoria del proyecto",
         "<h1>🧠 Memoria del proyecto</h1>" + sub
         + '<div class="dense2eq"><div class="panel"><h2>📚 Aprendizajes recientes</h2>' + blocks["aprendizajes"]
         + '</div><div class="panel"><h2>🕓 Últimas sesiones (handoffs)</h2>' + blocks["sesiones"] + "</div></div>",
         "doc", "auditoria", "memoria", "memorias learning lecciones handoff sesión contexto mem.py"),
    ]
    n = 0
    for fname, titulo, body, kind, cat, grupo, tags in paginas:
        pid = portal_lib.slug("paginas/" + fname)
        out = portal_lib.page_wrap(titulo, body, page_id=pid, extra_css=DASH_CSS, note=_NOTA_DERIVADO)
        open(os.path.join(pag, fname), "w", encoding="utf-8", newline="\n").write(out)
        portal_lib.register(spec_dir, origen="harness_graph", kind=kind,
                            ruta="paginas/" + fname, titulo=titulo, categoria=cat,
                            grupo=grupo, tags=tags.split(), texto=body)
        n += 1

    # Glosario: página oculta — se abre desde el topbar (📖) o el buscador
    pid = portal_lib.slug("paginas/negocio-glosario.html")
    out = portal_lib.page_wrap("Glosario del arnés", "<h1>📖 Glosario del arnés</h1>" + blocks["glosario"],
                               page_id=pid, extra_css=DASH_CSS, note=_NOTA_DERIVADO)
    open(os.path.join(pag, "negocio-glosario.html"), "w", encoding="utf-8", newline="\n").write(out)
    portal_lib.register(spec_dir, origen="harness_graph", kind="doc",
                        ruta="paginas/negocio-glosario.html", titulo="Glosario del arnés",
                        categoria="negocio",
                        tags="gate recibo risk tier adr drift loop lead time".split(),
                        texto=blocks["glosario"], oculto=True)
    portal_lib.set_topbar(spec_dir, [{"id": pid, "icono": "📖", "titulo": "Glosario"}])
    return n + 1 + len(diags)


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

    # spec/dashboard.html queda como redirect al portal (v2.20) pero conserva
    # el comentario dashboard-state: --check sigue comparando lo mismo.
    import html as _html
    html = ("<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'>"
            "<meta http-equiv='refresh' content='0; url=portal/index.html'>"
            f"<title>Portal — {_html.escape(model['proyecto'])}</title></head>"
            "<body style='font-family:system-ui;background:#0b1220;color:#e2e8f0;padding:3rem'>"
            "<p>El dashboard ahora es el <a href='portal/index.html' style='color:#58a6ff'>"
            "portal del proyecto</a> — redirigiendo…</p></body></html>\n"
            "<!-- dashboard-state: __STATE__ -->\n").replace("__STATE__", state_json)
    open(out, "w", encoding="utf-8", newline="\n").write(html)
    # Portal único del proyecto (v2.20): páginas de métricas + docs (mdview) +
    # sweep de diagramas → registry, y un solo rebuild del índice/shell.
    # Derivado, best-effort: nunca bloquea el dashboard.
    try:
        import portal_lib, mdview
        # Grafo de código (v2.27): si el proyecto tiene índice code_intel,
        # su vista interactiva (grafo-codigo, tema compartido con el portal)
        # se regenera ANTES del sweep de diagramas — queda registrada en
        # Auditoría y Trazabilidad (subgrupo "codigo") en esta misma pasada.
        cg_msg = ""
        try:
            import code_graph
            r = code_graph.emit_views(project_dir)
            if r:
                cg_msg = f" · grafo código: {r[2]} archivos, {r[3]} aristas"
        except Exception as e:
            cg_msg = f" · grafo código OMITIDO ({e})"
        emit_portal(model, spec_dir)
        n_docs = mdview.build(spec_dir)
        n_items = portal_lib.rebuild_index(spec_dir, proyecto=model["proyecto"],
                                           harness_version=model.get("harness_version", "?"))
        portal_msg = f" · portal: {n_items} páginas ({n_docs} docs){cg_msg}"
    except Exception as e:
        portal_msg = f" · portal OMITIDO ({e})"
    print(f"Dashboard generado: {out} (redirect → portal/index.html)")
    print(f"  fase actual: {model['fase_actual']} · sprints: {model['contadores']['sprints']} "
          f"· recibos vigentes: {model['contadores']['recibos_vigentes']}{portal_msg}")
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
