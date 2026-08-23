#!/usr/bin/env python3
"""self_test.py — regresión del arnés: valida que scripts, gates, plantillas,
matriz de autoridad y grafo de impacto sean consistentes ENTRE SÍ.

NO forma parte del paquete de skills (vive fuera de skills/, nunca entra al ZIP
de release). Ejecutar ANTES de publicar una versión:

    python tests/self_test.py

Exit 0 = todo verde. Exit 1 = hay fallos (se listan). Stdlib puro, sin deps.

Historia: nace de la revisión de calidad de v2.8.1, que encontró features
documentadas por encima de lo que los scripts hacían (ver CHANGELOG [2.8.1]).
"""
import os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORCH = os.path.join(ROOT, "skills", "sdlc-orchestrator", "scripts")
FAILURES = []
PASSES = 0

def ok(name):
    global PASSES
    PASSES += 1
    print(f"  OK  {name}")

def fail(name, detail=""):
    FAILURES.append(name)
    print(f"  FALLO {name}" + (f" — {detail}" if detail else ""))

def run(script, *args, cwd=None):
    """Corre un script del arnés. Devuelve (exit_code, stdout+stderr)."""
    p = subprocess.run([sys.executable, os.path.join(ORCH, script), *args],
                       capture_output=True, text=True, cwd=cwd or ROOT)
    return p.returncode, (p.stdout + p.stderr).strip()

def check(name, cond, detail=""):
    ok(name) if cond else fail(name, detail)


# ── 1. Todos los scripts compilan ────────────────────────────────────────────
print("\n[1] Compilación de scripts")
scripts = []
for base, _, files in os.walk(os.path.join(ROOT, "skills")):
    if "__pycache__" in base:
        continue
    scripts += [os.path.join(base, f) for f in files if f.endswith(".py")]
for s in sorted(scripts):
    code, out = run("gate_checker.py", "--help") if False else (
        subprocess.run([sys.executable, "-m", "py_compile", s],
                       capture_output=True, text=True).returncode, "")
    check(f"compila {os.path.relpath(s, ROOT)}", code == 0)

# ── 2. Plantillas con gate pasan su propio gate ──────────────────────────────
print("\n[2] Plantillas pasan su propio gate (lección v2.8.1: la plantilla es el ejemplo)")
TEMPLATE_GATES = [
    ("sdlc-product-owner/assets/vision.md", "vision"),
    ("sdlc-product-owner/assets/backlog.md", "backlog"),
    ("sdlc-ux-designer/assets/ux-flows.md", "ux-flows"),
    ("sdlc-ux-designer/assets/design-system.md", "design-system"),
    ("sdlc-ux-designer/assets/screen-inventory-template.md", "screen-inventory"),
    ("sdlc-software-architect/assets/architecture.md", "architecture"),
    ("sdlc-software-architect/assets/api-contract.yaml", "api-contract"),
    ("sdlc-security-engineer/assets/threat-model.md", "threat-model"),
    ("sdlc-qa-automation/assets/qa-report.md", "qa-report"),
    ("sdlc-sre/assets/slo.md", "slo"),
    ("sdlc-solution-architect/assets/technical-story-template.md", "technical-stories"),
    ("sdlc-solution-architect/assets/architecture-proposal-template.md", "architecture-proposal"),
    ("sdlc-business-analyst/assets/pdd-template.md", "process-definition"),
]
for rel, tipo in TEMPLATE_GATES:
    code, out = run("gate_checker.py", os.path.join(ROOT, "skills", rel), "--tipo", tipo)
    check(f"gate {tipo}: {os.path.basename(rel)}", code == 0, out.splitlines()[-1] if code else "")

# ── 3. Consistencia doc ↔ grafo de impacto (lección v2.8.1: spec_diff_impact) ─
print("\n[3] Grafo de impacto conoce los artefactos gobernados")
GOVERNED = ["roles.md", "process-definition.md", "screen-inventory.md", "epics.md",
            "architecture-proposal.md", "technical-stories.md", "cost-estimation.md",
            "user-stories.md", "tokens.json", "threat-model.md", "adr", "diagrams"]
for art in GOVERNED:
    code, out = run("spec_diff_impact.py", "--cambiado", art)
    check(f"spec_diff_impact conoce {art}", code == 0, out.splitlines()[0] if code else "")
# La promesa de v2.7: cambiar un rol revoca HU, UX y test-plan
code, out = run("spec_diff_impact.py", "--cambiado", "roles.md")
for promised in ("user-stories.md", "ux-flows.md", "test-plan.md", "screen-inventory.md"):
    check(f"roles.md revoca {promised} (promesa v2.7/v2.8)", code == 0 and promised in out)

# ── 4. Matriz de autoridad cubre los artefactos con skill dueña ───────────────
print("\n[4] Matriz de autoridad (lección v2.8.1: 'SIN REGLA' = cualquiera aprueba)")
MATRIX = os.path.join(ROOT, "skills", "sdlc-orchestrator", "assets", "authority-matrix.yaml")
matrix_text = open(MATRIX, encoding="utf-8").read()
OWNED = {
    "spec/security-requirements.md": "security-engineer",
    "spec/glossary.md": "business-analyst",
    "spec/data-governance.md": "data-engineer",
    "spec/cloud-costs.md": "cloud-engineer",
    "spec/tokens.json": "ux-designer",
    "spec/exception-log.md": "enterprise-architect",
    "spec/team-roster.yaml": "orchestrator",
    "spec/risk-tier.yaml": "orchestrator",
    "spec/roles.md": "business-analyst",
    "spec/process-definition.md": "business-analyst",
    "spec/ux/": "ux-designer",
}
for path, owner in OWNED.items():
    found = re.search(rf"path:\s*{re.escape(path)}\s+owner:\s*{owner}\b", matrix_text)
    check(f"matriz: {path} -> {owner}", bool(found))

with tempfile.TemporaryDirectory() as tmp:
    os.makedirs(os.path.join(tmp, "spec"))
    subprocess.run(["cmd", "/c", "copy", MATRIX, os.path.join(tmp, "spec")],
                   capture_output=True, shell=False) if os.name == "nt" else \
        subprocess.run(["cp", MATRIX, os.path.join(tmp, "spec")])
    code, out = run("authority_check.py", "spec/security-requirements.md",
                    "--role", "backend-dev", cwd=tmp)
    check("backend-dev NO puede emitir security-requirements", code == 1)
    code, out = run("authority_check.py", "spec/security-requirements.md",
                    "--role", "security-engineer", cwd=tmp)
    check("security-engineer SÍ puede emitir security-requirements", code == 0)

# ── 5. Roles gobernados end-to-end (lección v2.8.1: doc prometía más que el código)
print("\n[5] Roles: toda HU cita ROL-xx definido cuando existe el catálogo")
with tempfile.TemporaryDirectory() as tmp:
    spec = os.path.join(tmp, "spec")
    os.makedirs(spec)
    open(os.path.join(spec, "roles.md"), "w", encoding="utf-8").write(
        "# Catálogo\n## ROL-01 — Operador\n\n- **Acciones que habilita:** operar\n"
        "- **Contexto:** turno\n- **Reglas que lo restringen:** BR-001\n")
    stories_sin_rol = ("# HU\n\n## HU-001 — X\n**Épica:** EP-1 | **Prioridad:** Must\n\n"
                       "Como usuario quiero x para y.\n\n```gherkin\nEscenario: e\n"
                       "  Dado a\n  Cuando b\n  Entonces c\n```\n")
    f = os.path.join(spec, "user-stories.md")
    open(f, "w", encoding="utf-8").write(stories_sin_rol)
    code, out = run("gate_checker.py", f, "--tipo", "user-stories", cwd=tmp)
    check("HU sin ROL-xx falla el gate", code == 1 and "ROL-xx del cat" in out)
    open(f, "w", encoding="utf-8").write(stories_sin_rol.replace("Como usuario", "Como ROL-01"))
    code, out = run("gate_checker.py", f, "--tipo", "user-stories", cwd=tmp)
    check("HU con ROL-01 definido pasa el gate", code == 0, out if code else "")
    open(f, "w", encoding="utf-8").write(stories_sin_rol.replace("Como usuario", "Como ROL-99"))
    code, out = run("gate_checker.py", f, "--tipo", "user-stories", cwd=tmp)
    check("HU con ROL-99 (indefinido) falla", code == 1)
    # Degradación elegante: sin catálogo, pasa igual
    os.remove(os.path.join(spec, "roles.md"))
    open(f, "w", encoding="utf-8").write(stories_sin_rol)
    code, out = run("gate_checker.py", f, "--tipo", "user-stories", cwd=tmp)
    check("sin roles.md el gate degrada y pasa", code == 0, out if code else "")

# ── 6. Validación cruzada funciona desde otro cwd (lección v2.8.1) ───────────
print("\n[6] Validación cruzada independiente del cwd")
with tempfile.TemporaryDirectory() as tmp:
    spec = os.path.join(tmp, "spec")
    os.makedirs(os.path.join(spec, "ux"))
    open(os.path.join(spec, "user-stories.md"), "w", encoding="utf-8").write(
        "## HU-001 — X\n\nEscenario Dado Cuando Entonces épica\n")
    inv = os.path.join(spec, "ux", "screen-inventory.md")
    open(inv, "w", encoding="utf-8").write(
        "# Inv\n## PANT-01 — X\n\n- **Historias que cubre:** HU-001, HU-077\n"
        "- **Rol que la opera:** ROL-01\n- loading empty error success\n\n"
        "### Interacciones\n\n| Disparador | Destino |\n|---|---|\n| click | PANT-02 |\n")
    code, out = run("gate_checker.py", inv, "--tipo", "screen-inventory", cwd=tempfile.gettempdir())
    check("desde otro cwd detecta HU-077 sin definir", code == 1 and "HU-077" in out,
          out.splitlines()[-1] if code == 0 else "")

# ── 7. Manifiesto dinámico sin drift (v2.9: fuente de verdad en el frontmatter) ─
print("\n[7] Manifiesto derivado de las skills")
code, out = run("manifest_check.py", "--check")
check("manifiesto sin drift y sin inconsistencias cruzadas", code == 0,
      out.splitlines()[-1] if code else "")
# Las skills declaran sus metadatos en el frontmatter harness-* (no hay listas quemadas)
sample = open(os.path.join(ROOT, "skills", "sdlc-ux-designer", "SKILL.md"), encoding="utf-8").read()
check("frontmatter harness-* presente en las skills",
      "harness-role:" in sample and "harness-owns:" in sample)
# El doctor ya no tiene números quemados: lee las expectativas del manifiesto
doctor_src = open(os.path.join(ORCH, "harness_doctor.py"), encoding="utf-8").read()
check("harness_doctor consume el manifiesto (load_manifest)", "load_manifest" in doctor_src)

# ── Resumen ──────────────────────────────────────────────────────────────────
print(f"\n{'='*60}\n{PASSES} checks OK, {len(FAILURES)} fallos")
if FAILURES:
    print("Fallos:")
    for f_ in FAILURES:
        print(f"  - {f_}")
    sys.exit(1)
print("SELF-TEST VERDE — el arnés es consistente consigo mismo.")
