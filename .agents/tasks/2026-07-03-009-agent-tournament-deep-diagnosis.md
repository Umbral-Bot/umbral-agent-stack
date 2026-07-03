---
id: "2026-07-03-009"
title: "Diagnóstico profundo torneo de agentes / PIT — visión David 2026-07-03"
status: done
assigned_to: copilot
created_by: david
priority: high
sprint: pit
created_at: "2026-07-03"
updated_at: "2026-07-03"
---

## Objetivo

Diagnóstico READ-ONLY del torneo de agentes para innovación de producto orquestado por Rick vía Telegram: qué existe, qué falta, path a MVP ejecutable, mapeo del pedido natural de David a los contratos PIT/D3. Sin spawn, sin torneo real, sin merge sin David.

## MEGAPROMPT

AGENT-TOURNAMENT-DEEP-DIAG-v1 (pegado por David en sesión Copilot Windows 2026-07-03).

## Entregables

- [x] `docs/audits/agent-tournament-pit-deep-diagnosis-2026-07-03.md` (Resumen ejecutivo · Inventario Fase A · Flujos · Gap matrix · Model roster · Telegram path · Roadmap MVP · Riesgos · Preguntas abiertas · Apéndice con Telegram sample + pit_spec draft validado + lanes.yaml draft)
- [x] Esta task (log)
- [x] `.agents/board.md` fila diagnóstico
- [x] PR doc-only — NO merge sin David

## Log

- 2026-07-03: preflight OK (`main` @ `735a6c7`, branch `copilot/diag-agent-tournament-pit-2026-07-03`).
- Evidencia recolectada: 3 hilos de exploración (MC preview/judge · mecanismos torneo + ISSUE-001 · broker P-series) + lectura directa de skill PIT, specs v1/v2/v4, tool_policy, quota_policy, slug matrix P3, runner, queue-002.
- Tests PIT en Windows: **165 passed, 3 skipped** (spec_validate, vault_check, runner_tasks, dry_run, tournament_run, openclaw_broker, collect_tokens).
- Draft `pit_spec` del apéndice validado con `pit_spec_validate.py` → `status: pass` (4 lanes, 200 USD, 4 iter).

## Hallazgos clave (7)

1. PIT-6 en esencia ya ocurrió: 2 torneos v1 product reales con ledger (salud-mental 5.55M tokens, sharepoint-acc 6.62M) — repo dice; VPS a verificar.
2. Broker P-series probado end-to-end: P9 golden real `PIT_RUN_PASS_BROKER_REAL` (2026-06-22).
3. Per-lane model: solo spec v2 (broker); v1 product usa `--lane-model` global → propuesta lanes.yaml v1.1 (spec-only).
4. Roster David: fable-5 ✗ / sonnet-5 ✗ en probe P3 (06-21); kimi no es modelo CLI (path `llm.run` kimi_azure). Señal 07-03: Windows ya expone `claude-fable-5`/`claude-sonnet-5` → re-probe = paso 1.
5. Budget: estimate + ledger post-hoc; enforcement runtime = stub (PIT-3) → gap HIGH.
6. Telegram: ISSUE-001 bloquea spawn nested; recomendación Opción A (Rick parsea → gate → operador corre `pit_tournament_run.sh`), megaprompt ya listo en queue-002 §8.
7. MC preview/judge: P5.1–P5.3 completos en código, túnel 18089→8089; deploy VPS G1 marcado ✅ — smoke a verificar.

## Veredicto

`AGENT_TOURNAMENT_DIAG_READY | blockers=3 (roster modelos · per-lane model v1 · budget enforcement) | pit6_ready=PARTIAL | recomendacion=correr el próximo torneo con el pipeline probado (Opción A) invirtiendo solo en re-probe slugs + lanes.yaml v1.1 + enforcement mínimo`
