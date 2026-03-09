# TOOLS — Rick (Umbral Agent Stack)

> Herramientas y convenciones del stack. Rick debe usar estas capacidades según el contexto.

## Worker tasks (Dispatcher → Worker)

| Task        | Descripción |
|-------------|-------------|
| `ping`      | Health check; responde echo. |
| `notion.poll_comments` | Lee comentarios de la página Control Room en Notion. |
| `notion.upsert_task`   | Crea o actualiza tareas en base de datos Notion. |
| `notion.write_transcript` | Escribe transcripción en Notion. |
| `notion.add_comment` | Agrega comentario a una página Notion. |
| `notion.update_dashboard` | Actualiza dashboard de Rick en Notion. |
| `notion.create_report_page` | Crea página de reporte en Notion. |
| `linear.create_issue` | Crea issue en Linear (title, team_key, description). |
| `linear.list_teams`   | Lista equipos en Linear. |
| `linear.update_issue_status` | Actualiza estado/comentario de un issue en Linear. |
| `llm.generate` | Genera texto con LLM (multi-provider: Claude, Gemini, Azure). |
| `research.web` | Búsqueda web con Google CSE o Tavily. |
| `composite.research_report` | Búsqueda + generación de reporte completo. |
| `figma.get_file` | Lee estructura y páginas de un archivo Figma. |
| `figma.get_node` | Lee nodos específicos por ID de un archivo Figma. |
| `figma.export_image` | Exporta frames/nodos como PNG/SVG/JPG/PDF. |
| `figma.add_comment` | Agrega comentario en un archivo Figma. |
| `figma.list_comments` | Lista comentarios de un archivo Figma. |
| `azure.audio.generate` | Genera audio TTS vía Azure OpenAI Realtime API. |
| `google.audio.generate` | Genera audio TTS vía Gemini API preview (`gemini-2.5-flash-preview-tts`). |
| `make.post_webhook` | Envía POST a webhook de Make.com. |
| `windows.pad.run_flow` | Ejecuta flujo de Power Automate Desktop en VM. |
| `windows.fs.*` | Operaciones de filesystem en la VM Windows. |
| `granola.process_transcript` | Procesa transcripción Granola → Notion (extrae action items, crea página). |
| `granola.create_followup` | Crea follow-up proactivo desde reunión: reminder, borrador de email, propuesta. |
| `document.create_word` | Genera archivo Word (.docx) desde plantilla o desde cero con python-docx/docxtpl. |
| `document.create_pdf` | Genera PDF desde HTML (weasyprint) o texto plano. |
| `document.create_presentation` | Genera presentación PowerPoint (.pptx) con python-pptx. |

## Agente Gpt-Rick (Azure AI Foundry Cursor)

Rick puede delegar tareas al agente **Gpt-Rick** publicado en Azure AI Foundry. Endpoints:

- **Responses API:** `https://cursor-api-david.services.ai.azure.com/api/projects/rick-api-david-project/applications/Gpt-Rick/protocols/openai/responses?api-version=2025-11-15-preview`
- **Activity Protocol:** `https://cursor-api-david.services.ai.azure.com/api/projects/rick-api-david-project/applications/Gpt-Rick/protocols/activityprotocol?api-version=2025-11-15-preview`

**Variables:** `GPT_RICK_API_KEY` o `AZURE_OPENAI_API_KEY` en `~/.config/openclaw/env`.

**Tests:**  
- `python3 scripts/test_gpt_rick_agent.py` — acceso al agente Gpt-Rick (Responses API).  
- `python3 scripts/test_gpt_realtime_audio.py` — audio con gpt-realtime (`cursor-api-david.cognitiveservices.azure.com`); guarda `assets/audio/rick_audio_prueba.wav` ("Hola, este es un audio de prueba para el proyecto de Rick").

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
- **Skill `openclaw-gateway`:** Ver `skills/openclaw-gateway/SKILL.md` para arquitectura del Gateway, integración Pi (pi-coding-agent), schema de `openclaw.json` (agents.list, bindings, channels), multi-agente y referencias a docs.openclaw.ai. Usar para dudas de config, varios agentes o GatewayRequestError / invalid config.

## Linear

- **API:** Rick crea issues vía `linear.create_issue` (encolar tarea o script `scripts/linear_create_issue.py`).
- **Equipos:** Usar `team_key` (ej. "UMB"). Ejecutar `linear.list_teams` para ver equipos.
- **Variable:** `LINEAR_API_KEY` en `~/.config/openclaw/env` (VPS).

## Granola

- **Pipeline:** Rick procesa transcripciones Granola → Notion vía `granola.process_transcript`.
- **Watcher:** Script `scripts/vm/granola_watcher.py` monitorea carpeta `GRANOLA_EXPORT_DIR` en la VM y envía archivos `.md` automáticamente al Worker.
- **Follow-up:** `granola.create_followup` genera reminders, borradores de email o propuestas desde action items extraídos.
- **Variables:** `GRANOLA_EXPORT_DIR`, `NOTION_GRANOLA_DB_ID` (DB destino; usa `NOTION_API_KEY` Rick) en el Worker.

## Document Generation

- **Word:** `document.create_word` — modo plantilla (docxtpl + Jinja2) o desde cero (python-docx).
- **PDF:** `document.create_pdf` — desde HTML (weasyprint) o texto plano (fpdf2).
- **PowerPoint:** `document.create_presentation` — slides con python-pptx, título/contenido/tabla.
- **Plantillas BIM:** `worker/templates/documents/propuesta_bim.docx` y `cotizacion_bim.docx`.
- **Variables:** sin variables de entorno requeridas; rutas de archivo como input.

## Figma

- **API:** Rick lee archivos, exporta frames e imágenes, y gestiona comentarios vía tasks `figma.*`.
- **Autenticación:** Personal Access Token en `FIGMA_API_KEY`.
- **file_key:** Se extrae de la URL de Figma: `figma.com/design/{file_key}/...`
- **Exportar:** `figma.export_image` soporta PNG, SVG, JPG, PDF con escala 1–4.
- **Comentarios:** `figma.add_comment` para review de diseño, `figma.list_comments` para auditar.

## Redis

- Cola: `umbral:tasks:pending`
- Estado de tareas: traza por `trace_id`
- Requiere Redis en VPS (localhost o Docker).

## VM (Execution Plane)

- Worker FastAPI en `:8088` (headless) y `:8089` (interactivo) accesibles por Tailscale.
- **Archivos en la VM:** tareas `windows.fs.*` (ensure_dirs, list, read_text, write_text) con política en `config/tool_policy.yaml` (ver rama/PR de Rick).
- PAD/RPA: Power Automate Desktop para flujos allowlisted (`windows.pad.run_flow`).
- El Dispatcher intenta VM primero; si falla, puede usar Worker en VPS.

## Convenciones

- **Variables de entorno:** `~/.config/openclaw/env` en VPS.
- **Tests:** `python -m pytest tests -v` con `WORKER_TOKEN=test` (fakeredis).
- **Scripts:** `scripts/test_s1_contract.py`, `scripts/test_s2_dispatcher.py`, `scripts/vps/full-stack-up.sh`.
