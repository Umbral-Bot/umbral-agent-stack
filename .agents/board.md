# Agent Board — Umbral Agent Stack

> Última actualización: 2026-03-23 por **codex**
> Sprint activo: **R23**
> **Coordinación:** **Cursor** retoma el lead. Codex cerró la capitalización R23 (`2026-03-24-001`), limpió ramas/PRs `codex/*` y no dejó follow-ups nuevos de ese frente.
> **RONDA 23 — capitalización Codex cerrada**.

## Estado del sistema (actualizado 2026-03-07 — auditoría en vivo)

| Aspecto | Estado |
|---------|--------|
| Protocolo inter-agentes | ✅ Activo |
| VPS (Control Plane) | ✅ Redis + Dispatcher + Worker + 12 crons (branch `rick/vps`) |
| Notion Poller daemon | ✅ Corriendo (PID 269682, desde 2026-03-04) |
| Worker API VPS | ✅ v0.4.0 — 43 handlers — responde directo |
| Worker API VM | ⚠️ `8088`: health+ping OK pero `/providers` y `/quota` siguen en 503 hasta restart privilegiado; `8089` ya actualizado y smoke OK |
| Multi-LLM | ✅ Gemini 2.5 Flash operativo (llamada directa OK) |
| OpsLogger | ✅ 213 eventos en ~/.config/umbral/ops_log.jsonl |
| Crons activos | 12 (dashboard, health, supervisor, poller, sim-daily, sim-report, digest, sim-make, E2E, OODA, scheduled-tasks, quota-guard) |
| Tests | ✅ 900 passed (PR #96) |
| CI | ✅ GitHub Actions pytest (Python 3.11 + 3.12) |
| **E2E Dispatcher→Worker** | ✅ OK — token fix 2026-03-08 (PR #106) |
| VM SSH/WinRM | ❌ Puertos 22/5985 cerrados — solo :8088 abierto |
| Cuotas Redis | ❌ Vacías — Dispatcher no despacha exitosamente |

## Trabajo vivo

Regularización `UMB-132` (2026-03-22): se cerraron task files históricos que habían quedado `assigned` o `blocked` pese a corresponder a rondas cerradas o diagnósticos archivados. La coordinación activa queda reducida a las tareas realmente vivas.

| ID | Tarea | Agente | Estado |
|----|-------|--------|--------|
| 2026-03-09-002 | Recomendaciones Cursor para orquestacion y politica de ejecucion de Rick | cursor | assigned |
| 2026-03-22-001 | Diagnóstico env Rick vs local — Codex define canónicos | codex | ✅ done |
| 2026-03-22-002 | Super diagnóstico exhaustivo del sistema | codex | ✅ done (PR #126) |
| 2026-03-22-003 | Fix hallazgos super diagnóstico — VM /run y auto-issues | codex | ✅ done (PR #127) |
| 2026-03-23-001 | Calendar/Gmail: env VPS + verificación + seguimiento post diagnóstico | codex | ✅ done |
| 2026-03-23-002 | UMB-141: completar trazabilidad de runtime para enriquecer auto-issues | codex | ✅ done |
| 2026-03-23-003 | UMB-140: endurecer auto-issues con deduplicacion y proyecto canonico | codex | ✅ done |
| 2026-03-23-004 | UMB-148: retirar Google Custom Search como path primario de discovery web | codex | ✅ done |
| 2026-03-23-005 | Super diagnostico exhaustivo de interconectividad y gobernanza operativa | codex | ✅ done |
| 2026-03-23-006 | Fase 0: estabilizacion base, merge, deploy y smoke post-diagnostico | codex | blocked (runtime-main sync OK; 8089 OK; 8088 requiere restart privilegiado) |
| 2026-03-24-001 | Lead temporal Codex — capitalizar hallazgos + cerrar ramas codex/* + Claude si aplica | codex | ✅ done |

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

## Ronda 19 — Cerrada

| ID | Tarea | Estado |
|----|--------|--------|
| 096 | Supervisor: verificar aviso Notion | ✅ done — POST /run, sleep 4, JSON seguro; aviso operativo en VPS |
| 097 | Supervisor: post_notion_alert() + NOTION_SUPERVISOR_ALERT_PAGE_ID | ✅ done — integrado en main (67733e4). PR #99 cerrado como Superseded |

**Nota:** Para mantener la Control Room solo para comunicación, definir `NOTION_SUPERVISOR_ALERT_PAGE_ID` (página aparte, ej. "Alertas supervisor") en la VPS; ver runbook §1.4.

## Ronda 20 — Cerrada

| ID | Tarea | Estado |
|----|--------|--------|
| 098 | Auditoría variables Notion (Codex) | ✅ done — PR #100 mergeado. |

## Plan implementación auditoría 2026-03

Auditoría Claude (PR #101): **plan maestro** en [docs/plan-implementacion-auditoria-2026-03.md](../docs/plan-implementacion-auditoria-2026-03.md). Quick Wins (QW-1 a QW-6) ejecutados. Docs: `docs/audits/codebase-audit-2026-03/`. PRs #102, #103, #104 MERGED. Tests: 911 passed.

## Ronda 21 — Cerrada (PR #106 mergeado)

| ID | Tarea | Agente | Estado |
| -- | ----- | ------ | ------ |
| 099 | Fix token mismatch Dispatcher→Worker (P0) | claude-code | ✅ done — Dispatcher reiniciado, E2E OK (2026-03-08) |
| 100 | Test VPS + tests gpt-rick / gpt-realtime | claude-code | ✅ done — n8n OK, gpt-realtime OK, gpt-rick 403 (permisos Azure) |

**Resultado tests 2026-03-08:** `docs/audits/vps-test-results-2026-03-08.md`. VPS: KIMI_AZURE_API_KEY usada como AZURE_OPENAI_API_KEY; test_gpt_realtime_audio OK; test_gpt_rick_agent 403 (Identity sin permisos agents).

**Pendiente David:** Habilitar SSH en VM; permisos Azure para Gpt-Rick si se requiere. Sincronizar VPS a main tras merge.

**Rick 2026-03-08:** Reportes en `G:\...\Perfil de David Moreira\Reportes_Mercado`; Proyecto-Embudo-Ventas vacía. Herramienta **notion** (API); **browser** falla sin GUI. `.agents/para-rick.md`.

## Ronda 12 — Cerrada

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

## Seguimiento Rick 2026-03-09

| ID | Tarea | Agente | Estado |
|----|-------|--------|--------|
| 001 | Recomendaciones Antigravity para corregir la ejecucion de Rick en proyectos reales | antigravity | âœ… done â€” recomendaciones entregadas y mergeadas en main (PR #110) |
| 002 | Recomendaciones Cursor para orquestacion y politica de ejecucion de Rick | cursor | assigned |
| 003 | Recomendaciones Claude para guardrails runtime y trazabilidad de Rick | claude-code | âœ… done â€” guardrails, tests y auditoria mergeados en main |

## Notas
- Agentes: Cursor (lead), Antigravity, Codex, GitHub Copilot, Claude Code.
- Cada agente tiene su clon: `C:\GitHub\umbral-agent-stack-<nombre>`
- Motor de búsqueda: Tavily. LLM: Gemini 2.5 Flash.
- Workflow: feature branch → PR → Cursor merge → deploy VPS
