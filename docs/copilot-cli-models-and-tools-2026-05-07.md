# Copilot CLI models and tools — 2026-05-07

## Answer

Rick/subagents can request a stronger GitHub Copilot model through
`copilot_cli.run` after this PR by adding:

```json
{
  "model": "Claude Opus 4.7"
}
```

The worker validates the string against `config/tool_policy.yaml ::
copilot_cli.allowed_models` and passes it to Copilot CLI as:

```bash
copilot --model 'Claude Opus 4.7'
```

Actual availability is still controlled by GitHub Copilot plan, organization
model policy, and the installed CLI. If GitHub rejects the model, the run must
record the exact non-secret error and stop.

## Official-source basis

GitHub docs state that Copilot CLI can change model with `/model` or the
`--model` command-line option:

- https://docs.github.com/en/copilot/concepts/agents/copilot-cli/about-copilot-cli

GitHub's supported-model reference lists `Claude Opus 4.7` as a GA Copilot
model and documents premium-request multipliers:

- https://docs.github.com/en/copilot/reference/ai-models/supported-models

GitHub docs also document tool controls:

- `--available-tools`
- `--allow-tool`
- `--deny-tool`
- `--allow-all-tools`
- `--allow-all` / `--yolo`

Reference:

- https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/allowing-tools

## Current worker capability surface

Current `copilot_cli.run` remains read-only and repo-analysis oriented:

- Available tools exposed to Copilot CLI: `view,grep,glob`
- Built-in MCP disabled: `--disable-builtin-mcps`
- Shell, write, PR, publish, Notion, deploy, and network-egress operations are
  blocked by repo policy and global hard-deny operation checks.
- Token is passed by env name only: `--env COPILOT_GITHUB_TOKEN`
- Prompt is passed through stdin, not argv.
- Artifacts redact token-shaped strings before write.
- Real execution still requires L1-L5 gates and scoped `copilot-egress`.

## Why not enable all tools now

GitHub's full-power modes (`--allow-all-tools`, `--allow-all`, `--yolo`) are
intended only for isolated environments. In this repo, enabling them before the
egress issue is fixed would combine:

- write/shell power,
- network power,
- model autonomy,
- and an allow-list that already dropped packets in F8A run-6.

That is not an engineering-safe next step.

## Recommended power ladder

1. **Now:** enable model override with read-only tools. Preferred requested
   model for maximum reasoning: `Claude Opus 4.7`.
2. **F8B:** diagnose scoped egress drops and confirm `--model` behavior in the
   sandbox with the refreshed token. The report must include structured
   metrics JSON: `docker_start_ms`, `container_ready_ms`, `copilot_exit_ms`,
   `nft_drop_delta`, and `first_stdout_byte_ms`.
3. **F8C:** widen the scoped egress allow-list based on evidence; rerun one
   canonical read-only `copilot_cli.run`.
4. **F9:** add artifact-only write/diff generation, still no commits or PR
   creation.
5. **F10:** consider restricted shell/write permissions in an isolated throwaway
   worktree with explicit deny rules for `git push`, `gh pr *`, secrets, deploy,
   and external publication.

## Plan B shelf criteria

Do not pivot away from Docker rootless + scoped nft while Plan A is still
making measurable progress. A future ADR for a bubblewrap/sandbox-runtime
Plan B is warranted only if F8B/F8C evidence shows one of these objective
conditions:

- Scoped egress drops persist after the resolver/allow-list is widened from
  observed destination evidence.
- Two additional F8A/F8B/F8C iterations fail to reach a stable green run.
- Cold start p95 is greater than 5 seconds across three measured samples.
- The team cannot map required Copilot egress to stable FQDN/IP policy.

Evidence of container escape is not a Plan B trigger. It is an incident trigger:
stop immediately, rotate secrets, and write a post-mortem.

## Payload example

```json
{
  "task": "copilot_cli.run",
  "input": {
    "mission": "research",
    "model": "Claude Opus 4.7",
    "prompt": "Read this repository and produce a short markdown risk note: top 3 risks before letting Copilot CLI write files. Do not write files. Return only the markdown note.",
    "requested_operations": ["read_repo"],
    "repo_path": "/home/rick/umbral-agent-stack",
    "dry_run": false,
    "max_wall_sec": 600,
    "metadata": {
      "batch_id": "f8c-read-only-opus",
      "agent_id": "copilot-vps-single-007",
      "brief_id": "F8C-read-only-opus"
    }
  }
}
```
