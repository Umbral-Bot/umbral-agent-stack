# Stage 7 — Visual Brief Spec (Wave 1 design)

> **Status:** DESIGN ONLY. Define el contrato `VisualBrief` que el dispatcher (Stage 6) entrega al generador de imagen (Stage 8 ya existente). NO se modifica `stage8_image_generator.py` en Wave 1.

## Origen

Un `VisualBrief` deriva de la tupla **`(angle, variant)`**:

- `angle` = salida de Stage 5 (mock en Wave 1).
- `variant` = resultado del dispatcher Stage 6 para una plataforma concreta.

El brief es **por variante**, no por candidato. Una entrada de carrusel produce N briefs (uno por slide). Una entrada de video produce 1 brief para thumbnail + briefs por escena (Wave 2).

## Contrato Pydantic

Definido en [`scripts/discovery/lib/variants.py`](../../scripts/discovery/lib/variants.py):

```python
class VisualBrief(BaseModel):
    concept: str              # qué tiene que comunicar la imagen
    composition: str          # encuadre, foreground/background
    style: str                # fotorealista, ilustrativo, técnico, etc.
    mood: str                 # tono emocional / atmósfera
    text_overlay: str | None  # texto opcional sobre la imagen
    negative_prompts: list[str]  # qué NO mostrar (>=1 elemento)
    aspect_ratio: Literal["1:1", "16:9", "9:16", "4:5"]
    target_platform: Literal["linkedin", "x", "blog", "newsletter", "carousel", "video"]
```

Validators:

- `negative_prompts` no vacío (mínimo 1 entrada).
- `aspect_ratio` ∈ `{"1:1", "16:9", "9:16", "4:5"}`.
- `target_platform` ∈ las 6 plataformas soportadas.

## Cuándo se requiere `Visual asset URL`

| Plataforma | Visual obligatorio | Aspect ratio default | Notas |
|---|---|---|---|
| LinkedIn | **sí** | `1:1` o `4:5` | hero image; runtime hoy vía Stage 8 |
| X | opcional | `16:9` | recomendado para hooks fuertes |
| Blog (hero) | **sí** | `16:9` | hero del artículo |
| Newsletter | opcional | `16:9` o `4:5` | header de email |
| Carrusel | **obligatorio por slide** | `4:5` (LinkedIn) / `1:1` (IG) | 1 brief por slide |
| Video | **sí — thumbnail** | `9:16` (vertical) | thumbnail + briefs por escena en Wave 2 |

## Mapeo a Notion (sin escrituras Wave 1)

- `Visual asset URL` (Hilo 4 confirma nombre exacto) → URL de la imagen final generada por Stage 8.
- Carrusel/Video: **PROPUESTO** un campo agregador `Visual assets` (galería) — no crear hasta confirmación con Hilo 4.

## Handoff Stage 6 → Stage 8

Wave 1 deja únicamente el contrato. Wave 2 conectará:

```
stage6_generate_variants.py
    └── (variant, angle) ──► build_visual_brief() ──► VisualBrief
                                                          │
                                                          ▼
                                                stage8_image_generator
                                                          │
                                                          ▼
                                                 Visual asset URL
```

`build_visual_brief(angle, variant) -> VisualBrief` queda sin implementar en Wave 1 (es responsabilidad de Wave 2 una vez se acuerden los prompts por plataforma).

## NO-go Wave 1

- NO ejecutar Stage 8 desde el dispatcher.
- NO escribir URLs de imagen a Notion.
- NO modificar `scripts/discovery/stage8_image_generator.py`.
