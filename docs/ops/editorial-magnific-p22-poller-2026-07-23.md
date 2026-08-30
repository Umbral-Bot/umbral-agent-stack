# P2.2 — Poller/handler Magnific 5 alternativas de imagen (2026-07-23)

> **Estado:** código + tests implementados, **DEFAULT OFF** (fail-closed).
> Cablea el paquete P2.2 del
> [roadmap norte](editorial-roadmap-norte-p1-p3-2026-07-22.md) §3. No abre
> gates humanos, no publica, no toca `Visual asset URL` / copy. El único write
> sobre `Selección imagen` consume el comando humano `Regenerar` y lo devuelve
> a `Pendiente`; David sigue siendo quien decide ese gate.
>
> Este documento describe el contrato de código. El estado de credenciales,
> deploy y smoke live se verifica por separado; este paquete no escribe Notion
> live, no despliega VPS y no habilita `NOTION_POLLER_ENABLE_MAGNIFIC`.

## Qué hace

1. `dispatcher/notion_poller.py::_generate_magnific_variants_for_pending_rows`
   escanea (opt-in) la BD **Publicaciones** buscando filas con
   `origen_alternativa` no vacío (promovidas por P2.1 tras `Aprobar`) y
   `Estado imagen` fuera de `{Listo para selección, Seleccionada, Generando,
   Error}`. La excepción explícita es `Selección imagen = Regenerar`: una fila
   en `Listo para selección` o `Error` vuelve a ser candidata y el pedido
   humano también prevalece sobre checkpoints Redis anteriores. Sin ese
   comando, `Error` nunca se auto-reintenta (ver §Costo y reintentos).
2. Por cada candidata (máximo 1 por ciclo — ver §Costo), llama al task
   Worker/core `magnific.generate_variants`
   ([worker/tasks/magnific.py](../../worker/tasks/magnific.py)), que:
   1. Re-lee la página Publicaciones en vivo (fail-closed — nunca confía en
      el snapshot del scan para decidir si generar/escribir).
   2. Si ve `Selección imagen = Regenerar` en una fila lista o con error,
      consume el comando con un write dedicado: `Estado imagen = Regeneración
      pedida` + `Selección imagen = Pendiente`. No toca URLs en esa transición.
   3. Fuera de ese caso, si `Estado imagen` ya es `Generando`, `Listo para
      selección` o `Seleccionada`, hace no-op idempotente
      (`ok=true, skipped=true`).
   4. Parsea `Visual brief` como YAML. En legacy/v1, si existe `scene`, el
      prompt base es su valor más `avoid`; nunca envía las claves `style`,
      `model`, `trace_id`, `publication_id`, `style_ref`, `vignette`,
      `aspect_ratio` o `resolution` como texto. Si no hay `scene` (incluido
      YAML legacy inválido), usa `Título` + `Premisa`. Un brief que declara
      v2 valida el contrato y construye cinco prompts controlados; si su YAML
      es inválido, falla cerrado antes de generar. Agrega el sufijo editorial isométrico de
      [ADR-006](../adr/ADR-006-capa-visual-editorial.md), limitado junto al
      prompt a 3.000 caracteres.
   5. Escribe el estado interino `Estado imagen = Generando` — **sin tocar**
      `imagen_alt_*_url` — antes de gastar créditos Magnific, para probar
      que el write a Notion funciona. Deliberadamente no limpia URLs
      previas: un intento anterior puede haber producido variantes válidas
      (créditos ya gastados) antes de fallar a mitad de camino, y un
      reintento que también falla no debe destruirlas (ver §Costo).
   6. Genera hasta 5 variantes secuenciales vía la API REST de Magnific. El
      camino legacy/v1 conserva como default **Nano Banana Pro Flash / Nano
      Banana 2**:
      `POST /v1/ai/text-to-image/nano-banana-pro-flash` y poll
      `GET /v1/ai/text-to-image/nano-banana-pro-flash/{task-id}`, header
      `x-magnific-api-key`, `aspect_ratio=4:3`, `resolution=2K` y
      `use_google_search_tool=false`. Un Visual brief v2 explícito usa por
      default **Nano Banana Pro**, también con
      `use_google_search_tool=false`; Flash sigue disponible mediante
      `engine: flash`. Mystic/realism sólo se usa mediante override explícito
      y no recibe ese campo. El JSON oficial usa
      `data.task_id/status/generated`. El fallback headless está
      documentado en
      [magnific-editorial-setup-2026-06-06.md](magnific-editorial-setup-2026-06-06.md),
      distinto del MCP interactivo con OAuth que usa Rick/Cursor.
      En Mystic, los ratios canónicos se traducen a sus enums oficiales y
      tanto ratio como resolución (`1k|2k|4k`) se validan fail-closed.
   7. Si las 5 se generan: escribe `imagen_alt_1_url`…`imagen_alt_5_url`,
      `imagen_cantidad=5`, `imagen_generada_at=hoy`, `Estado imagen = Listo
      para selección`. Nunca escribe `url: null`; un override manual con
      `count < 5` tampoco borra slots previos.
   8. Si alguna falla (o el conteo queda por debajo de lo pedido): preserva
      atómicamente todo el set anterior en Notion y escribe únicamente
      `Estado imagen = Error` + `imagen_error`. La respuesta del Worker informa
      las URLs parciales al caller, pero no mezcla alternativas nuevas/viejas,
      no falsea `imagen_cantidad`/`imagen_generada_at` y **nunca** declara una
      falsa `Listo para selección` (riesgo "conteo 3 vs 5").

El poller **nunca escribe a Notion directamente** — sólo decide qué filas
pedirle al Worker que (re-)evalúe (ADR-011 #1: Notion writes son monopolio de
Worker/core).

También hay un script CLI delgado para invocación manual:
[scripts/editorial/magnific_generate_variants.py](../../scripts/editorial/magnific_generate_variants.py)
— llama al Worker por HTTP (mismo patrón que `scripts/run_worker_task.py`),
**no** toca Notion ni Magnific directo (a diferencia de
`sync_visual_asset_from_selection.py` / `apply_publication_copy.py`,
scripts pre-existentes que sí escriben Notion vía `NOTION_API_KEY` crudo —
deuda documentada, no repetida aquí).

## Qué NO hace (por diseño — alcance estricto de P2.2)

- No elige `Alt N`, no marca el gate humano por David y no toca `Visual asset
  URL`. Sólo consume `Regenerar` → `Pendiente`; la copia de una alternativa
  elegida sigue en `scripts/editorial/sync_visual_asset_from_selection.py`.
- No abre `aprobado_contenido` ni `autorizar_publicacion`.
- No escribe ni lee copy (Copy Blog/LinkedIn/X) — P2.3.
- La reacción a `Selección imagen = Regenerar` **sí está dentro del contrato**:
  el poller la encola aun desde `Listo para selección`/`Error`, y el Worker
  escribe `Regeneración pedida` + `Pendiente` antes de generar. Conserva las
  URLs existentes hasta un éxito completo 5/5; no ejecuta el reset destructivo
  de versiones antiguas del contrato.
- No dispara con el trigger antiguo (`aprobado_contenido` false→true) del
  doc de 2026-06-06 §9 — el contrato vigente
  ([§5.G](editorial-norte-hitl-contract-2026-07-22.md)) dispara "tras
  Aprobar" en Shortlist, es decir, tras la promoción P2.1
  (`origen_alternativa` presente).

## Costo y reintentos

- **Batch = 1 fila por ciclo** (`MAGNIFIC_BATCH_LIMIT`): cada fila cuesta
  hasta 5 llamadas Magnific secuenciales (minutos, no segundos); un batch
  mayor arriesgaría bloquear el resto del poller (Control Room, review,
  smart replies) detrás de una cola larga de generación.
- **Timeout del Worker call = 2400s** (`MAGNIFIC_CALL_TIMEOUT_SEC`, en el
  poller): v2/Pro tiene un techo conservador de 120 intentos × 3s por
  variante, cuyo piso de sólo-sleep es 5 × 120 × 3s = 1800s. No es una
  medición de latencia Pro: deja margen para ~605 requests (5 submits + hasta
  600 polls), descargas y Drive. Legacy/v1 Flash y Mystic conservan 40 × 3s
  por variante (600s de sleep para cinco). Si las constantes de
  `worker/tasks/magnific.py` cambian, revisar este valor junto con ellas.
- **HTTP 503 se reintenta con backoff exponencial acotado** (dos reintentos,
  1s/2s) tanto en submit como en poll. Otros estados HTTP fallan cerrados y
  sus diagnósticos se redactan antes de persistir o loguear.
- **`Error` nunca se reintenta solo**: el scan excluye explícitamente ese
  estado. Sin esta exclusión, una fila que falla de forma persistente se
  reintentaría cada 30 min indefinidamente. La excepción es una acción humana
  inequívoca: `Selección imagen = Regenerar`. Ese comando salta checkpoints
  viejos, pero el poller crea un marcador de intento propio por 30 min antes
  de invocar al Worker. Si el Worker no llega a consumir el comando, ese
  marcador evita un retry storm; se elimina al recibir éxito/no-op.
- **Ningún reintento destruye resultados previos**: el write interino
  `Regeneración pedida`/`Pendiente` y el write `Generando` no limpian
  `imagen_alt_*_url`; un fallo parcial no escribe alts, conteo ni fecha, y ni
  siquiera un éxito manual con `count < 5` emite `url: null`. Las cinco URLs
  de producción se reemplazan juntas únicamente con un éxito 5/5. Ver los tests
  `test_interim_write_never_clears_existing_urls` en
  `tests/test_magnific.py`.
- **Un fallo del write final no deja `Generando` permanente**: el Worker
  intenta recuperar la fila a `Estado imagen = Error` con un write separado
  que sólo toca estado/diagnóstico y nunca limpia alternativas anteriores.

## Credencial y activación live

`MAGNIFIC_API_KEY` (header `x-magnific-api-key`) es requisito del Worker para
una generación real y debe vivir sólo en el entorno seguro del runtime. Este
contrato no presupone ni expone su valor, y este paquete no audita su presencia
actual ni cambia configuración live.

Antes de activar producción hay que verificar, en un paquete de deploy/live
separado: credencial disponible para el Worker, balance suficiente, Worker con
el nuevo código, `NOTION_PUBLICACIONES_DB_ID` correcto y GO explícito para
`NOTION_POLLER_ENABLE_MAGNIFIC=true`. Sin la key, el handler responde
`ok=false` **antes de cualquier write a Notion** (fail-closed).

## Flags / env vars (todas fail-closed por ausencia)

| Var | Proceso | Default | Efecto |
|---|---|---|---|
| `NOTION_POLLER_ENABLE_MAGNIFIC` | dispatcher (poller) | off | Habilita el scan. Sin esto, el poller nunca lee Publicaciones para este scan — el resto del poller no se ve afectado. |
| `NOTION_PUBLICACIONES_DB_ID` | dispatcher (poller) + Worker | vacío | ID clásico de la página/DB "Publicaciones" (ya usado por P2.1). Sin esto, el scan es no-op y el handler responde `ok=false`. |
| `MAGNIFIC_API_KEY` | Worker | sin default | Header `x-magnific-api-key` para la API REST de Magnific. **Sin esto, el handler responde `ok=false` antes de cualquier write** — ver §Credencial y activación live. |

## Cómo correr un dry-run

El **handler** soporta `dry_run` por página — verifica la elegibilidad y
devuelve el prompt/params que se usarían, sin llamar a Magnific ni a Notion
para escribir nada (no requiere `MAGNIFIC_API_KEY`):

```bash
curl -s -X POST "$WORKER_URL/run" \
  -H "Authorization: Bearer $WORKER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task": "magnific.generate_variants", "input": {"publicacion_page_id": "<page_id_de_Publicaciones>", "dry_run": true}}'
```

O vía el script CLI:

```bash
export WORKER_URL=http://127.0.0.1:8088 WORKER_TOKEN=xxx
python scripts/editorial/magnific_generate_variants.py --page-id <page_id> --dry-run
```

La CLI usa 30s para el dry-run y el mismo timeout de 2400s del poller para la
generación real. Redacta las URLs generadas y el diagnóstico upstream de su
salida; las URLs operativas quedan en Notion.

Respuestas esperadas:
- Fila legacy/v1 elegible: `{"ok": true, "dry_run": true, "would_generate": true, "model": "nano-banana-pro-flash", "endpoint": "https://api.magnific.com/v1/ai/text-to-image/nano-banana-pro-flash", "aspect_ratio": "4:3", "resolution": "2K", ...}`.
- Fila Visual brief v2 elegible: devuelve `model=nano-banana-pro`, cinco
  `prompts` controlados y `use_google_search_tool=false`.
- Fila ya en curso: `{"ok": true, "skipped": true, "reason": "in_progress", ...}`.
- Fila ya lista/seleccionada: `{"ok": true, "skipped": true, "already_generated": true, ...}`.
- Fila lista/error con `Selección imagen = Regenerar`: elegible; en `dry_run`
  informa `"regeneration_requested": true` sin escribir.
- Sin `MAGNIFIC_API_KEY` y `dry_run` **no** seteado: `{"ok": false, "error": "MAGNIFIC_API_KEY not configured..."}` (no llama a Notion para escribir nada).

El **scan del poller** no tiene su propio modo dry-run — sólo decide qué
filas escanear y delega en el handler de arriba. Para probar el scan
completo sin gastar créditos, es más seguro iterar el dry-run del handler
página por página (arriba) que habilitar `NOTION_POLLER_ENABLE_MAGNIFIC=true`
— ese flag SÍ dispara generación real (y gasto de créditos) para toda fila
elegible que encuentre.

## Cómo habilitar el scan real (staging/producción, requiere GO + credencial)

1. Completar la verificación separada de §Credencial y activación live.
2. Confirmar `NOTION_PUBLICACIONES_DB_ID` configurado (ya debería estarlo
   desde P2.1).
3. Setear `NOTION_POLLER_ENABLE_MAGNIFIC=true` en el entorno del poller
   (dispatcher).
4. Relanzar el poller — mismo procedimiento que
   [runbooks/runbook-notion-poller.md](../../runbooks/runbook-notion-poller.md)
   para los flags hermanos: matar el daemon
   (`pkill -TERM -f "notion-poller-daemon[.]py"`), el watchdog lo relanza con
   el env nuevo.
5. Verificar en el log: `Magnific scan ENABLED` al boot, y por ciclo
   `Magnific scan: magnific_enabled=True scanned=N eligible=N generated=N
   skipped=N errors=N`.
6. El smoke E2E real (P3.3 del roadmap: copy largo + 5 imágenes tras
   Aprobar) queda para una fase posterior con GO explícito de David — este
   PR sólo cablea P2.2.

## Tests

- [tests/test_magnific.py](../../tests/test_magnific.py) — handler: input
  requerido, `count` inválido, sin `MAGNIFIC_API_KEY` (bloquea antes de
  cualquier write), idempotencia (`Generando` en curso, ya `Listo para
  selección`/`Seleccionada`), estado no elegible, `Regeneración pedida` sí
  elegible, default v1 Flash/default v2 Pro y aliases Flash-Pro-Mystic,
  parser YAML `scene` + `avoid`
  sin metadatos en el prompt, límite de 3.000 caracteres, `dry_run` (sin
  llamadas HTTP), payload/endpoint Flash y Pro exactos, override Mystic
  explícito,
  traducción/validación de enums Mystic,
  consumo ordenado de `Regenerar`, fallo del write interino antes de créditos,
  generación completa de 5 variantes (writes correctos e interino sin tocar
  URLs), fallo parcial → `Estado imagen = Error` sin falso "Listo" y sin destruir URLs previas
  (`test_interim_write_never_clears_existing_urls`), rechazo de URL
  `app.magnific.com`; más los casos de bajo nivel del cliente REST/Mystic
  (`task_id` faltante, `HTTPStatusError` en submit/poll, agotamiento de
  intentos de poll, `COMPLETED` sin URL).
- `tests/test_notion_poller.py::TestMagnificFlagParsing` /
  `TestMagnificScanBehavior` — scan: flag default-off, filtrado
  `origen_alternativa`/`Estado imagen` (incluyendo que `Error` nunca se
  auto-reintenta sin comando, que `Regenerar` desde listo/error sí encola aun
  con checkpoint Redis, y que `Regeneración pedida` es scan-elegible), no-op del
  handler no cuenta como generación, backoff en fallo/excepción, límite de
  batch (1), checkpoint Redis.
- `tests/test_worker_client.py::test_run_timeout_override_applies_only_to_that_call` —
  el override de `timeout` en `WorkerClient.run()` (necesario porque este
  scan puede tardar minutos) no afecta otras llamadas del mismo cliente.

## Referencias

- Contrato: [editorial-norte-hitl-contract-2026-07-22.md](editorial-norte-hitl-contract-2026-07-22.md) §5.G, §6
- Roadmap: [editorial-roadmap-norte-p1-p3-2026-07-22.md](editorial-roadmap-norte-p1-p3-2026-07-22.md) fila P2.2
- Estado de máquina / nombres de propiedad: [notion-publicaciones-v2-visual-gates-schema.md](notion-publicaciones-v2-visual-gates-schema.md)
- Setup Magnific (MCP + REST fallback, OAuth pendiente): [magnific-editorial-setup-2026-06-06.md](magnific-editorial-setup-2026-06-06.md)
- API oficial Nano Banana Pro Flash: [overview](https://docs.magnific.com/api-reference/text-to-image/nano-banana-pro-flash/overview), [POST Create Image](https://docs.magnific.com/api-reference/text-to-image/nano-banana-pro-flash/generate), [GET Task by ID](https://docs.magnific.com/api-reference/text-to-image/nano-banana-pro-flash/task-by-id)
- Anti-slop / estilo visual: [ADR-006](../adr/ADR-006-capa-visual-editorial.md), [umbral-bim-magnific-visual-style-v1.md](umbral-bim-magnific-visual-style-v1.md)
- Sibling P2.1 (promoción, mismo patrón poller+handler): [editorial-promote-p21-poller-2026-07-22.md](editorial-promote-p21-poller-2026-07-22.md)
- Schema mirror: [notion/schemas/publicaciones.schema.yaml](../../notion/schemas/publicaciones.schema.yaml)
