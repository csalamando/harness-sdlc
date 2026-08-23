#!/usr/bin/env python3
"""pipeline_diagram.py — Diagrama del pipeline CI/CD DERIVADO de los workflows (v2.6).

Dirección: .github/workflows/*.yml → diagrama. Nunca se edita a mano:
se regenera desde la fuente y el humano APRUEBA el contenido con recibo
(receipt.py emit --role devops-engineer). El diagrama es mecanismo de
aceptación: un cambio de pipeline sin diagrama aprobado no está aceptado.

Python stdlib puro: parser del subset de YAML que usan los workflows de
GitHub Actions (no un YAML completo). Valida lo que actionlint no hace sin
binario externo:
  - needs: que apunta a un job inexistente (pipeline roto)
  - ciclos de dependencias entre jobs
  - jobs huérfanos (sin needs ni triggers claros — solo informativo)

Comandos:
  generate --workflows-dir .github/workflows --out spec/diagrams/pipeline-cicd.md
  validate --workflows-dir .github/workflows      # solo validación, exit 1 si roto
  check    (como generate)                        # exit 1 si el .md difiere (drift)

Salida: Markdown con un bloque ```mermaid flowchart por workflow + tabla de
validación. Renderizable con diagram_render.py (mmdc) si se quiere SVG.
"""
import argparse
import glob
import os
import re
import sys


# ---------- Parser mínimo del subset YAML de GitHub Actions ----------

def parse_workflow(path):
    """→ {"name": str, "triggers": [str], "jobs": {id: {"needs": [], "steps": int}}}

    Soporta: name:, on: (forma `on: push`, lista `on: [push, pull_request]` y
    bloque con claves), jobs: → <job-id>: → needs: (string o lista inline o
    bloque) y steps: (conteo de ítems).
    """
    lines = open(path, encoding="utf-8").read().splitlines()
    wf = {"name": os.path.splitext(os.path.basename(path))[0],
          "triggers": [], "jobs": {}}
    section = None          # None | "on" | "jobs"
    cur_job = None
    in_steps = False
    in_needs_block = False
    for raw in lines:
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()

        if indent == 0:
            section = None
            cur_job = None
            in_steps = in_needs_block = False
            if line.startswith("name:"):
                v = line[5:].strip().strip("'\"")
                if v:
                    wf["name"] = v
            elif line.startswith("on:") or line == "on":
                section = "on"
                rest = line[3:].strip() if line.startswith("on:") else ""
                if rest.startswith("[") and rest.endswith("]"):
                    wf["triggers"] = [t.strip().strip("'\"") for t in rest[1:-1].split(",") if t.strip()]
                elif rest:
                    wf["triggers"] = [rest.strip("'\"")]
            elif line.startswith("jobs:"):
                section = "jobs"
            continue

        if section == "on":
            if line.startswith("- "):
                wf["triggers"].append(line[2:].strip().strip("'\""))
            elif ":" in line:
                wf["triggers"].append(line.split(":", 1)[0].strip())
            continue

        if section == "jobs":
            if indent == 2 and line.rstrip().endswith(":"):
                cur_job = line.rstrip()[:-1].strip().strip("'\"")
                wf["jobs"][cur_job] = {"needs": [], "steps": 0}
                in_steps = in_needs_block = False
            elif cur_job and indent >= 4:
                if line.startswith("needs:"):
                    rest = line[6:].strip()
                    in_needs_block = not rest
                    in_steps = False
                    if rest.startswith("[") and rest.endswith("]"):
                        wf["jobs"][cur_job]["needs"] = [
                            n.strip().strip("'\"") for n in rest[1:-1].split(",") if n.strip()]
                    elif rest:
                        wf["jobs"][cur_job]["needs"] = [rest.strip("'\"")]
                elif line.startswith("steps:"):
                    in_steps = True
                    in_needs_block = False
                elif in_needs_block and line.startswith("- "):
                    wf["jobs"][cur_job]["needs"].append(line[2:].strip().strip("'\""))
                elif in_steps and line.startswith("- "):
                    wf["jobs"][cur_job]["steps"] += 1
                elif indent == 4 and ":" in line:
                    in_steps = in_needs_block = False
    return wf


# ---------- Validación ----------

def validate(wf):
    """→ lista de (severidad, mensaje). severidad: ERROR | WARN."""
    issues = []
    jobs = wf["jobs"]
    for jid, job in jobs.items():
        for need in job["needs"]:
            if need not in jobs:
                issues.append(("ERROR", f"{wf['name']}: job '{jid}' hace needs "
                                        f"de '{need}', que no existe"))
    # ciclos (DFS sobre needs)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {j: WHITE for j in jobs}

    def visit(j, stack):
        color[j] = GRAY
        for n in jobs[j]["needs"]:
            if n not in jobs:
                continue
            if color[n] == GRAY:
                issues.append(("ERROR", f"{wf['name']}: ciclo de dependencias "
                                        f"{' → '.join(stack + [j, n])}"))
                continue
            if color[n] == WHITE:
                visit(n, stack + [j])
        color[j] = BLACK

    for j in jobs:
        if color[j] == WHITE:
            visit(j, [])
    for jid, job in jobs.items():
        if not job["needs"] and len(jobs) > 1:
            issues.append(("WARN", f"{wf['name']}: job '{jid}' no tiene needs "
                                   f"(corre en paralelo al inicio — ¿intencional?)"))
    return issues


# ---------- Mermaid ----------

def to_mermaid(wf):
    out = ["flowchart LR"]
    jobs = wf["jobs"]
    roots = [j for j in jobs if not jobs[j]["needs"]]
    trig = ", ".join(wf["triggers"]) or "trigger"
    out.append(f'    T(["{trig}"])')
    for j in jobs:
        steps = jobs[j]["steps"]
        label = f"{j}\\n({steps} steps)" if steps else j
        out.append(f'    {norm_id(j)}["{label}"]')
    for r in roots:
        out.append(f"    T --> {norm_id(r)}")
    for j, job in jobs.items():
        for n in job["needs"]:
            if n in jobs:
                out.append(f"    {norm_id(n)} --> {norm_id(j)}")
    return "\n".join(out)


def norm_id(s):
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


def build_md(workflows):
    parts = ["# Pipeline CI/CD (derivado de .github/workflows/)",
             "",
             "> Generado por `pipeline_diagram.py`. NO editar a mano: regenerar",
             "> desde los workflows y aprobar el cambio con recibo",
             "> (`receipt.py emit --role devops-engineer`).",
             ""]
    total_err = 0
    for wf in workflows:
        parts.append(f"## Workflow: {wf['name']}")
        parts.append("")
        parts.append("```mermaid")
        parts.append(to_mermaid(wf))
        parts.append("```")
        parts.append("")
        issues = validate(wf)
        errs = [m for s, m in issues if s == "ERROR"]
        total_err += len(errs)
        if issues:
            parts.append("| Severidad | Hallazgo |")
            parts.append("|---|---|")
            for s, m in issues:
                parts.append(f"| {s} | {m} |")
        else:
            parts.append("Validación: OK — `needs:` íntegros, sin ciclos.")
        parts.append("")
    parts.append("---")
    parts.append(f"Workflows: {len(workflows)} · Errores de integridad: {total_err}")
    return "\n".join(parts) + "\n", total_err


def load_workflows(a):
    files = sorted(glob.glob(os.path.join(a.workflows_dir, "*.yml")) +
                   glob.glob(os.path.join(a.workflows_dir, "*.yaml")))
    if not files:
        print(f"ERROR: no hay workflows en {a.workflows_dir}", file=sys.stderr)
        sys.exit(1)
    return [parse_workflow(f) for f in files]


def cmd_generate(a):
    wfs = load_workflows(a)
    md, errs = build_md(wfs)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"OK: {a.out} — {len(wfs)} workflows, {errs} errores de integridad.")
    print("Siguiente paso (gobierno): revisar el contenido y aprobarlo con "
          f"`receipt.py emit --artifact {a.out} --role devops-engineer`. "
          "Sin recibo, el cambio de pipeline NO está aceptado.")
    return 1 if errs else 0


def cmd_validate(a):
    wfs = load_workflows(a)
    errs = 0
    for wf in wfs:
        for s, m in validate(wf):
            print(f"{s}: {m}", file=sys.stderr if s == "ERROR" else sys.stdout)
            errs += (s == "ERROR")
        if not validate(wf):
            print(f"OK: {wf['name']}")
    return 1 if errs else 0


def cmd_check(a):
    if not os.path.isfile(a.out):
        print(f"DRIFT: no existe {a.out} (diagrama nunca generado).", file=sys.stderr)
        return 1
    md, _ = build_md(load_workflows(a))
    current = open(a.out, encoding="utf-8").read()
    if md.strip() == current.strip():
        print(f"OK: {a.out} sincronizado con los workflows.")
        return 0
    print(f"DRIFT: {a.out} difiere de los workflows actuales.", file=sys.stderr)
    print("Regenerar con `generate`, revisar el diff y aprobar con recibo. "
          "Ediciones manuales se perderán: la fuente de verdad es el workflow.",
          file=sys.stderr)
    return 1


def main():
    p = argparse.ArgumentParser(description="Diagrama CI/CD derivado de workflows de GitHub Actions.")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in (("generate", cmd_generate), ("validate", cmd_validate),
                     ("check", cmd_check)):
        sp = sub.add_parser(name)
        sp.add_argument("--workflows-dir", default=".github/workflows")
        sp.add_argument("--out", default="spec/diagrams/pipeline-cicd.md")
        sp.set_defaults(f=fn)
    a = p.parse_args()
    return a.f(a)


if __name__ == "__main__":
    sys.exit(main())
