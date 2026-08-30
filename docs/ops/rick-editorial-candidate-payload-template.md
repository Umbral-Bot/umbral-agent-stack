# Rick Editorial — Candidate Payload Template

> **Status**: design-only support document. No runtime activation.

## Purpose

Template for manually simulating `rick-editorial` output before the agent is active. Covers
both pipeline stages: the **V1 alternativa** (Shortlist, pre-HITL-1) and the **V2 candidate**
(Publicaciones, post-`Aprobar`) — without writing to Notion automatically.

The output contract spec lives in `openclaw/workspace-agent-overrides/rick-editorial/ROLE.md`.
This template is the practical, fill-in-the-blanks version for both stages.

## Safety

- No publication.
- No Rick runtime activation.
- No Notion writes from this template.
- Human gates remain false.
- David reviews before approval (V2) / decides HITL-1 (V1: Archivar/Observar/Descartar/Aprobar).
- `rick-qa` validates before any alternativa/candidate is considered ready for review.
- `content_hash` and `idempotency_key` remain empty until content is approved.

## V1 Alternativa Payload (Shortlist, pre-HITL-1)

Per `docs/ops/editorial-norte-hitl-contract-2026-07-22.md` §3 — the three fields marked
**OBLIGATORIO** are hard requirements; `rick-qa` rejects the alternativa if any is missing, or
if `fuente_pieza_url` is a home/feed URL instead of the concrete piece.

```yaml
Título: ""                     # título/ángulo de la alternativa
alternativa_id: ""             # ID estable — correlación / promoción a Publicaciones
topic_key: ""                  # tema normalizado, para dedupe (P2.4) — opcional pero recomendado

# --- OBLIGATORIO ---
arco_narrativo: ""             # trayectoria de la pieza (de qué parte, qué tensiona, a dónde
                                # llega) — NO un ángulo suelto
estructura_discurso: ""        # "Estructura de discurso usada: [hipótesis, introducción,
                                #  argumento 1, argumento 2, contraargumento,
                                #  contra-contraargumento, conclusión]" (secuencia puede variar,
                                #  pero el pie nunca puede omitirse)
fuente_pieza_url: ""           # URL de la PIEZA concreta (item_url) — NUNCA la home/feed
# --- fin OBLIGATORIO ---

premisa: ""                    # tesis condensada en 1-2 frases operativas
fuente_tipo: ""                # primary_source | original_article | official_doc |
                                # analysis_source | discovery_source | contextual_reference
fuente_discovery_url: ""       # home/feed de descubrimiento — trace interno, NO citable
canal_sugerido: ""             # blog | linkedin | x | newsletter
score_alineacion: 0            # 0-100
"Resultado revisión": Pendiente  # Pendiente | Archivar | Observar | Descartar | Aprobar (David, HITL-1)
```

Note: no `trace_id` field on the Shortlist schema — that field belongs to the V2
Publicaciones payload below, not V1.

### Required QA Checklist (V1 Alternativa)

Before handing an alternativa to `rick-qa` or David for HITL-1:

- [ ] `arco_narrativo` is present and describes an actual trajectory, not a single loose angle. **OBLIGATORIO.**
- [ ] `estructura_discurso` is present with the discourse structure actually used. **OBLIGATORIO.**
- [ ] `fuente_pieza_url` is the concrete-piece URL, never a home/feed page. **OBLIGATORIO.**
- [ ] `Resultado revisión` is `Pendiente` — never set by `rick-editorial`.
- [ ] Optional but recommended: consult the negative-examples store
      (`python scripts/editorial/sync_negative_examples.py --check-topic-key "<topic>" --check-error-kind <kind>`)
      to check whether this alternativa's topic/source resembles a previously `Descartar`'d
      candidate — see the negative-examples-log hook note below.
- [ ] Ready for HITL-1, not for promotion or publication.

## V2 Candidate Payload (Publicaciones, post-`Aprobar`)

```yaml
# --- Identity ---
publication_id: "CAND-NNN"
title: ""
trace_id: ""

# --- Classification ---
estado: Borrador
canal: ""                      # blog | linkedin | x | newsletter
tipo_de_contenido: ""          # blog_post | linkedin_post | x_post | newsletter | carousel | visual_asset | thread
etapa_audiencia: ""            # awareness | consideration | trust | conversion | retention | (empty)
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
visual_brief: ""              # legacy o YAML v2; docs/ops/editorial-visual-brief-v2-2026-08-29.md
visual_hitl_required: false    # true if people, brands, or sensitive content

# --- Review ---
comentarios_revision: ""
communication_review:
  required: false              # true for public-facing copy when voice/narrative quality is material
  status: ""                   # pending | pass | pass_with_changes | blocked_for_voice
  reviewer: ""                 # rick-communication-director or external curator
  voice_source: ""             # live_notion_guide | authorized_summary | marca_personal_docs | limited_evidence
  selected_variant: ""         # V1 | V2 | V3 | custom | empty
  notes: ""

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

### Required QA Checklist (V2 Candidate)

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
- [ ] Si usa Visual brief v2: declara hecho, consecuencia, metáfora núcleo,
      cinco ejes únicos y prohibiciones; cabe en 2000 caracteres y deja
      `engine` omitido/`pro` salvo pedido explícito de Flash.
- [ ] `trace_id` is set for trazabilidad.
- [ ] If public copy is involved, `communication_review` is present or explicitly marked not required.
- [ ] Public copy does not use `escalacion` as a noun.
- [ ] Voice validation reports phrases David probably would not say.
- [ ] Ready for David review, not ready for publication.

## Negative-examples-log hook (optional, cheap — see P2.5)

`scripts/editorial/sync_negative_examples.py` (P2.5) already provides a working,
Notion-network-free consult path over previously `Descartar`'d alternativas:

```bash
python scripts/editorial/sync_negative_examples.py \
  --check-topic-key "<candidate topic>" --check-error-kind <error_kind if known>
```

This is documented here as a **manual/Cursor-orchestrated step** for `rick-qa` (or
whoever validates a V1 alternativa) to run before finalizing a verdict — it is **not**
wired to fire automatically inside Rick's live QA pass. Automatic invocation during a
live OpenClaw run would require touching Rick's actual runtime behavior, which is a
separate, David-gated activation decision (same pattern as `rick-editorial`'s own
"Activation conditions" below) — out of scope for this docs/prompt-alignment package.

## Usage

1. Copy the relevant payload template above (V1 alternativa or V2 candidate).
2. Fill in the fields.
3. Save as a local file or structured document for review.
4. Hand to `rick-qa` (or manually validate using the matching QA checklist) — optionally
   consulting the negative-examples-log hook above for a V1 alternativa.
5. V1: David decides HITL-1 (Archivar/Observar/Descartar/Aprobar) on the alternativa.
   V2: once validated, register manually in Notion `Publicaciones` DB.
6. Re-run read-only audit after registration.

## References

- Output contract spec: `openclaw/workspace-agent-overrides/rick-editorial/ROLE.md`
- Contract (V1 alternativa fields, HITL-1): `docs/ops/editorial-norte-hitl-contract-2026-07-22.md` §3, §4
- Shortlist schema (live): `notion/schemas/alternativas-shortlist.schema.yaml`
- Publicaciones schema: `notion/schemas/publicaciones.schema.yaml`
- Negative-examples store (P2.5): `docs/ops/editorial-negative-loop-p25-2026-07-23.md`
- Test records: `docs/ops/notion-publicaciones-test-records.md`
- Setup runbook: `docs/ops/notion-publicaciones-setup-runbook.md`
