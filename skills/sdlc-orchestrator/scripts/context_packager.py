#!/usr/bin/env python3
"""context_packager.py — genera el paquete mínimo de contexto que un rol necesita.

Uso: python3 context_packager.py --rol <rol> --spec-dir spec/ [--code-root .]
Imprime la lista de archivos a entregar al agente de ese rol (entrada del orquestador).
Si existe spec/INDEX.md lo antepone como orientación de una página.
Si existe <code-root>/.codeintel/index.db, indica al rol de desarrollo que
consulte símbolos vía code_intel.py en vez de leer archivos completos.
"""
import os, argparse, json

ROLES_CODIGO = {"backend-dev", "frontend-dev", "qa", "sre"}

CONTEXT_MAP = {
    "product-owner":   ["impact-report.md", "tech-debt.md"],
    "business-analyst": ["vision.md", "backlog.md"],
    "ux-designer":     ["user-stories.md", "glossary.md"],
    "architect":       ["user-stories.md", "ux-flows.md", "business-rules.md", "glossary.md"],
    "security":        ["architecture.md", "data-model.md", "security-requirements.md"],
    "data-engineer":   ["data-model.md", "business-rules.md", "security-requirements.md"],
    "backend-dev":     ["api-contract.yaml", "business-rules.md", "test-plan.md", "security-requirements.md", "architecture.md"],
    "frontend-dev":    ["api-contract.yaml", "design-system.md", "tokens.json", "ux-flows.md", "user-stories.md", "glossary.md"],
    "qa":              ["user-stories.md", "test-plan.md", "architecture.md", "qa-report.md"],
    "devops":          ["architecture.md", "test-plan.md"],
    "cloud-engineer":  ["architecture.md", "security-requirements.md", "data-governance.md"],
    "sre":             ["architecture.md", "slo.md"],
    "product-analyst": ["vision.md", "user-stories.md", "impact-report.md"],
    "technical-writer":["user-stories.md", "ux-flows.md", "api-contract.yaml", "glossary.md"],
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rol", required=True, choices=sorted(CONTEXT_MAP))
    ap.add_argument("--spec-dir", default="spec/")
    ap.add_argument("--code-root", default=".")
    a = ap.parse_args()
    files, missing = [], []
    digest = os.path.join(a.spec_dir, "INDEX.md")
    if os.path.exists(digest):
        files.append(digest + "  # orientación: leer primero, abrir solo lo necesario")
    for f in CONTEXT_MAP[a.rol]:
        p = os.path.join(a.spec_dir, f)
        (files if os.path.exists(p) else missing).append(p)
    out = {
        "rol": a.rol,
        "contexto_a_entregar": files,
        "faltantes_bloquean_DoR": missing,
    }
    ci_db = os.path.join(a.code_root, ".codeintel", "index.db")
    if a.rol in ROLES_CODIGO and os.path.isfile(ci_db):
        out["code_intel"] = {
            "indice": os.path.relpath(ci_db),
            "regla": "NO leer archivos de código completos: consultar símbolos",
            "comandos": [
                "code_intel.py context <símbolo|archivo>   # cuerpo exacto o esqueleto",
                "code_intel.py impact <símbolo|archivo>    # blast radius antes de editar",
                "code_intel.py tests <símbolo|archivo>     # tests candidatos (GATE 2)",
                "code_intel.py search <texto>              # búsqueda en firmas/docstrings",
            ],
        }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    if missing:
        print("\nADVERTENCIA: entradas faltantes — DoR incumplido, no activar el rol todavía.")

if __name__ == "__main__":
    main()
