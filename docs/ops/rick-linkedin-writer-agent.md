# Rick LinkedIn Writer — Implementation

> **Status**: runtime-registered, read-only, dry-run. No autonomous routing, no Notion writes, no publication, no human gate mutation.

## Purpose

`rick-linkedin-writer` is the first-pass LinkedIn/X editorial drafting agent for the Umbral source-driven editorial flow. It receives a candidate payload with an AEC/BIM context frame and produces structured LinkedIn/X drafts for voice calibration and QA.

## Decision

Create a new agent and skill instead of extending existing ones.

| Existing skill | Fit | Decision |
|----------------|-----|----------|
| `linkedin-content` | Strategy, algorithm, hooks, templates | Not a writing workflow with structured handoff |
| `linkedin-david` | David-specific templates, tone, format | Not a structured editorial workflow |
| `editorial-source-curation` | Source fetch, normalize, score | Upstream skill, not a writer |
| `bim-coordination` | Technical BIM (clash, BCF) | Not editorial |
| `director-comunicacion-umbral` | Voice calibration | Downstream, not primary drafter |

The gap: no existing skill contains David's full LinkedIn writing rules, enforces length policy, requires calibration reading, or provides structured handoff output.

## Repo-side files

| File | Purpose |
|------|---------|
| `openclaw/workspace-templates/skills/linkedin-post-writer/SKILL.md` | Workflow with 9 steps |
| `openclaw/workspace-templates/skills/linkedin-post-writer/LINKEDIN_WRITING_RULES.md` | David's full rules (verbatim from `docs/ops/linkedin-writing-rules-source.md`) |
| `openclaw/workspace-templates/skills/linkedin-post-writer/CALIBRATION.md` | Persistent calibration rules |
| `openclaw/workspace-agent-overrides/rick-linkedin-writer/ROLE.md` | Agent contract |
| `openclaw/workspace-agent-overrides/rick-linkedin-writer/AGENTS.md` | Workspace bootstrap with mandatory reads |
| `openclaw/workspace-agent-overrides/rick-linkedin-writer/HEARTBEAT.md` | Agent heartbeat |

## Phase 1 authority

Allowed:

- Read candidate payloads and AEC/BIM context frames.
- Generate LinkedIn/X drafts.
- Apply writing rules and calibration.
- Verify source traceability.
- Deliver structured handoff to `rick-communication-director`.

Prohibited:

- Publishing.
- Marking `aprobado_contenido`.
- Marking `autorizar_publicacion`.
- Changing gates.
- Writing to Notion.
- Inventing AEC/BIM angle.
- Adding sources not in payload.
- Inventing claims.
- Creating autonomous routing.

## Canonical flow position

```text
1. sources / signals
2. source curation and candidate payload
3. AEC/BIM context framing
4. LinkedIn draft writing               <-- rick-linkedin-writer
5. communication direction / voice       <-- rick-communication-director
6. editorial QA                          <-- rick-qa
7. Notion draft registration
8. David review
9. human content approval
10. human publication authorization
```

## Runtime materialization

Materialized 2026-04-24. Permissions hardened (minimal alsoAllow, 29 deny entries). See `cand-003-linkedin-writer-runtime-smoke.md` for full evidence.

Commands used:

```bash
mkdir -p ~/.openclaw/workspaces/rick-linkedin-writer/skills/linkedin-post-writer

cp openclaw/workspace-agent-overrides/rick-linkedin-writer/ROLE.md \
   ~/.openclaw/workspaces/rick-linkedin-writer/ROLE.md

cp openclaw/workspace-agent-overrides/rick-linkedin-writer/AGENTS.md \
   ~/.openclaw/workspaces/rick-linkedin-writer/AGENTS.md

cp openclaw/workspace-agent-overrides/rick-linkedin-writer/HEARTBEAT.md \
   ~/.openclaw/workspaces/rick-linkedin-writer/HEARTBEAT.md

cp openclaw/workspace-templates/skills/linkedin-post-writer/SKILL.md \
   ~/.openclaw/workspaces/rick-linkedin-writer/skills/linkedin-post-writer/SKILL.md

cp openclaw/workspace-templates/skills/linkedin-post-writer/LINKEDIN_WRITING_RULES.md \
   ~/.openclaw/workspaces/rick-linkedin-writer/skills/linkedin-post-writer/LINKEDIN_WRITING_RULES.md

cp openclaw/workspace-templates/skills/linkedin-post-writer/CALIBRATION.md \
   ~/.openclaw/workspaces/rick-linkedin-writer/skills/linkedin-post-writer/CALIBRATION.md
```

Then register in `~/.openclaw/openclaw.json` following `rick-communication-director` pattern.

Restart gateway: `systemctl --user restart openclaw-gateway`
