# Stage 10 — Publish Safety (publish_guard) — Spec

**Hilo 6 / Wave 1 / Status: DRAFT — DO NOT MERGE**
**Owner**: Hilo 6 (S10/S11)
**Depends on**: Hilo 3 (`scripts/discovery/lib/dedup.py`), Hilo 4 (`scripts/discovery/lib/gates.py`), Hilo 1 (master plan §3 — gate vocabulary)

## 1. Resumen

`publish_guard` es el único punto de control entre cualquier publisher
del pipeline editorial y un POST real al canal externo (LinkedIn primero;
futuro: X, Notion público, blog). Implementa las **6 gates** que el master
plan exige antes de publicación y **es la única función que puede emitir
ese permiso**. Todo publisher (`stage9c_linkedin_publish.py`,
`stage9d_x_publish.py` futuro, etc.) **debe** llamarla **antes** de:

1. Sanitizar payload.
2. Refrescar tokens.
3. Abrir cliente HTTP.

Esto garantiza:

* Cero publicaciones no autorizadas por David.
* Idempotencia frente a duplicados (registro post-publicación en
  `published_history`).
* Trazabilidad completa vía `ops_log.jsonl`.

## 2. Las 6 gates (orden estable de evaluación)

| # | Gate (`gates.py` field)   | Reason code on failure          | Inverted? | Source             |
|---|----------------------------|----------------------------------|-----------|--------------------|
| 1 | `aprobado_contenido`       | `aprobado_contenido_missing`     | no        | Notion checkbox    |
| 2 | `autorizar_publicacion`    | `autorizar_publicacion_missing`  | no        | Notion checkbox    |
| 3 | `gate_invalidado`          | `gate_invalidado_active`         | **sí**    | Notion checkbox    |
| 4 | `fuente_primaria_ok`       | `fuente_primaria_missing`        | no        | Notion `Fuente primaria` URL |
| 5 | `plataforma_seleccionada`  | `plataforma_no_seleccionada`     | no        | Notion `Canal` (∈ blog/linkedin/x/newsletter) |
| 6 | `no_duplicado`             | `contenido_duplicado`            | **sí**    | `published_history` SQLite |

`gate_invalidado` y `no_duplicado` son **inversos**: el primero falla
cuando está `True` (alguien marcó la propuesta como inválida); el segundo
falla cuando `dedup.is_duplicate(...)` devuelve `True`.

El orden anterior es el contrato estable usado tanto por
`gates._GATE_ORDER` como por `publish_guard.REASON_CODES`. Está cubierto
por `tests/discovery/test_publish_guard.py::test_reason_codes_constant_matches_h4_order`.

## 3. API

```python
# scripts/discovery/lib/publish_guard.py

class PublishBlockedError(Exception):
    reasons: list[str]       # subset de REASON_CODES, orden estable
    page_id: str             # id de Notion (vacío si no aplica)
    content_hash: str        # echo del hash que se intentaba publicar

def assert_can_publish(
    notion_page: dict,
    content_hash: str,
    db_conn: sqlite3.Connection,
) -> None:
    """Raise PublishBlockedError si alguna gate falla."""
```

* **Inputs**:
  * `notion_page`: el objeto crudo de `GET /v1/pages/{id}`. Si está vacío,
    la guardia bloquea por las 5 gates de Notion (fail-safe).
  * `content_hash`: sha256 producido por
    `dedup.compute_content_hash(canonical_url, title, excerpt)` (Hilo 3).
    El guardia inyecta este valor en `properties.content_hash` para que
    `gates.evaluate_gates` pueda evaluar `no_duplicado`.
  * `db_conn`: conexión SQLite abierta sobre la DB que aloja
    `published_history`.
* **Side-effects**: emite **una** línea JSON al ops_log:
  * `publish_guard.pass` si todas las gates pasan.
  * `publish_guard.block` si alguna falla. Schema:
    ```json
    {"ts": "...", "event": "publish_guard.block",
     "page_id": "...", "content_hash": "...",
     "reasons": ["aprobado_contenido_missing", ...]}
    ```
  * **Nunca** escribe en `published_history` (eso es responsabilidad del
    publisher después de un POST 201).

## 4. Flujo de bloqueo (típico)

```
publish_one(row)
  → fetch_notion_page(page_id)       # GET /v1/pages/{id}
  → compute_payload_content_hash(payload)
  → assert_can_publish(...)          # ← raises PublishBlockedError
      ↳ ops_log: "publish_guard.block" + reasons
  → log_event("stage9c.blocked", ...)
  → _notify_blocked(page_id, reasons)  # best-effort comment en Notion
  → return ("blocked", "gates_failed=[...]")
```

`main()` agrupa el resultado en el contador `blocked=` del summary y
**retorna exit-code 0** (bloquear no es un error operacional).

## 5. Flujo de éxito + idempotencia

```
assert_can_publish(...) ✓
  → ops_log: "publish_guard.pass"
publish to LinkedIn → 201 Created
  → mark_published(state_db, pid, post_urn)
  → dedup.register_published(
        db_conn, content_hash,
        f"https://www.linkedin.com/feed/update/{post_urn}/",
        "linkedin",
    )
  → log_event("stage9c.published", proposal_id, post_urn, content_hash)
```

A partir de ese momento, cualquier intento futuro de publicar el mismo
`content_hash` será detenido por la gate `no_duplicado` (verificado en
`tests/discovery/test_stage9c_idempotency.py::test_second_run_with_same_content_hash_is_blocked`).

## 6. `--dry-run` — JSON contract

```json
{
  "proposal_id": 42,
  "page_id": "abc123",
  "content_hash": "<sha256 64-char hex>",
  "would_publish": true,
  "reasons_blocked": []
}
```

* `would_publish=true` ⇔ `reasons_blocked=[]` (las 6 gates pasan).
* En modo `--dry-run`, **ninguna** llamada a `httpx.Client` debe ocurrir.
  El test `test_no_hardcoded_linkedin_post_urls` y los autouse-fail-fast
  (`monkeypatch.setattr(mod.httpx, "Client", lambda *a, **kw: pytest.fail(...))`)
  defienden esa propiedad.

## 7. ops_log — eventos

| Evento                  | Cuándo                                  | Campos                                                     |
|-------------------------|------------------------------------------|------------------------------------------------------------|
| `publish_guard.pass`    | 6 gates OK                               | `page_id`, `content_hash`, `reasons=[]`                    |
| `publish_guard.block`   | ≥1 gate falla                            | `page_id`, `content_hash`, `reasons=[...]`                 |
| `stage9c.blocked`       | publisher recibe `PublishBlockedError`   | `proposal_id`, `page_id`, `content_hash`, `reasons`         |
| `stage9c.published`     | POST 201 + register_published OK         | `proposal_id`, `post_urn`, `content_hash`                   |

Path por defecto: `~/.config/umbral/ops_log.jsonl`. Override en tests
mediante `OPS_LOG_PATH`. Errores de I/O en el writer son **silenciados**
(observabilidad nunca debe romper correctitud).

## 8. Diff resumido (stage9c)

```
scripts/discovery/stage9c_linkedin_publish.py | +157 / -15
scripts/discovery/lib/publish_guard.py        | +220 (new)
scripts/discovery/lib/__init__.py             | +1   (new)
tests/discovery/test_publish_guard.py         | +260 (new)
tests/discovery/test_stage9c_dry_run.py       | +210 (new)
tests/discovery/test_stage9c_idempotency.py   | +180 (new)
tests/discovery/test_stage9c_linkedin_publish.py | +30 / -5
tests/discovery/conftest.py                   | +180 (new)
docs/editorial-pipeline/stage10-publish-safety-spec.md | +250 (new)
docs/editorial-pipeline/stage11-observability-spec.md  | +320 (new)
reports/2026-05-08-stage10-dry-run-audit.md   | +120 (new)
```

## 9. Qué NO está cubierto (out-of-scope para Hilo 6)

* **No** se publica a LinkedIn realmente — toda la batería de tests
  bloquea `httpx.Client`. La activación se hará en Hilo 7.
* **No** se incluye un publisher para X/Twitter — sólo se garantiza que
  el guard es plataforma-agnóstico (acepta cualquier `notion_page`).
* **No** se modifica la UI de Notion — los comentarios en `_notify_blocked`
  reusan `stage7_5_post_review_comment` ya existente (best-effort).
* **No** se escribe métrica post-publish (impressions/likes) — eso es
  Hilo 8 (ver `stage11-observability-spec.md` §3).
