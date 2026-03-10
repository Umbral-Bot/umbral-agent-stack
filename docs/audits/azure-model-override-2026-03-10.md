# Azure Model Override — 2026-03-10

Ejecutado por: codex

## Objetivo

Aplicar un override temporal de modelos en OpenClaw para el siguiente ciclo de pruebas:

- `rick-orchestrator` -> `azure-openai-responses/gpt-5.4-pro`
- `rick-ops` -> `azure-openai-responses/gpt-5.4`

Sin alterar autenticaciones ni el resto de prioridades.

## Estado previo

- `rick-orchestrator` -> `openai-codex/gpt-5.4`
- `rick-ops` -> `openai-codex/gpt-5.3-codex`

Provider Azure configurado en `~/.openclaw/openclaw.json`:

- `azure-openai-responses/gpt-5.2-chat`
- `azure-openai-responses/gpt-4.1`
- `azure-openai-responses/kimi-k2.5`

## Cambios aplicados

Se añadieron dos modelos al provider `azure-openai-responses`:

- `gpt-5.4`
- `gpt-5.4-pro`

Y se reasignaron solo estos agentes:

- `rick-orchestrator` -> `azure-openai-responses/gpt-5.4-pro`
- `rick-ops` -> `azure-openai-responses/gpt-5.4`

## Backup

Archivo de respaldo en VPS:

- `/home/rick/.openclaw/openclaw.json.bak.20260310-001604`

## Verificación

Smoke tests reales:

- `rick-orchestrator` respondió usando:
  - provider: `azure-openai-responses`
  - model: `gpt-5.4-pro`
- `rick-ops` respondió usando:
  - provider: `azure-openai-responses`
  - model: `gpt-5.4`

## Reversión esperada

Cuando termine este test temporal:

- `rick-orchestrator` debe volver a `openai-codex/gpt-5.4`
- `rick-ops` debe volver a `openai-codex/gpt-5.3-codex`

No hace falta quitar los modelos Azure nuevos del provider si se quieren conservar
como opciones disponibles.
