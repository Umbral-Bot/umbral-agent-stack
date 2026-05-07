# F10 H3 — Model refusal isolation report (rick-orchestrator subagent)

**Task**: `.agents/tasks/2026-05-07-019-copilot-vps-h3-model-refusal-isolation.md`
**Run TS**: 2026-05-07T13:56-14:04Z (UTC)
**Method**: Adapted recipe α — `sessions_spawn` with `model` param override, no openclaw.json edits, no gateway restart.
**OpenClaw version**: 2026.5.3-1 (gateway pid 54835, uptime since 2026-05-07T05:57:16Z)
**Hypothesis tested**: H3 — refusal trigger is one of (3a) model gpt-5.4 / (3b) Azure content filter / (3c) workspace bootstrap.

## Method (adaptation deviation from spec)

Original spec for Vector B required temporal edit of `~/.openclaw/openclaw.json` then revert. Pre-flight (commit `bbd6549`) demonstrated this is impossible without restart due to OpenClaw 2026.5.3-1 caching config as singleton pinned snapshot per process (`loadPinnedRuntimeConfig` in `dist/runtime-snapshot-DLdUvYCx.js`). David authorized adaptation **(α)**: use `sessions_spawn` tool's `model` param (verified in `dist/openclaw-tools-D7Zj4hDN.js`: `readStringParam(params, "model") → resolveModelOverride`).

Each vector dispatched via `openclaw agent --agent main --session-id 019-<vector>-<TS> --message "<directive>"` instructing main to invoke `sessions_spawn` exactly once with literal task body delimited by `<<<TASK_BODY_BEGIN>>>` markers.

## Inputs

- **Canonical baseline task body**: 977 chars from spawn 1 of parent session `smoke-o151-retest-1778133479.jsonl` (ts 2026-05-07T05:58:35.047Z). Opens with "Sos rick-orchestrator. Ejecutá la vía canónica delegando a rick-ops…". sha256 `206c896c…b15a72a5ea43f9eba11197e38e84`.
- **Trivial task body** (Vector 2 only): `Respondé únicamente con la palabra: pong. Nada más.` (51 chars).
- **CWD**: `/home/rick/.openclaw/workspace` (matches baseline).
- **Subagent timeout**: 180s.

## Trajectory paths

| # | Vector | Subagent trajectory |
|---|---|---|
| 1 | Baseline | `/home/rick/.openclaw/agents/rick-orchestrator/sessions/d20c3a76-981b-4aa0-9601-59e657de9614.trajectory.jsonl` |
| 2 | A trivial body | `/home/rick/.openclaw/agents/rick-orchestrator/sessions/5d5f60e3-fc06-42d1-b571-5f8521d5a473.trajectory.jsonl` |
| 3 | B model swap | `/home/rick/.openclaw/agents/rick-orchestrator/sessions/7d4da225-5dd4-495f-bdc8-c0a488dd8421.trajectory.jsonl` |
| 4 | C bootstrap minimal | `/home/rick/.openclaw/agents/rick-orchestrator/sessions/4461c4c7-8921-4de2-b122-22d897877585.trajectory.jsonl` |

## Verdict table

| # | Vector | Task body | Model (modelId / provider) | Bootstrap | systemPrompt size | First 200 chars of response | usage (in/out/cacheRead/total) | Wall | Aborted | Verbatim ✓ |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Baseline | smoke-healthcheck (977 c) | gpt-5.4 / azure-openai-responses | full (7 files, ~70k) | 69908 B | "I'm sorry, but I cannot assist with that request." | 0/0/0/0 (`usage: null`) | 2s | false | ✓ |
| 2 | A | "Respondé únicamente con la palabra: pong…" (51 c) | gpt-5.4 / azure-openai-responses | full | ~70k B | "I'm sorry, but I cannot assist with that request." | 0/0/0/0 | 2s | false | n/a (trivial) |
| 3 | B | smoke-healthcheck (977 c) | **gemini-3.1-pro-preview / google-vertex** | full | ~70k B | _empty assistantTexts; called tool `exec` with `uuidgen` (started executing task)_ | 36188/3114/154358/**193660** | 90s | false | ✓ |
| 4 | C | smoke-healthcheck (977 c) | gpt-5.4 / azure-openai-responses | **minimal: 95-byte AGENTS.md only** (SOUL/IDENTITY/TOOLS/SKILL/HEARTBEAT/USER quarantined) | 30390 B | "I'm sorry, but I cannot assist with that request." | 0/0/0/0 | 6s | false | ✓ |

### Verbatim transmission proof (anti-contamination)

For Vectors 1 / 3 / 4 the canonical task body was extracted from the subagent `prompt.submitted.systemPrompt` and `diff`'ed against `/tmp/019/baseline-task.txt` (sha256 `206c896c…`). Result: **identical** for all three. Vector 2 used a trivial body which appears verbatim under `## Your Role` section as "- You were created to handle: Respondé únicamente con la palabra: pong. Nada más."

## Verdict: **3a + 3b** (model + Azure provider/content-filter layer)

**Falsified**:

- **3c (bootstrap workspace files)** — FALSIFIED by Vector 4. Same model+provider+task body, bootstrap reduced from ~57KB across 7 files to 95 bytes in 1 file (systemPrompt 69908 → 30390 bytes), refusal still emitted with usage 0/0/0/0 in 6s.
- **task content (3-task)** — FALSIFIED by Vector 2. Same model+provider+bootstrap, body changed from 977-char "delegate to rick-ops" recipe to trivial "respond pong", refusal still emitted with usage 0/0/0/0 in 2s.

**Confirmed**:

- **3a/3b (model + provider stack)** — CONFIRMED by Vector 3. Same task body, same workspace bootstrap (full 7 files), same cwd, same dispatch path; only `model` param swapped from `gpt-5.4` (default azure-openai-responses) to `gemini-3.1-pro-preview` (google-vertex). Result: subagent processed normally, billed 193660 tokens, called `exec` tool to start executing the task body (generating UUID for `orchestrator_task_id`).

### 3a vs 3b — partial discrimination

The fingerprint **`usage: null` + 0 input / 0 output tokens billed + 2-6s wall time + canned response identical to common Azure content-filter pre-block message** strongly suggests **3b: Azure OpenAI Responses content-filter pre-block** rather than 3a (model intrinsic refusal).

A model intrinsic refusal (3a) would normally:
- Bill input tokens (the model has to read the prompt to decide refusing).
- Emit some output tokens via streaming.
- Have variable wording.

A content-filter pre-block (3b):
- Returns deterministic canned message.
- Bills 0 tokens (request never reached the model).
- Returns in a few seconds (filter latency only).
- All four signs match Vectors 1, 2, 4.

**Caveat**: Without testing the same gpt-5.4 model on a non-Azure provider (e.g., `openai-codex/gpt-5.4`, currently configured but not validated under same dispatch path), 3a alone cannot be fully ruled out. Recommend follow-up vector D using `openai-codex/gpt-5.4` with same baseline body to fully discriminate.

## Recommended fix (minimal)

**Switch `agents.list[id=="rick-orchestrator"].model.primary` from `azure-openai-responses/gpt-5.4` to `google-vertex/gemini-3.1-pro-preview`** (or `google/gemini-3-pro-preview`).

Alternatively, if Azure must be retained:

1. Verify content filter severity thresholds on the `gpt-5.4` deployment in Azure portal.
2. Inspect prompt for substrings that may trigger filter (e.g., "rick-ops", "delegating", "trace", paths with names) — although Vector 2 with trivial body also failed, suggesting the filter may be triggered by an injected prefix in the systemPrompt itself (Subagent Context wrapper, Tooling preamble, or workspace bootstrap header) rather than user-supplied content.
3. Open follow-up: test `gpt-5.4-pro` (same Azure deployment family) and `openai-codex/gpt-5.4` (different provider, same model family) to discriminate between deployment-level filter (3b) and model-intrinsic alignment (3a).

The change does NOT require gateway restart if applied via `sessions_spawn` model param at call sites. For permanent change in `openclaw.json`, gateway restart IS required (singleton config cache).

## Token cost (this experiment)

| Component | Input | Output | CacheRead | Total |
|---|---|---|---|---|
| v1 driver (main, gpt-5.4) | 43266 | 1748 | 20480 | **65494** |
| v1 subagent (gpt-5.4) | 0 | 0 | 0 | **0** |
| v2 driver | 3206 | 1479 | 82048 | **86733** |
| v2 subagent | 0 | 0 | 0 | **0** |
| v3 driver | 1871 | 1069 | 62720 | **65660** |
| v3 subagent (gemini-3.1-pro-preview) | 36188 | 3114 | 154358 | **193660** |
| v4 driver | 23720 | 1920 | 63744 | **89384** |
| v4 subagent | 0 | 0 | 0 | **0** |
| **GRAND TOTAL** | | | | **500,931 tokens** |

Note: the 4 refusal subagent calls billed 0 tokens, consistent with **3b content-filter pre-block** hypothesis.

## State preservation (post-experiment)

- `~/.openclaw/openclaw.json`: untouched. `diff` against backup `openclaw.json.bak-pre-019-20260507-093659` is empty.
- `~/.openclaw/workspaces/rick-orchestrator/`: restored from backup after Vector 4. `diff -r --exclude='.sync-backups'` against `workspaces/rick-orchestrator.bak-pre-019-20260507-093659/` is empty.
- Bump bootstrap (24k/120k) per task 017: still active (not reverted).
- Backups conserved (NOT removed) at:
  - `~/.openclaw/openclaw.json.bak-pre-019-20260507-093659`
  - `~/.openclaw/workspaces/rick-orchestrator.bak-pre-019-20260507-093659/`

## Hard rules respected

- 0 escrituras permanentes a `~/.openclaw/openclaw.json` ✓ (diff vacío)
- 0 restarts gateway/worker/dispatcher ✓
- 0 ejecutar `copilot_cli.run` ✓
- 0 dump de `/proc/PID/environ` ✓
- No tokens, PATs, secrets impresos en este report ✓
