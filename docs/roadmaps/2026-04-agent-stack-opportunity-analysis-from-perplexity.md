# Opportunity Analysis: Agent Stack Improvements from Perplexity Research

> **Fecha**: 2026-04-21
> **Estado**: PROPUESTO — pendiente de revisión humana
> **Fuente primaria Perplexity no montada en VPS**; análisis basado en master index + specs/ADRs/docs capitalizados + código fuente del Agent Stack.
> **Complementa**: [roadmap principal](2026-04-capitalizacion-perplexity-rick-umbral-bot.md)

---

## 1. Resumen ejecutivo

### Oportunidades reales detectadas

- **Error classification en Worker**: el Agent Stack clasifica errores por substring matching (`"timeout"`, `"rate_limit"` en texto). UB-07 P4 documenta una taxonomía de antipatrones (MAST) con categorías estructuradas. Adaptar esa taxonomía al Worker daría escalación automática más precisa a Linear.
- **Approval gates para editorial**: la spec v1 define dos gates humanos (`aprobado_contenido`, `autorizar_publicacion`) pero el Agent Stack no tiene infraestructura genérica de approval queues. El flujo de `model_selected` con `requires_approval=true` ya bloquea tareas — extender ese patrón al editorial sería incremental.
- **Auth lifecycle tracking**: UA-10 documenta que LinkedIn access tokens expiran en 60 días sin refresh y que `LinkedIn-Version` header caduca trimestralmente. El Agent Stack tiene `quota_guard` y alertas de cuota pero no tiene tracking de auth expiry por credential. Es un failure mode no cubierto.
- **Gold set editorial antes de torneo de prompts**: UB-04 define 15 dimensiones de evaluación que pueden aplicarse a outputs editoriales. Sin gold set, el torneo de prompts (UA-06) no tiene baseline.
- **Research intake pipeline**: 46 documentos Perplexity indexados, 11 pendientes de integrar. No hay proceso sistemático para convertir research en specs/ADRs/tests. Cada capitalización es manual y ad-hoc.

### Cosas que NO aparecen

- No hay evidencia de que el Agent Stack necesite routing multi-KB estilo Umbral Bot. Rick no rutea entre knowledge bases; rutea entre equipos.
- No hay evidencia de que el supervisor de mejora continua necesite activación urgente. La fase 5/6 está en observabilidad pasiva y funciona.
- No hay evidencia de necesidad de panel admin para el Agent Stack. UB-06 es específico del bot.
- No hay evidencia de que Grasshopper/Rhino/APS apliquen al Agent Stack.

### Qué cambia respecto al roadmap anterior

- Se agregan 3 oportunidades transversales (T0-T2) no presentes en las fases E0-E7 ni B0-B6.
- Se identifica que E2 (generación de borradores) debería incluir un gold set editorial mínimo antes de E7 (torneo).
- Se identifican 2 hardening items para el Worker que son independientes del editorial.

---

## 2. Opportunity register

| ID | Oportunidad | Fuente | Evidencia | Inferencia | Área | Prioridad | Tipo | Impacto | Riesgo si no se hace | Próximo artefacto |
|----|-------------|--------|-----------|------------|------|-----------|------|---------|---------------------|-------------------|
| OPP-01 | Structured error classification en Worker | UB-07 P4 (MAST taxonomy) | Worker `service.py` clasifica errores por substring en mensajes de excepción. Linear escalation usa fingerprint de texto libre | Aplicar categorías estructuradas (timeout/auth/quota/upstream/data/config) mejora dedup en Linear y permite alertas por tipo | Worker, Linear | P1 | implementación | Reducción de issues duplicados en Linear; alertas más precisas | Issues duplicados, falsos positivos en escalación, triaje manual | Spec: `error-classification-v1.md` con enum de categorías |
| OPP-02 | Auth lifecycle tracking (LinkedIn, Ghost, APIs) | UA-10 §§3-4 | LinkedIn token 60d sin refresh. Ghost JWT 5min por request. `LinkedIn-Version` header caduca trimestralmente. Ninguno de estos tiene tracking en `ops_log.jsonl` | Agregar eventos `auth.expiry_warning`, `auth.refresh_failed`, `auth.version_obsolete` al OpsLogger. Alerta a Notion/Telegram cuando token se acerca a expiración | Infra, Editorial | P1 | implementación | Evitar publicaciones bloqueadas por auth expirado sin aviso | Publicación falla silenciosamente; David descubre días después | Agregar `auth_expiry` event type a `infra/ops_logger.py` |
| OPP-03 | Gold set editorial mínimo | UB-04 (15 dimensiones), UA-06 (torneo prompts) | UB-04 define dimensiones aplicables a cualquier output de agente: relevance, accuracy, completeness, tone, sourcing, CTA alignment, etc. UA-06 requiere baseline para comparar prompts | Crear gold set de ~10 piezas editoriales manualmente evaluadas por David antes de intentar torneo de prompts. Sin baseline, el torneo no tiene criterio de comparación | Editorial, Eval | P2 | eval | Torneo de prompts con criterio objetivo en vez de subjetivo | Torneo produce ganadores que no representan preferencias reales de David | Gold set: `editorial-gold-set-v1.yaml` con 10 piezas + scores |
| OPP-04 | Research intake pipeline / capitalización sistemática | Perplexity master index (46 docs, 11 pendientes) | Cada capitalización es manual: alguien lee, propone spec/ADR, lo ejecuta. No hay workflow ni metadata estándar para convertir research en acción | Definir metadata mínima por investigación: `status`, `capitalized_in`, `blocks_decision`, `next_action_type`, `priority`. Agregar columnas al master index | Research, Governance | P2 | governance | Capitalización predecible; reduce research que se queda como PDF muerto | 11 docs pendientes se acumulan; nuevas investigaciones no se convierten | Agregar columnas al `perplexity-master-index.md` |
| OPP-05 | Comment invalidation tracking | UA-10, Spec v1 §6 | Spec define que si David comenta después de `aprobado_contenido = true`, la aprobación se invalida. Agent Stack ya tiene comment hardening (doc 76-audit) pero no tracking de invalidaciones | Agregar evento `editorial.approval_invalidated` al OpsLogger con causa (new_comment, manual_override). Necesario para auditoría del flujo editorial | Editorial, Observability | P2 | implementación | Auditoría de cuántas veces David invalida aprobaciones; detectar patrones | Aprobaciones invalidadas sin registro; no se sabe si el flujo funciona bien | Agregar event type a OpsLogger |
| OPP-06 | CTA rate-limit enforcement | UA-12 §§7-8 | Spec define rate-limiting de CTA (≤1/5 piezas LinkedIn, ≤1/3 blog, 0 X por defecto). No hay implementación ni tracking | El rate-limit necesita tracking por canal y ventana temporal. Puede ser un campo derivado en Notion o un counter en Redis | Editorial | P2 | implementación | CTAs comerciales no saturan audiencia | Fatiga de audiencia; pérdida de credibilidad (Edelman data: 38% saturación percibida) | Spec: `cta-rate-limiter.md` con storage decision |
| OPP-07 | Publish attempt tracking | UA-10 §§2-4 | Spec define failure modes por canal (409 Ghost, 401/426 LinkedIn, 187 X). No hay tracking de intentos de publicación en ops_log | Agregar `publish.attempt`, `publish.success`, `publish.failed` events con canal, error_class, retry_count | Editorial, Observability | P1 | implementación | Visibilidad de pipeline de publicación; detección de fallos recurrentes | Fallos de publicación no detectados hasta que David pregunta | Agregar event types a OpsLogger |
| OPP-08 | Provider health tracking en Model Router | UB-07 P4 (antipatrones), código `model_router.py` | Model Router usa quota windows pero no trackea health (errores recientes, latencia). UB-07 P4 documenta antipatrón "retry storm" cuando provider está degradado pero no muerto | Agregar health score por provider basado en errores recientes (últimos 10 requests). Auto-demote a fallback si health < threshold, sin esperar quota exhaustion | Worker, Model Router | P2 | implementación | Failover más rápido; menos requests perdidos a providers degradados | Requests perdidos a provider degradado hasta que quota window se llena | Spec o implementación directa en `model_router.py` |
| OPP-09 | Eval suite para outputs de agente | UB-04 (15 dimensiones) | Agent Stack tiene 113 test files pero cero tests de calidad de outputs (¿research.web devuelve resultados útiles? ¿llm.generate produce texto coherente? ¿composite report es completo?) | No propongo eval completo ahora. Propongo 1 smoke eval: guardar 5 queries conocidas + expected outputs, correr semanalmente, alertar si quality baja | Worker, Eval | P3 | eval | Detección de regresiones en calidad de outputs | Degradación de calidad no detectada hasta que David nota respuestas peores | Gold set mínimo: `agent-output-gold-set-v0.yaml` |
| OPP-10 | Idempotency tracking para Notion writes | UA-10 §5.3, code audit | Notion writes en `worker/tasks/notion.py` son fire-and-forget. Spec v1 propone `content_hash` para dedup. Agent Stack no tiene dedup genérico para Notion operations | Para editorial: `content_hash` en DB `Publicaciones` (ya en spec v1 §5.1). Para Agent Stack general: no es urgente, pero anotar como debt. No necesita implementación separada si spec v1 se respeta | Editorial, Worker | P3 | implementación | Evitar publicaciones duplicadas; idempotencia en pipeline editorial | Publicación duplicada si retry ocurre después de write parcial | Ya cubierto por spec v1 §5.1 `content_hash` — solo verificar implementación |

---

## 3. Oportunidades para Agent Stack core

### 3.1 Structured error classification (OPP-01)

**Estado actual**: `dispatcher/service.py` captura excepciones y las serializa como string. `infra/ops_logger.py` registra `task_failed` con `error` como texto libre (max 500 chars). Linear auto-issue usa fingerprint basado en texto del error.

**Oportunidad**: UB-07 P4 documenta la taxonomía MAST (Mode-Agent-Scope-Type) para antipatrones multiagente. La clasificación de tipo es directamente aplicable:
- `timeout`: provider no responde en tiempo
- `auth`: credencial expirada o inválida
- `quota`: límite de uso alcanzado
- `upstream`: provider devuelve error (4xx/5xx)
- `data`: input malformado o output inesperado
- `config`: misconfiguration del Agent Stack

**Impacto**: dedup en Linear baja de texto libre a `(task_type, error_class)`. Alertas pueden dispararse por categoría, no por substring.

**Próximo paso**: spec corta con enum de error_class, mapping de excepciones conocidas, y cambio en `ops_logger.py` para registrar `error_class` como campo estructurado.

### 3.2 Provider health tracking (OPP-08)

**Estado actual**: `model_router.py` selecciona provider por quota window (rolling 1h-24h). Si un provider tiene errores pero no ha agotado quota, sigue recibiéndole tráfico.

**Oportunidad**: UB-07 P4 documenta el antipatrón "retry storm": un provider degradado (latencia alta, errores intermitentes) consume retry budget antes de que quota lo descarte. El model router ya trackea uso; agregar un health score (% de éxito en últimos N requests) permitiría auto-demote sin esperar quota.

**Impacto**: failover en segundos en vez de minutos. Menos requests perdidos.

**Próximo paso**: agregar `recent_success_rate` al `quota_tracker.py`. Si < 0.7 en últimos 10 requests, tratar como `warn` independiente de quota.

### 3.3 Supervisor observability ya cubierta

La fase 5/6 de supervisor observability está en estado pasivo y funcional. No hay oportunidad nueva aquí — la activación depende de la fase 6B que tiene su propio plan (`docs/77`).

---

## 4. Oportunidades para Rick Editorial

### 4.1 Auth lifecycle tracking (OPP-02)

**Estado actual**: el Agent Stack tiene `quota_guard` (cuota de LLM providers) pero no tracking de credenciales de publicación. LinkedIn tokens (60d), Ghost JWT (5min por request), y `LinkedIn-Version` header (trimestral) son todos failure modes documentados en UA-10 pero sin cobertura en `ops_log.jsonl`.

**Oportunidad**: agregar `auth.expiry_warning` como event type al OpsLogger. Un cron diario (o el health check existente) verifica fecha de emisión de tokens conocidos y emite warning si quedan < 7 días.

**Complejidad**: baja. El OpsLogger ya soporta event types arbitrarios. El health check ya corre cada 30 min.

### 4.2 Publish attempt tracking (OPP-07)

**Estado actual**: no hay tracking de intentos de publicación en ops_log. Cuando el editorial esté operativo, cada intento de publicar a Ghost/LinkedIn/X debería registrar: canal, status (success/failed), error_class si falla, platform_post_id si éxito, retry_count.

**Oportunidad**: agregar `publish.attempt`, `publish.success`, `publish.failed` al OpsLogger. Esto es prerequisite operativo para E4/E5/E6 del roadmap.

**Timing**: implementar cuando se construya el primer adapter de canal (Ghost), no antes.

### 4.3 Comment invalidation tracking (OPP-05)

**Estado actual**: spec v1 §6 define que un comentario post-aprobación invalida `aprobado_contenido`. El Agent Stack ya tiene comment hardening (audit 2026-03-17). Pero no hay evento de invalidación.

**Oportunidad**: cuando Rick detecte un comentario nuevo en una pieza `content_approved`, registrar `editorial.approval_invalidated` con page_id, comment_id, timestamp_since_approval. Esto da visibilidad de cuántas veces el ciclo de aprobación rebota.

### 4.4 CTA rate-limit enforcement (OPP-06)

**Estado actual**: UA-12 define reglas de rate-limiting de CTA (≤1/5 piezas LinkedIn, etc). No hay implementación.

**Oportunidad**: el counter puede ser un campo derivado en Notion (rollup o formula sobre últimas N piezas) o un counter en Redis. La decisión depende de si Rick calcula CTA al generar borrador (Redis) o al cambiar status (Notion formula).

**Timing**: resolver en E2 cuando se generen los primeros borradores.

### 4.5 Gold set editorial (OPP-03)

**Estado actual**: UA-06 propone torneo de prompts pero no hay baseline. UB-04 define 15 dimensiones que aplican a outputs editoriales.

**Oportunidad**: antes de E7 (torneo), David evalúa manualmente ~10 piezas contra un subset de dimensiones relevantes (relevance, tone, sourcing, CTA alignment, audience fit). Eso crea baseline para comparar prompts.

**Timing**: después de E2 (cuando existan borradores reales). No antes — gold set sin corpus es abstracto.

---

## 5. Oportunidades compartidas con Umbral Bot

### 5.1 Qué se reutiliza

| Concepto | Origen | Reutilizable en Agent Stack | Cómo |
|----------|--------|----------------------------|------|
| MAST error taxonomy | UB-07 P4 | Sí — categorías de error | Adaptar enum; no copiar framework completo |
| Evaluation dimensions | UB-04 | Parcial — dimensiones genéricas (relevance, accuracy, completeness) | Seleccionar subset; no copiar 15 dimensiones |
| KB package schema | UB-07 P2 / PR #71 | No directamente — Agent Stack no usa KB packages | Referencia conceptual para source curation metadata |
| Gold set framework | UB-04 | Sí — patrón de gold set con expected outputs | Aplicar al editorial y a agent outputs |
| `Fuentes confiables` DB | Notion existente | Sí — compartida | Ya documentado en ADR-007 |
| CTA taxonomy | UA-12 | Sí — Rick específico | No compartir con bot; es editorial |

### 5.2 Qué NO copiar

| Concepto | Razón |
|----------|-------|
| Routing multi-KB (UB-10) | Agent Stack rutea entre equipos, no entre knowledge bases. TeamRouter ya resuelve esto |
| Specialist activation | Específico del bot. Agent Stack tiene supervisor improvement pero es advisory, no specialist |
| Governance multiagente completa (UB-07 5 archivos) | Overkill para Agent Stack. Rick no tiene 5+ agentes especializados; tiene 1 dispatcher + 1 worker + OpenClaw |
| Panel admin (UB-06) | Específico del bot. Agent Stack usa Notion Control Room |
| Intake conversacional (UB-03) | Específico del bot. Rick no tiene flujo de intake |

### 5.3 Dónde vive cada cosa

| Artefacto | Vive en | Razón |
|-----------|---------|-------|
| `perplexity-master-index.md` | Agent Stack (este repo) | Es el coordinador de investigación; bot consume |
| Error classification spec | Agent Stack | Aplica al Worker de este stack |
| Gold set editorial | Agent Stack | Rick editorial es de este stack |
| Gold set BEP/PEB | Umbral Bot (umbral-bot-2) | Específico del bot |
| KB package schema | Umbral Bot (umbral-bot-2) | Específico del bot |
| Eval dimensions (subset genérico) | Documento transversal o duplicado controlado | Dimensiones genéricas aplican a ambos |
| `Fuentes confiables` | Notion (compartida) | Una sola DB; ambos la leen |

---

## 6. Roadmap delta

Cambios respecto al [roadmap principal](2026-04-capitalizacion-perplexity-rick-umbral-bot.md):

### Agregar a fases existentes

| Fase | Cambio | ID oportunidad |
|------|--------|----------------|
| E2 | Agregar: "definir subset de dimensiones de evaluación editorial para gold set futuro (de UB-04)" como tarea de diseño. No bloquea E2 pero prepara E7 | OPP-03 |
| E4 | Agregar: "implementar `publish.attempt/success/failed` events en OpsLogger" como prerequisite de publicación | OPP-07 |
| E4 | Agregar: "implementar `auth.expiry_warning` event para tokens de Ghost y LinkedIn" | OPP-02 |
| E5 | Agregar: "verificar comment invalidation tracking antes de LinkedIn HITL" | OPP-05 |

### Nuevos bloques transversales

| Bloque | Objetivo | Prioridad | Timing |
|--------|----------|-----------|--------|
| **T0 — Error classification v1** | Structured error_class enum en Worker + OpsLogger. Dedup mejorada en Linear | P1 | Puede hacerse ahora; no depende de editorial ni bot |
| **T1 — Research intake metadata** | Agregar columnas `next_action_type`, `priority`, `blocks_decision` al master index | P2 | Después de merge PR #249 |
| **T2 — Provider health score** | Auto-demote de providers degradados en model_router sin esperar quota exhaustion | P2 | Independiente; puede hacerse cuando haya bandwidth |

### Mover entre horizontes

| Item | De | A | Razón |
|------|-----|-----|-------|
| Gold set editorial | Later (E7) | Next (preparar en E2, ejecutar pre-E7) | Sin gold set, torneo de prompts no tiene baseline |
| CTA rate-limiting | Implícito en spec v1 | Next (resolver storage en E2) | Necesita decisión Redis vs Notion antes de generar borradores |

### No cambiar

- Fases B0-B6 del bot quedan igual. No hay oportunidad nueva para el bot desde este análisis.
- Fases E0, E1, E3, E6 quedan iguales.
- Anti-roadmap del roadmap principal queda vigente.

---

## 7. Nuevas solicitudes Perplexity

### Veredicto: no hace falta nueva investigación ahora

Las 46 investigaciones existentes cubren:
- Editorial completo (UA-01 a UA-12, de los cuales 9 son canónicos)
- Bot completo para v1 (UB-01 a UB-10 + 20 docs raíz)
- Visual, CTA, publicación, gobernanza, routing, evaluation

Los huecos detectados (error classification, auth lifecycle, provider health) son problemas de ingeniería del Agent Stack, no de investigación. Se resuelven con specs/implementación, no con más research.

**Única excepción potencial**: si David decide que el torneo de prompts (UA-06) necesita más profundidad sobre metodología de A/B testing editorial con LLMs, podría justificarse UA-13. Pero eso es E7 y está en Later. No bloquea nada ahora.

---

## 8. Anti-roadmap actualizado

Además de los 12 items del [roadmap principal §7](2026-04-capitalizacion-perplexity-rick-umbral-bot.md):

| # | Prohibición | Razón |
|---|-------------|-------|
| 13 | No crear framework de gobernanza multiagente para Agent Stack | Rick no tiene 5+ agentes especializados. TeamRouter + supervisor pasivo son suficientes. UB-07 es para el bot |
| 14 | No copiar routing multi-KB al Agent Stack | Agent Stack rutea entre equipos, no entre knowledge bases. Son problemas distintos |
| 15 | No crear eval suite completo antes de tener corpus de outputs reales | Eval sin datos es especulativo. Primero generar borradores (E2), después evaluar (E7) |
| 16 | No agregar dashboards de observabilidad sin caso de uso operativo concreto | Cada métrica debe responder: "¿qué acción tomo cuando este número cambia?" |
| 17 | No solicitar nueva investigación Perplexity salvo hueco que bloquee decisión concreta en fase activa | 46 docs son suficientes. Más research sin capitalización agrava el problema |
| 18 | No implementar circuit breaker completo para el model router | Provider health score (OPP-08) es suficiente. Circuit breaker full es overengineering para el volumen actual |

---

## 9. Recomendación final

**Actualizar roadmap actual ahora** con el delta de §6. Específicamente:

1. **Merge este documento** junto con el roadmap en PR #249.
2. **T0 (error classification)** puede ejecutarse como PR independiente en cualquier momento — no depende del editorial ni del bot. Es el item de mayor impacto-por-esfuerzo.
3. **OPP-02 y OPP-07** (auth lifecycle + publish tracking) deben implementarse cuando se construya el primer adapter de canal (Ghost, en E4). No antes.
4. **OPP-03** (gold set editorial) se prepara conceptualmente en E2 y se ejecuta antes de E7. No bloquea nada intermedio.
5. **No crear ADR nuevo** para estas oportunidades. Son implementaciones incrementales que caben en specs cortas o directamente en PRs.

El roadmap principal no necesita reestructuración. Los cambios son aditivos: 3 bloques transversales, 4 items en fases existentes, 1 item movido de Later a Next.
