# Editorial Source Attribution Policy

> **Effective**: 2026-04-23
> **Applies to**: All editorial candidates produced by the Rick editorial system (rick-editorial, rick-orchestrator, and any operator simulating rick-editorial output).
> **Decision by**: David Moreira

## Core Rule

The public copy (LinkedIn, X, blog, newsletter) must NOT mention referentes/personas as the authority behind a claim if they are not the original/primary source of that claim. If a referente analyzes, summarizes, or interprets a publication from another entity, the citable source in public content must be the original entity, not the referente.

## Definitions

| Term | Definition |
|------|-----------|
| **Referente** | Person, account, or newsletter used to discover an editorial signal. Curated by David in the Referentes DB. |
| **Discovery source** | The referente or channel that led the editorial system to find an idea. Internal traceability only. |
| **Primary/original source** | The report, paper, article, official documentation, dataset, company, or organization that substantiates the factual claim. |
| **Citable source** | A source that may appear in public-facing content (copy, posts, articles). Must be a primary/original source or an organization producing original analysis. |
| **Internal traceability** | Source information that stays in Notion body, docs, and internal evidence files. Not exposed in public copy. |
| **Public attribution** | Any mention of a source, person, or organization in the final copy that the audience will see. |

## Source Hierarchy

Sources are ranked by citation authority. Higher-ranked sources take precedence in public attribution:

1. **Official document / original report / paper / dataset / primary publication** — e.g., McKinsey Global Institute report, ISO standard, Eurostat dataset, peer-reviewed paper.
2. **Official documentation from tool, standard, or institution** — e.g., Autodesk documentation, buildingSMART specifications, government regulations.
3. **Original article from media outlet or company** — e.g., The B1M original reporting, Bloomberg investigation, company press release.
4. **Newsletter/blog producing original verifiable analysis** — e.g., DeepLearning.AI/The Batch editorial analysis, construction industry newsletter with original data.
5. **Referente/persona commenting on or interpreting external sources** — e.g., Marc Vidal analyzing a McKinsey report, Andrew Ng discussing industry trends.
6. **Agent inference** — conclusions drawn by the editorial system from combining multiple sources.
7. **Editorial hypothesis** — unverified suppositions proposed by the editorial system.

## Attribution Rules

### 1. No Source Laundering

Do not convert a referente's opinion or commentary into primary evidence. If Marc Vidal publishes an article analyzing a McKinsey report, cite McKinsey as the source. Marc Vidal is the discovery path, not the authority.

### 2. No Public Name-Dropping

Do not use referentes' names in public copy to lend authority when the real evidence comes from another source. Avoid patterns like "Andrew Ng shows that..." or "Marc Vidal insists that..." when the underlying claim is supported by third-party data or research.

### 3. Trace, Don't Cite

Referentes can and should be traced internally (Notion body, extraction matrix, evidence docs) as discovery sources. This preserves the editorial audit trail. But they do not appear in the public copy as cited authorities unless they are the original source.

### 4. Original Source Required for Factual Claims

If a claim is presented as evidence (not opinion or hypothesis), it must be traceable to a primary source. If no primary source can be found:
- The signal can be used as **inspiration** or framed as an **editorial hypothesis**.
- It must NOT be presented as a cited factual claim.
- It must be clearly marked in the extraction matrix as `inferencia` or `hipotesis`.

### 5. Contextual References

If a source is only a landing page, manifesto, or general positioning statement without a specific article or data:
- Mark as `contextual_reference` in the source classification.
- Do NOT cite as a public source of evidence.
- May be used to inform editorial angle but not to substantiate factual claims.

### 6. Organizational vs. Personal Citation

When a referente produces content through an organization:
- Cite the **organization**, not the person, in public copy.
- Example: cite "The B1M" not "Fred Mills"; cite "DeepLearning.AI" or "The Batch" not "Andrew Ng"; cite "Aelion" not "Ivan Gomez".
- Exception: when the person IS the primary source (e.g., an author's own research paper, a CEO's direct statement about their company).

## Source Classification Schema

Every source used in a source-driven candidate must be classified:

```yaml
source_classification:
  - source_name: ""
    source_url: ""
    type: primary_source | original_article | official_doc | analysis_source | discovery_source | contextual_reference
    public_citable: true | false
    internal_trace_only: true | false
    reason: ""
    original_source_url: ""  # if discovery_source, the URL of the primary source found
    original_source_name: "" # name of the primary source organization
```

### Classification Decision Tree

1. Is this the original report, paper, dataset, or official document? -> `primary_source`, public_citable: true
2. Is this an original article/video by a media outlet with their own reporting? -> `original_article`, public_citable: true (cite organization, not person)
3. Is this official documentation from a tool, standard, or institution? -> `official_doc`, public_citable: true
4. Is this a newsletter/blog with original analysis? -> `analysis_source`, public_citable: true only if producing original verifiable analysis (cite organization)
5. Is this a referente commenting on or interpreting external sources? -> `discovery_source`, public_citable: false, internal_trace_only: true
6. Is this a landing page or general manifesto without specific data? -> `contextual_reference`, public_citable: false, internal_trace_only: true

## Impact on Existing Documents

### Extraction Matrix

The extraction matrix must include:
- `evidence_source`: the primary/original source that substantiates the claim
- `discovery_source`: the referente or channel that led to finding the idea
- `public_citation_source`: what the public copy should reference (if different from evidence_source)

### Payload Template

The payload template (`docs/ops/rick-editorial-candidate-payload-template.md`) must include `source_classification` in the source section.

### rick-editorial ROLE.md

The source discipline section of `ROLE.md` must reference this policy.

### QA Validation

`rick-qa` must validate:
- No referentes cited as public authorities when they are not original sources.
- Source classification is present and consistent.
- Public copy does not contain name-dropping of discovery sources.
- Claims marked as evidence have traceable primary sources.

## Retroactive Application

This policy applies immediately to:
- CAND-002 (first source-driven candidate) — copy and Notion body must be updated.
- All future source-driven candidates.

CAND-001 (opinion operativa without external sources) is not affected.

## References

- rick-editorial ROLE.md: `openclaw/workspace-agent-overrides/rick-editorial/ROLE.md`
- Payload template: `docs/ops/rick-editorial-candidate-payload-template.md`
- Publicaciones schema: `notion/schemas/publicaciones.schema.yaml`
