---
id: "2026-05-05-001"
title: "SECURITY: chmod 600 ~/.config/openclaw/env + rotar refresh tokens y client secrets expuestos"
status: assigned
assigned_to: copilot
created_by: copilot-chat-notion-governance
priority: high
sprint: Q2-2026 W2
created_at: 2026-05-05T00:00:00Z
updated_at: 2026-05-05T00:00:00Z
---

## Contexto previo

Hallazgo colateral durante diagnóstico de O8b.0 (task `2026-05-04-006`, commit `ab2c34d` en `main`):

```
-rw-r--r-- 1 rick rick 4079 Apr 12 19:53 /home/rick/.config/openclaw/env
```

Permisos `644` (world-readable). El archivo contiene en plaintext:

- `GOOGLE_API_KEY`, `GOOGLE_API_KEY_NANO`, `GOOGLE_API_KEY_RICK_UMBRAL`
- `GOOGLE_CALENDAR_CLIENT_ID`, `GOOGLE_CALENDAR_CLIENT_SECRET`, `GOOGLE_CALENDAR_REFRESH_TOKEN`
- `GOOGLE_GMAIL_CLIENT_ID`, `GOOGLE_GMAIL_CLIENT_SECRET`, `GOOGLE_GMAIL_REFRESH_TOKEN`
- `GOOGLE_CSE_API_KEY_RICK_UMBRAL`, `GOOGLE_CSE_API_KEY_RICK_UMBRAL_2`, `GOOGLE_CSE_CX`
- (probablemente más secretos: Notion tokens, OpenAI keys, Anthropic keys, etc.)

Cualquier usuario en el sistema (o cualquier proceso comprometido) puede leer estos secretos. Riesgo elevado especialmente si la VPS comparte usuarios o si se introduce malware con acceso al sistema.

Regla: `secret-output-guard` skill (cross-repo) — secretos jamás en plaintext world-readable.

## Objetivo

1. Restringir permisos del archivo a `600` (solo `rick` puede leer/escribir).
2. Auditar si hay otros archivos en `~/.config/` (o paths de openclaw/umbral) con permisos laxos.
3. **Rotar las credenciales que estuvieron expuestas** (asumir compromiso aunque no haya evidencia de acceso indebido — los logs del sistema no son retroactivos).
4. Documentar en runbook el patrón correcto para nuevos secrets.

## Procedimiento mínimo

```bash
# 1) Estado actual y aplicar chmod
ls -la ~/.config/openclaw/env
chmod 600 ~/.config/openclaw/env
ls -la ~/.config/openclaw/env  # confirmar -rw-------

# 2) Auditar otros files con secretos potenciales y permisos laxos
find ~/.config/ ~/.umbral/ ~/umbral-agent-stack/ \
  -type f \( -name "*.env*" -o -name "*secret*" -o -name "*credential*" -o -name "*token*" \) \
  -not -path "*/.git/*" \
  -exec ls -la {} \; 2>/dev/null

# 3) Buscar otros files world-readable con contenido sensible
find ~/.config/ -type f -perm /o+r 2>/dev/null | head -20

# 4) Inventario de qué hay que rotar (NO imprimir valores)
grep -E '^(GOOGLE_|OPENAI_|ANTHROPIC_|NOTION_|GROQ_|MISTRAL_|HF_|CO_)' \
  ~/.config/openclaw/env | sed -E 's/=.*/=<REDACTED>/' | sort

# 5) Verificar git status de cualquier path tracked accidentalmente
cd ~/umbral-agent-stack && git ls-files | xargs grep -l "GOOGLE_REFRESH_TOKEN\|client_secret\|api_key" 2>/dev/null | head
```

## Plan de rotación (decidir alcance con David antes de ejecutar)

Para cada credencial expuesta:

1. **Google OAuth (Calendar + Gmail):**
   - Ir a Google Cloud Console → APIs & Services → Credentials
   - Para cada OAuth 2.0 Client ID afectado: opción A (rotar `client_secret` y revocar refresh tokens existentes) vs opción B (crear cliente nuevo + invalidar viejo).
   - Re-emitir refresh tokens vía OAuth Playground (proceso documentado en `docs/35-google-calendar-token-setup.md` y `docs/35-gmail-token-setup.md`).
   - Actualizar `~/.config/openclaw/env`.
   - Restart `umbral-worker` y verificar tasks `google.calendar.list_events` y `gmail.list_drafts` siguen healthy.

2. **Google API keys (Gemini/Vertex/CSE):**
   - Cloud Console → APIs & Services → Credentials → API keys → regenerate.
   - Actualizar env, restart, smoke test.

3. **Notion / OpenAI / Anthropic / etc.** (si aplica):
   - Rotar en cada portal respectivo.
   - Actualizar env, restart, smoke test del servicio que usa cada uno.

## Criterios de aceptación

- [ ] `~/.config/openclaw/env` con permisos `600` confirmado por `ls -la`.
- [ ] Auditoría de otros archivos sensibles ejecutada y resultado en el log (paths con permisos laxos listados).
- [ ] Confirmar que NO hay secretos committeados en `~/umbral-agent-stack/` (output del CMD 5).
- [ ] Lista de credenciales que David debe rotar, priorizada por blast radius (OAuth refresh tokens primero, API keys después).
- [ ] Runbook actualizado o creado en `runbooks/` documentando el patrón "nuevos secretos → `chmod 600` antes de poblar".
- [ ] Status `done` solo después de chmod aplicado + auditoría completada. La rotación efectiva queda como sub-task aparte porque requiere acción manual de David en consolas externas.

## Antipatrones que esta tarea prohíbe

- ❌ Imprimir VALORES de los tokens en el log (solo nombres).
- ❌ Rotar credenciales sin avisar a David — puede romper integraciones en uso.
- ❌ Asumir "no hay evidencia de compromiso = no hace falta rotar". Permisos `644` en un file con refresh tokens es razón suficiente para rotar (defensa en profundidad).
- ❌ Hacer `chmod 600` y dar la task por terminada sin auditar otros paths.

## Log

- 2026-05-05 — `copilot-chat@notion-governance` — Tarea creada. Disparador: hallazgo colateral en task `2026-05-04-006` (diagnóstico O8b.0). Memoria del repo `notion-governance-lessons.md:11` también registra este hallazgo.
