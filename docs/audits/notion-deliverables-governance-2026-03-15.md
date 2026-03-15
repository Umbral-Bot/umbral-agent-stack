# Notion Deliverables Governance - 2026-03-15

## Objetivo

Reducir el desorden de paginas sueltas en `Control Room` / `OpenClaw` y dejar una estructura simple:

- `📁 Proyectos — Umbral` para estado canonico por proyecto
- `📬 Entregables Rick — Revision` para outputs revisables por David
- `🗂 Tareas — Umbral Agent Stack` para ejecucion fina
- `Control Room` / `OpenClaw` como dashboard y punto de coordinacion, no deposito de paginas sueltas

## Implementacion en repo

Se agrego soporte tipado para entregables revisables:

- `worker/config.py`
  - `NOTION_DELIVERABLES_DB_ID`
- `worker/tasks/notion.py`
  - `_lookup_project_page_id`
  - `_build_deliverable_properties`
  - `handle_notion_upsert_deliverable`
- `worker/tasks/__init__.py`
  - registra `notion.upsert_deliverable`
- `openclaw/extensions/umbral-worker/index.ts`
  - registra `umbral_notion_upsert_deliverable`

## Reglas y docs actualizadas

- `openclaw/workspace-templates/AGENTS.md`
  - proyecto activo + output revisable => `upsert_project` + `upsert_deliverable`
- `openclaw/workspace-templates/SOUL.md`
  - `Control Room` solo para coordinacion transversal
- `openclaw/workspace-templates/skills/notion-project-registry/SKILL.md`
  - aclara que outputs revisables no van como paginas sueltas
- `docs/07-worker-api-contract.md`
  - agrega `notion.upsert_deliverable`
- `docs/22-notion-dashboard-gerencial.md`
  - aclara que `Control Room` no debe ser deposito de paginas sueltas
- `docs/30-linear-notion-architecture.md`
  - incorpora la base de entregables al modelo

## Tests

Validados localmente:

- `python -m pytest tests/test_notion_project_registry.py tests/test_notion_deliverables_registry.py tests/test_notion_report_page.py -q`
  - `12 passed`
- `python scripts/validate_skills.py`
  - OK

Checks adicionales:

- import local de `worker.tasks` expone `notion.upsert_deliverable`
- `health` del worker en VPS reporta `notion.upsert_deliverable` en `tasks_registered`

## Notion real creado

Base creada bajo `OpenClaw`:

- Database: `📬 Entregables Rick — Revision`
- URL: `https://www.notion.so/dd8c27d75c6a462db0920ef16f9720c6`
- Data source: `collection://82493dd7-4ed2-4cd1-9d0b-9572bcffe417`

Views creadas:

- `Pendientes de revision`
- `Revision`

Relaciones:

- propiedad `Proyecto` relacionada a `📁 Proyectos — Umbral`

## Deploy real en VPS

Se desplego el subconjunto minimo a `/home/rick/umbral-agent-stack`:

- `worker/config.py`
- `worker/tasks/notion.py`
- `worker/tasks/__init__.py`
- `openclaw/extensions/umbral-worker/index.ts`
- `openclaw/workspace-templates/AGENTS.md`
- `openclaw/workspace-templates/SOUL.md`
- `openclaw/workspace-templates/skills/notion-project-registry/SKILL.md`

Tambien se actualizo:

- `~/.config/openclaw/env`
  - `NOTION_DELIVERABLES_DB_ID=dd8c27d75c6a462db0920ef16f9720c6`

## Incidente detectado y corregido

Al reiniciar `umbral-worker.service`, el worker de la VPS quedo roto por un problema previo del worktree remoto:

- `worker/tasks/__init__.py` importaba `handle_gui_list_windows`
- el `worker/tasks/gui.py` remoto no exponia esos handlers

Accion correctiva:

- backup remoto del archivo
- sincronizacion de `worker/tasks/gui.py` desde este repo
- restart de `umbral-worker.service`

Resultado:

- `http://127.0.0.1:8088/health` vuelve a responder
- el worker queda funcional otra vez

## Smoke real

Se creo por Worker en VPS un deliverable de smoke:

- `Smoke deliverable routing 2026-03-15`

Luego se actualizo a:

- `Estado revision = Archivado`

Objetivo:

- validar handler
- validar DB
- validar relacion a proyecto
- no dejar ruido en la cola real

## Backfill inicial

Se cargaron 3 entregables recientes y utiles para `Proyecto Embudo Ventas`:

1. `Benchmark Ruben Hassid - sistema contenido y funnel`
2. `Framing tipo Veritasium aplicado al embudo`
3. `Cierre critico del Proyecto Embudo Ventas`

Con esto la base no nace vacia y ya refleja outputs reales que David puede revisar.

## Estado final

Queda operativo este flujo:

`Proyecto -> Tareas -> Entregable -> Revision -> nuevas tareas o avance del proyecto`

Y `OpenClaw` / `Control Room` ya muestra la base de entregables como recurso estructurado, en vez de seguir acumulando paginas sueltas como unica salida.
