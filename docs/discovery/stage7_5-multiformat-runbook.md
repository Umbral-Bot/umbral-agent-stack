# Stage 7.5 — Multi-format Copy Generation (Runbook)

> Status: feature branch `rick/stage7_5-multiformat`. **DO NOT MERGE** until human review.
> Date generated: 2026-05-08.

This runbook documents the multi-format extension of the Stage 7.5 copy
pipeline introduced in commits `3bfd5b3 → 02f934a` on
`rick/stage7_5-multiformat`. It is **additive** on top of the Stage 7.5 v1
runbook ([stage7_5-copy-writer.md](stage7_5-copy-writer.md)) — the v1 flow
(single LinkedIn standalone copy → Notion `Copy LinkedIn` property) is fully
preserved when no new flag is set.

---

## 1. The three formats

| Format               | Length         | Hashtags | Source URL | Blog URL | H1   | Notion property              |
|----------------------|----------------|----------|------------|----------|------|------------------------------|
| `linkedin_standalone`| 400–3000 chars | 3–5      | required   | —        | —    | `Copy LinkedIn` (legacy)     |
| `linkedin_share`     | 400–1500 chars | 3–5      | —          | required | —    | `Copy LinkedIn Share`        |
| `blog`               | 2000–6000 chars| 0        | required   | —        | yes  | `Copy Blog`                  |

Universal rules (R7 emojis, R8 marketing-slop, R9 register, R11 CTA, R12
disciplines) are applied identically across all three formats.

The **Notion property names** for the new formats (`Copy LinkedIn Share`,
`Copy Blog`) are **best-effort** writes: if the property does not exist on
the Publicaciones data source the writer logs `skipped:property_missing:<name>`
and continues. Adding those properties to Publicaciones is a Hilo C task,
out of scope for this branch.

---

## 2. Files added or changed

| Path                                                      | Role                                                    |
|-----------------------------------------------------------|---------------------------------------------------------|
| `prompts/rick/blog-system.md`                             | Blog system prompt (long-form, Markdown, no hashtags)   |
| `prompts/rick/blog-user.md`                               | Blog user prompt template                               |
| `prompts/rick/linkedin-share-system.md`                   | LinkedIn Share system prompt (short, links to blog)     |
| `prompts/rick/linkedin-share-user.md`                     | LinkedIn Share user prompt (uses `{blog_url}`)          |
| `prompts/rick/linkedin-standalone-system.md`              | Standalone system prompt (mirrors legacy linkedin-copy) |
| `prompts/rick/linkedin-standalone-user.md`                | Standalone user prompt                                  |
| `tests/discovery/fixtures/stage7_5_proposals.json`        | 10 fixtures, every one carries `blog_url`               |
| `tests/discovery/fixtures/stage7_5_golden_copies.json`    | Adds `formats` block with per-format rule overrides     |
| `scripts/discovery/stage7_5_copy_writer.py`               | Multi-format pipeline (FORMATS, generate_format, …)     |
| `scripts/discovery/eval_stage7_5_copy.py`                 | `--format` flag, `score_copy_{standalone,share,blog}`   |
| `scripts/discovery/run_stage7_5_multiformat_real.py`      | Driver to run the (format × fixture × temp) matrix      |
| `tests/discovery/test_stage7_5_multiformat.py`            | 31 new tests (writer + evaluator multi-format)          |
| `reports/stage7_5_multiformat_real_v1.json`               | Real-run report (36 calls, openclaw/main)               |

---

## 3. CLI usage

### Writer

```bash
# Legacy: single linkedin standalone (default — unchanged)
python -m scripts.discovery.stage7_5_copy_writer

# All three formats per proposal
python -m scripts.discovery.stage7_5_copy_writer --multiformat

# Subset (overrides --multiformat)
python -m scripts.discovery.stage7_5_copy_writer --formats blog,linkedin_share
```

The new flags are additive. When neither `--multiformat` nor `--formats` is
set the writer takes the legacy path (`process_proposal`) and writes only
the `Copy LinkedIn` Notion property — backward compatible with the rest of
the runtime.

### Evaluator (synthetic + real)

```bash
# Default (linkedin_standalone, identical to v1 behavior)
python -m scripts.discovery.eval_stage7_5_copy --dry-run

# Score a real run for a specific format
python -m scripts.discovery.eval_stage7_5_copy --format blog --model openclaw/main

# Full matrix (the real-eval driver)
python -m scripts.discovery.run_stage7_5_multiformat_real \
    --formats linkedin_standalone,linkedin_share,blog \
    --fixture-ids F1-bim-only-clash-detection,F2-bim-plus-ia-paper,F3-bim-plus-automation-dynamo,F4-low-code-citizen-dev \
    --temperatures 0.3,0.7,1.0 \
    --model openclaw/main
```

The driver writes a single `reports/stage7_5_multiformat_real_v<n>.json`
with per-call rule results plus a per-(format × temp) aggregate.

---

## 4. Real-run results (commit 02f934a)

36 calls against `openclaw/main` via `http://127.0.0.1:18789`, elapsed 767s.

| Format               | t=0.3 | t=0.7 | t=1.0 |
|----------------------|-------|-------|-------|
| linkedin_standalone  | 1.000 | 1.000 | 1.000 |
| linkedin_share       | 0.981 | 1.000 | 1.000 |
| blog                 | 0.906 | 0.906 | 0.886 |

* `linkedin_standalone` and `linkedin_share` clear the 0.85 threshold on
  every (fixture × temp) combination — both formats are production-ready
  from a quality standpoint.
* `blog` misses **R1 (length)** on a minority of samples — the model
  occasionally emits articles just under the 2000-char floor. The
  `blog-system.md` prompt should be tightened in the next iteration to
  enforce a hard "≥2000 caracteres" instruction with an explicit rejection
  example.

---

## 5. Backward compat checklist

- [x] Legacy `process_proposal` + `build_copy_prompt` paths untouched.
- [x] `Copy LinkedIn` Notion property is still the only one written when
  the legacy CLI path is used.
- [x] All 21 pre-existing writer tests pass without modification.
- [x] Evaluator default (`--format` omitted) behaves identically to v1.
- [x] `score_copy` still exists with its v1 signature; new
  `score_copy_{standalone,share,blog}` are additive wrappers.
- [x] SQLite migration: `ensure_copy_columns` adds the 12 new per-format
  columns idempotently via `ALTER TABLE … ADD COLUMN IF NOT EXISTS`.
  Existing rows keep `copy_status` / `copy_text` semantics.

---

## 6. Open items (PR reviewer attention)

1. **Tune `blog-system.md` length floor** — current prompt occasionally
   produces 1900-char output; bump explicit instruction to ≥2000.
2. **Notion schema (Hilo C)** — add `Copy LinkedIn Share` (rich_text) and
   `Copy Blog` (rich_text or files+url to a Notion page) properties to
   Publicaciones before relying on the multi-format writes in production.
3. **Cost model** — the writer estimates cost via the same per-1k token
   knobs as v1; blog format produces ~3-5× tokens, so the daily budget
   should be reviewed in conjunction with the rollout plan.
4. **Eval threshold per format** — current global threshold is 0.85;
   consider per-format thresholds so blog's structural strictness doesn't
   bleed into the standalone/share gates.

---

## 7. Rollout sequence (suggested)

1. Merge this branch only after Hilo C adds the `Copy Blog` /
   `Copy LinkedIn Share` properties to Publicaciones.
2. Smoke run: `--formats linkedin_share` against staging proposals only.
3. Tighten `blog-system.md` per item §6.1, re-run the matrix, confirm
   blog ≥ 0.95.
4. Enable `--multiformat` in the cron, watch `ops_log.jsonl` for
   `pack_ready` / `FAIL_PACK` events for one week before declaring stable.
