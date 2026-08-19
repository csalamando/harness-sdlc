#!/usr/bin/env python3
"""decision_sizing.py — Clasifica el riesgo de una decisión/proyecto (Risk Tier 1/2/3)
para determinar el nivel de gobernanza requerido.

Uso: python3 decision_sizing.py --spec spec/ --output spec/risk-tier.yaml
Exit 0 siempre (salvo error de entrada); el tier se escribe en el YAML de salida.
"""
import argparse
import os
import sys
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    yaml = None

HIGH_RISK = [
    "core bancario", "core banking", "pagos", "payments", "transacciones financieras",
    "pii", "datos personales", "gdpr", "pci-dss", "pci dss", "hipaa",
    "base de datos principal", "main database", "motor de datos",
    "autenticación", "authentication", "authorization", "autorización", "oauth", "openid",
    "infraestructura crítica", "critical infrastructure",
    "integración regulatoria", "regulatory integration", "dinero real", "facturación",
]

MEDIUM_RISK = [
    "microservicio", "microservice", "api", "rest", "graphql",
    "message broker", "kafka", "rabbitmq", "eventos", "events",
    "frontend", "ui", "ux", "aplicación web", "web app",
    "integración", "integration", "webhook", "base de datos", "database",
]

GOVERNANCE = {
    1: "Completo: 8 pasos de Natanzon + Advice Process completo + revisión Enterprise Architect",
    2: "Estándar: 8 pasos de Natanzon + Advice Process con peers",
    3: "Ligero: ADR simplificado + registro en memoria",
}


def classify(text):
    t = text.lower()
    high = sum(1 for k in HIGH_RISK if k in t)
    med = sum(1 for k in MEDIUM_RISK if k in t)
    if high >= 1:
        return 1, f"{high} indicador(es) de riesgo crítico detectados"
    if med >= 3:
        return 2, f"{med} indicadores de riesgo moderado detectados"
    if med >= 1:
        return 2, f"{med} indicador(es) de riesgo moderado"
    return 3, "Sin indicadores de riesgo significativo"


def collect(path):
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    parts = []
    for root, _, files in os.walk(path):
        for fn in files:
            if fn.endswith((".md", ".yaml", ".yml")):
                try:
                    with open(os.path.join(root, fn), encoding="utf-8") as f:
                        parts.append(f.read())
                except OSError:
                    pass
    return "\n".join(parts)


def main():
    p = argparse.ArgumentParser(description="Clasifica el Risk Tier de la decisión")
    p.add_argument("--spec", required=True, help="Directorio spec/ o archivo")
    p.add_argument("--output", default="spec/risk-tier.yaml")
    args = p.parse_args()

    if not os.path.exists(args.spec):
        print(f"ERROR: no existe {args.spec}")
        sys.exit(1)

    content = collect(args.spec)
    if not content.strip():
        print("ERROR: spec vacío, nada que clasificar")
        sys.exit(1)

    tier, rationale = classify(content)
    result = {
        "risk_tier": tier,
        "rationale": rationale,
        "classified_at": datetime.now(timezone.utc).isoformat(),
        "governance_level": GOVERNANCE[tier],
    }

    outdir = os.path.dirname(args.output)
    if outdir:
        os.makedirs(outdir, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        if yaml:
            yaml.dump(result, f, default_flow_style=False, allow_unicode=True)
        else:
            for k, v in result.items():
                f.write(f'{k}: "{v}"\n')

    print(f"Risk Tier: {tier}")
    print(f"Justificación: {rationale}")
    print(f"Gobernanza: {result['governance_level']}")
    print(f"Guardado en: {args.output}")


if __name__ == "__main__":
    main()
