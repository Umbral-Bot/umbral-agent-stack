# Editorial model contract — GPT-5.5 via OpenClaw

Estado: **CANÓNICO** para producción editorial Rick/UmbralBIM (2026-06-29).

## Requisito

Toda **generación o re-redacción editorial** (LinkedIn, Blog, X, voice pass, QA con rewrite)
debe usar:

| Campo | Valor |
|-------|--------|
| Provider | `azure-openai-responses` |
| Model | `gpt-5.5` |
| Model ID | `azure-openai-responses/gpt-5.5` |
| Thinking (editorial) | `xhigh` |
| Thinking (rick-tracker) | `medium` |

Fuente repo: `config/editorial-model.yaml`

## Mapping alias OpenClaw

| Alias / path | Resuelve a |
|--------------|------------|
| `azure-openai-responses/gpt-5.5` | Deployment Foundry `gpt-5.5` (Responses API) |
| `openclaw/main` | `agents.defaults.model.primary` en `~/.openclaw/openclaw.json` |
| `openclaw agent --model azure-openai-responses/gpt-5.5` | Invocación explícita (preferida para micro-fixes) |

Activación alias: `docs/audits/openclaw-gpt-5.5-alias-activation-20260606.md`  
Promoción agentes: `docs/audits/openclaw-gpt-5.5-promotion-20260607.md`  
Patch VPS: `scripts/vps/patch-openclaw-gpt55-xhigh.py`

## Agentes editoriales

Deben tener `model.primary = azure-openai-responses/gpt-5.5`:

- `rick-orchestrator`
- `rick-linkedin-writer`
- `rick-communication-director`
- `rick-qa`
- `main` (default gateway para `stage7_5_copy_writer`)

`rick-editorial` permanece design-only; orchestrator + communication-director cubren redacción.

## Guardrail repo-side

```bash
python -c "from scripts.editorial.editorial_model_guard import assert_editorial_model; assert_editorial_model('azure-openai-responses/gpt-5.5')"
```

En VPS antes de aplicar copy:

```bash
python scripts/editorial/apply_publication_copy.py --publication-id CAND-001 --verify-openclaw ~/.openclaw/openclaw.json
```

Si el modelo no es 5.5: **fallar explícito** (`EditorialModelError`). Sin fallback silencioso a 5.4/Gemini.

## Anti-patrón detectado (CAND-001 Fase 4)

Copilot Chat escribiendo copy directamente **no garantiza** GPT-5.5. Para versiones finales usar:

```bash
openclaw agent --agent rick-communication-director \
  --model azure-openai-responses/gpt-5.5 \
  --message "..."
```

O aplicar copy canónico desde `evals/editorial/cand-001-final-copy.yaml`.
