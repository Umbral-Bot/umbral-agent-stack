# CAND-001 v2 — Rick Orchestrator Request

> **Date**: 2026-04-23
> **Target agent**: rick-orchestrator (simulating rick-editorial)
> **Purpose**: Generate CAND-001 v2 applying David's editorial decision.

---

Actúa como rick-orchestrator simulando explícitamente rick-editorial.

Objetivo: Generar el payload CAND-001 v2 aplicando la decisión editorial de David.

Reglas:
- No escribas en Notion.
- No publiques.
- No marques gates humanos.
- No actives Rick.
- Solo devuelve un payload YAML completo.

Título:
CAND-001 — Automatizar sin gobernanza escala el desorden

Idea central:
Antes de automatizar con IA/agentes, un proceso debe tener gobernanza mínima: responsables claros, revisión humana, criterios de calidad, fuentes, trazabilidad y forma de auditar decisiones. Si no, la automatización puede acelerar errores o aumentar el riesgo operativo.

Restricción editorial (decisión de David):
- No revelar detalles internos del sistema editorial Rick.
- No mencionar estados exactos internos, gates con nombres internos, auditorías internas, TEST-001, DB Publicaciones, ni la arquitectura interna de Umbral.
- Puede hablar de forma general sobre estados, revisión, trazabilidad, fuentes y gobernanza.
- No inventar fuente primaria. Si no hay fuente externa, marcar la pieza como opinión operativa.
- Suavizar claims categóricos sobre desinformación: hablar de riesgo de amplificar errores o afirmaciones no verificadas, no de hecho universal.
- El texto debe ser apto para LinkedIn awareness.

Audiencia:
Profesionales AEC, BIM managers, coordinadores digitales, consultores y líderes de transformación digital.

Tono:
Claro, directo, técnico pero entendible, sin hype, sin vender servicios, sin frases genéricas de IA. Sin hashtags.

Cambios respecto a v1 (QA feedback aplicado):
1. Eliminar todas las referencias a proceso interno específico (estados exactos, gates internos, auditoría interna, TEST-001).
2. Acortar copy LinkedIn entre 15-25% respecto a v1.
3. Suavizar afirmación sobre desinformación: tratarla como riesgo, no como hecho universal.
4. Mantener el ángulo general de gobernanza vs automatización sin detalle interno.

Formato requerido — devuelve SOLO el payload YAML sin texto adicional antes ni después:

```yaml
publication_id: CAND-001
title: ""
estado: Borrador
canal: linkedin
tipo_de_contenido: linkedin_post
etapa_audiencia: awareness
prioridad: media
claim_principal:
  texto: ""
  tipo: opinion_operativa
  requiere_fuente_primaria: false
angulo_editorial: ""
fuentes:
  fuente_primaria:
    estado: pendiente
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
```
