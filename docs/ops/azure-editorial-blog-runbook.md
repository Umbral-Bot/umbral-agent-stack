# Runbook · Azure Editorial Blog (ADR-010)

Operational guide for the editorial blog publishing layer: deploy, secrets,
smoke, rollback. **No production deploy happens from the feature PR** — only
`az bicep build` + `what-if`. Real deploy is an explicit operator action
(GitHub Copilot merges after David approves).

- Infra: [`infra/azure/modules/editorial-blog.bicep`](../../infra/azure/modules/editorial-blog.bicep)
- Function: [`functions/editorial-publish/`](../../functions/editorial-publish/)
- Worker task: `web.publish_editorial_post`

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

## 6. Rollback

The blog is static JSON; rollback = restore/remove blobs.

- **Unpublish one post**: delete `posts/{slug}.json` and remove its entry from
  `index.json` (or re-publish a previous version of the post).
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
