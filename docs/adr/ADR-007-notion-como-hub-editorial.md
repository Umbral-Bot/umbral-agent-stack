# ADR-007: Notion como Hub Editorial — Estructura y Gobernanza

## Estado

Proposed — 2026-04-21

## Contexto

Rick necesita un hub operativo para gestionar el ciclo de vida de contenido editorial: desde briefing hasta publicación y tracking. La decisión previa (auditoría de Notion aceptada en sesión anterior) estableció que el hub existente `Sistema Editorial Automatizado Umbral` en Notion es el contenedor canónico. Este ADR formaliza esa decisión y documenta las consecuencias.

Las alternativas fueron evaluadas contra los requisitos: DB relacional con views, human-in-the-loop nativo (comentarios, estados), API para automatización, y compatibilidad con el stack existente (OpenClaw, n8n, dispatcher).

## Decisión

### Notion como hub editorial único para v1

- **Hub raíz**: `Sistema Editorial Automatizado Umbral` (página existente).
- **DB nueva**: `Publicaciones` (~25 propiedades, schema en [spec v1 §5](../specs/sistema-editorial-rick-v1.md#5-db-publicaciones--propuesta-de-schema)).
- **Subpágina nueva**: `Perfil editorial David` (derivada de investigaciones UA-01, UA-02).
- **Reutilizar**: `Fuentes confiables` (DB existente bajo la página `Fuentes`; compartida con Umbral Bot).

> **Nota**: `PublicationLog` como DB separada se difiere a v1.1. En v1 el tracking mínimo de publicación se registra inline en `Publicaciones` (ver [spec v1 §5.3](../specs/sistema-editorial-rick-v1.md#53-tracking-de-publicación-inline-en-publicaciones)).

### Lista NO-TOUCH explícita

Las siguientes páginas/DBs de Notion **no se modifican** bajo ninguna circunstancia en el contexto del sistema editorial:

| Página/DB | Razón |
|-----------|-------|
| `Bandeja de revisión - Rick` | Pertenece al flujo conversacional del bot, no al editorial |
| `Control Room` | Gobernanza de Notion, no editorial |
| `Sistema Maestro Apoyo Editorial` | Legacy; congelada hasta re-evaluación |
| `Asesorías & Proyectos` | Negocio/CRM, no editorial |

### API y automatización

- Rick lee/escribe `Publicaciones` vía Notion API.
- n8n gestiona webhooks y cron scheduling contra la DB.
- Dispatcher puede poll por estado para triggering de publicación.
- Rate limit Notion API: ~3 requests/segundo sustained. Mitigación: cache local + backoff.

### Gobernanza

- Solo David puede crear/modificar la estructura de la DB (schema changes).
- Rick puede crear y actualizar páginas (filas) pero **nunca** cambiar propiedades de la DB.
- Rick **nunca** marca `aprobado_contenido` ni `autorizar_publicacion` como `true`. Solo David.
- Cualquier cambio de schema requiere actualización de la spec v1 y este ADR.

## Alternativas consideradas

### 1. Linear como hub editorial

Rechazada. Linear es excelente para issue tracking pero no tiene:
- Rich text body nativo para contenido largo.
- Comentarios inline en el body (solo comentarios de issue).
- Multi-select, relations, rollups nativos.
- Views tipo board, gallery, calendar integradas.
- Template de página por tipo de contenido.

Linear se usa para tracking de desarrollo (issues, sprints), no para gestión editorial.

### 2. GitHub Issues + Projects

Rechazada como hub primario. GitHub Issues carece de:
- Rich body editing (markdown sí, pero sin embed visual).
- DB relacional con propiedades tipadas.
- Views nativas tipo kanban/calendar para editorial.
- Comentarios inline en el contenido.

GitHub Issues es mejor para tracking técnico (bugs, features). Se usa como fuente para tickets de desarrollo, no para gestión editorial.

### 3. Custom DB (PostgreSQL/SQLite) con UI custom

Rechazada para v1. Requiere construir:
- CRUD + API REST para la DB.
- UI de gestión editorial (React/Next.js).
- Sistema de comentarios y revisión.
- Scheduling y notificaciones.

Overhead de desarrollo desproporcionado para un solo editor + un agente. Notion ya provee todo esto. Viable si el volumen o los usuarios crecen significativamente.

### 4. Airtable como hub

Rechazada. Pricing más alto que Notion para features equivalentes ($20/usuario/mes Pro). API similar pero ecosistema de integraciones inferior para el stack actual. No aporta ventaja sobre Notion que ya está en uso.

### 5. Google Sheets + Apps Script

Rechazada. Sin rich text para contenido editorial. Sin sistema de estados tipado. Sin comentarios inline. Funcional para tracking simple pero no para gestión editorial completa.

### 6. Notion + DB separada (híbrido)

Considerada pero diferida. Modelo donde Notion gestiona el flujo humano y una DB PostgreSQL maneja la capa de automatización. Overhead de sincronización alto para v1. Viable si los rate limits de Notion se vuelven un cuello de botella real.

## Consecuencias

### Positivas

- **Zero-build UI**: Notion provee kanban, calendar, gallery, table views sin desarrollo.
- **HITL nativo**: David revisa y aprueba en Notion con dos gates separados (contenido + publicación); no necesita UI custom ni CLI.
- **Relational DB**: `Publicaciones` con tracking inline; `PublicationLog` relacional diferida a v1.1.
- **Formulas y rollups**: métricas calculadas (posts por semana, CTA distribution, etc.).
- **Templates**: páginas pre-configuradas por tipo de pieza (`tecnico_corto`, `caso_estudio`, etc.).
- **Búsqueda**: búsqueda full-text nativa sobre todo el contenido.
- **Existente**: el hub, `Fuentes confiables`, y el workspace ya existen y están auditados.

### Negativas

- **Rate limits**: ~3 req/s sustained. Para 50-100 posts/mes con actualizaciones frecuentes, es suficiente pero apretado con batching.
- **No scheduling nativo**: Notion no tiene cron ni scheduled automations. Requiere n8n o cron externo.
- **No webhooks nativos push**: Requiere polling o n8n como bridge.
- **Schema lock-in**: cambiar propiedades de una DB Notion es manual y no versionable en Git.
- **No branching/versioning**: no hay historial de cambios por campo como Git. Solo page history nativo.
- **Single point of failure**: si la API de Notion cae, el flujo editorial se detiene.

## Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|-----------|
| Notion API rate limits bloquean flujo | Baja-Media | Medio | Cache local con TTL, backoff exponencial, batch reads |
| Notion depreca o cambia API v1 | Muy baja | Alto | Schema exportable; migración a DB propia documentada como plan B |
| DB schema drift (cambios manuales accidentales) | Media | Medio | Gobernanza: solo David modifica schema; checklist de cambios en spec |
| Contenido editorial perdido (Notion bug) | Muy baja | Alto | Backup: export markdown semanal a Git via API |
| Rick corrompe datos en DB por bug | Baja | Medio | Validación pre-write; idempotencia por content_hash; gates de estado |
| Crecimiento de editores rompe modelo single-user | Baja (largo plazo) | Medio | Migrar a DB custom cuando >2 editores activos |

## Fuentes Perplexity

- **UA-10**: `Perplexity/Umbral Agent Stack/10_ Investigación Sobre Publicación Automatizada/informe-publicacion-editorial.md` — §7 schema DB Publicaciones
- **UA-12**: `Perplexity/Umbral Agent Stack/12_ CTA Funnel y Estrategia Contenido/cta-funnel-sistema-editorial.md` — §7 metadata por pieza
- **UA-01**: `Perplexity/Umbral Agent Stack/01_ Investigación Dolor y Audiencia AECO/` — dolor y audiencia para perfil editorial
- **UA-02**: `Perplexity/Umbral Agent Stack/02_ Mapa de Autoridad y Credibilidad/` — mapa de autoridad para perfil editorial
- Auditoría de Notion y decisiones de gobernanza (sesiones previas con Copilot/Claude)
