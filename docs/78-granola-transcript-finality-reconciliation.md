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

## 7.1 Seguridad del matching por título/fecha

`_find_existing_raw_candidate` sigue aceptando el fallback `exact_title_date` /
`normalized_title_date` pero **ya no cruza barreras de `granola_document_id`**:

- si el payload entrante trae un `granola_document_id` no vacío y existe una
  página cuyo `granola_document_id` también es no vacío y **distinto**, la
  página queda excluida del fallback aunque compartan título y fecha;
- sólo se permite el match débil contra legacy pages *sin* `granola_document_id`,
  que son exactamente las que necesitan ser reconciliadas / backfilleadas.

Esto bloquea el caso en que dos reuniones reales distintas comparten título y
día (muy frecuente con "Comgrap Dynamo", "Standup", "Revisión semanal", etc.)
y evita que la ingesta colapse dos documentos Granola separados en una misma
página raw.

## 8. Qué NO cambia

- Dispatcher, supervisor, OpenClaw, `config/supervisors.yaml` y Phase 6B
  quedan intactos.
- Las tareas `granola.capitalize_raw`, `granola.promote_curated_session`,
  `granola.create_human_task_from_curated_session`,
  `granola.update_commercial_project_from_curated_session`,
  `granola.promote_operational_slice` no se tocan.
- El schema de la DB raw no requiere cambios para que la finality gate
  funcione — todo se persiste en `Trazabilidad` por default.

## 10. Trazabilidad de regularizaciones manuales

### 10.1 Brecha observada (Comgrap Dynamo)

PR #245 (este doc / reconciliación) y PR #246 (guardrails de
capitalización) resuelven el problema sistémico en el pipeline:
reuniones con identidad comercial ya no pueden cerrarse como “tarea
suelta”, y los raws truncados pueden reconciliarse in-place.

Pero en el caso real Comgrap Dynamo la regularización en Notion se hizo
**a mano con `curl` directo desde la VPS**:

- Se creó el proyecto `COMGRAP — Demo Dynamo / prefabricados de hormigon`.
- Se vinculó raw ⇄ proyecto ⇄ tarea.
- Se añadieron comentarios cruzados.
- La raw quedó `Pendiente / Revision requerida`.

Esa regularización es válida como trazabilidad humana dentro de Notion,
pero **no dejó evento central en `ops_log.jsonl`**: no hay
`operation_id`, no hay `trace_id`, no hay `source`, no hay conteo de
lecturas/escrituras, y no hay forma de auditar desde el stack qué
agente/script hizo qué operación sobre qué páginas.

### 10.2 Regla normativa

> Toda regularización manual sobre Notion hecha con API/curl/script
> directo debe emitir un evento `notion.operation_trace` con
> `operation_id`. No cerrar como trazado si solo hay comentarios en
> Notion.

### 10.3 Primitiva y CLI

Disponibles en `main` (sin tocar runtime, supervisor, OpenClaw ni
dispatcher routing):

- `infra.ops_logger.OpsLogger.notion_operation(...)` — método Python.
- `scripts/notion_trace_operation.py` — CLI con `--dry-run`.

Campos del evento (clave = `notion.operation_trace`):

| Campo              | Descripción                                              |
|--------------------|----------------------------------------------------------|
| `operation_id`     | UUID4 auto-generado si no se provee, o el valor dado.    |
| `actor`            | Quién ejecutó (david, copilot, claude, rick, ...).       |
| `action`           | Acción lógica corta (`regularize_granola_capitalization`).|
| `reason`           | Motivo estructurado (truncado a 300 chars).              |
| `raw_page_id`      | Página raw origen, si aplica.                            |
| `target_page_ids`  | Lista corta (≤25) de IDs/URLs afectados, deduplicada.    |
| `source`           | Origen (`vps_curl`, `copilot_script`, `cursor_agent`).   |
| `source_kind`      | Subtipo (`manual_regularization`, `cli`, `curl`).        |
| `notion_reads`     | Cantidad aproximada de reads reales a Notion.            |
| `notion_writes`    | Cantidad aproximada de writes reales a Notion.           |
| `status`           | `ok` / `partial` / `failed` / `rolled_back`.             |
| `details`          | Texto breve (truncado a 500 chars). Sin transcript ni prompts. |
| `ts`               | Aportado automáticamente por `OpsLogger._write`.         |

### 10.4 Ejemplo de regresión — Comgrap Dynamo

Este comando **no** hace llamadas a Notion; solo deja el breadcrumb:

```bash
python scripts/notion_trace_operation.py \
    --actor copilot \
    --action regularize_granola_capitalization \
    --reason task_only_capitalization_corrected_to_project_task \
    --raw-page-id 3485f443-fb5c-81e9-ae88-fe2fb7cd7b54 \
    --target-page-id df938460-fdee-4752-b9d4-293bede5e541 \
    --target-page-id 3485f443-fb5c-8198-9f54-fc5882302bf2 \
    --source vps_curl \
    --source-kind manual_regularization \
    --notion-reads 3 --notion-writes 5 \
    --status ok \
    --details "created project, linked raw and task, added cross comments"
```

Dry-run equivalente (no escribe en `ops_log.jsonl`):

```bash
python scripts/notion_trace_operation.py --dry-run \
    --actor copilot --action regularize_granola_capitalization \
    --reason example
```

### 10.5 Garantías

- No se persiste transcript completo, prompts completos ni contenido
  largo de páginas Notion. `details` queda acotado a 500 chars.
- `operation_id` siempre está presente en el evento persistido.
- El logger **nunca rompe la operación del caller** si el write al log
  falla; solo loguea el error a `logging.debug`.
- El CLI **no** requiere `NOTION_API_KEY` porque no llama a Notion.

## 11. Referencias

- `worker/tasks/granola_finality.py` (PR #245)
- `worker/tasks/granola.py` — `_upsert_raw_transcript_page`,
  `handle_granola_process_transcript`.
- `scripts/repair_granola_transcript.py` (PR #245)
- `tests/test_granola_transcript_reconciliation.py` (PR #245)
- `infra/ops_logger.py` — `notion_operation(...)`, evento
  `notion.operation_trace`.
- `scripts/notion_trace_operation.py` — CLI con `--dry-run`.
- `tests/test_notion_operation_trace.py`
- `docs/50-granola-notion-pipeline.md` (§9.9)
- `docs/64-granola-raw-ingest-batch.md`
- `docs/65-granola-vm-raw-intake.md`
