#!/usr/bin/env python3
"""contract_diff.py — compatibilidad de contratos OpenAPI del arnés SDLC (v2.21, N10).

Blinda la interfaz pública: compara el contrato viejo contra el nuevo y clasifica
cada cambio como BREAKING o compatible. Un breaking change sin bump de versión
mayor (`info.version`) es un gate bloqueado — el "cambio rupturista que nadie
declaró" deja de ser posible en silencio.

Uso:
  python3 contract_diff.py --old spec/api-contract.yaml --new spec/api-contract.yaml~
  python3 contract_diff.py --contra-git spec/api-contract.yaml   # contra HEAD

Exit 0 = compatible (o breaking declarado con bump mayor). Exit 1 = breaking sin
declarar. Exit 2 = no se pudo comparar (sin versión anterior, YAML inválido...).

Breaking detectado: path eliminado, operación eliminada, parámetro eliminado o
recién requerido, tipo de parámetro cambiado, propiedad requerida nueva en
requestBody, propiedad eliminada o con tipo cambiado en respuestas.

PyYAML es requerido para parsear; si no está, exit 2 con mensaje claro —
un control que no se puede ejecutar no es control (mismo criterio que arch_lint).

Cada comparación registra evento `contract_diff` en la memoria de auditoría
(ADR-004) cuando ésta existe.
"""
import argparse
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True

METHODS = ("get", "put", "post", "delete", "patch", "head", "options", "trace")


def _audit(spec_dir, **fields):
    try:
        from audit_log import append_event
        append_event(spec_dir, "contract_diff", **fields)
    except Exception:
        pass


def load_spec(text, nombre="contrato"):
    try:
        import yaml
    except ImportError:
        print("FALLO: PyYAML no instalado — no se puede verificar la compatibilidad "
              "del contrato. Un control que no se puede ejecutar no es control.")
        sys.exit(2)
    try:
        return yaml.safe_load(text) or {}
    except Exception as e:
        print(f"FALLO: {nombre} no es YAML válido: {e}")
        sys.exit(2)


def major_of(spec):
    v = str((spec.get("info") or {}).get("version", ""))
    m = re.match(r"^(\d+)", v)
    return int(m.group(1)) if m else None


def _params(op):
    return {p.get("name"): p for p in (op or {}).get("parameters", [])
            if isinstance(p, dict) and p.get("name")}


def _props(schema):
    return ((schema or {}).get("properties") or {}), set((schema or {}).get("required") or [])


def _content_schema(media):
    return ((media or {}).get("application/json") or {}).get("schema") or {}


def diff_specs(old, new):
    """Devuelve (breaking, additions): listas de descripciones legibles."""
    breaking, additions = [], []
    old_paths, new_paths = old.get("paths") or {}, new.get("paths") or {}

    for path in old_paths:
        if path not in new_paths:
            breaking.append(f"path eliminado: {path}")
    for path in new_paths:
        if path not in old_paths:
            additions.append(f"path nuevo: {path}")

    for path in set(old_paths) & set(new_paths):
        old_ops = {m: (old_paths[path] or {}).get(m) for m in METHODS
                   if (old_paths[path] or {}).get(m)}
        new_ops = {m: (new_paths[path] or {}).get(m) for m in METHODS
                   if (new_paths[path] or {}).get(m)}
        for m in old_ops:
            if m not in new_ops:
                breaking.append(f"operación eliminada: {m.upper()} {path}")
        for m in new_ops:
            if m not in old_ops:
                additions.append(f"operación nueva: {m.upper()} {path}")
        for m in set(old_ops) & set(new_ops):
            op_old, op_new = old_ops[m], new_ops[m]
            label = f"{m.upper()} {path}"
            po, pn = _params(op_old), _params(op_new)
            for name in po:
                if name not in pn:
                    breaking.append(f"{label}: parámetro eliminado '{name}'")
                else:
                    t_old = ((po[name].get("schema") or {}).get("type"))
                    t_new = ((pn[name].get("schema") or {}).get("type"))
                    if t_old != t_new:
                        breaking.append(f"{label}: tipo del parámetro '{name}' "
                                        f"cambió {t_old}→{t_new}")
            for name in pn:
                if name not in po:
                    if pn[name].get("required"):
                        breaking.append(f"{label}: parámetro requerido nuevo '{name}'")
                    else:
                        additions.append(f"{label}: parámetro opcional nuevo '{name}'")
            # requestBody: propiedades requeridas nuevas = breaking
            so, ro = _props(_content_schema((op_old.get("requestBody") or {}).get("content")))
            sn, rn = _props(_content_schema((op_new.get("requestBody") or {}).get("content")))
            for req in sorted(rn - ro):
                breaking.append(f"{label}: propiedad requerida nueva en requestBody '{req}'")
            for p_ in so:
                if p_ in sn and (so[p_] or {}).get("type") != (sn[p_] or {}).get("type"):
                    breaking.append(f"{label}: tipo de propiedad de requestBody '{p_}' "
                                    f"cambió {(so[p_] or {}).get('type')}→{(sn[p_] or {}).get('type')}")
            # respuestas: propiedad eliminada o tipo cambiado = breaking
            for code in (op_old.get("responses") or {}):
                if code not in (op_new.get("responses") or {}):
                    breaking.append(f"{label}: respuesta {code} eliminada")
                    continue
                rso, _ = _props(_content_schema(((op_old["responses"][code]) or {}).get("content")))
                rsn, _ = _props(_content_schema(((op_new["responses"][code]) or {}).get("content")))
                for p_ in rso:
                    if p_ not in rsn:
                        breaking.append(f"{label}: propiedad '{p_}' eliminada de la respuesta {code}")
                    elif (rso[p_] or {}).get("type") != (rsn[p_] or {}).get("type"):
                        breaking.append(f"{label}: tipo de propiedad '{p_}' de la respuesta "
                                        f"{code} cambió {(rso[p_] or {}).get('type')}→{(rsn[p_] or {}).get('type')}")
    return breaking, additions


def git_show_head(artefacto):
    """Contenido del artefacto en HEAD, o None si no hay repo/versión previa."""
    d = os.path.dirname(os.path.abspath(artefacto))
    try:
        root = subprocess.run(["git", "-C", d, "rev-parse", "--show-toplevel"],
                              capture_output=True, text=True, timeout=15)
        if root.returncode != 0:
            return None
        rel = os.path.relpath(os.path.abspath(artefacto), root.stdout.strip())
        old = subprocess.run(["git", "-C", d, "show", "HEAD:" + rel.replace(os.sep, "/")],
                             capture_output=True, text=True, timeout=15)
        return old.stdout if old.returncode == 0 and old.stdout.strip() else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def main():
    ap = argparse.ArgumentParser(description="Compatibilidad de contratos OpenAPI (N10)")
    ap.add_argument("artefacto", nargs="?", help="contrato nuevo (con --contra-git)")
    ap.add_argument("--old", help="contrato anterior (archivo)")
    ap.add_argument("--new", help="contrato nuevo (archivo)")
    ap.add_argument("--contra-git", action="store_true",
                    help="compara el artefacto contra su versión en HEAD")
    ap.add_argument("--spec-dir", default="spec/")
    a = ap.parse_args()

    if a.contra_git:
        new_path = a.artefacto
        old_text = git_show_head(new_path)
        if old_text is None:
            print("contract_diff: sin versión previa en git — primera versión del "
                  "contrato, nada que comparar.")
            sys.exit(2)
        new_text = open(new_path, encoding="utf-8").read()
    elif a.old and a.new:
        old_text = open(a.old, encoding="utf-8").read()
        new_text = open(a.new, encoding="utf-8").read()
        new_path = a.new
    else:
        ap.error("indica --old/--new o bien --contra-git <artefacto>")

    old, new = load_spec(old_text, "contrato anterior"), load_spec(new_text, "contrato nuevo")
    breaking, additions = diff_specs(old, new)
    mo, mn = major_of(old), major_of(new)

    resultado = "ok"
    if breaking and not (mo is not None and mn is not None and mn > mo):
        resultado = "fallo"
    _audit(a.spec_dir, artefacto=os.path.basename(new_path),
           violaciones=str(len(breaking)), resultado=resultado,
           nota=f"version {mo}->{mn}, +{len(additions)} compatibles")

    print(f"CONTRACT DIFF ({os.path.basename(new_path)}): "
          f"{len(breaking)} breaking, {len(additions)} compatibles, "
          f"versión {mo or '?'} → {mn or '?'}")
    for b in breaking:
        print(f"  BREAKING: {b}")
    for ad in additions:
        print(f"  compatible: {ad}")
    if resultado == "fallo":
        print("\nGATE BLOQUEADO: hay breaking changes y la versión mayor no subió. "
              "Declarar el bump en info.version (versión mayor nueva) o revertir "
              "los cambios rupturistas. Un breaking change no declarado no pasa.")
        sys.exit(1)
    if breaking:
        print("\nBreaking changes declarados correctamente (bump de versión mayor).")
    sys.exit(0)


if __name__ == "__main__":
    main()
