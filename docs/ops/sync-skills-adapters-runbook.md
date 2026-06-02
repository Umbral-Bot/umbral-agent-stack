# Sync skills adapters runbook

## Why this exists

Issue #445 extends the skills sync story beyond the legacy VPS-only SCP helper in `scripts/sync_skills_to_vps.py`.

For this change, we **introduced** `scripts/sync_skills_adapters.py` instead of expanding the SCP script. That keeps workstation-facing adapters (`codex`, `cursor`) isolated from live VPS transport logic, makes dry-runs deterministic, and keeps CI safely local-only.

`scripts/sync_skills_to_vps.py` remains as a compatibility entrypoint that forwards to the adapter implementation for existing tests and operator habits.

## Scope

This adapter script reads skills from:

- `openclaw/workspace-templates/skills/*/SKILL.md`

And targets:

- **Codex** → `~/.codex/skills/<slug>/SKILL.md`
- **Cursor** → `.cursor/rules/<slug>.mdc`

Out of scope:

- bulk migration from `umbral-skills-registry`
- SCP/VPS execution in CI
- gateway/env/runtime changes

## Guardrails

- `--dry-run` is the default behavior
- tests must use temp directories only
- no secrets are needed
- malformed `SKILL.md` frontmatter falls back to slug-only metadata so dry-runs stay usable
- unknown platforms are rejected by the CLI

## Usage

### Dry-run all adapters

```bash
python scripts/sync_skills_adapters.py --platform all
```

### Dry-run only Codex

```bash
python scripts/sync_skills_adapters.py --platform codex
```

### Dry-run only Cursor

```bash
python scripts/sync_skills_adapters.py --platform cursor
```

### Execute real writes

```bash
python scripts/sync_skills_adapters.py --platform all --execute
```

## Safer local testing with temp dirs

```bash
python scripts/sync_skills_adapters.py \
  --platform all \
  --skills-dir /tmp/demo-skills \
  --codex-root /tmp/demo-home/.codex/skills \
  --cursor-rules-dir /tmp/demo-workspace/.cursor/rules
```

## Output contract

The script prints a deterministic plan summary with:

- mode (`dry-run` or `execute`)
- requested platform
- total planned writes
- one stable line per target write, sorted by platform then slug
- content hash preview (`sha256` prefix)

That stable ordering is what makes repeated dry-runs idempotent in CI and local QA.

## Failure modes

### Unknown platform

Argparse rejects anything outside:

- `codex`
- `cursor`
- `all`

### Empty skills dir

The command exits `0` and prints `planned_writes=0` plus `No skills found.`

### Malformed frontmatter

The command stays usable in dry-run mode:

- `name` falls back to the directory slug
- `description` becomes empty
- adapter output remains deterministic

This keeps CI fixtures and partial skills from breaking the whole plan while still surfacing the degraded metadata in the output/JSON.

## Verification

Targeted test command:

```bash
python -m pytest tests/ -k sync_skills -q
```

The test suite covers:

- unknown platform rejection
- empty skills directory
- malformed frontmatter
- deterministic dry-run output
- Codex + Cursor output generation with temp dirs only
