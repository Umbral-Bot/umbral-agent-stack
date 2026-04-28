# CAND-003 — LinkedIn Writer Runtime Smoke Evidence

> **Date**: 2026-04-24
> **Branch**: `rick/editorial-linkedin-writer-flow`

## Agent Registration

```json5
{
  "id": "rick-linkedin-writer",
  "name": "Rick LinkedIn Writer",
  "workspace": "/home/rick/.openclaw/workspaces/rick-linkedin-writer",
  "model": "azure-openai-responses/gpt-5.4"
}
```

## Permissions (hardened)

```json5
{
  "tools": {
    "profile": "custom",
    "alsoAllow": ["umbral_notion_read_page", "umbral_ping", "umbral_provider_status"],
    "deny": [
      "group:web", "umbral_research_web", "umbral_composite_research_report",
      "umbral_llm_generate", "umbral_notion_write_transcript",
      "umbral_notion_add_comment", "umbral_notion_upsert_task",
      "umbral_notion_update_dashboard", "umbral_notion_create_report_page",
      "umbral_notion_enrich_bitacora_page", "umbral_notion_poll_comments",
      "umbral_linear_create_issue", "umbral_linear_list_teams",
      "umbral_linear_update_issue_status", "umbral_worker_run",
      "umbral_worker_enqueue", "umbral_worker_task_status",
      "umbral_worker_tools_inventory", "umbral_make_post_webhook",
      "umbral_gmail_create_draft", "umbral_gmail_list_drafts",
      "umbral_google_calendar_create_event", "umbral_google_calendar_list_events",
      "umbral_figma_get_file", "umbral_figma_get_node", "umbral_figma_export_image",
      "umbral_figma_add_comment", "umbral_figma_list_comments",
      "umbral_document_create_word", "umbral_document_create_pdf",
      "umbral_document_create_presentation"
    ]
  }
}
```

### Hardening decision

Initial registration copied `rick-communication-director` tools (included `group:web`, `umbral_research_web`, `umbral_composite_research_report`, `umbral_llm_generate`). A writer agent does not need web search or research tools. Moved all web/research/write tools to deny list, kept only `umbral_notion_read_page`, `umbral_ping`, `umbral_provider_status`.

## Materialization

Files copied from repo to live workspace:

| Repo source | Live destination |
|-------------|-----------------|
| `openclaw/workspace-agent-overrides/rick-linkedin-writer/ROLE.md` | `~/.openclaw/workspaces/rick-linkedin-writer/ROLE.md` |
| `openclaw/workspace-agent-overrides/rick-linkedin-writer/AGENTS.md` | `~/.openclaw/workspaces/rick-linkedin-writer/AGENTS.md` |
| `openclaw/workspace-agent-overrides/rick-linkedin-writer/HEARTBEAT.md` | `~/.openclaw/workspaces/rick-linkedin-writer/HEARTBEAT.md` |
| `openclaw/workspace-templates/skills/linkedin-post-writer/SKILL.md` | `~/.openclaw/workspaces/rick-linkedin-writer/skills/linkedin-post-writer/SKILL.md` |
| `openclaw/workspace-templates/skills/linkedin-post-writer/LINKEDIN_WRITING_RULES.md` | `~/.openclaw/workspaces/rick-linkedin-writer/skills/linkedin-post-writer/LINKEDIN_WRITING_RULES.md` |
| `openclaw/workspace-templates/skills/linkedin-post-writer/CALIBRATION.md` | `~/.openclaw/workspaces/rick-linkedin-writer/skills/linkedin-post-writer/CALIBRATION.md` |

Gateway restarted: `systemctl --user restart openclaw-gateway`

## Smoke Test 1 — Initial

```
read_role_md: false
read_linkedin_rules: true
read_calibration: true
read_skill: true
structured_output: true
```

**Issue**: `AGENTS.md` only listed 3 mandatory reads (SKILL.md, LINKEDIN_WRITING_RULES.md, CALIBRATION.md). ROLE.md was not included.

## Fix Applied

Added `ROLE.md` as first mandatory read in `AGENTS.md`:

```markdown
1. `ROLE.md` — contrato del agente, boundaries, anti-slop blacklist, acceptance criteria.
2. `skills/linkedin-post-writer/LINKEDIN_WRITING_RULES.md` — reglas completas de David para publicaciones LinkedIn.
3. `skills/linkedin-post-writer/CALIBRATION.md` — reglas persistentes de calibracion.
4. `skills/linkedin-post-writer/SKILL.md` — workflow completo con checks de longitud, anti-slop y trazabilidad.
```

Copied updated file to live workspace. Gateway restarted.

## Smoke Test 2 — After Fix

```
read_role_md: true
read_linkedin_rules: true
read_calibration: true
read_skill: true
structured_output: true
```

All mandatory reads confirmed. Agent produces structured YAML output with `linkedin_candidate`, `x_candidate`, `length_check`, `source_trace`, `risk_flags`, `handoff_to_rick_communication_director`.

## Variant Generation

3 variants generated successfully via `openclaw agent --agent rick-linkedin-writer`:
- V-A (Operativa): 187 words
- V-B (Estrategica): 185 words
- V-C (Conversacional): 152 words

## Refinement Round

After communication director and QA review, 3 refined variants generated:
- V-A2 (Operativa pulida): 185 words — pass_with_changes (QA)
- V-B2 (Estrategica operativa): 185 words — pass (QA)
- V-C2 (Conversacional extendida): 190 words — pass_with_changes (QA)

## Estado

- Dry-run: si.
- Runtime smoke: passed after hardening.
- Mandatory reads: ROLE.md, AGENTS.md, SKILL.md, LINKEDIN_WRITING_RULES.md, CALIBRATION.md.
- Notion: confirmado por run operativo 2026-04-24. CAND-003 contiene Iteracion 2 con variantes refinadas.
- Publicado: no.
- Programado: no.
- Gates: intactos.
