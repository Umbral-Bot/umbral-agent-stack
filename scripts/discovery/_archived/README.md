# Stage 6 legacy archive

> Archive proposal b0004 (2026-07-12). **Do not merge until David signs
> MP-D2** in `docs/editorial-pipeline/master-plan.md` §7.

## What the real flow uses

The executable spine visible in the repository is:

1. `stage5_rank_candidates.py` optionally writes `ranking_score`,
   `ranking_reason`, and `ranking_at` into `state.sqlite.discovered_items`.
   It has no static caller in `dispatcher/` or the current discovery cron.
2. `scripts/vps/discovery-publish-cron.sh` invokes
   `stage6_llm_combinator.py` after Stage 4. Stage 6 reads the ranked rows and
   falls back to recently promoted rows when ranking has not run, then writes
   draft rows to `state.sqlite.proposals`.
3. The same cron explicitly leaves `stage7_publish_drafts.py` manual. Stage 7
   reads draft proposals and creates draft pages in `📰 Publicaciones`.
4. `dispatcher/` and `worker/` do not statically dispatch Stage 5, Stage 6, or
   Stage 7 scripts.

Therefore `stage6_llm_combinator.py` is the only Stage 6 implementation wired
by an operational script today. The repository does not currently provide an
automatic S5→S6→S7 chain.

## Archived files

| File | Previous state | Why archived |
|---|---|---|
| `stage6_aec_combine.py` | Stub that always raised `NotImplementedError` | Superseded by the real LLM combinator; no runtime caller. |
| `stage6_generate_variants.py` | Wave 1 multi-platform skeleton | Produced placeholder variants and had tests/design docs, but no runtime caller or real generation outside LinkedIn. |

Historical audit documents keep their original paths as evidence. Active
references point here or to the canonical combinator.

## Recovery

The files remain versioned and importable from `_archived/`. To restore one as
an active Stage 6 implementation:

1. obtain David's explicit MP-D2 decision;
2. move the chosen file back under `scripts/discovery/` with `git mv`;
3. update active docs and the focused Stage 6 test path;
4. re-run the Stage 6 focused tests before opening the replacement PR.

Do not restore both files. Any future multi-platform implementation should be
introduced as a separately named stage or library so it does not recreate the
ambiguous `stage6_*` surface.
