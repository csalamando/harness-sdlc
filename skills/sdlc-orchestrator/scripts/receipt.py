#!/usr/bin/env python3
"""receipt.py — Recibos de aprobacion vinculados al contenido (patron RDD adaptado).

Principio: confiar en lo que el sistema puede derivar, no en la narracion del agente.
Cuando un gate pasa, se emite un recibo con el SHA-256 exacto del artefacto. Los gates
downstream VERIFICAN el recibo: si el artefacto cambio un byte, el recibo ya no aplica
y la aprobacion queda invalidada automaticamente.

Uso:
  python3 receipt.py emit <artefacto> --gate <gate> [--tipo <tipo>]
      Emite spec/receipts/<artefacto>.receipt.json tras validar con gate_checker.
  python3 receipt.py verify <artefacto>
      Exit 0 si el recibo existe y el hash coincide. Exit 1 si falta o esta invalidado.
  python3 receipt.py status [--spec-dir spec/]
      Lista recibos y su vigencia.
  python3 receipt.py revoke <artefacto>
      Revoca manualmente (p. ej. ante change-request).
"""
import os, sys, json, hashlib, argparse, datetime, subprocess

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
    if a.tipo:
        checker = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gate_checker.py")
        r = subprocess.run(["python3", checker, a.artefacto, "--tipo", a.tipo], capture_output=True, text=True)
        print(r.stdout.strip())
        if r.returncode != 0:
            print("Gate no pasado: no se emite recibo."); sys.exit(1)
    rec = {
        "artefacto": os.path.abspath(a.artefacto),
        "sha256": sha256(a.artefacto),
        "gate": a.gate,
        "tipo": a.tipo or "",
        "emitido": datetime.datetime.now().isoformat(timespec="seconds"),
        "estado": "vigente",
    }
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
    print(f"RECIBO VIGENTE ({rec['gate']}, emitido {rec['emitido']}): {a.artefacto}")

def cmd_status(a):
    d = receipts_dir(a.spec_dir)
    files = [f for f in os.listdir(d) if f.endswith(".receipt.json")]
    if not files:
        print("Sin recibos emitidos."); return
    print("| Artefacto | Gate | Estado | Hash coincide |")
    print("|---|---|---|---|")
    for f in sorted(files):
        rec = json.load(open(os.path.join(d, f), encoding="utf-8"))
        art = rec["artefacto"]
        match = "-"
        if os.path.isfile(art):
            match = "si" if sha256(art) == rec["sha256"] else "NO (invalidado)"
        print(f"| {os.path.basename(art)} | {rec['gate']} | {rec['estado']} | {match} |")

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
    p = sub.add_parser("emit"); p.add_argument("artefacto"); p.add_argument("--gate", required=True); p.add_argument("--tipo", default="")
    p = sub.add_parser("verify"); p.add_argument("artefacto")
    sub.add_parser("status")
    p = sub.add_parser("revoke"); p.add_argument("artefacto")
    a = ap.parse_args()
    {"emit": cmd_emit, "verify": cmd_verify, "status": cmd_status, "revoke": cmd_revoke}[a.cmd](a)

if __name__ == "__main__":
    main()
