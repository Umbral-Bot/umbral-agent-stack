# Master Plan — Pipeline Editorial Umbral

> **version:** v1.0-draft
> **date:** 2026-05-08
> **status:** PROPUESTO — pendiente revisión humana
> **estado de fuente:** ⚠️ BORRADOR-RECONSTRUIDO — el draft original aprobado (`.cache/quality-review/draft-master-plan.md`) no estaba presente en la VPS al momento de promover. Esta versión fue reconstruida desde la auditoría drift real (`docs/audits/2026-05-08-editorial-drift-audit.md`) + código real en `main`. Al recuperar el draft fuente, hacer diff y reconciliar, manteniendo las decisiones §7 abiertas hasta revisión humana explícita.
> **owners:** `rick-orchestrator` (handoffs), `rick-linkedin-writer` (transformación), David (gates).
> **scope:** spec canónica end-to-end del pipeline editorial (descubrimiento → ranking → combinación AEC → copy LinkedIn → review → publicación → dashboard).
> **non-scope:** generación visual Nano Banana 2 (futura), canales no-LinkedIn (otro hilo).

## 0. Restricciones duras Ola 1

- No publicar a ninguna plataforma.
- No marcar `aprobado_contenido` ni `autorizar_publicacion` (ni en test ni real).
- No crear DBs ni páginas Notion nuevas.
- No duplicar `📰 Publicaciones`.
- No tratar CAND-002/003/004 como fixtures canónicos.
- No modificar `scripts/discovery/stage7_5_*.py` (FROZEN).
- No mergear a `main`. Todo en branches y PR draft con label `do-not-merge`.
- Tests obligatorios cuando se toca código.
- Cero llamadas HTTP reales a LinkedIn en tests.

## 1. Stages canónicos

> Numeración basada en código real (`scripts/discovery/stage*.py`). La doc histórica (`docs/plans/linkedin-publication-pipeline.md`) usa "Etapa 0..9" — equivalencias en columna *alias doc*.

| Stage | Alias doc | Script | Estado | Output |
|---|---|---|---|---|
| **S0** | Etapa 0 | (subsumido en S2) | colapsado | — |
| **S1** | Etapa 1 | (subsumido en S2; ver Hilo 2) | colapsado | — |
| **S2** | (parte de "Etapa 1") | `scripts/discovery/stage2_ingest.py` | ✅ runtime real | items en SQLite `~/.cache/rick-discovery/state.sqlite` |
| **S3** | (parte de "Etapa 1") | `scripts/discovery/stage3_promote.py` | ✅ runtime real | `promovido_a_candidato_at` set |
| **S4** | Etapa 4 | `scripts/discovery/stage4_push_notion.py` | ✅ runtime real | páginas en `📰 Publicaciones` |
| **S5** | Etapa 2 | `scripts/discovery/stage5_rank_candidates.py` | ✅ heurístico determinístico v0 | score [0,1] por candidato |
| **S6** | Etapa 3 | `scripts/discovery/stage6_aec_combine.py` (stub) y `scripts/discovery/stage6_llm_combinator.py` | ⚠️ duplicado, stub + real | propuestas combinadas |
| **S7** | (no doc) | `scripts/discovery/stage7_publish_drafts.py` | ✅ runtime real | drafts en `📰 Publicaciones` |
| **S7.5** | Etapa 6 (voice pass) | `scripts/discovery/stage7_5_copy_writer.py` (FROZEN) + `stage7_5_post_review_comment.py` | ✅ runtime real (FROZEN Ola 1) | `Copy LinkedIn` rich_text + `Estado=Revisión pendiente` + review comment |
| **S8** | Etapa 9 | `scripts/discovery/stage8_image_generator.py` | ⚠️ existe (no aspiracional) | hero image |
| **S9** | (no doc) | `scripts/discovery/stage9_linkedin_draft.py` | existe | draft payload LinkedIn |
| **S9b** | (no doc) | `scripts/discovery/stage9b_linkedin_oauth.py` | existe | OAuth token cache |
| **S9c** | (no doc) | `scripts/discovery/stage9c_linkedin_publish.py` | ⛔ existe pero **PROHIBIDO Ola 1** | POST /v2/ugcPosts |
| **SX** | (transversal) | `scripts/discovery/stageX_pipeline_dashboard.py` | ✅ runtime real | subpage Notion `📊 Pipeline Editorial — Métricas` |

> Drift detallado: ver [`docs/audits/2026-05-08-editorial-drift-audit.md`](../audits/2026-05-08-editorial-drift-audit.md).

## 2. Flujo end-to-end

```
S2 ingest → S3 promote (SQLite) → S4 push → S5 rank → S6 combine (stub/LLM)
        → S7 drafts (Notion) → S7.5 copy LinkedIn (FROZEN) → S8 image
        → S9 draft payload → [GATE humano David] → S9b OAuth → S9c publish [PROHIBIDO Ola 1]
                                                                              ↑
                                                                  SX dashboard (transversal)
```

### Gates humanos

1. **Pre-S7.5:** `Estado=Revisión pendiente` activado por S7.5 → David revisa `Copy LinkedIn`.
2. **Pre-S9c:** `Estado=Aprobado` (no implementado en Ola 1; ver §7 decisión 3).
3. **Pre-publish:** `aprobado_contenido=True` AND `autorizar_publicacion=True` (ambos PROHIBIDOS Ola 1).

## 3. Superficies Notion (canónicas — NO crear nuevas en Ola 1)

| Superficie | ID | Rol | Acceso |
|---|---|---|---|
| `Sistema Editorial Rick` (hub) | `5894ba351e2749729077ca971fd9f52a` | Hub operativo | lectura/escritura via integración Rick |
| `Sistema Editorial Rick` (OpenClaw) | `31e5f443fb5c8180bec7cbcda641b3b7` | Proyecto técnico | lectura/escritura via integración Rick |
| DB `📰 Publicaciones` | `e6817ec4698a4f0fbbc8fedcf4e52472` | Candidatos editoriales | escritura via S4/S7/S7.5 |
| DB `👤 Referentes` | (data source `afc8d960-086c-4878-b562-7511dd02ff76`) | Catálogo de referentes | lectura por S2 |
| Subpage `📊 Pipeline Editorial — Métricas` | (bajo Control Room) | Dashboard | escritura por SX |

### 3.5. Reconciliación Notion

> ⚠️ **BLOQUEO DE FUENTE:** esta sección estaba marcada como "intacta del draft" en el contrato del Hilo 1, pero el draft fuente no existe en VPS. Lo siguiente es **placeholder reconstruido** desde runbooks (`docs/ops/notion-publicaciones-*`) y debe revisarse contra el draft original cuando se recupere.

- DB `📰 Publicaciones` tiene 45 propiedades reales = 26 schema canónico + 19 extras (audit 2026-04-22).
- DB `👤 Referentes` extendida 2026-05-05 con 10 columnas de canales (cobertura 14/26 = 53.8%).
- No re-crear superficies. No duplicar.
- TODO Hilo 4 (`docs/editorial-pipeline/notion-schema.md`): documentar las 45 propiedades + 10 columnas con tipo, owner, escritor autorizado y semántica por stage.

## 4. Artefactos por stage

- **S2/S3:** SQLite local `~/.cache/rick-discovery/state.sqlite`.
- **S4:** páginas en `📰 Publicaciones` con `Estado=Borrador`.
- **S5:** columna `score_ranking` (decimal [0,1]).
- **S6:** propuesta combinada (texto + trazabilidad referencias).
- **S7.5:** `Copy LinkedIn` (rich_text), `Estado=Revisión pendiente`, comentario `🟡 Revisión pendiente` con preview.
- **S8:** asset visual + URL hero.
- **S9:** payload JSON LinkedIn (sin POST).
- **S9c:** [PROHIBIDO Ola 1].
- **SX:** subpage Notion con métricas + ops_log JSONL.

### 4.5. Artefactos históricos (no-canónicos)

> ⚠️ **BLOQUEO DE FUENTE:** sección reconstruida.

- CAND-001/002/003/004 son artefactos de **calibración manual previos al runtime**. NO son fixtures canónicos. NO usarlos como ground truth para tests.
- Documentos en `docs/ops/cand-00*-*.md` son histórico, no spec.
- Layout "tipo CAND-004" es referencia visual aspiracional, no contrato.

## 5. Configuración (`config/`)

- `config/aec_keywords.yaml` — keywords core/adjacentes para S5.
- `config/source_verifier.yaml` — gates source verification S7.5 pre-LLM.
- (otras: ver `config/`)

## 6. Tests obligatorios al tocar código

- Stage que cambia → test correspondiente en `tests/discovery/test_stage*.py`.
- Cero llamadas HTTP reales a LinkedIn (mock obligatorio).
- Stage 7.5: FROZEN — no tocar.

## 7. Decisiones pendientes (5 ABIERTAS — no resolver unilateralmente)

> Estas decisiones afectan diseño y deben ser resueltas por David en revisión humana. Hilo 1 NO las resuelve.

1. **D1 — Romper o mantener colapso S0+S1 dentro de S2.** Hoy `stage2_ingest.py` hace S0 (lectura Referentes) + S1 (descubrimiento publicaciones) + persistencia en SQLite en un solo script. ¿Se rompe en `stage1_discover_publications.py` separado para testabilidad y cobertura por canal, o se mantiene? **Owner decisión:** David. **Handoff:** Hilo 2.
2. **D2 — Canónico de S6.** Existen `stage6_aec_combine.py` (stub) y `stage6_llm_combinator.py` (real). ¿Cuál es canónico? ¿Se renombra el stub para evitar confusión? ¿Se elimina? **Owner decisión:** David. **Handoff:** futuro hilo S6.
3. **D3 — Gate de aprobación pre-S9c.** Hoy no hay un mecanismo formal "Aprobado → puede publicar". `Estado=Revisión pendiente` permite review pero no marca aprobación. ¿Se añade `Estado=Aprobado` + `aprobado_contenido` + `autorizar_publicacion` (con doble confirmación)? **Owner decisión:** David. **Handoff:** futuro hilo de publicación.
4. **D4 — Naming canónico.** Doc histórica usa "Etapa 0..9", código usa "Stage 2..9c+X". ¿Migramos doc al naming código (Stage N) o viceversa? Decidir antes de cualquier nuevo doc. **Owner decisión:** David. **Handoff:** transversal.
5. **D5 — Política de imagen S8.** Hoy `stage8_image_generator.py` existe pero el master plan histórico declara la imagen como "futura". ¿Es producción real o experimento? ¿Cuándo dispara? ¿Pre-review o post-review? **Owner decisión:** David. **Handoff:** futuro hilo S8.

## 8. Anti-patterns observados (NO REPETIR)

> ⚠️ **BLOQUEO DE FUENTE:** sección reconstruida desde drift audit. Ampliar al recuperar draft.

1. **Falsa atribución de runtime.** Documentar un script como "✅ runtime real" cuando el archivo no existe (caso `stage1_load_referentes.py`).
2. **Drift de naming sin reconciliar.** Doc usa "Etapa N", código usa "Stage M", sin tabla de equivalencia → confusión sistémica.
3. **Duplicación de stages sin marcar canónico.** S6 tiene dos archivos sin que la doc indique cuál vale.
4. **Tratar artefactos históricos (CAND-002/003/004) como fixtures.** Son calibración manual, no spec.
5. **Documentar publicación (S9c) como "futura" cuando el script ya existe y posteo real es técnicamente posible.** Riesgo de bypass accidental del gate.
6. **Crear nuevas DBs Notion en lugar de reutilizar `📰 Publicaciones`.** Regla dura Ola 1: NO crear superficies.
7. **Tocar `stage7_5_*.py` durante Ola 1.** FROZEN.

## 9. Handoffs a otros hilos

- **Hilo 2 — Stage 1 Discovery Spec.** Stub: [`docs/editorial-pipeline/stage1-discovery-spec.md`](./stage1-discovery-spec.md). Decidir D1.
- **Hilo 4 — Notion Schema.** Stub: [`docs/editorial-pipeline/notion-schema.md`](./notion-schema.md). Documentar 45 props `📰 Publicaciones` + 10 cols canales `👤 Referentes`.
- **Hilo S6 (futuro):** decidir D2.
- **Hilo Publicación (futuro):** decidir D3.

## 10. Referencias

- Drift audit: [`docs/audits/2026-05-08-editorial-drift-audit.md`](../audits/2026-05-08-editorial-drift-audit.md).
- Doc canal LinkedIn (con banner cross-ref): [`docs/plans/linkedin-publication-pipeline.md`](../plans/linkedin-publication-pipeline.md).
- Stage 7.5 docs: `docs/discovery/stage7_5-runbook-real.md`, `docs/discovery/source-verification.md`, `docs/discovery/rick-linkedin-voice.md`, `docs/discovery/stage7_5-notion-ux.md`.
- ADR-011 orquestación editorial: `docs/adr/ADR-011-orquestacion-editorial-criterios-duros.md`.
- Spec v1: `docs/specs/sistema-editorial-rick-v1.md`.
- Notion runbook: `docs/ops/notion-publicaciones-setup-runbook.md`.
