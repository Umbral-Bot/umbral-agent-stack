# Copilot CLI — F5 `rick-tech` Agent Evidence

**Phase:** F5 — scaffold the `rick-tech` agent surface.
**Branch:** `rick/copilot-cli-capability-design`
**Status:** capability remains **DISABLED** (`copilot_cli.enabled: false`,
`RICK_COPILOT_CLI_ENABLED=false`, `phase_blocks_real_execution: true`).

---

## 1. What F5 actually does

F5 lands a new agent override directory `rick-tech/` containing `ROLE.md`
and `HEARTBEAT.md`. This declares — purely as documentation /
governance — the human-and-agent surface authorized to consume the
`copilot_cli.run` task once it is enabled. It does **not** flip any flag,
does **not** modify the live runtime, does **not** modify
`rick-delivery`, and does **not** request a single Copilot CLI call.

## 2. Why a separate `rick-tech` (not extend `rick-delivery`)

`rick-delivery` already has the **publish/materialize** surface:
`github.commit_and_push`, `github.open_pr`, `notion.upsert_*`,
`linear.update_issue_status` for delivery state, `document.create_*` for
artifacts that ship.

If we attached `copilot_cli.run` to `rick-delivery`, a single confused or
prompt-injected delivery flow could hand a Copilot output directly into a
commit + push + PR pipeline with no air gap. The whole point of F1–F4 is
that **every Copilot output is artifact-only and humans materialize**.

Putting Copilot CLI behind a **separate** `rick-tech` surface means:
- The technical agent can read, reason, and produce text artifacts.
- It cannot, by construction (declared in ROLE.md, enforced by the
  worker policy + wrapper deny-list), call any publish surface.
- Materialization always requires a Tech → Delivery (or Tech → David)
  handoff, which is auditable.

## 3. Files added (F5)

```
openclaw/workspace-agent-overrides/rick-tech/ROLE.md       (new, ~180 lines)
openclaw/workspace-agent-overrides/rick-tech/HEARTBEAT.md  (new, 5 bullets)
tests/test_rick_tech_agent.py                              (new, 9 tests)
docs/copilot-cli-f5-rick-tech-agent-evidence.md            (this file)
docs/copilot-cli-capability-design.md                      (F5 status)
```

Files explicitly **not** touched in F5:
- `openclaw/workspace-agent-overrides/rick-delivery/ROLE.md` ← unchanged
- `openclaw/workspace-agent-overrides/rick-delivery/HEARTBEAT.md` ← unchanged
- `~/.openclaw/openclaw.json` ← live runtime, never touched
- `config/tool_policy.yaml` ← already gated in F4
- `.env.example` ← still `RICK_COPILOT_CLI_ENABLED=false`
- `worker/tasks/copilot_cli.py` ← still F3 skeleton
- Any sandbox image, runner script, or systemd unit

## 4. Role contract summary

| Aspect | Rick Tech |
|---|---|
| Identity | Technical analysis agent; only surface authorized to call `copilot_cli.run` |
| Can read | Repos, evidence, test/lint outputs, runbooks |
| Can write | Artifacts under `reports/copilot-cli/<run_id>/` (gitignored) — text only |
| Tools allowed | `copilot_cli.run` (when enabled); read-only repo/RAG tools; `linear.update_issue_status` |
| Tools forbidden | `github.commit_and_push`, `github.open_pr`, all `notion.upsert_*`, all `notion.update_*`, all `notion.add_comment`, `windows.*`, `gui.*`, `browser.*`, `client.*`, `granola.*`, `make.post_webhook`, `n8n.*`, `figma.add_comment`, all `gh *` mutations |
| Handoffs | Tech → Delivery (materialize), Tech → QA (validate), Tech → Orchestrator (return), Tech → David (escalate before any mutation) |
| QA required | Yes — `rick-qa` validates patches before merge; David approves materialization |
| Failure policy | On `capability_disabled` / `mission_not_allowed` / `banned_subcommand` → report verbatim, do not retry with workaround |
| Escalation policy | Materialization, token rotation, capability flip, egress activation, sandbox image bumps → David approval |
| Status of `copilot_cli.run` | Declared as future tool; **not enabled** in F5 (env + policy + phase_blocks_real_execution all enforce off) |

## 5. Tests

```
$ WORKER_TOKEN=test python -m pytest tests/test_rick_tech_agent.py tests/test_copilot_cli.py -q
.......................................................                  [100%]
55 passed in 0.89s
```

Coverage delta vs F4 (+9 tests):
- `test_rick_tech_dir_exists`
- `test_rick_tech_has_role_and_heartbeat`
- 9 × `test_rick_tech_role_states_hard_boundaries[…]` (no publish, no
  gates, no Notion writes, no `git push`, no `gh pr create/merge/comment`,
  no token persistence, `COPILOT_GITHUB_TOKEN` named)
- `test_rick_tech_role_marks_copilot_cli_disabled` (env + policy +
  `phase_blocks_real_execution` references present)
- `test_rick_tech_role_requires_human_materialization`
- `test_rick_tech_role_lists_only_4_approved_missions`
- `test_rick_delivery_role_untouched_by_f5` (HEAD diff inspection — fails
  if rick-delivery/ROLE.md appears in the F5 commit)
- `test_rick_tech_heartbeat_mentions_escalation_and_artifacts`

Regression: `tests/test_sync_openclaw_workspace_governance.py` still green
(governance sync script picks up the new override automatically — no script
change needed).

## 6. What F5 explicitly does NOT do

- ✗ Does not flip `RICK_COPILOT_CLI_ENABLED`.
- ✗ Does not flip `copilot_cli.enabled`.
- ✗ Does not activate egress.
- ✗ Does not provision token, EnvironmentFile, or systemd dropin.
- ✗ Does not call subprocess.
- ✗ Does not invoke real Copilot CLI.
- ✗ Does not modify `rick-delivery` (test enforces this).
- ✗ Does not modify live `~/.openclaw/openclaw.json`.
- ✗ Does not restart any service.
- ✗ Does not touch Notion / gates / publication.
- ✗ Does not open / merge / comment any PR.

## 7. Risks / open items for F6

- **Token plumbing (F6 prerequisite):** `/etc/umbral/copilot-cli.env` +
  `/etc/umbral/copilot-cli-secrets.env`, mode `0600`, owner `rick`. Token:
  `COPILOT_GITHUB_TOKEN` (fine-grained PAT v2 with `Copilot Requests`).
  Document how to rotate.
- **Separate execute flag (F6):** `RICK_COPILOT_CLI_EXECUTE` distinct from
  `RICK_COPILOT_CLI_ENABLED`. Lifting `phase_blocks_real_execution`
  requires the execute flag, not just the enable flag.
- **Egress activation (F6):** `copilot_cli.egress.activated: true` plus
  iptables/nftables rules per design §10.2. Only allow the Copilot
  endpoints; everything else stays blocked.
- **Operation scoping enforcement (F6):**
  `allowed_operations`/`forbidden_operations` per mission are policy text
  today. F6 must wire the wrapper / handler to actively refuse anything
  outside `allowed_operations`.
- **Live runtime sync:** the new `rick-tech` override only takes effect on
  the live VPS after `scripts/sync_openclaw_workspace_governance.py`
  pushes it into `~/.openclaw/`. F5 does NOT do that; David runs the
  sync manually when ready.
- **Mailbox / `.agents/` integration:** F5 does not yet wire `rick-tech`
  into the multi-agent coordination protocol (`.agents/PROTOCOL.md`,
  `.agents/board.md`). That is a small follow-up before F6 productive
  use, not a hard prerequisite for the role contract itself.

## 8. Next prompt recommendation (F6 — DO NOT START WITHOUT EXPLICIT APPROVAL)

> Authorize F6 step 1 of N: token plumbing + separate execute flag.
> Add `RICK_COPILOT_CLI_EXECUTE=false` to `.env.example`, document
> EnvironmentFile layout, add a token-presence test (no real token
> needed). Capability remains **disabled** until step 2 of F6.
> No egress yet. PR remains draft.
