#!/usr/bin/env python3
"""audit_log.py — Memoria de auditoria del arnes (ADR-004, v2.21).

Traza append-only de HECHOS de gobierno en spec/audit/events.jsonl, separada de
la memoria de trabajo (sdlc-memory, evolutiva). Un hecho nunca se edita: una
correccion es un evento compensatorio nuevo.

Garantias (stdlib puro, cero dependencias):
  - Cadena de hash: cada evento lleva prev_hash (SHA-256 del evento anterior,
    genesis = "0"*64). Reescribir o reordenar el pasado rompe la cadena y lo
    detecta audit_verify.py.
  - Todo evento lleva ts en UTC ISO-8601 con zona y harness_version: un hecho
    sin cuando ni bajo que version de las reglas ocurrio no es auditable.

Eventos nucleo: audit_init (genesis), emit, invalidado, revocado, use,
bootstrap, harness_upgrade, freestyle.

Uso CLI:
  python3 audit_log.py init --proyecto <nombre> [--spec-dir spec/]
  python3 audit_log.py append --evento <tipo> [--spec-dir spec/]
      [--artefacto X] [--gate G] [--rol R] [--reason T] [--relation R]
      [--approved-by U] [--nota T] [--source git-history]

Uso como modulo (lo usan receipt.py y demas scripts del arnes):
  from audit_log import append_event
  append_event(spec_dir, "emit", artefacto="spec/x.md", gate="GATE 1", ...)
"""
import os, sys, json, hashlib, argparse, datetime, re

GENESIS_PREV = "0" * 64
EVENTOS_NUCLEO = {"audit_init", "emit", "invalidado", "revocado", "use",
                  "bootstrap", "harness_upgrade", "freestyle",
                  "arch_lint", "contract_diff", "circuit_breaker", "blast_radius"}


def gate_norm(gate):
    """Forma canonica: mayusculas, guiones a espacios ('GATE-0' -> 'GATE 0')."""
    return (gate or "").upper().replace("-", " ").strip()


def gate_fase(gate):
    """Catalogo unico gate -> fase (v2.21, N8): una sola fuente para receipt.py,
    skill_metrics.py y sprint_review.py. Normaliza variantes ('GATE-1' == 'GATE 1'),
    SPRINT-* -> fase 8 (archivo) y FASE-N -> N. Desconocido -> '?'."""
    g = gate_norm(gate)
    m = {"GATE 0": "0", "GATE 1": "3", "GATE 2": "5", "GATE 2.5": "5", "GATE 3": "6"}
    if g in m:
        return m[g]
    if re.match(r"SPRINT\s*\d+", g):
        return "8"
    f = re.match(r"FASE\s*(\d+)", g)
    if f:
        return f.group(1)
    return "?"


# ── Catalogo de gates validos (v2.21, N3) ────────────────────────────────────
# Un recibo solo puede emitirse para un gate del catalogo: nada de gates
# inventados ('gate2', 'SPRINT-5' mal escrito, etc.) que burlaban la gobernanza.
GATES_FIJOS = {"GATE 0", "GATE 1", "GATE 2", "GATE 2.5", "GATE 3"}
# Gates que exigen aprobador humano registrado (--approved-by): la aprobacion
# humana deja de ser narracion. SPRINT-* (cierre de sprint) tambien es humano.
GATES_HUMANOS = {"GATE 0", "GATE 1", "GATE 3"}


def gate_valido(gate):
    """Devuelve el gate normalizado si pertenece al catalogo; None si no."""
    g = gate_norm(gate)
    if g in GATES_FIJOS:
        return g
    if re.fullmatch(r"SPRINT\s*\d+", g) or re.fullmatch(r"FASE\s*\d+", g):
        return re.sub(r"\s+", " ", g)
    return None


def gate_es_humano(gate):
    g = gate_norm(gate)
    return g in GATES_HUMANOS or re.fullmatch(r"SPRINT\s*\d+", g) is not None

# Campos opcionales reconocidos (se omiten si llegan vacios)
CAMPOS = ("artefacto", "gate", "rol", "reason", "relation", "approved_by",
          "nota", "source", "sha256", "sha256_anterior", "sha256_nuevo",
          "skill", "fase", "modo", "auto", "attempts", "tokens_src",
          "version_anterior", "version_nueva", "proyecto",
          "reglas", "archivos", "violaciones", "resultado")


# Version embebida de respaldo: se usa cuando el script corre vendorado en un
# proyecto (scripts/ plano, sin SKILL.md junto). Actualizar en cada release;
# el self-test verifica que coincide con el frontmatter del orquestador.
FALLBACK_VERSION = "2.33.0"


def harness_version():
    """Version del arnes instalado (frontmatter del orquestador).

    Fallback: version embebida — un script vendorado no encuentra SKILL.md
    y la auditoria exige harness_version en TODO evento (audit_verify)."""
    md = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "SKILL.md")
    if os.path.isfile(md):
        m = re.search(r'^harness-version:\s*"?([^"\n]+)"?\s*$',
                      open(md, encoding="utf-8", errors="replace").read(), re.M)
        if m:
            return m.group(1).strip()
    return FALLBACK_VERSION


def log_path(spec_dir):
    d = os.path.join(spec_dir, "audit")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "events.jsonl")


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _canonical(ev):
    """JSON canonico del evento SIN el campo hash (base de la cadena)."""
    return json.dumps({k: v for k, v in ev.items() if k != "hash"},
                      sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def event_hash(ev):
    return hashlib.sha256(_canonical(ev).encode("utf-8")).hexdigest()


def last_event(spec_dir):
    p = log_path(spec_dir)
    if not os.path.isfile(p):
        return None
    last = None
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    last = json.loads(line)
                except json.JSONDecodeError:
                    return {"__corrupto__": True}
    return last


def append_event(spec_dir, evento, **fields):
    """Anexa un hecho al log. Devuelve el evento completo (con hash).

    El primer evento DEBE ser audit_init (init). Los campos vacios se omiten.
    El artefacto debe pasarse como ruta relativa al proyecto con '/' (ver
    receipt.py:_rel) — nunca rutas absolutas locales (leccion v2.20.1).
    """
    prev = last_event(spec_dir)
    if prev is None:
        if evento != "audit_init":
            raise RuntimeError("Log de auditoria no inicializado: el primer evento "
                               "debe ser audit_init (audit_log.py init).")
        seq, prev_hash = 1, GENESIS_PREV
    else:
        if prev.get("__corrupto__"):
            raise RuntimeError("Log de auditoria corrupto: linea no-JSON. "
                               "Revisar spec/audit/events.jsonl (audit_verify.py).")
        if evento == "audit_init":
            raise RuntimeError("El log de auditoria ya existe: audit_init solo es "
                               "valido como evento genesis.")
        seq, prev_hash = int(prev.get("seq", 0)) + 1, prev.get("hash", "")

    ev = {"seq": seq, "ts": utc_now(), "evento": evento}
    hv = harness_version()
    if hv:
        ev["harness_version"] = hv
    for k in CAMPOS:
        v = fields.get(k)
        if v not in (None, ""):
            ev[k] = v
    ev["prev_hash"] = prev_hash
    ev["hash"] = event_hash(ev)

    p = log_path(spec_dir)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
    return ev


def cmd_init(a):
    try:
        ev = append_event(a.spec_dir, "audit_init", proyecto=a.proyecto,
                          nota=a.nota or "Genesis de la memoria de auditoria (ADR-004)")
    except RuntimeError as e:
        print(f"FALLO: {e}"); sys.exit(1)
    print(f"AUDIT LOG INICIALIZADO: {log_path(a.spec_dir)}")
    print(f"  proyecto: {a.proyecto}  ts: {ev['ts']}  harness: {ev.get('harness_version', '?')}")
    print(f"  genesis hash: {ev['hash'][:16]}...")


def cmd_append(a):
    fields = {k: getattr(a, k.replace("-", "_"), None) for k in
              ("artefacto", "gate", "rol", "reason", "relation", "approved-by",
               "nota", "source")}
    fields = {k.replace("-", "_"): v for k, v in fields.items() if v}
    try:
        ev = append_event(a.spec_dir, a.evento, **fields)
    except RuntimeError as e:
        print(f"FALLO: {e}"); sys.exit(1)
    if a.evento not in EVENTOS_NUCLEO:
        print(f"  (nota: '{a.evento}' no es un evento nucleo; queda registrado igual)")
    print(f"EVENTO {ev['evento']} #{ev['seq']} registrado ({ev['ts']})  hash: {ev['hash'][:16]}...")


def main():
    ap = argparse.ArgumentParser(description="Memoria de auditoria append-only (ADR-004)")
    ap.add_argument("--spec-dir", default="spec/")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init", help="evento genesis (una sola vez por proyecto)")
    p.add_argument("--proyecto", required=True)
    p.add_argument("--nota", default="")
    p = sub.add_parser("append", help="registrar un hecho")
    p.add_argument("--evento", required=True)
    for f in ("artefacto", "gate", "rol", "reason", "relation", "approved-by",
              "nota", "source"):
        p.add_argument(f"--{f}", default="")
    a = ap.parse_args()
    {"init": cmd_init, "append": cmd_append}[a.cmd](a)


if __name__ == "__main__":
    main()
