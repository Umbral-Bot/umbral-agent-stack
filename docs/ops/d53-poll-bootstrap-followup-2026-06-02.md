# D5.3 follow-up — poll bootstrap (2026-06-02)

## Veredictos runtime

| Paso | Veredicto |
|------|-----------|
| Soak | `D53_GRANOLA_SOAK_DEGRADED` |
| Diagnóstico poller | `D53_POLLER_DIAG_READY` |
| Fix código (5c) | **`D53_FIX_ALREADY_IN_MAIN`** |

## Hallazgo Cursor 5c (repo `main` @ post-`7a4ffb04`)

- El bug P0 documentado en board §2026-05-07-032b (`if not bootstrap:` descartaba resultados) **ya no está** en `worker/notion_client.py`.
- Fix histórico: PR #361 (`fcd0c69f` / `8d6036db`). Regresiones cubiertas en `tests/test_notion_poll_bootstrap.py` y `tests/test_poll_comments_cursor.py`.
- `pytest` (poll suite): **11 passed** (2026-06-02, Windows `.venv`).

## Interpretación logs VPS (`bootstrap=True`, `cursor_used=False`)

Comportamiento **esperado** cuando:

1. Redis tiene `notion:poll:cursor:<page_id> == __TAIL__` → se limpia cursor y entra tail-seek bootstrap (`cursor_used=False`, `bootstrap=True`).
2. Primera poll de una página sin cursor guardado.

**No** implica por sí solo que el bug 032b siga activo. La clave global `notion:poll:cursor` **no se usa** (ADR-010); solo cursores per-page.

## Gap real (operativo, no código)

| Hallazgo diag | Acción |
|---------------|--------|
| Poller pid desde May 24, sin `notion-poller.service` | **PROMPT 5e** — restart controlado tras autorización David |
| `ops_log` Granola sin eventos Jun 01–02 | Observar; no confundir con `notion.poll_comments` |
| Worker posible código viejo en memoria | Incluir `systemctl --user restart umbral-worker` en **5e** |

## Secuencia

1. ~~5c PR~~ — **omitir** (fix ya en `main`).
2. ~~5d merge~~ — **omitir** (no hay PR).
3. **5e** Copilot-VPS — `autorizo reiniciar notion-poller y worker G-D0` + `git pull` + verificar logs.

## Evidencia VPS

- `~/.coord-ag-evidence/D5.3/poller-diagnostic-202606021409.log`
- `~/.coord-ag-evidence/D5.3/granola-soak-*.log`
