#!/usr/bin/env python3
"""manifest_check.py — deriva el manifiesto del arnés desde las skills y detecta drift.

Inspirado en "Everything is a plugin" de DeepSeek Harness (ver README §10): la fuente
de verdad de cada skill vive en el frontmatter de su propio SKILL.md (campos
harness-*); el manifiesto es un artefacto DERIVADO, nunca editado a mano.

Uso:
  python3 manifest_check.py --write    # regenera assets/harness-manifest.yaml
  python3 manifest_check.py --check    # exit 1 si hay drift o inconsistencias
  python3 manifest_check.py --summary  # imprime el resumen legible

Validaciones cruzadas (exit 1 en --check si fallan):
  - drift: el manifiesto versionado difiere de lo que declaran las skills hoy
  - gates declarados por skills existen en gate_checker.py (CHECKS)
  - artefactos "owns" de cada skill existen en la matriz de autoridad
  - scripts declarados existen en disco; scripts en disco están declarados
"""
import argparse, os, re, sys

SKILLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
ORCH = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(ORCH, "..", "assets", "harness-manifest.yaml")
MATRIX = os.path.join(ORCH, "..", "assets", "authority-matrix.yaml")
GATE_CHECKER = os.path.join(ORCH, "gate_checker.py")

FM_RE = re.compile(r"^harness-([a-z-]+):\s*\"?([^\"\n]*)\"?\s*$", re.MULTILINE)


def parse_list(v):
    return [x.strip() for x in v.split(",") if x.strip()]


def harness_version(skills_dir=None):
    """Versión del arnés, declarada en el frontmatter del orquestador (fuente única)."""
    d = skills_dir or SKILLS_DIR
    md = os.path.join(d, "sdlc-orchestrator", "SKILL.md")
    if not os.path.isfile(md):
        return None
    text = open(md, encoding="utf-8").read()
    fm = dict(FM_RE.findall(text.split("---", 2)[1] if "---" in text else ""))
    return fm.get("version") or None


def derive(skills_dir):
    """Escanea skills/*/SKILL.md y deriva el manifiesto como lista de dicts."""
    skills = []
    for name in sorted(os.listdir(skills_dir)):
        d = os.path.join(skills_dir, name)
        md = os.path.join(d, "SKILL.md")
        if not os.path.isdir(d) or not os.path.isfile(md) or not name.startswith("sdlc-"):
            continue
        text = open(md, encoding="utf-8").read()
        fm = dict(FM_RE.findall(text.split("---", 2)[1] if "---" in text else ""))
        sdir = os.path.join(d, "scripts")
        scripts = sorted(f for f in os.listdir(sdir) if f.endswith(".py")) if os.path.isdir(sdir) else []
        skills.append({
            "name": name,
            "role": fm.get("role", name.replace("sdlc-", "")),
            "phases": parse_list(fm.get("phases", "")),
            "owns": parse_list(fm.get("owns", "")),
            "gates": parse_list(fm.get("gates", "")),
            "conditional": fm.get("conditional", ""),
            "optional_deps": parse_list(fm.get("optional-deps", "")),
            "scripts": scripts,
        })
    return skills


def render(skills, skills_dir=None):
    """Serializa el manifiesto a YAML (subconjunto plano, stdlib puro)."""
    out = ["# Manifiesto del arnés SDLC — GENERADO por manifest_check.py --write",
           "# NO editar a mano: la fuente de verdad es el frontmatter harness-* de cada SKILL.md,",
           "# y la lista de scripts se deriva del disco. Drift = fallo en self_test y en CI.",
           "manifest-version: 1", f'harness-version: "{harness_version(skills_dir) or "sin-declarar"}"',
           f"skill-count: {len(skills)}", "skills:"]
    def lst(xs):
        return "[" + ", ".join(xs) + "]"
    for s in skills:
        out.append(f"  - name: {s['name']}")
        out.append(f"    role: {s['role']}")
        out.append(f"    phases: {lst(s['phases'])}")
        out.append(f"    owns: {lst(s['owns'])}")
        out.append(f"    gates: {lst(s['gates'])}")
        if s["conditional"]:
            out.append(f"    conditional: \"{s['conditional']}\"")
        out.append(f"    optional-deps: {lst(s['optional_deps'])}")
        out.append(f"    scripts: {lst(s['scripts'])}")
    return "\n".join(out) + "\n"


def gate_checker_types():
    """Tipos de gate soportados, extraídos del fuente de gate_checker.py."""
    src = open(GATE_CHECKER, encoding="utf-8").read()
    m = re.search(r"CHECKS\s*=\s*\{(.*?)\n\}", src, re.DOTALL)
    return set(re.findall(r'^\s*"([a-z0-9-]+)":', m.group(1), re.MULTILINE)) if m else set()


def matrix_paths():
    text = open(MATRIX, encoding="utf-8").read()
    return [m.group(1).strip() for m in re.finditer(r"-\s*path:\s*(\S+)\s+owner:", text)]


def cross_validate(skills):
    """Devuelve lista de inconsistencias entre skills, gates y matriz."""
    problems = []
    known_gates = gate_checker_types()
    paths = matrix_paths()

    def in_matrix(art):
        art = art.rstrip("/")
        return any(art == p.rstrip("/") or art.startswith(p.rstrip("/") + "/") for p in paths)

    for s in skills:
        for g in s["gates"]:
            if g not in known_gates:
                problems.append(f"{s['name']}: gate '{g}' declarado pero gate_checker.py no lo soporta")
        for art in s["owns"]:
            if not in_matrix(art):
                problems.append(f"{s['name']}: posee '{art}' pero no está en la matriz de autoridad")
        for sc in s["scripts"]:
            p = os.path.join(SKILLS_DIR, s["name"], "scripts", sc)
            if not os.path.isfile(p):
                problems.append(f"{s['name']}: script '{sc}' declarado pero no existe en disco")
    # vía contraria: artefacto en la matriz sin skill que lo declare (excepto gobierno y derivados)
    declared = {a for s in skills for a in s["owns"]}
    for p in paths:
        base = p.rstrip("/")
        if not any(base == d.rstrip("/") or base.startswith(d.rstrip("/") + "/") for d in declared):
            problems.append(f"matriz declara '{p}' pero ninguna skill lo declara en harness-owns")
    return problems


def summary(skills):
    print(f"Manifiesto del arnés: {len(skills)} skills\n")
    for s in skills:
        cond = f" · condicional: {s['conditional']}" if s["conditional"] else ""
        deps = f" · deps: {', '.join(s['optional_deps'])}" if s["optional_deps"] else ""
        print(f"  {s['name']:<28} rol={s['role']:<20} fases={','.join(s['phases']) or '-':<12} "
              f"gates={len(s['gates'])} owns={len(s['owns'])} scripts={len(s['scripts'])}{cond}{deps}")


PHASE_ORDER = ["-1", "0", "1", "2", "3", "4", "5", "6", "7", "transversal"]


def routing(skills, sin_ui=False, sin_datos=False, sin_procesos=False):
    """Routing orgánico derivado del manifiesto (v2.10): fases -> roles activos.

    Las capacidades condicionales se EXCLUYEN cuando la condición no aplica:
      --sin-ui        -> spec/ux/ del ux-designer (prototipo gobernado)
      --sin-datos     -> sdlc-data-engineer completa (skill condicional)
      --sin-procesos  -> process-definition.md (PDD) del business-analyst
    """
    excluir_skill = lambda s: sin_datos and s["name"] == "sdlc-data-engineer"
    def caps_excluidas(s):
        ex = []
        c = s["conditional"]
        if sin_ui and "UI" in c:
            ex.append(c)
        if sin_procesos and "process-definition" in c:
            ex.append("process-definition.md (PDD)")
        return ex
    print("Routing derivado del manifiesto"
          + (" [sin UI]" if sin_ui else "") + (" [sin datos]" if sin_datos else "")
          + (" [sin procesos]" if sin_procesos else "") + ":\n")
    for fase in PHASE_ORDER:
        grupo = [s for s in skills if fase in s["phases"] and not excluir_skill(s)]
        if not grupo:
            continue
        print(f"FASE {fase}")
        for s in grupo:
            extra = f" — gates: {', '.join(s['gates'])}" if s["gates"] else ""
            cond = f" — condicional: {s['conditional']}" if s["conditional"] and fase == "2" or \
                   (s["conditional"] and s["name"] == "sdlc-enterprise-architect") else ""
            print(f"  {s['role']}{extra}{cond}")
            for cap in caps_excluidas(s):
                print(f"    ✗ EXCLUIDA: {cap} (la condición no aplica a esta iniciativa)")
    if sin_datos:
        print("\n  ✗ sdlc-data-engineer excluida por completo (sin datos significativos)")


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--summary", action="store_true")
    g.add_argument("--routing", action="store_true",
                   help="routing por fases derivado del manifiesto (v2.10)")
    ap.add_argument("--sin-ui", action="store_true", help="la iniciativa no tiene UI")
    ap.add_argument("--sin-datos", action="store_true", help="sin datos significativos")
    ap.add_argument("--sin-procesos", action="store_true", help="no automatiza/rediseña procesos")
    ap.add_argument("--skills-dir", default=SKILLS_DIR)
    a = ap.parse_args()

    skills = derive(os.path.abspath(a.skills_dir))

    if a.summary:
        summary(skills)
        sys.exit(0)

    if a.routing:
        routing(skills, a.sin_ui, a.sin_datos, a.sin_procesos)
        sys.exit(0)

    problems = cross_validate(skills)
    text = render(skills, os.path.abspath(a.skills_dir))
    manifest_path = os.path.normpath(MANIFEST)

    if a.write:
        os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
        open(manifest_path, "w", encoding="utf-8", newline="\n").write(text)
        print(f"Manifiesto regenerado: {manifest_path} ({len(skills)} skills)")
        if problems:
            print("\nINCONSISTENCIAS (el manifiesto se escribió, pero hay que resolver):")
            for p in problems: print(f"  - {p}")
            sys.exit(1)
        sys.exit(0)

    # --check
    drift = not os.path.isfile(manifest_path) or open(manifest_path, encoding="utf-8").read() != text
    if drift:
        problems.insert(0, "DRIFT: el manifiesto versionado no coincide con las skills "
                           "(regenerar: manifest_check.py --write)")
    if problems:
        print("MANIFEST CHECK — FALLO:")
        for p in problems: print(f"  - {p}")
        sys.exit(1)
    print(f"MANIFEST CHECK OK: {len(skills)} skills consistentes, sin drift, "
          f"gates y matriz cruzados en verde.")


if __name__ == "__main__":
    main()
