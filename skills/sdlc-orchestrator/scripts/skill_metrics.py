#!/usr/bin/env python3
"""skill_metrics.py — telemetria de uso y aporte de las skills del arnes (v2.4).

Principio: la disciplina no se narra, se deriva. Responde tres preguntas sin
meter telemetria en el contexto del agente (cero tokens extra: escritura por
CLI en un comando que ya existe, lectura bajo demanda):

  1. APORTE   — que skill genero que artefactos, con que tasa de exito en
                gates (intentos por recibo) y cuantos tokens costo.
  2. COBERTURA — el agente trabajo A TRAVES de las skills o hizo freestyle?
                Cruza lo esperado por fase con las activaciones registradas:
                fase cerrada (recibos) sin activacion de la skill = trabajo
                fuera del arnes; activacion sin artefactos = skill de adorno.
  3. TOKENS   — por skill, separando fuente 'reportada' (telemetria exacta
                de la plataforma, p. ej. OTel de Claude Code) de 'estimada'
                (chars/4 calculado por receipt.py sin depender del agente).

Datos (dos fuentes ya gobernadas, nada nuevo que mantener):
  - spec/receipts/*.receipt.json  -> rol, gate, artefacto, tokens, intentos
  - spec/metrics/usage.jsonl      -> activaciones (append-only, versionable)

Uso:
  python3 skill_metrics.py use --skill backend-dev --fase 4 [--modo full-pipeline]
  python3 skill_metrics.py report [--spec-dir spec/] [--stdout]
Exit 0 siempre (herramienta informativa).
"""
import argparse
import collections
import datetime
import json
import os

# Fase -> roles cuya activacion se espera si esa fase produjo artefactos.
EXPECTED = {
    "-1": ["devops-engineer"],
    "0": ["product-owner", "business-analyst", "solution-architect", "cloud-pricing"],
    "1": ["business-analyst"],
    "2": ["ux-designer", "software-architect", "security-engineer"],
    "3": ["software-architect"],
    "4": ["backend-dev", "frontend-dev"],
    "5": ["qa-automation"],
    "6": ["devops-engineer", "cloud-engineer"],
    "7": ["sre", "product-analyst"],
}
# Gate -> fase aproximada (para ubicar recibos en el pipeline)
GATE_FASE = {"GATE 0": "0", "GATE 1": "3", "GATE 2": "5", "GATE 2.5": "5", "GATE 3": "6"}


def norm(skill):
    return skill.replace("sdlc-", "").strip()


def metrics_dir(spec_dir):
    d = os.path.join(spec_dir, "metrics")
    os.makedirs(d, exist_ok=True)
    return d


def load_usage(spec_dir):
    p = os.path.join(metrics_dir(spec_dir), "usage.jsonl")
    events = []
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return events


def load_receipts(spec_dir):
    d = os.path.join(spec_dir, "receipts")
    recs = []
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.endswith(".receipt.json"):
                try:
                    recs.append(json.load(open(os.path.join(d, f), encoding="utf-8")))
                except (json.JSONDecodeError, OSError):
                    pass
    return recs


def cmd_use(a):
    ev = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "tipo": "use",
        "skill": norm(a.skill),
        "fase": str(a.fase),
        "modo": a.modo or "",
    }
    p = os.path.join(metrics_dir(a.spec_dir), "usage.jsonl")
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
    print(f"ACTIVACION REGISTRADA: {ev['skill']} (fase {ev['fase']})")


def fmt_tokens(reported, estimated):
    parts = []
    if reported:
        parts.append(f"{reported:,} rep.")
    if estimated:
        parts.append(f"{estimated:,} est.")
    return " + ".join(parts) if parts else "-"


def cmd_report(a):
    spec_dir = a.spec_dir
    events = load_usage(spec_dir)
    recs = load_receipts(spec_dir)

    uses = collections.Counter(norm(e["skill"]) for e in events)
    fases_usadas = collections.defaultdict(set)
    for e in events:
        fases_usadas[str(e.get("fase", "?"))].add(norm(e["skill"]))

    # agregado por rol desde recibos
    por_rol = collections.defaultdict(lambda: {
        "artefactos": 0, "intentos": 0, "tok_rep": 0, "tok_est": 0, "gates": set()})
    for r in recs:
        rol = norm(r.get("rol") or "(sin rol)")
        agg = por_rol[rol]
        agg["artefactos"] += 1
        agg["intentos"] += int(r.get("attempts") or 1)
        if r.get("tokens_src") == "reportado":
            agg["tok_rep"] += int(r.get("tokens_in") or 0) + int(r.get("tokens_out") or 0)
        elif r.get("tokens_src") == "estimado":
            agg["tok_est"] += int(r.get("tokens_in") or 0) + int(r.get("tokens_out") or 0)
        agg["gates"].add(r.get("gate", "?"))

    skills = sorted(set(uses) | set(por_rol))
    out = [
        "# METRICS — aporte y disciplina de las skills",
        "",
        f"Generado: {datetime.datetime.now().isoformat(timespec='seconds')} — "
        f"activaciones: {sum(uses.values())}, recibos: {len(recs)}.",
        "Digest informativo: NO se inyecta en paquetes de contexto; consultar bajo demanda",
        "(el orquestador lo genera en Fase 8 y guarda las señales como memoria `learning`).",
        "",
        "## 1. Aporte por skill",
        "",
        "| Skill | Activaciones | Artefactos | Gates 1er intento | Tokens |",
        "|---|---|---|---|---|",
    ]
    if not skills:
        out.append("| (sin datos aun) | - | - | - | - |")
    for s in skills:
        agg = por_rol.get(s, {"artefactos": 0, "intentos": 0, "tok_rep": 0, "tok_est": 0})
        ok = "-"
        if agg["artefactos"]:
            pct = round(100 * agg["artefactos"] / max(agg["intentos"], 1))
            ok = f"{pct}%"
        out.append(f"| {s} | {uses.get(s, 0)} | {agg['artefactos']} | {ok} | "
                   f"{fmt_tokens(agg['tok_rep'], agg['tok_est'])} |")

    out += [
        "",
        "## 2. Cobertura: trabajo a traves de las skills o freestyle?",
        "",
        "Cruza fases con recibos emitidos contra las activaciones registradas.",
        "",
        "| Fase | Roles esperados | Activados | Artefactos con recibo | Diagnostico |",
        "|---|---|---|---|---|",
    ]
    # Atribucion: un recibo se atribuye a la fase donde el rol se ACTIVO (si se
    # activo); si el rol tiene recibos pero ninguna activacion, es FREESTYLE y
    # se ubica en la fase aproximada de su gate.
    fases_por_rol = collections.defaultdict(set)
    for e in events:
        fases_por_rol[norm(e["skill"])].add(str(e.get("fase", "?")))
    fases_con_recibos = collections.defaultdict(set)
    freestyle = set()
    for r in recs:
        rol = norm(r.get("rol") or "(sin rol)")
        if fases_por_rol.get(rol):
            fases_con_recibos[sorted(fases_por_rol[rol], key=lambda x: (len(x), x))[0]].add(rol)
        else:
            freestyle.add(rol)
            f = GATE_FASE.get(r.get("gate", ""), "?")
            fases_con_recibos[f].add(rol)
    n_alertas = len(freestyle)
    for fase in sorted(set(EXPECTED) | set(fases_con_recibos) | set(fases_usadas),
                       key=lambda x: (len(x), x)):
        esperados = EXPECTED.get(fase, [])
        activados = fases_usadas.get(fase, set())
        produjeron = fases_con_recibos.get(fase, set())
        if not esperados and not activados and not produjeron:
            continue
        diag = []
        # trabajo con recibo pero sin activacion registrada = freestyle
        sin_activar = produjeron & freestyle
        if sin_activar:
            diag.append(f"FREESTYLE: {', '.join(sorted(sin_activar))} produjo sin activarse")
        # activacion sin artefacto = skill de adorno
        sin_producir = activados - produjeron - {"orchestrator"}
        if sin_producir and produjeron:
            diag.append(f"adorno: {', '.join(sorted(sin_producir))} se activo sin producir")
        # fase esperada sin ninguna evidencia
        if not produjeron and not activados and esperados:
            diag.append("sin actividad")
        if not diag:
            diag.append("OK")
        out.append(f"| {fase} | {', '.join(esperados) or '-'} | "
                   f"{', '.join(sorted(activados)) or '-'} | "
                   f"{', '.join(sorted(produjeron)) or '-'} | {'; '.join(diag)} |")

    out += ["", "## 3. Senales", ""]
    senales = []
    for s in skills:
        agg = por_rol.get(s)
        if agg and agg["artefactos"] and agg["intentos"] > agg["artefactos"]:
            rechazos = agg["intentos"] - agg["artefactos"]
            senales.append(f"- **{s}**: {rechazos} rechazo(s) de gate — revisar su SKILL.md/plantillas "
                           f"o el gate que falla.")
        if agg and agg["tok_est"] + agg["tok_rep"] > 0:
            tot = agg["tok_est"] + agg["tok_rep"]
            if agg["artefactos"] and tot // agg["artefactos"] > 100_000:
                senales.append(f"- **{s}**: ~{tot // agg['artefactos']:,} tokens por artefacto — "
                               f"candidata a aplicar contexto minimo (INDEX.md, code_intel, mem --brief).")
    for s in uses:
        if s not in por_rol:
            senales.append(f"- **{s}**: se activo {uses[s]} vez/veces pero no tiene artefactos con recibo — "
                           f"verificar que este entregando en `spec/` y no trabajando fuera de la spec.")
    if n_alertas:
        senales.insert(0, f"- **DISCIPLINA**: {n_alertas} rol(es) produjeron artefactos sin registrar "
                          f"activacion — el agente esta trabajando sin pasar por la skill. "
                          f"Reforzar en el orquestador: `skill_metrics.py use` ANTES de activar cada rol.")
    if not senales:
        senales.append("- Sin senales: uso y aporte consistentes.")
    out += senales + [""]

    text = "\n".join(out)
    print(text)
    if not a.stdout:
        p = os.path.join(spec_dir, "METRICS.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"METRICS.md actualizado.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec-dir", default="spec/")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("use", help="registrar activacion de una skill (append-only)")
    p.add_argument("--skill", required=True)
    p.add_argument("--fase", required=True)
    p.add_argument("--modo", default="")
    p = sub.add_parser("report", help="generar spec/METRICS.md")
    p.add_argument("--stdout", action="store_true")
    a = ap.parse_args()
    {"use": cmd_use, "report": cmd_report}[a.cmd](a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
