---
id: "2026-05-04-006"
title: "Verificar en VPS si faltan GOOGLE_CLIENT_ID/SECRET/REFRESH_TOKEN base (O8b.0 blocker)"
status: assigned
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
