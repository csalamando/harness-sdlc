#!/usr/bin/env python3
"""audit_verify.py — Verificador de la memoria de auditoria (ADR-004, v2.21).

Comprueba que spec/audit/events.jsonl sea una traza integra:
  1. El log existe y no esta vacio; el primer evento es audit_init con
     prev_hash genesis.
  2. Cada linea es JSON valido con campos obligatorios: seq, ts, evento,
     harness_version, prev_hash, hash.
  3. ts es UTC ISO-8601 CON zona horaria (un hecho sin cuando verificable
     no es auditable).
  4. seq es monotonico desde 1.
  5. La cadena prev_hash -> hash es continua y cada hash recalcula.

Exit 0 = traza integra. Exit 1 = manipulacion o inconsistencia (se lista).
Stdlib puro. Pensado para CI y para Fase 8.
"""
import os, sys, json, argparse, re

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from audit_log import GENESIS_PREV, event_hash, log_path  # noqa: E402

REQUIRED = ("seq", "ts", "evento", "harness_version", "prev_hash", "hash")
TS_TZ = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\+\d{2}:\d{2}|Z)$")


def main():
    ap = argparse.ArgumentParser(description="Verifica la integridad del log de auditoria")
    ap.add_argument("--spec-dir", default="spec/")
    a = ap.parse_args()

    p = log_path(a.spec_dir) if os.path.isdir(os.path.join(a.spec_dir, "audit")) \
        else os.path.join(a.spec_dir, "audit", "events.jsonl")
    errors = []
    events = []

    if not os.path.isfile(p):
        print(f"SIN LOG: no existe {p} — la memoria de auditoria no fue inicializada "
              f"(audit_log.py init).")
        sys.exit(1)

    for i, line in enumerate(open(p, encoding="utf-8"), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            errors.append(f"linea {i}: JSON invalido")

    if not events:
        print(f"LOG VACIO: {p} — sin hechos registrados.")
        sys.exit(1)

    prev_hash = GENESIS_PREV
    for idx, ev in enumerate(events, start=1):
        tag = f"evento #{idx} ({ev.get('evento', '?')})"
        for k in REQUIRED:
            if k not in ev:
                errors.append(f"{tag}: falta campo obligatorio '{k}'")
        if errors and errors[-1].startswith(tag):
            continue  # sin campos completos no se puede verificar mas de este evento
        if ev["seq"] != idx:
            errors.append(f"{tag}: seq={ev['seq']}, esperado {idx} (evento eliminado o reordenado)")
        if not TS_TZ.match(str(ev["ts"])):
            errors.append(f"{tag}: ts '{ev['ts']}' no es UTC ISO-8601 con zona")
        if ev["prev_hash"] != prev_hash:
            errors.append(f"{tag}: prev_hash no encadena con el evento anterior "
                          f"(traza reescrita)")
        if event_hash(ev) != ev["hash"]:
            errors.append(f"{tag}: hash no recalcula (contenido manipulado)")
        if idx == 1 and ev["evento"] != "audit_init":
            errors.append(f"evento #1: es '{ev['evento']}', debe ser audit_init (genesis)")
        prev_hash = ev["hash"]

    if errors:
        print(f"AUDITORIA ROTA ({len(errors)} problema(s)) en {p}:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    tipos = {}
    for ev in events:
        tipos[ev["evento"]] = tipos.get(ev["evento"], 0) + 1
    resumen = ", ".join(f"{k}: {v}" for k, v in sorted(tipos.items()))
    print(f"AUDITORIA INTEGRA: {len(events)} eventos, cadena verificada ({resumen}).")
    sys.exit(0)


if __name__ == "__main__":
    main()
