---
id: 2026-06-01-014-gd52-oauth-scope-decision
title: "G-D5.2 — decisión scope OAuth ADR-16 vs tokens live"
status: pending
assigned_to: david
created_by: cursor
created: 2026-06-01
---

# G-D5.2 — Scope OAuth

## Contexto

- **G-D5.1 OK:** Gmail + Calendar smoke PASS en VPS (refresh tokens SET).
- **Drift:** tokens probablemente emitidos con scopes más amplios que ADR-16 mínimo (`gmail.modify`, `calendar.events`).
- **Opciones:**
  - **A** Aceptar tokens actuales (operativo > least-privilege strict) — documentar excepción en ADR-16 log
  - **B** Re-OAuth con scopes ADR — rotación + update `~/.config/openclaw/env` (Copilot-VPS + David browser)
  - **C** Diferir a Q3

## Gate David

Responder en chat: A, B o C.

## VEREDICTO

_Pendiente decisión David_
