# CAND-003 — Source-Driven Editorial Flow

> **Date**: 2026-04-23
> **Publication ID**: CAND-003
> **Thesis**: "Criterio antes que automatización"
> **Branch**: `codex/cand-002-source-driven-flow`
> **Notion Page**: `34b5f443-fb5c-8167-b184-e3c6cf1f6c3f`

---

## Canonical 9-Stage Sequence

### Stage 1 — Fuentes y señales
- **Status**: Complete
- Fetched and classified 6 sources (4 citable, 2 internal-only)
- Attempted additional sources: Bernard Marr (404), The B1M (weak fit), Batch #347 (weak signal)
- Source classification applied from start (lesson from CAND-002)
- **Files**: `cand-003-source-intake.md`, `cand-003-source-publications.md`

### Stage 2 — Extracción y transformación
- **Status**: Complete
- Extraction matrix with evidencia/inferencia/hipótesis separation from start
- Decantation: 4 discarded, 5 conserved, 2 combined syntheses
- Transformation formula: `pattern_synthesis`
- rick-orchestrator run: `67618f1e-5c7d-416f-83a9-6927d747a348`
- **Files**: `cand-003-rick-orchestrator-request.md`, `cand-003-rick-orchestrator-result.md`, `cand-003-payload.md`

### Stage 3 — Borrador editorial base
- **Status**: Complete
- Notion page created with 143 blocks
- Premisa as property AND visible in body (callout block)
- Properties: Título, Premisa, Copy LinkedIn, Copy X, Claim principal, Ángulo editorial, Resumen fuente, Visual brief, Comentarios revisión, Notas
- Estado: Borrador, all gates false

### Stage 4 — Validación de atribución y trazabilidad
- **Status**: Complete
- rick-qa attribution run: `11af3dbe-10dd-4882-b82b-2d32b0c3f6fc`
- Initial verdict: `pass_with_changes` (2 issues in extraction matrix)
  1. Vidal → OECD/McKinsey reclassified as primary source with discovery trace
  2. Aelion ROI-first removed from inference support
- Final verdict: `pass`
- **Files**: `cand-003-rick-qa-attribution-request.md`, `cand-003-rick-qa-attribution-result.md`

### Stage 5 — Pasada de voz contra Guía Editorial y Voz de Marca
- **Status**: Complete
- **This was a real, separate rewrite pass** — not just QA verification
- 7 Notion body blocks rewritten with David's voice profile
- Voice source: **authorized summary** (Notion voice guide page `0192ad1f-3ca1-44ae-954d-0b738261258e` not accessible by integration)
- Key changes: more direct opening, second person ("tu organización"), less expository transitions, more AEC-native language, added "Entregables que se aceptan por inercia, no por verificación"
- rick-qa voice validation run: `80827fc2-170b-4787-82aa-826a95f8691a`
- Verdict: `pass`
- **Files**: `cand-003-rick-qa-voice-request.md`, `cand-003-rick-qa-voice-result.md`

### Stage 6 — QA editorial y técnico (consolidated final)
- **Status**: Complete
- rick-qa final run: `ae155b48-e82e-4f59-ab40-a1589448bb66`
- Verdict: `pass` (all 7 dimensions)
- Technical: pytest 175 passed, schema validation passed, audit report written, security grep clean
- **Files**: `cand-003-rick-qa-request.md`, `cand-003-rick-qa-result.md`

### Stage 7 — Revisión humana
- **Status**: Ready
- CAND-003 is in Notion as Borrador, ready for David's review
- Gates remain false, no publication fields set

### Stage 8 — Aprobación de contenido
- **Status**: Not executed (awaiting David)

### Stage 9 — Autorización de publicación
- **Status**: Not executed (awaiting David)

---

## Evidence Files (12)

| # | File | Stage |
|---|------|-------|
| 1 | `cand-003-source-intake.md` | 1 |
| 2 | `cand-003-source-publications.md` | 1 |
| 3 | `cand-003-rick-orchestrator-request.md` | 2 |
| 4 | `cand-003-rick-orchestrator-result.md` | 2 |
| 5 | `cand-003-payload.md` | 2 |
| 6 | `cand-003-rick-qa-attribution-request.md` | 4 |
| 7 | `cand-003-rick-qa-attribution-result.md` | 4 |
| 8 | `cand-003-rick-qa-voice-request.md` | 5 |
| 9 | `cand-003-rick-qa-voice-result.md` | 5 |
| 10 | `cand-003-rick-qa-request.md` | 6 |
| 11 | `cand-003-rick-qa-result.md` | 6 |
| 12 | `cand-003-source-driven-flow.md` | 6 |

## Improvements over CAND-002

1. **Attribution from start**: Source classification applied in Stage 1, not retrofitted after draft
2. **Orthography from start**: Correct Spanish from first draft, no separate correction pass needed
3. **Voice pass as separate stage**: Real rewrite (Stage 5), not compressed into QA
4. **Premisa in body AND property**: Callout block in body for human review visibility
5. **Documented voice source**: Explicit that voice pass used authorized summary, not live guide

## State

- Estado: Borrador
- Gates: `aprobado_contenido=false`, `autorizar_publicacion=false`, `gate_invalidado=false`
- `ready_for_human_review`: true
- `ready_for_publication`: false
- Rick active: false
- Publish authorized: false
