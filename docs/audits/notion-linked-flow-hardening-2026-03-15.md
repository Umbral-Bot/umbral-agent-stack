# Notion Linked Flow Hardening - 2026-03-15

## Objetivo

Cerrar la brecha entre la estructura diseñada para Notion y su operación real:

- `Proyecto -> Tarea -> Entregable -> Revisión`
- dashboard limpio y legible
- histórico suelto contenido en `Archivo legacy`

## Problema real

La reorganización previa había dejado bien resueltos `Proyectos` y `Entregables`, pero `Tareas` seguía aislada:

- sin relación a proyecto
- sin relación al entregable que producía
- sin visibilidad suficiente en las vistas

Además, el dashboard `OpenClaw` seguía mostrando títulos de bases con emojis incrustados y sin una leyenda clara del flujo.

## Cambios aplicados

### 1. Esquema de Notion

Se actualizó la base `Tareas — Umbral Agent Stack` para incluir:

- `Proyecto` (relation -> `Proyectos — Umbral`)
- `Entregable` (relation -> `Entregables Rick — Revisión`)

Y quedaron creadas las relaciones recíprocas:

- en `Proyectos — Umbral`: `Tareas`
- en `Entregables Rick — Revisión`: `Tareas origen`

### 2. Worker / Gateway

Se extendió `notion.upsert_task` para aceptar y persistir:

- `project_name`
- `project_page_id`
- `deliverable_name`
- `deliverable_page_id`

Archivos tocados:

- `worker/tasks/notion.py`
- `worker/notion_client.py`
- `openclaw/extensions/umbral-worker/index.ts`

### 3. Skills / contrato

Se actualizaron:

- `openclaw/workspace-templates/skills/notion/SKILL.md`
- `openclaw/workspace-templates/skills/notion-project-registry/SKILL.md`
- `docs/07-worker-api-contract.md`

Nueva regla operativa:

- si una tarea ya pertenece a un proyecto o produce un entregable revisable, no dejar la fila de `Tareas` flotando; enlazarla.

### 4. Limpieza visual y dashboard

Se normalizaron títulos visibles de bases en `OpenClaw`:

- `Proyectos — Umbral`
- `Tareas — Umbral Agent Stack`
- `Entregables Rick — Revisión`

Y se agregó una leyenda en `OpenClaw` para explicar:

- qué es `Proyectos`
- qué es `Tareas`
- qué es `Entregables`
- qué es `Archivo legacy`

### 5. Backfill útil

Se hizo backfill adicional desde `Archivo legacy` hacia `Entregables Rick — Revisión` para dos artefactos históricos importantes:

1. `Auditoria real - Mejora Continua Umbral Agent Stack - 2026-03-10`
2. `Shortlist inicial v1 - Sistema Automatizado de Búsqueda y Postulación Laboral`

Ambos quedaron archivados y ligados a sus proyectos.

## Validación

### Tests locales

- `python -m pytest tests/test_notion_tasks_registry.py tests/test_notion_project_registry.py tests/test_notion_deliverables_registry.py tests/test_notion_database_page.py tests/test_notion_report_page.py -q`
  - `22 passed`
- `python scripts/validate_skills.py`
  - OK

### Smoke real en VPS

Se desplegaron los cambios al stack vivo y se ejecutó un smoke real por Worker:

- `notion.upsert_task`
  - creó `Governance smoke - task linked to embudo deliverable`
  - enlazado a:
    - `Proyecto Embudo Ventas`
    - `Benchmark Ruben Hassid - sistema contenido y funnel`

Validación en Notion:

- la fila de `Tareas` muestra relación a `Proyecto` y `Entregable`
- el entregable `Benchmark Ruben Hassid - sistema contenido y funnel` recibió la relación recíproca en `Tareas origen`

## Estado final

El flujo queda finalmente visible y operativo así:

`Proyecto -> Tarea -> Entregable -> Revisión`

Y `OpenClaw` queda como dashboard legible, no como depósito de páginas sueltas.

## Límite residual

La parte visual de íconos top-level de bases sigue limitada por el tooling actual:

- páginas y filas: icono real OK
- bases de datos/data sources: título ya quedó limpio, pero el icono real de database no quedó automatizado desde este stack

No bloquea el flujo ni la gobernanza; solo queda como deuda de UX menor.
