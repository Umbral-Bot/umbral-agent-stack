# P2.2 — Poller/handler Magnific 5 alternativas de imagen (2026-07-23)

> **Estado:** código + tests implementados, **DEFAULT OFF** (fail-closed).
> Cablea el paquete P2.2 del
> [roadmap norte](editorial-roadmap-norte-p1-p3-2026-07-22.md) §3. No abre
> gates humanos, no publica, no toca `Selección imagen` / `Visual asset URL`
> / copy — eso es David / `sync_visual_asset_from_selection.py` / P2.3.
>
> **Bloqueante para producción: `MAGNIFIC_API_KEY` no está configurada en
> ningún entorno** (VPS secrets / `~/.config/openclaw/env`). El código está
> listo, probado (mocks) y puede correr en `dry_run` hoy mismo sin la
> credencial; lo que no puede hacerse sin ella es una generación real ni
> activar el scan (`NOTION_POLLER_ENABLE_MAGNIFIC=true`) en producción — ver
> §Gap de credencial abajo.

## Qué hace

1. `dispatcher/notion_poller.py::_generate_magnific_variants_for_pending_rows`
   escanea (opt-in) la BD **Publicaciones** buscando filas con
   `origen_alternativa` no vacío (promovidas por P2.1 tras `Aprobar`) y
   `Estado imagen` fuera de `{Listo para selección, Seleccionada, Generando,
   Error}`. **`Error` queda deliberadamente excluido del scan automático**
   (ver §Costo y reintentos) — el handler sigue aceptándolo como reintento
   manual explícito (CLI/dry-run), pero el scan nunca lo re-selecciona solo.
2. Por cada candidata (máximo 1 por ciclo — ver §Costo), llama al task
   Worker/core `magnific.generate_variants`
   ([worker/tasks/magnific.py](../../worker/tasks/magnific.py)), que:
   1. Re-lee la página Publicaciones en vivo (fail-closed — nunca confía en
      el snapshot del scan para decidir si generar/escribir).
   2. Si `Estado imagen` ya es `Generando`, `Listo para selección` o
      `Seleccionada`, no-op idempotente (`ok=true, skipped=true`).
   3. Si no, construye el prompt (desde `Visual brief`, o `Título` +
      `Premisa` si está vacío) con el sufijo anti-slop de
      [ADR-006](../adr/ADR-006-capa-visual-editorial.md) y el aspect ratio
      canónico Umbral `classic_4_3` (4:3, ver
      [umbral-bim-magnific-visual-style-v1.md](umbral-bim-magnific-visual-style-v1.md)).
   4. Escribe el estado interino `Estado imagen = Generando` — **sin tocar**
      `imagen_alt_*_url` — antes de gastar créditos Magnific, para probar
      que el write a Notion funciona. Deliberadamente no limpia URLs
      previas: un intento anterior puede haber producido variantes válidas
      (créditos ya gastados) antes de fallar a mitad de camino, y un
      reintento que también falla no debe destruirlas (ver §Costo).
   5. Genera hasta 5 variantes secuenciales vía la API REST de Magnific
      (Mystic, `POST/GET https://api.magnific.com/v1/ai/mystic`, header
      `x-magnific-api-key`) — el fallback headless documentado en
      [magnific-editorial-setup-2026-06-06.md](magnific-editorial-setup-2026-06-06.md),
      distinto del MCP interactivo con OAuth que usa Rick/Cursor.
   6. Si las 5 se generan: escribe `imagen_alt_1_url`…`imagen_alt_5_url`,
      `imagen_cantidad=5`, `imagen_generada_at=hoy`, `Estado imagen = Listo
      para selección` — y limpia cualquier slot sobrante si `count < 5`
      (override manual; el flujo de producción siempre pide 5).
   7. Si alguna falla (o el conteo queda por debajo de lo pedido): escribe
      **sólo** las URLs que sí se generaron *en este intento* (no toca los
      slots que no le correspondieron), `imagen_cantidad=N real`, `Estado
      imagen = Error`, `imagen_error` con el detalle — **nunca** una falsa
      `Listo para selección` con menos de las variantes pedidas, y **nunca**
      destruye URLs válidas de un intento previo (riesgo nombrado en el
      roadmap: "conteo 3 vs 5").

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

- No marca `Selección imagen` ni `Visual asset URL` — eso es David +
  `scripts/editorial/sync_visual_asset_from_selection.py`.
- No abre `aprobado_contenido` ni `autorizar_publicacion`.
- No escribe ni lee copy (Copy Blog/LinkedIn/X) — P2.3.
- No implementa la reacción a `Selección imagen = Regenerar` (limpiar URLs +
  encolar) descrita en
  [notion-publicaciones-v2-visual-gates-schema.md §9](notion-publicaciones-v2-visual-gates-schema.md) —
  ese es un handler distinto, fuera de este paquete. Este paquete sí es
  **elegible** para correr cuando `Estado imagen = Regeneración pedida` ya
  fue puesto por otro proceso.
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
- **Timeout del Worker call = 1200s** (`MAGNIFIC_CALL_TIMEOUT_SEC`, en el
  poller): el piso teórico de sólo-sleep del handler es 5 variantes × 40
  intentos × 3s = 600s, sin contar latencia real de red en ~205 requests
  (5 submits + hasta 200 polls). 1200s da margen; si las constantes de
  `worker/tasks/magnific.py` cambian, revisar este valor junto con ellas.
- **`Error` nunca se reintenta solo**: el scan excluye explícitamente ese
  estado (ver §Qué hace, paso 1). Sin esta exclusión, una fila que falla de
  forma persistente (ej. un prompt que siempre dispara el filtro NSFW de
  Magnific) se reintentaría cada 30 min indefinidamente, gastando créditos
  sin límite. Sacarla de `Error` requiere una acción explícita (humana o de
  otro paquete) — hoy, en la práctica, sólo un reintento manual vía el
  script CLI o `curl` directo al Worker.
- **Ningún reintento destruye resultados previos**: el write interino
  `Generando` no limpia `imagen_alt_*_url`, y un fallo parcial sólo escribe
  los slots que ese intento produjo — nunca borra URLs válidas (créditos ya
  gastados) que un intento anterior haya dejado. Ver los tests
  `test_interim_write_never_clears_existing_urls` en
  `tests/test_magnific.py`.

## Gap de credencial (bloqueante de producción)

`MAGNIFIC_API_KEY` (header `x-magnific-api-key`, API REST de Magnific/Mystic)
**no existe hoy** en `.env.example`, `openclaw/env.template` real, ni se
encontró referencia a un valor cargado en VPS secrets. Estado previo
(`docs/ops/magnific-editorial-setup-2026-06-06.md` §Pendientes): "OAuth
Magnific completado en OpenClaw VPS (o REST fallback)" seguía pendiente.

**Qué falta exactamente para pasar a producción:**

- [E1] Obtener una API key de Magnific/Freepik con el header
  `x-magnific-api-key` (cuenta Magnific de David, plan con créditos
  suficientes — confirmar `account_balance` antes de habilitar el scan).
- [E2] Cargar `MAGNIFIC_API_KEY` en `~/.config/openclaw/env` (VPS) — el mismo
  archivo que ya tiene `NOTION_API_KEY`, `WORKER_TOKEN`, etc.
- [E3] Confirmar que el Worker (`umbral-worker.service`) relee ese env al
  reiniciar (mismo procedimiento que cualquier otra var de `worker/config.py`).
- [E4] Sólo entonces: `NOTION_POLLER_ENABLE_MAGNIFIC=true` + relanzar el
  daemon del poller (ver runbook).

Sin `MAGNIFIC_API_KEY`, el handler responde `ok=false` con el error
`MAGNIFIC_API_KEY not configured...` **antes de escribir nada en Notion**
(fail-closed) — no hay riesgo de corrupción de estado por habilitar el flag
sin la credencial, sólo backoff de 30 min por fila sin progreso.

## Flags / env vars (todas fail-closed por ausencia)

| Var | Proceso | Default | Efecto |
|---|---|---|---|
| `NOTION_POLLER_ENABLE_MAGNIFIC` | dispatcher (poller) | off | Habilita el scan. Sin esto, el poller nunca lee Publicaciones para este scan — el resto del poller no se ve afectado. |
| `NOTION_PUBLICACIONES_DB_ID` | dispatcher (poller) + Worker | vacío | ID clásico de la página/DB "Publicaciones" (ya usado por P2.1). Sin esto, el scan es no-op y el handler responde `ok=false`. |
| `MAGNIFIC_API_KEY` | Worker | vacío | Header `x-magnific-api-key` para la API REST de Magnific. **Sin esto, el handler responde `ok=false` antes de cualquier write** — ver §Gap de credencial. |

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

Respuestas esperadas:
- Fila elegible: `{"ok": true, "dry_run": true, "would_generate": true, "prompt": "...", "aspect_ratio": "classic_4_3", ...}`.
- Fila ya en curso: `{"ok": true, "skipped": true, "reason": "in_progress", ...}`.
- Fila ya lista/seleccionada: `{"ok": true, "skipped": true, "already_generated": true, ...}`.
- Sin `MAGNIFIC_API_KEY` y `dry_run` **no** seteado: `{"ok": false, "error": "MAGNIFIC_API_KEY not configured..."}` (no llama a Notion para escribir nada).

El **scan del poller** no tiene su propio modo dry-run — sólo decide qué
filas escanear y delega en el handler de arriba. Para probar el scan
completo sin gastar créditos, es más seguro iterar el dry-run del handler
página por página (arriba) que habilitar `NOTION_POLLER_ENABLE_MAGNIFIC=true`
— ese flag SÍ dispara generación real (y gasto de créditos) para toda fila
elegible que encuentre.

## Cómo habilitar el scan real (staging/producción, requiere GO + credencial)

1. Completar §Gap de credencial (E1-E3).
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
  elegible, `dry_run` (sin llamadas HTTP), fallo del write interino aborta
  antes de llamar a Magnific, generación completa de 5 variantes (writes
  correctos e interino sin tocar URLs), fallo parcial → `Estado imagen =
  Error` sin falso "Listo" y sin destruir URLs previas
  (`test_interim_write_never_clears_existing_urls`), rechazo de URL
  `app.magnific.com`; más los casos de bajo nivel del cliente Mystic
  (`task_id` faltante, `HTTPStatusError` en submit/poll, agotamiento de
  intentos de poll, `COMPLETED` sin URL).
- `tests/test_notion_poller.py::TestMagnificFlagParsing` /
  `TestMagnificScanBehavior` — scan: flag default-off, filtrado
  `origen_alternativa`/`Estado imagen` (incluyendo que `Error` nunca se
  auto-reintenta y que `Regeneración pedida` sí es scan-elegible), no-op del
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
- Anti-slop / estilo visual: [ADR-006](../adr/ADR-006-capa-visual-editorial.md), [umbral-bim-magnific-visual-style-v1.md](umbral-bim-magnific-visual-style-v1.md)
- Sibling P2.1 (promoción, mismo patrón poller+handler): [editorial-promote-p21-poller-2026-07-22.md](editorial-promote-p21-poller-2026-07-22.md)
- Schema mirror: [notion/schemas/publicaciones.schema.yaml](../../notion/schemas/publicaciones.schema.yaml)
