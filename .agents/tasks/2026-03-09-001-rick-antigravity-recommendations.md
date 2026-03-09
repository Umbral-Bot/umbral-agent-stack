---
id: "2026-03-09-001"
title: "Recomendaciones Antigravity para corregir la ejecucion de Rick en proyectos reales"
status: done
assigned_to: antigravity
created_by: codex
priority: high
sprint: R21
created_at: 2026-03-09T00:05:34-03:00
updated_at: 2026-03-09T00:18:00-03:00
---

## Objetivo

Revisar la auditoria detallada del live test de Rick y proponer recomendaciones concretas para corregir el problema de fondo: Rick entiende el contexto, pero no pasa de declaracion a ejecucion real.

## Contexto

Documentos de referencia:

- `docs/audits/rick-live-test-2026-03-08.md`
- `docs/audits/rick-live-test-2026-03-09-followup.md`
- `docs/audits/rick-live-test-2026-03-09-detailed.md`

Hallazgos ya confirmados:

- la infra base ya funciona para Notion y VM filesystem
- el proyecto `Proyecto-Embudo-Ventas` fue aclarado y el contexto fue entendido
- Rick no ejecuto tool calls nuevos despues del prompt corregido
- Rick no toco Linear, Notion ni el filesystem del proyecto
- Rick no delego a subagentes
- cron sigue interfiriendo en la misma sesion de trabajo

## Enfoque pedido a Antigravity

Se necesitan recomendaciones desde el angulo de:

- instrucciones y skills
- flujo operativo del agente principal
- disciplina de ejecucion
- conversion de prompts de proyecto en acciones reales
- forma de usar subagentes sin perder contexto

## Criterios de aceptacion

- [x] Entregar 5-10 recomendaciones concretas y priorizadas
- [x] Indicar si el problema principal esta en prompt, skills, workspace, contexto o policy
- [x] Proponer un cambio minimo y uno estructural
- [x] Identificar al menos un experimento rapido para validar mejora
- [x] Dejar el resultado en el `## Log` de esta tarea

## Log

### [codex] 2026-03-09 00:05 -03:00
Tarea creada por pedido directo de David tras la auditoria del live test de Rick.
Se requiere foco en recomendaciones, no implementacion inmediata.

### [antigravity] 2026-03-09 00:18 -03:00
**Diagnóstico:**
El problema principal reside en la **Policy (System Prompt) y la Orquestación (Flujo Operativo)**. Rick sufre de "alucinación de ejecución": prioriza mantener fluidez conversacional y asume que relatar su plan equivale a ejecutarlo. Entiende el contexto, pero no hay un mecanismo que lo fuerce a emitir `toolCalls` antes de responder verbalmente.

**Recomendaciones Priorizadas:**
1. **Regla de Ejecución Estricta (Policy):** Modificar el System Prompt de `main`: "Prohibido afirmar 'evaluando' o 'comenzado' sin ejecutar un `toolCall` exitoso en el mismo turno."
2. **Aislamiento de Cron (Workspace/Contexto):** Enrutar los eventos como `SIM - recoleccion senales` a un hilo/sesión background en OpenClaw, evitando que interrumpan el contexto conversacional del usuario.
3. **Acción Trazable Obligatoria (Flujo):** Todo inicio de proyecto oficial debe obligar procedimentalmente a emitir un `umbral_linear_create_issue` o buscar en `umbral_windows_fs` como primer step innegociable.
4. **Trigger Explícito para Subagentes (Prompt/Skills):** Proveer *few-shot examples* al System Prompt demostrando cómo invocar `sessions_spawn` en la primera interacción de un proyecto complejo en lugar de condensar todo en `main`.
5. **Verificación de Tool Call (Orquestación):** A nivel middleware (OpenClaw), si se detecta un "Proyecto Activo" y el LLM responde solo con texto (sin tools), inyectar un system prompt interno `ToolCallRequired` para forzar la ejecución real y demorar la respuesta al usuario.

**Cambio Mínimo (Quick Win):**
Actualizar el prompt de `main` con una directiva estricta: *"NUNCA digas 'ya validé' o 'ya empecé' sin ejecutar una tool en este turno. Si recibes un proyecto, tu PRIMERA acción DEBE ser llamar a `umbral_windows_fs`, `umbral_notion` o `sessions_spawn`. No hables sobre lo que harás, hazlo."*

**Cambio Estructural:**
Implementar un interceptor en OpenClaw (Guardrail de Ejecución). Si Rick entra en fase de proyecto, interceptar sus intentos de responder al usuario si no hay registros nuevos en `ops_log` (Notion/Linear/FS). Si el LLM intenta conversar sin actuar, el gateway le rebota un prompt sistémico exigiendo el llamado a la tool primero.

**Experimento Rápido para Validar Mejora:**
Aplicar el "Cambio Mínimo" al prompt actual. Repetir el prompt exacto de `Proyecto-Embudo-Ventas` en Telegram. Si Rick invoca preventivamente `umbral_windows_fs_list` ANTES de enviar su primer globo de texto de respuesta asintiendo, el experimento es exitoso.

