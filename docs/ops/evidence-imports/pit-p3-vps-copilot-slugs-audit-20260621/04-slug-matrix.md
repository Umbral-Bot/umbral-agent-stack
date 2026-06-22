# P3-VPS — Copilot CLI Model Slug Matrix (UmbralBIM token)

- **ts_utc:** 2026-06-21T17:28Z
- **host:** srv1431451 · repo HEAD: `802f431`
- **token:** `COPILOT_GITHUB_TOKEN` fp=`a19dbad9a470`, login=`UmbralBIM`, GitHub `/user`=200
- **CLI:** GitHub Copilot CLI `1.0.36` (sandbox image `umbral-sandbox-copilot-cli:6940cf0f274d`)
- **method:** direct `docker run` on `copilot-egress` bridge (nft ABSENT → egress open), read-only probe
  `copilot -p "Reply with exactly: MODEL_PROBE_OK" --model <slug> --available-tools=view --disable-builtin-mcps --no-color --no-ask-user`
- **gates untouched throughout:** L3=false · L4 `activated:false` · nft ABSENT · worker MainPID unchanged · no broker POST

## Key structural findings

1. **No `models`/`model list` subcommand exists in CLI 1.0.36.** `copilot models list` → `error: Invalid command format`. Enumeration of available models is impossible via CLI; the only signal is per-slug `--model` probing.
2. **`--model` requires the lowercase-hyphenated SLUG, not the display name.** `gpt-5.5` works; `GPT-5.5` → `Error: Model "GPT-5.5" from --model flag is not available`. Same for `claude-opus-4.7` (works) vs `Claude Opus 4.7` (rejected). **The policy `allowed_models` list currently stores DISPLAY names — those would all fail if passed verbatim to `--model`.**
3. **Rejected slugs cost 0 premium requests** (pre-flight rejection, no model call). Only available slugs that actually run consume quota.
4. `--reasoning-effort` now accepts `low|medium|high|xhigh` (policy comment at `tool_policy.yaml:46-48` claiming "only up to high" is **STALE**).

## Matrix

| slug | source | available | premium_mult | evidence | recommend_for_policy |
|---|---|---|---|---|---|
| `gpt-5.5` | policy default + task candidate | **YES** | 7.5x | 03-probe-gpt-5.5.txt | YES |
| `gpt-5.4` | policy (GPT-5.4) | **YES** | 1x | 03b-probe-gpt-5.4.txt | YES |
| `gpt-5.4-mini` | policy (GPT-5.4 mini) | **YES** | 0.33x | 03b-probe-gpt-5.4-mini.txt | YES |
| `gpt-5.3-codex` | policy (GPT-5.3-Codex) | **YES** | 1x | 03c-probe-gpt-5.3-codex.txt | YES |
| `claude-opus-4.8` | task candidate | **YES** | 1x | 03c-probe-claude-opus-4.8.txt | YES |
| `claude-opus-4.7` | policy (Claude Opus 4.7) | **YES** | 7.5x | 03b-probe-claude-opus-4.7.txt | YES |
| `claude-opus-4.6` | policy (Claude Opus 4.6) | **YES** | 3x | 03c-probe-claude-opus-4.6.txt | YES |
| `claude-sonnet-4.6` | policy (Claude Sonnet 4.6) | **YES** | 1x | 03c-probe-claude-sonnet-4.6.txt | YES |
| `claude-sonnet-4.5` | policy (Claude Sonnet 4.5) | **YES** | 1x | 03b-probe-claude-sonnet-4.5.txt | YES |
| `gpt-5.2-codex` | policy (GPT-5.2-Codex) | NO | — | 03c-probe-gpt-5.2-codex.txt | NO (remove) |
| `gemini-3.1-pro` | policy (Gemini 3.1 Pro) | NO | — | 03c-probe-gemini-3.1-pro.txt | NO (remove) |
| `gemini-3-flash` | policy (Gemini 3 Flash) | NO | — | 03b-probe-gemini-3-flash.txt | NO (remove) |
| `grok-code-fast-1` | policy (Grok Code Fast 1) | NO | — | 03b-probe-grok-code-fast-1.txt | NO (remove) |
| `GPT-5.5` (display) | task candidate | NO | — | 03-probe-GPT-5.5.txt | NO — use slug `gpt-5.5` |
| `Claude Opus 4.7` (display) | task candidate | NO | — | 03-probe-Claude_Opus_4.7.txt | NO — use slug `claude-opus-4.7` |
| `Claude Opus 4.8` (display) | task candidate | NO | — | 03-probe-Claude_Opus_4.8.txt | NO — use slug `claude-opus-4.8` |
| `fable-5-max` | task candidate (control) | NO | — | 03-probe-fable-5-max.txt | NO — no such model |
| `claude-opus-4.6 (fast mode) (preview)` | policy | DEFER | — | not probed (slug unknown) | DEFER — confirm slug before listing |

> `available=NO` for the four display-name rows is a **slug-format** failure, not an entitlement failure (the corresponding lowercase slugs ARE available). `available=NO` for `gpt-5.2-codex`/`gemini-3.1-pro`/`gemini-3-flash`/`grok-code-fast-1` is a genuine **entitlement** failure (the UmbralBIM token's Copilot plan lacks them).

## Suggested YAML for the P3 PR (Codex) — `config/tool_policy.yaml`

```yaml
  default_model: gpt-5.5
  force_default_model: true          # NOTE: while true, lanes can ONLY use default_model;
                                      # allowed_models below is moot per-lane until this is relaxed
  default_reasoning_effort: high      # CLI 1.0.36 also supports `xhigh` (comment "up to high" is stale)

  model_aliases:                      # display name -> CLI slug (CLI --model REJECTS display names)
    GPT-5.5: gpt-5.5
    GPT 5.5: gpt-5.5
    GPT-5.4: gpt-5.4
    GPT-5.4 mini: gpt-5.4-mini
    GPT-5.3-Codex: gpt-5.3-codex
    Claude Opus 4.8: claude-opus-4.8
    Claude Opus 4.7: claude-opus-4.7
    Claude Opus 4.6: claude-opus-4.6
    Claude Sonnet 4.6: claude-sonnet-4.6
    Claude Sonnet 4.5: claude-sonnet-4.5

  allowed_models:                     # store CANONICAL SLUGS (confirmed available 2026-06-21)
    - gpt-5.5            # 7.5x premium
    - gpt-5.4            # 1x
    - gpt-5.4-mini       # 0.33x  (cheapest)
    - gpt-5.3-codex      # 1x
    - claude-opus-4.8    # 1x
    - claude-opus-4.7    # 7.5x premium
    - claude-opus-4.6    # 3x
    - claude-sonnet-4.6  # 1x
    - claude-sonnet-4.5  # 1x
    # REMOVED — not available to UmbralBIM token (probed "not available"):
    #   gpt-5.2-codex, gemini-3.1-pro, gemini-3-flash, grok-code-fast-1
    # DEFER — slug unconfirmed:
    #   "Claude Opus 4.6 (fast mode) (preview)"
```

## Caveats for the PR author

- **`force_default_model: true` blocks every non-default model per lane today** (verified prior: any model ≠ `gpt-5.5` → `model_not_allowed`). Expanding `allowed_models` alone changes nothing for lanes until `force_default_model` is relaxed or a per-lane model override is added. Decide that policy lever in the same PR.
- The policy comment block above `allowed_models` says GitHub still enforces actual availability — confirmed true here (4 listed models are not entitled).
- This audit used the live UmbralBIM token; availability is token/plan-scoped and can change if the token or plan changes.
