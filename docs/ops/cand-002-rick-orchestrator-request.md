Actua como rick-orchestrator simulando explicitamente rick-editorial.

Objetivo: Generar el payload CAND-002 — primera candidata editorial source-driven, basada en fuentes reales seleccionadas por David desde la DB Referentes de Notion.

Reglas:
- No escribas en Notion.
- No publiques.
- No marques gates humanos.
- No actives Rick.
- No inventes fuentes. Usa solo las que se proporcionan abajo.
- Separa evidencia (datos verificables), inferencia (conclusiones logicas basadas en datos) e hipotesis (supuestos no verificados).
- Solo devuelve un payload YAML completo.

Fuentes analizadas:

1. The B1M (Fred Mills, theb1m.com):
   - "The World's Biggest Building Boom Isn't What You Think" (2026-04-20): Data centre construction reshaping global infrastructure investment.
   - "Can Saudi Arabia still complete The LINE?" (2025-12-18): Megaproject feasibility vs ambition, NEOM reality check.
   Senal: Megaprojects, infrastructure investment, feasibility vs ambition.

2. Andrew Ng / The Batch (deeplearning.ai/the-batch):
   - Issue #349 (2026-04-17): "AI-native software engineering teams operate very differently than traditional teams."
   - Issue #348 (2026-04-10): "As AI agents accelerate coding, what is the future of software engineering?"
   - Issue #346 (2026-03-27): Resistance movements against AI progress.
   - Issue #342 (2026-02-27): Agentic AI investor panic, local vs cloud.
   Senal: AI agents transforming how teams work, gap between capability and adoption, organizational resistance.

3. Marc Vidal (marcvidal.net):
   - "Cuando los imperios olvidan innovar: lecciones de Bizancio" (2026-04-20): Innovation stagnation leads to decline.
   - "El algoritmo como jefe supremo" (2026-03-23): Algorithmic management replacing human oversight.
   - "La paradoja de la productividad" (2026-03-09): Solow paradox — tech advances without productivity gains.
   Senal: Digital transformation tension, productivity paradox, organizational power shifts.

4. Aelion.io (Ivan Gomez Rodriguez):
   - Manifesto: "La tecnologia solo tiene sentido si genera valor desde el primer dia."
   Senal: Construction sector ROI-first mindset, BIM/AI/XR as ongoing unfulfilled promises.

Patron detectado entre fuentes:
Multiples fuentes convergen en la tension entre la capacidad de la IA y la preparacion organizacional para adoptarla. Esto aplica directamente a AEC/BIM:
- Ng dice que los equipos AI-native operan diferente, pero la mayoria de equipos AEC no son AI-native.
- Vidal advierte que las organizaciones que olvidan innovar declinan y que la paradoja de productividad persiste.
- Gomez (Aelion) expresa la perspectiva AEC: la tecnologia solo sirve si genera valor desde el dia uno.
- The B1M muestra que donde hay preparacion organizacional (data centres), la inversion fluye.

Audiencia:
Profesionales AEC, BIM managers, coordinadores digitales, consultores, lideres de transformacion digital.

Tono:
Claro, directo, tecnico pero entendible, sin hype, sin vender servicios, sin frases genericas de IA. Sin hashtags. Apropiado para LinkedIn awareness.

Restricciones editoriales:
- No revelar detalles internos del sistema editorial Rick.
- No mencionar estados exactos internos, gates, auditorias internas, DB Publicaciones, ni arquitectura Umbral.
- Puede hablar de forma general sobre gobernanza, procesos, preparacion organizacional.
- Los claims factuales deben referenciar la fuente (Ng/Batch, Vidal, B1M, Aelion).
- Los claims de opinion deben marcarse como inferencia o hipotesis.
- La pieza debe aportar algo que las fuentes individuales no dicen por separado (sintesis, no resumen).

Requisito de trazabilidad:
El payload DEBE incluir:
- source_set: fuentes analizadas con URLs
- extraction_matrix: que idea se extrajo de cada publicacion, tipo (evidencia/inferencia/hipotesis), por que sirve para AEC
- decantation: que se descarto y por que, que se conserva, que se combina
- transformation_formula: nombre, tipo, pasos, input_signals, aec_connection, assumptions, risks
- editorial_decision: angulo elegido, alternativas consideradas, por que se eligio

Rutas editoriales a considerar (proponer 2-3, elegir una):
- external_signal_to_aec_angle: tomar senales de IA/tech y traducirlas a AEC
- pattern_synthesis: combinar patrones de multiples fuentes en una tesis
- contrarian_take: cuestionar un consenso con evidencia de fuentes
- aec_translation: convertir una idea general en util para AEC

Formato requerido — devuelve SOLO el payload YAML sin texto adicional:

```yaml
publication_id: CAND-002
title: ""
estado: Borrador
canal: linkedin
tipo_de_contenido: linkedin_post
etapa_audiencia: awareness
prioridad: media
source_set:
  sources_analyzed:
    - name: ""
      url: ""
      period_reviewed: ""
      publications_found: []
      access_status: ""
  sources_discarded: []
extraction_matrix:
  - source: ""
    publication: ""
    idea_extracted: ""
    type: ""  # evidencia | inferencia | hipotesis
    pain_or_tension: ""
    aec_relevance: ""
    useful: true
decantation:
  discarded:
    - idea: ""
      reason: ""
  conserved:
    - idea: ""
      reason: ""
  combined:
    - ideas: []
      synthesis: ""
transformation_formula:
  formula_name: ""
  formula_type: ""  # external_signal_to_aec_angle | pattern_synthesis | contrarian_take | aec_translation
  input_signals: []
  transformation_steps: []
  aec_connection: ""
  assumptions: []
  risks: []
editorial_decision:
  selected_angle: ""
  alternatives_considered:
    - angle: ""
      why_rejected: ""
  why_selected: ""
claim_principal:
  texto: ""
  tipo: ""  # opinion_operativa | inferencia_con_fuentes | hipotesis
  requiere_fuente_primaria: false
angulo_editorial: ""
fuentes:
  fuente_primaria:
    estado: ""
    url: ""
    nota: ""
  fuente_referente:
    url: ""
    nota: ""
copies:
  copy_linkedin: ""
  copy_x: ""
  copy_blog: ""
  copy_newsletter: ""
visual:
  visual_brief: ""
  visual_hitl_required: true
  visual_asset_url: ""
revision:
  comentarios_revision: ""
  responsable_revision: David Moreira
  ultima_revision_humana: ""
  qa_requerida: true
  qa_owner: rick-qa
gates:
  aprobado_contenido: false
  autorizar_publicacion: false
  gate_invalidado: false
post_publication:
  published_url: ""
  published_at: ""
  platform_post_id: ""
  publication_url: ""
  canal_publicado: ""
  publish_error: ""
  error_kind: ""
system:
  creado_por_sistema: false
  rick_active: false
  publish_authorized: false
  content_hash: ""
  idempotency_key: ""
  repo_reference: ""
  proyecto: "Sistema Editorial Rick"
  trace_id: CAND-002-source-driven-editorial-candidate
acceptance_checklist:
  publication_id_unique: true
  estado_borrador: true
  gates_false: true
  no_publication_fields: true
  no_notion_write: true
  no_runtime_activation: true
  no_unverified_factual_claims: true
  source_primary_status_clear: true
  no_internal_details_exposed: true
  ready_for_human_review: true
  ready_for_publication: false
```
