# Notion Publicaciones Read-Only Audit

**Status**: read-only (no writes to Notion)
**Module**: `infra/notion_readonly_audit.py`
**CLI**: `scripts/audit_notion_publicaciones.py`

---

## What it compares

The auditor compares the approved local schema (`notion/schemas/publicaciones.schema.yaml`) against a Notion database's metadata. It checks:

- **Missing properties**: expected in schema but absent in Notion.
- **Extra properties**: present in Notion but not in schema.
- **Type mismatches**: property exists in both but with different type.
- **Missing options**: select/multi_select/status options expected but absent.
- **Extra options**: options in Notion not defined in schema.
- **Name/casing differences**: property names that match after normalization but differ in casing, spacing, or accents.

## What it does NOT do

- Does **not** create any Notion database.
- Does **not** modify any Notion database (no POST, PATCH, DELETE).
- Does **not** update properties, options, or metadata.
- Does **not** require `NOTION_API_KEY` in fixture mode.
- Does **not** print or log `NOTION_API_KEY`.
- Does **not** write files unless `--output <path>` is explicitly passed.
- Does **not** activate cron, services, webhooks, or publishing.

## How to use fixture mode (offline)

Fixture mode uses a local JSON file that mimics Notion database metadata. No API key or network access needed.

```bash
# Default audit
PYTHONPATH=. .venv/bin/python scripts/audit_notion_publicaciones.py \
    --fixture tests/fixtures/notion/publicaciones_database_valid.json

# With schema validation
PYTHONPATH=. .venv/bin/python scripts/audit_notion_publicaciones.py \
    --fixture tests/fixtures/notion/publicaciones_database_valid.json \
    --validate-schema

# JSON output
PYTHONPATH=. .venv/bin/python scripts/audit_notion_publicaciones.py \
    --fixture tests/fixtures/notion/publicaciones_database_valid.json --json

# Markdown output
PYTHONPATH=. .venv/bin/python scripts/audit_notion_publicaciones.py \
    --fixture tests/fixtures/notion/publicaciones_database_valid.json --markdown

# Fail if blockers found (CI-friendly)
PYTHONPATH=. .venv/bin/python scripts/audit_notion_publicaciones.py \
    --fixture tests/fixtures/notion/publicaciones_database_missing_critical.json \
    --fail-on-blocker
# → exit code 1
```

## How to use live read-only mode

Live mode fetches database metadata from Notion via `GET /v1/databases/{id}`. Requires `NOTION_API_KEY` in the environment.

```bash
export NOTION_API_KEY="ntn_..."
PYTHONPATH=. .venv/bin/python scripts/audit_notion_publicaciones.py \
    --database-id <your-database-id>
```

Only GET is used. No data is written to Notion.

## Severity levels

| Severity | Meaning | Examples |
|----------|---------|----------|
| **BLOCKER** | Critical field missing or type-incompatible. Must fix before provisioning. | `aprobado_contenido` missing, `content_hash` has wrong type |
| **WARNING** | Non-critical issue that should be reviewed. | Select option missing, non-critical property absent, name casing difference |
| **INFO** | Informational. No action required. | Extra property in Notion not in schema |

### Critical fields

These fields produce **BLOCKER** severity if missing or type-mismatched:

- `aprobado_contenido`
- `autorizar_publicacion`
- `gate_invalidado`
- `content_hash`
- `idempotency_key`
- `canal`
- `estado`

### Name normalization

The auditor normalizes property names before comparison:
- Lowercase
- Spaces and hyphens become underscores
- Accents stripped (e.g., `Título` → `titulo`)

This means `content_hash` matches `Content Hash`, and `autorizar_publicacion` matches `Autorizar publicación`.

## Recommended order of operations

1. **Setup runbook/checklist**: [`docs/ops/notion-publicaciones-setup-runbook.md`](notion-publicaciones-setup-runbook.md)
2. **Dry-run provisioner**: generate and review the provisioning plan
3. **Manual controlled creation**: follow the runbook checklist
4. **Read-only audit** (this tool): verify DB matches schema with 0 blockers
5. Only after all above: Rick can write drafts (requires David's explicit approval)

## What is needed before enabling apply

Before any future PR enables writes to Notion:

1. This read-only audit must pass with zero blockers.
2. The provisioner dry-run plan (PR #258) must be reviewed.
3. `NOTION_API_KEY` must be available and tested.
4. Parent page ID must be confirmed by David.
5. Idempotency check: no DB named `Publicaciones` already exists.
6. OpsLogger integration for `notion_operation` events.
7. Rollback plan documented.

## Security

- **GET only** — no POST, PATCH, or DELETE.
- **No writes** — database is never modified.
- **Token never printed** — `NOTION_API_KEY` is used in the Authorization header but never logged or printed.
- **No env vars required** for fixture mode.
- **No runtime activation** — no cron, no services, no webhooks.

## CLI options

| Flag | Description |
|------|-------------|
| `--schema <path>` | Path to local schema YAML (default: `notion/schemas/publicaciones.schema.yaml`) |
| `--fixture <path>` | Path to JSON fixture (offline mode) |
| `--database-id <id>` | Notion database ID (live read-only mode, requires `NOTION_API_KEY`) |
| `--json` | Output as JSON |
| `--markdown` | Output as Markdown |
| `--output <path>` | Write to file |
| `--fail-on-blocker` | Exit 1 if any blocker |
| `--fail-on-warning` | Exit 1 if any warning |
| `--validate-schema` | Validate local schema before auditing |

## Available fixtures

| Fixture | Purpose |
|---------|---------|
| `tests/fixtures/notion/publicaciones_database_valid.json` | All 26 properties present, correct types |
| `tests/fixtures/notion/publicaciones_database_missing_critical.json` | Missing critical fields (aprobado_contenido, autorizar_publicacion, content_hash, idempotency_key) |
| `tests/fixtures/notion/publicaciones_database_type_mismatch.json` | Critical fields present but wrong types |
| `tests/fixtures/notion/publicaciones_database_extra_properties.json` | All expected properties plus 3 extra |
