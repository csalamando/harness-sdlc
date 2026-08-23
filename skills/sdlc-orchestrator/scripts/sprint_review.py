#!/usr/bin/env python3
"""sprint_review.py — Sprint Review: reporte versionado de cierre de sprint (v2.5).

Se genera en Fase 8 (Archivo) y queda versionado en spec/reports/ — un archivo
por sprint, lo que habilita TENDENCIAS entre sprints (la mejora basada en datos
necesita serie historica, no solo el estado actual).

Secciones (todo derivado de fuentes gobernadas; cero narracion del agente):
  1. Resumen ejecutivo      — periodo, artefactos, gates, alertas
  2. Avance del proyecto    — aprobados por gate, recibos invalidados/revocados
                              (trabajo rehecho), cobertura de la spec
  3. Desempeno del arnes    — aporte/cobertura/senales por skill (skill_metrics)
  4. Tiempos del pipeline   — lead time por gate segun timestamps de recibos
  5. Tendencia              — comparativa con el sprint review anterior
  6. Aprendizajes           — memorias learning del periodo + acciones propuestas

Relacion con otros artefactos:
  - spec/METRICS.md: tablero VIVO entre sprints (se sobrescribe).
  - spec/reports/sprint-review-NN.md: SNAPSHOT versionado por sprint (este).
  - spec/impact-report.md (product-analyst): impacto de NEGOCIO; se enlaza, no se duplica.

Uso: python3 sprint_review.py --sprint <N> [--spec-dir spec/] [--stdout]
Exit 0 siempre (herramienta informativa).
"""
import argparse
import collections
import datetime
import glob
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skill_metrics  # norm(), load_usage(), load_receipts(), EXPECTED, GATE_FASE


def lead_times(recs):
    """Minutos min/max entre el primer y ultimo recibo de cada gate."""
    por_gate = collections.defaultdict(list)
    for r in recs:
        try:
            ts = datetime.datetime.fromisoformat(r["emitido"])
            por_gate[r.get("gate", "?")].append(ts)
        except (KeyError, ValueError):
            pass
    rows = []
    for gate in sorted(por_gate):
        ts = sorted(por_gate[gate])
        delta = ts[-1] - ts[0]
        rows.append((gate, ts[0].date().isoformat(), ts[-1].date().isoformat(),
                     len(ts), str(delta)))
    return rows


def load_previous_review(spec_dir, sprint):
    """Extrae los KPIs del review del sprint anterior, si existe."""
    reps = sorted(glob.glob(os.path.join(spec_dir, "reports", "sprint-review-*.md")))
    prev = None
    for p in reps:
        m = re.search(r"sprint-review-(\d+)", p)
        if m and int(m.group(1)) < sprint:
            prev = p
    if not prev:
        return None, {}
    kpis = {}
    text = open(prev, encoding="utf-8", errors="replace").read()
    for key, pat in [
        ("artefactos", r"Artefactos aprobados:\s*(\d+)"),
        ("gates_1er", r"Gates al primer intento:\s*(\d+)%"),
        ("freestyle", r"Roles en freestyle:\s*(\d+)"),
        ("tokens", r"Tokens totales:\s*([\d,]+)"),
    ]:
        m = re.search(pat, text)
        if m:
            kpis[key] = m.group(1)
    return os.path.basename(prev), kpis


def count_learnings(spec_dir):
    d = os.path.join(spec_dir, "memory", "entries")
    n = 0
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.endswith(".md"):
                try:
                    head = open(os.path.join(d, f), encoding="utf-8", errors="replace").read(600)
                    if "type: learning" in head:
                        n += 1
                except OSError:
                    pass
    return n


def metrics_section(spec_dir):
    """Ejecuta skill_metrics report --stdout y devuelve el cuerpo (sin el titulo)."""
    sp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skill_metrics.py")
    r = subprocess.run([sys.executable, sp, "--spec-dir", spec_dir, "report", "--stdout"],
                       capture_output=True, text=True)
    body = r.stdout.strip()
    body = re.sub(r"^# METRICS[^\n]*\n", "", body)  # sin titulo (se integra como seccion)
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sprint", type=int, required=True)
    ap.add_argument("--spec-dir", default="spec/")
    ap.add_argument("--stdout", action="store_true")
    a = ap.parse_args()
    spec_dir = a.spec_dir

    recs = skill_metrics.load_receipts(spec_dir)
    events = skill_metrics.load_usage(spec_dir)
    vigentes = [r for r in recs if r.get("estado") == "vigente"]
    rehechos = [r for r in recs if r.get("estado") in ("invalidado", "revocado")]
    artefactos = len(vigentes)
    intentos = sum(int(r.get("attempts") or 1) for r in recs)
    gates_1er = round(100 * artefactos / max(len(recs), 1)) if recs else 0
    tok_rep = sum(int(r.get("tokens_in") or 0) + int(r.get("tokens_out") or 0)
                  for r in recs if r.get("tokens_src") == "reportado")
    tok_est = sum(int(r.get("tokens_in") or 0) + int(r.get("tokens_out") or 0)
                  for r in recs if r.get("tokens_src") == "estimado")
    tokens_tot = tok_rep + tok_est

    # freestyle: roles con recibos pero sin activacion
    roles_activados = {skill_metrics.norm(e["skill"]) for e in events}
    roles_con_recibo = {skill_metrics.norm(r.get("rol")) for r in recs if r.get("rol")}
    freestyle = roles_con_recibo - roles_activados

    hoy = datetime.date.today().isoformat()
    fechas = sorted(r.get("emitido", "")[:10] for r in recs if r.get("emitido"))
    periodo = f"{fechas[0]} → {fechas[-1]}" if fechas else hoy

    out = [
        f"# Sprint Review — Sprint {a.sprint:02d}",
        "",
        f"Generado: {hoy} | Periodo (recibos): {periodo}",
        "Cifras acumuladas al cierre del sprint (los recibos no llevan etiqueta de sprint);",
        "la tendencia de la seccion 5 compara estos snapshots entre sprints.",
        "",
        "<!-- KPIs para tendencia (no borrar, los lee sprint_review.py) -->",
        f"<!-- Artefactos aprobados: {artefactos} -->",
        f"<!-- Gates al primer intento: {gates_1er}% -->",
        f"<!-- Roles en freestyle: {len(freestyle)} -->",
        f"<!-- Tokens totales: {tokens_tot:,} -->",
        "",
        "## 1. Resumen ejecutivo",
        "",
        f"- Artefactos aprobados (recibos vigentes): **{artefactos}**",
        f"- Gates al primer intento: **{gates_1er}%** ({intentos} intentos / {len(recs)} recibos)",
        f"- Trabajo rehecho (recibos invalidados/revocados): **{len(rehechos)}**",
        f"- Activaciones de skills: **{len(events)}** | Roles en freestyle: **{len(freestyle)}**"
        + (f" ({', '.join(sorted(freestyle))})" if freestyle else ""),
        f"- Tokens: {tok_rep:,} reportados + {tok_est:,} estimados",
        f"- Memorias learning acumuladas: **{count_learnings(spec_dir)}**",
        "",
        "## 2. Avance del proyecto",
        "",
        "| Gate | Artefactos vigentes | Rehechos |",
        "|---|---|---|",
    ]
    por_gate_v = collections.Counter(r.get("gate") for r in vigentes)
    por_gate_r = collections.Counter(r.get("gate") for r in rehechos)
    for g in sorted(set(por_gate_v) | set(por_gate_r)):
        out.append(f"| {g} | {por_gate_v.get(g, 0)} | {por_gate_r.get(g, 0)} |")
    if not recs:
        out.append("| - | 0 | 0 |")
    out += [
        "",
        "> Recibos rehechos = aprobaciones que se invalidaron o revocaron (cambio de spec,",
        "> trabajo devuelto por un gate). Un numero creciente indica gates debiles o",
        "> change-requests frecuentes — revisar causas en la retro.",
        "",
        "## 3. Desempeno del arnes (metricas de skills)",
        "",
        metrics_section(spec_dir),
        "",
        "## 4. Tiempos del pipeline (lead time por gate)",
        "",
        "| Gate | Primer recibo | Ultimo recibo | Recibos | Span |",
        "|---|---|---|---|---|",
    ]
    for gate, d0, d1, n, delta in lead_times(recs):
        out.append(f"| {gate} | {d0} | {d1} | {n} | {delta} |")
    if not recs:
        out.append("| - | - | - | 0 | - |")

    prev_name, prev = load_previous_review(spec_dir, a.sprint)
    out += ["", "## 5. Tendencia vs sprint anterior", ""]
    if prev:
        out += [
            f"Comparativa con `{prev_name}`:",
            "",
            "| KPI | Sprint anterior | Este sprint |",
            "|---|---|---|",
            f"| Artefactos aprobados | {prev.get('artefactos', '-')} | {artefactos} |",
            f"| Gates al primer intento | {prev.get('gates_1er', '-')}% | {gates_1er}% |",
            f"| Roles en freestyle | {prev.get('freestyle', '-')} | {len(freestyle)} |",
            f"| Tokens totales | {prev.get('tokens', '-')} | {tokens_tot:,} |",
        ]
    else:
        out.append("Primer sprint con review — la tendencia se calcula desde el proximo.")
    out += [
        "",
        "## 6. Aprendizajes y acciones",
        "",
        "- Memorias `learning` guardadas este sprint: revisar con `mem.py search learning --brief`.",
        "- Acciones propuestas (derivadas de la seccion 3 — senales):",
        "  - Skills con rechazos repetidos → ajustar su SKILL.md/plantillas o el gate que falla.",
        "  - Costo por artefacto alto → aplicar contexto minimo (INDEX.md, code_intel, mem --brief).",
        "  - Freestyle detectado → reforzar `skill_metrics.py use` antes de activar cada rol.",
        "- Impacto de negocio: ver `spec/impact-report.md` (product-analyst), si aplica.",
        "",
    ]
    text = "\n".join(out)
    print(text)
    if not a.stdout:
        d = os.path.join(spec_dir, "reports")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, f"sprint-review-{a.sprint:02d}.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"Sprint review guardado: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
