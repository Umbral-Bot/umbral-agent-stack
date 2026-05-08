# Stage 7.5 — voice-v3 eval summary (Hilo D v3)

**Branch**: `rick/stage7_5-voice-v3`
**Base**: `main` @ `f808edb`
**Cherry-picked**: `6112116` (prompt v2 + R13/R14 wiring) + `d059c76` (R13–R17 eval + scoring v2 + F7–F10). Excluded: `87fdaa6` (source-verify, fuera de scope) y `9a06ad9` (reports/voice doc v2).
**Date**: 2026-05-08.

## What v3 changed

Added section "Ejemplos de muletillas concretas a evitar" to `prompts/rick/linkedin-copy-system.md` listing 19 4-grams that appeared in >2 copies during the 3 v2 evaluation runs against `openclaw/main`. Three categories:

- **Opinion** (8 copies): `mi lectura es simple`, `el problema no es`, etc.
- **Diagnostic AECO** (5 copies): `el cuello de botella`, `el dolor real para`.
- **Transition** (5 copies): `y pasa a ser`, `en aeco latam eso`.

Explicit instruction: do NOT use, do NOT paraphrase with synonyms, rewrite the paragraph from another angle.

v2 archived to `prompts/rick/archive/linkedin-copy-system-v2.md`. v1 archive preserved.

## Live eval results (3 runs vs `openclaw/main` @ `127.0.0.1:18789`)

| Run | Score | R13 (4-gram batch) | `hard_all_100` |
|---|---|---|---|
| t=0.6 | 0.9550 | 40% | **False** |
| t=0.8 | 0.9400 | 20% | **False** |
| t=0.95 | 0.9400 | 20% | **False** |

Reports: `reports/stage7_5_eval_v3voice3_t{06,08,095}.json`.

All other rules at 100% (R1–R12, R14–R17). The whole batch is bottlenecked by R13 (cross-fixture 4-gram repetition).

## DoD verdict — FAILED honestly

Spec asked for `hard_all_100=True` in ≥2/3 runs. Got 0/3. v3 score did improve slightly vs v2 at t=0.6 (0.9285 → 0.9550) and lifted R13 from 20% → 40% at t=0.6, but the gain is fragile and disappears at higher temperature.

## Why prompt-only hit a ceiling

Cross-copy 4-gram analysis on the new v3 batches shows two failure modes:

1. **Listed bans partially ignored**: `en aeco latam eso` still appears in 6 copies, `bim deja de ser` in 4 copies — both are in the v3 ban list with explicit "do not use" instruction.
2. **New muletillas emerge**: the model just invents fresh repeated formulas not on the v3 list:
   - `el dato que me [importa]` — 5 copies
   - `yo lo veo así` — 4 copies
   - `interesante del paper no es` — 3 copies
   - `que declara bim es` — 3 copies
   - `si el BEP no` — 3 copies
   - `más de la mitad del` — 3 copies

Adding more bans to the prompt is whack-a-mole: the model regenerates new structural tics around whichever ones we list. Inside a single forward pass the model has no global view of "this 4-gram already appeared in copy 4", so the constraint is impossible to enforce purely in-prompt for batch-level repetition.

## Proposal for v4 — deterministic post-filter / regenerate loop

Move R13 enforcement from prompt-time persuasion to generation-time gating in `scripts/discovery/stage7_5_copy_writer.py`:

1. **Generate batch normally** with current v3 prompt.
2. **Compute cross-batch 4-gram frequency** in Python after generation, using the same algorithm R13 uses in the evaluator.
3. **Mark offending copies**: any copy that contributes a 4-gram appearing in >2 copies of the batch.
4. **Regenerate offenders** with a targeted "rewrite this paragraph — your previous attempt repeated the phrase `<X>` already used in another copy of this batch" follow-up call, capped at e.g. 2 retries per copy.
5. **Hard-fail the batch** only if the loop can't converge after the cap; emit an `ops_log` event for observability.

This converts a soft persuasion problem into a deterministic constraint solver problem and matches how R13 is *measured* with how it is *enforced*. v3 prompt becomes a soft prior (cheap, helps reduce retry count); the post-filter becomes the hard guarantee.

Optional v4.1 idea (if v4 still leaks): switch R13 measurement to *normalized* lemmas (so "el problema central no es" and "el problema no es" collide), but only after v4 deterministic loop is in place — otherwise we're tightening a constraint we can't even meet at the looser definition.

## Status

- Branch pushed, **draft PR opened over `main`**, **NOT** for merge.
- Recommend David: review the v3 ban-list rationale + this honest failure report, then green-light implementation of v4 post-filter loop on a follow-up branch.
