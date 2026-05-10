# Notion Schema — `📰 Publicaciones`

**Wave 1 / Hilo 4** · `wave1-h4-notion-schema-gates`
**Status:** draft (do-not-merge)
**Source of truth:** Live Notion DB `e6817ec4-698a-4f0f-bbc8-fedcf4e52472`
**Audited:** 2026-05-08 via `mcp_notion_notion-fetch`
**Audit detail:** [docs/audits/2026-05-08-notion-publicaciones-schema-audit.md](../audits/2026-05-08-notion-publicaciones-schema-audit.md)

> **Read-only contract.** This document describes the live schema, the gates
> contract S9→S10, and the typed Pydantic surface in
> [scripts/discovery/lib/notion_publicaciones.py](../../scripts/discovery/lib/notion_publicaciones.py).
> No writer is implemented here. Stage 10 (Hilo 6) is the only writer.

## 1. Quick facts

| Item | Value |
|---|---|
| DB title | `📰 Publicaciones` |
| DB ID | `e6817ec4-698a-4f0f-bbc8-fedcf4e52472` |
| Data source ID | `dc833f1f-07d9-49d0-82ec-fdfad1c808c4` |
| Parent page | `Sistema Editorial Rick` |
| Property count (live) | 45 |
| Master plan §3 fields covered | **16 / 16 — all present** |
| Idempotency key proposal | **NOT NEEDED — `idempotency_key` already exists** |

## 2. Live schema — full property list

Each row = one Notion property. `Author` codes:

- `H` — David / human (manual edit in Notion UI)
- `S9` — Stage 9 writer (LinkedIn draft / OAuth / publish)
- `S7` — Stage 7 / 7.5 writer (copy / proposal pack)
- `S4` — Stage 4 push to Notion
- `S10` — Stage 10 publisher (Hilo 6, not yet implemented)
- `SYS` — Notion-managed (system / read-only)

| # | Campo (Notion) | Tipo | Opciones / Default | Required | Author | Notes |
|---|---|---|---|---|---|---|
| 1 | `Título` | `title` | — | yes | H, S4 | Public-facing title. |
| 2 | `publication_id` | `text` | — | recommended | S4 | Stable system ID (UUID/slug). |
| 3 | `Canal` | `select` | `blog`, `linkedin`, `x`, `newsletter` | yes for publish | H, S4 | Target channel for this variant. |
| 4 | `canal_publicado` | `select` | `blog`, `linkedin`, `x`, `newsletter` | post-publish | S10 | Set after publish_success only. |
| 5 | `Tipo de contenido` | `select` | `linkedin_post`, `blog_post`, `x_post`, `newsletter`, `carousel`, `visual_asset`, `thread` | yes | H, S4 | — |
| 6 | `Etapa audiencia` | `select` | `awareness`, `consideration`, `trust`, `conversion`, **`retention`** | no | H | `retention` extra vs local YAML schema. |
| 7 | `Prioridad` | `select` | `alta`, `media`, `baja` | no | H | Not in local YAML schema (extra). |
| 8 | `Estado` | `status` | `Idea`, `Borrador`, `Revisión pendiente`, `Aprobado`, `Autorizado`, `Publicando`, `Publicado`, `Descartado` | yes | H + S7/S10 | Pipeline state machine. |
| 9 | **`aprobado_contenido`** | `checkbox` | default `false` | **yes (gate)** | **H only** | Gate 1. Never written by agents. |
| 10 | **`autorizar_publicacion`** | `checkbox` | default `false` | **yes (gate)** | **H only** | Gate 2. Never written by agents. |
| 11 | **`gate_invalidado`** | `checkbox` | default `false` | yes | H + SYS-auto | Auto-set by dedup / source-down detection. |
| 12 | `Creado por sistema` | `checkbox` | default `false` | no | S4 | Marks system-created records. |
| 13 | `visual_hitl_required` | `checkbox` | default `false` | no | S7, H | True for people / brand visuals. |
| 14 | **`content_hash`** | `text` | — | yes for publish | S7 | SHA-256 truncated 16 hex. |
| 15 | **`idempotency_key`** | `text` | — | yes for publish | S10 | Derived from canal + content_hash + page_id. **Already exists in live DB.** |
| 16 | **`trace_id`** | `text` | — | recommended | S4/S7/S10 | OpsLogger correlation. |
| 17 | `platform_post_id` | `text` | — | post-publish | S10 | Filled after publish_success. |
| 18 | `publication_url` | `url` | — | post-publish | S10 | Canonical URL. |
| 19 | **`published_url`** | `url` | — | post-publish | S10 | Final platform URL. |
| 20 | `published_at` | `date` | — | post-publish | S10 | Confirmed publish time. |
| 21 | `Fecha publicación` | `date` | — | no | H | Planned publish date (human input). |
| 22 | `publish_error` | `text` | — | error path | S10 | Human-readable error. |
| 23 | `error_kind` | `select` | `timeout`, `auth`, `quota`, `upstream`, `data`, `config`, `validation`, `unknown` | error path | S10 | Categorized error. |
| 24 | **`Fuente primaria`** | `url` | — | yes | H, S4 | Primary verifiable source. |
| 25 | **`Fuente referente`** | `url` | — | no | H, S4 | Discovery signal only — never primary. |
| 26 | `Fuentes confiables` | `relation` | → DB `2b45f443-fb5c-81f5-83eb-000b5cb372f1` | no | H, S4 | Trusted-sources DB. |
| 27 | `Resumen fuente` | `text` | — | no | S4 | Brief source summary. |
| 28 | `Responsable revisión` | `person` (limit 1) | — | no | H | Reviewer assignment. |
| 29 | `Comentarios revisión` | `text` | — | no | H | David's review notes. |
| 30 | `Premisa` | `text` | — | no | H, S7 | Editorial premise. |
| 31 | `Claim principal` | `text` | — | no | H, S7 | Main claim. |
| 32 | **`Ángulo editorial`** | `text` | — | no | H, S7 | Umbral / David point of view. |
| 33 | `Notas` | `text` | — | no | H | Internal notes. |
| 34 | **`Copy LinkedIn`** | `text` | — | no | S7 | Per-channel variant. |
| 35 | **`Copy Blog`** | `text` | — | no | S7 | Per-channel variant. |
| 36 | **`Copy Newsletter`** | `text` | — | no | S7 | Per-channel variant. |
| 37 | **`Copy X`** | `text` | — | no | S7 | Per-channel variant. |
| 38 | **`Visual brief`** | `text` | — | no | S7/S8 | Asset spec. |
| 39 | **`Visual asset URL`** | `url` | — | no | S8 | Generated asset URL. |
| 40 | `Repo reference` | `url` | — | no | H, S4 | Optional PR / commit / runbook link. |
| 41 | `Proyecto` | `text` | — | no | H | Pending: convert to relation when projects DB stabilises. |
| 42 | `Publicación padre` | `relation` (self) | → same DB | no | S7 | Variants → original blog post. |
| 43 | `Última revisión humana` | `date` | — | no | H | Manual review timestamp. |
| 44 | `Creado por` | `created_by` | — | yes (auto) | SYS | Notion-managed. |
| 45 | `Última edición` | `last_edited_time` | — | yes (auto) | SYS | Notion-managed. |

## 3. Reconciliation — master plan §3 vs live Notion

| Campo (master plan §3) | Declarado en plan | Observado en Notion | Divergencia |
|---|---|---|---|
| `aprobado_contenido` | checkbox, gate humano 1 | checkbox | none |
| `autorizar_publicacion` | checkbox, gate humano 2 | checkbox | none |
| `gate_invalidado` | checkbox, auto-invalidación | checkbox | none |
| `Estado` | status / state machine | status (8 valores) | none |
| `Fuente primaria` | url | url | none |
| `Fuente referente` | url | url | none |
| `content_hash` | text, idempotencia | text | none |
| `idempotency_key` | "if not exists, propose" | **EXISTS as text** | **No proposal needed.** |
| `published_url` | url, post-publish | url | none |
| `trace_id` | text, OpsLogger correlation | text | none |
| `Copy LinkedIn` | text variant | text | none |
| `Copy Blog` | text variant | text | none |
| `Copy Newsletter` | text variant | text | none |
| `Copy X` | text variant | text | none |
| `Visual brief` | text | text | none |
| `Visual asset URL` | url | url | none |
| `Ángulo editorial` | text | text | none |

**Verdict:** all 16 master-plan fields are present and typed correctly. No
schema-shaping work required for Stage 10.

### Extras observed in live Notion (not in master plan §3)

- `Prioridad` (`alta` / `media` / `baja`) — operational triage signal.
- `canal_publicado` — distinct from `Canal` (planned vs actual).
- `error_kind` + `publish_error` — failure categorization (used by S10).
- `Comentarios revisión`, `Responsable revisión`, `Última revisión humana` —
  human-review surface.
- `Repo reference`, `Resumen fuente`, `Premisa`, `Claim principal`,
  `Publicación padre`, `Creado por sistema` — editorial / lineage metadata.
- `Etapa audiencia` extra option `retention` (local YAML lists 4, Notion lists 5).

## 4. Contrato gates S9→S10

Stage 10 (`stage10_*`, Hilo 6) **must** evaluate the following 6 gates,
in order, before any platform publish call. Failure of **any** gate aborts
the run.

1. **`aprobado_contenido` == true** — David approved the content for the channel.
2. **`autorizar_publicacion` == true** — David authorized the publish action.
3. **`gate_invalidado` == false** — no auto-invalidation pending re-review.
4. **`Fuente primaria` non-empty** — primary verifiable source exists.
5. **`Canal` ∈ {blog, linkedin, x, newsletter}** — supported platform selected.
6. **`content_hash` non-empty AND not duplicate** — dedup check via
   `lib.dedup.is_duplicate(content_hash)` returns `False`.

### 4.1 Failure behavior

- **Stage 10 aborts immediately.** No partial publish, no retry, no `--force`.
- **Structured log:** OpsLogger event `stage10.publish.blocked` with
  `{trace_id, page_id, reasons: [<reason_codes>]}`.
- **No automatic retry.** Re-run only after the underlying condition
  changes (David re-approves, dedup index resolves, source URL filled, etc.).
- **Optional Notion comment:** S10 *may* leave a single comment on the page
  describing the blocking reasons, **but** must NOT modify any property,
  must NOT toggle `Estado`, must NOT touch the gate checkboxes.
- **Final reject** (gates fail after reasonable wait or in dry-run):
  exit code `2`. No state mutation in Notion.

### 4.2 Authorship matrix

| Gate | David humano | Agente (S7/S9/S10) | Sistema (auto) |
|---|---|---|---|
| `aprobado_contenido` | ✅ exclusive writer | ❌ never | ❌ never |
| `autorizar_publicacion` | ✅ exclusive writer | ❌ never | ❌ never |
| `gate_invalidado` | ✅ may set/clear | ❌ never set true outside auto-invalidation | ✅ auto-set on dedup hit / source-down |
| `Fuente primaria` (gate 4 input) | ✅ writes | ✅ S4 may pre-fill | ❌ |
| `Canal` (gate 5 input) | ✅ writes | ✅ S4 may pre-fill | ❌ |
| `content_hash` (gate 6 input) | ❌ | ✅ S7 writes from canonical copy | ❌ |

**Hard rule:** Stage 9 and Stage 10 **must never** write `aprobado_contenido`
or `autorizar_publicacion`. Auditable via `grep` over `notion-update-page`
calls in new code — see acceptance criteria (§ 8 of master plan).

### 4.3 Auto-invalidation logic for `gate_invalidado`

The system sets `gate_invalidado = true` (no Notion write yet — only the
in-memory contract) when **any** of:

- **Duplicate detected.** `dedup_check(content_hash) == True` while
  `aprobado_contenido` was already `true` at a previous tick.
- **Source down.** Primary source URL fails an HTTP HEAD check
  (`source_status == down`) — to be implemented in `lib/source_check.py`
  (out of scope for this Hilo).
- **Human comment after approval.** Notion-poller logic (existing) flags
  any David comment landing after `aprobado_contenido` flipped true.

In all three cases, S10 must abort even if `aprobado_contenido` and
`autorizar_publicacion` are still `true` in Notion. The
`gate_invalidado_active` reason wins.

## 5. API — `scripts/discovery/lib/gates.py`

Pure module. **Zero HTTP, zero Notion writes.**

```python
from scripts.discovery.lib.gates import (
    GatesStatus,
    evaluate_gates,
    can_publish,
)

# Caller (Stage 10) is responsible for fetching the page dict and supplying
# a dedup callable.
gates = evaluate_gates(notion_page_dict, dedup_check=is_duplicate)
allowed, reasons = can_publish(gates)
if not allowed:
    log_blocked(reasons)        # never raises
    return EXIT_BLOCKED          # no Notion mutation
```

### Reason codes (stable order)

```
aprobado_contenido_missing
autorizar_publicacion_missing
gate_invalidado_active
fuente_primaria_missing
plataforma_no_seleccionada
contenido_duplicado
```

### Safe-by-default invariants

- `GatesStatus()` defaults all fields to `False` → `can_publish` returns
  `(False, [...])` for an empty input. **A gate is never `True` by omission.**
- `evaluate_gates` accepts both Notion API shape (`{"properties": {...}}`)
  and flat dicts.
- If `dedup_check` raises, the result is treated as `is_duplicate=True`
  (publish blocked). Dedup outages must never silently approve.
- Missing `content_hash` → `no_duplicado=False` (blocking). Dedup is
  not even invoked in this case (defensive).

## 6. Read-only models — `scripts/discovery/lib/notion_publicaciones.py`

Pydantic v2 models mirroring the live schema. **Read-only by contract — no
writer implemented in this module.**

- `Publicacion.from_notion(page_dict) -> Publicacion`
- Sub-models: `Gates`, `Variants`, `Visual`
- Missing fields → safe defaults (gates default `False`, never `True`).
- `extra="forbid"` on all sub-models — unknown fields raise `ValidationError`.
- Gate checkboxes use `pydantic.StrictBool` so malformed payloads (`int`,
  `str`, etc.) raise `ValidationError`, never silent coercion.

## 7. Out of scope (this Hilo)

- Stage 10 implementation (Hilo 6).
- Dedup index implementation (`lib/dedup.py`, Hilo 3).
- Source-status checker (`lib/source_check.py`).
- Notion writes of any kind.
- Schema migrations / property creation.
- Hub / técnica subpage / dashboard pages (Hilo 1 stub topics 1, 2, 5).
  This Hilo focuses on the DB schema only; subpages remain in the Hilo 1
  follow-up backlog.
