# Fase 6 + F8a acotados — closeout (PKG-MACRO-P5-Q9-T1, 2026-08-21)

**Q9 = A:** retirar monitor fase 6; congelar F8a. Reconteo E6 filas 4 y 7.
Este es el closeout canónico: **donde choque con esas dos filas, gana éste.**

## Qué estaba mal

El monitor dedicado (`scripts/monitor_supervisor_observability.py`) no tenía
cron ni toque desde 2026-04-20 — fase 6 nunca ancló. F8a tenía evidencia live
histórica (mayo 2026) sin re-corrida ni smoke recurrente que la justifique
hoy. Ambos docs seguían leyéndose como si estuvieran activos.

## Qué se hizo

- Borrados `scripts/monitor_supervisor_observability.py` y
  `tests/test_supervisor_observability_monitoring.py`.
- `tests/test_supervisor_structured_telemetry.py`: sacada solo la entrada del
  script del `parametrize` de imports prohibidos; el resto (router, ops_logger,
  telemetría estructurada) intacto.
- `docs/75`, `76` y `77` llevan cabecera HISTÓRICO/RETIRADO. No se
  reescribieron.
- `docs/copilot-cli-f8a-real-execution-path.md` lleva banner CONGELADO: sin
  smoke recurrente, reactivar por caso de uso con GO explícito.
- `/code-review` encontró una referencia colgante fuera del sweep original:
  `openclaw/workspace-agent-overrides/improvement-supervisor/ROLE.md` citaba
  el script borrado como tooling vivo. Corregida (mínimo, sin reescribir el
  ROLE). `docs/75`/`77` tienen contenido histórico sin tachar más allá de la
  cabecera — a propósito, por instrucción explícita de no reescribir.

## Qué NO se hizo, a propósito

`dispatcher/supervisor_observability.py` y su cobertura de tests (fila 1)
**intactos** — la observability integrada en `dispatcher/router.py` sigue
viva. `worker/tasks/copilot_cli.py` intacto, `copilot_cli.run` sigue
registrado en el worker. `config/supervisors.yaml` (ya `design_only`) y
`config/tool_policy.yaml` sin tocar. `reports/copilot-cli/f8a-*` y
`.agents/tasks/f8a-*` quedan como histórico. Sin cron nuevo, sin job CI,
sin restart de worker/dispatcher/gateway.
