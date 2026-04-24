# Rick Communication Director — Phase 1 Implementation

> **Status**: runtime-registered, read-only, dry-run. Dedicated workspace identity and governance sync are defined repo-side. No autonomous routing, no Notion writes, no publication, no human gate mutation.

## Purpose

`rick-communication-director` is a new editorial communication reviewer for the Rick/OpenClaw editorial system. Its job is to decide whether a candidate sounds like David, not only whether it is correct.

It exists because CAND-003 showed a gap: the premise was acceptable, but the final copy used unnatural terms such as `escalacion` and `rick-qa` still returned `voice: pass`.

Subsequent iterations of CAND-003 revealed a deeper calibration failure: the same voice issues reappeared across versions because human feedback was not being absorbed into the system as persistent rules. This led to the creation of `CALIBRATION.md` as the operational base for voice calibration, and to hardened opening/grounding checks in both the communication director workflow and `rick-qa` voice QA.

## Decision

Create a new role instead of expanding an existing one.

| Existing agent | Fit | Decision |
| --- | --- | --- |
| Consultor Sistema Umbral BIM | Good for system audit | Not enough narrative ownership |
| Docente 2.1 | Good for orality | Domain is education |
| Revisor de Entregables y Riesgos | Good for claims/risk | Not a voice curator |
| Gobernanza Multiagente | Good for handoffs | Not a writing role |
| Arquitecto de Automatizacion | Good for loop design | Not a narrative role |
| Diseñador de Ofertas | Good for funnel/offer | Not the voice authority |
| Radar Editorial Umbral | Good for signals | Not final copy curator |
| Marca Personal | Strong source material | Use as knowledge base, not as the runtime role |

## Phase 1 authority

Allowed:

- Read candidate pages and evidence.
- Diagnose voice failures.
- Generate controlled variants.
- Propose prompt/config changes.
- Prepare handoffs for Copilot/Codex/VPS.
- Be invoked deliberately as `rick-communication-director` after the live OpenClaw config is updated.

Prohibited:

- Publishing.
- Marking `aprobado_contenido`.
- Marking `autorizar_publicacion`.
- Changing gates.
- Creating autonomous runtime routing, cron, or publication flow.
- Editing Notion.
- Modifying repos directly.
- Using Notion AI.

## Canonical flow addition

Add a communication review stage between the voice pass and final QA:

```text
1. fuentes y senales
2. extraccion y transformacion
3. borrador editorial base
4. validacion de atribucion y trazabilidad
5. pasada de voz contra Guia Editorial y Voz de Marca
5a. direccion de comunicacion / curaduria narrativa
6. QA editorial y tecnico
7. revision humana
8. aprobacion de contenido
9. autorizacion de publicacion
```

Stage `5a` does not replace QA. It validates naturalness, narrative, and David's voice. QA still validates sources, claims, gates, schema, and security.

## OpenClaw implementation surface

Repo-side implementation:

- `openclaw/workspace-agent-overrides/rick-communication-director/ROLE.md`
- `openclaw/workspace-agent-overrides/rick-communication-director/HEARTBEAT.md`
- `openclaw/workspace-templates/skills/director-comunicacion-umbral/SKILL.md`
- `scripts/sync_openclaw_workspace_governance.py` includes `~/.openclaw/workspaces/rick-communication-director`
- `docs/openclaw-config-reference-2026-03.json5` includes a reference `agents.list` entry

Live VPS activation still requires applying the config change to `~/.openclaw/openclaw.json`, running the governance sync, and smoke testing deliberate invocation. That is separate from autonomous routing.

## Evidence requirements

Every communication review must state which voice source was used:

- live Notion voice guide;
- authorized summary of the guide;
- local Marca Personal materials;
- limited evidence.

If the live Notion guide is inaccessible, the review cannot claim it used the live guide.

## CAND-003 failure pattern

Observed issues:

- `escalacion` appears as a noun in public copy and premise.
- Several lines sound like AI governance reporting rather than AEC experience.
- `rick-qa` approved voice despite David rejecting tone.
- The voice guide was not accessible to Rick's integration, so the pass depended on a summary.

System implication:

- `rick-qa` needs stricter voice evidence and opening coherence rules that block `voice: pass` for incoherent openings, bare sectoral labels, and ungrounded abstractions. QA does not rewrite — it blocks and returns to communication director.
- The voice pass needs an independent communication review when David-facing copy is involved.
- The system needs a blacklist and replacement table for terms that are technically understandable but unnatural in David's voice.
- Repeated human feedback must be converted into persistent calibration rules in `CALIBRATION.md`, not re-corrected manually each time.

## CALIBRATION.md

`openclaw/workspace-templates/skills/director-comunicacion-umbral/CALIBRATION.md` is the persistent calibration file. It absorbs recurring human feedback as structured rules (pattern / rejected example / preferred example / reason / when applies / when doesn't apply).

The communication director must read `CALIBRATION.md` before every review. When David's feedback reveals a new recurring pattern, the agent must propose a new entry as part of the handoff.

`CALIBRATION.md` lives inside the skill directory, not as a workspace governance file. OpenClaw reads skills directly from the workspace skill path. The governance sync script (`scripts/sync_openclaw_workspace_governance.py`) handles `HEARTBEAT.md` only. Skill files including `CALIBRATION.md` are available to the agent through the skill's own directory structure.

## First handoff prompt

```text
Actua como Director de Comunicacion Umbral.

Objetivo:
Diagnosticar por que CAND-003 no suena a David aunque la premisa sea correcta, y proponer como ajustar el sistema editorial Rick/OpenClaw para mejorar la redaccion en iteraciones futuras.

Trabaja en modo solo lectura.

Fuentes:
- Pagina Notion CAND-003.
- Guia Editorial y Voz de Marca en Notion, si esta accesible.
- Repo /home/rick/umbral-agent-stack.
- docs/ops/cand-003-*.
- docs/ops/cand-002-*.
- openclaw/workspace-agent-overrides/rick-editorial/ROLE.md.
- openclaw/workspace-agent-overrides/rick-qa/ROLE.md.
- docs/ops/rick-editorial-candidate-payload-template.md.
- docs/ops/editorial-source-attribution-policy.md.
- Documentacion de Marca Personal, Consultor, Docente V4 y Make LLMs V3 si esta disponible.

Restricciones:
- No publiques.
- No marques aprobado_contenido.
- No marques autorizar_publicacion.
- No edites Notion.
- No modifiques repo.
- No cambies la premisa aprobada salvo que lo propongas como alternativa y pidas autorizacion.
- No cambies fuentes ni atribucion.
- No uses Notion AI.

Entrega:
1. Diagnostico de tono de CAND-003.
2. Frases o palabras problematicas.
3. Causa probable en configuracion del flujo.
4. Reglas nuevas para rick-editorial.
5. Reglas nuevas para rick-qa voice.
6. Lista negra y reemplazos.
7. Tres variantes nuevas de Copy LinkedIn.
8. Tres variantes nuevas de Copy X.
9. Recomendacion de cual probar primero.
10. Prompt para Copilot/VPS que aplique los cambios de configuracion en branch draft.
```

## Acceptance criteria

- David can choose at least one variant as closer to his voice.
- `escalacion` is absent from public copy.
- Premise and source attribution are preserved unless David approves changes.
- `rick-qa` can no longer pass voice without reporting phrases David probably would not say.
- Runtime registration remains read-only/dry-run and does not create autonomous routing or publication permissions.
