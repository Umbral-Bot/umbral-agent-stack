---
id: "2026-03-23-001"
title: "Calendar/Gmail: env VPS + seguimiento post VM + diagnóstico"
status: done
assigned_to: codex
created_by: cursor
priority: medium
sprint: R22
created_at: 2026-03-23T00:00:00-03:00
updated_at: 2026-03-24T00:00:00-03:00
---

## Checklist para David (antes de asignar a Codex)

1. **VM:** `main` actualizado, `openclaw-worker` arriba, `/health` OK (ya validado 2026-03-22/23).
2. **`WORKER_TOKEN`:** alineado entre VM, NSSM y VPS (`~/.config/openclaw/env`) si Codex va a probar E2E.
3. **Secretos Google:** tener a mano (sin pegar en chat) refresh tokens / client id para **pegar en la VPS** en la sesión que elijas — Codex no puede inventar credenciales.
4. **Leer:** `.agents/para-rick.md` (sección 2026-03-23) y `docs/35-google-calendar-token-setup.md` para lenguaje común.
5. **Git:** hacer `git pull` en la máquina donde Codex trabaje para traer este commit/docs.

---

## Objetivo

Cerrar el gap operativo después de activar APIs Google (Calendar/Gmail) en el entorno local/rama: **variables en el Worker de la VPS**, verificación con `/run`, y **seguimiento** alineado con el super diagnóstico (monitoreo, correcciones menores de docs o drift).

Contexto previo (integrado en main por Cursor, 2026-03-23): `docs/35-google-calendar-token-setup.md`, `.env.example`, `.agents/para-rick.md`, skills `gmail` / `google-calendar` — discoverability para Rick y coherencia refresh vs Bearer.

---

## Contexto

- El Worker ya implementa `google.calendar.*` y `gmail.*`; OpenClaw expone `umbral_google_calendar_*` y `umbral_gmail_*`.
- Sin `GOOGLE_*` en el **proceso Worker** de la VPS, Rick seguirá viendo errores aunque el gateway tenga otras keys.
- Auditoría histórica: `docs/audits/vps-openclaw-llm-audio-validation-2026-03-08.md` mencionaba Calendar/Gmail bloqueados por credenciales — re-validar tras configurar env.

---

## Tareas

### 1. VPS — Worker env

1. Revisar `~/.config/openclaw/env` (o donde cargue el Worker en la VPS) y documentar qué vars de Google faltan vs `.env.example`.
2. Si David ya tiene refresh tokens en vault/local, **no** pegar secretos en el repo: indicar checklist de nombres exactos (`GOOGLE_CALENDAR_*`, `GOOGLE_GMAIL_*`).
3. Tras setear, reiniciar el servicio del Worker en la VPS si aplica y ejecutar verificación según `docs/35-google-calendar-token-setup.md` (POST `/run` `google.calendar.list_events`).

### 2. Verificación cruzada

- Mismo `WORKER_TOKEN` que Dispatcher y VM (ya corregido en operaciones recientes).
- Desde VPS: `curl` o script a `WORKER_URL` con tasks Calendar/Gmail; registrar resultado en el Log (OK / error sin valores secretos).

### 3. Seguimiento / monitoreo (ligero)

- Revisar si el super diagnóstico o `docs/audits/agent-stack-followups-2026-03-22.md` listan items aún abiertos relacionados con Worker, quotas o Notion — **solo** si encajan en el mismo turno; si no, crear subtarea o nota en board.

### 4. Documentación

- Si encontrás drift adicional (ej. otro doc que mencione solo `GOOGLE_CALENDAR_TOKEN` para verificación), unificar con un enlace a `docs/35-google-calendar-token-setup.md`.

---

## Criterios de aceptación

- [x] VPS Worker tiene vars Google necesarias **o** queda documentado explícitamente qué falta y quién las provee (David).
- [x] Verificación `/run` Calendar (y Gmail si aplica) registrada en Log con resultado.
- [x] Board actualizado; sin secretos en commits.

## Log

### david 2026-03-24 (VPS runtime)
Calendar OK (refresh en env). Gmail: `GOOGLE_GMAIL_*` configurado; tras `restart-worker.sh`, `gmail.list_drafts` y `gmail.create_draft` OK (`ok: true`). OAuth = cuenta Rick por decisión de producto.

### cursor 2026-03-23
Tarea creada; docs + para-rick + .env.example + skills actualizados en repo.
