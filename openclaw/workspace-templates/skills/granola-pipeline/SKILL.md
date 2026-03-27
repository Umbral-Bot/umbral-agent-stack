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
- La promoción a una DB curada humana es una fase aparte y no forma parte automática de esta skill.
- Si el watcher no está corriendo, Rick puede procesar archivos manualmente.

## Referencias

- `docs/50-granola-notion-pipeline.md`
- `worker/notion_client.py`
- `worker/tasks/granola.py`
- `scripts/vm/granola_watcher.py`
