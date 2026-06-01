#!/usr/bin/env bash
# G-D5.2 post-reOAuth smoke — no token values printed
set -euo pipefail

ENV="${HOME}/.config/openclaw/env"
EVID="${HOME}/.coord-ag-evidence/G-D5.2"
mkdir -p "$EVID"

set -a
# shellcheck disable=SC1090
source "$ENV"
set +a

echo "=== worker health ==="
curl -fsS http://127.0.0.1:8088/health | tee "$EVID/health.json" | head -c 120
echo

echo "=== tokeninfo scopes ==="
ACCESS=$(curl -fsS -X POST https://oauth2.googleapis.com/token \
  -d "client_id=${GOOGLE_GMAIL_CLIENT_ID}" \
  -d "client_secret=${GOOGLE_GMAIL_CLIENT_SECRET}" \
  -d "refresh_token=${GOOGLE_GMAIL_REFRESH_TOKEN}" \
  -d "grant_type=refresh_token" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -fsS "https://oauth2.googleapis.com/tokeninfo?access_token=${ACCESS}" \
  | tee "$EVID/tokeninfo.json" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('scope=', d.get('scope',''))"

echo "=== gmail account ==="
curl -fsS -H "Authorization: Bearer ${ACCESS}" \
  https://gmail.googleapis.com/gmail/v1/users/me/profile \
  | tee "$EVID/gmail_profile.json" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('email=', d.get('emailAddress',''))"

run_task() {
  local task="$1"
  local payload="$2"
  local out="$EVID/${task//./_}.json"
  curl -sS -X POST http://127.0.0.1:8088/run \
    -H "Authorization: Bearer ${WORKER_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"task\":\"${task}\",\"input\":${payload}}" \
    | tee "$out" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); r=d.get('result') or {}; print('task=${task}', 'http_ok=', d.get('ok'), 'inner_ok=', r.get('ok'), 'error=', r.get('error') or d.get('detail')); sys.exit(0 if d.get('ok') else 1)"
}

echo "=== worker smoke ==="
run_task "gmail.list_drafts" '{"max_results":3}'
run_task "google.calendar.list_events" '{"max_results":5,"time_min":"2026-06-01T00:00:00Z","time_max":"2026-07-01T00:00:00Z"}'

echo SMOKE_DONE
