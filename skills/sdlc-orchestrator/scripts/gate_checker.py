#!/usr/bin/env python3
"""gate_checker.py — valida el checklist de salida (DoD) de un artefacto de la spec.

Uso: python3 gate_checker.py <artefacto> --tipo <tipo>
Tipos: vision, backlog, user-stories, ux-flows, design-system, architecture,
       api-contract, test-plan, threat-model, qa-report, slo,
       technical-stories, architecture-proposal, cost-estimation (GATE 0),
       roles, process-definition (v2.7 — catálogo de roles y PDD AS-IS),
       screen-inventory (v2.8 — inventario de pantallas PANT-xx del prototipo UX)
Exit 0 = pasa el gate. Exit 1 = falla (imprime checks incumplidos).
"""
import sys, argparse, re, os

def has(path, *patterns):
    try:
        text = open(path, encoding="utf-8").read()
    except FileNotFoundError:
        return None
    return all(re.search(p, text, re.IGNORECASE | re.MULTILINE) for p in patterns)

CHECKS = {
    "vision": ["problema", "usuarios objetivo", "propuesta de valor", "métricas de éxito"],
    "backlog": ["prioridad", "métrica de éxito", r"EP-\d+"],
    "user-stories": [r"HU-\d+", r"[Ee]scenario", r"[Dd]ado", r"[Cc]uando", r"[Ee]ntonces", r"épica"],
    "ux-flows": ["loading", "empty", "error", "success"],
    "design-system": ["color", "tipografía|tipografia|typography", "espaciado|spacing", "componentes"],
    "architecture": [r"mermaid", r"requisitos no funcionales|NFR", r"componentes"],
    "api-contract": ["openapi:", "paths:", "components:"],
    "test-plan": [r"HU-\d+", r"unit|unitario", r"E2E", r"cobertura"],
    "threat-model": [r"S.*T.*R.*I.*D.*E|Spoofing", r"Mitigación|mitigacion", r"Riesgo|riesgo"],
    "qa-report": [r"[Vv]eredicto", r"HU-\d+", r"[Rr]egresión|regresion", r"[Bb]ugs"],
    "slo": [r"SLI", r"SLO", r"[Ee]rror budget"],
    # GATE 0 — aprobación de la iniciativa (Solution Architect)
    "technical-stories": [r"TS-\d+", r"[Tt]ipo.*enabler|debt|spike|nfr", r"[Oo]rigen",
                          r"[Cc]riterio de aceptación|aceptacion", r"[Cc]osto de NO"],
    "architecture-proposal": [r"[Cc]ontexto y objetivo de negocio", r"[Oo]pci[oó]n A", r"[Oo]pci[oó]n B",
                              r"[Cc]omparativa", r"[Rr]ecomendaci[oó]n", r"[Ee]stimaci[oó]n de costos",
                              r"ADR-P-\d+"],
    "cost-estimation": [r"CAPEX", r"OPEX", r"TCO", r"[Vv]alidez de precios",
                        r"[Mm]ínimo viable|[Mm]inimo viable", r"[Pp]ico", r"[Ss]upuestos"],
    # ADR de 8 pasos (Natanzon) — Tier 1-2
    "adr": [r"Problem Statement", r"Last Responsible Moment", r"Criterios de Evaluación",
            r"Opciones Consideradas", r"Advice Log", r"Scorecard", r"Decisión",
            r"Re-evaluation Triggers", r"Risk Tier"],
    # v2.7 — catálogo de roles gobernado y PDD (AS-IS)
    "roles": [r"ROL-\d+", r"[Aa]cciones que habilita", r"[Cc]ontexto",
              r"[Rr]eglas que lo restringen|[Rr]eglas.*restringen"],
    "process-definition": [r"AS-IS", r"[Dd]isparador", r"[Ee]xcepciones",
                           r"SLA", r"[Aa]plicaciones involucradas",
                           r"[Rr]iesgos", r"[Ss]upuestos", r"[Pp]rocess [Oo]wner"],
    # v2.8 — inventario de pantallas del prototipo gobernado (spec/ux/)
    "screen-inventory": [r"PANT-\d+", r"HU-\d+", r"ROL-\d+",
                         r"loading", r"empty", r"error", r"success",
                         r"[Ii]nteracciones", r"[Dd]estino"],
    # v2.15 — cierre de sprint con evidencia: el review es un artefacto gobernado
    "sprint-review": [r"Sprint Review — Sprint \d+", r"Resumen ejecutivo",
                      r"Avance del proyecto", r"Desempe.o del arn",
                      r"lead time por gate", r"Tendencia vs sprint anterior",
                      r"Aprendizajes y acciones", r"<!-- Artefactos aprobados:"],
}

TECH_KEYWORDS = [
    "kubernetes", "k8s", "docker", "aws", "azure", "gcp", "lambda",
    "postgres", "postgresql", "mysql", "mongodb", "redis", "kafka",
    "rabbitmq", "react", "angular", "vue", "spring", "django", "flask",
    "nodejs", "graphql", "grpc", "terraform", "ansible", "jenkins",
    "oracle", "sqlserver", "elasticsearch", "spark", "hadoop",
]

def check_adr_semantics(path, risk_tier):
    """Validaciones semánticas del ADR de 8 pasos. Devuelve lista de fallos."""
    text = open(path, encoding="utf-8").read()
    failures = []

    # 1. Problem Statement sin soluciones prematuras
    m = re.search(r"## Paso 1: Problem Statement\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    if m:
        body = "\n".join(ln for ln in m.group(1).lower().splitlines()
                         if not ln.strip().startswith("{") and "validación" not in ln.lower())
        found = [t for t in TECH_KEYWORDS if re.search(r"\b" + re.escape(t) + r"\b", body)]
        if found:
            failures.append(f"Problem Statement con soluciones prematuras: {', '.join(found)}")
    # 2. Pesos de criterios suman 100%
    rows = [(n, w) for n, w in re.findall(r"\|\s*([^|]+?)\s*\|\s*(\d+)\s*%\s*\|", text)
            if "total" not in n.lower() and "peso" not in n.lower()]
    seen = set()
    unique = []
    for n, w in rows:
        key = (n.strip(), w)
        if key not in seen:
            seen.add(key)
            unique.append((n, int(w)))
    # Paso 3 y Paso 6 repiten los criterios: deduplicar por nombre
    crit_weights = {}
    for n, w in unique:
        crit_weights.setdefault(n.strip(), w)
    if crit_weights and sum(crit_weights.values()) != 100:
        failures.append(f"Pesos de criterios suman {sum(crit_weights.values())}%, deben sumar 100%")
    # 3. Advice Log con consejos registrados (Tier 1-2)
    if risk_tier <= 2:
        advice = re.search(r"## Paso 5: Advice Log\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
        if not advice or not re.search(r"\|\s*[^|-].+?\|\s*.+?\|\s*\d{4}-\d{2}-\d{2}\s*\|", advice.group(1)):
            failures.append(f"Advice Log sin consejos registrados (obligatorio en Tier {risk_tier})")
    return failures

def check_tech_radar(adr_path, radar_path):
    """Cruza tecnologías del ADR con el Tech Radar. Devuelve lista de fallos."""
    try:
        import yaml
    except ImportError:
        return ["PyYAML no instalado: no se pudo validar el Tech Radar"]
    try:
        radar = yaml.safe_load(open(radar_path, encoding="utf-8").read())
    except FileNotFoundError:
        return []  # sin radar no hay validación
    text = open(adr_path, encoding="utf-8").read().lower()
    failures = []
    quadrants = (radar or {}).get("quadrants", {})
    for tech in quadrants.get("HOLD", []):
        name = str(tech.get("technology", "")).lower()
        if name and re.search(r"\b" + re.escape(name) + r"\b", text) \
                and "excepción" not in text:
            failures.append(f"Tecnología en HOLD detectada: {tech['technology']} — requiere ADR de excepción")
    return failures

def check_signoff(adr_path, receipts_dir):
    """Verifica que exista el Recibo de Arquitectura firmado y vigente."""
    import json, hashlib
    m = re.search(r"ADR-(\d+)", os.path.basename(adr_path))
    if not m:
        return ["No se pudo extraer el ID del ADR del nombre de archivo"]
    rpath = os.path.join(receipts_dir, f"ARCH-{m.group(1)}.json")
    if not os.path.exists(rpath):
        return [f"No existe Recibo de Arquitectura para ADR-{m.group(1)} (firmar con arch_signoff.py)"]
    receipt = json.load(open(rpath, encoding="utf-8"))
    if not receipt.get("signed") or receipt.get("status") != "ACTIVE":
        return ["El Recibo de Arquitectura no está firmado/activo"]
    h = hashlib.sha256(open(adr_path, "rb").read()).hexdigest()
    if h != receipt.get("adr_hash"):
        return ["El ADR cambió después de la firma: recibo INVALIDADO, volver a firmar"]
    return []


def resolve_spec_path(path, artefacto):
    """Resuelve una ruta de spec/ aunque se ejecute fuera de la raíz del proyecto.

    Prueba: (1) tal cual (cwd), (2) subiendo desde el directorio del artefacto
    hasta encontrar un directorio spec/ que la contenga. Devuelve None si no existe.
    """
    if os.path.exists(path):
        return path
    d = os.path.dirname(os.path.abspath(artefacto))
    for _ in range(6):
        cand = os.path.join(d, path)
        if os.path.exists(cand):
            return cand
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def check_sprint_learning(artefacto):
    """Sprint review sin memoria learning del periodo = aprendizaje perdido (v2.15).

    El aprendizaje institucional no es opcional: exige al menos una memoria
    `type: learning` creada dentro del periodo del sprint (del primer recibo a
    la fecha de generación del review). sprint_review.py autogenera la memoria
    "sprint limpio" cuando no hubo señales, así que esta regla nunca pide
    burocracia vacía — pide que el aprendizaje quede registrado.
    """
    import glob
    text = open(artefacto, encoding="utf-8").read()
    gen = re.search(r"Generado:\s*(\d{4}-\d{2}-\d{2})", text)
    per = re.search(r"Periodo \(recibos\):\s*(\d{4}-\d{2}-\d{2})", text)
    if not gen:
        return ["Sprint review sin línea 'Generado:' — regenerar con sprint_review.py"]
    inicio = per.group(1) if per else "0000-00-00"
    fin = gen.group(1)
    entries = resolve_spec_path("spec/memory/entries", artefacto)
    if not entries:
        return ["Sin spec/memory/entries/ — la memoria del sprint no existe (guardar una "
                "memoria learning con las señales del sprint; si fue limpio, "
                "sprint_review.py la autogenera)"]
    for p in glob.glob(os.path.join(entries, "*.md")):
        try:
            head = open(p, encoding="utf-8", errors="replace").read(600)
        except OSError:
            continue
        if "type: learning" not in head:
            continue
        c = re.search(r"created:\s*(\d{4}-\d{2}-\d{2})", head)
        if c and inicio <= c.group(1) <= fin:
            return []
    return [f"Sin memoria learning en el periodo del sprint ({inicio} → {fin}) — "
            "guardar con mem.py add --type learning (o regenerar el review: "
            "los sprints limpios la autogeneran)"]


def check_roles_refs(roles_path, stories_path):
    """Verifica que los ROL-xx citados en las historias existan en el catálogo.

    Si existe el catálogo (v2.7), además exige que TODA HU cite al menos un ROL-xx.
    """
    try:
        defined = set(re.findall(r"ROL-\d+", open(roles_path, encoding="utf-8").read()))
    except (FileNotFoundError, TypeError):
        return []
    failures = []
    try:
        stories = open(stories_path, encoding="utf-8").read()
    except (FileNotFoundError, TypeError):
        return []
    cited = set(re.findall(r"ROL-\d+", stories))
    unknown = sorted(cited - defined)
    if unknown:
        failures.append(f"ROL citado en {stories_path} sin definir en el catálogo: {', '.join(unknown)}")
    # Toda HU debe citar un ROL-xx del catálogo (el "Como <rol>" no es palabra libre)
    for m in re.finditer(r"(##\s*HU-\d+.*?)(?=\n##\s*HU-\d+|\Z)", stories, re.DOTALL):
        hu_id = re.search(r"HU-\d+", m.group(1)).group(0)
        hu_roles = set(re.findall(r"ROL-\d+", m.group(1)))
        if not hu_roles:
            failures.append(f"{hu_id} no cita ningún ROL-xx del catálogo (obligatorio cuando existe spec/roles.md)")
        elif hu_roles - defined:
            failures.append(f"{hu_id} cita ROL sin definir: {', '.join(sorted(hu_roles - defined))}")
    return failures


def check_screens_refs(inventory_path, stories_path):
    """Verifica que las HU-xx citadas en el inventario de pantallas existan en las historias."""
    try:
        defined = set(re.findall(r"HU-\d+", open(stories_path, encoding="utf-8").read()))
    except (FileNotFoundError, TypeError):
        return []
    try:
        cited = set(re.findall(r"HU-\d+", open(inventory_path, encoding="utf-8").read()))
    except (FileNotFoundError, TypeError):
        return []
    unknown = sorted(cited - defined)
    return [f"HU citada en {inventory_path} sin definir en user-stories: {', '.join(unknown)}"] if unknown else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("artefacto")
    ap.add_argument("--tipo", required=True, choices=sorted(CHECKS))
    ap.add_argument("--risk-tier", type=int, default=2, choices=[1, 2, 3],
                    help="Risk Tier de la decisión (solo tipo adr)")
    ap.add_argument("--tech-radar", default="spec/tech-radar.yaml",
                    help="Ruta al Tech Radar (solo tipo adr)")
    ap.add_argument("--receipts-dir", default="spec/receipts",
                    help="Directorio de recibos (solo tipo adr)")
    a = ap.parse_args()
    patterns = CHECKS[a.tipo]
    try:
        text = open(a.artefacto, encoding="utf-8").read()
    except FileNotFoundError:
        print(f"FALLO: no existe {a.artefacto}"); sys.exit(1)
    missing = [p for p in patterns if not re.search(p, text, re.IGNORECASE | re.MULTILINE)]
    semantic = []
    if a.tipo == "adr":
        semantic += check_adr_semantics(a.artefacto, a.risk_tier)
        semantic += check_tech_radar(a.artefacto, a.tech_radar)
        semantic += check_signoff(a.artefacto, a.receipts_dir)
    if a.tipo in ("roles", "user-stories"):
        roles_f = a.artefacto if a.tipo == "roles" else resolve_spec_path("spec/roles.md", a.artefacto)
        stories_f = a.artefacto if a.tipo == "user-stories" else resolve_spec_path("spec/user-stories.md", a.artefacto)
        semantic += check_roles_refs(roles_f, stories_f)
    if a.tipo == "screen-inventory":
        semantic += check_screens_refs(a.artefacto, resolve_spec_path("spec/user-stories.md", a.artefacto))
    if a.tipo == "sprint-review":
        semantic += check_sprint_learning(a.artefacto)
    if missing or semantic:
        print(f"GATE NO PASADO ({a.tipo}):")
        for m in missing: print(f"  - patrón no encontrado: {m}")
        for s in semantic: print(f"  - {s}")
        sys.exit(1)
    print(f"GATE PASADO ({a.tipo}): {len(patterns)} checks OK -> {a.artefacto}")

if __name__ == "__main__":
    main()
