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

### 4d. Actualizar propiedades o archivar una pagina

Task: `notion.update_page_properties`

```json
{
  "page_id_or_url": "https://www.notion.so/... o UUID",
  "properties": {"Estado": {"status": {"name": "En curso"}}},
  "icon": "📝",
  "archived": false
}
```

Devuelve: `{"page_id":"...", "url":"...", "updated": true}`.

Usa `archived=true` para retirar una pagina suelta que ya fue regularizada en otro contenedor canónico. No archives una pagina project-scoped sin antes dejar el proyecto y el entregable correctos.

### 5. Crear o actualizar tarea en DB

Task: `notion.upsert_task`

```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "running",
  "team": "marketing",
  "task": "research.web",
  "project_name": "Proyecto Embudo Ventas",
  "deliverable_name": "Benchmark Ruben Hassid - sistema contenido y funnel",
  "input_summary": "query=...",
  "result_summary": "..."
}
```

Devuelve: `{"page_id":"...", "updated": true}` o `{"skipped": true, "reason":"..."}`

Si la tarea pertenece claramente a un proyecto o produce/actualiza un entregable revisable, usa `project_name` / `project_page_id` y `deliverable_name` / `deliverable_page_id` para enlazar la fila. No dejes `Tareas` flotando sin contexto si ya conoces el proyecto o el entregable.
Si el caso queda realmente cerrado, no marques la tarea como `done` hasta que la fila tenga `Proyecto` y `Entregable` correctos.
Si la tarea nace sin proyecto ni entregable, asume que es ruido operativo o sistema y evita mandarla a Notion salvo que David haya pedido explícitamente trazabilidad o marques `notion_track=true`.

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
  "icon": "📝",
  "sources": [{"title": "Fuente", "url": "https://..."}],
  "metadata": {"team": "advisory"}
}
```

Devuelve: `{"page_id":"...", "page_url":"...", "ok": true}`

Usala para:
- coordinación transversal
- alertas
- borradores temporales fuera del flujo de proyecto

No usarla como artefacto final de un benchmark, reporte o referencia externa que ya pertenece a un proyecto activo. En ese caso el cierre correcto es `notion.upsert_deliverable`.

### 8. Crear o actualizar proyecto en registry

Task: `notion.upsert_project`

Requiere `NOTION_PROJECTS_DB_ID` configurado en el Worker.

```json
{
  "name": "Proyecto Embudo Ventas",
  "estado": "Activo",
  "icon": "📁",
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

### 9. Crear o actualizar entregable revisable

Task: `notion.upsert_deliverable`

```json
{
  "name": "Benchmark de Ruben Hassid para el sistema editorial",
  "project_name": "Proyecto Embudo Ventas",
  "deliverable_type": "Benchmark",
  "review_status": "Pendiente revision",
  "date": "2026-03-15",
  "suggested_due_date": "2026-03-18",
  "agent": "Rick",
  "summary": "Resumen corto y legible para David.",
  "artifact_path": "G:\\Mi unidad\\Rick-David\\Proyecto-Embudo-Ventas\\benchmark-ruben-hassid.md",
  "next_action": "Revisar si se traduce a sistema editorial reusable.",
  "icon": "🎯"
}
```

Reglas:
- El `name` debe quedar en español natural y legible para David.
- No poner fechas dentro del título; usar `date` y `suggested_due_date`.
- Si el entregable pertenece a un proyecto, usar el icono del proyecto salvo que haya una razón clara para diferenciarlo.
- El cuerpo de la página debe quedar con resumen, contexto y siguiente acción. No dejar páginas vacías.
- Si el entregable nace desde una tarea o follow-up, pasar `source_task_id` y no considerar el caso cerrado hasta que el entregable tenga `Proyecto` y `Tareas origen` o `Task ID origen` coherente.

## Regla de iconos

- Si la task acepta `icon`, usar ese campo y no meter el emoji dentro del `title` o `name`.
- Reservar emoji en el texto solo cuando el icono no pueda configurarse por API.
- Para filas/paginas ligadas a un proyecto, preferir el icono del proyecto como icono real.
- Si no hay proyecto, inferir un icono por contenido/tipo antes de dejar la pagina sin icono.
- En bases de datos top-level de Notion, mantener emoji en el titulo como fallback visual porque el icono de database no siempre queda gobernable por esta API.

## Regla de títulos y contenido

- Los títulos de entregables deben ser descriptivos, en español natural y sin fecha incrustada.
- Las fechas van en columnas (`Fecha`, `Fecha limite sugerida`) y no en el nombre.
- `Proyectos`, `Tareas` y `Entregables` deben dejar cuerpo útil dentro de la página; no crear filas que al abrirse queden en blanco.

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
