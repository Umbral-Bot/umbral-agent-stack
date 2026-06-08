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
| `hero_image_url` | `Hero Image` | url / files | lead image |
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

> Limitation (v1): `Copy Blog` read as a rich_text property has Notion's
> per-property size limits. Very long bodies that live in the page **body**
> (blocks) instead of a property are out of scope for the automatic read; use an
> explicit `payload` to the Worker task in that case, or paste the body into
> `Copy Blog`.

## Visual assets (deliverable F — spec, stub in code)

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

Status: **stubbed**. `resolve_visual_asset_urls()` in
[`worker/tasks/editorial_publish.py`](../../worker/tasks/editorial_publish.py)
returns `{}` and is marked TODO until the `Publicaciones` visual schema is
versioned. A skipped test documents the target behavior
(`tests/test_editorial_publish.py::TestVisualAssets`). Until then, set
`hero_image_url` directly (property `Hero Image`) or in the explicit payload.

## Operator flow (happy path)

1. Draft + review the piece in `Publicaciones` (status `Borrador`).
2. David sets `aprobado_contenido = true`, then `autorizar_publicacion = true`.
3. Telegram order "ok publica" → operator triggers the Worker task
   `web.publish_editorial_post` with the `notion_page_id`.
4. Worker validates gates → calls the Azure Function → blog is live at
   `umbralbim.io/noticias/:slug`.
5. `published_url` is written back / injected into the social copies.
6. Operator manually posts the LinkedIn (David), LinkedIn (empresa) and X copies.

## References

- [ADR-007](../adr/ADR-007-notion-como-hub-editorial.md) — Notion como hub
- [ADR-010](../adr/ADR-010-azure-editorial-blog-cms.md) — Azure editorial blog CMS
- [editorial-agent-flow.md](editorial-agent-flow.md) — agent responsibilities
- [azure-editorial-blog-runbook.md](azure-editorial-blog-runbook.md) — deploy/smoke/rollback
