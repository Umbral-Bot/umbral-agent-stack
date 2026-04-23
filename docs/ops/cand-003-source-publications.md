# CAND-003 — Source Publications Analysis

> **Date**: 2026-04-23
> **Purpose**: Document publications analyzed for CAND-003 signal extraction.
> **Thesis**: "Criterio antes que automatización"

## Sources Analyzed

### 1. DeepLearning.AI / The Batch — Issue #340 (2026-02-13) [CITABLE: analysis source]

**Title**: Claude Opus 4.6, xAI + SpaceX, AI Outperforms Doctors, Standardized AI Audits
**Access**: Public, read successfully.

**Key content — Standardized AI Audits (AVERI framework)**:
- "AI is becoming ubiquitous, yet no standards exist for auditing its safety and security"
- Independent auditors "typically have access only to public APIs" — cannot examine training data, model code, or documentation
- "Different developers view risks in different ways, and measures of risk aren't standardized" — audit results not comparable
- Miles Brundage's AVERI published framework with **8 audit principles**: independence, clarity, rigor, information access, continuous monitoring
- **3 risk categories**: technology risk, organizational risk, assurance levels
- "Auditors should analyze model vendors, and not just the models" — system prompts, retrieval sources, tool access
- **4 Assurance Levels (AALs)**: AAL-1 (weeks, limited), AAL-2 (months, interviews), AAL-3 (years, near-full), AAL-4 (persistent, detecting deception)

**Editorial signal**: Even the most advanced AI labs lack agreed-upon criteria for evaluating AI systems. Without explicit audit standards, deployment is ungoverned. Direct parallel to AEC: teams deploy BIM/AI tools without review criteria.

### 2. DeepLearning.AI / The Batch — Issue #343 (2026-03-06) [CITABLE: analysis source]

**Title**: Anthropic vs US Government, Nano Banana, Frontier Agent Management, Google Math
**Access**: Public, read successfully.

**Key content — Frontier Agent Management**:
- OpenAI Frontier platform: "help orchestrate corporate cadres of agents, including building them, sharing information and business context among them"
- Each agent gets "its own identity, permissions, and guardrails"
- Companies control which employees access which agents
- Evaluation: ground-truth data (accuracy) or model outputs (politeness assessment)
- Agents "build memories, turning past interactions into useful context"
- "Human oversight remains implicit in the design rather than formally outlined"

**Editorial signal**: Even frontier agent platforms treat oversight as implicit, not explicit. Governance criteria (who can use what, what constitutes acceptable output, when to escalate) are designed into platforms but not into organizational processes. In AEC, the same pattern: tools have built-in guardrails, but teams lack explicit operational criteria for using them.

### 3. Marc Vidal — "El algoritmo como jefe supremo" (2026-03-23) [DISCOVERY SOURCE]

**Access**: Public (fetched in CAND-002 cycle, URL confirmed).
**Note**: Reused article, different extraction angle for CAND-003.

**Key data cited by Vidal (primary sources)**:
- **OECD (2025)**: 79% of European companies use algorithmic management tools
- **McKinsey Global Institute**: up to 30% of US labor hours could be automated by 2030
- **WEF (2025)**: 92M jobs displaced, 170M created before 2030
- **EU AI Regulation (Feb 2025)**: banned emotional recognition in workplaces

**CAND-003 extraction angle** (distinct from CAND-002):
- "¿Quién vigila al vigilante?" — who monitors the algorithmic decision-maker?
- Companies deploy algorithmic management without criteria for: what decisions the algorithm can make, what triggers human review, what constitutes a valid algorithmic outcome
- 79% of companies use these tools, but no report quantifies how many have explicit governance criteria for them

**Editorial signal**: Algorithmic management deployed without operational criteria. The 79% statistic shows adoption; the absence of governance criteria shows the gap. This is the CAND-003 thesis applied to the broader economy, translatable to AEC.

### 4. OECD — Algorithmic Management Report (2025) [CITABLE: primary source]

**Access**: Primary source, cited by Marc Vidal. Report data verified through Vidal's analysis.
**Key data**: 79% of European companies use algorithmic management tools.
**Relevance to thesis**: Massive adoption without proportional governance criteria.

### 5. McKinsey Global Institute — Automation Data [CITABLE: primary source]

**Access**: Primary source, cited by Marc Vidal.
**Key data**: Up to 30% of US labor hours could be automated by 2030.
**Relevance to thesis**: Automation scale demands explicit criteria for what to automate vs what requires human judgment.

### 6. AVERI — AI Verification and Research Institute [CITABLE: primary source]

**Access**: Primary source, reported by The Batch #340.
**Key data**: 8 audit principles, 4 assurance levels, 3 risk categories.
**Relevance to thesis**: First proposed framework for explicit AI audit criteria. Demonstrates the gap: the framework is needed precisely because no criteria existed before.

### 7. Aelion.io (Iván Gómez) [CONTEXTUAL REFERENCE]

**Access**: Public landing page.
**Key signal**: "La tecnología solo tiene sentido si genera valor desde el primer día."
**CAND-003 extraction**: "Value from day one" requires criteria to define what "value" means operationally. Without that definition, the claim is aspirational, not measurable.

## Cross-Source Signal Matrix for CAND-003

| Signal | Source(s) | Type | CAND-003 Thesis Connection |
|--------|-----------|------|---------------------------|
| No AI audit standards exist | Batch #340, AVERI | Evidencia | Without criteria, AI deployment is ungoverned |
| 79% of European companies use algorithmic tools | OECD via Vidal | Evidencia | Massive adoption outpaces governance |
| Agent platforms treat oversight as implicit | Batch #343 | Evidencia | Even tech leaders don't formalize criteria |
| 30% of US labor hours automatable by 2030 | McKinsey via Vidal | Evidencia | Scale of automation demands explicit criteria |
| "¿Quién vigila al vigilante?" | Vidal (discovery) | Inferencia | No criteria = no accountability |
| AEC's ROI-first filter demands day-one value | Aelion (contextual) | Inferencia | "Day-one value" needs operational definition |
| AEC teams deploy BIM/AI without review protocols | Synthesis | Hipótesis | Sector-specific hypothesis from general pattern |

## Strongest editorial opportunity

**Pattern**: Multiple sources converge on the same gap — AI tools are deployed at scale (79% OECD, 30% McKinsey, frontier platforms, agentic workflows) but governance criteria remain implicit, undefined, or nonexistent (no audit standards, implicit oversight, algorithmic management without human review criteria).

**AEC translation**: In construction, this manifests as: BIM mandates without review criteria, AI tools without escalation protocols, coordination workflows without explicit quality thresholds. Teams automate what they don't fully understand, amplifying ambiguity rather than reducing it.

**Formula candidate**: `pattern_synthesis` — combining signals from AI audit gap + agent governance + algorithmic management into AEC-specific thesis about operational criteria.
