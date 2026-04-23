# CAND-003 — Editorial Candidate Payload

> **Date**: 2026-04-23
> **Type**: Source-driven editorial candidate
> **Generator**: rick-orchestrator (simulating rick-editorial)

```yaml
# --- Identity ---
publication_id: "CAND-003"
title: "Criterio antes que automatización: lo que AEC necesita definir antes de acelerar con IA"
trace_id: "CAND-003-source-driven-editorial-candidate"

# --- Classification ---
estado: Borrador
canal: linkedin
tipo_de_contenido: linkedin_post
etapa_audiencia: awareness
prioridad: media

# --- Editorial content ---
premisa: "En AEC, automatizar sin criterio operativo explícito no acelera: amplifica la ambigüedad. Antes de escalar con IA, hay que definir qué constituye una revisión válida, qué dispara una escalación y qué hace que la coordinación sea suficiente."

claim_principal:
  texto: "La principal barrera para que la automatización genere valor en AEC no es tecnológica ni presupuestaria: es la ausencia de criterios operativos explícitos que definan qué es aceptable, qué requiere revisión humana y cuándo escalar."
  tipo: inferencia_con_fuentes
  requiere_fuente_primaria: false

angulo_editorial: "La IA ya ofrece capacidad para automatizar partes del trabajo en AEC. Pero sin criterios claros de revisión, coordinación y escalación, la automatización amplifica procesos indefinidos en lugar de mejorarlos. La pieza conecta la ausencia de estándares de auditoría en IA con la ausencia de criterios operativos en AEC."

resumen_fuente: "Síntesis de The Batch (#340, auditorías IA sin estándares; #343, gobernanza de agentes implícita), OECD (79% de empresas europeas con gestión algorítmica), McKinsey (30% de horas automatizables para 2030), AVERI (primer framework de auditoría IA)."

# --- Sources ---
fuente_primaria: "pending"
fuente_referente: ""

# --- Source classification ---
source_classification:
  - source_name: "DeepLearning.AI / The Batch"
    source_url: "https://www.deeplearning.ai/the-batch"
    type: analysis_source
    public_citable: true
    internal_trace_only: false
    reason: "Newsletter con análisis editorial original. Issues #340 y #343 con reporteo propio sobre auditoría IA y gestión de agentes."
    public_citation: "DeepLearning.AI o The Batch (como organización)"

  - source_name: "OECD — Algorithmic Management Report (2025)"
    source_url: "https://www.oecd.org"
    type: primary_source
    public_citable: true
    internal_trace_only: false
    reason: "Reporte original con dato verificable: 79% de empresas europeas usan herramientas algorítmicas."
    public_citation: "OECD (como organización)"

  - source_name: "AVERI — AI Verification and Research Institute"
    source_url: ""
    type: primary_source
    public_citable: true
    internal_trace_only: false
    reason: "Framework publicado con 8 principios de auditoría y 4 niveles de aseguramiento. Investigación original."
    public_citation: "AVERI (como organización, no Miles Brundage por nombre)"

  - source_name: "McKinsey Global Institute"
    source_url: "https://www.mckinsey.com"
    type: primary_source
    public_citable: true
    internal_trace_only: false
    reason: "Investigación original: hasta 30% de horas laborales en EE.UU. automatizables para 2030."
    public_citation: "McKinsey Global Institute (como organización)"

  - source_name: "Marc Vidal"
    source_url: "https://www.marcvidal.net"
    type: discovery_source
    public_citable: false
    internal_trace_only: true
    reason: "Referente que analiza fuentes OECD, McKinsey, UE. Camino de descubrimiento, no fuente original."
    public_citation: "NO citar en copy público"

  - source_name: "Aelion.io / Iván Gómez"
    source_url: "https://aelion.io"
    type: contextual_reference
    public_citable: false
    internal_trace_only: true
    reason: "Landing page manifesto. Representa mentalidad sectorial AEC sin datos verificables."
    public_citation: "NO citar en copy público"

# --- Source set ---
source_set:
  sources_analyzed:
    - name: "DeepLearning.AI / The Batch #340"
      url: "https://www.deeplearning.ai/the-batch/issue-340/"
      period_reviewed: "2026-02-13"
      publications_found:
        - "Standardized AI Audits — AVERI framework, 8 principles, 4 assurance levels"
      access_status: "Public"

    - name: "DeepLearning.AI / The Batch #343"
      url: "https://www.deeplearning.ai/the-batch/issue-343/"
      period_reviewed: "2026-03-06"
      publications_found:
        - "Frontier Agent Management — identity, permissions, guardrails, implicit oversight"
      access_status: "Public"

    - name: "Marc Vidal — El algoritmo como jefe supremo"
      url: "https://www.marcvidal.net/blog/2026/3/23/el-algoritmo-como-jefe-supremo"
      period_reviewed: "2026-03-23"
      publications_found:
        - "Gestión algorítmica sin gobernanza: OECD 79%, McKinsey 30%, WEF 92M/170M, UE reg."
      access_status: "Public (fetched in CAND-002 cycle)"

    - name: "Aelion.io"
      url: "https://aelion.io"
      period_reviewed: "vigente"
      publications_found:
        - "Manifesto: valor desde el primer día"
      access_status: "Public landing"

  sources_discarded:
    - name: "Bernard Marr"
      reason: "Blog 404, no accesible"
    - name: "The B1M"
      reason: "Artículos disponibles no conectan directamente con tesis de criterio operativo"
    - name: "The Batch #347"
      reason: "Voice AI adoption — señal débil para tesis de criterio"

# --- Extraction matrix ---
extraction_matrix:

  evidencia:
    - source: "Batch #340 / AVERI"
      publication: "Standardized AI Audits"
      idea_extracted: "No existen estándares consensuados para auditar seguridad y calidad de IA. El framework AVERI propone 8 principios y 4 niveles de aseguramiento como primer intento."
      aec_relevance: "En AEC, los estándares de revisión de entregables BIM/coordinación tampoco están formalizados en muchas organizaciones."

    - source: "Batch #343"
      publication: "Frontier Agent Management"
      idea_extracted: "Las plataformas de agentes IA asignan identidad, permisos y guardarraíles por agente, pero la supervisión humana sigue siendo implícita, no formal."
      aec_relevance: "En coordinación AEC, los roles tienen responsabilidades implícitas pero rara vez criterios explícitos de aceptación."

    - source: "OECD (2025)"
      publication: "Algorithmic Management Report"
      idea_extracted: "79% de empresas europeas usan herramientas algorítmicas de gestión."
      aec_relevance: "Adopción masiva de herramientas sin criterios proporcionales de gobernanza."

    - source: "McKinsey Global Institute"
      publication: "Automation potential"
      idea_extracted: "Hasta 30% de horas laborales en EE.UU. podrían automatizarse para 2030."
      aec_relevance: "La escala de automatización posible exige definir qué se automatiza y qué no."

    - source: "Vidal (discovery) → OECD/McKinsey"
      publication: "El algoritmo como jefe supremo"
      idea_extracted: "Gestión algorítmica desplegada sin criterios de: qué decisiones toma el algoritmo, qué dispara revisión humana, qué constituye resultado aceptable."
      aec_relevance: "En AEC, las herramientas de automatización/IA se implementan sin protocolos de escalación ni criterios de calidad de output."

    - source: "Aelion.io (contextual)"
      publication: "Manifesto"
      idea_extracted: "La tecnología solo tiene sentido si genera valor desde el primer día."
      aec_relevance: "Valor desde el primer día requiere criterio operativo para definir qué es valor. Sin esa definición, la afirmación es aspiracional."

  inferencia:
    - idea: "La mayoría de equipos AEC automatizan tareas sin haber definido previamente qué constituye un entregable aceptable, una revisión completa o una coordinación suficiente."
      based_on: "OECD 79% + Batch #343 implicit oversight + sector knowledge"
      confidence: "Alta — inferencia razonable basada en evidencia de adopción sin gobernanza y conocimiento sectorial."

    - idea: "Sin criterio operativo explícito, la automatización amplifica la ambigüedad en lugar de reducirla: procesos mal definidos se ejecutan más rápido."
      based_on: "AVERI audit gap + McKinsey 30% + Vidal 'quién vigila al vigilante'"
      confidence: "Alta — consecuencia lógica de automatizar sin estándares."

    - idea: "La inversión en herramientas de IA para AEC no generará retorno si no viene acompañada de criterios explícitos de revisión, aceptación y escalación."
      based_on: "Batch #340 AVERI + OECD + Aelion ROI-first"
      confidence: "Media-alta — plausible pero no cuantificada en AEC específicamente."

  hipotesis:
    - idea: "La mayoría de equipos de coordinación BIM no tiene documentado qué constituye una revisión válida ni qué dispara una escalación."
      status: "Supuesto razonable para la audiencia AEC, no verificado con datos."

    - idea: "La falta de criterio operativo explícito es un factor más limitante que la falta de herramientas para capturar valor de IA en AEC."
      status: "Tesis central — plausible pero no cuantificada."

# --- Decantation ---
decantation:
  discarded:
    - idea: "Detalles técnicos de AVERI (4 niveles AAL, categorías de riesgo)"
      reason: "Demasiado técnico para audiencia AEC awareness. La señal es que el framework existe porque no había criterios, no los detalles del framework."
    - idea: "Estadísticas WEF (92M/170M empleos)"
      reason: "Macro-laboral, no conecta directamente con criterio operativo en AEC."
    - idea: "EU AI Regulation (reconocimiento emocional)"
      reason: "Regulación laboral específica, no relevante para tesis de criterio operativo en AEC."
    - idea: "The B1M — megaproyectos"
      reason: "Señal de inversión/ambición, más fuerte en CAND-002 que en CAND-003."

  conserved:
    - idea: "79% de empresas europeas usan herramientas algorítmicas sin estándares de auditoría"
      reason: "Dato concreto que muestra adopción masiva sin criterio. Trasladable a AEC."
    - idea: "Supervisión humana implícita en plataformas de agentes"
      reason: "Conecta directamente: incluso los que diseñan las herramientas no formalizan la supervisión."
    - idea: "No existen estándares consensuados de auditoría de IA"
      reason: "La ausencia de estándares es el punto central de la tesis."
    - idea: "30% de horas automatizables para 2030"
      reason: "Escala que exige criterio."
    - idea: "Valor desde el primer día requiere definir qué es valor"
      reason: "Puente directo con AEC y mentalidad ROI-first del sector."

  combined:
    - ideas: ["79% adopción sin auditoría", "supervisión implícita en agentes", "no estándares de auditoría"]
      synthesis: "Patrón transversal: la adopción de automatización avanza sin criterios formales de gobernanza, supervisión ni auditoría. Esto ocurre en la industria IA y se replica en AEC."
    - ideas: ["30% automatizable + criterio operativo ausente", "valor desde el primer día + definición de valor"]
      synthesis: "La automatización a escala sin criterio operativo genera velocidad sin dirección. En AEC, donde el filtro práctico es retorno inmediato, la ausencia de criterio convierte la promesa en frustración."

# --- Transformation formula ---
transformation_formula:
  formula_name: "Criterio antes que automatización"
  formula_type: pattern_synthesis
  input_signals:
    - "Batch #340: ausencia de estándares de auditoría IA (AVERI)"
    - "Batch #343: supervisión implícita en plataformas de agentes"
    - "OECD: 79% adopción algorítmica sin gobernanza proporcional"
    - "McKinsey: 30% automatizable — escala que exige criterio"
    - "Aelion: valor desde el primer día requiere definición operativa"
  transformation_steps:
    - "Identificar señales convergentes: herramientas desplegadas sin criterios explícitos."
    - "Eliminar detalles técnicos de frameworks que no aportan a la audiencia AEC."
    - "Traducir la brecha auditoría/gobernanza al lenguaje de coordinación BIM, revisión de entregables, criterios de aceptación."
    - "Convertir el patrón en tesis prescriptiva: el criterio operativo debe preceder a la automatización."
    - "Redactar pieza que aporte criterio, no alarma ni generalidad."
  aec_connection: "AEC despliega herramientas de coordinación, BIM, y cada vez más IA, pero muchas organizaciones no tienen documentado qué constituye una revisión válida, cuándo escalar y qué criterio define coordinación suficiente. La tesis conecta la ausencia de estándares de auditoría IA (nivel industria) con la ausencia de criterios operativos (nivel AEC)."
  assumptions:
    - "La mayoría de equipos AEC no tiene criterios operativos formalizados para revisión, coordinación y escalación."
    - "La audiencia AEC reconoce la frustración de implementar herramientas sin criterios claros."
  risks:
    - "Que se lea como anti-automatización en vez de pro-criterio."
    - "Que sobregeneralice AEC como sector sin criterios (algunas organizaciones sí los tienen)."
    - "Que la pieza se vuelva demasiado prescriptiva para awareness (riesgo de sonar a consultoría)."

# --- Editorial decision ---
editorial_decision:
  selected_angle: "pattern_synthesis"
  alternatives_considered:
    - angle: "aec_translation"
      why_rejected: "Traducción directa de AVERI/OECD a AEC sería demasiado técnica y menos distintiva."
    - angle: "contrarian_take"
      why_rejected: "Decir 'no automaticen' sería polarizante. La tesis es 'definan criterio antes de automatizar', que es constructiva."
    - angle: "external_signal_to_aec_angle"
      why_rejected: "Tomar una sola señal (Batch #340 o OECD) y traducirla sería limitado. La síntesis de múltiples señales da más valor."
  why_selected: "La síntesis de patrón permite combinar señales de industria IA (auditoría, agentes, adopción algorítmica) con la realidad operativa AEC para producir una tesis que ninguna fuente dice sola."

# --- Copies (base draft — pre-voice pass) ---
copies:
  copy_linkedin: |
    En AEC hay cada vez más herramientas de IA disponibles. Pero antes de incorporarlas, hay una pregunta que muchos equipos no se hacen: ¿tenemos criterio operativo explícito para lo que ya hacemos?

    Si una organización no tiene documentado qué constituye una revisión válida de un modelo BIM, qué dispara una escalación en coordinación, o qué criterio define que un entregable es suficiente, la IA no va a resolver eso. Va a ejecutar más rápido un proceso que nadie definió bien.

    No es un problema nuevo. A nivel global, reportes recientes muestran que la mayoría de empresas europeas ya usan herramientas algorítmicas de gestión. Pero los estándares para auditar esas herramientas recién se están proponiendo. Las plataformas más avanzadas de agentes de IA asignan permisos y guardarraíles, pero la supervisión humana sigue siendo implícita.

    Si trasladamos eso a construcción: los equipos están incorporando automatización sin haber formalizado sus criterios de trabajo. Revisiones que dependen de quién las hace, no de qué criterio aplican. Coordinación que funciona por costumbre, no por protocolo.

    Automatizar eso no mejora el proceso. Lo acelera con ambigüedad incluida.

    Antes de escalar con IA, quizá la pregunta operativa es: ¿mi equipo tiene criterio explícito para revisión, aceptación, escalación y coordinación? Si la respuesta es no, la herramienta no es el problema.

  copy_x: |
    En AEC, la IA puede automatizar tareas. Pero si tu equipo no tiene criterio explícito para revisión, escalación y coordinación, lo que automatizas es la ambigüedad.

    79% de empresas europeas ya usan herramientas algorítmicas de gestión. Los estándares para auditarlas recién se están proponiendo. Antes de más herramientas: más criterio.

  copy_blog: ""
  copy_newsletter: ""

# --- Visual ---
visual:
  visual_brief: "Visual editorial sobrio. Dos columnas: izquierda, íconos de herramientas IA (engranaje, robot, flujo). Derecha, un checklist vacío titulado 'Criterio operativo'. Línea punteada entre ambos mostrando la desconexión. Texto: Herramientas ↔ Criterio. Estética técnica, limpia, apta para LinkedIn."
  visual_hitl_required: true
  visual_asset_url: ""

# --- Revision ---
revision:
  comentarios_revision: "Candidata source-driven. Tesis distinta de CAND-002: criterio operativo antes que automatización. Fuentes clasificadas desde el inicio. Ortografía aplicada desde el borrador base."
  responsable_revision: "David Moreira"
  ultima_revision_humana: ""
  qa_requerida: true
  qa_owner: "rick-qa"

# --- Gates ---
gates:
  aprobado_contenido: false
  autorizar_publicacion: false
  gate_invalidado: false

# --- Post-publication ---
post_publication:
  published_url: ""
  published_at: ""
  platform_post_id: ""
  publication_url: ""
  canal_publicado: ""
  publish_error: ""
  error_kind: ""

# --- System ---
system:
  creado_por_sistema: false
  rick_active: false
  publish_authorized: false
  content_hash: ""
  idempotency_key: ""
  repo_reference: ""
  proyecto: "Sistema Editorial Rick"
  trace_id: "CAND-003-source-driven-editorial-candidate"

# --- Acceptance checklist ---
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
