# Granola Transcript Finality + Reconciliation

> Este documento cubre el gate de estabilidad, la reconciliación idempotente
> y la auditoría manual del pipeline `granola.process_transcript`.
>
> Alcance: **sólo** capa raw de Granola (`NOTION_GRANOLA_DB_ID`). No afecta
> supervisor, OpenClaw, Phase 6B, ni la capa curada humana.

## 0. Causa raíz (caso real)

En la página `Transcripciones Granola / Comgrap Dynamo` quedó persistida una
versión parcial de la transcripción: Notion AI detectó que el texto terminaba
mid-frase en

```
Entonces Me imagino, sí. Decía Lillo. De hecho, lo lo planteé a la señora,
```

La trazabilidad mostraba `ingest_path=granola.process_transcript` y un
`source_updated_at` temprano. El pipeline había disparado `process_transcript`
antes de que Granola terminara de actualizar el documento remoto y, como el
mismo `granola_document_id` llegó después con contenido más completo, el
comportamiento anterior no reconciliaba: el raw quedaba congelado en la
versión truncada y la capitalización posterior usaba un transcript corto.

Los dos problemas combinados:

1. **Falta de gate de estabilidad.** Granola marca un documento como
   actualizado apenas arranca la transcripción; la ingesta no esperaba a que
   el documento fuera "final".
2. **Reconciliación ausente.** Aunque los helpers `_find_existing_raw_candidate`
   ya matcheaban por `granola_document_id`, `_upsert_raw_transcript_page`
   reemplazaba propiedades y bloques sin comparar hash / char_count, y jamás
   corría un detector de truncamiento.

## 1. Nuevo flujo

```
granola.process_transcript(input)
    │
    ▼
compute_transcript_metrics(content)
    │  content_hash, char_count, segment_count, last_chars
    ▼
detect_truncation(content)
    │  truncated?, reason, tail_terminator
    ▼
read Notion raw DB schema + existing rows
    │
    ▼
_find_existing_raw_candidate(...)
    │  (por granola_document_id, source_url, export_signature, content_hash,
    │   shared_folder_path, sha1, título+fecha — sin cambios)
    ▼
decide_reconciliation(
    existing, new_content, source_updated_at,
    stability_window, min_chars, force_reconcile)
    │
    ├─► action = "defer"    → no-op; se devuelve deferred=true
    ├─► action = "noop"     → no-op; métricas idénticas
    ├─► action = "create"   → crea nueva página raw
    └─► action = "reconcile"→ UPDATE in-place misma page_id
```

### Estados posibles

| acción       | condición                                                                 | efecto                                                                 |
|--------------|---------------------------------------------------------------------------|------------------------------------------------------------------------|
| `create`     | no existía página raw y el transcript no está en la ventana de estabilidad | crea la página raw con todas las métricas, `ingested_at=now`.         |
| `reconcile`  | existe raw con el mismo `granola_document_id` (u otra llave) y el contenido difiere | **actualiza la misma page_id**, `reconciled_at=now`, preserva `ingested_at`. |
| `noop`       | existe raw y `content_hash` + `char_count` son idénticos                  | no se hace ninguna escritura en Notion.                                |
| `defer`      | primera ingesta, `source_updated_at` más reciente que la ventana          | no se crea ni actualiza; próxima corrida repite.                       |

`force_reconcile=true` convierte `noop` en `reconcile`. Nunca convierte
`defer` en escritura — para saltar la ventana hay que pasar
`stability_window_seconds=0` explícito.

## 2. Métricas persistidas

En cada raw se guardan (cuando el schema expone las columnas correspondientes
y siempre en `Trazabilidad`):

- `content_hash` — SHA-1 del cuerpo normalizado.
- `char_count` — largo exacto del content enviado.
- `segment_count` — turnos hablante / bullets detectados; fallback a líneas
  no vacías.
- `source_updated_at` — timestamp reportado por Granola (ya existía).
- `ingested_at` — primera vez que el pipeline creó la página raw.
- `reconciled_at` — última vez que el pipeline actualizó el mismo raw.
- `truncation_detected` + `truncation_reason` — output del detector.

Si el DB tiene columnas con los nombres `Char Count`, `Segment Count`,
`Ingested At`, `Reconciled At`, `Truncation Detected` (o `Truncado`), el
worker las llena automáticamente. Si no, sólo se persisten en
`Trazabilidad`. **No es necesario modificar el schema para que esto funcione.**

## 3. Detector de truncamiento

`worker.tasks.granola_finality.detect_truncation(content)` marca una
transcripción como truncada cuando:

- está vacía o es más corta que `GRANOLA_MIN_STABLE_CHARS` (default 200);
- el último carácter no-whitespace es `,`, `;`, `:`, `-`, `—`, `–`;
- el último fragmento tras el último terminador (`. ! ? …`) tiene menos de
  ~4 palabras (fragmento huérfano);
- no aparece ningún terminador de oración en todo el cuerpo.

Los casos "feliz" (termina en punto, punto dentro de comilla, etc.) no se
reportan como truncados.

Cuando un raw queda marcado con `truncation_detected=true` en su
trazabilidad, un ingest posterior **no truncado** se marca como `reconcile`
aunque las métricas de hash coincidan (ver
`decide_reconciliation → recovered_from_truncation`).

## 4. Dry-run / audit

`granola.process_transcript` ahora acepta dos modos equivalentes de preview:

```python
{"title": "...", "content": "...", "dry_run": true}
# o
{"title": "...", "content": "...", "audit": true}
```

En modo dry-run:

- **no se llama** a `create_database_page`, `update_page_properties`,
  `replace_blocks_in_page`, ni `add_comment`.
- se devuelve `reconciliation`, `reconciliation_action`, y
  `preview_properties` / `preview_block_count` / `effective_traceability_text`
  dentro de `page_result`.
- `notify_enlace` queda siempre forzado a falso.
- `action_items_created` siempre es `0`.

Esto permite auditar qué pasaría antes de disparar la reconciliación en vivo.

## 5. Variables de entorno

| Variable                              | Dónde            | Default | Uso                                                                 |
|---------------------------------------|------------------|---------|---------------------------------------------------------------------|
| `GRANOLA_STABILITY_WINDOW_SECONDS`    | Worker           | `900`   | Ventana después de `source_updated_at` en la que el ingest se difiere. |
| `GRANOLA_MIN_STABLE_CHARS`            | Worker           | `200`   | Contenido con menos caracteres queda marcado como truncado.         |

Por request se pueden sobreescribir con:

- `stability_window_seconds` (int segundos; `0` desactiva la ventana)
- `min_stable_chars` (int caracteres)
- `force_reconcile` (bool)
- `dry_run` / `audit` (bool)

## 6. Reparación manual

Cuando David o Enlace detectan una página raw truncada (tipo Comgrap Dynamo):

```bash
# 1) Preview: qué va a reconciliar, sin tocar Notion.
python scripts/repair_granola_transcript.py \
    --page-id 3305f443-fb5c-81db-9162-fd70c8574938 \
    --content-file ./exports/comgrap-dynamo.md \
    --mode local --json

# 2) Repair real, usando la misma page_id y URL.
python scripts/repair_granola_transcript.py \
    --page-id 3305f443-fb5c-81db-9162-fd70c8574938 \
    --content-file ./exports/comgrap-dynamo.md \
    --execute --mode worker --json

# 3) O desde la VM, tomando la versión completa directamente del API privada.
python scripts/repair_granola_transcript.py \
    --granola-document-id 4d4c239d-... \
    --fetch-from-granola --execute --mode local --json
```

Reglas de uso:

- El script **no hardcodea contenido sensible**. El texto real viene siempre
  de `--content-file`, stdin o el API privada de Granola en la VM.
- `--force-reconcile` está activado por default (es el punto de un repair).
- `--dry-run` (default) y `--execute` son mutuamente excluyentes al leer.
- Cada corrida deja un JSON line en
  `.tmp/granola_repair_audit.jsonl` (override con
  `GRANOLA_REPAIR_AUDIT_LOG`) con `granola_document_id`, `action`,
  `reason`, `dry_run`, `mode`, `page_id`, `content_chars`.

### Comando inverso: sólo auditar

```bash
python scripts/repair_granola_transcript.py \
    --page-id <ID> --content-file transcript.md \
    --mode local --dry-run --json
```

## 7. Auditoría 7 / 30 días

Tres puntos de chequeo recomendados para David:

1. **Trazabilidad de cada raw ingerida/reconciliada.**
   - Columna `Trazabilidad` debe contener
     `content_hash`, `char_count`, `segment_count`, `ingested_at`,
     y cuando aplique `reconciled_at` y `truncation_detected=false`.
   - Filtrar raws con `truncation_detected=true` para candidatas de repair.

2. **Log del worker.**
   - Cada corrida emite `Granola raw action=<create|reconcile|noop|defer>
     reason=... page_id=... url=... dry_run=...`.
   - Filtrar por `reason=source_updated_at too recent` para confirmar que la
     ventana de estabilidad está frenando ingestas tempranas.

3. **Audit log del repair script.**
   - `.tmp/granola_repair_audit.jsonl` contiene un registro append-only por
     repair (dry-run o execute). Se recomienda rotarlo semanalmente y
     revisarlo en la ventana 7 / 30 días:

     ```bash
     tail -n 100 .tmp/granola_repair_audit.jsonl | jq -r \
       '[.generated_at, .granola_document_id, .response.reconciliation.action, .response.reconciliation.reason] | @tsv'
     ```

Ejemplos de señales a vigilar:

- varios `action=reconcile` para el mismo `granola_document_id` en < 1 h →
  Granola sigue actualizando después de lo esperado; considerar ampliar
  `GRANOLA_STABILITY_WINDOW_SECONDS`.
- `action=noop` con `truncation_detected=true` previo → contenido nuevo
  también llegó truncado; habilitar repair manual con otra fuente.
- `action=defer` en cada corrida durante > 1 día para el mismo id → Granola
  nunca marca el documento como estable; investigar la reunión manualmente.

## 8. Qué NO cambia

- Dispatcher, supervisor, OpenClaw, `config/supervisors.yaml` y Phase 6B
  quedan intactos.
- Las tareas `granola.capitalize_raw`, `granola.promote_curated_session`,
  `granola.create_human_task_from_curated_session`,
  `granola.update_commercial_project_from_curated_session`,
  `granola.promote_operational_slice` no se tocan.
- El schema de la DB raw no requiere cambios para que la finality gate
  funcione — todo se persiste en `Trazabilidad` por default.

## 9. Referencias

- `worker/tasks/granola_finality.py` (nuevo)
- `worker/tasks/granola.py` — `_upsert_raw_transcript_page`,
  `handle_granola_process_transcript`.
- `scripts/repair_granola_transcript.py` (nuevo)
- `tests/test_granola_transcript_reconciliation.py` (nuevo)
- `docs/50-granola-notion-pipeline.md`
- `docs/64-granola-raw-ingest-batch.md`
- `docs/65-granola-vm-raw-intake.md`
