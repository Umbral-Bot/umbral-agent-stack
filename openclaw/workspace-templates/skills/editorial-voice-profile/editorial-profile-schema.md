# Editorial profile schema

Usar este documento como referencia cuando se necesite una plantilla mas detallada o una estructura editable de largo plazo.

## Principios de modelado

- modelar decisiones editables, no impresiones vagas
- separar evidencia, inferencia y preferencia humana
- mantener la diferencia entre rasgos globales y reglas por canal
- permitir versionado simple y actualizaciones incrementales
- registrar cobertura real de fuentes antes de fijar reglas duras de voz

## Plantilla recomendada

```yaml
profile_version: "v1"
owner: "David"
status: "draft | validated | evolving"
last_updated: "YYYY-MM-DD"
source_coverage:
  sufficiency: "sufficient | partial | insufficient"
  sources_used:
    own_materials:
      - source: "notion page, notion data source, pasted text, doc"
        channel: "linkedin | newsletter | video | x | web | email | other"
        completeness: "full | fragment | summary"
        notes: "why it matters"
    references:
      - source: "creator or publication"
        completeness: "full | fragment | summary"
        notes: "pattern worth studying, not copying"
  gaps:
    - "missing channel, missing period, missing piece type, etc."
editorial_north_star:
  editorial_promise: "what readers should reliably get"
  audience_primary: "who this is mainly for"
  audience_secondary: "adjacent audience"
  desired_effect: "what should change after consuming the piece"
  belief_shift: "idea the content wants to move"
narrative:
  central_thesis: "core story or worldview"
  recurring_tension:
    - "main tension"
  antagonists_or_false_shortcuts:
    - "what the content pushes against"
  promised_transformation:
    - "what improves for the audience"
  framing_preferences:
    do_more_of:
      - "angles to prefer"
    do_less_of:
      - "angles to avoid"
  confidence: "high | medium | low"
  evidence_notes:
    - "short observation"
tone:
  base_tone:
    - "e.g. lucid"
    - "e.g. demanding"
  allowed_ranges:
    - "how far the tone can move"
  avoid_ranges:
    - "tones that break the voice"
  relationship_to_audience: "peer | guide | operator | teacher | critic | mixed"
  confidence: "high | medium | low"
  evidence_notes:
    - "short observation"
style:
  sentence_rhythm: "short | mixed | extended"
  vocabulary_profile:
    preferred:
      - "preferred lexical traits"
    avoid:
      - "generic or off-brand wording"
  structure_preferences:
    openings:
      - "preferred opening moves"
    development:
      - "preferred middle moves"
    endings:
      - "preferred closing moves"
  rhetorical_devices:
    use:
      - "contrast, concrete example, question, etc."
    limit:
      - "devices to keep rare"
  technical_density: "low | medium | high"
  example_strategy: "what kinds of examples to use"
  confidence: "high | medium | low"
  evidence_notes:
    - "short observation"
communication_strategy:
  trust_builders:
    - "how credibility is earned"
  value_before_ask:
    - "what is delivered before any cta"
  cta_logic:
    purpose: "reply | save | subscribe | book call | click | share | other"
    style: "direct | conversational | invitational | analytical"
    frequency: "low | medium | high"
  content_architecture:
    - "pillar or pattern"
  confidence: "high | medium | low"
  evidence_notes:
    - "short observation"
channel_rules:
  linkedin:
    opening_rule: "..."
    body_rule: "..."
    ending_rule: "..."
    cta_rule: "..."
    avoid: ["..."]
  newsletter:
    opening_rule: "..."
    body_rule: "..."
    ending_rule: "..."
    cta_rule: "..."
    avoid: ["..."]
  short_video:
    hook_rule: "..."
    body_rule: "..."
    close_rule: "..."
    avoid: ["..."]
anti_patterns:
  - "error that makes the voice generic or distorted"
editing_preferences:
  always_keep:
    - "non negotiable rule"
  test_next:
    - "hypothesis to validate in future pieces"
open_questions:
  - "question for David"
change_log:
  - date: "YYYY-MM-DD"
    field: "tone.base_tone"
    previous: "..."
    updated: "..."
    reason: "explicit feedback or new evidence"
```

## Campos editables por david

Tratar como prioritarios para edicion humana:

- `editorial_north_star.editorial_promise`
- `editorial_north_star.desired_effect`
- `narrative.central_thesis`
- `narrative.recurring_tension`
- `narrative.framing_preferences`
- `tone.base_tone`
- `tone.allowed_ranges`
- `tone.avoid_ranges`
- `style.vocabulary_profile`
- `style.structure_preferences`
- `communication_strategy.cta_logic`
- `channel_rules.*`
- `anti_patterns`
- `editing_preferences.always_keep`
- `editing_preferences.test_next`

## Diferencias operativas entre capas

### Narrativa
Responder a: que historia se cuenta una y otra vez, que conflicto ordena el contenido y que cambio promete.

### Tono
Responder a: desde que energia emocional y relacion se habla.

### Estilo
Responder a: como suenan las frases y como se construye el texto en la pagina o en pantalla.

### Estrategia comunicativa
Responder a: para quien es, que valor se entrega, como se construye confianza y cuando se pide accion.

### Reglas por canal
Responder a: como cambia la ejecucion cuando el soporte cambia.

## Anti-patrones del perfil

- usar el esquema como checklist burocratica y no como sistema de decisiones
- escribir campos que no se puedan convertir en instrucciones de redaccion
- dejar `channel_rules` vacio aunque el corpus sea multicanal
- describir referentes como objetivo de imitacion
- no registrar cambios despues del feedback humano
- congelar reglas duras cuando la cobertura de fuentes es parcial

## Uso del perfil en redaccion

Antes de redactar, convertir el perfil en un mini brief:

1. idea central
2. tension o creencia a mover
3. tono activo para esta pieza
4. 2 o 3 movimientos de estilo
5. cta permitido para este canal
6. anti-patron principal a vigilar

No intentar activar todo el perfil a la vez. Elegir lo que sirve para la pieza concreta.
