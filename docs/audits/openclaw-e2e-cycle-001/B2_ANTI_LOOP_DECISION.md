# B2 — Poller anti-loop guard (Option C, Phase 2)

**Date:** 2026-05-15
**Branch:** `copilot/b2-poller-author-guard`
**Status:** Implementation — PR DRAFT (not for merge yet)
**Scope:** repo only. No VPS, no Notion runtime touched.

## Context

Cycle 001 E2E audit (`docs/audits/openclaw-e2e-cycle-001/`) closed without an observed loop, but only because the cron interval (5 min) was larger than the observation window (2 min). The next poll cycle would have re-processed the bot's own reply via the smart-reply fallback.

The current poller (`dispatcher/notion_poller.py`) defends against echoes via:

1. `ECHO_PREFIX = "Rick:"` string check (line ~438 in the canonical commit).
2. Redis `SETNX` per-comment-id (24h TTL).

**Gap discovered in Phase 1 audit:** the v0 orchestrator handler `worker/tasks/rick_orchestrator.py` formatters do NOT prefix replies with `Rick:` (they emit `"Worker /health response: ..."`, `"Comando no reconocido en triage v0..."`, `"No pude consultar el worker /health..."`). For these replies:

- `ECHO_PREFIX` never matches → Layer 1 fails open.
- `SETNX` per-comment-id only catches a *re-processing* of the exact same comment id, not the bot's *reply* (which has a new comment id) → Layer 2 does not address the loop class.
- `smart_reply` would respond to the bot's reply on the next poll. Loop.

`@rick`-mention path is bounded by `_david_allowlist()` (Ola 1b adapter), so author-id-based defense was already implicit there. The fallback `smart_reply` path has no author guard.

## Decision

**Option C — author.id of the bot/integration as primary defense, ECHO_PREFIX as fallback, SETNX as third layer.**

Three independent layers, in order inside `_do_poll`:

| Layer | Mechanism | Covers |
|-------|-----------|--------|
| 1 (new) | `author == bot_user_id` skip | Any reply emitted by our integration, regardless of text shape. |
| 2 (kept) | `text.startswith("Rick:")` | Smart-reply replies + back-compat when bot id is unresolvable. |
| 3 (kept) | Redis `SETNX` per `comment_id` | Re-processing of the same comment id (e.g., transient poller restarts). |

### bot_user_id resolution

`_resolve_bot_user_id()` (new helper in `dispatcher/notion_poller.py`):

1. **Env override:** `NOTION_BOT_USER_ID` (optional). If set, returned verbatim, no HTTP. Predictable, deterministic, useful for tests and emergency override.
2. **Fallback:** `GET https://api.notion.com/v1/users/me` with `Authorization: Bearer $NOTION_API_KEY` (5 s timeout). Result cached in module-level dict for process lifetime.
3. **On failure** (no `NOTION_API_KEY`, HTTP ≥ 400, network error, malformed JSON): returns `None`, logs a single `WARNING`, caches `None` (no retry loop). Caller treats `None` as "guard unavailable" and silently falls through to ECHO_PREFIX (Layer 2).

`NOTION_BOT_USER_ID` is **not required** in this phase — leaving it unset triggers the `/v1/users/me` discovery path. Secrets are never printed.

## Alternatives considered

- **Option A — only `author.id`.** Rejected: if `/v1/users/me` is unresolvable at process start (e.g. NOTION_API_KEY rotation in progress) and we drop ECHO_PREFIX, every legacy `Rick:`-prefixed reply would loop. Defense-in-depth wins.
- **Option B — keep only ECHO_PREFIX + SETNX.** Rejected: known gap with v0 orchestrator reply formatters. Either fixes the formatters (touches `worker/tasks/rick_orchestrator.py` semantics) or accepts the loop class.

## Consequences

- **+** Closes the observed gap without modifying v0 orchestrator reply text.
- **+** Zero impact when bot id is unresolvable: existing path preserved bit-for-bit.
- **+** One HTTP call per process lifetime (cached, 5 s timeout, never blocks > 5 s).
- **−** Adds a soft dependency on `NOTION_API_KEY` being available to the dispatcher process (already the case in VPS env). If absent, falls back gracefully.
- **−** If the integration token is rotated to a different bot, the cache must be invalidated (process restart). Acceptable: token rotation is already a "restart the service" event.

## Tests added

`tests/test_notion_poller.py` (+8 tests, total 18 pass):

- `test_resolve_bot_user_id_env_override_no_http` — env wins, no HTTP.
- `test_resolve_bot_user_id_falls_back_to_users_me` — discovery + module cache.
- `test_resolve_bot_user_id_no_token_returns_none_and_warns` — graceful degradation.
- `test_resolve_bot_user_id_http_error_returns_none` — 4xx handled, no leaks.
- `test_do_poll_skips_bot_reply_without_rick_prefix` — **the critical gap test**.
- `test_do_poll_skips_bot_reply_with_rick_prefix` — both layers concur.
- `test_do_poll_fallback_echo_prefix_when_bot_id_unresolvable` — no regression.
- `test_do_poll_processes_authorized_david_mention` — David's @rick still routed.

Run: `python -m pytest tests/test_notion_poller.py -v` → 18 passed.

## Out of scope (explicit)

- VPS deploy. PR is DRAFT.
- Modifying `worker/tasks/rick_orchestrator.py` reply formatters.
- Setting `NOTION_BOT_USER_ID` in VPS env (the `/v1/users/me` fallback handles it).
- Touching `dispatcher/smart_reply.py` or `dispatcher/rick_mention.py` semantics.
- Notion comment writes (no live Notion call from this PR).

## Deploy notes (NOT executed in this PR)

The poller module `dispatcher/notion_poller.py` is loaded by **two independent VPS processes** (per task 037 evidence, `docs/roadmap/12-q2-2026-platform-first-plan.md`):

1. `openclaw-dispatcher.service` (systemd user unit) → imports it via `dispatcher/service.py`.
2. `scripts/vps/notion-poller-daemon.py` → launched by `cron */5 notion-poller-cron.sh` (auto-respawn, NOT a systemd unit).

Both must run new code for the guard to be effective end-to-end. Restarting only one leaves a partial deploy until the other path is refreshed.

Recommended sequence (with explicit authorization, separate from this PR):

```
systemctl --user restart openclaw-dispatcher   # immediate
pkill -f notion-poller-daemon.py               # forces cron to respawn within 5 min
# or wait one cron cycle if no urgency
```

Verification (after restart of either process):

```
journalctl --user -u openclaw-dispatcher --since '2 min ago' | grep 'B2 author guard'
tail -50 /tmp/notion_poller_cron.log | grep 'B2 author guard'
```

Expected: a single INFO line `B2 author guard: bot user id resolved (cached for process lifetime).` per process on first poll after restart.

## Rollback

Single commit on isolated branch. Revert: `git revert <sha>` or close PR without merging. Runtime is unaffected until VPS pulls + service restart.
