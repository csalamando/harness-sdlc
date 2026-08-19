#!/usr/bin/env python3
"""arch_signoff.py — Genera el Recibo de Arquitectura (firma del Arquitecto de
Software) con SHA-256 del ADR y de los artefactos de diseño.

Uso: python3 arch_signoff.py --adr spec/adr/ADR-001.md --architect "Nombre" \
     [--role "Software Architect"] [--spec-dir spec] [--receipts-dir spec/receipts]

El recibo se invalida automáticamente si cambia cualquier artefacto firmado:
usar `receipt.py verify` para comprobarlo en los gates posteriores.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

DESIGN_FILES = ["architecture.md", "openapi.yaml", "api-contract.yaml",
                "data-model.md", "detailed-design.md"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_artifacts(spec_dir):
    artifacts = {}
    for name in DESIGN_FILES:
        p = os.path.join(spec_dir, name)
        if os.path.exists(p):
            artifacts[name] = sha256(p)
    diagrams = os.path.join(spec_dir, "diagrams")
    if os.path.isdir(diagrams):
        for d in sorted(Path(diagrams).glob("*.drawio")):
            artifacts[f"diagrams/{d.name}"] = sha256(d)
    return artifacts


def main():
    p = argparse.ArgumentParser(description="Firma Arquitectónica (Recibo de Arquitectura)")
    p.add_argument("--adr", required=True)
    p.add_argument("--architect", required=True)
    p.add_argument("--role", default="Software Architect")
    p.add_argument("--spec-dir", default="spec")
    p.add_argument("--receipts-dir", default="spec/receipts")
    args = p.parse_args()

    if not os.path.exists(args.adr):
        print(f"ERROR: ADR no encontrado: {args.adr}")
        sys.exit(1)

    m = re.search(r"ADR-(\d+)", os.path.basename(args.adr))
    if not m:
        print("ERROR: no se pudo extraer el ID del ADR del nombre de archivo")
        sys.exit(1)
    adr_id = m.group(1)

    adr_hash = sha256(args.adr)
    artifacts = collect_artifacts(args.spec_dir)
    composite = hashlib.sha256(
        (adr_hash + "".join(sorted(artifacts.values()))).encode()
    ).hexdigest()

    receipt = {
        "receipt_id": f"ARCH-{adr_id}",
        "type": "architectural-signoff",
        "adr_id": f"ADR-{adr_id}",
        "adr_path": args.adr,
        "adr_hash": adr_hash,
        "architect": args.architect,
        "role": args.role,
        "signed": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "artifacts": artifacts,
        "composite_hash": composite,
        "status": "ACTIVE",
    }

    os.makedirs(args.receipts_dir, exist_ok=True)
    out = os.path.join(args.receipts_dir, f"ARCH-{adr_id}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2, ensure_ascii=False)

    print(f"✓ Recibo de Arquitectura: {out}")
    print(f"  Arquitecto: {args.architect} ({args.role})")
    print(f"  ADR: ADR-{adr_id}  sha256: {adr_hash[:16]}...")
    print(f"  Hash compuesto: {composite[:16]}...  ({len(artifacts)} artefactos)")


if __name__ == "__main__":
    main()
