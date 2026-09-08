#!/usr/bin/env python3
"""diagram_render.py — Render headless de diagramas Mermaid a SVG/PNG (v2.6).

Fuentes soportadas:
  - .mmd / bloques Mermaid en Markdown → SVG vía @mermaid-js/mermaid-cli (mmdc).
    Con un .md de entrada, mmdc renderiza cada bloque ```mermaid y reescribe
    el documento referenciando las imágenes (ideal para doc-as-code).

Filosofía del arnés: los motores son OPCIONALES. Si mmdc no está instalado,
el script informa y sale 0 (el fuente .mmd/.md versionado es el entregable;
el render es una vista derivada, nunca bloquea).

v2.20: se retira el soporte .drawio (el arnés ya no genera drawio).

Uso:
  python3 diagram_render.py render <archivo.mmd|.md> [--fmt svg|png]
                                    [--out <ruta>] [--tema claro|oscuro]
  python3 diagram_render.py engines            # qué motores hay disponibles

Notas:
  - mmdc requiere Chrome (puppeteer); en contenedores usar
    PUPPETEER_ARGS='--no-sandbox' si es root.
"""
import argparse
import os
import shutil
import subprocess
import sys


def which(name):
    return shutil.which(name)


def find_mmdc():
    if which("mmdc"):
        return which("mmdc")
    if which("npx"):
        return None  # se invocará vía npx
    return None


def have_npx():
    return bool(which("npx"))


def render_mermaid(src, out, fmt, tema=None):
    mmdc = find_mmdc()
    if mmdc:
        cmd = [mmdc]
    elif have_npx():
        cmd = ["npx", "-y", "@mermaid-js/mermaid-cli"]
    else:
        return None, "mmdc no instalado (npm i -g @mermaid-js/mermaid-cli) ni npx disponible"
    cmd += ["-i", src, "-o", out]
    # Lenguaje visual común (v2.19): --tema fija el tema mermaid y el fondo.
    if tema == "oscuro":
        cmd += ["-t", "dark", "-b", "#0b1220"]
    elif tema == "claro":
        cmd += ["-t", "default", "-b", "white"]
    elif src.endswith(".mmd"):
        cmd += ["-b", "transparent"]
    env = dict(os.environ)
    if os.geteuid() == 0 if hasattr(os, "geteuid") else False:
        env.setdefault("PUPPETEER_ARGS", "--no-sandbox")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)
    if r.returncode != 0:
        return False, (r.stderr or r.stdout).strip()[:400]
    return True, out


def default_out(src, fmt):
    base, ext = os.path.splitext(src)
    if ext == ".md":
        return base + ".rendered.md"
    return base + "." + fmt


def cmd_engines(_a):
    print("Motores de render disponibles:")
    m = find_mmdc()
    if m:
        print(f"  mmdc           : OK — {m}")
    elif have_npx():
        print("  mmdc           : vía npx (se descargará @mermaid-js/mermaid-cli en el primer uso)")
    else:
        print("  mmdc           : no instalado")
        print("\nSin motor: los fuentes .mmd/.md quedan versionados igual "
              "(capacidad opcional, nunca bloquea).")
    return 0


def cmd_render(a):
    src = a.archivo
    if not os.path.isfile(src):
        print(f"ERROR: no existe {src}", file=sys.stderr)
        return 1
    fmt = a.fmt
    out = a.out or default_out(src, fmt)
    ext = os.path.splitext(src)[1].lower()
    if ext in (".mmd", ".md"):
        ok, msg = render_mermaid(src, out, fmt, a.tema)
    else:
        print(f"ERROR: extensión no soportada ({ext}); usa .mmd o .md "
              "(el arnés ya no genera .drawio desde v2.20)", file=sys.stderr)
        return 1
    if ok is None:
        print(f"SKIP: {msg}")
        print(f"El fuente {src} sigue siendo el entregable versionado.")
        return 0
    if ok:
        print(f"OK: {src} → {msg}")
        return 0
    print(f"ERROR al renderizar: {msg}", file=sys.stderr)
    return 1


def main():
    p = argparse.ArgumentParser(description="Render headless de Mermaid (opcional, con degradación elegante).")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render", help="Renderiza un .mmd o .md con bloques Mermaid")
    r.add_argument("archivo")
    r.add_argument("--fmt", choices=["svg", "png"], default="svg")
    r.add_argument("--out")
    r.add_argument("--tema", choices=["claro", "oscuro"],
                   help="Tema mermaid (dark/default + fondo coherente con el IR)")
    r.set_defaults(f=cmd_render)
    e = sub.add_parser("engines", help="Lista motores de render disponibles")
    e.set_defaults(f=cmd_engines)
    a = p.parse_args()
    return a.f(a)


if __name__ == "__main__":
    sys.exit(main())
