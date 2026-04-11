---
name: daily-briefing
description: >-
  Briefing matutino proactivo. Rick compila calendario, tareas pendientes
  y alertas del día para David. Se ejecuta automáticamente vía cron cada
  mañana. Usa cuando David diga "briefing del día", "qué tengo hoy",
  "resumen de la mañana".
metadata:
  openclaw:
    emoji: "\U00002600"
    requires:
      env:
        - GOOGLE_CALENDAR_REFRESH_TOKEN
        - GOOGLE_CALENDAR_CLIENT_ID
        - GOOGLE_CALENDAR_CLIENT_SECRET
        - NOTION_API_KEY
---

# Daily Briefing Skill

Rick genera un briefing matutino combinando Google Calendar, tareas
pendientes en Notion y alertas operativas.

## Flujo

1. **Obtener eventos del día** via `google.calendar.list_events`
   con `time_min` = hoy 00:00 y `time_max` = hoy 23:59 (America/Santiago).
2. **Leer tareas pendientes** via `notion.read_database` en la base de
   tareas activas (usar `NOTION_CONTROL_ROOM_PAGE_ID` o la base de Kanban).
3. **Compilar briefing** via `llm.generate` con el siguiente prompt
   template:

```
Eres Rick, asistente ejecutivo de David Moreira.
Genera un briefing matutino conciso en español:

## ☀️ Briefing — {fecha}

### 📅 Agenda del día
{eventos_calendario}

### 📋 Tareas pendientes prioritarias
{tareas_notion_top_5}

### ⚠️ Alertas
{alertas_si_hay}

### 💡 Recomendación
{una_sugerencia_accionable}
```

4. **Entregar** el briefing por el canal configurado (Telegram, Notion comment,
   o respuesta en sesión).

## Tasks utilizadas

| Task | Propósito |
|------|-----------|
| `google.calendar.list_events` | Eventos del día |
| `notion.read_database` | Tareas pendientes en Kanban/Control Room |
| `llm.generate` | Compilar y redactar el briefing |

## Cron recomendado

```bash
openclaw cron add \
  --name "Briefing matutino" \
  --agent rick-orchestrator \
  --cron "30 7 * * 1-5" \
  --tz America/Santiago \
  --session isolated \
  --timeout-seconds 120 \
  --message "Ejecuta el briefing matutino para David. 1) Lista eventos de hoy con google.calendar.list_events (time_min=hoy 00:00, time_max=hoy 23:59, timezone America/Santiago). 2) Lee las tareas pendientes de Notion. 3) Compila un briefing conciso y entrégalo. Si no hay eventos ni tareas, responde NO_REPLY."
```

## Notas

- Días hábiles solamente (lunes a viernes).
- Si no hay eventos ni tareas, Rick responde `NO_REPLY` para evitar ruido.
- El timeout es de 120s para cubrir las 3 llamadas secuenciales.
