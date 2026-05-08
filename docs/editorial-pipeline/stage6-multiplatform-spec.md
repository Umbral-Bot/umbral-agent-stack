# Stage 6 — Multi-platform Variants Spec (Wave 1 design)

> **Status:** DESIGN ONLY. Multi-plataforma hoy = **schema + dispatcher esqueleto, NO runtime**. Solo LinkedIn (Stage 7.5) está activo en runtime.

## Stage 7.5 — FROZEN

| Aspect | State |
|---|---|
| Branch diff vs `main` for `scripts/discovery/stage7_5_*` | **must be 0** |
| Status | **FROZEN** for Wave 1 |
| What it does | Generates LinkedIn copy with Voice v3 retry loop, validates, writes to Notion `📰 Publicaciones.Copy LinkedIn`, sets `Estado=Revisión pendiente`. |
| Owner | Hilo D Voice v3 (PR #390 merged). |

### Criterios de descongelamiento

Stage 7.5 vuelve a ser editable cuando:

1. Se requiera generar variantes para una plataforma distinta de LinkedIn y la abstracción no pueda colocarse fuera (en `lib/variants.py` o `stage6_generate_variants.py`).
2. Aparezca un ajuste de voz / hard-reject que no sea resoluble vía cambio de prompt en `prompts/stage7_5/`.
3. Cambien los campos de Notion `📰 Publicaciones` consumidos por el writer (Hilo 4).

Mientras ninguna de las tres se cumpla, todo cambio de comportamiento multi-plataforma se hace en archivos nuevos (`lib/variants.py`, `stage6_generate_variants.py`, `stage7_*` específico de plataforma). Stage 7.5 no se toca.

---

## Contrato de variantes por plataforma

| Plataforma | Límites | Estructura | Notion field | Status Wave 1 |
|---|---|---|---|---|
| **LinkedIn** | (delegado a Stage 7.5) | post largo, voice v3 | `Copy LinkedIn` | **runtime ✅** (Stage 7.5) |
| **X** | ≤280 chars/tweet · 1–5 tweets · ≤2 hashtags · hook explícito en tweet 1 | single tweet o thread | `Copy X` | stub Wave 2 |
| **Blog** | 800–1500 palabras · `seo_title` ≤60 · `meta_description` ≤160 | H2/H3 + CTA final | `Copy Blog` | stub Wave 2 |
| **Newsletter** | 400–700 palabras · `subject_line` ≤60 · `preheader` ≤90 | email-first, CTA final | `Copy Newsletter` | stub Wave 2 |
| **Carrusel** (LinkedIn / Instagram) | 6–10 slides | cada slide: `title` + `bullet` (1–3 líneas) + `visual_hint` | `Copy Carrusel` (**PROPUESTO**) | stub Wave 2 |
| **Video corto** (Reels/TikTok/Shorts) | 30–60s · hook 0–3s · 4–6 escenas | `hook`, `storyboard[Scene]`, `on_screen_text` | `Copy Video` (**PROPUESTO**) | stub Wave 2 |

Modelos Pydantic en [`scripts/discovery/lib/variants.py`](../../scripts/discovery/lib/variants.py): `VariantBase` + `LinkedInVariant`, `XVariant`, `BlogVariant`, `NewsletterVariant`, `CarouselVariant`, `VideoVariant`, `Slide`, `Scene`.

`VariantBase` campos comunes: `platform`, `content`, `char_count`, `word_count`, `hashtags: list[str]`, `cta: str | None`, `generated_at`, `model_used`, `voice_match_score ∈ [0,1]`.

---

## Mapeo a Notion `📰 Publicaciones`

**Sin escrituras Notion en Wave 1.** Mapeo declarativo solamente:

| Variante | Campo Notion | Estado del campo |
|---|---|---|
| LinkedIn | `Copy LinkedIn` | existe (runtime Stage 7.5) |
| X | `Copy X` | existente o por confirmar con Hilo 4 |
| Blog | `Copy Blog` | existente o por confirmar con Hilo 4 |
| Newsletter | `Copy Newsletter` | existente o por confirmar con Hilo 4 |
| Carrusel | `Copy Carrusel` | **PROPUESTO — no crear hasta confirmación** |
| Video | `Copy Video` | **PROPUESTO — no crear hasta confirmación** |

> Hilo 4 (`docs/editorial-pipeline/notion-schema.md`) es la fuente de verdad de qué campos existen hoy. Esta tabla declara intención; no la realidad runtime de la base.

---

## Dispatcher Stage 6 — esqueleto

[`scripts/discovery/stage6_generate_variants.py`](../../scripts/discovery/stage6_generate_variants.py)

```
generate_variants(candidate, angle, platforms) -> {platform: VariantBase}
```

- `linkedin` → delega a Stage 7.5 (importa el módulo como prueba de integración; Wave 1 NO ejecuta el writer real porque haría escrituras a Notion).
- `x` / `blog` / `newsletter` / `carousel` / `video` → stub Pydantic-válido marcado `model_used="stub-wave2"` + log `INFO stub Wave 2 platform=<X>`.
- Plataforma desconocida → `ValueError("unknown platform(s): [...]")`.

**CLI:**
```
python scripts/discovery/stage6_generate_variants.py \
    --candidate-id SYN-AECO-001 \
    --platforms linkedin,x,blog \
    --dry-run
```

Lee fixtures sintéticos (no usar `CAND-002/003/004`) desde `tests/discovery/fixtures/synthetic_candidates.json`.

---

## Dependencias declaradas

- **Stage 5** (ranking + ángulos): hoy mock vía `mock_angle` en fixtures sintéticos. Wave 2 reemplaza por salida real de Stage 5.
- **Hilo 4 — `notion-schema.md`**: confirmar nombres exactos de columnas `Copy X` / `Copy Blog` / `Copy Newsletter` antes de escribir runtime.
- **Hilo 6 — `S10`**: contrato de variantes consumido por el agendador / publisher.

## NO-go Wave 1

- NO publicar en ninguna plataforma.
- NO crear campos Notion nuevos.
- NO tocar `scripts/discovery/stage7_5_*`.
- NO usar `CAND-002/003/004` como gold fixture.
