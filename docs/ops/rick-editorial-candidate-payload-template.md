# Rick Editorial — Candidate Payload Template

> **Status**: design-only support document. No runtime activation.

## Purpose

Template for manually simulating `rick-editorial` output before the agent is active. This prepares candidate records for `Publicaciones` without writing to Notion automatically.

The output contract spec lives in `openclaw/workspace-agent-overrides/rick-editorial/ROLE.md`. This template is the practical, fill-in-the-blanks version for creating CAND-001 and subsequent candidates.

## Safety

- No publication.
- No Rick runtime activation.
- No Notion writes from this template.
- Human gates remain false.
- David reviews before approval.
- `rick-qa` validates before any candidate is considered ready for review.
- `content_hash` and `idempotency_key` remain empty until content is approved.

## Payload

```yaml
# --- Identity ---
publication_id: "CAND-NNN"
title: ""
trace_id: ""

# --- Classification ---
estado: Borrador
canal: ""                      # blog | linkedin | x | newsletter
tipo_de_contenido: ""          # blog_post | linkedin_post | x_post | newsletter | carousel | visual_asset | thread
etapa_audiencia: ""            # awareness | consideration | trust | conversion | (empty)
prioridad: ""                  # (if applicable)

# --- Editorial content ---
claim_principal: ""
angulo_editorial: ""
premisa: ""                    # Afirmación breve, fuerte, clara — la tesis condensada en 1-2 frases operativas
resumen_fuente: ""

# --- Sources ---
fuente_primaria: ""            # URL or "pending" — required for verifiable claims
fuente_referente: ""           # URL or empty — discovery signal only, not source of truth

# --- Source classification (per editorial-source-attribution-policy.md) ---
source_classification:
  - source_name: ""
    source_url: ""
    type: ""                   # primary_source | original_article | official_doc | analysis_source | discovery_source | contextual_reference
    public_citable: false      # true only if primary/original source or org producing original analysis
    internal_trace_only: false # true for discovery sources and contextual references
    reason: ""
    original_source_url: ""    # if discovery_source, URL of primary source found
    original_source_name: ""   # name of primary source organization

# --- Per-channel copies ---
copy_linkedin: ""
copy_x: ""
copy_blog: ""
copy_newsletter: ""

# --- Visual ---
visual_brief: ""
visual_hitl_required: false    # true if people, brands, or sensitive content

# --- Review ---
comentarios_revision: ""

# --- Human gates (never set by rick-editorial) ---
gates:
  aprobado_contenido: false
  autorizar_publicacion: false
  gate_invalidado: false

# --- Post-publication (empty until publish_success) ---
post_publication:
  published_url: ""
  published_at: ""
  platform_post_id: ""
  publish_error: ""
  error_kind: ""

# --- System metadata ---
system:
  creado_por_sistema: false
  rick_active: false
  publish_authorized: false
  content_hash: ""             # calculated only after content approval
  idempotency_key: ""          # derived from canal + content_hash + page_id
```

## Required QA Checklist

Before handing a candidate to `rick-qa` or David:

- [ ] `publication_id` is unique (CAND-NNN format, sequential).
- [ ] `estado` is `Borrador` — never higher.
- [ ] `canal` is valid per Publicaciones schema: `blog`, `linkedin`, `x`, `newsletter`.
- [ ] `tipo_de_contenido` is valid per schema: `blog_post`, `linkedin_post`, `x_post`, `newsletter`, `carousel`, `visual_asset`, `thread`.
- [ ] Human gates are all `false`.
- [ ] No publication fields are set (`published_url`, `platform_post_id` empty).
- [ ] Source separation is clear: `fuente_primaria` is the source of truth; `fuente_referente` is discovery signal only.
- [ ] Source classification is present per `editorial-source-attribution-policy.md`.
- [ ] No referentes cited as public authorities in copy when they are not the original source.
- [ ] No unsupported factual claims without a primary source.
- [ ] `visual_hitl_required` is explicitly set (true if people/brands/sensitive content).
- [ ] `trace_id` is set for trazabilidad.
- [ ] Ready for David review, not ready for publication.

## Usage

1. Copy the payload template above.
2. Fill in the fields for the candidate.
3. Save as a local file or structured document for review.
4. Hand to `rick-qa` (or manually validate using the QA checklist).
5. Once validated, register manually in Notion `Publicaciones` DB.
6. Re-run read-only audit after registration.

## References

- Output contract spec: `openclaw/workspace-agent-overrides/rick-editorial/ROLE.md`
- Publicaciones schema: `notion/schemas/publicaciones.schema.yaml`
- Test records: `docs/ops/notion-publicaciones-test-records.md`
- Setup runbook: `docs/ops/notion-publicaciones-setup-runbook.md`
