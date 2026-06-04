# Obsidian Context Vault

Status: v0 design + local mirror check.

## Decision

Use Obsidian as a complementary context vault, not as the source of truth.

| Surface | Role |
|---|---|
| Repo | Technical source of truth: code, tests, ADRs, runbooks, tasks. |
| Notion | Human HITL surface: decisions, tasks, dashboards, publication approval. |
| Obsidian | Private context graph: distilled notes, decisions, meeting digests, research maps. |

## Recommended topology

```text
Windows Obsidian app
  -> private Git repository for the vault
  -> VPS git pull mirror, pull-only
  -> agents read markdown context
```

The VPS mirror should be treated as read-only operational input. It should not
push edits back to the vault in v0.

## Required vault folders

```text
00_inbox/
10_decisiones/
20_reuniones/
30_investigacion/
40_runbooks/
90_evals/
```

The checker also accepts the previous English/hyphen names for compatibility
with early mirrors: `00-inbox`, `10-decisions`, `20-meetings`, `30-research`,
`40-runbooks`, `90-evals`.

## Environment

```bash
export OBSIDIAN_VAULT_PATH=/srv/umbral-obsidian-vault
export OBSIDIAN_SYNC_MODE=pull-only
```

Do not store API keys, OAuth files, private keys, browser sessions, or
application tokens in the vault or repo.

## VPS setup prompt for Copilot-VPS

Use this only after the repo branch with this runbook is merged or otherwise
available on the VPS.

```text
Sos Copilot-VPS. Configura mirror read-only de Obsidian para Umbral.

Preflight repo:
cd ~/umbral-agent-stack
git fetch origin main
git checkout main
git pull --ff-only origin main
git log -1 --oneline
test -f docs/ops/obsidian-context-vault.md && echo OBSIDIAN_RUNBOOK_OK || echo OBSIDIAN_RUNBOOK_MISSING

Objetivo:
- Clonar el repo privado del vault autorizado por David en ~/umbral-obsidian-vault
- Si ya existe, hacer git pull --ff-only
- Dejar el mirror en modo pull-only operacional
- No imprimir tokens ni credenciales GitHub
- No configurar ningun writer desde VPS hacia el vault

Checks:
export OBSIDIAN_VAULT_PATH=$HOME/umbral-obsidian-vault
export OBSIDIAN_SYNC_MODE=pull-only
git -C "$OBSIDIAN_VAULT_PATH" status --short --branch
python scripts/obsidian_context_check.py --vault-path "$OBSIDIAN_VAULT_PATH" --require-pull-only

Entrega:
- VEREDICTO: OBSIDIAN_CONTEXT_GIT_MIRROR_OK o OBSIDIAN_CONTEXT_GIT_MIRROR_BLOCKED
- Salida redacted de git status/log
- Salida de obsidian_context_check.py
- Cualquier comando systemd/user timer creado, si aplica
```

## Local check

```powershell
$env:OBSIDIAN_VAULT_PATH="C:\Users\david\Documents\Umbral-Knowledge"
$env:OBSIDIAN_SYNC_MODE="pull-only"
python scripts/obsidian_context_check.py --vault-path $env:OBSIDIAN_VAULT_PATH --require-pull-only
```

## Security rules

- Do not place `.env`, private keys, browser session files, or OAuth token files
  in the vault.
- If the vault is versioned with Git, ignore `.obsidian/workspace.json` and
  `.obsidian/workspaces.json`.
- Obsidian notes may inform agent context, but repo changes still go through PR.

## References

- Obsidian data storage: https://help.obsidian.md/data-storage
- Obsidian Headless Sync: https://help.obsidian.md/sync/headless
- Obsidian Sync security: https://help.obsidian.md/sync/security
- Obsidian plugin security: https://help.obsidian.md/plugin-security
