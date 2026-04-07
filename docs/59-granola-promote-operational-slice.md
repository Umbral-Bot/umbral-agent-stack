# 59 - Granola promote_operational_slice

> LEGACY V1 / SUPERSEDED: este orquestador compone `raw -> curado -> destino(s)`, un camino que ya no representa el contrato vigente de sesiones.

> Orquestador explicito para componer `raw -> curado -> destino(s)` reutilizando los handlers conservadores ya validados.

## 1. Objetivo

`granola.promote_operational_slice` existe para evitar que la futura automatizacion:

- duplique logica entre slices
- mezcle heuristicas opacas con escritura en Notion
- salte directo desde raw a multiples destinos sin evidencia intermedia

El handler no agrega clasificacion nueva.
Solo encadena los slices ya existentes cuando el payload lo pide de forma explicita.

## 2. Que compone

Siempre:

- `granola.promote_curated_session`

Opcionalmente:

- `granola.create_human_task_from_curated_session`
- `granola.update_commercial_project_from_curated_session`

## 3. Contrato minimo

```json
{
  "transcript_page_id": "<raw-page-id>",
  "curated_payload": {
    "session_name": "Konstruedu - propuesta 6 cursos"
  },
  "human_task_payload": {
    "task_name": "Revisar contrato Konstruedu"
  }
}
```

Debe existir siempre:

- `transcript_page_id`
- `curated_payload`

Y ademas al menos uno:

- `human_task_payload`
- `commercial_project_payload`

## 4. Que no hace

- no decide si la reunion merece promocion
- no inventa nombres de sesion, tarea o cambio comercial
- no llena automaticamente payloads faltantes
- no reemplaza la logica de los handlers subyacentes

## 5. Estado operativo actual

Al 2026-03-27:

- la promocion `raw -> curado` ya esta validada
- la creacion de tarea humana desde curado ya esta validada
- la actualizacion comercial desde curado ya esta validada
- el orquestador bundle ya quedo validado en vivo
- el `dry_run` compuesto ya quedo validado en vivo

## 6. Piloto live validado

Validacion ejecutada el 2026-03-27 con:

- raw page:
  - `Konstruedu`
  - page id: `3305f443-fb5c-81db-9162-fd70c8574938`
- sesion curada existente:
  - `Konstruedu - propuesta 6 cursos`
  - page id: `3305f443-fb5c-81cd-ba63-c6d06624f6a2`
- tarea humana existente:
  - `Revisar contrato Konstruedu`
  - page id: `3305f443-fb5c-81a0-8239-fd9ec0600ae3`
- proyecto comercial existente:
  - `Especializacion IA + Automatizacion AECO - 6 Cursos Konstruedu`
  - page id: `dcd955f0-28e5-432a-a7ed-9be1ea091a74`

Payload usado:

- `curated_payload` explicito
- `human_task_payload` explicito
- `commercial_project_payload` explicito
- `add_trace_comments = false` en subpayloads para evitar duplicacion

Resultado:

- `curated_session` actualizado con `matched_existing = true`
- `human_task` actualizada con `matched_existing = true`
- `commercial_project` actualizado por `page_id`

## 7. Soporte `dry_run`

El handler acepta:

```json
{
  "transcript_page_id": "<raw-page-id>",
  "dry_run": true,
  "curated_payload": {...},
  "human_task_payload": {...},
  "commercial_project_payload": {...}
}
```

Comportamiento:

- propaga `dry_run=true` a cada subhandler si no viene definido en el subpayload
- resuelve matches existentes
- devuelve el `properties` payload que escribiria cada slice
- no hace writes
- no deja comentarios de trazabilidad
- si la sesion curada todavia no existe, devuelve igual el preview de `curated`
- en ese caso marca los destinos downstream como `skipped = true` con razon:
  - `curated_session_page_id_unavailable_in_dry_run_for_new_session`

Esto es el gate correcto antes de correr lotes mas grandes.

## 8. Validacion live de `dry_run`

Validacion ejecutada el 2026-03-27 con `Konstruedu`:

- `curated_session`: `matched_existing = true`, `dry_run = true`
- `human_task`: `matched_existing = true`, `dry_run = true`
- `commercial_project`: `project_page_id` resuelto, `dry_run = true`

La salida incluyo los `properties` exactos que se escribirian en cada destino sin tocar Notion.

Validacion adicional del 2026-03-27 con lote real de 3 casos:

- `Konstruedu`: preview completo de `curated`, `human_task` y `commercial_project`
- `Borago`: preview completo de `curated`; destinos downstream `skipped` por ser sesion nueva
- `Asesoria discurso`: preview completo de `curated`; `human_task` `skipped` por la misma razon

Ese comportamiento parcial en `dry_run` es el esperado para lotes mixtos con sesiones existentes y nuevas.

## 9. Criterio de uso

Usar este orchestrator cuando:

- ya decidiste explicitamente que sesion curada crear o actualizar
- ya decidiste explicitamente si corresponde tarea humana y/o actualizacion comercial
- quieres una sola ejecucion de Worker sin duplicar payloads manuales

No usarlo como sustituto de clasificacion humana.

## 10. Referencias

- `worker/tasks/granola.py`
- `tests/test_granola.py`
- `docs/56-granola-promote-curated-session.md`
- `docs/57-granola-human-task-from-curated-session.md`
- `docs/58-granola-commercial-project-from-curated-session.md`
