# Agent Board — Umbral Agent Stack

> Última actualización: 2026-03-04 por **cursor**
> Sprint activo: **S5**
> **HACKATHON — RONDA 3 EN CURSO**

## Estado del sistema

| Aspecto | Estado |
|---------|--------|
| Protocolo inter-agentes | ✅ Activo |
| VPS (Control Plane) | ✅ Redis + Dispatcher + Worker + 6 crons |
| Notion Poller daemon | ✅ Corriendo (PID activo, polling cada 60s) |
| Worker API | ✅ v0.4.0 — 24 handlers, 6 endpoints |
| Crons activos | 6 (dashboard, health, supervisor, poller, SIM research, SIM report) |
| PRs mergeados (hackathon) | 15 |
| VM (Execution Plane) | 🔴 Red caída (APIPA) — requiere intervención manual |

## Ronda 5 — Tareas Activas (2026-03-04)

| ID | Título | Asignado | Rama | Estado |
|----|--------|----------|------|--------|
| 019 | Error Alert System — Notificaciones push de fallos | codex | feat/codex-error-alerts | 📋 assigned |
| 020 | Team Workflow Engine — Flujos por equipo | github-copilot | feat/copilot-team-workflows | 📋 assigned |
| 021 | Scheduled Tasks Manager — Tareas programadas via Notion | antigravity | feat/antigravity-scheduled-tasks | 📋 assigned |

> Claude Code en pausa hasta que se restablezcan los créditos.

### Objetivo Ronda 5
Madurar el sistema: alertas de errores, workflows por equipo, y tareas programadas desde Notion.

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

## Worker v0.4.0 — 25 handlers

`ping` · `notion.*` (5) · `windows.*` (6) · `windows.fs.*` (5) · `system.*` (2) · `linear.*` (3) · `research.web` · `llm.generate` · **`composite.research_report`**

## Notas
- Agentes: Cursor (lead), Antigravity, Codex, GitHub Copilot, Claude Code.
- Cada agente tiene su clon: `C:\GitHub\umbral-agent-stack-<nombre>`
- Motor de búsqueda: Tavily. LLM: Gemini 2.5 Flash.
- Workflow: feature branch → PR → Cursor merge → deploy VPS
