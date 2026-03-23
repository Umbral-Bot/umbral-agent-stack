---
name: google-calendar
description: >-
  Crear y listar eventos en Google Calendar. Usa cuando el usuario diga
  "agendar reunion", "crear evento", "recordatorio en calendario",
  "ver mis eventos", "Google Calendar".
metadata:
  openclaw:
    emoji: "\U0001F4C5"
    requires:
      env: []
---

# Google Calendar Skill

Rick puede crear y listar eventos en Google Calendar a traves de las Worker
tasks del Umbral Agent Stack.

## Requisitos

- `GOOGLE_CALENDAR_REFRESH_TOKEN` + `GOOGLE_CALENDAR_CLIENT_ID` +
  `GOOGLE_CALENDAR_CLIENT_SECRET`: opcion persistente recomendada; el Worker
  renueva el access token solo.
- `GOOGLE_CALENDAR_TOKEN`: OAuth2 Bearer token con scope `calendar`
  (temporal, caduca en ~1 h).
- Alternativa: `GOOGLE_SERVICE_ACCOUNT_JSON` (ruta al archivo JSON de service
  account con scope calendar).

## Tasks disponibles

### 1. Crear evento

Task: `google.calendar.create_event`

```json
{
  "title": "Reunion de seguimiento con Cliente X",
  "description": "Revisar avance del proyecto BIM",
  "start": "2026-03-10T10:00:00",
  "end": "2026-03-10T11:00:00",
  "timezone": "America/Santiago",
  "attendees": ["cliente@email.com", "partner@email.com"],
  "calendar_id": "primary"
}
```

Devuelve: `{"ok": true, "event_id": "...", "html_link": "..."}`

**Evento de dia completo** (sin hora de fin):

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

- Todas las tasks se encolan via el Dispatcher a Redis y las ejecuta el Worker.
- El timezone por defecto es `America/Santiago`.
- El `calendar_id` por defecto es `primary`.
- Para calendarios compartidos, **no** usar `primary`: pasa el `calendar_id`
  explicito del calendario compartido.
- Soporta refresh token OAuth, OAuth Bearer temporal y Service Account
  (con lazy import de `google-auth`).
