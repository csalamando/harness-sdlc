#!/usr/bin/env python3
"""diagram_catalog.py — routing canónico PLT-01 (D1..D8) y referencia derivada.

El asset assets/catalogo-arquitectura.json es la fuente; la referencia Markdown
es una vista derivada, nunca una segunda matriz editada a mano. Python stdlib.
"""
import argparse
import json
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
DEFAULT_ASSET = SKILL / "assets" / "catalogo-arquitectura.json"
DEFAULT_DOC = SKILL / "references" / "catalogo-arquitectura.md"
EXPECTED = [f"D{i}" for i in range(1, 9)]


def load(path=DEFAULT_ASSET):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate(cat):
    errs = []
    ds = cat.get("diagramas", [])
    ids = [d.get("id") for d in ds]
    if ids != EXPECTED:
        errs.append(f"el catálogo debe contener exactamente {','.join(EXPECTED)} en orden; encontró {ids}")
    for d in ds:
        for field in ("id", "nombre", "pregunta", "fuente", "sintaxis", "vista", "motivo"):
            if not d.get(field):
                errs.append(f"{d.get('id', '?')}: falta '{field}'")
        if d.get("fuente") not in ("IR", "Mermaid"):
            errs.append(f"{d.get('id', '?')}: fuente '{d.get('fuente')}' inválida (IR|Mermaid)")
        if d.get("fuente") == "IR" and not d.get("tipo_ir"):
            errs.append(f"{d.get('id', '?')}: fuente IR sin tipo_ir")
        if d.get("fuente") == "Mermaid" and d.get("tipo_ir") is not None:
            errs.append(f"{d.get('id', '?')}: fuente Mermaid no debe declarar tipo_ir")
        if not isinstance(d.get("iconos_diagrams"), bool):
            errs.append(f"{d.get('id', '?')}: iconos_diagrams debe ser booleano")
    return errs


def route(cat, diagrama, kubernetes=False):
    for d in cat["diagramas"]:
        if d["id"] == diagrama:
            lines = [f"{d['id']} · {d['nombre']}",
                     f"Pregunta: {d['pregunta']}",
                     f"Fuente: {d['fuente']}" + (f" · tipo {d['tipo_ir']}" if d.get("tipo_ir") else ""),
                     f"Sintaxis/archivo: {d['sintaxis']}",
                     f"Vista: {d['vista']}",
                     f"Iconos Diagrams: {'opcionales' if d['iconos_diagrams'] else 'no aportan en esta familia'}",
                     f"Motivo: {d['motivo']}"]
            if kubernetes:
                adapter = (d.get("adaptadores") or {}).get("kubernetes")
                if not adapter:
                    return [f"{diagrama} no tiene adaptador Kubernetes; use su fuente principal"], 1
                lines.append(f"Adaptador Kubernetes: {adapter}")
            return lines, 0
    return [f"Diagrama '{diagrama}' fuera del catálogo D1..D8"], 1


def render(cat):
    out = ["# Catálogo de diagramas de arquitectura — routing del arnés", "",
           "<!-- GENERADO por diagram_catalog.py render; NO editar a mano. -->",
           "<!-- Fuente: ../assets/catalogo-arquitectura.json -->", "",
           f"**Catálogo:** {cat['catalogo']} · **Versión del routing:** {cat['version']}", "",
           f"> {cat['principio']}", "",
           "Esta referencia adapta la propuesta PLT-01 al arnés. Define la fuente y la herramienta; los atributos de contenido de la propuesta original siguen siendo exigibles por el rol dueño y la revisión del DAS.", "",
           "## Decisión por diagrama", "",
           "| # | Diagrama | Pregunta | Fuente principal | Vista / apoyo | Iconos Diagrams |",
           "|---|---|---|---|---|---|"]
    for d in cat["diagramas"]:
        fuente = d["fuente"] + (f" `{d['tipo_ir']}`" if d.get("tipo_ir") else "")
        out.append(f"| {d['id']} | {d['nombre']} | {d['pregunta']} | {fuente} | {d['vista']} | {'Opcionales' if d['iconos_diagrams'] else 'No'} |")
    out += ["", "## Fuentes y sintaxis", ""]
    for d in cat["diagramas"]:
        out += [f"### {d['id']} · {d['nombre']}", "",
                f"- **Archivo/sintaxis:** `{d['sintaxis']}`",
                f"- **Por qué esta ruta:** {d['motivo']}"]
        for name, adapter in (d.get("adaptadores") or {}).items():
            out.append(f"- **Adaptador {name}:** {adapter}")
        out.append("")
    out += ["## Reglas comunes", "",
            "1. **Draw.io permanece retirado.** No es una salida vigente del arnés.",
            "2. **Una fuente por diagrama.** Las imágenes y esta referencia se derivan; no se mantiene una copia equivalente en otro lenguaje.",
            "3. **IR interactivo:** conserva foco, lens, detalle, insights, validación, diff y recibos. Archify es inspiración de interacción, no dependencia.",
            "4. **Mermaid en D4:** conservar `sequenceDiagram` para flujos con notas, error o compensación; en Azure DevOps 8.13.9 usar la valla `::: mermaid`, `graph` en flowcharts y sin comentario inicial.",
            "5. **Diagrams:** sus iconos se sincronizan a `spec/diagrams/icons/` y se incrustan en HTML sin red. El backend de exports estáticos es opcional y está planificado.",
            "6. **KubeDiagrams:** adaptador D3 planificado para entradas offline. El estado de un clúster solo se incorporará con opt-in, minimización y sanitización.",
            "7. **Contenido mínimo:** nombres reales, ficha INI/ambiente/fecha/responsable y tablas complementarias se gobiernan en el DAS; ningún icono sustituye protocolos, clasificación, controles o responsables.",
            "8. **Complementos, no fuentes ocultas:** una tabla complementaria debe derivarse del mismo IR o llevar referencia explícita a su fuente gobernada.", "",
            "## Consulta y anti-drift", "",
            "```bash",
            "python diagram_catalog.py list",
            "python diagram_catalog.py route --diagrama D3 --kubernetes",
            "python diagram_catalog.py check",
            "```", "",
            "Decisión arquitectónica: `docs/decisions/ADR-005-routing-hibrido-diagramas.md`.", ""]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Routing PLT-01 D1..D8 y referencia derivada")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    p_route = sub.add_parser("route")
    p_route.add_argument("--diagrama", required=True, type=str.upper)
    p_route.add_argument("--kubernetes", action="store_true")
    for name in ("render", "check"):
        p = sub.add_parser(name)
        p.add_argument("--asset", default=str(DEFAULT_ASSET))
        p.add_argument("--out", default=str(DEFAULT_DOC))
    args = ap.parse_args(argv)
    cat = load(getattr(args, "asset", DEFAULT_ASSET))
    errs = validate(cat)
    if errs:
        print("CATÁLOGO INVÁLIDO:", file=sys.stderr)
        for e in errs:
            print(f"- {e}", file=sys.stderr)
        return 1
    if args.cmd == "list":
        for d in cat["diagramas"]:
            print(f"{d['id']}  {d['fuente']:<7} {d.get('tipo_ir') or '-':<12} {d['nombre']}")
        return 0
    if args.cmd == "route":
        lines, code = route(cat, args.diagrama, args.kubernetes)
        print("\n".join(lines))
        return code
    text = render(cat)
    out = Path(args.out)
    if args.cmd == "render":
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")
        print(f"OK {out}")
        return 0
    if not out.is_file() or out.read_text(encoding="utf-8") != text:
        print(f"DRIFT: {out} falta o difiere del catálogo; regenerar con diagram_catalog.py render", file=sys.stderr)
        return 1
    print(f"OK sin drift: {out} (8 rutas canónicas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
