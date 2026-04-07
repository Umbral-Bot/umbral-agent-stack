# 60 - Granola operational batch runner

> LEGACY V1 / SUPERSEDED: este runner opera planes que todavia pasan por `curated_payload`. No tratarlo como camino normal del flujo V2 directo.

> Runner repo-side para ejecutar lotes explicitos del pipeline `raw -> curado -> destino(s)` usando planes JSON versionables.

## 1. Objetivo

`scripts/run_granola_operational_batch.py` existe para evitar dos problemas:

- correr payloads complejos a mano uno por uno
- escalar a lotes sin perder el gate de seguridad y trazabilidad

El runner no clasifica reuniones.
Solo ejecuta planes explicitos contra `granola.promote_operational_slice`.

## 2. Principios

- `dry_run` por defecto
- planes JSON explicitos
- un plan por reunion
- sin inferencias automaticas nuevas
- la decision humana sigue ocurriendo antes del write real

## 3. Formato del plan

Aporta:

- un array JSON
- o un objeto con `plans: []`

Cada plan debe incluir:

- `transcript_page_id`
- `curated_payload`
- y al menos uno:
  - `human_task_payload`
  - `commercial_project_payload`

Template repo-side:

- `scripts/templates/granola_operational_batch.plan.template.json`

## 4. Ejemplo minimo

```json
{
  "plans": [
    {
      "label": "konstruedu-contract-followup",
      "transcript_page_id": "3305f443-fb5c-81db-9162-fd70c8574938",
      "curated_payload": {
        "session_name": "Konstruedu - propuesta 6 cursos"
      },
      "human_task_payload": {
        "task_name": "Revisar contrato Konstruedu"
      }
    }
  ]
}
```

## 5. Uso recomendado

### 5.1 Dry run

```powershell
python scripts/run_granola_operational_batch.py scripts/templates/granola_operational_batch.plan.template.json --json
```

### 5.2 Ejecucion real

```powershell
python scripts/run_granola_operational_batch.py path\\to\\batch.plan.json --execute --json
```

## 6. Filtros utiles

El runner soporta:

- `--only-label`
- `--only-transcript-page-id`
- `--limit`

Esto permite preparar un lote de 5 planes y ejecutar solo 1 o 2 primero.

## 7. Regla de seguridad

El flujo correcto para un lote nuevo es:

1. preparar 3 a 5 planes explicitos
2. correr `dry_run`
3. inspeccionar:
   - `matched_existing`
   - `schema_fields_used`
   - `properties` que se escribirian
   - `skipped` si la sesion curada aun no existe
4. recien despues correr `--execute`

No conviene saltarse el preview.

## 8. Comportamiento esperado en `dry_run`

Para reuniones ya promovidas a curado:

- el runner devuelve preview completo de `curated`, `human_task` y/o `commercial_project`

Para reuniones nuevas:

- devuelve preview completo de `curated`
- los destinos downstream pueden venir como:
  - `skipped = true`
  - `reason = curated_session_page_id_unavailable_in_dry_run_for_new_session`

Eso evita falsos errores de infraestructura cuando el lote mezcla casos existentes y nuevos.

## 9. Validacion ejecutada

Al 2026-03-27 quedo validado:

- parser del runner
- validacion de planes
- filtro por `label`
- ejecucion `dry_run` contra el Worker real
- template repo-side con `Konstruedu`
- primer lote local de 3 casos:
  - `Konstruedu`
  - `Borago`
  - `Asesoria discurso`

Resultado observado:

- `dry_run` del lote: `count = 3`, `ok = 3`
- `Konstruedu`: preview completo de los tres slices
- `Borago`: preview completo de `curated`; downstream `skipped`
- `Asesoria discurso`: preview completo de `curated`; downstream `skipped`
- ejecucion real posterior:
  - `Borago` creado en curado + tarea humana + comentario comercial
  - `Asesoria discurso` creada en curado + tarea humana

## 10. Que sigue

Con este runner ya no falta infraestructura.
Lo siguiente es curar mas lotes explicitos de 3 a 5 reuniones reales:

- primero en `dry_run`
- luego en `--execute`

## 11. Referencias

- `scripts/run_granola_operational_batch.py`
- `scripts/templates/granola_operational_batch.plan.template.json`
- `worker/tasks/granola.py`
- `docs/59-granola-promote-operational-slice.md`
