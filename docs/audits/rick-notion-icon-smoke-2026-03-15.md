# Rick Notion Icon Smoke - 2026-03-15

## Context

After adding `icon` support to Notion page and row tools, Rick still created deliverables with the icon serialized into page content instead of using the structured `icon` tool argument.

## Initial failures

Three smoke attempts exposed two different states:

1. Before the live code deploy, Rick created deliverable rows in the correct database but no page icon was set.
2. After the live deploy, Rick still wrote `icon=...` into page content instead of passing the structured argument.

This showed that the backend support was present, but Rick still needed a stronger prompt/guardrail against serializing structured tool arguments into markdown content.

## Correction

I updated both live workspace guardrails:

- `openclaw/workspace-templates/AGENTS.md`
- `openclaw/workspace-templates/SOUL.md`

New rule:

- if a tool exposes structured arguments such as `icon`, `project_name`, `review_status` or `parent_page_id`, Rick must pass them in the tool payload and never encode them inside page content or titles as text hacks.

The updated files were synced to Rick's live workspace on the VPS.

## Validation

Final smoke run by Rick:

- deliverable title: `Smoke icon deliverable guardrail 2026-03-15`
- page URL:
  - `https://www.notion.so/Smoke-icon-deliverable-guardrail-2026-03-15-3245f443fb5c81f9b2a5f20d4fb8b520`

Verified outcome:

- page icon metadata is set to `🧪`
- title property remains clean:
  - `Smoke icon deliverable guardrail 2026-03-15`
- no `icon=...` text appears in page content

## Result

The bug is now closed in practice:

- backend tools accept real Notion icons
- Rick now uses the structured icon field correctly for deliverables
- project-scoped outputs can be created in `📬 Entregables Rick — Revisión` without polluting titles or content

## Residual limitation

This does not fully solve top-level Notion database icons. The current stack cleanly supports page and row icons, but database/data source icon handling is still limited by the tooling path we are using.
