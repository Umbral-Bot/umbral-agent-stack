# Task 015 — G-D5.2 OAuth Rick Closeout (Copilot-VPS)

- **assigned_to:** Copilot-VPS
- **status:** done
- **created:** 2026-06-02
- **depends_on:** task 014 (G-D5.2 OAuth scope decision), task 011 (G-D5.1 audit)
- **gate:** G-D5.2

## Objective

Formal closeout of G-D5.2 re-OAuth on the VPS. Verify that:

1. G-D5.1 env vars: 7 SET / 3 UNSET (expected) — no missing names.
2. G-D5.2 rotated VALUES: client Rick OpenClaw + refresh token + scopes ADR-16.
3. `tokeninfo` returns scopes: `gmail.modify` + `calendar.events`.
4. Worker smoke: `gmail.list_drafts` + `google.calendar.list_events` → PASS.

## Procedure

1. `cd ~/umbral-agent-stack && git pull --ff-only origin main`
2. `bash scripts/vps/write-gd52-traceability.sh`
3. `bash scripts/vps/audit-google-env-vs-gd51.sh | tee ~/.coord-ag-evidence/G-D5.2/closeout-audit.txt`
4. `bash scripts/vps/smoke-gd52-oauth.sh`
5. Verify conditions above.
6. If all PASS → VERDICT: `G_D52_VPS_CLOSEOUT_OK`
7. If smoke FAIL → diagnostics: `git log -1; journalctl --user -u umbral-worker -n 30 --no-pager`

## Evidence

- `~/.coord-ag-evidence/G-D5.1/audit-report.md`
- `~/.coord-ag-evidence/G-D5.2/traceability-report.md`
- `~/.coord-ag-evidence/G-D5.2/closeout-audit.txt` (this task)
- `~/.coord-ag-evidence/G-D5.2/tokeninfo.json` (smoke output)
- `~/.coord-ag-evidence/G-D5.2/gmail_profile.json` (smoke output)

## Log

### 2026-06-02 Execution

1. **Preflight**: `git pull --ff-only origin main` → already up to date on `main`.
2. **write-gd52-traceability.sh** → wrote `~/.coord-ag-evidence/G-D5.2/traceability-report.md`. Confirms values rotated (client secret + refresh tokens for Gmail and Calendar), scopes narrowed to `gmail.modify` + `calendar.events`, same CLIENT_ID prefix. Verdict in report: `G_D52_VPS_REOAUTH_OK`.
3. **audit-google-env-vs-gd51.sh** → initial run showed 1 row (bash `set -euo pipefail` + `((count++))` bug). Fixed: removed `-u`, switched to `${%%=*}` parsing + `$((var + 1))` arithmetic. Re-run: **7/7 SET, 3/3 UNSET, 0 failures. AUDIT_RESULT=PASS.**
4. **smoke-gd52-oauth.sh** →
   - Worker health: `ok:true`, version `0.4.0`.
   - tokeninfo scopes: `calendar.events`, `gmail.modify` (ADR-16 compliant).
   - Gmail account: `rick.asistente@gmail.com`.
   - `gmail.list_drafts`: http_ok=True, inner_ok=True, error=None.
   - `google.calendar.list_events`: http_ok=True, inner_ok=True, error=None.
   - **SMOKE_DONE**.
5. All 8 verification conditions PASS (see verification matrix in conversation).

## Verdict

**G_D52_VPS_CLOSEOUT_OK**

All conditions met:
- 7 vars SET / 3 UNSET — matches G-D5.1 baseline exactly.
- Values rotated via Rick OpenClaw re-OAuth (G-D5.2 traceability confirmed).
- Scopes narrowed to ADR-16 spec: `gmail.modify` + `calendar.events`.
- Worker smoke PASS on both channels.

Optional for David (browser): revoke old OAuth consent at https://myaccount.google.com/permissions
