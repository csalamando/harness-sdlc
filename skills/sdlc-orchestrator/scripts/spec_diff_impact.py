#!/usr/bin/env python3
"""spec_diff_impact.py — al cambiar un artefacto, lista los artefactos downstream invalidados.

Uso: python3 spec_diff_impact.py --cambiado <nombre-artefacto>
"""
import argparse

# Grafo de dependencias: artefacto -> artefactos que lo consumen (downstream)
DEPENDS_ON = {
    "vision.md":            [],
    "epics.md":             ["vision.md"],
    "backlog.md":           ["vision.md", "epics.md"],
    # GATE 0 — discovery de la iniciativa (v2.1)
    "architecture-proposal.md": ["vision.md", "backlog.md"],
    "technical-stories.md": ["architecture-proposal.md"],
    "cost-estimation.md":   ["architecture-proposal.md"],
    # Fase 1 — análisis (v2.7: catálogo de roles y PDD)
    "roles.md":             [],
    "user-stories.md":      ["vision.md", "backlog.md", "roles.md"],
    "business-rules.md":    ["user-stories.md"],
    "process-definition.md": ["business-rules.md", "roles.md"],
    "glossary.md":          ["user-stories.md"],
    "ux-flows.md":          ["user-stories.md"],
    "design-system.md":     ["user-stories.md"],
    "tokens.json":          ["design-system.md"],
    # v2.8 — inventario de pantallas del prototipo gobernado (spec/ux/)
    "screen-inventory.md":  ["user-stories.md", "roles.md", "ux-flows.md"],
    "architecture.md":      ["user-stories.md", "business-rules.md", "architecture-proposal.md"],
    "adr":                  ["architecture.md"],
    "tech-radar.yaml":      [],
    "api-contract.yaml":    ["architecture.md"],
    "data-model.md":        ["business-rules.md", "architecture.md"],
    "threat-model.md":      ["architecture.md", "data-model.md"],
    "security-requirements.md": ["threat-model.md"],
    "data-governance.md":   ["data-model.md", "security-requirements.md"],
    "test-plan.md":         ["user-stories.md", "api-contract.yaml", "architecture.md"],
    "src-backend":          ["api-contract.yaml", "business-rules.md", "test-plan.md", "security-requirements.md"],
    "src-frontend":         ["api-contract.yaml", "tokens.json", "ux-flows.md", "design-system.md", "screen-inventory.md"],
    "tests-e2e":            ["user-stories.md", "test-plan.md"],
    "qa-report.md":         ["tests-e2e"],
    "infra":                ["architecture.md", "security-requirements.md"],
    "diagrams":             ["infra", "architecture.md"],
    "slo.md":               ["architecture.md"],
    "docs":                 ["api-contract.yaml", "ux-flows.md", "glossary.md"],
}

def downstream(changed):
    impact, queue = set(), [changed]
    while queue:
        cur = queue.pop()
        for art, deps in DEPENDS_ON.items():
            if cur in deps and art not in impact:
                impact.add(art); queue.append(art)
    return sorted(impact)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cambiado", required=True)
    ap.add_argument("--relation", choices=["supersedes", "conflicts_with"], default="supersedes",
                    help="Relacion del cambio con la version anterior del artefacto")
    ap.add_argument("--nueva-version", default="")
    a = ap.parse_args()
    if a.cambiado not in DEPENDS_ON:
        print(f"Artefacto desconocido: {a.cambiado}. Conocidos: {', '.join(sorted(DEPENDS_ON))}")
        raise SystemExit(1)
    if a.relation == "conflicts_with":
        print(f"ALERTA: '{a.cambiado}' contradice su version anterior (conflicts_with).")
        print("  Requiere resolucion humana ANTES de tocar artefactos downstream.")
        print("  Bloquea GATE 1 mientras no se resuelva.\n")
    else:
        print("El cambio reemplaza a la version anterior (supersedes).")
        if a.nueva_version: print(f"  Nueva version: {a.nueva_version}")
    impacted = downstream(a.cambiado)
    print(f"\nImpacto de cambiar '{a.cambiado}':")
    if not impacted:
        print("  Sin artefactos downstream.")
    for art in impacted:
        print(f"  - {art}  -> revocar recibo, re-validar gate y re-ejecutar fase correspondiente")
    print(f"\nTotal: {len(impacted)} artefacto(s) a re-validar. Nueva versión de spec requerida.")

if __name__ == "__main__":
    main()
