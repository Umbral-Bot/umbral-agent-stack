# Notion `📰 Publicaciones` — Schema Audit (read-only)

**Date:** 2026-05-08
**Auditor:** GitHub Copilot — Hilo 4 (`wave1-h4-notion-schema-gates`)
**Method:** `mcp_notion_notion-fetch` against DB
`e6817ec4-698a-4f0f-bbc8-fedcf4e52472`. Zero writes. Zero schema changes.
**Local schema reference:** `notion/schemas/publicaciones.schema.yaml` (v0.1.0).
**Master plan reference:** Hilo 1 stub at
[docs/editorial-pipeline/notion-schema.md](../editorial-pipeline/notion-schema.md)
(now superseded by full schema doc).

## Access status

| Check | Result |
|---|---|
| `NOTION_API_KEY` exported (from `~/.config/openclaw/env`) | yes |
| MCP fetch via `mcp_notion_notion-fetch` | success |
| Live schema retrieved | yes (45 properties) |
| Live state values retrieved | yes (8 statuses, all selects enumerated) |
| Notion writes performed | **none** |

## Result

- **All 16 master-plan §3 fields are present in live Notion.**
- `idempotency_key` already exists as `text` → no new property proposed.
- Live DB has 45 properties; YAML schema spec lists ~28 → 17 extras live.
- 1 select-option drift on `Etapa audiencia` (`retention` extra in live).
- 0 type mismatches on master-plan fields.
- 0 missing master-plan fields.

## Schema real vs declarado vs propuesto

Legend: `LIVE` = read from Notion · `YAML` = `notion/schemas/publicaciones.schema.yaml` · `PLAN` = master plan §3.

| Campo | LIVE tipo | YAML tipo | PLAN | Verdict |
|---|---|---|---|---|
| `Título` | title | title | — | ok |
| `publication_id` | text | rich_text | — | ok (text == rich_text in Notion) |
| `Canal` | select [blog,linkedin,x,newsletter] | select (4) | — | ok |
| `canal_publicado` | select [blog,linkedin,x,newsletter] | — | — | extra (live only) |
| `Tipo de contenido` | select (7) | select (7) | — | ok |
| `Etapa audiencia` | select (5: incl. `retention`) | select (4) | — | drift: live has extra `retention` |
| `Prioridad` | select [alta,media,baja] | — | — | extra (live only) |
| `Estado` | status (8) | status (8) | yes | ok |
| `aprobado_contenido` | checkbox | checkbox | yes | ok |
| `autorizar_publicacion` | checkbox | checkbox | yes | ok |
| `gate_invalidado` | checkbox | checkbox | yes | ok |
| `Creado por sistema` | checkbox | — | — | extra (live only) |
| `visual_hitl_required` | checkbox | checkbox | — | ok |
| `content_hash` | text | rich_text | yes | ok |
| `idempotency_key` | text | rich_text | yes (proposed) | **ok — already exists, proposal cancelled** |
| `trace_id` | text | rich_text | yes | ok |
| `platform_post_id` | text | rich_text | — | ok |
| `publication_url` | url | url | — | ok |
| `published_url` | url | — | yes | extra in live; aligns with PLAN |
| `published_at` | date | — | — | extra (live only) |
| `Fecha publicación` | date | date | — | ok |
| `publish_error` | text | — | — | extra (live only) |
| `error_kind` | select (8) | — | — | extra (live only) |
| `Fuente primaria` | url | url | yes | ok |
| `Fuente referente` | url | url | yes | ok |
| `Fuentes confiables` | relation | relation | — | ok |
| `Resumen fuente` | text | — | — | extra (live only) |
| `Responsable revisión` | person (limit 1) | — | — | extra (live only) |
| `Comentarios revisión` | text | — | — | extra (live only) |
| `Premisa` | text | rich_text | — | ok |
| `Claim principal` | text | — | — | extra (live only) |
| `Ángulo editorial` | text | — | yes | extra in live; aligns with PLAN |
| `Notas` | text | rich_text | — | ok |
| `Copy LinkedIn` | text | — | yes | extra in live; aligns with PLAN |
| `Copy Blog` | text | — | yes | extra in live; aligns with PLAN |
| `Copy Newsletter` | text | — | yes | extra in live; aligns with PLAN |
| `Copy X` | text | — | yes | extra in live; aligns with PLAN |
| `Visual brief` | text | rich_text | yes | ok |
| `Visual asset URL` | url | url | yes | ok |
| `Repo reference` | url | — | — | extra (live only) |
| `Proyecto` | text | rich_text | — | ok |
| `Publicación padre` | relation (self) | relation | — | ok |
| `Última revisión humana` | date | — | — | extra (live only) |
| `Creado por` | created_by | created_by | — | ok (system-managed) |
| `Última edición` | last_edited_time | last_edited_time | — | ok (system-managed) |

## Properties in YAML but missing in live Notion

None of the YAML properties are missing in live.

## Properties in live Notion but missing in YAML (17 extras)

`Prioridad`, `canal_publicado`, `published_url`, `published_at`, `publish_error`,
`error_kind`, `Resumen fuente`, `Responsable revisión`, `Comentarios revisión`,
`Claim principal`, `Ángulo editorial`, `Copy LinkedIn`, `Copy Blog`,
`Copy Newsletter`, `Copy X`, `Repo reference`, `Última revisión humana`,
`Creado por sistema`.

(Note: `published_url`, `Ángulo editorial`, and the four `Copy *` columns are
expected by master plan §3 but absent from the YAML spec. Suggest a follow-up
to align YAML with live in a separate read-only PR — out of scope for this
Hilo.)

## Master plan §3 coverage

| # | Master plan field | Present in live | Tipo live |
|---|---|---|---|
| 1 | `aprobado_contenido` | yes | checkbox |
| 2 | `autorizar_publicacion` | yes | checkbox |
| 3 | `gate_invalidado` | yes | checkbox |
| 4 | `Estado` | yes | status |
| 5 | `Fuente primaria` | yes | url |
| 6 | `Fuente referente` | yes | url |
| 7 | `content_hash` | yes | text |
| 8 | `idempotency_key` | **yes (already exists)** | text |
| 9 | `published_url` | yes | url |
| 10 | `trace_id` | yes | text |
| 11 | `Copy LinkedIn` | yes | text |
| 12 | `Copy Blog` | yes | text |
| 13 | `Copy Newsletter` | yes | text |
| 14 | `Copy X` | yes | text |
| 15 | `Visual brief` | yes | text |
| 16 | `Visual asset URL` | yes | url |
| 17 | `Ángulo editorial` | yes | text |

(17 ≥ 16 master-plan minimum.)

## Proposals — NOT EXECUTED

This Hilo created **no** Notion properties, **no** select options,
**no** views, **no** pages.

| Proposal | Reason | Status |
|---|---|---|
| Create `idempotency_key` if missing | not needed — already exists as text | **dropped** |
| Align YAML schema with the 17 live extras | YAML spec drifted vs live; YAML edit only, no Notion change | **deferred** to a future read-only PR |
| Convert `Proyecto` text → relation | requires canonical projects DB | deferred (already noted in YAML spec) |
| Document `retention` option on `Etapa audiencia` in YAML | YAML edit only | deferred |

## Audit hygiene

```bash
# Verify zero writers in new code (should be 0):
grep -rn "notion-update-data-source\|notion-create-database\|notion-update-page" \
  scripts/discovery/lib/ tests/lib/ docs/editorial-pipeline/notion-schema.md
# (also expected: 0 inside this audit document itself, except in the assertion line above)
```

## Appendix — raw schema source

Captured by `mcp_notion_notion-fetch` (database mode). The full JSON payload
is stored in the chat session resources for this conversation only and is
**not** committed to the repo (size: ~26 KB). The `_data-source-state_` block
within the payload provides the canonical type information transcribed in
the table above.
