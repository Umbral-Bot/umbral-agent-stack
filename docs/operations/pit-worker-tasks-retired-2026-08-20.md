# Tournament/PIT fuera del worker — closeout (PKG-MACRO-P5-PIT-T1, 2026-08-20)

**Q7 = A:** matar PIT/tasks + colas. Reconteo E6 fila 18 / P5-16 / megadiag
fila 18. Este es el closeout canónico: **donde choque con esas dos, gana éste.**

## Qué estaba mal

PIT es HISTÓRICO desde #594 y no hay cron que dispare torneos, pero el worker
seguía registrando `tournament.run`, `github.orchestrate_tournament`,
`tournament_lane.*` y `pit.*` en `TASK_HANDLERS` — invocables a mano.

## Qué se hizo

- `worker/tasks/__init__.py` ya no importa ni registra esas 11 claves.
  Borrados `tournament.py`, `github_tournament.py`, `tournament_lane_github.py`,
  `pit_runner.py`. `worker/tasks/github.py` (preflight/branch/commit/pr) intacto.
- Docstring de `worker/sandbox/__init__.py` corregido (nombraba un handler
  que ya no existe).
- Test de no-regresión `tests/test_pit_tournament_tasks_retired.py`: falla si
  vuelve cualquier clave retirada o si los 4 módulos vuelven a importar.
- `scripts/pit/` y el PIT de `mission_control` quedan **residuales a
  propósito** (no importan lo borrado, pack futuro).
- Colas `agents/`: no eran jobs Redis, eran 21 carpetas de identidades
  torneo/PIT (~12M total, 232K–1.2M c/u), ninguna en `openclaw.json` ni KEEP.
  Movidas a `/home/rick/_archive/pit-tournament-agents-20260820/` + `INDEX.txt`.
- `/code-review` cazó 3 referencias colgantes fuera del grep original: allowlist
  del sandbox, `config/client_tiers.yaml` (task + feature flag muertos en las
  3 tiers) y el runbook con instrucciones sin marcar debajo del banner. Las 3,
  corregidas y re-testeadas en verde.

## Qué NO se hizo

`openclaw.json` no se mutó. `scripts/pit`, `examples/pit`,
`mission_control/routes/pit*.py` y skills OpenClaw de tournament, sin tocar.
El worker vivo sigue listando las tasks retiradas hasta el restart post-merge.
