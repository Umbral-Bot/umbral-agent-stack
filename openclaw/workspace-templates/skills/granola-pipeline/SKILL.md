---
name: granola-pipeline
description: >-
  Process Granola meeting notes or transcripts into Notion raw intake, review
  them through the V1 `session_capitalizable` layer, extract action items, and
  create proactive follow-ups. Use when "subir transcripcion",
  "procesar granola", "reunion terminada", "compromisos reunion", or
  "propuesta de seguimiento".
metadata:
  openclaw:
    emoji: "\U0001F399"
    requires:
      env:
        - NOTION_API_KEY
        - NOTION_GRANOLA_DB_ID
---

# Granola Pipeline Skill

Rick puede procesar notas o transcripciones de Granola y generar follow-ups proactivos usando las tasks `granola.*` del Worker.

## Estado vigente

- El flujo V1 vigente es `raw -> session_capitalizable -> capitalization`.
- El repo conserva `curated` en algunos nombres de env vars, tasks y docs por compatibilidad.
- En esta skill, `curated` se lee solo como alias legacy de `session_capitalizable`, no como capa paralela activa.

## Regla principal

Esta skill trabaja primero sobre la capa raw y luego sobre el paso controlado hacia `session_capitalizable`.

No asumas que:

- todo item raw debe promoverse
- toda reunion debe convertirse en proyecto o tarea
- Granola siempre trae transcript de audio
- el alias `curated` implica una capa distinta a `session_capitalizable`

La arquitectura vigente es:

1. **Raw**: DB `NOTION_GRANOLA_DB_ID`
2. **`session_capitalizable`**: binding V1 hacia `Registro de Sesiones y Transcripciones`, hoy resuelto desde `NOTION_CURATED_SESSIONS_DB_ID`
3. **Capitalization targets**: proyectos, tareas, entregables, bridge items y follow-ups solo cuando el payload y el contrato lo permiten

## Requisitos

- `NOTION_API_KEY`: token de integracion Notion Rick.
- `NOTION_GRANOLA_DB_ID`: ID de la DB raw de Granola.
- `NOTION_TASKS_DB_ID` (opcional): superficie operativa de tareas del stack.
- `NOTION_CURATED_SESSIONS_DB_ID` (opcional): nombre legacy del binding actual hacia la capa V1 `session_capitalizable`.
- `NOTION_HUMAN_TASKS_DB_ID` (opcional): DB humana de tareas usada desde un registro `session_capitalizable`.
- `NOTION_COMMERCIAL_PROJECTS_DB_ID` (opcional): DB comercial usada desde un registro `session_capitalizable`.
- Watcher corriendo en la VM (`scripts/vm/granola_watcher.py`) o flujo manual hacia `.md`.

## Tasks disponibles

### 1. Procesar intake raw

Task: `granola.process_transcript`

Pipeline raw completo:

1. crea pagina raw en Notion
2. extrae action items
3. opcionalmente crea tareas del stack cuando el handler lo soporta
4. notifica a Enlace

### 2. Crear follow-up

Task: `granola.create_followup`

### 3. Evaluar capitalizacion de raw ya ingresado

Task: `granola.capitalize_raw`

Usar esta task sabiendo que:

- en V1, `raw -> canonical target` viene bloqueado por defecto
- si no se habilita `allow_legacy_raw_to_canonical=true`, el handler deja comentario de revision y redirige hacia `session_capitalizable`
- el escape hatch legacy existe solo para casos repo-side explicitos y con destinos exactos

### 4. Promover a `session_capitalizable` (nombre de task legacy)

Task: `granola.promote_curated_session`

Usar esta task solo cuando:

- la pagina raw ya existe
- la superficie V1 fue compartida con Rick
- `NOTION_CURATED_SESSIONS_DB_ID` ya esta configurado
- quieres crear o actualizar un registro `session_capitalizable` con trazabilidad

Esta task:

- inspecciona el schema vivo de la superficie V1
- crea o actualiza por titulo exacto
- solo crea relaciones si recibe `page_id` explicitos
- no reemplaza la derivacion posterior hacia tareas o proyectos humanos

### 5. Crear tarea humana desde `session_capitalizable` (nombre de task legacy)

Task: `granola.create_human_task_from_curated_session`

Usar esta task solo cuando:

- el registro `session_capitalizable` ya existe
- `NOTION_HUMAN_TASKS_DB_ID` ya esta configurado
- quieres registrar una tarea humana explicita y trazable

Esta task:

- exige `task_name` explicito
- inspecciona el schema vivo de la DB humana de tareas
- crea o actualiza por titulo exacto
- hereda `Proyecto` desde el registro `session_capitalizable` cuando existe
- enlaza `Sesion relacionada`

### 6. Actualizar proyecto comercial desde `session_capitalizable` (nombre de task legacy)

Task: `granola.update_commercial_project_from_curated_session`

Usar esta task solo cuando:

- el registro `session_capitalizable` ya existe
- el proyecto comercial humano ya esta identificado
- `NOTION_COMMERCIAL_PROJECTS_DB_ID` ya esta configurado
- el cambio comercial cabe en campos explicitos del proyecto

Esta task:

- usa `project_page_id` explicito o la relacion `Proyecto` heredada desde `session_capitalizable`
- actualiza solo campos comerciales soportados por el schema vivo
- deja trazabilidad por comentario entre el registro `session_capitalizable` y el proyecto comercial
- no crea proyectos comerciales nuevos

### 7. Orquestar un slice operativo explicito

Task: `granola.promote_operational_slice`

Usar esta task cuando:

- ya tienes una pagina raw concreta
- ya sabes exactamente que registro `session_capitalizable` registrar
- quieres encadenar en la misma corrida una tarea humana y/o una actualizacion comercial

Esta task:

- siempre ejecuta `granola.promote_curated_session`
- puede ejecutar ademas `granola.create_human_task_from_curated_session`
- puede ejecutar ademas `granola.update_commercial_project_from_curated_session`
- exige payloads explicitos por tramo
- no agrega inferencias nuevas
- soporta `dry_run=true` para devolver los payloads exactos sin escribir en Notion

Para lotes explicitos repo-side, usar:

- `scripts/run_granola_operational_batch.py`
- template: `scripts/templates/granola_operational_batch.plan.template.json`

## Procedimientos

### Pipeline automatico

1. Granola deja la reunion en cache local
2. un exporter o copy/paste genera `.md` en `GRANOLA_EXPORT_DIR`
3. `granola_watcher.py` detecta el archivo y llama al Worker
4. Worker crea pagina raw, extrae action items y notifica a Enlace

### Pipeline manual

1. David copia la nota o transcript desde Granola
2. Rick o una herramienta intermedia la guarda como `.md`
3. el Worker procesa ese material en la capa raw

## Notas

- Los docs repo-side que todavia usan `curated` deben leerse como alias legacy de `session_capitalizable`.
- Si falta sharing de la superficie V1 o de los targets humanos, el bloqueo correcto es de acceso, no de arquitectura.
- No asumas que `session_capitalizable` o los targets humanos son visibles para Rick solo porque existan en Notion.
- Si el watcher no esta corriendo, Rick puede procesar archivos manualmente.

## Referencias

- `docs/50-granola-notion-pipeline.md`
- `docs/54-granola-capitalize-raw-slice.md`
- `docs/56-granola-promote-curated-session.md`
- `docs/57-granola-human-task-from-curated-session.md`
- `docs/58-granola-commercial-project-from-curated-session.md`
- `docs/59-granola-promote-operational-slice.md`
- `worker/notion_client.py`
- `worker/tasks/granola.py`
- `scripts/vm/granola_watcher.py`

Los docs `56-59` conservan naming legacy con `curated`; en el contrato vigente debe leerse como alias de `session_capitalizable`.
