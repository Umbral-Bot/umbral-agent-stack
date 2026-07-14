---
id: "2026-07-14-001"
title: "P1.1 Granola — VPS readiness (deploy main + worker env), NO smoke Notion"
status: assigned
assigned_to: copilot
created_by: cursor
priority: high
sprint: exec-post-diag-2026-07 / P1.1
created_at: "2026-07-14T14:30:00Z"
updated_at: "2026-07-14T14:45:00Z"
---

# P1.1 Granola — readiness VPS (sin smoke Notion)

## Contexto previo

- P1.1 Fase A+B cerradas en laptop (Claude Code).
- Merged a `main`:
  - PR #530 → `2971a06c` (gap freshness exit 3 + PS1 exit-code)
  - PR #531 → `b70c94cb` (feeder MCP → `granola.process_transcript`, dry-run default, metadata+summary)
- Smoke Notion = **HOLD** hasta que David diga `GO smoke`.
- Capture mode actual: **metadata + AI summary**, no transcript verbatim (Basic).
- Antes de empezar: `cd ~/umbral-agent-stack && git fetch origin && git checkout main && git pull --ff-only origin main` (o worktree limpio; no ensuciar main si política H6 lo exige).

## Objetivo

Confirmar que la VPS/VM worker puede en principio correr el smoke de 1 reunión (sin ejecutarlo), y desplegar `main` con #530+#531.

## Procedimiento mínimo

1. Sync repo al SHA que incluye `b70c94cb` (o más nuevo en main).
2. Deploy/restart worker según runbook VPS habitual.
3. Health: curl worker `:8088` (o puerto canónico) + auth Bearer si aplica.
4. Env (enmascarar secrets): `NOTION_GRANOLA_DB_ID`, `NOTION_API_KEY`, `WORKER_TOKEN` set? sí/no.
5. Localizar entrypoint feeder #531; dry-run sin `--execute`. Si MCP Granola no está en VPS, documentar: smoke = laptop-MCP → WORKER_URL VPS.
6. Informe REPO vs VPS (HEAD, worker, env, blockers).

## Criterios de aceptación

- [ ] `main` en VPS contiene (o is after) `b70c94cb`
- [ ] Worker responde
- [ ] `NOTION_GRANOLA_DB_ID` presente en env del worker
- [ ] Veredicto: `P1_1_VPS_READY` | `P1_1_VPS_BLOCKED`
- [ ] Cero writes Notion / cero GO smoke / cero R4
- [ ] Separar "Repo dice X" vs "VPS muestra Y"

## Antipatrones que esta tarea prohíbe

- Declarar READY sin health real
- Ejecutar feeder `--execute` o process_transcript live
- Imprimir tokens / DB IDs completos
- Drive / Lote B / D-19 moves

## Log

- 2026-07-14 — cursor: tarea creada post-merge #530/#531; smoke hold; asignada Copilot VPS.
