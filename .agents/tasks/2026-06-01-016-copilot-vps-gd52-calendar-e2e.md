# Task 016 — G-D5.2 Calendar E2E Rick → David primary (Copilot-VPS)

- **assigned_to:** copilot-vps
- **status:** done
- **created:** 2026-06-02
- **depends_on:** 2026-06-01-015 (G_D52_VPS_CLOSEOUT_OK)
- **gate:** G-D5.2 calendar channel

## Objective

Confirm Calendar API works on **David's shared primary** using Rick OAuth (ADR-16 D6), not Rick's empty `primary`.

## Procedure

```bash
cd ~/umbral-agent-stack && git pull --ff-only origin main
bash scripts/vps/smoke-gd52-oauth.sh
```

Then worker smoke with explicit calendar (read-only first):

```bash
# list events on David primary — expect ok:true
curl -sS -X POST http://127.0.0.1:8088/run \
  -H "Authorization: Bearer ${WORKER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"task":"google.calendar.list_events","input":{"calendar_id":"david.a.moreira.m@gmail.com","max_results":3}}' \
  | tee ~/.coord-ag-evidence/G-D5.2/calendar-david-primary-list.json \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('ok=',d.get('ok'), 'inner=', (d.get('result') or {}).get('ok'))"
```

**Do NOT** create live events unless David explicitly says `autorizo evento prueba`.

## Pass criteria

- [x] `calendar_id=david.a.moreira.m@gmail.com` returns events (non-empty or empty list OK)
- [x] tokeninfo still `calendar.events` + `gmail.modify`
- [x] Log notes: share calendar confirmed (Rick UI) — no env change needed

## Boundaries

- NO env patch / NO re-OAuth (env already Rick OpenClaw `285813488732-ij582…`)
- NO print secrets

## VEREDICTO

**G_D52_CALENDAR_E2E_OK**

## Log

### 2026-06-02 — Copilot-VPS

1. Preflight: `git pull --ff-only origin main` → TASK_FILE_OK.
2. `bash scripts/vps/smoke-gd52-oauth.sh` → PASS (`calendar.events` + `gmail.modify`, `rick.asistente@gmail.com`, inner_ok Gmail + Calendar).
3. `google.calendar.list_events` con `calendar_id=david.a.moreira.m@gmail.com` → `ok=True`, `inner_ok=True`, `events_count=3`.
4. Evidencia: `~/.coord-ag-evidence/G-D5.2/calendar-david-primary-list.json`.
5. NO env patch, NO re-OAuth, NO eventos creados.
