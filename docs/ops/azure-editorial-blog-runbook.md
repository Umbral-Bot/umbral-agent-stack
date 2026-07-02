# Runbook · Azure Editorial Blog (ADR-010)

Operational guide for the editorial blog publishing layer: deploy, secrets,
smoke, rollback. **No production deploy happens from the feature PR** — only
`az bicep build` + `what-if`. Real deploy is an explicit operator action
(GitHub Copilot merges after David approves).

- Infra: [`infra/azure/modules/editorial-blog.bicep`](../../infra/azure/modules/editorial-blog.bicep)
- Function: [`functions/editorial-publish/`](../../functions/editorial-publish/)
- Worker tasks: `web.publish_editorial_post`, `web.unpublish_editorial_post`

## 0. Prerequisites

```powershell
az login
az account set --subscription "<SPONSORSHIP_SUB_ID>"   # never commit the id
func --version    # Azure Functions Core Tools v4
```

## 1. Environment variables

### Worker (calls the Function)

| Variable | Required | Notes |
|----------|----------|-------|
| `EDITORIAL_BLOG_FUNCTION_URL` | yes | full endpoint, e.g. `https://func-umbral-editorial-prod.azurewebsites.net/api/publish-editorial-post` |
| `EDITORIAL_BLOG_FUNCTION_KEY` | yes | function key → header `x-functions-key` |
| `EDITORIAL_BLOG_CANONICAL_BASE_URL` | no | default `https://umbralbim.io` |
| `WORKER_TOKEN` | recommended | shared secret → header `x-worker-token` |
| `EDITORIAL_RAG_INDEX_NAME` | no | post-publish RAG index (default `umbral-editorial`) |
| `AZURE_SEARCH_ENDPOINT` / `AZURE_SEARCH_API_KEY` | for RAG hook | else the hook skips (publish still ok) |
| `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_API_KEY` | for RAG hook | embeddings; else the hook skips |

### Function (app settings — set by Bicep / `az functionapp config appsettings`)

| Variable | Required | Notes |
|----------|----------|-------|
| `EDITORIAL_BLOG_STORAGE_ACCOUNT` | yes (cloud) | account name; auth via Managed Identity |
| `EDITORIAL_BLOG_CONNECTION_STRING` | local only | overrides MI (Azurite/dev) |
| `EDITORIAL_BLOG_CONTAINER` | no | default `editorial-posts` |
| `EDITORIAL_BLOG_CANONICAL_BASE_URL` | no | default `https://umbralbim.io` |
| `EDITORIAL_BLOG_CDN_BASE_URL` | no | used to build `public_json_url` |
| `WORKER_TOKEN` | recommended | enables the `x-worker-token` check |

> Secrets live in Key Vault / app settings / `@secure()` params. **Never commit**
> a function key, `WORKER_TOKEN`, connection string or subscription id.

## 2. Validate + preview infra (no credits, no deploy)

```powershell
# syntax / ARM transpile
az bicep build --file infra/azure/main.bicep --outfile $env:TEMP\main.json

# preview the editorial layer only (flag forced ON)
./infra/azure/scripts/what-if-editorial-blog.ps1
```

Review `Microsoft.Web/*` (Function + plan), `Microsoft.Cdn/*` (profile +
endpoint) and the `steditorial*` storage account in the what-if output.

## 3. Deploy (operator, explicit)

### 3a. Infra (Bicep)

```powershell
az deployment sub create `
  --location eastus2 `
  --template-file infra/azure/main.bicep `
  --parameters infra/azure/main.bicepparam `
  --parameters deployEditorialBlog=true `
               editorialWorkerToken="<from-key-vault>"
```

Capture outputs:

```powershell
az deployment sub show -n main --query properties.outputs.editorialFunctionPublishUrl.value -o tsv
az deployment sub show -n main --query properties.outputs.editorialPublicReadBaseUrl.value -o tsv
```

### 3b. Function code

```powershell
cd functions/editorial-publish
func azure functionapp publish func-umbral-editorial-prod --python
```

### 3c. Get the function key

```powershell
az functionapp function keys list `
  -g rg-umbral-agents-prod `
  -n func-umbral-editorial-prod `
  --function-name publish_editorial_post -o json
```

Store it as the Worker's `EDITORIAL_BLOG_FUNCTION_KEY`.

## 4. Smoke test

```powershell
$env:EDITORIAL_BLOG_FUNCTION_URL = "https://func-umbral-editorial-prod.azurewebsites.net/api/publish-editorial-post"
$env:EDITORIAL_BLOG_FUNCTION_KEY = "<function-key>"
$env:WORKER_TOKEN = "<worker-token>"

./scripts/smoke-publish-editorial-post.ps1
```

Expected: HTTP 200 with `published_url`, `blob_path`, `index_updated`. Then
verify the blobs:

```powershell
az storage blob list --account-name steditorialprod --container-name editorial-posts `
  --prefix posts/ --auth-mode login -o table
az storage blob download --account-name steditorialprod --container-name editorial-posts `
  --name index.json --auth-mode login --file - 2>$null
```

`index.json` must contain one light entry per published slug, sorted
`published_at` desc, with no duplicate slugs.

### Worker dry-run (no network)

```powershell
$env:WORKER_TOKEN="test"
.\.venv\Scripts\python.exe -c "from worker.tasks.editorial_publish import handle_web_publish_editorial_post as h; import json; print(json.dumps(h({'payload': {'slug':'smoke-dry','title':'t','body_markdown':'b','notion_page_id':'n','autorizar_publicacion': True}, 'dry_run': True}), indent=2))"
```

## 5. Idempotency check

Re-run the smoke with the **same** payload → response `index_updated: false`
(content unchanged, slug not duplicated). Change the title → `index_updated:
true` and the entry is updated in place.

## 5a. Unpublish / cleanup

Use the Function endpoint instead of editing `index.json` or deleting blobs by
hand. This is the supported rollback path for individual posts and for smoke
fixtures.

```powershell
$env:EDITORIAL_BLOG_FUNCTION_URL = "https://func-umbral-editorial-prod.azurewebsites.net/api/unpublish-editorial-post"
$env:EDITORIAL_BLOG_FUNCTION_KEY = "<function-key>"
$env:WORKER_TOKEN = "<worker-token>"

./scripts/smoke-unpublish-editorial-post.ps1 -Slug criterios-de-aceptacion-antes-de-automatizar-bim
```

Request contract:

```json
{
  "slug": "kebab-case",
  "notion_page_id": "uuid-opcional",
  "delete_post_blob": true
}
```

Provide either `slug` or `notion_page_id`. If `notion_page_id` is present, the
Function removes the matching `index.json` entry by that id and uses the removed
entry's slug for blob deletion. Missing entries and missing post blobs are
idempotent 200 responses.

Expected response:

```json
{
  "ok": true,
  "slug": "criterios-de-aceptacion-antes-de-automatizar-bim",
  "index_updated": true,
  "post_blob_deleted": true,
  "removed_from_index": true
}
```

Worker dry-run (no network, no human publish gate required):

```powershell
$env:WORKER_TOKEN="test"
.\.venv\Scripts\python.exe -c "from worker.tasks.editorial_publish import handle_web_unpublish_editorial_post as h; import json; print(json.dumps(h({'slug':'criterios-de-aceptacion-antes-de-automatizar-bim', 'dry_run': True}), indent=2))"
```

## 5b. Post-publish RAG indexing (Task B)

After a successful publish (not `dry_run`, gate open), the Worker indexes
`body_markdown` into Azure AI Search by reusing `worker/tasks/rag.py` (`rag.index`
→ embeddings). Index defaults to `umbral-editorial` (`EDITORIAL_RAG_INDEX_NAME`),
`source_type = editorial_blog`.

Best-effort, never blocks the blog:

- Missing `AZURE_SEARCH_*` / `AZURE_OPENAI_*` → response has `rag_indexed:false` +
  `rag_skipped_reason:"missing_env:…"`; the blog is still published.
- Indexing error → `rag_indexed:false` + `rag_error`; publish stays `ok`.
- Flags: `index_after_publish` (default `true`), `skip_rag_index` (default `false`).

Ensure the index exists once (idempotent):

```powershell
# via the worker rag.ensure_index task (or rag.index auto-creates on first write)
$env:WORKER_TOKEN="test"
.\.venv\Scripts\python.exe -c "from worker.tasks.rag import handle_rag_ensure_index as e; import json; print(json.dumps(e({'index_name':'umbral-editorial'})))"
```

Verify after a real publish: response includes `rag_indexed: true` and
`rag_chunks: N`, and `rag.search`/`rag.query` against `umbral-editorial` return
the post.

## 6. Rollback

The blog is static JSON; rollback = unpublish or restore blobs.

- **Unpublish one post**: prefer `POST /api/unpublish-editorial-post` or
  `scripts/smoke-unpublish-editorial-post.ps1`, which removes the index entry
  and deletes `posts/{slug}.json` idempotently.
- **Manual emergency fallback**: delete `posts/{slug}.json` and remove its entry
  from `index.json` only if the Function path is unavailable.
  ```powershell
  az storage blob delete --account-name steditorialprod --container-name editorial-posts `
    --name posts/<slug>.json --auth-mode login
  ```
  Soft-delete is enabled (7-day retention) — blobs can be undeleted within the
  window.
- **Disable the whole layer**: redeploy with `deployEditorialBlog=false` (stops
  the Function + CDN; storage with `deleteRetentionPolicy` is preserved by ARM
  but review before destructive changes).
- **Bad Function release**: `func azure functionapp publish` the previous commit,
  or swap to a deployment slot if configured.

## 7. Security checklist (before deploy)

- [ ] `editorialWorkerToken` comes from Key Vault, not the repo.
- [ ] `editorialPublicBlobRead` stays `false` unless serving directly from blob.
- [ ] Function key rotated if it ever appeared in logs/chat.
- [ ] No subscription id / tenant id / object id committed.
- [ ] `WORKER_TOKEN` matches between Worker and Function app settings.

## 8. Known limitations (v1)

- `index.json` is a single object — fine for tens/hundreds of posts; paginate or
  move to a DB beyond that.
- Slug rename leaves the old `posts/{old}.json` blob unlisted (not auto-deleted);
  clean up manually if needed.
- Long bodies stored in the Notion page body (not the `Copy Blog` property)
  require an explicit payload to the Worker task.
