# CAND-002 — Source-Driven Editorial Flow

> **Date**: 2026-04-23
> **Type**: Source-driven editorial candidate
> **Source DB**: Notion "Referentes" (`05f04d48c44943e8b4acc572a4ec6f19`)
> **Target DB**: Notion "Publicaciones" (`e6817ec4698a4f0fbbc8fedcf4e52472`)

## Summary

First source-driven editorial flow. Unlike CAND-001 (opinion operativa without external sources), CAND-002 is built from real sources selected by David from the Referentes DB.

## Source Notion page

- DB: Referentes (`05f04d48c44943e8b4acc572a4ec6f19`)
- View: `71d3f67ec4214b898cf1f43e3c034e2f`
- 25 referentes curated by David across 5 categories

## Sources extracted and analyzed

| Source | URL | Publications Found | Access |
|--------|-----|-------------------|--------|
| The B1M (Fred Mills) | theb1m.com | 7 articles (2025-10 to 2026-04) | Public |
| Andrew Ng / The Batch | deeplearning.ai/the-batch | 10 issues (2026-02 to 2026-04) | Public |
| Marc Vidal | marcvidal.net | 7 blog posts (2026-03 to 2026-04) | Public |
| Aelion.io (Ivan Gomez) | aelion.io | Manifesto | Public landing |
| 12 LinkedIn profiles | linkedin.com | N/A | Blocked (auth required) |
| Ruben Hassid / How to AI | howtoai.substack.com | N/A | Wrong Substack URL |

## Transformation formula

- **Name**: Capacidad vs preparacion
- **Type**: pattern_synthesis
- **Thesis**: The main barrier to capturing AI value in AEC is not the lack of tools, but the lack of organizational readiness.
- **Sources combined**: Ng (AI-native teams), Vidal (productivity paradox), Aelion (ROI-first), B1M (investment follows clarity)

## QA verdict

- **Initial verdict**: pass_with_changes (Run ID: `e7ede159-9b1c-4e04-9012-8c6e827e3e22`)
- **Post-change verdict**: **pass** (Run ID: `33554772-9f2b-41a6-87de-21bab936874f`)
- **ready_for_human_review**: true
- **Blockers**: 0
- **Required changes**: 3 (all resolved)
  1. Add specific article URLs to source_set — resolved (URLs verificadas section added)
  2. Add explicit inferencia/hipotesis rows to extraction_matrix — resolved (3 subsections)
  3. Tie claim to sources more explicitly — resolved (inference rows with source attribution)
- **rick-qa Run ID**: e7ede159-9b1c-4e04-9012-8c6e827e3e22

## Notion page created

- **Page ID**: `34b5f443-fb5c-81da-abe1-e586033ceed8`
- **URL**: [CAND-002](https://www.notion.so/CAND-002-La-IA-ya-cambio-de-ritmo-En-AEC-el-cuello-de-botella-sigue-siendo-la-organizacion-34b5f443fb5c81daabe1e586033ceed8)
- **Estado**: Borrador
- **Gates**: all false
- **Publication fields**: all empty
- **Body**: 124 blocks (editorial review, sources, extraction matrix, formula, checklist)

## Relation to CAND-001

CAND-001 (PR #266) was the first editorial candidate — opinion operativa without external sources, testing the flow and format. CAND-002 is the first source-driven candidate, using David's curated referentes as input.

## OpenClaw commands used

| Agent | Run ID | Purpose |
|-------|--------|---------|
| rick-orchestrator | `0be78ce9-6621-4180-8f84-615da49cf6c4` | Generate CAND-002 payload |
| rick-qa | `e7ede159-9b1c-4e04-9012-8c6e827e3e22` | Validate CAND-002 payload |

## For David

1. Search in Notion: **CAND-002 — La IA ya cambio de ritmo**
2. Review: propuesta LinkedIn, variante X, fuentes, formula de transformacion, checklist
3. The page contains full traceability: what was extracted from each source, what was discarded, what was combined
4. Use the checklist to approve/reject formula, sources, AEC relevance, and tone

## Next steps

- David reviews CAND-002 in Notion
- If approved, proceed to content approval workflow
- If changes needed, iterate with rick-orchestrator
