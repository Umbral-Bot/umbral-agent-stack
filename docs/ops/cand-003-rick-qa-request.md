Actúa como rick-qa. Esta es la validación final consolidada (Stage 6) para CAND-003.

Contexto:
CAND-003 es una candidata source-driven con tesis "Criterio antes que automatización". Ha pasado por todas las etapas previas:
- Stage 1: Fuentes y señales (6 fuentes clasificadas)
- Stage 2: Extracción y transformación (payload completo con extraction matrix, decantation, transformation formula)
- Stage 3: Borrador editorial base (Notion page creada con 143 bloques)
- Stage 4: Validación de atribución (pass_with_changes → pass after fixes)
- Stage 5: Pasada de voz (reescritura real aplicada, validada como pass)

Page ID: 34b5f443-fb5c-8167-b184-e3c6cf1f6c3f
Estado: Borrador
Gates: aprobado_contenido=false, autorizar_publicacion=false, gate_invalidado=false

Valida:
1. **Schema**: publication_id único, estado Borrador, gates false, no publication fields, no runtime activation.
2. **Sources and traceability**: fuentes clasificadas correctamente, extraction matrix con separación evidencia/inferencia/hipótesis, no source laundering.
3. **Attribution policy**: no personas citadas como autoridad pública, discovery sources solo internos, fuentes citables correctas.
4. **AEC relevance**: conexión AEC clara y concreta, no genérica.
5. **Editorial quality**: copy directo, operativo, sin slop, con voz de marca aplicada, ortografía correcta.
6. **Governance**: gates false, ready_for_publication false, no Notion write beyond draft, no Rick active.
7. **Internal disclosure**: no internal details exposed (trace IDs, model names, agent names) in public copy.

Devuelve resultado en formato YAML:

```yaml
qa_final_result:
  verdict: pass | pass_with_changes | blocked
  validation_summary:
    schema: pass | fail
    sources_and_traceability: pass | fail
    attribution_policy: pass | fail
    aec_relevance: pass | fail
    editorial_quality: pass | fail
    governance: pass | fail
    internal_disclosure: pass | fail
  ready_for_human_review: true | false
  ready_for_publication: false
  blockers: []
  required_changes: []
  recommendations: []
  residual_risks: []
  next_action: ""
```
