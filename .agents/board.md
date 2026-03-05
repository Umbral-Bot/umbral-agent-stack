# Agent Board — Umbral Agent Stack

> Última actualización: 2026-03-05 por **cursor**
> Sprint activo: **Hackathon — Rondas completadas R1–R16**

## Estado del sistema

| Aspecto | Estado |
|---------|--------|
| Protocolo inter-agentes | ✅ Activo |
| VPS (Control Plane) | ✅ Redis + Dispatcher + Worker + 11 crons |
| Notion Poller daemon | ✅ Corriendo (PID activo, polling cada 60s) |
| Worker API | ✅ v0.4.0 — 43 handlers, 10+ endpoints |
| Multi-LLM | ✅ Gemini + OpenAI + Anthropic (model routing activo) |
| Langfuse Tracing | ✅ Integrado (graceful degradation sin keys) |
| Rate Limiting | ✅ 60 RPM (configurable via RATE_LIMIT_RPM) |
| Scheduled Tasks | ✅ Redis sorted set, cron cada minuto |
| Quota Dashboard | ✅ GET /quota/status + reporte Notion |
| Crons activos | 11 (dashboard, health, supervisor, poller, SIM x2, digest, SIM-make, E2E, OODA, scheduled-tasks) |
| Tests | ✅ 881 passed, 5 skipped |
| CI (GitHub Actions) | ✅ pytest en push/PR a main (Python 3.11 + 3.12) |
| PRs mergeados (hackathon) | 66 |
| PRs abiertos | 8 (#69–#76) |
| Bitácora Notion | ✅ 22 entradas enriquecidas con "En pocas palabras" |
| VM (Execution Plane) | ✅ v0.4.0 — 25 handlers — reconectada |

## Ronda 16 — En curso

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 072 | Board + Bitácora + CI docs | cursor-agent-cloud | 🔄 in progress |

### Objetivo Ronda 16
Cerrar documentación: board actualizado R14–R16, Bitácora con entrada de cierre, README/CONTRIBUTING con instrucciones de tests y CI.

## Ronda 15 — Completada ✅

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 065 | Consolidar PRs abiertos (#69-#71) | cursor-agent-cloud | ✅ done (PR #74) |
| 066 | CI — GitHub Actions pytest workflow | cursor-agent-cloud | ✅ done (PR #73) |
| 067 | Resolver test failures post-merge | cursor-agent-cloud | ✅ done |
| 068 | Actualizar pyproject.toml test deps | cursor-agent-cloud | ✅ done |
| 069 | Eliminar warnings de pytest/FastAPI | cursor-agent-cloud | ✅ done (PR #69) |
| 070 | Actualizar board con estado R8–R15 | cursor-agent-cloud | ✅ done (PR #76) |

### Objetivo Ronda 15
Consolidación: todos los tests en verde, CI automatizado, board actualizado, warnings eliminados.

## Ronda 14 — Completada ✅

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 060 | Document generator test dependencies | cursor-agent-cloud | ✅ done (PR #71) |
| 061 | Skills coverage — single-word tasks | cursor-agent-cloud | ✅ done (PR #70) |
| 062 | Pytest/FastAPI warnings cleanup | cursor-agent-cloud | ✅ done (PR #69) |
| 063 | Bitácora: enriquecimiento con detalle, diagramas, tablas | cursor-agent-cloud | ✅ done (PR #72) |
| 064 | Bitácora: resumen amigable "En pocas palabras" | cursor-agent-cloud | ✅ done (PR #72) |

### Objetivo Ronda 14
Estabilización: corregir tests, eliminar warnings, enriquecer Bitácora con contenido técnico y no técnico.

## Ronda 13 — Completada ✅

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 055 | Auditoría de trazabilidad y gobernanza | cursor-agent-cloud | ✅ done (PR #68) |
| 056 | Governance Metrics Report | cursor-agent-cloud | ✅ done (PR #65) |
| 057 | Runbook operacional + troubleshooting | cursor-agent-cloud | ✅ done (PR #66) |
| 058 | OpsLogger audit improvements | cursor-agent-cloud | ✅ done (PR #67) |
| 059 | Bitácora — poblamiento inicial | cursor-agent-cloud | ✅ done |

### Objetivo Ronda 13
Gobernanza y auditoría: trazabilidad end-to-end, métricas, runbook, OpsLogger mejorado, Bitácora poblada.

## Ronda 12 — Completada ✅

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 050 | Google Calendar + Gmail Worker Handlers | cursor-agent-cloud-1 | ✅ done (PR #61) |
| 051 | Granola VM Service (PowerShell) | cursor-agent-cloud | ✅ done (PR #60) |
| 052 | BIM Skills — IFC/Speckle | cursor-agent-cloud | ✅ done (PR #62) |
| 053 | Skills Audit + Pytest + Coverage | cursor-agent-cloud | ✅ done (PR #63) |
| 054 | Pipeline RRSS con n8n | cursor-agent-cloud | ✅ done (PR #64) |

### Objetivo Ronda 12
Integraciones: Google Calendar/Gmail, Granola VM, skills BIM avanzados, auditoría de skills, diseño pipeline RRSS.

## Ronda 11 — Completada ✅

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 042 | Skills BIM/AEC — Revit, Dynamo, Rhino, Navisworks, ACC, KUKA | cursor-agent-cloud-1 | ✅ done (PR #52) |
| 043 | Skills Automation — Power Platform, n8n, Make, Copilot Studio | cursor-agent-cloud-2 | ✅ done (PR #55) |
| 044 | Skills Cloud/AI/Data — Azure, Vertex, Langchain, MCP | cursor-agent-cloud-3 | ✅ done (PR #53) |
| 045 | Skills Content/Marketing — LinkedIn, marca personal, Notion | cursor-agent-cloud-4 | ✅ done (PR #56) |
| 046 | Skills Open Source — video, diagramas, imágenes, scraping | cursor-agent-cloud-5 | ✅ done (PR #54) |
| 047 | Skills Personal from Drive | cursor-agent-cloud-6 | ✅ done (PR #57) |
| 048 | Granola → Notion Pipeline | cursor-agent-cloud-7 | ✅ done (PR #58) |
| 049 | Document Generation — Word, PDF, PowerPoint | cursor-agent-cloud-8 | ✅ done (PR #59) |

### Objetivo Ronda 11
Skills masivos: 50+ skills en BIM, automatización, cloud/AI, contenido, open source. Pipelines Granola→Notion y generación de documentos.

## Ronda 10 — Completada ✅

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 040 | OpenClaw Skill Builder Pipeline | claude-code | ✅ done (PR #50) |
| 041 | Personal Skills from Google Drive | antigravity | ✅ done (PR #51) |

### Objetivo Ronda 10
Automatización de creación de skills a partir de documentación. Skills personales del equipo.

## Ronda 9 — Completada ✅

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 035 | OpenClaw Skills + Figma Tests | cursor-agent-cloud | ✅ done (PR #47) |
| 036 | OpenClaw Skills — Notion + Windows | codex | ✅ done (PR #46) |
| 037 | Dashboard + Tools Sync to Notion | antigravity | ✅ done (PR #48) |
| 038 | Skills Validation E2E | claude-code | ✅ done (PR #49) |
| 039 | Skills — LLM, Make, Observability | github-copilot | ✅ done (PR #45) |

### Objetivo Ronda 9
OpenClaw workspace skills para todos los handlers. Figma tests. Tools inventory endpoint.

## Ronda 8 — Completada ✅

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 031 | Linear Webhooks → Dispatcher | codex | ✅ done (PR #41) |
| 032 | Provider Health Dashboard | antigravity | ✅ done (PR #40) |
| 033 | Multi-agent E2E Validation | claude-code | ✅ done (PR #39) |
| — | Azure Foundry Provider | cursor | ✅ done (PR #37) |
| — | Real Model Names 2026 | cursor | ✅ done (PR #36) |
| — | GitHub Models Provider | cursor | ✅ done (PR #35) |
| — | Real Inventory Vertex + Haiku | cursor | ✅ done (PR #38) |
| — | OpenClaw Proxy Provider | github-copilot | ✅ done (PR #44) |
| — | Azure Audio TTS | github-copilot | ✅ done (PR #43) |

### Objetivo Ronda 8
Multi-modelo real: Azure Foundry, GitHub Models, Vertex AI. Linear webhooks. Provider health dashboard.

## Ronda 7 — Completada ✅

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 027 | Langfuse Tracing — Instrumentar LLM calls | codex | ✅ done (PR #30) |
| 028 | OODA Report con Langfuse — Reporte semanal | github-copilot | ✅ done (PR #32) |
| 029 | Hardening Final — Rate limiting + sanitización | antigravity | ✅ done (PR #34) |
| 030 | E2E Integration Final — Validación completa | claude-code | ✅ done (PR #31) |

### Objetivo Ronda 7
Cerrar brechas de observabilidad (Langfuse) y seguridad (rate limiting, sanitización, secrets audit). Validación final.

## Ronda 6 — Completada ✅

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 023 | Multi-LLM Worker — OpenAI + Anthropic + Gemini | codex | ✅ done (PR #27) |
| 024 | Dispatcher Model Routing — Integrar al flujo real | github-copilot | ✅ done (PR #28) |
| 025 | Quota Dashboard — Reporte de uso en Notion | antigravity | ✅ done (PR #33) |
| 026 | Multi-Model E2E + Scheduled Tasks Validation | claude-code | ✅ done (PR #29) |

### Objetivo Ronda 6
Multi-modelo real: Worker habla con Gemini + OpenAI + Anthropic, Dispatcher enruta con ModelRouter, quota dashboard visual.

## Ronda 5 — Completada ✅

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 019 | Error Alert System — Notificaciones push de fallos | codex | ✅ done (PR #23) |
| 020 | Team Workflow Engine — Flujos por equipo | github-copilot | ✅ done (PR #24) |
| 021 | Scheduled Tasks Manager — Tareas programadas via Notion | antigravity | ✅ done (PR #26) |
| 022 | E2E Validation Suite — Prueba completa en producción | claude-code | ✅ done (PR #25) |

## Ronda 4 — Completada ✅

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 016 | Task History API + Redis Pagination | codex | ✅ done (PR #21) |
| 017 | Make.com Webhook Integration — SIM Pipeline | github-copilot | ✅ done (PR #20) |
| 018 | Notion Result Poster (smart reply + composite) | antigravity | ✅ done (PR #22) |

## Ronda 3 — Completada ✅

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 012 | Smart Notion Reply Pipeline | claude-code | ✅ done (PR #18) |
| 013 | Daily Activity Digest + Notion Post | github-copilot | ✅ done (PR #17) |
| 014 | Webhook Callback System | codex | ✅ done (PR #16) |
| 015 | Composite Task Handler (Research Report) | antigravity | ✅ done (PR #19) |

## Ronda 2 — Completada ✅

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| PR #11 | Worker/Dispatcher supervisor | github-copilot | ✅ merged |
| PR #12 | Notion Poller daemon + cron wrapper | claude-code | ✅ merged + deployed |
| PR #13 | Notion Poller --once flag + health check | antigravity | ✅ merged + deployed |
| PR #14 | SIM report cron + tests | codex | ✅ merged + deployed |
| PR #15 | POST /enqueue + GET /task/{id}/status API | github-copilot | ✅ merged |

## Ronda 1 (Hackathon base) — Completada ✅

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 001 | Diagnóstico completo + script + fixes | cursor | ✅ done |
| 002 | Verificar/activar infraestructura VPS | cursor | ✅ done |
| 003 | Mejoras de código — Poller inteligente + docs | antigravity | ✅ done |
| 004 | Integraciones — LiteLLM, cuotas, Notion | github-copilot | ✅ done |
| 005 | Activar OpsLogger + persistencia | cursor | ✅ done |
| 006 | Notion Poller inteligente (clasificar+encolar) | antigravity | ✅ done |
| 007 | Conectar LLM (Gemini 2.5 Flash) al Worker | cursor | ✅ done |
| 008 | Task handler research.web (Tavily) | cursor | ✅ done |
| 009 | SIM daily cron (3x/día research+resumen) | cursor | ✅ done |
| 010 | Reporte diario SIM + tests | codex | ✅ done |
| 011 | Resiliencia Dispatcher + Poller clasificador | claude-code | ✅ done |

## VPS — Crontab activo

| Frecuencia | Script | Función |
|------------|--------|---------|
| */15 min | dashboard-cron.sh | Dashboard Notion |
| */30 min | health-check.sh | Health check Redis/Worker/Dispatcher |
| */5 min | supervisor.sh | Auto-restart Worker/Dispatcher |
| */5 min | notion-poller-cron.sh | Watchdog daemon Notion Poller |
| 8:00, 14:00, 20:00 | sim-daily-cron.sh | SIM research (Tavily) |
| 8:30, 14:30, 20:30 | sim-report-cron.sh | SIM report (LLM + Notion) |
| 22:00 | daily-digest-cron.sh | Digest diario (Redis → LLM → Notion) |

## Worker v0.4.0 — 43 handlers

| Dominio | Handlers |
|---------|----------|
| Core | `ping` |
| Notion | `notion.write_transcript` · `notion.add_comment` · `notion.poll_comments` · `notion.upsert_task` · `notion.update_dashboard` · `notion.create_report_page` · `notion.enrich_bitacora_page` |
| Windows | `windows.pad.run_flow` · `windows.open_notepad` · `windows.write_worker_token` · `windows.firewall_allow_port` · `windows.start_interactive_worker` · `windows.add_interactive_worker_to_startup` |
| Windows FS | `windows.fs.ensure_dirs` · `windows.fs.list` · `windows.fs.read_text` · `windows.fs.write_text` · `windows.fs.write_bytes_b64` |
| Observability | `system.ooda_report` · `system.self_eval` |
| Linear | `linear.create_issue` · `linear.list_teams` · `linear.update_issue_status` |
| Research + LLM | `research.web` · `llm.generate` · `composite.research_report` |
| Integrations | `make.post_webhook` · `azure.audio.generate` |
| Figma | `figma.get_file` · `figma.get_node` · `figma.export_image` · `figma.add_comment` · `figma.list_comments` |
| Documents | `document.create_word` · `document.create_pdf` · `document.create_presentation` |
| Granola | `granola.process_transcript` · `granola.create_followup` |
| Google | `google.calendar.create_event` · `google.calendar.list_events` |
| Gmail | `gmail.create_draft` · `gmail.list_drafts` |

## Pendientes explícitamente diferidos

| Item | Razón |
|------|-------|
| VM PAD/Power Automate | Requiere instalación manual de PAD en VM |
| Telegram como canal | Fuera del scope del hackathon |

## Notas
- Agentes: Cursor (lead), Antigravity, Codex, GitHub Copilot, Claude Code.
- Cada agente tiene su clon: `C:\GitHub\umbral-agent-stack-<nombre>`
- Motor de búsqueda: Tavily. LLM: Gemini 2.5 Flash.
- Workflow: feature branch → PR → Cursor merge → deploy VPS
- Bitácora: https://www.notion.so/umbralbim/85f89758684744fb9f14076e7ba0930e
