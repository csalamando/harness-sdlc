#!/usr/bin/env python3
"""gate_checker.py — valida el checklist de salida (DoD) de un artefacto de la spec.

Uso: python3 gate_checker.py <artefacto> --tipo <tipo>
Tipos: vision, backlog, user-stories, ux-flows, design-system, architecture,
       api-contract, test-plan, threat-model, qa-report, slo
Exit 0 = pasa el gate. Exit 1 = falla (imprime checks incumplidos).
"""
import sys, argparse, re

def has(path, *patterns):
    try:
        text = open(path, encoding="utf-8").read()
    except FileNotFoundError:
        return None
    return all(re.search(p, text, re.IGNORECASE | re.MULTILINE) for p in patterns)

CHECKS = {
    "vision": ["problema", "usuarios objetivo", "propuesta de valor", "métricas de éxito"],
    "backlog": ["prioridad", "métrica de éxito", r"EP-\d+"],
    "user-stories": [r"HU-\d+", r"[Ee]scenario", r"[Dd]ado", r"[Cc]uando", r"[Ee]ntonces", r"épica"],
    "ux-flows": ["loading", "empty", "error", "success"],
    "design-system": ["color", "tipografía|tipografia|typography", "espaciado|spacing", "componentes"],
    "architecture": [r"mermaid", r"requisitos no funcionales|NFR", r"componentes"],
    "api-contract": ["openapi:", "paths:", "components:"],
    "test-plan": [r"HU-\d+", r"unit|unitario", r"E2E", r"cobertura"],
    "threat-model": [r"S.*T.*R.*I.*D.*E|Spoofing", r"Mitigación|mitigacion", r"Riesgo|riesgo"],
    "qa-report": [r"[Vv]eredicto", r"HU-\d+", r"[Rr]egresión|regresion", r"[Bb]ugs"],
    "slo": [r"SLI", r"SLO", r"[Ee]rror budget"],
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("artefacto")
    ap.add_argument("--tipo", required=True, choices=sorted(CHECKS))
    a = ap.parse_args()
    patterns = CHECKS[a.tipo]
    try:
        text = open(a.artefacto, encoding="utf-8").read()
    except FileNotFoundError:
        print(f"FALLO: no existe {a.artefacto}"); sys.exit(1)
    missing = [p for p in patterns if not re.search(p, text, re.IGNORECASE | re.MULTILINE)]
    if missing:
        print(f"GATE NO PASADO ({a.tipo}): faltan {len(missing)} elementos:")
        for m in missing: print(f"  - patrón no encontrado: {m}")
        sys.exit(1)
    print(f"GATE PASADO ({a.tipo}): {len(patterns)} checks OK -> {a.artefacto}")

if __name__ == "__main__":
    main()
