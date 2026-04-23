# CAND-001 — Rick QA Validation Request

> **Date**: 2026-04-22
> **Requester**: rick-orchestrator (simulated by Codex)
> **Target agent**: rick-qa
> **Invocation**: `openclaw agent --agent rick-qa --message "..." --json`
> **Purpose**: Validate CAND-001 editorial candidate payload before Notion registration.

## Safety constraints

- No Notion writes.
- No record creation.
- No publication.
- No Rick runtime activation.
- No gate marking.
- Validation only.

## Payload submitted for validation

```yaml
publication_id: CAND-001
title: "CAND-001 — Automatizar sin gobernanza escala el desorden"
estado: Borrador
canal: linkedin
tipo_de_contenido: linkedin_post
etapa_audiencia: awareness
prioridad: media

claim_principal:
  texto: "Automatizar un proceso que no tiene gobernanza clara no mejora la calidad del resultado — solo escala el desorden más rápido."
  tipo: opinion_operativa
  requiere_fuente_primaria: false

angulo_editorial: >
  Antes de activar agentes, integraciones o publicación automática,
  conviene validar manualmente que la estructura, los estados, los gates
  humanos, las fuentes, la trazabilidad y la auditoría funcionan.
  La pieza habla desde la experiencia operativa de montar un sistema
  editorial con IA donde la primera decisión fue NO automatizar todavía.

fuentes:
  fuente_primaria:
    estado: pendiente
    url: ""
    nota: "No hay fuente primaria externa porque la pieza es opinión operativa basada en criterio profesional."
  fuente_referente:
    url: ""
    nota: ""

copies:
  copy_linkedin: "(full copy included in invocation — see rick-qa result for validation)"
  copy_x: "(compressed version of same angle)"
  copy_blog: ""
  copy_newsletter: ""

visual:
  visual_brief: "Diagrama conceptual: dos caminos divergentes. Freepik API/MCP, no UI automation."
  visual_hitl_required: true
  visual_asset_url: ""

gates:
  aprobado_contenido: false
  autorizar_publicacion: false
  gate_invalidado: false

system:
  creado_por_sistema: false
  rick_active: false
  publish_authorized: false
  content_hash: ""
  idempotency_key: ""
  trace_id: CAND-001-manual-editorial-candidate
```

## QA criteria requested

1. Schema validation (estado, canal, tipo_de_contenido, gates, post-publication fields, trace_id)
2. Operational security (no Notion write, no runtime, no publication)
3. Source and claims (factual claims requiring primary source, opinion vs. verifiable assertion)
4. Editorial quality (clarity, tone, length, self-promotional risk, LinkedIn awareness fit)
5. Governance (gates correct, not approved, not authorized, not ready for publication)
6. Visual (brief safety, no UI automation, HITL required)
7. Next action recommendation

## Invocation details

- **Command**: `openclaw agent --agent rick-qa --message "$(cat /tmp/cand-001-qa-prompt.txt)" --json --timeout 300`
- **Agent**: rick-qa
- **Model**: azure-openai-responses/gpt-5.4
- **Session ID**: ba3ec54c-a5f4-44b5-8518-f52e1fe26a30
- **Run ID**: bfabbd46-690f-4167-b8f5-52c5f177aec0
- **Duration**: 67.2s
- **Status**: ok / completed
