---
name: stale-watch
description: >-
  Vigilancia de tareas estancadas. Rick revisa tareas en Notion y Linear
  que llevan más de N días sin actualización y alerta proactivamente.
  Se ejecuta una vez al día. Usa cuando David diga "tareas estancadas",
  "qué quedó pendiente", "revisar atrasos".
metadata:
  openclaw:
    emoji: "\U0001F440"
    requires:
      env:
        - NOTION_API_KEY
---

# Stale Watch Skill

Rick revisa diariamente las tareas activas en Notion (y opcionalmente
Linear) que llevan más de 3 días sin actualización y genera una alerta.

## Flujo

1. **Leer base de tareas activas** via `notion.read_database` en la base
   de Kanban/Control Room, filtrando por estado != "Done"/"Archived".
2. **Identificar tareas estancadas**: items cuya última edición
   (`last_edited_time`) sea > 3 días atrás.
3. Si **no hay tareas estancadas** → responder `NO_REPLY`.
4. Si hay tareas estancadas:
   a. Compilar lista con título, responsable, días sin actividad.
   b. **Generar alerta** via `llm.generate`:

```
Eres Rick, asistente ejecutivo de David Moreira.
Genera una alerta de tareas estancadas:

## 👀 Stale Watch — {fecha}

### Tareas sin actividad (>{umbral_dias} días)
| Tarea | Responsable | Días sin update | Última actividad |
|-------|-------------|-----------------|------------------|
{filas}

### 💡 Recomendación
{accion_sugerida_para_las_top_3}
```

5. **Entregar** la alerta por el canal configurado.

## Tasks utilizadas

| Task | Propósito |
|------|-----------|
| `notion.read_database` | Leer tareas activas |
| `llm.generate` | Compilar alerta y recomendaciones |

## Cron recomendado

```bash
openclaw cron add \
  --name "Stale Watch diario" \
  --agent rick-ops \
  --cron "0 21 * * *" \
  --tz America/Santiago \
  --session isolated \
  --timeout-seconds 90 \
  --message "Revisa las tareas activas en Notion. 1) Lee la base de tareas con notion.read_database. 2) Identifica tareas cuya última edición fue hace más de 3 días y cuyo estado NO sea Done o Archived. 3) Si no hay tareas estancadas, responde EXACTAMENTE: NO_REPLY. 4) Si hay, genera una tabla con nombre, responsable, días sin actividad y una recomendación para las top 3."
```

## Notas

- Se ejecuta a las 21:00 Chile (fin del día laboral).
- El umbral de 3 días es configurable en el mensaje del cron.
- Las tareas con estado "Blocked" o "Waiting" se incluyen pero se marcan
  como tal para no confundir con abandono.
- Usa `rick-ops` porque es una tarea operativa de monitoreo.
