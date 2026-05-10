# Wave 2.A — n8n applicability scan

**Date**: 2026-05-10
**Scope**: Decide, per candidate use case, whether n8n is the right tool
**now**, **later**, or **never** for the editorial pipeline (#405 / #402 /
#404-lite) and adjacent automation surface.
**Restrictions in force** (Wave 2.A megaprompt §2):

* No n8n workflow that publishes (LinkedIn / blog / X / newsletter).
* No n8n as the source of truth for editorial gates.
* No n8n that writes human approvals in Notion (`aprobado_contenido`,
  `autorizar_publicacion`, `gate_invalidado`).
* No n8n that flips `publish_enabled` runtime flag.
* No n8n productive workflows activated as a side effect of this scan.

This document is **design-only**. Nothing in `scripts/`, `dispatcher/`,
`worker/`, or n8n itself is changed by Wave 2.A as a result.

## Decision rubric

| Decision           | Meaning                                                                                       |
|---|---|
| **Use now**        | n8n adds value, no restriction violated, low integration cost, can ship in Wave 2.A or 2.B.    |
| **Document later** | n8n could fit, but blocked by an upstream contract (#404 dashboard, #406 source-use, #408 retro). Park as design intent.  |
| **Discard**        | n8n is the wrong tool (would violate restriction, duplicate existing service, or create runtime authority drift). |

Where Python wins:

* Anything that needs to read SQLite directly from
  `~/.config/umbral/state.sqlite`.
* Anything that needs to call `lib.publish_guard.assert_can_publish` —
  the guard is the single source of truth, must not be re-implemented.
* Anything that flips runtime authority (PublishFlags).

Where n8n wins:

* Webhook fan-in (single endpoint that 3-4 producers POST to).
* Cron-driven shaping of payloads from JSONL → email/Telegram/Notion
  *as observability*, never as authority.
* Visual flow when David needs to inspect / pause / resume by hand.

## Use cases scanned (15)

| # | Use case                                                                                       | Decision         | Rationale                                                                                                                                                       |
|---|---|---|---|
| 1 | **Tail `publish_log.jsonl` → Telegram alert when `would_publish=true && publish_enabled=true && dry_run=false`** | Document later   | Depends on #404-lite merging + a producer wiring `would_publish`. n8n Read Binary File + cron is a natural fit. NOT a runtime authority — pure observability. Park until #404-lite is in `main`. |
| 2 | **Daily 09:00 digest of `publish_log.jsonl` (last 24h) → email to David**                     | Document later   | Same dependency on #404-lite. Trivial n8n cron + Code node + Send Email. Useful for retro. Not authority.                                                       |
| 3 | **Weekly Friday-retro evidence pack (publish_log + ops_log slice) → Notion page**             | Document later   | Combines #404-lite tail + Notion MCP. Requires #408 retro contract to define the page schema. n8n Notion node is mature.                                        |
| 4 | **Replace `publish_guard.assert_can_publish` with an n8n Function node**                      | **Discard**      | Violates "n8n not source of truth for gates". The guard's pure-Python contract + tests is the entire point of #405 / #402. Re-implementing in JS would fork the truth.|
| 5 | **n8n flips `publish_enabled` based on a Notion checkbox**                                    | **Discard**      | Violates "no n8n flips runtime flag". Runtime authority lives in `PublishFlags` env / DB; flipping it from a workflow erases the audit trail.                   |
| 6 | **n8n writes `autorizar_publicacion=true` in Notion when David replies to an email**           | **Discard**      | Violates "no n8n writes human approvals". The human approval channel is Notion UI, by hand, on purpose.                                                         |
| 7 | **n8n calls LinkedIn POST endpoint when guard returns `would_publish=true`**                  | **Discard**      | Violates "no n8n that publishes". Publication remains in `scripts/discovery/stage9_*` Python.                                                                   |
| 8 | **Webhook fan-in: 3 RSS scrapers POST raw items → n8n normalizes → enqueue dispatcher task**  | Use now          | n8n Webhook + Set + HTTP Request to dispatcher is the *original* sweet spot for n8n. No restriction touched (no gate, no publish, no human approval).           |
| 9 | **n8n cron polls `state.sqlite` every 6h → Slack notification of new candidate signals**       | Document later   | Pure observability. SQLite read is awkward from n8n directly; better via a Python helper script that n8n calls via HTTP. Park until #404 dashboard contract.    |
| 10 | **Error-workflow that pages David on dispatcher 5xx**                                         | Use now          | Generic SRE pattern, no editorial-pipeline coupling. n8n Error Trigger + Telegram. Already a pattern in n8n docs (`error workflows`).                          |
| 11 | **n8n schedules Granola transcript ingestion at 22:00 daily**                                 | Document later   | Granola pipeline is owned by `umbral-agent-stack/notion/granola_*` Python. Cron is currently in systemd timers (per `notion-governance` VPS reality rule). Moving to n8n duplicates scheduling authority. Defer until a clear need to consolidate.  |
| 12 | **Build a "Wave 2.A status board" in n8n that aggregates PR #407 / #410 / #411 + tests + flags state** | Document later   | Useful but deeply tied to GitHub API + dispatcher health. Better as a static HTML or Notion page rendered by Python; n8n adds nothing here.                    |
| 13 | **n8n watches `~/.config/umbral/ops_log.jsonl` for `publish_guard.runtime_block` and pings David instantly** | Use now          | Observability of the stop button. Reads a file, applies a filter, sends an alert. No authority touched. Useful even before #404-lite ships.                    |
| 14 | **n8n re-runs failed Stage 7.5 generations on a schedule**                                    | **Discard**      | Stage 7.5 is frozen for Wave 2.A (restriction). Even outside the freeze, retry policy lives in dispatcher.                                                     |
| 15 | **n8n auto-merges PRs when CI passes**                                                        | **Discard**      | Violates "no removal of `do-not-merge` for PR #407 / #410 / #411". Also general bad practice for editorial-pipeline PRs that need human review.                |

## Tally

* **Use now (3)**: #8 webhook fan-in, #10 dispatcher error pager, #13
  ops_log runtime-block alert.
* **Document later (5)**: #1, #2, #3, #9, #11, #12.
* **Discard (6)**: #4, #5, #6, #7, #14, #15.

## n8n service status (design-only check)

The Wave 2.A megaprompt forbids activating productive workflows. To stay
inside the restriction:

* Confirm the existing n8n instance is running ONLY in `dev` /
  `inactive` mode for Wave 2.A. Verification belongs on the VPS, not
  in this scan (per `cross-repo-handoff-rules` + `notion-governance`
  VPS reality rule). See VPS-4 prompt in `docs/audits/2026-05-10-wave2a-vps-prompts.md`.
* Do NOT activate any workflow as a side effect of this design pass.

## Authority diagram (Wave 2.A target)

```text
Notion (human approvals: aprobado_contenido, autorizar_publicacion, gate_invalidado)
        │
        ▼
Python publish_guard.assert_can_publish  ←  PublishFlags (env / DB; #405)
        │                                            ▲
        ├──→ ops_log.jsonl  (#405)                   │
        ├──→ publish_log.jsonl  (#404-lite, post-merge wiring)
        │                                            │
        ▼                                            │
Python publisher  (#402 publication_content_hash check)
        │                                            │
        ▼                                            │
LinkedIn / blog / X (real POST, Wave 2.B+)            │
                                                    n8n (observability ONLY,
                                                         use cases #1, #2, #3, #8, #10, #13)
```

n8n sits *to the side* of the authority chain. Every authority arrow is
Python-owned. Every n8n touchpoint is either input (webhook fan-in) or
output (alerts, digests).

## What this document does NOT decide

* Whether n8n is the right tool for **Wave 2.B** publish-window
  scheduling (deferred to that wave's plan).
* Whether to migrate Granola cron from systemd to n8n (parked in #11).
* Whether to give n8n write access to GitHub (used in #15 as a discard
  example; not under consideration).
* Concrete workflow JSON exports (this is design-only; implementation
  lands when an issue is opened per "use now" item).

## References

* n8n knowledge base (snapshot):
  `docs/external-context/n8n-llms-full.txt`
* Wave 2.A plan: `docs/audits/2026-05-10-wave2a-plan.md`
* `docs/editorial-pipeline/runtime-flags-contract.md`
* `docs/editorial-pipeline/publication-content-hash-contract.md`
* `docs/editorial-pipeline/publish-log-contract.md`
