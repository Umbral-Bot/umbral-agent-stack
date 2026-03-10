# Rick Natural Prompt Runtime Alignment — 2026-03-09

Ejecutado por: codex

## Objetivo

Diagnosticar por qué Rick no infería ni ejecutaba slices útiles frente a prompts naturales y desordenados, aunque usara el mismo modelo base que Codex, y corregir la capa de runtime para acercar su comportamiento al de un operador autónomo.

## Diagnóstico

La diferencia principal no estaba en el modelo sino en el runtime:

1. El workspace de `main` tenía demasiadas skills y demasiado ruido operativo.
2. Faltaban reglas explícitas de:
   - tolerancia a prompts naturales;
   - autopilot por proyecto;
   - honestidad obligatoria cuando una tool fallaba.
3. Las skills críticas de gobernanza existían pero no quedaban suficientemente forzadas en la práctica.
4. El Worker rechazaba comentarios normales con backticks por una regla de sanitización demasiado amplia.

## Causa raíz técnica encontrada

En [worker/sanitize.py](/c:/GitHub/umbral-agent-stack-codex/worker/sanitize.py) existía este patrón:

- `` `[^`]+` ``

Eso bloqueaba cualquier inline code markdown, incluso comentarios legítimos con:

- rutas de archivos
- nombres de issues
- artefactos de trazabilidad

Efecto práctico:

- `linear.update_issue_status` podía devolver `422`
- Rick luego seguía respondiendo como si la trazabilidad hubiese quedado persistida

## Cambios aplicados

### Repo

- [worker/sanitize.py](/c:/GitHub/umbral-agent-stack-codex/worker/sanitize.py)
  - la regla de backticks pasó a bloquear solo contenido con forma de comando real dentro de backticks.
- [tests/test_hardening.py](/c:/GitHub/umbral-agent-stack-codex/tests/test_hardening.py)
  - se agregaron tests para:
    - permitir markdown de trazabilidad con backticks;
    - seguir bloqueando comandos peligrosos en backticks.
- [AGENTS.md](/c:/GitHub/umbral-agent-stack-codex/openclaw/workspace-templates/AGENTS.md)
  - se reforzaron:
    - prompts naturales;
    - autopilot por proyecto;
    - prohibición de reclamar éxito si una tool falló.
- [SOUL.md](/c:/GitHub/umbral-agent-stack-codex/openclaw/workspace-templates/SOUL.md)
  - se añadieron reglas explícitas para:
    - comprensión robusta de prompts naturales;
    - autopilot por proyecto;
    - honestidad frente a errores de tools.
- [AGENTS.md](/c:/GitHub/umbral-agent-stack-codex/openclaw/workspace-templates/AGENTS.md)
  - se añadieron reglas nuevas para:
    - delegación mínima;
    - tratar completions esperados como trabajo pendiente.
- [SOUL.md](/c:/GitHub/umbral-agent-stack-codex/openclaw/workspace-templates/SOUL.md)
  - se añadió una regla específica para:
    - no usar `sessions_spawn` cuando el slice ya es pequeño y resoluble inline;
    - no emitir `NO_REPLY` si un completion útil llegó antes de cerrar la respuesta.
- Skills marcadas como `always: true`:
  - [subagent-result-integration](/c:/GitHub/umbral-agent-stack-codex/openclaw/workspace-templates/skills/subagent-result-integration/SKILL.md)
  - [linear-delivery-traceability](/c:/GitHub/umbral-agent-stack-codex/openclaw/workspace-templates/skills/linear-delivery-traceability/SKILL.md)
  - [notion-project-registry](/c:/GitHub/umbral-agent-stack-codex/openclaw/workspace-templates/skills/notion-project-registry/SKILL.md)
  - [agent-handoff-governance](/c:/GitHub/umbral-agent-stack-codex/openclaw/workspace-templates/skills/agent-handoff-governance/SKILL.md)
- [subagent-result-integration](/c:/GitHub/umbral-agent-stack-codex/openclaw/workspace-templates/skills/subagent-result-integration/SKILL.md)
  - se reforzó con:
    - no spawnear para verificaciones cortas o validaciones que `main` ya puede resolver;
    - antipatrones observados (`sessions_spawn` + `NO_REPLY`).

### VPS

- Se curó el set de skills de `main` para reducir ruido operativo.
- Se sincronizaron `AGENTS.md`, `SOUL.md` y las skills críticas al workspace vivo.
- Se desplegó el parche de sanitización al Worker.
- Se reiniciaron:
  - `umbral-worker.service`
  - `openclaw-gateway.service`

## Verificación

### Local

```text
python -m pytest tests/test_hardening.py -q
31 passed
```

### VPS

```text
./.venv/bin/python -m pytest tests/test_hardening.py -q
31 passed
```

## Smoke test real

Prompt usado contra Rick `main`:

> sigamos con el proyecto embudo, revisa donde quedo el hub y avanza con un corte util de verdad, deja trazabilidad en linear nombrando el artefacto con su ruta exacta si corresponde, y no me des teoria ni lista de pasos, solo haz lo que siga y al final dime que hiciste y si quedo algo bloqueado

### Comportamiento observado

Rick:

- no pidió pasos;
- leyó el estado actual;
- editó el hub real en el repo;
- escribió artefacto de trazabilidad;
- actualizó la issue correcta en Linear con comentario persistido;
- respondió con resultado y bloqueos reales.

### Evidencia relevante

- edición real del repo:
  - `/home/rick/.openclaw/workspace/proyectos/venta-servicios-embudo/landing-umbralbim-io.html`
- artefacto nuevo:
  - `G:\Mi unidad\Rick-David\Proyecto-Embudo-Ventas\corte-util-hub-v4.md`
- comentario de Linear persistido en `UMB-39`
- el tool `umbral_linear_update_issue_status` devolvió `ok: true` después del parche

## Resultado

La mejora fue real.

Antes del fix:

- prompt natural -> Rick actuaba mejor que antes, pero la trazabilidad podía fallar por sanitización y aun así él reportar éxito.

Después del fix:

- prompt natural -> Rick actuó sin pedir estructura extra y dejó trazabilidad real persistida.

Después del segundo endurecimiento:

- en el tramo más reciente del turno bueno, Rick resolvió inline el slice útil del hub;
- no hubo `sessions_spawn` ni `NO_REPLY` en ese cierre;
- reforzó el hub directamente, escribió `decision-cierre-hub-primero-v1.md` y persistió el comentario en `UMB-39`.

## Residuales

1. `systemPromptReport.skills.entries` todavía no refleja de forma confiable todas las custom skills instaladas en sesiones viejas.
2. El patrón `sessions_spawn -> NO_REPLY` mejoró, pero sigue siendo un riesgo que debe seguirse auditando.
   - En sesiones viejas todavía aparece con claridad.
   - En el último tramo bueno ya no apareció.
3. La diferencia entre Codex y Rick sigue siendo de runtime total, no solo de skill selection:
   - contexto de workspace;
   - heurísticas de gobernanza;
   - saneamiento de inputs;
   - curación de skills.

## Conclusión

Rick no necesitaba “otro modelo”.
Necesitaba:

- menos ruido,
- mejores guardrails,
- skills críticas forzadas,
- y una capa de ejecución que no rompiera la trazabilidad legítima.

Con esas correcciones, ya empezó a comportarse bastante más cerca de lo que se espera frente a prompts humanos naturales y desordenados.
