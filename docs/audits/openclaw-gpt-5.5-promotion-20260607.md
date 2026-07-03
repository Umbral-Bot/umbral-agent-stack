# OpenClaw promotion — `gpt-5.5` + `xhigh` thinking

- **Fecha:** 2026-06-07
- **Autorización:** David — promover agentes a GPT 5.5 Azure con extra high; tracker con thinking menor
- **Superficie:** VPS (`vps-umbral`, usuario `rick`)

## Contexto

- `/model azure-openai-responses/gpt-5.5` en Telegram es **solo sesión**; no modifica `openclaw.json`.
- El dashboard OpenClaw puede cambiar modelo por sesión; sin patch en JSON, `/reset` o sesión nueva vuelve al default anterior.
- El alias `azure-openai-responses/gpt-5.5` ya existía desde 2026-06-06 ([`openclaw-gpt-5.5-alias-activation-20260606.md`](./openclaw-gpt-5.5-alias-activation-20260606.md)).

## Cambio aplicado

Patch en `~/.openclaw/openclaw.json`:

| Campo | Antes | Después |
|---|---|---|
| `agents.defaults.model.primary` | `azure-openai-responses/gpt-5.4` | `azure-openai-responses/gpt-5.5` |
| `agents.defaults.thinkingDefault` | *(ausente)* | `xhigh` |
| Todos los agentes `model.primary` | `gpt-5.4` o Gemini (orchestrator/tracker) | `azure-openai-responses/gpt-5.5` |
| `thinkingDefault` por agente | *(ausente)* | `xhigh` (excepto tracker) |
| `rick-tracker.thinkingDefault` | — | `medium` |

### Agentes

| Agente | Modelo | Thinking |
|---|---|---|
| main | `azure-openai-responses/gpt-5.5` | `xhigh` |
| rick-orchestrator | `azure-openai-responses/gpt-5.5` | `xhigh` |
| rick-delivery | `azure-openai-responses/gpt-5.5` | `xhigh` |
| rick-qa | `azure-openai-responses/gpt-5.5` | `xhigh` |
| rick-ops | `azure-openai-responses/gpt-5.5` | `xhigh` |
| rick-communication-director | `azure-openai-responses/gpt-5.5` | `xhigh` |
| rick-linkedin-writer | `azure-openai-responses/gpt-5.5` | `xhigh` |
| rick-tracker | `azure-openai-responses/gpt-5.5` | `medium` |

Fallback principal conservado: `azure-openai-responses/gpt-5.4`.

## Backup

`/home/rick/.openclaw/openclaw.json.bak.20260607-gpt55-promo`

Script reutilizable: `scripts/vps/patch-openclaw-gpt55-xhigh.py`

## Rollback

```bash
cp -a ~/.openclaw/openclaw.json.bak.20260607-gpt55-promo ~/.openclaw/openclaw.json
systemctl --user restart openclaw-gateway.service
```

## Verificación

| Check | Resultado |
|---|---|
| JSON válido | PASS |
| `openclaw models list` → default `azure-openai-responses/gpt-5.5` | PASS |
| `systemctl --user is-active openclaw-gateway.service` | active |
| Smoke `openclaw agent --agent main --model azure-openai-responses/gpt-5.5` | PASS — `PASS-GPT55` |

## Notas operativas

- Sesiones Telegram **ya abiertas** pueden conservar override de modelo/thinking de la sesión. Para heredar el nuevo default: `/model default` y `/think default`, o `/reset`.
- `xhigh` en OpenClaw mapea a `extra-high` / `extra high` en UI y comandos (`/think:xhigh`).
- `rick-tracker` quedó en `medium` por tareas de trazabilidad/Linear (menor coste de reasoning).
