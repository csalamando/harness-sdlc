#!/usr/bin/env python3
"""circuit_breaker.py — circuit breaker con estado del arnés SDLC (v2.22, N11a).

Formaliza lo que era prosa ("una sola corrección acotada por gate antes de
escalar a humano"): los reintentos fallidos de un gate quedan en
`spec/run-state.yaml` (contenido JSON — YAML 1.2 compatible), el exceso CONGELA
el artefacto y solo un humano lo descongela. Todo hecho queda en la auditoría.

Uso:
  python3 circuit_breaker.py fail --artefacto spec/x.md --gate "GATE 2" [--max 1] [--motivo "..."]
  python3 circuit_breaker.py ok   --artefacto spec/x.md --gate "GATE 2"
  python3 circuit_breaker.py unfreeze --artefacto spec/x.md --gate "GATE 2" --approved-by <humano>
  python3 circuit_breaker.py status

Exit 1 = congelado (escalar a humano) / hay congelados (status). Exit 0 = ok.
"""
import argparse
import json
import os
import sys

sys.dont_write_bytecode = True


def _load(spec_dir):
    p = os.path.join(spec_dir, "run-state.yaml")
    if os.path.isfile(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"items": {}}


def _save(spec_dir, state):
    os.makedirs(spec_dir, exist_ok=True)
    open(os.path.join(spec_dir, "run-state.yaml"), "w",
         encoding="utf-8").write(json.dumps(state, indent=2, ensure_ascii=False) + "\n")


def _audit(spec_dir, **fields):
    try:
        from audit_log import append_event
        append_event(spec_dir, "circuit_breaker", **fields)
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser(description="Circuit breaker con estado (N11a)")
    ap.add_argument("cmd", choices=["fail", "ok", "unfreeze", "status"])
    ap.add_argument("--artefacto")
    ap.add_argument("--gate", default="")
    ap.add_argument("--max", type=int, default=1,
                    help="correcciones acotadas permitidas antes de congelar (default 1)")
    ap.add_argument("--motivo", default="")
    ap.add_argument("--approved-by", default="")
    ap.add_argument("--spec-dir", default="spec/")
    a = ap.parse_args()
    state = _load(a.spec_dir)
    key = f"{os.path.basename(a.artefacto or '')}@{a.gate}" if a.artefacto else ""

    if a.cmd == "status":
        items = state["items"]
        congelados = [k for k, v in items.items() if v.get("congelado")]
        if not items:
            print("CIRCUIT BREAKER: sin actividad registrada.")
        for k, v in sorted(items.items()):
            print(f"  {k}: {v.get('fallos', 0)} fallo(s)"
                  + (" — CONGELADO, escalar a humano" if v.get("congelado") else ""))
        if congelados:
            print(f"\n{len(congelados)} artefacto(s) congelados — el pipeline no "
                  "avanza hasta que un humano los descongele (unfreeze --approved-by).")
            sys.exit(1)
        sys.exit(0)

    if not a.artefacto or not a.gate:
        print("FALLO: --artefacto y --gate son obligatorios.")
        sys.exit(1)
    try:
        from audit_log import gate_valido
        gn = gate_valido(a.gate)
        if gn is None:
            print(f"FALLO: gate '{a.gate}' fuera del catálogo.")
            sys.exit(1)
        a.gate = gn
        key = f"{os.path.basename(a.artefacto)}@{gn}"
    except ImportError:
        pass

    item = state["items"].setdefault(key, {"fallos": 0, "congelado": False})

    if a.cmd == "fail":
        if item.get("congelado"):
            print(f"CONGELADO: {key} ya excedió sus correcciones acotadas. "
                  "Requiere unfreeze humano — el agente no reintenta más.")
            sys.exit(1)
        item["fallos"] += 1
        from datetime import datetime, timezone
        item["ultimo"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        item["motivo"] = a.motivo
        if item["fallos"] > a.max:
            item["congelado"] = True
            _save(a.spec_dir, state)
            _audit(a.spec_dir, artefacto=os.path.basename(a.artefacto), gate=a.gate,
                   attempts=str(item["fallos"]), nota=a.motivo,
                   resultado="congelado")
            print(f"CIRCUIT BREAKER: {key} CONGELADO tras {item['fallos']} fallo(s) "
                  f"(max {a.max}). Escalar a humano — la máquina deja de reintentar.")
            sys.exit(1)
        _save(a.spec_dir, state)
        _audit(a.spec_dir, artefacto=os.path.basename(a.artefacto), gate=a.gate,
               attempts=str(item["fallos"]), nota=a.motivo, resultado="reintento")
        print(f"Corrección acotada {item['fallos']}/{a.max} autorizada para {key}. "
              "Un fallo más congela.")
        sys.exit(0)

    if a.cmd == "ok":
        state["items"].pop(key, None)
        _save(a.spec_dir, state)
        _audit(a.spec_dir, artefacto=os.path.basename(a.artefacto), gate=a.gate,
               resultado="ok")
        print(f"OK: {key} sin deuda de reintentos.")
        sys.exit(0)

    if a.cmd == "unfreeze":
        if not a.approved_by:
            print("FALLO: unfreeze exige --approved-by <humano> — descongelar es "
                  "una decisión humana auditada.")
            sys.exit(1)
        if not item.get("congelado"):
            print(f"{key} no está congelado.")
            sys.exit(0)
        state["items"].pop(key)
        _save(a.spec_dir, state)
        _audit(a.spec_dir, artefacto=os.path.basename(a.artefacto), gate=a.gate,
               approved_by=a.approved_by, resultado="descongelado")
        print(f"DESCONGELADO por {a.approved_by}: {key}. Queda en la auditoría.")
        sys.exit(0)


if __name__ == "__main__":
    main()
