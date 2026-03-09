# Scoring Schema

## 1. Normalized item schema
Usar este set de campos por cada item capturado.

| Field | Required | Notes |
|---|---|---|
| `source_name` | yes | `gartner`, `mckinsey`, `every`, `ruben-substack` |
| `source_url` | yes | home o feed principal usado para descubrir el item |
| `item_title` | yes | titulo fiel a la fuente |
| `item_url` | yes | URL directa del item |
| `published_at` | yes | fecha conocida o estimada claramente marcada |
| `fetched_at` | yes | fecha de captura |
| `format` | yes | article, report, essay, newsletter, podcast, video, note |
| `access_status` | yes | `public`, `subscriber`, `licensed`, `inaccessible` |
| `theme` | yes | tema editorial resumido en 2-6 palabras |
| `source_claim` | yes | 1-3 bullets con la tesis o hallazgo central |
| `editorial_interpretation` | yes | 1-2 bullets con la lectura util para David |
| `why_now` | yes | por que este item merece atencion ahora |
| `narrative_fit_notes` | yes | ajuste con tesis o worldview de David |
| `proposal_fit_notes` | yes | ajuste con oferta, posicionamiento o CTA |
| `audience_fit_notes` | yes | ajuste con pains, maturity y jobs-to-be-done |
| `novelty_notes` | yes | que aporta frente a piezas recientes parecidas |
| `evidence_notes` | yes | credibilidad, datos, ejemplos o limites |
| `derivative_angles` | yes | hasta 3 angulos derivables |
| `risks_or_gaps` | yes | acceso, ambiguedad, rights, datos debiles o duplicacion |
| `score_100` | yes | resultado final 0-100 |
| `confidence` | yes | `high`, `medium`, `low` |
| `decision_tag` | yes | `shortlist`, `monitor`, `discard` |

## 2. Editorial baseline inputs
Antes de puntuar, fijar estas tres mini-fichas.

### Narrative
- core thesis
- repeated motifs
- contrarian or differentiated angle

### Proposal
- what David sells or advances
- implied transformation or promise
- CTA or business relevance

### Audience
- who the content is for
- current sophistication level
- pains, jobs and buying triggers

Si faltan datos, inferirlos y marcarlos como `assumption`.

## 3. Scoring rubric
Puntuar cada dimension de 0 a 5.

| Dimension | Weight | What 5 means |
|---|---:|---|
| `narrative_fit` | 25 | refuerza o avanza claramente la tesis de David |
| `proposal_fit` | 20 | conecta con la oferta o posicionamiento sin forzar |
| `audience_fit` | 20 | importa de verdad al ICP y a su nivel de madurez |
| `freshness` | 10 | muy reciente o muy oportuna para la conversacion actual |
| `authority_evidence` | 10 | fuente fuerte, bien atribuida, con evidencia util |
| `novelty` | 10 | anade una idea, dato o framing menos obvio |
| `derivative_potential` | 5 | se presta bien a un take, hook o traduccion accionable |

Calcular asi:

`score_100 = narrative_fit*5 + proposal_fit*4 + audience_fit*4 + freshness*2 + authority_evidence*2 + novelty*2 + derivative_potential*1`

## 4. Penalties and gating rules
Aplicar estas reglas antes de shortlist final.

- Si el contenido es `inaccessible` y solo se conoce el titulo o teaser, no colocarlo por encima de items accesibles comparables.
- Si el item duplica otra pieza del mismo lote, marcar `monitor` o `discard`.
- Si el ajuste con audiencia es bajo aunque la fuente sea prestigiosa, no compensar inflando autoridad.
- Si la atribucion es debil, bajar `confidence` y aplicar una penalizacion editorial de 5-10 puntos.
- Si el item requiere supuestos fuertes para conectar con la propuesta, tratarlo como `monitor` salvo que la novedad sea excepcional.

## 5. Confidence guide
- `high`: se leyo el item o un extracto suficiente, con tesis y fecha claras.
- `medium`: se leyo un resumen fiable o material parcial con alguna laguna.
- `low`: solo hay metadata, teaser o acceso incompleto.

## 6. Decision tags
- `shortlist`: candidato para decision humana inmediata.
- `monitor`: interesante, pero no listo para priorizar ahora.
- `discard`: baja alineacion, duplicado, demasiado viejo o poco util.
