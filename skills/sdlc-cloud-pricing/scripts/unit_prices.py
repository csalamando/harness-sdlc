"""Precios unitarios de referencia (lista pública on-demand, USD, region base us-east-1 / East US).

SON UN PUNTO DE PARTIDA para estimación temprana (Fase 0). Verificar contra las
calculadoras oficiales antes de presentar a negocio:
  - AWS:   https://calculator.aws/
  - Azure: https://azure.microsoft.com/pricing/calculator/
Cualquier precio puede sobreescribirse vía `overrides:` en el YAML de supuestos.
Última revisión de esta tabla: 2026-08 (aproximada, nivel de magnitud).
"""

UNIT_PRICES = {
    "aws": {
        # USD/hora por sizing (cómputo genérico tipo EC2/ECS on-demand)
        "compute": {"small": 0.012, "medium": 0.048, "large": 0.096, "xlarge": 0.192},
        # USD/hora por sizing (base de datos gestionada tipo RDS; ha duplica)
        "database": {"small": 0.020, "medium": 0.080, "large": 0.160, "xlarge": 0.320},
        "storage_gb_month": 0.023,   # object storage estándar
        "egress_gb": 0.09,           # transferencia saliente
        "requests_million": 0.20,    # balanceo/API gestionado, referencia
    },
    "azure": {
        "compute": {"small": 0.013, "medium": 0.052, "large": 0.104, "xlarge": 0.208},
        "database": {"small": 0.022, "medium": 0.088, "large": 0.176, "xlarge": 0.352},
        "storage_gb_month": 0.020,
        "egress_gb": 0.087,
        "requests_million": 0.22,
    },
}

CLOUD_NAMES = {"aws": "AWS", "azure": "Azure"}
