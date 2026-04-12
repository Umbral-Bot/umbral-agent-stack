---
name: reunion-prep
description: >-
  Preparación proactiva antes de reuniones. Rick revisa el calendario,
  busca contexto relevante en Notion y entrega un brief de preparación.
  Se ejecuta cada 30 minutos para detectar reuniones próximas. Usa cuando
  David diga "prepárame para la reunión", "contexto de la próxima reunión".
metadata:
  openclaw:
    emoji: "\U0001F91D"
    requires:
      env:
        - GOOGLE_CALENDAR_REFRESH_TOKEN
        - GOOGLE_CALENDAR_CLIENT_ID
        - GOOGLE_CALENDAR_CLIENT_SECRET
        - NOTION_API_KEY
---

# Reunion Prep Skill

Rick detecta reuniones próximas (dentro de 60 minutos) y prepara un brief
con contexto relevante de Notion, historial de proyectos y puntos clave.

## Flujo

1. **Detectar reunión próxima** via `google.calendar.list_events`
   con `time_min` = ahora y `time_max` = ahora + 60 minutos.
2. Si **no hay reuniones** en la próxima hora → responder `NO_REPLY`.
3. Si hay reunión:
   a. Extraer título, asistentes y descripción del evento.
   b. **Buscar contexto** en Notion via `notion.search_databases`
      usando el nombre del proyecto/cliente del evento.
   c. Si se encuentra una página relevante, leerla con `notion.read_page`.
4. **Compilar prep brief** via `llm.generate`:

```
Eres Rick, asistente ejecutivo de David Moreira.
Genera un brief de preparación para la reunión:

## 🤝 Prep — {título_reunión}
**Hora**: {hora_inicio} - {hora_fin}
**Asistentes**: {asistentes}

### 📌 Contexto
{resumen_contexto_notion}

### 🎯 Puntos sugeridos a tratar
{3_a_5_bullets}

### ⚡ Dato útil
{insight_relevante}
```

5. **Entregar** el brief por el canal configurado.

## Tasks utilizadas

| Task | Propósito |
|------|-----------|
| `google.calendar.list_events` | Detectar reuniones próximas |
| `notion.search_databases` | Buscar contexto por nombre de proyecto |
| `notion.read_page` | Leer página de contexto |
| `llm.generate` | Compilar el prep brief |

## Cron recomendado

```bash
openclaw cron add \
  --name "Prep reuniones próximas" \
  --agent rick-orchestrator \
  --every 30m \
  --session isolated \
  --timeout-seconds 90 \
  --light-context \
  --message "Revisa si hay una reunión en los próximos 60 minutos con google.calendar.list_events (time_min=ahora, time_max=ahora+60min, timezone America/Santiago). Si NO hay reuniones, responde EXACTAMENTE: NO_REPLY. Si hay reunión, busca contexto relevante en Notion y genera un prep brief conciso."
```

## Notas

- Con `--light-context` para reducir latencia en la verificación frecuente.
- La mayoría de las ejecuciones responderán `NO_REPLY` (sin reunión próxima).
- El timeout de 90s cubre el caso donde sí hay reunión y debe buscar contexto.
- No repite prep si ya envió uno para la misma reunión (el agente lleva contexto
  de sesión aislada).
