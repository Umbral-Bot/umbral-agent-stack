---
id: "2026-03-22-001"
title: "Diagnóstico env Rick vs local — Codex define canónicos"
status: done
assigned_to: codex
created_by: cursor
priority: medium
sprint: R21
created_at: 2026-03-22T00:00:00-06:00
updated_at: 2026-03-22T00:00:00-06:00
---

## Objetivo

**Codex tiene más noción del estado actual** — ha hecho harto trabajo reciente (Notion, dashboard, auditorías, etc.). Esta tarea pide que Codex **defina los valores canónicos** para las variables de entorno y que Cursor sincronice su `.env` local hacia esos valores.

**Fuente de verdad:** El env de Rick (`~/.config/openclaw/env` en VPS) es producción. Si Codex trabajó con Rick y sabe qué IDs/keys son los correctos, esa es la referencia. Cursor actualizará su `.env` local para alinearse.

## Contexto

Cursor comparó `env.rick` (copia de Rick) con `.env` local y encontró diferencias. Cursor **no cambiará nada** hasta que Codex declare los canónicos.

### Diferencias detectadas

| Variable | Rick (VPS) | Local (Cursor) |
|----------|------------|----------------|
| NOTION_DASHBOARD_PAGE_ID | `3265f443-fb5c-816d-9ce8-c5d6cf075f9c` | `0fd13978-b220-498e-9465-b4fb2efc5f4a` |
| NOTION_TASKS_DB_ID | `afda99a3666e49f0a2f670cb228ac3ab` | `3145f443-fb5c-814a-8764-efbd7203048d` |
| GOOGLE_CSE_API_KEY_RICK_UMBRAL | `[REDACTED - rotate in Google]` | `[REDACTED - rotate in Google]` |
| GOOGLE_API_KEY_RICK_UMBRAL | `[REDACTED]` | `[REDACTED]` |

Docs históricos dicen Dashboard Rick = `0fd13978-b220-498e-9465-b4fb2efc5f4a`, pero si Codex/Rick usan otro en producción, ese es el canónico.

### Otras correcciones (Cursor las hará después)

- `.env` local: eliminar líneas 51-54 (comandos de shell que se colaron)
- `env.rick`: `GOOGLE_CSE_CX` duplicado (quitar el incorrecto)
- `env.rick`: redundancia `GOOGLE_API_KEY_RICK_UMBRAL_ALT`
- Agregar variables faltantes según lo que Codex indique

## Tareas para Codex

1. **Validar qué está operando hoy** — Con tu contexto reciente (R20-098, R18-094, dashboard, scripts), confirmá qué valores de NOTION_* y GOOGLE_* son los que Rick/producción usan de verdad.
2. **Definir canónicos** — Para cada variable en disputa, indicá cuál es el valor correcto (Rick suele ser la referencia).
3. **Escribir informe breve** en el `## Log` con:
   - Valores canónicos por variable (los que Cursor debe usar en `.env` local).
   - Si hay algo en `env.rick` que deba corregirse (duplicados, typos).
   - Variables que Cursor deba agregar a su `.env` para paridad con Rick.

## Criterios de aceptación

- [x] Codex validó el estado operativo actual y definió valores canónicos.
- [x] Informe en el Log con lista de variables canónicas y correcciones sugeridas.
- [x] Cursor podrá aplicar las correcciones en `.env` local y `env.rick` sin preguntar más.

## Log

### [cursor] 2026-03-22
Tarea creada. Codex tiene más contexto del estado reciente; define canónicos y Cursor sincroniza local hacia Rick.

### [codex] 2026-03-22
Diagnóstico basado en comparación directa entre `.env` y `env.rick`, más evidencia del repo y auditorías recientes.

**Valores canónicos (Cursor debe alinear .env local):**
- `NOTION_DASHBOARD_PAGE_ID` = `3265f443-fb5c-816d-9ce8-c5d6cf075f9c`
- `NOTION_TASKS_DB_ID` = `afda99a3666e49f0a2f670cb228ac3ab`
- Google: usar valores de env.rick (GOOGLE_CSE_API_KEY_RICK_UMBRAL, GOOGLE_API_KEY_RICK_UMBRAL, GOOGLE_CSE_CX = d6471a4b4be614b13)

**env.rick — correcciones:**
- Quitar GOOGLE_CSE_CX incorrecto (línea con AQ.Ab8RN6...; el correcto es d6471a4b4be614b13)
- Eliminar GOOGLE_API_KEY_RICK_UMBRAL_ALT (redundante)
- No tocar NOTION_SUPERVISOR_ALERT_PAGE_ID

**Nota:** web_discovery.py prioriza GOOGLE_CSE_API_KEY_RICK_UMBRAL_2 si existe.
