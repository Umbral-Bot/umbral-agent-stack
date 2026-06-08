# Function: `editorial-publish`

Azure Function (Python **v2** programming model) that publishes editorial blog
posts to Blob Storage. It is the Azure-side endpoint behind the Worker task
`web.publish_editorial_post` (ADR-010).

```
POST /api/publish-editorial-post
  → editorial-posts/posts/{slug}.json     (full post, schema_version 1)
  → editorial-posts/index.json            (light listing, published_at desc)
```

> v2 model note: there is **no hand-written `function.json`** — the binding is
> declared by the `@app.route(...)` decorator in [`function_app.py`](function_app.py)
> and generated at build time. `host.json` + `requirements.txt` are still required.

## Files

| File | Purpose |
|---|---|
| `function_app.py` | HTTP trigger + blob IO (MI / connection string) |
| `shared.py` | pure validation + idempotent index upsert (stdlib only, unit-tested) |
| `host.json` | runtime config + extension bundle v4 |
| `requirements.txt` | `azure-functions`, `azure-storage-blob`, `azure-identity` |
| `local.settings.json.example` | copy to `local.settings.json` for local runs (gitignored) |

## Auth (defense in depth)

1. **Azure function key** — `authLevel = FUNCTION`; send header `x-functions-key: <key>`.
2. **Optional shared secret** — if the `WORKER_TOKEN` app setting is set, the
   request must also send header `x-worker-token: <same value>`, else `401`.

## Storage access

- **Cloud**: Managed Identity via `DefaultAzureCredential` against
  `EDITORIAL_BLOG_STORAGE_ACCOUNT` (needs *Storage Blob Data Contributor*; the
  Bicep module assigns it to the Function's system-assigned identity).
- **Local**: set `EDITORIAL_BLOG_CONNECTION_STRING` (e.g. Azurite
  `UseDevelopmentStorage=true`).

## App settings

| Setting | Required | Notes |
|---|---|---|
| `EDITORIAL_BLOG_STORAGE_ACCOUNT` | cloud | account name (MI auth) |
| `EDITORIAL_BLOG_CONNECTION_STRING` | local | overrides MI when set |
| `EDITORIAL_BLOG_CONTAINER` | no | default `editorial-posts` |
| `EDITORIAL_BLOG_CANONICAL_BASE_URL` | no | default `https://umbralbim.io` |
| `EDITORIAL_BLOG_CDN_BASE_URL` | no | used to build `public_json_url` |
| `WORKER_TOKEN` | no | enables the `x-worker-token` check |

## Request body

```json
{
  "slug": "ia-en-coordinacion-bim",
  "title": "IA en la coordinación BIM",
  "excerpt": "Cómo aplicamos IA con criterios de aceptación explícitos.",
  "body_markdown": "## Intro\n\nTexto…",
  "hero_image_url": "https://cdn.umbralbim.io/heroes/ia-bim.jpg",
  "author": "David Moreira",
  "published_at": "2026-06-07T12:00:00Z",
  "notion_page_id": "11111111-1111-1111-1111-111111111111",
  "content_hash": "sha256hex…",
  "tags": ["BIM", "IA"]
}
```

`published_at`, `updated_at`, `author` and `canonical_url` are filled with
defaults when omitted. `content_hash` is required by the function (the Worker
computes it if the caller doesn't).

## Response

```json
{
  "ok": true,
  "published_url": "https://umbralbim.io/noticias/ia-en-coordinacion-bim",
  "blob_path": "posts/ia-en-coordinacion-bim.json",
  "index_updated": true,
  "slug": "ia-en-coordinacion-bim",
  "content_hash": "sha256hex…",
  "public_json_url": "https://<cdn>/editorial-posts/posts/ia-en-coordinacion-bim.json"
}
```

`index_updated` is `false` when re-publishing byte-identical content
(idempotent — the slug is never duplicated).

## Run locally

```bash
cd functions/editorial-publish
cp local.settings.json.example local.settings.json
python -m venv .venv && . .venv/Scripts/activate   # PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Azurite (separate terminal): npx azurite --silent
func start
```

### curl

```bash
# local (anonymous when running under `func start`)
curl -sS -X POST http://localhost:7071/api/publish-editorial-post \
  -H "Content-Type: application/json" \
  --data @../../scripts/editorial/fixture-post-cand001.json | jq

# deployed (function key + optional worker token)
curl -sS -X POST "https://<function-app>.azurewebsites.net/api/publish-editorial-post" \
  -H "Content-Type: application/json" \
  -H "x-functions-key: $EDITORIAL_BLOG_FUNCTION_KEY" \
  -H "x-worker-token: $WORKER_TOKEN" \
  --data @../../scripts/editorial/fixture-post-cand001.json | jq
```

## Deploy

```bash
func azure functionapp publish func-umbral-editorial-prod --python
```

See [`docs/ops/azure-editorial-blog-runbook.md`](../../docs/ops/azure-editorial-blog-runbook.md)
for secrets, smoke and rollback.
