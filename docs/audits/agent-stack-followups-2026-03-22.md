# Follow-ups listos para `Mejora Continua Agent Stack` - 2026-03-22

## Objetivo

Dejar cuatro follow-ups canónicos, con suficiente contexto para que cualquier agente con acceso al repo `umbral-agent-stack` pueda:

- entender el problema sin depender del chat original
- abrir o actualizar la issue correspondiente en Linear
- ejecutar el siguiente slice útil
- validar el cierre con evidencia del repo y del runtime

Proyecto destino en Linear:

- `Mejora Continua Agent Stack`

## 1. Unificar dispatcher vivo en VPS

### Título sugerido

- `Unificar dispatcher vivo en VPS`

### Tipo

- `operational_debt`

### Agente sugerido

- `Codex`

### Resumen

Se observaron dos procesos `dispatcher.service` vivos en la VPS aunque el servicio no quedaba reflejado de forma consistente en `systemctl`.

### Evidencia

- En la memoria de monitoreo consolidada:
  - [`automation-capitalization-2026-03-22.md`](C:/Users/david/.codex/worktrees/6446/umbral-agent-stack-codex/docs/audits/automation-capitalization-2026-03-22.md)
- En el corte operativo más fuerte:
  - [`vps-openclaw-llm-audio-validation-2026-03-08.md`](C:/Users/david/.codex/worktrees/6446/umbral-agent-stack-codex/docs/audits/vps-openclaw-llm-audio-validation-2026-03-08.md)
- En la memoria de la automatización `monitoreo-umbral-3` quedaron dos PIDs explícitos:
  - `905580`
  - `905626`

### Impacto

Riesgo de doble consumo, drift de observabilidad y estado de servicio inconsistente entre proceso real, `systemctl` y monitoreo.

### Siguiente acción

Definir un único método canónico de arranque del dispatcher en VPS, matar el duplicado y dejar una validación reproducible de:

- proceso vivo
- `systemctl --user status`
- smoke `Redis -> Dispatcher -> Worker`

### Validación esperada

- un solo proceso de dispatcher
- `systemctl` consistente con el proceso real
- `scripts/test_s2_dispatcher.py` o equivalente OK

### Payload listo para Linear

```json
{
  "title": "Unificar dispatcher vivo en VPS",
  "summary": "Se detectaron dos procesos dispatcher.service activos en la VPS.",
  "evidence": "La automatización de monitoreo dejó registrados dos procesos dispatcher en la VPS aunque systemctl no reflejaba ese estado de forma consistente.",
  "impact": "Riesgo de doble consumo, drift operativo y observabilidad engañosa.",
  "next_action": "Dejar un solo método de arranque, matar el duplicado y validar el flujo Redis -> Dispatcher -> Worker.",
  "kind": "operational_debt",
  "designated_agent": "codex",
  "source_ref": "docs/audits/automation-capitalization-2026-03-22.md"
}
```

## 2. Resincronizar worker VM con VPS

### Título sugerido

- `Resincronizar worker VM con VPS`

### Tipo

- `operational_debt`

### Agente sugerido

- `Codex`

### Resumen

El worker de la VM quedó con menos handlers que el worker de la VPS. En particular faltan capacidades de Notion relevantes para trazabilidad.

### Evidencia

- Hallazgo consolidado en:
  - [`automation-capitalization-2026-03-22.md`](C:/Users/david/.codex/worktrees/6446/umbral-agent-stack-codex/docs/audits/automation-capitalization-2026-03-22.md)
- Las corridas vivas de monitoreo registraron:
  - Worker VPS con `77` handlers
  - Worker VM `8088` y `8089` con `75` handlers
- Capacidades faltantes indicadas por el monitoreo:
  - `notion.upsert_deliverable`
  - `notion.upsert_bridge_item`

### Impacto

Rick y agentes derivados pueden operar con un runtime inconsistente según si ejecutan en VPS o en VM. Eso afecta trazabilidad en Notion y puede producir cierres parciales o falsos bloqueos.

### Siguiente acción

Resincronizar el deployment del worker en VM con la versión activa de VPS y dejar un smoke explícito de handlers publicados en:

- VPS `8088`
- VM `8088`
- VM interactivo `8089`

### Validación esperada

- mismos handlers críticos en VPS y VM
- smoke OK para `notion.upsert_deliverable`
- smoke OK para `notion.upsert_bridge_item`

### Payload listo para Linear

```json
{
  "title": "Resincronizar worker VM con VPS",
  "summary": "La VM publica menos handlers que el worker de la VPS.",
  "evidence": "Las corridas de monitoreo mostraron 77 handlers en VPS y 75 en la VM; faltan notion.upsert_deliverable y notion.upsert_bridge_item.",
  "impact": "Riesgo de comportamiento inconsistente entre VPS y VM y pérdida de trazabilidad en Notion.",
  "next_action": "Redeploy del worker VM y smoke de handlers críticos en 8088 y 8089.",
  "kind": "operational_debt",
  "designated_agent": "codex",
  "source_ref": "docs/audits/automation-capitalization-2026-03-22.md"
}
```

## 3. Curar tareas huérfanas de Granola

### Título sugerido

- `Curar tareas huérfanas duplicadas de Granola`

### Tipo

- `drift`

### Agente sugerido

- `Rick`

### Resumen

Persisten cuatro tareas `queued` huérfanas de Granola, duplicadas y sin vínculo suficiente a proyecto o entregable.

### Evidencia

- Consolidado en:
  - [`automation-capitalization-2026-03-22.md`](C:/Users/david/.codex/worktrees/6446/umbral-agent-stack-codex/docs/audits/automation-capitalization-2026-03-22.md)
- El monitoreo dejó explícitos estos duplicados:
  - `[Granola] Verify watcher works` x2
  - `[Granola] Confirmar E2E del watcher` x2

### Impacto

Contaminan paneles, métricas y backlog operativo. Además mantienen ruido en `tasks_unlinked` y degradan la lectura real de estado.

### Siguiente acción

Auditar esas cuatro filas, deduplicar y decidir por cada una si corresponde:

- vincular a proyecto/entregable correcto
- consolidar en una sola issue o tarea
- cerrar/archivar si ya quedó cubierta por otro flujo

### Validación esperada

- `tasks_unlinked` baja respecto al último corte
- no quedan duplicados `queued` de Granola sin owner ni contexto

### Payload listo para Linear

```json
{
  "title": "Curar tareas huérfanas duplicadas de Granola",
  "summary": "Persisten cuatro tareas queued de Granola duplicadas y sin contexto suficiente.",
  "evidence": "El monitoreo consolidado dejó dos duplicados de Verify watcher works y dos de Confirmar E2E del watcher.",
  "impact": "Ruido en paneles, métricas y backlog; degrada la lectura real del estado de Granola.",
  "next_action": "Deduplicar, relinkear o cerrar las cuatro filas y bajar tasks_unlinked.",
  "kind": "drift",
  "designated_agent": "rick",
  "source_ref": "docs/audits/automation-capitalization-2026-03-22.md"
}
```

## 4. Alinear `.agents/board.md` y `.agents/tasks`

### Título sugerido

- `Alinear board y task files con el estado real`

### Tipo

- `drift`

### Agente sugerido

- `Cursor`

### Resumen

El board y múltiples task files quedaron desalineados con la operación real y con rondas que el board declara cerradas.

### Evidencia

- Ya aparecía en:
  - [`system-usage-drift-review-2026-03-11.md`](C:/Users/david/.codex/worktrees/6446/umbral-agent-stack-codex/docs/audits/system-usage-drift-review-2026-03-11.md)
- Volvió a aparecer en:
  - [`automation-capitalization-2026-03-22.md`](C:/Users/david/.codex/worktrees/6446/umbral-agent-stack-codex/docs/audits/automation-capitalization-2026-03-22.md)
- Hallazgo concreto:
  - `.agents/board.md` declara rondas cerradas
  - varios archivos en `.agents/tasks/` siguen `assigned` o `blocked`

### Impacto

Los agentes arrancan con una representación atrasada del estado, lo que afecta coordinación, triage y confianza en la bitácora del repo.

### Siguiente acción

Revisar `.agents/board.md` y los task files antiguos, cerrar o regularizar los que ya no representen trabajo activo y dejar el protocolo otra vez consistente con el estado real.

### Validación esperada

- board consistente con rondas cerradas
- task files viejos ya no quedan `assigned` por arrastre
- agentes nuevos pueden iniciar sesión sin drift de coordinación

### Payload listo para Linear

```json
{
  "title": "Alinear board y task files con el estado real",
  "summary": "El board y varios archivos de tareas siguen atrasados respecto de la operación real.",
  "evidence": "El board declara rondas cerradas mientras múltiples task files continúan assigned o blocked por arrastre.",
  "impact": "Drift de coordinación interagente y pérdida de confianza en el estado oficial del repo.",
  "next_action": "Regularizar board y task files históricos para que representen solo trabajo vivo.",
  "kind": "drift",
  "designated_agent": "cursor",
  "source_ref": "docs/audits/automation-capitalization-2026-03-22.md"
}
```

## Orden recomendado

1. Unificar dispatcher vivo en VPS
2. Resincronizar worker VM con VPS
3. Curar tareas huérfanas duplicadas de Granola
4. Alinear `board` y `tasks`
