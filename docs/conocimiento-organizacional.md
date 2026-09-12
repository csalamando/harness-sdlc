# Conocimiento organizacional en el arnés: políticas, lineamientos y patrones

> Cómo una organización inyecta **su** conocimiento en el arnés — políticas de cumplimiento obligatorio, lineamientos técnicos, paved roads y patrones probados — de forma que cada proyecto los herede, los gates los hagan cumplir y los aprendizajes regresen a la organización.

El arnés no solo gobierna *cómo* se construye; también es el canal por el que **el conocimiento de la organización llega a cada agente en cada proyecto**. Hay cuatro mecanismos, cada uno con su dueño y su punto de enforcement:

| Mecanismo | Qué contiene | Dónde vive | Quién lo gobierna | Dónde se hace cumplir |
|---|---|---|---|---|
| **Políticas org** (`sdlc-memory`, tipo `policy`) | Lineamientos obligatorios o recomendados: seguridad, cumplimiento, estándares corporativos | `~/.sdlcmem/org/` (repo Git corporativo) | El humano/área que emite la política | `policy check` **bloquea GATE 1** |
| **Tech Radar + Principios + Decision Packages** (`sdlc-enterprise-architect`) | Tecnologías ADOPT/TRIAL/ASSESS/HOLD, principios arquitectónicos, decisiones pre-aprobadas (paved roads) | Assets del skill → `spec/tech-radar.yaml`, `spec/architectural-principles.yaml` del proyecto | Enterprise Architect | `gate_checker.py --check tech-radar` en GATE 1; tecnología en HOLD bloquea |
| **Matriz de autoridad + roster + glosario** | Quién firma qué artefacto, quién ejerce cada rol, vocabulario canónico | `spec/authority-matrix.yaml`, `spec/team-roster.yaml`, `spec/glossary.md` | Orquestador (scaffold) + cada rol dueño | `authority_check.py` en cada recibo |
| **Reglas de arquitectura** (`arch_lint`) | La arquitectura aprobada como política binaria sobre el código | `spec/architecture-rules.yaml` | Software Architect | CI: el código que diverge de lo firmado detiene el pipeline |

---

## 1. Políticas organizacionales con enforcement real

Las políticas viven en la **memoria scope org** — un directorio Git (`~/.sdlcmem/org`) que la organización mantiene como repo corporativo y cada usuario clona localmente. Solo ahí pueden crearse memorias de tipo `policy` (el scope org rechaza además contenido con patrones de secretos).

```bash
# La organización publica un lineamiento (una sola vez, en el repo org)
python3 mem.py save --scope org --type policy \
    --title "APIs públicas exigen OAuth2+PKCE" \
    --what "Toda API expuesta fuera de la red interna usa OAuth2 con PKCE" \
    --why  "Estándar corporativo de seguridad (ISO 27001, control A.9)" \
    --enforcement mandatory        # o recommended
```

Cada proyecto, **antes de GATE 1**, debe resolver cada política `mandatory` de una de dos formas:

```bash
python3 mem.py policy list            # qué políticas aplican
python3 mem.py policy check           # VIOLATION bloquea el gate (exit 1)

# Camino A — cumplimiento attestado:
python3 mem.py policy attest POL-xxxx --status compliant --by software-architect

# Camino B — desviación con aprobación humana y expiración:
python3 mem.py deviation request --policy POL-xxxx --title "API batch m2m" \
    --justification "Canal interno m2m sin interacción humana"
#   → un humano designado aprueba o rechaza:
python3 mem.py deviation approve DEV-xxxx --approver "J. Pérez" --expires 2026-12-31
python3 mem.py policy check           # ahora WAIVED hasta la expiración
```

**Reglas de gobierno:**

- Solo humanos designados aprueban desviaciones (`--approver` obligatorio) — el agente no se auto-exime.
- Toda desviación **expira**; al vencer, la política vuelve a bloquear. `approved`/`rejected` es irreversible: si cambian las condiciones, se solicita una nueva.
- Una desviación rechazada obliga a cumplir la política. No hay tercera vía.
- Dos memorias que se contradicen (`conflicts_with`) bloquean GATE 1 hasta resolución humana.

## 2. Tech Radar, Principios y Decision Packages (paved roads)

El **Enterprise Architect** mantiene tres activos que bajan a cada proyecto en el scaffold (`init_project.py`) o al activarse el rol:

1. **Tech Radar** (`spec/tech-radar.yaml`) — cuadrantes con efecto directo en GATE 1:
   - `ADOPT` → paved road: usar sin fricción.
   - `TRIAL` / `ASSESS` → permitido con justificación registrada.
   - `HOLD` → **bloquea el gate** salvo ADR de excepción aprobado.
2. **Principios Arquitectónicos** (`spec/architectural-principles.yaml`) — declaraciones verificables ("toda persistencia pasa por la API de datos", "nada de PII en logs"). Una violación de principio escala al Enterprise Architect.
3. **Decision Packages** — decisiones arquitectónicas recurrentes ya resueltas (8 pasos + scorecard) y pre-aprobadas: si tu caso encaja en un package, lo adoptas sin repetir el proceso completo.

El Enterprise Architect **gobierna por excepción**: solo interviene en decisiones Risk Tier 1, violaciones de principios o tecnologías en HOLD. El resto lo resuelven los equipos con el proceso normal.

## 3. Conocimiento que fluye en ambas direcciones

El sistema está diseñado para que la organización no solo *imponga* conocimiento sino que *lo coseche*:

```
proyecto aprende (spec/memory)  ──promote──▶  usuario (~/.sdlcmem/user)
usuario generaliza              ──promote──▶  organización (~/.sdlcmem/org)
organización publica políticas y radar  ──▶  todos los proyectos (GATE 1 los exige)
```

- **`promote MEM-xxx --to user|org`** copia la memoria con `derived_from`: el original queda intacto y trazable.
- Un patrón probado en dos o tres proyectos se promueve a org; si demuestra ser un lineamiento, se convierte en `policy` o entra al Tech Radar como `ADOPT`.
- Los **sprint reviews** (Fase 8, gate bloqueante) son la cosecha sistemática: un sprint sin aprendizaje registrado no pasa, y esos aprendizajes son la materia prima de las promociones.
- La **búsqueda federada** (`mem.py search`, servidor MCP incluido) consulta los tres scopes y etiqueta el origen: ORG > USER > PROJECT — lo general de la organización siempre gana.

## 4. Receta de adopción para una organización

1. **Crear el repo de memoria org**: un repositorio Git corporativo clonado como `~/.sdlcmem/org` en cada máquina (o configurar `SDLCMEM_ORG_ROOT` apuntando a una ruta compartida). Tras cada pull, `mem.py reindex`.
2. **Sembrar las políticas**: convertir los lineamientos existentes (seguridad, datos, cumplimiento) en memorias `policy` con `enforcement mandatory|recommended`. Empezar con pocas y mandatory solo las innegociables.
3. **Publicar el Tech Radar y los Principios**: partir de los assets del skill `sdlc-enterprise-architect`, adaptarlos a la organización y distribuirlos como plantilla de scaffold.
4. **Nombrar aprobadores**: quién firma gates humanos, quién aprueba desviaciones, quién es Enterprise Architect — queda en `spec/team-roster.yaml` y la matriz de autoridad de cada proyecto.
5. **Operar el ciclo**: cada proyecto attesta o desvía en GATE 1; cada sprint cosecha aprendizajes en Fase 8; periódicamente la organización promueve patrones y actualiza políticas/radar.
6. **Auditar**: la página de Auditoría del portal del proyecto muestra la cadena de hash íntegra, recibos, revocaciones y aprobadores humanos — evidencia lista para compliance.

> **Regla de oro:** si un lineamiento no está en la memoria org, el radar o los principios, no existe para el arnés — y si está, ningún agente puede ignorarlo sin que un humano lo apruebe explícitamente.
