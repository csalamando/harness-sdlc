# Secuencia, Gantt y GitFlow vía Mermaid → drawio

Ruta de importación: generar el código Mermaid y abrirlo con `open_drawio_mermaid`. El servidor importa y convierte a shapes editables de draw.io.

## Diagrama de secuencia (UML)

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario
    participant SPA as Web SPA
    participant API as API Backend
    participant DB as Azure SQL
    U->>SPA: Inicia registro (HU-001)
    SPA->>API: POST /usuarios [HTTPS/JSON]
    API->>DB: INSERT usuario [TDS]
    alt email duplicado
        DB-->>API: error UNIQUE
        API-->>SPA: 409 Conflict
        SPA-->>U: mensaje de validación
    else ok
        DB-->>API: 1 row
        API-->>SPA: 201 Created
        SPA-->>U: confirmación
    end
```

Tips:
- `actor` para personas; `participant X as Nombre` para renombrar.
- `-->>` respuesta, `--)` asíncrono; `alt/else`, `loop`, `opt`, `par` para fragmentos.
- Activaciones: `activate API` / `deactivate API` si se quiere mostrar foco de control.
- Referenciar la HU en el primer mensaje o en una `Note over`.

## Gantt (roadmap / plan de sprint)

```mermaid
gantt
    title Roadmap Sprint N (EP-1)
    dateFormat YYYY-MM-DD
    axisFormat %d/%m
    section Fase 1-2
    Historias + Gherkin      :done,  ba,   2026-08-10, 3d
    Arquitectura + contratos :active, arch, after ba, 4d
    section Fase 4
    Backend (TDD)            :back, after arch, 5d
    Frontend (TDD)           :front, after arch, 5d
    section Fase 5-6
    QA E2E + DAST            :qa,   after back, 2d
    Deploy staging/prod      :dep,  after qa, 1d
```

Tips: `done`/`active` para estado, `after <id>` para dependencias, `crit` para ruta crítica, `milestone` para hitos (gates: `GATE 1 :milestone, g1, after arch, 0d`).

## GitFlow / Git graph

```mermaid
gitGraph
    commit id: "init"
    branch develop
    commit id: "setup"
    branch feature/HU-001
    commit id: "test (RED)"
    commit id: "impl (GREEN)"
    checkout develop
    merge feature/HU-001 id: "PR #12"
    branch release/1.0
    commit id: "freeze"
    checkout main
    merge release/1.0 tag: "v1.0.0"
    branch hotfix/1.0.1
    commit id: "fix + test"
    checkout main
    merge hotfix/1.0.1 tag: "v1.0.1"
```

Convención del arnés: ramas `feature/HU-xxx`, `hotfix/x.y.z`; merges a `develop`/`main` etiquetados con el PR; tags de versión en `main`. El diagrama documenta la estrategia de branching en `spec/` la primera vez (DevOps, Fase -1).

## Notas de importación

- Tras `open_drawio_mermaid`, el resultado es 100% editable: ajustar colores/layout en el editor o con `set_page`.
- El código Mermaid fuente se guarda también como comentario/página o en el `.md` de la spec para regeneración futura (Mermaid es más fácil de diff-ear que el XML resultante).
- Si la importación de una sintaxis falla, corregir el Mermaid antes de reintentar; no retocar el XML a mano para estas familias (regenerar es más barato).
