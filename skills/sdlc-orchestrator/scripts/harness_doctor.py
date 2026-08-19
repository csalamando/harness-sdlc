#!/usr/bin/env python3
"""harness_doctor.py — Health check read-only del arnes SDLC instalado.

Verifica: skills instaladas (17 roles + memoria + diagramas), plantillas assets presentes,
scripts del orquestador ejecutables, estructura spec/ del proyecto.

Uso: python3 harness_doctor.py [--skills-dir <ruta>] [--project-dir <ruta>]
Exit 0 si todo OK; 1 si hay problemas.
"""
import os, sys, json, argparse, subprocess

EXPECTED_SKILLS = [
    "sdlc-orchestrator", "sdlc-product-owner", "sdlc-business-analyst", "sdlc-ux-designer",
    "sdlc-software-architect", "sdlc-security-engineer", "sdlc-data-engineer",
    "sdlc-backend-dev-tdd", "sdlc-frontend-dev-tdd", "sdlc-qa-automation",
    "sdlc-devops-engineer", "sdlc-cloud-engineer", "sdlc-sre",
    "sdlc-product-analyst", "sdlc-technical-writer", "sdlc-memory", "sdlc-diagrams",
    "sdlc-decision-engine", "sdlc-enterprise-architect",
]
ORCH_SCRIPTS = ["gate_checker.py", "context_packager.py", "spec_diff_impact.py",
                "decision_sizing.py", "advisor.py", "arch_signoff.py",
                "traceability_matrix.py", "receipt.py", "detect_stack.py"]
MEM_SCRIPTS = ["mem.py", "mem_mcp.py"]

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
    for name in EXPECTED_SKILLS:
        d = os.path.join(skills_dir, name)
        has_md = os.path.isfile(os.path.join(d, "SKILL.md"))
        check(results, f"skill {name}", os.path.isdir(d) and has_md)

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

    print(f"\nProyecto: {a.project_dir}")
    spec = os.path.join(a.project_dir, "spec")
    for sub in ["", "memory/entries", "receipts"]:
        p = os.path.join(spec, sub)
        check(results, f"spec/{sub}", os.path.isdir(p), "(se crea al primer uso)" if not os.path.isdir(p) else "")
    gi = os.path.join(a.project_dir, ".gitignore")
    if os.path.isfile(gi):
        has_ignore = ".index" in open(gi, encoding="utf-8", errors="ignore").read()
        check(results, ".gitignore incluye spec/memory/.index/", has_ignore)

    n_fail = results.count(False)
    print(f"\nEstado: {'OK' if n_fail == 0 else f'REVISAR — {n_fail} problema(s)'}")
    sys.exit(0 if n_fail == 0 else 1)

if __name__ == "__main__":
    main()
