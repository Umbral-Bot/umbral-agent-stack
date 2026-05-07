---
id: 2026-05-07-035
title: Fix poll_comments bootstrap infinite-zero loop on small pages
status: open
priority: P0-blocker
assigned_to: codex
created_at: 2026-05-07
created_by: claude (smoke real B6 task 032)
parent: 2026-05-07-032
blocks: O15.1b
---

# 035 — Fix `poll_comments` bootstrap infinite-zero loop on small pages

## Contexto

El smoke real de task 032 (B6) demostró empíricamente que el handler `rick.orchestrator.triage` (PR #349, mergeado en main) está sano y registrado, pero el canal Notion → poller → dispatcher → worker NO entrega comments cuando la Control Room tiene ≤ `page_size` (20) comments en total. David posteó el comment de validación a las `2026-05-07T18:44:00Z` y permanece sin reply: el handler nunca se invocó porque el poller jamás emitió `Rick mention routed` para ese comment.

Evidencia completa en `/tmp/032/smoke-real-fail.md` y `/tmp/032/comments-window.json`.

## Root cause (confirmado empíricamente)

`worker/notion_client.poll_comments` (worker/notion_client.py ~líneas 500-665) tiene un branch de bootstrap que **descarta resultados** y entra en loop infinito cuando se cumplen TODAS las condiciones:

1. Redis cursor `notion:poll:cursor:<page_id>` == `"__TAIL__"` (sentinel `CURSOR_TAIL_SENTINEL`).
2. La página devuelve `has_more=False` y `next_cursor=None` en una sola request (i.e. tiene ≤ `page_size` comments en total).

Mecanismo:

```python
saved_cursor = "__TAIL__"
if saved_cursor == CURSOR_TAIL_SENTINEL:
    saved_cursor = None
    bootstrap = True
# loop:
data = GET /v1/comments?block_id=...&page_size=20
# data.results = [2 comments], has_more=False, next_cursor=None
if not bootstrap:           # <-- bootstrap=True → resultados descartados
    for c in data["results"]: comments.append(...)
next_cursor = None          # → last_seen_cursor sigue None
if not data["has_more"]:    # → reached_tail=True, break
    break
# persistencia:
cursor_to_save = last_seen_cursor or CURSOR_TAIL_SENTINEL
# = None or "__TAIL__" → "__TAIL__" re-grabado → loop perpetuo
```

Reproducción exacta (ejecutada en VPS 2026-05-07T18:55Z):
```
cursor before: '__TAIL__'
count: 0
bootstrap: True
cursor_used: False
requests_count: 1
cursor after: '__TAIL__'
```

## Impacto

- **Bloquea O15.1b al 100%** — todo intento de validación end-to-end por Notion (David comenta → Rick responde) falla silenciosamente mientras la Control Room tenga ≤20 comments.
- Bug latente: en cuanto la página supere `page_size`, el bootstrap caminará pagination y guardará un cursor real, "auto-curándose". Pero hasta entonces, el canal queda muerto.
- Pre-existente, NO regresión de task 032.

## Criterio de aceptación

1. **Empírico**: tras el fix + restart `umbral-worker`, ejecutar el smoke real:
   - David (o Claude usando token de David) postea un comment `@Rick ping worker /health …` en Control Room.
   - Dentro de ≤6 min (1 cron tick + buffer): aparece reply nuevo por bot Rick (`3145f443…`) con `created_time > T0` y body conteniendo JSON parseable de `/health` (`ok=true`, `version`, `tasks_registered`).
   - Logs: `notion_poller` emite `Rick mention routed`; dispatcher emite `Executing task rick.orchestrator.triage`; worker emite `rick.orchestrator.triage classify command=health`.
2. **Test unitario** que reproduzca el escenario (cursor==`__TAIL__`, page con ≤page_size comments, mock httpx returning has_more=False+next_cursor=None) y assertee `count > 0` cuando hay comments nuevos.
3. **No-regresión**: tests existentes de `poll_comments` siguen verdes (paginación normal, since-filter, cursor invalidation D3).

## Opciones de fix (elegir una en design.md)

### Opción A (mínima) — bootstrap también colecciona

Eliminar el guard `if not bootstrap:` y dejar que bootstrap recolecte. Aplicar el `since` filter (que ya está dentro del loop) para no traer históricos. Pro: 1 línea de cambio. Contra: si la página tiene exactamente 20 comments todos antiguos, podría re-emitir comments ya procesados — mitigado por el dedupe que el dispatcher ya hace por `comment_id`.

### Opción B — guardar último id visto en bootstrap

Bootstrap colecciona y guarda en Redis (key `notion:poll:lastid:<page_id>`) el id del comment más reciente visto. Próximo poll filtra por id > último visto. Más robusto pero requiere migración de schema y más código.

### Opción C — tras bootstrap exitoso, NO re-grabar sentinel; grabar timestamp

Cambiar `CURSOR_TAIL_SENTINEL` por una marca de tiempo (`"TAIL@<ts_iso>"`); próximos polls usan ese ts como `since` defensivo aunque no haya cursor real. Más cambio quirúrgico pero alinea con el `since` filter existente.

**Recomendación**: Opción A + el dedupe del dispatcher es suficiente y mínimo. Validar que el dedupe efectivamente exista y funcione antes de cerrar.

## Plan sugerido (sin ejecutar — para Codex)

1. B0: branch nueva desde main `codex/fix-035-poll-bootstrap-collect`, F-INC-002.
2. B1: design.md eligiendo opción (recomendada A), justificación + análisis del dedupe del dispatcher.
3. B2: edit `worker/notion_client.py` — remover/condicionar el guard `if not bootstrap:`.
4. B3: test nuevo `tests/test_notion_poll_bootstrap.py` con escenario reproducido.
5. B4: pytest local todo verde + test específico.
6. B5: commit + push + PR.
7. **Después del merge**: VPS deploy (`git pull` + `systemctl --user restart umbral-worker`); luego re-correr smoke real con David o test manual; recién ahí O15.1b cierra al 100%.

## NO hacer en este task

- ❌ NO restart gateway pid 75421 (Vertex Fase 1, hasta 2026-05-14).
- ❌ NO tocar el handler `rick.orchestrator.triage` (sano).
- ❌ NO borrar manualmente la key `notion:poll:cursor:30c5f443fb5c80eeb721dc5727b20dca` como "fix" — es workaround temporal que vuelve al loop.

## Referencias

- Smoke real evidencia: `/tmp/032/smoke-real-fail.md`.
- Notion API snapshot: `/tmp/032/comments-window.json`.
- Task 032 (handler implementado): `.agents/tasks/2026-05-07-032-*.md` + PR #349.
- Task 031 (diagnosis previa que pasó porque el cursor entonces no era TAIL): PR #346 commit `100af66`.
