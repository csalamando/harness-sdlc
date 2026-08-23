#!/usr/bin/env python3
"""diagram_render.py — Render headless de diagramas a SVG/PNG (v2.6).

Fuentes soportadas:
  - .drawio → SVG/PNG vía drawio-desktop CLI (el SVG puede embeber el fuente:
    la imagen generada sigue siendo editable en app.diagrams.net).
  - .mmd / bloques Mermaid en Markdown → SVG vía @mermaid-js/mermaid-cli (mmdc).
    Con un .md de entrada, mmdc renderiza cada bloque ```mermaid y reescribe
    el documento referenciando las imágenes (ideal para doc-as-code).

Filosofía del arnés: los motores son OPCIONALES. Si ninguno está instalado,
el script informa y sale 0 (el fuente .drawio/.mmd versionado es el entregable;
el render es una vista derivada, nunca bloquea — igual que drawio sin MCP o
code_intel sin índice).

Uso:
  python3 diagram_render.py render <archivo.drawio|.mmd|.md> [--fmt svg|png]
                                    [--out <ruta>] [--page <nombre>]
  python3 diagram_render.py engines            # qué motores hay disponibles
  python3 diagram_render.py render-dir <dir> [--fmt svg]   # todos los .drawio

Notas:
  - drawio-desktop en Linux headless (CI) puede requerir xvfb-run; el script
    lo usa automáticamente si el render directo falla y xvfb-run existe.
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


def find_drawio():
    """Binario de drawio-desktop según plataforma."""
    for cand in ("drawio", "drawio-desktop", "draw.io"):
        if which(cand):
            return which(cand)
    for path in ("/Applications/draw.io.app/Contents/MacOS/draw.io",
                 "/opt/drawio/drawio", "/usr/local/bin/drawio"):
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def find_mmdc():
    if which("mmdc"):
        return which("mmdc")
    if which("npx"):
        return None  # se invocará vía npx
    return None


def have_npx():
    return bool(which("npx"))


def run(cmd, timeout=180):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def render_drawio(src, out, fmt, page=None):
    bin_path = find_drawio()
    if not bin_path:
        return None, "drawio-desktop no instalado (https://github.com/jgraph/drawio-desktop/releases)"
    cmd = [bin_path, "-x", "-f", fmt, "--crop", "-o", out]
    if page:
        cmd += ["-p", page]
    if fmt == "svg":
        cmd.append("--embed-svg-images")
    cmd.append(src)
    r = run(cmd)
    if r.returncode != 0 and which("xvfb-run"):
        r = run(["xvfb-run", "-a"] + cmd)
    if r.returncode != 0:
        return False, (r.stderr or r.stdout).strip()[:400]
    return True, out


def render_mermaid(src, out, fmt):
    mmdc = find_mmdc()
    if mmdc:
        cmd = [mmdc]
    elif have_npx():
        cmd = ["npx", "-y", "@mermaid-js/mermaid-cli"]
    else:
        return None, "mmdc no instalado (npm i -g @mermaid-js/mermaid-cli) ni npx disponible"
    cmd += ["-i", src, "-o", out]
    if src.endswith(".mmd"):
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
    d = find_drawio()
    print(f"  drawio-desktop : {'OK — ' + d if d else 'no instalado'}")
    m = find_mmdc()
    if m:
        print(f"  mmdc           : OK — {m}")
    elif have_npx():
        print("  mmdc           : vía npx (se descargará @mermaid-js/mermaid-cli en el primer uso)")
    else:
        print("  mmdc           : no instalado")
    if not d and not m and not have_npx():
        print("\nSin motores: los fuentes .drawio/.mmd quedan versionados igual "
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
    if ext == ".drawio":
        ok, msg = render_drawio(src, out, fmt, a.page)
    elif ext in (".mmd", ".md"):
        ok, msg = render_mermaid(src, out, fmt)
    else:
        print(f"ERROR: extensión no soportada ({ext}); usa .drawio, .mmd o .md",
              file=sys.stderr)
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


def cmd_render_dir(a):
    if not os.path.isdir(a.dir):
        print(f"ERROR: no existe el directorio {a.dir}", file=sys.stderr)
        return 1
    fallos = 0
    renders = 0
    for name in sorted(os.listdir(a.dir)):
        if name.endswith(".drawio"):
            src = os.path.join(a.dir, name)
            out = os.path.join(a.dir, os.path.splitext(name)[0] + "." + a.fmt)
            ok, msg = render_drawio(src, out, a.fmt)
            if ok:
                renders += 1
                print(f"OK: {name} → {os.path.basename(out)}")
            elif ok is False:
                fallos += 1
                print(f"ERROR: {name}: {msg}", file=sys.stderr)
            else:
                print(f"SKIP: {msg}")
                break
    print(f"\n{renders} renderizados, {fallos} con error.")
    return 1 if fallos else 0


def main():
    p = argparse.ArgumentParser(description="Render headless de diagramas (opcional, con degradación elegante).")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render", help="Renderiza un .drawio, .mmd o .md con bloques Mermaid")
    r.add_argument("archivo")
    r.add_argument("--fmt", choices=["svg", "png"], default="svg")
    r.add_argument("--out")
    r.add_argument("--page", help="Nombre de página (solo .drawio multipágina)")
    r.set_defaults(f=cmd_render)
    e = sub.add_parser("engines", help="Lista motores de render disponibles")
    e.set_defaults(f=cmd_engines)
    d = sub.add_parser("render-dir", help="Renderiza todos los .drawio de un directorio")
    d.add_argument("dir")
    d.add_argument("--fmt", choices=["svg", "png"], default="svg")
    d.set_defaults(f=cmd_render_dir)
    a = p.parse_args()
    return a.f(a)


if __name__ == "__main__":
    sys.exit(main())
