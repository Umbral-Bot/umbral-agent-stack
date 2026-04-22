# Editorial PR Stack Coordination QA

**Date**: 2026-04-21
**Scope**: PRs #249 – #254
**Type**: Static audit — no runtime, no merges, no PR modifications

---

## 1. PRs Under Audit

| PR   | Branch                                    | Title                                      | Status  |
|------|-------------------------------------------|--------------------------------------------|---------|
| #249 | `codex/editorial-pipeline-spec`           | docs: editorial pipeline specification     | Open    |
| #250 | `codex/structured-error-classification`   | feat: structured error classification      | Open    |
| #251 | `codex/auth-lifecycle-check`              | feat: auth lifecycle check                 | Open    |
| #252 | `codex/publish-tracking-events`           | feat: publish attempt/success/failed tracking | Merged |
| #253 | `codex/editorial-gold-set-minimum`        | evals: editorial gold set minimum          | Open    |
| #254 | `codex/notion-publicaciones-schema-spec`  | docs: Notion Publicaciones schema spec     | Open    |

**Note**: PR #250 branch (`codex/structured-error-classification`) does not exist locally and could not be inspected at code level. Findings for #250 are limited to its GitHub PR metadata.

---

## 2. File Overlap & Merge Conflict Risk

### Guaranteed conflict: `infra/ops_logger.py`

PRs #251 and #252 both insert new methods at the **exact same location** — after `notion_operation()` (line ~562), before `read_events()`.

- **#251** adds `auth_lifecycle_check()` method
- **#252** adds `_build_publish_event()` + `publish_attempt()` / `publish_success()` / `publish_failed()`

The methods are functionally independent. The conflict is purely textual — whoever merges second resolves by keeping both blocks.

### No other file overlaps detected

| PR   | Files touched (new or modified)                              |
|------|--------------------------------------------------------------|
| #249 | `docs/specs/editorial-pipeline.md` (docs only)              |
| #250 | Unknown (branch not available locally)                       |
| #251 | `infra/ops_logger.py`, `infra/auth_lifecycle.py`, tests     |
| #252 | `infra/ops_logger.py`, `infra/publish_tracking.py`, tests, scripts, docs |
| #253 | `evals/editorial/` (new dir), `infra/editorial_gold_set.py`, tests, scripts, docs |
| #254 | `notion/schemas/` (new dir), `infra/notion_schema.py`, tests, scripts, docs |

PRs #253 and #254 create entirely new directories and have zero overlap with any other PR.

---

## 3. Naming & Enum Coherence

### Channel naming

| Module                        | Channels                                          |
|-------------------------------|---------------------------------------------------|
| `infra/publish_tracking.py` (#252) | `ghost`, `linkedin`, `x`, `manual`, `unknown`    |
| `evals/editorial/gold-set-minimum.yaml` (#253) | `linkedin`, `blog`, `x`                |
| `notion/schemas/publicaciones.schema.yaml` (#254) | `blog`, `linkedin`, `x`, `newsletter` |
| `docs/specs/editorial-pipeline.md` (#249) | `linkedin`, `blog`, `x`                    |

**Divergences**:
- `ghost` (#252) vs `blog` (#253, #254, #249): These may refer to the same channel (Ghost is the blog platform). Needs alignment — recommend `blog` as the canonical name with `ghost` as an implementation alias.
- `newsletter` appears only in #254. Per human decision: newsletter is an allowed channel but NOT v1 priority. Acceptable as-is.
- `manual` and `unknown` exist only in #252 (runtime fallback values). Acceptable.

### Status / state naming

| Source | Statuses |
|--------|----------|
| #249 (pipeline spec) | `draft`, `ready_for_review`, `content_approved`, `publish_authorized`, `scheduled`, `published`, `archived` |
| #254 (Notion schema) | `Idea`, `Borrador`, `Revisión pendiente`, `Aprobado`, `Autorizado`, `Publicando`, `Publicado`, `Descartado` |

**Major divergence**: #249 uses English-developer names; #254 uses Spanish-Notion names. These are two different naming conventions for the same lifecycle.

**Recommendation**: #254 is the Notion-facing truth (David sees Spanish). #249 is the code-facing spec. Both are valid for their audience. The future `infra/` code should map between them. No immediate fix required, but document the mapping.

| #249 (code)            | #254 (Notion)          |
|------------------------|------------------------|
| `draft`                | `Borrador`             |
| `ready_for_review`     | `Revisión pendiente`   |
| `content_approved`     | `Aprobado`             |
| `publish_authorized`   | `Autorizado`           |
| `scheduled`            | `Publicando`           |
| `published`            | `Publicado`            |
| `archived`             | `Descartado`           |
| —                      | `Idea` (no #249 equiv) |

Note: #249 has no `Idea` state. #254 has no `archived` state (uses `Descartado` which is closer to "discarded").

### Property naming

| Concept               | #249                                         | #254                          |
|-----------------------|----------------------------------------------|-------------------------------|
| Channel field         | `Canal primario` (select) + `Canales secundarios` (multi-select) | `Canal` (single select per row) |
| Content body          | `Content markdown` (as page body)            | Omitted intentionally         |
| Platform copies       | `Copy LinkedIn`, `Copy Blog title`, etc.     | Uses `Publicación padre` self-relation for variantes |
| Gate timestamps       | `Content approved at`, `Publish authorized at` | Not included                |
| Gate invalidation     | Not explicit                                 | `gate_invalidado` (checkbox)  |

**Key design divergence**: #249 models one row per content piece with multiple channel copies inline. #254 models one row per channel variante with a parent relation. These are architecturally different approaches. **Human decision required** before both can coexist.

---

## 4. Semantic Contradictions

### 4a. Single-row vs variante-per-row

- **#249**: One `Publicaciones` row = one content piece. Channels are properties (`Canal primario`, `Canales secundarios`). Platform-specific copies live as inline properties.
- **#254**: One `Publicaciones` row = one channel variante. Multi-channel content uses `Publicación padre` self-relation to link variantes back to a parent row.

These are **mutually exclusive** designs for the same database. Must resolve before implementing.

### 4b. Content body storage

- **#249** includes `Content markdown` as a property / page body.
- **#254** intentionally omits content body from the schema (content lives elsewhere or in page body outside the properties).

Not a hard contradiction — #254's approach is simpler and avoids syncing issues.

### 4c. No contradictions found in

- Gate semantics: both agree on `aprobado_contenido` + `autorizar_publicacion` as human gates.
- Referente handling: #253 case ED-GOLD-002 and #254 invariant `referente_is_discovery_not_source` are aligned.
- Visual HITL: #253 cases ED-GOLD-007/008 and #254 invariant `linkedin_x_require_hitl` are aligned.
- No separate Assets DB in v1: both #249 and #254 agree.

---

## 5. Dependency Graph

```
#253 (gold set)  ──────────────── independent
#254 (schema)    ──────────────── independent
#249 (pipeline spec) ──────────── independent (docs only)
#250 (error classification) ───── unknown deps (branch unavailable)
#251 (auth lifecycle) ─────┐
                           ├──── conflict on infra/ops_logger.py
#252 (publish tracking) ───┘
```

No PR depends on another PR's code to compile or pass tests. The only coupling is the textual merge conflict between #251 and #252.

---

## 6. Test Isolation

| PR   | Test file                                  | Count | External deps |
|------|--------------------------------------------|-------|---------------|
| #251 | `tests/test_auth_lifecycle.py`             | ~20   | None          |
| #252 | `tests/test_publish_tracking.py`           | 41    | None (tmp_path for OpsLogger) |
| #253 | `tests/test_editorial_gold_set.py`         | 27    | None (reads YAML/JSON from evals/) |
| #254 | `tests/test_notion_publicaciones_schema.py`| 45    | None (reads YAML from notion/schemas/) |

All test suites are self-contained. No shared fixtures, no test interdependencies, no network calls. Existing tests (`test_dashboard.py`, etc.) are unaffected.

---

## 7. Human Decision Notes Encoded

These decisions from David are already encoded in the PRs:

| Decision | Where encoded |
|----------|--------------|
| Single DB `Publicaciones` (no separate Assets DB v1) | #254 invariant `no_separate_assets_db_v1` |
| Two human gates: `aprobado_contenido`, `autorizar_publicacion` | #254 state machine + #253 case ED-GOLD-010 |
| Comments post-approval invalidate gates | #254 invariant `gate_invalidation_on_comment` + #253 case ED-GOLD-010 |
| Newsletter allowed but not v1 priority | #254 includes in Canal; #253 has no newsletter cases |
| Referente = discovery signal, not source | #254 invariant + #253 case ED-GOLD-002 |
| v1 priority channels: linkedin, blog, x | #253 gold set coverage |

---

## 8. Recommended Merge Order

### Tier 1 — No conflicts, pure new files (merge in any order)

1. **#253** `evals: editorial gold set minimum` — new `evals/` directory, zero overlap
2. **#254** `docs: Notion Publicaciones schema spec` — new `notion/schemas/` directory, zero overlap

### Tier 2 — Docs only

3. **#249** `docs: editorial pipeline specification` — docs only, no code conflict

### Tier 3 — OpsLogger conflict pair (order matters)

4. **#251** `feat: auth lifecycle check` — merges cleanly against current main
5. **#252** `feat: publish tracking` — already merged; if it weren't, whoever merges second resolves the textual conflict on `infra/ops_logger.py`

### Tier 4 — Unknown

6. **#250** `feat: structured error classification` — cannot assess; merge after inspecting branch

### Pre-merge checklist for each PR

- [ ] `PYTHONPATH=. .venv/bin/python -m pytest` passes (full suite)
- [ ] No secrets in diff (`grep -rn 'sk-\|PRIVATE_KEY\|password' <changed files>`)
- [ ] PR description matches actual changes

---

## 9. Open Questions for Human Decision

| # | Question | Blocking? |
|---|----------|-----------|
| 1 | **Single-row vs variante-per-row**: #249 models one row per content piece; #254 models one row per channel variante. Which is canonical? | Yes — blocks implementation of `Publicaciones` DB |
| 2 | **`ghost` vs `blog`**: Should the publish tracking module (#252) use `blog` instead of `ghost`? Or keep `ghost` as an alias? | Low — alias mapping suffices |
| 3 | **Status mapping**: Should the codebase maintain an explicit English↔Spanish status mapping, or should code always use the Spanish Notion names? | Medium — affects all future pipeline code |
| 4 | **Gate timestamps**: #249 includes `Content approved at` / `Publish authorized at`. Should #254 add these? | Low — can add later |
| 5 | **PR #250 audit gap**: Branch not available locally. Should we fetch/inspect before merging? | Yes — unknown risk |

---

## 10. Summary

**Stack health**: Good. The 6 PRs are largely independent. The only guaranteed merge conflict is textual (OpsLogger, #251 vs #252) and trivially resolvable.

**Primary risk**: Design divergence between #249 and #254 on the Publicaciones data model (single-row vs variante-per-row). This is an architectural decision that must be resolved before either spec drives implementation code.

**Secondary risk**: PR #250 could not be audited at code level. Its impact on the stack is unknown.

**No blockers for merging** #253 and #254 immediately — they are pure additions with no conflicts and full test coverage.
