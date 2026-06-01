---
id: 2026-06-01-010-copilot-windows-o15-gmail-calendar-discovery
title: "D5.1 prep — Gmail/Calendar OAuth discovery (Copilot Windows read-only)"
status: done
assigned_to: copilot-windows
created_by: cursor
created: 2026-06-01
---

# D5.1 OAuth discovery (Windows)

## Objetivo

Inventario read-only de lo necesario para O15 canales Gmail + Calendar (`rick.asistente@gmail.com`, ADR-16). **No** ejecutar OAuth ni tocar VPS.

## Fuentes

- `notion-governance/docs/architecture/16-multichannel-rick-channels.md` (ADR-16)
- `notion-governance/docs/architecture/15-rick-organizational-model.md` §3.5
- `umbral-agent-stack/.agents/tasks/2026-03-23-001-*` (Calendar/Gmail VPS histórico)
- Repo: buscar `GMAIL`, `CALENDAR`, `google.oauth`, `rick.asistente`

## Entregables

1. Tabla: canal | estado repo | estado VPS (si conocido) | blocker | owner sugerido
2. Lista env vars / cred files esperados (nombres only, no secret values)
3. Gate recomendado para David (G-D5-oauth o similar)
4. Actualizar Log en esta task; no editar board (Cursor lo hace al cerrar)

## Boundaries

- NO SSH VPS
- NO pegar tokens
- NO crear OAuth clients sin autorización

## Prompt para Copilot Windows (pegar en hilo)

Ver `docs/ops/copilot-handoff-prompts.md` § Thread C.

## Log

### 2026-06-01 — Cursor

Task creada para hilo Copilot Windows paralelo.

### 2026-06-01 — Copilot Windows (read-only discovery)

Inventario read-only ejecutado en Windows + repo. **No** se ejecutó OAuth, **no** se tocó VPS, **no** se pegaron valores de secretos.

**Hallazgo de seguridad (STOP CONDITION secret-output-guard #5):** `grep` expuso valores reales de tokens Google en `umbral-agent-stack/.env` y `umbral-agent-stack/env.rick`. No se reprodujeron en ningún output. `.env` está cubierto por `.gitignore` (`.env`, `*.env`). **`env.rick` NO coincide con esos patrones** (`*.env` = termina en `.env`; `env.rick` termina en `.rick`) → posible archivo de secretos **trackeado**. Requiere verificación `git ls-files env.rick` antes de cualquier push. Marcado como RIESGO ALTO para David.

**Estado credenciales (Windows local):**
- `.env`: presentes `GOOGLE_CALENDAR_REFRESH_TOKEN` + `_CLIENT_ID` + `_CLIENT_SECRET`; `GOOGLE_GMAIL_REFRESH_TOKEN` + `_CLIENT_ID` + `_CLIENT_SECRET`; `GOOGLE_GMAIL_TOKEN` comentado.
- `env.rick`: presentes `GOOGLE_CALENDAR_*` (refresh token con valor **distinto** al de `.env` → drift / ambigüedad de cuál es canónico).
- `.env.example` documenta todos los nombres de variables (sección Google).

**Drift de scope ADR-16 vs setup docs:**
- ADR-16 §2.3 Gmail scope mínimo = `gmail.modify`; `docs/35-gmail-token-setup.md` usa `gmail.compose` + `gmail.readonly`.
- ADR-16 §2.4 Calendar scope mínimo = `calendar.events`; `docs/35-google-calendar-token-setup.md` usa `calendar` (full, prohibido por ADR).

**Notion guest:** ADR-16 §6 (2026-05-07) **canceló** la invitación guest de `rick.asistente@gmail.com`; D2 relajada a permanente para canal Notion → usa `NOTION_API_KEY` (integration bot "Rick"). El "Notion guest OAuth" ya **no** es gap de O15.

Veredicto técnico de discovery: **D51_OAUTH_DISCOVERY_OK** (inventario completo; ejecución OAuth pendiente de gate David).

## VEREDICTO

**D51_OAUTH_DISCOVERY_OK** — David eligió opción **b** (audit VPS G-D5.1 primero). Task 011 asignada Copilot-VPS.
