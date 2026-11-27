#!/usr/bin/env python3
"""diagram_icons.py — caché local y verificable de iconos Diagrams para el IR.

sync  --ir FILE.ir.json  Copia solo los recursos referenciados y actualiza el lock.
check --ir FILE.ir.json  Verifica lock, rutas y SHA-256 sin importar Diagrams.

Los PNG viven en <directorio del IR>/icons/ y el HTML los incrusta como data:.
No se descarga contenido ni se ejecuta Graphviz. Python 3 stdlib puro.
"""
import argparse
import hashlib
import importlib.metadata
import json
import shutil
import sys
from pathlib import Path

from diagram_ir import icon_cache_path, icon_parts, load_ir

DIAGRAMS_VERSION = "0.25.1"
LOCK_NAME = "index.json"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def referenced_icons(ir):
    """IDs únicos y ordenados; rechaza rutas fuera del contrato canónico."""
    iconos = {n.get("icono") for n in ir.get("nodos", []) if n.get("icono")}
    invalidos = sorted(i for i in iconos if not icon_parts(i))
    if invalidos:
        raise ValueError("iconos inválidos (provider.categoria.recurso): " + ", ".join(invalidos))
    return sorted(iconos)


def icons_dir(ir_path):
    return Path(ir_path).resolve().parent / "icons"


def lock_path(ir_path):
    return icons_dir(ir_path) / LOCK_NAME


def read_lock(ir_path):
    path = lock_path(ir_path)
    if not path.is_file():
        return {"diagrams_version": DIAGRAMS_VERSION, "iconos": {}}
    with open(path, encoding="utf-8") as f:
        lock = json.load(f)
    if not isinstance(lock.get("iconos"), dict):
        raise ValueError(f"lock inválido: {path} no contiene un objeto 'iconos'")
    return lock


def relative_name(icono):
    provider, category, name = icon_parts(icono)
    return f"{provider}/{category}/{name}.png"


def package_resource(icono):
    """Resuelve explícitamente en Diagrams; una caché previa nunca lo sustituye."""
    try:
        import diagrams
    except ImportError as exc:
        raise RuntimeError(
            f"faltan recursos en caché; instale diagrams=={DIAGRAMS_VERSION} y repita sync"
        ) from exc
    try:
        installed = importlib.metadata.version("diagrams")
    except importlib.metadata.PackageNotFoundError as exc:
        raise RuntimeError(f"no se puede determinar la versión de Diagrams; se exige {DIAGRAMS_VERSION}") from exc
    if installed != DIAGRAMS_VERSION:
        raise RuntimeError(f"Diagrams {installed} instalado; sync exige exactamente {DIAGRAMS_VERSION}")
    resources = Path(diagrams.__file__).resolve().parent.parent / "resources"
    source = resources / relative_name(icono)
    if not source.is_file():
        raise RuntimeError(f"Diagrams {DIAGRAMS_VERSION} no contiene el recurso '{icono}'")
    return source


def cache_is_current(icono, ir_path, lock):
    entry = (lock.get("iconos") or {}).get(icono)
    cached = icon_cache_path(icono, Path(ir_path).resolve().parent)
    return bool(
        lock.get("diagrams_version") == DIAGRAMS_VERSION
        and entry
        and entry.get("path") == relative_name(icono)
        and cached.is_file()
        and entry.get("sha256") == sha256(cached)
    )


def sync(ir_path):
    ir_path = Path(ir_path).resolve()
    ir = load_ir(ir_path)
    iconos = referenced_icons(ir)
    if not iconos:
        print("OK: el IR no referencia iconos; no se modifica la caché")
        return 0
    lock = read_lock(ir_path)
    entries = dict(lock["iconos"])
    copied = []
    cached = []
    for icono in iconos:
        destination = icon_cache_path(icono, ir_path.parent)
        if cache_is_current(icono, ir_path, lock):
            cached.append(icono)
            continue
        source = package_resource(icono)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        entries[icono] = {"path": relative_name(icono), "sha256": sha256(destination)}
        copied.append(icono)
    # Conserva entradas de otros IR que comparten este directorio de caché.
    new_lock = {"diagrams_version": DIAGRAMS_VERSION, "iconos": dict(sorted(entries.items()))}
    target = lock_path(ir_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(new_lock, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8", newline="\n")
    print(f"OK: {len(copied)} icono(s) sincronizados, {len(cached)} ya vigentes; lock {target}")
    for icono in copied:
        print(f"  + {icono}")
    return 0


def check(ir_path):
    ir_path = Path(ir_path).resolve()
    ir = load_ir(ir_path)
    iconos = referenced_icons(ir)
    if not iconos:
        print("OK: el IR no referencia iconos")
        return 0
    target = lock_path(ir_path)
    if not target.is_file():
        print(f"ERROR: falta {target}; ejecute diagram_icons.py sync --ir <archivo>", file=sys.stderr)
        return 1
    try:
        lock = read_lock(ir_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    errs = []
    if lock.get("diagrams_version") != DIAGRAMS_VERSION:
        errs.append(f"lock declara Diagrams {lock.get('diagrams_version')!r}; se exige {DIAGRAMS_VERSION}")
    entries = lock.get("iconos", {})
    for icono in iconos:
        entry = entries.get(icono)
        cached = icon_cache_path(icono, ir_path.parent)
        if not entry:
            errs.append(f"{icono}: falta entrada en {LOCK_NAME}")
            continue
        if entry.get("path") != relative_name(icono):
            errs.append(f"{icono}: ruta de lock no canónica {entry.get('path')!r}")
            continue
        if not cached.is_file():
            errs.append(f"{icono}: falta {cached}")
            continue
        actual = sha256(cached)
        if entry.get("sha256") != actual:
            errs.append(f"{icono}: SHA-256 no coincide (lock {entry.get('sha256')}, actual {actual})")
    if errs:
        print("CACHÉ DE ICONOS INVÁLIDA:", file=sys.stderr)
        for err in errs:
            print(f"- {err}", file=sys.stderr)
        return 1
    print(f"OK: {len(iconos)} icono(s) con caché y SHA-256 vigentes; Diagrams no requerido")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Sincroniza y verifica iconos Diagrams del IR")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("sync", "check"):
        p = sub.add_parser(name)
        p.add_argument("--ir", required=True)
    args = parser.parse_args(argv)
    try:
        return sync(args.ir) if args.cmd == "sync" else check(args.ir)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
