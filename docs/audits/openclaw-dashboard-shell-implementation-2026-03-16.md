# OpenClaw dashboard shell implementation

Fecha: 2026-03-16  
Autor: Codex

## Objetivo

Cerrar la brecha entre el diagnostico UX de `OpenClaw` y una shell operativa real:

- sin texto suelto tipo reporte,
- con lectura rapida visual,
- preservando navegacion util al resto del workspace,
- y sin volver fragil el refresh automatico.

## Problemas detectados

1. `OpenClaw` seguia comportandose como reporte generado.
2. La parte baja de la pagina quedaba desordenada:
   - links sueltos sin seccion,
   - headings duplicados,
   - historico mezclado con accesos vivos.
3. El renderer dependia de un ID fijo de `Bandeja Puente`.
4. Si ese ID dejaba de estar compartido con la integracion Rick, el refresh podia romperse.

## Cambios aplicados

### 1. Shell visual de dashboard

Se reemplazo el bloque superior por una shell compacta con:

- callout de rol de la pagina,
- resumen operativo,
- tarjetas KPI en `column_list`,
- tablas compactas para:
  - `Entregables por revisar`
  - `Proyectos que requieren atencion`
  - `Bandeja viva`
  - `Proximos vencimientos`

### 2. Navegacion inferior ordenada

La parte baja de `OpenClaw` quedo separada en:

- `Accesos rapidos`
- `Bases operativas`
- `Historico reciente`

Estructura verificada en vivo:

1. `OpenClaw` callout
2. `Resumen operativo`
3. tarjetas KPI
4. cuatro tablas de prioridad
5. `Accesos rapidos`
6. `Bases operativas`
7. `Historico reciente`

### 3. Resiliencia ante drift de Notion

El renderer ya no depende solo de un ID fijo de `Bandeja Puente`.

Se agrego:

- `NOTION_BRIDGE_DB_ID` opcional en config/env
- descubrimiento por titulo cuando exista la base en la pagina
- fallback seguro si la base no esta accesible

Si `Bandeja Puente` no esta compartida con la integracion:

- el refresh no se cae,
- la tarjeta muestra `0`,
- y el texto explicita `Sin acceso actual a Bandeja Puente.`

## Validacion

Local:

- `python -m pytest tests/test_openclaw_panel.py tests/test_dashboard.py -q`
  - `24 passed`
- `python -m py_compile scripts/openclaw_panel_vps.py worker/config.py`
  - OK
- `python scripts/validate_skills.py`
  - OK

VPS / Notion:

- deploy de `scripts/openclaw_panel_vps.py`
- limpieza de `__pycache__` para evitar bytecode stale
- refresh remoto:
  - `{"updated": true, "panel_blocks": 12, "validation": {"ok": true, "first_callout": true, "bases_anchor": true, "child_databases_after_anchor": 3}}`

Verificacion en vivo de la pagina:

- shell superior visible con `24` bloques top-level
- `Accesos rapidos` presente
- `Bases operativas` presente
- `Historico reciente` presente
- tarjeta `Bandeja` muestra explicitamente falta de acceso

## Residual real

La deuda que sigue abierta no es del renderer sino de Notion:

- `Bandeja Puente` no esta accesible para la integracion Rick
- por eso no se puede usar hoy como fuente viva dentro del shell

Mientras eso no se resuelva:

- el dashboard queda honesto y estable,
- pero la bandeja no aporta datos vivos al resumen

## Siguiente paso recomendado

Recompartir `Bandeja Puente` con la integracion Rick o reemplazarla por una base nueva oficialmente soportada por el flujo actual.
