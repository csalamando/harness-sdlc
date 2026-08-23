---
artifact: process-definition
owner: business-analyst
status: AS-IS pendiente de firma del Process Owner
---

# PDD — <nombre del proceso> (AS-IS)

> Process Definition Document: captura del proceso **actual** antes de diseñar el TO-BE. Usar cuando la iniciativa automatiza o rediseña un proceso existente (RPA, BPM, modernización). El TO-BE lo produce el arquitecto sobre esta base (architecture.md + BPMN TO-BE en `spec/diagrams/`). **Sin firma del Process Owner (recibo) no hay diseño.** Si la realidad del proceso cambia (nueva excepción descubierta en piloto, cambio de aplicación), este documento se re-emite y re-aprueba.

## 1. Alcance y disparadores

- **Disparador:** <qué inicia el proceso>
- **Fin:** <qué lo termina / resultado de negocio>
- **Frecuencia y volumen:** <ej. 1.800 ejecuciones/mes; picos: ...>
- **Fuera de alcance:** <qué NO cubre este proceso>

## 2. Flujo AS-IS (resumen)

<Enumeración de pasos con tiempos y sistemas. El detalle gráfico vive en `spec/diagrams/<proceso>-asis.bpmn` (vía sdlc-diagrams, BPMN con lanes por ROL-xx). Marcar los cuellos de botella con ←.>

1. ...
2. ...

## 3. Reglas de negocio del proceso

<Referencias a BR-xxx del catálogo de reglas; no duplicar el texto.>

## 4. Catálogo de excepciones

| Tipo | Excepción | Frecuencia | Manejo actual |
|---|---|---|---|
| Conocida | ... | ... | ... |
| Desconocida | — (se descubren en piloto; este PDD se re-emite) | — | — |

## 5. Volúmenes y SLA

- **SLA actual:** <si existe>
- **SLA objetivo del TO-BE:** <medible; alimenta NFRs y el caso de negocio>
- **Ventana de operación:** <horario, días>

## 6. Aplicaciones involucradas

<Sistemas que toca el proceso, con capacidades/limitaciones relevantes — ej. "API solo lectura". Esto alimenta los ADRs del arquitecto.>

## 7. Riesgos y supuestos

- **Riesgos:** <con impacto en la automatización>
- **Supuestos:** <con plan de validación: qué se valida, cuándo, cómo>

## 8. Firma del Process Owner

Aprobado por: <rol/persona responsable del proceso> — fecha: <YYYY-MM-DD>
Recibo: `python3 receipt.py emit --artifact spec/process-definition.md --role business-analyst` + aceptación humana registrada.
