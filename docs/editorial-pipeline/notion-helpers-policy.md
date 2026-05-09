# Notion Helpers Policy — Editorial Pipeline Wave 1.5

> **Status:** Draft (do-not-merge) · branch `wave1.5-integration` · 2026-05-08
> **Scope:** documentation-only decision on the structure of Notion helper
> modules under `scripts/discovery/lib/`.
> **Conflict reconciled:** review-external #7 ("potential duplication of
> Notion clients between `notion_read.py` (H2) and `notion_publicaciones.py`
> (H4)").

## 1. Live audit

| Module | LoC | Surface | HTTP? |
|---|---|---|---|
| [`scripts/discovery/lib/notion_read.py`](../../scripts/discovery/lib/notion_read.py) | 182 | `ReferenteRow` dataclass + parsers (`_plain`, `_url`, `_select_name`, `_multi_select_names`), `normalize_referente`, `fan_out_channels`, `query_data_source` | **Yes — read-only** (`POST /v1/data_sources/{id}/query` for the `👤 Referentes` data source). |
| [`scripts/discovery/lib/notion_publicaciones.py`](../../scripts/discovery/lib/notion_publicaciones.py) | 295 | Pydantic models (`Gates`, `Variants`, `Visual`, `Publicacion`) + property-value parsers (`_checkbox`, `_url`, `_select`, `_status`, `_text`, `_date_start`) | **No.** Pure parsing layer over already-fetched Notion page payloads. No HTTP. |

## 2. Decision

**Keep the per-domain split. Do NOT refactor in Wave 1.5.**

### Rationale

1. **Different domains, different schemas.** `notion_read.py` is the
   `👤 Referentes` data-source reader (S0/S1 only). `notion_publicaciones.py`
   is the typed surface over the `📰 Publicaciones` DB (S4/S7/S9/S10). The
   property names, types and value spaces do not overlap.
2. **Different I/O profiles.** Only `notion_read.py` makes HTTP calls today;
   `notion_publicaciones.py` is a pure parser. A shared "client" abstraction
   would solve a duplication that does not exist.
3. **Different writer contracts.** `notion_publicaciones.py` will gain a
   *writer* in Hilo 6 (S10 publisher) gated by the human gates
   `aprobado_contenido` / `autorizar_publicacion`. `notion_read.py` must
   remain read-only forever (Referentes is curated by David). Keeping the
   modules apart enforces this asymmetry by structure, not by convention.
4. **Test isolation.** `tests/lib/test_notion_publicaciones_models.py` and
   `tests/discovery/test_stage0_load_referentes.py` already exercise the
   two surfaces independently. A shared helper would couple the test
   suites for no benefit.

## 3. What we explicitly DO NOT do in Wave 1.5

- ❌ Extract a common `NotionClient` class. There is no shared HTTP code
  to extract today.
- ❌ Add rate-limit / retry middleware. The current `query_data_source`
  uses `httpx` defaults; if a backoff layer is needed it is added in the
  one module that does HTTP, not in a shared helper.
- ❌ Rename either module to suggest a "Notion package". Flat layout under
  `scripts/discovery/lib/` keeps imports short and ownership clear.

## 4. Reconciliation with external review (#7)

> "ChatGPT/equipo dice X" → "Verificación VPS muestra Y"

| Claim | Reality on `wave1.5-integration` |
|---|---|
| "There is duplication of Notion clients between H2 and H4." | False. Only `notion_read.py` has client code. `notion_publicaciones.py` is pure parsing — no `httpx` import, no HTTP call. |
| "Auth/rate-limit handling is duplicated." | False. Auth lives in `notion_read.query_data_source` (single `Authorization: Bearer` header). `notion_publicaciones.py` does not authenticate to anything. |

## 5. When this decision should be revisited

- When Hilo 6's S10 writer is implemented and starts issuing
  `PATCH /v1/pages/{id}` calls to `📰 Publicaciones`. At that point the
  *writer* lives in `notion_publicaciones.py` and will need its own
  auth/retry. If patterns from `notion_read.py` get copy-pasted, a small
  shared helper (`_notion_http.py` with `headers()` + `request_with_backoff()`)
  becomes justified. Until then, YAGNI.
- When a third Notion surface gets a helper. Two helpers is not enough
  duplication to refactor; three usually is.

## 6. Cross-references

- Schema audit (Publicaciones): [`docs/audits/2026-05-08-notion-publicaciones-schema-audit.md`](../audits/2026-05-08-notion-publicaciones-schema-audit.md).
- Hash contract: [`./hash-contract.md`](./hash-contract.md).
- SQLite policy: [`./sqlite-policy.md`](./sqlite-policy.md).
