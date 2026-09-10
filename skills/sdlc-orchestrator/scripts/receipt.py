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
  python3 receipt.py revoke <artefacto> --reason "<causa>" [--relation supersedes|conflicts_with]
      Revoca manualmente (p. ej. ante change-request). La razón es OBLIGATORIA
      (ADR-004, v2.21): queda en la memoria de auditoría spec/audit/events.jsonl.

ADR-004 (v2.21): emit/invalidado/revocado anexan un hecho append-only con cadena
de hash a la memoria de auditoría (audit_log.py). Los .receipt.json son el estado
operativo derivado; la verdad histórica es el log.
"""
import os, sys, json, hashlib, argparse, datetime, subprocess

# ADR-004 (v2.21): toda emision/invalidacion/revocacion deja un hecho en la
# memoria de auditoria (spec/audit/events.jsonl, append-only con cadena de hash).
try:
    from audit_log import append_event, gate_valido, gate_es_humano
except ImportError:
    append_event = None
    gate_valido = gate_es_humano = None

def _audit(spec_dir, evento, **fields):
    """Best-effort visible: si el log no esta disponible/inicializado, se advierte
    (nunca silencioso). El drift de scripts vendored queda expuesto aqui hasta
    que harness_doctor --check-vendored lo vuelva bloqueante."""
    if append_event is None:
        print("  ⚠ audit_log.py no encontrado junto a receipt.py — el hecho NO queda "
              "en la memoria de auditoria (scripts del arnes incompletos o desactualizados).")
        return
    try:
        append_event(spec_dir, evento, **fields)
    except RuntimeError as e:
        print(f"  ⚠ hecho '{evento}' no registrado en auditoria: {e}")

def _rel(spec_dir, artefacto):
    """Ruta relativa al proyecto con '/' — portable y sin filtrar rutas locales
    (leccion v2.20.1). El recibo historico conserva la absoluta; el evento usa esta."""
    root = os.path.dirname(os.path.abspath(spec_dir))
    try:
        return os.path.relpath(os.path.abspath(artefacto), root).replace(os.sep, "/")
    except ValueError:
        return os.path.basename(artefacto)

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
    # Catalogo de gates (v2.21, N3): nada de gates inventados; los gates humanos
    # (0/1/3 y cierres SPRINT-*) exigen aprobador registrado — la aprobacion
    # humana deja de ser narracion.
    if gate_valido is not None:
        gn = gate_valido(a.gate)
        if gn is None:
            print(f"FALLO: gate '{a.gate}' no esta en el catalogo del arnes "
                  f"(GATE 0/1/2/2.5/3, SPRINT-N, FASE-N). Un recibo solo puede "
                  f"emitirse para un gate reconocido."); sys.exit(1)
        if gn != a.gate:
            print(f"  (gate normalizado: '{a.gate}' -> '{gn}')")
            a.gate = gn
        if gate_es_humano(gn) and not a.approved_by:
            print(f"FALLO: {gn} es un gate HUMANO — exige --approved-by <identidad> "
                  f"del aprobador. El agente no puede auto-aprobarse."); sys.exit(1)
    else:
        print("  ⚠ audit_log.py no encontrado junto a receipt.py — emitiendo SIN "
              "validar el catalogo de gates ni registrar auditoria (scripts "
              "incompletos o desactualizados).")
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
    if a.approved_by:
        rec["approved_by"] = a.approved_by
    if a.tokens_src:
        rec["tokens_src"] = a.tokens_src
        if t_in:
            rec["tokens_in"] = int(t_in)
        if t_out:
            rec["tokens_out"] = int(t_out)
    if a.attempts and int(a.attempts) > 1:
        rec["attempts"] = int(a.attempts)
    p = receipt_path(a.spec_dir, a.artefacto)
    prev_estado = None
    if os.path.isfile(p):
        try:
            prev_estado = json.load(open(p, encoding="utf-8")).get("estado")
        except (json.JSONDecodeError, OSError):
            pass
    open(p, "w", encoding="utf-8").write(json.dumps(rec, indent=2, ensure_ascii=False))
    print(f"RECIBO EMITIDO ({a.gate}): {a.artefacto}\n  sha256: {rec['sha256'][:16]}...  -> {p}")
    # ADR-004: hecho en la memoria de auditoria. Si habia un recibo previo no
    # vigente, esta emision es una RE-emision (retrabajo) — queda explícito.
    _audit(a.spec_dir, "emit", artefacto=_rel(a.spec_dir, a.artefacto), gate=a.gate,
           rol=a.role or "", sha256=rec["sha256"], approved_by=a.approved_by or "",
           attempts=str(a.attempts) if a.attempts and int(a.attempts) > 1 else "",
           nota="re-emision (recibo previo no vigente)" if prev_estado in ("invalidado", "revocado") else "")
    # v2.16: auto-registro de la activacion en usage.jsonl — el recibo ES evidencia
    # de que la skill produjo; cierra la brecha de metricas muertas cuando el agente
    # olvida 'skill_metrics.py use'. skill_metrics report deduplica contra usos manuales.
    # v2.21 (ADR-004): la activacion TAMBIEN queda como evento 'use' en la memoria de
    # auditoria, con la fase derivada del catalogo unico gate_fase (adios fase '?').
    if a.role:
        try:
            from audit_log import gate_fase as _gate_fase
        except ImportError:
            _gate_fase = None
        if _gate_fase:
            fase = _gate_fase(a.gate)
        else:
            GATE_FASE = {"GATE 0": "0", "GATE 1": "3", "GATE 2": "5", "GATE 2.5": "5", "GATE 3": "6"}
            fase = GATE_FASE.get(a.gate, "?")
        skill = a.role.replace("sdlc-", "")
        ev = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), "tipo": "use",
              "skill": skill, "fase": fase, "modo": "", "auto": "receipt"}
        md = os.path.join(a.spec_dir, "metrics")
        os.makedirs(md, exist_ok=True)
        with open(os.path.join(md, "usage.jsonl"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
        _audit(a.spec_dir, "use", skill=skill, fase=fase, auto="receipt")

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
        _audit(a.spec_dir, "invalidado", artefacto=_rel(a.spec_dir, a.artefacto),
               gate=rec.get("gate", ""), rol=rec.get("rol", ""),
               sha256_anterior=rec["sha256"], sha256_nuevo=actual)
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
    problemas = []
    for f in sorted(files):
        rec = json.load(open(os.path.join(d, f), encoding="utf-8"))
        art = rec["artefacto"]
        match = "-"
        if os.path.isfile(art):
            match = "si" if sha256(art) == rec["sha256"] else "NO (invalidado)"
        else:
            problemas.append(f"{os.path.basename(art)}: artefacto no existe")
        if rec["estado"] != "vigente":
            problemas.append(f"{os.path.basename(art)}: estado {rec['estado']}")
        if match.startswith("NO"):
            problemas.append(f"{os.path.basename(art)}: hash no coincide (invalidado sin re-emitir)")
        print(f"| {os.path.basename(art)} | {rec['gate']} | {rec.get('rol', '-')} | {rec['estado']} | {match} |")
    # v2.21 (N3): --strict convierte el estado en veredicto ejecutable para CI
    if getattr(a, "strict", False):
        if problemas:
            print(f"\nSTRICT: {len(problemas)} problema(s) — los gates no estan en verde:")
            for p_ in problemas:
                print(f"  - {p_}")
            sys.exit(1)
        print("\nSTRICT: todos los recibos vigentes y coincidentes.")

def cmd_revoke(a):
    if not a.reason:
        print("FALLO: revocar exige --reason (ADR-004: una revocación sin causa "
              "declarada no es auditoría, es ruido)."); sys.exit(1)
    p = receipt_path(a.spec_dir, a.artefacto)
    if not os.path.isfile(p):
        print(f"Sin recibo que revocar para {a.artefacto}"); sys.exit(1)
    rec = json.load(open(p, encoding="utf-8"))
    rec["estado"] = "revocado"
    rec["revocado"] = datetime.datetime.now().isoformat(timespec="seconds")
    open(p, "w", encoding="utf-8").write(json.dumps(rec, indent=2, ensure_ascii=False))
    _audit(a.spec_dir, "revocado", artefacto=_rel(a.spec_dir, a.artefacto),
           gate=rec.get("gate", ""), rol=rec.get("rol", ""), reason=a.reason,
           relation=a.relation or "", approved_by=a.approved_by or "",
           sha256_anterior=rec.get("sha256", ""))
    print(f"RECIBO REVOCADO: {a.artefacto} — razón registrada en la memoria de auditoría.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec-dir", default="spec/")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("emit"); p.add_argument("artefacto"); p.add_argument("--gate", required=True); p.add_argument("--tipo", default=""); p.add_argument("--role", default="")
    p.add_argument("--tokens-in", type=int, default=0); p.add_argument("--tokens-out", type=int, default=0)
    p.add_argument("--tokens-src", choices=["reportado", "estimado"], default="")
    p.add_argument("--attempts", type=int, default=1)
    p.add_argument("--approved-by", default="", help="identidad del aprobador humano (gates humanos)")
    p = sub.add_parser("verify"); p.add_argument("artefacto")
    p = sub.add_parser("status"); p.add_argument("--strict", action="store_true",
        help="exit 1 si hay recibos no vigentes, artefactos faltantes o hashes que no coinciden (CI)")
    p = sub.add_parser("revoke"); p.add_argument("artefacto")
    p.add_argument("--reason", required=True, help="causa de la revocación (obligatoria, ADR-004)")
    p.add_argument("--relation", choices=["supersedes", "conflicts_with"], default="")
    p.add_argument("--approved-by", default="")
    a = ap.parse_args()
    {"emit": cmd_emit, "verify": cmd_verify, "status": cmd_status, "revoke": cmd_revoke}[a.cmd](a)

if __name__ == "__main__":
    main()
