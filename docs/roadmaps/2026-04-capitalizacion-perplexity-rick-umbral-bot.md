# Roadmap: Capitalización Perplexity — Rick Editorial y Umbral Bot

> **Fecha**: 2026-04-21
> **Estado**: PROPUESTO — pendiente de revisión humana
> **Contexto PR**: umbral-agent-stack PR #249, umbral-bot-2 PR #70 (draft), umbral-bot-2 PR #71 (draft)
> **Autor**: Copilot (sesión de capitalización)

---

## 1. Resumen ejecutivo

- **Rick Editorial**: 14 investigaciones Perplexity (UA-01 a UA-14) están indexadas y 11 son canónicas. Cuatro ADRs y una spec v1 completa formalizan las decisiones de publicación, visual, Notion y orquestación. Falta aprobación humana para crear estructuras en Notion y conectar canales reales.
- **Umbral Bot**: 10 investigaciones temáticas (UB-01 a UB-10) + 20 documentos raíz indexados. PR #70 formaliza docs conceptuales; PR #71 entrega el primer artefacto ejecutable (`kb-package.schema.json` + `bep-peb.yaml`). Gold Set mínimo debe preceder routing.
- **Compartido**: `Fuentes confiables` (Notion DB) es el único recurso compartido entre ambos proyectos. El `perplexity-master-index.md` es la referencia canónica para toda investigación.
- **Regla general**: no implementar automatización sin gates humanos; no activar routing sin gold set; no publicar sin `autorizar_publicacion = true`.
- **Inmediato**: revisar y aprobar PR #249, PR #70, PR #71. Aprobar ADRs y spec v1. Después crear Notion structures.
- **Diferido**: routing implementation, specialist activation, panel admin, recomendaciones comerciales, Grasshopper/Rhino, torneo de prompts.

---

## 2. Decisiones ya tomadas

| # | Decisión | Fuente |
|---|----------|--------|
| 1 | Notion como hub editorial v1 | [ADR-007](../adr/ADR-007-notion-como-hub-editorial.md) |
| 2 | Crear solo `Publicaciones` + `Perfil editorial David` en Notion v1 | [Spec v1 §4](../specs/sistema-editorial-rick-v1.md) |
| 3 | `PublicationLog` queda v1.1/futuro; tracking inline en `Publicaciones` | [Spec v1 §5.3](../specs/sistema-editorial-rick-v1.md) |
| 4 | Dos gates humanos: `aprobado_contenido` y `autorizar_publicacion` | [Spec v1 §6](../specs/sistema-editorial-rick-v1.md) |
| 5 | Blog (Ghost self-hosted) automatizable primero | [ADR-005](../adr/ADR-005-publicacion-multicanal.md) |
| 6 | LinkedIn HITL obligatorio (ToS §3.1.26) | [ADR-005](../adr/ADR-005-publicacion-multicanal.md) |
| 7 | X asistido v1; API directa diferida a v2 | [ADR-005](../adr/ADR-005-publicacion-multicanal.md) |
| 8 | Vertex AI / Gemini 3 Pro Image como primario visual; Freepik fallback/stock | [ADR-006](../adr/ADR-006-capa-visual-editorial.md) |
| 9 | No routing Umbral Bot antes de Gold Set mínimo | [Capitalization plan — matriz](../research/umbral-bot-capitalization-plan.md) |
| 10 | No specialist activation antes de resolver latencia/calidad/UX | [Capitalization plan — diferidos](../research/umbral-bot-capitalization-plan.md) |
| 11 | KB Package YAML Contracts como artefacto fundacional P1 | [Capitalization plan §1](../research/umbral-bot-capitalization-plan.md) |
| 12 | Perfil editorial derivado de UA-01 (dolor/audiencia) + UA-02 (autoridad) | [Spec v1 §4.3](../specs/sistema-editorial-rick-v1.md) |
| 13 | API-first obligatorio para herramientas visuales de terceros; UI automation prohibida | [ADR-006](../adr/ADR-006-capa-visual-editorial.md) (actualizado con UA-13) |
| 14 | Freepik API/MCP oficial como vía autorizada; Freepik UI automation prohibida | [ADR-006](../adr/ADR-006-capa-visual-editorial.md) (UA-13) |
| 15 | Preview models no primarios de producción hasta GA/IP indemnification | [ADR-006](../adr/ADR-006-capa-visual-editorial.md) (UA-13) |
| 16 | Orquestación editorial: Agent Stack core + n8n bordes + Make lab/stand-by | [ADR-008](../adr/ADR-008-orquestacion-editorial.md) (UA-14) |
| 17 | n8n con Postgres desde día 1 (no SQLite en producción) | [ADR-008](../adr/ADR-008-orquestacion-editorial.md) (UA-14) |
| 18 | No crear DB separada `Assets Visuales Rick` en v1; assets inline en `Publicaciones` | [Spec v1 §9.1](../specs/sistema-editorial-rick-v1.md) (reconciliación UA-13 vs decisión David) |

---

## 3. Roadmap Rick Editorial

### Fase E0 — Cierre documental y aprobación humana

| Campo | Detalle |
|-------|---------|
| **Objetivo** | David revisa y aprueba PR #249, ADRs y spec v1 antes de crear nada en Notion |
| **Entradas** | PR #249 (este repo): `perplexity-master-index.md`, `umbral-bot-capitalization-plan.md`, `sistema-editorial-rick-v1.md`, ADR-005, ADR-006, ADR-007, ADR-008 |
| **Entregable** | PR #249 mergeado. ADRs en estado `Accepted` |
| **Bloqueadores** | Revisión humana pendiente |
| **No hacer todavía** | No crear DBs en Notion. No instalar Ghost. No registrar LinkedIn Developer App |
| **Criterio de salida** | David ha leído spec v1 y ADRs, marcado accepted o devuelto con feedback |

### Fase E1 — Notion setup controlado

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Crear las dos estructuras mínimas en Notion bajo el hub `Sistema Editorial Automatizado Umbral` |
| **Entradas** | Spec v1 §4 y §5 aprobados. Hub existente en Notion |
| **Entregable** | DB `Publicaciones` con schema completo (§5.1). Subpágina `Perfil editorial David` con contenido de §4.3. Link a `Fuentes confiables` |
| **Bloqueadores** | Fase E0 completada. Copies por canal resuelto: propiedades en DB `Publicaciones` (spec v1 §5.2, decisión #5 aceptada) |
| **No hacer todavía** | No crear `PublicationLog`. No tocar `Bandeja de revisión - Rick`, `Control Room`, `Sistema Maestro Apoyo Editorial` |
| **Criterio de salida** | DB `Publicaciones` creada y verificada con al menos 1 fila de prueba. `Perfil editorial David` con pilares, audiencia y voz |

### Fase E2 — Perfil editorial + generación de borradores

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Rick genera su primer borrador editorial real desde un briefing en Notion |
| **Entradas** | `Perfil editorial David` completado. `Fuentes confiables` revisadas. Al menos 1 briefing ingresado en `Publicaciones` |
| **Entregable** | 1-3 borradores en estado `ready_for_review` con metadata completa (§11). CTA asignado según reglas (§10.3) |
| **Bloqueadores** | E1 completada. Fase editorial manual validada (doc 68 gates cumplidos) |
| **No hacer todavía** | No publicar a ningún canal. No generar assets AI |
| **Criterio de salida** | David ha revisado al menos 1 borrador y marcado `aprobado_contenido = true` o devuelto con feedback |

### Fase E3 — Assets visuales y metadata

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Generar assets visuales para piezas aprobadas usando la arquitectura de ADR-006 |
| **Entradas** | Cuenta Google Cloud con billing activo (Vertex AI). Opcionalmente: Freepik API key |
| **Entregable** | Assets generados (Vertex AI o diagrama) asignados a piezas. `featured_image_url` y `featured_image_alt` completados |
| **Bloqueadores** | Cuenta Google Cloud con billing activo. Freepik API key si se activa fallback. UA-13 confirma API-first (UI automation prohibida) |
| **No hacer todavía** | No publicar. No automatizar generación en batch sin validación |
| **Criterio de salida** | Al menos 1 asset AI y 1 diagrama Mermaid generados y validados |

### Fase E4 — Publicación blog / Ghost

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Publicar la primera pieza en blog con automatización completa |
| **Entradas** | Ghost self-hosted instalado en VPS. Custom Integration creada. Pieza en `publish_authorized` |
| **Entregable** | Pieza publicada en Ghost. `Platform post ID` y `Publication URL` registrados en Notion |
| **Bloqueadores** | Ghost self-hosted instalado. n8n con Postgres configurado (ADR-008). `N8N_ENCRYPTION_KEY` respaldada |
| **No hacer todavía** | No publicar a LinkedIn ni X. No configurar cross-post a Hashnode |
| **Criterio de salida** | 1 pieza publicada end-to-end: `draft` → `published`. Webhooks operativos |

### Fase E5 — LinkedIn HITL

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Publicar a LinkedIn perfil personal con HITL obligatorio |
| **Entradas** | LinkedIn Developer App registrada. OAuth 2.0 access token obtenido. Copy LinkedIn generado |
| **Entregable** | 1 publicación en LinkedIn con media. Alerta día 55 configurada para re-auth |
| **Bloqueadores** | LinkedIn Developer App aprobada. David completa OAuth flow. Fase E4 operativa |
| **No hacer todavía** | No publicar automáticamente (ToS §3.1.26). No crear Company Page |
| **Criterio de salida** | 1 post LinkedIn publicado via HITL. Auth lifecycle documentado. Re-auth flow probado |

### Fase E6 — X asistido y futura automatización

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Publicar a X de forma asistida (Rick genera copy, David publica manualmente) |
| **Entradas** | Copy X generado en Notion por Rick. Pieza en `publish_authorized` |
| **Entregable** | 1-3 publicaciones en X. Feedback loop para evaluar si API directa justifica inversión |
| **Bloqueadores** | E4 o E5 operativos (al menos 1 canal real funcionando) |
| **No hacer todavía** | No invertir en X API adapter. No activar publicación automática |
| **Criterio de salida** | David ha publicado al menos 2 piezas manualmente desde copy preparado por Rick |

### Fase E7 — Torneo/evaluación de prompts

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Evaluar y seleccionar prompts editoriales con corpus real de piezas |
| **Entradas** | UA-06 (framework torneo prompts). Corpus de al menos 10 piezas publicadas |
| **Entregable** | Framework de evaluación aplicado. Prompts ganadores documentados |
| **Bloqueadores** | Corpus insuficiente (necesita al menos 10 piezas reales). E4+E5 operativos |
| **No hacer todavía** | No diseñar torneo sin corpus. No optimizar prompts antes de tener feedback humano |
| **Criterio de salida** | Prompts evaluados contra al menos 5 dimensiones de UA-06 con datos reales |

---

## 4. Roadmap Umbral Bot

### Fase B0 — Formalizar docs conceptuales (PR #70)

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Revisar y mergear PR #70 que formaliza `agent-catalog-proposal.md`, `agent-evaluation-lab.md`, `kb-package-architecture.md` |
| **Entradas** | PR #70 en umbral-bot-2 (draft). Investigaciones UB-04, UB-07 parcialmente capitalizadas |
| **Entregable** | PR #70 mergeado. Docs conceptuales como base formal para fases siguientes |
| **Bloqueadores** | Revisión humana de PR #70 |
| **No hacer todavía** | No crear schemas ejecutables sin docs formalizados. No depender formalmente de docs no mergeados |
| **Criterio de salida** | PR #70 mergeado. Docs accesibles en `main` de umbral-bot-2 |

### Fase B1 — KB Package schema + `bep-peb.yaml` (PR #71)

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Revisar y mergear PR #71 que entrega `kb-package.schema.json` + `bep-peb.yaml` + README |
| **Entradas** | PR #71 en umbral-bot-2 (draft). PR #70 mergeado (idealmente). UB-07 P2, UB-R6, UB-R11 |
| **Entregable** | Schema JSON validable y 1 package ejemplo (BEP/PEB) en `main` |
| **Bloqueadores** | Idealmente PR #70 primero. Revisión humana de PR #71 |
| **No hacer todavía** | No activar routing. No activar specialist. No tocar Lovable/Supabase/Foundry/Edge Functions |
| **Criterio de salida** | PR #71 mergeado. Schema validable. `bep-peb.yaml` conforme al schema |

### Fase B2 — `gold-set-bep-minimum`

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Crear el gold set mínimo de evaluación para BEP/PEB antes de routing |
| **Entradas** | PR #71 mergeado (schema + package). UB-04 (15 dimensiones, scoring rubrics). UB-07 P4 (antipatrones) |
| **Entregable** | `gold-set-framework.md`, `dimensions.yaml`, `gold-set-bep.yaml` en umbral-bot-2 |
| **Bloqueadores** | KB package schema definido (B1). Investigación UB-04 accesible |
| **No hacer todavía** | No definir thresholds de routing sin gold set. No evaluar calidad sin framework |
| **Criterio de salida** | Gold set con al menos 10 preguntas BEP/PEB con respuestas esperadas y dimensiones de evaluación |

### Fase B3 — Spec Intake BEP

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Especificar el flujo conversacional de intake para BEP consulting |
| **Entradas** | UB-03 (35 variables, S0-S3). UB-02 (anatomía BEP/PEB). UB-R6, UB-R17 |
| **Entregable** | `docs/specs/intake-bep-v1.md` en umbral-bot-2 |
| **Bloqueadores** | KB schema definido (B1). Puede avanzar en paralelo con B2 (gold set) |
| **No hacer todavía** | No implementar intake sin spec. No conectar a Supabase |
| **Criterio de salida** | Spec con variables, stages, decision tree, validation rules, fallback paths |

### Fase B4 — Spec Routing v1

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Especificar el sistema de routing multi-KB con cascading |
| **Entradas** | UB-10 (cascada regex/embeddings/LLM). UB-07 P3. Gold set mínimo (B2) para calibrar thresholds |
| **Entregable** | `docs/specs/routing-v1.md` en umbral-bot-2 |
| **Bloqueadores** | Gold set mínimo completado (B2). KB schema definido (B1) |
| **No hacer todavía** | No implementar routing. No activar specialist |
| **Criterio de salida** | Spec con pipeline stages, confidence thresholds calibrados contra gold set, fallback logic |

### Fase B5 — Decisión sobre `AgenteUB-specialist`

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Decidir la estrategia de activación del specialist: async, streaming-only, manual o bloqueado |
| **Entradas** | Resultados de gold set (B2). Spec routing (B4). Métricas de latencia y calidad |
| **Entregable** | Decisión documentada con justificación basada en datos |
| **Bloqueadores** | B2 y B4 completados. Datos de latencia/calidad reales |
| **No hacer todavía** | No activar specialist. No crear panel admin. No conectar a producción |
| **Criterio de salida** | Decisión tomada por David con recomendación basada en datos. Documentada en ADR |

### Fase B6 — Governance / admin / comercial (diferido)

| Campo | Detalle |
|-------|---------|
| **Objetivo** | Implementar gobernanza multiagente, panel admin, recomendaciones comerciales |
| **Entradas** | UB-05 (comercial), UB-06 (admin), UB-07 completo (gobernanza), UB-09 (Grasshopper/Rhino) |
| **Entregable** | Framework de gobernanza, panel admin, motor comercial |
| **Bloqueadores** | Fases B0-B5 completadas. Decisiones humanas sobre alcance |
| **No hacer todavía** | Todo. Esta fase no se inicia hasta que B0-B5 estén cerradas |
| **Criterio de salida** | Definida cuando se active la fase |

---

## 5. Matriz Now / Next / Later

| Horizonte | Rick Editorial | Umbral Bot | Compartido |
|-----------|---------------|------------|------------|
| **Now** | Revisar/aprobar PR #249. Aprobar ADRs y spec v1. Decidir Ghost vs Astro | Revisar/aprobar PR #70 (docs). Revisar PR #71 (schema + bep-peb) | Aprobar `perplexity-master-index.md` como índice canónico |
| **Next** | Crear DB `Publicaciones` + `Perfil editorial David` en Notion. Generar primeros borradores. Instalar Ghost | Crear `gold-set-bep-minimum`. Spec Intake BEP. Spec Routing v1 | Vincular `Fuentes confiables` a ambos proyectos |
| **Later** | Assets visuales (Vertex AI). Blog adapter. LinkedIn HITL. X asistido. Torneo prompts | Decisión specialist. Gobernanza multiagente. KB packages dominio. Panel admin | Estrategia de divergencia/convergencia entre repos |

---

## 6. Dependencias entre PRs

```
umbral-agent-stack PR #249
  ├── Debe revisarse ANTES de crear Notion structures o implementar Rick editorial
  ├── Contiene: master index, capitalization plan, spec v1, ADR-005/006/007
  └── No depende de PRs externos

umbral-bot-2 PR #70 (docs conceptuales)
  ├── Debe entrar ANTES de depender formalmente de docs conceptuales del bot
  ├── Formaliza: agent-catalog-proposal, agent-evaluation-lab, kb-package-architecture
  └── No depende de PRs de este repo

umbral-bot-2 PR #71 (schema + bep-peb)
  ├── Puede revisarse como artefacto ejecutable mínimo
  ├── Mejor entendido DESPUÉS de PR #70
  ├── Agrega: kb-package.schema.json, bep-peb.yaml, README, ajustes RELEASE-GATES
  └── NO activa routing, specialist, Lovable, Supabase, Foundry ni Edge Functions

Gold set (futuro)
  ├── Debe venir DESPUÉS de PR #71
  ├── Debe venir ANTES de Spec Routing v1
  └── Routing NO activa specialist por sí mismo
```

---

## 7. Anti-roadmap: cosas que NO hacer ahora

| # | Prohibición | Razón |
|---|-------------|-------|
| 1 | No nueva investigación Perplexity salvo hueco explícito | 46 documentos indexados son suficientes para v1 |
| 2 | No activar routing specialist en Umbral Bot | Requiere gold set evaluado + métricas de latencia/calidad/UX |
| 3 | No implementar publicación LinkedIn automática sin HITL | ToS §3.1.26 lo prohíbe; HITL es obligatorio |
| 4 | No crear `PublicationLog` en v1 | Tracking inline en `Publicaciones` es suficiente; `PublicationLog` es v1.1 |
| 5 | No crear panel admin del bot todavía | UB-06 es fase 2; depende de routing y gobernanza |
| 6 | No crear motor comercial/recomendaciones | UB-05 es fase 2; depende de trust calibration y guardrails |
| 7 | No crear DB de assets separada en v1 | Assets se gestionan inline con `featured_image_url` en `Publicaciones` |
| 8 | No mezclar `Control Room` ni `Bandeja de revisión - Rick` como base editorial | Tienen propósitos distintos; lista NO-TOUCH explícita en ADR-007 |
| 9 | No usar PRs grandes multi-sistema | Cada artefacto es un PR independiente con scope limitado |
| 10 | No tocar `Sistema Maestro Apoyo Editorial` en Notion | Legacy, congelada hasta re-evaluación |
| 11 | No crear KB packages de dominio antes de tener schema validado | Dependen de PR #71 |
| 12 | No automatizar n8n editorial antes de fase manual estable | Gate de doc 68 §9: shortlist estable 3-4 semanas |
| 13 | No automatizar UI de Freepik, Midjourney, Adobe Firefly ni Gemini app | AUP prohíbe bots/external tools/RPA sobre interfaces web, incluso con cuenta propia (UA-13) |
| 14 | No hacer scraping de LinkedIn ni X | ToS prohíben acceso automatizado sin API. HITL obligatorio para publicación (UA-13) |
| 15 | No usar Make para polling Notion productivo | Quema créditos Make y duplica Notion Poller del Agent Stack (UA-14) |
| 16 | No usar SQLite para n8n en producción | No soporta concurrencia; corrompe bajo carga. Postgres desde día 1 (UA-14) |
| 17 | No publicar en X/LinkedIn personal sin preview y consentimiento registrado | HITL obligatorio; `autorizar_publicacion` gate (UA-13, UA-14) |
| 18 | No crear DB separada `Assets Visuales Rick` en v1 | Assets inline en `Publicaciones` por decisión de David. DB separada es v1.1/v2 (UA-13 reconciliación) |

---

## 8. Decisiones pendientes humanas

| # | Decisión | Opciones | Recomendación actual | Cuándo decidir | Qué desbloquea |
|---|----------|----------|---------------------|----------------|----------------|
| 1 | Ghost vs Astro+Git para blog v1 | Ghost self-hosted (ADR-005) / Astro+Git+Cloudflare Pages | **✅ Aceptado: Ghost v1** — ADR-005 accepted 2026-04-21; Astro como objetivo futuro | — | Publicación blog |
| 2 | Vertex AI vs Gemini API directo para assets | Vertex AI (mejor SLA, ADR-006) / Gemini API consumer (más simple) | **✅ Aceptado: Vertex AI**. UA-13 confirma API-first y advierte preview models no primarios hasta GA | — | Pipeline de assets visuales |
| 3 | Freepik API vs Freepik UI/stock | API pay-per-use (ADR-006) / Solo UI manual | **✅ Resuelto: Freepik API/MCP como vía autorizada**. UI automation prohibida (UA-13 AUP) | — | Fallback visual |
| 4 | Estructura copies por canal en Notion | Propiedades en `Publicaciones` / Subpáginas por canal | **✅ Aceptado: propiedades en una sola DB `Publicaciones`** (spec v1 §5.2) | — | Creación DB `Publicaciones` |
| 5 | PR #70 antes de PR #71 | Sí (docs primero) / No (schema independiente) | Sí — docs conceptuales dan contexto para entender schema | Ahora | Orden de merge en umbral-bot-2 |
| 6 | Estrategia `AgenteUB-specialist` por latencia | Async / streaming-only / manual / bloqueado | Bloqueado hasta tener datos de gold set | Después de B2+B4 | Activación de specialist |
| 7 | Cron scheduling editorial: n8n vs custom | n8n (existente en VPS) / Custom cron | **✅ Aceptado: n8n** — UA-14 recomienda Agent Stack core + n8n bordes. Ver [ADR-008](../adr/ADR-008-orquestacion-editorial.md) | — | Scheduling de publicación |
| 8 | Idempotencia publicación: Redis vs Notion | Redis TTL 24h / Campo `content_hash` en Notion | **✅ Aceptado: `content_hash` en Notion** — zero-infra adicional para v1; Redis TTL como v2 | — | Pipeline de publicación |

### Investigaciones Perplexity capitalizadas

| ID | Tema | Estado | Capitalizado en |
|----|------|--------|----------------|
| UA-13 | Automatización visual con cuentas de usuario, navegador y RPA | **Capitalizado** | ADR-006 (API-first, Freepik API/MCP, prohibición UI automation), spec v1 §9.1, §14 #2/#3/#9 |
| UA-14 | Orquestación editorial Rick: n8n vs Make vs Agent Stack | **Capitalizado** | ADR-008 (Agent Stack core + n8n bordes + Make lab), spec v1 §14 #7/#10, roadmap §8 #7 |

### Referentes como señal de descubrimiento editorial

La DB `Referentes` en Notion (25 registros, 13 propiedades) funciona como `discovery_signal` para el sistema editorial, no como `source_of_truth`. Los referentes informan:
- **Curation (E2)**: qué temas y estilos narrativos resuenan con la audiencia target.
- **Visual direction (E3)**: qué formatos visuales usan los referentes más relevantes.
- **CTA patterns (E4)**: qué estrategias de conversión aplican los referentes en su nicho.

**No es v1-blocking**: la DB ya existe y es usable. Las mejoras recomendadas (dedup, fill rate, campos computados) son incrementales y pueden aplicarse en paralelo con cualquier fase.

### Backlog técnico n8n/orquestación (UA-14)

| Item | Razón | Cuándo | Bloquea |
|------|-------|--------|---------|
| n8n con Postgres | SQLite no soporta concurrencia; corrompe bajo carga | Antes de cualquier workflow productivo | E4 |
| Backup `N8N_ENCRYPTION_KEY` fuera de VPS | Pérdida = todas las credenciales encriptadas perdidas | Inmediato al configurar n8n con Postgres | E4 |
| Export nocturno n8n → Git | `n8n export:workflow --all` + commit al repo | Cron nocturno post n8n productivo | — |
| Notion webhooks beta PoC | Mantener Poller como fallback hasta validar webhooks | Cuando Notion webhooks salga de beta | — |
| Outbox/DLQ PoC | Retry estructurado para publicaciones fallidas | Antes de E5 (LinkedIn HITL) | E5 |

---

## 9. Criterios de calidad para avanzar

### Rick Editorial

- Rick no pasa a publicación si no existen ambos gates humanos (`aprobado_contenido`, `autorizar_publicacion`).
- Rick nunca marca estos gates como `true`. Solo David.
- Ningún canal publica si `autorizar_publicacion != true`.
- CTA asignado según reglas de la spec v1 §10.3; validado por gates de §6.
- Si David comenta después de `aprobado_contenido = true`, la aprobación se invalida automáticamente.
- Toda pieza tiene metadata obligatoria completa (spec v1 §11) antes de `ready_for_review`.
- No automatizar n8n antes de que la fase manual (doc 68 §9) esté estable.

### Umbral Bot

- Bot no pasa a routing spec si no existe gold set mínimo.
- Gold set debe tener al menos 10 preguntas BEP/PEB con respuestas esperadas.
- Cualquier KB package debe tener: fuente trazable, límites declarados, eval binding, owner.
- Schema debe ser validable (JSON Schema o YAML schema con tests).
- PR #71 NO activa routing, specialist, Lovable, Supabase, Foundry ni Edge Functions.
- Specialist no se activa hasta tener datos de latencia/calidad/UX del gold set.

### Compartido

- Cualquier automatización debe tener rollback documentado y manual fallback.
- `perplexity-master-index.md` es el índice canónico; toda referencia debe usar IDs de ese índice.
- No referenciar documentos históricos (UA-07, UA-08, UA-09, UB-R1) como fuente de decisión.
- Investigaciones Perplexity se consumen como input; nunca se implementan directamente desde este repo.

---

## 10. Próximos 5 pasos recomendados

1. **David revisa PR #249** (este repo). Aprobar o devolver con feedback: spec v1, ADR-005/006/007, master index, capitalization plan. Esto desbloquea todo Rick Editorial.

2. **David revisa PR #70** (umbral-bot-2). Aprobar docs conceptuales (`agent-catalog-proposal`, `agent-evaluation-lab`, `kb-package-architecture`). Esto da base formal para PR #71 y gold set.

3. **David revisa PR #71** (umbral-bot-2). Verificar `kb-package.schema.json` y `bep-peb.yaml`. Esto desbloquea gold set mínimo.

4. **Crear DB `Publicaciones` y `Perfil editorial David` en Notion** (E1). Ghost y copies-por-canal ya decididos (§8 #1, #4). Scope mínimo: schema de spec v1 §5, contenido de §4.3.

5. **Configurar n8n con Postgres** en VPS (ADR-008 backlog). Respaldar `N8N_ENCRYPTION_KEY`. Esto desbloquea workflows productivos para E4.

6. **T0: structured error classification** como PR independiente. Aceptado por David como siguiente PR después de #249.

---

## 11. Delta de oportunidades detectadas

Análisis completo en [opportunity analysis](2026-04-agent-stack-opportunity-analysis-from-perplexity.md). Resumen de cambios al roadmap:

### Nuevos bloques transversales

| Bloque | Qué | Prioridad | Timing |
|--------|-----|-----------|--------|
| T0 | Structured error classification en Worker (enum `error_class` + dedup Linear) | P1 | **Aceptado** — siguiente PR después de #249 |
| T1 | Research intake metadata en master index (`next_action_type`, `priority`, `blocks_decision`) | P2 | Después de merge PR #249 |
| T2 | Provider health score en model router (auto-demote sin esperar quota) | P2 | Independiente |

### Cambios en fases existentes

| Fase | Agregar |
|------|---------|
| E2 | Definir subset de dimensiones de evaluación editorial (de UB-04) para gold set futuro |
| E4 | Implementar `publish.attempt/success/failed` y `auth.expiry_warning` en OpsLogger |
| E5 | Verificar comment invalidation tracking antes de LinkedIn HITL |

### Movimientos de horizonte

| Item | De → A | Razón |
|------|--------|-------|
| Gold set editorial | Later (E7) → Next (preparar en E2) | Sin gold set, torneo de prompts no tiene baseline |
| CTA rate-limiting | Implícito → Next (resolver en E2) | Necesita decisión Redis vs Notion antes de generar borradores |

### No se necesita nueva investigación Perplexity

48 documentos existentes cubren editorial, bot, visual, CTA, gobernanza, routing, evaluation, automatización visual y orquestación. Los huecos detectados son de ingeniería, no de research.

---

## Referencias

| Documento | Ubicación |
|-----------|-----------|
| Perplexity Master Index | [docs/research/perplexity-master-index.md](../research/perplexity-master-index.md) |
| Umbral Bot Capitalization Plan | [docs/research/umbral-bot-capitalization-plan.md](../research/umbral-bot-capitalization-plan.md) |
| Spec v1 Sistema Editorial Rick | [docs/specs/sistema-editorial-rick-v1.md](../specs/sistema-editorial-rick-v1.md) |
| ADR-005 Publicación Multicanal | [docs/adr/ADR-005-publicacion-multicanal.md](../adr/ADR-005-publicacion-multicanal.md) |
| ADR-006 Capa Visual Editorial | [docs/adr/ADR-006-capa-visual-editorial.md](../adr/ADR-006-capa-visual-editorial.md) |
| ADR-007 Notion como Hub Editorial | [docs/adr/ADR-007-notion-como-hub-editorial.md](../adr/ADR-007-notion-como-hub-editorial.md) |
| ADR-008 Orquestación Editorial | [docs/adr/ADR-008-orquestacion-editorial.md](../adr/ADR-008-orquestacion-editorial.md) |
| Editorial Source Curation | [docs/67-editorial-source-curation.md](../67-editorial-source-curation.md) |
| Editorial Phase 1 Manual | [docs/68-editorial-phase-1-manual.md](../68-editorial-phase-1-manual.md) |
| Editorial Automation Audit | [docs/audits/rick-editorial-automation-system-2026-03-09.md](../audits/rick-editorial-automation-system-2026-03-09.md) |
| Rick Estado y Capacidades | [docs/rick-estado-y-capacidades.md](../rick-estado-y-capacidades.md) |
