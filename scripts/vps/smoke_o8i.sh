#!/bin/bash
# O8i smoke: 2 cycles on a high-volume page; expect cycle 2 to be near-instant with cursor_used=true.
set -e
. /home/rick/.config/openclaw/env
PAGE="${1:-30c5f443fb5c80eeb721dc5727b20dca}"
PAYLOAD="{\"task\":\"notion.poll_comments\",\"input\":{\"page_id\":\"$PAGE\",\"limit\":20}}"
echo "=== Cycle 1 (bootstrap expected) page=$PAGE ==="
time curl -fsS -X POST http://127.0.0.1:8088/run \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $WORKER_TOKEN" \
  -d "$PAYLOAD"
echo
echo "=== Cycle 2 (cursor hit expected) ==="
time curl -fsS -X POST http://127.0.0.1:8088/run \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $WORKER_TOKEN" \
  -d "$PAYLOAD"
echo
