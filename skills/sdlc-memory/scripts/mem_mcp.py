#!/usr/bin/env python3
"""mem_mcp.py — Servidor MCP (stdio, JSON-RPC 2.0) del motor de memoria del arnes SDLC.

Expone mem.py como herramientas MCP para agentes compatibles (Claude Code, VS Code
Copilot, Cursor, Antigravity, Codex...). Sin dependencias externas: Python 3 stdlib.

Registro tipico en el agente (ejemplo .mcp.json / mcp config):
  { "mcpServers": { "sdlc-memory": {
      "command": "python3",
      "args": ["<ruta>/sdlc-memory/scripts/mem_mcp.py"],
      "env": { "SDLCMEM_ROOT": "<proyecto>/spec/memory" } } } }

Herramientas: mem_save, mem_search, mem_get, mem_timeline, mem_conflicts_list,
              mem_conflicts_resolve, mem_session_start, mem_session_end, mem_doctor.
"""
import sys, os, json, subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MEM_PY = os.path.join(SCRIPT_DIR, "mem.py")

TOOLS = [
    {"name": "mem_save", "description": "Guarda una memoria estructurada (What/Why/Where/Details/Learned) en la memoria del proyecto. Detecta automaticamente memorias candidatas a conflicto.",
     "inputSchema": {"type": "object", "required": ["type", "title", "what", "why"], "properties": {
        "type": {"type": "string", "enum": ["decision", "bug", "learning", "architecture", "incident", "context"]},
        "title": {"type": "string"}, "what": {"type": "string"}, "why": {"type": "string"},
        "where": {"type": "string"}, "details": {"type": "string"}, "learned": {"type": "string"},
        "links": {"type": "string", "description": "IDs separados por coma: HU-001, ADR-002, EP-1"},
        "supersedes": {"type": "string", "description": "IDs MEM- separados por coma que esta memoria reemplaza"},
        "tags": {"type": "string"}, "project": {"type": "string"}}}},
    {"name": "mem_search", "description": "Busca memorias por texto completo (FTS5). match_any=true amplia el recall.",
     "inputSchema": {"type": "object", "required": ["query"], "properties": {
        "query": {"type": "string"}, "match_any": {"type": "boolean"}, "type": {"type": "string"}, "project": {"type": "string"}}}},
    {"name": "mem_get", "description": "Devuelve el contenido completo de una memoria por ID.",
     "inputSchema": {"type": "object", "required": ["id"], "properties": {"id": {"type": "string"}}}},
    {"name": "mem_timeline", "description": "Muestra el contexto cronologico y las relaciones de una memoria.",
     "inputSchema": {"type": "object", "required": ["id"], "properties": {"id": {"type": "string"}}}},
    {"name": "mem_conflicts_list", "description": "Lista pares de memorias candidatas a conflicto pendientes de resolver.",
     "inputSchema": {"type": "object", "properties": {"status": {"type": "string"}}}},
    {"name": "mem_conflicts_resolve", "description": "Resuelve un par candidato declarando la relacion real: supersedes, conflicts_with o unrelated.",
     "inputSchema": {"type": "object", "required": ["src", "dst", "relation"], "properties": {
        "src": {"type": "string"}, "dst": {"type": "string"},
        "relation": {"type": "string", "enum": ["supersedes", "conflicts_with", "unrelated"]}, "note": {"type": "string"}}}},
    {"name": "mem_session_start", "description": "Abre una sesion de trabajo; las memorias siguientes quedan asociadas a ella.",
     "inputSchema": {"type": "object", "properties": {"project": {"type": "string"}}}},
    {"name": "mem_session_end", "description": "Cierra la sesion activa con un resumen (entrada de la proxima sesion).",
     "inputSchema": {"type": "object", "required": ["summary"], "properties": {"summary": {"type": "string"}}}},
    {"name": "mem_doctor", "description": "Verifica la salud del sistema de memoria (directorios, sincronia indice-markdown, conflictos pendientes).",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "mem_promote", "description": "Promueve una memoria de project a scope user u org (patron reutilizable cross-proyecto), registrando derived_from.",
     "inputSchema": {"type": "object", "required": ["id", "to"], "properties": {
        "id": {"type": "string"}, "to": {"type": "string", "enum": ["user", "org"]}}}},
    {"name": "mem_policy_list", "description": "Lista las politicas (lineamientos) del scope org con su enforcement.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "mem_policy_check", "description": "Verifica cumplimiento de politicas mandatory: compliant (attestada), waived (desviacion aprobada vigente) o violation (bloquea GATE 1).",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "mem_policy_attest", "description": "Registra attestation de cumplimiento de una politica mandatory en el proyecto.",
     "inputSchema": {"type": "object", "required": ["id"], "properties": {
        "id": {"type": "string"}, "status": {"type": "string", "enum": ["compliant", "violation"]},
        "note": {"type": "string"}, "by": {"type": "string"}}}},
    {"name": "mem_deviation_request", "description": "Solicita una desviacion aprobable a una politica org (justificacion, alcance, riesgo, mitigacion, expiracion). Queda pending hasta aprobacion humana.",
     "inputSchema": {"type": "object", "required": ["policy", "title", "justification"], "properties": {
        "policy": {"type": "string"}, "title": {"type": "string"}, "justification": {"type": "string"},
        "scope_": {"type": "string"}, "risk": {"type": "string"}, "mitigation": {"type": "string"},
        "expires": {"type": "string", "description": "YYYY-MM-DD"}, "by": {"type": "string"}}}},
    {"name": "mem_deviation_decide", "description": "Aprueba o rechaza una desviacion pendiente. Requiere approver (aprobador humano/designado).",
     "inputSchema": {"type": "object", "required": ["id", "decision", "approver"], "properties": {
        "id": {"type": "string"}, "decision": {"type": "string", "enum": ["approve", "reject"]},
        "approver": {"type": "string"}, "note": {"type": "string"}}}},
    {"name": "mem_deviation_list", "description": "Lista desviaciones del proyecto con estado, politica y expiracion.",
     "inputSchema": {"type": "object", "properties": {}}},
]

def run_mem(args):
    env = dict(os.environ)
    r = subprocess.run(["python3", MEM_PY, *args], capture_output=True, text=True, env=env)
    return (r.stdout + r.stderr).strip() or "(sin salida)"

def call_tool(name, args):
    def s(*flags):
        out = []
        for k, v in args.items():
            if isinstance(v, bool):
                if v: out.append(f"--{k.replace('match_any', 'any')}")
            elif v: out += [f"--{k}", str(v)]
        return out
    if name == "mem_save": return run_mem(["save", *s()])
    if name == "mem_search": return run_mem(["search", args["query"], *([ "--any" ] if args.get("match_any") else []),
                                            *( ["--type", args["type"]] if args.get("type") else []),
                                            *( ["--project", args["project"]] if args.get("project") else [])])
    if name == "mem_get": return run_mem(["get", args["id"]])
    if name == "mem_timeline": return run_mem(["timeline", args["id"]])
    if name == "mem_conflicts_list": return run_mem(["conflicts", "list", *( ["--status", args["status"]] if args.get("status") else [])])
    if name == "mem_conflicts_resolve": return run_mem(["conflicts", "resolve", args["src"], args["dst"], "--relation", args["relation"],
                                                        *( ["--note", args["note"]] if args.get("note") else [])])
    if name == "mem_session_start": return run_mem(["session", "start", *( ["--project", args["project"]] if args.get("project") else [])])
    if name == "mem_session_end": return run_mem(["session", "end", "--summary", args["summary"]])
    if name == "mem_doctor": return run_mem(["doctor"])
    if name == "mem_promote": return run_mem(["promote", args["id"], "--to", args["to"]])
    if name == "mem_policy_list": return run_mem(["policy", "list"])
    if name == "mem_policy_check": return run_mem(["policy", "check"])
    if name == "mem_policy_attest":
        return run_mem(["policy", "attest", args["id"], "--status", args.get("status", "compliant"),
                        *( ["--note", args["note"]] if args.get("note") else []),
                        *( ["--by", args["by"]] if args.get("by") else [])])
    if name == "mem_deviation_request":
        return run_mem(["deviation", "request", "--policy", args["policy"], "--title", args["title"],
                        "--justification", args["justification"],
                        *( ["--scope_", args["scope_"]] if args.get("scope_") else []),
                        *( ["--risk", args["risk"]] if args.get("risk") else []),
                        *( ["--mitigation", args["mitigation"]] if args.get("mitigation") else []),
                        *( ["--expires", args["expires"]] if args.get("expires") else []),
                        *( ["--by", args["by"]] if args.get("by") else [])])
    if name == "mem_deviation_decide":
        return run_mem(["deviation", args["decision"], args["id"], "--approver", args["approver"],
                        *( ["--note", args["note"]] if args.get("note") else [])])
    if name == "mem_deviation_list": return run_mem(["deviation", "list"])
    raise ValueError(f"Herramienta desconocida: {name}")

def reply(rid, result):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "result": result}) + "\n"); sys.stdout.flush()

def reply_err(rid, code, msg):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": msg}}) + "\n"); sys.stdout.flush()

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try: req = json.loads(line)
        except json.JSONDecodeError: continue
        method, rid, params = req.get("method"), req.get("id"), req.get("params", {})
        if method == "initialize":
            reply(rid, {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                        "serverInfo": {"name": "sdlc-memory", "version": "1.0.0"}})
        elif method == "notifications/initialized" or method == "ping":
            if rid is not None: reply(rid, {})
        elif method == "tools/list":
            reply(rid, {"tools": TOOLS})
        elif method == "tools/call":
            try:
                out = call_tool(params.get("name"), params.get("arguments", {}))
                reply(rid, {"content": [{"type": "text", "text": out}]})
            except Exception as ex:
                reply(rid, {"content": [{"type": "text", "text": f"ERROR: {ex}"}], "isError": True})
        elif rid is not None:
            reply_err(rid, -32601, f"Metodo no soportado: {method}")

if __name__ == "__main__":
    main()
