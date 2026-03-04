---
name: notion
description: >-
  Interact with Notion via Umbral Worker tasks for transcripts, comments,
  Control Room polling, Kanban task updates, dashboard updates, and report pages.
  Use when "write to notion", "notion comment", "poll notion comments",
  "update dashboard", "create report page", "sync task status to notion".
metadata:
  openclaw:
    emoji: "\U0001F4DD"
    requires:
      env:
        - NOTION_API_KEY
---

# Notion Skill

Rick puede operar Notion usando la familia de tasks `notion.*` del Worker.

## Requisitos

- `NOTION_API_KEY`: token de integracion de Notion.
- Variables de entorno recomendadas en el Worker:
  - `NOTION_CONTROL_ROOM_PAGE_ID`
  - `NOTION_GRANOLA_DB_ID`
  - `NOTION_DASHBOARD_PAGE_ID` (si aplica)

## Tasks disponibles

### 1. Escribir transcript

Task: `notion.write_transcript`

```json
{
  "title": "Llamada con cliente",
  "content": "Resumen de transcript...",
  "source": "granola",
  "date": "2026-03-04"
}
```

Devuelve: `{"page_id":"...", "url":"..."}`

### 2. Agregar comentario

Task: `notion.add_comment`

```json
{
  "text": "Rick: avance completado",
  "page_id": "optional-control-room-page-id"
}
```

Devuelve: `{"comment_id":"..."}`

### 3. Leer comentarios recientes

Task: `notion.poll_comments`

```json
{
  "page_id": "optional-control-room-page-id",
  "since": "2026-03-04T00:00:00Z",
  "limit": 20
}
```

Devuelve: `{"comments":[...], "count": N}`

### 4. Crear o actualizar tarea en DB

Task: `notion.upsert_task`

```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "running",
  "team": "marketing",
  "task": "research.web",
  "input_summary": "query=...",
  "result_summary": "..."
}
```

Devuelve: `{"page_id":"...", "updated": true}` o `{"skipped": true, "reason":"..."}`

### 5. Actualizar dashboard

Task: `notion.update_dashboard`

```json
{
  "metrics": {
    "Redis pending": "4",
    "Worker health": "ok"
  },
  "page_id": "optional-dashboard-page-id"
}
```

Devuelve: `{"updated": true, "blocks_appended": N}`

### 6. Crear pagina de reporte

Task: `notion.create_report_page`

```json
{
  "title": "Reporte semanal",
  "content": "# Resumen\nHallazgos...",
  "parent_page_id": "optional-parent-id",
  "sources": [{"title": "Fuente", "url": "https://..."}],
  "metadata": {"team": "advisory"}
}
```

Devuelve: `{"page_id":"...", "page_url":"...", "ok": true}`

## Triggers recomendados

- "write to notion"
- "notion comment"
- "poll notion comments"
- "update dashboard"
- "create report"

## Referencias

- `worker/tasks/notion.py`
- `worker/notion_client.py`

## Notas

- Estas tasks se encolan via Dispatcher/Redis y las ejecuta el Worker.
- Si faltan credenciales de Notion, las tasks pueden devolver error de configuracion.
