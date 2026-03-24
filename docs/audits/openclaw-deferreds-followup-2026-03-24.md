# OpenClaw deferreds follow-up - 2026-03-24

## Scope

This pass closes as much as possible of the deferred OpenClaw work left after Actions 1, 2, 3, 4, 5, 6, and 8:

- revalidate VPS -> VM reachability over Tailscale after the reboot
- implement a repo-side snapshot for panel/OpenClaw activity
- evaluate and implement finer token or cost attribution where viable
- leave a clear Tavily/provider recommendation
- note additional improvement opportunities discovered during the pass

## Result

The deferred package is materially advanced and mostly closed:

- VPS -> VM Tailscale reachability was revalidated and is still degraded after reboot
- repo-side runtime snapshot is now implemented and versioned
- finer OpenClaw usage attribution is now partially implemented via:
  - `ops_log` `llm_usage` events for Worker-side LLM tasks
  - session-store snapshotting from `~/.openclaw/agents/*/sessions/sessions.json`
- Tavily is no longer required for healthy runtime behavior; Gemini grounded search is the operational path that currently works

What remains open is not lack of implementation, but explicit operational choice:

- whether Tavily should be funded and kept as a secondary backend
- whether exact billing-grade cost accounting is worth the extra complexity

## Revalidated VPS -> VM tailnet state

The VM internet recovery remains valid, but the direct service path over tailnet is still not healthy after reboot.

Evidence:

- from VPS:
  - `tailscale status --json` shows `PCRick` / `100.109.16.40` with `Active=true`, `Online=false`
  - `ping -c 2 100.109.16.40` -> `100% packet loss`
  - `curl --max-time 10 http://100.109.16.40:8088/health` -> timeout
  - `curl --max-time 10 http://100.109.16.40:8089/health` -> timeout
- from local/host side:
  - `Invoke-RestMethod http://100.109.16.40:8088/health` -> connection failure
  - `Invoke-RestMethod http://100.109.16.40:8089/health` -> connection failure

Status:

- VM internet: recovered earlier and still treated as good
- VM direct tailnet service path from VPS: still degraded

Related record:

- [vm-tailnet-operational-recovery-2026-03-15.md](./vm-tailnet-operational-recovery-2026-03-15.md)

## Repo-side tracking snapshot

Implemented:

- [scripts/openclaw_runtime_snapshot.py](../../scripts/openclaw_runtime_snapshot.py)
- [reports/runtime/openclaw-runtime-snapshot-2026-03-24.md](../../reports/runtime/openclaw-runtime-snapshot-2026-03-24.md)
- [reports/runtime/openclaw-runtime-snapshot-latest.json](../../reports/runtime/openclaw-runtime-snapshot-latest.json)

The snapshot now consolidates:

- panel activity from `system_activity`
- Worker-side OpenClaw runtime events from `source=openclaw_gateway`
- Worker-side `llm_usage` events from `ops_log`
- session-store usage from `~/.openclaw/agents/*/sessions/sessions.json`

## Snapshot highlights (7-day window)

From the current runtime snapshot:

- OpenClaw runtime events: `12`
  - completed: `8`
  - failed: `0`
  - blocked: `4`
- traced Worker-side LLM events: `2`
- traced Worker-side LLM tokens: `319`
- traced Worker-side proxy cost: `0.000069 USD`
- panel reads/writes:
  - reads: `128`
  - writes: `120`

Top OpenClaw runtime tasks in the window:

- `google.calendar.list_events` -> `2`
- `linear.list_teams` -> `2`
- `research.web` -> `2`
- `composite.research_report` -> `1`
- `llm.generate` -> `1`

## Session usage highlights

OpenClaw session stores do contain usable token fields:

- `inputTokens`
- `outputTokens`
- `totalTokens`
- `cacheRead`
- `cacheWrite`

That is enough to build a useful usage snapshot by agent and model, even though it is still not billing-grade accounting.

Top agent totals in the current cut:

- `main` -> `47` sessions, `1,505,398` total tokens
- `rick-ops` -> `50` sessions, `1,276,478` total tokens
- `rick-orchestrator` -> `1` session, `21,010` total tokens
- `rick-tracker` -> `1` session, `16,079` total tokens
- `rick-qa` -> `1` session, `13,629` total tokens
- `rick-delivery` -> `1` session, `13,307` total tokens

Top model totals in the current cut:

- `gpt-5.3-codex` / `openai-codex` -> `52` sessions, `1,303,414` total tokens
- `gemini-2.5-flash` / `google` -> `37` sessions, `1,078,078` total tokens
- `gpt-5.4` / `openai-codex` -> `8` sessions, `393,314` total tokens

## Cost and token attribution: final status

What is now implemented:

1. Worker-side LLM usage attribution in `ops_log`
   - direct `llm.generate`
   - composite query generation for `composite.research_report`
2. Repo-side snapshot of panel activity
3. Repo-side snapshot of session token usage by agent and model
4. Rough proxy cost estimate using repo-side rate tables

What is still not exact:

- `research.web` via Gemini grounded search does not expose token usage in `ops_log` today
- the current proxy cost model does not bill `cacheRead` or `cacheWrite`
- OpenClaw session totals are snapshots of stored session state, not official invoice lines

Conclusion:

- useful operational attribution: **yes**
- exact provider billing accounting: **not yet**

## Tavily / provider recommendation

Current state:

- Tavily still fails by quota/plan exhaustion when used directly
- runtime no longer depends on Tavily to stay functional
- `research.web` and `scripts/web_discovery.py` already have a healthy operational path through Gemini grounded search

Recommendation:

1. Keep Gemini grounded search as the canonical discovery path now.
2. Treat Tavily as optional or secondary, not required.
3. Only recharge Tavily if there is a concrete use case where its search quality or policy is materially better than Gemini grounded search.
4. If Tavily is not re-funded soon, document it as intentionally secondary and stop treating its quota state as an incident.

Practical reading:

- runtime problem: already solved
- provider strategy problem: still a business or budget choice

## Additional opportunities found

1. Add a small exporter cron for the runtime snapshot so `reports/runtime/openclaw-runtime-snapshot-latest.json` can be refreshed automatically from VPS.
2. Extend tracing for Gemini grounded search if the provider starts returning token usage or cost hints.
3. Add a compact "usage summary" block to `Dashboard Rick` rather than exposing the full detail in Notion.
4. Revalidate and, if needed, re-harden the fallback path between VPS and VM so the execution plane does not depend on a manually rechecked tailnet.
5. Add retry/backoff specifically for `Gemini 503 UNAVAILABLE` on report-generation paths like `composite.research_report`.

## Bottom line

This deferred pass closes the important part of the remaining work:

- the repo now has a concrete runtime snapshot
- usage is now attributable at panel, Worker LLM, session, agent, and model level
- the Tailscale weakness is no longer assumed away; it is documented as still degraded after reboot
- Tavily is no longer a runtime blocker and should be handled as a provider strategy decision, not an outage
