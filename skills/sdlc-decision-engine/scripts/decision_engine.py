#!/usr/bin/env python3
"""decision_engine.py — Valida ADRs contra el framework de 8 pasos de Natanzon
y carga Decision Packages pre-aprobados.

Uso:
  python3 decision_engine.py --validate --adr spec/adr/ADR-001.md
  python3 decision_engine.py --load-package pkg-auth --adr spec/adr/ADR-001.md \
      [--packages-dir assets/decision-packages]
"""
import argparse
import os
import re
import sys

try:
    import yaml
except ImportError:
    yaml = None

REQUIRED_SECTIONS = [
    ("## Metadata", "Metadata"),
    ("## Paso 1: Problem Statement", "Problem Statement"),
    ("## Paso 2: Last Responsible Moment", "Last Responsible Moment"),
    ("## Paso 3: Criterios de Evaluación", "Criterios de Evaluación"),
    ("## Paso 4: Opciones Consideradas", "Opciones Consideradas"),
    ("## Paso 5: Advice Log", "Advice Log"),
    ("## Paso 6: Scorecard de Trade-Offs", "Scorecard de Trade-Offs"),
    ("## Paso 7: Decisión", "Decisión"),
    ("## Paso 8: Re-evaluation Triggers", "Re-evaluation Triggers"),
]

TECH_KEYWORDS = [
    "kubernetes", "k8s", "docker", "aws", "azure", "gcp", "lambda",
    "postgres", "postgresql", "mysql", "mongodb", "redis", "kafka",
    "rabbitmq", "react", "angular", "vue", "spring", "django", "flask",
    "nodejs", "graphql", "grpc", "terraform", "ansible", "jenkins",
    "oracle", "sqlserver", "elasticsearch", "spark", "hadoop",
]


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _section(content, header):
    m = re.search(re.escape(header) + r"\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    return m.group(1).strip() if m else None


def check_sections(content):
    missing = [label for header, label in REQUIRED_SECTIONS if header not in content]
    return missing


def check_problem_statement(content):
    text = _section(content, "## Paso 1: Problem Statement")
    if text is None:
        return False, "Falta la sección Problem Statement"
    # Ignorar líneas de la plantilla (placeholders y notas de validación)
    body = "\n".join(
        ln for ln in text.lower().splitlines()
        if not ln.strip().startswith(("**validación", "{", "validación"))
    )
    found = [t for t in TECH_KEYWORDS if re.search(r"\b" + re.escape(t) + r"\b", body)]
    if found:
        return False, f"Soluciones prematuras detectadas: {', '.join(found)}"
    if len(body.strip()) < 40:
        return False, "Problem Statement vacío o demasiado corto"
    return True, "Problem Statement libre de soluciones prematuras"


def check_criteria(content):
    text = _section(content, "## Paso 3: Criterios de Evaluación") or ""
    rows = re.findall(r"\|\s*([^|]+?)\s*\|\s*(\d+)\s*%\s*\|", text)
    rows = [r for r in rows if "total" not in r[0].lower() and "peso" not in r[0].lower()]
    if len(rows) < 3:
        return False, f"Se requieren al menos 3 criterios (encontrados: {len(rows)})"
    total = sum(int(w) for _, w in rows)
    if total != 100:
        return False, f"Los pesos suman {total}%, deben sumar 100%"
    return True, f"{len(rows)} criterios, pesos = 100%"


def check_options(content):
    text = _section(content, "## Paso 4: Opciones Consideradas") or ""
    options = re.findall(r"###\s+Opci[oó]n\s+[A-Z]", text)
    if len(options) < 2:
        return False, f"Se requieren al menos 2 opciones (encontradas: {len(options)})"
    return True, f"{len(options)} opciones consideradas"


def check_advice_log(content, risk_tier):
    text = _section(content, "## Paso 5: Advice Log")
    if text is None:
        return False, "Falta la sección Advice Log"
    if risk_tier <= 2:
        # Tier 1-2: al menos un consejo registrado (fila de tabla con fecha)
        rows = re.findall(r"\|\s*[^|-].+?\|\s*.+?\|\s*\d{4}-\d{2}-\d{2}\s*\|", text)
        if not rows:
            return False, f"Advice Log sin consejos registrados (requerido para Tier {risk_tier})"
    return True, "Advice Log presente"


def check_decision(content):
    text = _section(content, "## Paso 7: Decisión") or ""
    if "{" in text or len(text.strip()) < 60:
        return False, "La sección Decisión sigue con placeholders o está incompleta"
    if "consecuencias negativas" not in text.lower():
        return False, "Faltan las consecuencias negativas aceptadas"
    return True, "Decisión documentada"


def check_triggers(content):
    text = _section(content, "## Paso 8: Re-evaluation Triggers") or ""
    items = [ln for ln in text.splitlines() if ln.strip().startswith("-") and "{" not in ln]
    if not items:
        return False, "Sin triggers de re-evaluación definidos"
    return True, f"{len(items)} triggers definidos"


def validate(adr_path, risk_tier):
    content = _read(adr_path)
    results = []
    missing = check_sections(content)
    results.append(("Secciones (8 pasos)", not missing,
                    "completas" if not missing else "faltan: " + ", ".join(missing)))
    for name, fn in [
        ("Problem Statement", lambda: check_problem_statement(content)),
        ("Criterios ponderados", lambda: check_criteria(content)),
        ("Opciones", lambda: check_options(content)),
        ("Advice Log", lambda: check_advice_log(content, risk_tier)),
        ("Decisión", lambda: check_decision(content)),
        ("Re-evaluation triggers", lambda: check_triggers(content)),
    ]:
        ok, msg = fn()
        results.append((name, ok, msg))
    return results


def load_package(pkg_name, adr_path, packages_dir):
    if yaml is None:
        print("ERROR: falta PyYAML (pip install pyyaml)")
        return 1
    pkg_path = os.path.join(packages_dir, pkg_name + ".yaml")
    if not os.path.exists(pkg_path):
        print(f"ERROR: package no encontrado: {pkg_path}")
        return 1
    pkg = yaml.safe_load(_read(pkg_path))
    weights = sum(c.get("weight", 0) for c in pkg.get("criteria", []))
    if weights != 100:
        print(f"ERROR: los criterios del package suman {weights}%, deben sumar 100%")
        return 1
    content = _read(adr_path)
    block = ["<!-- DECISION-PACKAGE: " + pkg["name"] + " v" + str(pkg.get("version", "?")) + " -->",
             "### Decision Package aplicado: " + pkg["name"], ""]
    block.append("| Criterio | Peso | Métrica | Umbral Mínimo |")
    block.append("|----------|------|---------|---------------|")
    for c in pkg.get("criteria", []):
        block.append(f"| {c['name']} | {c['weight']}% | {c.get('metric','')} | {c.get('threshold','')} |")
    block.append("| **TOTAL** | **100%** | | |")
    if pkg.get("paved_roads"):
        block.append("\n**Paved Roads del package:**")
        for pr in pkg["paved_roads"]:
            pa = "pre-aprobada" if pr.get("pre_approved") else "requiere justificación"
            block.append(f"- {pr['technology']} ({pr.get('quadrant','?')}) — {pa}")
    if pkg.get("constraints"):
        block.append("\n**Constraints obligatorios:**")
        block += [f"- {c}" for c in pkg["constraints"]]
    if pkg.get("required_advice"):
        block.append("\n**Advice obligatorio:** " + ", ".join(pkg["required_advice"]))
    block.append("<!-- /DECISION-PACKAGE -->")
    injected = "\n".join(block) + "\n"
    with open(adr_path, "a", encoding="utf-8") as f:
        f.write("\n" + injected)
    print(f"OK: package {pkg['name']} inyectado en {adr_path} (anclado con marcador DECISION-PACKAGE)")
    return 0


def main():
    p = argparse.ArgumentParser(description="Motor de decisiones de 8 pasos")
    p.add_argument("--validate", action="store_true", help="Validar el ADR contra los 8 pasos")
    p.add_argument("--load-package", metavar="PKG", help="Inyectar un Decision Package en el ADR")
    p.add_argument("--adr", required=True, help="Ruta al ADR")
    p.add_argument("--risk-tier", type=int, default=2, choices=[1, 2, 3])
    p.add_argument("--packages-dir", default=os.path.join(os.path.dirname(__file__), "..", "assets", "decision-packages"))
    args = p.parse_args()

    if not os.path.exists(args.adr):
        print(f"ERROR: ADR no encontrado: {args.adr}")
        sys.exit(1)

    if args.load_package:
        sys.exit(load_package(args.load_package, args.adr, args.packages_dir))

    if args.validate:
        results = validate(args.adr, args.risk_tier)
        all_ok = True
        for name, ok, msg in results:
            print(f"{'✓ PASS' if ok else '✗ FAIL'}: {name} — {msg}")
            all_ok = all_ok and ok
        sys.exit(0 if all_ok else 1)

    print("Nada que hacer: usa --validate o --load-package")
    sys.exit(2)


if __name__ == "__main__":
    main()
