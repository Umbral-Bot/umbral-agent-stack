---
id: "2026-05-04-006"
title: "Verificar en VPS si faltan GOOGLE_CLIENT_ID/SECRET/REFRESH_TOKEN base (O8b.0 blocker)"
status: done
assigned_to: copilot
created_by: copilot-chat-notion-governance
priority: high
sprint: Q2-2026 W2
created_at: 2026-05-04T00:00:00Z
updated_at: 2026-05-04T00:00:00Z
---

## Contexto previo

- Regla obligatoria: `.github/copilot-instructions.md` → sección **"VPS Reality Check Rule"** (commit `fbc5dae`, 2026-05-04). Antes de cualquier afirmación runtime: SSH + `journalctl`/`systemctl`/`cat env`. Nada de "el repo dice X, así que el problema es Y".
- Esta tarea NACE de un diagnóstico hecho desde `notion-governance` que dice (sin verificar): _"`~/.config/openclaw/env` tiene `GOOGLE_CALENDAR_*` y `GOOGLE_GMAIL_*` pero le falta el set base `GOOGLE_CLIENT_ID/SECRET/REFRESH_TOKEN`, y por eso O8b.0 (Drive/Workspace scope) está bloqueado."_ Esa afirmación viene de `notion-governance/.claude/memory/notion-governance-lessons.md` línea 10, NO de un check a la VPS.
- Antes de gastar 2 h reconfigurando OAuth en Google Cloud Console, hay que **verificar el estado real**.

Plan Q2-2026 referencia: `notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md` línea 498 (O8b.0 unchecked).

## Objetivo

Determinar con evidencia de la VPS:

1. Qué variables `GOOGLE_*` están **realmente** seteadas en `~/.config/openclaw/env` del usuario `rick`.
2. Qué nombres de variables consume la skill Granola Pipeline V2 (`openclaw/workspace-templates/skills/granola-pipeline/`) en runtime.
3. Si la diferencia entre (1) y (2) es el blocker real de O8b.0, o si el blocker es otro (token expirado, scopes faltantes, API no habilitada en GCP, etc.).

## Procedimiento mínimo

Ejecutar en la VPS como `rick`:

```bash
# 1) Inventario de GOOGLE_* en el env real (sin imprimir valores)
grep -E '^(GOOGLE_|GMAIL_|GCAL_)' ~/.config/openclaw/env \
  | sed -E 's/=.*/=<REDACTED>/' \
  | sort

# 2) Permisos del archivo (debe ser 600)
ls -la ~/.config/openclaw/env

# 3) Qué variables GOOGLE_* lee la skill Granola pipeline
grep -RInE 'GOOGLE_[A-Z_]+|GMAIL_[A-Z_]+|GCAL_[A-Z_]+' \
  ~/umbral-agent-stack/openclaw/workspace-templates/skills/granola-pipeline/ \
  2>/dev/null \
  | sort -u

# 4) Lo mismo para el worker y dispatcher (consumidores potenciales)
grep -RInE 'GOOGLE_[A-Z_]+' \
  ~/umbral-agent-stack/worker/ \
  ~/umbral-agent-stack/dispatcher/ \
  2>/dev/null \
  | sort -u

# 5) Última corrida de Granola y errores recientes relacionados con Google
tail -300 ~/.config/umbral/ops_log.jsonl 2>/dev/null \
  | jq 'select(.event | test("granola|google|drive|gmail|calendar"; "i"))' \
  2>/dev/null | tail -50

# 6) Health del worker (sanity)
curl -fsS http://127.0.0.1:8088/health || echo "WORKER NO RESPONDE"

# 7) Status del servicio
systemctl --user status umbral-worker --no-pager | head -20
```

## Criterios de aceptación

- [ ] Reporte en este `## Log` con OUTPUT REAL de cada comando (truncado si es largo, pero no inventado).
- [ ] Tabla explícita "Repo dice X" vs "VPS muestra Y" para los nombres de variables `GOOGLE_*`.
- [ ] Veredicto: ¿la hipótesis "faltan `GOOGLE_CLIENT_ID/SECRET/REFRESH_TOKEN` base y por eso O8b.0 está bloqueado" se **confirma**, se **refuta**, o se **refina** (otro blocker)?
- [ ] Si se confirma: lista de pasos faltantes (qué API habilitar en GCP, qué scopes pedir en OAuth Playground, qué keys exactas inyectar en `~/.config/openclaw/env`).
- [ ] Si se refuta: cuál es el blocker real con evidencia (log, error message, etc.).
- [ ] `status:` cambiado a `done` o `blocked`. Si `blocked`, indicar qué necesita de David.

## Antipatrones que esta tarea prohíbe

- ❌ "Leí `granola-pipeline/SKILL.md` y dice que usa `GOOGLE_CLIENT_ID`, así que confirmo el blocker." → eso NO es verificación. La verificación es el OUTPUT REAL del `grep` al env de la VPS.
- ❌ Asumir que `notion-governance-lessons.md` es source of truth para runtime — esa memoria puede tener semanas de antigüedad.
- ❌ Confirmar el blocker sin chequear si las APIs de Google Drive/Docs están habilitadas en el proyecto GCP de Rick.
- ❌ Imprimir valores reales de tokens/secrets en el log (usar `<REDACTED>` o solo el nombre de la variable).

## Log

- 2026-05-04 — `copilot-chat@notion-governance` — Tarea creada. Disparador: durante el avance W2 del Plan Q2-2026, el agente produjo una receta de 2 h para O8b.0 basada en memoria del repo, sin verificar la VPS. El usuario lo cuestionó correctamente ("¿quién hizo ese diagnóstico? ¿está validado por la VPS?"). Esta tarea cierra el gate antes de gastar tiempo en GCP Console.
- 2026-05-04 ~20:25 -04 — `copilot-vps` — Diagnóstico ejecutado en VPS, veredicto: **HIPÓTESIS REFUTADA + REFINADA**. Detalles abajo.

### OUTPUT REAL de los 7 comandos

**CMD 1 — `GOOGLE_*/GMAIL_*/GCAL_*` en `~/.config/openclaw/env` (redacted):**

```
GOOGLE_API_KEY=<REDACTED>
GOOGLE_API_KEY_NANO=<REDACTED>
GOOGLE_API_KEY_RICK_UMBRAL=<REDACTED>
GOOGLE_CALENDAR_CLIENT_ID=<REDACTED>
GOOGLE_CALENDAR_CLIENT_SECRET=<REDACTED>
GOOGLE_CALENDAR_REFRESH_TOKEN=<REDACTED>
GOOGLE_CLOUD_LOCATION=<REDACTED>
GOOGLE_CLOUD_PROJECT=<REDACTED>
GOOGLE_CLOUD_PROJECT_RICK_UMBRAL=<REDACTED>
GOOGLE_CSE_API_KEY_RICK_UMBRAL=<REDACTED>
GOOGLE_CSE_API_KEY_RICK_UMBRAL_2=<REDACTED>
GOOGLE_CSE_CX=<REDACTED>
GOOGLE_GMAIL_CLIENT_ID=<REDACTED>
GOOGLE_GMAIL_CLIENT_SECRET=<REDACTED>
GOOGLE_GMAIL_REFRESH_TOKEN=<REDACTED>
```

NO hay `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN` base. NO hay `GOOGLE_DRIVE_*` ni `GOOGLE_DOCS_*` ni `GOOGLE_WORKSPACE_*`.

**CMD 2 — Permisos del env:**

```
-rw-r--r-- 1 rick rick 4079 Apr 12 19:53 /home/rick/.config/openclaw/env
```

⚠️ **Permisos `644` (world-readable), NO `600`.** El archivo contiene refresh tokens y client secrets en texto plano, y cualquier usuario en el sistema puede leerlo. No es el blocker de O8b.0 pero es un hallazgo de seguridad colateral que merece task aparte.

**CMD 3 — Granola pipeline skill GOOGLE_*/GMAIL_*/GCAL_*:**

```
(vacío — 0 matches)
```

🔴 **La skill Granola pipeline NO consume ninguna variable `GOOGLE_*`.** La premisa de la hipótesis ("Granola pipeline V2 necesita esas creds") es falsa a nivel de código.

**CMD 4 — Worker/dispatcher GOOGLE_* refs (resumen):**

Variables consumidas por el código real:
- `GOOGLE_API_KEY`, `GOOGLE_API_KEY_NANO`, `GOOGLE_API_KEY_RICK_UMBRAL`, `GOOGLE_CLOUD_PROJECT_RICK_UMBRAL` — Gemini/Vertex (`worker/tasks/llm.py`, `worker/tasks/google_audio.py`, `worker/tasks/google_image.py`, `dispatcher/model_router.py`).
- `GOOGLE_CSE_API_KEY_RICK_UMBRAL[_2]`, `GOOGLE_CSE_CX` — Custom Search (`worker/research_backends.py`).
- `GOOGLE_GMAIL_TOKEN`, `GOOGLE_GMAIL_REFRESH_TOKEN`, `GOOGLE_GMAIL_CLIENT_ID`, `GOOGLE_GMAIL_CLIENT_SECRET`, `GOOGLE_SERVICE_ACCOUNT_JSON` — Gmail (`worker/tasks/gmail.py`).
- `GOOGLE_CALENDAR_TOKEN`, `GOOGLE_CALENDAR_REFRESH_TOKEN`, `GOOGLE_CALENDAR_CLIENT_ID`, `GOOGLE_CALENDAR_CLIENT_SECRET` — Calendar (`worker/tasks/google_calendar.py`).

🔴 **CERO referencias a `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REFRESH_TOKEN` (sin prefijo) en todo el repo.** Solo aparecen en el texto de esta misma task.

🔴 **CERO referencias a `google.drive.*` / `google.docs.*` / `google_drive` / `google_docs` en `worker/` o `dispatcher/`.** Único hit en todo el repo: `scripts/vm/granola_full_gap_audit.py:482` que usa `GOOGLE_DRIVE_MANUAL_DIR` como path local manual (no API OAuth).

**CMD 5 — ops_log Granola/Google events últimos 300:**

```
(vacío — 0 matches relevantes en últimas 300 entradas)
```

**CMD 6 — Worker health:**

```
{"ok":true,"ts":1777954989,"version":"0.4.0",...}
```

Worker healthy. Tasks Google registradas: `google.calendar.create_event`, `google.calendar.list_events`, `gmail.create_draft`, `gmail.list_drafts`, `google.audio.generate`, `google.image.generate`. **NINGUNA `google.drive.*` ni `google.docs.*`.**

**CMD 7 — umbral-worker service status:**

```
● umbral-worker.service - Umbral Worker API
   Active: active (running) since Mon 2026-04-27 05:41:32 -04; 1 week 0 days ago
   Main PID: 1124888
```

Servicio activo desde hace 1 semana sin restart. Logs recientes son requests Notion, sin errores Google.

### Tabla "Repo dice X" vs "VPS muestra Y"

| Variable | Repo (premisa de la hipótesis) | VPS env real | Código que la consume |
|---|---|---|---|
| `GOOGLE_CLIENT_ID` | "falta, bloquea O8b.0" | **AUSENTE** | **NINGUNO** (0 hits) |
| `GOOGLE_CLIENT_SECRET` | "falta, bloquea O8b.0" | **AUSENTE** | **NINGUNO** (0 hits) |
| `GOOGLE_REFRESH_TOKEN` | "falta, bloquea O8b.0" | **AUSENTE** | **NINGUNO** (0 hits) |
| `GOOGLE_GMAIL_CLIENT_ID` | (no mencionada) | PRESENTE | `worker/tasks/gmail.py:44` |
| `GOOGLE_GMAIL_CLIENT_SECRET` | (no mencionada) | PRESENTE | `worker/tasks/gmail.py:45` |
| `GOOGLE_GMAIL_REFRESH_TOKEN` | (no mencionada) | PRESENTE | `worker/tasks/gmail.py:43` |
| `GOOGLE_CALENDAR_CLIENT_ID` | (no mencionada) | PRESENTE | `worker/tasks/google_calendar.py:40` |
| `GOOGLE_CALENDAR_CLIENT_SECRET` | (no mencionada) | PRESENTE | `worker/tasks/google_calendar.py:41` |
| `GOOGLE_CALENDAR_REFRESH_TOKEN` | (no mencionada) | PRESENTE | `worker/tasks/google_calendar.py:39` |
| `GOOGLE_DRIVE_*` | (implícita en "Drive/Workspace scope") | **AUSENTE** | **NINGUNO** (0 handlers) |
| `GOOGLE_DOCS_*` | (implícita en "Drive/Workspace scope") | **AUSENTE** | **NINGUNO** (0 handlers) |

### Veredicto: **HIPÓTESIS REFUTADA + REFINADA**

**Por qué se refuta:**

1. **Las variables base `GOOGLE_CLIENT_ID/SECRET/REFRESH_TOKEN` no son consumidas por ningún código en `worker/`, `dispatcher/`, ni en la skill `granola-pipeline/`.** El repo entero tiene 0 referencias a esos nombres exactos. Agregarlas al env no desbloquearía nada porque nada las leería.

2. **La premisa "Granola pipeline V2 necesita esas creds" es falsa.** La skill `openclaw/workspace-templates/skills/granola-pipeline/` tiene 0 referencias a cualquier variable `GOOGLE_*`/`GMAIL_*`/`GCAL_*`. Granola en este stack es un pipeline interno (procesar transcripts + crear human tasks), no consume Google APIs directamente.

3. **El env tiene credenciales OAuth completas para Gmail y Calendar** con el patrón scoped (`GOOGLE_<SERVICE>_{CLIENT_ID,CLIENT_SECRET,REFRESH_TOKEN}`). Esa es la convención del repo y funciona.

**Por qué se refina (cuál es el blocker real de O8b.0):**

O8b.0 = "Drive/Workspace scope". El blocker real no es de credenciales sino **de implementación**:

- **No existen handlers `google.drive.*` ni `google.docs.*` en `worker/tasks/`** — verificado vía CMD 6 (worker `tasks_registered` no los lista) y CMD 4 (0 hits de `google_drive`/`google_docs` en código).
- Sin handler, no hay consumer; sin consumer, definir creds es prematuro.

**Plan correcto para desbloquear O8b.0** (NO ejecutar sin OK de David):

1. **Decidir alcance funcional:** ¿qué operaciones Drive/Docs necesita el sistema concretamente? (read files, write files, share, list, search, append to doc, etc.) Sin este recorte, "Drive/Workspace scope" es vago.
2. **Implementar handlers** en `worker/tasks/google_drive.py` y/o `worker/tasks/google_docs.py` siguiendo el patrón existente de `gmail.py` y `google_calendar.py` (refresh_token + client_id + client_secret + access_token cache).
3. **Registrar las tasks** en `worker/app.py`.
4. **Decisión de creds (dos opciones):**
   - (A) **Reusar el OAuth client existente de Calendar o Gmail** (mismo proyecto GCP), simplemente añadir scopes `drive` / `docs` al consent y rotar refresh token de ese cliente. Más simple, menos clients que mantener.
   - (B) **Crear un OAuth client nuevo dedicado** y agregar variables `GOOGLE_DRIVE_CLIENT_ID/SECRET/REFRESH_TOKEN` siguiendo la convención scoped. Más aislado, mejor auditabilidad.
5. **Habilitar APIs en GCP Console** del proyecto que se use: Drive API y Docs API.
6. **Inyectar las variables nuevas en `~/.config/openclaw/env`** (NO base sin prefijo — siempre scoped, según la convención existente).

**Estimación corregida:** la "receta de 2h para configurar OAuth base" es errónea. El trabajo real es implementación (handlers + tests + registro) más decisión de scopes en cliente OAuth existente. 2-3 sesiones, no 2 h, y empieza por el ADR de scope funcional, no por GCP Console.

### Hallazgos colaterales

- **SECURITY:** `~/.config/openclaw/env` con permisos `644`. Contiene refresh tokens y client secrets. Recomendación: `chmod 600 ~/.config/openclaw/env`. Crear task aparte para rotación + chmod (no la ejecuto acá porque la tarea es solo diagnóstico de O8b.0).
- La memoria `notion-governance/.claude/memory/notion-governance-lessons.md:10` tiene info incorrecta sobre el blocker O8b.0. Actualizar esa entrada cuando se cierre esta task.

### Estado final

- Hipótesis original: ❌ refutada.
- Blocker real: implementación de handlers Drive/Docs + decisión de scopes OAuth (no falta de creds).
- Acción inmediata: ninguna en runtime/GCP — espera decisión de David sobre el plan refinado de arriba.

Status: `done` (diagnóstico completado, sin acciones reversivas ejecutadas).
