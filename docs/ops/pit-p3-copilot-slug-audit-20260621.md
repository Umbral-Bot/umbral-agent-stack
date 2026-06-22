# PIT P3 - Copilot CLI slug policy audit

Date: 2026-06-21
Source: Copilot-VPS read-only evidence at `~/.coord-ag-evidence/pit-p3-vps-copilot-slugs-audit-20260621/`
Imported evidence: `docs/ops/evidence-imports/pit-p3-vps-copilot-slugs-audit-20260621/`
Verdict: `P3_SLUGS_OK`

## Summary

GitHub Copilot CLI `1.0.36` does not expose a `models list` command. Model availability was verified by read-only per-model `--model <value>` probes on the VPS. The decisive result is that `--model` accepts lowercase-hyphenated slugs and rejects display names. For example, `gpt-5.5` and `claude-opus-4.7` work, while `GPT-5.5` and `Claude Opus 4.7` are rejected.

Policy must therefore keep `allowed_models` as canonical slugs and resolve human display names through `model_aliases` before building the Copilot CLI argv. `force_default_model` is now `false` so PIT lanes can request per-lane models; `default_model: gpt-5.5` remains the fallback when no model is requested.

PR #481 (`fix(copilot): require GitHub Meta for egress activation`) was checked separately: state `OPEN`, mergeable `MERGEABLE`. It was not merged as part of P3.

## Model Matrix

| Model slug or display value | Result | Policy action |
|---|---:|---|
| `gpt-5.5` | YES | allow |
| `gpt-5.4` | YES | allow |
| `gpt-5.4-mini` | YES | allow |
| `gpt-5.3-codex` | YES | allow |
| `claude-opus-4.8` | YES | allow |
| `claude-opus-4.7` | YES | allow |
| `claude-opus-4.6` | YES | allow |
| `claude-sonnet-4.6` | YES | allow |
| `claude-sonnet-4.5` | YES | allow |
| `gpt-5.2-codex` | NO | remove |
| `gemini-3.1-pro` | NO | remove |
| `gemini-3-flash` | NO | remove |
| `grok-code-fast-1` | NO | remove |
| `GPT-5.5` | NO | alias to `gpt-5.5` |
| `Claude Opus 4.7` | NO | alias to `claude-opus-4.7` |
| `Claude Opus 4.8` | NO | alias to `claude-opus-4.8` |
| `fable-5-max` | NO | reject |
| `Claude Opus 4.6 (fast mode) (preview)` | DEFER | keep out until slug is confirmed |

## Runtime Rule

The worker must resolve display names to slugs via `copilot_cli.model_aliases` before passing `--model` to the CLI. `allowed_models` should contain only confirmed slugs. Display names are user-facing aliases, not execution values.

## Evidence Notes

- `VERDICT.txt`: canonical verdict, CLI version, available/unavailable slug sets.
- `04-slug-matrix.md`: full slug matrix and suggested YAML.
- `03-model-probes.tsv`, `03b-slug-format-probes.tsv`, `03c-policy-completion-probes.tsv`: probe outcomes.
- `REPORT.md`: audit narrative and safety state.

No token or secret files were imported. In particular, `00-github-user.json` and any secret/env material remain excluded.
