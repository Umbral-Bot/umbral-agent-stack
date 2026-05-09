# Editorial Pipeline — Drift Audit (doc ↔ código)

> **Fecha:** 2026-05-08
> **Branch:** `copilot/docs-editorial-master-plan`
> **Hilo:** wave1-h1-master-plan-drift-audit
> **Status:** PROPUESTO — pendiente revisión humana
> **Scope:** auditar divergencias entre la documentación editorial existente y el estado real de `scripts/discovery/stage*.py` en `main` al commit actual. Ola 1 — read-only. No toca código.

## 0. Inventario real de scripts (`ls scripts/discovery/stage*.py`)

| Archivo | Existe en `main` |
|---|---|
| `scripts/discovery/stage2_ingest.py` | ✅ |
| `scripts/discovery/stage3_promote.py` | ✅ |
| `scripts/discovery/stage4_push_notion.py` | ✅ |
| `scripts/discovery/stage5_rank_candidates.py` | ✅ |
| `scripts/discovery/stage6_aec_combine.py` | ✅ (stub `NotImplementedError`) |
| `scripts/discovery/stage6_llm_combinator.py` | ✅ |
| `scripts/discovery/stage7_5_copy_writer.py` | ✅ (FROZEN Ola 1) |
| `scripts/discovery/stage7_5_post_review_comment.py` | ✅ |
| `scripts/discovery/stage7_publish_drafts.py` | ✅ |
| `scripts/discovery/stage8_image_generator.py` | ✅ |
| `scripts/discovery/stage9_linkedin_draft.py` | ✅ |
| `scripts/discovery/stage9b_linkedin_oauth.py` | ✅ |
| `scripts/discovery/stage9c_linkedin_publish.py` | ✅ |
| `scripts/discovery/stageX_pipeline_dashboard.py` | ✅ |
| `scripts/discovery/stage0_load*.py` | ❌ NO EXISTE |
| `scripts/discovery/stage1_load_referentes.py` | ❌ NO EXISTE |
| `scripts/discovery/stage1_*.py` (cualquier variante) | ❌ NO EXISTE |

**Hallazgo principal:** el pipeline real arranca en `stage2_ingest.py`. No hay `stage0` ni `stage1` implementados. Todas las referencias a `stage1_load_referentes.py` en documentación o SKILLs son **aspiracionales**.

## 1. Tabla drift por stage

| Stage | Doc dice | Código real | Drift | Evidencia (ruta:línea) |
|---|---|---|---|---|
| **S0 — Leer catálogo Referentes** | "✅ runtime real" via `scripts/discovery/stage1_load_referentes.py` (audit 006) | Script no existe. La lectura de Referentes ocurre dentro de `stage2_ingest.py` (lectura directa de Notion DB Referentes). | **SÍ — falsa atribución** | `docs/plans/linkedin-publication-pipeline.md:241`; `openclaw/workspace-agent-overrides/rick-linkedin-writer/SKILL.md:31` |
| **S1 — Descubrir publicaciones nuevas por referente** | "⚠️ parcial (2/5 canales productivos)", cobertura 14/26 | Subsumido en `stage2_ingest.py` (canales LinkedIn activity, RSS, YouTube, Web). No hay un script `stage1_*` standalone. La doc trata S0+S1 como fases lógicas, no archivos. | **SÍ — naming gap**: docs hablan de "Etapa 1" pero código colapsa S0+S1 en S2. | `docs/plans/linkedin-publication-pipeline.md:241-244` vs `scripts/discovery/stage2_ingest.py` |
| **S2 — Ingest** | (no aparece como stage explícito en `linkedin-publication-pipeline.md`; doc usa "Etapa 1") | `stage2_ingest.py` ejecuta carga + descubrimiento + persistencia en SQLite (`~/.cache/rick-discovery/state.sqlite`). | **SÍ — gap de naming**: el código numera S2 lo que la doc llama "Etapa 1". | `scripts/discovery/stage2_ingest.py` (real) vs `docs/plans/linkedin-publication-pipeline.md` |
| **S3 — Promoción a candidato** | (parcial; mencionado como parte de Etapas 1-4) | `stage3_promote.py` setea `promovido_a_candidato_at` en SQLite. | NO drift sustantivo, sí **drift de naming** (doc no documenta S3 como stage propio). | `scripts/discovery/stage3_promote.py:1` (`"""Stage 3 — Promoción a candidatos (local, dry-run first)."""`) |
| **S4 — Push a Notion** | "Etapa 4 — push a Notion (Stage 4) ✅ runtime real" | `stage4_push_notion.py` real. | NO drift. | `scripts/discovery/stage4_push_notion.py`; `docs/plans/linkedin-publication-pipeline.md:241` (tabla 4.A) |
| **S5 — Ranking determinístico** | "Etapa 2 — ranking ✅ heurístico determinístico (Stage 5 v0)" | `stage5_rank_candidates.py` real. 10 tests verdes. | **SÍ — drift de naming**: doc llama "Etapa 2" a lo que el código numera "Stage 5". | `docs/plans/linkedin-publication-pipeline.md:241-244`; `scripts/discovery/stage5_rank_candidates.py` |
| **S6 — Combinación AEC** | "Etapa 3 — combinación AEC ⏸ stub" | Existen DOS scripts: `stage6_aec_combine.py` (stub `NotImplementedError`) y `stage6_llm_combinator.py` (real, con `Stage 6: LLM combinator for AEC editorial proposals.`). | **SÍ — duplicación**: dos archivos S6, doc menciona solo el stub. Falta clarificar cuál es canónico. | `scripts/discovery/stage6_aec_combine.py:1`; `scripts/discovery/stage6_llm_combinator.py:1` |
| **S7 — Publicaciones drafts (Notion)** | (no documentado como stage propio en master plan; tratado como parte de "Etapa 4") | `stage7_publish_drafts.py` (`Stage 7: write proposals as draft pages in the Notion 'Publicaciones' DB.`). | **SÍ — gap doc**: stage real sin doc explícita en `docs/plans/`. | `scripts/discovery/stage7_publish_drafts.py:1` |
| **S7.5 — Copy LinkedIn (LLM transformer)** | Documentado en `docs/discovery/stage7_5-runbook-real.md`, `docs/discovery/source-verification.md`, `docs/discovery/rick-linkedin-voice.md`, `docs/discovery/stage7_5-notion-ux.md` | `stage7_5_copy_writer.py` (FROZEN Ola 1) + `stage7_5_post_review_comment.py`. | NO drift sustantivo; sí **falta master-plan.md** que ate todos los docs S7.5 sueltos. | múltiples (ver `grep "Stage 7.5\|stage7_5" docs/`) |
| **S8 — Imagen hero** | "Etapa 9 — generación imagen Nano Banana 2 ⏸ futura" | `stage8_image_generator.py` real (`Stage 8: hero image generator for Publicaciones drafts.`). | **SÍ — falsa premisa**: master plan dice que S8/imagen es futura, pero el código ya tiene `stage8_image_generator.py`. | `scripts/discovery/stage8_image_generator.py:1`; `docs/plans/linkedin-publication-pipeline.md:241-244` |
| **S9 — LinkedIn draft** | "Etapa 8 — trigger imagen ⏸ decisión abierta" (no menciona S9 explícito) | `stage9_linkedin_draft.py` (`Stage 9: build LinkedIn draft payloads for approved Publicaciones pages.`). | **SÍ — gap doc**. | `scripts/discovery/stage9_linkedin_draft.py:1` |
| **S9b — OAuth** | (no documentado en master plan) | `stage9b_linkedin_oauth.py` (`Stage 9b: LinkedIn OAuth helper for Rick's editorial pipeline.`). | **SÍ — gap doc**. | `scripts/discovery/stage9b_linkedin_oauth.py:1` |
| **S9c — Publish (POST /v2/ugcPosts)** | (no documentado en master plan; estado declarado "publicación bloqueada") | `stage9c_linkedin_publish.py` (`Stage 9c: publish LinkedIn drafts (real POST /v2/ugcPosts).`). | **SÍ — gap doc crítico**: existe el script de publicación real, no aparece en el master plan. Restricción Ola 1: NO usar. | `scripts/discovery/stage9c_linkedin_publish.py:1` |
| **S10 — (no asignado)** | n/d | n/d | — | — |
| **S11 — (no asignado)** | n/d | n/d | — | — |
| **SX — Pipeline dashboard** | Documentado parcialmente en `docs/discovery/stage7_5-notion-ux.md:142` y `docs/discovery/stage7_5-runbook-real.md:117` | `stageX_pipeline_dashboard.py` real, escribe subpage "📊 Pipeline Editorial — Métricas". Cron en `scripts/vps/discovery-publish-cron.sh:125`. | NO drift sustantivo. Doc menciona, código ejecuta. | `scripts/discovery/stageX_pipeline_dashboard.py:37`; `scripts/vps/discovery-publish-cron.sh:125` |

### Resumen drift

- **Drifts confirmados:** 9 (S0, S1, S2, S5, S6, S7, S8, S9, S9b, S9c).
- **Drifts críticos (publicación):** S9c existe pero no está documentado en el master plan; riesgo de confusión sobre qué bloquea publicación.
- **Drifts de naming:** la doc usa "Etapa 0..9" mientras el código usa "Stage 2..9c+X". Solo S4 coincide en numeración.
- **Falsa atribución mayor:** `stage1_load_referentes.py` no existe.

## 2. Greps ejecutados

```bash
grep -rn "stage1_load_referentes\|stage0_load" docs/ openclaw/ scripts/
```

**2 matches (2 únicos relevantes):**
- `docs/plans/linkedin-publication-pipeline.md:241` — tabla 4.A asigna "✅ runtime real" a script inexistente.
- `openclaw/workspace-agent-overrides/rick-linkedin-writer/SKILL.md:31` — nota operativa cita 4 scripts como pre-paso, uno de los cuales (`stage1_load_referentes.py`) no existe.

```bash
grep -rn "Stage 7.5\|stage7_5" docs/
```

**~40 matches (todas relevantes, en 5 docs distintos):**
- `docs/discovery/stage7_5-notion-ux.md` (Notion UX scaffolding, dashboard, post review comment)
- `docs/discovery/rick-linkedin-voice.md` (voice spec, integración con `stage7_5_copy_writer.py`)
- `docs/discovery/source-verification.md` (gate pre-LLM, hooks, ops_log events)
- `docs/discovery/stage7_5-runbook-real.md` (procedimiento end-to-end)
- (sin doc en `docs/plans/` que ate todo)

**Hallazgo:** S7.5 está bien documentado pero fragmentado. El master plan lo subsume bajo "Etapa 6 — voice pass / copy LinkedIn ⏸ no implementado", lo cual es **falso** (está implementado y FROZEN para Ola 1).

```bash
grep -rn "CAND-002\|CAND-003\|CAND-004" docs/ openclaw/ scripts/ tests/
```

**~25 matches (3 únicos relevantes):**
- `docs/plans/linkedin-publication-pipeline.md` líneas 24, 205, 392, 454 — uso de CAND-002/003 como referencia histórica de calibración del redactor; CAND-004 mencionado como layout futuro deseado.
- `docs/ops/cand-002-payload.md`, `docs/ops/cand-003-payload.md`, `docs/ops/cand-003-source-intake.md`, `docs/ops/cand-003-rick-qa-postchange-request.md`, `docs/ops/cand-003-communication-director-v2.md`, `docs/ops/cand-003-notion-draft-result.md` — artefactos históricos.
- `docs/ops/editorial-agent-flow.md:82` — ejemplo "For CAND-003".

**Restricción Ola 1:** no tratar CAND-002/003/004 como fixtures canónicos. Son artefactos históricos de calibración manual previos al runtime real.

```bash
grep -rn "Pipeline Editorial — Métricas\|stageX_pipeline_dashboard" docs/ scripts/
```

**5 matches (5 únicos relevantes):**
- `docs/discovery/stage7_5-notion-ux.md:142` — descripción del dashboard.
- `docs/discovery/stage7_5-runbook-real.md:117` — invocación CLI.
- `scripts/vps/discovery-publish-cron.sh:125` — invocación desde cron.
- `scripts/discovery/stageX_pipeline_dashboard.py:10` — usage banner.
- `scripts/discovery/stageX_pipeline_dashboard.py:37` — `DEFAULT_SUBPAGE_TITLE = "📊 Pipeline Editorial — Métricas"`.

**Hallazgo:** dashboard existe, escribe subpage real bajo Control Room. Sin drift.

```bash
grep -rn "Sistema Editorial Rick\|📰 Publicaciones" docs/
```

**~20 matches (relevantes):**
- Hub principal Notion: `Sistema Editorial Rick` (`5894ba35...`) — documentado en múltiples runbooks/specs.
- Página técnica OpenClaw: `Sistema Editorial Rick` (`31e5f443...`).
- DB `📰 Publicaciones` (`e6817ec4698a4f0fbbc8fedcf4e52472`) — 26 propiedades schema + 19 extras (auditoría 2026-04-22).
- ADR-011 (`docs/adr/ADR-011-orquestacion-editorial-criterios-duros.md:11,23`) cita Sistema Editorial Rick.
- Spec v1 (`docs/specs/sistema-editorial-rick-v1.md:1`).
- Roadmap (`docs/roadmaps/2026-04-capitalizacion-perplexity-rick-umbral-bot.md:407`).

**Restricción Ola 1:** no duplicar `📰 Publicaciones`. La DB ya existe, está auditada, conectada.

## 3. Implicaciones para Hilos posteriores

- **Hilo 2 (stage1-discovery-spec.md):** debe definir el contrato S0/S1 que actualmente está colapsado en `stage2_ingest.py`. Decidir: ¿se sigue colapsando o se rompe en scripts separados? Hilo 2 NO toca `stage7_5_*.py` (FROZEN).
- **Hilo 4 (notion-schema.md):** debe documentar el schema real de las 45 propiedades en `📰 Publicaciones` (26 canon + 19 extras), y aclarar el rol de las 10 columnas de canales en `👤 Referentes` (carga 2026-05-05). NO crear DBs nuevas.
- **Hilo de publicación (futuro):** debe abordar S9c. Hoy existe el script real `stage9c_linkedin_publish.py`. Está prohibido invocarlo en Ola 1.
- **Hilo de S6:** dirimir la duplicación `stage6_aec_combine.py` (stub) vs `stage6_llm_combinator.py` (real).

## 4. Verificaciones

- `git diff main scripts/` → vacío (este audit no toca código). ✅
- Cada script citado en la tabla §1 fue verificado con `ls scripts/discovery/`.
- Cada `ruta:línea` fue obtenida con `grep -n` sobre el árbol actual de `main` (commit `4e07866` aprox., post-merge Stage 5/6).

## 5. Bloqueos

- **Source draft `.cache/quality-review/draft-master-plan.md` no existe en VPS** (ni en stash ni en historia git). El master plan promovido se reconstruyó desde código real + esta auditoría, marcado `status: BORRADOR-RECONSTRUIDO`. Las §3.5/§4.5/§7/§8 originales del draft NO se pudieron preservar intactas porque no estaban accesibles. Al volver el draft, hacer diff y reconciliar.
