#!/usr/bin/env python3
"""init_project.py — scaffold determinista de un proyecto del arnés (v2.22, N4).

"Lo mínimo para iniciar" deja de interpretarse: todo proyecto arranca con la
misma estructura y los mismos controles de gobierno. Idempotente — NUNCA
sobrescribe un archivo existente (reporta lo saltado).

Uso:
  python3 init_project.py --proyecto <nombre> [--dir .] [--capas]
                          [--sin-ui] [--sin-datos] [--sin-procesos]

Crea:
  spec/                       estructura de directorios gobernada
  spec/authority-matrix.yaml  qué rol es dueño de cada artefacto (desde el arnés)
  spec/team-roster.yaml       plantilla usuario → roles
  spec/tech-radar.yaml        radar tecnológico (desde el arnés)
  spec/architecture-rules.yaml  SOLO con --capas (invariantes para arch_lint)
  spec/audit/events.jsonl     memoria de auditoría inicializada + evento bootstrap

Exit 0 = proyecto inicializado (o ya lo estaba). Exit 1 = error.
"""
import argparse
import os
import shutil
import sys

sys.dont_write_bytecode = True

DIRS = ["spec", "spec/adr", "spec/diagrams", "spec/receipts", "spec/metrics",
        "spec/reports", "spec/memory/entries"]

# (destino en el proyecto, asset de origen relativo a skills/)
COPIES = [
    ("spec/authority-matrix.yaml", "sdlc-orchestrator/assets/authority-matrix.yaml"),
    ("spec/team-roster.yaml",      "sdlc-orchestrator/assets/team-roster-template.yaml"),
    ("spec/tech-radar.yaml",       "sdlc-enterprise-architect/assets/tech-radar.yaml"),
]


def main():
    ap = argparse.ArgumentParser(description="Scaffold determinista de proyecto (N4)")
    ap.add_argument("--proyecto", required=True)
    ap.add_argument("--dir", default=".", help="raíz del proyecto")
    ap.add_argument("--capas", action="store_true",
                    help="declara arquitectura por capas: scaffolding de architecture-rules.yaml")
    ap.add_argument("--sin-ui", action="store_true")
    ap.add_argument("--sin-datos", action="store_true")
    ap.add_argument("--sin-procesos", action="store_true")
    a = ap.parse_args()
    root = os.path.abspath(a.dir)
    skills = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "..", ".."))

    creados, saltados = [], []
    for d in DIRS:
        os.makedirs(os.path.join(root, d), exist_ok=True)
    if not a.sin_ui:
        os.makedirs(os.path.join(root, "spec", "ux"), exist_ok=True)

    copies = list(COPIES)
    if a.capas:
        copies.append(("spec/architecture-rules.yaml",
                       "sdlc-software-architect/assets/architecture-rules.yaml"))
    for entry in copies:
        dest_rel, src_rel = entry[0], entry[1]
        dest = os.path.join(root, dest_rel)
        if os.path.exists(dest):
            saltados.append(dest_rel)
            continue
        shutil.copyfile(os.path.join(skills, src_rel), dest)
        creados.append(dest_rel)

    # Memoria de auditoría (ADR-004): génesis + bootstrap en el mismo arranque.
    from audit_log import append_event, harness_version, log_path, last_event
    spec_dir = os.path.join(root, "spec")
    if not os.path.exists(log_path(spec_dir)):
        append_event(spec_dir, "audit_init", proyecto=a.proyecto,
                     nota="Genesis de la memoria de auditoria (init_project.py)")
        creados.append("spec/audit/events.jsonl")
        flags = [f for f, on in (("sin-ui", a.sin_ui), ("sin-datos", a.sin_datos),
                                 ("sin-procesos", a.sin_procesos), ("capas", a.capas)) if on]
        append_event(spec_dir, "bootstrap", proyecto=a.proyecto,
                     modo=" ".join(flags) or "full-pipeline",
                     nota=f"scaffold init_project.py (harness {harness_version()})")

    # Estado del pipeline derivado (N7): el primer pipeline-state.md nace de
    # hechos (matriz + auditoría), nunca narrado a mano.
    try:
        from pipeline_state import build
        open(os.path.join(spec_dir, "pipeline-state.md"), "w",
             encoding="utf-8").write(build(spec_dir, root))
        if "spec/pipeline-state.md" not in saltados:
            creados.append("spec/pipeline-state.md")
    except Exception as e:
        print(f"  ⚠ no se pudo derivar pipeline-state.md: {e}")

    print(f"PROYECTO INICIALIZADO: {a.proyecto} (harness {harness_version()})")
    for c in creados:
        print(f"  + {c}")
    for s in saltados:
        print(f"  = {s} (ya existía, no se tocó)")
    print("\nSiguiente paso: roles de Fase 0 (product-owner + solution-architect). "
          "Verificar un gate con: gate_verify.py --gate 'GATE 0'.")
    sys.exit(0)


if __name__ == "__main__":
    main()
