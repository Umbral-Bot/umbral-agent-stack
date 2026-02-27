# 27 — Kanban de tareas en Notion

## Resumen

Base de datos "Tareas Umbral" en Notion con vista Kanban para seguir en qué trabaja cada agente.

**Propiedades:**
- Tarea (title)
- Estado: En cola, En curso, Hecho, Bloqueado, Fallido
- Agente: marketing, advisory, improvement, system, lab
- Task ID, Actualizada, Creada, Resumen

**Actualización:** El Dispatcher llama a `notion.upsert_task` en cada transición (running → done/failed/blocked).

## Setup

### 1. Crear la base de datos

```bash
cd ~/umbral-agent-stack && source .venv/bin/activate
export NOTION_API_KEY=...
export NOTION_TASKS_PARENT_PAGE_ID=...   # o NOTION_DASHBOARD_PAGE_ID
python scripts/setup_notion_tasks_db.py
```

### 2. Añadir NOTION_TASKS_DB_ID al env

El script imprime el ID. Añadirlo a `~/.config/openclaw/env`:

```
NOTION_TASKS_DB_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### 3. Dar acceso a la integración

La integración de Notion debe tener acceso a la página padre (Dashboard o Control Room) para crear la DB. Ver [Notion integrations](https://www.notion.so/my-integrations).

### 4. Vista Kanban en Notion

En la DB creada: + Nueva vista → Board → agrupar por "Estado".

## Enlace en otra página

Para añadir un enlace al Kanban en una página (ej. Dashboard):

```bash
export TARGET_PAGE_ID=xxx   # o usa NOTION_DASHBOARD_PAGE_ID del env
python scripts/link_kanban_to_page.py
```

Sin `TARGET_PAGE_ID`, usa `NOTION_DASHBOARD_PAGE_ID`. La página debe estar compartida con la integración de Notion.

## Uso

Sin `NOTION_TASKS_DB_ID`, el Dispatcher sigue funcionando; `notion.upsert_task` devuelve `skipped`.

Con la DB configurada, cada tarea encolada y procesada aparece en el Kanban.
