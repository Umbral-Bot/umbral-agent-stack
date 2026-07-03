# Agent Board — Umbral Agent Stack

> Última actualización: 2026-07-03 por **cursor** (post-merge #496 + G-WH-1)
> Sprint activo: **workspace-hygiene Pass 8** + Graphify #495 + Rick voz 004 + Notion MCP 005
> **Coordinación:** **Cursor** lead.

## Sprint 2026-07-02 — hilos vivos

| ID | Tarea | Agente | Estado |
|----|-------|--------|--------|
| 2026-07-02-001 | CAND-001 blog unpublish closeout | copilot | ✅ done (`CAND001_BLOG_EXAMPLE_COMPLETE`, PR #494 merged) |
| 2026-07-02-002 | Graphify piloto F1–F4 | copilot | ✅ done (GO_PARTIAL S7/R6, PR #495 merged, G-GR-1) |
| 2026-07-02-003 | Rick voz TTS MVP restart+smoke (VPS) | copilot-vps | ✅ done (no rehacer) |
| 2026-07-02-004 | Rick voz capitalización persona MVP | cursor | ✅ done — PR cursor/rick-voice-capitalize-mvp |
| 2026-07-02-005 | Notion MCP opportunity audit | copilot | ✅ done — `NOTION_MCP_AUDIT_READY` · [`docs/audits/notion-mcp-opportunity-audit-2026-07-03.md`](../docs/audits/notion-mcp-opportunity-audit-2026-07-03.md) · 4 QW / 4 ST / 2 DF · rec **O1** (gate G-NMCP-1) · smoke live BLOCKED parcial (tools MCP removidas de sesión) |
| 2026-07-03-008 | **Ola O1 Notion MCP (G-NMCP-1)** | copilot | ✅ done — PRs merged: **UAS#513** (`8326e79`) + **governance#15** (`f9047b5`) · QW-1/QW-3/F5 OK · QW-2 smoke **BLOCKED×3** (hosted `mcp.notion.com` confirmado; falta chat nuevo con server Running) · **Fase 0 rotación VPS DONE** (smoke PASS, tokens revocados, 281 JSONL redactados — deuda 006 §6.8.4 cerrada) · doc topología env → PR pendiente merge · ST-1 defer |
| 2026-07-02-006 | **Workspace hygiene audit + Pass 8** | copilot | ✅ done — `WORKSPACE_HYGIENE_PASS8_DONE` · rescates **#498/#499 merged** · 13 ramas locales limpiadas · pendiente David: G-WH-2, Fase A, zombis mayo, handoff MEGAPROMPT VPS |
| 2026-07-03-007 | Bloque decisión PRs (#480 + zombis mayo + #321) | copilot | ✅ **EJECUTADO** — 7 PRs cerrados sin merge (#480 #421 #418 #413 #389 #379 #321) con autorización David · rescates merged: **#508** (evidencia E2E 421), **#509** (test_pdf_parser 418, 16/16), **#510** (ADR-013 + runbook off-sponsorship 321) · main `ae34e08` · ⚠️ runbook off-sponsorship: deadline 2026-07-30, trigger ya activo — revisar |
| 2026-07-03-009 | **Diagnóstico profundo torneo agentes / PIT** (visión David) | copilot | ✅ done — `AGENT_TOURNAMENT_DIAG_READY` · [`docs/audits/agent-tournament-pit-deep-diagnosis-2026-07-03.md`](../docs/audits/agent-tournament-pit-deep-diagnosis-2026-07-03.md) · blockers=3 (roster fable-5/sonnet-5/kimi · per-lane model v1 · budget enforcement) · `pit6_ready=PARTIAL` (2 torneos v1 reales ya en vault + broker P9 golden PASS) · rec: Opción A Telegram + re-probe slugs + lanes.yaml v1.1 · **PR #516 merged** |
| 2026-07-03-010 | **PIT Telegram deliverables** — deck PPT → Drive + link Rick | copilot | ✅ done — `PIT_TG_DRIVE_IMPLEMENTED` · worker `google_drive.upload_file/upload_presentation` + `pit_build_outcome_deck.py` + `pit_deliver_telegram_pack.py` + skill §Entrega Telegram + runbook OAuth · 27 tests nuevos verdes (371 total PIT+MC) · pendiente David: OAuth VPS (runbook §1-3) + smoke real · PR pendiente review |

> Auditoría 006: 17 clones Windows (objetivo 5), 4 rescates, 5 hilos activos. MEGAPROMPT VPS listo post-main.

## Estado del sistema (actualizado 2026-03-07 — auditoría en vivo)

| Aspecto | Estado |
|---------|--------|
| Protocolo inter-agentes | ✅ Activo |
| VPS (Control Plane) | ✅ Redis + Dispatcher + Worker + 12 crons (branch `rick/vps`) |
| Notion Poller daemon | ✅ Corriendo (PID 269682, desde 2026-03-04) |
| Worker API VPS | ✅ v0.4.0 — 43 handlers — responde directo |
| Worker API VM | ✅ `8088` y `8089` alineados a `main`; health/ping/providers/quota OK |
| Multi-LLM | ✅ Gemini 2.5 Flash operativo (llamada directa OK) |
| OpsLogger | ✅ 213 eventos en ~/.config/umbral/ops_log.jsonl |
| Crons activos | 12 (dashboard, health, supervisor, poller, sim-daily, sim-report, digest, sim-make, E2E, OODA, scheduled-tasks, quota-guard) |
| Tests | ✅ 900 passed (PR #96) |
| CI | ✅ GitHub Actions pytest (Python 3.11 + 3.12) |
| **E2E Dispatcher→Worker** | ✅ OK — token fix 2026-03-08 (PR #106) |
| VM SSH/WinRM | ❌ Puertos 22/5985 cerrados — solo :8088 abierto |
| Cuotas Redis | ❌ Vacías — Dispatcher no despacha exitosamente |

## Editorial CAND-001 — Cerrado (2026-07-02)

| ID | Tarea | Agente | Estado |
|----|-------|--------|--------|
| — | Unpublish endpoint + eliminar fixture smoke | codex | ✅ PR [#494](https://github.com/Umbral-Bot/umbral-agent-stack/pull/494) merged; fixture `criterios-de-aceptacion-antes-de-automatizar-bim` → 404 |
| — | Fase 6 blog CAND-001 manual (SWA + Notion URL) | codex/cursor | ✅ slug `automatizar-sin-gobernanza-escala-el-desorden` live |
| 2026-07-02-001 | Closeout bitácora + verificación gates | cursor | ✅ done |

**Veredicto:** `CAND001_BLOG_EXAMPLE_COMPLETE` — doc `docs/ops/cand-001-closeout-2026-07-02.md`

**Deferido (no bloquea cierre):** republicar hero **Alt 1** (live = Alt 2 `7d3b9a`; Notion `Selección imagen` = Alt 1).

**Siguiente frente:** CAND-004+ pipeline source-driven — prompt Rick en `docs/ops/cand-full-pipeline-next-2026-06-07.md`.

---

## Rick voz MVP (2026-07-02)

| ID | Tarea | Agente | Estado |
|----|-------|--------|--------|
| 2026-07-02-003 | Push-to-talk Telegram STT/TTS + fallbacks + persona VPS | copilot-vps | ✅ done (runtime) |
| 2026-07-02-004 | Capitalizar templates/runbook/governance sync VOICE.md | cursor | ✅ done |

**MEGAPROMPT capitalización:** `docs/ops/MEGAPROMPT-cursor-capitalize-rick-voice-persona-mvp.md`  
**Deuda Fase 2:** `docs/ops/MEGAPROMPT-rick-voice-realtime-phase2.md` (gpt-realtime + Tailscale web; NO TG bot)

---

## Trabajo vivo

Regularización `UMB-132` (2026-03-22): se cerraron task files históricos que habían quedado `assigned` o `blocked` pese a corresponder a rondas cerradas o diagnósticos archivados. La coordinación activa queda reducida a las tareas realmente vivas.

| ID | Tarea | Agente | Estado |
|----|-------|--------|--------|
| 2026-07-02-005 | Auditoría Notion MCP oficial — gaps y oportunidades vs UAS | copilot | ✅ done (`NOTION_MCP_AUDIT_READY`, audit 2026-07-03, rec O1) |
| 2026-07-02-002 | Piloto Graphify F1–F4 — **`GO_PARTIAL` FIRMADO G-GR-1** (goldset A 8/10 vs B 9.5/10, S7/R6; uso local opcional, revisión 30d) — done al mergear PR #495 | copilot | review |
| 2026-03-09-002 | Recomendaciones Cursor para orquestacion y politica de ejecucion de Rick | cursor | assigned |
| 2026-03-22-001 | Diagnóstico env Rick vs local — Codex define canónicos | codex | ✅ done |
| 2026-03-22-002 | Super diagnóstico exhaustivo del sistema | codex | ✅ done (PR #126) |
| 2026-03-22-003 | Fix hallazgos super diagnóstico — VM /run y auto-issues | codex | ✅ done (PR #127) |
| 2026-03-23-001 | Calendar/Gmail: env VPS + verificación + seguimiento post diagnóstico | codex | ✅ done |
| 2026-03-23-002 | UMB-141: completar trazabilidad de runtime para enriquecer auto-issues | codex | ✅ done |
| 2026-03-23-003 | UMB-140: endurecer auto-issues con deduplicacion y proyecto canonico | codex | ✅ done |
| 2026-03-23-004 | UMB-148: retirar Google Custom Search como path primario de discovery web | codex | ✅ done |
| 2026-03-23-005 | Super diagnostico exhaustivo de interconectividad y gobernanza operativa | codex | ✅ done |
| 2026-03-23-006 | Fase 0: estabilizacion base, merge, deploy y smoke post-diagnostico | codex | ✅ done |
| 2026-03-23-007 | Fase 1: supervisor VPS y alerting Notion robusto | codex | ✅ done |
| 2026-03-23-008 | Fase 1 follow-up: restaurar ruta dedicada de alertas Notion del Supervisor | codex | ✅ done |
| 2026-03-23-009 | Supervisor: publicar alertas en espanol | codex | ✅ done |
| 2026-03-23-010 | Fase 4: rediseño UX/copy de OpenClaw y unificación de Dashboard Rick | codex | ✅ done |
| 2026-03-23-011 | Fase 2: separar rate limiting interno del trafico externo | codex | ✅ done |
| 2026-03-23-012 | Cleanup de directorios pytest temporales con permisos rotos | codex | ✅ done |
| 2026-03-23-013 | GitLab sandbox mirror desde GitHub sin cambiar el tracker canonico | codex | ✅ done (descartado y revertido) |
| 2026-03-23-014 | Revertir soporte GitLab sandbox y reconfirmar cierre de Fase 2 | codex | ✅ done |
| 2026-03-23-015 | Fase 3: hardening runtime real de research.web | codex | ✅ done |
| 2026-03-23-016 | OpenClaw: separar cadencia de refresh y dejar tracking de gasto/actividad | codex | ✅ done (PR #150) |
| 2026-03-23-017 | Fase 5: skills reales faltantes y monitoreo continuo del stack | codex | ✅ done (PR #152) |
| 2026-03-24-001 | Lead temporal Codex — capitalizar hallazgos + cerrar ramas codex/* + Claude si aplica | codex | ✅ done |

| 2026-03-23-018 | Diagnostico integral OpenClaw: servicio, configuracion, agentes, modelos, cron y mejoras | codex | ✅ done |
| 2026-03-23-019 | Accion 1: regularizar topologia OpenClaw en VPS y dejar un solo gateway canonico | codex | ✅ done |
| 2026-03-24-003 | Accion 2: sincronizar workspace compartido OpenClaw VPS con el repo | codex | ✅ done |
| 2026-03-24-004 | Accion 3: resolver discovery web y degradacion Tavily en runtime | codex | ✅ done |
| 2026-03-24-005 | Accion 4: sanear sesiones y transcripts de OpenClaw en VPS | codex | ✅ done |
| 2026-03-24-006 | Accion 5: hardening de seguridad OpenClaw | codex | ✅ done |
| 2026-03-24-007 | Accion 6: bootstrap y gobernanza fina por agente en OpenClaw | codex | ✅ done |
| 2026-03-24-008 | Test general post-acciones OpenClaw | codex | ✅ done |
| 2026-03-24-009 | Diferidos OpenClaw: tailscale, tracking repo-side, costo y propuesta Tavily | codex | ✅ done |
| 2026-03-24-010 | Fallback VM no invasivo + Gemini grounded como primario de discovery | codex | ✅ done |
| 2026-03-24-011 | Gemini canonico, Tavily backup y tracking de necesidad futura | codex | ✅ done |
| 2026-03-24-012 | OpenClaw: automatizar runtime snapshot y resumir uso en Dashboard Rick | codex | ✅ done |
| 2026-03-24-002 | Accion 8: revisar skills faltantes en OpenClaw VPS y decidir sync vs skill nueva | codex | ✅ done |

| 2026-03-24-013 | Follow-up post-Rick: aterrar diagnostico real y endurecer composite.research_report | codex | ✅ done |

| 2026-03-24-014 | PCRick: persistencia real del node OpenClaw en la VM | codex | ✅ done |

## Pendientes diferidos post-fases

- Exact billing-grade attribution de costo/tokens para `research.web` y session caching de OpenClaw; hoy ya existe snapshot repo-side y costo proxy, pero no facturacion oficial por request.
- Decidir humanamente si Tavily se recarga, se deja como backend secundario o se retira del discovery ahora que `research.web` y `web_discovery.py` ya quedan cubiertos por Gemini grounded fallback.
- Hardening OpenClaw residual aceptado: `gateway.trustedProxies` vacio mientras la Control UI siga local-only y warning `potential-exfiltration` del plugin `umbral-worker` por lectura deliberada de `tokenFile` con permisos `600`.
- Reparar o revalidar reachability Tailscale VPS -> VM despues del reinicio del host; la recuperacion de internet de la VM quedo documentada, pero el tailnet end-to-end sigue degradado tras el reboot.
- Fallback VM no invasivo listo en scripts; sigue faltando una direccion host->VM realmente alcanzable para cerrar el tunel sin tocar la topologia Hyper-V.

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


## 2026-05-07-031 — diagnose orchestrator triage 400 (smoke O15.1b) [DONE]
- merged: PR #346 (commit 100af660) 2026-05-07T17:53Z
- status: done (read-only diagnosis; fix DIFERIDO a task 032)
- hipótesis confirmada: HB primaria (Pydantic enum mismatch) + HA secundaria (model routing log) + HC latente (handler missing); HD descartada
- root cause: dispatcher/rick_mention.py (Ola 1b) introdujo team='rick-orchestrator' y task_type='triage' sin extender los enums Team/TaskType en worker/models/__init__.py:43,51 ni registrar handler rick.orchestrator.triage en worker/tasks/__init__.py:TASK_HANDLERS. El 400 lo emite FastAPI/Pydantic en worker/app.py:523 antes del dispatch.
- fix propuesto (NO aplicado): (1) extender enums Team+TaskType con RICK_ORCHESTRATOR/TRIAGE; (2) implementar handle_rick_orchestrator_triage (decisión de diseño: proxy a OpenClaw gateway agent o pipeline interno); (3) opcional quota_policy.yaml.routing.triage para coherencia telemetría
- requires restart? sí — umbral-worker (NO el gateway). Ningún cambio toca openclaw.json ni model.primary. Vertex Fase 1 ventana hasta 2026-05-14 intacta.
- task 032 follow-up: diseñar+implementar handler rick.orchestrator.triage + enum extension + tests + restart worker + smoke regresión
- evidencia (working notes locales VPS): /tmp/031/payload-and-400-response.md, /tmp/031/model-routing.md, /tmp/031/verdict.md
- F-INC-002: clean pre y post merge
- secret-output-guard: respetado (ningún token impreso; comment_id/page_id solo parciales)
- SOUL Reglas 21+22: respetadas (400 reproducido empíricamente con curl; sin payloads inventados)
- constraint observado: .agents/board.md está protegido por GitHub Push Protection en branches no-main; esta entry se appendea directo en main (commit Copilot Chat post-merge PR346)

## 2026-05-07-032 — fix orchestrator triage handler [DONE — handler merged, smoke real pendiente]
- merged: PR #349 (commit 2eb4a7d4) 2026-05-07T18:41Z
- decisión diseño: Opción C minimal (pipeline interno hard-coded /health; sin LLM, sin subagent, sin gateway)
- enums extendidos: Team.RICK_ORCHESTRATOR + TaskType.TRIAGE
- handler implementado: worker/tasks/rick_orchestrator.py + registrado en TASK_HANDLERS
- 16 tests nuevos pasando (test_rick_orchestrator.py); 30/30 en suite combinada con rick_mention + notion_mention_router
- CI: 16/16 nuevos PASS; failures preexistentes test_copilot_agent (idénticas a PR #346) NO regresión
- worker restart: pid 59402 → 96364, active, 104 tasks_registered (incluye rick.orchestrator.triage)
- smoke local: POST /run 200, JSON real /health, gap honesto (no_page_id) cuando falta page_id (SOUL Regla 22)
- smoke real con David: PENDIENTE — repostear "@Rick ping worker /health y devolveme el JSON acá como reply" en Control Room (page id 30c5f443fb5c80eeb721dc5727b20dca); Copilot VPS verifica notion_poller log + dispatcher journalctl + worker journalctl; si OK → O15.1b PASS 100%
- F-INC-002 + secret-output-guard #8 + SOUL Reglas 21/22: respetadas
- gateway pid 75421 SIN restart (uptime ~4h continuo), openclaw.json intacto, model.primary=Vertex intacto, Vertex Fase 1 ventana hasta 2026-05-14 intacta
- follow-up task 033: Opción A proxy a OpenClaw subagent rick-orchestrator (ventana post-2026-05-14)
- follow-up bug Telegram-side detectado por David (no abierto aún): rick-orchestrator no tiene 'sessions_spawn' en tool policy → handoff a rick-ops bloqueado en Telegram. Path Telegram→OpenClaw confirma model.primary=Vertex engaging (write-path JSONL real, evidencia smoke gobernanza-side David 10:52-13:26 ART)

## 2026-05-07-032b — smoke real O15.1b [FAIL — bug pre-existente bloquea canal]
- ejecutor: Copilot VPS 2026-05-07T18:54Z (post comment David T0=2026-05-07T18:44:00.000Z en Control Room page 30c5f443…)
- verdict: SMOKE REAL FAIL — O15.1b NO cierra al 100%
- handler `rick.orchestrator.triage` (entregable task 032) SANO y registrado: `/health.tasks_registered` lo lista; smoke local previo PASS 14:35:31 -04
- canal Notion → poller → dispatcher → worker → reply BLOQUEADO antes del Hop2 (dispatcher)
- root cause confirmado empíricamente (NO regresión task 032; bug pre-existente): `worker/notion_client.poll_comments` (líneas ~500-665). Redis cursor `notion:poll:cursor:30c5f443…` = sentinel `"__TAIL__"` (TTL ~30d) → `poll_comments` entra `bootstrap=True` → 1 GET trae 2 comments con `has_more=False` y `next_cursor=None` → guard `if not bootstrap:` DESCARTA resultados → re-graba sentinel → loop perpetuo de 0 comments. Cualquier página con ≤page_size=20 comments queda atrapada.
- evidencia hops vacíos: H1 poller log "0 comments" en ciclo 18:53:14 con since 17:25Z (ventana cubre 18:44); H2 dispatcher journalctl since 14:30 local sin "Rick mention routed" ni "rick.orchestrator"; H3 worker journalctl sin "Executing task rick.orchestrator.triage" ni id 3595f443; H4 Notion API 0 replies por bot Rick (3145f443) post-T0 (B3 anti-fabricación cross-check)
- comment David presente vía Notion API directa: id 3595f443-fb5c-80e4…, by 1e3d872b… (allowlist), text matchea exactamente
- no-regresión limpia: gateway pid 75421 intacto (etime ~4h18m, Vertex Fase 1 OK), worker /health ok 104 tasks, ambos services active, ops_log limpio (0 eventos rick.orchestrator), repo 0 ahead/0 behind `e36358b9` al momento del check
- F-INC-002 + secret-output-guard #8 + SOUL 21/22: respetadas. NO restart worker, NO touch gateway, NO borrar cursor (tentador pero vuelve al loop perpetuo)
- artefactos VPS: `/tmp/032/smoke-real-fail.md` + `/tmp/032/comments-window.json` + spec local `/home/rick/umbral-agent-stack/.agents/tasks/2026-05-07-035-fix-poll-comments-bootstrap-collect.md` (NO pusheado — branch actual reservada para otra task; pendiente recrear o branch dedicada)
- follow-up task 035 (P0-blocker para cerrar O15.1b): fix poll_comments bootstrap collect — recomendación Opción A: remover guard `if not bootstrap:` para que también colecte resultados durante bootstrap cuando no hay más páginas
- follow-up task 036 (Media): helper `notion_safe_comment` para chunkear replies > 2000 chars (límite duro Notion API `rich_text.content`); auditar todos los call sites de `add_comment`
- follow-up Telegram-side (gobernanza smoke David): `rick-orchestrator` falta `sessions_spawn` en tool policy → task pendiente


## 2026-05-07-035b — task 035 deploy + smoke real B6 [PARTIAL — fix verified, channel still blocked by task 037]
- ejecutor: Copilot Chat (merges PRs #353 + #361) + Copilot VPS (deploy + reproducción runtime) 2026-05-07T20:50-21:00Z
- merges main: PR #353 spec (commit 61651e41) + PR #361 fix (commit fcd0c69f, fix subyacente 8d6036db)
- VPS deploy: git pull `fcd0c69f` clean, sin pyproject changes, sin reinstall deps
- worker restart: pid 96364 → 114572, active running, /health ok 104 tasks `triage` ∈
- fix runtime VERIFICADO empíricamente: `poll_comments(page=30c5f443…, since=2026-05-07T17:25Z, cursor=__TAIL__)` retorna count=4 (vs count=0 perpetuo pre-fix); incluye comment David `3595f443…` 18:44Z. Bug 035 eliminado en runtime real, no solo en código.
- daemon poller pid 1571 vivo (1d 2h 18min uptime, NO down — diagnóstico previo de poller down fue erróneo: pgrep mal escrito `notion_poller` vs `notion-poller-daemon`; gap honesto declarado y corregido)
- entrega end-to-end CONFIRMADA hops 1-3: H1 poller 16:51:08 ART `Rick mention routed comment=3595f443 author=1e3d872b page=? trace=75e1c4b9`; H2 dispatcher routed `Executing task 987bbfca rick.orchestrator.triage -> VPS`; H3 worker handler `classify command=health comment=3595f443 trace=75e1c4b9`
- NUEVO BLOCKER post-fix-035 (NO regresión task 035; bug pre-existente enmascarado): handler skipped reply `WARNING rick.orchestrator.triage missing page_id in envelope; reply skipped`. Causa raíz: `dispatcher/notion_poller.py:227` arma poll_targets `[{page_id: None, page_kind: control_room}]` → envelope al worker llega con page_id=null → handler hace gap honesto (SOUL Regla 22) y skip. Comment David 18:44Z sigue SIN reply real; los 2 comments bot Rick a 20:51Z son outputs de OTROS workflows (SIM Daily Report, research_and_post), no responden al /health.
- O15.1b NO cierra al 100% — abre task 037
- follow-up task 037 (P0-blocker para cerrar O15.1b): fix `dispatcher/notion_poller.py` resolución page_id para control_room — cuando `page_kind=control_room` y `page_id is None`, resolver con `os.environ['NOTION_CONTROL_ROOM_PAGE_ID']` antes de routing. Alternativa defensiva en handler: fallback a CONTROL_ROOM env si page_id None y page_kind control_room.
- no-regresión limpia: gateway pid 75421 intacto (etime 06:18:43 monotónicamente creciente, Vertex Fase 1 OK), openclaw.json/model.primary intactos, openclaw-dispatcher no tocado, cursor Redis `__TAIL__` intacto (daemon usa since-filter, no cursor); F-INC-002 + secret-output-guard #8 + SOUL 21/22: respetadas
- stash VPS preservado: `vps-deploy-035-pre-pull-20260507T205002Z` (cambios ajenos discovery-publish-cron.sh, NO reaplicados)
- side-finding (no investigar ahora): RuntimeError 404 en worker startup sobre database `7eca76a8…` (integration Rick sin acceso) — pre-existente, no afecta /health 200

## 2026-05-07-037b — O15.1b cerrada al 100% [DONE]
- ejecutor: Copilot Chat (merges PRs #362 spec + #364 fix) + Copilot VPS (deploy + verificación 4-hop) 2026-05-07T22:42-22:45Z
- merges main: PR #362 spec (commit 0ee65977) + PR #364 fix (commit c8584f96, fix subyacente b62ef049)
- VPS deploy: poller daemon respawn (pid 1571 → 120685 vía cron */5), openclaw-dispatcher restart (MainPID 120697); gateway pid 75421 intacto (etime monotónica +33min, Vertex Fase 1 OK), worker pid 114572 untouched, /health ok=True count=104 has_triage=True
- smoke unitario código: `_control_room_poll_target()` retorna page_id_prefix=30c5f443 len=32 (vs None pre-fix) — Opción A confirmada cargada en runtime
- smoke real end-to-end VERIFICADO VISUALMENTE: David postea `@Rick ping worker /health smoke-O15.1b T0=2026-05-07T06:42` en Control Room ~22:42Z; bot Rick (id 3145f443…) replica en mismo thread con JSON real de /health (ok=true, tasks_in_memory=1000, lista completa tasks_registered incluyendo notion.poll_comments, notion.add_comment, rick.orchestrator.triage). 4 hops PASS implícitos: H1 poller detectó comment, H2 dispatcher armó envelope con page_id resuelto (sin esto el handler hubiera skippeado), H3 worker handler ejecutó SIN `missing page_id; reply skipped`, H4 Notion API write OK con parent=comment David
- O15.1b: ✅ 100%
- side-finding capitalizado como task 038 candidata (NO blocker): 500 errors en `dispatcher/notion_poller.py:198` rama `_resolve_review_targets` `session_capitalizable`. Pre-existente, NO regresión 037, path Control Room funciona OK. Agendar Ola 2.
- restricciones respetadas: F-INC-002 (fetch+log pre push), secret-output-guard #8 (IDs prefix-only), SOUL Reglas 21+22 (gap honesto declarado cuando smoke real bloqueado por dedupe Redis con comment viejo, esperó input nuevo de David en lugar de fabricar PASS), NO restart gateway, NO touch openclaw.json/model.primary

## 2026-06-01-002 — G-D1a-RESTART: gateway + smoke post maxSpawnDepth=2 [DONE → G_D1a_RESTART_OK]
- Copilot-VPS 2026-06-01 05:38: restart gateway pid 1045197, health 200, `maxSpawnDepth=2` **efectivo en runtime**.
- pre/post gateway: 2026-05-21 11:15:35 → 2026-06-01 05:38:52. OpenClaw 2026.5.19, 8 agentes smoke OK.
- intacto: model.primary gpt-5.4, worker, Granola. evidencia: `~/.coord-ag-evidence/G-D1a-RESTART/`.
- D1.1 spine cerrado. D1.2 ✅ D1.3 ✅ (M2_VPS03_OK). D2.2 M1_VPS02_D22_OK.

## 2026-06-01 — Oleada paralela W/V [CAPITALIZED]
| Hilo | VEREDICTO |
|---|---|
| INFRA-WIN-01 | S2_G8_RECLONE_BLOCKED |
| Q2-WIN-01 | Q2_WIN01_READ_ONLY |
| M2-WIN-01 | M2_WIN01_SPEC_DRAFT_READY |
| M1-VPS-02 | M1_VPS02_D22_OK |
| M2-VPS-02 | M2_VPS02_SYNC_OK |
| M2-VPS-03 | M2_VPS03_OK |

## 2026-06-01-017 — G-D5.2 gate closeout sync [ASSIGNED → copilot-vps]
- Post O/P/N: VPS pull #438, refresh traceability, VEREDICTO **G_D52_GATE_CLOSED**

## 2026-06-04 — Core-first tracker + docs [IN PROGRESS — Cursor]
- **P4:** `TRACKER_CLEANUP_INVENTORY_READY` (Codex)
- **P4-close:** `STALE_PRS_442_443_CLOSED` (#442/#443 sin merge; canon #444)
- **Docs:** unified plan, d35 judge kit, d36 tournament gh plugin roadmap, core-first refresh, editorial HITL preview (commit pendiente push)
- **Siguiente:** Codex D3.6 PR · VPS sync skill tournament-github-cli · Notion live HITL verify · D3.5 tras D3.6

## 2026-06-02-020 — D3.3 tournament sync_skills adapters #445 [DONE]
- Torneo: **M1_D33_TOURNAMENT_PARTIAL** → rescate #447 → judge → **D33_WINNER_MERGED** #446 @ **`da8eba85`**
- Loser [#447](https://github.com/Umbral-Bot/umbral-agent-stack/pull/447) **closed without merge** 2026-06-03; issue [#445](https://github.com/Umbral-Bot/umbral-agent-stack/issues/445) **closed** 2026-06-03
- **D33_VPS_POST_MERGE_OK** @ `fce55518`
- **D3.4 retro:** `M1_D34_TOURNAMENT_RETRO_OK` — `docs/ops/d3-tournament-retro-2026-06-02.md`
- **D4.1:** ✅ `D41_MERGED` (#448 @ `805aa57b`) + `D41_VPS_POST_MERGE_OK` (HEAD `9730bfa6`, 35 passed mission)
- **D5.3:** ✅ `D53_RUNTIME_APPLIED_OK` (poller 1130156, worker health OK, cursor_used=True en 30c5…)
- **5c:** `D53_FIX_ALREADY_IN_MAIN` · soak inicial `D53_GRANOLA_SOAK_DEGRADED` (Granola ops_log quieto)
- **D6.1a:** ✅ `D61_AECO_KB_PREFLIGHT_OK` — Azure/GHCR what-if read-only OK; único drift esperado `aeco-source-crawler` env vars `SOURCE_TYPE`/`MAX_DOCS`.
- **D6.1b:** ✅ `D61_AECO_KB_DEPLOY_OK` — deployment `aeco-kb-pipeline-20260603-064344` `Succeeded`; jobs `aeco-source-crawler` + `aeco-index-pipeline` manual/succeeded; drift `SOURCE_TYPE`/`MAX_DOCS` saneado; no runtime run.
- **D6.1c:** ⚠️ `D61_AECO_KB_RUN_VERIFY_BLOCKED` — Copilot-VPS no tiene `az` ni `azure.identity`; regla de superficie prohíbe instalar Azure CLI en VPS. Evidencia `~/.coord-ag-evidence/D6.1/aeco-kb-run-202606030717.log`.
- **D6.1e:** ✅ `D6_1E_AECO_KB_BUILDINGSMART_OK` — GHCR pull auth reparado en ACA, 3 jobs alineados a `core-first-e98cd374`, crawler `aeco-source-crawler-do3yotx`, parser `aeco-pdf-parser-wz51605`, publisher `aeco-index-pipeline-j70gux1`, verify ACA/UAMI `aeco-index-pipeline-ahu3zpk`. Alias `aeco-kb-es-current` -> `aeco-kb-es-v20260604-0509`; doc_count 1187, `jurisdiction=intl` 1187, queries `IFC`/`ISO 19650`/`BIM` con 3 hits. Issue #454 cerrado. PRs runtime: #457, #458, #459, #460.
- Lección D3.2: exigir PR URL por lane antes de announce done

## 2026-06-02-019 — D3.2 tournament O2 backup alerts #440 [DONE — salvage merged]
- Issue #440 cerrado vía salvage PR **#444** → **`2fe58535`** (`D32_ISSUE440_MERGED` Copilot Windows 2026-06-02)
- VPS post-merge: **`D32_VPS_POST_MERGE_OK`** @ `2fe5853`
- Torneo real: **`M1_D32_TOURNAMENT_PARTIAL`** (0 PR URLs; gate #441 OK). Entregable funcional = salvage Codex, no winner de torneo.
- Evidencia torneo: `~/.coord-ag-evidence/D3.2/` (intacta). Opcional cleanup worktree: requiere `autorizo cleanup worktree D3.2`
- Siguiente torneo competitivo: **D3.3** (`sync_skills`)

## 2026-06-01-018 — O15 Gmail/Calendar OpenClaw skills [DONE → O15_OPENCLAW_WORKSPACE_SKILLS_OK]
- PR #439 `3388bf9c`; skills live VPS workspace

## 2026-06-01-016 — G-D5.2 Calendar E2E [DONE → G_D52_CALENDAR_E2E_OK]
- Copilot-VPS: list_events david.a.moreira.m@gmail.com, events_count=3, evidencia calendar-david-primary-list.json

## 2026-06-01-014 — G-D5.2 OAuth scope decision [DONE → opción B]
## 2026-06-01-013 — D3.1 worktree cleanup [ASSIGNED → copilot-vps]
## 2026-06-01-012 — Tournament lane PR gate [DONE → M1_D31_LANE_GATE_OK]
- PR #441 → **`462ef1c1`**
## 2026-06-01-011 — G-D5.1 OAuth VPS audit [DONE → G_D51_VPS_AUDIT_OK]
## 2026-06-01-008 — D3.1 tournament #403 [DONE → M1_D31_TOURNAMENT_PARTIAL, #437 merged]
## 2026-06-01-010 — D5.1 OAuth discovery Windows [DONE → D51_OAUTH_DISCOVERY_OK]
## 2026-06-01-009 — O15 delegation smoke [DONE → O15_DELEGATION_SMOKE_OK]

## 2026-06-01-007 — O15 Ola 3 gerencias semilla prompts [DONE → O15_OLA3_VPS_OK]
- ROLE: delivery, ops (new), communication-director, linkedin-writer; charter `docs/ops/o15-ola3-gerencias-semillas-charter.md`

## 2026-06-01-006 — O15 Ola 2 Mejora Continua prompts [DONE → O15_OLA2_VPS_OK]
- Repo: `main` + `rick-orchestrator` IDENTITY; QA/tracker ROLE; charter `docs/ops/o15-ola2-mejora-continua-charter.md`
- Sync script: `IDENTITY.md` / `ROLE.md` (override-only)
- Pendiente VPS: pull + `sync_openclaw_workspace_governance.py --execute`

## 2026-06-01-005 — D3.0 tournament smoke [DONE → M1_D30_SMOKE_OK]
- Issue #434; winner PR #435 (lane-a); spawn sessions_spawn x2 verified.
- Scripts: `scripts/vps/d3-smoke-*.sh`

## 2026-06-01-004 — EDITORIAL-03 [DONE → M2_VPS03_OK]
- Azure host fix + writer pause. Gateway pid 1057064. policy-05 §1e.

## 2026-06-01-003 — D2.1 + D2.2 [DONE / D22_OK]
- Skill synced VPS; dry-run OK. Pendiente: gh auth + G-D1b manual.

## 2026-07-02 — CAND-001 blog-only + unpublish editorial [DONE]
- Codex: `POST /api/unpublish-editorial-post` + deploy prod; smoke eliminó fixture `criterios-de-aceptacion-antes-de-automatizar-bim`.
- PR #494 merged `main` @ `1660538` (unpublish + YAML Perplexity §3 interno).
- CAND-001 blog live SWA; gates Notion intactos; closeout `docs/ops/cand-001-closeout-2026-07-02.md`.
- Task: `.agents/tasks/2026-07-02-001-cand001-blog-unpublish-closeout.md`.
- Abierto: hero Alt 1 vs Alt 2 en blob (republicación opcional).

## 2026-06-01-003 — D2.1: skill multi-agent-tournament-orchestrator [DONE]
- G-D1b: `main`/standalone — `docs/architecture/tournament-protocol.md`.
- Skill v1 + smoke spec + dry-run script + `docs/ops/tournament-d2.2-dry-run-checklist.md`.
- Task: `.agents/tasks/2026-06-01-003-d2.1-multi-agent-tournament-orchestrator-skill.md`.

## 2026-06-01 — Regla handoff VPS + push main [DONE]
- David: siempre push `main` antes de handoff Copilot-VPS que lea `.agents/tasks/*.md`; tareas incluyen `git pull --ff-only origin main`.
- PROTOCOL § Handoffs Copilot-VPS + copilot-instructions.md actualizados; tareas 001/002/2026-05-30-001 con Preflight repo.
- Pushed: `umbral-agent-stack` **d65b080f**, `notion-governance` **411da7c**.

## 2026-06-01 — VPS_SYNC post-push [DONE → VPS_SYNC_OK]
- Copilot-VPS: `git pull --ff-only` → HEAD **daeda1df**; TASK_001/002/D02 OK.
- Runtime estable post G-D1a-RESTART: `maxSpawnDepth=2`, gateway active pid 1045197 (since 2026-06-01 05:38:52), health 200. Sin writes.
- Gates G-D1a + G-D1a-RESTART verificados y repo↔VPS alineados.

## 2026-06-01 — EDITORIAL-02 cross-ref (Mega 1, VPS read-only) [DONE → EDITORIAL_02_DIAG_READY]
- Task: `.agents/tasks/2026-06-01-001-copilot-vps-editorial-02-diag-linkedin-writer-granola.md` (⚠️ mismo día-ID que G-D1a; slugs distintos).
- Granola: V2 sano, skip/dedup — **G-D0 diferido** para editorial. FailoverError: Azure store=false cross-agent.
- Siguiente editorial: G-ED-HITO (Cursor) + EDITORIAL-03 VPS (pause writer + Azure fix). **No mezclar con torneo D2.**

## 2026-06-01-001 — G-D1a: elevar maxSpawnDepth a 2 en openclaw.json (VPS) [DONE → G_D1a_PATCH_OK]
- creada por: Cursor (lead) 2026-06-01 como D1.1 / gate G-D1a del Plan Q2 v2 (`notion-governance/docs/roadmap/13-q2-2026-v2-deployment-spine.md §6`)
- ejecutado por Copilot-VPS 2026-06-01 05:25 (skill `openclaw-vps-operator`). VEREDICTO **G_D1a_PATCH_OK**.
- resultado: `agents.defaults.subagents.maxSpawnDepth` `<NOT SET>` → `2` (única adición). `JSON_VALID`. backup `~/.coord-ag-evidence/G-D1a/openclaw.json.bak.202606010525`.
- **NO restart**: gateway activo desde 2026-05-21 11:15:35 sin cambio → patch en disco, **NO efectivo en runtime** hasta `G-D1a-RESTART` (gate separado, pendiente firma David).
- torneos siguen bloqueados (depth efectivo = default) hasta el restart.
- archivo tarea: `.agents/tasks/2026-06-01-001-gd1a-set-maxspawndepth.md`
- capitalizado: spine D1.1 + outcome D0.3 (`notion-governance/docs/audits/2026-05-30-vps-reality-check-q2v2-d0.md`, sección G-D1a verificada; resto D0.2 PENDING).

## 2026-05-30-001 — Verificación read-only runtime torneo+multi-agente+OpenClaw (base Q2 v2) [ASSIGNED → copilot-vps]
- creada por: Cursor (lead) 2026-05-30 como paso D0.2 del nuevo Plan Q2 v2 (`notion-governance/docs/roadmap/13-q2-2026-v2-deployment-spine.md`)
- origen: revisión completa Q2 agendada 2026-05-30 + diagnóstico `notion-governance/docs/audits/2026-05-30-q2-tournament-multiagent-openclaw-diagnostic.md`
- scope: READ-ONLY. Confirmar `maxSpawnDepth` (clave para torneo O7/D1.1), `agents.list` + `model.primary` vigente, health gateway :18789 + worker :8088, y estado real Granola (muerto desde 2026-05-11 según VPS check 2026-05-20)
- NO ejecuta restart worker (acción A1 / D0.1) — eso es gate separado de David
- archivo tarea: `.agents/tasks/2026-05-30-001-verify-tournament-multiagent-openclaw-runtime.md`
- handoff a David: ejecutar esta verificación + decidir gates G-D0 (restart worker), G-D1a (maxSpawnDepth 1→2), G-D1c (provider primary) listados en Q2 v2 §6
