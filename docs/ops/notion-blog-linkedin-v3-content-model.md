# Notion · Blog + LinkedIn + X — Content Model v3

> Status: repo-side process contract. This document does not activate runtime
> agents, edit Notion, publish, or change human gates. It defines the **fields**
> and **channel rules** the editorial flow relies on (see
> [ADR-010](../adr/ADR-010-azure-editorial-blog-cms.md)).

## Why v3

v1/v2 treated each channel as an independent long post. v3 makes the **blog the
single canonical source** and turns social into pointers to it. This removes
duplicate long-form content and fixes attribution (every channel links back to
`umbralbim.io/noticias/:slug`).

## Channel rules (do not renegotiate)

| Channel | Role | Length | Links to blog? | Auto-published? |
|---|---|---|---|---|
| **Blog** | Canonical, full article | full | n/a (is canonical) | by Worker, after gate |
| **LinkedIn — David** | Short teaser in David's voice | 60-120 words | **yes** (required) | **no** (manual/HITL) |
| **LinkedIn — Umbral BIM (empresa)** | Suggested text to *share* the page post | 40-80 words | yes | **no** (manual) |
| **X** | Summary + link | ≤ 280 chars | yes | **no** (manual) |

Hard rules:

- The **blog is published first**. The canonical `published_url` is produced by
  the Azure layer (ADR-010).
- If a social copy is missing the link, inject `published_url` **after** the blog
  is published — never before.
- LinkedIn/X are **never auto-published** by the code in this repo. Only the blog
  blob + canonical URL are produced automatically.

## Norte 2026-07-22 — V1 outline vs V2 long copy, RRSS = Opción B

> See `editorial-norte-hitl-contract-2026-07-22.md`.

- **V1 (alternatives):** short outline per alternative (narrative arc +
  discourse-structure footer + concrete-piece source URL), for human choice —
  **not** final copy.
- **V2 (post-approval):** full long `Copy Blog` (~CAND-001, 350-500+ words) +
  final per-channel copies. Mind the `Copy Blog` rich_text size limit (below).
- **RRSS = Opción B (Fila I):** the blog auto-publishes after gates; LinkedIn/X
  receive the injected `published_url` + Notion copy and a `listo_rrss` state,
  then a human posts (manual/semi-auto). This reaffirms the channel rules above —
  social is never auto-published (LinkedIn ToS §3.1.26).

## Publicaciones DB — fields used by the publish step

The `Publicaciones` DB schema is owned by David (ADR-007: only David changes
schema). The Worker reads these properties (names are **configurable** per call
via `notion_prop_map`; defaults below). If your DB uses different names, pass the
map or update the defaults in
[`worker/tasks/editorial_publish.py`](../../worker/tasks/editorial_publish.py).

| Post field | Default Notion property | Type | Notes |
|---|---|---|---|
| `title` | `Title` | title | falls back to the page title |
| `slug` | `Slug` | rich_text / url | lowercase kebab-case |
| `body_markdown` | `Copy Blog` | rich_text | canonical body (see limitation) |
| `excerpt` | `Bajada` | rich_text | short summary / dek |
| `hero_image_url` | `Visual asset URL` / selección visual v2 | url | `Alt N` resolves from `imagen_alt_N_url`; legacy `Hero Image` remains a fallback |
| `tags` | `Tags` | multi_select | |
| `published_at` | `Fecha publicación` | date | defaults to now |
| `canonical_url` / write-back | `published_url` | url | filled after publish |
| **gate** `aprobado_contenido` | `aprobado_contenido` | checkbox | only David sets true |
| **gate** `autorizar_publicacion` | `autorizar_publicacion` | checkbox | only David sets true |

### New column — `Copy LinkedIn empresa`

v3 adds a dedicated column for the **company-page** suggested share text, kept
separate from `Copy LinkedIn` (David's teaser). This column is **not** consumed
by the publish handler (no auto-post); it exists so the operator can copy/paste
when sharing the company post.

| Copy field | Suggested Notion property | Used by code? |
|---|---|---|
| LinkedIn David teaser | `Copy LinkedIn` | no (manual) |
| **LinkedIn empresa** | `Copy LinkedIn empresa` *(new)* | no (manual) |
| X copy | `Copy X` | no (manual) |
| Blog body | `Copy Blog` | **yes** (publish) |

`scripts/editorial/apply_publication_copy.py` writes `Copy LinkedIn empresa`
whenever the local copy YAML sets `copy_linkedin_empresa` (missing is a
validation warning, not a hard failure, so existing anchors like CAND-001 keep
applying without it until Rick starts producing the field). The live Notion
column itself is created by David in P1 — see
[editorial-roadmap-norte-p1-p3-2026-07-22.md P2.3](editorial-roadmap-norte-p1-p3-2026-07-22.md).

> Limitation (v1): `Copy Blog` read as a rich_text property has Notion's
> per-property size limits (2000 chars per rich_text object, 100 objects per
> property — roughly 200k chars before the property itself would need more
> chunks than Notion allows). Very long bodies that live in the page **body**
> (blocks) instead of a property are out of scope for the automatic read; use an
> explicit `payload` to the Worker task in that case, or paste the body into
> `Copy Blog`.
>
> **P2.3 resolution:** `apply_publication_copy.py` now offers both escape
> hatches named above, so the operator picks whichever fits:
> - `--write-body` appends the full `copy_blog` text as page **body** blocks
>   (paragraphs behind a callout+divider marker, idempotent per `trace_id` —
>   a re-run skips instead of duplicating). Independent of the `Copy Blog`
>   *property* write, which still happens too (best-effort, chunked, and now
>   guarded: it raises `RichTextOverflowError` instead of silently truncating
>   if the text would need more than 100 rich_text chunks).
> - `--emit-worker-payload PATH` writes a partial JSON payload (`body_markdown`
>   full text + `notion_page_id`/`trace_id`, gates hardcoded `false`) shaped for
>   `worker/tasks/editorial_publish.py`'s explicit `payload` input — the Worker
>   never re-reads `Copy Blog` back through the property in that path, so the
>   property limit cannot truncate it. It is **partial**: slug/title/tags/
>   excerpt belong to the blog-metadata step and must be merged in before a
>   real publish call.
> - Anchor test: CAND-001's ~500-word body fits well under the property limit
>   on its own; both hatches exist for when a future body doesn't.

## Visual assets (deliverable F — implemented)

Goal: derive the post's image URLs from the editorial selection so the operator
doesn't paste URLs by hand.

```
Selección imagen  (select/relation: which rendered variant to use)
      ↓  resolve
imagen_alt_1_url / imagen_alt_2_url / … (url properties: the rendered variants)
      ↓  map
hero_image_url  (the chosen variant feeds the blog post)
```

Intended mapping:

1. Read `Selección imagen` → which `imagen_alt_N_url` is the chosen one.
2. Set `hero_image_url` = that URL.
3. Carry the remaining `imagen_alt_N_url` as gallery candidates (future).

Status: **implemented** against the versioned
[`Publicaciones` visual schema v2](notion-publicaciones-v2-visual-gates-schema.md).
`resolve_visual_asset_urls()` in
[`worker/tasks/editorial_publish.py`](../../worker/tasks/editorial_publish.py)
reads the exact `Alt 1` ... `Alt 5` options, carries non-empty alternative URLs,
and gives the selected URL priority as `hero_image_url`. Missing, pending,
`Sin imagen`, and incomplete selections return `{}` from the resolver. The
publish handler additionally enforces this Notion-only gate:

| Notion visual state | Publish behavior |
|---|---|
| `Selección imagen` property absent | Legacy-compatible: prefer `Visual asset URL`, then configured `Hero Image` |
| Select empty, `Pendiente`, or `Regenerar` | Block with `visual_asset_not_ready` before the Azure Function call |
| `Alt N` without `imagen_alt_N_url` | Block |
| `Alt N` with `Estado imagen` other than `Seleccionada` | Block |
| `Alt N` with non-empty `Visual asset URL` different from the selected alt | Block as `canonical_url_mismatch` |
| Valid `Alt N`, canonical URL empty | Allow transition using the selected `imagen_alt_N_url` |
| Valid `Alt N`, canonical URL matching | Use `Visual asset URL` |
| `Sin imagen` | Explicit approval; publish with an empty hero |

The response exposes the decision under `gates.visual_asset`; those diagnostics
are never included in the Azure Function payload. Explicit payload sources do
not use this visual gate. Tests live in
`tests/test_editorial_publish.py::TestVisualAssets`.

## Operator flow (happy path)

1. Draft + review the piece in `Publicaciones` (status `Borrador`).
2. David sets `aprobado_contenido = true`, then `autorizar_publicacion = true`.
3. Telegram order "ok publica" → operator triggers the Worker task
   `web.publish_editorial_post` with the `notion_page_id`.
4. Worker validates editorial + visual gates → calls the Azure Function → blog is live at
   `umbralbim.io/noticias/:slug`.
5. `published_url` is written back / injected into the social copies.
6. Operator manually posts the LinkedIn (David), LinkedIn (empresa) and X copies.

## V2 copy step — how to dry-run (P2.3)

Before step 1 above, `scripts/editorial/apply_publication_copy.py` writes the
approved copy (blog + per-channel) from a local YAML
(`evals/editorial/{publication-id}-final-copy.yaml`) into `Publicaciones`.
Gates are never touched by this script in any mode.

```bash
# Property-only (existing v1 behavior): validate + preview, no Notion call.
python scripts/editorial/apply_publication_copy.py \
  --publication-id CAND-001 --dry-run --skip-model-verify

# V2: also preview the page-body-blocks escape hatch (long Copy Blog, no
# property size risk) and emit a partial Worker payload (full body_markdown,
# gates hardcoded false) — still no Notion call.
python scripts/editorial/apply_publication_copy.py \
  --publication-id CAND-001 --dry-run --skip-model-verify \
  --write-body \
  --emit-worker-payload evals/editorial/cand-001-worker-payload.json
```

Drop `--dry-run` (and export `NOTION_API_KEY`) to actually write. `--write-body`
is idempotent: a re-run skips the body append if its `trace_id` marker block is
already present on the page (pass `--force-body-append` to override). See
[§Limitation](#new-column--copy-linkedin-empresa) above for when to reach for
`--write-body` / `--emit-worker-payload` versus the plain property write.

## References

- [ADR-007](../adr/ADR-007-notion-como-hub-editorial.md) — Notion como hub
- [ADR-010](../adr/ADR-010-azure-editorial-blog-cms.md) — Azure editorial blog CMS
- [editorial-agent-flow.md](editorial-agent-flow.md) — agent responsibilities
- [azure-editorial-blog-runbook.md](azure-editorial-blog-runbook.md) — deploy/smoke/rollback
