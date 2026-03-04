# Task R12 — Cloud 1: Google Calendar + Gmail Worker Handlers

**Fecha:** 2026-03-04  
**Ronda:** 12  
**Agente:** Cursor Agent Cloud 1  
**Branch:** `feat/google-calendar-gmail`

---

## Contexto

El pipeline Granola → Notion fue implementado en R11 por Cloud 7 (`worker/tasks/granola.py`). El handler `granola.create_followup` puede generar reminders, borradores de email y propuestas, pero **no tiene handlers reales de Google Calendar ni Gmail**. El objetivo de este task es implementarlos como Worker tasks completos.

**Archivos de referencia existentes:**
- `worker/tasks/granola.py` — genera `action_items` con `due` y `assignee`; el `create_followup` necesita llamar a calendar/gmail
- `worker/tasks/__init__.py` — registro de tasks
- `worker/config.py` — patrón `os.environ.get(...)` para variables
- `worker/tasks/figma.py` — patrón de cliente HTTP con urllib
- `.env.example` — agregar las variables nuevas
- `docs/50-granola-notion-pipeline.md` — arquitectura del pipeline

---

## Tareas requeridas

### 1. `worker/tasks/google_calendar.py`

Implementar con la [Google Calendar REST API v3](https://developers.google.com/calendar/api/v3/reference) usando `urllib.request` (sin SDK externo).

**Handlers requeridos:**

#### `handle_google_calendar_create_event`
- Task name: `google.calendar.create_event`
- Input:
  ```json
  {
    "title": "string",
    "description": "string (opcional)",
    "start": "2026-03-10T10:00:00",
    "end": "2026-03-10T11:00:00",
    "timezone": "America/Santiago (default)",
    "attendees": ["email1@..."],
    "calendar_id": "primary (default)"
  }
  ```
- Output: `{ "ok": true, "event_id": "...", "html_link": "..." }`
- Usa `GOOGLE_CALENDAR_TOKEN` (OAuth Bearer) o `GOOGLE_SERVICE_ACCOUNT_JSON` (ruta a archivo de service account)
- Endpoint: `POST https://www.googleapis.com/calendar/v3/calendars/{calendarId}/events`

#### `handle_google_calendar_list_events`
- Task name: `google.calendar.list_events`
- Input: `{ "calendar_id": "primary", "time_min": "2026-03-01T00:00:00Z", "max_results": 10 }`
- Output: `{ "ok": true, "events": [...] }`
- Endpoint: `GET https://www.googleapis.com/calendar/v3/calendars/{calendarId}/events`

**Auth helper:** implementar `_get_calendar_headers()` que intente primero `GOOGLE_CALENDAR_TOKEN` como Bearer. Si no está, intentar `GOOGLE_SERVICE_ACCOUNT_JSON` con google-auth (lazy import).

---

### 2. `worker/tasks/gmail.py`

Implementar con la [Gmail REST API v1](https://developers.google.com/gmail/api/reference/rest) usando `urllib.request`.

**Handlers requeridos:**

#### `handle_gmail_create_draft`
- Task name: `gmail.create_draft`
- Input:
  ```json
  {
    "to": "destinatario@email.com",
    "subject": "Asunto del email",
    "body": "Cuerpo en texto plano o HTML",
    "body_type": "plain | html (default: plain)",
    "cc": ["cc@..."],
    "reply_to": "reply@..."
  }
  ```
- Output: `{ "ok": true, "draft_id": "...", "message_id": "..." }`
- Codifica el email en base64 RFC 2822
- Endpoint: `POST https://gmail.googleapis.com/gmail/v1/users/me/drafts`

#### `handle_gmail_list_drafts`
- Task name: `gmail.list_drafts`
- Input: `{ "max_results": 10, "q": "query opcional" }`
- Output: `{ "ok": true, "drafts": [{"id": "...", "snippet": "..."}] }`
- Endpoint: `GET https://gmail.googleapis.com/gmail/v1/users/me/drafts`

**Auth helper:** `_get_gmail_headers()` — mismo patrón que calendar: `GOOGLE_GMAIL_TOKEN` o `GOOGLE_SERVICE_ACCOUNT_JSON`.

---

### 3. Integrar con `granola.create_followup`

En `worker/tasks/granola.py`, en la función `handle_granola_create_followup`:

- Si `followup_type == "calendar_event"` → llamar a `handle_google_calendar_create_event` con los datos del action item
- Si `followup_type == "email_draft"` → llamar a `handle_gmail_create_draft` con el template de email generado
- Agregar campo `calendar_event` y `email_draft` en el output del followup con el resultado

---

### 4. Actualizar `worker/tasks/__init__.py`

Registrar los 4 nuevos handlers:
```python
from .google_calendar import handle_google_calendar_create_event, handle_google_calendar_list_events
from .gmail import handle_gmail_create_draft, handle_gmail_list_drafts

# En TASK_HANDLERS:
"google.calendar.create_event": handle_google_calendar_create_event,
"google.calendar.list_events": handle_google_calendar_list_events,
"gmail.create_draft": handle_gmail_create_draft,
"gmail.list_drafts": handle_gmail_list_drafts,
```

---

### 5. Actualizar `.env.example`

Agregar:
```dotenv
# Google Calendar / Gmail (OAuth Bearer o Service Account)
GOOGLE_CALENDAR_TOKEN=CHANGE_ME_GOOGLE_CALENDAR_OAUTH_TOKEN
GOOGLE_GMAIL_TOKEN=CHANGE_ME_GOOGLE_GMAIL_OAUTH_TOKEN
# Alternativa: ruta a JSON de Service Account con scopes calendar + gmail
GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/service-account.json
```

---

### 6. Skills OpenClaw

#### `openclaw/workspace-templates/skills/google-calendar/SKILL.md`

```yaml
---
name: google-calendar
description: >-
  Crear y listar eventos en Google Calendar. Usa cuando el usuario diga
  "agendar reunión", "crear evento", "recordatorio en calendario",
  "ver mis eventos", "Google Calendar".
metadata:
  openclaw:
    emoji: "📅"
    requires:
      env:
        - GOOGLE_CALENDAR_TOKEN
---
```

Incluir instrucciones detalladas para `google.calendar.create_event` y `google.calendar.list_events` con ejemplos JSON.

#### `openclaw/workspace-templates/skills/gmail/SKILL.md`

```yaml
---
name: gmail
description: >-
  Crear borradores de email en Gmail. Usa cuando el usuario diga
  "redactar email", "guardar borrador", "email borrador", "Gmail draft".
metadata:
  openclaw:
    emoji: "📧"
    requires:
      env:
        - GOOGLE_GMAIL_TOKEN
---
```

Incluir instrucciones para `gmail.create_draft` y `gmail.list_drafts`.

---

### 7. Tests

Crear `tests/test_google_calendar_gmail.py` con al menos 14 tests:

- `test_create_event_success` — mock urllib, verifica payload
- `test_create_event_missing_token` — error claro
- `test_create_event_all_day` — sin hora de fin
- `test_create_event_with_attendees`
- `test_list_events_success`
- `test_list_events_empty`
- `test_gmail_create_draft_plain_text`
- `test_gmail_create_draft_html`
- `test_gmail_create_draft_missing_token`
- `test_gmail_create_draft_with_cc`
- `test_gmail_list_drafts_success`
- `test_gmail_list_drafts_empty`
- `test_granola_followup_calls_calendar` — integración con granola
- `test_granola_followup_calls_gmail`

---

## Convenciones del proyecto

- **No usar SDKs externos** (google-api-python-client) — solo `urllib.request` y lazy imports de `google-auth` si disponible
- **Patrón de error:** `raise ValueError("GOOGLE_CALENDAR_TOKEN not set")` cuando faltan credenciales
- **Logging:** `logger = logging.getLogger("worker.tasks.google_calendar")`
- **Tests:** usar `unittest.mock.patch("urllib.request.urlopen")`
- **Rama:** crear `feat/google-calendar-gmail` y abrir PR a `main`

## Criterios de éxito

- [ ] `worker/tasks/google_calendar.py` con 2 handlers implementados
- [ ] `worker/tasks/gmail.py` con 2 handlers implementados
- [ ] `granola.create_followup` integrado con calendar/gmail
- [ ] `worker/tasks/__init__.py` actualizado (4 nuevas tasks)
- [ ] `.env.example` con variables de Google
- [ ] 2 skills SKILL.md creados
- [ ] `tests/test_google_calendar_gmail.py` con 14+ tests
- [ ] PR abierto a `main`
