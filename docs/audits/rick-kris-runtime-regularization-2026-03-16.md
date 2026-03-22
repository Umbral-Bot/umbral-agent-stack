# Rick Kris Runtime Regularization - 2026-03-16

## Objetivo
Cerrar el caso Kris Wojslaw sin hacerlo directamente por Rick: endurecer el runtime, volver trazable la instruccion y forzar una reejecucion minima hasta que `Tarea -> Proyecto -> Entregable` quedara canonico en Notion.

## Que se corrigio en el sistema
- `dispatcher/smart_reply.py`
  - las correcciones via Notion ya no quedan solo como `Recibido`; exigen cierre operativo para referencias externas.
- `worker/tasks/notion.py`
  - `notion.upsert_task` ahora reusa contexto existente, backfillea relaciones y resuelve el nombre del entregable desde `deliverable_page_id` si no llega en el payload.
  - `notion.upsert_project` y `notion.upsert_deliverable` reemplazan el cuerpo completo al refrescar, en vez de dejar bloques viejos mezclados.
- `worker/notion_client.py`
  - soporte para `replace_blocks_in_page(...)` y `archived` en `update_page_properties(...)`.
- `scripts/notion_curate_ops_vps.py`
  - la curacion ya no se cae si `Bandeja Puente` no esta compartida con la integracion Rick.
- `scripts/openclaw_panel_vps.py`
  - la validacion de shell ahora falla si quedan paginas sueltas bajo `OpenClaw`.
- `AGENTS.md`, `SOUL.md` y las skills `external-reference-intelligence` y `notion`
  - se reforzo que una referencia externa no queda cerrada solo con un `.md` local: debe quedar ligada a proyecto y entregable cuando aplica.

## Intervencion runtime sobre Rick
Se uso el canal directo de OpenClaw hacia la sesion activa de Rick para pedirle una reejecucion minima y canonica del caso:
- no rehacer el benchmark
- refrescar la `Tarea` existente
- refrescar el `Entregable` existente
- verificar relaciones y contenido de ambas paginas

Rick respondio ejecutando el refresh minimo con `notion.upsert_task` y `notion.upsert_deliverable`.

## Verificacion final independiente

### 1. Control Room / OpenClaw
- `NOTION_CONTROL_ROOM_PAGE_ID`: `30c5f443fb5c80eeb721dc5727b20dca`
- Hijos `child_page` residuales bajo OpenClaw: `0`

### 2. Tarea canonica del caso Kris
- Pagina: `3265f443-fb5c-8121-90da-de3704b5fedd`
- `Task ID`: `notion-instruction-3265f443`
- `Status`: `done`
- `Proyecto`: `31e5f443-fb5c-8125-a21c-e5333fb32a03` (`Proyecto Embudo Ventas`)
- `Entregable`: `3265f443-fb5c-81c0-9565-e442a9b70d50`
- `Source`: `notion_poll`
- `Source Kind`: `instruction_comment`
- `Trace ID`: `3265f443-fb5c-8127-bbbd-001dcb81ac81`

Texto verificado en el cuerpo de la tarea:
- `Proyecto: Proyecto Embudo Ventas`
- `Entregable: Benchmark parcial de Kris Wojslaw para el embudo`
- `Origen: notion_poll`
- `Tipo de origen: instruction_comment`
- `Trace ID: 3265f443-fb5c-8127-bbbd-001dcb81ac81`

### 3. Entregable canonico del caso Kris
- Pagina: `3265f443-fb5c-81c0-9565-e442a9b70d50`
- `Nombre`: `Benchmark parcial de Kris Wojslaw para el embudo`
- `Proyecto`: `31e5f443-fb5c-8125-a21c-e5333fb32a03`
- `Tareas origen`: `3265f443-fb5c-8121-90da-de3704b5fedd`
- `Task ID origen`: `notion-instruction-3265f443`
- `Procedencia`: `Tarea`
- `Estado revision`: `Pendiente revision`

Texto verificado en el cuerpo del entregable:
- `Proyecto: Proyecto Embudo Ventas`
- `Procedencia: Tarea`
- `Task ID origen: notion-instruction-3265f443`
- `Fecha limite sugerida: 2026-03-18`

## Resultado
El caso Kris ya no queda half-done:
- la instruccion llega
- el task se crea
- Rick puede reejecutar sobre la misma pieza
- el task queda ligado a proyecto y entregable
- el entregable queda ligado a proyecto y tarea
- OpenClaw no deja paginas sueltas como residuo

## Residuales reales
- El benchmark sigue siendo **parcial**. No se cambio artificialmente a un benchmark profundo de LinkedIn porque la evidencia original seguia siendo incompleta.
- `Bandeja Puente` sigue sin acceso para la integracion Rick; el sistema ahora degrada limpio en vez de romperse.

## Veredicto
- Runtime de Rick endurecido: OK
- OpenClaw / Control Room sin residuos sueltos: OK
- Caso Kris regularizado por Rick, no por reemplazo manual: OK
