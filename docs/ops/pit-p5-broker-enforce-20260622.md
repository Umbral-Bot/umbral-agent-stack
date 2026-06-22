# PIT P5 — Broker-only enforcement (skill + pit_spec v2 + validator)

**Date:** 2026-06-22
**Surface:** Copilot Windows (repo). No VPS writes; no runtime gates touched.
**Builds on:** P3 slugs ([`config/tool_policy.yaml`](../../config/tool_policy.yaml)) + P4 broker
contract ([`pit-p4-broker-contract-20260621.md`](pit-p4-broker-contract-20260621.md)).

P5 makes the broker the **only** path for PIT lanes that read/analyze the repo or
write code: every such lane is dispatched through the Worker task
`copilot_cli.run`. Lanes never call an LLM provider directly. This turn ships the
contract (skill rule + spec template + validator + tests + doc); it does **not**
run a tournament or open any gate.

## What this blocks / allows

**Blocks**

- A PIT lane calling an LLM provider directly for coding / repo-analysis ⇒ `lane_blocked`.
- Silent fallback when `copilot_cli.run` fails (the lane is `blocked`, not retried out-of-band).
- A spec with bad `pit_id`/`lane_id`, unknown `model`, bad `reasoning_effort`,
  `secrets_scope.deny` missing `WORKER_TOKEN`, or `broker_contract` that is not
  `required_task: copilot_cli.run` + `forbid_direct_llm_repo_analysis: true`.

**Allows**

- Lanes dispatched as `copilot_cli.run` with full PIT metadata.
- Per-lane `model` override as a slug or a display name resolvable via
  `model_aliases`; `reasoning_effort` in `low | medium | high | xhigh | max`
  (`max` is the display alias normalized to `xhigh` by the broker at run time).

## Preflight checklist (skill, before broker-lane spawn)

All green or STOP:

- `P2_PROBE_REAL_OK`
- `P3_SLUGS_OK` (slugs + aliases + `force_default_model: false`)
- `#481` / `#482` / `#483` merged in `main`
- `P4_RUNTIME_LOAD_OK` (worker restarted with the P4 contract in runtime)
- `pit_spec_validate` PASS: `python scripts/pit/pit_spec_validate.py <spec.yaml>`

## Canonical lane payload

The spec lives in [`examples/pit/pit_spec.v2.yaml`](../../examples/pit/pit_spec.v2.yaml);
each lane is dispatched as `copilot_cli.run`:

```json
{
  "task": "copilot_cli.run",
  "input": {
    "mission": "research",
    "model": "Claude Opus 4.7",
    "reasoning_effort": "xhigh",
    "repo_path": "/work",
    "dry_run": true,
    "metadata": {
      "batch_id": "pit-batch-01",
      "agent_id": "copilot-a",
      "pit_id": "pit-broker-smoke-01",
      "lane_id": "lane-contract-a",
      "iteration": 1
    }
  }
}
```

`batch_id`, `agent_id`, `pit_id`, `lane_id`, `iteration` are required for
audit↔response correlation (P4).

## pit_spec v2 + validator

- **Template:** [`examples/pit/pit_spec.v2.yaml`](../../examples/pit/pit_spec.v2.yaml)
- **Validator:** `scripts/pit/pit_spec_validate.py` auto-detects v2 (`schema_version: 2`
  or a `broker_contract` block) and checks, with clear per-field errors:
  - `pit_id` / `lane_id` ~ `^[A-Za-z0-9._-]{1,64}$` (same grammar as the runtime broker)
  - each lane `model` ∈ `allowed_models` **or** resolvable via `model_aliases`
    (read from `config/tool_policy.yaml`)
  - `reasoning_effort` ∈ `{low, medium, high, xhigh, max}`
  - `secrets_scope.deny` contains `WORKER_TOKEN` (logical names only, never values)
  - `broker_contract.required_task == copilot_cli.run`
  - `broker_contract.forbid_direct_llm_repo_analysis == true`
- v1 **product** specs are unaffected — the v1 `PitSpec` path and its tests are intact.

Run:

```bash
python scripts/pit/pit_spec_validate.py examples/pit/pit_spec.v2.yaml
python -m pytest tests/test_pit_spec_validate.py -q
python -m pytest tests/test_copilot_cli.py -q -k "metadata or reasoning"
```

## Relation to P4 / P3

- **P3:** model slugs + display aliases in `config/tool_policy.yaml`
  (`force_default_model: false`).
- **P4:** `copilot_cli.run` accepts the PIT metadata + `reasoning_effort` and
  correlates every audit event and response back to `batch_id`/`lane_id`/`pit_id`/`iteration`.
- **P5 (this):** the skill and the v2 spec **require** that path for code/repo-analysis
  lanes and forbid any direct-LLM shortcut.

## Verdict

`P5_BROKER_ENFORCE_OK`
