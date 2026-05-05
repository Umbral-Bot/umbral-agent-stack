# SEV-1 Triage — `notion.poll_comments` timeout (2026-05-05)

**Status:** ✅ Pipeline restored (tactical fix). Architectural follow-up pending.
**Severity:** SEV-1 (silent pipeline failure, ~3 days zero comment processing).
**Detected:** 2026-05-05 ~15:50 UTC (during Ola 1b smoke verification by Copilot-VPS).
**Resolved (tactical):** 2026-05-05 18:06 UTC.
**Operator:** Copilot-VPS (this thread). Coordinator: David. Parallel thread: Codex (F6 tournaments — not interfered).

---

## Timeline

| Timestamp (UTC) | Event |
|---|---|
| 2026-05-02 17:49 | Last successful `Processing [intent→team] for comment` log line in `/tmp/notion_poller.log`. |
| 2026-05-02 ~18:00 → 2026-05-05 ~18:00 | ~3 days of `httpx.ReadTimeout` on every poll iteration (60s daemon cycle). Zero comments routed. **No alarm fired.** |
| 2026-05-05 15:50 | Copilot-VPS thread (Ola 1b smoke verification) detected the silence. Found daemon (PID 409021) had also been running stale code from 2026-04-13 (21 days). Restarted daemon → still failed (real bug was upstream). |
| 2026-05-05 17:30 | David posted smoke comments on OpenClaw page `30c5f443…`: `@Rick smoke ola 1b` and `nota suelta regression test ola 1b`. |
| 2026-05-05 18:00 | This thread: isolated repro confirmed root cause — `notion.poll_comments` call takes **62s**, exceeds default 30s `WorkerClient` timeout. |
| 2026-05-05 18:06 | Tactical fix deployed (daemon timeout 30→300s). First `Notion poll retrieved 20 comments` after fix. Backlog draining. |
| 2026-05-05 18:10 | David's smoke comments processed by daemon (legacy path — PR #284 not yet merged). |

---

## Root cause (confirmed, not hypothesis)

`worker.notion_client.poll_comments` (file `worker/notion_client.py:464`) paginates through ALL comments on the polled page in **oldest-first order** (Notion API default), filtering by `since` *post-fetch* via `continue`:

```python
for c in data.get("results", []):
    created_dt = _parse_notion_datetime(c.get("created_time", ""))
    if since_dt and created_dt and created_dt <= since_dt:
        continue  # skip — but loop keeps walking ALL old comments
    comments.append({...})
```

The OpenClaw page (`30c5f443fb5c80eeb721dc5727b20dca`) accumulates SIM Daily Reports every 6h plus other agent traffic. By 2026-05-02 it had ~30k comments. With `page_size=20`, one poll call requires ~1500 paginated GETs to `https://api.notion.com/v1/comments`, taking ~60s.

Meanwhile the daemon constructs `WorkerClient(...)` with the **default timeout of 30s** (`client/worker_client.py:52`). Result: poller raises `httpx.ReadTimeout` while the worker handler keeps running and eventually returns 200.

### "Repo says" vs "VPS shows"

| Repo says | VPS shows |
|---|---|
| `worker.notion_client.poll_comments` last touched 2026-03-16 (commit `7608036`) — code is correct | Call returns HTTP 200 with valid 20 comments — code IS correct, but slow on busy pages |
| Daemon polls every 60s | Daemon polled but every iteration crashed pre-comment-loop with `ReadTimeout` since 2026-05-02 |
| `WorkerClient` default 30s timeout has been the same for months | Threshold crossed when page volume pushed call latency past 30s on/around 2026-05-02 17:49 |

### Hypotheses evaluated

| # | Hypothesis | Verdict |
|---|---|---|
| H1 | Recent change in `worker/tasks/notion_poll_comments.py` ~2026-05-02 introduced loop bug | ❌ No commits to that file or to `worker/notion_client.py::poll_comments` since 2026-03-16 |
| H2 | New page/database added to config that broke query | ❌ Same target pages as before; no config change in window |
| H3 | `NOTION_API_KEY` rotated/expired partial | ❌ Notion returns HTTP 200 on every paginated GET (verified in `journalctl --user -u umbral-worker`) |
| H4 | Notion rate limit | ❌ No 429s in worker journal; all GETs return 200 |
| H5 | Worker overloaded / event loop blocked | ❌ Worker is FastAPI sync; single `poll_comments` call uses `httpx.Client` synchronously. Worker stayed responsive on `/health` throughout |
| **H6** | **Cumulative page growth crossed the 30s `WorkerClient` timeout** | ✅ **CONFIRMED** by isolated repro (62s end-to-end on page `30c5f443…`) |

---

## Tactical fix (PR #290 — draft)

`scripts/vps/notion-poller-daemon.py`:

```python
# Before
wc = WorkerClient(base_url=worker_url, token=worker_token)
# After (+ comment block)
wc = WorkerClient(base_url=worker_url, token=worker_token, timeout=300.0)
```

8 lines changed (1 code line + 7 comment lines explaining context for future maintainers).

**No worker restart required.** Daemon restarted only.

---

## Validation evidence (live, this VPS)

```
$ ps -p 1437386 -o pid,etime,cmd
    PID     ELAPSED CMD
1437386       04:00 .venv/bin/python3 scripts/vps/notion-poller-daemon.py

$ awk '/PID 1437386 written/{found=1} found' /tmp/notion_poller.log | grep -c "Poll iteration failed"
0

$ awk '/PID 1437386 written/{found=1} found' /tmp/notion_poller.log | grep "Notion poll retrieved" | tail -1
2026-05-05 18:06:51,696 [INFO] dispatcher.notion_poller: Notion poll retrieved 20 comments since 2026-05-02T21:49:00+00:00

$ awk '/PID 1437386 written/{found=1} found' /tmp/notion_poller.log | grep "Processing" | wc -l
9 (and growing — backlog draining)

$ curl -fsS http://127.0.0.1:8088/health | jq .ok
true
```

Smoke comments confirmed processed:
```
2026-05-05 18:10:20 [INFO] dispatcher.notion_poller: Processing [echo->system] for comment 3575f443: @Rick  smoke ola 1b...
2026-05-05 18:10:20 [INFO] dispatcher.notion_poller: Processing [echo->lab]    for comment 3575f443: nota suelta regression test ola 1b...
```

> Note: `@Rick smoke ola 1b` was classified by the **legacy** intent classifier as `echo->system`. Ola 1b's structured-mention bypass (PR #284) is not loaded because that PR is not yet merged. Once PR #284 merges and daemon restarts, the same comment would be intercepted by `is_rick_mention()` BEFORE the legacy path. This actually **validates** the architectural need for PR #284: the legacy classifier doesn't recognize `@rick` as a mention.

---

## Collateral impact (3-day silence window 2026-05-02 17:49 → 2026-05-05 18:06)

| Surface | Impacted? | Notes |
|---|---|---|
| **PR #284 — Ola 1b mention adapter** | YES | Smoke verification blocked. Now unblocked. |
| **O8 Granola capitalization** | UNKNOWN | If triggered by Notion comment events via the poller, paused for 3 days. If triggered by direct DB scan or webhook, unaffected. **Needs separate check.** |
| **O15 Telegram bot bind** | UNKNOWN | If telegram bot ingests Notion comments via the poller, paused. Likely independent (telegram has its own ingestion). **Needs separate check.** |
| **smart_reply** | YES | All `@umbral-rick` comments + smart-reply intents silently dropped. Backlog draining now. |
| **Linear webhooks** | NO | Separate ingestion path (`dispatcher/linear_webhook.py`). |
| **OpenClaw gateway** | NO | Independent process. |
| **VM (Tailscale)** | NO | Health checks unaffected. |
| **F6 tournaments** | NO | Codex's parallel thread, separate codepath. |

---

## Architectural follow-up (separate issue — NOT this PR)

300s timeout is a band-aid. As the page keeps growing, latency will cross 300s too. Real fix:

**Option A (preferred):** Persist `next_cursor` per `(page_id, last_seen_comment_id)` in Redis. On each poll, resume from cursor; only paginate forward through *new* comments. O(new comments) per cycle instead of O(all comments).

**Option B:** Switch to descending order if Notion API supports it (`sort_direction=descending` on `/v1/comments`). Stop on first comment older than `since`. O(new comments) but requires Notion API support.

**Option C:** Rotate `created_time >= since` server-side filter if Notion API exposes one (currently doesn't on comments endpoint as of 2026-05).

Recommended: A. Estimated complexity: ~50 lines + Redis schema migration + tests.

---

## Recommendations for Mission Control

1. **O13 — stale-code detector** (priority: **HIGH**). Daemon ran for 21 days (2026-04-13 → 2026-05-05) on stale code without alarm. Need: alarm if any process's start time predates `git log --format=%ct -1` of its source file by > N days. Affected processes to monitor: `notion-poller-daemon.py`, `umbral-worker`, `openclaw-gateway`, `openclaw-dispatcher`.

2. **Worker health-check addition** (priority: **HIGH**). The `/health` endpoint currently reports task registry only. It does NOT report whether each task **succeeds within SLA**. Add per-task success rate + p95 latency over rolling 5-min window, and alarm on:
   - `notion.poll_comments` p95 > 60s OR success rate < 95%.
   - Any task with success rate dropping below 90% over 10 min.

3. **Pipeline silence alarm** (priority: **HIGH**). Alarm if `dispatcher.notion_poller: Processing` log lines drop to zero for > 30 minutes during business hours. Would have caught this 3 days ago.

4. **Daemon log rotation** (priority: MED). `/tmp/notion_poller.log` is 189MB, never rotated. logrotate config or `RotatingFileHandler` in the daemon.

5. **Cron supervision verification** (priority: MED). The cron wrapper (`scripts/vps/notion-poller-cron.sh`) only checks `kill -0` — a hung-but-alive process passes. Add: also alarm if PID hasn't logged in last 5 min.

---

## Delivery summary (YAML)

```yaml
sev1_status: fixed (tactical) — architectural follow-up pending
root_cause: |
  worker.notion_client.poll_comments paginates ALL comments on a page (oldest-first
  per Notion API, since-filter applied post-fetch). On the OpenClaw page (~30k
  comments) one call now takes ~62s, exceeding the daemon's default 30s
  WorkerClient timeout. Threshold crossed 2026-05-02 17:49 UTC.
fix_branch: copilot/fix-notion-poll-comments-timeout
fix_pr: https://github.com/Umbral-Bot/umbral-agent-stack/pull/290
fix_commit: 4c5e55c
worker_restored: true (worker was never broken; only client-side timeout was)
poller_processing_again: true
last_successful_processing_after_fix: "2026-05-05 18:10:20 UTC"
pr_284_unblocked: true (smoke can re-run once PR #284 + #290 both deploy)
collateral_impact:
  - O8_granola: unknown (needs separate check — see "Collateral impact" section)
  - O15_telegram: unknown (needs separate check)
  - smart_reply: yes (silent for 3 days, backlog draining now)
  - PR_284_smoke: yes (blocked, now unblocked)
  - F6_tournaments: no (independent codepath, Codex thread untouched)
evidence_file: docs/ops/notion-poll-comments-sev1-triage-2026-05-05.md
recommendations:
  - mission_control_stale_code_detector: high
  - worker_health_check_addition: high
  - pipeline_silence_alarm: high
  - daemon_log_rotation: med
  - cron_supervision_hung_process_alarm: med
  - architectural_cursor_checkpoint: separate_issue (preferred fix)
no_ejecutado:
  - PR #290 NOT merged (draft, awaiting David approval)
  - PR #284 NOT merged (still blocked on architectural decision; tactical fix in #290 unblocks smoke)
  - umbral-worker NOT restarted (was healthy throughout; only daemon needed restart)
  - F6 tournament gates NOT touched (Codex parallel thread)
  - architectural cursor-checkpoint refactor NOT implemented (proposed for separate issue)
```
