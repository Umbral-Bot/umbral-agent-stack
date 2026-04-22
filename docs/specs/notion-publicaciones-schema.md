# Notion Publicaciones — Schema Spec

Executable schema specification for the `Publicaciones` Notion database.
**This spec does NOT create the DB in Notion.** It defines the structure
locally for validation, tooling, and future provisioning.

## What this does

- Defines all properties (name, type, options, constraints).
- Documents the state machine (Idea → Borrador → ... → Publicado).
- Documents two human gates (`aprobado_contenido`, `autorizar_publicacion`)
  and the gate invalidation mechanism.
- Documents invariants (no publish without gates, no publish_success
  without platform confirmation, etc.).
- Documents recommended views (Kanban, by channel, gates invalidados).
- Provides a Python loader/validator and CLI.

## What this does NOT do

- **No Notion API calls.** The DB is not created or modified.
- **No runtime activation.** No crons, webhooks, or workflows.
- **No publishing.** No Ghost, LinkedIn, X, or newsletter integration.
- **No content generation.** No posts or assets created.

## Files

| File | Purpose |
|------|---------|
| `notion/schemas/publicaciones.schema.yaml` | Schema spec (YAML) |
| `infra/notion_schema.py` | Loader and structural validator |
| `scripts/validate_notion_schema.py` | CLI: validate and summarize |
| `tests/test_notion_publicaciones_schema.py` | Tests |

## Key decisions encoded

| Decision | Value | Source |
|----------|-------|--------|
| Single DB | `Publicaciones` (no separate Assets DB in v1) | David |
| Channels | blog, linkedin, x, newsletter | ADR-005 |
| Human gates | `aprobado_contenido` + `autorizar_publicacion` | Spec v1 |
| Gate invalidation | Comment post-approval → gate_invalidado = true | Spec v1 |
| Content hash | SHA-256/16 for idempotency | Spec v1 |
| Visual assets | Inline (Visual brief, URL, HITL flag) | UA-13 |
| Source tracking | Fuente primaria (URL) + Fuente referente (URL) + Fuentes confiables (relation) | UA-01/02 |
| LinkedIn/X HITL | autorizar_publicacion required | ADR-005 |
| Blog v1 | Ghost | David |

## Running validation

```bash
python scripts/validate_notion_schema.py
```

Output:
```
Schema: notion/schemas/publicaciones.schema.yaml
  Database: Publicaciones v0.1.0 (draft)
  Properties: 22 (5 required)
  ...
  Invariants: 7
  Recommended views: 5

Validation passed.
```

## Running tests

```bash
python -m pytest tests/test_notion_publicaciones_schema.py -q
```

## State machine

```
Idea → Borrador → Revisión pendiente → Aprobado → Autorizado → Publicando → Publicado
                   ↑                     |            |
                   ├─────────────────────┘            |
                   ├──────────────────────────────────┘
                   │ (gate invalidation on comment)
                   
  Idea/Borrador/Revisión pendiente → Descartado
```

Key transitions:
- **Aprobado → Revisión pendiente**: David comments after approval → gate
  invalidation, must re-approve.
- **Publicando → Autorizado**: publish_failed → stays in Autorizado, does
  not advance to Publicado.
- **Publicando → Publicado**: only on publish_success with
  platform_post_id confirmed.

## Parent policy

The DB should live under `Sistema Editorial Automatizado Umbral` page.
It must NOT be placed under Control Room, Bandeja de revisión, or other
operational DBs.

## Adding properties

1. Edit `notion/schemas/publicaciones.schema.yaml`.
2. Add the property under `properties:` with name, type, description.
3. Run `python scripts/validate_notion_schema.py` to verify.
4. Run tests to confirm structure.
5. Document the decision context in the property description.

## Future: provisioning

When ready to create the DB in Notion:
1. Schema status changes from `draft` to `ready`.
2. A provisioning script reads the schema and creates the DB via
   Notion API.
3. The script respects `parent_policy` and `forbidden_parents`.
4. This is NOT in scope for this PR.
