# Editorial Stack — Final Readiness QA

**Date**: 2026-04-22
**Scope**: PRs #249, #253, #254, #255, #256 (plus superseded #250, #251, #252)
**Type**: Static audit + merge simulation. No runtime, no Notion, no publishing.

---

## 1. Resumen ejecutivo

**Veredicto: READY TO MERGE**

No technical blockers. All 4 main PRs merge cleanly in sequence with zero conflicts. 205 tests pass. Both validation scripts pass. All human decisions are correctly encoded.

**Orden final recomendado**:
1. **#253** (gold set) — pure new files, zero overlap
2. **#254** (Notion schema) — pure new files, zero overlap
3. **#249** (editorial spec/ADRs/roadmaps) — docs only, no code conflict
4. **#256** (OpsLogger integration) — supersedes #250, #251, #252

**PRs to close after merge**:
- **#250** (structured error classification) — superseded by #256
- **#251** (auth lifecycle tracking) — superseded by #256
- **#252** (publish tracking events) — superseded by #256
- **#255** (coordination QA audit) — close as historical reference or leave open

---

## 2. PRs auditados

| PR | Branch | Objetivo | Estado | Draft | Archivos principales |
|----|--------|----------|--------|-------|---------------------|
| #249 | `codex/editorial-research-capitalization` | Spec editorial v1, ADRs, roadmaps | OPEN | Draft | `docs/specs/`, `docs/adr/`, `docs/roadmaps/`, `docs/research/` |
| #253 | `codex/editorial-gold-set-minimum` | Gold set editorial (10 cases, 12 dims) | OPEN | Draft | `evals/editorial/`, `infra/editorial_gold_set.py`, `tests/`, `scripts/`, `docs/evals/` |
| #254 | `codex/notion-publicaciones-schema-spec` | Notion Publicaciones DB schema YAML | OPEN | Draft | `notion/schemas/`, `infra/notion_schema.py`, `tests/`, `scripts/`, `docs/specs/` |
| #255 | `codex/editorial-pr-stack-coordination-qa` | Prior coordination audit | OPEN | Draft | `docs/audits/` |
| #256 | `codex/ops-logger-observability-integration` | OpsLogger integration (#250+#251+#252) | OPEN | Draft | `infra/ops_logger.py`, `infra/error_classification.py`, `infra/auth_lifecycle.py`, `infra/publish_tracking.py`, `worker/`, `dispatcher/`, `tests/`, `scripts/`, `docs/ops/`, `config/` |

---

## 3. Decisiones verificadas

| Decision | Verified | Where |
|----------|----------|-------|
| Ghost blog v1 | YES | #249 ADR-005, spec §8.1 |
| Single DB `Publicaciones` | YES | #249 spec §5 "Decisión de modelo de datos v1", #254 schema |
| No `Variantes` v1 | YES | #249 spec line 88: "alternativa v1.1/v2" |
| No `Assets Visuales Rick` v1 | YES | #249 spec line 89, #254 invariant `no_separate_assets_db_v1` |
| No `PublicationLog` v1 | YES | #249 spec line 90, §5.3, ADR-007 |
| Newsletter prepared, not v1 priority | YES | #249 spec line 91, #254 canal includes `newsletter`, #253 has no newsletter cases |
| HITL LinkedIn/X | YES | #249 ADR-005, spec §8.2/8.3, #254 invariant `linkedin_x_require_hitl` |
| Referentes = discovery_signal | YES | #249 roadmap §8.5, #254 invariant `referente_is_discovery_not_source`, #253 case ED-GOLD-002 |
| API-first visual | YES | #249 ADR-006, spec §9.1 (UA-13), #253 cases ED-GOLD-007/008 |
| n8n edge + Agent Stack core | YES | #249 ADR-008, roadmap §2 decision #16, #253 case ED-GOLD-009 |
| `content_hash` for idempotency | YES | #249 spec §5.1, #254 property `content_hash` |
| Two human gates | YES | #249 spec §6, #254 properties `aprobado_contenido` + `autorizar_publicacion`, #253 all cases `human_gate_required: true` |

---

## 4. Consistencia cruzada

### PR #249 vs #254 — Property naming divergences

This is the most significant cross-PR finding. Both PRs design the same DB but use different naming conventions:

| Concept | #249 (code-facing spec) | #254 (Notion-facing schema) | Assessment |
|---------|------------------------|----------------------------|------------|
| Title | `Title` | `Título` | #254 is Notion-native (Spanish) |
| Canal | `Canal primario` (Select) + `Canales secundarios` (Multi-select) | `Canal` (single Select per variante row) | **Design divergence** — different data models |
| Status | `Status` (English: draft, ready_for_review, content_approved...) | `Estado` (Spanish: Idea, Borrador, Revisión pendiente...) | **Naming divergence** — same lifecycle, different labels |
| Content type | `Tipo pieza` (10 options) | `Tipo de contenido` (7 options) | Minor naming + option count divergence |
| Audience | `Audience stage` | `Etapa audiencia` | Language divergence |
| Content body | `Content markdown` (included) | Not included | #254 intentionally omits (content in page body) |
| Gate timestamps | `Content approved at`, `Publish authorized at` | Not included | #254 omits; could be added later |
| Copies per channel | Properties: `Copy LinkedIn`, `Copy X`, etc. | Self-relation via `Publicación padre` | **Design divergence** |
| Visual assets | `Featured image URL`, `Featured image alt` | `Visual brief`, `Visual asset URL`, `visual_hitl_required` | Different field names, #254 richer |
| Gate invalidation | Described in §6 rules | `gate_invalidado` checkbox | #254 adds explicit tracking field |

**Assessment**: These divergences are **not blockers**. #249 is a proposal/spec document; #254 is the authoritative Notion schema. When implementation code is written, it should follow #254's property names and add a mapping layer if #249's code-facing names are preferred. The data model divergence (single-row vs variante-per-row) is documented in QA #255 as a human decision item — David chose single DB with inline variantes.

### PR #249 vs #253

Consistent. The gold set covers all channels from the spec (linkedin, blog, x). Gate semantics (`aprobado_contenido`, `autorizar_publicacion`) match. CTA dimensions in #253 align with CTA rules in #249 §10. Referente handling (discovery, not source) is consistent.

### PR #249 vs #256

Consistent. The spec's failure modes (§12) describe auth expiry and publish errors that are now tracked by #256's `auth_lifecycle_check()` and `publish_attempt/success/failed()`. The publish tracking accepts `error_kind`, `error_code`, `retryable`, `provider` — compatible with structured error classification.

### PR #253 vs #254

Consistent. Gold set channels (linkedin, blog, x) are a subset of schema channels (adds newsletter). Gate property names match: `aprobado_contenido`, `autorizar_publicacion`. Gold set case ED-GOLD-010 tests the same gate invalidation behavior encoded in #254's `gate_invalidation_on_comment` invariant.

### PR #254 vs #256

No direct dependency. #254 defines the Notion schema; #256 defines OpsLogger events. The `content_hash` field in #254 is the same concept used by `publish_tracking.py`'s `compute_content_hash()` in #256. The `idempotency_key` derivation in #256 uses `channel + content_hash + page_id`, consistent with #254's field definition.

---

## 5. Conflictos de merge

### Individual PR merges (against main)

| PR | Conflicts | Notes |
|----|-----------|-------|
| #253 | None | Pure new `evals/` directory + new files |
| #254 | None | Pure new `notion/schemas/` directory + new files |
| #249 | None | Pure docs additions/modifications |
| #256 | None | Already resolved internally (integrated #250+#251+#252) |

### Cumulative merge simulation (#253 → #254 → #249 → #256)

**Zero conflicts.** All 4 PRs merged cleanly in sequence on temporary branch `tmp/full-editorial-stack-merge-sim`. Tested and validated. Branch deleted after verification.

---

## 6. Tests y validaciones

### Test suite on merged simulation

```
.venv/bin/python -m pytest tests/test_editorial_gold_set.py \
  tests/test_notion_publicaciones_schema.py tests/test_ops_logger.py \
  tests/test_dashboard.py tests/test_error_classification.py \
  tests/test_auth_lifecycle.py tests/test_auth_lifecycle_check.py \
  tests/test_publish_tracking.py -q
```

**Result: 205 passed in 10.22s**

### Validation scripts

```
PYTHONPATH=. .venv/bin/python scripts/validate_editorial_gold_set.py
```
```
Gold set: evals/editorial/gold-set-minimum.yaml
  Cases: 10
  Channels: blog, linkedin, x
  Input types: cta_variant, news_reactive, raw_idea, reference_post, source_signal, technical_explainer
  Audience stages: awareness, consideration, trust
  Dimensions used: 12
  All have human gate: True
Validation passed.
```

```
PYTHONPATH=. .venv/bin/python scripts/validate_notion_schema.py
```
```
Schema: notion/schemas/publicaciones.schema.yaml
  Database: Publicaciones v0.1.0 (draft)
  Properties: 26 (7 required)
  Channels: blog, linkedin, x, newsletter
  Statuses: Idea, Borrador, Revisión pendiente, Aprobado, Autorizado, Publicando, Publicado, Descartado
  Transitions: 11
  Invariants: 7
  Recommended views: 5
Validation passed.
```

### Pre-existing failures (not related)

21 failures in `tests/test_worker.py` — all 401 auth token errors. These exist identically on `main` and are caused by auth token env mismatch on the VPS. Not related to any editorial/observability PR.

---

## 7. Blockers

**No hay blockers técnicos detectados.**

All PRs merge cleanly. All tests pass. All validation scripts pass. All human decisions are correctly encoded. No secrets, no runtime activation, no external API calls.

---

## 8. Warnings

| # | Warning | Severity | Action |
|---|---------|----------|--------|
| W1 | Property naming divergence between #249 and #254 (Status/Estado, Canal primario/Canal, etc.) | Low | Document mapping when implementation code is written. Not a merge blocker. |
| W2 | #249 includes `Content markdown` property; #254 intentionally omits it | Low | Acknowledged design choice. Content lives in page body per #254. |
| W3 | #249 includes gate timestamps (`Content approved at`, `Publish authorized at`); #254 doesn't | Low | Can be added to #254 schema later if needed. |
| W4 | #249 uses `Canal primario` + `Canales secundarios`; #254 uses single `Canal` per row | Medium | This is the row-model divergence. David chose single DB. Future code follows #254. |
| W5 | `test_worker.py` has 21 pre-existing auth failures on main | Low | Not related to these PRs. Needs separate fix. |
| W6 | #254 has `Tipo de contenido` with 7 options; #249 has `Tipo pieza` with 10 options | Low | Reconcile when DB is created in Notion. |

---

## 9. Orden final de merge recomendado

| Step | PR | Title | Rationale |
|------|----|-------|-----------|
| 1 | **#253** | evals: editorial gold set minimum | Pure new files, zero overlap with anything |
| 2 | **#254** | specs: Notion Publicaciones schema spec | Pure new files, zero overlap |
| 3 | **#249** | docs: editorial research capitalization | Docs only, adds specs/ADRs/roadmaps |
| 4 | **#256** | observability: integrate OpsLogger extensions | Code changes in `infra/`, `worker/`, `dispatcher/` |

**After merge**:
- Close **#250** as superseded by #256
- Close **#251** as superseded by #256
- Close **#252** as superseded by #256
- Close **#255** as historical audit (findings incorporated into this report)

---

## 10. Acciones siguientes

1. **Merge PRs in order** (#253 → #254 → #249 → #256). All merge cleanly.
2. **Close superseded PRs** (#250, #251, #252) with comment referencing #256.
3. **Close audit PRs** (#255, this QA) as historical documentation.
4. **Reconcile property names** (#249 vs #254) when writing implementation code. Create a mapping document or constants file.
5. **Fix `test_worker.py` auth failures** on main — separate issue, not blocking editorial stack.
6. **Decide on `Tipo de contenido` options** — #249 has 10, #254 has 7. Align before creating Notion DB.
7. **Optionally add gate timestamps** to #254 schema (`Content approved at`, `Publish authorized at`) before creating Notion DB.
