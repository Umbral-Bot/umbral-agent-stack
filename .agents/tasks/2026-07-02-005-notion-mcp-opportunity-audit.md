---
id: "2026-07-02-005"
title: "Auditoría Notion MCP oficial — diagnóstico, gaps y oportunidades vs stack UAS"
status: assigned
assigned_to: codex
created_by: cursor
priority: medium
sprint: notion-mcp-eval
created_at: "2026-07-02"
updated_at: "2026-07-02T20:30"
---

## Objetivo

Investigar el impacto del **Notion MCP oficial** (OAuth HTTP, tools modernas, HTML/attachments) sobre `umbral-agent-stack` y proponer oportunidades de mejora **sin implementar** cambios de producción en esta pasada.

## Contexto

- Referencia externa: [What is MCP? (Notion)](https://nine-coreopsis-f5f.notion.site/What-is-MCP-3915436b72f581ee8971e4169e8bf1e0) — demostración de `notion-create-pages`, `notion-create-attachment`, host/client/server, Streamable HTTP @ `mcp.notion.com`.
- Anuncio LinkedIn: bloques HTML funcionan con cualquier agente vía MCP.
- Baseline interno: audit previo concluyó que **Rick VPS no tiene MCP Notion nativo** — usa REST (`NOTION_API_KEY`) vía Worker/Poller. Ver task `2026-05-05-006`.
- Gobernanza cross-repo: `notion-governance` define permisos por superficie antes de cualquier write MCP.

## Alcance (diagnóstico)

1. Inventario paths Notion actuales en UAS (Worker, Poller, editorial, OpenClaw prompts, tests).
2. Comparar capacidades MCP Notion 2025–2026 vs integración REST actual.
3. Matriz gap + oportunidades (dev agents, Rick runtime, editorial, observabilidad).
4. Riesgos y gates (NO-TOUCH, HITL, rate limits, duplicación REST+MCP).
5. Roadmap recomendado O0–O3 con esfuerzo/impacto — **sin ejecutar O1+ sin firma David**.

## Fuera de alcance

- Instalar MCP en VPS / OpenClaw runtime (solo recomendar).
- Writes a Notion producción (Publicaciones, Control Room, etc.).
- Cambios de schema Notion.
- Merge PR sin revisión David.

## Lectura obligatoria

- `docs/ops/MEGAPROMPT-notion-mcp-opportunity-audit-2026-07-02.md`
- `.agents/tasks/2026-05-05-006-copilot-vps-audit-rick-notion-mcp-integration.md`
- `docs/adr/ADR-007-notion-como-hub-editorial.md`
- `docs/editorial-pipeline/notion-schema.md`
- `docs/plans/linkedin-publication-pipeline.md` (bloques audit MCP)
- Repo `notion-governance`: `docs/policies/02-permissions-by-surface.md` (read-only)

## Entregables

- [ ] `docs/audits/notion-mcp-opportunity-audit-2026-07-02.md` (13 secciones mínimo)
- [ ] Log en esta task + línea board
- [ ] Veredicto: `NOTION_MCP_AUDIT_<READY|BLOCKED>` + top 5 oportunidades priorizadas

## Log

### [cursor] 2026-07-02 20:30
Task + MEGAPROMPT creados. Disparador: conexión MCP Notion + página demo HTML attachments.
