# Rick: estado actual y capacidades

> Doc de referencia para que Rick (o quien opere el stack) conozca el estado operativo y qué puede hacer. Actualizar cuando cambie el diseño o se añadan capacidades.

## Dónde leer más (en orden)

1. **Runbook operativo** — [docs/62-operational-runbook.md](62-operational-runbook.md)  
   Env vars (§1.4), verificación VPS y VM (§7), crons (§2), troubleshooting (§5). Es la fuente de verdad para ops.

2. **Convención con Enlace** — [docs/18-notion-enlace-rick-convention.md](18-notion-enlace-rick-convention.md)  
   Cómo coordinarte con Enlace, qué responde Rick automáticamente, regla anti-loop, alcance de cada uno.

3. **Board y tareas** — [.agents/board.md](../.agents/board.md)  
   Estado del sprint, tareas cerradas y pendientes.

---

## Qué corre en producción

| Componente | Dónde | Función |
|------------|--------|---------|
| **Worker** | VPS (puerto 8088) | API FastAPI: ejecuta tareas (`/run`), health, quota, tasks, etc. |
| **Dispatcher** | VPS | Control Plane: encola desde Redis, envía a Worker (y opcionalmente a VM si `WORKER_URL_VM` está definido). |
| **Notion poller daemon** | VPS | Pollea Control Room cada 60 s, smart reply (research + LLM), encola tareas. |
| **Worker VM** (opcional) | Windows (NSSM, 8088) | Execution Plane: tareas improvement/lab, windows.fs.*, PAD si está instalado. |
| **Redis** | VPS | Cola de tareas, scheduled tasks, estado. |
| **Crons** | VPS | Supervisor (cada 5 min), dashboard Notion (cada 15 min), health-check (30 min), SIM, digest, E2E, etc. |

---

## Capacidades recientes / cambios de diseño

- **Git en la VPS:** Rick no trabaja en `main`. Cambios desde la VPS: rama **`rick/vps`** → push → PR → David/Cursor hace el merge → en la VPS `git checkout main && git pull origin main`. Detalle: [docs/62-operational-runbook.md](62-operational-runbook.md) §7.0 y [34-rick-github-token-setup.md](34-rick-github-token-setup.md).
- **Avisos del supervisor a Notion:** Cuando el supervisor reinicia Worker o Dispatcher, postea un comentario en Notion (Control Room por defecto, o en la página de `NOTION_SUPERVISOR_ALERT_PAGE_ID` si se define). Función `post_notion_alert()` en `scripts/vps/supervisor.sh`; JSON seguro vía Python.
- **Verificación VPS y VM:** Runbook §7 tiene el checklist para comprobar que ambas están al día con el repo (`git pull`, `pip install -r worker/requirements.txt`, reinicio del Worker si aplica).
- **Control Room:** Puede ser uso mixto (comunicación Rick/Enlace/David + avisos operativos del supervisor). Si se prefiere solo comunicación, definir `NOTION_SUPERVISOR_ALERT_PAGE_ID` en la VPS para que los avisos vayan a otra página.

Para el listado completo de capacidades de Rick (smart reply, SIM, digest, report pages, etc.) ver [docs/18-notion-enlace-rick-convention.md](18-notion-enlace-rick-convention.md) sección "Capacidades actuales de Rick".

---

## Agente Gpt-Rick (Azure AI Foundry Cursor)

Rick puede asignar tareas al agente **Gpt-Rick** publicado en Azure AI Foundry. Endpoints:

- **Responses API:** POST `.../protocols/openai/responses?api-version=2025-11-15-preview` — chat stateless con el agente.
- **Activity Protocol:** para Microsoft 365 / Teams.

**Variables:** `GPT_RICK_API_KEY` o `AZURE_OPENAI_API_KEY` en env. **Test:** `python3 scripts/test_gpt_rick_agent.py`.

---

## Tareas del Worker (resumen)

Las tareas disponibles se listan en `GET /tasks` (o en el health). Incluyen entre otras: `ping`, `notion.add_comment`, `notion.poll_comments`, `notion.update_dashboard`, `notion.write_transcript`, `research.web`, `llm.generate`, `figma.*`, `windows.fs.*` (en VM), etc. Detalle en README y en el runbook.

---

## Si algo no cuadra

1. Comprobar runbook §7 (VPS y VM al día con el repo).
2. Revisar env en VPS: `~/.config/openclaw/env` (WORKER_TOKEN, NOTION_*, REDIS_URL, etc.).
3. Ejecutar `bash scripts/vps/supervisor.sh` en la VPS para ver estado de Redis, Worker y Dispatcher.
4. Si el Worker falla al arrancar: `pip install -r worker/requirements.txt` y reiniciar.
