
---

## Resultado 2026-05-07

### Phase A — recursive inline in link labels ✅
`_parse_inline` recurses with `link=url` context (depth ≤ 2). `[**X**](url)` →
single span with `bold:true` AND `text.link.url=url`. Mismo trato para italic,
code, strike, mixed (`[foo **bar** baz](url)` → 3 link spans, middle bold).
Test: `test_bold_inside_link_label_preserves_link_and_bold` + 2 más.

### Phase B — heading_3 from bold-only paragraph ✅
Promueve a `heading_3` solo si el párrafo entero es un único bold span y (a)
termina en `:` o (b) la siguiente línea no-vacía es bullet/numbered. Conservador:
no inferir h1/h2. Tests: positivo con `:`, positivo seguido por lista, negativo
sin `:` y siguiente párrafo, negativo bold inline en medio de párrafo.

### Phase C — divider ✅
`_DIVIDER_RE = ^\s*\\?(?:-{3,}|\*{3,}|_{3,})\s*$` → bloque
`{"type":"divider","divider":{}}`. Detección a nivel de línea ANTES del parser
inline.

### Phase D — image-in-link ✅
`_IMAGE_IN_LINK_RE = ^\s*\\?\[!\[([^\]]*)\]\(([^)\s]+)\)\]\(([^)\s]+)\)\s*$` →
bloque `image` con `external.url=src` y caption con span clickeable a `href`.
No se observó rechazo por Notion en las páginas re-renderizadas.

### Phase E — markdownify escape reduction ✅ (opción 1)
Pasamos `escape_asterisks=False, escape_underscores=False` al call de
`md_convert(...)`. El parser inline maneja literal vs sintaxis vía regex
precedence + backslash unescape. No fue necesario opción 2 (post-procesado).

### Bonus — colapso de runs de 3+ asterisks/underscores
Hallazgo durante Phase G: rojo.me usa nested `<strong><b>...</b></strong>` que
produce `****X****` post-markdownify; el bold matcher dejaba el outer `**` como
literal (31 hits en page 32). Fix: pre-procesar `*{3,}`→`**` y `_{3,}`→`__`
DENTRO del parser inline. Divider está detectado a nivel de línea ANTES, así
que `***` solo en su línea NO se ve afectado. Test:
`test_quad_asterisks_collapse_to_bold`.

### Phase F — tests ✅
- 18 tests previos (013-G) → green.
- 11 tests nuevos en `TestNestedAndBlockExtensions` → green.
- Total: **29/29 green**.

### Phase G — re-render 5 páginas ✅

Run reports:
- Archive: `reports/rerender-pages-20260507T041205Z-commit.json` →
  archived_ok=5, errors=0.
- Stage4 re-push: `reports/stage4-push-20260507T041228Z-commit5.json` →
  created=4, created_no_body=1, errors=0.

URLs Notion (round 2, post-fix asterisk):

| sqlite_id | referente | canal | new notion_page_id | blocks | status |
|---:|---|---|---|---:|---|
| 1 | Cole Nussbaumer Knaflic | rss | `3595f443-fb5c-816b-9f2e-e85ae07a5b31` | 21 | created |
| 31 | Rodrigo Rojo | rss | `3595f443-fb5c-8123-ac04-c55b9effc505` | 36 | created |
| 32 | Rodrigo Rojo | rss | `3595f443-fb5c-818b-a725-c9dd5149c3e5` | 65 | created |
| 33 | Rodrigo Rojo | rss | `3595f443-fb5c-8188-9053-e621df1ebd6e` | 57 | created |
| 51 | Alex Freberg | youtube | `3595f443-fb5c-81dd-9571-e421519213ce` | 1 | created_no_body (RSSHub gap, out of scope) |

### Quality gate ✅
Nuevo script `scripts/discovery/quality_gate_grep_blocks.py` (read-only,
default off; usa `NOTION_API_KEY` solo en headers, mismo rate-limit y backoff
que stage4). Hace `GET /blocks/children` paginado y busca tokens prohibidos
(`**`, `__`, `\*`, `\---`, `\!\[`, `[![`) en `rich_text.content` y `image.caption`.

Reporte: `reports/qa-grep-20260507T041345Z.json`.

| sqlite_id | notion_page_id | blocks | hits |
|---:|---|---:|---:|
| 1 | `3595f443-fb5c-816b-9f2e-e85ae07a5b31` | 21 | **0** |
| 31 | `3595f443-fb5c-8123-ac04-c55b9effc505` | 36 | **0** |
| 32 | `3595f443-fb5c-818b-a725-c9dd5149c3e5` | 65 | **0** |
| 33 | `3595f443-fb5c-8188-9053-e621df1ebd6e` | 57 | **0** |
| 51 | `3595f443-fb5c-81dd-9571-e421519213ce` | 1 | **0** |
| **TOTAL** | | **180** | **0** |

### STOP — Phase 4.4 bulk NO ejecutada
Por hard-stop del spec, los 15 items restantes de 013-F siguen BLOQUEADOS.
Pendiente go/no-go del owner tras validación visual + Comet re-QA de las
páginas re-renderizadas (objetivo: ≥4 de 5 sin BLOCKER ni MAJOR).

### Files changed in 013-H
- `scripts/discovery/html_to_notion_blocks.py` — recursive inline, divider,
  image-in-link, heading-from-bold, escape reduction, asterisk collapse.
- `tests/test_html_to_notion_blocks.py` — +11 tests (29 total).
- `scripts/discovery/quality_gate_grep_blocks.py` — new read-only QA tool.
- `reports/rerender-pages-20260507T041205Z-commit.json` — round 2 archive.
- `reports/stage4-push-20260507T041228Z-commit5.json` — round 2 push.
- `reports/qa-grep-20260507T041345Z.json` — quality gate proof.
