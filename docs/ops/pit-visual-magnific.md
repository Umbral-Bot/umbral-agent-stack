# PIT — Generación visual con Magnific (4:3)

- **Status:** v2 (PIT-DEV FASE 6) — 2026-07-03. Regla dura global: **Magnific
  PROHIBIDO para toda lane/juez/subagente efímero en TODOS los modos**. Solo
  Rick, fuera de las lanes, post-judge, si el torneo lo pide en spec.
- **Decisión canónica:** `aspect_ratio: "4:3"` es el **default Magnific de Umbral** para el deck ejecutivo del torneo — alineado con editorial LinkedIn y blog hero editorial ([`umbral-bim-magnific-visual-style-v1.md`](umbral-bim-magnific-visual-style-v1.md)).
- **Contrato:** campo `visual_generation` del pit_spec v1 ([schema](../schemas/pit-spec-v1.schema.json)). El spec v3 (PIT-DEV) NO tiene `visual_generation`: el visual del deck es decisión de Rick post-judge, fuera del spec de lanes.

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

**Regla dura (FASE 6, 2026-07-03):** ningún agente efímero (lane, juez,
security, traceability) puede **solicitar ni invocar** Magnific, en ningún
modo. Pedirlo ⇒ `lane_blocked`. Los gates de columna de v1 quedan obsoletos
como vía de lane: no hay vía de lane.

Magnific solo se usa **post-judge**, por Rick, para el deck ejecutivo del
torneo (flujo PIT-TG-DRIVE) — y solo si el spec v1 lo habilitó
(`visual_generation.enabled: true`). Genera evidencia visual del cierre, no
material de iteración.

## 3. Broker (quién)

- **Solo Rick**, fuera de las lanes. Las lanes ya no piden visuales — ni
  directo ni vía broker.
- Rick decide post-judge si el deck lleva visuales, ejecuta la generación y
  registra las URLs en los deliverables del torneo.
- Esto concentra gasto, credenciales y rate limits en un solo punto (mismo
  patrón broker del roadmap [`copilot-cli-autonomy-vision-roadmap.md`](../copilot-cli-autonomy-vision-roadmap.md)).
- Defensa en profundidad: el registro de efímeros del runner añade
  `tools.deny: ["magnific", "magnific*"]` a cada agente efímero
  (`scripts/pit/pit_tournament_run.py::register_ephemeral_agents`).

## 4. Dónde quedan los assets (sin autopublicación)

- **Sin autopublicación**: ningún asset PIT se publica a LinkedIn/blog/web por el torneo. PIT genera material interno de prototipo.
- Las URLs se registran en `kpi_pack.visual_assets[]` (`{url, provider: magnific, aspect_ratio, style_ref}`) y/o en el `prototype-meta` de la iteración.
- Si un visual de torneo quisiera reutilizarse editorialmente después, pasa por el pipeline editorial normal con sus gates humanos — fuera del scope PIT.

## 5. Resumen operativo

| Pregunta | Respuesta |
|---|---|
| ¿Ratio default? | **4:3** (canónico Umbral: editorial LinkedIn, blog hero, PIT) |
| ¿Quién genera? | SOLO Rick — lanes/jueces/subagentes JAMÁS (ni pedir; regla FASE 6) |
| ¿Cuándo? | post-judge, para el deck ejecutivo, si el spec lo habilitó |
| ¿Dónde queda? | deliverables del torneo (deck) — nunca material de iteración de lane |
| ¿Se publica? | No. Sin autopublicación; reuso editorial = pipeline editorial aparte |
