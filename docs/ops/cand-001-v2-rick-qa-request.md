# CAND-001 v2 — Rick QA Validation Request

> **Date**: 2026-04-23
> **Target agent**: rick-qa
> **Purpose**: Validate CAND-001 v2 before creating Notion draft.

---

Actua como rick-qa en OpenClaw.

Objetivo: Validar el payload editorial CAND-001 v2 antes de crear registro en Notion.

Reglas:
- No escribas en Notion.
- No publiques.
- No marques gates.
- Solo valida y entrega dictamen.

Contexto:
- CAND-001 v1 fue validado con verdict pass_with_changes.
- David decidio: no exponer detalles internos, suavizar claims, acortar copy.
- rick-orchestrator genero v2 aplicando esos cambios.

Payload a validar:

publication_id: CAND-001
title: "Automatizar sin gobernanza escala el desorden"
estado: Borrador
canal: linkedin
tipo_de_contenido: linkedin_post
etapa_audiencia: awareness
prioridad: media
claim_principal:
  texto: "Antes de automatizar con IA o agentes, un proceso necesita gobernanza mínima. Si no hay responsables, revisión humana, criterios de calidad, fuentes y trazabilidad, la automatización puede acelerar errores y aumentar el riesgo operativo."
  tipo: opinion_operativa
  requiere_fuente_primaria: false
angulo_editorial: "La automatización no corrige un proceso débil. Solo lo hace más rápido y más difícil de auditar."
fuentes:
  fuente_primaria:
    estado: pendiente
    url: ""
    nota: "Pieza planteada como opinión operativa. No se incorpora fuente primaria externa en esta versión."
  fuente_referente:
    url: ""
    nota: "Sin fuente externa referencial en esta versión para evitar atribuciones no verificadas."
copies:
  copy_linkedin: "Muchas empresas quieren automatizar procesos con IA antes de ordenar cómo toman decisiones.\n\nAhí aparece el problema.\n\nSi no hay responsables claros, revisión humana, criterios mínimos de calidad, fuentes trazables y una forma simple de auditar decisiones, la automatización no resuelve el desorden: lo escala.\n\nY cuando eso pasa, el riesgo no es solo técnico. También aumenta la probabilidad de amplificar errores, repetir afirmaciones no verificadas o perder control sobre excepciones relevantes.\n\nAutomatizar bien no parte por la herramienta.\nParte por la gobernanza mínima del proceso.\n\nPrimero claridad.\nDespués velocidad."
  copy_x: "Automatizar un proceso desordenado no lo arregla: lo acelera.\n\nAntes de usar IA o agentes, hace falta gobernanza mínima: responsables, revisión humana, criterios de calidad, fuentes y trazabilidad.\n\nPrimero claridad. Después velocidad."
  copy_blog: ""
  copy_newsletter: ""
visual:
  visual_brief: "Gráfica simple tipo diagrama comparativo. Lado izquierdo: proceso sin gobernanza con nodos difusos, flechas caóticas y etiquetas como responsables difusos, sin revisión, sin trazabilidad. Lado derecho: proceso con gobernanza mínima, flujo claro y etiquetas responsables, revisión humana, criterios, fuentes y auditoría. Estética sobria, técnica, legible para LinkedIn, sin UI interna ni referencias a sistemas específicos."
  visual_hitl_required: true
  visual_asset_url: ""
revision:
  comentarios_revision: "Versión v2 ajustada a la decisión editorial: sin referencias internas, sin detalles del sistema, con claim suavizado sobre riesgo de amplificar errores o afirmaciones no verificadas. Copy reducido y orientado a awareness en LinkedIn."
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
  trace_id: CAND-001-v2-editorial-candidate
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

Criterios de validacion:
1. Schema: estado/canal/tipo_de_contenido validos, gates false, campos post-publicacion vacios, trace_id presente.
2. No exposicion de detalles internos del sistema Rick (estados internos, gates internos, auditoria interna, TEST-001, DB Publicaciones, arquitectura Umbral).
3. No claims factuales sin fuente primaria. Opinion operativa correctamente marcada.
4. Copy apto para LinkedIn awareness: claro, directo, no autopromocional, longitud adecuada.
5. Gobernanza: gates false, no aprobado, no autorizado, no listo para publicacion.
6. Visual: brief seguro, no UI automation, HITL requerido.
7. Decision: ready_to_create_notion_draft true or false.

Formato de respuesta requerido (YAML):

qa_result:
  verdict: pass | pass_with_changes | blocked
  ready_to_create_notion_draft: true | false
  ready_for_publication: false
  blockers: [...]
  required_changes: [...]
  recommendations: [...]
  schema_validation:
    status: pass | fail
    notes: [...]
  internal_disclosure_check:
    status: pass | fail
    notes: [...]
  source_validation:
    status: pass | warning | fail
    notes: [...]
  editorial_quality:
    status: pass | warning | fail
    notes: [...]
  governance_validation:
    status: pass | fail
    notes: [...]
  visual_validation:
    status: pass | warning | fail
    notes: [...]
  residual_risks: [...]
  next_action: ""

No reescribas la pieza. Si propones cambios, hazlos como lista concreta.
