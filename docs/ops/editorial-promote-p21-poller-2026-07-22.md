# P2.1 — Poller/handler Aprobar → promueve a Publicaciones (2026-07-22)

> **Estado:** implementado, **DEFAULT OFF** (fail-closed). Cablea el paquete
> P2.1 del [roadmap norte](editorial-roadmap-norte-p1-p3-2026-07-22.md) §3.
> No abre gates humanos, no publica, no genera copy largo/imágenes, no marca
> `listo_rrss` — eso es P2.2/P2.3/P2.6/P2.7, fuera de este paquete.

## Qué hace

1. `dispatcher/notion_poller.py::_promote_approved_shortlist_rows` escanea
   (opt-in) la BD **Alternativas / Shortlist** buscando filas con
   `Resultado revisión = Aprobar` y `promovido_a` vacío.
2. Por cada candidata, llama al task Worker/core
   `editorial.promote_shortlist_approval`
   ([worker/tasks/editorial_promote.py](../../worker/tasks/editorial_promote.py)),
   que:
   1. Re-lee la página Shortlist en vivo (fail-closed — nunca confía en el
      snapshot del scan para la decisión de escribir).
   2. Verifica `Resultado revisión == "Aprobar"`; si no, no escribe nada
      (`ok=false, error="not_approved"`).
   3. Si `promovido_a` ya tiene valor, no-op idempotente
      (`ok=true, already_promoted=true`).
   4. Si no, busca en Publicaciones una fila existente con
      `origen_alternativa` apuntando a esta Shortlist (red de seguridad ante
      un reintento parcial: create tuvo éxito pero el write-back de
      `promovido_a` falló); si no existe, crea **1** fila en Publicaciones en
      `Borrador` (`aprobado_contenido=false`, `autorizar_publicacion=false`,
      `Creado por sistema=true`) mapeando `Título`/`canal_sugerido` →
      `Canal`+`Tipo de contenido`/`premisa` → `Premisa`/`fuente_pieza_url` →
      `Fuente primaria`/`arco_narrativo`+`estructura_discurso` → `Notas`.
   5. Escribe `promovido_a` (Shortlist → fila nueva o existente) y
      `origen_alternativa` (fila → Shortlist, ya seteado en la creación).

El poller **nunca escribe a Notion directamente** — sólo decide qué páginas
pedirle al Worker que (re-)evalúe (ADR-011 #1: Notion writes son monopolio de
Worker/core).

## Qué NO hace (por diseño — alcance estricto de P2.1)

- No abre `aprobado_contenido` ni `autorizar_publicacion` — la fila nueva
  siempre nace con ambos gates en `false`.
- No genera copy largo ni imágenes (P2.2/P2.3).
- No publica ni marca `listo_rrss` (P2.6/P2.7).
- No dedupe contra el backlog de Publicaciones por tema (P2.4, distinto de la
  red de seguridad anti-duplicado de este paquete, que sólo mira
  `origen_alternativa` de esta misma alternativa).
- No implementa el loop de aprendizaje de `Descartar` (P2.5).

## Flags / env vars (todas fail-closed por ausencia)

| Var | Proceso | Default | Efecto |
|---|---|---|---|
| `NOTION_POLLER_ENABLE_PROMOTE` | dispatcher (poller) | off | Habilita el scan. Sin esto, el poller nunca lee la BD Shortlist para promoción — el resto del poller (Control Room, review targets, smart replies, V2 classify) no se ve afectado. |
| `NOTION_SHORTLIST_DS_ID` | dispatcher (poller) | vacío | ID **clásico** de página/DB de "Alternativas / Shortlist" (NO el `collection://` data-source id — ver nota de compatibilidad abajo). Sin esto, el scan es no-op aunque el flag esté en `true`. |
| `NOTION_PUBLICACIONES_DB_ID` | Worker | vacío | ID clásico de página/DB de "Publicaciones". Sin esto, el handler responde `ok=false`. |

**Nota de compatibilidad de API:** `worker/notion_client.py` usa la Notion API
`2022-06-28` (endpoint clásico `/v1/databases/{id}`), distinta del
`collection://<data_source_id>` documentado en
[alternativas-shortlist.schema.yaml](../../notion/schemas/alternativas-shortlist.schema.yaml)
(modelo multi-data-source más nuevo). Configurar `NOTION_SHORTLIST_DS_ID` y
`NOTION_PUBLICACIONES_DB_ID` con el ID clásico de la página/DB (el que aparece
en la URL `https://app.notion.com/p/<id>`), no con el `collection://...` id.

## Cómo correr un dry-run

El **handler** soporta `dry_run` por página — verifica el gate y devuelve las
propiedades que se escribirían, sin llamar a Notion para crear/actualizar
nada:

```bash
curl -s -X POST "$WORKER_URL/run" \
  -H "Authorization: Bearer $WORKER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task": "editorial.promote_shortlist_approval", "input": {"shortlist_page_id": "<page_id_de_la_fila_Aprobar>", "dry_run": true}}'
```

Respuestas esperadas:
- Fila en `Aprobar` y sin promover: `{"ok": true, "dry_run": true, "would_promote": true, "properties_preview": {...}, ...}`.
- Fila no aprobada: `{"ok": false, "error": "not_approved", "resultado_revision": "<valor actual>", ...}` (no llama a Notion para crear/actualizar).
- Fila ya promovida: `{"ok": true, "created": false, "already_promoted": true, "publicacion_page_id": "..."}` (corta antes del preview; el `dry_run` no cambia este caso, ya es un no-op).

El **scan del poller** (`_promote_approved_shortlist_rows`) no tiene su propio
modo dry-run — sólo decide qué filas escanear y delega en el handler de
arriba. Para probar el scan completo sin escribir nada en un ambiente real, es
más seguro iterar el dry-run del handler página por página (arriba) que
habilitar `NOTION_POLLER_ENABLE_PROMOTE=true` — ese flag SÍ dispara escrituras
reales para toda fila `Aprobar` que encuentre.

## Cómo habilitar el scan real (staging/producción, requiere GO)

1. Confirmar `NOTION_SHORTLIST_DS_ID` y `NOTION_PUBLICACIONES_DB_ID`
   configurados (ver `.env.example` / `openclaw/env.template`).
2. Setear `NOTION_POLLER_ENABLE_PROMOTE=true` en el entorno del poller
   (dispatcher).
3. Relanzar el poller — mismo procedimiento que
   [runbooks/runbook-notion-poller.md](../../runbooks/runbook-notion-poller.md)
   para el flag hermano `NOTION_POLLER_ENABLE_V2_CLASSIFY`: matar el daemon
   (`pkill -TERM -f "notion-poller-daemon[.]py"`), el watchdog lo relanza con
   el env nuevo.
4. Verificar en el log: `Promote scan ENABLED` al boot, y por ciclo
   `Promote scan: promote_enabled=True scanned=N eligible=N promoted=N
   skipped=N errors=N`.
5. El smoke E2E real (P3.2 del roadmap, las 4 salidas de HITL-1) queda para
   una fase posterior con GO explícito de David — este PR sólo cablea P2.1.

## Tests

- [tests/test_editorial_promote.py](../../tests/test_editorial_promote.py) —
  handler: gate (`not_approved`), idempotencia (`already_promoted`),
  `dry_run`, creación + write-back de relaciones, red de seguridad ante
  duplicados (re-run no duplica), mapeo `canal_sugerido` → `Tipo de
  contenido`, fallos de lectura/creación.
- `tests/test_notion_poller.py::TestPromoteFlagParsing` /
  `TestPromoteScanBehavior` — scan: flag default-off, filtrado
  Aprobar/`promovido_a`, backoff en fallo, límite de batch, checkpoint Redis.

## Referencias

- Contrato: [editorial-norte-hitl-contract-2026-07-22.md](editorial-norte-hitl-contract-2026-07-22.md) §4, §6
- Roadmap: [editorial-roadmap-norte-p1-p3-2026-07-22.md](editorial-roadmap-norte-p1-p3-2026-07-22.md) fila P2.1
- Schemas: [alternativas-shortlist.schema.yaml](../../notion/schemas/alternativas-shortlist.schema.yaml) (bloque `promotion`), [publicaciones.schema.yaml](../../notion/schemas/publicaciones.schema.yaml) (`origen_alternativa`)
- Snapshot live de IDs: [editorial-shortlist-p1-live-snapshot-2026-07-22.md](editorial-shortlist-p1-live-snapshot-2026-07-22.md)
- Runbook poller (topología, flags hermanos): [runbooks/runbook-notion-poller.md](../../runbooks/runbook-notion-poller.md)
