# OpenClaw revert — OAuth only (sin Azure AI Foundry)

- **Fecha:** 2026-07-12
- **Autorización:** David — urgente: quitar todos los LLM de AI Foundry; solo ChatGPT vía OAuth
- **Superficie:** VPS (`vps-umbral`, usuario `rick`)

## Contexto

Desde la promoción 2026-06-07 todos los agentes usaban `azure-openai-responses/gpt-5.5` con `thinkingDefault: xhigh`. David solicita reversión inmediata a provider `openai-codex` (OAuth ChatGPT Plus).

## Cambio

Script: `scripts/vps/patch-openclaw-oauth-only.py`

| Campo | Antes (documentado) | Después |
|---|---|---|
| `models.providers.azure-openai-responses` | presente | **eliminado** |
| `agents.defaults.model.primary` | `azure-openai-responses/gpt-5.5` | `openai-codex/gpt-5.4` |
| `agents.defaults.model.fallbacks` | incluye Foundry | solo `openai/*` / `openai-codex/*` |
| **`main` (Rick)** | Foundry 5.5 | **`openai/gpt-5.6-sol`** |
| Agentes heavy (orchestrator, comms, linkedin) | Foundry 5.5 | `openai-codex/gpt-5.4` |
| Agentes light (delivery, qa, ops, tracker) | Foundry 5.5 | `openai-codex/gpt-5.3-codex` |
| `thinkingDefault` global `xhigh` | presente | **removido** |

Env: comentar `AZURE_OPENAI_*` y `KIMI_AZURE_API_KEY` en `~/.config/openclaw/env` y `~/.openclaw/.env`.

## Ejecución VPS

```bash
cd ~/umbral-agent-stack && git pull origin main
python3 scripts/vps/patch-openclaw-oauth-only.py
openclaw doctor --fix
systemctl --user restart openclaw-gateway.service
openclaw models status --probe-provider openai
openclaw agent --agent main --model openai/gpt-5.6-sol --message "PASS-GPT56-SOL" --timeout 180
```

## Verificación

| Check | Esperado |
|---|---|
| `openclaw models list` sin `azure-openai-responses/*` | PASS |
| `main.model.primary` = `openai/gpt-5.6-sol` | PASS |
| Probe `openai` OAuth | PASS |
| Smoke agent `main` con 5.6-sol | PASS |

## Rollback

Restaurar backup `openclaw.json.bak.oauth-only.*` generado por el script.

## Fuera de alcance (esta urgencia)

- Worker/Dispatcher `azure_foundry` en `quota_policy.yaml` — sigue independiente de OpenClaw gateway
- `config/editorial-model.yaml` — requiere cambio separado si editorial debe dejar Foundry
