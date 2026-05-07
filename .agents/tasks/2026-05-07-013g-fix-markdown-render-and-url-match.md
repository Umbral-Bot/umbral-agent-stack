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
