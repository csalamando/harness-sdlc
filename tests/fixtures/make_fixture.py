#!/usr/bin/env python3
"""Genera tests/fixtures/proyecto-demo — proyecto mínimo gobernado por el arnés.

Lo usa el self-test para probar `harness_graph.py --proyecto` (ADR-002):
2 sprints cerrados, recibos vigentes + 1 invalidado (GATE 2), 1 release,
memorias learning y trazabilidad HU -> test -> codigo.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "proyecto-demo")


def w(rel, content):
    p = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8", newline="\n").write(content)


def receipt(artefacto, gate, estado, emitido, rol="sdlc-orchestrator"):
    return json.dumps({"artefacto": os.path.join(ROOT, "spec", artefacto),
                       "sha256": "0" * 64, "gate": gate, "tipo": "",
                       "rol": rol, "emitido": emitido, "estado": estado},
                      indent=2, ensure_ascii=False)


# ── spec/ ──
w("spec/user-stories.md", """# Historias de usuario

## HU-001 Login
Given un usuario registrado When ingresa credenciales validas Then accede.

## HU-002 Checkout
Given un carrito con items When paga Then recibe confirmacion.

## HU-003 Catalogo
Given visitante When navega Then ve productos.

## HU-004 Perfil
Given usuario logueado When edita perfil Then se guarda.
""")
w("spec/vision.md", "# Vision\nProducto demo para el fixture del self-test.\n")
w("spec/architecture.md", "# Arquitectura\nContratos y ADRs del fixture.\n")
w("spec/test-plan.md", "# Test plan\nE2E del fixture.\n")

# ── recibos ──
w("spec/receipts/vision.md.receipt.json",
  receipt("vision.md", "GATE 0", "vigente", "2026-08-01T10:00:00"))
w("spec/receipts/architecture.md.receipt.json",
  receipt("architecture.md", "GATE 1", "vigente", "2026-08-05T11:00:00"))
w("spec/receipts/test-plan.md.receipt.json",
  receipt("test-plan.md", "GATE 2", "invalidado", "2026-08-15T09:30:00"))
w("spec/receipts/release.md.receipt.json",
  receipt("release.md", "GATE 3", "vigente", "2026-08-18T16:00:00"))
w("spec/release.md", "# Release v0.9.0\n")

# ── sprint reviews (snapshots canónicos, formato sprint_review.py) ──
def review(n, artefactos, gates_1er, rehechos, lead_rows):
    lead = "\n".join(f"| {g} | {d0} | {d1} | {k} | {span} |" for g, d0, d1, k, span in lead_rows)
    return f"""# Sprint Review — Sprint {n:02d}

Generado: 2026-08-{10 + n} | Periodo (recibos): 2026-08-01 → 2026-08-{10 + n}

<!-- KPIs para tendencia (no borrar, los lee sprint_review.py) -->
<!-- Artefactos aprobados: {artefactos} -->
<!-- Gates al primer intento: {gates_1er}% -->
<!-- Roles en freestyle: 0 -->
<!-- Tokens totales: 1,000 -->

## 1. Resumen ejecutivo

- Artefactos aprobados (recibos vigentes): **{artefactos}**
- Gates al primer intento: **{gates_1er}%**
- Trabajo rehecho (recibos invalidados/revocados): **{rehechos}**

## 4. Tiempos del pipeline (lead time por gate)

| Gate | Primer recibo | Ultimo recibo | Recibos | Span |
|---|---|---|---|---|
{lead}
"""

w("spec/reports/sprint-review-01.md", review(1, 2, 100, 0, [
    ("GATE 0", "2026-08-01", "2026-08-02", 1, "1 days, 0:00:00"),
    ("GATE 1", "2026-08-03", "2026-08-05", 1, "2 days, 0:00:00"),
]))
w("spec/reports/sprint-review-02.md", review(2, 3, 75, 1, [
    ("GATE 0", "2026-08-01", "2026-08-02", 1, "1 days, 0:00:00"),
    ("GATE 1", "2026-08-03", "2026-08-05", 1, "2 days, 0:00:00"),
    ("GATE 2", "2026-08-12", "2026-08-15", 1, "3 days, 12:00:00"),
]))

# ── memorias learning ──
w("spec/memory/entries/2026-08-10-mocks-desde-contrato.md", """---
type: learning
---
# Los mocks generados desde el contrato OpenAPI reducen el retrabajo

Aprendido en el sprint 1 tras las primeras integraciones.
""")

# ── ADRs y tech radar (v2.13) ──
w("spec/adr/ADR-001-postgresql-excepcion.md", """# ADR-001: PostgreSQL como excepción al radar

## Metadata
- **Status**: Adopted
- **Risk Tier**: 1
- **Decision Owner**: Arquitecto del fixture
- **Date Proposed**: 2026-08-06
- **Date Adopted**: 2026-08-08
""")
w("spec/adr/ADR-002-frontend-spa.md", """# ADR-002: Frontend SPA

## Metadata
- **Status**: Proposed
- **Risk Tier**: 3
- **Decision Owner**: Arquitecto del fixture
""")
w("spec/tech-radar.yaml", """version: "2026-Q3"
quadrants:
  ADOPT:
    - technology: "TypeScript"
      category: "Lenguaje"
    - technology: "Python"
      category: "Lenguaje"
  TRIAL:
    - technology: "Vitest"
      category: "Testing"
  ASSESS: []
  HOLD: []
""")

# ── trazabilidad HU -> test -> codigo ──
w("tests/test_hu.py", '''"""Tests del fixture: HU-001, HU-002, HU-003."""
def test_login():  # HU-001
    assert True
def test_checkout():  # HU-002
    assert True
def test_catalogo():  # HU-003
    assert True
''')
w("src/app.py", '''"""Codigo del fixture: HU-001, HU-002, HU-003."""
def login(): ...      # HU-001
def checkout(): ...   # HU-002
def catalogo(): ...   # HU-003
''')

print(f"Fixture generado: {ROOT}")
