# Umbral BIM — Estilo visual Magnific v1

- **Status:** v1 — 2026-06-09. Creado en PIT-1 para anclar la decisión canónica de aspect ratio (el doc no existía en `main`; las referencias previas vivían fuera del repo).
- **Scope:** estilo de generación visual con Magnific para superficies Umbral BIM: editorial LinkedIn, blog hero editorial y torneos PIT.

---

## 1. Aspect ratio canónico: 4:3

**Decisión David (2026-06-09):** el aspect ratio Magnific canónico de Umbral es **`4:3`** en:

| Superficie | Ratio | Antes |
|---|---|---|
| Editorial LinkedIn (hero del post) | **4:3** | 1:1 / 4:5 (deprecado para Magnific) |
| Blog hero editorial (`umbralbim.io/noticias`) | **4:3** | 16:9 (deprecado para Magnific) |
| PIT — mockups/hero de prototipo | **4:3** (default del spec) | — (nuevo) |

Cualquier doc o código que aún declare `1:1` como default LinkedIn/Magnific está desactualizado y debe corregirse a 4:3. Estado del código en este repo:

- `scripts/discovery/lib/variants.py` — `VisualBrief.aspect_ratio` acepta `4:3` y la spec Stage 7 lo marca default para LinkedIn/blog ([stage7-visual-brief-spec.md](../editorial-pipeline/stage7-visual-brief-spec.md)).
- `docs/schemas/pit-spec-v1.schema.json` — `visual_generation.aspect_ratio` default `4:3`.

Ratios no-4:3 siguen disponibles para casos explícitos (ej. `9:16` thumbnail video, `16:9` X): la regla es **default 4:3 salvo pedido explícito de David o requerimiento duro de plataforma**.

## 2. PIT usa 4:3

Cross-ref: los torneos de producto (PIT) heredan este estilo —
`visual_generation.aspect_ratio` default `"4:3"`, generación vía Rick broker
con gate de columna Prototype, sin autopublicación. Detalle operativo en
[`pit-visual-magnific.md`](pit-visual-magnific.md).

## 3. Lineamientos de estilo (v1 mínimo)

Hasta tener el style guide completo (pendiente de curación David), reglas vigentes:

- **Default editorial:** ilustración isométrica, deliberadamente no fotorealista; no recrear una obra ni una oficina técnica y no introducir cascos o monitores fotorealistas.
- **Sin personas ni rostros**, sin logos/lockups ni marcas de software identificables.
- **Sin texto ni letras incrustadas** generados por el modelo (el copy va aparte; overlay solo vía `text_overlay` controlado).
- **Paleta por defecto:** turquesa/cian/menta sobre navy-carbón. Un brief explícito puede indicar otra paleta y tiene precedencia.
- **`style_ref`:** los specs (editorial `VisualBrief`, PIT `visual_generation.style_ref`) pueden apuntar a una referencia de estilo concreta; si es null, aplica este doc.

## 4. Gobernanza

- La generación editorial sigue el pipeline editorial con gates humanos (ADR-007/008/010); la generación PIT sigue [`pit-visual-magnific.md`](pit-visual-magnific.md). En ambos, **nada se autopublica**.
- Cambios a este doc = PR + revisión David (es la fuente del default visual).
