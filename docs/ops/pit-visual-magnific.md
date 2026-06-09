# PIT — Generación visual con Magnific (4:3)

- **Status:** v1 (PIT-1 spec) — 2026-06-09.
- **Decisión canónica:** `aspect_ratio: "4:3"` es el **default Magnific de Umbral** para mockups y hero del prototipo PIT — alineado con editorial LinkedIn y blog hero editorial ([`umbral-bim-magnific-visual-style-v1.md`](umbral-bim-magnific-visual-style-v1.md)).
- **Contrato:** campo `visual_generation` del pit_spec ([schema](../schemas/pit-spec-v1.schema.json)).

---

## 1. Campo `visual_generation` en pit_spec

```yaml
visual_generation:
  enabled: true          # default false — el torneo puede correr sin visuales
  provider: magnific     # único provider v1
  aspect_ratio: "4:3"   # DEFAULT canónico Umbral; otro ratio solo si David lo pide explícito
  style_ref: null        # opcional — referencia de estilo (umbral-bim-magnific-visual-style-v1)
```

El validador (`scripts/pit/pit_spec_validate.py`) aplica el default `4:3` cuando el campo se omite; ratios permitidos: `4:3 | 16:9 | 9:16 | 4:5 | 1:1`.

## 2. Gate de generación (cuándo)

Un visual Magnific solo puede pedirse cuando la tarjeta de la lane está en columna **Prototype** del kanban, **o** cuando la hipótesis de la iteración ya está validada (`hypothesis.validated: true` en el kpi_pack anterior).

Nunca en `Research`/`Hypothesis`: el visual ilustra un prototipo que existe, no reemplaza la validación. Genera evidencia, no humo.

## 3. Broker (quién)

- Las lanes **no** llaman a Magnific directo: piden el visual a **Rick (broker)** con `{lane_id, iteración, concepto, aspect_ratio, style_ref}`.
- Rick valida el gate de columna, ejecuta la generación y devuelve la URL del asset.
- Esto concentra gasto, credenciales y rate limits en un solo punto (mismo patrón broker del roadmap [`copilot-cli-autonomy-vision-roadmap.md`](../copilot-cli-autonomy-vision-roadmap.md)).

## 4. Dónde quedan los assets (sin autopublicación)

- **Sin autopublicación**: ningún asset PIT se publica a LinkedIn/blog/web por el torneo. PIT genera material interno de prototipo.
- Las URLs se registran en `kpi_pack.visual_assets[]` (`{url, provider: magnific, aspect_ratio, style_ref}`) y/o en el `prototype-meta` de la iteración.
- Si un visual de torneo quisiera reutilizarse editorialmente después, pasa por el pipeline editorial normal con sus gates humanos — fuera del scope PIT.

## 5. Resumen operativo

| Pregunta | Respuesta |
|---|---|
| ¿Ratio default? | **4:3** (canónico Umbral: editorial LinkedIn, blog hero, PIT) |
| ¿Quién genera? | Rick broker — lanes nunca directo |
| ¿Cuándo? | columna Prototype o hipótesis validada |
| ¿Dónde queda? | `kpi_pack.visual_assets` / prototype-meta del vault |
| ¿Se publica? | No. Sin autopublicación; reuso editorial = pipeline editorial aparte |
