# Contrato: revisión humana de publicaciones editoriales

Estado: vigente desde Fase 2 (versioning editorial). Surface repo-only.
Referencia: docs/ops/cand-001-editorial-audit-v2.md (C1/C2/C3).

## Propósito

Definir qué debe existir **antes** de que una publicación pase a revisión humana
(Gate 1) y antes de que Rick escriba copy v2 en Notion. Backward-compatible: no
cambia el pipeline v1; añade precondiciones de artefacto.

## Capacidades de versionado

- **C1 — Anti-muletilla:** `evals/editorial/benchmark-umbral-voice-v1.yaml`
  (`fail_automatico_si_aparece`, `flags_revision_obligatoria`, `reglas_cuantitativas`)
  + calibración `director-comunicacion-umbral/CALIBRATION.md` + QA en `rick-qa/ROLE.md`.
- **C2 — Claim ledger:** `evals/editorial/claim-ledger.schema.yaml`.
- **C3 — Revision log:** `evals/editorial/revision-log.template.md`.

## Precondiciones de Gate 1 (revisión humana)

1. **C2 claim ledger** generado para la publicación: cada claim → fuente → confianza →
   método → evidencia. Sin ledger, Gate 1 no se habilita.
2. **C3 revision log** generado para la versión propuesta (vN → vN+1), con citas
   antes→después y regla aplicada.
3. Benchmark C1 corrido sin `fail_automatico` sin resolver (`voice: pass` lo exige).

## Regla operativa

Rick **no** escribe copy v2 en Notion sin generar antes el claim ledger (C2) y el
revision log (C3). Los gates de publicación y la autorización siguen siendo de David;
este contrato solo define los artefactos previos, no automatiza ninguna publicación.
