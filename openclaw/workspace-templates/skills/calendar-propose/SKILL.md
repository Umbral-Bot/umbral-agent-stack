---
name: calendar-propose
description: >-
  Proponer y listar eventos de Google Calendar de forma segura para Rick (policy
  propose+confirm).
metadata:
  openclaw:
    emoji: "🗓️"
    requires:
      env: []
---

# Calendar Propose Skill

Skill para trabajar con Calendar en el canal de Rick.

## Alcance y límites

- Este skill propone eventos con `google.calendar.create_event` y solo usa lectura con `google.calendar.list_events`.
- Las escrituras se tratan como **propuesta**. El evento se puede crear con prefijo `"[PROPUESTA]"`.
- Sigue ADR-16:
  - **D4**: scope mínimo `https://www.googleapis.com/auth/calendar.events`.
  - **D5**: escritura Calendar = `propose + confirm` (no autoapply).
  - **D6**: whitelisting de calendar_id por design del entorno (David-primary en este gate).

## Recomendación de gate humano

`create_event` no se usa como commit final automático; se usa para propuesta.
El agente debe esperar confirmación de David antes de crear o editar en contextos sensibles.

## Tasks soportadas

### 1) Proponer evento

Task: `google.calendar.create_event`

Inputs sugeridos:

```json
{
  "title": "[PROPUESTA] Reunión seguimiento",
  "description": "Validar avances de BIM",
  "start": "2026-03-10T10:00:00",
  "end": "2026-03-10T11:00:00",
  "timezone": "America/Santiago",
  "attendees": ["cliente@email.com"],
  "calendar_id": "primary"
}
```

Retorna `{"ok": true, "event_id": "...", "html_link": "..."}`.

### 2) Listar eventos

Task: `google.calendar.list_events`

```json
{
  "calendar_id": "primary",
  "time_min": "2026-03-01T00:00:00Z",
  "time_max": "2026-03-02T00:00:00Z",
  "max_results": 10
}
```

Retorna `{"ok": true, "events": [{"id": "...", "summary": "...", "start": "...", "end": "...", "html_link": "..."}]}`.

## Qué no hace este skill

- No modifica ACLs ni calendarios.
- No borra eventos.
- No crea calendarios nuevos.
- No usa `calendar` scope global.

## Notas de implementación

Usa worker tasks existentes en `worker/tasks/google_calendar.py`.
Para setup y scopes, revisar:

- `docs/35-google-calendar-token-setup.md`
- `docs/external-context/adr-16-multichannel-rick-channels.md`
