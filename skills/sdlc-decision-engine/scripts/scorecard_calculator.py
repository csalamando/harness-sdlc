#!/usr/bin/env python3
"""scorecard_calculator.py — Calcula la scorecard ponderada de un ADR (Paso 6).

Lee las tablas de criterios (Paso 3) y de puntajes (Paso 6), calcula totales
ponderados y verifica que la opción elegida sea la ganadora o tenga justificación.

Uso: python3 scorecard_calculator.py --adr spec/adr/ADR-001.md
Exit 0 si la scorecard es consistente, 1 si no.
"""
import argparse
import re
import sys


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _section(content, header):
    m = re.search(re.escape(header) + r"\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    return m.group(1) if m else ""


def parse_criteria(content):
    text = _section(content, "## Paso 3: Criterios de Evaluación")
    criteria = []
    for name, weight in re.findall(r"\|\s*([^|]+?)\s*\|\s*(\d+)\s*%\s*\|", text):
        n = name.strip().strip("*")
        if n.lower() in ("criterio", "total", "peso") or n.startswith("-"):
            continue
        criteria.append((n, int(weight)))
    return criteria


def parse_scores(content):
    """Devuelve {opcion: {criterio: puntaje}} a partir de la tabla del Paso 6."""
    text = _section(content, "## Paso 6: Scorecard de Trade-Offs")
    lines = [ln for ln in text.splitlines() if ln.strip().startswith("|")]
    if len(lines) < 2:
        return {}, []
    header = [c.strip() for c in lines[0].strip("|").split("|")]
    options = [h for h in header[2:] if h and "total" not in h.lower()]
    scores = {opt: {} for opt in options}
    for ln in lines[1:]:
        cells = [c.strip().strip("*") for c in ln.strip("|").split("|")]
        if len(cells) < 3 or cells[0].startswith("-") or "criterio" in cells[0].lower():
            continue
        if "total" in cells[0].lower():
            continue
        crit = cells[0]
        for i, opt in enumerate(options):
            idx = i + 2
            if idx < len(cells):
                try:
                    scores[opt][crit] = float(cells[idx])
                except ValueError:
                    pass
    return scores, options


def main():
    p = argparse.ArgumentParser(description="Calcula la scorecard ponderada del ADR")
    p.add_argument("--adr", required=True)
    args = p.parse_args()

    content = _read(args.adr)
    criteria = parse_criteria(content)
    if not criteria:
        print("✗ FAIL: no se encontraron criterios ponderados en el Paso 3")
        sys.exit(1)
    total_weight = sum(w for _, w in criteria)
    if total_weight != 100:
        print(f"✗ FAIL: los pesos suman {total_weight}%, deben sumar 100%")
        sys.exit(1)

    scores, options = parse_scores(content)
    if not options:
        print("✗ FAIL: no se encontró la tabla de puntajes del Paso 6")
        sys.exit(1)

    totals = {}
    print("\nScorecard ponderada (escala 0-10):")
    print(f"{'Criterio':<28}{'Peso':>6}" + "".join(f"{o:>12}" for o in options))
    for crit, weight in criteria:
        row = f"{crit:<28}{str(weight) + '%':>6}"
        for opt in options:
            v = scores.get(opt, {}).get(crit)
            row += f"{v if v is not None else '—':>12}"
        print(row)
    for opt in options:
        tot = sum(scores.get(opt, {}).get(c, 0) * w / 100 for c, w in criteria)
        totals[opt] = round(tot, 2)
    print(f"{'TOTAL':<34}" + "".join(f"{totals[o]:>12}" for o in options))

    winner = max(totals, key=totals.get)
    print(f"\nOpción con mayor puntaje: {winner} ({totals[winner]})")

    m = re.search(r"Opción ganadora\*?\*?:\s*(.+)", content)
    if not m:
        print("✗ FAIL: el ADR no declara la 'Opción ganadora'")
        sys.exit(1)
    chosen = m.group(1).strip()
    print(f"Opción elegida en el ADR: {chosen}")

    # La opción elegida debe corresponder a la de mayor puntaje
    chosen_letter = (re.search(r"([A-Z])", chosen) or [None])[1] if re.search(r"[A-Z]", chosen) else None
    winner_letter = re.search(r"[A-Z]", winner).group(0) if re.search(r"[A-Z]", winner) else winner
    if chosen_letter == winner_letter:
        print("✓ PASS: la opción elegida coincide con la de mayor puntaje")
        sys.exit(0)
    # Si no coincide, exigir justificación explícita
    if re.search(r"justificación si no es la de mayor puntaje\*?\*?:\s*(?!N/?A)(.+)", content, re.IGNORECASE):
        print("✓ PASS (con justificación): la opción elegida no es la de mayor puntaje pero hay justificación explícita")
        sys.exit(0)
    print("✗ FAIL: la opción elegida NO es la de mayor puntaje y no hay justificación explícita")
    sys.exit(1)


if __name__ == "__main__":
    main()
