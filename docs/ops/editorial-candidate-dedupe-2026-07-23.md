# P2.4 — Dedupe de candidato vs backlog (2026-07-23)

> **Estado:** código + tests implementados, **DEFAULT OFF** (fail-closed).
> Cablea el paquete P2.4 del
> [roadmap norte](editorial-roadmap-norte-p1-p3-2026-07-22.md) §3 (fila J de
> la [matriz de brecha](editorial-gap-matrix-norte-2026-07-22.md)). No abre
> gates humanos, no publica, no promueve (eso es P2.1), no genera copy/imagen
> (P2.2/P2.3), no simula a Rick — Rick sigue siendo quien crea filas en
> Shortlist; este paquete sólo evalúa las que ya existen.

## Qué es (y qué NO es)

Dedupe de **candidato** responde: *"¿ya se curó/redactó/publicó algo sobre
este tema o esta pieza fuente antes?"* — una consulta de pre-registro sobre
Notion (`Alternativas / Shortlist` vs `Publicaciones`).

Esto es **distinto** de la idempotencia de **publish** ya existente:

| | Dedupe de candidato (P2.4, este paquete) | Idempotencia de publish (ya existía) |
|---|---|---|
| Pregunta | ¿Ya existe esta *tema/fuente* en el backlog? | ¿Ya publiqué este *contenido renderizado exacto*? |
| Dónde vive | Notion (`Alternativas / Shortlist` ↔ `Publicaciones`) | SQLite `published_history` (`scripts/discovery/lib/dedup.py`, `publication_hash.py`) + `content_hash`/`idempotency_key` en Publicaciones |
| Cuándo corre | Antes de que la alternativa entre a HITL-1 | En el momento de publicar/postear |
| Campo que escribe | `dedupe_status` (+ `publicacion_relacionada`) en Shortlist | `content_hash` / `idempotency_key` en Publicaciones |

No confundir ambos: `worker/tasks/editorial_dedupe.py` **no** toca
`content_hash`, `published_history`, ni ningún flujo de publish.

## Qué hace

1. `dispatcher/notion_poller.py::_dedupe_pending_shortlist_rows` escanea
   (opt-in) la BD **Alternativas / Shortlist** buscando filas no archivadas
   (`archived != true`, mismo check que el scan V2 classify) con
   `dedupe_status` vacío — **sin condicionar por `Resultado revisión`**: el
   dedupe corre antes o en paralelo a HITL-1, no sólo tras `Aprobar` (eso es
   P2.1, un flujo independiente y paralelo, no encadenado).
2. Por cada candidata (máximo 3 por ciclo), llama al task Worker/core
   `editorial.dedupe_candidate_vs_backlog`
   ([worker/tasks/editorial_dedupe.py](../../worker/tasks/editorial_dedupe.py)),
   que:
   1. Re-lee la página Shortlist en vivo (fail-closed — nunca confía en el
      snapshot del scan).
   2. Si `dedupe_status` ya tiene un valor, no-op idempotente
      (`already_evaluated=true`) — el veredicto se calcula **una vez**.
   3. Consulta `Publicaciones` (`notion_client.query_database`) filtrando
      `Estado` en `{Borrador, Publicado}` — el backlog vigente, sin incluir
      `Descartado`/`Idea`/etc.
   4. Compara la candidata contra cada fila del backlog con dos señales
      independientes (basta con que una coincida):
      - **URL de fuente exacta**: `fuente_pieza_url` (Shortlist) ==
        `Fuente primaria` (Publicaciones) — la misma pieza concreta ya se
        curó.
      - **Tema normalizado**: `topic_key` (o, si está vacío, `Título`)
        normalizado (minúsculas, sin acentos/puntuación, espacios
        colapsados) contra `Título` normalizado de cada fila del backlog.
      - Una coincidencia contra una fila `Publicado` gana sobre una contra
        `Borrador` (duplicado más severo).
   5. Escribe `dedupe_status` (`nuevo` / `duplicado_borrador` /
      `duplicado_publicado`) y, si hubo match, `publicacion_relacionada`
      (relation → la fila de Publicaciones encontrada) en la página
      Shortlist.

El poller **nunca escribe a Notion directamente** — sólo decide qué filas
pedirle al Worker que evalúe (ADR-011 #1: Notion writes son monopolio de
Worker/core), igual que P2.1/P2.2.

## Dry-run: divergencia deliberada del patrón P2.1/P2.2

A diferencia de `editorial.promote_shortlist_approval` y
`magnific.generate_variants` (cuyo `dry_run` evita **toda** llamada Notion más
allá del `get_page` inicial), aquí `dry_run=True` **sí** ejecuta la consulta a
Publicaciones (`query_database`, una lectura sin efectos secundarios) y **sólo
omite** el `update_page_properties` final sobre Shortlist. Razón: la consulta
al backlog **es** el cómputo que este task existe para hacer — sin ella, un
"preview" no podría decir `nuevo` vs `duplicado_*`, sería un dry-run vacío. Ver
docstring de `handle_editorial_dedupe_candidate_vs_backlog` en
`worker/tasks/editorial_dedupe.py`.

## Qué NO hace (por diseño — alcance estricto de P2.4)

- No crea ni modifica el schema vivo de Notion — los campos `topic_key`,
  `dedupe_status`, `publicacion_relacionada` ya existen en la BD Shortlist
  (P1, `notion/schemas/alternativas-shortlist.schema.yaml`, `status: live`).
- No bloquea ni condiciona la promoción P2.1: `dedupe_status` es información
  para HITL-1 (David decide con ese dato a la vista), no un gate automático.
  El poller de promoción (`_promote_approved_shortlist_rows`) sigue
  promoviendo por `Resultado revisión == Aprobar`, sin mirar `dedupe_status`.
- No implementa el loop de aprendizaje de `Descartar` (fila D, AUSENTE,
  P2.5 — paquete separado).
- No añade un campo `topic_key`/equivalente a Publicaciones: la comparación
  usa `Título` de Publicaciones normalizado en tiempo de consulta, sin
  persistir nada nuevo ahí.

## Limitación conocida (v1, documentada — no es un bug)

`normalize_topic_key` es deliberadamente simple: casefold + strip de
acentos/puntuación + colapso de espacios. **No** hace stemming ni reconoce
sinónimos ("gobernanza de datos" vs "gobernanza en datos BIM" no matchean si
los títulos difieren de forma no trivial). Esto puede producir falsos
negativos (duplicados no detectados) pero no falsos positivos agresivos
(nunca declara duplicado por coincidencia parcial/difusa). Mejorar la
heurística (embeddings, fuzzy match) queda para una iteración posterior si el
volumen de falsos negativos lo justifica.

La consulta a Publicaciones trae **todo** el backlog Borrador+Publicado sin
paginación explícita en el handler (delega en la paginación automática de
`notion_client.query_database`) — aceptable al volumen actual (decenas de
filas), sin optimización de escala en este paquete.

## Flags / env vars (todas fail-closed por ausencia)

| Var | Proceso | Default | Efecto |
|---|---|---|---|
| `NOTION_POLLER_ENABLE_DEDUPE` | dispatcher (poller) | off | Habilita el scan. Sin esto, el poller nunca lee Shortlist para este scan — el resto del poller no se ve afectado. |
| `NOTION_SHORTLIST_DS_ID` | dispatcher (poller) | vacío | ID/URL del data source Shortlist (ya usado por P2.1). Sin esto, el scan es no-op. |
| `NOTION_PUBLICACIONES_DB_ID` | Worker | vacío | ID clásico de la BD Publicaciones (ya usado por P2.1/P2.2). Sin esto, el handler responde `ok=false` antes de leer/escribir nada. |

## Cómo correr un dry-run

El **handler** soporta `dry_run` por página — consulta el backlog real y
devuelve el veredicto que se escribiría, sin tocar la página Shortlist:

```bash
curl -s -X POST "$WORKER_URL/run" \
  -H "Authorization: Bearer $WORKER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task": "editorial.dedupe_candidate_vs_backlog", "input": {"shortlist_page_id": "<page_id_de_Shortlist>", "dry_run": true}}'
```

Respuestas esperadas:
- Fila nueva (sin match): `{"ok": true, "dry_run": true, "would_write_dedupe_status": "nuevo", "dedupe_status": "nuevo", "matched_publicacion_page_id": null, ...}`.
- Fila ya evaluada: `{"ok": true, "already_evaluated": true, "dedupe_status": "<valor previo>", ...}` (no vuelve a consultar el backlog).
- Duplicado detectado: `{"ok": true, "dedupe_status": "duplicado_borrador"|"duplicado_publicado", "matched_publicacion_page_id": "<id>", ...}`.

El **scan del poller** no tiene su propio modo dry-run — sólo decide qué
filas escanear y delega en el handler de arriba (mismo patrón que P2.2). Para
probar el scan completo sin escribir en Notion, es más seguro iterar el
dry-run del handler página por página (arriba) que habilitar
`NOTION_POLLER_ENABLE_DEDUPE=true`.

## Cómo habilitar el scan real (staging/producción, requiere GO)

1. Confirmar `NOTION_SHORTLIST_DS_ID` y `NOTION_PUBLICACIONES_DB_ID`
   configurados (ya deberían estarlo desde P2.1).
2. Setear `NOTION_POLLER_ENABLE_DEDUPE=true` en el entorno del poller
   (dispatcher).
3. Relanzar el poller — mismo procedimiento que
   [runbooks/runbook-notion-poller.md](../../runbooks/runbook-notion-poller.md)
   para los flags hermanos.
4. Verificar en el log: `Dedupe scan ENABLED` al boot, y por ciclo
   `Dedupe scan: dedupe_enabled=True scanned=N eligible=N evaluated=N
   skipped=N errors=N`.

## Tests

- [tests/test_editorial_dedupe.py](../../tests/test_editorial_dedupe.py) —
  handler: input requerido, sin `NOTION_PUBLICACIONES_DB_ID`, idempotencia
  (`dedupe_status` ya presente no vuelve a consultar/escribir), `dry_run`
  (consulta pero no escribe), veredicto `nuevo` sin match, match por URL exacta
  → `duplicado_borrador` con `publicacion_relacionada`, `Publicado` gana sobre
  `Borrador`, fallo de lectura/consulta/escritura no deja estado a medias; más
  las funciones puras `normalize_topic_key` y `find_backlog_match` probadas
  directamente (acentos, puntuación, prioridad Publicado > Borrador, ningún
  match → `nuevo`).
- `tests/test_notion_poller.py::TestDedupeFlagParsing` /
  `TestDedupeScanBehavior` — scan: flag default-off, evaluación **sin**
  depender de `Resultado revisión`, filas ya evaluadas se saltan, backoff en
  fallo/excepción, límite de batch (3), checkpoint Redis.

## Referencias

- Contrato: [editorial-norte-hitl-contract-2026-07-22.md](editorial-norte-hitl-contract-2026-07-22.md) §5.J, §6
- Roadmap: [editorial-roadmap-norte-p1-p3-2026-07-22.md](editorial-roadmap-norte-p1-p3-2026-07-22.md) fila P2.4
- Matriz de brecha: [editorial-gap-matrix-norte-2026-07-22.md](editorial-gap-matrix-norte-2026-07-22.md) fila J
- Schema Shortlist (campos `topic_key`/`dedupe_status`/`publicacion_relacionada`, ya vivos):
  [notion/schemas/alternativas-shortlist.schema.yaml](../../notion/schemas/alternativas-shortlist.schema.yaml)
- Schema Publicaciones (backlog consultado: `Estado`, `Título`, `Fuente primaria`):
  [notion/schemas/publicaciones.schema.yaml](../../notion/schemas/publicaciones.schema.yaml)
- Idempotencia de publish (distinta, no tocada aquí):
  [scripts/discovery/lib/dedup.py](../../scripts/discovery/lib/dedup.py),
  [scripts/discovery/lib/publication_hash.py](../../scripts/discovery/lib/publication_hash.py)
- Sibling P2.1 (promoción, mismo patrón poller+handler): [editorial-promote-p21-poller-2026-07-22.md](editorial-promote-p21-poller-2026-07-22.md)
- Sibling P2.2 (mismo patrón dry-run-con-lectura): [editorial-magnific-p22-poller-2026-07-23.md](editorial-magnific-p22-poller-2026-07-23.md)
