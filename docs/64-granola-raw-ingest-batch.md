# Granola Raw Ingest Batch

Runner operativo para que Rick mueva backlog de Granola a la DB raw de Notion
sin abrir la puerta a capitalización canónica.

## Qué hace

- consume el reporte live de `scripts/list_granola_raw_ingest_gap.py`
- selecciona un bucket de backlog
- exporta solo esos documentos de Granola a markdown temporal
- ejecuta `granola.process_transcript` en modo `worker` o `local`
- persiste trazabilidad fuerte en raw:
  - `granola_document_id`
  - `source_updated_at`
  - `source_url`
  - `ingest_path=granola.process_transcript`

## Qué no hace

- no hace `raw -> canonical`
- no promueve a `session_capitalizable`
- no escribe CRM, programas o recursos
- no activa `allow_legacy_raw_task_writes`
- no notifica a Enlace por defecto

## Precondiciones

- `.env` local con:
  - `NOTION_API_KEY`
  - `NOTION_GRANOLA_DB_ID`
- cache local accesible:
  - `%APPDATA%\\Granola\\cache-v6.json`
- opcional para modo worker:
  - `WORKER_URL`
  - `WORKER_TOKEN`

## Preview seguro

```powershell
python scripts/run_granola_raw_ingest_batch.py --json
```

Comportamiento esperado:

- usa el bucket `batch1_recent_unique`
- no escribe en Notion
- deja markdown temporal en `.tmp/granola_raw_ingest_batch/<timestamp>/exports`
- muestra qué documentos quedarían listos para ingest

## Ejecución real mínima

Modo local:

```powershell
python scripts/run_granola_raw_ingest_batch.py --execute --mode local --json
```

Modo worker:

```powershell
python scripts/run_granola_raw_ingest_batch.py --execute --mode worker --json
```

## Batch recomendado inicial

Usar solo `batch1_recent_unique` hasta que el backlog histórico quede más limpio.

No ejecutar buckets ambiguos salvo revisión humana explícita.

Si de verdad hace falta revisar uno ambiguo:

```powershell
python scripts/run_granola_raw_ingest_batch.py --bucket batch1_recent_ambiguous --allow-ambiguous --json
```

Primero en preview. No ejecutar a ciegas.

## Señales de éxito

- cada resultado devuelve `ok=true`
- la página raw creada devuelve `page_id` y `url`
- `traceability_written=true`
- en raw queda poblada la propiedad `Trazabilidad` cuando existe en el schema

## Señales de fallo

- `missing_document_ids` no vacío
- errores de Notion auth/share
- modo `worker` sin reachability a `WORKER_URL`
- rows duplicadas por títulos ambiguos si se fuerza un bucket ambiguo sin revisión

## Nota operativa

El gap report sigue siendo conservador porque el histórico raw previo no
persistía de forma confiable `granola_document_id`. Los nuevos ingests sí lo
harán, lo que mejora la reconciliación para los próximos batches.
