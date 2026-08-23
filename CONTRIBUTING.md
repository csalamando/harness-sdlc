# Contribuir al Arnés SDLC

Gracias por querer mejorar el arnés. Esta guía es **para quienes modifican el arnés en sí** (skills, scripts, gates, plantillas, docs del repo). Si solo quieres **usarlo** en tu proyecto, no necesitas esto: instala las skills desde el ZIP de la [release](https://github.com/csalamando/harness-sdlc/releases) más reciente y sigue la [Guía de uso](docs/guia-de-uso-arnes-sdlc.md) §2.

## Principio rector

El arnés predica gobierno con evidencia — y se predica con el ejemplo: **ningún cambio entra si la documentación promete algo que los scripts no hacen**. La deuda de v2.7/v2.8 (features documentadas sin implementar, corregidas en v2.8.1) es el ejemplo de lo que este proceso evita.

## Checklist antes de abrir PR

1. **Self-test en verde** (obligatorio):

   ```bash
   python tests/self_test.py   # exit 0 = 71+ checks OK; exit 1 = lista los fallos
   ```

   Valida que los 23 scripts compilan, que las 13 plantillas pasan su propio `gate_checker.py`, que el grafo de impacto (`spec_diff_impact.py`) conoce todos los artefactos gobernados, que la matriz de autoridad no tiene huecos y que la validación cruzada de roles/pantallas funciona desde cualquier cwd.

2. **Si tu cambio añade un artefacto gobernado, un gate o una revocación de recibos**, añade el check correspondiente en `tests/self_test.py` **en el mismo commit**. Una feature sin check de consistencia es una deuda de v2.8.1 esperando a repetirse.

3. **CHANGELOG.md** con su entrada siguiendo la regla SemVer del repo:
   - **MAJOR** (x.0.0): cambios incompatibles en gates, recibos o formato de spec.
   - **MINOR** (2.x.0): skills nuevas, gates nuevos, features retrocompatibles.
   - **PATCH** (2.x.y): correcciones en scripts, plantillas o documentación.

4. **Docs al día**: si el cambio es visible para el usuario, actualiza `README.md` y/o la guía (`docs/guia-de-uso-arnes-sdlc.md`).

## Estructura del repo

| Ruta | Qué es | ¿Entra al ZIP de release? |
|---|---|---|
| `skills/` | Las 21 skills (SKILL.md + assets/references/scripts) | ✅ Sí — es el paquete |
| `docs/` | Guía de uso, notas de release | ❌ No |
| `tests/` | Herramientas de mantenimiento (`self_test.py`) | ❌ No |

El ZIP se construye con `git archive <tag> skills`: todo lo que viva fuera de `skills/` queda automáticamente fuera del paquete que descargan los usuarios. No pongas tooling de mantenimiento dentro de `skills/`.

## Convenciones

- **Commits** en español, estilo conventional: `feat(vX.Y):`, `fix(vX.Y):`, `docs(vX.Y):`, `test:`, `chore:`.
- **Scripts en Python stdlib puro** siempre que sea posible — el arnés corre en entornos donde no se puede instalar nada. Degradación elegante: una capacidad opcional nunca bloquea (ej. drawio sin MCP, `code_intel` sin índice).
- **Las plantillas son ejemplos ejecutables**: si una plantilla tiene gate, debe pasarlo tal cual (`gate_checker.py <plantilla> --tipo <tipo>` exit 0).
- **Detalle operativo completo** del checklist de release en la Guía de uso §5k.

## Proceso

1. Fork + rama (`fix/...`, `feat/...`).
2. Cambios + self-test verde + CHANGELOG.
3. PR describiendo: qué se rompía/faltaba, cómo se verifica (pega la salida del self-test).
4. El maintainer revisa, mergea y publica release siguiendo el checklist de §5k.
