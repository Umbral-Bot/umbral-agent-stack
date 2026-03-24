---
id: "2026-03-24-005"
title: "Accion 4: sanear sesiones y transcripts de OpenClaw en VPS"
status: done
assigned_to: codex
created_by: codex
priority: medium
sprint: R23
created_at: 2026-03-24T01:58:00-03:00
updated_at: 2026-03-24T02:00:00-03:00
---

## Objetivo
Dejar consistente el store de sesiones/transcripts de OpenClaw en la VPS, reduciendo ruido de `doctor` sin perder historial util.

## Contexto
- El diagnostico integral detecto deuda en `~/.openclaw/agents/main/sessions`.
- `openclaw doctor` reportaba `4/5 recent sessions are missing transcripts` y `6 orphan transcript files`.
- `openclaw sessions cleanup --agent main --dry-run --fix-missing --json` indicaba que mutaria el store de `main` de `55` a `47`.
- El chequeo directo por `sessionId -> <sessionId>.jsonl` no reproducia inicialmente el mismo conteo, asi que fue necesario validar la mutacion con backup previo y diff exacto de claves removidas.
- Se creo backup inicial de `sessions.json` en `~/.openclaw/agents/main/sessions/.cleanup-backups/`.

## Criterios de aceptacion
- [x] Se corre `dry-run` y se identifica con evidencia que entries y/o transcripts serian afectados.
- [x] Se respalda el store antes de cualquier mutacion real.
- [x] Se aplica el saneamiento real solo si la mutacion es segura.
- [x] Se vuelve a correr `openclaw doctor` para verificar mejora real.
- [x] Queda documentado el resultado honesto en tarea, board y diagnostico si cambia el estado del hallazgo.

## Log
### [codex] 2026-03-24 01:58
Tarea creada. Estado inicial: `openclaw doctor` sigue reportando `4/5 recent sessions are missing transcripts` y `6 orphan transcript files`, pero el chequeo directo de `sessions.json` contra `<sessionId>.jsonl` no reproduce esa inconsistencia. Se hara backup + comparacion exacta antes de aplicar `cleanup --enforce`.

### [codex] 2026-03-24 01:57
Saneamiento ejecutado en la VPS sobre `main`:

- backup de `sessions.json` en `~/.openclaw/agents/main/sessions/.cleanup-backups/sessions.json.20260324-045424.bak`
- snapshot de claves previas en `~/.openclaw/agents/main/sessions/.cleanup-backups/keys.before.20260324-accion4.json`
- `openclaw sessions cleanup --agent main --enforce --fix-missing --json` redujo el store de `55` a `47`
- claves removidas: 8, todas de runs `cron` recientes con transcripts faltantes
- se reinicio `openclaw-gateway.service` para recargar el store saneado
- se archivaron 6 transcripts huérfanos como `*.jsonl.deleted.2026-03-24T04-56-58.322796Z`

Validacion final:
- `openclaw doctor` ya no reporta `recent sessions missing transcripts`
- `openclaw doctor` ya no reporta `orphan transcript files`
- el hallazgo de higiene de sesiones/transcripts queda resuelto para `main`

Deuda restante no incluida en esta accion:
- warning de Telegram first-time setup
- startup optimization (`NODE_COMPILE_CACHE`, `OPENCLAW_NO_RESPAWN`)
