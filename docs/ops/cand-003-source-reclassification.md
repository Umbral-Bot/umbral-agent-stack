# CAND-003 — Source Reclassification per Attribution Policy

> **Date**: 2026-04-23
> **Policy applied**: `docs/ops/editorial-source-attribution-policy.md`
> **Purpose**: Reclassify all sources used in CAND-003 per David's attribution rule.
> **Note**: Same policy as CAND-002. Applied from the start (not post-hoc).

## Source Classification

```yaml
source_classification:
  - source_name: "The B1M"
    source_url: "https://www.theb1m.com"
    type: original_article
    public_citable: true
    internal_trace_only: false
    reason: "Original construction media with own journalism and reporting. Both articles (LA Olympics, Tour Montparnasse) are original reporting by The B1M team."
    publication_urls:
      - "https://www.theb1m.com/video/will-los-angeles-be-ready-for-the-next-olympics"
      - "https://www.theb1m.com/video/the-plan-to-save-paris-most-hated-building"
    public_citation: "The B1M (as organization, not Fred Mills by name)"

  - source_name: "DeepLearning.AI / The Batch"
    source_url: "https://www.deeplearning.ai/the-batch"
    type: analysis_source
    public_citable: true
    internal_trace_only: false
    reason: "Newsletter producing original editorial analysis on AI trends. Issue #343 on agent management and #347 on Claude Code architecture are The Batch's own synthesis and analysis. Citable as organization."
    publication_urls:
      - "https://www.deeplearning.ai/the-batch/issue-343/"
      - "https://www.deeplearning.ai/the-batch/issue-347/"
    public_citation: "DeepLearning.AI or The Batch (as organization, not Andrew Ng by name)"

  - source_name: "Marc Vidal"
    source_url: "https://www.marcvidal.net"
    type: discovery_source
    public_citable: false
    internal_trace_only: true
    reason: "Referente who analyzes and interprets external sources. For CAND-003, the criteria angle comes from the OECD and Solow data he cites, not from his own research. Vidal is the discovery path, not the authority."
    original_source_name: "See primary sources below"
    public_citation: "DO NOT cite in public copy"

  - source_name: "Aelion.io / Ivan Gomez Rodriguez"
    source_url: "https://aelion.io"
    type: contextual_reference
    public_citable: false
    internal_trace_only: true
    reason: "Landing page manifesto without specific data or verifiable claims. Represents AEC sector mindset (ROI-first = criteria-first) but does not substantiate factual claims."
    public_citation: "DO NOT cite in public copy"
```

## Primary Sources Identified Behind Discovery Sources

### Behind Marc Vidal's articles (same as CAND-002, different extraction angle):

| Vidal Article | Primary Source | Organization | CAND-003 Criteria Angle |
|--------------|---------------|-------------|------------------------|
| El algoritmo como jefe supremo | OECD Algorithmic Management report (2025) | OECD | 79% of European companies deploy algorithms without governance criteria |
| El algoritmo como jefe supremo | McKinsey Global Institute | McKinsey | Automation of labor hours without governance frameworks |
| La paradoja de la productividad | Robert Solow's productivity paradox (1987) | — (established concept) | Technology without criteria/process change doesn't improve productivity |

### The Batch (citable as analysis_source):

| Batch Issue | Content Type | Criteria-Relevant Content |
|------------|-------------|--------------------------|
| #343: Management for Agents | Original editorial + product analysis | Frontier: permissions, guardrails, evaluation metrics per agent. Context Hub: explicit context prevents hallucination. |
| #347: Inside Claude Code | Analysis of leaked source code | 40+ tools with permission gates, 3-tier memory, subagent coordination. Architecture embeds criteria. |
| #347: OpenAI Exits Sora | Market analysis | $1M/day loss, capability without operational criteria = cancellation. |

### The B1M (citable as original_article):

| B1M Article | Content Type | Criteria-Relevant Content |
|------------|-------------|--------------------------|
| LA Olympics readiness | Original journalism | "Twenty-eight by 28" — aspirational criteria, retreat from "no cars" to "transit-first". Schank: "Not all of them were realistic." |
| Tour Montparnasse renovation | Original journalism | Built 1973 without integration criteria → 50 years rejection → France banned skyscrapers → €300M renovation |

## Impact on CAND-003 Copy

### Copy was written WITH attribution policy from the start:

1. **No persons named**: Copy does not mention Andrew Ng, Marc Vidal, Ivan Gomez, Fred Mills, or any referente by name.
2. **Concepts, not names**: "plataformas de gestión de agentes", "arquitecturas más avanzadas", "una ciudad prometió una olimpíada sin autos", "un rascacielos se construyó sin criterios".
3. **Citable organizations referenced indirectly**: The B1M content is referenced as infrastructure evidence. The Batch content is referenced as AI/agent management evidence.
4. **Primary sources behind discovery**: OECD and Solow data inform the thesis but are not explicitly cited in the LinkedIn copy (they are in internal traceability).

### Internal traceability preserved:

- Marc Vidal as discovery source for OECD/Solow signals
- Aelion.io as contextual reference for AEC ROI-first mindset
- Full extraction matrix with source attribution in payload
- Source reclassification documented in this file
