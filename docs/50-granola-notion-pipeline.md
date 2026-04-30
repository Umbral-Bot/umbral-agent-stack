# Granola -> Notion Pipeline

Estado: 2026-04-03

## Objetivo

Definir el flujo operativo actual para reuniones capturadas en Granola:

1. preservar la transcripcion completa en `Transcripciones Granola`
2. evitar promociones implicitas a superficies canonicas
3. capitalizar despues desde raw solo cuando el target es deterministico

## Contrato vigente

La ingesta oficial ya no debe asumir `raw -> Registro de Sesiones y Transcripciones` como paso persistente por defecto.

El contrato de runtime del stack queda asi:

1. `granola_watcher.py` detecta o lee exports
2. `granola.process_transcript` escribe solo en raw
3. `granola.capitalize_raw` capitaliza desde raw a canonicos cuando el target es claro

El modo de rollout se controla con:

```text
GRANOLA_CAPITALIZATION_MODE=legacy_session | raw_direct_v2
```

Default:

```text
GRANOLA_CAPITALIZATION_MODE=legacy_session
```

En `legacy_session`, `granola.capitalize_raw` no hace writes canonicos live.

## Flujo operativo

```text
Granola export / cache / shared folder
        |
        v
scripts/vm/granola_watcher.py
        |
        v
POST /run -> granola.process_transcript
        |
        v
Notion DB: Transcripciones Granola (raw)
        |
        +--> vistas V2 de review en raw
        |
        +--> granola.capitalize_raw (solo si target deterministico)
                  |
                  +--> notion.upsert_task
                  +--> notion.upsert_project
                  +--> notion.upsert_deliverable
```

## Responsabilidades

### `granola.process_transcript`

Responsabilidad exacta:

1. crear la pagina raw en `Transcripciones Granola`
2. preservar transcript + metadata
3. detectar action items solo como senal
4. opcionalmente notificar a Enlace por comentario

No debe:

- crear tareas canonicas
- crear proyectos
- crear entregables
- escribir en `Registro de Sesiones y Transcripciones`

### `granola.capitalize_raw`

Responsabilidad exacta:

1. leer una fila raw existente
2. tomar transcript + metadata del raw
3. escribir un target canonico soportado
4. actualizar la fila raw con trazabilidad y estado

Targets soportados en el primer corte:

- `task`
- `project`
- `deliverable`

Targets no soportados aun para write automatico:

- `program`
- `resource`

Esos casos deben quedar en raw como `Revision requerida`.

## Variables de entorno

| Variable | Donde | Requerida | Descripcion |
|---|---|---|---|
| `GRANOLA_EXPORT_DIR` | VM watcher | si | carpeta de exports |
| `GRANOLA_PROCESSED_DIR` | VM watcher | no | carpeta de procesados |
| `WORKER_URL` | VM watcher | si | URL del worker |
| `WORKER_TOKEN` | watcher + worker | si | auth Bearer |
| `NOTION_GRANOLA_DB_ID` | worker | si | DB raw `Transcripciones Granola` |
| `NOTION_GRANOLA_SESSION_DB_ID` | worker/scripts | no | DB legacy `Registro de Sesiones y Transcripciones`; solo auditoria y migracion |
| `GRANOLA_CAPITALIZATION_MODE` | worker | no | `legacy_session` o `raw_direct_v2` |
| `NOTION_TASKS_DB_ID` | worker | no | target canonico para `task` |
| `NOTION_PROJECTS_DB_ID` | worker | no | target canonico para `project` |
| `NOTION_DELIVERABLES_DB_ID` | worker | no | target canonico para `deliverable` |
| `ENLACE_NOTION_USER_ID` | worker | no | soporte para comentarios de revision |

## Notas sobre schema raw

El rollout `raw_direct_v2` requiere que `Transcripciones Granola` tenga estos campos adicionales:

- `Dominio propuesto`
- `Tipo propuesto`
- `Destino canonico`
- `Proyecto relacionado`
- `Programa relacionado`
- `Recurso relacionado`

Tambien requiere vistas V2:

- `V2 - Raw pendientes`
- `V2 - Raw revision requerida`
- `V2 - Raw listos para capitalizar`
- `V2 - Raw capitalizados`

## Regla de seguridad

Si el target es ambiguo o no esta soportado:

- no escribir el canonico
- dejar la fila raw en `Revision requerida`
- registrar el motivo en `Log del agente`

## Formatos de entrada

El watcher debe soportar:

- export markdown clasico con `## Notes / ## Transcript / ## Action Items`
- export plano de carpeta compartida con:
  - `Meeting Title:`
  - `Date:`
  - `Meeting participants:`
  - `Transcript:`

La regla principal es preservar el contenido raw exacto y completo.
