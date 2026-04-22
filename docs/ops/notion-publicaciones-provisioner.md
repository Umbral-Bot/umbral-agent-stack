# Notion Publicaciones Provisioner — Dry Run

**Status**: dry-run only (no Notion API calls)
**Schema**: `notion/schemas/publicaciones.schema.yaml`
**Module**: `infra/notion_provisioner.py`
**CLI**: `scripts/plan_notion_publicaciones.py`

---

## What the dry-run does

1. Loads the approved local schema (`publicaciones.schema.yaml`).
2. Optionally validates it using `infra/notion_schema.py`.
3. Converts every property to its Notion API-compatible configuration.
4. Produces a structured plan containing:
   - Database name, version, owner, description.
   - Parent policy (recommended and forbidden parents).
   - All properties with their Notion API config shape.
   - State machine transitions and gates.
   - Invariants as documentation/checks.
   - Recommended views as metadata.
   - Summary statistics.
5. Outputs the plan as human-readable text, JSON, or Markdown.

## What it does NOT do

- Does **not** call the Notion API.
- Does **not** create, modify, or delete any Notion database.
- Does **not** require `NOTION_API_KEY` or any environment variable.
- Does **not** read `.env` or any secrets file.
- Does **not** write files unless `--output <path>` is explicitly passed.
- Does **not** activate cron, services, or webhooks.
- Does **not** call Ghost, LinkedIn, X, Freepik, Vertex, n8n, or Make.

## How to run the CLI

```bash
# Default summary
PYTHONPATH=. .venv/bin/python scripts/plan_notion_publicaciones.py

# With schema validation
PYTHONPATH=. .venv/bin/python scripts/plan_notion_publicaciones.py --validate

# JSON output
PYTHONPATH=. .venv/bin/python scripts/plan_notion_publicaciones.py --validate --json

# Markdown output
PYTHONPATH=. .venv/bin/python scripts/plan_notion_publicaciones.py --validate --markdown

# Save to file
PYTHONPATH=. .venv/bin/python scripts/plan_notion_publicaciones.py --json --output plan.json

# --apply is intentionally disabled
PYTHONPATH=. .venv/bin/python scripts/plan_notion_publicaciones.py --apply
# → ERROR: --apply is intentionally disabled in this PR.
```

### Options

| Flag | Description |
|------|-------------|
| `--schema <path>` | Path to schema YAML (default: `notion/schemas/publicaciones.schema.yaml`) |
| `--validate` | Run structural validation before generating plan |
| `--json` | Output as JSON |
| `--markdown` | Output as Markdown |
| `--output <path>` | Write to file instead of stdout |
| `--apply` | **Disabled.** Exits with error. |

## How to interpret the plan

The plan is a JSON-serializable dict with these sections:

- **`database`**: Name, version, status, owner, description.
- **`parent_policy`**: Where the DB should (and should not) be created in Notion.
- **`properties`**: Each property with its name, type, Notion API config, required flag, and description.
- **`api_properties`**: The exact dict shape that would be sent to `POST /v1/databases` under `properties`.
- **`state_machine`**: The initial state and all transitions with triggers and gates.
- **`invariants`**: Business rules that code/automation must enforce.
- **`recommended_views`**: Suggested Notion views (Kanban, tables, filters).
- **`summary`**: Counts of properties, channels, types.

## What is needed before enabling `--apply`

Before a future PR enables actual Notion provisioning:

1. **NOTION_API_KEY** must be available in the environment (not in this PR).
2. **Parent page ID** must be provided — the integration must have access to the target parent page.
3. **OpsLogger integration** — the apply function should log `notion_operation` events.
4. **Human confirmation** — David must approve which Notion workspace/parent to target.
5. **Idempotency check** — verify no DB named `Publicaciones` already exists under the target parent.
6. **Rollback plan** — document how to archive/delete a mistakenly created DB.
7. **Tests with mocked Notion client** — no real API calls in CI.

## Safety rules

- No Notion API calls by default. The module is pure computation.
- No environment variables are read by the provisioner or the CLI.
- No database is created, modified, or deleted.
- `apply_plan()` raises `NotImplementedError` unconditionally.
- `build_provisioning_plan(dry_run=False)` raises `NotImplementedError`.
- `--apply` CLI flag exits with error code 1 and a clear message.

## Next step: read-only audit

Before enabling `--apply`, run the read-only audit to compare the local schema against an existing Notion database (or fixture). See [`docs/ops/notion-publicaciones-readonly-audit.md`](notion-publicaciones-readonly-audit.md) for details.

```bash
# Fixture mode (offline)
PYTHONPATH=. .venv/bin/python scripts/audit_notion_publicaciones.py \
    --fixture tests/fixtures/notion/publicaciones_database_valid.json --validate-schema

# Live read-only mode
PYTHONPATH=. .venv/bin/python scripts/audit_notion_publicaciones.py \
    --database-id <id> --fail-on-blocker
```

The audit must pass with zero blockers before any apply is considered.

## Relationships

| Component | Relationship |
|-----------|-------------|
| `notion/schemas/publicaciones.schema.yaml` | Source schema. The provisioner reads this file. |
| `docs/specs/notion-publicaciones-schema.md` | Human-readable spec for the same schema. |
| `infra/notion_schema.py` | Schema loader and validator. Reused by the provisioner. |
| `infra/ops_logger.py` | Future: `apply_plan()` should log `notion_operation` events. |
| Human gates (`aprobado_contenido`, `autorizar_publicacion`) | Encoded as checkbox properties in the plan. Not enforced by the provisioner — enforcement is in the state machine and worker logic. |
| `content_hash` / `idempotency_key` | Present in the plan as `rich_text` properties. Computation logic lives in `infra/publish_tracking.py`. |
