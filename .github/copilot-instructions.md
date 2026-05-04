# Umbral Agent Stack — Copilot Instructions

## ⚠️ CRITICAL — Runtime lives on the VPS, not in this repo

This repository is the **source code** of services that run on a remote VPS under systemd. Editing files here does NOT apply changes to the running system. A code change is only "applied" once the VPS has pulled the new commit AND the affected service has been restarted AND a health check confirms it's healthy.

### Files whose changes require VPS deploy

| Path edited | Service to restart on VPS |
|---|---|
| `worker/**` | `systemctl restart umbral-worker` (FastAPI on `:8088`) |
| `dispatcher/**` | `systemctl restart umbral-dispatcher` |
| `openclaw/**` | `systemctl restart umbral-openclaw` (gateway) |
| `identity/**` | restart whichever service consumes it (typically worker + dispatcher) |
| `client/**` | no service restart needed if SDK is consumed by external apps; if used internally, restart consumer service |
| `config/**` | restart all services that read the changed file |
| `scripts/**` | no restart; scripts are invoked on demand |
| `tests/**`, `docs/**`, `runbooks/**`, `reports/**`, `.agents/**`, `.claude/**`, `.cursor/**` | no deploy needed (repo-only) |

### Mandatory protocol after editing a runtime file

1. Commit + push to `main` (or feature branch then PR).
2. SSH into VPS (`ssh umbral@<vps-host>`).
3. `cd /opt/umbral-agent-stack && git pull origin main`.
4. If dependencies changed (`pyproject.toml`): `source .venv/bin/activate && pip install -e .`.
5. Restart the affected service(s) per the table above.
6. Run health check (see runbook for the specific service).
7. **Only then** report the task as done.

### When this protocol does NOT apply

- Edits to `tests/`, `docs/`, `runbooks/`, `reports/`, `.agents/`, `.claude/`, `.cursor/` — repo-only.
- PRs in draft state — deploy only after merge.
- Local-only experimentation that won't be committed.

### Skill that implements this

[`.agents/skills/vps-deploy-after-edit/SKILL.md`](../.agents/skills/vps-deploy-after-edit/SKILL.md) — invocable end-to-end procedure with health-check commands per service.

---

## Project Overview

Hybrid multi-agent infrastructure for Umbral BIM. Combines OpenClaw on VPS with a Windows Worker VM, plus a roadmap for LangGraph/LiteLLM/PAD integration. This repo contains runbooks, scripts, operational docs, and the core Python codebase.

## Architecture

- **Language**: Python 91.6%, PowerShell 3%, TypeScript 2.8%, Shell 2.5%
- **Runtime**: Python with pyproject.toml (use `uv` or `pip`)
- **Core modules**: `dispatcher/`, `worker/`, `client/`, `openclaw/`, `identity/`
- **Config**: `config/` directory for consolidated settings
- **Infrastructure**: `infra/` for deployment and provisioning
- **Tests**: `tests/` directory with pytest
- **Docs**: `docs/` for operational documentation
- **Reports**: `reports/` for generated output snapshots
- **Runbooks**: `runbooks/` for operational procedures
- **Agent coordination**: `.agents/` for multi-agent mailbox protocol
- **Claude config**: `.claude/` for Claude agent settings
- **Cursor rules**: `.cursor/rules/` for Cursor IDE integration

## Multi-Agent Coordination

This repo uses a multi-agent coordination protocol. Key agents:
- **Codex** (GitHub Copilot Coding Agent): infrastructure tasks, merges
- **Claude**: refactoring, documentation, complex analysis
- **Copilot Chat**: code review, quick fixes, PR reviews

See `AGENTS.md` and `AGENT_INSTRUCTIONS.md` for the full protocol.

## Code Style & Patterns

1. **Python**: Follow PEP 8, type hints required, docstrings for public functions
2. **Imports**: Use absolute imports from project root
3. **Error handling**: Use structured logging, never bare `except:`
4. **Config**: Environment variables via `.env` (see `.env.example`)
5. **Pre-commit**: Hooks configured in `.pre-commit-config.yaml`
6. **Testing**: pytest with fixtures, tests mirror source structure
7. **Scripts**: PowerShell for Windows worker tasks, Shell for VPS operations

## Key Patterns

- **Dispatcher pattern**: Central dispatcher routes tasks to appropriate workers
- **Worker isolation**: Each worker handles specific task types independently
- **Client SDK**: `client/` provides typed interfaces for external consumers
- **OpenClaw**: Custom orchestration layer in `openclaw/`
- **Identity**: Centralized identity and auth management in `identity/`

## Branch Naming

```
codex/feat-xxx    ← New feature (via Codex)
codex/fix-xxx     ← Bug fix
claude/refactor-xxx ← Refactoring (via Claude)
copilot/docs-xxx  ← Documentation
```

## Security

- Never commit secrets or API keys
- Use `.env` for all credentials
- Service tokens must be scoped to minimum required permissions
- All external API calls must use authenticated sessions

## Related Repositories

- `umbral-bot-2`: Frontend chatbot (TypeScript/React, Lovable Cloud)
- `notion-governance`: Notion workspace governance rules and prompts
