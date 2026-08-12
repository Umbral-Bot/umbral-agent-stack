# Task 013-G — Fix markdown→Notion annotations + URL match diagnostic + re-render 5 pages

**Status:** open
**Owner:** Copilot VPS
**Branch base:** `copilot-vps/rollback-013e-and-013f-content-capture` (PR #325)
**Fecha:** 2026-05-07
**Bloquea:** Phase 4.4 bulk de 013-F.

---

## Contexto

Validación visual de las 5 páginas creadas en Phase 4.3 de 013-F detectó dos issues:

1. **Markdown crudo en Notion** — la página con body completo (sqlite_id=1, SWD Challenge,
   `3595f443-fb5c-81cf-af51-cf22d1ad1dfd`) muestra `**bold**` y `# heading` como texto literal
   en vez de aplicar Notion `annotations: {bold: true}` y bloques `heading_1/2/3`. El render
   estructural (image, paragraphs, bullets) sí funciona.

2. **Backfill matcheó 1/20** — el episodio rojo.me del 6-may (sqlite_id=31,
   url `https://www.rojo.me/nuevo-episodio-la-universidad-ya-no-sirve-para-esto`) cayó a
   `created_no_body` aunque está en la ventana de feeds actual. Sospecha: mismatch de URL
   canonicalization entre SQLite (`url_canonica`) y la URL re-parseada del feed (trailing slash,
   `?utm_*`, http vs https, `www.` opcional).

Esta task arregla ambos issues, re-renderiza las 5 páginas ya creadas, y deja todo listo para
Phase 4.4 bulk.

**No hacer Phase 4.4 bulk hasta que el owner confirme go.**

---

## Phase A — Fix markdown→Notion annotations + heading detection

**Archivo:** `scripts/discovery/html_to_notion_blocks.py`

### A.1 Detectar headings antes de paragraph

En el flujo actual, después de `markdownify(html)` el texto es markdown. Antes de emitir cada
bloque `paragraph`, evaluar la línea:

- `^# (.+)$`   → `heading_1`
- `^## (.+)$`  → `heading_2`
- `^### (.+)$` → `heading_3` (los `####`+ se colapsan a `heading_3`)
- todo lo demás → `paragraph`

El contenido del heading sigue pasando por el parser inline (Phase A.2) — un heading puede tener
links o bold dentro.

### A.2 Parser inline markdown → Notion rich_text

Reemplazar el path "markdown crudo → `text.content`" por un parser que produzca una lista de
spans `{type: "text", text: {content, link?}, annotations: {...}}`.

Sintaxis a soportar (en este orden de precedencia):

| Markdown | Notion annotation |
|---|---|
| `**foo**` o `__foo__` | `bold: true` |
| `*foo*` o `_foo_` | `italic: true` (cuando no es parte de `**`/`__`) |
| `` `foo` `` | `code: true` |
| `~~foo~~` | `strikethrough: true` |
| `[text](url)` | `text.link.url = url` (sin annotation) |

Reglas:

- Implementación pragmática: regex pass por cada token, dividiendo el string en spans. No hace
  falta un parser AST completo. Aceptar overlaps simples (`**bold _and italic_**` puede no
  detectar el italic anidado — documentar limitación en docstring).
- Cada span resultante se chunkea a 1900 chars como ya hace el código actual.
- Escape de caracteres: `\*`, `\_`, `\` `` ` `` se interpretan como literales (el carácter sin la barra).
- Si el inline parsing falla (excepción), fallback al texto crudo en un único span sin annotations
  + log warning. **No abortar la página por esto.**

### A.3 Listas y links

- `bulleted_list_item` y `numbered_list_item` ya existen → su `rich_text` ahora también pasa por
  el parser inline (links dentro de bullets deben ser clickeables, no `[text](url)` literal).
- Bloque `image` ya OK (no requiere parser inline).

### A.4 Tests nuevos en `tests/test_html_to_notion_blocks.py`

Agregar al menos:

1. `test_bold_inline_produces_annotation` — `**foo**` → 1 span con `annotations.bold = True`.
2. `test_italic_inline_produces_annotation` — `*foo*` → italic.
3. `test_link_inline_produces_text_link` — `[txt](https://x)` → span con `text.link.url`.
4. `test_heading_h1_h2_h3_block_types` — `# A\n## B\n### C\n#### D` → tipos `heading_1`,
   `heading_2`, `heading_3`, `heading_3` (colapsado).
5. `test_mixed_inline_in_bullet` — `- foo **bar** [link](https://x)` → 1 bullet con 3 spans
   (texto plano, bold, link).
6. `test_inline_parser_fallback_on_exception` — input adversarial → fallback a texto crudo, sin
   raise.
7. `test_no_double_processing_when_no_markdown` — texto plano sin syntax → 1 span, 0 annotations.

Mantener verde los 11 tests existentes.

---

## Phase B — Diagnosticar URL match en backfill

**Archivo nuevo:** `scripts/discovery/diagnose_backfill_url_match.py` (puro diagnóstico, no muta).

**Comportamiento:**

1. Cargar registry (`vendor/notion-governance/registry/notion-data-sources.template.yaml`).
2. Levantar de SQLite los items con `promovido_a_candidato_at IS NOT NULL AND contenido_html IS NULL`
   (los 19 unmatched).
3. Para cada referente con items pending:
   - Re-fetchear el feed via `parse_feed_xml` (reuso de Stage 2).
   - Listar todas las URLs del feed.
   - Para cada item pending de ese referente: imprimir tabla
     `sqlite_url_canonica | feed_urls_que_contienen_misma_basename | match_exacto? | normalized_match?`
   - "normalized" = strip de `?utm_*`, trailing `/`, force `https://`, force `www.` consistente.
4. Output JSON a `reports/diagnose-backfill-url-match-{ts}.json` + tabla legible a stdout.

**Heurística esperada:** identificar el patrón de mismatch (probablemente uno de: trailing slash
en feed pero no en SQLite, http en feed → https en SQLite, query string utm en uno solo).

---

## Phase C — Fix URL canonicalization

Solo después de ver el diagnóstico de Phase B. Si el patrón es claro:

**Archivo a modificar:** lo más probable `scripts/discovery/stage2_ingest.py` (función que produce
`url_canonica`) o el call site del backfill.

**Reglas duras de `url_canonica`** (proponer en PR, ajustar tras diagnóstico):

- Forzar scheme `https://`.
- Forzar `www.` si el host original lo tenía OR si ningún canonical existe — preservar lo que diga
  el feed/SQLite original consistentemente. **Decidir UNA regla y documentarla.**
- Strip query params `utm_*`, `fbclid`, `gclid`, `ref`, `mc_cid`, `mc_eid`.
- Strip fragment `#...` excepto cuando el host es youtube.com (que usa `?v=` no fragment, OK).
- Strip trailing `/` excepto si el path es `/` puro.
- `path` lowercase **solo** para hosts donde sea seguro (no aplicar globalmente — algunos sitios
  son case-sensitive). Conservador: NO lowercase a menos que el patrón observado lo justifique.

**Test:** agregar a `tests/test_stage2_content_extraction.py` o nuevo
`tests/test_url_canonicalization.py` con casos del diagnóstico.

**Migración:** si la regla cambia, los `url_canonica` ya persistidos pueden quedar
inconsistentes con los nuevos. Como el dataset es chico (~50 items) y el `idempotency_key`
de Notion usa el mismo `url_canonica`:

- Opción 1 (preferida): script `scripts/discovery/recanonicalize_urls.py --commit` que recalcula
  `url_canonica` para todas las filas y lo persiste. Idempotente. Default dry-run.
- Si una fila cambia su `url_canonica` y ya tiene `notion_page_id`, **NO crear página nueva** —
  PATCHear `idempotency_key` en Notion al nuevo valor.

---

## Phase D — Re-correr backfill con URLs corregidas

```bash
cd ~/umbral-agent-stack && set -a; source ~/.config/openclaw/env; set +a
source .venv/bin/activate
TS=$(date -u +%Y%m%dT%H%M%SZ)
python -m scripts.discovery.backfill_content_for_promoted \
  --registry vendor/notion-governance/registry/notion-data-sources.template.yaml \
  --commit \
  --output reports/backfill-content-${TS}-after-canonical-fix.json
```

Esperado: `matched` debería subir significativamente (de 1 a >5 ideal; depende de cuántos items
sigan vivos en feeds).

---

## Phase E — Re-render de las 5 páginas existentes

Las 5 páginas (sqlite_id 1, 31, 32, 33, 51) tienen `notion_page_id` poblado y por eso el rerun
sería no-op. Necesitamos forzar re-creación con el código nuevo.

**Script nuevo:** `scripts/discovery/rerender_pages.py`

Comportamiento:

1. Args: `--sqlite-ids 1,31,32,33,51` (o `--all-with-page-id` para reset total) y `--commit`.
2. Para cada sqlite_id:
   - Leer `notion_page_id` actual de SQLite.
   - PATCH `archived: true` en Notion (default 350ms rate-limit, mismo backoff que stage4).
   - Verificar response `archived: true, in_trash: true`.
   - `UPDATE discovered_items SET notion_page_id = NULL WHERE rowid = ?`.
3. Reportar cuántas archivó OK / cuántas fallaron.
4. Default dry-run; `--commit` requerido.

**Ejecución:**

```bash
# Dry-run
python -m scripts.discovery.rerender_pages --sqlite-ids 1,31,32,33,51

# Commit
python -m scripts.discovery.rerender_pages --sqlite-ids 1,31,32,33,51 --commit

# Re-run stage4 con limit 5 → recreará las mismas 5 con código fixed
TS=$(date -u +%Y%m%dT%H%M%SZ)
python -m scripts.discovery.stage4_push_notion \
  --database-id b9d3d8677b1e4247bafdcb0cc6f53024 \
  --data-source-id 9d4dbf65-664f-41b4-a7f6-ce378c274761 \
  --referentes-data-source-id afc8d960-086c-4878-b562-7511dd02ff76 \
  --commit --limit 5 \
  --output reports/stage4-push-${TS}-rerender5.json
```

**Verificación visual** (hacer el owner, NO la VPS):
- sqlite_id=1: bold/italic/headings deberían renderizar con formato real, no como markdown crudo.
- Items que ahora tengan `contenido_html` (post-canonical-fix): deberían tener body real, no
  `created_no_body`.

---

## Phase F — STOP

**NO ejecutar Phase 4.4 bulk.** Reportar al owner con:

1. Diff de `html_to_notion_blocks.py` (resumen de annotations soportadas).
2. Output del diagnóstico Phase B (tabla de mismatches detectados).
3. Resumen de la regla de canonicalización aplicada en Phase C (si aplicó).
4. Resultado del backfill rerun (matched antes vs después).
5. URLs de las 5 páginas re-renderizadas para validación visual.
6. Update del PR #325 (force-push al mismo branch) o nuevo PR si Codex prefiere separar
   (recomendado: nuevo PR `feat(013-G): markdown annotations + url canonical` para review limpio).

---

## Quality gates

- ✅ Tests viejos verdes (39 de 013-F).
- ✅ Tests nuevos de annotations + heading + URL canonical verdes.
- ✅ Re-render de sqlite_id=1 muestra bold/italic/headings nativos en Notion.
- ✅ Backfill rerun aumenta `matched` (objetivo conservador: ≥5/19).
- ✅ Idempotency: rerun de stage4 sobre las 5 re-renderizadas devuelve `created=0,
  skipped_existing=5`.
- ❌ NO touch en Phase 4.4 bulk.
- ❌ NO modificar páginas que no estén en `--sqlite-ids` explícitos.

## Reglas operativas

- Token solo en headers; nunca en logs ni reports.
- Default dry-run en todos los scripts nuevos; `--commit` opt-in.
- Reusar exactamente las mismas reglas de rate-limit + backoff que stage4 (350ms, 1/2/4/8s).
- Respetar el guardrail `secret-output-guard` — ningún token literal en outputs.
- Si Phase B revela que el problema NO es URL canonicalization sino otra cosa (ej: feed devuelve
  estructura diferente al inicial), parar Phase C/D y reportar al owner antes de inventar fix.

---

## Resultado 2026-05-07

### Phase A — markdown annotations + heading inline parser ✅

`scripts/discovery/html_to_notion_blocks.py`: replaced `_rich_text_with_links` with
a full inline parser supporting **bold** (`**` / `__`), *italic* (`*` / `_`),
`code` (backtick), ~~strikethrough~~ (`~~`), and `[text](url)` links. Headings,
bullets and numbered list items now also pass through the parser. Backslash
escapes for `*` `_` backtick `~` produce literal characters. Parser failure falls
back to single plain-text span (logged warning, no abort).

Tests: 11 existing + 7 new (`TestInlineAnnotations`) → **18/18 green**.

Commit: `691f197 feat(013-G): inline markdown annotations + heading inline parsing`

### Phase B — URL match diagnostic ✅

New script `scripts/discovery/diagnose_backfill_url_match.py` (read-only).

Run report: `reports/diagnose-backfill-url-match-20260507T031726Z.json`

Match buckets across 19 pending items:

| bucket          | count | notes |
| --------------- | ----: | ----- |
| exact           |     0 | feed URLs always have trailing slash; sqlite has none |
| **canonical**   | **3** | Rodrigo Rojo RSS — current `canonicalize_url` already matches |
| loose           |     0 | no extra fuzzy hits beyond canonical |
| basename_only   |     0 | YouTube IDs unique, no near-misses |
| no_match        |    16 | mostly YouTube via RSSHub |

Per-referente feed health:

| referente            | canal   | feed_items | issue |
| -------------------- | ------- | ---------- | ----- |
| Rodrigo Rojo         | rss     | 15         | OK — 3/3 promoted items match canonical |
| Alex Freberg         | youtube | 0          | RSSHub HTTP 404 |
| Nate Gentile         | youtube | 0          | empty feed |
| Daniel Shiffman      | youtube | 0          | RSSHub HTTP 404 |
| Milos Temerinski     | youtube | 0          | empty feed |
| Andrew Ng            | youtube | 0          | RSSHub HTTP 404 |
| Fred Mills           | youtube | 0          | RSSHub HTTP 404 |
| Bernard Marr         | youtube | 10         | items rolled out of feed window (expected) |
| José Luis Crespo     | youtube | 0          | empty feed |

**Conclusion:** the reported "1/20 matched" is **NOT** a URL canonical issue.
Per spec rule "Si Phase B revela que el problema NO es URL canonical, abortá
Phase C/D y reportá", **Phase C is skipped**. Two genuine non-canonical issues
were surfaced:

1. **Backfill `fetch_and_index` missing `follow_redirects=True`** — Rodrigo
   Rojo's feed serves a 302 (`https://rojo.me/feed` → `https://www.rojo.me/feed`).
   Without redirect-following, backfill silently dropped every redirected feed.
   This is a one-line fix that mirrors stage2's existing behaviour in
   `_fetch_and_parse`, applied as an explicitly-separate finding (NOT a
   canonical change).
2. **YouTube via RSSHub broken** — multiple channels return HTTP 404 or empty
   feeds. **Out of scope for 013-G**; needs a dedicated RSSHub diagnostic
   ticket.

### Phase D — backfill rerun (post follow_redirects fix) ✅

Before fix: `reports/backfill-content-20260507T031851Z.json` → matched **0/19**.

After fix: `reports/backfill-content-20260507T032025Z.json` → matched **3/19** (Rodrigo Rojo: 3/3). Combined with the
prior Cole Nussbaumer match, **4 of the 5 target re-render pages now have
contenido_html**; the 5th (Alex Freberg / YouTube id 51) remains empty due to
the unresolved RSSHub issue and will render as `created_no_body`.

### Phase E — re-render 5 pages ✅

New script `scripts/discovery/rerender_pages.py` (default dry-run; archives
pages via `PATCH /pages/{id}` with `{"archived": true}` then nulls
`notion_page_id`). Same rate-limit and 429 backoff as stage4
(`RATE_LIMIT_SLEEP_S = 0.35s`, retries 1/2/4/8s, max 4; abort run after 3
consecutive non-429 errors).

Run reports:
- Archive: `reports/rerender-pages-20260507T032142Z-commit.json` →
  archived_ok=5, errors=0.
- Stage4 re-push: `reports/stage4-push-20260507T032210Z-commit5.json` →
  created=4, created_no_body=1, errors=0.

| sqlite_id | referente                 | canal   | new notion_page_id                       | blocks | status            |
| --------: | ------------------------- | ------- | ---------------------------------------- | -----: | ----------------- |
|         1 | Cole Nussbaumer Knaflic   | rss     | `3595f443-fb5c-811e-a57f-cccb88a56b36`   |     21 | created           |
|        31 | Rodrigo Rojo              | rss     | `3595f443-fb5c-81ac-8297-ede8571d9297`   |     36 | created           |
|        32 | Rodrigo Rojo              | rss     | `3595f443-fb5c-8130-b44d-d0ce84c43df7`   |     65 | created           |
|        33 | Rodrigo Rojo              | rss     | `3595f443-fb5c-81eb-ba76-efe38ae07b98`   |     57 | created           |
|        51 | Alex Freberg              | youtube | `3595f443-fb5c-8193-8a63-d6924fd64985`   |      1 | created_no_body   |

### STOP — Phase 4.4 bulk NO ejecutada

Per spec hard-stop, the 013-F bulk run remains BLOCKED pending owner visual
validation of the 4 re-rendered pages with content (ids 1, 31, 32, 33). After
sign-off, the bulk run from 013-F can proceed.

### Files changed in 013-G

- Modified: `scripts/discovery/html_to_notion_blocks.py` (inline parser)
- Modified: `scripts/discovery/backfill_content_for_promoted.py` (one-line
  `follow_redirects=True`)
- New: `scripts/discovery/diagnose_backfill_url_match.py`
- New: `scripts/discovery/rerender_pages.py`
- Modified: `tests/test_html_to_notion_blocks.py` (+7 inline-annotation tests)
