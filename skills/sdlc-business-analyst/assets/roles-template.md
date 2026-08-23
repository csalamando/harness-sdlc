---
artifact: roles
owner: business-analyst
status: borrador
---

# Catálogo de Roles — <nombre del producto>

> Regla del arnés: un rol no es una etiqueta, es **nombre + acciones que habilita + contexto/condiciones + reglas que lo restringen**. Toda HU, lane BPMN y caso E2E debe citar un ROL-xx de este catálogo. Cambiar este artefacto revoca los recibos de lo que dependa de él (HU, UX flows, test-plan, RBAC del diseño).

## ROL-01 — <nombre del rol, ej. Cajero de sucursal>

- **Tipo:** humano | sistema | externo
- **Reporta a / escala a:** ROL-xx (o "—")
- **Acciones que habilita:** <qué puede ejecutar en el sistema, en lenguaje de negocio>
- **Contexto / condiciones:** <bajo qué condiciones puede o no ejecutar cada acción — montos, turno, estado del sistema, canal>
- **Reglas que lo restringen:** BR-xxx, SEC-xxx (referencias, no texto duplicado)
- **Sistemas que opera:** <apps/pantallas, con nivel de acceso: lectura/escritura>
- **Volumen / frecuencia esperada:** <si aplica; alimenta NFRs>

## ROL-02 — <siguiente rol>

- **Tipo:** ...
- **Reporta a / escala a:** ...
- **Acciones que habilita:** ...
- **Contexto / condiciones:** ...
- **Reglas que lo restringen:** ...
- **Sistemas que opera:** ...
- **Volumen / frecuencia esperada:** ...

## Conflictos de interés entre roles (si los hay)

<Declarar aquí los conflictos conocidos — ej. un rol quiere rapidez y otro control — y cómo se resolvió la prioridad. Esta decisión la firma el PO en GATE 0/1.>
