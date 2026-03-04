---
id: "039"
title: "OpenClaw Skills: LLM Generate + Make Webhook + Observability"
assigned_to: copilot
branch: feat/copilot-skills-llm-make-obs
round: 9
status: assigned
created: 2026-03-04
---

## Objetivo

Crear OpenClaw workspace skills para las tasks de LLM, Make.com webhook y observabilidad del sistema.

## Contexto

- Los skills se colocan en `openclaw/workspace-templates/skills/<nombre>/SKILL.md`
- Referencia de formato: `openclaw/workspace-templates/skills/figma/SKILL.md`
- Cada skill tiene YAML frontmatter (name, description, metadata) + Markdown con instrucciones

## Skills a crear

### 1. `openclaw/workspace-templates/skills/llm-generate/SKILL.md`

Task: `llm.generate`

Documentar:
- Input: `prompt`, `model` (opcional), `max_tokens`, `temperature`, `system_prompt`
- Providers disponibles y su auto-detección:
  - `openclaw_proxy` → Claude vía OpenClaw gateway (OPENCLAW_GATEWAY_TOKEN)
  - `anthropic` → Claude directo (ANTHROPIC_API_KEY)
  - `azure_foundry` → GPT vía Azure OpenAI (AZURE_OPENAI_ENDPOINT + KEY)
  - `openai` → GPT directo (OPENAI_API_KEY)
  - `gemini` → Gemini via AI Studio (GOOGLE_API_KEY)
  - `vertex` → Gemini via Vertex AI (GOOGLE_API_KEY_RICK_UMBRAL)
- Aliases de modelo: `claude_pro`, `gemini_pro`, `gemini_flash`, etc.
- Ejemplo de uso con cada provider
- Requiere: al menos uno de los API keys mencionados
- Triggers: "generate text", "ask llm", "use claude", "use gemini", "generate with gpt"
- Referencia: `worker/tasks/llm.py`, `docs/15-model-quota-policy.md`

### 2. `openclaw/workspace-templates/skills/make-webhook/SKILL.md`

Task: `make.post_webhook`

Documentar:
- Input: `webhook_url`, `payload` (dict)
- Descripción: envía POST a un webhook de Make.com para triggear escenarios
- Requiere: URL del webhook (no necesita API key global, cada webhook tiene su URL)
- Triggers: "trigger make scenario", "post to make", "webhook make.com"
- Referencia: `worker/tasks/make_webhook.py`

### 3. `openclaw/workspace-templates/skills/observability/SKILL.md`

Tasks: `system.ooda_report`, `system.self_eval`

Documentar:
- `system.ooda_report`: genera reporte OODA (Observe, Orient, Decide, Act) del estado del sistema
  - Input: vacío o `{}`
  - Output: reporte con estado de tasks, workers, providers
- `system.self_eval`: auto-evaluación del rendimiento de Rick
  - Input: `period` (opcional, ej. "last_24h")
  - Output: métricas de éxito, errores, tiempos
- Requiere: WORKER_TOKEN, REDIS_URL
- Triggers: "system report", "ooda report", "self evaluation", "how am I doing", "system status"
- Referencia: `worker/tasks/observability.py`, `scripts/ooda_report.py`

## Instrucciones

```bash
git pull origin main
git checkout -b feat/copilot-skills-llm-make-obs

# Crear los 3 skills
# Verificar frontmatter:
python -c "import yaml; [yaml.safe_load(open(f'openclaw/workspace-templates/skills/{s}/SKILL.md').read().split('---')[1]) for s in ['llm-generate','make-webhook','observability']]"

git add .
git commit -m "feat: openclaw skills for llm-generate, make-webhook, observability"
git push -u origin feat/copilot-skills-llm-make-obs
gh pr create --title "feat: openclaw skills — llm, make, observability" --body "SKILL.md for llm.generate, make.post_webhook, system.ooda_report, system.self_eval"
```

## Criterio de éxito

- 3 SKILL.md creados con frontmatter YAML válido
- Formato consistente con `skills/figma/SKILL.md`
- Todas las tasks listadas con input/output documentado
- Providers de LLM correctamente documentados con su lógica de detección
