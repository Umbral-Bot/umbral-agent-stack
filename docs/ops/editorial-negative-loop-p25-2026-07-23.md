# P2.5 — Loop de aprendizaje de Descartar (2026-07-23)

> **Estado:** código + tests implementados, **DEFAULT OFF** (fail-closed).
> Cablea el paquete P2.5 del
> [roadmap norte](editorial-roadmap-norte-p1-p3-2026-07-22.md) §3, cerrando la
> **fila D** de la [matriz de brecha](editorial-gap-matrix-norte-2026-07-22.md)
> (previamente **AUSENTE**). No abre gates humanos, no publica, no promueve
> (P2.1), no genera copy/imagen (P2.2/P2.3), no dedupea (P2.4), no simula a
> Rick — Rick sigue siendo quien marca `Resultado revisión = Descartar` y
> escribe `motivo_descarte`; este paquete sólo valida y persiste la captura, y
> deja el negativo listo para consultarse.

## Qué es

Cuando David (o Rick, vía HITL-1) marca una alternativa `Descartar`, el
contrato (§4) exige registrar un **ejemplo negativo** estructurado que
realimente QA/generación para no repetir el mismo fallo. Antes de este
paquete, `ejemplo_negativo`/`error_kind`/`motivo_descarte` existían en el
schema (P1) pero **nada los escribía ni los consultaba** — el riesgo nombrado
en el roadmap: *"Loop que no cierra (se captura pero no se consume)"*.

Este paquete cierra **ambos** lados del loop:

1. **Captura** (Notion, Worker/core): valida y persiste el negativo en la
   fila Shortlist misma.
2. **Consumo** (archivo local, sin Notion nuevo): materializa los negativos
   capturados en un JSONL versionable en el repo, con una función de consulta
   (`find_similar_negatives`) que demuestra el caso real — "¿este candidato
   nuevo repite un fallo ya conocido?" — lista para que rick-qa/generación la
   use (activación de ese consumo en el prompt de Rick es fuera de alcance
   aquí, ver §Qué NO hace).

## Qué hace

### 1. Captura (Notion)

1. `dispatcher/notion_poller.py::_capture_negative_shortlist_rows` escanea
   (opt-in) la BD **Alternativas / Shortlist** buscando filas no archivadas
   con `Resultado revisión == "Descartar"` **y** `ejemplo_negativo` falso.
2. Por cada candidata (máximo 3 por ciclo), llama al task Worker/core
   `editorial.capture_negative_example`
   ([worker/tasks/editorial_negative_capture.py](../../worker/tasks/editorial_negative_capture.py)),
   que:
   1. Re-lee la página Shortlist en vivo (fail-closed).
   2. Si `Resultado revisión != Descartar`, bloquea sin escribir
      (`error: "not_discarded"`) — nunca confía en el snapshot del scan.
   3. Si `ejemplo_negativo` ya es `true`, no-op idempotente
      (`already_captured=true`) — el marcador de "ya capturado" **es**
      `ejemplo_negativo` mismo (no se inventa un campo adicional), igual que
      `promovido_a` (P2.1) y `dedupe_status` (P2.4).
   4. **`motivo_descarte` es obligatorio en código** (el schema sólo lo dice
      en la descripción, `required: false` a nivel Notion): si está vacío,
      bloquea sin escribir (`error: "motivo_descarte_missing"`) — un
      Descartar sin motivo no produce un negativo útil.
   5. **`error_kind` es opcional**: su propia descripción de schema dice
      "poblar empíricamente ... no inventar un enum cerrado aquí" — este
      handler nunca bloquea por `error_kind` vacío ni inventa un valor.
   6. Escribe `ejemplo_negativo = true` (única escritura — `motivo_descarte`
      y `error_kind` ya los puso David/Rick vía Notion; este handler los lee,
      valida y confirma, no los fabrica).

El poller **nunca escribe a Notion directamente** — sólo decide qué filas
pedirle al Worker que evalúe (ADR-011 #1), igual que P2.1/P2.4.

### 2. Consumo (archivo local)

[scripts/editorial/sync_negative_examples.py](../../scripts/editorial/sync_negative_examples.py)
— CLI de sólo-lectura hacia Notion (llama al task genérico
`notion.read_database` vía HTTP al Worker, mismo patrón que
`magnific_generate_variants.py`; **no** toca la API de Notion directo, **no**
escribe nada en Notion):

1. Lee la BD Shortlist, filtra filas con `ejemplo_negativo == true`.
2. Materializa cada una como un registro JSON (`alternativa_id`, `titulo`,
   `topic_key` normalizado, `motivo_descarte`, `error_kind`,
   `fuente_pieza_url`) y lo **añade** (idempotente, deduplicado por
   `alternativa_id`/`page_id`) a un archivo JSONL local:
   `evals/editorial/negative-examples-log.jsonl` — el mismo directorio donde
   ya viven otros archivos de referencia consumidos en generación
   (`benchmark-umbral-voice-v1.yaml`, `channel-criteria-v1.yaml`).
3. `find_similar_negatives(topic_key, error_kind, examples)` — la función de
   consulta real: compara un candidato nuevo contra el store por **tema
   normalizado** (misma heurística que `worker/tasks/editorial_dedupe.py`'s
   `normalize_topic_key`, duplicada localmente porque `scripts/` y `worker/`
   están silados en este repo — ninguno importa al otro) o por **solape de
   `error_kind`**. Cualquiera de las dos señales basta.

Este JSONL **no es una DB Notion nueva** (cumple la prohibición explícita) —
es un artefacto de archivo, versionable, que cualquier proceso de
generación/QA puede leer directamente sin credenciales de Notion.

## Qué NO hace (por diseño — alcance estricto de P2.5)

- No activa el consumo dentro del prompt/ROLE de `rick-qa` en runtime — eso
  requeriría editar
  [openclaw/workspace-agent-overrides/rick-qa/ROLE.md](../../openclaw/workspace-agent-overrides/rick-qa/ROLE.md)
  y activar con GO explícito de David, mismo patrón que P2.8
  (`rick-editorial`) en el roadmap. Este paquete deja la función de consulta
  **lista y probada**, no la cablea en el ROLE.
- No fabrica `motivo_descarte` ni `error_kind` — sólo lee lo que David/Rick ya
  escribieron en Notion vía HITL-1.
- No define un enum cerrado de `error_kind` (el schema lo prohíbe
  explícitamente). §Convención sugerida abajo da ejemplos, no una lista
  cerrada.
- No toca `Resultado revisión`, gates, promoción (P2.1), dedupe (P2.4), copy
  (P2.3) ni imágenes (P2.2).
- No reactiva ni modifica el schema Notion vivo.

## Convención sugerida para `error_kind` (no un enum cerrado)

El campo ya existe con `options: []` — cualquiera puede escribir un valor
nuevo desde la UI de Notion. Como punto de partida (no obligatorio, no
codificado en ningún validador):

`fuente_home_no_pieza` · `arco_narrativo_ausente` · `estructura_discurso_ausente` ·
`tono_generico` · `dato_no_verificado` · `tesis_debil`

Poblar empíricamente conforme se capturen negativos reales (según indica la
propia descripción del campo en el schema).

## Flags / env vars (todas fail-closed por ausencia)

| Var | Proceso | Default | Efecto |
|---|---|---|---|
| `NOTION_POLLER_ENABLE_NEGATIVE_CAPTURE` | dispatcher (poller) | off | Habilita el scan. Sin esto, el poller nunca lee Shortlist para este scan. |
| `NOTION_SHORTLIST_DS_ID` | dispatcher (poller) + `sync_negative_examples.py` | vacío | ID/URL del data source Shortlist (ya usado por P2.1/P2.4). |
| `WORKER_URL` / `WORKER_TOKEN` | `sync_negative_examples.py` | — | Igual que cualquier script CLI de este directorio (o `~/.config/openclaw/env`). |

## Cómo correr un dry-run

**Captura** (handler, por página):

```bash
curl -s -X POST "$WORKER_URL/run" \
  -H "Authorization: Bearer $WORKER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task": "editorial.capture_negative_example", "input": {"shortlist_page_id": "<page_id_de_Shortlist>", "dry_run": true}}'
```

Respuestas esperadas:
- No es Descartar: `{"ok": false, "error": "not_discarded", "resultado_revision": "..."}`.
- Ya capturado: `{"ok": true, "already_captured": true, "motivo_descarte": "...", "error_kind": [...]}`.
- Sin `motivo_descarte`: `{"ok": false, "error": "motivo_descarte_missing"}`.
- Candidata válida: `{"ok": true, "dry_run": true, "would_capture": true, "motivo_descarte": "...", "error_kind": [...]}`.

**Sync al archivo local** (sin escribir, sólo preview):

```bash
export WORKER_URL=http://127.0.0.1:8088 WORKER_TOKEN=xxx NOTION_SHORTLIST_DS_ID=<ds_id>
python scripts/editorial/sync_negative_examples.py --dry-run
```

**Consultar el store local** (cómo un negativo bloquea/repite un patrón — sin
llamar a Notion en absoluto):

```bash
python scripts/editorial/sync_negative_examples.py \
  --check-topic-key "Gobernanza en BIM sin fuente" \
  --check-error-kind fuente_home_no_pieza
```

Si el store ya tiene un negativo con el mismo tema normalizado o el mismo
`error_kind`, imprime `SIMILAR_NEGATIVES_FOUND count=N` + el/los registro(s)
JSON — esta es la señal que un futuro cableado en `rick-qa` (P2.8-style,
fuera de alcance aquí) usaría para rechazar o replantear un candidato antes
de generarlo, cerrando el loop "no se repite el fallo" del contrato §4.

El **scan del poller** no tiene su propio modo dry-run — sólo decide qué
filas escanear y delega en el handler de arriba (mismo patrón que P2.2/P2.4).

## Cómo habilitar el scan real (staging/producción, requiere GO)

1. Confirmar `NOTION_SHORTLIST_DS_ID` configurado (ya debería estarlo).
2. Setear `NOTION_POLLER_ENABLE_NEGATIVE_CAPTURE=true` en el entorno del
   poller (dispatcher).
3. Relanzar el poller — mismo procedimiento que
   [runbooks/runbook-notion-poller.md](../../runbooks/runbook-notion-poller.md).
4. Verificar en el log: `Negative-capture scan ENABLED` al boot, y por ciclo
   `Negative-capture scan: negative_capture_enabled=True scanned=N
   eligible=N captured=N skipped=N errors=N`.
5. Correr `python scripts/editorial/sync_negative_examples.py` periódicamente
   (o vía cron) para mantener `evals/editorial/negative-examples-log.jsonl`
   al día.

## Tests

- [tests/test_editorial_negative_capture.py](../../tests/test_editorial_negative_capture.py) —
  handler: input requerido, bloqueo sin escrituras si no es `Descartar`,
  idempotencia (`ejemplo_negativo` ya true no vuelve a escribir),
  `motivo_descarte` vacío/sólo-espacios bloquea sin escribir, `error_kind`
  vacío **no** bloquea, `dry_run` (sin escrituras), captura exitosa
  (`ejemplo_negativo → true`), fallo de lectura/escritura no deja estado a
  medias.
- `tests/test_notion_poller.py::TestNegativeCaptureFlagParsing` /
  `TestNegativeCaptureScanBehavior` — scan: flag default-off, filas no
  Descartar/ya capturadas/archivadas se saltan, backoff en fallo/excepción,
  límite de batch (3), checkpoint Redis.
- [tests/test_sync_negative_examples.py](../../tests/test_sync_negative_examples.py) —
  extracción de registros desde items de `notion.read_database`, persistencia
  JSONL idempotente (no duplica en re-sync), `find_similar_negatives` (match
  por tema normalizado, por `error_kind`, ningún match, guard contra falso
  match vacío-vacío), CLI (`--dry-run` no escribe, `--check-topic-key` no
  llama a Notion, sync real escribe el archivo).

## Referencias

- Contrato: [editorial-norte-hitl-contract-2026-07-22.md](editorial-norte-hitl-contract-2026-07-22.md) §4
- Roadmap: [editorial-roadmap-norte-p1-p3-2026-07-22.md](editorial-roadmap-norte-p1-p3-2026-07-22.md) fila P2.5
- Matriz de brecha: [editorial-gap-matrix-norte-2026-07-22.md](editorial-gap-matrix-norte-2026-07-22.md) fila D
- Schema Shortlist (campos `motivo_descarte`/`ejemplo_negativo`/`error_kind`, ya vivos):
  [notion/schemas/alternativas-shortlist.schema.yaml](../../notion/schemas/alternativas-shortlist.schema.yaml)
- `rick-qa` (consumidor futuro, no cableado aquí):
  [openclaw/workspace-agent-overrides/rick-qa/ROLE.md](../../openclaw/workspace-agent-overrides/rick-qa/ROLE.md)
- Sibling P2.1 (mismo patrón poller+handler): [editorial-promote-p21-poller-2026-07-22.md](editorial-promote-p21-poller-2026-07-22.md)
- Sibling P2.4 (mismo patrón + `normalize_topic_key`): [editorial-candidate-dedupe-2026-07-23.md](editorial-candidate-dedupe-2026-07-23.md)
