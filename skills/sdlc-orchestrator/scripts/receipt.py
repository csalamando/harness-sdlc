#!/usr/bin/env python3
"""receipt.py — Recibos de aprobacion vinculados al contenido (patron RDD adaptado).

Principio: confiar en lo que el sistema puede derivar, no en la narracion del agente.
Cuando un gate pasa, se emite un recibo con el SHA-256 exacto del artefacto. Los gates
downstream VERIFICAN el recibo: si el artefacto cambio un byte, el recibo ya no aplica
y la aprobacion queda invalidada automaticamente.

Uso:
  python3 receipt.py emit <artefacto> --gate <gate> [--tipo <tipo>] [--role <rol>]
      [--tokens-in N --tokens-out M --tokens-src reportado|estimado] [--attempts K]
      Emite spec/receipts/<artefacto>.receipt.json tras validar con gate_checker.
      Si existe spec/authority-matrix.yaml y el artefacto tiene owner declarado,
      --role es OBLIGATORIO y debe coincidir con el owner (un dev no puede emitir
      el recibo de un ADR; un arquitecto no puede emitir el de user-stories).
      Telemetria (v2.4, opcional): tokens reportados por la plataforma del agente
      (--tokens-src reportado) o estimados por chars/4 del artefacto
      (--tokens-src estimado sin valores -> el script los calcula). --attempts
      registra en que intento de gate se aprobo (1 = a la primera).
  python3 receipt.py verify <artefacto>
      Exit 0 si el recibo existe y el hash coincide. Exit 1 si falta o esta invalidado.
  python3 receipt.py status [--spec-dir spec/]
      Lista recibos y su vigencia.
  python3 receipt.py revoke <artefacto>
      Revoca manualmente (p. ej. ante change-request).
"""
import os, sys, json, hashlib, argparse, datetime, subprocess

def harness_version():
    """Versión del arnés instalado (frontmatter del orquestador); None si no se puede leer."""
    md = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "SKILL.md")
    if not os.path.isfile(md):
        return None
    import re as _re
    m = _re.search(r'^harness-version:\s*"?([^"\n]+)"?\s*$',
                   open(md, encoding="utf-8", errors="replace").read(), _re.M)
    return m.group(1).strip() if m else None


def receipts_dir(spec_dir):
    d = os.path.join(spec_dir, "receipts")
    os.makedirs(d, exist_ok=True)
    return d

def receipt_path(spec_dir, artefacto):
    base = os.path.basename(artefacto).replace("/", "_")
    return os.path.join(receipts_dir(spec_dir), f"{base}.receipt.json")

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def cmd_emit(a):
    if not os.path.isfile(a.artefacto):
        print(f"FALLO: no existe {a.artefacto}"); sys.exit(1)
    # Autoridad: si la matriz cubre el artefacto, el rol emisor debe ser el owner
    try:
        from authority_check import owner_of, load_matrix
        owner = owner_of(a.artefacto, load_matrix(os.path.join(a.spec_dir, "authority-matrix.yaml")))
    except ImportError:
        owner = None
    if owner is not None:
        if not a.role:
            print(f"FALLO: {a.artefacto} tiene owner declarado ({owner}) en la matriz de autoridad. "
                  f"Indica --role para emitir el recibo."); sys.exit(1)
        if a.role != owner:
            print(f"NO AUTORIZADO: rol '{a.role}' no puede emitir el recibo de {a.artefacto} "
                  f"— owner requerido: {owner}. El gate no reconoce esta aprobación."); sys.exit(1)
    if a.tipo:
        checker = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gate_checker.py")
        r = subprocess.run(["python3", checker, a.artefacto, "--tipo", a.tipo], capture_output=True, text=True)
        print(r.stdout.strip())
        if r.returncode != 0:
            print("Gate no pasado: no se emite recibo."); sys.exit(1)
    # Telemetria v2.4: tokens estimados por chars/4 si se pidio y no se dieron valores
    t_in, t_out = a.tokens_in, a.tokens_out
    if a.tokens_src == "estimado" and not t_in and not t_out:
        t_out = max(1, os.path.getsize(a.artefacto) // 4)
    rec = {
        "artefacto": os.path.abspath(a.artefacto),
        "sha256": sha256(a.artefacto),
        "gate": a.gate,
        "tipo": a.tipo or "",
        "rol": a.role or "",
        "emitido": datetime.datetime.now().isoformat(timespec="seconds"),
        "estado": "vigente",
    }
    hv = harness_version()
    if hv:
        rec["harness_version"] = hv
    if a.tokens_src:
        rec["tokens_src"] = a.tokens_src
        if t_in:
            rec["tokens_in"] = int(t_in)
        if t_out:
            rec["tokens_out"] = int(t_out)
    if a.attempts and int(a.attempts) > 1:
        rec["attempts"] = int(a.attempts)
    p = receipt_path(a.spec_dir, a.artefacto)
    open(p, "w", encoding="utf-8").write(json.dumps(rec, indent=2, ensure_ascii=False))
    print(f"RECIBO EMITIDO ({a.gate}): {a.artefacto}\n  sha256: {rec['sha256'][:16]}...  -> {p}")

def cmd_verify(a):
    p = receipt_path(a.spec_dir, a.artefacto)
    if not os.path.isfile(p):
        print(f"SIN RECIBO: {a.artefacto} nunca paso su gate."); sys.exit(1)
    rec = json.load(open(p, encoding="utf-8"))
    if rec.get("estado") != "vigente":
        print(f"RECIBO REVOCADO ({rec['gate']}): {a.artefacto}"); sys.exit(1)
    if not os.path.isfile(a.artefacto):
        print(f"INVALIDADO: el artefacto {a.artefacto} ya no existe."); sys.exit(1)
    actual = sha256(a.artefacto)
    if actual != rec["sha256"]:
        rec["estado"] = "invalidado"
        rec["invalidado"] = datetime.datetime.now().isoformat(timespec="seconds")
        open(p, "w", encoding="utf-8").write(json.dumps(rec, indent=2, ensure_ascii=False))
        print(f"RECIBO INVALIDADO: el contenido de {a.artefacto} cambio desde la aprobacion ({rec['gate']}).")
        print("  El gate debe volver a ejecutarse y emitirse un recibo nuevo.")
        sys.exit(1)
    # Autoridad: el rol emisor registrado debe seguir siendo el owner según la matriz vigente
    try:
        from authority_check import owner_of, load_matrix
        owner = owner_of(a.artefacto, load_matrix(os.path.join(a.spec_dir, "authority-matrix.yaml")))
    except ImportError:
        owner = None
    if owner is not None and rec.get("rol") and rec["rol"] != owner:
        print(f"RECIBO NO VALIDO: fue emitido por rol '{rec['rol']}' pero el owner de {a.artefacto} "
              f"es '{owner}' según la matriz vigente. Re-emitir con el rol correcto.")
        sys.exit(1)
    print(f"RECIBO VIGENTE ({rec['gate']}, emitido {rec['emitido']}): {a.artefacto}")

def cmd_status(a):
    d = receipts_dir(a.spec_dir)
    files = [f for f in os.listdir(d) if f.endswith(".receipt.json")]
    if not files:
        print("Sin recibos emitidos."); return
    print("| Artefacto | Gate | Rol | Estado | Hash coincide |")
    print("|---|---|---|---|---|")
    for f in sorted(files):
        rec = json.load(open(os.path.join(d, f), encoding="utf-8"))
        art = rec["artefacto"]
        match = "-"
        if os.path.isfile(art):
            match = "si" if sha256(art) == rec["sha256"] else "NO (invalidado)"
        print(f"| {os.path.basename(art)} | {rec['gate']} | {rec.get('rol', '-')} | {rec['estado']} | {match} |")

def cmd_revoke(a):
    p = receipt_path(a.spec_dir, a.artefacto)
    if not os.path.isfile(p):
        print(f"Sin recibo que revocar para {a.artefacto}"); sys.exit(1)
    rec = json.load(open(p, encoding="utf-8"))
    rec["estado"] = "revocado"
    rec["revocado"] = datetime.datetime.now().isoformat(timespec="seconds")
    open(p, "w", encoding="utf-8").write(json.dumps(rec, indent=2, ensure_ascii=False))
    print(f"RECIBO REVOCADO: {a.artefacto}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec-dir", default="spec/")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("emit"); p.add_argument("artefacto"); p.add_argument("--gate", required=True); p.add_argument("--tipo", default=""); p.add_argument("--role", default="")
    p.add_argument("--tokens-in", type=int, default=0); p.add_argument("--tokens-out", type=int, default=0)
    p.add_argument("--tokens-src", choices=["reportado", "estimado"], default="")
    p.add_argument("--attempts", type=int, default=1)
    p = sub.add_parser("verify"); p.add_argument("artefacto")
    sub.add_parser("status")
    p = sub.add_parser("revoke"); p.add_argument("artefacto")
    a = ap.parse_args()
    {"emit": cmd_emit, "verify": cmd_verify, "status": cmd_status, "revoke": cmd_revoke}[a.cmd](a)

if __name__ == "__main__":
    main()
