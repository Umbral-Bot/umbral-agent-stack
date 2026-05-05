# Task 011 — Ola 1b: adaptador `@rick` mention en notion poller

- **Date:** 2026-05-05
- **Assigned to:** copilot-vps
- **Depends on:** Task 010 (helper `_trace.append_delegation`) mergeado.
- **Related ADR:** `notion-governance/docs/adr/05-ola-1b-channel-adapters-and-traceability.md` §2.1, §2.2.
- **Related design:** `notion-governance/docs/roadmap/13-ola-1b-design-notion-mention-to-task.md` §3, §4.
- **Status:** ready (no ejecutar antes de cerrar 010)
- **Estimated effort:** 1 sesión (~60 min, incluyendo tests + deploy + smoke en VPS)

---

## Objetivo

Detectar comentarios Notion donde el autor (David) menciona `@rick` y bypassear el flujo legado `intent_classifier + smart_reply`, encolando en su lugar una tarea para `rick-orchestrator` con payload `notion.comment.mention` (ADR 05 §2.2). Cada delegación queda registrada vía `_trace.append_delegation`.

## Scope concreto

### Archivo nuevo: `dispatcher/rick_mention.py` (≤120 líneas)

```python
"""
Rick mention adapter (Ola 1b).

Detects @rick mentions in Notion comments and routes them to the
rick-orchestrator subagent, bypassing the legacy intent_classifier path.
"""
from __future__ import annotations

import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from worker.tasks._trace import append_delegation
from dispatcher.queue import TaskQueue
from dispatcher.scheduler import TaskScheduler
from client.worker_client import WorkerClient

logger = logging.getLogger("dispatcher.rick_mention")

_RICK_MENTION_RE = re.compile(r"@rick(?:-orchestrator)?\b", re.IGNORECASE)
_MAX_TEXT_SNIPPET = 500


def is_rick_mention(text: str, author: Optional[str], allowlist: set[str]) -> bool:
    """Return True if text mentions @rick AND author is in allowlist."""
    if not text or not author:
        return False
    if author not in allowlist:
        return False
    return bool(_RICK_MENTION_RE.search(text))


def _david_allowlist() -> set[str]:
    raw = os.environ.get("DAVID_NOTION_USER_ID", "").strip()
    return {raw} if raw else set()


def handle_rick_mention(
    *,
    text: str,
    comment_id: str,
    page_id: Optional[str],
    page_kind: Optional[str],
    author: Optional[str],
    wc: WorkerClient,
    queue: TaskQueue,
    scheduler: TaskScheduler,
) -> None:
    """Enqueue rick-orchestrator triage + record delegation trace."""
    trace_id = uuid.uuid4().hex
    snippet = (text or "")[:_MAX_TEXT_SNIPPET]
    payload = {
        "kind": "notion.comment.mention",
        "comment_id": comment_id,
        "page_id": page_id,
        "page_kind": page_kind,
        "author": author,
        "text": snippet,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "trace_id": trace_id,
    }
    queue.enqueue("rick.orchestrator.triage", payload)
    append_delegation({
        "trace_id": trace_id,
        "from": "channel-adapter:notion-poller",
        "to": "rick-orchestrator",
        "intent": "triage",
        "ref": {"comment_id": comment_id, "page_id": page_id},
        "summary": f"@rick mention from author={author[:8] if author else '?'} on {page_kind or 'unknown'}",
    })
    logger.info(
        "Rick mention routed: comment=%s author=%s page=%s trace=%s",
        comment_id[:8], (author or "?")[:8], (page_id or "?")[:8], trace_id[:8],
    )
```

### Patch a `dispatcher/notion_poller.py`

En el loop `for c in comments:` de `_do_poll`, **antes** de la línea `from dispatcher.intent_classifier import classify_intent, route_to_team`, insertar:

```python
        # Ola 1b: @rick mention adapter (bypass legacy intent path)
        from dispatcher.rick_mention import is_rick_mention, handle_rick_mention, _david_allowlist
        if is_rick_mention(text, c.get("created_by"), _david_allowlist()):
            handle_rick_mention(
                text=text,
                comment_id=comment_id,
                page_id=c.get("page_id"),
                page_kind=c.get("page_kind"),
                author=c.get("created_by"),
                wc=wc,
                queue=queue,
                scheduler=scheduler,
            )
            continue
```

NO modificar nada más del poller. Comentarios sin `@rick` continúan por `handle_smart_reply` exactamente como hoy.

### Tests nuevos: `tests/test_rick_mention.py`

Mínimo 7 casos:

1. `is_rick_mention("hola @rick haz X", author="UID_DAVID", allowlist={"UID_DAVID"})` → True.
2. `is_rick_mention("hola @rick-orchestrator", author="UID_DAVID", allowlist={"UID_DAVID"})` → True.
3. `is_rick_mention("hola @rick", author="UID_OTHER", allowlist={"UID_DAVID"})` → False (autor no allowlisted).
4. `is_rick_mention("hola sin mention", author="UID_DAVID", allowlist={"UID_DAVID"})` → False.
5. `is_rick_mention("@RICK hola", author="UID_DAVID", allowlist={"UID_DAVID"})` → True (case insensitive).
6. `handle_rick_mention(...)` invoca `queue.enqueue("rick.orchestrator.triage", payload)` con todos los campos requeridos del schema (mock `TaskQueue`, `WorkerClient`, `TaskScheduler`).
7. `handle_rick_mention(...)` invoca `append_delegation` con `from=channel-adapter:notion-poller`, `to=rick-orchestrator`, `intent=triage`, y `ref` con `comment_id`/`page_id` (verificar via `tmp_path` y luego parsear JSONL).

### Variable de entorno

Documentar en `config/.env.example` (o equivalente):

```env
# Ola 1b: Notion user UUID de David, requerido para que el adaptador @rick actúe.
# Obtener vía: GET https://api.notion.com/v1/users → buscar "David Moreira".
DAVID_NOTION_USER_ID=
```

## Plan de ejecución (Copilot-VPS)

1. **Verificar Task 010 mergeado** en `main` (helper `_trace.py` disponible).
2. **Pull:** `cd /home/rick/umbral-agent-stack && git pull origin main`.
3. **Branch:** `git checkout -b copilot-vps/ola-1b-rick-mention-adapter`.
4. **Resolver `DAVID_NOTION_USER_ID`** vía API Notion (`curl -H "Authorization: Bearer $NOTION_API_KEY" -H "Notion-Version: 2022-06-28" https://api.notion.com/v1/users | jq '.results[] | select(.name | contains("David"))'`).
5. **Setear** `DAVID_NOTION_USER_ID` en `~/.config/umbral/.env` (o donde el worker/dispatcher cargue env). NO commitear el valor real.
6. **Implementar** `dispatcher/rick_mention.py` + patch `notion_poller.py` + `tests/test_rick_mention.py`.
7. **Tests:** `python -m pytest tests/test_rick_mention.py -v` → 7/7 verdes.
8. **Deploy:** `systemctl --user restart openclaw-dispatcher` (el poller corre dentro del dispatcher).
9. **Smoke:** logs `journalctl --user -u openclaw-dispatcher -f` mientras David escribe un comment de prueba `@rick test ola 1b` en una página watched. Confirmar log line `Rick mention routed: ...`.
10. **Verificar trace:** `cat ~/.local/state/umbral/delegations.jsonl | tail -3 | jq` → debe mostrar el record con `trace_id`, `from=channel-adapter:notion-poller`, `to=rick-orchestrator`.
11. **Commit + push + PR** a `main`.

⚠️ El task `rick.orchestrator.triage` aún no tiene handler (se implementa en Tasks 012–013). El smoke test SOLO verifica que la encolación + traza funcionan. El job quedará como `pending` o `failed` en queue — esperado.

## Quality gate

- ✅ `pytest tests/test_rick_mention.py -v` → 7/7.
- ✅ `pytest tests/` global → no regresiones (tests existentes verdes).
- ✅ Comentario `@rick test ola 1b` en página de prueba aparece en `delegations.jsonl` < 60s después.
- ✅ Comentario sin mention sigue procesado por `smart_reply` (verificar log line `Processing [...->...] for comment ...`).
- ✅ `dispatcher/notion_poller.py` patch ≤ 12 líneas añadidas.
- ✅ Cumple `secret-output-guard` (no loggea text completo, autor truncado a 8 chars).
- ✅ Cumple `cross-repo-handoff-rules` (PR pusheado antes de cerrar).
- ✅ `vps-deploy-after-edit` ejecutado: `systemctl --user restart openclaw-dispatcher` + verificación journalctl.

## Reportar al cerrar

- Commit hash mergeado.
- Output `pytest tests/test_rick_mention.py -v`.
- Líneas relevantes de `journalctl --user -u openclaw-dispatcher` durante el smoke (sanitizadas — sin tokens).
- Output `cat ~/.local/state/umbral/delegations.jsonl | tail -3 | jq` (sanitizado).
- Confirmación de que comentarios sin `@rick` siguen procesados por flujo legado.
