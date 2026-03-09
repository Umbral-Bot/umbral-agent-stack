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
  - `NOTION_GRANOLA_DB_ID` (solo pipeline Granola; usa la misma `NOTION_API_KEY` Rick)
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

### 4. Leer una página

Task: `notion.read_page`

```json
{
  "page_id_or_url": "https://www.notion.so/... o UUID",
  "max_blocks": 30
}
```

Devuelve: `{"page_id":"...", "title":"...", "blocks":[...], "plain_text":"..."}`.

Úsalo cuando David te pida estudiar una página concreta de Notion y necesites citar o resumir su contenido antes de actuar.

### 4b. Leer una base de datos

Task: `notion.read_database`

```json
{
  "database_id_or_url": "https://www.notion.so/... o UUID",
  "max_items": 30
}
```

Devuelve: `{"database_id":"...", "title":"...", "schema":{"Prop":"type"}, "items":[...]}`.

Úsalo cuando David te pase una base de datos de Notion con filas/entries y necesites:
- listar fuentes o referentes,
- inspeccionar columnas,
- leer el inventario base antes de diseñar automatizaciones o curación.

### 4c. Buscar bases de datos por título

Task: `notion.search_databases`

```json
{
  "query": "Fuentes confiables",
  "max_results": 5
}
```

Devuelve: `{"query":"...", "results":[{"database_id":"...", "title":"...", "url":"..."}], "count": N}`.

Úsalo cuando una página de Notion contenga un `child_database` y necesites resolver cuál es la base real antes de leerla con `notion.read_database`.

### 5. Crear o actualizar tarea en DB

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

### 6. Actualizar dashboard

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

### 7. Crear pagina de reporte

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

### 8. Crear o actualizar proyecto en registry

Task: `notion.upsert_project`

Requiere `NOTION_PROJECTS_DB_ID` configurado en el Worker.

```json
{
  "name": "Proyecto Embudo Ventas",
  "estado": "Activo",
  "linear_project_url": "https://linear.app/umbral/project/...",
  "shared_path": "G:\\Mi unidad\\Rick-David\\Proyecto-Embudo-Ventas\\",
  "responsable": "David Moreira",
  "agentes": "Rick,Claude",
  "sprint": "R21",
  "open_issues": 7,
  "next_action": "Completar arquitectura web v1 (UMB-32)"
}
```

Devuelve: `{"ok": true, "page_id": "...", "url": "...", "created": bool}`

- `created: true` → se creó una nueva entrada.
- `created: false` → se actualizó la entrada existente (busca por nombre exacto).

Variables opcionales: `start_date`, `target_date` (YYYY-MM-DD), `bloqueos`, `last_update_date`.

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
