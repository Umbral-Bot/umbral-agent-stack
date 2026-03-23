# Protocolo Linear - Mejora Continua Agent Stack

## Objetivo

Usar un proyecto canonico de Linear para capturar y ejecutar pendientes internos de Umbral Agent Stack sin mezclarlos con proyectos que vengan desde Rick o desde trabajo externo.

Proyecto canonico:

- `Mejora Continua Agent Stack`

Regla de resolucion:

- antes de crear un proyecto nuevo, buscar por `LINEAR_AGENT_STACK_PROJECT_ID`
- si no existe ese ID en config, reutilizar el alias historico `Auditoria Mejora Continua - Umbral Agent Stack` si ya existe
- solo crear proyecto nuevo si no existe ni el canonico ni el alias historico
- si hay que crearlo, copiar descripcion y contenido ricos; no dejar un proyecto vacio o generico

## Cuando usarlo

Usar este flujo cuando el pendiente trate sobre:

- Worker
- Dispatcher
- OpenClaw
- Redis
- Tailscale
- VPS o VM
- Notion o Linear del propio stack
- drift operativo
- deuda tecnica u operativa
- follow-ups que salgan de auditorias, monitoreo o analisis

No usar este proyecto para:

- benchmarks externos
- proyectos de cliente
- entregables de negocio
- iniciativas tematicas de Rick fuera del stack

## Tasks canonicas

### 1. Publicar un pendiente

Task:

- `linear.publish_agent_stack_followup`

Uso:

- crea la issue
- la adjunta al proyecto correcto
- agrega labels base de Agent Stack
- opcionalmente designa un agente

### 2. Ver backlog del proyecto

Task:

- `linear.list_agent_stack_issues`

Uso:

- ver cola completa
- ver solo issues no tomadas
- filtrar por agente

### 3. Tomar una issue

Task:

- `linear.claim_agent_stack_issue`

Uso:

- marca ownership operativo por agente
- agrega label `Agente: <Nombre>`
- puede mover la issue a `In Progress`
- deja comentario trazable

## Agentes permitidos

Los nombres soportados por este flujo son:

- `Codex`
- `Cursor`
- `Antigravity`
- `GitHub Copilot`
- `Rick`
- `OpenClaw`

## Convencion minima

Cuando una auditoria o analisis deje trabajo pendiente:

1. publicar cada follow-up real con `linear.publish_agent_stack_followup`
2. si ya hay owner, designarlo al crearla
3. si no, dejarla sin claim y verla con `linear.list_agent_stack_issues`
4. cuando un agente la tome, usar `linear.claim_agent_stack_issue`

## Auto-escalacion del Dispatcher

La auto-escalacion por fallos del Dispatcher debe publicar follow-ups usando `linear.publish_agent_stack_followup`, no `linear.create_issue` crudo.

Reglas:

- escalar solo si el envelope trae `source` o `source_kind` de flujo canonico
- por defecto el filtro estricto queda activo con `ESCALATE_ONLY_CANONICAL=true`
- no escalar tareas ruidosas o de soporte operativo como cron, reportes o backfills
- si una tarea falla fuera de ese criterio, dejar trazabilidad en logs y revisar manualmente si amerita follow-up

## Campos recomendados al publicar

- `title`
- `summary`
- `evidence`
- `impact`
- `next_action`
- `kind`
- `designated_agent` si ya se sabe

## Tipos (`kind`) recomendados

- `analysis_followup`
- `operational_debt`
- `human_review`
- `drift`

## Ejemplos

### Publicar un follow-up

```json
{
  "title": "Resincronizar worker VM con VPS",
  "summary": "La VM publica menos handlers que la VPS.",
  "evidence": "Faltan notion.upsert_deliverable y notion.upsert_bridge_item en la VM.",
  "impact": "Rick y los agentes derivados pueden quedar sin capacidades de trazabilidad.",
  "next_action": "Deploy del worker VM y smoke de handlers.",
  "kind": "operational_debt",
  "designated_agent": "codex"
}
```

### Tomar una issue

```json
{
  "identifier": "UMB-123",
  "agent_name": "rick",
  "comment": "Voy a tomar el slice y dejar trazabilidad al cerrar."
}
```
