# Core Eval Harness v0

Status: implemented as deterministic offline runner.

## Purpose

The harness gives Rick and Mission Control one small quality surface before
the stack expands memory, connectors, or publishing automation.

It does not call live services, does not call LLM judges, and does not write to
Notion, Gmail, Calendar, LinkedIn, Redis, or Azure.

## Suites

| Suite | What it proves |
|---|---|
| `editorial_gold_set` | Editorial gold-set structure, dimensions, weights, and HITL gates are valid. |
| `stage5_ranking` | Deterministic editorial ranking keeps precision@5 >= 0.8 on the synthetic dataset. |
| `agent_output_gold_set` | Minimum agent-output gold set exists, is offline by default, and covers core quality dimensions. |

## Run

```powershell
python scripts/eval_harness.py --format markdown
python scripts/eval_harness.py --format json
python scripts/eval_harness.py --write
python scripts/eval_harness.py --suite stage5_ranking --write
```

`--write` creates:

```text
reports/evals/generated/core-eval-harness-latest.json
reports/evals/generated/core-eval-harness-latest.md
```

These files are runtime evidence and are ignored by git. Mission Control reads
the latest JSON through `GET /evals`.

## Contract

- `read_only: true`
- `network: none`
- `llm_calls: 0`
- non-zero exit when any suite fails
- no live credentials required

## Next increments

1. Add fixture outputs for `research.web`, `gmail.router`, and `calendar.propose`.
2. Add an opt-in `--live` mode only after deterministic cases are stable.
3. Add LLM-as-judge only behind explicit model/env gates and with stored prompts.
4. Feed the latest report into Mission Control gates without adding a launcher.
