---
name: granola-pipeline
description: >-
  Process Granola meeting transcripts into Notion, extract action items as tasks,
  and create proactive follow-ups (reminders, proposals, email drafts).
  Use when "reunión terminada", "subir transcripción", "procesar granola",
  "compromisos reunión", "follow-up reunión", "crear propuesta de reunión".
metadata:
  openclaw:
    emoji: "\U0001F399"
    requires:
      env:
        - NOTION_API_KEY
        - NOTION_GRANOLA_DB_ID
---

# Granola Pipeline Skill

Rick puede procesar transcripciones de reuniones desde Granola y crear follow-ups proactivos.

## Requisitos

- `NOTION_API_KEY`: Token de integración de Notion.
- `NOTION_GRANOLA_DB_ID`: ID de la DB de transcripciones (Granola Inbox).
- `NOTION_TASKS_DB_ID`: ID de la DB Kanban para action items (opcional).
- Watcher en VM: `scripts/vm/granola_watcher.py` (automatiza la detección de exports).

## Tasks disponibles

### 1. Procesar transcript completo

Task: `granola.process_transcript`

```json
{
  "title": "Reunión con Cliente ABC",
  "content": "# Notas de la reunión\n\n## Participantes\n- David\n- María\n\n## Resumen\nSe discutió la propuesta...\n\n## Action Items\n- [ ] Enviar cotización\n- [ ] Agendar demo",
  "date": "2026-03-04",
  "attendees": ["David", "María"],
  "action_items": ["Enviar cotización", "Agendar demo"]
}
```

Devuelve:
```json
{
  "page_id": "abc123...",
  "page_url": "https://notion.so/...",
  "tasks_created": 2,
  "action_items_found": 2,
  "comment_added": true
}
```

**Qué hace internamente:**
1. Crea página en Notion (Granola Inbox DB) con contenido en Markdown rico
2. Agrega bloques de action items como to-do checkboxes
3. Deja comentario: "Transcripción lista para optimizar"
4. Crea tareas individuales en la DB Kanban para cada action item

### 2. Crear follow-up proactivo

Task: `granola.create_followup`

#### Tipo: reminder
```json
{
  "transcript_page_id": "abc123...",
  "followup_type": "reminder",
  "title": "Enviar cotización a Cliente ABC",
  "due_date": "2026-03-07",
  "assignee": "David"
}
```

#### Tipo: proposal
```json
{
  "transcript_page_id": "abc123...",
  "followup_type": "proposal",
  "title": "Propuesta técnica para Cliente ABC",
  "notes": "Incluir timeline y presupuesto estimado"
}
```

#### Tipo: email_draft
```json
{
  "transcript_page_id": "abc123...",
  "followup_type": "email_draft",
  "title": "Seguimiento reunión con Cliente ABC",
  "assignee": "María García",
  "notes": "confirmar los puntos acordados en la reunión de hoy"
}
```

## Triggers recomendados

- "reunión terminada" → `granola.process_transcript`
- "subir transcripción" → `granola.process_transcript`
- "procesar granola" → `granola.process_transcript`
- "compromisos reunión" → revisar action items del último transcript
- "follow-up reunión" → `granola.create_followup`
- "crear propuesta de reunión" → `granola.create_followup` con type `proposal`
- "borrador de email de reunión" → `granola.create_followup` con type `email_draft`
- "recordatorio de reunión" → `granola.create_followup` con type `reminder`

## Proactividad de Rick

Rick puede revisar periódicamente las transcripciones en Notion y sugerir acciones:

1. **Transcripción sin follow-up**: Si hay una transcripción reciente sin comentarios de follow-up, Rick sugiere crear uno.
2. **Action items vencidos**: Si hay tareas de reunión en estado "queued" por más de 48 horas, Rick recuerda a David.
3. **Reuniones sin notas**: Si el calendario muestra reuniones pasadas sin transcripción asociada, Rick pregunta si hubo notas.

## Pipeline automático (VM Watcher)

El script `scripts/vm/granola_watcher.py` corre en la VM y:
1. Monitorea `GRANOLA_EXPORT_DIR` por archivos `.md` nuevos
2. Parsea título, fecha, participantes, action items del Markdown
3. Llama al Worker con `granola.process_transcript`
4. Mueve el archivo procesado a `GRANOLA_PROCESSED_DIR`

## Referencias

- `worker/tasks/granola.py` — Handlers del Worker
- `scripts/vm/granola_watcher.py` — Watcher en VM
- `docs/50-granola-notion-pipeline.md` — Documentación completa
- `worker/notion_client.py` — Cliente Notion subyacente
