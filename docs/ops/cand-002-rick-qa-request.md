Actua como rick-qa. Valida el siguiente payload de candidata editorial CAND-002 (source-driven).

Este es el primer flujo editorial basado en fuentes externas seleccionadas por David desde la DB Referentes de Notion. A diferencia de CAND-001 (opinion operativa sin fuente), CAND-002 debe tener trazabilidad completa de fuentes.

Criterios de validacion:

1. Schema: Verifica que publication_id, estado, canal, tipo_de_contenido, etapa_audiencia, gates, post_publication y system sean validos segun el schema de Publicaciones.

2. Fuentes y trazabilidad:
   - Las fuentes listadas en source_set deben ser reales y trazables.
   - La extraction_matrix debe separar evidencia, inferencia e hipotesis.
   - Ningun claim factual debe carecer de fuente.
   - Las URLs de fuentes deben ser publicas y verificables.

3. Decantacion y formula:
   - La decantation debe explicar que se descarto, que se conservo y que se combino.
   - La transformation_formula debe ser explicita: tipo, pasos, conexion AEC, supuestos y riesgos.
   - La formula debe producir algo que las fuentes individuales no dicen por separado (sintesis, no resumen).

4. Relacion AEC:
   - La conexion con AEC/BIM debe ser razonable, no forzada.
   - El copy debe ser util para la audiencia target (BIM managers, coordinadores digitales, lideres de transformacion digital).

5. Editorial:
   - Copy claro, directo, sin hype, sin vender servicios.
   - Longitud apropiada para LinkedIn awareness.
   - Tono sobrio y tecnico pero entendible.

6. Governance:
   - gates false
   - no publicacion
   - no runtime
   - no detalles internos del sistema Rick

7. Disclosure:
   - No debe exponer estados internos, nombres de gates internos, auditorias internas, DB Publicaciones ni arquitectura Umbral.

Devuelve tu resultado en formato YAML con esta estructura:

```yaml
qa_result:
  verdict: pass | pass_with_changes | blocked
  ready_to_create_notion_draft: true | false
  ready_for_publication: false
  blockers: []
  required_changes: []
  recommendations: []
  schema_validation:
    status: pass | fail
    notes: []
  source_validation:
    status: pass | fail
    notes: []
  extraction_matrix_validation:
    status: pass | fail
    notes: []
  transformation_formula_validation:
    status: pass | fail
    notes: []
  aec_relevance_validation:
    status: pass | fail
    notes: []
  editorial_quality:
    status: pass | fail
    notes: []
  governance_validation:
    status: pass | fail
    notes: []
  internal_disclosure_check:
    status: pass | fail
    notes: []
  residual_risks: []
  next_action: ""
```

Payload a validar:

```yaml
publication_id: CAND-002
title: "La IA ya cambio de ritmo. En AEC, el cuello de botella sigue siendo la organizacion."
estado: Borrador
canal: linkedin
tipo_de_contenido: linkedin_post
etapa_audiencia: awareness
prioridad: media
source_set:
  sources_analyzed:
    - name: "The B1M"
      url: "https://www.theb1m.com"
      period_reviewed: "2025-12-18 a 2026-04-20"
      publications_found:
        - "The World's Biggest Building Boom Isn't What You Think"
        - "Can Saudi Arabia still complete The LINE?"
      access_status: "provided_by_user"
    - name: "Andrew Ng / The Batch"
      url: "https://www.deeplearning.ai/the-batch"
      period_reviewed: "2026-02-27 a 2026-04-17"
      publications_found:
        - "Issue #349: AI-native software engineering teams operate very differently than traditional teams."
        - "Issue #348: As AI agents accelerate coding, what is the future of software engineering?"
        - "Issue #346: Resistance movements against AI progress."
        - "Issue #342: Agentic AI investor panic, local vs cloud."
      access_status: "provided_by_user"
    - name: "Marc Vidal"
      url: "https://marcvidal.net"
      period_reviewed: "2026-03-09 a 2026-04-20"
      publications_found:
        - "Cuando los imperios olvidan innovar: lecciones de Bizancio"
        - "El algoritmo como jefe supremo"
        - "La paradoja de la productividad"
      access_status: "provided_by_user"
    - name: "Aelion.io / Ivan Gomez Rodriguez"
      url: "https://aelion.io"
      period_reviewed: "manifesto vigente"
      publications_found:
        - "La tecnologia solo tiene sentido si genera valor desde el primer dia."
      access_status: "provided_by_user"
  sources_discarded: []
extraction_matrix:
  - source: "The B1M"
    publication: "The World's Biggest Building Boom Isn't What You Think"
    idea_extracted: "La construccion de data centres esta reconfigurando la inversion global en infraestructura."
    type: "evidencia"
    pain_or_tension: "El capital se mueve hacia donde existe una tesis operativa clara."
    aec_relevance: "La adopcion tecnologica depende de capacidad organizacional para convertir demanda en ejecucion confiable."
    useful: true
  - source: "Andrew Ng / The Batch"
    publication: "Issue #349"
    idea_extracted: "Los equipos AI-native operan de forma distinta a los equipos tradicionales."
    type: "evidencia"
    pain_or_tension: "Brecha entre capacidad tecnologica disponible y forma real de trabajo."
    aec_relevance: "La mayoria de equipos AEC no son AI-native."
    useful: true
  - source: "Marc Vidal"
    publication: "La paradoja de la productividad"
    idea_extracted: "El avance tecnologico no siempre se traduce en productividad observable."
    type: "evidencia"
    pain_or_tension: "Adoptar tecnologia no garantiza retorno inmediato."
    aec_relevance: "Conecta con implementaciones BIM/IA que agregan complejidad sin cambiar flujos."
    useful: true
  - source: "Aelion.io / Ivan Gomez Rodriguez"
    publication: "Manifesto"
    idea_extracted: "En construccion, la adopcion se mide contra valor temprano y tangible."
    type: "evidencia"
    pain_or_tension: "Fatiga sectorial frente a promesas de tecnologia."
    aec_relevance: "Traduccion directa del filtro mental con que AEC evalua BIM, IA y XR."
    useful: true
decantation:
  discarded:
    - idea: "Detalles de NEOM/The LINE como caso aislado."
      reason: "Desvia hacia megaproyecto especifico."
    - idea: "Arquitectura tecnica de agentes."
      reason: "No es nivel correcto para awareness."
    - idea: "Resistencia como rechazo irracional."
      reason: "Simplifica problema real."
  conserved:
    - idea: "La IA avanza mas rapido que la preparacion de equipos."
      reason: "Nucleo comun entre Ng, Vidal y Aelion."
    - idea: "La productividad no mejora sola por tecnologia."
      reason: "Conecta promesa de IA con realidad operativa AEC."
  combined:
    - ideas:
        - "Equipos AI-native operan distinto."
        - "Paradoja de productividad persiste."
        - "Tecnologia solo sirve si genera valor desde dia uno."
      synthesis: "El problema no es adoptar IA, sino rediseñar la forma de trabajar."
transformation_formula:
  formula_name: "Capacidad vs preparacion"
  formula_type: "pattern_synthesis"
  input_signals:
    - "Equipos AI-native funcionan distinto."
    - "Tecnologia no garantiza productividad sola."
    - "AEC filtra por valor temprano."
    - "Inversion premia claridad operativa."
  transformation_steps:
    - "Tomar senales externas de IA, productividad e inversion."
    - "Eliminar detalles que no aportan a audiencia AEC."
    - "Traducir brecha capacidad-adopcion al lenguaje operativo BIM."
    - "Convertir patron en tesis: el cuello de botella es la organizacion."
    - "Redactar pieza que aporte sintesis y criterio."
  aec_connection: "AEC/BIM vive tension entre nuevas capacidades y su captura de valor, que depende de procesos, roles, criterio y gobernanza."
  assumptions:
    - "Mayoria de equipos AEC no opera como AI-native."
    - "Audiencia reconoce frustracion entre promesa y valor real."
  risks:
    - "Sobregeneralizar AEC como sector homogeneo."
    - "Que se lea como anti-IA."
    - "Que pierda fuerza sin separar evidencia de inferencia."
claim_principal:
  texto: "La barrera principal para capturar valor de IA en AEC no parece ser la falta de herramientas, sino la falta de preparacion organizacional."
  tipo: "inferencia_con_fuentes"
  requiere_fuente_primaria: false
angulo_editorial: "La IA ya ofrece capacidad suficiente, pero en AEC el retorno sera limitado mientras equipos y procesos operen con logicas pre-IA."
copies:
  copy_linkedin: "Hay una idea que se repite en distintas conversaciones sobre IA: que el problema es acceder a la herramienta correcta.\n\nNo estoy seguro de que ese sea el cuello de botella principal en AEC.\n\nAndrew Ng viene mostrando que los equipos AI-native trabajan de forma distinta a los equipos tradicionales. Marc Vidal insiste en una tension que no es nueva: la tecnologia puede avanzar mas rapido que la productividad real. Y desde AEC, Ivan Gomez lo resume con un filtro brutalmente util: la tecnologia solo importa si genera valor desde el primer dia.\n\nSi juntas esas senales, aparece una lectura incomoda:\n\nla barrera no parece ser la falta de IA, sino la falta de preparacion organizacional para usarla bien.\n\nEso incluye roles, criterio, revision, trazabilidad y procesos capaces de absorber una nueva velocidad de trabajo.\n\nPor eso muchas organizaciones pueden incorporar mas automatizacion y aun asi no capturar mas valor.\n\nNo porque la tecnologia falle.\nSino porque el sistema de trabajo sigue disenado para otra etapa.\n\nEn AEC, quiza la pregunta ya no es quien esta probando IA.\nLa pregunta es quien esta redisenando su forma de operar para que esa IA realmente produzca impacto."
  copy_x: "En AEC, el cuello de botella de la IA puede no ser la herramienta.\n\nPuede ser la organizacion.\n\nSi los equipos AI-native operan distinto, si la productividad no mejora sola y si el sector exige valor temprano, entonces la captura de valor depende menos del hype y mas de roles, criterio, revision y procesos."
  copy_blog: ""
  copy_newsletter: ""
visual:
  visual_brief: "Visual editorial sobrio con tension central: izquierda, curva ascendente 'capacidad de IA'; derecha, curva mas lenta 'preparacion organizacional'. Espacio entre ambas con etiquetas: roles, criterio, revision, trazabilidad, procesos."
  visual_hitl_required: true
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
  trace_id: CAND-002-source-driven-editorial-candidate
```
