# Lovable Handoff · `umbralbim.io/noticias` (Azure CDN blog)

> **Spec only.** This document describes what the **frontend** (SPA, repo
> `umbral-bot-codex-clean`) must implement to render the editorial blog. **Do not
> implement UI in `umbral-agent-stack`.** The publishing backend (Azure Blob +
> Function + CDN) is owned here and described in
> [ADR-010](../adr/ADR-010-azure-editorial-blog-cms.md).

## What the backend gives you

A public, CDN-fronted blob container `editorial-posts` with two JSON shapes:

```
{CDN_BASE}/editorial-posts/index.json            # listing
{CDN_BASE}/editorial-posts/posts/{slug}.json      # one post
```

`CDN_BASE` is provided as an env/config value (`EDITORIAL_BLOG_CDN_BASE_URL`,
e.g. `https://func-umbral-editorial-prod-cdn.azureedge.net`). Treat it as
configurable — do not hardcode.

> Decoupling: this content is **not** in Supabase. Supabase/Lovable auth stays
> for chat/product; the blog is read-only static JSON. No auth needed to read.

### `index.json` (array, sorted `published_at` desc)

Light entries for the listing page. The SPA should only depend on:

```json
[
  {
    "slug": "ia-en-coordinacion-bim",
    "title": "IA en la coordinación BIM",
    "excerpt": "Criterios de aceptación explícitos antes de escalar.",
    "hero_image_url": "https://cdn.umbralbim.io/heroes/ia-bim.jpg",
    "published_at": "2026-06-07T12:00:00Z",
    "tags": ["BIM", "IA"]
  }
]
```

> Entries may also carry `notion_page_id` / `content_hash` (backend
> idempotency). **Ignore them** in the UI.

### `posts/{slug}.json` (full post, `schema_version: 1`)

```json
{
  "schema_version": 1,
  "slug": "ia-en-coordinacion-bim",
  "title": "IA en la coordinación BIM",
  "excerpt": "Criterios de aceptación explícitos antes de escalar.",
  "body_markdown": "## Intro\n\nTexto…",
  "hero_image_url": "https://cdn.umbralbim.io/heroes/ia-bim.jpg",
  "author": "David Moreira",
  "published_at": "2026-06-07T12:00:00Z",
  "updated_at": "2026-06-07T12:00:00Z",
  "tags": ["BIM", "IA"],
  "canonical_url": "https://umbralbim.io/noticias/ia-en-coordinacion-bim"
}
```

Render `body_markdown` with a Markdown renderer + sanitizer (e.g.
`react-markdown` + `rehype-sanitize`). Do **not** dangerouslySetInnerHTML raw.

## Routes to implement

| Route | Data | Behavior |
|---|---|---|
| `/noticias` | `GET {CDN_BASE}/editorial-posts/index.json` | grid/list of cards (hero, title, excerpt, date, tags); newest first |
| `/noticias/:slug` | `GET {CDN_BASE}/editorial-posts/posts/{slug}.json` | full article; render `body_markdown` |

### States (required)

- **Loading**: skeleton on both routes while fetching.
- **Empty**: `/noticias` with `[]` → friendly empty state.
- **404**: `/noticias/:slug` where the blob returns 404 → "post not found",
  link back to `/noticias`.
- **Error**: network/parse error → retry affordance; never a blank screen.

### Caching

- CDN sets `Cache-Control` on the JSON. The SPA may add a cache-bust on the post
  fetch using the listing's freshness (e.g. `?v={published_at}` or `{content_hash}`
  if you choose to read it) when a hard refresh is needed.

## SEO / meta (per post)

`/noticias/:slug` must set, from the post JSON:

- `<title>` = `title`
- `<meta name="description">` = `excerpt`
- `<link rel="canonical" href="{canonical_url}">` (always the umbralbim.io URL)
- Open Graph: `og:title`, `og:description`, `og:image` = `hero_image_url`,
  `og:type=article`, `og:url` = `canonical_url`
- Twitter: `twitter:card=summary_large_image`, `twitter:title`,
  `twitter:description`, `twitter:image`
- JSON-LD `Article` (headline, image, datePublished=`published_at`,
  dateModified=`updated_at`, author=`author`).

> Because this is an SPA, use SSR/prerender or a meta-injection strategy so
> crawlers and LinkedIn/X link unfurlers see per-post tags. Client-only meta will
> not unfurl reliably.

## Out of scope (handled elsewhere)

- Publishing / editing posts (Worker + Azure Function, this repo).
- LinkedIn/X posting — manual, never from the SPA (see
  [content model v3](../ops/notion-blog-linkedin-v3-content-model.md)).
- Auth — the blog is public, read-only.

## Acceptance (frontend)

1. `/noticias` lists posts from `index.json`, newest first, with loading/empty
   states.
2. `/noticias/:slug` renders the post Markdown with sanitization and 404/error
   states.
3. Per-post canonical + OG/Twitter/JSON-LD meta are correct and unfurl on
   LinkedIn/X.
4. `CDN_BASE` is configurable (no hardcoded host).
