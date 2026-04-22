# Notion Publicaciones — Last Audit Result

**Date**: 2026-04-22
**Mode**: live read-only (attempted)
**Status**: PENDING — integration access not yet granted

---

## Audit attempt

```
PYTHONPATH=. .venv/bin/python scripts/audit_notion_publicaciones.py \
    --database-id e6817ec4698a4f0fbbc8fedcf4e52472 --validate-schema --markdown
```

**Result**: HTTP 404 — Notion API could not find the database.

**Cause**: The Notion integration has not been shared with the `Sistema Editorial Rick` page (or its child DB `Publicaciones`). The API key is valid but lacks access to this resource.

## How to fix

1. Open [Sistema Editorial Rick](https://www.notion.so/Sistema-Editorial-Rick-5894ba351e2749729077ca971fd9f52a) in Notion.
2. Click the `...` menu (top right) → "Connections" → add the integration that corresponds to the `NOTION_API_KEY`.
3. Confirm that the integration has access to child pages/databases.
4. Re-run the audit command above.

## DB details

| Field | Value |
|-------|-------|
| Database ID | `e6817ec4698a4f0fbbc8fedcf4e52472` |
| Database URL | [link](https://www.notion.so/e6817ec4698a4f0fbbc8fedcf4e52472) |
| Visible name | `📰 Publicaciones` |
| Data source name | `Publicaciones` |
| Parent hub | `Sistema Editorial Rick` (`5894ba351e2749729077ca971fd9f52a`) |

## Command to run when access is granted

```bash
export NOTION_API_KEY="ntn_..."
PYTHONPATH=. .venv/bin/python scripts/audit_notion_publicaciones.py \
    --database-id e6817ec4698a4f0fbbc8fedcf4e52472 --validate-schema --markdown \
    --output docs/ops/notion-publicaciones-last-audit.md
```

This file will be overwritten by the audit output when the command succeeds.
