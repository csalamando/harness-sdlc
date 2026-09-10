#!/usr/bin/env python3
"""pipeline_state.py — estado del pipeline DERIVADO, nunca narrado (v2.22, N7).

`spec/pipeline-state.md` se genera desde hechos: matriz de autoridad + recibos
vigentes + memoria de auditoría + detect_stack. Nadie lo edita a mano y nadie
emite recibo sobre él (certificar narración era la brecha B-14): si el archivo
en disco difiere del derivado, `--check` falla en CI.

Uso:
  python3 pipeline_state.py [--spec-dir spec/] [--root .]   # regenera el archivo
  python3 pipeline_state.py --check                         # anti-drift (CI)

Exit 0 = generado / sin drift. Exit 1 = drift detectado.
"""
import argparse
import datetime
import glob
import hashlib
import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_REL = "pipeline-state.md"

GATES = ("GATE 0", "GATE 1", "GATE 2", "GATE 2.5", "GATE 3")


def _receipts(spec_dir):
    d = os.path.join(spec_dir, "receipts")
    out = {}
    for f in sorted(glob.glob(os.path.join(d, "*.receipt.json"))):
        try:
            rec = json.load(open(f, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        base = os.path.basename(rec.get("artefacto", f)).replace("\\", "/")
        out.setdefault(base, rec)  # el primero en orden de archivo gana
    return out


def _detect_stack(root):
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, "detect_stack.py"),
                            "--project-dir", root], capture_output=True, text=True,
                           timeout=60)
        lineas = [l.strip() for l in r.stdout.splitlines() if l.strip()]
        return " | ".join(lineas[:3]) if lineas else f"exit {r.returncode}"
    except (OSError, subprocess.TimeoutExpired):
        return "no disponible"


def build(spec_dir, root):
    from authority_check import load_matrix
    rules = load_matrix(os.path.join(spec_dir, "authority-matrix.yaml"))
    recs = _receipts(spec_dir)

    filas, sin_recibo = [], 0
    for path, owner in rules:
        if path.endswith("/"):
            continue  # directorios: se reportan en bloque aparte
        rel = path[len("spec/"):] if path.startswith("spec/") else path
        ap = os.path.join(spec_dir, rel)
        if not os.path.isfile(ap):
            filas.append((rel, owner, "—", "no creado", "", ""))
            continue
        rec = recs.get(os.path.basename(rel))
        if not rec:
            sin_recibo += 1
            filas.append((rel, owner, "—", "**sin recibo**", "", ""))
            continue
        estado = rec.get("estado", "?")
        h = hashlib.sha256(open(ap, "rb").read()).hexdigest()
        if estado == "vigente" and rec.get("sha256") != h:
            estado = "invalidado (hash)"
        filas.append((rel, owner, rec.get("gate", "?"), estado,
                      rec.get("approved_by", "") or rec.get("rol", ""),
                      str(rec.get("emitido", ""))[:10]))

    # Estado por gate: hay recibo vigente registrado con ese gate (desde la auditoría)
    gates_ok = {}
    audit = os.path.join(spec_dir, "audit", "events.jsonl")
    n_eventos, ultimo = 0, "—"
    if os.path.isfile(audit):
        for ln in open(audit, encoding="utf-8"):
            ln = ln.strip()
            if not ln:
                continue
            n_eventos += 1
            try:
                e = json.loads(ln)
            except json.JSONDecodeError:
                continue
            ultimo = f"{e.get('evento', '?')} · {str(e.get('ts', ''))[:10]}"
            if e.get("evento") == "emit" and e.get("gate") in GATES:
                gates_ok[e["gate"]] = gates_ok.get(e["gate"], 0) + 1

    gh = ["| Gate | Emisiones auditadas |", "|---|---|"]
    for g in GATES:
        gh.append(f"| {g} | {gates_ok.get(g, 0)} |")

    th = ["| Artefacto | Owner | Gate | Estado | Aprobador/rol | Emitido |", "|---|---|---|---|---|---|"]
    for f in filas:
        th.append("| " + " | ".join(f) + " |")

    return "\n".join([
        "# Pipeline State — DERIVADO",
        "",
        "<!-- GENERADO por pipeline_state.py desde matriz de autoridad + recibos +",
        "     memoria de auditoría. NO editar a mano; drift = fallo de CI (--check). -->",
        "",
        f"Regenerado: {datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}",
        f"Stack (detect_stack): {_detect_stack(root)}",
        "",
        f"## Auditoría: {n_eventos} eventos · último: {ultimo}",
        "",
        "## Gates",
        *gh,
        "",
        "## Artefactos gobernados (matriz de autoridad)",
        *th,
        "",
        f"Artefactos creados sin recibo: **{sin_recibo}**",
        "",
    ])


def main():
    ap = argparse.ArgumentParser(description="Estado del pipeline derivado (N7)")
    ap.add_argument("--spec-dir", default="spec/")
    ap.add_argument("--root", default=".")
    ap.add_argument("--check", action="store_true", help="anti-drift para CI")
    a = ap.parse_args()
    contenido = build(a.spec_dir, a.root)
    out = os.path.join(a.spec_dir, OUT_REL)
    if a.check:
        actual = open(out, encoding="utf-8").read() if os.path.isfile(out) else None
        _sin_ts = lambda t: "\n".join(l for l in (t or "").splitlines()
                                      if not l.startswith("Regenerado:"))
        if _sin_ts(actual) != _sin_ts(contenido):
            print(f"DRIFT: {out} no coincide con el estado derivado de recibos + "
                  "auditoría. Regenerar: pipeline_state.py")
            sys.exit(1)
        print("PIPELINE-STATE sin drift.")
        sys.exit(0)
    os.makedirs(a.spec_dir, exist_ok=True)
    open(out, "w", encoding="utf-8").write(contenido)
    print(f"PIPELINE-STATE derivado -> {out} (nunca editado a mano, nunca con recibo)")


if __name__ == "__main__":
    main()
