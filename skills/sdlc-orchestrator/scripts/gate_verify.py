#!/usr/bin/env python3
"""gate_verify.py — verificación agregada de un gate del arnés (v2.22, N4).

Un gate ya no se interpreta: se ejecuta. Para el gate pedido verifica, sobre
todo artefacto exigible:
  1. PRESENCIA — el archivo existe en spec/.
  2. TIPO      — pasa su gate_checker.py --tipo (si el artefacto tiene tipo).
  3. RECIBO    — tiene recibo VIGENTE con hash coincidente.

Además, verificaciones transversales según el gate:
  - memoria de auditoría íntegra (audit_verify.py) en todos los gates;
  - GATE 0/1: roster diligenciado con personas reales, no la plantilla (v2.33.3);
  - GATE 2: arch_lint en verde si existe spec/architecture-rules.yaml, y test
    runner configurado (detect_stack) o waiver aprobado spec/tdd-waiver.md
    con recibo vigente (v2.33.3 — la pausa de Strict TDD deja de ser narrativa);
  - condicionales del routing: --sin-ui / --sin-datos / --sin-procesos excluyen
    los artefactos condicionales que no aplican (mismo criterio que
    manifest_check.py --routing).

Uso:
  python3 gate_verify.py --gate "GATE 0" [--spec-dir spec/] [--root .]
                         [--sin-ui] [--sin-datos] [--sin-procesos]

Exit 0 = gate verificado. Exit 1 = lista cada faltante/incumplimiento.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))

# Catálogo gate -> artefactos exigibles: (ruta, tipo de gate_checker o None,
# condicional: None | "ui" | "datos" | "procesos")
CATALOGO = {
    "GATE 0": [
        ("spec/architecture-proposal.md", "architecture-proposal", None),
        ("spec/technical-stories.md", "technical-stories", None),
        ("spec/cost-estimation.md", "cost-estimation", None),
    ],
    "GATE 1": [
        ("spec/vision.md", "vision", None),
        ("spec/backlog.md", "backlog", None),
        ("spec/user-stories.md", "user-stories", None),
        ("spec/business-rules.md", None, None),
        ("spec/glossary.md", None, None),
        ("spec/roles.md", "roles", None),
        ("spec/process-definition.md", "process-definition", "procesos"),
        ("spec/ux-flows.md", "ux-flows", "ui"),
        ("spec/design-system.md", "design-system", "ui"),
        ("spec/ux/screen-inventory.md", "screen-inventory", "ui"),
        ("spec/architecture.md", "architecture", None),
        ("spec/api-contract.yaml", "api-contract", None),
        ("spec/data-model.md", None, "datos"),
        ("spec/threat-model.md", "threat-model", None),
        ("spec/test-plan.md", "test-plan", None),
    ],
    "GATE 2": [
        ("spec/qa-report.md", "qa-report", None),
    ],
    "GATE 2.5": [
        ("spec/security-requirements.md", None, None),
        ("spec/threat-model.md", "threat-model", None),
    ],
    "GATE 3": [
        ("spec/slo.md", "slo", None),
    ],
}


def receipt_vigente(spec_dir, artefacto):
    """(ok, detalle) — recibo vigente y con hash coincidente."""
    base = os.path.basename(artefacto).replace("/", "_")
    rp = os.path.join(spec_dir, "receipts", f"{base}.receipt.json")
    if not os.path.isfile(rp):
        return False, "sin recibo"
    try:
        rec = json.load(open(rp, encoding="utf-8"))
    except json.JSONDecodeError:
        return False, "recibo corrupto"
    if rec.get("estado") != "vigente":
        return False, f"recibo {rec.get('estado')}"
    h = hashlib.sha256(open(artefacto, "rb").read()).hexdigest()
    if rec.get("sha256") != h:
        return False, "hash no coincide (editado sin re-aprobar)"
    return True, ""


def roster_diligenciado(spec_dir):
    """(ok, detalle) — v2.33.3: Fase -1 no termina sin roster real.
    La matriz de autoridad dice qué rol posee cada artefacto; el roster dice qué
    humano encarna cada rol. Con la plantilla intacta, authority_check --author y
    el CODEOWNERS derivado son letra muerta."""
    p = os.path.join(spec_dir, "team-roster.yaml")
    if not os.path.isfile(p):
        return False, "spec/team-roster.yaml: NO EXISTE — init_project.py lo scaffolda"
    text = open(p, encoding="utf-8").read()
    if "# agregar aquí el resto del equipo" in text:
        return False, ("spec/team-roster.yaml: sigue siendo la PLANTILLA — "
                       "diligenciar personas reales (usuario-git → roles) en Fase -1")
    import re
    miembros = re.findall(r"^\s{2}\S+:\s*\[?[^\]\n]+\]?\s*$", text, re.MULTILINE)
    if not miembros:
        return False, "spec/team-roster.yaml: sin miembros definidos (usuario: [roles])"
    return True, ""


def runner_ok(spec_dir, root):
    """(ok, detalle) — v2.33.3: la pausa de Strict TDD tiene dientes.
    detect_stack exit 2 (sin test runner) bloquea GATE 2 salvo waiver aprobado
    por humano: spec/tdd-waiver.md con recibo vigente (emitido con --approved-by)."""
    r = subprocess.run([sys.executable, os.path.join(HERE, "detect_stack.py"),
                        "--project-dir", root], capture_output=True, text=True)
    if r.returncode != 2:
        return True, ""
    waiver = os.path.join(spec_dir, "tdd-waiver.md")
    if os.path.isfile(waiver):
        ok, det = receipt_vigente(spec_dir, waiver)
        if ok:
            return True, ""
        return False, (f"sin test runner (detect_stack exit 2) y waiver {det} — "
                       "re-aprobar spec/tdd-waiver.md")
    return False, ("sin test runner configurado (detect_stack exit 2): Strict TDD "
                   "sigue EN PAUSA al entrar a Fase 4 — configurar un runner o "
                   "registrar waiver aprobado por humano en spec/tdd-waiver.md "
                   "con recibo (--approved-by)")


def main():
    ap = argparse.ArgumentParser(description="Verificación agregada de gate (N4)")
    ap.add_argument("--gate", required=True)
    ap.add_argument("--spec-dir", default="spec/")
    ap.add_argument("--root", default=".")
    ap.add_argument("--sin-ui", action="store_true")
    ap.add_argument("--sin-datos", action="store_true")
    ap.add_argument("--sin-procesos", action="store_true")
    a = ap.parse_args()

    from audit_log import gate_valido
    gate = gate_valido(a.gate)
    if gate is None:
        print(f"FALLO: gate '{a.gate}' fuera del catálogo (GATE 0/1/2/2.5/3, "
              "SPRINT-N, FASE-N).")
        sys.exit(1)

    excluidas = set()
    if a.sin_ui:
        excluidas.add("ui")
    if a.sin_datos:
        excluidas.add("datos")
    if a.sin_procesos:
        excluidas.add("procesos")

    if gate.startswith("SPRINT-"):
        nn = gate.split("-")[1]
        requisitos = [(f"spec/reports/sprint-review-{int(nn):02d}.md", "sprint-review", None)]
    elif gate.startswith("FASE-"):
        print(f"GATE {gate}: los gates de fase se verifican artefacto a artefacto "
              "con gate_checker.py + receipt.py — gate_verify agrega los gates de entrega.")
        sys.exit(0)
    else:
        requisitos = CATALOGO.get(gate)
        if requisitos is None:
            print(f"FALLO: {gate} sin catálogo de verificación agregada.")
            sys.exit(1)

    fallos, verificados, excl = [], [], []
    for rel, tipo, cond in requisitos:
        if cond and cond in excluidas:
            excl.append(f"{rel} (condicional: {cond}, no aplica)")
            continue
        path = os.path.join(a.spec_dir, os.path.relpath(rel, "spec"))
        if not os.path.isfile(path):
            fallos.append(f"{rel}: NO EXISTE")
            continue
        if tipo:
            r = subprocess.run([sys.executable, os.path.join(HERE, "gate_checker.py"),
                                path, "--tipo", tipo], capture_output=True, text=True)
            if r.returncode != 0:
                detalle = (r.stdout.strip().splitlines() or ["gate no pasado"])[-1]
                fallos.append(f"{rel}: gate_checker --tipo {tipo} falló — {detalle}")
                continue
        ok, detalle = receipt_vigente(a.spec_dir, path)
        if not ok:
            fallos.append(f"{rel}: {detalle}")
            continue
        verificados.append(rel)

    # Transversal 1: la auditoría debe existir y estar íntegra
    audit_log = os.path.join(a.spec_dir, "audit", "events.jsonl")
    if not os.path.isfile(audit_log):
        fallos.append("spec/audit/events.jsonl: NO EXISTE — inicializar con "
                      "init_project.py o audit_log.py init (sin auditoría no hay gate)")
    else:
        r = subprocess.run([sys.executable, os.path.join(HERE, "audit_verify.py"),
                            "--spec-dir", a.spec_dir], capture_output=True, text=True)
        if r.returncode != 0:
            fallos.append("memoria de auditoría NO íntegra — audit_verify.py falló")

    # Transversal 2 (GATE 2): invariantes de arquitectura si están declarados
    if gate == "GATE 2" and os.path.isfile(os.path.join(a.spec_dir, "architecture-rules.yaml")):
        r = subprocess.run([sys.executable, os.path.join(HERE, "arch_lint.py"),
                            "--root", a.root, "--spec-dir", a.spec_dir],
                           capture_output=True, text=True)
        if r.returncode != 0:
            fallos.append("arch_lint: el código viola los invariantes declarados")

    # Transversal 3 (GATE 0/1, v2.33.3): roster real — sin personas mapeadas a
    # roles, la matriz de autoridad y el CODEOWNERS no tienen a quién aplicar
    if gate in ("GATE 0", "GATE 1"):
        ok, detalle = roster_diligenciado(a.spec_dir)
        if not ok:
            fallos.append(detalle)

    # Transversal 4 (GATE 2, v2.33.3): la pausa de Strict TDD no es narrativa —
    # entrar a Fase 4 sin test runner exige waiver aprobado por humano
    if gate == "GATE 2":
        ok, detalle = runner_ok(a.spec_dir, a.root)
        if not ok:
            fallos.append(detalle)

    print(f"GATE VERIFY {gate}: {len(verificados)} verificados, "
          f"{len(fallos)} faltantes/incumplidos, {len(excl)} excluidos por routing")
    for v in verificados:
        print(f"  OK  {v}")
    for e in excl:
        print(f"  --  {e}")
    for f in fallos:
        print(f"  FALLO  {f}")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
