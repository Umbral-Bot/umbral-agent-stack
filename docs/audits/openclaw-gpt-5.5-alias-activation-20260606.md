# OpenClaw alias activation — `azure-openai-responses/gpt-5.5`

- **Fecha:** 2026-06-06
- **Autorización:** David — "ok, activa alias"
- **Precondición:** [`foundry-gpt-5.5-audit-20260606.md`](./foundry-gpt-5.5-audit-20260606.md) → PASS
- **Superficie:** VPS (`vps-umbral`, usuario `rick`)

## Cambio aplicado

Patch mínimo en `~/.openclaw/openclaw.json`:

1. Agregado modelo `gpt-5.5` en `models.providers["azure-openai-responses"].models[]` (patrón `gpt-5.4`, reasoning=true, contextWindow 400k).
2. Agregado allowlist UI `agents.defaults.models["azure-openai-responses/gpt-5.5"]: {}`.
3. **Sin cambios** en `agents.defaults.model.primary` ni en `agents.list[*].model`.

## Backup

`/home/rick/.openclaw/openclaw.json.bak.20260606-085516`

## Rollback

```bash
cp -a /home/rick/.openclaw/openclaw.json.bak.20260606-085516 ~/.openclaw/openclaw.json
systemctl --user restart openclaw-gateway.service
```

## Verificación

| Check | Resultado |
|---|---|
| `openclaw models list` incluye `azure-openai-responses/gpt-5.5` | PASS |
| `systemctl --user is-active openclaw-gateway.service` | active |
| Smoke alias nuevo (`--model azure-openai-responses/gpt-5.5`) | PASS — output `PASS`, provider `azure-openai-responses`, model `gpt-5.5` |
| Smoke alias existente (`--model azure-openai-responses/gpt-5.4`) | PASS — output `OK` |

## Estado post-activación

- **Default global:** sigue `azure-openai-responses/gpt-5.4`
- **Agentes Rick:** sin promoción a 5.5 (pendiente Prompt 3 / soak editorial)
- **Magnific MCP:** timeout OAuth pendiente (no bloquea el alias 5.5)

## Próximo paso opcional

Promover agentes (`rick-orchestrator`, `rick-editorial`, `rick-qa`, etc.) a `gpt-5.5` solo con autorización explícita tras soak.
