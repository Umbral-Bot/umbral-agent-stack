## Rick Benchmark Persistence Iteration — 2026-03-13

Ejecutado por: codex

### Objetivo

Corregir el comportamiento de Rick para que un benchmark competitivo pedido dentro de un proyecto no termine solo en una respuesta de chat, sino en un entregable persistido con trazabilidad real en el proyecto correspondiente.

Caso usado para la iteración:

- Proyecto: `Proyecto Embudo Ventas`
- Caso benchmark: Cristian Tala
- Prompt base:
  - análisis del post de LinkedIn
  - análisis de la landing `lp.cristiantala.com/linkedin-cheatsheets/`
  - insights para adaptar al embudo de Umbral

### Problema previo

Rick ya era capaz de:

- navegar fuentes reales
- usar `browser.*` y `research.web`
- producir insights razonables

Pero todavía fallaba en una parte clave:

- no siempre convertía el benchmark en artefacto persistido del proyecto
- no siempre dejaba comentario/update en Linear
- no siempre actualizaba el registro del proyecto en Notion
- podía responder desde memoria/contexto sin dejar evidencia nueva del proyecto

### Cambios aplicados a Rick

Se endureció el runtime y la skill para que un benchmark dentro de un proyecto quede persistido obligatoriamente.

Archivos modificados:

- `openclaw/workspace-templates/AGENTS.md`
- `openclaw/workspace-templates/SOUL.md`
- `openclaw/workspace-templates/skills/competitive-funnel-benchmark/SKILL.md`

Reglas nuevas:

1. `Benchmark de proyecto = entrega persistida`
2. `Benchmark repetido = refresco o persistencia`
3. La skill `competitive-funnel-benchmark` ahora exige:
   - artefacto en carpeta compartida
   - trazabilidad en Linear
   - actualización en Notion si el proyecto usa registro allí
   - separación explícita entre evidencia, inferencia e hipótesis

### Despliegue

Se sincronizaron estos cambios a la VPS en:

- workspace principal de Rick
- `rick-orchestrator`
- `rick-tracker`
- `rick-delivery`
- `rick-qa`
- `rick-ops`

Y se reinició:

- `openclaw-gateway.service`

### Retest ejecutado

Sesión principal usada para la iteración:

- `56677010-c8d6-41e0-8925-54822a270c88`

### Evidencia de ejecución real

Herramientas observadas en la sesión:

- `web_fetch` x6
- `web_search` x3
- `umbral_windows_fs_write_text`
- `umbral_windows_fs_read_text`
- `umbral_linear_update_issue_status`
- `umbral_linear_create_project_update`
- `umbral_notion_upsert_project`

Resultado funcional:

- Rick investigó de nuevo el caso
- Rick generó benchmark persistido
- Rick dejó comentario en issue del proyecto
- Rick dejó project update en Linear
- Rick actualizó el registro del proyecto en Notion

### Persistencia confirmada

Artefacto creado:

- `G:\Mi unidad\Rick-David\Proyecto-Embudo-Ventas\benchmark-cristian-tala-linkedin-funnel-2026-03-13.md`

Verificación independiente:

Se leyó el archivo por fuera de la sesión de Rick, llamando directamente al Worker remoto de la VM desde la VPS.

Resultado:

- `ok: true`
- longitud leída: `10000` caracteres
- el contenido comienza con:
  - `# Benchmark — Cristian Tala como referencia para Proyecto Embudo Ventas`

### Trazabilidad confirmada

Linear:

- comentario creado en issue del proyecto con referencia explícita al artefacto
- project update creado en:
  - `https://linear.app/umbral/project/proyecto-embudo-ventas-6d4b3ed16eb2/updates#project-update-7b00ef12`

Notion:

- `Proyecto Embudo Ventas` actualizado vía `notion.upsert_project`
- página:
  - `https://www.notion.so/Proyecto-Embudo-Ventas-31e5f443fb5c8125a21ce5333fb32a03`

### Resultado

La iteración fue exitosa.

Rick ahora ya no solo:

- investiga
- navega
- responde con insights

Sino que además:

- convierte el benchmark en entregable de proyecto
- lo deja en carpeta compartida
- deja update en Linear
- y actualiza el registro del proyecto en Notion

### Límite actual

Sigue siendo cierto que un benchmark “profundo total” puede requerir validaciones adicionales si la fuente principal depende de:

- primer comentario
- formulario exacto de opt-in
- thank-you page
- nurturance posterior al opt-in

Eso no invalida esta iteración. Lo importante aquí era corregir la falta de persistencia, y eso sí quedó resuelto.

### Estado final

- benchmark competitivo: persistido
- Linear: actualizado
- Notion: actualizado
- carpeta compartida: actualizada
- comportamiento de Rick: mejorado respecto al problema original
