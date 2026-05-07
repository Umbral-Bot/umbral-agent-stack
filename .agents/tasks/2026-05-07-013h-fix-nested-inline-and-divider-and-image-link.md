# Task 013-H — Cubrir bugs detectados por QA Comet en 5 páginas re-renderizadas

**Status:** open
**Owner:** Copilot VPS
**Branch base:** `copilot-vps/013g-markdown-annotations-and-url-canonical` (PR #329)
**Fecha:** 2026-05-07
**Bloquea:** Phase 4.4 bulk de 013-F.

---

## Contexto

QA externo (Comet, navegador real) revisó las 5 páginas re-renderizadas en 013-G y
detectó BLOCKER en #2 y #4, MAJOR en #1 y #3. Ningún OK. El reporte completo vive
en el handoff del owner; resumen de issues confirmados:

1. **Bold/italic NO recursa dentro de link labels.** `[**OpenClaw**](url)` sale como
   `**OpenClaw**` literal con link clickeable. Fix Phase A no cubrió este nesting.
2. **Headings de sección invisibles.** Autores (rojo.me, storytellingwithdata.com)
   usan `<p><strong>Título:</strong></p>` como heading visual; markdownify produce
   `**Título:**` (no `## Título:`); Phase A solo detecta heading si la línea empieza
   con `#`. Resultado: queda bold-roto sin heading.
3. **Separadores `---` quedan como texto** (a veces escapados `\---`). Falta map a
   bloque `divider`.
4. **Patrón `[![alt](src)](href)`** (image-in-link, embed típico de podcasts) sale
   markdown crudo. Falta detección + emisión de bloque `image` con caption.
5. Caracteres escapados redundantes (`\*`, `\!`, `\[`) heredados de markdownify
   escaping dentro de link labels — secundario, mitigable bajando aggressive escaping.

---

## Phase A — Inline annotations dentro de link labels

**Archivo:** `scripts/discovery/html_to_notion_blocks.py`

Refactor del parser inline de Phase 013-G:

- Cuando se matchea `[label](url)`, **el label tiene que pasar recursivamente** por
  el mismo tokenizer inline antes de emitir el span, generando spans con
  `text.link.url` poblado en cada uno.
- Caso típico:
  - Input markdown: `[**OpenClaw**](https://x)`
  - Output esperado: 1 span `{type:"text", text:{content:"OpenClaw", link:{url:"https://x"}}, annotations:{bold:true}}`
- Caso mixto:
  - Input: `[foo **bar** baz](https://x)`
  - Output: 3 spans, todos con `link.url`, el del medio con `bold:true`.

Reglas:

- Profundidad máxima recursión: 2 (label dentro de label es exotic, ignorable).
- Si la recursión falla, fallback al label como texto plano + link (comportamiento
  actual). Log warning, no abortar.
- Mismo tratamiento para `*italic*`, `` `code` ``, `~~strike~~` dentro de labels.

---

## Phase B — Heading inferred-from-bold paragraph

Comportamiento nuevo en `html_to_notion_blocks.py`:

- Antes de emitir un `paragraph`, evaluar si el bloque contiene **un único span**
  cuyo contenido es 100% bold (la línea es `**texto:**` o `**texto**` y nada más).
- Si SÍ, además el texto termina en `:` o el bloque siguiente es una lista o un
  párrafo (heurística "esto es un sub-título"), emitir `heading_3` en lugar de
  `paragraph`.
- Conservador: solo `heading_3` (no inferir h1/h2 desde bold). Los `# / ## / ###`
  reales siguen mapeando a `heading_1/2/3` como Phase 013-G.

Test cases:

- `**Qué aprenderás:**` solo en su línea → `heading_3`.
- `**Frameworks y agentes:**\n* item1\n* item2` → `heading_3` + bullets.
- `**bold inline** middle of paragraph` → sigue siendo `paragraph` con bold span.
- `**foo**` no termina en `:` y siguiente bloque no es lista → sigue siendo
  `paragraph` (NO inferir).

---

## Phase C — Divider

Cuando una línea del markdown post-markdownify es exactamente `---`, `***` o
`\---` (3+ chars repetidos del mismo tipo), emitir bloque Notion:

```json
{"object":"block","type":"divider","divider":{}}
```

NO emitir `paragraph` con texto `---`.

---

## Phase D — Image-in-link `[![alt](src)](href)`

Pattern detection antes del parser inline general:

- Regex: `\[!\[([^\]]*)\]\(([^)]+)\)\]\(([^)]+)\)`
- Si match, emitir 1 bloque `image`:
  ```json
  {
    "type":"image",
    "image":{
      "type":"external",
      "external":{"url":"<src>"},
      "caption":[{"type":"text","text":{"content":"<alt>","link":{"url":"<href>"}}}]
    }
  }
  ```
- El href va en el caption como link clickeable, conservando la semántica original
  (clic en imagen → destino externo, ej: video YouTube).
- Si emitir `image` falla (URL inválida, host no soportado por Notion external image),
  fallback: bloque `paragraph` con 1 span `[alt](href)` (sin la imagen, link vivo).

---

## Phase E — Reducir escaping agresivo de markdownify

`markdownify` por default escapa `*`, `_`, `[`, `!` dentro de texto plano. Eso
genera los `\*\*` literales que Comet vió cuando el label de un link contenía
markdown sin parsear correctamente.

Opciones:

1. Pasar `escape_asterisks=False, escape_underscores=False` al call de markdownify
   y dejar que el parser inline maneje literal vs syntax.
2. Post-procesar el markdown de markdownify quitando `\*` → `*`, `\_` → `_`,
   `\!` → `!`, `\[` → `[`, `\]` → `]` antes del tokenizer inline.

Elegir opción 1 si funciona limpio; si rompe casos que ya estaban OK, usar 2.
Documentar la decisión en el PR.

---

## Phase F — Tests

En `tests/test_html_to_notion_blocks.py` agregar al menos:

- `test_bold_inside_link_label_preserves_link_and_bold`
- `test_italic_inside_link_label_preserves_link_and_italic`
- `test_link_with_mixed_inline_in_label_produces_multi_span`
- `test_heading_inferred_from_bold_only_paragraph_ending_in_colon`
- `test_bold_inline_in_paragraph_NOT_inferred_as_heading`
- `test_three_dashes_emits_divider_block`
- `test_image_in_link_pattern_emits_image_block_with_caption_link`
- `test_escape_chars_stripped_from_link_labels`

Mantener verdes los 18 tests de Phase 013-G y los 39 de 013-F.

---

## Phase G — Re-render de las mismas 5 páginas

Idéntico a Phase E de 013-G. Reusar `scripts/discovery/rerender_pages.py`:

```bash
cd ~/umbral-agent-stack && set -a; source ~/.config/openclaw/env; set +a
source .venv/bin/activate

python -m scripts.discovery.rerender_pages --sqlite-ids 1,31,32,33,51 --commit

TS=$(date -u +%Y%m%dT%H%M%SZ)
python -m scripts.discovery.stage4_push_notion \
  --database-id b9d3d8677b1e4247bafdcb0cc6f53024 \
  --data-source-id 9d4dbf65-664f-41b4-a7f6-ce378c274761 \
  --referentes-data-source-id afc8d960-086c-4878-b562-7511dd02ff76 \
  --commit --limit 5 \
  --output reports/stage4-push-${TS}-rerender5-013h.json
```

Reportar las 5 nuevas URLs Notion en el PR para validación visual del owner.

---

## Phase H — STOP

NO ejecutar Phase 4.4 bulk de 013-F. Reportar al owner con:

1. Diff conceptual del parser inline (qué cambió respecto a 013-G).
2. Resultado de los nuevos tests.
3. URLs Notion de las 5 re-renderizadas.
4. Confirmación: "Phase 4.4 bulk NO ejecutada — pendiente go/no-go tras validación
   visual del owner (objetivo: ≥4 de 5 sin BLOCKER ni MAJOR según criterios Comet)".

---

## Quality gates

- ✅ Tests de 013-F (39) y 013-G (18) verdes.
- ✅ ≥8 tests nuevos de Phase F verdes.
- ✅ En las 5 re-renderizadas: 0 ocurrencias de `**`, `__`, `\*`, `\---`, `\!\[`,
   `[![` literales en el cuerpo (verificable con GET /blocks/children sobre las 5
   page IDs y grep al rich_text content).
- ❌ NO Phase 4.4 bulk hasta sign-off del owner.

## Reglas operativas

- Token solo en headers; nunca en logs/reports/PR body.
- Default dry-run para `rerender_pages.py`; `--commit` opt-in.
- Mismo rate-limit 350ms y backoff que stage4.
- Solo `--sqlite-ids 1,31,32,33,51` — no tocar otras páginas.
- Si Phase D (image-in-link) revela que Notion API rechaza la URL del CDN del autor
  como external image (CORS o auth), documentar el fallback y seguir; no bloquear
  el resto del PR por eso.
