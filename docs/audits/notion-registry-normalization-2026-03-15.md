# Notion Registry Normalization — 2026-03-15

## Objetivo

Dejar el flujo de Notion legible y gobernado para:

- `Proyectos -> Tareas -> Entregables -> Revisión`
- nombres humanos en español para entregables y tareas visibles
- sin fechas incrustadas en los nombres
- con contenido útil en las subpáginas
- y con reglas para que Rick no vuelva a dejar páginas sueltas ni ruido operativo en la base principal.

## Cambios de código

### `worker/tasks/notion.py`

- `notion.upsert_deliverable`
  - normaliza nombres a lenguaje natural en español
  - elimina fechas del nombre visible
  - sugiere `Fecha limite sugerida`
  - crea o rellena cuerpo útil de la página
- `notion.upsert_project`
  - rellena cuerpo útil de los proyectos cuando están vacíos
- `notion.upsert_task`
  - prioriza `task_name` como nombre humano visible
  - mantiene `task` como identificador técnico en el contexto de la página
  - crea o rellena cuerpo útil de la página

### `worker/notion_client.py`

- `upsert_task(...)`
  - acepta `task_name`
  - usa `task_name` como título visible cuando existe
  - conserva relaciones a proyecto y entregable

### `dispatcher/service.py`

- `notion_upsert` dejó de contaminar la base de tareas con eventos genéricos del sistema.
- Solo se escribe automáticamente en Notion cuando la tarea está ligada a un proyecto/entregable o cuando el envelope marca `notion_track=true`.

### Skills y guardrails

Se endurecieron:

- `openclaw/workspace-templates/skills/notion/SKILL.md`
- `openclaw/workspace-templates/skills/notion-project-registry/SKILL.md`
- `openclaw/workspace-templates/AGENTS.md`
- `openclaw/workspace-templates/SOUL.md`

Reglas activas:

- entregables con nombre natural y sin fecha en el título
- usar `Fecha limite sugerida`
- evitar páginas sueltas en Control Room
- preferir `upsert_project` + `upsert_deliverable`
- las tareas visibles deben usar nombre humano cuando exista

## Normalización en Notion

### Bases activas

- `📁 Proyectos — Umbral`
- `🗂 Tareas — Umbral Agent Stack`
- `📬 Entregables Rick — Revisión`

### Estructura

- `Proyectos` quedó como registro canónico
- `Tareas` quedó ligada a `Proyecto` y `Entregable`
- `Entregables` quedó ligada a `Proyecto` y `Tareas origen`
- `OpenClaw` quedó como hub/dashboard
- `Archivo legacy — entregables sueltos` quedó como contenedor histórico

### Vistas útiles

- `Tareas / Recientes ligadas`
- `Tareas / Historial ligado`
- `Tareas / Sistema / automatizaciones`
- `Entregables / Activos y recientes`
- `Entregables / Pendientes de revisión`
- `Entregables / Archivo / histórico`

### Ajuste posterior de UX

Después de la primera pasada quedó una fricción real: la base `Tareas` parecía vacía porque la vista por defecto solo mostraba tareas activas o bloqueadas.

Se corrigió así:

- la vista por defecto pasó a `Recientes ligadas`
  - muestra tareas recientes relacionadas a proyecto o entregable, aunque ya estén `done`
- la vista operativa estricta quedó separada como `Activas / seguimiento`

Con eso la base ya no se percibe vacía al abrirla, pero sigue existiendo una vista específica para trabajo pendiente.

### Backfill real

Se corrigieron páginas que estaban vacías en:

- proyectos activos principales
- entregables importantes del embudo y mejora continua
- tareas de smoke ligadas al proyecto embudo

También se normalizaron nombres como:

- `Benchmark Ruben Hassid - sistema contenido y funnel`
  -> `Benchmark del sistema de contenido y funnel de Ruben Hassid`
- `Auditoria real - Mejora Continua Umbral Agent Stack - 2026-03-10`
  -> `Auditoría real del frente de mejora continua`

## Despliegue en VPS

Se copiaron a la VPS y al workspace vivo de Rick los archivos de Notion/gobernanza:

- `worker/tasks/notion.py`
- `worker/notion_client.py`
- `dispatcher/service.py`
- `openclaw/extensions/umbral-worker/index.ts`
- `AGENTS.md`
- `SOUL.md`
- `skills/notion/SKILL.md`
- `skills/notion-project-registry/SKILL.md`

Servicios/procesos actualizados:

- `umbral-worker.service`
- `openclaw-gateway.service`
- `python3 -m dispatcher.service`

## Validación

### Local

- `python -m pytest tests/test_notion_tasks_registry.py tests/test_notion_project_registry.py tests/test_notion_deliverables_registry.py tests/test_dispatcher_resilience.py -q`
  - `37 passed`
- `python scripts/validate_skills.py`
  - `OK`

### Smoke real en VPS

1. Se creó un entregable real vía worker:
   - nombre natural
   - icono heredado por proyecto
   - fecha límite sugerida
   - cuerpo útil
2. Se creó/actualizó una tarea real vía worker:
   - nombre humano visible
   - relación al proyecto
   - relación al entregable
   - cuerpo útil
3. El entregable smoke quedó archivado para no contaminar la vista activa.

## Estado final

### Resuelto

- entregables con nombres legibles en español
- sin fechas en el título
- columna `Fecha limite sugerida`
- tareas y proyectos ya no vacíos
- base de tareas mucho menos ruidosa
- flujo enlazado `Proyecto -> Tarea -> Entregable -> Revisión`
- Rick quedó guiado por guardrails y skills nuevas para seguir este mismo patrón

### Residuo conocido

- El icono nativo de la base `Tareas — Umbral Agent Stack` no quedó totalmente controlable por el mismo canal de API usado aquí.
- Se dejó resuelto visualmente con emoji en el título como fallback rápido para lectura humana.
- En subpáginas y filas, el icono sí quedó correcto y consistente.
