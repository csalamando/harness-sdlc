#!/usr/bin/env python3
"""harness_doctor.py — Health check read-only del arnes SDLC instalado.

Verifica: skills instaladas, plantillas assets presentes, scripts ejecutables,
estructura spec/ del proyecto.

Desde v2.9 las expectativas (qué skills y qué scripts deben existir) se leen del
manifiesto derivado `assets/harness-manifest.yaml` — ya no hay listas quemadas que
se desactualizan. Si el manifiesto no existe (instalación antigua), degrada a las
listas mínimas históricas.

Uso: python3 harness_doctor.py [--skills-dir <ruta>] [--project-dir <ruta>]
Exit 0 si todo OK; 1 si hay problemas.
"""
import os, sys, json, argparse, subprocess, re

# Fallback histórico (pre-v2.9) si no hay manifiesto instalado.
EXPECTED_SKILLS = [
    "sdlc-orchestrator", "sdlc-product-owner", "sdlc-business-analyst", "sdlc-ux-designer",
    "sdlc-software-architect", "sdlc-security-engineer", "sdlc-data-engineer",
    "sdlc-backend-dev-tdd", "sdlc-frontend-dev-tdd", "sdlc-qa-automation",
    "sdlc-devops-engineer", "sdlc-cloud-engineer", "sdlc-sre",
    "sdlc-product-analyst", "sdlc-technical-writer", "sdlc-memory", "sdlc-diagrams",
    "sdlc-decision-engine", "sdlc-enterprise-architect",
    "sdlc-solution-architect", "sdlc-cloud-pricing",
]
ORCH_SCRIPTS = ["gate_checker.py", "context_packager.py", "spec_diff_impact.py",
                "decision_sizing.py", "advisor.py", "arch_signoff.py",
                "traceability_matrix.py", "receipt.py", "detect_stack.py", "authority_check.py",
                "code_intel.py", "spec_index.py", "skill_metrics.py", "sprint_review.py",
                "manifest_check.py"]
MEM_SCRIPTS = ["mem.py", "mem_mcp.py"]
DIAGRAM_SCRIPTS = ["diagram_render.py", "iac_to_diagram.py", "pipeline_diagram.py"]


def load_manifest(skills_dir):
    """Lee assets/harness-manifest.yaml del orquestador (formato plano generado).
    Devuelve {skill: [scripts]} o None si no existe."""
    path = os.path.join(skills_dir, "sdlc-orchestrator", "assets", "harness-manifest.yaml")
    if not os.path.isfile(path):
        return None
    scripts, current = {}, None
    for line in open(path, encoding="utf-8"):
        m = re.match(r"  - name: (\S+)", line)
        if m:
            current = m.group(1); scripts[current] = []
        elif line.startswith("    scripts:") and current:
            scripts[current] = re.findall(r"[\w.-]+\.py", line)
    return scripts or None

def check(ok_list, label, ok, detail=""):
    ok_list.append(ok)
    print(f"  {'OK ' if ok else 'FALTA'} {label} {detail}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skills-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    ap.add_argument("--project-dir", default=os.getcwd())
    a = ap.parse_args()
    skills_dir = os.path.abspath(a.skills_dir)
    results = []

    print(f"Skills dir: {skills_dir}")
    manifest = load_manifest(skills_dir)
    if manifest:
        expected_skills = sorted(manifest)
        print(f"  (expectativas leídas del manifiesto derivado: {len(expected_skills)} skills)")
    else:
        expected_skills = EXPECTED_SKILLS
        print("  (manifiesto no encontrado — usando listas mínimas históricas; "
              "regenerar con manifest_check.py --write)")
    for name in expected_skills:
        d = os.path.join(skills_dir, name)
        has_md = os.path.isfile(os.path.join(d, "SKILL.md"))
        check(results, f"skill {name}", os.path.isdir(d) and has_md)

    if manifest:
        print("\nScripts por skill (compilacion, según manifiesto):")
        for skill in expected_skills:
            for s in manifest[skill]:
                p = os.path.join(skills_dir, skill, "scripts", s)
                ok = os.path.isfile(p) and subprocess.run(["python3", "-m", "py_compile", p], capture_output=True).returncode == 0
                check(results, f"{skill}/{s}", ok)
    else:
        print("\nScripts del orquestador (compilacion):")
        for s in ORCH_SCRIPTS:
            p = os.path.join(skills_dir, "sdlc-orchestrator", "scripts", s)
            ok = os.path.isfile(p) and subprocess.run(["python3", "-m", "py_compile", p], capture_output=True).returncode == 0
            check(results, s, ok)

        print("\nScripts de memoria (compilacion):")
        for s in MEM_SCRIPTS:
            p = os.path.join(skills_dir, "sdlc-memory", "scripts", s)
            ok = os.path.isfile(p) and subprocess.run(["python3", "-m", "py_compile", p], capture_output=True).returncode == 0
            check(results, s, ok)

        print("\nScripts de diagramas (compilacion):")
        for s in DIAGRAM_SCRIPTS:
            p = os.path.join(skills_dir, "sdlc-diagrams", "scripts", s)
            ok = os.path.isfile(p) and subprocess.run(["python3", "-m", "py_compile", p], capture_output=True).returncode == 0
            check(results, s, ok)
    import shutil as _sh
    print("  Motores de render (opcionales): drawio-desktop="
          + ("OK" if any(_sh.which(c) for c in ("drawio", "drawio-desktop", "draw.io")) else "no")
          + ", mmdc=" + ("OK" if _sh.which("mmdc") or _sh.which("npx") else "no")
          + " — sin motores, el render se omite y el fuente .drawio/.mmd sigue siendo el entregable")

    print(f"\nProyecto: {a.project_dir}")
    spec = os.path.join(a.project_dir, "spec")
    for sub in ["", "memory/entries", "receipts"]:
        p = os.path.join(spec, sub)
        check(results, f"spec/{sub}", os.path.isdir(p), "(se crea al primer uso)" if not os.path.isdir(p) else "")
    gi = os.path.join(a.project_dir, ".gitignore")
    if os.path.isfile(gi):
        gi_text = open(gi, encoding="utf-8", errors="ignore").read()
        check(results, ".gitignore incluye spec/memory/.index/", ".index" in gi_text)
        check(results, ".gitignore incluye .codeintel/ (índice derivable)", ".codeintel" in gi_text)
    ci_db = os.path.join(a.project_dir, ".codeintel", "index.db")
    check(results, ".codeintel/index.db (code_intel indexado)",
          os.path.isfile(ci_db),
          "" if os.path.isfile(ci_db) else "(correr: code_intel.py --root <proyecto> index)")

    # Frescura del dashboard en CI (v2.15): si el proyecto tiene workflows pero
    # ninguno regenera/verifica el dashboard, la visibilidad queda por demanda.
    wf_dir = os.path.join(a.project_dir, ".github", "workflows")
    if os.path.isdir(wf_dir):
        mencion = False
        for wf in os.listdir(wf_dir):
            if wf.endswith((".yml", ".yaml")):
                txt = open(os.path.join(wf_dir, wf), encoding="utf-8", errors="ignore").read()
                if "harness_graph" in txt:
                    mencion = True
                    break
        check(results, "CI regenera/verifica spec/dashboard.html (harness_graph)",
              mencion,
              "sin eso el dashboard solo se actualiza por demanda — añadir ci-spec-governance.yml")

    # Versión del arnés: instalada vs. la última vista en los recibos del proyecto (v2.12.1)
    import json as _json
    hv = None
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from manifest_check import harness_version
        hv = harness_version(skills_dir)
    except Exception:
        pass
    print(f"\nVersión del arnés instalado: {hv or 'no declarada (anterior a v2.12.1)'}")
    rdir = os.path.join(spec, "receipts")
    if os.path.isdir(rdir):
        versions = set()
        for f in sorted(os.listdir(rdir)):
            if f.endswith(".receipt.json"):
                try:
                    v = _json.load(open(os.path.join(rdir, f), encoding="utf-8")).get("harness_version")
                    if v:
                        versions.add(v)
                except (OSError, ValueError):
                    pass
        if hv and versions and hv not in versions and max(versions) < hv:
            print(f"  ⚠ el proyecto operó con arnés {sorted(versions)} y tienes instalado {hv}"
                  " — considera actualizar la adopción (nuevos gates, herramientas y plantillas)")
        elif versions:
            print(f"  Recibos del proyecto emitidos con arnés: {', '.join(sorted(versions))}")
        else:
            print("  Recibos sin harness_version (emitidos con arnés anterior a v2.12.1)")

    n_fail = results.count(False)
    print(f"\nEstado: {'OK' if n_fail == 0 else f'REVISAR — {n_fail} problema(s)'}")
    sys.exit(0 if n_fail == 0 else 1)

if __name__ == "__main__":
    main()
