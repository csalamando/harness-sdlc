#!/usr/bin/env python3
"""blast_radius_check.py — confinamiento verificado sobre el diff (v2.22, N11b).

El alcance autorizado de un change-request/hotfix se verifica contra hechos:
`git diff` (incluye archivos sin trackear — un agente creando archivos fuera de
alcance también escapa). Todo archivo tocado debe calzar con la lista autorizada.

Uso:
  python3 blast_radius_check.py --allowed "src/api/**, spec/user-stories.md" [--base HEAD]
  python3 blast_radius_check.py --cr spec/change-requests/CR-003.md [--base origin/main]

--cr lee la lista autorizada de la sección "## Alcance autorizado" del
change-request (una ruta/glob por línea, con o sin viñeta).

Exit 0 = diff dentro del alcance. Exit 1 = escape (bloquea el gate, queda en la
auditoría). Exit 2 = no es repo git o base inexistente.
"""
import argparse
import fnmatch
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True


def _audit(spec_dir, **fields):
    try:
        from audit_log import append_event
        append_event(spec_dir, "blast_radius", **fields)
    except Exception:
        pass


def _git(root, *args):
    r = subprocess.run(["git", "-C", root] + list(args),
                       capture_output=True, text=True, timeout=30)
    return r


def changed_files(root, base):
    """Archivos tocados vs base: modificados + nuevos sin trackear."""
    r = _git(root, "diff", "--name-only", base)
    if r.returncode != 0:
        return None
    files = {l.strip() for l in r.stdout.splitlines() if l.strip()}
    r2 = _git(root, "ls-files", "--others", "--exclude-standard")
    if r2.returncode == 0:
        files |= {l.strip() for l in r2.stdout.splitlines() if l.strip()}
    return sorted(files)


def load_allowed(cr_path):
    """Lista autorizada desde la sección '## Alcance autorizado' del CR."""
    text = open(cr_path, encoding="utf-8").read()
    m = re.search(r"##\s*Alcance autorizado\s*\n(.*?)(?=\n##\s|\Z)", text,
                  re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    out = []
    for ln in m.group(1).splitlines():
        ln = ln.strip().lstrip("-*").strip().strip("`")
        if ln and not ln.startswith("#"):
            out.append(ln)
    return out


# Artefactos de gobierno escritos POR SCRIPTS del arnés (auditoría, estado
# derivado, métricas): cambian como efecto de la gobernanza misma, nunca son
# escape de alcance.
EXENTOS = ("spec/audit/", "spec/run-state.yaml", "spec/pipeline-state.md",
           "spec/METRICS.md", "spec/metrics/", "spec/portal/", ".codeintel/")


def matches(path, patterns):
    for p in patterns:
        p = p.replace("\\", "/").strip()
        if not p:
            continue
        if p.endswith("/") and path.startswith(p):
            return p
        if fnmatch.fnmatch(path, p) or fnmatch.fnmatch(path, p.rstrip("/") + "/*"):
            return p
        if path == p:
            return p
    return None


def main():
    ap = argparse.ArgumentParser(description="Confinamiento del diff al alcance autorizado (N11b)")
    ap.add_argument("--allowed", help="globs separados por coma")
    ap.add_argument("--cr", help="change-request con sección '## Alcance autorizado'")
    ap.add_argument("--base", default="HEAD", help="ref base del diff (default HEAD)")
    ap.add_argument("--root", default=".")
    ap.add_argument("--spec-dir", default="spec/")
    a = ap.parse_args()

    allowed = []
    if a.allowed:
        allowed = [x.strip() for x in a.allowed.split(",") if x.strip()]
    elif a.cr:
        allowed = load_allowed(a.cr) or []
        if not allowed:
            print(f"FALLO: {a.cr} sin sección '## Alcance autorizado' con rutas — "
                  "un change-request sin alcance declarado no autoriza nada.")
            sys.exit(1)
    else:
        ap.error("indica --allowed o --cr")

    files = changed_files(a.root, a.base)
    if files is None:
        print(f"FALLO: no se pudo calcular el diff (¿repo git? ¿base '{a.base}' existe?)")
        sys.exit(2)

    exentos = list(EXENTOS)
    if a.cr:  # el propio change-request viaja con el cambio
        rel = os.path.relpath(os.path.abspath(a.cr), os.path.abspath(a.root))
        exentos.append(rel.replace("\\", "/"))
    escapes = [f for f in files
               if not matches(f, exentos) and not matches(f, allowed)]
    fuente = a.cr or "--allowed"
    _audit(a.spec_dir, source=fuente, archivos=str(len(files)),
           violaciones=str(len(escapes)),
           resultado="fallo" if escapes else "ok",
           nota=f"base {a.base}; alcance: {', '.join(allowed)[:200]}")

    if escapes:
        print(f"BLAST RADIUS: {len(escapes)} archivo(s) FUERA del alcance autorizado "
              f"({fuente}):")
        for e in escapes:
            print(f"  - {e}")
        print("El gate queda bloqueado: ampliar el alcance del change-request (con "
              "aprobación) o revertir los archivos que escapan.")
        sys.exit(1)
    print(f"BLAST RADIUS OK: {len(files)} archivo(s) dentro del alcance autorizado "
          f"({len(allowed)} patrón/patrones, base {a.base}).")
    sys.exit(0)


if __name__ == "__main__":
    main()
