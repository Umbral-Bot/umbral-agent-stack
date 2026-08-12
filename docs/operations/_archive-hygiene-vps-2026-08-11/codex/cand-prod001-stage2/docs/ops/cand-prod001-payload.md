# CAND-PROD-001 — Editorial Candidate Payload (Production Soak · STAGE2)

> **Date**: 2026-06-06
> **Type**: Source-driven editorial candidate (production soak)
> **Generator**: Rick (OpenClaw VPS) simulando `rick-editorial` — design-only, **No runtime activation**.
> **Stage**: STAGE2_PAYLOAD — Decision Brief + framing + payload. **NO copy final, NO publish, NO Notion write, NO gates.**
> **Source intake**: `docs/ops/cand-prod001-source-intake.md`
> **Attribution policy**: `docs/ops/editorial-source-attribution-policy.md`

---

## A. Trace IDs / Run IDs (editorial, no gateway-exec)

> Identificadores **editoriales/de proceso**, deterministas. NO son logs de ejecución del `openclaw-gateway` (este stage es design-only; no se ejecutó ningún run de gateway). Honestidad runtime: ninguna afirmación de ejecución en VPS.

```yaml
trace_id: "CAND-PROD001-trazabilidad-cierre-decisiones"
soak_run_id: "SOAK-EDIT-2026-06-06-CANDPROD001-01"
stage: "STAGE2_PAYLOAD"
stage_status: "READY"
gateway_execution: false          # design-only; sin run de openclaw-gateway
created_at: "2026-06-06"
operator: "rick-editorial (simulado por Rick OpenClaw VPS)"
```

---

## B. Decision Brief

**Problema editorial.** En AEC ya circula la conversación sobre escalar IA en flujos BIM. Las dos candidatas previas cubrieron *preparación organizacional* (CAND-002) y *criterios de aceptación antes de automatizar* (CAND-003). Queda una superficie de falla sin tocar: **la decisión misma**. En muchos proyectos las decisiones se toman en reuniones, chats y correos, y nunca reciben un estado formal de "cerrado" ni un registro reconstruible (quién, cuándo, sobre qué base). Escalar IA sobre ese sustrato no lo limpia: lo hereda y lo amplifica.

**Tesis (dedup-safe).** El factor que más limita el valor de escalar IA en flujos BIM no es la madurez del equipo ni la falta de criterios de aceptación, sino que **las decisiones de proyecto no son trazables ni están formalmente cerradas**. Una IA que opera sobre un registro de decisiones incompleto amplifica la ambigüedad y traslada la deuda de decisión aguas abajo, donde corregir cuesta más.

**Por qué es defendible sin inventar datos.** La disciplina ya existe y es citable: ISO 19650 define el CDE con estados (WIP → Compartido → Publicado → Archivado) y transiciones de revisión/autorización; buildingSMART publica BCF, un formato abierto que registra incidencias/decisiones con autor, fecha y estado. El marco para trazar y cerrar decisiones está estandarizado; la brecha es de implementación. La tesis es una `inferencia_con_fuentes` (síntesis), no una afirmación estadística.

**Decisión editorial.** Ángulo `pattern_synthesis`: combinar la disciplina BIM de gestión de información (ISO 19650 / BCF) con la conversación de IA sobre provenance/auditabilidad de decisiones automatizadas, para producir una tesis que ninguna fuente dice sola: *antes de escalar IA, hacé reconstruibles y cerrables tus decisiones — porque la IA va a heredar cada decisión abierta*.

**Qué NO hace esta pieza.** No dice "no automaticen" (no es contrarian). No repite "preparate primero" (CAND-002) ni "definí el criterio primero" (CAND-003). No expone sistemas internos de Umbral. No cita referentes como autoridad pública. No afirma estadísticas sin fuente primaria.

---

## C. Framing AEC

- **Vocabulario nativo.** La tesis se ancla en términos que la audiencia AEC ya reconoce: *Common Data Environment (CDE)*, *estados de aprobación/autorización*, *BCF / registro de incidencias*, *RFI*, *coordinación de modelos federados*, *órdenes de cambio*. No se importa jerga de otra industria.
- **Tensión central.** El marco para trazar y cerrar decisiones **existe y está normado** (ISO 19650, BCF), pero su implementación es dispar. La IA no crea ese problema; lo vuelve caro, porque automatiza sobre el hueco.
- **Reencuadre de "audit trail".** No como burocracia, sino como **precondición para que la IA sea confiable**: sin traza ni cierre, la IA no puede distinguir "decidido y cerrado" de "asumido como cerrado".
- **Riesgo de lectura a evitar.** Que suene a "más documentación por documentar". El framing debe dejar claro que el objetivo es *valor y confiabilidad al escalar IA*, no compliance por compliance.

---

## D. Payload

```yaml
# --- Identity ---
publication_id: "CAND-PROD-001"
title: "Antes de escalar IA en BIM: ¿podés reconstruir y cerrar tus decisiones?"
trace_id: "CAND-PROD001-trazabilidad-cierre-decisiones"
soak_run_id: "SOAK-EDIT-2026-06-06-CANDPROD001-01"

# --- Classification ---
estado: Borrador
canal: linkedin
tipo_de_contenido: linkedin_post
etapa_audiencia: awareness
prioridad: media

# --- Editorial content ---
premisa: >
  En flujos BIM, muchas decisiones se toman pero nunca se cierran ni se vuelven
  reconstruibles: quedan en chats, reuniones y memorias individuales. Escalar IA
  sobre ese sustrato no resuelve el problema — lo hereda y lo amplifica, porque la
  IA actúa sobre decisiones abiertas, sin autor, sin fecha y sin fundamento recuperable.

claim_principal:
  texto: >
    El factor que más limita el valor de escalar IA en flujos BIM no es la madurez
    del equipo ni la falta de criterios de aceptación, sino que las decisiones de
    proyecto no son trazables ni están formalmente cerradas. Una IA que opera sobre
    un registro de decisiones incompleto amplifica la ambigüedad y traslada la deuda
    de decisión aguas abajo, donde corregir cuesta más.
  tipo: inferencia_con_fuentes
  requiere_fuente_primaria: false   # la tesis es síntesis; los conceptos de soporte sí están anclados (ISO 19650, BCF)
  claim_type: inferencia_con_fuentes

angulo_editorial: >
  pattern_synthesis. Combina la disciplina BIM de gestión de información (ISO 19650
  CDE, BCF) con la conversación de IA sobre provenance/auditabilidad de decisiones
  automatizadas. Produce una tesis nueva: antes de escalar IA, hacé reconstruibles y
  cerrables tus decisiones, porque la IA hereda cada decisión abierta.

# --- Objetivo comercial ---
objetivo_comercial:
  posicionamiento: >
    Posicionar a Umbral BIM como el socio que instala trazabilidad y cierre de
    decisiones (registro de decisiones, estados de aprobación, audit trail) como capa
    previa a escalar IA en AEC.
  audiencia_objetivo: "Directores de transformación digital y coordinadores BIM que ya evalúan automatización/IA."
  cta_tipo: "diagnóstico"            # de los 5 permitidos: diagnóstico | checklist | newsletter | recurso | conversación
  cta_intencion: "Diagnóstico de trazabilidad/cierre de decisiones — entrada suave, no venta directa."
  etapa_embudo: awareness
  no_vender_directo: true

# --- Sources (ver source-intake para clasificación completa) ---
fuentes:
  fuente_primaria:
    estado: "anclas_conceptuales_citables"
    nota: >
      Tesis por síntesis. Anclas citables: ISO 19650 (estados CDE y transiciones de
      revisión/autorización) y buildingSMART BCF (registro de incidencias/decisiones).
      No se afirma ninguna estadística.
  fuente_referente:
    nota: "Discovery interno: Burcin Kaplanoglu, Ignasi Perez Arnal (DB Referentes). NO citar en copy."

source_classification:
  - source_name: "ISO 19650-1 / 19650-2"
    type: official_doc
    public_citable: true
    internal_trace_only: false
    public_citation: "ISO 19650 (como norma/organización)"
  - source_name: "buildingSMART — BCF"
    type: official_doc
    public_citable: true
    internal_trace_only: false
    public_citation: "buildingSMART / BCF (como organización/estándar)"
  - source_name: "DeepLearning.AI / The Batch (provenance de agentes)"
    type: analysis_source
    public_citable: true
    internal_trace_only: false
    verification_status: pending_verification
    public_citation: "DeepLearning.AI / The Batch (como organización)"
    dedup_note: "Ángulo provenance/decision-log; NO reusar #340 ni #343 (CAND-003)."
  - source_name: "Burcin Kaplanoglu"
    type: discovery_source
    public_citable: false
    internal_trace_only: true
    public_citation: "NO citar en copy público"
  - source_name: "Ignasi Perez Arnal"
    type: discovery_source
    public_citable: false
    internal_trace_only: true
    public_citation: "NO citar en copy público"

# --- AEC framing ---
aec_framing:
  vocabulario: ["CDE", "estados de aprobación/autorización", "BCF", "RFI", "modelos federados", "órdenes de cambio"]
  tension_central: >
    El marco para trazar y cerrar decisiones existe y está normado (ISO 19650, BCF),
    pero la implementación es dispar. La IA no crea ese hueco; lo vuelve caro al
    automatizar sobre él.
  reencuadre: "Audit trail = precondición de IA confiable, no burocracia."
  riesgo_de_lectura: "Evitar que suene a 'documentar por documentar'. El objetivo es valor y confiabilidad al escalar IA."

# --- 3 escenas operativas (framing, NO copy) ---
escenas_operativas:
  - id: ESC-1
    nombre: "Clash resuelto en reunión, no en el modelo"
    situacion: >
      Una interferencia MEP–estructura se "resuelve" verbalmente en coordinación.
      Nadie registra la decisión en BCF ni actualiza el estado en el CDE.
    falla_de_decision: "Decisión existente pero no trazada ni cerrada."
    amplificacion_ia: >
      Semanas después, un asistente IA de coordinación re-detecta el mismo clash como
      abierto y dispara una acción redundante — o propone una solución que contradice
      el acuerdo no registrado.
    artefacto_bim: ["BCF", "estado CDE"]

  - id: ESC-2
    nombre: "Cambio de criterio sin autoría ni fecha"
    situacion: >
      Se cambia el criterio de modelado de un sistema (p. ej. nivel de desarrollo de
      instalaciones) por una conversación de chat. No queda quién lo decidió, cuándo,
      ni con qué fundamento.
    falla_de_decision: "Decisión sin autor, sin fecha, sin fundamento recuperable."
    amplificacion_ia: >
      Al conectar una IA para auto-validar entregables contra el criterio, valida
      contra el criterio viejo (el único documentado) y aprueba/escala lo incorrecto
      a escala. La automatización hereda una decisión abierta.
    artefacto_bim: ["criterio de modelado", "control de versiones documental"]

  - id: ESC-3
    nombre: "Aprobación que nadie puede reconstruir"
    situacion: >
      Un entregable pasa de "compartido" a "publicado" en el CDE, pero la base de la
      aprobación (qué se revisó, qué se aceptó condicionalmente, qué quedó pendiente)
      vive en la memoria del coordinador.
    falla_de_decision: "Estado 'cerrado' sin evidencia reconstruible del cierre."
    amplificacion_ia: >
      Al escalar IA para acelerar el ciclo de aprobación, el sistema no distingue
      "cerrado" de "asumido como cerrado", y arrastra deuda de decisión aguas abajo,
      donde el costo de corrección es mayor.
    artefacto_bim: ["transición de estado CDE", "registro de aprobación"]

# --- Per-channel copies (DIFERIDO — no se genera en STAGE2) ---
copies:
  copy_linkedin: ""    # NO generar en STAGE2 (Decision Brief + framing solamente)
  copy_x: ""
  copy_blog: ""
  copy_newsletter: ""

# --- Visual ---
visual:
  visual_brief: >
    (Diferido a stage de copy) Concepto tentativo: línea de tiempo de una decisión BIM
    con dos trayectorias — una "trazada y cerrada" (autor, fecha, estado, evidencia) y
    otra "abierta" que se diluye; al final, una capa IA que hereda ambas. Sin interfaces
    internas ni marcas de terceros.
  visual_hitl_required: true

# --- Review ---
revision:
  comentarios_revision: >
    Candidata source-driven de production soak. Tesis dedup-safe vs CAND-002/003.
    Anclas citables ISO 19650 + BCF; sin estadísticas afirmadas. Copy diferido.
  responsable_revision: David Moreira
  qa_requerida: true
  qa_owner: rick-qa
  communication_review:
    required: true
    status: "pending"
    voice_source: "limited_evidence"   # benchmark-umbral-voice-v1.yaml no existe; usar dimensions.yaml + gold-set-minimum.yaml en copy stage
    notes: "Voice QA pendiente para stage de copy; benchmark de voz declarado no existe en repo (ver source-intake §0)."

# --- Human gates (never set by rick-editorial) ---
gates:
  aprobado_contenido: false
  autorizar_publicacion: false
  gate_invalidado: false

# --- Post-publication (empty) ---
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
  content_hash: ""
  idempotency_key: ""
  proyecto: "Sistema Editorial Rick"
  trace_id: "CAND-PROD001-trazabilidad-cierre-decisiones"

# --- Acceptance checklist (STAGE2) ---
acceptance_checklist:
  publication_id_unique: true
  estado_borrador: true
  gates_false: true
  no_publication_fields: true
  no_notion_write: true
  no_runtime_activation: true
  no_unverified_factual_claims: true     # ninguna estadística afirmada
  source_classification_present: true
  dedup_vs_cand002_cand003: true
  copy_deferred: true                    # STAGE2: Decision Brief + framing solamente
  ready_for_human_review: true
  ready_for_publication: false
```

---

## E. Handoff a Codex (evidencia en repo)

```yaml
handoff:
  to: Codex
  intent: "Registrar evidencia del soak STAGE2 (sin merge a runtime, sin Notion, sin gates)."
  files:
    - docs/ops/cand-prod001-source-intake.md
    - docs/ops/cand-prod001-payload.md
  branch_suggestion: "codex/docs-cand-prod001-soak-stage2"
  do_not:
    - "No generar copy LinkedIn final (stage de copy es posterior)."
    - "No escribir en Notion ni tocar gates."
    - "No marcar el soak como published."
  next_stage_inputs_needed:
    - "Verificar issue específico de The Batch (provenance) — pending_verification."
    - "benchmark-umbral-voice-v1.yaml (no existe) o confirmar uso de dimensions.yaml + gold-set-minimum.yaml para voice QA."
    - "Definición formal del soak: docs/ops/editorial-production-soak-2026-06-05.md (no existe) si debe regir parámetros adicionales."
```

---

## F. Referencias

- Source intake: `docs/ops/cand-prod001-source-intake.md`
- Política de atribución: `docs/ops/editorial-source-attribution-policy.md`
- Template payload: `docs/ops/rick-editorial-candidate-payload-template.md`
- Dedup: `docs/ops/cand-002-payload.md`, `docs/ops/cand-003-payload.md`
- Voz (proxy benchmark): `evals/editorial/dimensions.yaml`, `evals/editorial/gold-set-minimum.yaml`
