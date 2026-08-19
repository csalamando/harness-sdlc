#!/usr/bin/env python3
"""cost_estimator.py — Estimación CAPEX/OPEX/TCO por opción, nube (AWS/Azure) y escenario.

Uso:
    python3 cost_estimator.py --assumptions spec/cost-assumptions.yaml \
        --clouds aws,azure --out spec/cost-estimation.md

Genera un Markdown con: OPEX mensual en 3 escenarios por nube, CAPEX, TCO 3 años,
supuestos usados y registro de precios sobreescritos. Precios de referencia en
unit_prices.py (lista on-demand aproximada; verificar contra calculadora oficial).
"""
import argparse
import datetime
import sys

import yaml

from unit_prices import UNIT_PRICES, CLOUD_NAMES

ENV_FACTOR = {"prod": 1.0, "staging": 0.5, "dev": 0.25}


def price(prices, overrides, cloud, key):
    full = f"{cloud}.{key}"
    if full in overrides:
        return overrides[full], True
    parts = key.split(".")
    node = prices[cloud]
    for p in parts:
        node = node[p]
    return node, False


def opex_option(opt, scenario, cloud, overrides, used_overrides):
    prices = UNIT_PRICES
    sc = scenario
    lines = {}
    envs = opt.get("environments", ["prod"])
    env_mult = sum(ENV_FACTOR.get(e, 1.0) for e in envs)

    compute_h = db_h = 0.0
    for svc in opt.get("services", []):
        t = svc["type"]
        if t == "compute":
            p, ov = price(prices, overrides, cloud, f"compute.{svc['sizing']}")
            used_overrides |= {f"{cloud}.compute.{svc['sizing']}"} if ov else set()
            compute_h += p * svc["quantity"] * svc.get("hours_month", 730) * env_mult
        elif t == "database":
            p, ov = price(prices, overrides, cloud, f"database.{svc['sizing']}")
            used_overrides |= {f"{cloud}.database.{svc['sizing']}"} if ov else set()
            mult = 2 if svc.get("ha") else 1
            db_h += p * svc["quantity"] * mult * svc.get("hours_month", 730) * env_mult

    p, ov = price(prices, overrides, cloud, "storage_gb_month")
    if ov:
        used_overrides.add(f"{cloud}.storage_gb_month")
    storage = p * sc["storage_gb"]

    p, ov = price(prices, overrides, cloud, "egress_gb")
    if ov:
        used_overrides.add(f"{cloud}.egress_gb")
    egress = p * sc["egress_gb_month"]

    p, ov = price(prices, overrides, cloud, "requests_million")
    if ov:
        used_overrides.add(f"{cloud}.requests_million")
    reqs = p * (sc["rps_avg"] * 86400 * 30) / 1_000_000

    lines = {"Cómputo": compute_h, "Base de datos": db_h,
             "Almacenamiento": storage, "Red (egress)": egress, "Peticiones": reqs}
    total = sum(lines.values())
    return lines, total


def fmt(x):
    return f"${x:,.0f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assumptions", required=True)
    ap.add_argument("--clouds", default="aws,azure")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    cfg = yaml.safe_load(open(a.assumptions))
    clouds = [c.strip() for c in a.clouds.split(",")]
    for c in clouds:
        if c not in UNIT_PRICES:
            sys.exit(f"Nube no soportada: {c} (soportadas: {', '.join(UNIT_PRICES)})")
    overrides = cfg.get("overrides") or {}
    used_overrides = set()
    today = datetime.date.today().isoformat()

    out = []
    out.append(f"# Estimación de costos — CAPEX / OPEX / TCO\n")
    out.append(f"- **Generada**: {today}")
    out.append(f"- **Validez de precios**: {cfg.get('validity_date', 'NO DECLARADA')}")
    out.append(f"- **Moneda**: {cfg.get('currency', 'USD')}")
    out.append("- **Naturaleza de los precios**: lista pública on-demand de referencia"
               + (f"; sobreescritos: {', '.join(sorted(used_overrides))}" if overrides else "")
               + ". Verificar contra AWS Pricing Calculator / Azure Pricing Calculator antes de presentar a negocio.\n")

    scenarios = cfg["scenarios"]
    for opt in cfg["options"]:
        out.append(f"\n## {opt['name']}\n")
        out.append(f"{opt.get('description', '')}\n")
        out.append(f"Ambientes: {', '.join(opt.get('environments', ['prod']))}\n")
        capex = opt.get("capex", {})
        capex_total = capex.get("engineering_hours", 0) * capex.get("hourly_rate", 0) + capex.get("one_time", 0)

        for cloud in clouds:
            out.append(f"\n### {CLOUD_NAMES[cloud]}\n")
            out.append("| Concepto | Mínimo viable | Crecimiento esperado | Pico |")
            out.append("|---|---|---|---|")
            per_sc, totals = {}, {}
            for sname, sc in scenarios.items():
                lines, total = opex_option(opt, sc, cloud, overrides, used_overrides)
                per_sc[sname] = lines
                totals[sname] = total
            for concept in per_sc["expected"].keys():
                out.append(f"| {concept} | {fmt(per_sc['minimum'][concept])} | "
                           f"{fmt(per_sc['expected'][concept])} | {fmt(per_sc['peak'][concept])} |")
            out.append(f"| **OPEX mensual** | **{fmt(totals['minimum'])}** | "
                       f"**{fmt(totals['expected'])}** | **{fmt(totals['peak'])}** |")
            tco = capex_total + 36 * totals["expected"]
            out.append(f"| **TCO 3 años** (CAPEX + 36 × OPEX esperado) | | **{fmt(tco)}** | |\n")

        out.append(f"\n**CAPEX** ({opt['name']}): {fmt(capex_total)} "
                   f"({capex.get('engineering_hours', 0)} h × ${capex.get('hourly_rate', 0)}/h "
                   f"+ {fmt(capex.get('one_time', 0))} one-time)\n")

    out.append("\n## Supuestos de negocio por escenario\n")
    out.append("| Supuesto | Mínimo viable | Esperado | Pico |")
    out.append("|---|---|---|---|")
    for key in ["active_users", "rps_avg", "rps_peak", "storage_gb", "egress_gb_month"]:
        out.append(f"| {key} | {scenarios['minimum'][key]} | {scenarios['expected'][key]} | {scenarios['peak'][key]} |")
    out.append(f"\nSupuestos completos: `{a.assumptions}` (versionado en spec/).")

    if used_overrides:
        out.append(f"\n## Precios sobreescritos\n\n" + "\n".join(f"- {o}" for o in sorted(used_overrides)))

    open(a.out, "w").write("\n".join(out) + "\n")
    print(f"OK: {a.out}")


if __name__ == "__main__":
    main()
