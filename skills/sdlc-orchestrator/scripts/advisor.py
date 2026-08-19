#!/usr/bin/env python3
"""advisor.py — Identifica stakeholders para el Advice Process según el impacto
del ADR y genera el Advice Request (JSON) que bloquea el GATE 1 hasta registrar
el consejo en el Advice Log.

Uso: python3 advisor.py --adr spec/adr/ADR-001.md --risk-tier 1 [--output spec/advice/ADR-001.json]
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

IMPACT_STAKEHOLDERS = {
    "database": ["Data Engineer", "DBA"],
    "security": ["Security Engineer", "CISO"],
    "pii": ["Legal", "Compliance", "Data Privacy Officer"],
    "payments": ["Security Engineer", "Compliance"],
    "api": ["QA Lead"],
    "infrastructure": ["Cloud Engineer", "SRE Lead"],
    "frontend": ["UX Designer"],
    "integration": ["Security Engineer"],
}

KEYWORDS = {
    "database": ["base de datos", "database", "sql", "nosql", "postgres", "mysql", "mongodb", "persistencia"],
    "security": ["seguridad", "security", "autenticación", "authentication", "oauth", "jwt", "encript", "cifrado"],
    "pii": ["datos personales", "pii", "gdpr", "privacidad", "privacy"],
    "payments": ["pagos", "payments", "transacciones", "pci", "tarjetas", "facturación"],
    "api": ["api", "rest", "graphql", "grpc", "endpoint", "openapi"],
    "infrastructure": ["infraestructura", "infrastructure", "kubernetes", "docker", "cloud", "aws", "azure", "gcp"],
    "frontend": ["frontend", "ui", "ux", "react", "angular", "vue"],
    "integration": ["integración", "integration", "webhook", "message broker", "kafka", "rabbitmq", "eventos"],
}


def detect_impact_areas(content):
    t = content.lower()
    return [area for area, terms in KEYWORDS.items() if any(k in t for k in terms)]


def build_request(adr_path, risk_tier, areas):
    stakeholders = set()
    for a in areas:
        stakeholders.update(IMPACT_STAKEHOLDERS.get(a, []))
    if risk_tier == 1:
        stakeholders.add("Enterprise Architect")
    if risk_tier >= 2:
        stakeholders.add("Peer Review")
    return {
        "adr_path": adr_path,
        "risk_tier": risk_tier,
        "impact_areas": areas,
        "stakeholders": sorted(stakeholders),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "PENDING",
        "rule": "El consejo NO es vinculante, pero la omisión de consulta bloquea el GATE 1. "
                "Registrar cada consejo en la sección Advice Log del ADR.",
    }


def main():
    p = argparse.ArgumentParser(description="Identifica stakeholders para el Advice Process")
    p.add_argument("--adr", required=True)
    p.add_argument("--risk-tier", type=int, required=True, choices=[1, 2, 3])
    p.add_argument("--output", default=None)
    args = p.parse_args()

    if not os.path.exists(args.adr):
        print(f"ERROR: ADR no encontrado: {args.adr}")
        sys.exit(1)

    with open(args.adr, encoding="utf-8") as f:
        content = f.read()

    areas = detect_impact_areas(content) or ["general"]
    req = build_request(args.adr, args.risk_tier, areas)

    print(f"Advice Request para {args.adr}")
    print(f"  Risk Tier: {args.risk_tier}")
    print(f"  Áreas de impacto: {', '.join(areas)}")
    print("  Stakeholders a consultar:")
    for s in req["stakeholders"]:
        print(f"    - {s}")
    print("  Regla: consejo no vinculante; omisión de consulta bloqueante.")

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(req, f, indent=2, ensure_ascii=False)
        print(f"  Guardado en: {args.output}")


if __name__ == "__main__":
    main()
