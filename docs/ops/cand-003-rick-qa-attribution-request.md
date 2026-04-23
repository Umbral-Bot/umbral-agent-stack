Actúa como rick-qa. Esta es una validación de atribución para CAND-003.

Contexto:
CAND-003 es la segunda candidata source-driven. Tesis: "Criterio antes que automatización". La política de atribución fue aplicada desde el inicio del borrador (lección de CAND-002).

Fuentes clasificadas:
- CITABLES: DeepLearning.AI / The Batch (analysis_source, issues #340 y #343), OECD (primary_source, 79% algorítmica), McKinsey Global Institute (primary_source, 30% automatización), AVERI (primary_source, framework auditoría IA)
- DISCOVERY (solo interno): Marc Vidal (discovery_source, cita OECD/McKinsey/UE)
- CONTEXTUAL (solo interno): Aelion.io / Iván Gómez (contextual_reference, manifesto sin datos)

Copy LinkedIn:
"En AEC hay cada vez más herramientas de IA disponibles. Pero antes de incorporarlas, hay una pregunta que muchos equipos no se hacen: ¿tenemos criterio operativo explícito para lo que ya hacemos?

Si una organización no tiene documentado qué constituye una revisión válida de un modelo BIM, qué dispara una escalación en coordinación, o qué criterio define que un entregable es suficiente, la IA no va a resolver eso. Va a ejecutar más rápido un proceso que nadie definió bien.

No es un problema nuevo. A nivel global, reportes recientes muestran que la mayoría de empresas europeas ya usan herramientas algorítmicas de gestión. Pero los estándares para auditar esas herramientas recién se están proponiendo. Las plataformas más avanzadas de agentes de IA asignan permisos y guardarraíles, pero la supervisión humana sigue siendo implícita.

Si trasladamos eso a construcción: los equipos están incorporando automatización sin haber formalizado sus criterios de trabajo. Revisiones que dependen de quién las hace, no de qué criterio aplican. Coordinación que funciona por costumbre, no por protocolo.

Automatizar eso no mejora el proceso. Lo acelera con ambigüedad incluida.

Antes de escalar con IA, quizá la pregunta operativa es: ¿mi equipo tiene criterio explícito para revisión, aceptación, escalación y coordinación? Si la respuesta es no, la herramienta no es el problema."

Copy X:
"En AEC, la IA puede automatizar tareas. Pero si tu equipo no tiene criterio explícito para revisión, escalación y coordinación, lo que automatizas es la ambigüedad.

79% de empresas europeas ya usan herramientas algorítmicas de gestión. Los estándares para auditarlas recién se están proponiendo. Antes de más herramientas: más criterio."

Premisa: "En AEC, automatizar sin criterio operativo explícito no acelera: amplifica la ambigüedad. Antes de escalar con IA, hay que definir qué constituye una revisión válida, qué dispara una escalación y qué hace que la coordinación sea suficiente."

Page ID: 34b5f443-fb5c-8167-b184-e3c6cf1f6c3f
Estado: Borrador
Gates: aprobado_contenido=false, autorizar_publicacion=false, gate_invalidado=false

Valida específicamente:
1. Que no se citan personas/referentes como fuentes públicas cuando no son fuente original.
2. Que las fuentes citables son correctas (The Batch como analysis_source, OECD/McKinsey/AVERI como primary_source).
3. Que los discovery sources quedan solo como trazabilidad interna.
4. Que no se introduce source laundering.
5. Que la tesis sigue sustentada.
6. Que la conexión AEC sigue clara.
7. Que el copy mantiene calidad editorial.
8. Que gates siguen false y ready_for_publication=false.

Devuelve resultado en formato YAML:

```yaml
qa_attribution_result:
  verdict: pass | pass_with_changes | blocked
  attribution_validation:
    no_person_as_public_authority: true | false
    citable_sources_correct: true | false
    discovery_sources_internal_only: true | false
    no_source_laundering: true | false
    thesis_still_supported: true | false
    aec_connection_clear: true | false
    editorial_quality_maintained: true | false
    notes: ""
  ready_for_human_review: true | false
  ready_for_publication: false
  blockers: []
  required_changes: []
  recommendations: []
  validation_summary:
    schema: pass | fail
    sources_and_traceability: pass | fail
    attribution_policy: pass | fail
    aec_relevance: pass | fail
    editorial_quality: pass | fail
    governance: pass | fail
    internal_disclosure: pass | fail
  residual_risks: []
  next_action: ""
```
