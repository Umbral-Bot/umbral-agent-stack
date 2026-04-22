# ADR-005: Publicación Multicanal — Factibilidad y Estrategia por Canal

## Estado

Accepted — 2026-04-21

## Contexto

El sistema editorial de Rick necesita publicar contenido técnico B2B en múltiples canales: LinkedIn, X (Twitter) y blog. Cada canal tiene restricciones de API, ToS, pricing y estabilidad distintas. La investigación UA-10 evaluó la factibilidad técnica y operativa de cada canal para un consultor independiente (sin partnership MDP en LinkedIn, sin empresa legal registrada, volumen ~20-40 posts/mes en redes, ~10-40 posts/año en blog).

La decisión afecta qué canales se automatizan completamente, cuáles requieren human-in-the-loop, y cuáles se difieren.

## Decisión

### Blog: Ghost self-hosted — automatización completa (v1)

- **Plataforma v1**: Ghost self-hosted en VPS existente.
- **Automatización**: completa. Admin API + JWT + webhooks. Scheduling nativo.
- **Objetivo futuro**: migrar a Astro + Git + Cloudflare Pages para portabilidad total y cero lock-in (~$15/año).
- **Cross-post**: Hashnode con `canonicalUrl` apuntando al blog primario (fase 2).

### LinkedIn perfil personal — automatización con HITL obligatorio

- **API**: `POST /rest/posts` con `w_member_social` (self-serve).
- **HITL**: obligatorio. ToS §3.1.26 prohíbe automatizar publicaciones. Rick prepara draft + media en Notion; David clickea "Publicar".
- **Auth**: OAuth 2.0, access token 60 días sin refresh (no-MDP). Alerta día 55 para re-auth.
- **Company Page**: no viable sin entidad legal. Diferida.

### X — asistido en v1, API directa diferida a v2

- **v1**: Rick genera copy final + media URLs en Notion. David publica manualmente.
- **v2**: `POST /2/tweets` con pay-per-use (~$0.015/post + $0.20 si URL, ~$7/mes).
- **Razón del diferimiento**: plataforma inestable (5 cambios materiales en 36 meses). No justifica inversión en adapter hasta estabilización.
- **Fallback**: si X rompe reglas otra vez, redirigir a TypefullyAdapter o BufferAdapter.

## Alternativas consideradas

### 1. Automatización completa en todos los canales

Rechazada. LinkedIn ToS §3.1.26 lo prohíbe explícitamente sin partnership MDP. En X, la inestabilidad hace que un adapter directo tenga vida útil incierta.

### 2. Todo vía tools gestionados (Buffer/Typefully/Hootsuite)

Rechazada como estrategia primaria. Los tools resuelven la publicación pero no la generación ni el flujo editorial. Además, agregan capa de dependencia y costo ($5-8/mes por tool) sin resolver el problema de auth lifecycle. Se mantiene como fallback para X.

### 3. Blog en WordPress self-hosted

Rechazada. Mayor mantenimiento (PHP/MySQL/plugins/security) que Ghost o Astro. Sin ventaja funcional para contenido técnico markdown.

### 4. Blog en WordPress.com o Webflow

Rechazada. WordPress.com: $300/año para acceso pleno (Business). Webflow: $276/año + lock-in alto + poco orientado a markdown técnico.

### 5. Notion-as-CMS (Super/Feather/Notaku/Potion)

Rechazada. Sin control suficiente para screenshots BIM, code blocks técnicos y SEO avanzado.

### 6. X API directa desde v1

Rechazada para v1. El pay-per-use es económico (~$7/mes) pero la plataforma cambió reglas 5 veces en 36 meses. La inversión en adapter no justifica el riesgo de rotura. Mejor usar asistido v1 y evaluar en 3-6 meses.

## Consecuencias

### Positivas

- Blog con automatización completa desde v1 — canal más estable y con mayor durabilidad del contenido.
- HITL en LinkedIn protege contra violación de ToS y preserva autenticidad.
- Desacoplamiento de X permite absorber cambios sin romper el sistema.
- Arquitectura de adapters (interfaz `publish(post) → {platform_post_id, url}`) permite swap sin tocar el orquestador.

### Negativas

- LinkedIn requiere re-auth manual cada ~55 días. Carga operativa recurrente.
- X asistido en v1 implica fricción manual para cada post.
- Ghost en VPS requiere instalación y mantenimiento de Node.js + MySQL/SQLite.
- No hay scheduling nativo en LinkedIn API — requiere cron propio.

## Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|-----------|
| LinkedIn cambia ToS o depreca `w_member_social` | Baja | Alto | Monitorear changelog trimestral. Fallback: publicación manual |
| X cambia pricing/API otra vez | Alta | Medio | Adapter abstraction. Fallback a Typefully |
| Ghost depreca Admin API o JWT auth | Muy baja | Alto | Self-hosted = control de versión. Migración a Astro planeada |
| Auth token LinkedIn expira sin re-auth | Media | Medio | Alerta automatizada día 55 |
| Re-auth LinkedIn falla (usuario deslogueado) | Baja | Medio | Proceso manual documentado en runbook |

## Fuentes Perplexity

- **UA-10**: `Perplexity/Umbral Agent Stack/10_ Investigación Sobre Publicación Automatizada/informe-publicacion-editorial.md` — factibilidad completa por canal con endpoints, auth, pricing, rate limits
- **UA-07**: `Perplexity/Umbral Agent Stack/07_ Factibilidad de Publicación Automatizada Multicanal/factibilidad_publicacion_automatizada.md` — versión previa (histórica, sustituida por UA-10)
