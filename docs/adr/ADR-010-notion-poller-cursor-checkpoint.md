# ADR-010: `notion.poll_comments` cursor checkpoint en Redis

## Estado

Accepted — 2026-05-06

Deriva de: O8i del Plan Q2-2026 Platform-First (`notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md`). Sigue al fix tactical PR #290 (timeout 30→300s) registrado en O8h. Esta ADR cierra el sub-objetivo `O8i.(a)`.

## Contexto

### El bug

`notion.poll_comments` (`worker/notion_client.py::poll_comments`) lista comentarios de una página Notion. La API `GET /v1/comments?block_id=...` de Notion retorna comentarios **oldest-first** y no acepta filtro `since` server-side. La implementación actual:

1. Pide páginas de hasta 100 comentarios.
2. Aplica el filtro `since` **post-fetch**: `if since_dt and created_dt <= since_dt: continue`.
3. Sólo rompe el loop si `len(comments) >= limit` (default 20) o si Notion responde `has_more=false`.

Resultado: en una página con N comentarios históricos y `since` reciente, el loop hace `ceil(N/100)` requests aunque sólo haya 0–20 comentarios nuevos. Para la página OpenClaw `30c5f443fb5c80eeb721dc5727b20dca` (~30k comments acumulados por SIM Daily Reports c/6h) son ~300 requests por poll cycle ≈ 60s, excediendo el timeout default 30s del `WorkerClient` y causando `httpx.ReadTimeout` en cada cycle.

### El sev-1 ya cerrado

Sev-1 detectado 2026-05-05: poller silente desde 2026-05-02 17:49 UTC (3 días sin procesar comments). Fix tactical PR #290 mergeado: timeout 30→300s en daemon (`scripts/vps/notion-poller-daemon.py`, commit `4c5e55c`). Pipeline restaurado, backlog drenado. Triage: `docs/ops/notion-poll-comments-sev1-triage-2026-05-05.md`.

**El timeout bumpeo es paliativo.** Al ritmo actual (~5 SIM Daily Reports/día = 1825/año + comentarios humanos), los 30k comments de OpenClaw crecen ~5k/año. Proyección: el timeout 300s también se agota cuando la página llegue a ~100k comments (~14 meses sin más mitigación). Páginas adicionales high-volume aceleran el deadline.

### Restricciones de la API Notion

- No hay parámetro `direction=descending` ni `sort` en `/v1/comments`.
- No hay parámetro `created_after` server-side.
- `next_cursor` es estable: una vez obtenido, sigue apuntando a la misma posición lógica aún si llegan comentarios nuevos al final (los nuevos quedan después del cursor).
- `has_more=false` no devuelve `next_cursor`. Es el "fin de stream conocido".

## Decisión

### D1 — Mantener cursor opaco per-page en Redis

Para cada `page_id` polleado, persistir el último `next_cursor` que apuntaría al siguiente comentario no-procesado.

Clave Redis: `notion:poll:cursor:<page_id>`
Valor: cursor opaco (string) devuelto por la API Notion.
TTL: **30 días**, refrescado en cada poll exitoso. Si el cursor caduca (página sin polls 30+ días), siguiente poll cae en fallback (D3).

Comportamiento por cycle:

1. Si existe cursor en Redis → usarlo como `start_cursor` desde el primer request. Esto **salta todo el histórico en una sola llamada API** y procesa sólo los comentarios añadidos desde el último poll.
2. Procesar comentarios. Cada vez que la respuesta trae `next_cursor` (incluso entre páginas internas), guardarlo en Redis al final del cycle.
3. Cuando `has_more=false`, el cursor guardado es el último `next_cursor` recibido (o si fue `false` en el primer request, conservar el cursor anterior — Notion no entrega cursor nuevo si no hay más páginas).

### D2 — Bootstrap "tail-seek" en primer poll sin cursor

Primera vez que se pollea una página y no hay cursor en Redis: **NO recorrer todo el histórico**. En su lugar:

1. Hacer un único request con `page_size=100`, sin `start_cursor`, ignorar los comentarios devueltos (todos son históricos pre-deploy).
2. Si `has_more=true`: usar `next_cursor` y seguir paginando hasta `has_more=false`, **sin acumular comentarios** (modo seek).
3. Persistir el último `next_cursor` (o un sentinel "tail-reached" si la última respuesta fue `has_more=false`) en Redis.
4. Retornar `{"comments": [], "count": 0, "bootstrap": true}`.

Costo: una vez por página, equivalente al costo del bug actual (N/100 requests). Pero a partir del segundo poll, todos los cycles son O(1) requests + lo nuevo.

**Alternativa rechazada:** seed externo via script one-shot. Más operacional. Tail-seek auto-bootstrap es self-healing.

### D3 — Fallback soft cuando el cursor falla

Si Notion responde 400/404 a un `start_cursor` (cursor inválido o expirado en server, raro pero posible):

1. Loggear `notion.poll_comments.cursor_invalidated` con `page_id` y excepción.
2. Borrar la key Redis.
3. Re-bootstrap automáticamente (D2). Cycle actual retorna `{"comments": [], "count": 0, "cursor_reset": true}`.

Sin pánico, sin fail. Próximo cycle ya tendrá cursor fresco.

### D4 — Mantener `since` como segundo filtro defensivo

El parámetro `since` no se elimina. Si el caller pasa `since`, se aplica POST-fetch como hoy, **encima** del filtro por cursor. Esto cubre dos casos:

- Tests/scripts que llamen sin Redis disponible (`since` sigue funcionando como filtro grueso).
- Defensa en profundidad si un cursor mal-guardado entrega un comment antiguo por error (improbable pero barato).

### D5 — Métrica observable

Cada poll loggea:

- `cursor_used`: bool (true si vino de Redis, false si bootstrap o sin Redis)
- `requests_count`: cuántas llamadas Notion se hicieron
- `comments_returned`: cuántos comments efectivos
- `bootstrap`: bool
- `cursor_reset`: bool

Esto permite ver en `journalctl -u notion-poller-daemon` cuándo el bootstrap está ocurriendo y validar que `requests_count` cae a 1–2 en estado estable.

### D6 — Re-evaluar timeout WorkerClient después de soak

Con cursor activo, una poll cycle estable debería tomar <2s. Re-bajar el timeout del daemon de 300s → 60s **una semana después** de deploy si métricas confirman. Mantenerlo en 300s entre tanto (defensa contra bootstrap de páginas grandes recién añadidas).

## Consecuencias

### Positivas

- **O(1) requests por cycle en estado estable** — independiente del tamaño histórico de la página.
- Self-healing: cursor expirado o inválido → re-bootstrap automático sin intervención manual.
- Permite polleat páginas con >100k comments sin reescribir nada.
- Backwards-compat: `since` sigue funcionando como filtro defensivo.

### Negativas

- Dependencia adicional en Redis (ya existe, ya usada por daemon).
- Bootstrap de página nueva sigue siendo O(N/100) requests one-shot — aceptable: ocurre una sola vez.
- Cursor opaco no es legible por humanos. Para debug, exponer en log + endpoint admin (`/admin/notion-poll-cursors`) en futuro Mission Control O13.

### Riesgos abiertos

- Si Notion cambia el formato/semántica de `next_cursor` (ej. los invalida tras T tiempo), el fallback D3 cubre el caso. Métrica D5 detecta degradación.
- Múltiples consumers polleando la misma `page_id` desde Redis = compiten por el cursor. **Decisión:** asumimos un solo poller daemon per page (es el modelo actual). Si esto cambia (ej. multi-tenant), revisitar con leases Redis.

## Plan de implementación

Sub-pasos del plan O8i:

- [x] **(a)** ADR escrita (este documento).
- [ ] **(b)** Implementar D1+D2+D3+D5 en `worker/notion_client.py::poll_comments`. Inyectar Redis client opcional via parámetro (default: `None` → comportamiento legacy con `since` puro). El daemon `scripts/vps/notion-poller-daemon.py` pasa `redis_client=r`.
- [ ] **(c)** Tests `tests/test_poll_comments_cursor.py`: bootstrap, cursor hit, cursor invalidation/fallback, sin Redis (legacy path).
- [ ] **(d)** Smoke en VPS: ejecutar manual contra OpenClaw page (~30k comments) y 2 pages low-volume; capturar `requests_count` antes/después del segundo cycle. Observar `journalctl` por 24h post-deploy. Después de 7 días, ejecutar D6 (re-bajar timeout).

## Referencias

- O8h triage: `umbral-agent-stack/docs/ops/notion-poll-comments-sev1-triage-2026-05-05.md`
- PR tactical fix: Umbral-Bot/umbral-agent-stack#290 (commit `4c5e55c`)
- Plan Q2 O8 cluster: `notion-governance/docs/roadmap/12-q2-2026-platform-first-plan.md` líneas 510–518
- Notion Comments API: <https://developers.notion.com/reference/retrieve-a-comment>
