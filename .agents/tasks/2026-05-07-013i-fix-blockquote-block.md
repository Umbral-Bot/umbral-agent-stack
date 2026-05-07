# Task 013-I — Fix markdown blockquote → Notion `quote` block

**Owner**: Copilot VPS
**Stacks on**: 013-H (PR #332) → branch `copilot-vps/013h-nested-inline-divider-image-link`
**Blocks**: Phase 4.4 bulk de 013-F (los 15 items restantes).

## Contexto

Comet QA round 2 sobre las 5 páginas re-renderizadas de 013-H confirmó:

- ✅ 3 BLOCKERs de round 1 RESUELTOS (bold-en-link literal x2, image-in-link crudo).
- ✅ Todos los MAJORs de round 1 RESUELTOS (separadores, headings, asteriscos cuádruples, escape sequences).
- ❌ **Bug nuevo único**: markdown blockquote `> ...` queda como párrafo plano con `>` literal al inicio en vez de bloque `quote` nativo de Notion.

Ocurrencias detectadas:
- **Página 3** (sqlite_id=32): 1× — `> Explorar lo inexplorado para detonar la curiosidad…`
- **Página 4** (sqlite_id=33): 3× — `> 💡 Tip: en GPT…`, `> No tienes que tener el modelo más caro…`, `> Cada 2 o 3 semanas, vuelve a probar…`

Las 4 son citas destacadas en el HTML original del autor (`<blockquote>...</blockquote>`); markdownify las renderiza como `> texto` y nuestro parser de bloques las trata como párrafo.

## Scope (estricto)

Phases A-D solamente. NO refactorizar el parser. NO tocar phases A-G de 013-H. NO ejecutar Phase 4.4 bulk de 013-F.

## Phase A — Detección de blockquote

En el block walker de `scripts/discovery/html_to_notion_blocks.py`, agregar detección a nivel de línea ANTES del paragraph fallback y DESPUÉS de divider/image-in-link:

- Regex: `^\s*>\s?(.*)$`
- Si la línea matchea, capturar el contenido (grupo 1) y agruparlo con líneas consecutivas que también matcheen (multi-line blockquote → un solo bloque `quote` con saltos preservados como separadores `\n` o como spans separados, lo que sea más limpio).
- Una línea en blanco o una línea que NO empieza con `>` corta el bloque.
- Emitir bloque Notion:
  ```python
  {"type": "quote", "quote": {"rich_text": _parse_inline(content)}}
  ```
- El `_parse_inline` resultante mantiene bold/italic/code/link recursivos heredados de 013-H (importante: una blockquote PUEDE contener `[**bold link**](url)`).

### Edge cases obligatorios
1. `> ` con espacio → contenido sin el espacio.
2. `>` sin espacio → contenido vacío después del `>` (válido, párrafo vacío en quote).
3. Múltiples `> ` consecutivos → un solo bloque quote, líneas concatenadas con `\n` (Notion soporta `\n` en rich_text content).
4. `> >` (nested blockquote) → fuera de scope, tratar como blockquote simple con `> texto` literal en el contenido (no romper).
5. Blockquote con `**bold**` o `[link](url)` adentro → annotations preservadas vía `_parse_inline`.
6. Línea que empieza con `>` pero es parte de un code block fenced (` ``` `) → NO matchear (respetar el fence). Si el parser actual no maneja code fences, OK ignorar este caso por ahora — documentarlo en el PR.

## Phase B — Tests

Mínimo 5 tests nuevos en `tests/test_html_to_notion_blocks.py` dentro de una nueva clase `TestBlockquote`:

1. `test_single_line_blockquote_emits_quote_block`
2. `test_multi_line_blockquote_groups_into_one_quote_block`
3. `test_blockquote_with_bold_inline_preserves_annotations`
4. `test_blockquote_with_link_preserves_link`
5. `test_paragraph_with_gt_in_middle_NOT_treated_as_quote` (negativo: solo aplica si `>` está al inicio de línea).

Mantener verdes los **29 tests previos** (18 de 013-G + 11 de 013-H). Total esperado: **34/34 green** en `tests/test_html_to_notion_blocks.py`.

## Phase C — Re-render mismas 5 páginas

Reusar `scripts/discovery/rerender_pages.py --sqlite-ids 1,31,32,33,51 --commit`.
Reusar `scripts/discovery/stage4_push_notion.py ... --limit 5 --commit`.

Reportar nuevas page IDs en el PR.

## Phase D — Quality gate ampliado

Reusar `scripts/discovery/quality_gate_grep_blocks.py` con tokens prohibidos AMPLIADOS:

- Mantener: `**`, `__`, `\*`, `\---`, `\!\[`, `[![`
- **Agregar**: `> ` (`> ` al inicio de un `rich_text.content` de tipo `paragraph` específicamente).

Modificar el script (mismo branch) para detectar el patrón nuevo: si un `paragraph.rich_text[0].text.content` empieza con `> ` → hit. NO falsear-positivear sobre `quote` blocks (su contenido legítimamente puede arrancar con texto que contenga `>`).

Quality gate: **0 hits sobre las 5 páginas nuevas, total ≥150 bloques scaneados.**

## Phase E — STOP

Reportar:
- 5 nuevas page IDs Notion.
- Salida del quality gate.
- Confirmación literal: "Phase 4.4 bulk de 013-F NO ejecutada — pendiente go/no-go del owner".

## Reglas duras

- Token solo en headers.
- Default dry-run en rerender + quality gate.
- Rate-limit 350ms + backoff 1/2/4/8s.
- Solo `--sqlite-ids 1,31,32,33,51`.
- NO ejecutar Phase 4.4 bulk de 013-F.
- Branch nueva sobre 013-H: `copilot-vps/013i-blockquote-block`.
- PR base = `copilot-vps/013h-nested-inline-divider-image-link` (stacked).

## Aceptación

- Tests 34/34 verdes.
- Quality gate 0 hits con tokens ampliados.
- Página 3 visualmente: la cita "Explorar lo inexplorado…" renderiza como bloque quote nativo de Notion.
- Página 4 visualmente: las 3 citas (Tip GPT, invitación Cristian, invitación Rodrigo) renderizan como bloques quote nativos.
- PR abierto con base = #332.
