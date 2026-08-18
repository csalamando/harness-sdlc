# Perfiles de modelo por fase (cost optimization)

No todas las fases necesitan el modelo más potente. Asignar el tier correcto reduce costo y latencia sin degradar calidad. En LiteLLM se implementa con `model_list` por alias; en IDEs, cambiando el modelo del agente al cambiar de fase.

| Fase / Rol | Tier recomendado | Justificación |
|---|---|---|
| Exploración de código (routing orgánico) | económico | Lectura y resumen; volumen alto de tokens |
| Fase 0-1: PO, BA | intermedio | Redacción estructurada con plantillas |
| Fase 2: Architect, Security | potente | Decisiones de alto impacto, threat modeling |
| Fase 2: UX, Data | intermedio | Diseño guiado por plantillas |
| Fase 3: Consolidación de spec | potente | Detectar contradicciones entre artefactos |
| Fase 4: Devs (TDD) | intermedio-alto | Generación guiada por tests y contratos |
| Fase 5: QA (Gherkin→E2E) | intermedio | Transformación mecánica de escenarios |
| Fase 6: DevOps/Cloud | intermedio | IaC y pipelines con plantillas |
| Gates automáticos (gate_checker, receipt, etc.) | ninguno | Son scripts deterministas: cero tokens |
| harness_doctor, detect_stack, reindex | ninguno | Scripts |

## Ejemplo con LiteLLM (config.yaml)

```yaml
model_list:
  - model_name: sdlc-economico
    litellm_params: { model: anthropic/claude-haiku-4-5, api_key: os.environ/ANTHROPIC_API_KEY }
  - model_name: sdlc-intermedio
    litellm_params: { model: anthropic/claude-sonnet-4-5, api_key: os.environ/ANTHROPIC_API_KEY }
  - model_name: sdlc-potente
    litellm_params: { model: anthropic/claude-opus-4-5, api_key: os.environ/ANTHROPIC_API_KEY }
```

El orquestador sugiere el alias al activar cada rol: "activa Architect con `sdlc-potente`; activa QA con `sdlc-intermedio`".

## Regla de escalamiento

Si una fase falla dos veces su checklist con el tier asignado (p. ej. el gate detecta artefactos incoherentes), escalar un tier y reintentar una vez antes de escalar a humano.
