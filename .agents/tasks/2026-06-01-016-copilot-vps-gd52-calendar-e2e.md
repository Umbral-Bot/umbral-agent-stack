# Task 016 — G-D5.2 Calendar E2E Rick → David primary (Copilot-VPS)

- **assigned_to:** copilot-vps
- **status:** assigned
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

- [ ] `calendar_id=david.a.moreira.m@gmail.com` returns events (non-empty or empty list OK)
- [ ] tokeninfo still `calendar.events` + `gmail.modify`
- [ ] Log notes: share calendar confirmed (Rick UI) — no env change needed

## Boundaries

- NO env patch / NO re-OAuth (env already Rick OpenClaw `285813488732-ij582…`)
- NO print secrets

## VEREDICTO

(pending) → **G_D52_CALENDAR_E2E_OK** or **G_D52_CALENDAR_E2E_BLOCKED** with reason

## Log
