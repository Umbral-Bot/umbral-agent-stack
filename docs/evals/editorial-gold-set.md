# Editorial Gold Set

A minimum viable evaluation base for the Rick editorial system.
10 cases, 12 dimensions, structural validation only.

## What this does

- Defines 12 evaluation dimensions with weighted scoring (sum = 1.0).
- Provides 10 concrete editorial scenarios covering the core risk
  surface: source handling, voice fidelity, channel adaptation, CTA,
  visual briefs, AI slop, human gates, and orchestration decisions.
- Validates structural integrity via Python loader (no LLM needed).
- CLI script for quick validation and summary.

## What this does NOT do

- **No LLM evaluation.** This is the data layer only.  A future prompt
  tournament or LLM-as-judge evaluator will consume these cases.
- **No content generation.** No posts are created or published.
- **No Notion integration.** No pages, DBs, or API calls.
- **No runtime activation.** No crons, workflows, or webhooks.

## Relation to prompt tournament

The gold set is a prerequisite for the prompt tournament (UA-06).  The
tournament will:

1. Load cases from `gold-set-minimum.yaml`.
2. Generate candidate outputs using different prompt variants.
3. Score each output against the `evaluation_dimensions` for that case.
4. Compare scores to `minimum_score` thresholds.
5. Select the best prompt variant per scenario.

This PR provides step 1 only.

## Files

| File | Purpose |
|------|---------|
| `evals/editorial/gold-set.schema.json` | JSON Schema for gold-set cases |
| `evals/editorial/dimensions.yaml` | 12 evaluation dimensions with weights |
| `evals/editorial/gold-set-minimum.yaml` | 10 minimum viable cases |
| `infra/editorial_gold_set.py` | Loader and structural validator |
| `scripts/validate_editorial_gold_set.py` | CLI: validate and summarize |
| `tests/test_editorial_gold_set.py` | Tests for structure and coverage |

## Running validation

```bash
python scripts/validate_editorial_gold_set.py
```

Output:
```
Gold set: evals/editorial/gold-set-minimum.yaml
Dimensions: evals/editorial/dimensions.yaml
  Cases: 10
  Channels: blog, linkedin, x
  Input types: cta_variant, news_reactive, raw_idea, reference_post, source_signal, technical_explainer
  Audience stages: awareness, consideration, trust
  Dimensions used: 12
  All have human gate: True

Validation passed.
```

## Running tests

```bash
python -m pytest tests/test_editorial_gold_set.py -q
```

## Adding new cases

1. Add a new entry to `evals/editorial/gold-set-minimum.yaml` under
   `cases:`.
2. Use the next sequential ID (e.g. `ED-GOLD-011`).
3. Reference only dimensions that exist in `dimensions.yaml`.
4. Set `human_gate_required: true` unless you have a specific reason
   not to.
5. Run `python scripts/validate_editorial_gold_set.py` to verify.
6. Run `python -m pytest tests/test_editorial_gold_set.py -q` to check.

## Evaluation dimensions

| ID | Name | Weight |
|----|------|--------|
| `strategic_fit` | Ajuste estratégico | 0.12 |
| `audience_relevance` | Relevancia para audiencia AECO | 0.12 |
| `technical_accuracy` | Precisión técnica | 0.10 |
| `source_handling` | Manejo de fuentes | 0.10 |
| `primary_source_discipline` | Disciplina de fuente primaria | 0.08 |
| `voice_fit` | Fidelidad a la voz editorial | 0.10 |
| `channel_fit` | Adaptación al canal | 0.08 |
| `cta_quality` | Calidad del CTA | 0.08 |
| `visual_brief_quality` | Calidad del brief visual | 0.06 |
| `anti_ai_slop` | Anti AI slop | 0.08 |
| `risk_control` | Control de riesgos | 0.04 |
| `human_gate_compliance` | Cumplimiento de gates humanos | 0.04 |

Total: 1.00

## Key decisions

- **10 cases, not 50.** This is a minimum viable set.  More cases can
  be added incrementally as the system matures.
- **No conversion stage yet.** The gold set covers awareness,
  consideration, and trust.  Conversion cases will come when the CTA
  funnel is more mature.
- **All cases require human gate.** In initial phases, no content
  publishes without human approval.
- **Dimensions are weighted, not equal.** Strategic fit and audience
  relevance are weighted highest (0.12 each) because they're the
  hardest to recover from if wrong.

## Research references

These Perplexity studies informed the case design (by ID, not by
file path):

- UA-01: dolor/audiencia AECO BIM IA
- UA-02: mapa de autoridad AECO/BIM/IA
- UA-03: benchmark editorial multicanal B2B
- UA-06: marco conceptual torneo de prompts
- UA-12: CTA/funnel
- UA-13: automatización visual segura (API-first)
- UA-14: orquestación editorial (Agent Stack + n8n + Make)
