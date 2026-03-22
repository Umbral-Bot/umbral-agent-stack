# Bridge inbox operationalization - 2026-03-17

## Objetivo
Convertir `Bandeja Puente` en un inbox operativo real para `OpenClaw`, en vez de dejarla solo como base accesible pero vacía o decorativa.

## Cambios aplicados
### Schema de `Bandeja Puente`
`scripts/provision_bridge_db_vps.py` ahora asegura este schema:
- `Ítem` (title)
- `Estado` (status)
- `Último movimiento` (date)
- `Notas` (rich_text)
- `Proyecto` (rich_text)
- `Prioridad` (select)
- `Origen` (select)
- `Siguiente acción` (rich_text)
- `Link` (url)

### Handler nuevo
Se añadió `notion.upsert_bridge_item` en:
- `worker/tasks/notion.py`
- `worker/tasks/__init__.py`

Capacidades:
- crea o actualiza ítems de bandeja
- acepta `page_id` explícito para update directo
- si no hay `page_id`, intenta resolver por título
- si el filtro exacto falla, hace fallback local por nombre leyendo la base completa

### UI de `OpenClaw`
`scripts/openclaw_panel_vps.py` ahora muestra `Bandeja viva` con:
- `Item`
- `Estado`
- `Proyecto`
- `Prioridad`
- `Siguiente acción`

La tarjeta principal de foco también usa `Proyecto` y `Siguiente acción`, no solo fecha o nota suelta.

### Integración con instrucciones de Notion
`dispatcher/smart_reply.py` ahora:
- crea una tarea de seguimiento
- crea además un ítem en `Bandeja Puente`
- y, si la instrucción cambia de `Nuevo` a `En curso` o `Esperando` en el mismo flujo, reutiliza el `page_id` de la primera creación para evitar duplicados por escrituras consecutivas

### Hardening del cliente Notion
`worker/notion_client.py` ahora reintenta `create_database_page()` y `update_page_properties()` sin icono cuando la API rechaza un emoji explícito de icono.

### Dashboard técnico alineado
`scripts/dashboard_report_vps.py` dejó de depender de un `NOTION_BRIDGE_DB_ID` hardcodeado.

Ahora resuelve `Bandeja Puente` con este orden:
1. `NOTION_BRIDGE_DB_ID` del entorno
2. child database `Bandeja Puente` bajo `OpenClaw`
3. fallback al ID legacy solo como respaldo

Eso evita que `Dashboard Rick` vuelva a leer una base equivocada si cambia la bandeja canónica.

## Verificación real en VPS
### Deploy
Se desplegaron y validaron en la VPS:
- `worker/tasks/notion.py`
- `worker/tasks/__init__.py`
- `worker/notion_client.py`
- `dispatcher/smart_reply.py`
- `scripts/provision_bridge_db_vps.py`
- `scripts/openclaw_panel_vps.py`
- `scripts/dashboard_report_vps.py`

### Smoke create/update
Se probó un smoke técnico controlado:
1. crear un ítem `Smoke tecnico de Bandeja Puente v3`
2. actualizar inmediatamente el mismo ítem a `Resuelto`
3. verificar que el segundo upsert no creara una página nueva

Resultado:
- `first_created = True`
- `second_created = False`
- un solo match para `Smoke tecnico de Bandeja Puente v3`
- estado final: `Resuelto`

### Limpieza
Los smokes técnicos se archivaron después de la prueba.

Estado final de la bandeja tras refresh y curación:
- `bridge_available = true`
- `bridge_total = 0`
- `bridge_live = 0`
- `bridge_resolved = 0`

### Shell `OpenClaw`
Refresh real en VPS:
- `validation.ok = true`
- `child_databases_after_anchor = 4`
- `residual_child_pages = 0`

### Dashboard técnico
Refresh real en VPS:
- `Dashboard actualizado ... {'updated': True, 'blocks_appended': 24}`

## Resultado
`Bandeja Puente` dejó de ser una base “visible pero inútil” y quedó lista para servir como inbox real de coordinación dentro de `OpenClaw`, tanto para triage humano como para seguimiento estructurado de instrucciones y pendientes.
