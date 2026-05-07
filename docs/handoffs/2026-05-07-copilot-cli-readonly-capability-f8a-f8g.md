# Copilot CLI read-only capability — F8A to F8G handoff

Date: 2026-05-07  
Repo: `Umbral-Bot/umbral-agent-stack`  
Status: read-only canonical path proven; write-limited missions still blocked by hardening work.

## Executive summary

We turned the GitHub Copilot CLI integration from a gated design stub into a
working, audited, read-only capability that Rick and subagents can use through
`copilot_cli.run`.

The proven production-safe slice is:

- Read-only repo analysis through `copilot_cli.run`.
- Scoped Docker network egress through `copilot-egress` / `br-copilot`.
- GitHub Meta CIDR based allow-listing for GitHub/Copilot endpoints.
- Token discipline: `COPILOT_GITHUB_TOKEN` passed by name only, never printed.
- Hardened sandbox invocation with read-only bind mount, tmpfs, non-root user,
  dropped capabilities, `no-new-privileges`, and no builtin MCPs.
- Audit JSONL + artifacts + manifest + secret scan per real run.
- Default canonical model pinned to `gpt-5.5` with Copilot CLI
  `--reasoning-effort high` in PR #337.

The capability is **not** yet approved for file writes, patch application,
commits, PR creation, Notion writes, deploys, or arbitrary shell/network access.

## Current operating position

| Area | State | Evidence |
| --- | --- | --- |
| Egress | green | F8C/F8D/F8E: `nft_drop_delta=0/0` after GitHub Meta CIDRs |
| Auth | green | F8E retry: token with `Copilot Requests` passed T1 |
| Canonical worker path | green | F8E T4: `copilot_cli.run` completed with marker |
| Quality ladder | green | F8E T5-T7 scored 5/5 |
| Max OpenAI model | green direct | F8F: `gpt-5.5` passed T1-T7 |
| Max Anthropic model | unavailable | F8F: Opus 4.6 candidates unavailable for token/account |
| Canonical `gpt-5.5` override | pending fix | F8F T8 found display-name vs slug mismatch; PR #337 fixes |
| Write-limited missions | blocked | T6 HIGH risks still unresolved |

## Important PR chain

- PR #322 — F8A run-6 after token refresh: infra path worked but scoped
  egress dropped GitHub load balancer IPs.
- PR #326 — F8B egress/model diagnostic: identified sibling GitHub LB IP
  `140.82.113.21` outside per-FQDN snapshot but inside GitHub Meta `api` CIDR.
- PR #327 — GitHub Meta CIDR resolver fix: adds
  `--include-github-meta` and merges GitHub Meta CIDRs into nft sets.
- PR #328 — F8C retry: egress fixed (`0/0` drops), but `Claude Opus 4.7`
  unavailable.
- PR #330 — F8D default-model proof: egress good, backend reached, old token
  lacked `Copilot Requests`.
- PR #331 — F8E progressive ladder: after token rotation, T1-T7 green and
  canonical `copilot_cli.run` green with default model.
- PR #335 — F8F max-model benchmark: `gpt-5.5` available and strong; Opus 4.6
  unavailable; canonical T8 blocked by policy/CLI model-name mismatch.
- PR #337 — F8G pin canonical model: pins `gpt-5.5`, adds aliases for
  `GPT-5.5`, and configures `--reasoning-effort high`.

## Runtime model

The worker task is `copilot_cli.run`, implemented in
`worker/tasks/copilot_cli.py`.

Runtime gates:

1. L1 env flag: `RICK_COPILOT_CLI_ENABLED=true`.
2. L2 policy flag: `config/tool_policy.yaml :: copilot_cli.enabled=true`.
3. L3 execution flag: `RICK_COPILOT_CLI_EXECUTE=true`.
4. L4 egress flag: `config/tool_policy.yaml :: copilot_cli.egress.activated=true`.
5. L5 code gate: `_REAL_EXECUTION_IMPLEMENTED=True`.

Operational default:

- Keep L3 and L4 closed.
- Open them only during an approved probe/run window.
- Roll back immediately after the run.

## Egress model

The original per-FQDN DNS snapshot was fragile because GitHub load-balances
among sibling IPs. F8B proved the container could resolve a sibling IP that was
not in the nft set.

The fix is GitHub Meta CIDR inclusion:

- Resolver: `scripts/copilot_egress_resolver.py --include-github-meta`.
- Network: Docker bridge `copilot-egress` with bridge name `br-copilot`.
- Enforcement: `infra/networking/copilot-egress.nft.example`.
- Required proof: `140.82.112.0/20` present in the v4 set and
  `nft_drop_delta=0/0` during test windows.

## Token model

The old token was valid for `api.github.com/user` but failed Copilot backend
auth with a `Copilot Requests` error.

The working token pattern is a fine-grained GitHub token under an account with
active Copilot access and account permissions:

- `Copilot Requests: Read-only`
- `Copilot Chat: Read-only`
- `Copilot Editor Context: Read-only`
- `Models: Read-only`

Never print the token. Evidence uses only:

- `COPILOT_GITHUB_TOKEN=present_by_name`
- token length
- short hash fingerprint for rotation tracking

## Proven read-only mission envelope

Recommended `copilot_cli.run` input shape:

```json
{
  "task": "copilot_cli.run",
  "input": {
    "mission": "research",
    "requested_operations": ["read_repo", "summarize", "explain", "cite_files"],
    "repo_path": "/home/rick/umbral-agent-stack",
    "dry_run": false,
    "max_wall_sec": 300,
    "prompt": "Read the repo and return a concise, cited analysis. Do not write files."
  }
}
```

Allowed mission types remain read-only / artifact-only:

- `research`
- `lint-suggest`
- `test-explain`
- `runbook-draft`

Hard-denied operations include:

- `apply_patch`
- `git_commit`
- `git_push`
- `gh_pr_create`
- `gh_pr_merge`
- `notion_write`
- `publish`
- `deploy`
- `secret_read`
- `secret_write`
- `shell_exec`
- `write_files`

## Model policy

F8F proved that GitHub Copilot CLI accepts the slug `gpt-5.5`, not the display
name `GPT-5.5`, in this environment.

PR #337 sets:

```yaml
copilot_cli:
  default_model: gpt-5.5
  force_default_model: true
  default_reasoning_effort: high
  model_aliases:
    GPT-5.5: gpt-5.5
    GPT 5.5: gpt-5.5
```

`high` is the maximum reasoning effort currently documented for GitHub
Copilot CLI (`low`, `medium`, `high`). There is no documented `xhigh` or
`extreme` flag in Copilot CLI. If GitHub later exposes a higher effort level,
update `worker/tool_policy.py` validation and re-run the F8F/F8G canonical
probe.

Opus status:

- `Claude Opus 4.6`
- `Claude Opus 4.6 (fast mode)`
- `Claude Opus 4.6 (fast mode) (preview)`

were unavailable for the current token/account during F8F. Do not route
production traffic to Opus until availability is proven with a fresh F8 probe.

## What F8E proved

F8E was the full progressive capability ladder:

- T1 token entitlement: green.
- T2 minimal compute: green.
- T3 Opus override: partial amarillo because Opus unavailable.
- T4 canonical worker path: green.
- T5 repo comprehension: green, 5/5.
- T6 risk review: green, 5/5.
- T7 text-only patch proposal plan: green, 5/5.

Final scores:

| Score | Value |
| --- | --- |
| `network_score` | 1.0 |
| `auth_score` | 1.0 |
| `canonical_score` | 1.0 |
| `quality_score` | 1.0 |
| `safety_score` | 1.0 |
| `model_power_score` | 0.5 |

## What F8F proved

F8F benchmarked maximum available model candidates:

- `gpt-5.5`: available; T1-T7 green; quality 5/5.
- Opus 4.6 variants: unavailable for the token/account.
- T8 canonical path: amarillo because the worker policy used display name
  `GPT-5.5`, while the CLI required slug `gpt-5.5`.

This led directly to PR #337.

## Remaining hardening before write-limited missions

Do not enable write-limited missions until these are addressed:

1. DNS pinning / controlled resolver:
   `infra/networking/copilot-egress.nft.example` currently allows DNS in the
   sandbox path. Pin resolver IPs or route through a logging resolver tied to
   policy.
2. Kernel-level exec defense:
   The wrapper reduces tool surface, but Copilot-internal behavior should also
   be constrained with seccomp/AppArmor or equivalent to block `git`, `gh`,
   `sh`, and dangerous exec paths where possible.
3. Write enforcement and diff capture:
   Add a writable overlay/tmp workspace, capture diff artifacts, enforce file
   count/path limits, and require human approval before materialization.
4. Deterministic sandbox image:
   Prefer `COPILOT_CLI_SANDBOX_IMAGE=umbral-sandbox-copilot-cli:<sha/tag>` over
   relying on `:latest`.

## Standard rollback checklist

After any real run:

```bash
cp "$BACKUP/copilot-cli.env" ~/.config/openclaw/copilot-cli.env
cp "$BACKUP/tool_policy.yaml" config/tool_policy.yaml
rm -f ~/.config/systemd/user/umbral-worker.service.d/<temporary-dropin>.conf
systemctl --user daemon-reload
systemctl --user restart umbral-worker.service
curl -fsS -o /dev/null -w "HEALTH=%{http_code}\n" http://127.0.0.1:8088/health
sudo nft delete table inet copilot_egress || true
docker network rm copilot-egress || true
shred -u /tmp/.f8*-tok /tmp/.f8*-wtok 2>/dev/null || true
```

Verify:

- `/health=200`
- `RICK_COPILOT_CLI_EXECUTE=false`
- `egress.activated=false`
- no `inet copilot_egress` nft table
- no `copilot-egress` docker network
- no token printed in logs/artifacts

## Handoff prompt for a coordinating Copilot agent

Use this prompt when Copilot is coordinating a larger system and needs to treat
this capability as one gear inside the whole stack:

```text
You are coordinating work inside the Umbral Agent Stack. Before making plans,
read this repo handoff:

docs/handoffs/2026-05-07-copilot-cli-readonly-capability-f8a-f8g.md

Context you must preserve:

1. GitHub Copilot CLI is now a proven READ-ONLY capability through
   `copilot_cli.run`, not a general write agent.
2. The safe path is:
   - `mission=research`
   - `requested_operations=["read_repo","summarize","explain","cite_files"]`
   - `repo_path=/home/rick/umbral-agent-stack`
   - no file writes
   - no shell execution
   - no git/gh mutations
   - no Notion writes
3. Egress only works safely through the scoped `copilot-egress` Docker bridge
   and nft table populated by `scripts/copilot_egress_resolver.py
   --include-github-meta`.
4. Token handling is strict: never print or request the token value. Only use
   `COPILOT_GITHUB_TOKEN=present_by_name`, length, and short fingerprint if
   rotation evidence is needed.
5. The canonical model policy is `gpt-5.5` with `--reasoning-effort high`
   once PR #337 is merged. `GPT-5.5` is a human display alias; the CLI slug is
   `gpt-5.5`.
6. Opus 4.6 variants were unavailable for the current token/account in F8F.
   Do not route production work to Opus unless a fresh availability probe
   proves it.
7. Write-limited missions are intentionally blocked until hardening lands:
   DNS pinning, kernel-level exec restrictions, write overlay/diff capture,
   and human approval materialization.

When proposing work:

- Use Copilot CLI read-only for repo comprehension, risk review, implementation
  plans, and cited architecture analysis.
- Keep L3/L4 gates closed by default. Open them only inside an approved run
  window, then rollback immediately.
- If you need actual file edits, assign them to Codex/Cursor/another code agent
  outside `copilot_cli.run`; Copilot CLI may produce text-only plans or diffs
  but must not materialize changes.
- For any new probe, produce a report under `reports/copilot-cli/` and include
  metrics: rc, duration, stdout/stderr bytes, nft_drop_delta, secret_scan,
  audit path, artifact manifest, and rollback proof.

Treat this capability as an analysis/reasoning gear in a larger orchestrated
system, not as an autonomous deploy/write agent.
```

