---
id: "2026-07-03-008"
title: "Ola O1 Notion MCP (G-NMCP-1) — implementación quick wins"
status: done
assigned_to: copilot
created_by: cursor
priority: high
sprint: notion-mcp-eval
created_at: "2026-07-03"
updated_at: "2026-07-03T13:30"
---

## Objetivo

Ejecutar la Ola O1 autorizada por David (gate **G-NMCP-1**, megaprompt `NOTION-MCP-O1-v1` 2026-07-03) tras la auditoría [#512](https://github.com/Umbral-Bot/umbral-agent-stack/pull/512) / task `2026-07-02-005`: QW-1 doc superficie MCP IDE · QW-2 smoke read-only · QW-3 regla scripts lectura · QW-4 actor governance · Fase 5 doc `mcp_server/` · rotación tokens VPS (Fase 0, superficie VPS).

## Decisiones cerradas (autorización David — no re-preguntar)

- MCP IDE = superficie **DEV** (Cursor/Copilot Windows). Producción Rick sigue Worker REST + Poller VPS.
- Rotación tokens Notion VPS: autorizada. Env canónico: `~/.config/openclaw/env`.
- ST-1 (HTML attachment): **DEFER** hasta post-QW-2 verde.
- `mcp_server/` interno: solo documentar; dormido hasta O2.
- O2/O3: NO implementar.

## Entregables

- [x] `docs/ops/notion-mcp-ide-surface.md` (QW-1 + QW-3 + tabla decisión + NO-TOUCH + defer ST-1)
- [x] `docs/ops/mcp-server-worker-bridge.md` (Fase 5)
- [x] `docs/audits/notion-mcp-smoke-readonly-2026-07-03.md` (QW-2 — **BLOCKED**, ver log)
- [x] `scripts/README.md` (regla QW-3, scripts legacy-ok)
- [x] Referencia en `docs/62-operational-runbook.md` + nota cierre OQ#3 en task 006
- [x] PR governance separado (QW-4): actor `ide_mcp_agent` — **#15 MERGED**
- [ ] Fase 0 rotación tokens VPS — **handoff Copilot-VPS** (no ejecutable desde Windows; requiere Notion web para crear tokens + superficie VPS)
- [x] Board actualizado

## Log

### [copilot] 2026-07-03 13:00
Arranque O1. Preflight OK (`main@ccf9529`), rama `copilot/feat-notion-mcp-o1-gate1`.

- **QW-2 smoke: BLOCKED.** Las tools `notion-API-*` del host fueron removidas de la sesión Copilot (tool change notice 2026-07-03 10:13, mismo estado que durante el audit #512). 0 llamadas MCP posibles. Documentado en `docs/audits/notion-mcp-smoke-readonly-2026-07-03.md` con pasos de reconexión para David. Gate workspace-scope queda pendiente del smoke.
- **Fase 0 rotación: SKIP en esta superficie** — crear integraciones/tokens nuevos es acción Notion web (David) y la edición `~/.config/openclaw/env` + restarts + limpieza JSONL es superficie Copilot-VPS (custom instructions: Windows no toca runtime VPS). Los pasos completos del megaprompt quedan transcritos abajo en "Handoff Fase 0".
- QW-1/QW-3/Fase 5/Fase 6-defer: docs creados en este PR.
- QW-4: PR governance **[notion-governance#15](https://github.com/Umbral-Bot/notion-governance/pull/15)** (rama `copilot/feat-ide-mcp-agent-governance`; actor `ide_mcp_agent` + policy 02 + changelog 05; YAML validado). Merge pendiente de revisión David.

## Handoff Fase 0 — rotación tokens VPS (para Copilot-VPS / David)

Ejecutar en VPS según megaprompt `NOTION-MCP-O1-v1` §FASE 0 (backup env → tokens nuevos en Notion web → editar `~/.config/openclaw/env` → `systemctl --user daemon-reload && systemctl --user restart openclaw-worker-vps openclaw-dispatcher openclaw-gateway` → smoke `curl http://127.0.0.1:8088/health` + `scripts/smoke_test.py` → grep `ntn_` en `~/.openclaw/agents/*/sessions/*.jsonl` y redactar líneas → evidencia en `~/.coord-ag-evidence/notion-token-rotation-2026-07-03.md`, sin tokens). Revocar tokens viejos SOLO tras smoke verde.

### [copilot] 2026-07-03 13:10 — QW-2 re-run (megaprompt NOTION-MCP-QW2-RERUN-v1)

Paso A negativo: las tools `notion-API-*` siguen **no disponibles en la sesión del agente** (último tool-change notice 12:47 las lista como removidas; sin re-alta posterior). Veredicto se mantiene: **`QW2_SMOKE_BLOCKED` (host)** — 0 llamadas, sin resultados inventados, STOP según megaprompt. Evidencia actualizada con tabla de intentos, pasos VS Code precisados (`MCP: List Servers` → server Running → **reiniciar sesión del agente** para re-inyectar tools) y plantilla "Resultado live" lista para el próximo re-run. Cambios appendeados a **PR #513** (aún OPEN — un solo PR para O1, opción permitida por el megaprompt).

### [copilot] 2026-07-03 13:30 — O1 CERRADA (megaprompt NOTION-MCP-O1-CLOSE-v2)

- QW-2 intento 3: **BLOCKED (host/session)** — server confirmado por David = hosted `mcp.notion.com` (HTTP); el fallo persistente es la re-inyección de tools a una sesión ya iniciada, no la config. Próximo re-run: server Running + **chat nuevo**.
- Merges autorizados y ejecutados: **notion-governance#15** (squash `f9047b5`) + **UAS#513** (squash `8326e79`), ramas remotas borradas.
- Task → **done**. Pendientes que NO son de esta ola: rotación tokens VPS (handoff arriba), ST-1 (defer), O2 (gate G-NMCP-2).
