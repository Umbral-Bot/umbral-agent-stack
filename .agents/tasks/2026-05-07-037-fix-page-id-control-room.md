---
id: 2026-05-07-037
title: Fix page_id resolution for Control Room in notion_poller (envelope reaches handler with page_id=None)
status: open
priority: P0-blocker
assigned_to: codex
created_at: 2026-05-07
created_by: claude (post-035 deploy + smoke B6 PARTIAL)
parent: 2026-05-07-035
relates_to: 2026-05-07-032
blocks: O15.1b
---

# 037 — Fix `page_id` resolution for Control Room in `notion_poller`

## Contexto

Task 035 (PR #361, merged en main `fcd0c69f`, capitalizado en board `466c5c26`) eliminó el bug de `poll_comments` bootstrap que descartaba resultados con cursor `__TAIL__`. Tras el deploy en VPS y restart de `umbral-worker` (pid 96364 → 114572), el path Notion → poller → dispatcher → worker → handler **funciona end-to-end hasta el handler** — pero el reply nunca se postea porque el envelope llega con `page_id=None`. El handler `rick.orchestrator.triage` ejecuta correctamente su gap honesto (SOUL Regla 22) y skipea el reply.

Resultado: David's comment `2026-05-07T18:44:00Z @Rick ping worker /health …` sigue **sin reply real** en la Control Room. Los 2 comments del bot Rick a `2026-05-07T20:51:00Z` son outputs de OTROS workflows (`SIM Daily Report` Marketing post + `research_and_post` workflow completion), no responden al `/health`.

**NO regresión de task 035** — bug pre-existente que estaba enmascarado: antes el comment nunca llegaba al handler (bloqueado por bug 035); ahora que llega, este otro aflora. Bloquea cierre 100% de O15.1b (smoke real Notion → reply).

## Root cause (rastreado empíricamente)

Cadena exacta del envelope con `page_id=None`:

1. **`dispatcher/notion_poller.py:227`** — `_collect_candidate_comments` arma:
   ```python
   poll_targets: list[dict[str, str | None]] = [{"page_id": None, "page_kind": "control_room"}]
   poll_targets.extend(_resolve_review_targets(wc))
   ```
   La Control Room es el ÚNICO target con `page_id=None` (los `_resolve_review_targets` sí pasan ids reales).

2. **`dispatcher/notion_poller.py:240-247`** — al mergear los comments retornados, hay guard:
   ```python
   merged = dict(comment)
   if page_id:
       merged.setdefault("page_id", page_id)
       if page_kind:
           merged.setdefault("page_kind", page_kind)
   ```
   Cuando `page_id is None` (Control Room), el `merged` dict **nunca recibe `page_id`** ni `page_kind`. El comment crudo de Notion API no trae `page_id` propio.

3. **`dispatcher/notion_poller.py:441`** — call site del rick_mention router:
   ```python
   handle_rick_mention(
       text=text, comment_id=comment_id,
       page_id=c.get("page_id"), page_kind=c.get("page_kind"),
       ...
   )
   ```
   `c.get("page_id")` → `None`.

4. **`dispatcher/rick_mention.py:70`** — el envelope al worker se arma con:
   ```python
   "input": { ..., "page_id": page_id, "page_kind": page_kind, ... }
   ```
   Llega `"page_id": null` al worker.

5. **`worker/tasks/rick_orchestrator.py:131-149`** — handler:
   ```python
   if page_id:
       reply = notion_client.add_comment(page_id=page_id, text=reply_text)
       ...
   else:
       error = (error + " | " if error else "") + "no_page_id_in_envelope"
       logger.warning("rick.orchestrator.triage missing page_id in envelope; reply skipped")
   ```

Evidencia runtime post-035 (logs del 2026-05-07 16:51:08 ART, trace `75e1c4b9`):
- Poller log: `Rick mention routed: comment=3595f443 author=1e3d872b page=? trace=75e1c4b9`
- Dispatcher journal: `Executing task 987bbfca... rick.orchestrator.triage -> VPS`
- Worker journal:
  ```
  rick.orchestrator.triage classify command=health comment=3595f443 trace=75e1c4b9
  rick.orchestrator.triage missing page_id in envelope; reply skipped
  ```

## Opciones de fix

### Opción A (RECOMENDADA — fix en el origen)

En `dispatcher/notion_poller.py`, resolver el page_id de la Control Room desde env ANTES de armar `poll_targets`:

```python
# en _collect_candidate_comments (~línea 226)
control_room_pid = os.environ.get("NOTION_CONTROL_ROOM_PAGE_ID", "").strip() or None
poll_targets = [{"page_id": control_room_pid, "page_kind": "control_room"}]
```

Trade-offs:
- ✅ Arregla el origen — todos los downstream (rick_mention, smart_reply, otros routes) reciben page_id real.
- ✅ Consistente con el resto de targets (que ya pasan ids reales).
- ⚠️ Cambia comportamiento del `wc.notion_poll_comments(page_id=...)`: pasa de `None` (que el client probablemente resuelve internamente al CONTROL_ROOM env) a un valor explícito. Verificar que el `worker_client.notion_poll_comments` acepta page_id explícito sin romper la query.

### Opción B (fallback defensivo en handler)

En `worker/tasks/rick_orchestrator.py` (~línea 130), antes del `if page_id:`:

```python
import os
if not page_id and input_data.get("page_kind") == "control_room":
    page_id = os.environ.get("NOTION_CONTROL_ROOM_PAGE_ID", "").strip() or None
```

Trade-offs:
- ✅ NO toca canal lateral del poller (otros consumers no afectados).
- ❌ El bug del poller queda. Cualquier nuevo handler también recibirá `page_id=None` para Control Room.
- ❌ Spreads de la responsabilidad (cada handler tiene que hacer su propio fallback).

**Recomendación**: **Opción A** + opcional Opción B como cinturón-y-tirantes. Codex decide en base a tests.

## Tests obligatorios

Agregar en `tests/test_notion_poller.py` (o nuevo `tests/test_notion_poller_targets.py`):

1. `test_control_room_target_resolves_page_id_from_env` — con `NOTION_CONTROL_ROOM_PAGE_ID` exportado en monkeypatch, `_collect_candidate_comments` (o el helper que arma poll_targets) produce `page_id` no-None para `page_kind=="control_room"`. Verificar que el envelope downstream lleva el page_id real (mockeando rick_mention router).

2. `test_control_room_target_no_env_logs_warning_no_silent_none` — sin env exportado, el código loguea `WARNING` explícito (no propaga None silencioso). Aceptable que el target quede skip o con marca explícita, pero NUNCA `page_id=None` silencioso que termine en envelope.

3. (Solo si Opción B) `test_handler_rick_orchestrator_envelope_page_id_none_control_room_fallback` en `tests/test_rick_orchestrator.py` — handler recibe envelope con `page_id=None` y `page_kind="control_room"`, con env set; verifica que NO skipea, sí postea reply al CONTROL_ROOM page_id.

4. **No-regresión**: `tests/test_notion_poll_bootstrap.py` (de task 035) sigue verde. Tests del handler `test_rick_orchestrator.py` (de task 032) siguen verdes. Tests existentes del poller (`tests/test_notion_poller*.py`) sin regresión.

## Restart requerido post-merge

```bash
# en VPS, como user rick
cd /home/rick/umbral-agent-stack
git pull origin main
systemctl --user restart umbral-worker         # SI Opción B (handler tocado)
systemctl --user restart openclaw-dispatcher   # SI Opción A (poller tocado) — el daemon notion_poller corre en este unit
```

Verificación post-restart:
- `journalctl --user -u openclaw-dispatcher --since "1 min ago" | grep "Rick mention routed"` debe mostrar `page=<8-char prefix de CONTROL_ROOM>` (no `page=?`).
- `curl http://127.0.0.1:8088/health` → `ok=True`, `tasks_registered` incluye `rick.orchestrator.triage`.

## Smoke real Notion post-fix (cierre O15.1b)

David repostea en Control Room (page_id `30c5f443fb5c80eeb721dc5727b20dca`):
> @Rick ping worker /health y devolveme el JSON acá como reply

Verificar en ≤6 min (1 cron tick + buffer):
- Logs muestran `Rick mention routed: comment=<X> author=1e3d872b page=30c5f443 trace=<Y>` (page con 8-char prefix real).
- Worker journal muestra `rick.orchestrator.triage classify command=health` y `reply posted page=30c5f443 reply=<Z>`.
- Notion API: nuevo comment en Control Room creado por bot Rick (`3145f443-fb5c-814d-bbd1-0027093cebce`) con `created_time > T0` y body con JSON parseable de `/health`.

## Constraints heredados

- ❌ NO restart `openclaw-gateway` pid 75421 (Vertex Fase 1 ventana hasta 2026-05-14, debe seguir intacto).
- ❌ NO touch `~/.openclaw/openclaw.json` ni `model.primary`.
- ❌ NO borrar cursor Redis `notion:poll:cursor:30c5f443…` (volvería al loop perpetuo del bug 035).
- ✅ F-INC-002 antes de pull/push (fetch + log HEAD..origin/main + log origin/main..HEAD).
- ✅ secret-output-guard #8 (no imprimir `NOTION_API_KEY`, `WORKER_TOKEN`, `GITHUB_TOKEN`; ids por prefijo 8 chars).
- ✅ SOUL Reglas 21+22 (verificar runtime real, no inventar; si Codex detecta que Opción A rompe algo, abortar y pasar a Opción B).

## Honest gap conocido

Si Codex implementa Opción A y verifica que `worker.notion_client.poll_comments` ya hace el fallback `if page_id is None: page_id = config.NOTION_CONTROL_ROOM_PAGE_ID` (que sí lo hace, ver `worker/notion_client.py:535`), confirmar que pasar el page_id explícito desde el dispatcher NO duplica la query ni cambia el cursor key (la cursor key es por page_id; si antes era None y ahora es el id real, podría arrancar bootstrap nuevo — verificar con dry-run y ajustar).

## Referencias

- Board entry capitalización 035 + 037 abierto: commit `466c5c26` en `main` umbral-agent-stack.
- PR #361 closeout task 035 (merged main `fcd0c69f`).
- Plan Q2 capitalización en notion-governance: commit `86d93a8`.
- Spec task 035 referencia formato: `.agents/tasks/2026-05-07-035-fix-poll-comments-bootstrap-collect.md`.
- PR #353 (spec task 035 handoff Codex pattern): https://github.com/Umbral-Bot/umbral-agent-stack/pull/353.

## Suggested branch name

`codex/037-fix-page-id-control-room`
