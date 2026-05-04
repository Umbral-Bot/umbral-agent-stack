# Umbral Agent Stack — Copilot Instructions

## ⚠️ CRITICAL — Runtime lives on the VPS, not in this repo

This repository is the **source code** of services that run on a remote VPS under systemd. Editing files here does NOT apply changes to the running system. A code change is only "applied" once the VPS has pulled the new commit AND the affected service has been restarted AND a health check confirms it's healthy.

### Files whose changes require VPS deploy

| Path edited | Service to restart on VPS |
|---|---|
| `worker/**` | `systemctl --user restart umbral-worker` (FastAPI on `127.0.0.1:8088`) |
| `dispatcher/**` | `systemctl --user restart openclaw-dispatcher` |
| `openclaw/**` | ⚠️ NO automatic mapping. The running `openclaw-gateway.service` is an **npm-global binary** (`openclaw-gateway --port 18789`), it does NOT consume code from `openclaw/**` in this repo. Edits here only affect runtime if/when the gateway is re-pointed to repo code. |
| `identity/**` | restart whichever service consumes it (typically `umbral-worker` and/or `openclaw-dispatcher`) |
| `client/**` | no restart needed if SDK is consumed by external apps; if used internally, restart consumer service |
| `config/**` | restart all services that read the changed file |
| `scripts/**` | no restart; scripts are invoked on demand |
| `tests/**`, `docs/**`, `runbooks/**`, `reports/**`, `.agents/**`, `.claude/**`, `.cursor/**` | no deploy needed (repo-only) |

### Mandatory protocol after editing a runtime file

1. Commit + push to `main` (or feature branch then PR).
2. SSH into VPS as the runtime user (`ssh rick@<vps-host>`).
3. `cd /home/rick/umbral-agent-stack && git pull origin main`.
4. If dependencies changed (`pyproject.toml`): `source .venv/bin/activate && pip install -e .`.
5. Restart the affected service(s) per the table above using `systemctl --user restart <service>` (NOT `sudo` — services run as user units under `/home/rick/.config/systemd/user/`).
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

## VPS Reality Check Rule (CRITICAL — added 2026-05-04)

**El repo refleja intención; la VPS refleja realidad. NUNCA declarar un cron, health, runtime, deploy o servicio como "broken" o "fixed" basado solo en lectura del repo.**

Antes de afirmar el estado de cualquier componente runtime (cron jobs, systemd units, OpenClaw gateway, Worker, Dispatcher, Granola pipeline, writers a Notion, headers/dashboards refrescados por job, etc.), DEBES verificar en la VPS real:

```bash
# Patrones mínimos según el componente:
# Cron / scheduling
ssh rick@<vps> "crontab -l && systemctl list-timers --all | grep -i <pattern>"
ssh rick@<vps> "sudo journalctl -u <unit> --since '24 hours ago' | tail -100"

# OpenClaw / gateway
ssh rick@<vps> "openclaw status --all && openclaw models status"
ssh rick@<vps> "bash ~/umbral-agent-stack/scripts/vps/verify-openclaw.sh"

# Logs de pipeline (Granola, etc.)
ssh rick@<vps> "tail -200 ~/.config/umbral/ops_log.jsonl | jq 'select(.event | startswith(\"<prefix>\"))'"

# Worker / health endpoints
ssh rick@<vps> "curl -fsS http://127.0.0.1:8088/health"
```

**Reglas operativas:**

1. Si la tarea menciona un cron stale, dashboard zombi, header desactualizado, agente que no escribe, etc.: la PRIMERA acción es SSH a la VPS, NO `grep` en el repo.
2. El repo puede tener un script o ADR que diga "corre cada hora" — eso describe la intención de diseño, no el estado actual. Verificar el cron/timer real y el log real.
3. Cuando reportes hallazgos, separa explícitamente: **"Repo dice X"** vs **"VPS muestra Y"**. Si difieren, la divergencia ES el hallazgo principal.
4. Si no tienes acceso SSH en una sesión dada, declarar el límite y NO inventar el estado runtime. Pedir a David que ejecute el check o delegar vía mailbox.
5. Esta regla aplica especialmente a investigaciones de zombi processes, cron drift, header refresh failures y cualquier debate "¿está corriendo o no?".

**Antipatrón bloqueado:** "Leí el archivo `xxx.sh` en el repo y el cron debería correr cada hora, así que el problema es Z." — Esto NO es una verificación, es una hipótesis. La verificación requiere `journalctl`/`systemctl`/`tail log` en la VPS.

## Related Repositories

- `umbral-bot-2`: Frontend chatbot (TypeScript/React, Lovable Cloud)
- `notion-governance`: Notion workspace governance rules and prompts
