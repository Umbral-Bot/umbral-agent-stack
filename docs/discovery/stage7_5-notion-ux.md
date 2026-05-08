# Stage 7.5 — Notion UX (schema audit + review comment + dashboard tab)

> Branch: `rick/stage7_5-notion-ux`
> Scope: schema audit + additive migration + review-comment helper + Mission Control "Copy review pending" tab.
> **Out of scope:** Stage 7.5 core (Hilo A) and voice/prompts (Hilo B).

This stage adds the **Notion-side UX scaffolding** that Stage 7.5 (Hilo A) needs once it starts writing `Copy LinkedIn` rich_text and flipping `Estado` to "En revisión":

1. A read-only schema audit script that checks the live Publicaciones DB has the properties Hilo A relies on.
2. An additive-only migration script (dry-run by default) that adds missing properties / select options without mutating existing data.
3. A reusable helper that posts an `@David, revisá el copy` comment on a Publicaciones page (idempotent — never duplicates).
4. A new **Copy review pending** section in the Pipeline Editorial dashboard listing pages with `copy_status='copy_ready' AND linkedin_status IS NULL`.

---

## Required schema for DB Publicaciones (`e6817ec4698a4f0fbbc8fedcf4e52472`)

| Property         | Required type | Required options                                                                                |
| ---------------- | ------------- | ----------------------------------------------------------------------------------------------- |
| `Copy LinkedIn`  | `rich_text`   | —                                                                                               |
| `Estado`         | `select`      | `Borrador`, `En revisión`, `Autorizado`, `Rechazado`, `Publicado` (additive — never destructive) |
| `Visual asset URL` | `url`       | —                                                                                               |

### Live state (verified 2026-05-08)

```json
{
  "Copy LinkedIn":    { "type": "rich_text" },                              // ✅ ok
  "Estado":           { "type": "status", "options": [
                          "Idea", "Borrador", "Revisión pendiente",
                          "Aprobado", "Autorizado", "Publicando",
                          "Publicado", "Descartado" ] },                    // ⚠ status, not select
  "Visual asset URL": { "type": "url" }                                     // ✅ ok
}
```

The `Estado` property is currently a Notion **`status`** type. Notion's REST API does not allow integrations to add/remove options on `status` properties (that has to be done in the Notion UI). The migration script reports this as `type_mismatch_no_action` and refuses to mutate it.

**Resolution path:** Stage 7.5 (Hilo A) should map the spec'd state names to the existing status options:

| Spec name        | Existing live option | Action          |
| ---------------- | -------------------- | --------------- |
| `Borrador`       | `Borrador`           | use as-is       |
| `En revisión`    | `Revisión pendiente` | rename in code  |
| `Autorizado`     | `Autorizado`         | use as-is       |
| `Rechazado`      | `Descartado`         | rename in code  |
| `Publicado`      | `Publicado`          | use as-is       |

Alternatively, David can rename the options manually in the Notion UI. **Either way, this stage will NOT auto-convert `Estado`.**

---

## Scripts

All scripts read `NOTION_API_KEY` from the environment. Source `~/.config/openclaw/env` first.

### `scripts/discovery/check_publicaciones_schema.py`

Read-only audit. Outputs JSON with `ok: bool`, per-property checks, and a `summary` block.

```bash
python scripts/discovery/check_publicaciones_schema.py --pretty
# exit 0 = schema fully matches spec
# exit 1 = divergence (see JSON for details)
# exit 2 = unrecoverable error (auth / network)
```

### `scripts/discovery/migrate_publicaciones_schema.py`

Additive-only migration. Default is dry-run; `--commit` applies the PATCH.

```bash
# Default: dry-run, no PATCH issued.
python scripts/discovery/migrate_publicaciones_schema.py --pretty

# Apply additive changes (only run after explicit OK from David).
python scripts/discovery/migrate_publicaciones_schema.py --commit --pretty
```

Guarantees:

* **Never** removes properties or options.
* **Never** changes a property's type.
* **Never** mutates `status` properties.
* **Idempotent** — running `--commit` twice in a row leaves the second run as a no-op.

### `scripts/discovery/stage7_5_post_review_comment.py`

Posts a review-pending comment on a Publicaciones page.

```bash
# CLI usage (manual / debugging).
python scripts/discovery/stage7_5_post_review_comment.py \
    --page-id <NOTION_PAGE_ID> \
    --copy "Texto del Copy LinkedIn (se truncará a 200 chars en el preview)"
```

Or from Python (Hilo A integration):

```python
from scripts.discovery.stage7_5_post_review_comment import post_review_comment
import httpx
client = httpx.Client(base_url="https://api.notion.com/v1",
                     headers={"Authorization": f"Bearer {token}",
                              "Notion-Version": "2025-09-03"})
result = post_review_comment(client, page_id, copy_text,
                            david_user_id=os.environ.get("DAVID_NOTION_USER_ID"))
# result -> {"action": "posted"|"skipped", "comment_id": str|None, "preview": str}
```

#### Comment template

```
🤖 Rick escribió un borrador de Copy LinkedIn para esta publicación.

Preview (primeros 200 chars):
> {copy_preview}

@David revisá el campo "Copy LinkedIn" arriba. Cuando esté listo:
- Si te sirve tal cual → setear Estado=Autorizado
- Si querés ajustar → editar el campo y luego Estado=Autorizado
- Si no sirve → Estado=Rechazado (Rick no reintenta automáticamente)

— Rick (Stage 7.5)
```

If `DAVID_NOTION_USER_ID` is set, the literal `@David` is replaced by a real Notion user mention node (`{type: "mention", mention: {type: "user", user: {id: ...}}}`). Otherwise the literal text is used.

#### Idempotency

Before posting, the helper lists existing comments on the page (`GET /v1/comments?block_id=<page_id>`) and skips when a previous comment carries:

* the marker `🤖 Rick escribió un borrador de Copy LinkedIn`, AND
* the same `preview` substring (first 200 chars of the copy).

If the preview changed (Hilo A wrote a new draft), a new comment is posted — duplicate detection is preview-bound, not page-bound.

---

## Mission Control — Copy review pending tab

`scripts/discovery/stageX_pipeline_dashboard.py` now includes a "Copy review pending" section, both in the markdown and Notion-block renders.

### SQLite query

```sql
SELECT id, titular, notion_page_id,
       copy_model_used, copy_last_attempt_at,
       copy_cost_usd_estimate, LENGTH(copy_linkedin) AS copy_len
FROM proposals
WHERE notion_page_id IS NOT NULL
  AND copy_status = 'copy_ready'
  AND COALESCE(linkedin_status, '') = ''
ORDER BY id ASC
```

The dashboard checks for the `copy_*` columns first. If they're missing (Hilo A hasn't migrated yet), the section renders a placeholder note: `(esperando Stage 7.5 core — columnas copy_* aún no presentes)`. This is the expected state until Hilo A's migration lands.

Storage column for the copy text is auto-detected: prefers `copy_text` (current Hilo A choice), falls back to `copy_linkedin` if present, otherwise `copy_len` is reported as `0`.

### Rendered fields

* **ID** — `proposals.id`.
* **Titular** — proposal title (markdown `|` escaped).
* **Page** — `https://www.notion.so/{notion_page_id}` link.
* **Copy len** — character length of `copy_linkedin`.
* **Modelo** — `copy_model_used`.
* **Último intento** — `copy_last_attempt_at` (epoch → ISO UTC if numeric).

Footer shows the count of pending pages and accumulated `copy_cost_usd_estimate`.

---

## Tests

Located under `tests/discovery/`:

* `test_check_publicaciones_schema.py` — 6 cases (ok / missing / status-no-action / partial select / no token / type mismatch).
* `test_migrate_publicaciones_schema.py` — 7 cases (dry-run / commit / idempotency / status-skip / additive options / double-commit / no token).
* `test_stage7_5_post_review_comment.py` — 8 cases (post / skip-duplicate / repost-on-change / preview truncation / mention with id / literal fallback / truncate util / template content).
* `test_stageX_dashboard_copy_review.py` — 8 cases (column-missing / zero rows / one row / linkedin-already-set / N rows + cost / blocks placeholder / blocks with rows / dashboard markdown integration).

**29 new tests, all passing alongside the existing 134 discovery tests (163 total).**

---

## Operational notes

* `migrate_publicaciones_schema.py --commit` must NOT be run without explicit OK from David. The current live state needs no PATCH (only the `Estado` `status`-type discrepancy, which the script intentionally skips).
* The post-review-comment helper does not call Notion during tests — tests use a fake httpx-shaped client. Live posts only happen via the CLI or via Hilo A integration.
* Dashboard render is purely additive: the existing tabs and the cron schedule logic are untouched.
