# Spec v1 — Sistema Editorial Rick

> **Estado**: PROPUESTO — pendiente de revisión humana
> **Creado**: 2026-04-21
> **Autor**: Copilot (sesión de capitalización)
> **Fuentes Perplexity**: UA-10 (publicación), UA-11 (visual), UA-12 (CTA/funnel)
> **Decisiones Notion previas**: auditoría aceptada en sesión anterior

---

## 1. Objetivo

Definir el sistema editorial de Rick como producto mínimo operable: un agente que redacta, revisa, asigna assets visuales y prepara publicación de contenido técnico B2B en LinkedIn, X y blog, usando Notion como bus humano y fuente de estado.

Rick **no publica automáticamente** en v1 a LinkedIn ni X. El human-in-the-loop es obligatorio por ToS (LinkedIn) y por decisión de producto (X). Blog (Ghost) sí admite automatización completa.

---

## 2. Alcance v1

- Generación de borradores editoriales desde briefings en Notion.
- Ciclo de revisión humana con dos gates explícitos: aprobación de contenido y autorización de publicación.
- Generación y asignación de assets visuales (AI + stock + diagramas).
- Preparación de copies adaptados por canal (LinkedIn, X, Blog).
- Publicación automatizada a Ghost (blog primario).
- Publicación asistida a LinkedIn (HITL explícito) y X (manual v1).
- Registro mínimo de publicación inline en DB `Publicaciones` de Notion.
- Capa de CTA tipada con reglas de decisión y rate-limiting.
- Metadata obligatoria por pieza.

---

## 3. Fuera de alcance v1

- Publicación a LinkedIn Company Page (requiere CMA + entidad legal).
- Publicación directa a X vía API (diferido a v2; v1 es asistida).
- Blog en Astro + Git + Cloudflare Pages (objetivo futuro; v1 usa Ghost).
- Cross-post a Hashnode (posible en v2 con `canonicalUrl`).
- Radar de noticias reactivas (UA-05 — no priorizado).
- Motor de recomendaciones comerciales de Umbral Bot.
- Panel admin o gobernanza de datos del bot.
- Cualquier modificación a `Bandeja de revisión - Rick`, `Control Room`, `Sistema Maestro Apoyo Editorial`, `Asesorías & Proyectos` en Notion.

---

## 4. Arquitectura Notion

### 4.1 Hub editorial

**Hub**: `Sistema Editorial Automatizado Umbral` (página existente en Notion). Decisión arquitectural formalizada en [ADR-007](../adr/ADR-007-notion-como-hub-editorial.md).

Todo lo relacionado con el sistema editorial de Rick vive bajo este hub. No crear hubs nuevos.

### 4.2 Páginas y DBs

| Elemento | Tipo | Estado | Acción |
|----------|------|--------|--------|
| `Sistema Editorial Automatizado Umbral` | Página hub | Existente | Usar como contenedor |
| `Fuentes confiables` | DB (bajo página `Fuentes`) | Existente | Reusar como DB. No es subpágina, es DB existente bajo la página `Fuentes`. Vincular fuentes normativas compartidas con Umbral Bot |
| `Perfil editorial David` | Subpágina | **Nueva** | Crear. Derivar de `Mi Perfil` + `Plan Estrategia Comercial` + UA-01 + UA-02 |
| `Publicaciones` | DB | **Nueva** | Crear como DB dentro del hub. Schema en §5 |
| `Bandeja de revisión - Rick` | Página | Existente | **NO TOCAR** |
| `Control Room` | Página | Existente | **NO TOCAR** |
| `Sistema Maestro Apoyo Editorial` | Página | Existente | **NO TOCAR** |
| `Asesorías & Proyectos` | Página | Existente | **NO TOCAR** |

### 4.3 Perfil editorial David — contenido mínimo

Derivado de UA-01 (dolor/audiencia) y UA-02 (mapa de autoridad):

- **Audiencia primaria**: BIM managers, jefes de proyecto AECO, CTOs de oficinas AECO, consultores BIM (Chile + España).
- **Audiencia secundaria**: arquitectos en transición digital, estudiantes avanzados BIM, community técnica Power Platform + BIM.
- **Pilares temáticos**: Automatización Empática, Puentes Digitales, Citizen Developer AECO, ISO 19650 operativo.
- **Voz**: técnica, específica, anti-hype. Snippets reales, cifras verificables, opinión con argumento.
- **Anti-patrones de tono**: creator economy hooks, "sígueme para más", hype sin data, pitch sin confianza.
- **Activos institucionales**: Máster AEC 4.0 (Butic), Umbral BIM (producto), consultoría activa.

---

## 5. DB `Publicaciones` — propuesta de schema

Basado en UA-10 §7 y UA-12 §7.1. Una fila por pieza de contenido fuente.

### 5.1 Propiedades principales

| Propiedad | Tipo Notion | Descripción | Obligatoria |
|-----------|-------------|-------------|-------------|
| `Title` | Title | Título de la pieza (max 120 chars) | sí |
| `Slug` | Rich text | kebab-case, único, <60 chars | sí |
| `Status` | Status | `draft` → `ready_for_review` → `content_approved` → `publish_authorized` → `scheduled` → `published` → `archived` | sí |
| `Aprobado contenido` | Checkbox | **Solo David marca `true`**. Rick nunca lo toca. Indica que David revisó y aprobó el contenido editorial | sí |
| `Autorizar publicación` | Checkbox | **Solo David marca `true`**. Rick nunca lo toca. Indica que David autoriza la publicación efectiva por canal. Requiere `aprobado_contenido = true` previo | sí |
| `Canal primario` | Select | `linkedin` / `blog` / `x` | sí |
| `Canales secundarios` | Multi-select | Otros canales donde se publicará | no |
| `Tipo pieza` | Select | `tecnico_corto` / `reflexivo` / `producto` / `post_mortem` / `caso_estudio` / `tutorial` / `opinion` / `recap` / `docencia` / `respuesta_publica` | sí |
| `Objective` | Select | `autoridad` / `enablement` / `validacion` / `activacion` / `memoria` | sí |
| `CTA type` | Select | `none` / `conversacion` / `validacion_problema` / `recurso` / `diagnostico` / `discovery` / `producto` / `educacion` | sí |
| `CTA strength` | Select | `none` / `soft` / `medium` / `strong` | sí |
| `CTA destination` | URL | URL destino del CTA (null si cta_type = none) | no |
| `CTA text` | Rich text | Texto final del CTA que inserta Rick | no |
| `Audience stage` | Select | `cold` / `warm` / `hot` | sí |
| `Evidence density` | Select | `low` / `med` / `high` | sí |
| `Funnel stage` | Select | `memory` / `enablement` / `validation` / `activation` | sí |
| `Commercial intent` | Select | `none` / `low` / `med` / `high` | sí |
| `Content markdown` | Rich text (page body) | Contenido fuente en markdown | sí |
| `Content hash` | Rich text | sha256 del content markdown — para idempotencia | auto |
| `Excerpt` | Rich text | Max 300 chars, reusable como meta description | sí |
| `Tags` | Multi-select | Etiquetas temáticas | sí |
| `Series` | Select | Nombre de serie si aplica | no |
| `Featured image URL` | URL | URL del asset principal | no |
| `Featured image alt` | Rich text | Alt text obligatorio si hay imagen | condicional |
| `Canonical URL` | URL | URL del blog primario (fuente de verdad SEO) | post-publicación |
| `Scheduled at` | Date | Fecha programada de publicación (UTC) | condicional |
| `Published at` | Date | Fecha de primera publicación exitosa | auto |
| `Content approved at` | Date | Fecha en que David marcó `aprobado_contenido = true` | auto |
| `Publish authorized at` | Date | Fecha en que David marcó `autorizar_publicacion = true` | auto |
| `No CTA reason` | Select | `saturated_rate_limit` / `low_evidence` / `post_mortem` / `cold_audience` / `experimental` / `null` | condicional |
| `Platform post ID` | Rich text | URN, tweet_id, ghost_post_id del último intento de publicación | auto |
| `Publication URL` | URL | URL pública final de la publicación | auto |
| `Last publish error` | Rich text | Último mensaje de error de publicación (si aplica) | auto |

### 5.2 Copies por canal (propiedades adicionales o subpáginas)

| Propiedad | Tipo | Descripción |
|-----------|------|-------------|
| `Copy LinkedIn` | Rich text | Commentary adaptado para LinkedIn (max 3000 chars) |
| `Copy X` | Rich text | Thread adaptado para X (280 chars por tweet, o 25k si note_tweet) |
| `Copy Blog title` | Rich text | Título SEO para blog |
| `Copy Blog meta description` | Rich text | Meta description (max 160 chars) |

### 5.3 Tracking de publicación (inline en `Publicaciones`)

En v1 no se crea una DB separada `PublicationLog`. La auditoría de Notion recomendó mínima duplicación: una sola DB nueva (`Publicaciones`) y una subpágina (`Perfil editorial David`).

El tracking mínimo de publicación por canal se registra inline en `Publicaciones` con las propiedades `Platform post ID`, `Publication URL` y `Last publish error` de §5.1.

> **v1.1 (futuro)**: si el volumen crece o se necesita historial de reintentos por canal, crear DB relacional `PublicationLog` con schema: `Post` (relation), `Channel` (select), `Status` (select), `Platform post ID`, `Publication URL`, `Published at`, `Retries`, `Last error`, `Error code`, `Platform version`.

---

## 6. Estados y gates

```
draft
  │
  ▼  [Rick genera borrador, completa metadata]
ready_for_review
  │
  ▼  [David revisa contenido — GATE HUMANO 1: aprobado_contenido = true]
content_approved
  │
  ▼  [David autoriza publicación — GATE HUMANO 2: autorizar_publicacion = true]
publish_authorized
  │
  ▼  [Rick programa publicación — si scheduled_at está definido]
scheduled
  │
  ▼  [Publicación ejecutada por canal]
published
  │
  ▼  [Manual: si la pieza se retira]
archived
```

### Gates obligatorios

| Gate | Quién | Qué valida | Señal |
|------|-------|------------|-------|
| `draft → ready_for_review` | Rick | Contenido completo, metadata obligatoria rellena, CTA asignado según reglas | Rick cambia Status |
| `ready_for_review → content_approved` | **David (humano)** | Calidad editorial, precisión técnica, tono, CTA apropiado | David marca `aprobado_contenido = true` |
| `content_approved → publish_authorized` | **David (humano)** | Copies por canal listos, asset asignado, momento oportuno | David marca `autorizar_publicacion = true` |
| `publish_authorized → scheduled/published` | Rick | Auth tokens válidos, canal listo | Rick cambia Status a `scheduled` o `published` |
| `published → archived` | David (humano) | Decisión manual de retirar contenido | David cambia Status |

### Reglas de gate (obligatorias)

- **Rick nunca marca `aprobado_contenido = true`**. Solo David.
- **Rick nunca marca `autorizar_publicacion = true`**. Solo David.
- Si David comenta después de `aprobado_contenido = true`, la aprobación de contenido se invalida: `aprobado_contenido` vuelve a `false`, `autorizar_publicacion` vuelve a `false`, y Status regresa a `ready_for_review`.
- **Ningún canal publica si `autorizar_publicacion != true`**.
- `autorizar_publicacion` no puede ser `true` si `aprobado_contenido != true`.
- Si `cta_type ≠ none` y `cta_text` está vacío → bloquear en `ready_for_review`.
- Si `featured_image_url` presente y `featured_image_alt` vacío → bloquear.
- Si `canal primario = linkedin` y auth token expirado → bloquear en `publish_authorized` y alertar.

---

## 7. Comentarios y revisión humana

### Flujo de revisión

1. Rick genera borrador y lo marca `ready_for_review`.
2. David abre la página en Notion.
3. David puede:
   - **Aprobar contenido**: marcar `aprobado_contenido = true`. Status pasa a `content_approved`.
   - **Pedir cambios**: dejar comentario inline en Notion. Rick lee comentarios y genera nueva versión en `draft`.
   - **Rechazar**: cambiar status a `archived` con motivo.
4. Una vez en `content_approved`, David revisa copies por canal y assets, y puede:
   - **Autorizar publicación**: marcar `autorizar_publicacion = true`. Status pasa a `publish_authorized`.
   - **Pedir ajustes de copy/assets**: dejar comentario. Esto invalida `aprobado_contenido` y vuelve a `ready_for_review`.
5. Rick **nunca** marca `aprobado_contenido = true` ni `autorizar_publicacion = true`. Solo David.

### Canal de feedback

- Comentarios inline en Notion (mecanismo nativo).
- Campo `revision_notes` (rich text) para instrucciones generales.
- Rick debe **preservar comentarios previos** como historial.

---

## 8. Publicación por canal

Basado en UA-10 §§2-4.

### 8.1 Blog (Ghost self-hosted) — Automatización completa

| Aspecto | Detalle |
|---------|---------|
| **Endpoint** | `POST /ghost/api/admin/posts/?source=html` |
| **Auth** | Custom Integration → `id:secret` → JWT HS256, exp ≤5 min, aud `/admin/` |
| **Formato** | Markdown → HTML con `marked` o `pandoc` |
| **Media** | `POST /ghost/api/admin/images/upload/` (multipart) |
| **Upsert** | GET por slug → PUT con `updated_at` exacto; retry en 409 |
| **Scheduling** | `status: scheduled` + `published_at` futuro (nativo Ghost) |
| **Webhooks** | `post.published`, `post.edited` → actualizar DB Publicaciones |
| **Code blocks** | Prism nativo en tema Casper/Source |
| **Rotación auth** | JWT fresco por request (no reutilizar) |
| **Failure mode** | 409 conflict (sha obsoleto) → GET + retry. JWT expired → regenerar |

### 8.2 LinkedIn perfil personal — HITL obligatorio

| Aspecto | Detalle |
|---------|---------|
| **Endpoint** | `POST https://api.linkedin.com/rest/posts` |
| **Auth** | OAuth 2.0 Authorization Code (PKCE rec.), scopes `openid profile email w_member_social` |
| **Access token** | 60 días, **sin refresh token** (no-MDP) |
| **Rotación** | Alerta día 55 → re-auth manual (OAuth flow) |
| **Header obligatorio** | `LinkedIn-Version: YYYYMM` (revisar trimestralmente; 426 si expirado) |
| **Person URN** | `GET /v2/userinfo` → `sub` |
| **Media** | Async: `POST /rest/images?action=initializeUpload` → PUT binario → polling hasta `AVAILABLE` → URN |
| **HITL gate** | Rick genera draft con copy final + media URN en Notion. David clickea "Publicar" que dispara el POST |
| **Scheduling** | No nativo. Rick usa cron propio; Notion guarda `scheduled_at` |
| **Límite texto** | 3.000 chars |
| **Alt text** | Campo `altText`, ≤4.086 chars (rec. <120) |
| **Rate limits** | ~100K/día/app self-serve |
| **Failure modes** | Token expirado (401) → re-auth. `LinkedIn-Version` obsoleto (426) → actualizar header. Media no AVAILABLE → timeout y retry |
| **Restricción ToS** | §3.1.26 prohíbe automatizar publicaciones. HITL obligatorio |

### 8.3 X — Asistido v1

| Aspecto | Detalle |
|---------|---------|
| **v1** | Rick genera copy final + media URLs en Notion. David publica manualmente desde X.com o Typefully |
| **v2 (futuro)** | `POST https://api.x.com/2/tweets`, OAuth 2.0 PKCE, pay-per-use (~$0.015/post + $0.20 si URL) |
| **Razón de diferir** | Plataforma inestable: 5 cambios materiales en 36 meses. No vale invertir en adapter hasta que se estabilice |
| **Threading** | Encadenar con `reply.in_reply_to_tweet_id` sobre IDs propios |
| **Media v2** | `POST /2/media/upload` → INIT/APPEND/FINALIZE/STATUS |
| **Límite texto** | 280 chars estándar / 25.000 via `note_tweet` (Premium $8/mes) |
| **Duplicados** | Error 187 si texto idéntico reciente — no reintentar con mismo contenido |
| **Fallback** | Si X rompe reglas otra vez: redirigir a TypefullyAdapter sin tocar el resto |

---

## 9. Capa visual / assets

Basado en UA-11 §§2-7.

### 9.1 Arquitectura visual

```
Rick asset_router
  ├── AI primary: Vertex AI / gemini-3-pro-image-preview
  ├── AI fallback: Freepik API (nano-banana-pro, ideogram-3, mystic)
  ├── Vector / Stock: Freepik stock + Flaticon + Lucide/Heroicons
  ├── Diagramas: Mermaid + Excalidraw + tldraw + Graphviz
  └── Screenshots: capturas reales (Revit, Dynamo, Power BI, ACC, n8n)
```

### 9.2 Reglas de decisión del asset_router

| Caso | Herramienta | Nunca AI |
|------|-------------|----------|
| Diagrama de arquitectura (OpenClaw, Rick, flujos) | Mermaid / Excalidraw / draw.io / Graphviz | ✅ |
| Screenshot de UI real (Revit, Dynamo, Power BI) | Captura real + anotación Excalidraw/CleanShot | ✅ |
| Gráfico de datos / chart | matplotlib / Power BI export | ✅ |
| Iconografía | Freepik stock SVG + Flaticon + Lucide | ✅ |
| Portada conceptual (hero LinkedIn, blog) | Gemini 3 Pro Image 2K/4K con references | — |
| Imagen con texto legible | Gemini 3 Pro Image (su diferencial) | — |
| Carrusel técnico LinkedIn | Template Figma + slots | — |
| Asset de X | Gemini 3 Pro Image 1K batch | — |
| Serie visual consistente | Gemini 3 Pro Image con ref-pack fijo | — |

### 9.3 Pricing y riesgos

| Plataforma | Pricing por imagen (1K/2K) | Riesgo clave |
|------------|---------------------------|--------------|
| Gemini API directo (Standard) | $0.134 | **Preview state**: ToS prohíbe uso producción. Usar Vertex AI |
| Gemini API directo (Batch 24h) | $0.067 | — |
| Vertex AI | Mismo base, SLA más estable | Región configurable (EU/US) |
| Freepik API (NBP) | ~75 créditos/imagen, pay-per-use | Más caro que Google directo |

**Decisión**: Vertex AI como canal primario. Freepik como fallback y stock. Ver [ADR-006](../adr/ADR-006-capa-visual-editorial.md).

### 9.4 Regla anti-AI-slop

- Sin personas foto-real generadas por AI.
- Priorizar diagramas, texturas, abstracciones, mockups.
- Si la pieza tiene dato verificable, gana el diagrama o screenshot.
- AI solo para atmósfera, concepto o titular.
- SynthID activo siempre (no removible). No declarar como foto real.

---

## 10. CTA / Funnel

Basado en UA-12 §§2-8.

### 10.1 Tipos de CTA

| Tipo | Fricción | Cuándo usar |
|------|----------|-------------|
| `none` | Ninguna | **Default**. Observaciones técnicas, TILs, notas breves, post-mortems |
| `conversacion` | Baja | Preguntas abiertas genuinas, invitación a discrepar |
| `validacion_problema` | Baja | "¿Te ha pasado?", "¿Cómo lo resuelven?" — activa mere-measurement |
| `recurso` | Baja | Link a artículo propio, repo, plantilla pública. Sin gatear |
| `diagnostico` | Media | Checklist, mini-auditoría, calculadora. Entrega valor sin contacto |
| `discovery` | Alta | Llamada de exploración. Solo en piezas con confianza densa acumulada |
| `producto` | Media-alta | Umbral BIM, waitlist. Solo en piezas sobre el problema que Umbral resuelve |
| `educacion` | Media | Máster AEC 4.0, workshops. Solo en ventana de inscripción |

### 10.2 Anti-patrones

| Anti-patrón | Por qué daña |
|-------------|-------------|
| "Agenda una llamada" en pieza fría | 70% del journey B2B ocurre antes de contacto; presión prematura reduce cierre (Rackham/SPIN) |
| "Sígueme para más" / hooks virales | Creator economy pattern; atrae audiencia no-ICP |
| "Comenta X y te envío Y" | Engagement transaccional visible; incompatible con dark social B2B |
| Lead magnet genérico gateado | Refuerza saturación percibida (Edelman 2022: 38% saturación) |
| Pitch sin confianza previa | "Cheap talk" sin señal costosa; una pieza pitch envenena 10 piezas legítimas |
| CTA comercial en pieza de bajo valor | Amplifica percepción de mediocridad (Edelman: 55% abandona en <1 min) |
| CTA repetida demasiado | Mere-exposure → fatiga → reactancia |

### 10.3 Reglas de decisión para Rick (pseudocódigo)

```
# GATE DURO
if tipo_pieza == "post_mortem": cta_type = "none"
if evidence_density == "low" and commercial_intent >= "med": cta_type = "none"
if rate_limit_exceeded("commercial", window=10_piezas): downgrade_to_soft_or_none()

# CANAL
if canal == "x": cta_type in {none, recurso}; cta_strength in {none, soft}
if canal == "linkedin" and tipo_pieza in {tecnico_corto, opinion, reflexivo}:
    cta_type in {none, conversacion, validacion_problema}; cta_strength = "soft"

# AUDIENCE + TRUST
if audience_stage == "cold" and trust_required >= "med": prohibir discovery, producto
if audience_stage == "hot" and offer_relation == "direct": permitir producto, educacion, discovery

# OFFER RELATION
if offer_relation == "unrelated": prohibir producto, educacion, discovery

# DEFAULT
cta_type = "none" or "conversacion"; cta_strength = "none" or "soft"
```

### 10.4 Rate-limiting

| Canal | Límite CTA comercial |
|-------|---------------------|
| LinkedIn | ≤1 cada 5-7 piezas. No seguidas en ventana 72h |
| Blog | ≤1 cada 3 artículos largos. Link en firma de autor no cuenta |
| X | 0 por defecto. Solo si atada a evento explícito |
| Global por cuenta | Ningún lector recurrente ve ≥2 CTAs comerciales en 10 días |
| Proporción objetivo | 60-70% {none, conversacion, validacion, recurso} / 20-25% {diagnostico, recurso avanzado} / 10-15% {discovery, producto, educacion} |

### 10.5 Funnel ligero (4 capas)

| Capa | Objetivo | Métricas | % piezas aprox |
|------|----------|----------|----------------|
| **Memoria** (95% out-of-market) | Entrar en lista corta mental | Menciones orgánicas, forwards, seguidores cualificados | 60-70% |
| **Buyer enablement** (solution exploration) | Material para construir requisitos internamente | Tráfico blog, descargas plantillas, forwards dark social | 20-25% |
| **Validación** (supplier selection) | Resolver objeciones, validar elección | Engagement casos estudio, DMs cualificados | 5-10% |
| **Activación** (cierre) | Discovery, waitlist, inscripciones | Formularios, calendario, waitlist | 5-10% |

---

## 11. Metadata obligatoria

Toda pieza en DB `Publicaciones` debe tener completos antes de pasar a `ready_for_review`:

- `title`, `slug`, `canal primario`, `tipo_pieza`, `objective`
- `cta_type`, `cta_strength`, `audience_stage`, `evidence_density`
- `funnel_stage`, `commercial_intent`
- `content_markdown` (body)
- `excerpt` (max 300 chars)
- `tags` (≥1)
- Si `cta_type ≠ none`: `cta_text` y `cta_destination`
- Si `cta_type = none`: `no_cta_reason`
- Si `featured_image_url` presente: `featured_image_alt`

---

## 12. Failure modes

| Modo de fallo | Canal | Impacto | Mitigación |
|---------------|-------|---------|-----------|
| Token LinkedIn expirado | LinkedIn | Publicación bloqueada | Alerta día 55, re-auth manual |
| `LinkedIn-Version` header obsoleto (HTTP 426) | LinkedIn | Publicación bloqueada | Revisar changelog trimestral |
| Media LinkedIn no alcanza `AVAILABLE` | LinkedIn | Publicación sin imagen | Timeout 60s + retry 2x + fallback sin imagen |
| Ghost `updated_at` collision (409) | Blog | Upsert falla | GET + PUT inmediato, retry en 409 |
| Ghost JWT expirado | Blog | Publicación falla | Generar JWT fresco por request |
| X error 187 (duplicado) | X | Tweet rechazado | No reintentar con mismo contenido; agregar variación |
| X pricing/API change | X | Adapter roto | Abstracción: swap a Typefully/Buffer adapter |
| Gemini API preview breaking change | Visual | Generación de assets falla | Wrapper abstraction + fallback a Freepik API |
| Rate limit Gemini (429) | Visual | Throttled | Backoff exponencial; batch API 50% descuento |
| Notion API rate limit | Todos | Lectura/escritura lenta | Backoff + cache local |
| Content hash collision (dedup) | Todos | Publicación duplicada evitada | Clave `(slug, channel, content_hash)` con TTL 24h |
| Comentario post-aprobación no detectado | Todos | Pieza publicada con contenido no aprobado | Rick debe poll comentarios; si detecta comentario nuevo después de `content_approved_at`, invalidar `aprobado_contenido` y `autorizar_publicacion` |

---

## 13. Dependencias técnicas

| Dependencia | Tipo | Estado | Bloquea |
|-------------|------|--------|---------|
| Notion API access | Infraestructura | Existente | DB Publicaciones |
| Ghost self-hosted en VPS | Infraestructura | **Pendiente** — evaluar instalación | Blog automatizado |
| Google Cloud billing activo | Cuenta | **Pendiente** | Vertex AI para assets |
| LinkedIn Developer App | Cuenta | **Pendiente** — registro | LinkedIn adapter |
| OpenClaw en VPS | Infraestructura | Existente | Rick como meta-orquestador |
| n8n en VPS | Infraestructura | Existente | Webhooks, cron scheduling |
| Freepik API key | Cuenta | **Pendiente** — registro | Assets stock/fallback |
| `marked` o `pandoc` | Librería | Disponible | Markdown → HTML para Ghost |

---

## 14. Decisiones pendientes

| # | Decisión | Contexto | Estado |
|---|----------|----------|--------|
| 1 | Ghost vs Astro+Git como blog primario | Ghost v1 propuesto en [ADR-005](../adr/ADR-005-publicacion-multicanal.md), Astro como objetivo futuro. Astro tiene portabilidad total y cero lock-in | **✅ Aceptado** — Ghost self-hosted para v1; Astro como objetivo futuro (ADR-005 accepted 2026-04-21) |
| 2 | Vertex AI vs Gemini API directo para assets AI | Vertex propuesto en [ADR-006](../adr/ADR-006-capa-visual-editorial.md). Vertex tiene mejor SLA para preview. Gemini API es más simple | **Propuesta en ADR-006** — aceptado Vertex; pendiente UA-13 para automatización con cuentas de usuario |
| 3 | Freepik API como fallback vs solo stock UI | Freepik como fallback propuesto en [ADR-006](../adr/ADR-006-capa-visual-editorial.md). API es pay-per-use independiente de suscripción | **Propuesta en ADR-006** — diferida hasta UA-13 |
| 4 | X API directa vs tool gestionado (Typefully/Buffer) | X asistido v1 propuesto en [ADR-005](../adr/ADR-005-publicacion-multicanal.md). Pay-per-use directa: ~$7/mes. Tool: $5-8/mes pero absorbe cambios | **Propuesta en ADR-005** — re-evaluar en v2 |
| 5 | Estructura de copies por canal en Notion | ¿Propiedades en la misma DB o subpáginas? | **✅ Aceptado** — propiedades en la misma DB `Publicaciones` (spec v1 §5.2). Una sola DB para v1 |
| 6 | LinkedIn Company Page a futuro | Requiere entidad legal + CMA Development tier | **Diferida** — cuando exista entidad legal |
| 7 | Cron scheduling: n8n vs custom cron | n8n ya existe en VPS; custom cron es más ligero | **Probable n8n** — ya desplegado en VPS; decisión final pendiente de UA-14 (orquestación editorial: n8n vs Make vs Agent Stack) |
| 8 | Idempotencia: Redis vs Notion computed | Redis TTL 24h vs campo content_hash en Notion | **✅ Aceptado** — `content_hash` en Notion para v1 (zero-infra adicional); Redis TTL como v2 |
| 9 | Automatización visual con cuentas de usuario | Navegador + RPA para plataformas sin API (Freepik UI, LinkedIn manual) | **Pendiente** — investigación UA-13 por solicitar |
| 10 | Orquestación editorial: n8n vs Make vs Agent Stack | Qué capa coordina el flujo de publicación | **Pendiente** — investigación UA-14 por solicitar |

---

## 15. Criterios de aceptación

El sistema editorial v1 se considera **aceptado** cuando:

1. ✅ DB `Publicaciones` existe en Notion con todos los campos de §5.
2. ✅ `Perfil editorial David` existe como subpágina del hub con contenido de §4.3.
3. ✅ Rick puede generar un borrador desde briefing y marcarlo `ready_for_review`.
4. ✅ David puede marcar `aprobado_contenido = true` y el estado cambia a `content_approved`.
5. ✅ David puede marcar `autorizar_publicacion = true` y el estado cambia a `publish_authorized`.
6. ✅ Si David comenta después de `aprobado_contenido = true`, la aprobación se invalida y vuelve a `ready_for_review`.
7. ✅ Rick nunca marca `aprobado_contenido` ni `autorizar_publicacion` como `true`.
8. ✅ Ningún canal publica si `autorizar_publicacion != true`.
9. ✅ Rick puede publicar a Ghost automáticamente desde `publish_authorized`/`scheduled`.
10. ✅ Rick puede generar copy adaptado para LinkedIn con metadata completa.
11. ✅ Rick puede generar copy adaptado para X con metadata completa.
12. ✅ Publicación a LinkedIn requiere acción humana explícita (HITL verificable).
13. ✅ Publicación a X es manual en v1 (copy preparado en Notion).
14. ✅ CTA asignado según reglas de §10.3 y validado por gates de §6.
15. ✅ Rate-limiting de CTA opera según §10.4.
16. ✅ Al menos un asset visual generado por AI (Vertex) y validado.
17. ✅ Al menos un diagrama generado por Mermaid y publicado.
18. ✅ Auth lifecycle de LinkedIn documentado y alertas configuradas.

---

## Referencias Perplexity

| ID | Documento | Ruta |
|----|-----------|------|
| UA-10 | Publicación automatizada v2 | `Perplexity/Umbral Agent Stack/10_…/informe-publicacion-editorial.md` |
| UA-11 | Capa visual Rick v2 | `Perplexity/Umbral Agent Stack/11_…/capa-visual-rick-v1.md` |
| UA-12 | CTA/funnel v2 | `Perplexity/Umbral Agent Stack/12_…/cta-funnel-sistema-editorial.md` |
| UA-01 | Dolor audiencia | `Perplexity/Umbral Agent Stack/01_…/` |
| UA-02 | Mapa de autoridad | `Perplexity/Umbral Agent Stack/02_…/` |
| UA-04 | Dirección visual | `Perplexity/Umbral Agent Stack/04_…/` |
| UA-06 | Torneo de prompts | `Perplexity/Umbral Agent Stack/06_…/` |

Ver [perplexity-master-index.md](../research/perplexity-master-index.md) para inventario completo.
