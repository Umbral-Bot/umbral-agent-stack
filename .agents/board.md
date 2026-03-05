# Agent Board — Umbral Agent Stack

> Última actualización: 2026-03-05 por **cursor**
> Sprint activo: **R15**
> **HACKATHON — RONDA 15 EN CURSO**

## Estado del sistema

| Aspecto | Estado |
|---------|--------|
| Protocolo inter-agentes | ✅ Activo |
| VPS (Control Plane) | ✅ Redis + Dispatcher + Worker + 11 crons |
| Notion Poller daemon | ✅ Corriendo (PID activo, polling cada 60s) |
| Worker API | ✅ v0.4.0 — **42 handlers**, 10+ endpoints |
| Multi-LLM | ✅ Gemini + OpenAI + Anthropic (model routing activo) |
| Langfuse Tracing | ✅ Integrado (graceful degradation sin keys) |
| Rate Limiting | ✅ 60 RPM (configurable via RATE_LIMIT_RPM) |
| Scheduled Tasks | ✅ Redis sorted set, cron cada minuto |
| Quota Dashboard | ✅ GET /quota/status + reporte Notion |
| Crons activos | 11 (dashboard, health, supervisor, poller, SIM x2, digest, SIM-make, E2E, OODA, scheduled-tasks) |
| Tests | ✅ **847 passed**, 5 skipped |
| PRs mergeados (hackathon) | **66** (#2–#68) |
| PRs abiertos | **6** (#69–#74) |
| VM (Execution Plane) | ✅ v0.4.0 — reconectada |

## PRs abiertos

| PR | Título | Branch | Ronda |
|----|--------|--------|-------|
| #69 | fix: eliminate PytestCollectionWarning and FastAPI DeprecationWarning | `cursor/pytest-fastapi-lifespan-9a62` | R14 |
| #70 | fix: skills coverage detecta tareas de una sola palabra (ping) | `feat/skills-coverage-single-word` | R14 |
| #71 | fix: add document_generator test dependencies to pyproject.toml | `cursor/tests-document-generator-dependencias-8af0` | R14 |
| #72 | feat(R14): Enriquecimiento Bitácora — notion.enrich_bitacora_page + script | `cursor/bit-cora-contenido-enriquecido-4099` | R14 |
| #73 | ci: GitHub Actions workflow para pytest en push/PR a main | `cursor/workflow-ci-pytest-a6f3` | R15 |
| #74 | chore(R15): merge PRs #69, #70, #71 — pytest 847 passed, 0 failed | `cursor/fusi-n-prs-69-70-71-23e1` | R15 |

## Ronda 15 — En curso

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 065 | Integrar PRs R14 (#69–#71) y dejar pytest en verde | cursor-agent-cloud | 🔄 in_progress (PR #74) |
| 066 | CI: GitHub Actions workflow para pytest | cursor-agent-cloud | 🔄 in_progress (PR #73) |
| 067 | Bitácora: sección "En pocas palabras" en cada página | cursor-agent-cloud | ⏳ pending |
| 068 | Diagrama detallado del pipeline Notion → OpenClaw | cursor-agent-cloud | ⏳ pending |
| 069 | Integración main: pytest verde + CI | cursor-agent-cloud | ⏳ pending (depende de #74) |
| 070 | Actualizar board con estado R14/R15 | cursor-agent-cloud | 🔄 in_progress |

### Objetivo Ronda 15
Consolidar rondas anteriores: mergear PRs de R14, añadir CI con GitHub Actions, actualizar documentación y board.

## Ronda 14 — PRs abiertos

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 060 | Fix: document_generator test dependencies en pyproject.toml | cursor-agent-cloud | 🔄 PR #71 abierto |
| 061 | Fix: skills coverage detecta tareas de una sola palabra (ping) | cursor-agent-cloud | 🔄 PR #70 abierto |
| 062 | Fix: eliminar PytestCollectionWarning y FastAPI DeprecationWarning | cursor-agent-cloud | 🔄 PR #69 abierto |
| 063 | Bitácora: enriquecimiento del dashboard con contenido real | cursor-agent-cloud | 🔄 PR #72 abierto |
| 064 | Bitácora: resumen amigable para perfiles no técnicos | cursor-agent-cloud | ⏳ pending |

### Objetivo Ronda 14
Estabilización: arreglar warnings de pytest/FastAPI, dependencias de test, mejorar Bitácora.

## Ronda 13 — Completada ✅ (parcial)

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 055 | Auditoría de trazabilidad y gobernanza | cursor-agent-cloud | ✅ done (PR #68) |
| 056 | Dashboard de métricas de gobernanza | cursor-agent-cloud | ✅ done (PR #65) |
| 057 | Runbook operacional y checklist de gobernanza | cursor-agent-cloud | ✅ done (PR #66) |
| 058 | OpsLogger audit improvements — trace_id, input_summary, log rotation | cursor-agent-cloud | ✅ done (PR #67) |
| 059 | Poblar Bitácora Umbral Agent Stack en Notion | cursor-agent-cloud | ⏳ pending (requiere Notion API) |

### Objetivo Ronda 13
Gobernanza y auditoría: trazabilidad completa, runbook operacional, métricas, mejoras de OpsLogger.

## Ronda 12 — Completada ✅

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 050 | Google Calendar + Gmail Worker Handlers | cursor-agent-cloud | ✅ done (PR #61) |
| 051 | Granola Watcher — PowerShell installer, env loader y tests | cursor-agent-cloud | ✅ done (PR #60) |
| 052 | BIM Skills — IFC/IfcOpenShell, BIM Coordination, Speckle mejorado | cursor-agent-cloud | ✅ done (PR #62) |
| 053 | Skills Audit + Pytest Fixes + 100% Coverage | cursor-agent-cloud | ✅ done (PR #63) |
| 054 | Diseño pipeline RRSS con n8n | cursor-agent-cloud | ✅ done (PR #64) |

### Objetivo Ronda 12
Integración Google + Granola, skills BIM avanzados, audit de skills, pipeline RRSS.

## Ronda 11 — Completada ✅

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 042 | Skills BIM/AEC — Revit, Dynamo, Rhino, Navisworks, ACC, KUKA | cursor-agent-cloud | ✅ done (PR #52) |
| 043 | Skills automatización — Power Platform, n8n, Make, Copilot Studio | cursor-agent-cloud | ✅ done (PR #55) |
| 044 | Skills cloud/IA/data — Azure, Vertex, LangChain, MCP, big data | cursor-agent-cloud | ✅ done (PR #53) |
| 045 | Skills contenido/marketing — LinkedIn, marca personal, marketing | cursor-agent-cloud | ✅ done (PR #56) |
| 046 | Skills librerías open source — video, diagramas, scraping | cursor-agent-cloud | ✅ done (PR #54) |
| 047 | Skills personal desde Google Drive AI folder | cursor-agent-cloud | ✅ done (PR #51) |
| 048 | Granola → Notion pipeline con follow-up proactivo | cursor-agent-cloud | ✅ done (PR #58) |
| 049 | Document Generation — Word, PDF, PowerPoint | cursor-agent-cloud | ✅ done (PR #59) |

### Objetivo Ronda 11
Expansión masiva de skills: BIM, automatización, cloud/AI, marketing, open source, Google Drive, Granola, documentos.

## Ronda 10 — Completada ✅

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 040 | Skill Builder Pipeline — generar SKILL.md desde docs | cursor-agent-cloud | ✅ done (PR #50) |

### Objetivo Ronda 10
Pipeline para generar SKILL.md automáticamente a partir de documentación existente.

## Ronda 9 — Completada ✅

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 035 | OpenClaw Skills + Figma Tests | cursor-agent-cloud | ✅ done (PR #49) |
| 036 | OpenClaw Skills — Notion + Windows | codex | ✅ done (PR #46) |
| 037 | Tools Inventory endpoint + Notion/VPS sync | antigravity | ✅ done (PR #48) |
| 038 | Skills Validation + Figma E2E + Coverage Report | claude-code | ✅ done (PR #47) |
| 039 | OpenClaw Skills — LLM, Make, Observability | github-copilot | ✅ done (PR #45) |

### Objetivo Ronda 9
OpenClaw skills completos, validación E2E, Figma tests, inventario de herramientas.

## Ronda 8 — Completada ✅

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 031 | Linear Webhooks → Dispatcher enqueue | codex | ✅ done (PR #41) |
| 032 | Provider Health Dashboard — GET /providers/status | github-copilot | ✅ done (PR #40) |
| 033 | Multimodel E2E + escalation + provider detection | claude-code | ✅ done (PR #39) |

### Objetivo Ronda 8
Multi-modelo real con providers (GitHub Models, Azure AI Foundry, Vertex AI), Linear webhooks, health dashboard. PRs adicionales: #35 (GitHub Models), #36 (modelos 2026), #37 (Azure AI Foundry), #38 (Vertex AI), #43 (Azure Audio TTS), #44 (OpenClaw Proxy).

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
Multi-modelo real: Worker habla con Gemini + OpenAI + Anthropic, Dispatcher enruta con ModelRouter, quota dashboard visual. Dependencias: 023 → 024 → 026.

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

## Rondas anteriores completadas

### Ronda 1 (Hackathon base)
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

### Ronda 2
| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| PR #11 | Worker/Dispatcher supervisor | github-copilot | ✅ merged |
| PR #12 | Notion Poller daemon + cron wrapper | claude-code | ✅ merged + deployed |
| PR #13 | Notion Poller --once flag + health check | antigravity | ✅ merged + deployed |
| PR #14 | SIM report cron + tests | codex | ✅ merged + deployed |
| PR #15 | POST /enqueue + GET /task/{id}/status API | github-copilot | ✅ merged |

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

## Worker v0.4.0 — 42 handlers

`ping` · `notion.*` (7) · `windows.*` (6) · `windows.fs.*` (5) · `system.*` (2) · `linear.*` (3) · `research.web` · `llm.generate` · `composite.research_report` · `make.post_webhook` · `azure.audio.generate` · `figma.*` (5) · `document.*` (3) · `granola.*` (2) · `google.calendar.*` (2) · `gmail.*` (2)

## Pendientes explícitamente diferidos

| Item | Razón |
|------|-------|
| VM PAD/Power Automate | Requiere instalación manual de PAD en VM |
| Telegram como canal | Fuera del scope del hackathon |
| Merge PRs R14 (#69–#72) | Pendiente revisión y CI verde |

## Bitácora (últimas entradas)

| Fecha | Entrada |
|-------|---------|
| 2026-03-05 | **Estado R14/R15** — Board actualizado: 42 handlers, 847 tests, 66 PRs mergeados, 6 PRs abiertos (#69–#74). Rondas R13 (gobernanza) completada, R14 (estabilización) con PRs abiertos, R15 (consolidación + CI) en curso. |

## Notas
- Agentes: Cursor (lead), Antigravity, Codex, GitHub Copilot, Claude Code.
- Cada agente tiene su clon: `C:\GitHub\umbral-agent-stack-<nombre>`
- Motor de búsqueda: Tavily. LLM: Gemini 2.5 Flash.
- Workflow: feature branch → PR → Cursor merge → deploy VPS
