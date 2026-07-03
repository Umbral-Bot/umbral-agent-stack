# Bloque decisión PRs — 2026-07-03

- **Surface:** Copilot Windows (repo-only; sin VPS, sin runtime).
- **Base:** `main@454e606` (post #504/#507). Contexto: hygiene Pass 8 cerrado, Rick operativo.
- **Gate:** sin autorización explícita de David en el prompt → **0 merges, 0 cierres ejecutados**. Este doc es la recomendación.

## Tabla resumen

| PR | Título (corto) | Estado | Decisión recomendada | Motivo |
|----|----------------|--------|----------------------|--------|
| #480 | docs(pit): contrato v2 broker-real + roadmap P1-P9 | OPEN, CI verde, mergeable | **CLOSE con comentario** | Contrato pre-ejecución ya superseded; ver justificación abajo |
| #421 | docs(evidence): OpenClaw E2E Cycle 001 sanitized | OPEN (2026-05-19) | **CLOSE con comentario** ⚠️ | Evidencia histórica de ciclo cerrado; **contenido único no está en main** (rescatable vía cherry-pick si se quiere archivo) |
| #418 | test(o16-2/047): pdf_parser tests + gap-closure audit | OPEN (2026-05-14) | **CLOSE con comentario** ⚠️ | O16.2/047 stale 7 semanas; bicep tocado divergió de main (c-via-3). **Rescatable:** `tests/test_pdf_parser.py` (250 líneas; `scripts/aeco-kb/pdf_parser.py` sigue vivo en main) |
| #413 | task(coord-ag-2a): pinned aeco-source-crawler **[DO NOT MERGE]** | OPEN (2026-05-10) | **CLOSE con comentario** | DO NOT MERGE explícito en título; el pin del crawler llegó a main vía c-via-3 (`475c7a5`) |
| #389 | feat(stage7_5): multiformat **(DRAFT — DO NOT MERGE)** | OPEN (2026-05-08), +5491 | **CLOSE con comentario** | DRAFT/DO NOT MERGE explícito; la generación multi-formato ya está en main por otra vía (`tests/test_document_generator.py`, deps docxtpl/fpdf2 en `pyproject.toml`) |
| #379 | task(052): blocked — GHCR sin write:packages | OPEN (2026-05-08), +34/-2 | **CLOSE con comentario** | Status-report de un blocker resuelto por C-VIA-3 (PAT design 2026-05-15 + imagen pinned en main); el task file base ya existe en main |
| #321 | feat(infra): O16 base — ADR + arch + Bicep + off-sponsorship | OPEN (2026-05-07), +1161 | **REPORTAR — no cerrar sin OK David** | Tiene **2 piezas únicas** (ver análisis abajo); resto superseded |

## PR #480 — justificación CLOSE (5 líneas)

1. Su propio criterio de salida P0 dice literal: *"el PR queda sin merge"* — era artefacto de contrato pre-ejecución (`P0_CONTRACT_OK`), no candidato a merge.
2. El roadmap P1-P9 que define **ya se ejecutó**: broker-real alcanzado el 2026-06-22 (`PIT_RUN_PASS_BROKER_REAL` REACHED — `pit-broker-real-pass-handoff-20260622.md`, `pit-readiness-golden-20260622.md`).
3. Su payload `copilot_cli.run` (bloques `repo.provider/permissions/secrets_scope`, placeholders `TODO_P3_VPS_VERIFY_*`) **contradice el contrato P4 implementado y testeado** en main (`pit-p4-broker-contract-20260621.md` + `tests/test_copilot_cli.py`: `mission/model/prompt/metadata`).
4. Main ya tiene la cadena canónica viva: SKILL.md post-#484 (metadata P4 obligatoria), `examples/pit/pit_spec.v2.yaml` + specs broker v1-v4 (#504), validador y token ledger (#485); los veredictos (`PIT_RUN_PASS_BROKER_REAL`, etc.) ya están absorbidos en docs P5/P6/P9.
5. Mergearlo hoy introduciría 3 docs auto-declarados "contrato canónico vigente" con schema divergente y gaps ya cerrados → drift documental sin ganancia. Cerrar referenciando este análisis; la historia queda preservada en el PR cerrado.

## PR #321 — análisis ADRs únicos (reporte para David)

| Archivo en #321 | ¿En main? | Veredicto |
|---|---|---|
| `docs/adr/ADR-011-2026-05-06-codegen-backend-stage-gate.md` | ❌ No (main tiene otros dos ADR-011: orquestación-editorial y pit-scope — colisión de numeración preexistente) | **ÚNICO** — decisión codegen backend stage-gate no registrada en main |
| `docs/runbooks/azure-off-sponsorship-2026-07-30.md` | ❌ No hay runbook off-sponsorship en main | **ÚNICO y sensible al tiempo** — la fecha 2026-07-30 está a 27 días |
| `docs/architecture/17-areas-gerencias-agentes-subagentes-model.md` | ✅ Sí (llegó vía `85a0215`+`4117dfb`, versión posterior con gaps confirmados) | Superseded |
| `infra/azure/*.bicep` (11 archivos, layout plano) | ✅ Conceptualmente (main evolucionó a `infra/azure/modules/` con deploy scripts, editorial-blog y aeco-kb) | Superseded |
| `docs/adr/ADR-011… (nota)` | — | Si se rescata, renumerar (ADR-013+) para no agravar la colisión ADR-011 |

**Recomendación #321:** cherry-pick de las 2 piezas únicas (ADR renumerado + runbook off-sponsorship) a un PR nuevo pequeño → luego CLOSE #321. El runbook off-sponsorship conviene revisarlo pronto por la fecha 2026-07-30. **No se cierra sin OK explícito de David.**

## Ejecución

- Merges ejecutados: **0**. Cierres ejecutados: **0**.
- Motivo: el prompt no contiene autorización explícita (las frases "Autorizo…" figuran solo como plantilla del gate).
- Para ejecutar, David responde con: `Autorizo merge #480` (no recomendado; la recomendación es CLOSE), `Autorizo cierre #480`, y/o `Autorizo cierre zombis #421 #418 #413 #389 #379`.
- #321 requiere frase propia tras decidir sobre el rescate: `Autorizo cierre #321 (con/sin rescate)`.
