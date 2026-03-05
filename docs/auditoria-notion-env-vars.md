# Auditoria de Variables Notion (R20-098)

Fecha: 2026-03-07  
Scope: inventario de variables `NOTION_*` en runtime, scripts operativos, plantillas de entorno y docs del repo.

## Metodologia

- Busqueda en `worker/`, `dispatcher/`, `scripts/`, `docs/`, `README.md`, `.env.example`, `openclaw/env.template`.
- Se consideraron variables reales cuando aparecen como:
  - `os.environ.get("NOTION_...")` en Python.
  - `${NOTION_...}` en scripts shell.
  - `NOTION_...=` en plantillas de entorno.

## Inventario (variables reales)

| Variable | Tipo | Rol | Donde se usa (archivos clave) | Funcionalidad |
|---|---|---|---|---|
| `NOTION_API_KEY` | key | Rick | `worker/config.py`, `worker/notion_client.py`, `scripts/vps/dashboard-cron.sh`, `scripts/vps/supervisor.sh`, scripts utilitarios (`setup_notion_tasks_db.py`, `link_kanban_to_page.py`, etc.) | Token principal de integracion Notion para Worker/cron/scripts (comentarios, polling, dashboard, reportes, DB ops). |
| `NOTION_CONTROL_ROOM_PAGE_ID` | page_id | Rick | `worker/config.py`, `worker/notion_client.py`, `worker/tasks/notion.py`, `dispatcher/service.py`, `scripts/check_notion_comments_raw.py`, `scripts/vps/supervisor.sh` (fallback) | Pagina Control Room por defecto para `notion.add_comment`, `notion.poll_comments`, `create_report_page` y alertas del Dispatcher. |
| `NOTION_DASHBOARD_PAGE_ID` | page_id | Rick | `worker/config.py`, `worker/notion_client.py`, `scripts/dashboard_report_vps.py`, `scripts/vps/dashboard-cron.sh`, scripts de dashboard/kanban | Destino de `notion.update_dashboard` y herramientas de mantenimiento del dashboard. |
| `NOTION_GRANOLA_DB_ID` | db_id | Rick (opcional) | `worker/config.py`, `worker/notion_client.py` (`create_transcript_page`), `scripts/verify_stack_vps.py` | DB de transcripciones Granola. Requerida solo para pipeline Granola. |
| `NOTION_TASKS_DB_ID` | db_id | Rick (opcional) | `worker/config.py`, `worker/notion_client.py` (`upsert_task`), scripts de setup/kanban (`setup_notion_tasks_db.py`, `create_dashboard_page.py`, `link_kanban_to_page.py`) | DB Kanban de tareas (`notion.upsert_task`). Si falta, el Worker hace `skipped` en esa funcionalidad. |
| `NOTION_SUPERVISOR_API_KEY` | key | Supervisor (opcional) | `scripts/vps/supervisor.sh`, `docs/62-operational-runbook.md` | Token de integracion Notion "Supervisor" para post directo a Notion (identidad separada de Rick). |
| `NOTION_SUPERVISOR_ALERT_PAGE_ID` | page_id | Supervisor (opcional) | `scripts/vps/supervisor.sh`, `docs/62-operational-runbook.md`, `docs/rick-estado-y-capacidades.md` | Pagina destino de alertas del supervisor. Si no esta, fallback a Control Room via Worker. |
| `NOTION_BITACORA_DB_ID` | db_id | Otro (scripts offline) | `scripts/add_resumen_amigable.py`, `scripts/enrich_bitacora_pages.py`, `docs/bitacora-scripts.md` | DB de Bitacora para scripts manuales de enriquecimiento/resumen. |
| `NOTION_TASKS_PARENT_PAGE_ID` | page_id | Otro (setup) | `scripts/setup_notion_tasks_db.py`, `scripts/get_db_parent.py`, `docs/27-notion-kanban-tracking.md` | Pagina padre para crear DB de tareas (bootstrap). |
| `NOTION_MAIN_DB_ID` | db_id | Otro (legacy/setup) | `scripts/create_dashboard_page.py` | Fallback historico para definir parent database al crear pagina dashboard. |
| `NOTION_API_KEY_RICK` | key | Legacy | `.env.example`, `docs/36-rick-embudo-capabilities.md` | Duplicado documental. No hay lectura en runtime. |
| `NOTION_API_VERSION` | config | Rick | `worker/config.py`, `worker/notion_client.py`, scripts utilitarios Notion | Version de API Notion (no es key/page/db). |
| `NOTION_POLL_AT_MINUTE` | config | Rick | `dispatcher/notion_poller.py`, `README.md` | Configura minuto del poller cuando no se usa modo intervalo. |
| `NOTION_POLL_INTERVAL_SEC` | config | Rick | `dispatcher/notion_poller.py`, `README.md` | Configura polling continuo cada N segundos. |

## Hallazgos

1. La identidad principal activa es `NOTION_API_KEY` (Rick) para casi todo el runtime Notion.
2. El par `NOTION_SUPERVISOR_API_KEY` + `NOTION_SUPERVISOR_ALERT_PAGE_ID` ya habilita identidad separada para alertas operativas del supervisor.
3. `NOTION_API_KEY_RICK` esta en `.env.example` y docs, pero no se usa en codigo.
4. Hay variables de scripts puntuales (`NOTION_BITACORA_DB_ID`, `NOTION_TASKS_PARENT_PAGE_ID`, `NOTION_MAIN_DB_ID`) que no son parte del core diario del stack.

## Variables mencionadas en docs pero no activas como env runtime

- `NOTION_TOKEN` (auditoria historica VM; legacy).
- `NOTION_DASHBOARD` (referencia textual/abreviada en docs, no variable declarada).
- `NOTION_DATABASE_ID` y `NOTION_USER_ID` aparecen por substring en nombres como `GRANOLA_NOTION_DATABASE_ID` o `ENLACE_NOTION_USER_ID`, no como variables reales `NOTION_*` activas del runtime actual.

## Recomendacion de Simplificacion (Rick + Supervisor)

### 1) Base minima Rick (core)

Mantener como contrato principal:

- `NOTION_API_KEY`
- `NOTION_CONTROL_ROOM_PAGE_ID`
- `NOTION_DASHBOARD_PAGE_ID`

Opcionales por funcionalidad:

- `NOTION_GRANOLA_DB_ID` (solo si se usa pipeline Granola).
- `NOTION_TASKS_DB_ID` (solo si se usa Kanban/upsert).
- `NOTION_API_VERSION` (si no se define, usar default actual).
- `NOTION_POLL_AT_MINUTE` / `NOTION_POLL_INTERVAL_SEC` (solo configuracion de frecuencia).

### 2) Identidad Supervisor (operacional)

Para separar avisos operativos de la conversacion en Control Room:

- `NOTION_SUPERVISOR_API_KEY`
- `NOTION_SUPERVISOR_ALERT_PAGE_ID`

Si faltan, el comportamiento actual hace fallback via Worker (identidad Rick).

### 3) Deprecar/aislar legacy

- Deprecar `NOTION_API_KEY_RICK` del contrato activo (duplicada).
- Mantener `NOTION_BITACORA_DB_ID`, `NOTION_TASKS_PARENT_PAGE_ID`, `NOTION_MAIN_DB_ID` como variables de scripts de mantenimiento/bootstrap, no como requeridas del runtime core.

## Matriz objetivo propuesta

| Identidad | Variables |
|---|---|
| Rick (core) | `NOTION_API_KEY`, `NOTION_CONTROL_ROOM_PAGE_ID`, `NOTION_DASHBOARD_PAGE_ID` |
| Rick (opcionales por modulo) | `NOTION_GRANOLA_DB_ID`, `NOTION_TASKS_DB_ID`, `NOTION_API_VERSION`, `NOTION_POLL_AT_MINUTE`, `NOTION_POLL_INTERVAL_SEC` |
| Supervisor | `NOTION_SUPERVISOR_API_KEY`, `NOTION_SUPERVISOR_ALERT_PAGE_ID` |
| Legacy/script-only | `NOTION_API_KEY_RICK`, `NOTION_BITACORA_DB_ID`, `NOTION_TASKS_PARENT_PAGE_ID`, `NOTION_MAIN_DB_ID` |
