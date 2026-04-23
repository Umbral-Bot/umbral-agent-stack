# CAND-003 — Source Intake

> **Date**: 2026-04-23
> **Purpose**: Document source discovery for CAND-003 editorial candidate.
> **Thesis target**: "Criterio antes que automatización" — before automating with AI in AEC, teams need explicit operational criteria.
> **Source DB**: Notion "Referentes" (`05f04d48c44943e8b4acc572a4ec6f19`)
> **Dedup reference**: CAND-002 used The B1M, The Batch (#342, #346, #348, #349), Marc Vidal (3 articles), Aelion.io

## Source selection criteria for CAND-003

Signals prioritized for this thesis:
- Algorithmic governance and audit criteria
- Agent management, permissions, and oversight
- What happens when organizations automate without explicit criteria
- Operational criteria for AEC: review, coordination, escalation, quality gates

## Sources analyzed

| Source | URL | Access | New for CAND-003? | Relevance |
|--------|-----|--------|-------------------|-----------|
| The Batch #340 | deeplearning.ai/the-batch/issue-340 | Public | Yes (new issue) | Standardized AI audits — AVERI framework |
| The Batch #343 | deeplearning.ai/the-batch/issue-343 | Public | Yes (new issue) | Frontier agent management — governance |
| Marc Vidal — "El algoritmo como jefe supremo" | marcvidal.net | Public | Reused article, new extraction | Algorithmic management without human oversight |
| OECD (2025) — Algorithmic management report | oecd.org | Primary source (cited by Vidal) | Primary source identified in CAND-002 | 79% of European companies use algorithmic tools |
| McKinsey Global Institute | mckinsey.com | Primary source (cited by Vidal) | Primary source identified in CAND-002 | 30% of US labor hours could be automated by 2030 |
| AVERI — AI Verification and Research Institute | averi (Brundage) | Primary source (cited by Batch #340) | New primary source | 8 audit principles, 4 assurance levels |
| Aelion.io | aelion.io | Public landing | Reused, same extraction | ROI-first mindset in AEC |

## Sources attempted but not usable

| Source | URL | Issue |
|--------|-----|-------|
| Bernard Marr | bernardmarr.com/blog | 404 — blog page not accessible |
| Dion Hinchcliffe | dionhinchcliffe.com | Not attempted (lower priority) |
| Ruben Hassid / How to AI | howtoai.substack.com | Wrong Substack URL (identified in CAND-002) |
| LinkedIn profiles (12) | linkedin.com | Blocked (auth required) |

## Dedup vs CAND-002

| Source | CAND-002 extraction | CAND-003 extraction |
|--------|---------------------|---------------------|
| The Batch #349 | AI-native teams operate differently | Not used in CAND-003 |
| The Batch #346 | Organizational resistance to AI | Not used in CAND-003 |
| The Batch #340 | Not used in CAND-002 | AI audit standards, governance criteria |
| The Batch #343 | Not used in CAND-002 | Agent management, permissions, guardrails |
| Marc Vidal "Algoritmo" | Algorithmic management displacing oversight (evidence for productivity paradox) | Deeper extraction: who monitors the monitor? what criteria govern algorithmic decisions? |
| OECD | 79% statistic cited as background | 79% statistic used as primary evidence: companies deploy algorithmic tools without audit criteria |
| McKinsey | 30% automation potential cited as background | 30% automation potential without criteria = amplified ambiguity |
| Aelion.io | ROI-first mindset (general) | ROI-first requires explicit criteria to evaluate "value from day one" |
| The B1M | Data centres + investment follows clarity | Not primary for CAND-003 (weak fit for criteria thesis) |

## Source classification (per attribution policy, applied from start)

```yaml
source_classification:
  - source_name: "DeepLearning.AI / The Batch"
    source_url: "https://www.deeplearning.ai/the-batch"
    type: analysis_source
    public_citable: true
    internal_trace_only: false
    reason: "Newsletter producing original editorial analysis. Issues #340 and #343 contain original reporting on AI audit standards and agent management."
    public_citation: "DeepLearning.AI or The Batch (as organization)"

  - source_name: "OECD — Algorithmic Management Report (2025)"
    source_url: "https://www.oecd.org"
    type: primary_source
    public_citable: true
    internal_trace_only: false
    reason: "Original report with verifiable data: 79% of European companies use algorithmic management tools."
    public_citation: "OECD (as organization)"

  - source_name: "AVERI — AI Verification and Research Institute (Brundage)"
    source_url: ""
    type: primary_source
    public_citable: true
    internal_trace_only: false
    reason: "Published 8-principle audit framework with 4 assurance levels. Original research."
    public_citation: "AVERI (as organization, not Miles Brundage by name)"

  - source_name: "McKinsey Global Institute"
    source_url: "https://www.mckinsey.com"
    type: primary_source
    public_citable: true
    internal_trace_only: false
    reason: "Original research: up to 30% of US labor hours could be automated by 2030."
    public_citation: "McKinsey Global Institute (as organization)"

  - source_name: "Marc Vidal"
    source_url: "https://www.marcvidal.net"
    type: discovery_source
    public_citable: false
    internal_trace_only: true
    reason: "Referente who analyzes OECD, McKinsey, EU data. Discovery path to primary sources. Not original source."
    public_citation: "DO NOT cite in public copy"

  - source_name: "Aelion.io / Iván Gómez"
    source_url: "https://aelion.io"
    type: contextual_reference
    public_citable: false
    internal_trace_only: true
    reason: "Landing page manifesto. Represents AEC sector mindset but no verifiable data."
    public_citation: "DO NOT cite in public copy"
```
