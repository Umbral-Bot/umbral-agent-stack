# Bandeja Puente Provisioning - 2026-03-17

## Objetivo
Eliminar el estado degradado de `OpenClaw` donde la seccion `Bandeja viva` mostraba `Sin acceso actual a Bandeja Puente`.

## Diagnostico
El problema no era solo de permisos sobre una base antigua.

Estado real observado:
- `OpenClaw` no tenia ninguna child database titulada `Bandeja Puente`.
- `~/.config/openclaw/env` no tenia `NOTION_BRIDGE_DB_ID`.
- `scripts/notion_curate_ops_vps.py` seguia dependiendo de un ID legacy fijo (`8496ee73-6c7d-43a3-89cf-b9c8825b5dfc`).

Conclusión:
- el panel no tenia una bandeja operativa canónica que Rick pudiera leer hoy.

## Cambios aplicados

### 1. Resolucion dinamica de la bandeja
En `scripts/notion_curate_ops_vps.py`:
- se reemplazo la dependencia dura por `LEGACY_BRIDGE_DB_ID`;
- se agrego `_resolve_bridge_db_id()` con este orden:
  1. `config.NOTION_BRIDGE_DB_ID`
  2. child database `Bandeja Puente` bajo `OpenClaw`
  3. fallback al ID legacy
- `curate_bridge()` y `_db_counts()` ahora usan esa resolucion dinamica.

### 2. Degradacion limpia
Si la base no existe o no responde:
- la curacion ya no se rompe;
- reporta `bridge_available = false` y conteos en `0`.

### 3. Provisionador reproducible
Se agrego:
- `scripts/provision_bridge_db_vps.py`

Este script:
- reutiliza una DB `Bandeja Puente` si ya existe bajo `OpenClaw`;
- si no existe, crea una nueva con schema minimo compatible:
  - `Ítem` (title)
  - `Estado` (status)
  - `Último movimiento` (date)
  - `Notas` (rich_text)

### 4. Provision real en VPS
Se ejecuto en la VPS y se creo:
- DB `Bandeja Puente`
- ID: `3265f443-fb5c-81c6-a104-e383b4fdfdf4`

Tambien se actualizo:
- `/home/rick/.config/openclaw/env`
- `NOTION_BRIDGE_DB_ID=3265f443-fb5c-81c6-a104-e383b4fdfdf4`

## Verificacion

### OpenClaw shell
- `scripts/openclaw_panel_vps.py` ejecuto OK
- validacion:
  - `ok = true`
  - `child_databases_after_anchor = 4`
  - `residual_child_pages = 0`

### Conteos operativos
`scripts/notion_curate_ops_vps.py` ya devuelve:
- `bridge_available = true`
- `bridge_total = 0`
- `bridge_live = 0`
- `bridge_resolved = 0`

### Lectura directa
`read_database(NOTION_BRIDGE_DB_ID)` devuelve:
- titulo: `Bandeja Puente`
- count: `0`

## Resultado
`OpenClaw` deja de estar degradado por ausencia de bandeja.

El estado correcto ahora es:
- bandeja disponible
- sin items vivos

Eso es diferente de:
- sin acceso

## Residual
No hubo migracion del contenido de la base legacy inaccesible.

Se eligio una base nueva y canónica porque:
- el ID legacy ya no estaba operativo para Rick;
- y el panel necesitaba una fuente viva y soportada hoy.
