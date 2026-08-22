#!/usr/bin/env python3
"""mem.py — Motor de memoria del arnes SDLC (v1.2: scopes + gobierno de politicas).

Diseno: Git-nativo. Las memorias son markdown con frontmatter (FUENTE DE VERDAD).
SQLite+FTS5 en .index/ es un indice DERIVADO reconstruible (`reindex`).

Scopes (precedencia: lo especifico vence a lo general):
  project -> ./spec/memory        (versionada con la spec; default)
  user    -> ~/.sdlcmem/user      (aprendizajes personales cross-proyecto)
  org     -> ~/.sdlcmem/org       (patrones y POLITICAS de la organizacion)

Tipo `policy`: lineamiento normativo en scope org. enforcement=mandatory exige,
en cada proyecto, attestation `compliant` o desviacion APROBADA y vigente antes
del GATE 1. Las desviaciones siguen flujo request -> approve|reject, con expiracion.

Comandos: save, search, get, timeline, conflicts, session, promote,
          policy list|check|attest, deviation request|approve|reject|list,
          reindex, doctor, export.
Overrides: --root, SDLCMEM_ROOT (project), SDLCMEM_USER_ROOT, SDLCMEM_ORG_ROOT.
"""
import os, re, sys, json, sqlite3, argparse, datetime, unicodedata, glob

TYPES = ["decision", "bug", "learning", "architecture", "incident", "context", "policy"]
SCOPES = ["project", "user", "org"]
SECRET_PATTERNS = [
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}",
    r"sk-[A-Za-z0-9]{20,}",
    r"(?i)bearer\s+[A-Za-z0-9_\-\.]{20,}",
]

# ---------- resolucion de raices por scope ----------

def scope_root(a, scope):
    if scope == "project":
        return getattr(a, "root", None) or os.environ.get("SDLCMEM_ROOT") or os.path.join(os.getcwd(), "spec", "memory")
    if scope == "user":
        return os.environ.get("SDLCMEM_USER_ROOT") or os.path.expanduser("~/.sdlcmem/user")
    return os.environ.get("SDLCMEM_ORG_ROOT") or os.path.expanduser("~/.sdlcmem/org")

def active_scopes(a):
    s = getattr(a, "scope", "") or ""
    return [s] if s in SCOPES else SCOPES

def paths(root):
    return (os.path.join(root, "entries"), os.path.join(root, ".index"),
            os.path.join(root, ".index", "mem.db"), os.path.join(root, "sessions"))

def db(root):
    entries, idx, dbp, sessions = paths(root)
    os.makedirs(entries, exist_ok=True); os.makedirs(idx, exist_ok=True); os.makedirs(sessions, exist_ok=True)
    con = sqlite3.connect(dbp)
    con.executescript("""
    CREATE TABLE IF NOT EXISTS entries(id TEXT PRIMARY KEY, title TEXT, type TEXT, project TEXT,
        created TEXT, session TEXT, file TEXT, tags TEXT, links TEXT);
    CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(id, title, body, tokenize='unicode61');
    CREATE TABLE IF NOT EXISTS relations(src TEXT, dst TEXT, relation TEXT, status TEXT DEFAULT 'judged',
        note TEXT DEFAULT '', PRIMARY KEY(src, dst, relation));
    CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, project TEXT, started TEXT, ended TEXT, summary TEXT DEFAULT '');
    """)
    return con

# ---------- parseo de entradas ----------

FRONT = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)

def parse_entry(path):
    text = open(path, encoding="utf-8").read()
    m = FRONT.match(text)
    if not m: return None
    meta, body = m.group(1), m.group(2)
    e = {"file": path, "body": body.strip(), "title": os.path.basename(path)}
    for line in meta.splitlines():
        if ":" in line and not line.startswith((" ", "-")):
            k, v = line.split(":", 1)
            e[k.strip()] = v.strip().strip('"')
    for k in ("tags", "links", "supersedes"):
        e[k] = [x.strip() for x in e.get(k, "").strip("[]").split(",") if x.strip()]
    mt = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    if mt: e["title"] = mt.group(1).strip()
    return e

def slug(s, n=40):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return (re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:n] or "memoria")

def next_id(root, prefix):
    entries = paths(root)[0]
    today = datetime.date.today().strftime("%Y%m%d")
    n = 0
    if os.path.isdir(entries):
        for f in os.listdir(entries):
            m = re.match(rf"{prefix}-{today}-(\d+)", f)
            if m: n = max(n, int(m.group(1)))
    return f"{prefix}-{today}-{n+1:03d}"

TEMPLATE = """---
id: {id}
type: {type}
project: {project}
created: {created}
session: {session}
tags: [{tags}]
links: [{links}]
supersedes: [{supersedes}]{extra_meta}
---
# {title}

**What**: {what}

**Why**: {why}

**Where**: {where}

**Key details**: {details}

**Learned**: {learned}
"""

def current_session(root):
    con = db(root)
    row = con.execute("SELECT id FROM sessions WHERE ended IS NULL ORDER BY started DESC LIMIT 1").fetchone()
    con.close()
    return row[0] if row else ""

def fts_candidates(con, mid, title):
    tokens = [t for t in re.findall(r"\w{4,}", title.lower())][:6]
    if not tokens: return []
    try:
        return con.execute("SELECT id, title FROM fts WHERE fts MATCH ? AND id != ? LIMIT 5",
                           (" OR ".join(tokens), mid)).fetchall()
    except sqlite3.OperationalError:
        return []

def index_entry(con, e):
    con.execute("INSERT OR REPLACE INTO entries VALUES (?,?,?,?,?,?,?,?,?)",
        (e["id"], e.get("title", ""), e.get("type", ""), e.get("project", ""), e.get("created", ""),
         e.get("session", ""), e["file"], ",".join(e.get("tags", [])), ",".join(e.get("links", []))))
    con.execute("DELETE FROM fts WHERE id=?", (e["id"],))
    con.execute("INSERT INTO fts VALUES (?,?,?)", (e["id"], e.get("title", ""), e.get("body", "")))
    for dst in e.get("supersedes", []):
        con.execute("INSERT OR REPLACE INTO relations VALUES (?,?,?,?,?)", (e["id"], dst, "supersedes", "judged", "declarada al guardar"))
    con.commit()

def contains_secret(text):
    return any(re.search(p, text) for p in SECRET_PATTERNS)

# ---------- comandos base ----------

def cmd_save(a):
    scope = a.scope or "project"
    if a.type == "policy" and scope != "org":
        print("Las politicas (type=policy) solo pueden guardarse en scope org."); sys.exit(1)
    if a.type not in TYPES:
        print(f"Tipo invalido. Validos: {', '.join(TYPES)}"); sys.exit(1)
    if scope == "org":
        full = " ".join([a.title, a.what, a.why, a.details or "", a.learned or ""])
        if contains_secret(full):
            print("RECHAZADO: el contenido parece contener secretos/credenciales. El scope org no los admite."); sys.exit(1)
    root = scope_root(a, scope)
    prefix = "POL" if a.type == "policy" else "MEM"
    mid = next_id(root, prefix)
    created = datetime.datetime.now().isoformat(timespec="seconds")
    session = current_session(root)
    sup = [s.strip() for s in a.supersedes.split(",") if s.strip()] if a.supersedes else []
    extra = ""
    if a.type == "policy":
        extra = f"\nenforcement: {a.enforcement}\napplies_to: {a.applies_to or 'all'}"
    fname = f"{mid}-{slug(a.title)}.md"
    fpath = os.path.join(paths(root)[0], fname)
    open(fpath, "w", encoding="utf-8").write(TEMPLATE.format(
        id=mid, type=a.type, project=a.project or os.path.basename(os.getcwd()), created=created,
        session=session, tags=a.tags or "", links=a.links.upper() if a.links else "",
        supersedes=",".join(sup), extra_meta=extra, title=a.title, what=a.what or "-",
        why=a.why or "-", where=a.where or "-", details=a.details or "-", learned=a.learned or "-"))
    e = {"id": mid, "type": a.type, "project": a.project or os.path.basename(os.getcwd()),
         "created": created, "session": session, "title": a.title,
         "tags": [t.strip() for t in a.tags.split(",") if t.strip()] if a.tags else [],
         "links": [l.strip().upper() for l in a.links.split(",") if l.strip()] if a.links else [],
         "supersedes": sup, "file": fpath, "body": open(fpath, encoding="utf-8").read()}
    con = db(root)
    index_entry(con, e)
    cands = fts_candidates(con, mid, a.title)
    for cid, _ in cands:
        con.execute("INSERT OR IGNORE INTO relations VALUES (?,?,?,?,?)", (mid, cid, "candidate", "pending", "detectado por similitud FTS"))
    con.commit(); con.close()
    print(f"Guardada [{scope}]: {mid} -> {fpath}")
    if a.type == "policy":
        print(f"Politica {mid} enforcement={a.enforcement}. Los proyectos deben attestarla (policy attest) o pedir desviacion antes de GATE 1.")
    if cands:
        print(f"\n{len(cands)} posible(s) memoria(s) relacionada(s):")
        for cid, ctitle in cands: print(f"  - {cid}: {ctitle}")

def cmd_search(a):
    tokens = re.findall(r"\w+", a.query)
    if not tokens: print("Consulta vacia."); sys.exit(1)
    q = (" OR " if a.any else " AND ").join(tokens)
    found = False
    for scope in active_scopes(a):
        root = scope_root(a, scope)
        if not os.path.isfile(paths(root)[2]): continue
        con = db(root)
        where, params = "fts MATCH ?", [q]
        if a.type: where += " AND e.type=?"; params.append(a.type)
        if a.project: where += " AND e.project=?"; params.append(a.project)
        try:
            rows = con.execute(f"""SELECT e.id, e.type, e.title, e.created, snippet(fts,2,'>>','<<','...',10)
                FROM fts JOIN entries e ON e.id=fts.id WHERE {where} ORDER BY rank LIMIT 10""", params).fetchall()
        except sqlite3.OperationalError:
            rows = []
        con.close()
        if rows:
            found = True
            print(f"--- scope: {scope} ---")
            for r in rows:
                if getattr(a, "brief", False):
                    print(f"{r[0]}  [{r[1]}]  {r[2]}  ({r[3][:10]})")
                else:
                    print(f"{r[0]}  [{r[1]}]  {r[2]}  ({r[3][:10]})\n    {r[4]}")
            if getattr(a, "brief", False):
                print("    (abrir con: mem.py get <id>)")
    if not found: print("Sin resultados en ningun scope.")

def find_entry(a, mid):
    for scope in SCOPES:
        root = scope_root(a, scope)
        if not os.path.isfile(paths(root)[2]): continue
        con = db(root)
        row = con.execute("SELECT file FROM entries WHERE id=?", (mid,)).fetchone()
        con.close()
        if row: return scope, row[0]
    return None, None

def cmd_get(a):
    scope, f = find_entry(a, a.id)
    if not f: print(f"No existe {a.id} en ningun scope"); sys.exit(1)
    print(f"[scope: {scope}]")
    print(open(f, encoding="utf-8").read())

def cmd_timeline(a):
    scope, _ = find_entry(a, a.id)
    if not scope: print(f"No existe {a.id}"); sys.exit(1)
    root = scope_root(a, scope); con = db(root)
    print(f"=== Timeline de {a.id} [scope: {scope}] ===")
    for src, dst, rel, status in con.execute(
        "SELECT src, dst, relation, status FROM relations WHERE src=? OR dst=? ORDER BY src", (a.id, a.id)):
        print(f"  {src} --[{rel}/{status}]--> {dst}")
    for rid, typ, title, created in con.execute("SELECT id, type, title, created FROM entries ORDER BY created"):
        mark = " <==" if rid == a.id else ""
        print(f"  {created[:16]}  [{typ}] {rid}: {title}{mark}")
    con.close()

def cmd_conflicts(a):
    root = scope_root(a, a.scope or "project"); con = db(root)
    if a.sub == "list":
        rows = con.execute("SELECT src, dst, note FROM relations WHERE relation='candidate' AND status=?",
                           (a.status or "pending",)).fetchall()
        if not rows: print("Sin candidatos pendientes.")
        for s, d, n in rows: print(f"  {s}  <->  {d}   ({n})")
    else:
        if a.relation == "unrelated":
            con.execute("DELETE FROM relations WHERE src=? AND dst=? AND relation='candidate'", (a.id, a.dst))
        else:
            con.execute("INSERT OR REPLACE INTO relations VALUES (?,?,?,?,?)",
                        (a.id, a.dst, a.relation, "judged", a.note or ""))
            con.execute("DELETE FROM relations WHERE src=? AND dst=? AND relation='candidate'", (a.id, a.dst))
        con.commit()
        print(f"Resuelto: {a.id} --[{a.relation}]--> {a.dst}")
    con.close()

def cmd_session(a):
    root = scope_root(a, "project"); con = db(root)
    if a.sub == "start":
        sid = f"SES-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
        con.execute("INSERT INTO sessions VALUES (?,?,?,NULL,'')", (sid, a.project or os.path.basename(os.getcwd()),
                    datetime.datetime.now().isoformat(timespec="seconds")))
        con.commit(); print(f"Sesion iniciada: {sid}")
    else:
        row = con.execute("SELECT id FROM sessions WHERE ended IS NULL ORDER BY started DESC LIMIT 1").fetchone()
        if not row: print("No hay sesion activa."); sys.exit(1)
        sid = row[0]
        con.execute("UPDATE sessions SET ended=?, summary=? WHERE id=?",
                    (datetime.datetime.now().isoformat(timespec="seconds"), a.summary or "", sid))
        n = con.execute("SELECT COUNT(*) FROM entries WHERE session=?", (sid,)).fetchone()[0]
        con.commit()
        spath = os.path.join(paths(root)[3], f"{sid}.md")
        open(spath, "w", encoding="utf-8").write(
            f"# Resumen de sesion {sid}\n\n**Memorias creadas**: {n}\n\n**Resumen**: {a.summary or '-'}\n")
        print(f"Sesion cerrada: {sid} ({n} memorias) -> {spath}")
    con.close()

def cmd_promote(a):
    scope, src_file = find_entry(a, a.id)
    if not src_file: print(f"No existe {a.id}"); sys.exit(1)
    if scope == a.to: print(f"{a.id} ya esta en scope {a.to}"); sys.exit(1)
    dst_root = scope_root(a, a.to)
    text = open(src_file, encoding="utf-8").read()
    text = re.sub(r"^---\n", f"---\nderived_from: {a.id} (scope {scope})\n", text, count=1)
    if contains_secret(text):
        print("RECHAZADO: la memoria parece contener secretos; no se promueve."); sys.exit(1)
    dst = os.path.join(paths(dst_root)[0], os.path.basename(src_file))
    open(dst, "w", encoding="utf-8").write(text)
    e = parse_entry(dst)
    if e: index_entry(db(dst_root), e)
    print(f"Promovida: {a.id} [{scope}] -> scope {a.to} (derived_from registrado)")
    print("  La original permanece en su scope; la promovida es la referencia cross-proyecto.")

def cmd_reindex(a):
    for scope in active_scopes(a):
        root = scope_root(a, scope)
        dbp = paths(root)[2]
        if os.path.exists(dbp): os.remove(dbp)
        con = db(root)
        entries = paths(root)[0]
        n = 0
        if os.path.isdir(entries):
            for f in sorted(os.listdir(entries)):
                if f.endswith(".md"):
                    e = parse_entry(os.path.join(entries, f))
                    if e and "id" in e: index_entry(con, e); n += 1
        con.close()
        print(f"[{scope}] reindexadas {n} memorias.")

def cmd_doctor(a):
    ok = True
    for scope in SCOPES:
        root = scope_root(a, scope)
        entries, idx, dbp, _ = paths(root)
        print(f"[{scope}] {root}")
        if not os.path.isdir(entries):
            print("  sin memorias (se creara al primer uso)"); continue
        nfiles = len([f for f in os.listdir(entries) if f.endswith(".md")])
        print(f"  OK entries/ — {nfiles} memorias markdown")
        if os.path.exists(dbp):
            con = db(root); ndb = con.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
            pend = con.execute("SELECT COUNT(*) FROM relations WHERE relation='candidate' AND status='pending'").fetchone()[0]
            con.close()
            sync = ndb == nfiles
            ok &= sync
            print(f"  indice: {ndb} {'OK' if sync else 'DESINCRONIZADO — correr reindex'}")
            if pend: print(f"  {pend} conflicto(s) pendiente(s)")
    print("Estado:", "OK" if ok else "REVISAR")
    sys.exit(0 if ok else 1)

def cmd_export(a):
    data = {}
    for scope in active_scopes(a):
        root = scope_root(a, scope)
        if not os.path.isfile(paths(root)[2]): continue
        con = db(root)
        data[scope] = {"entries": [dict(zip(["id","title","type","project","created","session","file","tags","links"], r))
                                   for r in con.execute("SELECT * FROM entries")],
                       "relations": [dict(zip(["src","dst","relation","status","note"], r))
                                     for r in con.execute("SELECT * FROM relations")]}
        con.close()
    out = json.dumps(data, indent=2, ensure_ascii=False)
    if a.file: open(a.file, "w", encoding="utf-8").write(out); print(f"Exportado a {a.file}")
    else: print(out)

# ---------- gobierno de politicas ----------

def deviations_dir(a):
    d = os.path.join(scope_root(a, "project"), "deviations")
    os.makedirs(d, exist_ok=True)
    return d

def load_deviations(a):
    devs = []
    for f in sorted(glob.glob(os.path.join(deviations_dir(a), "DEV-*.md"))):
        devs.append(parse_entry(f))
    return [d for d in devs if d]

def org_policies(a, mandatory_only=False):
    root = scope_root(a, "org")
    entries = paths(root)[0]
    pols = []
    if os.path.isdir(entries):
        for f in sorted(os.listdir(entries)):
            if f.startswith("POL-") and f.endswith(".md"):
                e = parse_entry(os.path.join(entries, f))
                if e and e.get("type") == "policy":
                    if not mandatory_only or e.get("enforcement") == "mandatory":
                        pols.append(e)
    return pols

def attestations_file(a):
    root = scope_root(a, "project")
    os.makedirs(root, exist_ok=True)
    return os.path.join(root, "policy-attestations.json")

def load_attestations(a):
    f = attestations_file(a)
    return json.load(open(f, encoding="utf-8")) if os.path.isfile(f) else {}

def cmd_policy(a):
    if a.sub == "list":
        pols = org_policies(a)
        if not pols: print("Sin politicas en scope org.")
        for p in pols:
            print(f"{p['id']}  [{p.get('enforcement','?')}]  {p['title']}")
        return
    if a.sub == "attest":
        att = load_attestations(a)
        att[a.id] = {"status": a.status, "note": a.note or "", "by": a.by or "orchestrator",
                     "date": datetime.datetime.now().isoformat(timespec="seconds")}
        open(attestations_file(a), "w", encoding="utf-8").write(json.dumps(att, indent=2, ensure_ascii=False))
        print(f"Attestation registrada: {a.id} -> {a.status} (por {att[a.id]['by']})")
        return
    # policy check
    pols = org_policies(a, mandatory_only=True)
    att = load_attestations(a)
    devs = {d.get("policy"): d for d in load_deviations(a) if d.get("status") == "approved"}
    today = datetime.date.today().isoformat()
    violations, waived, compliant = [], [], []
    for p in pols:
        pid = p["id"]
        d = devs.get(pid)
        if d and (d.get("expires", "9999") >= today):
            waived.append((pid, p["title"], d.get("id", "")))
        elif att.get(pid, {}).get("status") == "compliant":
            compliant.append((pid, p["title"]))
        else:
            violations.append((pid, p["title"]))
    print("=== policy check (mandatory, scope org) ===")
    for pid, t in compliant: print(f"  COMPLIANT  {pid}: {t}")
    for pid, t, dev in waived: print(f"  WAIVED     {pid}: {t}  (desviacion {dev} aprobada)")
    for pid, t in violations: print(f"  VIOLATION  {pid}: {t}  — sin attestation ni desviacion aprobada")
    if violations:
        print(f"\nGATE 1 BLOQUEADO: {len(violations)} politica(s) mandatory sin cumplir.")
        print("Acciones: attestar con 'policy attest <id> --status compliant' o pedir desviacion con 'deviation request'.")
        sys.exit(1)
    print("\nTodas las politicas mandatory cumplidas o con desviacion vigente. GATE 1 desbloqueado en este aspecto.")

DEV_TEMPLATE = """---
id: {id}
policy: {policy}
status: pending
requested_by: {by}
created: {created}
expires: {expires}
approver: 
---
# Desviacion de {policy}: {title}

**Justificacion**: {justification}

**Alcance** (artefactos/HU afectados): {scope_}

**Riesgo de no cumplir la politica**: {risk}

**Mitigacion compensatoria**: {mitigation}
"""

def cmd_deviation(a):
    if a.sub == "request":
        pols = {p["id"] for p in org_policies(a)}
        if a.policy not in pols:
            print(f"La politica {a.policy} no existe en scope org. Existentes: {', '.join(sorted(pols)) or 'ninguna'}"); sys.exit(1)
        did = f"DEV-{datetime.date.today().strftime('%Y%m%d')}-{len(load_deviations(a))+1:03d}"
        fpath = os.path.join(deviations_dir(a), f"{did}-{slug(a.title)}.md")
        open(fpath, "w", encoding="utf-8").write(DEV_TEMPLATE.format(
            id=did, policy=a.policy, by=a.by or "orchestrator",
            created=datetime.datetime.now().isoformat(timespec="seconds"),
            expires=a.expires or "", title=a.title, justification=a.justification,
            scope_=a.scope_ or "-", risk=a.risk or "-", mitigation=a.mitigation or "-"))
        print(f"Desviacion solicitada: {did} -> {fpath}")
        print(f"Estado: pending. Requiere aprobacion humana: deviation approve {did} --approver <nombre>")
        return
    devs = {d["id"]: d for d in load_deviations(a)}
    if a.sub == "list":
        if not devs: print("Sin desviaciones.")
        for d in devs.values():
            print(f"{d['id']}  [{d.get('status')}]  policy={d.get('policy')}  expires={d.get('expires','-')}  approver={d.get('approver','-')}")
        return
    d = devs.get(a.id)
    if not d: print(f"No existe {a.id}"); sys.exit(1)
    if d.get("status") != "pending":
        print(f"{a.id} ya fue {d.get('status')}; no se puede volver a decidir."); sys.exit(1)
    if a.sub == "approve" and not a.approver:
        print("approve requiere --approver <nombre del aprobador humano/designado>"); sys.exit(1)
    text = open(d["file"], encoding="utf-8").read()
    text = text.replace("status: pending", f"status: {'approved' if a.sub == 'approve' else 'rejected'}")
    if a.approver: text = text.replace("approver: ", f"approver: {a.approver}")
    if a.note: text += f"\n**Nota del aprobador** ({a.approver or '-'}): {a.note}\n"
    open(d["file"], "w", encoding="utf-8").write(text)
    print(f"Desviacion {a.id}: {a.sub}d" + (f" por {a.approver}" if a.approver else ""))
    if a.sub == "approve":
        print("La desviacion queda vigente hasta 'expires'. Verificar con 'policy check'.")

def main():
    ap = argparse.ArgumentParser(description="Motor de memoria del arnes SDLC v1.2")
    ap.add_argument("--root", help="Raiz scope project (default ./spec/memory)")
    ap.add_argument("--scope", choices=SCOPES, default="", help="Scope de la operacion (save/conflicts/reindex/export)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("save"); p.add_argument("--type", required=True); p.add_argument("--title", required=True)
    p.add_argument("--scope", choices=SCOPES, default="", help="Scope donde guardar (default project)")
    for f in ["what", "why", "where", "details", "learned", "links", "supersedes", "tags", "project",
              "enforcement", "applies_to"]:
        p.add_argument(f"--{f}", default="")
    p.set_defaults(enforcement="recommended")
    p = sub.add_parser("search"); p.add_argument("query"); p.add_argument("--any", action="store_true")
    p.add_argument("--brief", action="store_true", help="una linea por resultado (ahorra contexto)")
    p.add_argument("--type", default=""); p.add_argument("--project", default="")
    p.add_argument("--scope", choices=SCOPES, default="", help="Limitar busqueda a un scope")
    p = sub.add_parser("get"); p.add_argument("id")
    p = sub.add_parser("timeline"); p.add_argument("id")
    p = sub.add_parser("conflicts"); p.add_argument("sub", choices=["list", "resolve"])
    p.add_argument("id", nargs="?"); p.add_argument("dst", nargs="?")
    p.add_argument("--relation", choices=["supersedes", "conflicts_with", "unrelated"]); p.add_argument("--note", default="")
    p.add_argument("--status", default="")
    p = sub.add_parser("session"); p.add_argument("sub", choices=["start", "end"])
    p.add_argument("--project", default=""); p.add_argument("--summary", default="")
    p = sub.add_parser("promote"); p.add_argument("id"); p.add_argument("--to", choices=["user", "org"], required=True)
    sub.add_parser("reindex")
    p = sub.add_parser("policy"); p.add_argument("sub", choices=["list", "check", "attest"])
    p.add_argument("id", nargs="?", default=""); p.add_argument("--status", choices=["compliant", "violation"], default="compliant")
    p.add_argument("--note", default=""); p.add_argument("--by", default="")
    p = sub.add_parser("deviation"); p.add_argument("sub", choices=["request", "approve", "reject", "list"])
    p.add_argument("id", nargs="?", default="")
    for f in ["policy", "title", "justification", "scope_", "risk", "mitigation", "expires", "by", "approver", "note"]:
        p.add_argument(f"--{f}", default="")
    sub.add_parser("doctor")
    p = sub.add_parser("export"); p.add_argument("file", nargs="?", default="")
    a = ap.parse_args()
    if a.cmd == "conflicts" and a.sub == "resolve" and (not a.id or not a.dst or not a.relation):
        print("conflicts resolve requiere: <src> <dst> --relation ..."); sys.exit(1)
    if a.cmd == "deviation" and a.sub == "request" and (not a.policy or not a.title or not a.justification):
        print("deviation request requiere: --policy <POL-id> --title <t> --justification <j>"); sys.exit(1)
    {"save": cmd_save, "search": cmd_search, "get": cmd_get, "timeline": cmd_timeline,
     "conflicts": cmd_conflicts, "session": cmd_session, "promote": cmd_promote,
     "reindex": cmd_reindex, "policy": cmd_policy, "deviation": cmd_deviation,
     "doctor": cmd_doctor, "export": cmd_export}[a.cmd](a)

if __name__ == "__main__":
    main()
