# Prompt inicial para el GPT

```text
Audita el agente `rick-communication-director`.

Trabaja en modo solo lectura.

Fuentes minimas:
- `openclaw/workspace-agent-overrides/rick-communication-director/ROLE.md`
- `openclaw/workspace-agent-overrides/rick-communication-director/HEARTBEAT.md`
- `openclaw/workspace-templates/skills/director-comunicacion-umbral/SKILL.md`
- `docs/ops/rick-communication-director-agent.md`
- `openclaw/workspace-templates/AGENTS.md`
- `scripts/sync_openclaw_workspace_governance.py`
- `docs/openclaw-config-reference-2026-03.json5`
- `docs/03-setup-vps-openclaw.md`
- Guia Editorial y Voz de Marca, si esta accesible.

Entrega:
1. Estado real: que esta implementado repo-side, que falta para runtime vivo y que NO esta activado.
2. Riesgos de autoridad, permisos, handoffs y QA.
3. Si el agente puede corregir el problema de CAND-003 o si falta configuracion adicional.
4. Cambios concretos recomendados a ROLE.md, SKILL.md, AGENTS.md, runbooks o config reference.
5. Prompt para Codex/Copilot que aplique esos cambios en branch draft.
6. Criterios de aceptacion para que David valide el agente.

No publiques.
No marques gates humanos.
No modifiques Notion.
No modifiques repos.
No actives runtime.
```
