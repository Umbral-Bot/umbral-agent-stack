# Cierre de trazabilidad de entregables — Notion

Fecha: 2026-03-16
Autor: Codex

## Objetivo

Cerrar la deuda residual de `Entregables` sin inventar relaciones historicas falsas:

- distinguir deuda viva de deuda historica,
- etiquetar procedencia real,
- y garantizar que los entregables nuevos nazcan bien por el camino real del worker.

## Cambio de enfoque

No se forzo una relacion `Tareas origen` para todos los entregables viejos.

Se aplico una separacion mas honesta:

- `Tarea`: entregable con `source_task_id` o con backfill controlado sobre item vivo
- `Historico`: entregable heredado/canonico ya aprobado o archivado
- `Smoke`: pruebas tecnicas o validaciones de routing/iconos
- `Manual`: item vivo que aun requeria cierre de trazabilidad

Eso evita dos errores:

- contaminar `Tareas` con backfills falsos masivos
- seguir tratando el historico como deuda operativa activa

## Implementacion

### Procedencia explicita

Se agrego soporte a `notion.upsert_deliverable` para persistir `Procedencia` y mostrarla en la subpagina del entregable.

Archivos:

- [worker/tasks/notion.py](C:/GitHub/umbral-agent-stack-codex/worker/tasks/notion.py)
- [tests/test_notion_deliverables_registry.py](C:/GitHub/umbral-agent-stack-codex/tests/test_notion_deliverables_registry.py)

### Curacion incremental

La curacion ahora:

- asegura el schema `Procedencia` en la DB de entregables
- normaliza procedencia historica/smoke/manual
- crea backfill solo para entregables vivos (`Pendiente revision` o `Aprobado con ajustes`) cuando falta `Tareas origen`

Archivos:

- [scripts/notion_curate_ops_vps.py](C:/GitHub/umbral-agent-stack-codex/scripts/notion_curate_ops_vps.py)
- [tests/test_notion_ops_curation.py](C:/GitHub/umbral-agent-stack-codex/tests/test_notion_ops_curation.py)

## Resultado real

Snapshot final en VPS:

- `deliverables_total`: `21`
- `deliverables_pending_review`: `3`
- `deliverables_without_task_origin`: `16`
- `deliverables_live_without_task_origin`: `0`
- `deliverables_historical_without_task_origin`: `16`

Interpretacion:

- la deuda operativa viva quedo cerrada
- lo que queda sin `Tareas origen` es historico o smoke preservado, no flujo roto actual

## Smoke del camino real del worker

Se ejecuto un smoke real por el worker HTTP:

1. `notion.upsert_deliverable`
2. `notion.upsert_task`
3. `notion_curate_ops_vps.py`

Verificacion del smoke:

- el entregable quedo con `Procedencia = Tarea`
- `Task ID origen = smoke-notion-structured-flow-2026-03-16`
- `Tareas origen` enlazada a la tarea creada
- la tarea quedo ligada a proyecto y entregable
- `source = openclaw_gateway`
- `source_kind = tool_enqueue`
- `trace_id` persistido

Luego las dos paginas de smoke se archivaron para no ensuciar la operacion diaria.

## Conclusion

La solucion definitiva no era forzar todo a `Tareas origen`.

La solucion correcta fue:

- separar historico de operativo
- etiquetar procedencia real
- cerrar solo los entregables vivos
- y validar con un smoke real del worker

Con eso, `Entregables` queda util para operacion presente y el historico deja de contaminar el diagnostico.
