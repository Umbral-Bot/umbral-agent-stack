---
id: 2026-06-01-010-copilot-windows-o15-gmail-calendar-discovery
title: "D5.1 prep — Gmail/Calendar OAuth discovery (Copilot Windows read-only)"
status: assigned
assigned_to: copilot-windows
created_by: cursor
created: 2026-06-01
---

# D5.1 OAuth discovery (Windows)

## Objetivo

Inventario read-only de lo necesario para O15 canales Gmail + Calendar (`rick.asistente@gmail.com`, ADR-16). **No** ejecutar OAuth ni tocar VPS.

## Fuentes

- `notion-governance/docs/architecture/16-multichannel-rick-channels.md` (ADR-16)
- `notion-governance/docs/architecture/15-rick-organizational-model.md` §3.5
- `umbral-agent-stack/.agents/tasks/2026-03-23-001-*` (Calendar/Gmail VPS histórico)
- Repo: buscar `GMAIL`, `CALENDAR`, `google.oauth`, `rick.asistente`

## Entregables

1. Tabla: canal | estado repo | estado VPS (si conocido) | blocker | owner sugerido
2. Lista env vars / cred files esperados (nombres only, no secret values)
3. Gate recomendado para David (G-D5-oauth o similar)
4. Actualizar Log en esta task; no editar board (Cursor lo hace al cerrar)

## Boundaries

- NO SSH VPS
- NO pegar tokens
- NO crear OAuth clients sin autorización

## Prompt para Copilot Windows (pegar en hilo)

Ver `docs/ops/copilot-handoff-prompts.md` § Thread C.

## Log

### 2026-06-01 — Cursor

Task creada para hilo Copilot Windows paralelo.

## VEREDICTO

_Pendiente → **D51_OAUTH_DISCOVERY_OK**_
