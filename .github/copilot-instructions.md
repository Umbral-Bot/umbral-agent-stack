# Umbral Agent Stack — Copilot Instructions

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
