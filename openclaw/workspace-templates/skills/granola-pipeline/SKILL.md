---
name: granola-pipeline
description: >-
  Pipeline Granola → Notion para procesar transcripciones de reuniones,
  extraer action items y generar follow-ups proactivos.
  Use when "procesar transcripción", "subir granola", "reunión terminada",
  "compromisos reunión", "follow-up reunión", "propuesta reunión".
metadata:
  openclaw:
    emoji: "\U0001F399"
    requires:
      env:
        - NOTION_API_KEY
        - NOTION_GRANOLA_DB_ID
---

# Granola Pipeline Skill

Rick puede procesar transcripciones de Granola y generar follow-ups
proactivos usando las tasks `granola.*` del Worker.

## Requisitos

- `NOTION_API_KEY`: token de integración de Notion.
- `NOTION_GRANOLA_DB_ID`: ID de la base de datos Granola Inbox en Notion.
- `NOTION_CONTROL_ROOM_PAGE_ID`: para comentarios de notificación.
- `NOTION_TASKS_DB_ID`: para crear action items como tareas.

## Tasks disponibles

### 1. Procesar transcripción

Task: `granola.process_transcript`

```json
{
  "title": "Reunión con cliente ABC",
  "content": "# Reunión con cliente ABC\n\nDiscusión sobre...\n\n## Action Items\n- Enviar propuesta\n- Revisar contrato",
  "date": "2026-03-04",
  "attendees": ["David", "Juan"],
  "action_items": ["Enviar propuesta", "Revisar contrato"]
}
```

Devuelve:

```json
{
  "page_id": "abc123",
  "url": "https://notion.so/...",
  "action_items_created": 2,
  "action_items_total": 2,
  "comment_id": "comm123"
}
```

**Qué hace:**

1. Crea una página en la DB Granola Inbox de Notion con la transcripción.
2. Agrega un comentario: "Transcripción lista para optimizar".
3. Extrae action items del contenido (si no se envían explícitamente).
4. Crea una tarea en Notion por cada action item.

### 2. Crear follow-up

Task: `granola.create_followup`

#### Reminder

```json
{
  "transcript_page_id": "abc123",
  "followup_type": "reminder",
  "title": "Enviar propuesta a cliente ABC",
  "due_date": "2026-03-10",
  "assignee": "David"
}
```

#### Email draft

```json
{
  "transcript_page_id": "abc123",
  "followup_type": "email_draft",
  "title": "Seguimiento reunión ABC",
  "body": "Estimado Juan,\n\nGracias por la reunión de hoy...",
  "assignee": "Juan"
}
```

#### Propuesta

```json
{
  "transcript_page_id": "abc123",
  "followup_type": "proposal",
  "title": "Propuesta de servicios BIM para ABC",
  "body": "# Propuesta\n\n## Alcance\n...",
  "assignee": "Juan"
}
```

Devuelve: `{"ok": true, "followup_type": "...", "result": {...}}`

## Triggers recomendados

- "reunión terminada" → `granola.process_transcript`
- "subir transcripción" → `granola.process_transcript`
- "procesar granola" → `granola.process_transcript`
- "compromisos reunión" → revisar action items creados
- "follow-up reunión" → `granola.create_followup`
- "propuesta reunión" → `granola.create_followup` con `followup_type: "proposal"`
- "email de seguimiento" → `granola.create_followup` con `followup_type: "email_draft"`

## Proactividad

Rick puede actuar proactivamente:

1. **Detectar transcripciones sin follow-up**: revisar Notion, si hay
   transcripciones recientes sin tareas de follow-up asociadas, sugerir a
   David crear follow-ups.
2. **Recordatorios automáticos**: si un action item de reunión tiene fecha
   límite próxima y no se ha completado, recordar a David.
3. **Generar borradores**: Rick puede usar `granola.create_followup` con
   tipo "email_draft" o "proposal" para preparar borradores que David
   revisa y envía.

## Pipeline automático (Watcher)

El script `scripts/vm/granola_watcher.py` corre en la VM Windows y
monitorea `GRANOLA_EXPORT_DIR`. Cuando David guarda un archivo `.md`:

1. El watcher lo detecta.
2. Parsea metadata (título, fecha, participantes, action items).
3. Envía `granola.process_transcript` al Worker.
4. Mueve el archivo a `processed/`.

## Referencias

- `worker/tasks/granola.py`
- `scripts/vm/granola_watcher.py`
- `docs/50-granola-notion-pipeline.md`
