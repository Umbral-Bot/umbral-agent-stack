---
id: 2026-06-01-014-gd52-oauth-scope-decision
title: "G-D5.2 — decisión scope OAuth ADR-16 vs tokens live"
status: decided
assigned_to: david
decision: B
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

**Decisión: B** — Re-OAuth con scopes ADR mínimos (2026-06-01). Drift verificado: Calendar over-scoped (`calendar` full).

## VEREDICTO

**G_D52_DECISION_B** — Ejecutar runbook `docs/ops/gd52-reoauth-runbook.md` + task 015 VPS.

### 2026-06-01 — Cursor (cierre G-D5.2)

- Umbral-bot: redirect OAuth Playground eliminado (solo umbralbim.io + Supabase).
- Client **Rick OpenClaw** creado (GCP `future-yeti-455715-u7`).
- OAuth Playground: consent `rick.asistente@gmail.com`, scopes `gmail.modify` + `calendar.events`.
- VPS `~/.config/openclaw/env`: credenciales rotadas (client `285813488732-ij582…`).
- Worker: desplegados `gmail.py` / `google_calendar.py` con scopes ADR-16 (pendiente commit a `main`).
- Smoke PASS: tokeninfo, Gmail profile, `gmail.list_drafts`, `google.calendar.list_events`.
- Evidencia: `~/.coord-ag-evidence/G-D5.2/` en VPS.

**G_D52_VPS_REOAUTH_OK**
