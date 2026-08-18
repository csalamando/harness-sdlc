#!/usr/bin/env python3
"""detect_stack.py — Deteccion de stack y capacidades de test para la Fase -1.

Escanea el proyecto e infiere: lenguajes, frameworks, package managers, test runners
y si el modo Strict TDD puede activarse (hay runner con coverage disponible).
El resultado se registra en spec/pipeline-state.md por la skill de DevOps.

Uso: python3 detect_stack.py [--project-dir <ruta>] [--json]
"""
import os, sys, json, argparse

SIGNALS = [
    # (archivo/marcador, stack, test_runner, coverage)
    ("package.json",   "node/javascript", "vitest|jest (verificar devDependencies)", "@vitest/coverage|c8"),
    ("tsconfig.json",  "typescript", None, None),
    ("pyproject.toml", "python", "pytest (si esta en deps)", "pytest-cov"),
    ("requirements.txt","python", "pytest (verificar)", "pytest-cov"),
    ("pytest.ini",     "python", "pytest", "pytest-cov"),
    ("pom.xml",        "java/maven", "junit (surefire)", "jacoco"),
    ("build.gradle",   "java/gradle", "junit", "jacoco"),
    ("go.mod",         "go", "go test", "go test -cover"),
    ("Cargo.toml",     "rust", "cargo test", "tarpaulin|llvm-cov"),
    ("*.csproj",       "dotnet", "dotnet test (xunit/nunit)", "coverlet"),
    ("Gemfile",        "ruby", "rspec|minitest", "simplecov"),
    ("composer.json",  "php", "phpunit", "phpunit --coverage"),
    ("Dockerfile",     "docker", None, None),
    ("docker-compose.yml", "docker-compose", None, None),
    ("main.tf",        "terraform/iac", None, None),
]

def scan(project_dir):
    found, runners, coverage, extras = [], set(), set(), []
    try:
        entries = set(os.listdir(project_dir))
    except FileNotFoundError:
        return None
    names = set(entries)
    has_csproj = any(e.endswith(".csproj") for e in entries)
    for marker, stack, runner, cov in SIGNALS:
        hit = marker in names or (marker == "*.csproj" and has_csproj)
        if hit:
            found.append(stack)
            if runner: runners.add(runner)
            if cov: coverage.add(cov)
            if stack.startswith(("docker", "terraform")): extras.append(stack)
    return {"stacks": sorted(set(found)), "test_runners": sorted(runners),
            "coverage_tools": sorted(coverage), "infra": sorted(set(extras))}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-dir", default=os.getcwd())
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = scan(a.project_dir)
    if r is None:
        print(f"No existe {a.project_dir}"); sys.exit(1)
    strict_tdd = bool(r["test_runners"])
    r["strict_tdd_disponible"] = strict_tdd
    if a.json:
        print(json.dumps(r, indent=2, ensure_ascii=False)); return
    print(f"Stacks detectados: {', '.join(r['stacks']) or 'ninguno conocido'}")
    print(f"Test runners: {', '.join(r['test_runners']) or 'NINGUNO — gates de cobertura no exigibles'}")
    print(f"Coverage: {', '.join(r['coverage_tools']) or '-'}")
    if r["infra"]: print(f"Infra: {', '.join(r['infra'])}")
    print(f"\nStrict TDD: {'DISPONIBLE — activar en pipeline-state.md' if strict_tdd else 'NO DISPONIBLE — configurar un test runner antes de Fase 4'}")
    if not strict_tdd:
        sys.exit(2)

if __name__ == "__main__":
    main()
