---
id: "2026-03-22-001"
title: "Diagnóstico env Rick vs local — coordinación con Cursor"
status: assigned
assigned_to: codex
created_by: cursor
priority: medium
sprint: R21
created_at: 2026-03-22T00:00:00-06:00
updated_at: 2026-03-22T00:00:00-06:00
---

## Objetivo

Hacer un diagnóstico y análisis de las diferencias entre el env de Rick (`~/.config/openclaw/env` en VPS) y el `.env` local de Cursor, y **determinar si Codex introdujo algún cambio** en variables de Notion u otras durante sus tareas previas (R20-098, R18-094, etc.), para que Cursor y Codex coordinen antes de aplicar correcciones.

## Contexto

Cursor comparó `env.rick` (copia de Rick) con `.env` local y encontró diferencias en varias variables. **No debe cambiarse nada** hasta que Codex confirme si él hizo modificaciones intencionales.

### Diferencias detectadas (punto 4 — NO tocar hasta coordinación)

| Variable | Rick (VPS) | Local (Cursor) |
|----------|------------|----------------|
| NOTION_DASHBOARD_PAGE_ID | `3265f443-fb5c-816d-9ce8-c5d6cf075f9c` | `0fd13978-b220-498e-9465-b4fb2efc5f4a` |
| NOTION_TASKS_DB_ID | `afda99a3666e49f0a2f670cb228ac3ab` | `3145f443-fb5c-814a-8764-efbd7203048d` |
| GOOGLE_CSE_API_KEY_RICK_UMBRAL | `AIzaSyDJzcEoepEL9CEkXI5zYgd9T6mj_Vz0Fsw` | `AIzaSyBWDev_CloKq0L6zKcqySJBHKEjMp4aUNY` |
| GOOGLE_API_KEY_RICK_UMBRAL | `...Mmbg` (sin s) | `...Mmbgs` (con s) |

Según docs, el Dashboard Rick canónico es `0fd13978-b220-498e-9465-b4fb2efc5f4a`.

### Otras correcciones pendientes (Cursor las hará después de este diagnóstico)

- `.env` local: eliminar líneas 51-54 (comandos de shell que se colaron)
- `env.rick`: `GOOGLE_CSE_CX` duplicado con valores distintos (quitar el incorrecto)
- `env.rick`: redundancia `GOOGLE_API_KEY_RICK_UMBRAL_ALT`
- Agregar variables faltantes en cada lado según diagnóstico

## Tareas para Codex

1. **Revisar tus tareas previas** (R20-098 auditoría Notion, R18-094 dashboard Notion, otras que hayan tocado .env o plantillas de entorno).
2. **Confirmar si Codex modificó** valores de NOTION_DASHBOARD_PAGE_ID, NOTION_TASKS_DB_ID, o cualquier otra variable de Notion/Google en el repo, en .env.example, en docs o en scripts de setup.
3. **Investigar en el historial de Git** si hay commits que cambiaron esos IDs (ej. en `setup_notion_tasks_db.py`, `create_dashboard_page.py`, docs de Notion, etc.).
4. **Escribir un informe breve** en el `## Log` de esta tarea con:
   - Qué cambió Codex (si algo) y por qué.
   - Cuál de los dos valores (Rick vs local) debería ser el canónico para NOTION_DASHBOARD_PAGE_ID y NOTION_TASKS_DB_ID.
   - Recomendación: ¿unificar ambos env hacia los valores correctos, o hay razón para mantener diferencias?

## Criterios de aceptación

- [ ] Codex revisó sus tareas previas y el historial del repo.
- [ ] Informe en el Log indicando si Codex hizo cambios y cuáles son los valores canónicos.
- [ ] Recomendación clara para que Cursor aplique las correcciones del resto de puntos de forma coordinada.

## Log

### [cursor] 2026-03-22
Tarea creada. Contexto: comparación env.rick vs .env local; diferencias en Notion/Google. Punto 4 (valores distintos) se deja en espera hasta diagnóstico de Codex.
