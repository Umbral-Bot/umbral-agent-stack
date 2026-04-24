# Knowledge Manifest

## Conectores recomendados

Habilitar en modo lectura:

- GitHub: `umbral-agent-stack`, `umbral-agent-stack-codex-coordinador`, `notion-governance`, `umbral-bot-2`, `umbral-bim`.
- Notion: Guia Editorial y Voz de Marca, Publicaciones, Control Room, runbooks, decisiones operativas.
- Google Drive: carpetas transversales de Marca Personal, Consultor, Docente V4 y Make LLMs V3.

No habilitar escritura por defecto.

## Fuentes repo prioritarias

- `AGENTS.md`
- `.agents/PROTOCOL.md`
- `.agents/board.md`
- `openclaw/workspace-agent-overrides/*/ROLE.md`
- `openclaw/workspace-agent-overrides/*/HEARTBEAT.md`
- `openclaw/workspace-templates/AGENTS.md`
- `openclaw/workspace-templates/skills/*/SKILL.md`
- `scripts/sync_openclaw_workspace_governance.py`
- `docs/openclaw-config-reference-2026-03.json5`
- `docs/03-setup-vps-openclaw.md`
- `docs/70-agent-governance.md`
- `docs/71-supervisor-routing-contract.md`
- `docs/72-ambiguous-improvement-task-detection.md`
- `docs/73-supervisor-resolution-contract.md`
- `docs/74-closed-ooda-loop-contract.md`
- `docs/75-improvement-supervisor-activation-playbook.md`
- `docs/76-supervisor-observability-monitoring.md`
- `docs/77-improvement-supervisor-phase6-activation-plan.md`

## Fuentes especificas para `rick-communication-director`

- `openclaw/workspace-agent-overrides/rick-communication-director/ROLE.md`
- `openclaw/workspace-agent-overrides/rick-communication-director/HEARTBEAT.md`
- `openclaw/workspace-templates/skills/director-comunicacion-umbral/SKILL.md`
- `docs/ops/rick-communication-director-agent.md`
- `docs/ops/rick-editorial-candidate-payload-template.md`
- `docs/ops/editorial-source-attribution-policy.md`
- `docs/ops/cand-002-*`
- `docs/ops/cand-003-*`

## Fuentes Drive recomendadas

- `G:\Mi unidad\06_Sistemas y Automatizaciones\01_Agentes y Dominios\Transversales\Marca Personal`
- `G:\Mi unidad\06_Sistemas y Automatizaciones\01_Agentes y Dominios\Transversales\Consultor`
- `G:\Mi unidad\06_Sistemas y Automatizaciones\01_Agentes y Dominios\Transversales\Docente\V4`
- `G:\Mi unidad\06_Sistemas y Automatizaciones\01_Agentes y Dominios\Transversales\Make LLMs\V3`

## Fuentes Notion recomendadas

- Guia Editorial y Voz de Marca:
  `https://www.notion.so/umbralbim/Gu-a-Editorial-y-Voz-de-Marca-0192ad1f3ca144ae954d0b738261258e`
- DB Publicaciones.
- Paginas CAND-002 y CAND-003.
- Runbooks o decisiones operativas sobre Rick/OpenClaw.

## Regla de ausencia de fuente

Si una fuente no esta accesible, el GPT debe decirlo y bajar confianza. No debe simular que leyo la Guia Editorial viva si solo recibio un resumen.
