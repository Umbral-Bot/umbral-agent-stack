---
id: "2026-03-23-011"
title: "Fase 2: separar rate limiting interno del trafico externo"
status: in_progress
assigned_to: codex
created_by: codex
priority: high
sprint: R24
created_at: 2026-03-23T13:34:49-03:00
updated_at: 2026-03-23T13:34:49-03:00
---

## Objetivo
Resolver el hallazgo de Fase 2: el Worker no debe mezclar en el mismo bucket de rate limiting a crons, diagnósticos y tráfico humano autenticado que hoy llegan por `127.0.0.1` o clientes internos equivalentes.

## Contexto
- Diagnóstico base: `docs/audits/super-diagnostico-interconectividad-2026-03-23.md` (`P0.3`).
- `worker/app.py` hoy limita por `request.client.host`.
- En la VPS, varios scripts y crons llaman al Worker local, comparten `127.0.0.1` y pueden disparar `429` falsos.
- El fix debe preservar protección para tráfico externo y dejar una semántica más útil para tráfico interno autenticado.

## Criterios de aceptación
- [ ] El rate limiter deja de agrupar todo el tráfico interno autenticado bajo un único bucket por IP.
- [ ] El tráfico externo mantiene rate limiting razonable.
- [ ] Hay tests que cubren el nuevo comportamiento.
- [ ] Se valida en vivo en la VPS con una prueba reproducible que antes era susceptible a `429`.
- [ ] Task y board quedan actualizados con resultado honesto.

## Log
### [codex] 2026-03-23 13:34
Tarea creada. Voy a atacar el slice en `worker/app.py` y pruebas del Worker. La hipótesis de implementación es distinguir tráfico interno autenticado y darle un bucket más fino por ruta/tarea, manteniendo el bucket externo por cliente.
### [codex] 2026-03-23 14:31
Implementado el slice de repo. Cambios principales:
- `worker/app.py`: rate limiting externo por cliente/IP e interno autenticado por host+ruta+tarea, con `X-RateLimit-*` y soporte opcional de `X-Umbral-Caller`.
- `worker/config.py`: nueva variable `RATE_LIMIT_INTERNAL_RPM` (default 600).
- `client/worker_client.py` y `scripts/run_worker_task.py`: soporte para `caller_id`.
- `scripts/verify_stack_vps.py`, `scripts/e2e_validation.py`, `scripts/smoke_test.py`, `scripts/dashboard_report_vps.py`, `scripts/vps/health-check.sh`, `scripts/vps/e2e-validation-cron.sh`, `scripts/vps/supervisor.sh`: caller IDs explícitos para tráfico interno frecuente.
- Tests nuevos/ajustados en `tests/test_worker.py`, `tests/test_enqueue_api.py`, `tests/test_worker_client.py`, `tests/conftest.py`.

Validación local:
- `python -m pytest tests/test_worker.py tests/test_enqueue_api.py tests/test_worker_client.py tests/test_hardening.py -q` -> `89 passed`
- `WORKER_TOKEN=test python -m pytest tests -q` -> `1208 passed, 4 skipped, 1 warning`

Pendiente antes de cerrar: deploy en VPS y smoke reproducible para confirmar que el `429` interno deja de aparecer en runtime real.
