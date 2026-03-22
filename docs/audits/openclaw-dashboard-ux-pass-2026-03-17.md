# OpenClaw Dashboard UX Pass — 2026-03-17

## Objetivo

Mejorar la interfaz operativa de `OpenClaw` en Notion para que funcione como panel humano usable y no como reporte textual, sin romper el flujo estructurado:

- `Dashboard Rick` = dashboard tecnico
- `OpenClaw` = panel operativo humano
- `Proyectos / Tareas / Entregables / Bandeja Puente` = bases operativas

## Problemas detectados

1. `OpenClaw` seguia viendose como reporte:
   - frases sueltas
   - poca jerarquia visual
   - sin una prioridad humana evidente al entrar

2. El wrapper `scripts/vps/dashboard-cron.sh` era fragil:
   - si fallaba `Dashboard Rick`, no necesariamente quedaba claro si `OpenClaw` se refrescaba
   - habia line endings Windows (`CRLF`) en wrappers de VPS

3. `Dashboard Rick` estaba caido:
   - `NOTION_DASHBOARD_PAGE_ID` apuntaba a un page id inexistente / no compartido
   - `dashboard_report_vps.py` devolvia 500 por `notion.update_dashboard`

4. `OpenClaw` podia fallar al limpiar bloques ya archivados:
   - Notion devolvia `Can't edit block that is archived`

## Cambios aplicados

### UX de OpenClaw

Se rediseño `scripts/openclaw_panel_vps.py` para que el panel tenga:

- tarjeta principal de decision (`Prioridad inmediata`)
- KPI cards compactas por columna, sin texto suelto debajo
- segunda fila con:
  - `Estado del panel`
  - `Como usar este panel`
- tablas compactas para:
  - `Entregables por revisar`
  - `Proyectos que requieren atencion`
  - `Bandeja viva`
  - `Proximos vencimientos`

### Priorizacion

Se ajusto la priorizacion de entregables:

- primero `Pendiente revision`
- despues `Aprobado con ajustes`
- luego fecha sugerida

Tambien se reforzo la sincronizacion del callout principal para que, despues del insert, reescriba el resumen con un snapshot fresco y no quede un foco viejo.

### Hardening de shell

`validate_openclaw_shell()` ahora permite `Dashboard Rick` como child page tecnico valido, sin contarla como residuo.

### Dashboard Rick

Se reprovisiono una pagina nueva `Dashboard Rick` en Notion y se actualizo:

- `NOTION_DASHBOARD_PAGE_ID=3265f443-fb5c-816d-9ce8-c5d6cf075f9c`

Despues se reinicio el worker para que tomara el env nuevo.

### Wrappers VPS

Se agrego `.gitattributes`:

- `*.sh text eol=lf`

Y se normalizaron los wrappers `scripts/vps/*.sh` a LF.

Ademas, `scripts/vps/dashboard-cron.sh` quedo resiliente:

- si falla `dashboard_report_vps.py`, igual intenta correr `openclaw_panel_vps.py`
- devuelve estado no-cero si algo falla, pero no corta el panel humano por un fallo tecnico del dashboard

### Cleanup tolerante

`_delete_blocks()` en `scripts/openclaw_panel_vps.py` ahora ignora de forma segura:

- bloques ya archivados
- bloques ya no encontrados

## Verificacion

### Local

- `python -m pytest tests/test_openclaw_panel.py tests/test_dashboard.py tests/test_notion_ops_curation.py -q`
  - `46 passed`
- `python -m py_compile scripts/openclaw_panel_vps.py scripts/dashboard_report_vps.py`
  - OK
- `python scripts/validate_skills.py`
  - OK

### VPS / Notion real

Wrapper real ejecutado:

- `/bin/bash /home/rick/umbral-agent-stack/scripts/vps/dashboard-cron.sh`

Resultado:

- `Dashboard actualizado ... {'updated': True, 'blocks_appended': 21}`
- `OpenClaw ... validation.ok = true`

Lectura real de `OpenClaw`:

- callout principal = `Prioridad inmediata`
- foco actual = benchmark de Ruben Hassid en `Proyecto Embudo Ventas`
- `quick_access_present = true`
- `residual_child_pages = 0`

Lectura real de `Dashboard Rick`:

- pagina accesible
- heading principal `Dashboard Rick`
- callout de estado tecnico visible

## Resultado

`OpenClaw` ya funciona como panel humano usable:

- mas jerarquia
- mejor foco
- menos aspecto de reporte textual
- mejor resiliencia frente a fallos del dashboard tecnico

`Dashboard Rick` volvio a quedar operativo.

## Residual no bloqueante

1. `Dashboard Rick` sigue siendo tecnico y utilitario.
   - Esta bien para su rol.
   - Si se quisiera, se puede mejorar despues con mas jerarquia visual, pero ya no bloquea.

2. `Dashboard Rick` como child page tecnico existe, pero no esta todavia reordenado visualmente como acceso rapido perfecto dentro de `OpenClaw`.
   - No bloquea la operacion.
   - Puede refinarse en otra pasada si se quiere optimizar navegacion.
