#!/usr/bin/env python3
"""tdd_order_check.py — evidencia de orden TDD a partir del historial git (v2.15).

El TDD intra-sesion no se puede probar desde fuera; lo que SI queda en git es
el orden de los commits. Convencion del arnes:

    test(HU-xxx): red      <- el test que falla, primero
    feat(HU-xxx): green    <- la implementacion que lo pasa, despues

Este script verifica, por cada HU que aparece en los mensajes de commit de un
rango (tipicamente un PR), que el primer commit de test preceda al primer
commit de codigo. No bloquea por HUs sin par test/feat (a veces el TDD ocurre
en un solo commit o la HU se cerro en otro PR): solo reporta orden invertido.

Uso:
    python3 tdd_order_check.py [--range origin/main...HEAD] [--warn]

    --range   rango git a inspeccionar (default: HEAD~20..HEAD)
    --warn    exit 0 siempre (modo CI visible-no-bloqueante)
"""
import argparse
import re
import subprocess
import sys

HU = re.compile(r"\b([A-Z]+-\d+)\b")
KIND = re.compile(r"^(test|feat|fix|refactor)\(")


def commits(rango):
    out = subprocess.run(
        ["git", "log", "--reverse", "--format=%H%x09%ci%x09%s", rango],
        capture_output=True, text=True)
    if out.returncode != 0:
        print(f"ERROR git log: {out.stderr.strip()}", file=sys.stderr)
        sys.exit(2)
    res = []
    for line in out.stdout.splitlines():
        h, fecha, msg = line.split("\t", 2)
        m = KIND.match(msg)
        ids = HU.findall(msg)
        if m and ids:
            res.append({"hash": h[:8], "fecha": fecha, "kind": m.group(1),
                        "hus": ids, "msg": msg})
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--range", dest="rango", default="HEAD~20..HEAD")
    ap.add_argument("--warn", action="store_true")
    a = ap.parse_args()

    cs = commits(a.rango)
    if not cs:
        print(f"Sin commits test/feat con HU en {a.rango} — nada que verificar.")
        sys.exit(0)

    por_hu = {}
    for c in cs:
        for hu in c["hus"]:
            por_hu.setdefault(hu, []).append(c)

    violaciones, verificadas, sin_par = [], [], []
    for hu, hist in sorted(por_hu.items()):
        tests = [c for c in hist if c["kind"] == "test"]
        code = [c for c in hist if c["kind"] in ("feat", "fix")]
        if not tests or not code:
            sin_par.append(hu)
            continue
        if hist.index(tests[0]) < hist.index(code[0]):
            verificadas.append(hu)
        else:
            violaciones.append((hu, code[0], tests[0]))

    print(f"TDD por commits — rango {a.rango}")
    print(f"  HUs con evidencia de orden correcto (test antes que codigo): {len(verificadas)}"
          + (f" ({', '.join(verificadas)})" if verificadas else ""))
    if sin_par:
        print(f"  HUs sin par test/feat en el rango (no verificables): {len(sin_par)}"
              f" ({', '.join(sin_par)})")
    for hu, c, t in violaciones:
        print(f"  VIOLACION {hu}: codigo '{c['msg']}' ({c['hash']}) precede al test"
              f" '{t['msg']}' ({t['hash']}) — el test debio existir primero (red -> green)")

    if violaciones:
        print(f"\n{len(violaciones)} HU(s) con orden TDD invertido.")
        sys.exit(0 if a.warn else 1)
    print("\nSin violaciones de orden TDD.")
    sys.exit(0)


if __name__ == "__main__":
    main()
