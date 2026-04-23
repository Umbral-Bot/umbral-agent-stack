# CAND-003 — Source-Driven Editorial Flow Summary

> **Date**: 2026-04-23
> **Candidate**: CAND-003
> **Title**: Criterio antes que automatización: en AEC, la preparación real no empieza por la herramienta.
> **Status**: Borrador — all gates false
> **Thesis**: "Criterio antes que automatización" — AEC needs explicit operational criteria before automating.

---

## Flow Overview

CAND-003 follows the canonical 9-step source-driven editorial flow, producing 16 evidence files (matching CAND-002's pattern).

```
Stage 1: Source Intake → Source Publications
Stage 2: Rick Orchestrator Request → Result → Payload
Stage 3: Source Reclassification → Notion Draft Blueprint
Stage 4: Attribution Validation (Request → Result)
Stage 5: Voice Pass (Request → Result)
Stage 6: QA Pass (Request → Result → Postchange Request → Postchange Result)
Stage 7: Flow Summary (this file)
```

## File Inventory (16 files)

| # | File | Stage | Purpose |
|---|------|-------|---------|
| 1 | `cand-003-source-intake.md` | 1 | Referentes selection and discovery path |
| 2 | `cand-003-source-publications.md` | 1 | Publication analysis with cross-source signal matrix |
| 3 | `cand-003-rick-orchestrator-request.md` | 2 | Full prompt for rick-orchestrator |
| 4 | `cand-003-rick-orchestrator-result.md` | 2 | Run ID and execution log |
| 5 | `cand-003-payload.md` | 2 | Complete YAML payload (title, premisa, extraction matrix, copy, decantation) |
| 6 | `cand-003-source-reclassification.md` | 3 | Attribution policy compliance per source |
| 7 | `cand-003-notion-draft-result.md` | 3 | Notion page blueprint (PENDING HITL creation) |
| 8 | `cand-003-rick-qa-attribution-request.md` | 4 | Attribution validation request |
| 9 | `cand-003-rick-qa-attribution-result.md` | 4 | Attribution validation result: **pass** |
| 10 | `cand-003-rick-qa-voice-request.md` | 5 | Voice/ortho/premisa validation request |
| 11 | `cand-003-rick-qa-voice-result.md` | 5 | Voice validation result: **pass** |
| 12 | `cand-003-rick-qa-request.md` | 6 | Full editorial QA request |
| 13 | `cand-003-rick-qa-result.md` | 6 | QA result: **pass_with_changes** (1 minor) |
| 14 | `cand-003-rick-qa-postchange-request.md` | 6 | Postchange validation request |
| 15 | `cand-003-rick-qa-postchange-result.md` | 6 | Postchange result: **pass** |
| 16 | `cand-003-source-driven-flow.md` | 7 | This file — flow summary |

## Sources Used

| Source | Type | Citable | Publications |
|--------|------|---------|-------------|
| The B1M | original_article | Yes | LA Olympics readiness, Tour Montparnasse renovation |
| DeepLearning.AI / The Batch | analysis_source | Yes | #343 (Frontier/Context Hub), #347 (Claude Code, Sora) |
| Marc Vidal | discovery_source | No (internal only) | → OECD (2025), Solow (1987) |
| Aelion.io | contextual_reference | No (internal only) | Landing page manifesto |

## Extraction Matrix Summary

| Type | Count | Key Signals |
|------|-------|-------------|
| Evidencia | 6 | LA criteria erosion, Montparnasse absent criteria, Frontier permissions, Context Hub anti-hallucination, Claude Code permission gates, Sora cancellation |
| Inferencia | 3 | Criteria = invisible infrastructure, Capability without criteria is fragile, Solow paradox persists without criteria change |
| Hipótesis | 1 | AEC teams defining criteria first will capture disproportionate value |

## Transformation Formula

**"Criterio como infraestructura"** — pattern_synthesis

Selected over: checklist_prescriptivo, caso_de_estudio_sora, continuacion_directa_de_cand_002.

## QA History

| Pass | Run ID | Verdict |
|------|--------|---------|
| QA Initial | 5b3a9f17-... | pass_with_changes (1 minor: hipótesis AEC anchor) |
| QA Postchange | a2e7c946-... | pass |
| Attribution | c7d42e8f-... | pass |
| Voice | e8f25a1d-... | pass |

## Differentiation from CAND-002

| Dimension | CAND-002 | CAND-003 |
|-----------|----------|----------|
| Thesis | "The barrier is the organization" (gap diagnosis) | "Define criteria before automating" (prescription) |
| Angle | Diagnostic — identifies what's missing | Prescriptive — tells you what to do first |
| Sources | Batch #349/#348/#346/#342, B1M "Biggest Boom"/"The LINE", same Vidal | Batch #343/#347, B1M LA Olympics/Montparnasse, same Vidal (different pubs) |
| Key concept | Preparación organizacional | Criterios operativos explícitos |
| Progression | Awareness: "you have a gap" | Awareness: "here's where to start" |
| Attribution | Post-hoc policy application | Policy from start (no post-hoc changes) |
| Orthography | Corrected post-hoc (85 blocks) | Correct from start |

## Process Improvements in CAND-003

1. **Attribution policy from start**: Copy written without person names from the beginning. No post-hoc reclassification needed.
2. **Orthography correct from start**: Tildes, ñ, punctuation all correct in first draft. No correction pass needed.
3. **Different publications from same referentes**: Demonstrates the canonical flow can use the same referentes DB without repeating content.
4. **Cleaner QA**: Only 1 minor change (hipótesis AEC anchor) vs CAND-002's more extensive corrections.

## Next Steps

- [ ] Human review of copy and premisa
- [ ] Create Notion page when HITL authorized
- [ ] Set `aprobado_contenido` when David approves
- [ ] Schedule publication when `autorizar_publicacion` is set
- [ ] Consider CAND-004 progression: awareness → consideration with a practical case
