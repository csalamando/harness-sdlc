# Waiver de Strict TDD — <proyecto>

> Artefacto de excepción gobernada (v2.33.3). Sin test runner configurado,
> `detect_stack.py` sale con exit 2 y Strict TDD queda EN PAUSA. Entrar a
> Fase 4 en ese estado exige este waiver **aprobado por un humano**:
> `receipt.py emit spec/tdd-waiver.md --gate "GATE 2" --role devops-engineer --approved-by <humano>`.
> `gate_verify.py --gate "GATE 2"` lo exige vigente si no hay runner.

## Contexto

- **Proyecto**: <nombre>
- **Fecha**: <YYYY-MM-DD>
- **Aprobado por**: <humano que asume el riesgo>

## Justificación

<por qué no hay test runner configurado aún: stack decidido pero sin setup,
stack sin ecosistema de tests maduro, prototipo desechable, etc.>

## Riesgo asumido

<qué deja de ser exigible: gates de cobertura, TDD estricto red-green-refactor
verificable, evidencia de tests candidatos por code_intel en GATE 2>

## Plan de resolución

<condición o fecha en que el runner se configurará y este waiver quedará
revocado — p. ej. "tras el ADR de stack de Fase 2" / "antes del sprint 2">

## Revocación

Cuando el runner quede configurado (`detect_stack.py` exit 0), este waiver se
revoca: `receipt.py revoke spec/tdd-waiver.md --reason "runner configurado"`.
