---
id: "2026-03-23-001"
title: "Calendar/Gmail en VPS y seguimiento post-diagnostico"
status: blocked
assigned_to: codex
created_by: codex
priority: high
sprint: R21
created_at: 2026-03-23T00:00:00-03:00
updated_at: 2026-03-23T00:05:00-03:00
---

## Objetivo

Cierre operativo post-diagnostico para Google Calendar y Gmail en el Worker de
la VPS, sin re-auditar todo el stack. Verificar como carga env el Worker vivo,
comparar contra `.env.example` y docs Google, ejecutar smoke real por `POST
/run` y dejar trazabilidad honesta de lo que quedo funcionando y de lo que
depende de credenciales que David debe pegar en la VPS.

## Contexto

- El super diagnostico `2026-03-22-002` ya fue entregado.
- Los fixes mayores del informe quedaron en `main` via PRs previos, en especial
  `2026-03-22-003` / PR #127.
- Tras `git pull origin main`, este task file todavia no existia en
  `.agents/tasks/`; se materializa aqui desde el brief del usuario para dejar
  board y log consistentes con la operacion real.
- Runbooks y docs fuente usados en esta ejecucion:
  - `docs/62-operational-runbook.md`
  - `docs/35-google-calendar-token-setup.md`
  - `docs/35-gmail-token-setup.md`
  - `.env.example`
  - `docs/audits/agent-stack-followups-2026-03-22.md`

## Criterios de aceptacion

- [x] Confirmado en VPS desde donde carga env el Worker (`~/.config/openclaw/env`
      via scripts de supervisor/restart).
- [x] Comparadas variables Google de la VPS contra `.env.example` y docs, sin
      exponer secretos.
- [x] `google.calendar.list_events` verificado por `POST /run` en la VPS usando
      `WORKER_URL` y `WORKER_TOKEN` del entorno remoto.
- [ ] `gmail.list_drafts` verificado por `POST /run` en la VPS.
- [x] Seguimiento ligero de follow-up Worker/Dispatcher documentado.
- [x] `board.md` y log actualizados con estado real.

## Estado operativo verificado

### VPS Worker y carga de entorno

- El Worker vivo corre en la VPS desde `main`:
  - PID `1074741`
  - comando `/home/rick/umbral-agent-stack/.venv/bin/python -m uvicorn worker.app:app --host 127.0.0.1 --port 8088 --log-level info`
- El cron canónico de mantenimiento sigue llamando:
  - `bash /home/rick/umbral-agent-stack/scripts/vps/supervisor.sh`
- Los scripts de restart/supervisor cargan `~/.config/openclaw/env`; no se
  detecto en esta tarea otro origen canónico de env para el Worker.

### Variables Google observadas en `~/.config/openclaw/env`

- `GOOGLE_CALENDAR_TOKEN`: missing
- `GOOGLE_CALENDAR_REFRESH_TOKEN`: set (`len=103`)
- `GOOGLE_CALENDAR_CLIENT_ID`: set (`len=72`)
- `GOOGLE_CALENDAR_CLIENT_SECRET`: set (`len=35`)
- `GOOGLE_GMAIL_TOKEN`: missing
- `GOOGLE_GMAIL_REFRESH_TOKEN`: missing
- `GOOGLE_GMAIL_CLIENT_ID`: missing
- `GOOGLE_GMAIL_CLIENT_SECRET`: missing
- `GOOGLE_SERVICE_ACCOUNT_JSON`: missing
- `WORKER_URL`: set (`len=21`)
- `WORKER_TOKEN`: set (`len=48`)

## Log

### [codex] 2026-03-23 00:05 -03:00

Ejecutado `git pull origin main` en este worktree antes de tocar artefactos del
repo; resultado: `Already up to date.`. Se leyo `.agents/PROTOCOL.md`,
`.agents/board.md`, `.env.example`, `docs/35-google-calendar-token-setup.md`,
`docs/35-gmail-token-setup.md`, `docs/62-operational-runbook.md` y
`docs/audits/agent-stack-followups-2026-03-22.md`.

Con SSH real a la VPS (`ssh vps-umbral`) se verifico:

- repo `/home/rick/umbral-agent-stack` en `main`
- Worker vivo en PID `1074741`
- cron `*/5 * * * * bash /home/rick/umbral-agent-stack/scripts/vps/supervisor.sh >> /tmp/supervisor.log 2>&1`
- env file presente en `~/.config/openclaw/env`

Inventario seguro de env en VPS:

- Calendar configurado con refresh token + client id + client secret
- Gmail sin credenciales
- `WORKER_URL` y `WORKER_TOKEN` presentes

Smoke real por `POST /run`, usando `WORKER_URL` y `WORKER_TOKEN` cargados desde
`~/.config/openclaw/env`:

- `google.calendar.list_events` -> HTTP `200`, `ok=true`, `events=0`
- `gmail.list_drafts` -> no ejecutado porque faltan `GOOGLE_GMAIL_*` y no hay
  `GOOGLE_SERVICE_ACCOUNT_JSON`

No se reinicio el Worker en esta corrida porque no se cambiaron credenciales en
la VPS durante el turno y el smoke de Calendar ya paso con el proceso vivo.

Follow-up ligero validado en el mismo turno:

- `Unificar dispatcher vivo en VPS` sigue vigente. Se observaron dos procesos
  `dispatcher.service` (`905626` y `1074021`) mientras
  `bash scripts/vps/dispatcher-service.sh status` reporta solo el PID canónico
  `1074021`.

Accion pendiente para David:

1. Pegar en `~/.config/openclaw/env` uno de estos esquemas para Gmail:
   - recomendado: `GOOGLE_GMAIL_REFRESH_TOKEN`,
     `GOOGLE_GMAIL_CLIENT_ID`, `GOOGLE_GMAIL_CLIENT_SECRET`
   - alternativa temporal: `GOOGLE_GMAIL_TOKEN`
2. Reiniciar Worker en la VPS:
   - `bash ~/umbral-agent-stack/scripts/vps/restart-worker.sh`
   - o `bash ~/umbral-agent-stack/scripts/vps/supervisor.sh`
3. Repetir smoke:
   - `gmail.list_drafts` por `POST /run`

La tarea queda `blocked` solo por ese insumo externo; Calendar en VPS ya quedo
operativo y verificado.
