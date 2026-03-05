# Agent Board — Umbral Agent Stack

> Última actualización: 2026-03-06 por **cursor**
> Sprint activo: **R17**
> **RONDA 17 — Post-R16: Notion, changelog, runbook, script ramas**

## Estado del sistema

| Aspecto | Estado |
|---------|--------|
| Protocolo inter-agentes | ✅ Activo |
| VPS (Control Plane) | ✅ Redis + Dispatcher + Worker + 11 crons |
| Notion Poller daemon | ✅ Corriendo (PID activo, polling cada 60s) |
| Worker API | ✅ v0.4.0 — 28 handlers, 10+ endpoints |
| Multi-LLM | ✅ Gemini + OpenAI + Anthropic (model routing activo) |
| Langfuse Tracing | ✅ Integrado (graceful degradation sin keys) |
| Rate Limiting | ✅ 60 RPM (configurable via RATE_LIMIT_RPM) |
| Scheduled Tasks | ✅ Redis sorted set, cron cada minuto |
| Quota Dashboard | ✅ GET /quota/status + reporte Notion |
| Crons activos | 11 (dashboard, health, supervisor, poller, SIM x2, digest, SIM-make, E2E, OODA, scheduled-tasks) |
| Tests | ✅ 900 passed (tras PR #96; 34 tests Bitácora) |
| PRs mergeados (hackathon) | 50+ (#91–#96 en main) |
| PRs obsoletos cerrados | 11 (limpieza R16-080, inventario en docs/branches-cerrados-inventario.md) |
| CI | ✅ GitHub Actions pytest (Python 3.11 + 3.12) |
| VM (Execution Plane) | ✅ v0.4.0 — 25 handlers — reconectada |

## Ronda 16 — Cerrada

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 077 | Cierre integración main — pytest verde, merge PRs 69–73 | cursor | ✅ done (integrado via PR #80) |
| 078 | Board + Bitácora estado final R16 | cursor | ✅ done (board actualizado) |
| 079 | Merge final a main y verificación CI | codex | ✅ done |
| 080 | Limpieza de PRs y documentación (README, board) | github-copilot | ✅ done (11 PRs cerrados, CI + README) |
| 081 | Capitalizar trabajo en ramas | codex | ✅ done (PR #86) |
| 082 | Capitalizar PRs cerrados — inventario de ramas | github-copilot | ✅ done (PR #85) |
| 083 | Análisis de contenido perdido en ramas | antigravity | ✅ done (PR #87) |
| 084 | Recuperar rate limiter por provider | codex | ✅ done (PR #90) |
| 085 | Recuperar scripts enriquecimiento Bitácora | github-copilot | ✅ done (PR #89) |
| 086 | Recuperar browser automation VM plan + skill | antigravity | ✅ done (PR #88) |
| 087 | Merge ordenado + verificación final (main verde) | codex | ✅ done (main: #85–#90 merged, pytest 866) |
| 088 | Cierre Bitácora: doc scripts + 9 funciones con firma | github-copilot | ✅ done (bitacora-scripts.md) |
| 089 | Resumen cierre R16 + guía borrado ramas | antigravity | ✅ done (PR #92: r16-cierre-resumen, guia-borrar-ramas) |

R16 cerrado — PRs mergeados: #85–#90. Docs R16/R17 mergeados: #91 (bitacora-scripts), #92 (resumen+guía ramas), #93–#96 (script ramas, changelog, runbook, Notion). pytest: 900 passed.

## Ronda 17 — Cerrada

| ID | Tarea | Agente | Rama | Estado |
|----|--------|--------|------|--------|
| 090 | Implementar 9 funciones Notion para Bitácora | claude-code | `claude/090-implementar-notion-bitacora` | ✅ done (PR #96, 900 tests) |
| 091 | Script dry-run borrado ramas (generar comandos git) | codex | `codex/091-script-borrado-ramas` | ✅ done (PR #93) |
| 092 | Changelog / Estado R16 en README | github-copilot | `copilot/092-changelog-r16` | ✅ done |
| 093 | Runbook: Bitácora + browser automation | antigravity | `antigravity/093-runbook-bitacora-browser` | ✅ done (PR #95) |

## Ronda 18 — Cerrada

| ID | Tarea | Agente | Rama | Estado |
|----|--------|--------|------|--------|
| 094 | Dashboard Notion: actualizar con seguimiento R16/R17 | codex | `codex/094-dashboard-notion-seguimiento` | ✅ done (PR #97) |
| 095 | Actualizar r16-cierre-resumen + marcar R18 cerrada | codex | `codex/095-actualizar-docs-board` | ✅ done (PR #98) |

R18 cerrada — dashboard Notion actualizado (PR #97).

## Ronda 12 — En curso

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 050 | Google Calendar + Gmail Worker Handlers | cursor-agent-cloud-1 | ✅ done |

## Ronda 11 — Completada ✅

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 042 | Skills BIM/AEC — Revit, Dynamo, Rhino, Navisworks, ACC, KUKA | cursor-agent-cloud-1 | ✅ done (PR #52) |

## Ronda 9 — Completada ✅

| ID | Título | Asignado | Estado |
|----|--------|----------|--------|
| 035 | OpenClaw Skills + Figma Tests | cursor-agent-cloud | ✅ done |

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

## Logros acumulados Ronda 3

### Claude Code
- `dispatcher/smart_reply.py` — research.web + llm.generate + notion.add_comment en pipeline
- Cuando David pregunta en Notion, Rick ahora busca y responde de verdad

### GitHub Copilot
- `scripts/daily_digest.py` — escanea Redis, genera resumen LLM, postea en Notion a las 22:00

### Codex
- `dispatcher/service.py` — callback_url fire-and-forget con retry
- POST /enqueue acepta callback_url para Make.com/n8n

### Antigravity
- `worker/tasks/composite.py` — handler #25 que orquesta research+LLM en un solo comando
- Profundidad configurable: quick/standard/deep

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

## Logros acumulados del hackathon

### Cursor (Lead)
- Flujo e2e verificado: Enqueue → Dispatcher → Worker → Complete
- Dashboard, .env, Tailscale, Notion API: todo arreglado
- research.web (Tavily) + llm.generate (Gemini 2.5 Flash) implementados
- SIM daily cron, 6 crons productivos en VPS
- 15 PRs coordinados y mergeados

### Antigravity
- Intent classifier (question/task/instruction/echo)
- Team routing por @mención y keyword scoring
- Notion Poller --once flag + health check
- 33 tests unitarios puros

### Claude Code (Opus 4.6)
- Fire-and-forget en daemon threads (Notion/Linear)
- Retry automático con retry_count en envelope
- Notion Poller daemon (60s loop, PID file, SIGTERM handling)
- Graceful connection refused

### GitHub Copilot
- Quota usage report
- Worker/Dispatcher supervisor
- POST /enqueue + GET /task/{id}/status (Worker v0.4.0)
- Health check cron

### Codex
- SIM daily report mejorado + Notion posting
- SIM report cron + tests
- test_research_handler + test_llm_handler

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

## Worker v0.4.0 — 28 handlers

`ping` · `notion.*` (6) · `windows.*` (6) · `windows.fs.*` (5) · `system.*` (2) · `linear.*` (3) · `research.web` · `llm.generate` · `composite.research_report` · `make.post_webhook` · `observability.*` (2)

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
