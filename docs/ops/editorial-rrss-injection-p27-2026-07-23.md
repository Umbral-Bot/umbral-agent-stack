# P2.7 — Inyección `published_url` + `listo_rrss` (2026-07-23)

> **Estado:** código + tests implementados, **DEFAULT OFF** (fail-closed).
> Cablea el paquete P2.7 del
> [roadmap norte](editorial-roadmap-norte-p1-p3-2026-07-22.md) §3 (Fila I = B).
> **Cero llamadas a API de LinkedIn/X** — este paquete sólo escribe
> propiedades de Notion (rich_text/checkbox/url). No abre gates, no inventa
> Telegram, no crea schema, no toca Magnific/copy/dedupe/negativos (P2.2-P2.5)
> ni el gate D3 de HITL-2 (P2.6).

## Qué es (Fila I = B)

Tras publicar el blog con éxito, el contrato (§5.I) exige: inyectar
`published_url` en las copies por canal y marcar `listo_rrss = true` como
**estado terminal** de RRSS bajo Fila I = B — el post real a LinkedIn/X sigue
siendo **manual** (David/operador copia el texto ya con el link y lo publica
a mano). Antes de este paquete, `listo_rrss` existía en el schema (P1) pero
nada lo escribía ni inyectaba el link en las copies.

## Qué hace

### 1. Núcleo compartido (`worker/tasks/editorial_publish.py::inject_rrss_copies_and_mark_ready`)

Una sola función, reusada por el hook inline y por la task standalone:

1. Re-lee la página Publicaciones en vivo (fail-closed).
2. Si `listo_rrss` ya es `true` → no-op idempotente (`already_ready=true`).
3. Resuelve `published_url` — recibido explícito (hook inline, recién obtenido
   de Azure) o leído de la propiedad `published_url` de Notion (task
   standalone/backfill). Si no hay ninguno → `error: "published_url_missing"`,
   sin escribir nada.
4. Por cada copy de canal (`Copy LinkedIn`, `Copy X`, `Copy LinkedIn empresa`)
   que **tenga contenido** y **no contenga ya** el link: agrega
   `\n\n{published_url}` al final. Una copy vacía se **salta** (no se fabrica
   contenido — sigue siendo trabajo de P2.3/Rick). Una copy que ya contiene
   el link se deja intacta (idempotencia por canal, no sólo por el checkbox).
5. Escribe las copies modificadas + `published_url` + `listo_rrss=true` en
   **una sola llamada** a `update_page_properties`.

### 2. Hook inline (post-publish, dentro de `handle_web_publish_editorial_post`)

Nuevo input `inject_rrss_after_publish` (bool, **default `False`**, mismo
criterio de cautela que `write_back_to_notion`). Cuando está en `true`:
tras un publish real exitoso (nunca en `dry_run`, nunca si el triple gate de
P2.6 bloqueó), llama a la función compartida con el `published_url` recién
devuelto por Azure. **Best-effort** — un fallo de la inyección nunca revierte
ni marca como fallido el publish ya ocurrido (mismo patrón que el hook de RAG,
Task B).

### 3. Task standalone (`editorial.inject_rrss_ready`)

Para backfill/uso manual sin re-publicar: dado sólo `notion_page_id`, lee
`published_url` de la página y aplica la misma lógica. Soporta `dry_run`.

### 4. Scan de backfill (`dispatcher/notion_poller.py::_inject_rrss_for_published_rows`)

Opt-in, **DEFAULT OFF** (`NOTION_POLLER_ENABLE_RRSS_INJECTION`). Escanea
Publicaciones buscando filas no archivadas con `Estado == "Publicado"` **y**
`published_url` no vacío **y** `listo_rrss` falso — cubre filas publicadas
antes de este paquete, o publicadas con `inject_rrss_after_publish=False`.
Llama a `editorial.inject_rrss_ready` (a diferencia del scan de observabilidad
de P2.6, este **sí** escribe en Notion una vez habilitado — nunca en
LinkedIn/X). El poller **nunca** escribe directo (ADR-011 #1).

## Qué NO hace (por diseño — alcance estricto de P2.7)

- **Cero llamadas a LinkedIn/X.** Ni la función compartida, ni el hook, ni la
  task, ni el scan tocan ninguna API de red social. El "post" sigue siendo
  100% manual, coherente con Fila I = B y ADR-010 §Contexto.
- No fabrica copy — si un canal no tiene texto (P2.3 aún no corrió, o Rick no
  lo generó), esa copy se salta, no se rellena con texto genérico.
- No abre `aprobado_contenido` / `autorizar_publicacion`, no toca el gate
  `telegram_confirmed` (P2.6) — `listo_rrss` es un estado terminal posterior
  al publish, no uno de los gates de disparo.
- No crea ni modifica schema Notion — `listo_rrss` ya vive en
  `notion/schemas/publicaciones.schema.yaml` desde P1.

## Flags / inputs (todas fail-closed por ausencia)

| Var / input | Proceso | Default | Efecto |
|---|---|---|---|
| `inject_rrss_after_publish` (input del task `web.publish_editorial_post`) | Worker | `False` | Activa el hook inline tras un publish real exitoso. |
| `NOTION_POLLER_ENABLE_RRSS_INJECTION` | dispatcher (poller) | off | Habilita el scan de backfill. Sin esto, el poller nunca corre este scan. |
| `NOTION_PUBLICACIONES_DB_ID` | dispatcher (poller) + Worker | vacío | Ya usado por P2.1/P2.2/P2.6. Sin esto, el scan es no-op. |

## Cómo correr un dry-run

**Task standalone, por página** (no requiere haber publicado en esta misma
llamada):

```bash
curl -s -X POST "$WORKER_URL/run" \
  -H "Authorization: Bearer $WORKER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task": "editorial.inject_rrss_ready", "input": {"notion_page_id": "<page_id>", "dry_run": true}}'
```

Respuestas esperadas:
- Ya lista: `{"ok": true, "already_ready": true, "injected_channels": []}`.
- Sin `published_url`: `{"ok": false, "error": "published_url_missing"}`.
- Candidata válida: `{"ok": true, "dry_run": true, "would_inject": true, "injected_channels": ["copy_linkedin", ...]}`.

**Hook inline, junto con un publish dry-run** (previsualiza ambos a la vez —
nota: el hook inline sólo corre en publish **real**, no en `dry_run`; para
probar la inyección sin publicar de verdad usar la task standalone de
arriba).

**Scan del poller**: no tiene dry-run propio — probar página por página con
la task standalone antes de habilitar `NOTION_POLLER_ENABLE_RRSS_INJECTION`.

## Cómo habilitar en producción

1. Confirmar `NOTION_PUBLICACIONES_DB_ID` configurado (ya debería estarlo).
2. Para el hook inline: pasar `inject_rrss_after_publish: true` en las
   llamadas reales a `web.publish_editorial_post` (vía el operador o el
   futuro puente n8n de P2.6).
3. Para el backfill: `NOTION_POLLER_ENABLE_RRSS_INJECTION=true` + relanzar el
   poller (mismo procedimiento que
   [runbooks/runbook-notion-poller.md](../../runbooks/runbook-notion-poller.md)).
4. Verificar en el log: `RRSS-injection scan ENABLED` al boot, y por ciclo
   `RRSS-injection scan: rrss_injection_enabled=True scanned=N eligible=N
   injected=N skipped=N errors=N`.

## Tests

- [tests/test_editorial_rrss_injection.py](../../tests/test_editorial_rrss_injection.py) —
  función compartida: idempotencia (`listo_rrss` ya true), `published_url`
  faltante bloquea, inyección en las tres copies, copy vacía se salta sin
  fabricar contenido, canal ya con el link queda intacto, `dry_run` sin
  escribir, fallback a leer `published_url` de Notion, fallos de lectura/
  escritura; task standalone: input requerido, lee `published_url` de Notion,
  `dry_run`, registro en `TASK_HANDLERS`.
- `tests/test_editorial_publish.py::TestRrssInjectionHook` — hook inline:
  apagado por defecto (no llama a Notion), inyecta con el `published_url`
  recién publicado, un fallo de inyección nunca falla el publish, no se
  intenta si el publish fue bloqueado o fue `dry_run`.
- `tests/test_notion_poller.py::TestRrssInjectionFlagParsing` /
  `TestRrssInjectionScanBehavior` — scan: flag default-off, filtrado
  `Estado`/`published_url`/`listo_rrss`/archivadas, backoff en fallo/
  excepción, límite de batch, checkpoint Redis.

## Referencias

- Contrato: [editorial-norte-hitl-contract-2026-07-22.md](editorial-norte-hitl-contract-2026-07-22.md) §5.I
- Roadmap: [editorial-roadmap-norte-p1-p3-2026-07-22.md](editorial-roadmap-norte-p1-p3-2026-07-22.md) fila P2.7
- ADR-010 (nunca autopublica RRSS): [ADR-010-azure-editorial-blog-cms.md §Contexto](../adr/ADR-010-azure-editorial-blog-cms.md)
- Content model / canales: [notion-blog-linkedin-v3-content-model.md](notion-blog-linkedin-v3-content-model.md)
- Schema `listo_rrss` (ya vivo desde P1): [notion/schemas/publicaciones.schema.yaml](../../notion/schemas/publicaciones.schema.yaml)
- Sibling P2.6 (gate de disparo, no confundir con este estado terminal): [editorial-hitl2-publish-bridge-p26-2026-07-23.md](editorial-hitl2-publish-bridge-p26-2026-07-23.md)
