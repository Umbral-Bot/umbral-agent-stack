---
name: google-calendar
description: >-
  Crear y listar eventos en Google Calendar. Usa cuando el usuario diga
  "agendar reunión", "crear evento", "recordatorio en calendario",
  "ver mis eventos", "Google Calendar".
metadata:
  openclaw:
    emoji: "\U0001F4C5"
    requires:
      env:
        - GOOGLE_CALENDAR_TOKEN
---

# Google Calendar Skill

Rick puede crear y listar eventos en Google Calendar a través de las Worker tasks del Umbral Agent Stack.

## Requisitos

- `GOOGLE_CALENDAR_TOKEN`: OAuth2 Bearer token con scope `calendar`.
- Alternativa: `GOOGLE_SERVICE_ACCOUNT_JSON` (ruta al archivo JSON de service account con scope calendar).

## Tasks disponibles

### 1. Crear evento

Task: `google.calendar.create_event`

```json
{
  "title": "Reunión de seguimiento con Cliente X",
  "description": "Revisar avance del proyecto BIM",
  "start": "2026-03-10T10:00:00",
  "end": "2026-03-10T11:00:00",
  "timezone": "America/Santiago",
  "attendees": ["cliente@email.com", "partner@email.com"],
  "calendar_id": "primary"
}
```

Devuelve: `{"ok": true, "event_id": "...", "html_link": "..."}`

**Evento de día completo** (sin hora de fin):

```json
{
  "title": "Deadline propuesta",
  "start": "2026-03-15T00:00:00"
}
```

### 2. Listar eventos

Task: `google.calendar.list_events`

```json
{
  "calendar_id": "primary",
  "time_min": "2026-03-01T00:00:00Z",
  "max_results": 10
}
```

Devuelve: `{"ok": true, "events": [{"id", "summary", "start", "end", "html_link"}, ...]}`

## Notas

- Todas las tasks se encolan vía el Dispatcher a Redis y las ejecuta el Worker.
- El timezone por defecto es `America/Santiago`.
- El `calendar_id` por defecto es `primary`.
- Soporta tanto OAuth Bearer como Service Account (con lazy import de `google-auth`).
