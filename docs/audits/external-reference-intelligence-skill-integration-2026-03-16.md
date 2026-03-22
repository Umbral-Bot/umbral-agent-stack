# External Reference Intelligence Skill Integration — 2026-03-16

## Objetivo

Evaluar la skill compartida `Rick-David/Skills/external-reference-intelligence`, decidir si servia tal cual para Rick y dejar una version oficial, validada y desplegada en el stack real.

## Diagnostico

La skill compartida estaba bien orientada conceptualmente, pero no convenia usarla tal cual por estas razones:

1. tenia problemas de encoding y mojibake en `description` y `emoji`
2. no estaba integrada al arbol oficial de skills del repo
3. no estaba priorizada en `AGENTS.md`
4. no estaba alineada del todo con el flujo real ya endurecido:
   - `📁 Proyectos — Umbral`
   - `📬 Entregables Rick — Revision`
   - `🗂 Tareas — Umbral Agent Stack`
5. no estaba desplegada al workspace vivo de `rick-orchestrator`

## Decision

- superficie: `repo-skill`
- accion: `create`

No se uso la copia compartida como version canonica. Se tomo como base conceptual y se escribio una version repo-first, OpenClaw-first y alineada al runtime real.

## Archivos creados

- `openclaw/workspace-templates/skills/external-reference-intelligence/SKILL.md`
- `openclaw/workspace-templates/skills/external-reference-intelligence/references/evidence-thresholds.md`
- `openclaw/workspace-templates/skills/external-reference-intelligence/references/reference-type-matrix.md`
- `openclaw/workspace-templates/skills/external-reference-intelligence/references/project-routing-guide.md`
- `openclaw/workspace-templates/skills/external-reference-intelligence/references/traceability-checklist.md`
- `openclaw/workspace-templates/skills/external-reference-intelligence/references/style-vs-strategy-vs-funnel.md`
- `openclaw/workspace-templates/skills/external-reference-intelligence/references/external-input-safety.md`
- `openclaw/workspace-templates/skills/external-reference-intelligence/references/output-contract.md`

## Archivos actualizados

- `openclaw/workspace-templates/AGENTS.md`

## Validacion

Comando:

```text
python scripts/validate_skills.py
```

Resultado:

- OK

## Despliegue

Se copio a:

- `/home/rick/umbral-agent-stack/openclaw/workspace-templates/skills/external-reference-intelligence`
- `/home/rick/.openclaw/workspaces/rick-orchestrator/skills/external-reference-intelligence`

Tambien se sincronizo `AGENTS.md` en:

- `/home/rick/umbral-agent-stack/openclaw/workspace-templates/AGENTS.md`
- `/home/rick/.openclaw/workspaces/rick-orchestrator/AGENTS.md`

## Resultado

Rick ya puede usar una skill oficial para referencias externas que:

- exige evidencia real cuando hay URL o referente concreto
- separa evidencia, inferencia e hipotesis
- decide routing por proyecto o sistema
- evita cerrar solo con un archivo local
- fuerza trazabilidad proporcional cuando el hallazgo impacta trabajo real
