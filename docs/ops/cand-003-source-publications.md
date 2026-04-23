# CAND-003 — Source Publications Analysis

> **Date**: 2026-04-23
> **Purpose**: Capture publications from David's referentes for CAND-003 editorial extraction.
> **Method**: Public web fetch (RSS/web pages). No login bypass. No scraping.
> **Thesis**: "Criterio antes que automatización"

## Sources Analyzed

### 1. The B1M (Fred Mills) — theb1m.com

**Access status**: Public, read successfully.
**Period reviewed**: Feb — Apr 2026
**Publications selected** (different from CAND-002):

| Date | Title | Editorial Signal for CAND-003 |
|------|-------|-------------------------------|
| 2026-04-13 | Will Los Angeles Be Ready For The Next Olympics? | Readiness = explicit criteria, not ambition. "Twenty-eight by 28" had 28 transport projects — many aspirational, not realistic. "No cars" retreated to "transit-first" when criteria didn't hold. |
| 2026-02-11 | The Plan to Save Paris' Most Hated Building | Building without integration criteria → 50 years of rejection. France banned skyscrapers in central Paris. Now €300M renovation to fix the original absence of criteria. |

**Key signals for CAND-003**:
- **LA Olympics**: The shift from "no-car Games" to "transit-first Games" demonstrates what happens when criteria aren't defined before committing to ambition. Joshua Schank (InfraStrategies): "A lot of the projects in 'Twenty-eight by 28' I think were much more aspirational... Not all of them were realistic. And I think the folks who were there at the time knew that."
- **Tour Montparnasse**: Built in 1973 without urban integration criteria. Backlash was so strong France imposed 25m height limits across central Paris in 1977. The absence of criteria at design phase created 50+ years of organizational debt. The €300M renovation by Nouvelle AOM is the cost of missing criteria.

### 2. Andrew Ng / The Batch — deeplearning.ai/the-batch

**Access status**: Public, read successfully.
**Period reviewed**: Mar — Apr 2026
**Issues selected** (different from CAND-002):

| Date | Issue | Key Theme | Criteria Connection |
|------|-------|-----------|---------------------|
| 2026-03-06 | #343 | Frontier agent management, Context Hub | Agent management requires explicit criteria: permissions, guardrails, evaluation metrics per agent. Context Hub: agents without explicit operational context hallucinate and use wrong APIs. |
| 2026-04-03 | #347 | Inside Claude Code, OpenAI Exits Sora, Voice UI adoption | Claude Code architecture embeds criteria: 40+ tools each with permission gates, 3-tier memory, subagent coordination. Sora cancellation: capability without operational criteria = $1M/day loss → shutdown. Voice UIs: adoption barrier is knowing when/how to use, not the tech itself. |

**Key signals for CAND-003**:

#### The Batch #343 — Management for Agents (OpenAI Frontier)
- OpenAI launched Frontier: platform for orchestrating corporate agent cadres.
- Each agent has own identity, permissions, guardrails. Companies control which employees can use it.
- Frontier evaluates agents' outputs and provides feedback based on ground-truth metrics.
- **Signal**: Even AI agent management requires CRITERIA (permissions, guardrails, evaluation) before deployment.
- Andrew Ng on Context Hub: coding agents use outdated APIs, hallucinate parameters, don't know about tools they should use. Solution = explicit context/criteria.
- **Signal**: Agents without explicit operational context produce wrong outputs. Criteria prevent hallucination.

#### The Batch #347 — Inside Claude Code
- Source code leak revealed architecture: 40+ tools each with own permission modules and gates, 3-tier memory system, subagent swarms with shared memory.
- **Signal**: The most advanced agent architectures embed explicit operational criteria at the architecture level — permissions, tool isolation, memory management.

#### The Batch #347 — OpenAI Exits Video Generation (Sora)
- Sora losing ~$1M/day. DAU peaked at 1M, halved quickly.
- "The era in which an AI demo — however impressive — is sufficient to establish leadership may be drawing to a close."
- **Signal**: Impressive capability without sustainable operational criteria = failure. Capability alone doesn't create value.

### 3. Marc Vidal — marcvidal.net (Discovery Source)

**Access status**: Public, read successfully.
**Period reviewed**: Mar 2026
**Publications reused from CAND-002 with DIFFERENT extraction angle**:

| Date | Title | CAND-003 Criteria Angle (vs CAND-002 Gap Angle) |
|------|-------|------------------------------------------------|
| 2026-03-23 | El algoritmo como jefe supremo | CAND-002 extracted: algorithmic management replaces oversight. **CAND-003 extracts**: deploying algorithms without governance CRITERIA = opaque centralization. The OECD primary source shows 79% of companies lack criteria. |
| 2026-03-09 | La paradoja de la productividad | CAND-002 extracted: tech without productivity gains. **CAND-003 extracts**: technology without PROCESS CRITERIA doesn't produce returns. Solow's insight is that criteria/process must change, not just tools. |

**Note**: Marc Vidal remains discovery_source (not citable). The primary sources are OECD and Solow.

### 4. Aelion.io (Ivan Gomez Rodriguez)

**Access status**: Public landing page, no blog.
**Key quote**: "La tecnología solo tiene sentido si genera valor desde el primer día."
**CAND-003 angle**: ROI-first = criteria-first. The AEC mindset demands defined criteria for when technology generates value, not open-ended experimentation.
**Classification**: Contextual reference (same as CAND-002).

## Cross-Source Signal Matrix for CAND-003

| Signal | Sources | Type | CAND-003 Relevance |
|--------|---------|------|-------------------|
| Undefined criteria lead to scope retreat | B1M (LA Olympics) | evidencia | "No car" → "transit-first" → "some car" = criteria erosion under pressure |
| Building without criteria creates permanent debt | B1M (Tour Montparnasse) | evidencia | 50 years rejection + €300M fix = cost of absent criteria |
| Agent management requires explicit criteria | Batch #343 (Frontier) | evidencia | Permissions, guardrails, evaluation metrics per agent |
| Agents without context produce wrong output | Batch #343 (Context Hub) | evidencia | Explicit operational context prevents hallucination |
| Advanced architectures embed criteria | Batch #347 (Claude Code) | evidencia | 40+ tools with permission gates, 3-tier memory |
| Capability without criteria = failure | Batch #347 (Sora exit) | evidencia | $1M/day loss, DAU halved → cancelled |
| Most companies deploy algorithms without governance criteria | OECD 2025 (behind Vidal) | evidencia | 79% European companies lack algorithmic governance criteria |
| Technology without process criteria ≠ productivity | Solow 1987 (behind Vidal) | evidencia | Established economic principle |
| AEC demands criteria-first value | Aelion.io | contextual | ROI-first = criteria-first sector mindset |

## Strongest Pattern

**Criteria before capability**: Across infrastructure (B1M), AI agent management (The Batch), and organizational research (OECD/Solow), the same pattern emerges — defining explicit operational criteria before deploying capability is what determines whether that capability produces value or amplifies disorder.

**Differentiation from CAND-002**: CAND-002 identified the gap between capability and readiness. CAND-003 identifies the specific missing element: explicit operational criteria. The prescription is not "get ready" (vague) but "define your criteria first" (actionable).
