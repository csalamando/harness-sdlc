#!/usr/bin/env python3
"""authority_check.py — Verifica que quien emite/firma un artefacto sea su rol dueño.

La matriz de autoridad (spec/authority-matrix.yaml) declara UN owner por artefacto.
Opinar no es poseer: cualquier rol participa vía Advice Process; la matriz solo
restringe la autoría y la emisión del recibo.

Uso:
  python3 authority_check.py <artefacto> --role software-architect
  python3 authority_check.py <artefacto> --author <github-user> --team spec/team-roster.yaml
  python3 authority_check.py --list                 # muestra la matriz

Exit 0 = autorizado (o artefacto sin regla en la matriz). Exit 1 = no autorizado.
"""
import os, sys, argparse

DEFAULT_MATRIX = os.path.join("spec", "authority-matrix.yaml")


def load_matrix(path=DEFAULT_MATRIX):
    """Devuelve lista de (path, owner). Sin PyYAML: parseo mínimo del formato plano."""
    rules = []
    try:
        text = open(path, encoding="utf-8").read()
    except FileNotFoundError:
        return rules
    import re
    for m in re.finditer(r"-\s*path:\s*(\S+)\s*\n\s*owner:\s*(\S+)", text):
        rules.append((m.group(1).strip(), m.group(2).strip()))
    return rules


def owner_of(artefacto, rules):
    """Owner del artefacto según la matriz (match exacto o por prefijo de directorio). None si no hay regla."""
    art = artefacto.replace("\\", "/").lstrip("./")
    # Normalizar: la matriz usa rutas relativas al proyecto ("spec/...")
    if "/spec/" in art:
        art = "spec/" + art.split("/spec/", 1)[1]
    for path, owner in rules:
        p = path.rstrip("/")
        if art == p or art.startswith(p + "/"):
            return owner
    return None


def roles_of_author(author, team_path):
    """Roles de un usuario según spec/team-roster.yaml (parseo mínimo)."""
    import re
    try:
        text = open(team_path, encoding="utf-8").read()
    except FileNotFoundError:
        return None  # sin roster no se puede mapear
    m = re.search(rf"^\s*{re.escape(author)}:\s*\[?([^\]\n]+)\]?\s*$", text, re.MULTILINE)
    if not m:
        return []
    return [r.strip() for r in m.group(1).split(",") if r.strip()]


def check(artefacto, role=None, author=None, team=None, matrix=DEFAULT_MATRIX):
    """Devuelve (ok, mensaje)."""
    rules = load_matrix(matrix)
    owner = owner_of(artefacto, rules)
    if owner is None:
        return True, f"SIN REGLA: {artefacto} no está en la matriz — sin restricción de autoría."
    if author is not None:
        roles = roles_of_author(author, team or os.path.join("spec", "team-roster.yaml"))
        if roles is None:
            return False, f"FALLO: no existe team-roster.yaml para mapear a {author} a un rol."
        if owner in roles:
            return True, f"AUTORIZADO: {author} ({', '.join(roles)}) es owner de {artefacto} [{owner}]."
        return False, (f"NO AUTORIZADO: {author} ({', '.join(roles) or 'sin rol'}) no puede emitir "
                       f"{artefacto} — owner requerido: {owner}.")
    if role == owner:
        return True, f"AUTORIZADO: {role} es owner de {artefacto}."
    return False, (f"NO AUTORIZADO: rol '{role}' no puede emitir {artefacto} "
                   f"— owner requerido: {owner}. El artefacto no pasa el gate.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("artefacto", nargs="?")
    ap.add_argument("--role")
    ap.add_argument("--author")
    ap.add_argument("--team")
    ap.add_argument("--map", dest="matrix", default=DEFAULT_MATRIX)
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    if a.list:
        for path, owner in load_matrix(a.matrix):
            print(f"  {path:45s} -> {owner}")
        return
    if not a.artefacto:
        ap.error("falta <artefacto> (o usa --list)")
    if not a.role and not a.author:
        ap.error("indica --role o --author")

    ok, msg = check(a.artefacto, role=a.role, author=a.author, team=a.team, matrix=a.matrix)
    print(msg)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
