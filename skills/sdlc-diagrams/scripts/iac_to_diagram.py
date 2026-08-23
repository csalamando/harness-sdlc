#!/usr/bin/env python3
"""iac_to_diagram.py — Diagrama de despliegue DERIVADO del IaC (v2.6).

Dirección: infra/ → diagrama. Este diagrama NUNCA se edita a mano:
se regenera desde la fuente y el humano APRUEBA el cambio con recibo
(receipt.py emit --role cloud-engineer) — el diagrama es un mecanismo
de aceptación de cambios de infraestructura, no solo documentación.

Fuentes soportadas (Python stdlib puro, sin ejecutar Terraform):
  --tfstate <terraform.tfstate>   Estado real de Terraform (JSON). Refleja lo
                                  REALMENTE desplegado — la verdad post-apply.
  --arm <template.json>           ARM JSON (Bicep compilado: az bicep build).

Comandos:
  generate  --tfstate f.json|--arm f.json --out spec/diagrams/despliegue.drawio
  check     (mismos args) — exit 1 si el .drawio versionado difiere de lo que
            genera la fuente actual (= drift: alguien cambió el IaC sin pasar
            por la aprobación del diagrama, o el diagrama se editó a mano).

El .drawio generado usa los estilos oficiales de iconos AWS/Azure/GCP
(mxgraph.aws4.* / mscae/azure / img/lib/gcp) y agrupa por resource group /
módulo / VPC como clusters.
"""
import argparse
import json
import os
import re
import sys
import xml.sax.saxutils as sx

# Mapeo tipo de recurso → (estilo drawio, etiqueta corta). Fallback: genérico.
STYLES = {
    # Azure (mscae / azure2)
    "azurerm_kubernetes_cluster": "img/lib/azure2/compute/Kubernetes_Services.svg",
    "azurerm_app_service": "img/lib/azure2/app_services/App_Services.svg",
    "azurerm_linux_function_app": "img/lib/azure2/compute/Function_Apps.svg",
    "azurerm_windows_function_app": "img/lib/azure2/compute/Function_Apps.svg",
    "azurerm_postgresql_flexible_server": "img/lib/azure2/databases/SQL_Database.svg",
    "azurerm_mssql_server": "img/lib/azure2/databases/SQL_Server.svg",
    "azurerm_cosmosdb_account": "img/lib/azure2/databases/Azure_Cosmos_DB.svg",
    "azurerm_storage_account": "img/lib/azure2/storage/Storage_Accounts.svg",
    "azurerm_key_vault": "img/lib/azure2/security/Key_Vaults.svg",
    "azurerm_application_gateway": "img/lib/azure2/networking/Application_Gateways.svg",
    "azurerm_virtual_network": "img/lib/azure2/networking/Virtual_Networks.svg",
    "azurerm_container_registry": "img/lib/azure2/containers/Container_Registries.svg",
    "azurerm_servicebus_namespace": "img/lib/azure2/integration/Service_Bus.svg",
    "azurerm_redis_cache": "img/lib/azure2/databases/Cache_for_Redis.svg",
    "Microsoft.Web/sites": "img/lib/azure2/app_services/App_Services.svg",
    "Microsoft.Sql/servers": "img/lib/azure2/databases/SQL_Server.svg",
    "Microsoft.KeyVault/vaults": "img/lib/azure2/security/Key_Vaults.svg",
    "Microsoft.ContainerService/managedClusters": "img/lib/azure2/compute/Kubernetes_Services.svg",
    "Microsoft.Storage/storageAccounts": "img/lib/azure2/storage/Storage_Accounts.svg",
    "Microsoft.Network/virtualNetworks": "img/lib/azure2/networking/Virtual_Networks.svg",
    # AWS (aws4)
    "aws_lambda_function": "mxgraph.aws4.lambda",
    "aws_instance": "mxgraph.aws4.ec2",
    "aws_db_instance": "mxgraph.aws4.rds",
    "aws_s3_bucket": "mxgraph.aws4.s3",
    "aws_eks_cluster": "mxgraph.aws4.eks",
    "aws_ecs_cluster": "mxgraph.aws4.ecs",
    "aws_vpc": "mxgraph.aws4.vpc",
    "aws_lb": "mxgraph.aws4.elastic_load_balancing",
    "aws_sqs_queue": "mxgraph.aws4.sqs",
    "aws_sns_topic": "mxgraph.aws4.sns",
    # GCP
    "google_compute_instance": "img/lib/gcp/compute/Compute_Engine.svg",
    "google_container_cluster": "img/lib/gcp/compute/Kubernetes_Engine.svg",
    "google_sql_database_instance": "img/lib/gcp/databases/Cloud_SQL.svg",
    "google_storage_bucket": "img/lib/gcp/storage/Cloud_Storage.svg",
}

GENERIC = "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;"


def style_for(rtype):
    icon = STYLES.get(rtype)
    if icon and icon.startswith("mxgraph.aws4"):
        return ("shape=mxgraph.aws4.resourceIcon;resIcon=" + icon +
                ";verticalLabelPosition=bottom;verticalAlign=top;html=1;")
    if icon:
        return ("shape=image;image=" + icon +
                ";verticalLabelPosition=bottom;verticalAlign=top;html=1;")
    return GENERIC


def parse_tfstate(path):
    """→ [(group, rtype, name)]. group = módulo (o 'root')."""
    data = json.load(open(path, encoding="utf-8"))
    nodes = []
    for res in data.get("resources", []):
        rtype, name = res.get("type", "?"), res.get("name", "?")
        mod = res.get("module", "root").replace("module.", "")
        # una entrada por instancia con nombre, o una sola
        insts = res.get("instances") or [{}]
        idx = insts[0].get("index_key") if insts else None
        label = f"{name}" + (f"[{idx}]" if isinstance(idx, (str, int)) else "")
        nodes.append((mod, rtype, label))
    return nodes


def parse_arm(path):
    """→ [(group, rtype, name)]. group = resourceGroup inferido del nombre o 'arm'."""
    data = json.load(open(path, encoding="utf-8"))
    nodes = []
    for res in data.get("resources", []):
        rtype, name = res.get("type", "?"), res.get("name", "?")
        nodes.append(("arm", rtype, name))
    return nodes


def norm_name(s):
    return re.sub(r"[^A-Za-z0-9_\-.]", "_", s)


def build_drawio(nodes, title="Despliegue"):
    """Genera XML drawio: un cluster por grupo, grid de recursos dentro."""
    groups = {}
    for g, t, n in sorted(nodes, key=lambda x: (x[0], x[1], x[2])):
        groups.setdefault(g, []).append((t, n))
    parts = [
        '<mxfile host="app.diagrams.net" agent="iac_to_diagram.py" version="24.0.0">',
        f'  <diagram id="despliegue" name="{sx.escape(title)}">',
        '    <mxGraphModel dx="800" dy="600" grid="1" gridSize="10" guides="1" '
        'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
        'pageWidth="1169" pageHeight="827" math="0" shadow="0">',
        "      <root>",
        '        <mxCell id="0"/>',
        '        <mxCell id="1" parent="0"/>',
    ]
    cid = 2
    x0 = 40
    for gname, items in groups.items():
        cols = max(1, min(4, int(len(items) ** 0.5) + 1))
        rows = (len(items) + cols - 1) // cols
        w, h = cols * 120 + 40, rows * 100 + 70
        gid = f"g{cid}"
        parts.append(
            f'        <mxCell id="{gid}" value="{sx.escape(gname)}" '
            f'style="rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;'
            f'align=left;spacingLeft=8;fontStyle=1;fillColor=#f5f5f5;'
            f'strokeColor=#666666;" vertex="1" parent="1">'
            f'<mxGeometry x="{x0}" y="40" width="{w}" height="{h}" as="geometry"/>'
            f"</mxCell>")
        cid += 1
        for i, (t, n) in enumerate(items):
            cx, cy = 20 + (i % cols) * 120, 40 + (i // cols) * 100
            label = f"{n}\\n{t}"
            parts.append(
                f'        <mxCell id="n{cid}" value="{sx.escape(label)}" '
                f'style="{style_for(t)}" vertex="1" parent="{gid}">'
                f'<mxGeometry x="{cx}" y="{cy}" width="80" height="80" as="geometry"/>'
                f"</mxCell>")
            cid += 1
        x0 += w + 40
    parts += ["      </root>", "    </mxGraphModel>", "  </diagram>", "</mxfile>"]
    return "\n".join(parts) + "\n"


def load_nodes(a):
    if a.tfstate:
        return parse_tfstate(a.tfstate)
    return parse_arm(a.arm)


def normalize(xml):
    """Comparación estable: sin espacios finales ni fin de línea."""
    return "\n".join(l.rstrip() for l in xml.strip().splitlines())


def cmd_generate(a):
    nodes = load_nodes(a)
    if not nodes:
        print("AVISO: la fuente no contiene recursos; no se genera diagrama.")
        return 1
    xml = build_drawio(nodes, a.title)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"OK: {a.out} — {len(nodes)} recursos, "
          f"{len({g for g, _, _ in nodes})} grupos.")
    print("Siguiente paso (gobierno): revisar el contenido y aprobarlo con "
          "`receipt.py emit --artifact " + a.out + " --gate GATE-3 "
          "--role cloud-engineer`. El diagrama sin recibo NO está aceptado.")
    return 0


def cmd_check(a):
    if not os.path.isfile(a.out):
        print(f"DRIFT: no existe {a.out} (diagrama nunca generado).", file=sys.stderr)
        return 1
    expected = normalize(build_drawio(load_nodes(a), a.title))
    current = normalize(open(a.out, encoding="utf-8").read())
    if expected == current:
        print(f"OK: {a.out} está sincronizado con la fuente IaC.")
        return 0
    print(f"DRIFT: {a.out} difiere del IaC actual.", file=sys.stderr)
    print("Regenerar con `generate`, revisar el diff en Git y aprobar con recibo. "
          "Si el diagrama se editó a mano, esas ediciones se perderán: "
          "este artefacto es derivado, la fuente de verdad es el IaC.",
          file=sys.stderr)
    return 1


def main():
    p = argparse.ArgumentParser(description="Diagrama de despliegue derivado del IaC (tfstate/ARM → .drawio).")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in (("generate", cmd_generate), ("check", cmd_check)):
        sp = sub.add_parser(name)
        src = sp.add_mutually_exclusive_group(required=True)
        src.add_argument("--tfstate", help="terraform.tfstate (JSON)")
        src.add_argument("--arm", help="ARM JSON (Bicep compilado)")
        sp.add_argument("--out", default="spec/diagrams/despliegue.drawio")
        sp.add_argument("--title", default="Despliegue")
        sp.set_defaults(f=fn)
    a = p.parse_args()
    return a.f(a)


if __name__ == "__main__":
    sys.exit(main())
