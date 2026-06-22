# P3-VPS — Copilot CLI Slug Audit — REPORT

**Verdict:** `P3_SLUGS_OK`
**ts_utc:** 2026-06-21T17:29Z · **host:** srv1431451 · **repo HEAD:** `802f431`
**Task:** read-only audit of Copilot CLI model slugs available to the UmbralBIM token (input to the P3 policy PR). No tournament, no broker `copilot_cli.run`, no interactive Copilot.

## Result in one paragraph (for David)

With the rotated UmbralBIM token (`COPILOT_GITHUB_TOKEN` fp `a19dbad9a470`, GitHub `/user` 200), GitHub Copilot CLI `1.0.36` has **no `models list` subcommand**, so model availability can only be learned by probing `--model <slug>` one at a time. The decisive finding: the CLI **`--model` flag accepts only lowercase-hyphenated slugs and rejects display names** — `gpt-5.5` works but `GPT-5.5` returns *"Model … not available"*; likewise `claude-opus-4.7` works while `Claude Opus 4.7` is rejected. Because the policy's `allowed_models` currently stores **display names**, those entries would all fail if passed verbatim to `--model`. Probing every policy entry as a slug, **9 are available** to this token — `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.3-codex`, `claude-opus-4.8`, `claude-opus-4.7`, `claude-opus-4.6`, `claude-sonnet-4.6`, `claude-sonnet-4.5` — and **4 are genuinely not entitled** (`gpt-5.2-codex`, `gemini-3.1-pro`, `gemini-3-flash`, `grok-code-fast-1`). `gpt-5.5` is confirmed green (the task minimum). The concrete P3 PR action: convert `allowed_models` to canonical slugs, keep `model_aliases` mapping display→slug, drop the 4 unentitled models, and note that `force_default_model: true` still pins every lane to `gpt-5.5` until relaxed. See `04-slug-matrix.md` for the matrix + ready-to-apply YAML.

## Phases executed

- **FASE 0 — preflight + token gate:** GO. host srv1431451, worker 200, L3=false, L4 `activated:false`, nft ABSENT, sandbox image `umbral-sandbox-copilot-cli:6940cf0f274d` + network `copilot-egress` present. Token fp `a19dbad9a470` == expected, GitHub `/user` 200 login `UmbralBIM`.
- **FASE 1 — offline introspection (`--network=none`):** CLI `1.0.36`. `--help` shows commands = `help/init/login/mcp/plugin/update/version` only (no `models`). `--reasoning-effort` choices = `low|medium|high|xhigh`.
- **FASE 2 — `copilot models list` (bridge):** `error: Invalid command format` for both `models list` and `model list` → subcommand does not exist (NOT an egress failure; bridge worked, token len 93 injected). FASE 2b egress probe **not warranted** — no `models` command exists to reach.
- **FASE 3 — read-only `--model` probes:** 5 task candidates + 6 slug-format disambiguation + 6 policy-completion = 17 probes. Detection = echo `MODEL_PROBE_OK` (available) vs `"… not available"` (unavailable). Two task-script bugs fixed: (a) `-p /dev/stdin` does not read the pipe (copilot took it literally → "No actionable task") so prompt delivered via `-p "<text>"`; (b) `for M in $CANDIDATES` word-splits multi-word names so a bash array + per-container `PROBE_MODEL` env var was used.
- **FASE 4 — matrix:** `04-slug-matrix.md` (18 rows incl. controls + DEFER, with suggested YAML).
- **FASE 5 — deliverables + secret scan:** PAT-pattern hits = **0** (CLEAN).

## Cost / quota note (transparency)

Rejected slugs cost **0** premium requests (pre-flight rejection). Available slugs that ran consumed premium requests per their multiplier: `gpt-5.4-mini` 0.33x · `gpt-5.4`/`claude-sonnet-4.5`/`claude-sonnet-4.6`/`gpt-5.3-codex`/`claude-opus-4.8` 1x · `claude-opus-4.6` 3x · `gpt-5.5`/`claude-opus-4.7` 7.5x. Approx total this session ≈ 31 premium requests (incl. one FORM-A validation run on gpt-5.5). Prompts were ~4k input tokens each (tiny).

## Safety / state

- Gates **never touched**: all probes were direct `docker run` (bypassing the worker broker), so L3/L4/nft were irrelevant and remained closed. No `RICK_COPILOT_CLI_EXECUTE=true`, no `--allow-all*`/`--yolo`, no repo writes, no config/secret edits.
- **POST-state** (`05-post-state.txt`): L3=false · L4 `activated:false` · nft ABSENT · worker 200 · 0 leftover sandbox containers (the 2 running are pre-existing `rsshub`+`umbral-redis`, up 6 weeks) · repo clean (only pre-existing untracked `00_auditoria_schema_rick_cursor.md`) · shell token cleared.
- Secret guard honored: only present/len/fp[:12] surfaced; PAT never printed; evidence scan CLEAN.

## Scope boundary

This is the audit input only. No PR opened, no policy merged on the VPS — handed to Codex per the suggested YAML in `04-slug-matrix.md`.
