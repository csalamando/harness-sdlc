#!/usr/bin/env python3
"""codeowners_gen.py — CODEOWNERS derivado de la matriz de autoridad + roster (v2.33.4).

La frontera dura en Git ("un PR que toca spec/adr/ no se mergea sin el Arquitecto")
deja de ser una plantilla copiada a mano que se desactualiza: se DERIVA de las dos
fuentes de verdad del gobierno de identidades —
  spec/authority-matrix.yaml  (qué rol posee cada artefacto)
  spec/team-roster.yaml       (qué humano encarna cada rol)

Una línea por artefacto gobernado: `spec/<artefacto>  @titular-1 @titular-2`.
Un rol sin titular en el roster no desaparece en silencio: la línea queda
comentada como SIN TITULAR y se reporta (la frontera para ese artefacto no
existe en GitHub — visible, nunca invisible).

Uso:
  python3 codeowners_gen.py [--spec-dir spec/] [--root .] [--out .github/CODEOWNERS]
  python3 codeowners_gen.py --check      # anti-drift para CI: exit 1 si difiere

Exit 0 = generado/verificado. Exit 1 = drift (--check) o roster/matriz ausentes.
Recordatorio: activar en GitHub Settings → Branches → Branch protection →
"Require review from Code Owners". El archivo sin la protección es decorativo.
"""
import argparse
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))

HEADER = [
    "# CODEOWNERS — GENERADO por codeowners_gen.py (arnés SDLC v2.33.4)",
    "# Fuentes de verdad: spec/authority-matrix.yaml + spec/team-roster.yaml",
    "# NO editar a mano: drift = fallo de CI (codeowners_gen.py --check).",
    "# Para que muerda: Settings → Branches → Branch protection →",
    "#   \"Require review from Code Owners\".",
    "",
]


def build(spec_dir):
    """(contenido, warnings) — deriva el CODEOWNERS. Lanza SystemExit con
    mensaje si falta la matriz o el roster (sin fuentes no hay frontera)."""
    from authority_check import load_matrix, load_roster
    matrix_path = os.path.join(spec_dir, "authority-matrix.yaml")
    roster_path = os.path.join(spec_dir, "team-roster.yaml")
    rules = load_matrix(matrix_path)
    if not rules:
        print(f"FALLO: sin matriz de autoridad legible en {matrix_path}")
        sys.exit(1)
    roster = load_roster(roster_path)
    if roster is None:
        print(f"FALLO: sin roster en {roster_path} — la matriz no tiene a quién "
              "aplicar (diligenciar en Fase -1)")
        sys.exit(1)

    titulares = {}
    for user, roles in roster.items():
        for rol in roles:
            titulares.setdefault(rol, []).append(user)

    lineas, warnings = list(HEADER), []
    ancho = max(len(p) for p, _ in rules)
    for path, owner in rules:
        users = titulares.get(owner, [])
        if users:
            mentions = " ".join(f"@{u}" for u in sorted(users))
            lineas.append(f"{path.ljust(ancho)}  {mentions}")
        else:
            lineas.append(f"# SIN TITULAR: {path}  (rol {owner} sin persona en el "
                          "roster — la frontera NO aplica en GitHub para este artefacto)")
            warnings.append(f"{path}: rol '{owner}' sin titular en el roster")
    lineas.append("")
    return "\n".join(lineas), warnings


def main():
    ap = argparse.ArgumentParser(description="CODEOWNERS derivado de matriz + roster")
    ap.add_argument("--spec-dir", default="spec/")
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default=None,
                    help="ruta destino (default <root>/.github/CODEOWNERS)")
    ap.add_argument("--check", action="store_true",
                    help="anti-drift para CI: exit 1 si el archivo difiere")
    a = ap.parse_args()

    contenido, warnings = build(a.spec_dir)
    out = a.out or os.path.join(a.root, ".github", "CODEOWNERS")

    if a.check:
        actual = open(out, encoding="utf-8").read() if os.path.isfile(out) else None
        if actual != contenido:
            print(f"DRIFT: {out} no coincide con matriz + roster "
                  "(regenerar: codeowners_gen.py)")
            sys.exit(1)
        print(f"CODEOWNERS sin drift ({out}).")
    else:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "w", encoding="utf-8").write(contenido)
        print(f"CODEOWNERS derivado -> {out} "
              "(activar 'Require review from Code Owners' en branch protection)")
    for w in warnings:
        print(f"  ⚠ {w}")
    sys.exit(0)


if __name__ == "__main__":
    main()
