---
name: granola-pipeline
description: >-
  Process Granola meeting notes or transcripts into Notion raw intake,
  extract action items, and create proactive follow-ups. Use when
  "subir transcripción", "procesar granola", "reunión terminada",
  "compromisos reunión", "follow-up de reunión", or
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

## Regla principal

Esta skill trabaja sobre la **capa raw** de Granola.

No asumas que:

- todo item raw debe pasar a una DB humana curada
- toda reunión debe convertirse en proyecto o tarea
- Granola siempre trae transcript de audio

La arquitectura correcta es:

1. **Raw**: DB `NOTION_GRANOLA_DB_ID`
2. **Curado**: DB humana separada de sesiones/transcripciones
3. **Destino**: proyectos, tareas, recursos y follow-ups

## Requisitos

- `NOTION_API_KEY`: token de integración Notion Rick.
- `NOTION_GRANOLA_DB_ID`: ID de la DB raw de Granola (Granola Inbox).
- `NOTION_TASKS_DB_ID` (opcional): DB Kanban para action items.
- `NOTION_CURATED_SESSIONS_DB_ID` (opcional): DB humana curada compartida con Rick.
- `NOTION_HUMAN_TASKS_DB_ID` (opcional): DB humana de tareas para el slice `curado -> destino`.
- Watcher corriendo en la VM (`scripts/vm/granola_watcher.py`) o flujo manual hacia `.md`.

## Tasks disponibles

### 1. Procesar intake raw

Task: `granola.process_transcript`

Pipeline raw completo:

1. crea página raw en Notion
2. extrae action items
3. opcionalmente crea tareas
4. notifica a Enlace

```json
{
  "title": "Reunión con Cliente X - Revisión de proyecto",
  "content": "## Notes\n\nSe revisó el avance...\n\n## Action Items\n\n- [ ] Enviar propuesta",
  "date": "2026-03-04",
  "attendees": ["David", "Cliente X"],
  "action_items": [
    {"text": "Enviar propuesta", "assignee": "David", "due": "2026-03-07"}
  ],
  "source": "granola",
  "notify_enlace": true
}
```

### 2. Crear follow-up

Task: `granola.create_followup`

### 3. Capitalizar raw ya ingresado

Task: `granola.capitalize_raw`

Usar esta task cuando la pagina raw ya existe y quieres dejar trazabilidad hacia objetos que el stack si gobierna hoy:

- proyecto
- entregable
- item puente
- follow-up

No usa la DB humana curada como destino automatico.

### 4. Promover a capa `session_capitalizable`

Tasks: `granola.promote_curated_session`, `granola.promote_session_capitalizable`

Usar esta task solo cuando:

- la pagina raw ya existe
- la DB humana curada fue compartida con Rick
- `NOTION_CURATED_SESSIONS_DB_ID` ya esta configurado
- quieres crear o actualizar una sesion curada con trazabilidad

Esta task:

- inspecciona el schema vivo de la DB curada
- crea o actualiza por titulo exacto
- si hay ambiguedad, comenta para revision en la fuente raw
- solo crea relaciones si recibe `page_id` explicitos
- no reemplaza la posterior derivacion hacia tareas o proyectos humanos

### 5. Leer una `session_capitalizable` real

Task: `granola.read_session_capitalizable`

Usar esta task cuando:

- la sesion ya deberia existir en la capa `session_capitalizable`
- quieres resolverla por `session_capitalizable_page_id` o desde `transcript_page_id`
- necesitas verificar operacion real sin escribir en destinos canonicos

Esta task:

- resuelve la sesion por binding live y evidencia source-aware
- permite testing real con reuniones de Granola
- si hay ambiguedad, comenta para revision en la fuente raw
- no capitaliza hacia proyectos, tareas ni entregables

### 6. Crear tarea humana desde una sesion curada

Task: `granola.create_human_task_from_curated_session`

Usar esta task solo cuando:

- la sesion curada ya existe
- `NOTION_HUMAN_TASKS_DB_ID` ya esta configurado
- quieres registrar una tarea humana explicita y trazable

Esta task:

- exige `task_name` explicito
- inspecciona el schema vivo de la DB humana de tareas
- crea o actualiza por titulo exacto
- hereda `Proyecto` desde la sesion curada cuando existe
- enlaza `Sesion relacionada`
- no actualiza todavia la DB comercial humana

### 7. Actualizar proyecto comercial desde una sesion curada

Task: `granola.update_commercial_project_from_curated_session`

Usar esta task solo cuando:

- la sesion curada ya existe
- el proyecto comercial humano ya está identificado
- `NOTION_COMMERCIAL_PROJECTS_DB_ID` ya está configurado
- el cambio comercial cabe en campos explícitos del proyecto

Esta task:

- usa `project_page_id` explícito o la relacion `Proyecto` heredada desde la sesion curada
- actualiza solo campos comerciales soportados por el schema vivo
- hoy el contrato cubre `Estado`, `Acción Requerida`, `Fecha`, `Plazo`, `Monto`, `Tipo` y `Cliente`
- deja trazabilidad por comentario entre la sesion curada y el proyecto comercial
- no crea proyectos comerciales nuevos

### 7. Orquestar un slice operativo explícito

Task: `granola.promote_operational_slice`

Usar esta task cuando:

- ya tienes una pagina raw concreta
- ya sabes exactamente qué sesión curada registrar
- y quieres encadenar en la misma corrida una tarea humana y/o una actualización comercial

Esta task:

- siempre ejecuta `granola.promote_curated_session`
- puede ejecutar además `granola.create_human_task_from_curated_session`
- puede ejecutar además `granola.update_commercial_project_from_curated_session`
- exige payloads explícitos por tramo
- no agrega inferencias nuevas
- soporta `dry_run=true` para devolver los payloads exactos sin escribir en Notion

Para lotes explícitos repo-side, usar:

- `scripts/run_granola_operational_batch.py`
- template:
  - `scripts/templates/granola_operational_batch.plan.template.json`

Tipos:

- `reminder`
- `email_draft`
- `proposal`

## Procedimientos

### Pipeline automático

1. Granola deja la reunión en cache local
2. un exporter o copy/paste genera `.md` en `GRANOLA_EXPORT_DIR`
3. `granola_watcher.py` detecta el archivo y llama al Worker
4. Worker crea página raw, extrae action items y notifica a Enlace

### Pipeline manual

1. David copia la nota o transcript desde Granola
2. Rick o una herramienta intermedia la guarda como `.md`
3. el Worker procesa ese material en la capa raw

## Notas

- Granola puede entregar notas en ProseMirror JSON; en ese caso hace falta una capa exportadora previa a `.md`.
- La promoción a una DB curada humana ya tiene un slice repo-side (`granola.promote_curated_session`), pero sigue dependiendo de sharing y configuración reales.
- No asumir que la DB humana curada es visible para Rick solo porque exista en Notion; si falta sharing, el bloqueo correcto es de acceso, no de arquitectura.
- Si el watcher no está corriendo, Rick puede procesar archivos manualmente.

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
