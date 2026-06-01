---
id: 2026-06-01-011-copilot-vps-gd51-oauth-audit
title: "G-D5.1 — VPS read-only Google OAuth audit (Gmail + Calendar)"
status: done
assigned_to: copilot-vps
created_by: cursor
created: 2026-06-01
gates:
  - David approved option b (2026-06-01 chat)
  - Discovery D51_OAUTH_DISCOVERY_OK (task 010)
---

# G-D5.1 — OAuth audit VPS (read-only)

## Objetivo

Confirmar qué credenciales Google usa **runtime VPS** y si Gmail/Calendar responden vía Worker — **sin** imprimir tokens, **sin** re-OAuth, **sin** editar `openclaw.json`.

## Preflight repo

```bash
cd ~/umbral-agent-stack
git pull --ff-only origin main
git log -1 --oneline
test -f .agents/tasks/2026-06-01-011-copilot-vps-gd51-oauth-audit.md && echo TASK_FILE_OK
```

## Fuentes

- `notion-governance/docs/architecture/16-multichannel-rick-channels.md` (ADR-16, G1–G5)
- Task 010 Log (drift scope ADR vs docs/35)
- VPS env: `~/.config/openclaw/env` (names only in report)

## Pasos (read-only)

1. Evidencia: `~/.coord-ag-evidence/G-D5.1/`
2. Listar **nombres** de vars `GOOGLE_*` presentes/ausentes en `~/.config/openclaw/env` (redact values → `[REDACTED]` or `SET`/`UNSET`)
3. Worker health `:8088/health`
4. Si vars presentes: smoke mínimo vía Worker API o handler documentado:
   - Gmail: list drafts o equivalente read-only (ADR G2)
   - Calendar: list events read-only
5. Documentar scope drift vs ADR-16 (qualitative: "token likely issued with scope X" only if inferable without printing secrets)
6. Tabla final: canal | VPS vars | smoke | blocker | next gate

## Boundaries

- NO `echo $GOOGLE_*` en output
- NO OAuth browser flow
- NO gateway restart
- NO merge PRs

## Criterios

- [ ] Tabla canal × VPS state
- [ ] Smoke result PASS/FAIL/BLOCKED per channel
- [ ] Recomendación G-D5.2 (re-OAuth con scopes ADR) si aplica
- [ ] VEREDICTO in Log

## Log

### 2026-06-01 — Cursor

Task creada post-aprobación David (opción b).

### 2026-06-01 — Copilot-VPS (read-only audit)

Preflight OK (HEAD `1ae522b`, TASK_FILE_OK). Evidence: `~/.coord-ag-evidence/G-D5.1/audit-report.md`.

**Env inventory (names + SET/UNSET only, values never printed):** 7 vars SET — `GOOGLE_GMAIL_CLIENT_ID`, `GOOGLE_GMAIL_CLIENT_SECRET`, `GOOGLE_GMAIL_REFRESH_TOKEN`, `GOOGLE_CALENDAR_CLIENT_ID`, `GOOGLE_CALENDAR_CLIENT_SECRET`, `GOOGLE_CALENDAR_REFRESH_TOKEN`, `GOOGLE_CLOUD_LOCATION`. UNSET: `GOOGLE_GMAIL_TOKEN`, `GOOGLE_CALENDAR_TOKEN`, `GOOGLE_SERVICE_ACCOUNT_JSON` → both channels use the **refresh-token flow**.

**Worker health:** `:8088/health` ok, v0.4.0; tasks `gmail.list_drafts` + `google.calendar.list_events` registered.

**Read-only smoke (POST /run):**
- `gmail.list_drafts` → HTTP 200, inner_ok=true, 1 draft → **PASS**.
- `google.calendar.list_events` → HTTP 200, inner_ok=true, 0 events in window → **PASS** (auth OK).

No tokens printed; temp response files deleted post-run.

**Channel × VPS × ADR-16 table:**

| Channel | VPS vars | Smoke | Blocker | Next gate |
|---|---|---|---|---|
| Gmail | id+secret+refresh SET | PASS (read) | Scope drift §2.3 (min `gmail.modify` vs requested `gmail.compose`+`gmail.readonly`) | G-D5.2 re-OAuth if strict |
| Calendar | id+secret+refresh SET | PASS (auth) | Scope drift §2.4 (min `calendar.events` vs full `calendar`, D6 over-broad) | G-D5.2 re-OAuth narrowed |

**Note:** local ADR-16 copy does not enumerate literal `G1–G5`; canonical `notion-governance` ADR not present on this VPS. Mapped to ADR-16 D2/D6 + task 010 scope-drift instead.

**Recommendation:** channels live & read-capable; no connectivity fix needed. If D6 least-scope enforced → schedule **G-D5.2 re-OAuth** (`gmail.modify`, `calendar.events`) + authorized env hot-swap (restart = separate gate).

## VEREDICTO

**G_D51_VPS_AUDIT_OK** — both Google channels (Gmail, Calendar) authenticate and read live on the VPS via refresh-token flow. Only open item: scope compliance vs ADR-16 (G-D5.2). No tokens exposed, no OAuth flow run, no gateway restart.
