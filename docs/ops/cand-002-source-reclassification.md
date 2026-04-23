# CAND-002 — Source Reclassification per Attribution Policy

> **Date**: 2026-04-23
> **Policy applied**: `docs/ops/editorial-source-attribution-policy.md`
> **Purpose**: Reclassify all sources used in CAND-002 per David's attribution rule.

## Source Classification

```yaml
source_classification:
  - source_name: "The B1M"
    source_url: "https://www.theb1m.com"
    type: original_article
    public_citable: true
    internal_trace_only: false
    reason: "Original construction media with own journalism and reporting. Citable as organization."
    original_source_url: ""
    original_source_name: ""
    public_citation: "The B1M (as organization, not Fred Mills by name)"

  - source_name: "DeepLearning.AI / The Batch"
    source_url: "https://www.deeplearning.ai/the-batch"
    type: analysis_source
    public_citable: true
    internal_trace_only: false
    reason: "Newsletter producing original editorial analysis on AI trends. Issue #349 on AI-native teams is Ng's own synthesis/observation, not a summary of external research. Citable as organization."
    original_source_url: ""
    original_source_name: ""
    public_citation: "DeepLearning.AI or The Batch (as organization, not Andrew Ng by name)"

  - source_name: "Marc Vidal"
    source_url: "https://www.marcvidal.net"
    type: discovery_source
    public_citable: false
    internal_trace_only: true
    reason: "Referente who analyzes and interprets external sources. His articles cite OECD, McKinsey, Robert Solow, WEF, EU AI Regulation. The primary sources behind his claims are those organizations. Vidal is the discovery path, not the authority."
    original_source_url: ""
    original_source_name: "See primary sources below"
    public_citation: "DO NOT cite in public copy"

  - source_name: "Aelion.io / Ivan Gomez Rodriguez"
    source_url: "https://aelion.io"
    type: contextual_reference
    public_citable: false
    internal_trace_only: true
    reason: "Landing page manifesto without specific data, articles, or verifiable claims. Represents a sector mindset (ROI-first in AEC) but does not substantiate factual claims."
    original_source_url: ""
    original_source_name: ""
    public_citation: "DO NOT cite in public copy"
```

## Primary Sources Identified Behind Discovery Sources

### Behind Marc Vidal's articles:

| Vidal Article | Primary Source Found | Organization | Claim Supported |
|--------------|---------------------|-------------|-----------------|
| La paradoja de la productividad | Robert Solow's productivity paradox (1987) | — (established economic concept) | Technology does not automatically translate into productivity |
| El algoritmo como jefe supremo | OECD Algorithmic Management report (2025) | OECD | 79% of European companies use algorithmic tools |
| El algoritmo como jefe supremo | McKinsey Global Institute | McKinsey | Up to 30% of US labor hours could be automated by 2030 |
| El algoritmo como jefe supremo | World Economic Forum (2025) | WEF | 92M jobs displaced, 170M created before 2030 |
| El algoritmo como jefe supremo | EU AI Regulation (Feb 2025) | European Union | Banned emotional recognition in workplaces |
| Cuando los imperios olvidan innovar | Mario Draghi report (European Commission) | European Commission | Europe's competitiveness challenges |
| Cuando los imperios olvidan innovar | Ifo Institute, Bruegel, ITIF | Think tanks | Mid-tech trap, innovation gaps |

### Behind The Batch issues:

| Batch Issue | Content Type | Notes |
|------------|-------------|-------|
| #349: AI-native teams | Ng's own editorial analysis | No external research cited for the AI-native teams observation |
| #348: Future of SE | Mixed editorial + citations | Cites Citadel Securities data on SE job postings |
| #346: Resistance to AI | Editorial analysis | General trend observation |
| #342: Agentic AI uncertainty | Editorial analysis | General market observation |

### The B1M:

| B1M Article | Content Type | Notes |
|------------|-------------|-------|
| Data centre construction boom | Original journalism | B1M's own reporting on construction trends |
| Can The LINE be built? | Original journalism | B1M's own analysis of NEOM feasibility |

## Impact on CAND-002 Copy

### What changes in public copy:

1. **Remove**: "Andrew Ng viene mostrando que..." → Replace with reference to the concept (AI-native teams, organizational transformation)
2. **Remove**: "Marc Vidal insiste en una tension..." → Replace with the underlying concept (Solow productivity paradox, or general observation about technology vs productivity gap)
3. **Remove**: "Ivan Gomez lo resume con..." → Remove entirely or replace with general AEC sector sentiment
4. **Keep concept**: The thesis remains the same — the barrier is organizational readiness, not tool availability
5. **Keep structure**: Pattern synthesis from multiple signals
6. **Add if needed**: Reference to Solow paradox, OECD data, or McKinsey findings as primary evidence (in traceability, not necessarily in copy body)

### What stays in internal traceability:

- Marc Vidal as discovery source for productivity paradox signal
- Ivan Gomez / Aelion as discovery source for AEC ROI-first mindset
- Andrew Ng as discovery source for AI-native teams concept
- Fred Mills / The B1M as discovery source for construction investment patterns
- Full extraction matrix with discovery_source attribution

## Corrected Copy — LinkedIn

```
Hay una idea que se repite en distintas conversaciones sobre IA: que el problema es acceder a la herramienta correcta.

No estoy seguro de que ese sea el cuello de botella principal en AEC.

Al comparar senales recientes sobre equipos AI-native, productividad y adopcion tecnologica en construccion, aparece un patron comun: la brecha entre capacidad disponible y preparacion real para usarla.

No es un problema nuevo. La paradoja de la productividad lleva decadas mostrando que mas tecnologia no garantiza mas retorno. Y en AEC, donde el filtro practico siempre ha sido si la tecnologia genera valor desde el primer dia, esa tension se siente con fuerza.

Si juntas esas senales, aparece una lectura incomoda:

la barrera no parece ser la falta de IA, sino la falta de preparacion organizacional para usarla bien.

Eso incluye roles, criterio, revision, trazabilidad y procesos capaces de absorber una nueva velocidad de trabajo.

Por eso muchas organizaciones pueden incorporar mas automatizacion y aun asi no capturar mas valor.

No porque la tecnologia falle.
Sino porque el sistema de trabajo sigue disenado para otra etapa.

En AEC, quiza la pregunta ya no es quien esta probando IA.
La pregunta es quien esta redisenando su forma de operar para que esa IA realmente produzca impacto.
```

## Corrected Copy — X

```
En AEC, el cuello de botella de la IA puede no ser la herramienta.

Puede ser la organizacion.

La paradoja de la productividad sigue vigente: mas tecnologia no garantiza mas retorno. Si el sector exige valor temprano y los equipos siguen operando igual, la captura de valor depende menos del hype y mas de roles, criterio, revision y procesos.
```

## Changes Summary

| Element | Before | After |
|---------|--------|-------|
| "Andrew Ng viene mostrando que..." | Named person as authority | "Al comparar senales recientes sobre equipos AI-native..." |
| "Marc Vidal insiste en una tension..." | Named person as authority | "La paradoja de la productividad lleva decadas mostrando..." |
| "Ivan Gomez lo resume con un filtro..." | Named person as authority | "donde el filtro practico siempre ha sido si la tecnologia genera valor desde el primer dia" |
| Copy X references | Referenced AI-native teams, productivity, sector value | Referenced productivity paradox, value from day one, organizational change |
| Source attribution | Persons as authorities | Concepts and evidence patterns |
