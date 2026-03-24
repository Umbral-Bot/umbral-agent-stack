---
id: "2026-03-24-008"
title: "Test general post-acciones OpenClaw"
status: done
assigned_to: codex
created_by: codex
priority: high
sprint: R24
created_at: 2026-03-24T17:15:00-03:00
updated_at: 2026-03-24T19:10:00-03:00
---

## Objetivo
Ejecutar una validacion general post-acciones sobre OpenClaw y el wiring principal con Umbral Agent Stack para confirmar que las Acciones 1-6 y 8 no dejaron regresiones operativas.

## Contexto
- Las Acciones 1, 2, 3, 4, 5, 6 y 8 ya quedaron cerradas y mergeadas a `main`.
- La VPS ya quedo alineada a `main`.
- OpenClaw dashboard abre, skills quedaron sincronizadas y la gobernanza por workspace ya fue regularizada.

## Criterios de aceptacion
- [x] Queda corrida una bateria post-acciones sobre OpenClaw en VPS.
- [x] Queda corrida una validacion local relevante en el repo.
- [x] Quedan documentados hallazgos reales, residuales y proximos pasos si aparecen.
- [x] La tarea y el board quedan actualizados con resultado honesto.

## Log
### [codex] 2026-03-24 17:15
Tarea creada. Se preparan pruebas locales y validaciones vivas en la VPS sobre gateway, seguridad, cron, canales, skills, agentes y tools reales del stack.

### [codex] 2026-03-24 19:10
Test general post-acciones cerrado.

Validacion local:

- `WORKER_TOKEN=test python -m pytest tests -q` -> `1223 passed, 4 skipped`

Validacion viva en VPS:

- `openclaw status --all`
- `openclaw models status`
- `openclaw security audit --deep`
- `openclaw cron status`
- `openclaw channels status --probe`
- `openclaw agent --agent main` con `umbral_provider_status`, `umbral_linear_list_teams`, `umbral_google_calendar_list_events` y `umbral_research_web`
- smokes directos de `rick-ops`, `rick-tracker` y `rick-qa`
- `python3 scripts/verify_stack_vps.py`
- `python3 scripts/research_web_smoke.py --query "BIM trends 2026"`
- refresh forzado de `dashboard_report_vps.py` y `openclaw_panel_vps.py`

Hallazgos reales encontrados durante el test:

1. `umbral-worker.service` estaba en loop de auto-restart porque `8088` seguia ocupado por un `uvicorn worker.app` huerfano lanzado fuera de systemd.
2. Varios scripts VPS seguian cargando `~/.config/openclaw/env` con `source` / `export $(grep ... | xargs)`, lo que rompia al encontrar `LINEAR_AGENT_STACK_PROJECT_NAME=Mejora Continua Agent Stack`.
3. `verify_stack_vps.py` seguia mostrando la cadencia vieja y un ejemplo de carga de env inseguro.

Fixes aplicados:

- nuevo helper `scripts/vps/load-openclaw-env.sh`
- cron wrappers y scripts VPS actualizados para usar el helper seguro
- `restart-worker.sh` y `supervisor.sh` ahora limpian procesos `worker.app` sobre `127.0.0.1:8088` antes de delegar a systemd
- deteccion de `umbral-worker.service` endurecida con consulta exacta a `list-unit-files`
- `verify_stack_vps.py` actualizado con la cadencia actual y la forma segura de cargar env

Estado final:

- `umbral-worker.service` -> `ActiveState=active`, `SubState=running`
- `NRestarts` estable (`52 -> 52` en 10s)
- `127.0.0.1:8088` ya queda servido por el PID de systemd, no por un `nohup`
- `umbral_provider_status` -> `redis_available=true`
- `umbral_linear_list_teams` -> `team_count=1`
- `umbral_google_calendar_list_events` -> `event_count=0`
- `umbral_research_web` y `research_web_smoke.py` -> `provider=gemini_google_search`
- refresh de Dashboard Rick y OpenClaw -> sin stderr, desaparece el error `Continua: command not found`

Artefacto de cierre:

- `docs/audits/openclaw-post-actions-validation-2026-03-24.md`
