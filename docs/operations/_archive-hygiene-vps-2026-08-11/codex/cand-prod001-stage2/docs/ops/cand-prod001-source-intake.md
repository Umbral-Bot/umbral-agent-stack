# CAND-PROD-001 — Source Intake (Editorial Production Soak)

> **Date**: 2026-06-06
> **Operator**: Rick (OpenClaw VPS) simulando `rick-editorial` — design-only, sin runtime activation.
> **Soak**: Editorial Production Soak · `SOAK-EDIT-2026-06-06-CANDPROD001-01`
> **Stage**: STAGE2 (source-intake + payload). NO copy, NO publish, NO Notion write, NO gates.
> **Thesis target**: Trazabilidad y cierre de decisiones antes de escalar IA en flujos BIM.
> **Source DB**: Notion "Referentes" (`05f04d48c44943e8b4acc572a4ec6f19`), vista `71d3f67ec4214b898cf1f43e3c034e2f` — misma que CAND-002 (snapshot documentado en `cand-002-source-intake.md`; lectura del snapshot del repo, sin query live ni write).
> **Attribution policy**: `docs/ops/editorial-source-attribution-policy.md` (aplicada desde el inicio).

---

## 0. Reality check de inputs (Repo dice X vs realidad del repo)

| Input declarado en el prompt | Estado real en el repo | Decisión |
|---|---|---|
| `docs/ops/editorial-source-attribution-policy.md` | **EXISTE** | Usado como gobierno de clasificación de fuentes. |
| `docs/ops/editorial-production-soak-2026-06-05.md` | **NO EXISTE** (sin referencias en el repo) | No bloquea: el prompt mismo define el soak (tema, dedup, entregables, veredicto). Se toma el prompt como definición de soak de referencia. |
| `evals/editorial/benchmark-umbral-voice-v1.yaml` | **NO EXISTE** | No bloquea STAGE2: el copy se difiere explícitamente. Proxy de voz disponible: `evals/editorial/dimensions.yaml` + `evals/editorial/gold-set-minimum.yaml`. Se reserva el benchmark de voz para el stage de copy. |

Conclusión: 1 de 3 inputs presente es suficiente para STAGE2 (source-intake + payload), porque el input que gobierna este stage —la política de atribución— está presente, y el resto se difiere al stage de copy.

---

## 1. Criterio de selección de señales para esta tesis

Tesis distinta a las dos candidatas previas (ver §4 dedup). Señales priorizadas:

- **Registro de decisiones / decision records** y su ausencia en flujos de proyecto.
- **Estados de aprobación y autorización** en entornos de datos comunes (CDE) — ISO 19650.
- **Formato abierto de trazabilidad de incidencias/decisiones** en BIM — BCF (buildingSMART).
- **Provenance / audit trail de acciones automatizadas** en gobernanza de IA/agentes.
- **Deuda de decisión** (decisiones tomadas pero no cerradas ni reconstruibles) y su amplificación al escalar IA.

Señales NO priorizadas (pertenecen a tesis previas): madurez/preparación organizacional (CAND-002) y definición de criterios de aceptación/escalación previa a automatizar (CAND-003).

---

## 2. Fuentes analizadas y clasificadas

### 2.1 Citables (públicas) — anclan el concepto, sin estadísticas inventadas

| # | Fuente | Tipo | Citable | Ancla para la tesis |
|---|--------|------|---------|---------------------|
| 1 | **ISO 19650-1 / -2 — Information management using BIM (CDE)** | `official_doc` / `primary_source` | Sí (como norma/organización) | El CDE define estados de contenedor (WIP → Compartido → Publicado → Archivado) y transiciones de revisión/autorización. La trazabilidad y el cierre de decisiones **ya son una disciplina normada**: el problema es implementación dispar, no ausencia de marco. |
| 2 | **buildingSMART — BIM Collaboration Format (BCF)** | `official_doc` | Sí (como organización/estándar) | Estándar abierto que registra incidencias/decisiones con autor, fecha, estado y comentarios. **El audit trail de decisiones tiene formato estándar**: la brecha es de uso, no de herramienta. |
| 3 | **DeepLearning.AI / The Batch — gobernanza/provenance de agentes** | `analysis_source` | Sí (como organización) — **issue específico `pending_verification`** | Conversación de industria sobre auditabilidad/provenance de decisiones automatizadas. Marca el puente "IA que actúa sobre decisiones sin trazar". *Dedup*: ángulo provenance/decision-log, distinto a #340 (AVERI audits) y #343 (agent permissions) usados en CAND-003. |

> Disciplina de fuente primaria: la tesis es `inferencia_con_fuentes` (síntesis). No se afirma ninguna estadística. Cualquier dato cuantitativo queda marcado `pending_verification` y se resuelve recién en el stage de copy con fuente primaria fetcheada. Coherente con `gold-set-minimum.yaml` (must_avoid: inventar estadísticas).

### 2.2 Discovery (solo traza interna) — NO citables en copy público

| # | Referente (DB Referentes) | Tipo | Citable | Rol |
|---|---------------------------|------|---------|-----|
| 4 | **Burcin Kaplanoglu** (#2 — BIM, IA, Construction 4.0, Digital Twins) | `discovery_source` | No | Camino de descubrimiento para la señal BIM+IA sobre confiabilidad/trazabilidad del dato de proyecto. No usado como discovery primario en CAND-002/003 → mantiene el intake fresco. |
| 5 | **Ignasi Perez Arnal** (#6 — BIM Academy / European BIM Summit) | `discovery_source` | No | Camino de descubrimiento para el framing ISO 19650 / information management. No usado como discovery primario en CAND-002/003. |

### 2.3 Reference contextual / excluidas por dedup

| Fuente | Decisión | Razón |
|--------|----------|-------|
| **Aelion.io / Iván Gómez** | Excluida (no relevante a esta tesis) | Ya usada en CAND-002 (evidencia) y CAND-003 (contextual). Reusarla erosiona el dedup y no aporta a trazabilidad/cierre. |
| **Marc Vidal** | No usar como discovery aquí | Discovery primario en CAND-002/003. Reusarlo concentraría el camino de descubrimiento; se prioriza Kaplanoglu/Perez Arnal (AEC-direct). |

---

## 3. Source classification (per attribution policy)

```yaml
source_classification:
  - source_name: "ISO 19650-1 / 19650-2 — Information management using BIM (CDE)"
    source_url: "https://www.iso.org/standard/68078.html"
    type: official_doc
    public_citable: true
    internal_trace_only: false
    reason: >
      Norma que define el Common Data Environment, los estados de contenedor
      (WIP/Compartido/Publicado/Archivado) y las transiciones de revisión y
      autorización. Ancla conceptual de trazabilidad y cierre de decisiones.
    public_citation: "ISO 19650 (como norma/organización)"
    original_source_url: "https://www.iso.org/standard/68078.html"
    original_source_name: "ISO"

  - source_name: "buildingSMART — BIM Collaboration Format (BCF)"
    source_url: "https://www.buildingsmart.org/standards/bsi-standards/bim-collaboration-format-bcf/"
    type: official_doc
    public_citable: true
    internal_trace_only: false
    reason: >
      Estándar abierto que registra incidencias/decisiones con autor, fecha,
      estado y comentarios. Demuestra que el audit trail de decisiones tiene
      formato estándar; la brecha es de implementación.
    public_citation: "buildingSMART / BCF (como organización/estándar)"
    original_source_url: "https://www.buildingsmart.org/standards/bsi-standards/bim-collaboration-format-bcf/"
    original_source_name: "buildingSMART International"

  - source_name: "DeepLearning.AI / The Batch — provenance y supervisión de agentes"
    source_url: "https://www.deeplearning.ai/the-batch"
    type: analysis_source
    public_citable: true
    internal_trace_only: false
    reason: >
      Newsletter con análisis original sobre auditabilidad y provenance de
      decisiones automatizadas. Issue específico pendiente de verificación para
      evitar solapamiento con #340/#343 ya usados en CAND-003.
    public_citation: "DeepLearning.AI / The Batch (como organización)"
    verification_status: pending_verification
    dedup_note: "Usar ángulo provenance/decision-log; NO reusar #340 (AVERI) ni #343 (agent permissions)."

  - source_name: "Burcin Kaplanoglu"
    source_url: "https://www.linkedin.com/in/burcinkaplanoglu/"
    type: discovery_source
    public_citable: false
    internal_trace_only: true
    reason: "Referente BIM+IA. Camino de descubrimiento, no fuente original."
    public_citation: "NO citar en copy público"

  - source_name: "Ignasi Perez Arnal"
    source_url: "https://www.linkedin.com/in/ignasiperezarnal/"
    type: discovery_source
    public_citable: false
    internal_trace_only: true
    reason: "Referente BIM/ISO 19650. Camino de descubrimiento, no fuente original."
    public_citation: "NO citar en copy público"
```

---

## 4. Dedup vs CAND-002 y CAND-003 (obligatorio)

| Eje | CAND-002 | CAND-003 | CAND-PROD-001 (este) |
|-----|----------|----------|----------------------|
| Tesis | Capacidad vs preparación: el cuello de botella es la organización, no la herramienta. | Criterio antes que automatización: definir qué es revisión válida / cuándo escalar antes de automatizar. | **Trazabilidad y cierre de decisiones**: la IA hereda y amplifica las decisiones que no son reconstruibles ni están formalmente cerradas. |
| Pregunta al lector | ¿Está tu equipo listo para trabajar distinto? | ¿Definiste el criterio de aceptación antes de automatizar? | ¿Podés reconstruir quién decidió qué, cuándo y sobre qué base — y saber si esa decisión está cerrada? |
| Fuente ancla | The Batch (#342/#346/#348/#349), The B1M, Vidal, Aelion | The Batch #340/#343, OECD 79%, McKinsey 30%, AVERI | **ISO 19650 (CDE states), BCF (buildingSMART)** + The Batch (provenance, issue pending) |
| Superficie de falla | Madurez de personas/procesos | Ausencia de criterios de input/gates | **Registro de decisiones inexistente o no cerrado (decision audit trail)** |

**Por qué no solapa:** un equipo puede estar preparado (CAND-002) y tener criterios de aceptación (CAND-003) y aun así operar un proyecto donde las decisiones se evaporan en chats/reuniones y nunca reciben un estado "cerrado". Esa brecha de traza/cierre es la superficie específica de CAND-PROD-001. Fuentes ancla nuevas (ISO 19650 + BCF) que no fueron las anclas de las candidatas previas.

---

## 5. Fuentes intentadas pero no usables / pendientes

| Fuente | Estado | Acción |
|--------|--------|--------|
| The Batch (issue provenance específico) | `pending_verification` | Fetchear issue concreto en stage de copy; no afirmar número/issue hasta verificar. |
| Estadísticas de adopción de CDE/BCF en proyectos | No buscadas / no afirmadas | Prohibido inventar (gold-set must_avoid). Si se requiere dato, fetchear primaria en copy stage. |

---

## 6. Referencias

- Política de atribución: `docs/ops/editorial-source-attribution-policy.md`
- Template payload: `docs/ops/rick-editorial-candidate-payload-template.md`
- Dimensiones de voz (proxy benchmark): `evals/editorial/dimensions.yaml`
- Gold set (proxy benchmark): `evals/editorial/gold-set-minimum.yaml`
- DB Referentes snapshot (misma vista que CAND-002): `docs/ops/cand-002-source-intake.md`
- Dedup: `docs/ops/cand-002-payload.md`, `docs/ops/cand-003-payload.md`
- Payload de este candidato: `docs/ops/cand-prod001-payload.md`
