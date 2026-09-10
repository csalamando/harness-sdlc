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
import os, re, subprocess, sys, tempfile, json, shutil

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
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=cwd or ROOT)
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
    found = re.search(rf"path:\s*{re.escape(path)}\s*\n\s*owner:\s*{owner}\b", matrix_text)
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
# Routing derivado (v2.10): las condicionales se auto-excluyen
code, out = run("manifest_check.py", "--routing", "--sin-ui", "--sin-datos", "--sin-procesos")
check("routing --sin-datos excluye sdlc-data-engineer",
      code == 0 and "data-engineer excluida" in out)
check("routing --sin-ui excluye el prototipo spec/ux/",
      code == 0 and "EXCLUIDA" in out and "spec/ux/" in out)
code2, out2 = run("manifest_check.py", "--routing")
check("routing sin flags incluye a data-engineer en fase 2",
      code2 == 0 and "data-engineer" in out2)
# Versión del arnés (v2.12.1): frontmatter del orquestador = última entrada del CHANGELOG
sys.path.insert(0, ORCH)
from manifest_check import harness_version  # noqa: E402
_hv = harness_version()
_cl = open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8").read()
_latest = re.search(r"## \[(\d+\.\d+\.\d+)\]", _cl)
check("harness-version declarada y coincide con el CHANGELOG",
      bool(_hv) and bool(_latest) and _hv == _latest.group(1),
      f"declarada={_hv} changelog={_latest.group(1) if _latest else '?'}")
# receipt.py estampa la versión en los recibos nuevos
_receipt_src = open(os.path.join(ORCH, "receipt.py"), encoding="utf-8").read()
check("receipt.py estampa harness_version", 'rec["harness_version"]' in _receipt_src)
# FALLBACK_VERSION de audit_log (usada al correr vendorado) no puede desactualizarse
_al = open(os.path.join(ORCH, "audit_log.py"), encoding="utf-8").read()
_fb = re.search(r'FALLBACK_VERSION\s*=\s*"([^"]+)"', _al)
check("audit_log.FALLBACK_VERSION coincide con harness-version",
      bool(_fb) and bool(_hv) and _fb.group(1) == _hv,
      f"fallback={_fb.group(1) if _fb else '?'} frontmatter={_hv}")

# Grafo interactivo derivado (v2.11): docs/graph.html no puede quedar desactualizado
code, out = run("harness_graph.py", "--check")
check("grafo interactivo docs/graph.html sin drift", code == 0,
      out.splitlines()[-1] if code else "")

# ── 8. Dashboard vivo del proyecto (v2.12, ADR-002) ─────────────────────────
print("\n[8] Dashboard del proyecto (--proyecto) con fixture demo")
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "proyecto-demo")
if not os.path.isdir(FIXTURE):
    run_fixture = subprocess.run([sys.executable, os.path.join(ROOT, "tests", "fixtures", "make_fixture.py")],
                                 capture_output=True, text=True)
    check("fixture proyecto-demo generado", run_fixture.returncode == 0,
          (run_fixture.stderr or "").splitlines()[-1] if run_fixture.returncode else "")
code, out = run("harness_graph.py", "--proyecto", FIXTURE, "--json")
model = json.loads(out) if code == 0 else {}
check("derive_project del fixture exit 0 y modelo válido",
      code == 0 and model.get("fase_actual") == 4
      and model.get("loops_activos", {}).get("5->4") == 1
      and model.get("contadores", {}).get("sprints") == 2,
      out.splitlines()[-1] if code else "")
# v2.13: ADRs, tech radar, artefactos por fase y recorridos históricos de loops
check("modelo incluye ADRs con estado y tier",
      len(model.get("adrs", [])) == 2
      and model["adrs"][0]["status"] == "Adopted" and model["adrs"][0]["tier"] == "1")
check("modelo incluye tech radar por cuadrante",
      (model.get("radar") or {}).get("counts", {}).get("ADOPT") == 2
      and model["radar"]["counts"].get("TRIAL") == 1
      and len(model["radar"]["techs"].get("ADOPT", [])) == 2)
check("modelo incluye artefactos por fase y recorridos de loops",
      model.get("artefactos_por_fase", {}).get("1") == ["vision.md"]
      and model.get("loops_count", {}).get("4->4") == 2
      and model.get("loops_count", {}).get("5->4") == 1)
# v2.20.1 (lección CI): un recibo con ruta absoluta de Windows no debe romper
# el basename en Linux (os.path.basename no separa '\\' en POSIX)
tmp_rec = tempfile.mkdtemp()
os.makedirs(os.path.join(tmp_rec, "spec", "receipts"))
json.dump({"artefacto": "D:\\repo\\proyecto\\spec\\vision.md", "gate": "GATE 0",
           "estado": "vigente", "sha256": "x"},
          open(os.path.join(tmp_rec, "spec", "receipts", "vision.md.receipt.json"), "w"))
code, out = run("harness_graph.py", "--proyecto", tmp_rec, "--json")
model_win = json.loads(out) if code == 0 else {}
check("derive: basename correcto con ruta Windows en recibo (cross-platform)",
      model_win.get("artefactos_por_fase", {}).get("1") == ["vision.md"])
shutil.rmtree(tmp_rec, ignore_errors=True)
code, out = run("harness_graph.py", "--proyecto", FIXTURE)
check("dashboard del fixture generado", code == 0 and "Dashboard generado" in out,
      out.splitlines()[-1] if code else "")
code, out = run("harness_graph.py", "--proyecto", FIXTURE, "--check")
check("dashboard del fixture sin drift", code == 0,
      out.splitlines()[-1] if code else "")
# drift detectable: mutar un recibo del fixture debe romper el check
_rec = os.path.join(FIXTURE, "spec", "receipts", "release.md.receipt.json")
_orig = open(_rec, encoding="utf-8").read()
try:
    _r = json.loads(_orig); _r["estado"] = "revocado"
    open(_rec, "w", encoding="utf-8").write(json.dumps(_r, indent=2))
    code, _ = run("harness_graph.py", "--proyecto", FIXTURE, "--check")
    check("drift del dashboard detectado al mutar un recibo", code == 1)
finally:
    open(_rec, "w", encoding="utf-8").write(_orig)
code, out = run("harness_graph.py", "--proyecto", FIXTURE, "--check")
check("fixture restaurado: dashboard sin drift de nuevo", code == 0)

# ── 9. Visibilidad gobernada (v2.15) ─────────────────────────────────────────
print("\n[9] v2.15: gate sprint-review, telemetría con dueño y TDD por commits")
code, out = run("gate_checker.py", os.path.join(FIXTURE, "spec", "reports", "sprint-review-02.md"),
                "--tipo", "sprint-review")
check("gate sprint-review: review canónico del fixture pasa (8 checks + learning del periodo)",
      code == 0, out.splitlines()[-1] if code else "")
# negativo: el mismo review en un spec sin memorias learning debe fallar
with tempfile.TemporaryDirectory() as tmp:
    rdir = os.path.join(tmp, "spec", "reports")
    os.makedirs(rdir)
    import shutil as _sh2
    _sh2.copy(os.path.join(FIXTURE, "spec", "reports", "sprint-review-02.md"), rdir)
    code, out = run("gate_checker.py", os.path.join(rdir, "sprint-review-02.md"),
                    "--tipo", "sprint-review")
    check("gate sprint-review sin learning del periodo FALLA", code == 1,
          out if code == 0 else "")
# dueños de la telemetría en la matriz (antes eran tierra de nadie)
for path in ("spec/METRICS.md", "spec/metrics/", "spec/reports/"):
    check(f"matriz: {path} -> orchestrator",
          bool(re.search(rf"path:\s*{re.escape(path)}\s*\n\s*owner:\s*orchestrator\b", matrix_text)))
# tdd_order_check: compila y detecta orden invertido en un repo sintético
code, _ = run("tdd_order_check.py", "--help")
check("tdd_order_check.py compilable y con CLI", code == 0)
with tempfile.TemporaryDirectory() as tmp:
    subprocess.run(["git", "init", "-q"], cwd=tmp, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.co"], cwd=tmp, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp, capture_output=True)
    for msg in ("chore: init", "feat(HU-001): green", "test(HU-001): red"):
        open(os.path.join(tmp, "f.txt"), "a").write(msg + "\n")
        subprocess.run(["git", "add", "."], cwd=tmp, capture_output=True)
        subprocess.run(["git", "commit", "-qm", msg], cwd=tmp, capture_output=True)
    r = subprocess.run([sys.executable, os.path.join(ORCH, "tdd_order_check.py"),
                        "--range", "HEAD~2..HEAD"],
                       capture_output=True, text=True, cwd=tmp)
    check("tdd_order_check detecta código antes que test (exit 1)",
          r.returncode == 1 and "VIOLACION HU-001" in r.stdout,
          (r.stdout + r.stderr).splitlines()[-1] if r.returncode != 1 else "")

# ── 9b. Assets YAML válidos (lección v2.15.2: flow map con ${{ rompió CI) ────
print("\n[9b] Assets .yml/.yaml de las skills parsean como YAML válido")
try:
    import yaml as _yaml
    _bad = []
    for base, _, files in os.walk(os.path.join(ROOT, "skills")):
        for f in files:
            if f.endswith((".yml", ".yaml")):
                p = os.path.join(base, f)
                try:
                    _yaml.safe_load(open(p, encoding="utf-8"))
                except Exception as e:
                    _bad.append(f"{os.path.relpath(p, ROOT)}: {str(e).splitlines()[-1]}")
    check("todos los assets YAML parsean", not _bad, " | ".join(_bad))
except ImportError:
    check("todos los assets YAML parsean", True, "(pyyaml no disponible — omitido)")

# ── 9c. diagram_ir.py: validate / render / check / diff (ADR-003) ───────────
print("\n[9c] Diagramas IR interactivos (diagram_ir.py)")
DIR_SCRIPT = os.path.join(ROOT, "skills", "sdlc-diagrams", "scripts", "diagram_ir.py")
FIX = os.path.join(ROOT, "tests", "fixtures")
def rund(*args):
    p = subprocess.run([sys.executable, DIR_SCRIPT, *args], capture_output=True, text=True, cwd=ROOT)
    return p.returncode, (p.stdout + p.stderr).strip()

for fx in ("diagram-flow.ir.json", "diagram-sequence.ir.json"):
    code, out = rund("validate", "--ir", os.path.join(FIX, fx))
    check(f"validate acepta fixture {fx}", code == 0, out)
    code, out = rund("validate", "--ir", os.path.join(FIX, fx))
    with tempfile.TemporaryDirectory() as tmp:
        out_html = os.path.join(tmp, fx.replace(".ir.json", ".html"))
        code, out = rund("render", "--ir", os.path.join(FIX, fx), "--out", out_html)
        cond = code == 0 and os.path.exists(out_html)
        if cond:
            content = open(out_html, encoding="utf-8").read()
            cond = "insights" in content and "#focus=" in content and "http" not in content.replace("http://www.w3.org/2000/svg", "")
        check(f"render {fx}: HTML auto-contenido con insights e interaccion", cond, out)
        code, out = rund("check", "--ir", os.path.join(FIX, fx), "--out", out_html)
        check(f"check {fx}: sin drift tras render", code == 0, out)
        # drift: tocar el HTML
        open(out_html, "a", encoding="utf-8").write("<!-- editado a mano -->")
        code, out = rund("check", "--ir", os.path.join(FIX, fx), "--out", out_html)
        check(f"check {fx}: detecta HTML editado a mano (exit 1)", code == 1, out)

# validate rechaza IR roto
with tempfile.TemporaryDirectory() as tmp:
    bad = os.path.join(tmp, "bad.ir.json")
    json.dump({"titulo": "roto", "nodos": [{"id": "a", "titulo": "A", "tipo": "service"}],
               "aristas": [{"desde": "a", "hasta": "fantasma", "label": "x"}]}, open(bad, "w", encoding="utf-8"))
    code, out = rund("validate", "--ir", bad)
    check("validate rechaza arista a nodo inexistente (exit 1)", code == 1 and "fantasma" in out, out)

# diff: sin cambios exit 0; con cambios exit 2 y lista el agregado
code, out = rund("diff", "--old", os.path.join(FIX, "diagram-flow.ir.json"),
                 "--new", os.path.join(FIX, "diagram-flow.ir.json"))
check("diff sin cambios: exit 0", code == 0 and "Agregados (0)" in out, out)
with tempfile.TemporaryDirectory() as tmp:
    mod = json.load(open(os.path.join(FIX, "diagram-flow.ir.json"), encoding="utf-8"))
    mod["nodos"].append({"id": "nuevo", "titulo": "Nuevo", "tipo": "job"})
    p2 = os.path.join(tmp, "mod.ir.json")
    json.dump(mod, open(p2, "w", encoding="utf-8"))
    code, out = rund("diff", "--old", os.path.join(FIX, "diagram-flow.ir.json"), "--new", p2)
    check("diff detecta nodo agregado (exit 2)", code == 2 and "[nodo] nuevo" in out, out)

# ── 9d. mdview: visor Markdown de la spec dentro del portal (v2.18/2.20) ─────
print("\n[9d] mdview.py (docs Markdown → páginas del portal)")
MDV = os.path.join(ORCH, "mdview.py")
sys.path.insert(0, ORCH)
import mdview
import portal_lib
html_md = mdview.render_md(
    "# Titulo\n\nTexto con **negrita** y `codigo`.\n\n"
    "| A | B |\n|---|---|\n| 1 | 2 |\n\n"
    "- item\n- item2\n\n```mermaid\nflowchart LR\n A-->B\n```\n\n> cita\n\n[enlace](x.md)\n")
check("mdview renderiza encabezado/tabla/lista/codigo/cita/enlace",
      all(t in html_md for t in ("<h1>", "<table>", "<li>", "<pre>", "<blockquote>", "<a href")))
check("mdview: mermaid queda como codigo (sin red)",
      "mermaid (ver fuente)" in html_md and "cdn" not in html_md)
check("mdview doc_name: ruta anidada -> nombre unico",
      mdview.doc_name("reports/sprint-review-11.md") == "reports__sprint-review-11.html")
with tempfile.TemporaryDirectory() as tmp:
    spec = os.path.join(tmp, "spec")
    os.makedirs(os.path.join(spec, "reports"))
    open(os.path.join(spec, "vision.md"), "w", encoding="utf-8").write(
        "# Vision\n\nHola **mundo**. Ver [review](reports/sprint-review-01.md).")
    open(os.path.join(spec, "reports", "sprint-review-01.md"), "w", encoding="utf-8").write("# S1\n\ncierre.")
    n = mdview.build(spec)
    docs_dir = os.path.join(spec, "portal", "paginas", "docs")
    pag = open(os.path.join(docs_dir, "vision.html"), encoding="utf-8").read()
    check("mdview build: genera paginas en portal/paginas/docs",
          n == 2 and os.path.isfile(os.path.join(docs_dir, "reports__sprint-review-01.html")))
    check("mdview pagina: identidad portal (tokens + data-page-id), sin backlink",
          "<b>mundo</b>" in pag and "data-page-id=" in pag and "--bg:" in pag
          and "dashboard.html" not in pag)
    check("mdview: enlaces .md internos reescritos a su pagina",
          'href="reports__sprint-review-01.html"' in pag)
    reg = portal_lib._load_registry(spec)
    check("mdview: cada doc queda registrado en el portal con texto buscable",
          any(i["ruta"] == "paginas/docs/vision.html" and "mundo" in i["texto"]
              for i in reg["items"]))

# ── 9f. Portal único del proyecto (v2.20) ────────────────────────────────────
print("\n[9f] Portal único (shell + registry + búsqueda + drift)")
PORTAL = os.path.join(FIXTURE, "spec", "portal")
shell = open(os.path.join(PORTAL, "index.html"), encoding="utf-8").read()
check("portal: shell con sidebar, buscador Ctrl+K, ayuda, migas y tema compartido",
      all(t in shell for t in ("PORTAL_MANIFEST", "#/id/", "dir-tema", "Ctrl+K",
                               "portal-version", "helpbox", "topxtra",
                               "crumbs", "portal-last-")))
man = open(os.path.join(PORTAL, "manifest.js"), encoding="utf-8").read()
check("portal: manifest con páginas densas, docs, diagrama y topbar",
      all(t in man for t in ('"inicio"', '"metricas"', '"arquitectura"', '"memoria"',
                             "docs-vision", "diagrams-arquitectura", '"topbar"', "Glosario")))
check("portal: glosario oculto del menú lateral (solo topbar/buscador)",
      '"oculto": true' in man)
idx = open(os.path.join(PORTAL, "search-index.js"), encoding="utf-8").read()
check("portal: índice de búsqueda cubre docs y métricas (texto plano)",
      "PORTAL_INDEX" in idx and "PostgreSQL" in idx)
ini = open(os.path.join(PORTAL, "paginas", "inicio.html"), encoding="utf-8").read()
check("portal: inicio denso — pipeline compacto + acumulado en una pantalla",
      "graph-wrap" in ini and "FASES=" in ini and "Acumulado del proyecto" in ini
      and "data-page-id=" in ini)
arq = open(os.path.join(PORTAL, "paginas", "arquitectura.html"), encoding="utf-8").read()
check("portal: arquitectura vincula diagramas y ADR↔radar (data-tech)",
      "dcard" in arq and "#/id/diagrams-arquitectura" in arq
      and 'data-tech="postgresql"' in arq and "tr.adr-row" in arq)
check("portal: artefactos del popup navegan dentro del portal (target _top)",
      '../index.html#/id/' in ini and "_top" in ini)
dash = open(os.path.join(FIXTURE, "spec", "dashboard.html"), encoding="utf-8").read()
check("portal: dashboard.html es redirect pero conserva dashboard-state",
      "portal/index.html" in dash and "dashboard-state:" in dash)
code, out = run("portal_lib.py", "--spec", os.path.join(FIXTURE, "spec"), "--check")
check("portal: check OK tras regenerar", code == 0, out)
# poda: registrar una página fantasma y reconstruir → desaparece del manifiesto
portal_lib.register(os.path.join(FIXTURE, "spec"), origen="test", kind="doc",
                    ruta="paginas/fantasma.html", titulo="Fantasma")
portal_lib.rebuild_index(os.path.join(FIXTURE, "spec"))
man = open(os.path.join(PORTAL, "manifest.js"), encoding="utf-8").read()
check("portal: rebuild poda páginas cuyo archivo ya no existe", "fantasma" not in man)
code, out = run("portal_lib.py", "--spec", os.path.join(FIXTURE, "spec"), "--check")
check("portal: check sigue OK tras la poda", code == 0, out)
# drift detectable: tocar manifest.js debe romper el check
_man = os.path.join(PORTAL, "manifest.js")
_orig = open(_man, encoding="utf-8").read()
try:
    open(_man, "w", encoding="utf-8").write(_orig.replace('"inicio"', '"inicioX"', 1))
    code, _ = run("portal_lib.py", "--spec", os.path.join(FIXTURE, "spec"), "--check")
    check("portal: drift detectado al tocar manifest.js", code == 1)
finally:
    open(_man, "w", encoding="utf-8").write(_orig)
code, out = run("portal_lib.py", "--spec", os.path.join(FIXTURE, "spec"), "--check")
check("portal: manifest restaurado, check OK de nuevo", code == 0, out)

# ── 9e. pipeline_diagram: lenguaje visual comun (v2.19); drawio retirado (v2.20) ──
print("\n[9e] Pipeline CI/CD derivado (--tema, labels) + retiro de drawio")
DIR_SCRIPTS = os.path.join(ROOT, "skills", "sdlc-diagrams", "scripts")
def rund2(script, *args):
    p = subprocess.run([sys.executable, script, *args], capture_output=True, text=True, cwd=ROOT)
    return p.returncode, (p.stdout + p.stderr).strip()
with tempfile.TemporaryDirectory() as tmp:
    # workflow mínimo con job de nombre largo
    wf_dir = os.path.join(tmp, "workflows")
    os.makedirs(wf_dir)
    open(os.path.join(wf_dir, "ci.yml"), "w", encoding="utf-8").write(
        "name: CI\non: [push]\njobs:\n"
        "  lint-y-unit-tests-backend-frontend:\n    steps:\n      - run: pytest\n"
        "  contract-e2e:\n    needs: lint-y-unit-tests-backend-frontend\n    steps:\n      - run: e2e\n")
    pip = os.path.join(DIR_SCRIPTS, "pipeline_diagram.py")
    out_m = os.path.join(tmp, "pipeline.md")
    code, out = rund2(pip, "generate", "--workflows-dir", wf_dir, "--out", out_m, "--tema", "oscuro")
    md = open(out_m, encoding="utf-8").read() if code == 0 else ""
    check("pipeline_diagram: --tema oscuro emite init dark", code == 0 and "'theme': 'dark'" in md, out)
    check("pipeline_diagram: labels largos se quiebran con <br/>", "<br/>" in md, "")
    code, out = rund2(pip, "check", "--workflows-dir", wf_dir, "--out", out_m)
    check("pipeline_diagram: check detecta el tema grabado (sin drift)", code == 0, out)
    code, out = rund2(pip, "generate", "--workflows-dir", wf_dir, "--out", out_m)
    md = open(out_m, encoding="utf-8").read() if code == 0 else ""
    check("pipeline_diagram: tema auto no emite init (el renderer elige)",
          code == 0 and "%%{init:" not in md, out)
    # v2.20: drawio retirado — diagram_render rechaza .drawio y sugiere la via vigente
    fake = os.path.join(tmp, "viejo.drawio")
    open(fake, "w", encoding="utf-8").write("<mxfile/>")
    code, out = rund2(os.path.join(DIR_SCRIPTS, "diagram_render.py"), "render", fake)
    check("diagram_render: .drawio rechazado con mensaje de retiro (v2.20)",
          code == 1 and "v2.20" in out, out)

# ── 10. Memoria de auditoría (ADR-004, v2.21) ────────────────────────────────
print("\n[10] Memoria de auditoría: append-only, cadena de hash, ts UTC + harness_version")
with tempfile.TemporaryDirectory() as tmp:
    os.makedirs(os.path.join(tmp, "spec"))
    def runa(script, *args):
        p = subprocess.run([sys.executable, os.path.join(ORCH, script), "--spec-dir", "spec/",
                            *args], capture_output=True, text=True, cwd=tmp)
        return p.returncode, (p.stdout + p.stderr).strip()
    def events():
        p = os.path.join(tmp, "spec", "audit", "events.jsonl")
        if not os.path.isfile(p):
            return []
        return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]

    code, out = runa("audit_log.py", "append", "--evento", "emit")
    check("audit: append antes de init rechazado (exit 1)", code == 1, out)
    code, out = runa("audit_log.py", "init", "--proyecto", "demo")
    evs = events()
    check("audit: init crea génesis audit_init con hash y versión",
          code == 0 and len(evs) == 1 and evs[0]["evento"] == "audit_init"
          and evs[0]["prev_hash"] == "0" * 64 and "harness_version" in evs[0], out)
    check("audit: ts del génesis es UTC ISO-8601 con zona",
          bool(evs) and re.search(r"\+\d{2}:\d{2}$|Z$", evs[0]["ts"]) is not None,
          evs[0]["ts"] if evs else "sin eventos")
    code, out = runa("audit_log.py", "init", "--proyecto", "demo")
    check("audit: doble init rechazado (exit 1)", code == 1, out)

    art = os.path.join(tmp, "spec", "vision.md")
    open(art, "w", encoding="utf-8").write("# visión\n")
    code, out = runa("receipt.py", "emit", art, "--gate", "GATE 0",
                     "--role", "product-owner", "--approved-by", "Karlo")
    evs = events()
    emit_ev = [e for e in evs if e["evento"] == "emit"]
    check("audit: receipt emit registra evento con aprobador y ruta relativa",
          code == 0 and len(emit_ev) == 1
          and emit_ev[0].get("approved_by") == "Karlo"
          and emit_ev[0].get("artefacto") == "spec/vision.md", out)

    open(art, "a", encoding="utf-8").write("cambio\n")
    code, out = runa("receipt.py", "verify", art)
    inv_ev = [e for e in events() if e["evento"] == "invalidado"]
    check("audit: verify ante cambio registra 'invalidado' con hashes anterior/nuevo",
          code == 1 and len(inv_ev) == 1
          and inv_ev[0].get("sha256_anterior") and inv_ev[0].get("sha256_nuevo"), out)

    code, out = runa("receipt.py", "revoke", art)
    check("audit: revoke sin --reason rechazado (ADR-004)", code != 0, out)
    code, out = runa("receipt.py", "revoke", art, "--reason", "cambio de spec",
                     "--relation", "supersedes")
    rev_ev = [e for e in events() if e["evento"] == "revocado"]
    check("audit: revoke con razón registra evento revocado",
          code == 0 and len(rev_ev) == 1 and rev_ev[0].get("reason") == "cambio de spec", out)

    code, out = runa("receipt.py", "emit", art, "--gate", "GATE 0", "--role", "product-owner",
                     "--approved-by", "Karlo")
    reem = [e for e in events() if e["evento"] == "emit"]
    check("audit: re-emisión tras revocación queda marcada como retrabajo",
          code == 0 and len(reem) == 2 and "re-emision" in reem[1].get("nota", ""), out)

    code, out = runa("audit_verify.py")
    check("audit: verify acepta la traza íntegra (exit 0)", code == 0, out)

    # tamper 1: modificar el contenido de un evento pasado rompe su hash
    logp = os.path.join(tmp, "spec", "audit", "events.jsonl")
    orig = open(logp, encoding="utf-8").read().splitlines()
    lines = list(orig)
    ev2 = json.loads(lines[1]); ev2["gate"] = "GATE 99"
    lines[1] = json.dumps(ev2, ensure_ascii=False)
    open(logp, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    code, out = runa("audit_verify.py")
    check("audit: verify detecta evento manipulado (exit 1)", code == 1 and "manipulado" in out, out)

    # restaurar y tamper 2: eliminar un evento intermedio rompe seq + cadena
    lines = list(orig)
    del lines[2]
    open(logp, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    code, out = runa("audit_verify.py")
    check("audit: verify detecta evento intermedio eliminado (exit 1)", code == 1, out)

# ── 10b. N8: métricas derivadas del log de auditoría (hechos, no estados) ────
print("\n[10b] Métricas desde la memoria de auditoría: el retrabajo ya no vuelve a cero")
with tempfile.TemporaryDirectory() as tmp:
    os.makedirs(os.path.join(tmp, "spec"))
    def runm(script, *args):
        return run(script, "--spec-dir", "spec/", *args, cwd=tmp)
    runm("audit_log.py", "init", "--proyecto", "demo")
    art = os.path.join(tmp, "spec", "vision.md")
    open(art, "w", encoding="utf-8").write("# v1\n")

    # N3: catálogo de gates + aprobador humano exigible
    code, out = runm("receipt.py", "emit", art, "--gate", "gate2", "--role", "product-owner")
    check("N3: gate inventado ('gate2') rechazado — catálogo cerrado",
          code == 1 and "catalogo" in out, out)
    code, out = runm("receipt.py", "emit", art, "--gate", "GATE 0", "--role", "product-owner")
    check("N3: gate humano sin --approved-by rechazado (anti auto-aprobación)",
          code == 1 and "auto-aprobarse" in out, out)

    runm("receipt.py", "emit", art, "--gate", "GATE 0", "--role", "product-owner",
         "--approved-by", "Karlo")
    open(art, "a", encoding="utf-8").write("cambio\n")
    runm("receipt.py", "verify", art)                       # -> invalidado
    runm("receipt.py", "revoke", art, "--reason", "supersedes de vision")
    runm("receipt.py", "emit", art, "--gate", "GATE 0", "--role", "product-owner",
         "--attempts", "2", "--approved-by", "Karlo")       # re-emision (retrabajo)
    art2 = os.path.join(tmp, "spec", "backlog.md")
    open(art2, "w", encoding="utf-8").write("# b\n")
    runm("receipt.py", "emit", art2, "--gate", "GATE-0", "--role", "product-owner",
         "--approved-by", "Karlo")                           # variante GATE-0
    import json as _j
    evs = [_j.loads(l) for l in open(os.path.join(tmp, "spec", "audit", "events.jsonl"), encoding="utf-8") if l.strip()]
    emit_gates = [e.get("gate") for e in evs if e["evento"] == "emit"]
    check("N3: 'GATE-0' se normaliza y se registra como 'GATE 0'",
          emit_gates == ["GATE 0", "GATE 0", "GATE 0"], str(emit_gates))

    # N3: status --strict en verde (aún sin invalidaciones extra)
    code, out = runm("receipt.py", "status", "--strict")
    check("N3: status --strict en verde con todos los recibos vigentes",
          code == 0 and "STRICT" in out, out)

    code, out = runm("skill_metrics.py", "report", "--stdout")
    check("N8 metrics: declara la memoria de auditoría como fuente",
          code == 0 and "Fuente: memoria de auditoria" in out, out)
    check("N8 metrics: retrabajo visible por skill (invalidado+revocado)",
          "2 retrabajo(s)" in out, out)
    check("N8 metrics: activaciones use del log fusionadas (1 auto, sin duplicar)",
          "| product-owner | 1 | 3 |" in out, out)

    code, out = runm("sprint_review.py", "--sprint", "1", "--stdout")
    check("N8 sprint: retrabajo cuenta eventos tras re-aprobar (**2**, antes 0)",
          code == 0 and "Trabajo rehecho (recibos invalidados/revocados): **2**" in out, out)
    check("N8 sprint: 'primer intento' con fórmula única (67% = 2/3 emisiones)",
          "Gates al primer intento: **67%**" in out, out)
    check("N8 sprint: variantes de gate normalizadas (GATE-0 ≡ GATE 0, una fila)",
          out.count("| GATE 0 |") == 2 and "GATE-0" not in out, out)

    # N3: status --strict falla cuando aparece un recibo no vigente (al final,
    # para no contaminar los conteos de retrabajo de los checks N8 anteriores)
    open(art2, "a", encoding="utf-8").write("cambio sin gate\n")
    runm("receipt.py", "verify", art2)                       # invalida backlog.md
    code, out = runm("receipt.py", "status", "--strict")
    check("N3: status --strict falla (exit 1) con un recibo invalidado",
          code == 1 and "invalidado" in out, out)

# ── 10c. N6: diagramas IR exigibles — validate con ubicacion + gates ─────────
print("\n[10c] Gates de diagramas IR: la arquitectura vuelve a exigir diagramas")
import json as _j2
with tempfile.TemporaryDirectory() as tmp:
    os.makedirs(os.path.join(tmp, "spec", "diagrams"))
    # 1. validate: tipo architecture exige ubicacion en todos los nodos
    ir = {"kind": "flow", "tipo": "architecture", "titulo": "t",
          "nodos": [{"id": "a", "titulo": "A", "tipo": "service"},
                    {"id": "b", "titulo": "B", "tipo": "db", "ubicacion": "AWS"}],
          "aristas": [{"desde": "a", "hasta": "b", "label": "SQL"}]}
    p = os.path.join(tmp, "sin-ubi.ir.json")
    open(p, "w", encoding="utf-8").write(_j2.dumps(ir))
    code, out = rund("validate", "--ir", p)
    check("N6: IR tipo architecture con nodo sin 'ubicacion' NO pasa validate",
          code == 1 and "ubicacion" in out, out)
    ir["nodos"][0]["ubicacion"] = "Azure"
    open(p, "w", encoding="utf-8").write(_j2.dumps(ir))
    code, out = rund("validate", "--ir", p)
    check("N6: IR tipo architecture con ubicaciones pasa validate", code == 0, out)
    ir["tipo"] = "foo"
    open(p, "w", encoding="utf-8").write(_j2.dumps(ir))
    code, out = rund("validate", "--ir", p)
    check("N6: 'tipo' fuera del catálogo rechazado por validate", code == 1, out)
    # sin tipo (IRs antiguos) sigue validando: retrocompatible
    del ir["tipo"]; ir["nodos"][0].pop("ubicacion")
    open(p, "w", encoding="utf-8").write(_j2.dumps(ir))
    code, out = rund("validate", "--ir", p)
    check("N6: IR sin 'tipo' (pre-v2.21) sigue validando", code == 0, out)

    # 2. gate architecture: mermaid suelto ya no cumple; IR + recibo vigente sí
    arch = os.path.join(tmp, "spec", "architecture.md")
    open(arch, "w", encoding="utf-8").write(
        "# Arq\n```mermaid\nflowchart LR\n A-->B\n```\n## Componentes\n## Requisitos no funcionales\n")
    code, out = run("gate_checker.py", arch, "--tipo", "architecture", cwd=tmp)
    check("N6: architecture con solo mermaid NO pasa el gate",
          code == 1 and "Sin diagrama IR" in out, out)
    open(arch, "a", encoding="utf-8").write("\nVer `diagrams/c4.ir.json`\n")
    code, out = run("gate_checker.py", arch, "--tipo", "architecture", cwd=tmp)
    check("N6: IR referenciado inexistente NO pasa el gate",
          code == 1 and "no existe" in out, out)
    irpath = os.path.join(tmp, "spec", "diagrams", "c4.ir.json")
    ir["tipo"] = "architecture"
    ir["nodos"][0]["ubicacion"] = "AWS"
    open(irpath, "w", encoding="utf-8").write(_j2.dumps(ir))
    code, out = run("gate_checker.py", arch, "--tipo", "architecture", cwd=tmp)
    check("N6: IR referenciado y válido pasa (proyecto aún sin recibos)",
          code == 0, out)
    os.makedirs(os.path.join(tmp, "spec", "receipts"))   # el proyecto ya gobierna
    code, out = run("gate_checker.py", arch, "--tipo", "architecture", cwd=tmp)
    check("N6: con recibos activos, IR sin recibo NO pasa el gate",
          code == 1 and "sin recibo" in out, out)
    run("receipt.py", "--spec-dir", "spec/", "emit", irpath, "--gate", "FASE-2",
        "--role", "software-architect", cwd=tmp)
    code, out = run("gate_checker.py", arch, "--tipo", "architecture", cwd=tmp)
    check("N6: IR con recibo vigente pasa el gate", code == 0, out)
    open(irpath, "a", encoding="utf-8").write(" ")        # edición sin re-aprobar
    code, out = run("gate_checker.py", arch, "--tipo", "architecture", cwd=tmp)
    check("N6: IR editado tras su recibo NO pasa (hash no coincide)",
          code == 1 and "hash no coincide" in out, out)

    # 3. architecture-proposal: cada opción exige su diagrama IR
    prop = os.path.join(tmp, "spec", "architecture-proposal.md")
    base = ("# Propuesta\n## Contexto y objetivo de negocio\nx\n"
            "### Opción A: mono\n- Diagrama: `spec/diagrams/prop-a.ir.json`\n- ADR-P-001\n"
            "### Opción B: micro\n- Componentes: sin diagrama\n- ADR-P-002\n"
            "## Comparativa\n## Recomendación\n## Estimación de costos\n")
    open(prop, "w", encoding="utf-8").write(base)
    code, out = run("gate_checker.py", prop, "--tipo", "architecture-proposal", cwd=tmp)
    check("N6: opción sin diagrama IR NO pasa la propuesta",
          code == 1 and "Opción B sin diagrama IR" in out, out)
    open(prop, "w", encoding="utf-8").write(
        base.replace("- Componentes: sin diagrama",
                     "- Diagrama: `spec/diagrams/prop-b.ir.json`"))
    code, out = run("gate_checker.py", prop, "--tipo", "architecture-proposal", cwd=tmp)
    check("N6: propuesta con diagrama por opción pasa el gate", code == 0, out)

# ── 10d. N9: arch_lint — invariantes arquitectónicos ejecutables ─────────────
print("\n[10d] arch_lint: la arquitectura por capas es política binaria")
with tempfile.TemporaryDirectory() as tmp:
    def w(rel, content):
        p = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(content)
        return p

    def runl(*args):
        return run("arch_lint.py", "--root", tmp, "--spec-dir",
                   os.path.join(tmp, "spec"), *args, cwd=tmp)

    # sin reglas declaradas: condicional, exit 0
    code, out = runl()
    check("N9: sin architecture-rules.yaml no hay nada que verificar (exit 0)",
          code == 0 and "nada que verificar" in out, out)

    w("spec/architecture-rules.yaml", """version: 1
layers:
  - {name: ui, paths: ["frontend/"]}
  - {name: domain, paths: ["src/domain/"]}
  - {name: infra, paths: ["src/infra/"]}
forbidden:
  - "domain -> *"
  - "ui -> domain"
""")
    # código limpio → verde
    w("src/domain/model.py", "class Pedido:\n    pass\n")
    w("src/infra/repo.py", "from src.domain.model import Pedido\n")
    code, out = runl()
    check("N9: dependencias permitidas pasan (infra -> domain)", code == 0, out)

    # violación Python: domain importa infra
    w("src/domain/service.py", "from src.infra.repo import Pedido\n")
    code, out = runl()
    check("N9: domain importando infra es violación (exit 1, 'domain -> *')",
          code == 1 and "domain" in out and "infra" in out, out)
    os.remove(os.path.join(tmp, "src", "domain", "service.py"))

    # violación JS: ui importa domain directo
    w("frontend/app.js", "import { Pedido } from '../src/domain/model.js';\n")
    w("src/domain/model.js", "export class Pedido {}\n")
    code, out = runl()
    check("N9: ui importando domain en JS es violación ('ui -> domain')",
          code == 1 and "app.js" in out, out)
    os.remove(os.path.join(tmp, "frontend", "app.js"))

    # config inválida: regla que cita capa no declarada
    w("spec/architecture-rules.yaml", """layers:
  - {name: a, paths: ["src/a/"]}
forbidden:
  - "a -> fantasmas"
""")
    code, out = runl()
    check("N9: regla que cita capa no declarada = config inválida (exit 1)",
          code == 1 and "no declarada" in out, out)

    # reglas declaradas sin forbidden: política vacía, falla
    w("spec/architecture-rules.yaml", "layers:\n  - {name: a, paths: ['src/a/']}\n")
    code, out = runl()
    check("N9: reglas sin 'forbidden' no controlan nada (exit 1)",
          code == 1 and "forbidden" in out, out)

    # evento en la memoria de auditoría (ADR-004)
    w("spec/architecture-rules.yaml", """layers:
  - {name: a, paths: ["src/a/"]}
forbidden:
  - "a -> *"
""")
    run("audit_log.py", "--spec-dir", os.path.join(tmp, "spec"), "init",
        "--proyecto", "lint", cwd=tmp)
    runl()
    evs = [_j2.loads(l) for l in
           open(os.path.join(tmp, "spec", "audit", "events.jsonl"), encoding="utf-8")]
    lint_ev = [e for e in evs if e["evento"] == "arch_lint"]
    check("N9: cada corrida registra evento arch_lint en la auditoría",
          len(lint_ev) == 1 and lint_ev[0].get("resultado") == "ok"
          and lint_ev[0].get("harness_version"), str(lint_ev))

# ── 10e. N10: contract_diff — breaking changes no declarados bloquean ────────
print("\n[10e] contract_diff: la interfaz pública blindada")
with tempfile.TemporaryDirectory() as tmp:
    V1 = """openapi: 3.0.3
info: {title: API, version: 1.2.0}
paths:
  /pedidos:
    get:
      parameters:
        - {name: page, schema: {type: integer}}
      responses:
        '200':
          content:
            application/json:
              schema: {properties: {id: {type: string}, total: {type: number}}}
  /legacy:
    get:
      responses: {'200': {description: ok}}
components: {}
"""
    V2_COMPAT = V1.replace("version: 1.2.0", "version: 1.3.0").replace(
        "  /legacy:", """  /nuevo:
    post:
      responses: {'201': {description: creado}}
  /legacy:""")
    V2_BREAK = V1.replace("  /legacy:\n    get:\n      responses: {'200': {description: ok}}\n", "") \
                 .replace("- {name: page, schema: {type: integer}}",
                          "- {name: page, schema: {type: string}}") \
                 .replace(", total: {type: number}", "")
    V2_BREAK_BUMP = V2_BREAK.replace("version: 1.2.0", "version: 2.0.0")

    def w2(name, content):
        p = os.path.join(tmp, name)
        open(p, "w", encoding="utf-8").write(content)
        return p

    old_f = w2("old.yaml", V1)
    def runc(*args):
        return run("contract_diff.py", "--spec-dir", os.path.join(tmp, "spec"), *args, cwd=tmp)

    code, out = runc("--old", old_f, "--new", w2("compat.yaml", V2_COMPAT))
    check("N10: cambios compatibles pasan (exit 0)", code == 0 and "0 breaking" in out, out)
    code, out = runc("--old", old_f, "--new", w2("break.yaml", V2_BREAK))
    check("N10: breaking sin bump de mayor bloquea (exit 1)",
          code == 1 and "GATE BLOQUEADO" in out and "path eliminado" in out, out)
    code, out = runc("--old", old_f, "--new", w2("bump.yaml", V2_BREAK_BUMP))
    check("N10: breaking declarado con bump mayor pasa", code == 0, out)

    # integración con el gate api-contract vía git
    repo = os.path.join(tmp, "repo")
    os.makedirs(os.path.join(repo, "spec"))
    apif = os.path.join(repo, "spec", "api-contract.yaml")
    open(apif, "w", encoding="utf-8").write(V1)
    for c in (["git", "init", "-q"], ["git", "add", "."],
              ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "v1"]):
        subprocess.run(c, cwd=repo, capture_output=True)
    open(apif, "w", encoding="utf-8").write(V2_BREAK)
    code, out = run("gate_checker.py", apif, "--tipo", "api-contract", cwd=repo)
    check("N10: gate api-contract bloquea breaking sin declarar (contra git)",
          code == 1 and "breaking change" in out, out)
    open(apif, "w", encoding="utf-8").write(V2_BREAK_BUMP)
    code, out = run("gate_checker.py", apif, "--tipo", "api-contract", cwd=repo)
    check("N10: gate api-contract pasa con bump mayor declarado", code == 0, out)

    # evento en la auditoría
    os.makedirs(os.path.join(tmp, "spec"), exist_ok=True)
    run("audit_log.py", "--spec-dir", os.path.join(tmp, "spec"), "init",
        "--proyecto", "contratos", cwd=tmp)
    runc("--old", old_f, "--new", old_f)
    evs = [_j2.loads(l) for l in
           open(os.path.join(tmp, "spec", "audit", "events.jsonl"), encoding="utf-8")]
    cd_ev = [e for e in evs if e["evento"] == "contract_diff"]
    check("N10: cada comparación registra evento contract_diff en la auditoría",
          len(cd_ev) == 1 and cd_ev[0].get("resultado") == "ok", str(cd_ev))

# ── 10f. N4: init_project + gate_verify — arranque y gates deterministas ─────
print("\n[10f] Arranque determinista: todo proyecto inicia igual y los gates se ejecutan")
with tempfile.TemporaryDirectory() as tmp:
    def runi(*args):
        return run("init_project.py", *args, cwd=tmp)

    code, out = runi("--proyecto", "demo")
    check("N4: init_project crea el scaffold completo (exit 0)",
          code == 0 and "PROYECTO INICIALIZADO" in out, out)
    esperados = ["spec/authority-matrix.yaml", "spec/team-roster.yaml",
                 "spec/tech-radar.yaml", "spec/audit/events.jsonl",
                 "spec/ux", "spec/receipts", "spec/memory/entries"]
    faltan = [e for e in esperados
              if not os.path.exists(os.path.join(tmp, *e.split("/")))]
    check("N4: estructura mínima creada (matriz, roster, radar, auditoría, dirs)",
          not faltan, str(faltan))
    check("N4: sin --capas no se scaffoldan reglas de arquitectura",
          not os.path.exists(os.path.join(tmp, "spec", "architecture-rules.yaml")))
    evs = [_j2.loads(l) for l in
           open(os.path.join(tmp, "spec", "audit", "events.jsonl"), encoding="utf-8")]
    check("N4: auditoría nace con génesis + bootstrap (versión y fecha registradas)",
          [e["evento"] for e in evs] == ["audit_init", "bootstrap"]
          and all(e.get("harness_version") and e.get("ts") for e in evs), str(evs))

    # idempotente: no pisa archivos existentes
    mpath = os.path.join(tmp, "spec", "authority-matrix.yaml")
    open(mpath, "a", encoding="utf-8").write("# custom del proyecto\n")
    code, out = runi("--proyecto", "demo")
    check("N4: init es idempotente — no sobrescribe (reporta saltados)",
          code == 0 and "no se tocó" in out
          and open(mpath, encoding="utf-8").read().endswith("# custom del proyecto\n"), out)
    evs2 = [_j2.loads(l) for l in
            open(os.path.join(tmp, "spec", "audit", "events.jsonl"), encoding="utf-8")]
    check("N4: re-init no duplica génesis ni bootstrap", len(evs2) == 2, str(len(evs2)))

    # gate_verify: GATE 0 recién inicializado falla listando faltantes
    def runv(*args):
        return run("gate_verify.py", "--spec-dir", os.path.join(tmp, "spec"),
                   "--root", tmp, *args, cwd=tmp)
    code, out = runv("--gate", "GATE 0")
    check("N4: gate_verify GATE 0 sin artefactos falla listándolos",
          code == 1 and "architecture-proposal.md" in out and "NO EXISTE" in out, out)
    code, out = runv("--gate", "gate2")
    check("N4: gate_verify rechaza gates fuera del catálogo", code == 1, out)

    # crear los 3 artefactos de GATE 0 + recibos → verde
    def w3(rel, content):
        p = os.path.join(tmp, rel)
        open(p, "w", encoding="utf-8").write(content)
        return p
    w3("spec/architecture-proposal.md",
       "# Propuesta\n## Contexto y objetivo de negocio\nx\n"
       "### Opción A: mono\n- Diagrama: `spec/diagrams/a.ir.json`\n- ADR-P-001\n"
       "### Opción B: micro\n- Diagrama: `spec/diagrams/b.ir.json`\n- ADR-P-002\n"
       "## Comparativa\n## Recomendación\n## Estimación de costos\n")
    w3("spec/technical-stories.md",
       "## TS-001\n- Tipo: enabler\n- Origen: NFR\n- Criterio de aceptación: x\n"
       "- Costo de NO hacerlo: y\n")
    w3("spec/cost-estimation.md",
       "CAPEX OPEX TCO\nValidez de precios: 30d\nMínimo viable / Pico\nSupuestos\n")
    for art, rol in (("architecture-proposal.md", "solution-architect"),
                     ("technical-stories.md", "solution-architect"),
                     ("cost-estimation.md", "cloud-pricing")):
        c, o = run("receipt.py", "--spec-dir", "spec/", "emit",
                   os.path.join(tmp, "spec", art), "--gate", "GATE 0",
                   "--role", rol, "--approved-by", "Karlo", cwd=tmp)
        assert c == 0, o
    code, out = runv("--gate", "GATE 0")
    check("N4: GATE 0 completo con recibos vigentes pasa (exit 0)",
          code == 0 and "3 verificados" in out, out)

    # editar un artefacto aprobado rompe el gate (hash no coincide)
    open(os.path.join(tmp, "spec", "cost-estimation.md"), "a",
         encoding="utf-8").write("cambio sin re-aprobar\n")
    code, out = runv("--gate", "GATE 0")
    check("N4: artefacto editado tras el recibo rompe gate_verify (exit 1)",
          code == 1 and "hash no coincide" in out, out)

    # condicional de routing: GATE 1 sin UI excluye los artefactos UX
    code, out = runv("--gate", "GATE 1", "--sin-ui")
    check("N4: --sin-ui excluye los artefactos condicionales del routing",
          "excluidos por routing" in out and "ux-flows" in out, out)

# ── 10g. N7: pipeline-state derivado — fin del estado narrado ────────────────
print("\n[10g] pipeline-state derivado de hechos, con --check anti-drift")
with tempfile.TemporaryDirectory() as tmp:
    run("init_project.py", "--proyecto", "demo", cwd=tmp)
    ps = os.path.join(tmp, "spec", "pipeline-state.md")
    check("N7: init_project genera el primer pipeline-state derivado",
          os.path.isfile(ps) and "DERIVADO" in open(ps, encoding="utf-8").read())

    def runp(*args):
        return run("pipeline_state.py", "--spec-dir", os.path.join(tmp, "spec"),
                   "--root", tmp, *args, cwd=tmp)
    code, out = runp("--check")
    check("N7: --check recién generado pasa (sin drift)", code == 0, out)

    # emitir un recibo → el estado derivado lo refleja
    v = os.path.join(tmp, "spec", "vision.md")
    open(v, "w", encoding="utf-8").write(
        "# V\n## Problema\nx\n## Usuarios objetivo\nx\n## Propuesta de valor\nx\n"
        "## Métricas de éxito\nx\n")
    run("receipt.py", "--spec-dir", "spec/", "emit", v, "--gate", "GATE 0",
        "--role", "product-owner", "--approved-by", "Karlo", cwd=tmp)
    runp()
    contenido = open(ps, encoding="utf-8").read()
    check("N7: el estado refleja el recibo emitido (gate + vigente + aprobador)",
          "| vision.md | product-owner | GATE 0 | vigente | Karlo |" in contenido
          and "| GATE 0 | 1 |" in contenido, contenido[-600:])

    # editado a mano = drift = fallo de CI
    open(ps, "a", encoding="utf-8").write("\nnarración manual\n")
    code, out = runp("--check")
    check("N7: edición manual detectada como drift (exit 1)",
          code == 1 and "DRIFT" in out, out)
    code, out = runp()
    check("N7: regenerar limpia el drift", code == 0, out)
    code, out = runp("--check")
    check("N7: --check vuelve a verde tras regenerar", code == 0, out)

# ── 10h. N2: invalidación derivada — el cambio no depende de la memoria ──────
print("\n[10h] Hash compuesto de dependencias + spec_diff_impact --apply")
with tempfile.TemporaryDirectory() as tmp:
    run("init_project.py", "--proyecto", "demo", cwd=tmp)
    def w4(rel, content):
        p = os.path.join(tmp, rel)
        open(p, "w", encoding="utf-8").write(content)
        return p
    VIS = "# V\n## Problema\nx\n## Usuarios objetivo\nx\n## Propuesta de valor\nx\n## Métricas de éxito\nx\n"
    HU = ("## HU-001\nComo visitante (ROL-001)\n### Escenario\n**Dado** d **Cuando** c "
          "**Entonces** e\nÉpica: EP-01\n")
    w4("spec/roles.md", "ROL-001\n## ROL-001\nAcciones que habilita: x\nContexto: y\n"
                        "Reglas que lo restringen: z\n")
    v = w4("spec/vision.md", VIS)
    hu = w4("spec/user-stories.md", HU)
    for art, rol in ((v, "product-owner"), (hu, "business-analyst")):
        c, o = run("receipt.py", "--spec-dir", "spec/", "emit", art,
                   "--gate", "GATE 0" if rol == "product-owner" else "FASE-1",
                   "--role", rol, "--approved-by", "Karlo", cwd=tmp)
        assert c == 0, o

    # el recibo de user-stories guarda el hash de sus dependencias upstream
    rec = _j2.load(open(os.path.join(tmp, "spec", "receipts",
                                     "user-stories.md.receipt.json"), encoding="utf-8"))
    check("N2: el recibo guarda hash de dependencias upstream (vision, backlog…)",
          rec.get("deps", {}).get("vision.md") and "roles.md" in rec["deps"],
          str(rec.get("deps")))

    # cambia vision.md y se re-emite: user-stories queda invalidado derivadamente
    w4("spec/vision.md", VIS + "cambio aprobado\n")
    run("receipt.py", "--spec-dir", "spec/", "emit", v, "--gate", "GATE 0",
        "--role", "product-owner", "--approved-by", "Karlo", cwd=tmp)
    code, out = run("receipt.py", "--spec-dir", "spec/", "verify", hu, cwd=tmp)
    check("N2: verify invalida derivadamente aunque el artefacto no cambió",
          code == 1 and "DERIVADAMENTE" in out and "vision.md" in out, out)
    evs = [_j2.loads(l) for l in
           open(os.path.join(tmp, "spec", "audit", "events.jsonl"), encoding="utf-8")]
    check("N2: la invalidación derivada queda auditada con su causa",
          any(e["evento"] == "invalidado" and "vision.md" in e.get("nota", "")
              for e in evs), str([e["evento"] for e in evs]))

    # re-emitir user-stories y probar --apply sobre un cambio de roles.md
    run("receipt.py", "--spec-dir", "spec/", "emit", hu, "--gate", "FASE-1",
        "--role", "business-analyst", cwd=tmp)
    code, out = run("spec_diff_impact.py", "--cambiado", "roles.md", "--apply",
                    "--spec-dir", os.path.join(tmp, "spec"), cwd=tmp)
    rec2 = _j2.load(open(os.path.join(tmp, "spec", "receipts",
                                      "user-stories.md.receipt.json"), encoding="utf-8"))
    check("N2: --apply invalida los recibos downstream vigentes",
          code == 0 and "invalidados" in out and rec2["estado"] == "invalidado",
          out + rec2["estado"])
    evs = [_j2.loads(l) for l in
           open(os.path.join(tmp, "spec", "audit", "events.jsonl"), encoding="utf-8")]
    check("N2: --apply audita la revocación derivada con origen y relación",
          any(e["evento"] == "invalidado" and "--apply" in e.get("nota", "")
              and "supersedes" in e.get("nota", "") for e in evs), "")
    code, out = run("receipt.py", "--spec-dir", "spec/", "status", "--strict", cwd=tmp)
    check("N2: status --strict refleja la invalidación derivada (exit 1)",
          code == 1, out)

# ── 10i. N5: check-vendored — el gobernado no edita al gobernante ────────────
print("\n[10i] check-vendored: scripts vendorados idénticos a la release o nada")
with tempfile.TemporaryDirectory() as tmp:
    def rund5(*args):
        return run("harness_doctor.py", *args, cwd=tmp)

    code, out = rund5("--project-dir", tmp, "--check-vendored")
    check("N5: proyecto sin scripts vendorados pasa (forma preferida)",
          code == 0 and "instalación" in out, out)

    os.makedirs(os.path.join(tmp, "scripts"))
    import shutil as _sh5
    _sh5.copyfile(os.path.join(ROOT, "skills", "sdlc-orchestrator", "scripts",
                               "receipt.py"), os.path.join(tmp, "scripts", "receipt.py"))
    code, out = rund5("--project-dir", tmp, "--check-vendored")
    check("N5: script vendorado idéntico a la release pasa",
          code == 0 and "idénticos" in out, out)

    with open(os.path.join(tmp, "scripts", "receipt.py"), "a", encoding="utf-8") as fh:
        fh.write("\n# Patch local: relajar gates\n")
    code, out = rund5("--project-dir", tmp, "--check-vendored")
    check("N5: patch local en script vendorado = fallo (exit 1, DRIFT)",
          code == 1 and "DRIFT" in out, out)

    open(os.path.join(tmp, "scripts", "iac_to_diagram.py"), "w").write("# retirado\n")
    code, out = rund5("--project-dir", tmp, "--check-vendored")
    check("N5: script ajeno a la release (retirado/local) = fallo",
          code == 1 and "NO pertenece a la release" in out, out)

# ── 10j. N11: circuit breaker con estado + blast radius sobre el diff ────────
print("\n[10j] HITL portable: reintentos congelables y alcance verificado")
with tempfile.TemporaryDirectory() as tmp:
    run("init_project.py", "--proyecto", "demo", cwd=tmp)
    def runcb(*args):
        return run("circuit_breaker.py", "--spec-dir", os.path.join(tmp, "spec"),
                   *args, cwd=tmp)

    code, out = runcb("fail", "--artefacto", "spec/qa-report.md", "--gate", "GATE 2",
                      "--motivo", "E2E roto")
    check("N11: primer fallo = corrección acotada autorizada (exit 0)",
          code == 0 and "1/1" in out, out)
    code, out = runcb("fail", "--artefacto", "spec/qa-report.md", "--gate", "GATE 2")
    check("N11: segundo fallo CONGELA (exit 1, escalar a humano)",
          code == 1 and "CONGELADO" in out, out)
    code, out = runcb("fail", "--artefacto", "spec/qa-report.md", "--gate", "GATE 2")
    check("N11: congelado no permite más reintentos del agente",
          code == 1 and "unfreeze humano" in out, out)
    code, out = runcb("status")
    check("N11: status refleja el congelado (exit 1 para CI)", code == 1, out)
    code, out = runcb("unfreeze", "--artefacto", "spec/qa-report.md", "--gate", "GATE 2")
    check("N11: unfreeze sin humano rechazado", code == 1 and "approved-by" in out, out)
    code, out = runcb("unfreeze", "--artefacto", "spec/qa-report.md", "--gate", "GATE 2",
                      "--approved-by", "Karlo")
    check("N11: unfreeze humano descongela (exit 0)", code == 0, out)
    evs = [_j2.loads(l) for l in
           open(os.path.join(tmp, "spec", "audit", "events.jsonl"), encoding="utf-8")]
    cb = [e for e in evs if e["evento"] == "circuit_breaker"]
    check("N11: reintento, congelamiento y descongelamiento auditados con aprobador",
          [e.get("resultado") for e in cb] == ["reintento", "congelado", "descongelado"]
          and cb[-1].get("approved_by") == "Karlo", str(cb))

with tempfile.TemporaryDirectory() as tmp:
    os.makedirs(os.path.join(tmp, "spec"))
    run("audit_log.py", "--spec-dir", os.path.join(tmp, "spec"), "init",
        "--proyecto", "blast", cwd=tmp)
    os.makedirs(os.path.join(tmp, "src", "api"))
    open(os.path.join(tmp, "src", "api", "a.py"), "w").write("x = 1\n")
    for c in (["git", "init", "-q"], ["git", "add", "."],
              ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "v1"]):
        subprocess.run(c, cwd=tmp, capture_output=True)
    def runbr(*args):
        return run("blast_radius_check.py", "--spec-dir", os.path.join(tmp, "spec"),
                   "--root", tmp, *args, cwd=tmp)

    open(os.path.join(tmp, "src", "api", "a.py"), "a").write("y = 2\n")
    code, out = runbr("--allowed", "src/api/**")
    check("N11: diff dentro del alcance pasa (exit 0)",
          code == 0 and "BLAST RADIUS OK" in out, out)
    os.makedirs(os.path.join(tmp, "src", "web"))
    open(os.path.join(tmp, "src", "web", "evil.js"), "w").write("// fuera de alcance\n")
    code, out = runbr("--allowed", "src/api/**")
    check("N11: archivo nuevo fuera de alcance = escape (exit 1, bloquea gate)",
          code == 1 and "FUERA del alcance" in out and "evil.js" in out, out)
    cr = os.path.join(tmp, "spec", "CR-001.md")
    open(cr, "w", encoding="utf-8").write(
        "# CR-001\n## Alcance autorizado\n- src/api/**\n- src/web/\n\n## Otro\n")
    code, out = runbr("--cr", cr)
    check("N11: --cr lee el alcance autorizado del change-request y pasa",
          code == 0, out)
    evs = [_j2.loads(l) for l in
           open(os.path.join(tmp, "spec", "audit", "events.jsonl"), encoding="utf-8")]
    br = [e for e in evs if e["evento"] == "blast_radius"]
    check("N11: escapes y verificaciones quedan en la auditoría",
          [e.get("resultado") for e in br] == ["ok", "fallo", "ok"], str(br))
    code, out = runbr("--allowed", "src/**", "--root", os.path.join(tmp, "noexiste"))
    check("N11: sin repo git = exit 2 con mensaje claro", code == 2, out)

# ── Resumen ──────────────────────────────────────────────────────────────────
print(f"\n{'='*60}\n{PASSES} checks OK, {len(FAILURES)} fallos")
if FAILURES:
    print("Fallos:")
    for f_ in FAILURES:
        print(f"  - {f_}")
    sys.exit(1)
print("SELF-TEST VERDE — el arnés es consistente consigo mismo.")
