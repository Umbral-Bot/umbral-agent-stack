# TOOLS — Rick (Umbral Agent Stack)

> Herramientas y convenciones del stack. Rick debe usar estas capacidades según el contexto.

## Worker tasks (Dispatcher → Worker)

| Task        | Descripción |
|-------------|-------------|
| `ping`      | Health check; responde echo. |
| `notion.poll_comments` | Lee comentarios de la página Control Room en Notion. |
| `notion.upsert_task`   | Crea o actualiza tareas en base de datos Notion. |

El Dispatcher encola tareas en Redis (`umbral:tasks:pending`) y el Worker las ejecuta vía HTTP. Requiere `WORKER_URL`, `WORKER_TOKEN`, `REDIS_URL`.

## Notion

- **Control Room:** Página donde Rick lee comentarios (poller a las XX:10). Configurada en Worker como `NOTION_CONTROL_ROOM_PAGE_ID`.
- **Dashboard Rick:** Página actualizada por el sistema para estado gerencial.
- **Bandeja Puente:** Mantenida por Enlace; estados Pendiente/En curso/Bloqueado/Resuelto.
- **Integración:** Usar API de Notion con `NOTION_API_KEY` para leer/escribir contenido y comentarios.

## OpenClaw

- **Gateway:** 24/7 en VPS; Telegram bot + Control UI (puertos 18789 ws, 18791 http).
- **Modelos:** Configurados vía `openclaw config`; Gemini, Claude, etc. según cuotas.
- **Workspace:** `~/.openclaw/workspace` — IDENTITY.md, SOUL.md, AGENTS.md, TOOLS.md.

## Redis

- Cola: `umbral:tasks:pending`
- Estado de tareas: traza por `trace_id`
- Requiere Redis en VPS (localhost o Docker).

## VM (Execution Plane)

- Worker FastAPI en `:8088` accesible por Tailscale (IP Tailscale de la VM).
- PAD/RPA: Power Automate Desktop para automatizaciones Windows (futuro).
- El Dispatcher intenta VM primero; si falla, puede usar Worker en VPS.

## Convenciones

- **Variables de entorno:** `~/.config/openclaw/env` en VPS.
- **Tests:** `python -m pytest tests -v` con `WORKER_TOKEN=test` (fakeredis).
- **Scripts:** `scripts/test_s1_contract.py`, `scripts/test_s2_dispatcher.py`, `scripts/vps/full-stack-up.sh`.
