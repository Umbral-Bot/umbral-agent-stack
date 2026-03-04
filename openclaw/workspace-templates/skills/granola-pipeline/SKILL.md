---
name: granola-pipeline
description: >-
  Process Granola meeting transcripts into Notion, extract action items,
  and create proactive follow-ups. Use when "subir transcripción",
  "procesar granola", "reunión terminada", "compromisos reunión",
  "follow-up de reunión", "propuesta de seguimiento".
metadata:
  openclaw:
    emoji: "\U0001F399"
    requires:
      env:
        - NOTION_API_KEY
        - NOTION_GRANOLA_DB_ID
---

# Granola Pipeline Skill

Rick puede procesar transcripciones de Granola y generar follow-ups proactivos usando las tasks `granola.*` del Worker.

## Requisitos

- `NOTION_API_KEY`: token de integración de Notion.
- `NOTION_GRANOLA_DB_ID`: ID de la DB de transcripciones (Granola Inbox).
- `NOTION_TASKS_DB_ID` (opcional): ID de la DB Kanban para action items.
- Watcher corriendo en la VM (`scripts/vm/granola_watcher.py`) para pipeline automático.

## Tasks disponibles

### 1. Procesar transcripción

Task: `granola.process_transcript`

Pipeline completo: crea página en Notion, extrae action items, notifica a Enlace.

```json
{
  "title": "Reunión con Cliente X — Revisión de proyecto",
  "content": "## Notas\n\nSe revisó el avance del proyecto...\n\n## Action Items\n\n- [ ] Enviar propuesta (David, 2026-03-07)\n- [ ] Revisar presupuesto (Partner Y)",
  "date": "2026-03-04",
  "attendees": ["David", "Cliente X", "Partner Y"],
  "action_items": [
    {"text": "Enviar propuesta", "assignee": "David", "due": "2026-03-07"},
    {"text": "Revisar presupuesto", "assignee": "Partner Y", "due": ""}
  ],
  "source": "granola",
  "notify_enlace": true
}
```

Devuelve:
```json
{
  "page_id": "abc-123",
  "url": "https://notion.so/...",
  "action_items_created": 2,
  "notification_sent": true
}
```

### 2. Crear follow-up

Task: `granola.create_followup`

Follow-up proactivo con tres tipos: reminder, email_draft, proposal.

#### Reminder
```json
{
  "transcript_page_id": "abc-123",
  "followup_type": "reminder",
  "title": "Reunión con Cliente X",
  "date": "2026-03-04",
  "attendees": ["David", "Cliente X"],
  "action_items": [{"text": "Enviar propuesta", "assignee": "David", "due": "2026-03-07"}],
  "due_date": "2026-03-10"
}
```

#### Email draft
```json
{
  "transcript_page_id": "abc-123",
  "followup_type": "email_draft",
  "title": "Reunión con Cliente X",
  "date": "2026-03-04",
  "action_items": [{"text": "Enviar propuesta", "assignee": "David", "due": "2026-03-07"}],
  "notes": "Agregar referencia al proyecto anterior."
}
```

#### Proposal
```json
{
  "transcript_page_id": "abc-123",
  "followup_type": "proposal",
  "title": "Reunión con Cliente X",
  "date": "2026-03-04",
  "attendees": ["David", "Cliente X"],
  "action_items": [{"text": "Enviar propuesta", "assignee": "David", "due": "2026-03-07"}]
}
```

## Triggers recomendados

- "reunión terminada" / "meeting done"
- "subir transcripción" / "procesar granola"
- "compromisos de la reunión"
- "follow-up de reunión"
- "crear propuesta de seguimiento"
- "borrador de email de la reunión"
- "recordatorio de compromisos"

## Procedimientos

### Pipeline automático (watcher)

1. David termina reunión en Granola
2. Exporta nota (Copy/Paste .md) a `GRANOLA_EXPORT_DIR` en la VM
3. `granola_watcher.py` detecta el archivo, lo parsea y envía al Worker
4. Worker crea página en Notion, extrae action items, notifica a Enlace

### Pipeline manual (Rick)

1. Rick recibe instrucción: "Sube la transcripción de la reunión X"
2. Rick lee el archivo de la VM con `windows.fs.read_text`
3. Rick envía el contenido a `granola.process_transcript`

### Follow-up proactivo

1. Rick revisa Notion y detecta transcripción sin follow-up
2. Rick sugiere: "Puedo crear un reminder, borrador de email o propuesta"
3. David elige → Rick ejecuta `granola.create_followup`

## Referencias

- `worker/tasks/granola.py` — handlers
- `scripts/vm/granola_watcher.py` — watcher en VM
- `docs/50-granola-notion-pipeline.md` — arquitectura y setup
- `worker/notion_client.py` — cliente Notion

## Notas

- El watcher mueve archivos procesados a `GRANOLA_EXPORT_DIR/processed/`.
- Si el watcher no está corriendo, Rick puede procesar archivos manualmente.
- Action items se crean como tareas en la DB Kanban si `NOTION_TASKS_DB_ID` está configurado.
- La notificación a Enlace se envía como comentario en la página de Notion creada.
