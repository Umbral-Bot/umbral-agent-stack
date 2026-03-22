---
name: linkedin-marketing-api-embudo
description: >-
  operar linkedin marketing api de forma realista para el proyecto embudo de
  umbral dentro del stack openclaw + worker + dispatcher + n8n + notion +
  linear. usar cuando chatgpt deba decidir que partes de linkedin conviene
  resolver con api oficial, que productos y permisos oficiales aplican, que
  roles de admin o ad account son necesarios, que depende de development tier,
  standard tier o access review, y que no debe prometerse. cubre organization o
  company page, member o perfil personal, ads y reporting, lead sync,
  community management, analytics y conversions, siempre separando soportado por
  la api, requiere aprobacion, no recomendado y fuera de scope, con
  recomendacion operativa para embudo.
metadata:
  openclaw:
    emoji: "🔗"
    requires:
      env: []
---

# LinkedIn Marketing API para Embudo

Usar esta skill para diseñar, revisar o aterrizar trabajo real del proyecto embudo que dependa de LinkedIn Marketing API. No explicar LinkedIn en abstracto: decidir con rigor qué conviene implementar en Umbral, qué producto oficial corresponde, qué prerrequisitos faltan y qué fallback prudente usar.

## Fuente de verdad obligatoria

Tomar como autoridad solo documentación oficial vigente de LinkedIn.

Prioridad de consulta:
1. `https://learn.microsoft.com/en-us/linkedin/marketing/`
2. `https://learn.microsoft.com/en-us/linkedin/marketing/increasing-access`
3. `https://learn.microsoft.com/en-us/linkedin/marketing/versioning`
4. `https://learn.microsoft.com/en-us/linkedin/shared/authentication/authentication`
5. `https://developer.linkedin.com/product-catalog/marketing`

Usar los archivos de `references/` para el marco operativo y ejemplos, pero no para sobreescribir la documentación oficial si hay conflicto.

Si hay una discrepancia entre una referencia vieja y una página vigente, priorizar la página vigente y degradar cualquier afirmación que no esté confirmada.

## Regla maestra de salida

Antes de recomendar o ejecutar una integración, clasificar cada afirmación en una de estas cuatro etiquetas y mantenerlas separadas en toda la respuesta:

- `soportado por la api`
- `requiere aprobacion`
- `no recomendado`
- `fuera de scope`

Nunca mezclar estas etiquetas en una misma frase ambigua.

## Flujo de trabajo

Seguir este orden.

### 1. Clasificar el pedido por superficie exacta

Primero decidir cuál es el plano principal:

1. `company page / organization`
2. `member / perfil personal`
3. `ads / reporting`
4. `lead sync`
5. `community management`
6. `analytics`
7. `conversions`
8. `arquitectura de stack / decision operativa`

Si el pedido mezcla varios planos, separar por bloques. No asumir que permisos o accesos de ads cubren organization posting, ni que permisos de organization cubren member.

### 2. Resolver el producto oficial correcto

Distinguir explícitamente:

- Community Management API para page management, posts, social actions y analytics de organization
- Advertising API para cuentas publicitarias, campaign management y reporting
- Lead Sync API para `leadForms`, `leadFormResponses` y `leadNotifications`
- Conversions API para upload de conversiones
- Member scopes solo cuando el caso realmente es sobre una cuenta personal y exista soporte oficial

Si el usuario habla de “LinkedIn” en general, no responder en genérico: precisar sobre cuál producto y entidad se puede actuar.

### 3. Verificar acceso antes de proponer implementación

Confirmar en este orden:

1. existe una app de LinkedIn
2. el producto oficial correcto está aprobado para esa app
3. el caso usa Member Authorization de 3-legged OAuth
4. existen scopes exactos para el caso
5. el miembro autenticado tiene rol suficiente sobre la organization o la ad account
6. el producto está en el tier o access review correcto
7. la versión de API y endpoint siguen vigentes

Si una capa no está confirmada, marcar el caso como `requiere aprobacion` o `bloqueado por acceso`, no como implementable.

## Baseline técnico obligatorio

### A. OAuth

Para Marketing APIs, asumir **3-legged OAuth** como flujo base. No proponer client credentials como sustituto para Marketing APIs. Consultar `references/oauth-and-scopes.md`.

### B. Versionado y endpoint base

Para Marketing APIs versionadas:

- usar base path `https://api.linkedin.com/rest/`
- enviar header `Linkedin-Version: YYYYMM`
- enviar header `X-Restli-Protocol-Version: 2.0.0`

No usar ejemplos viejos de `/v2/` como plantilla operativa para integraciones nuevas de marketing.

### C. Verificación de roles

Antes de publicar, leer analytics o extraer leads, comprobar roles por API. Preferir:

- Organization Access Control u Organization Authorizations para páginas
- Account Access Control para ad accounts

No hardcodear privilegios “porque alguien dijo que es admin”.

## Elección de mecanismo dentro del stack Umbral

### Preferir API oficial

Elegir API oficial cuando:
- la documentación soporta claramente el caso
- el flujo requiere trazabilidad o sincronización confiable
- el dato termina en Notion, CRM, Linear o n8n
- el caso es organization posting, analytics, reporting, lead sync o conversions

### Preferir n8n

Elegir n8n cuando:
- la API ya resuelve el dato o la acción y solo falta orquestación
- hay que normalizar payloads, deduplicar, enrutar o reintentar
- conviene separar polling, webhooks, retries, colas y observabilidad

### Browser o RPA solo como último recurso

Usar browser o RPA solo si:
- no hay soporte razonable por API oficial
- la acción es puntual, visible y con gate humano
- no se está reemplazando un permiso faltante con automatización frágil

Nunca vender browser o RPA como capacidad nativa de LinkedIn Marketing API.

### Mantener gate humano

Exigir gate humano cuando:
- el caso afecta publicación externa, community management sensible o presupuesto publicitario
- falta claridad de permisos, términos o compliance
- el caso toca member/personal profile
- la alternativa depende de un workaround no oficial

## Qué sí conviene hacer en embudo

Foco primario, siempre sujeto a acceso aprobado:

- publicar y gestionar contenido institucional de organization con Posts API
- medir follower, page, share, social metadata y video analytics de organization
- sincronizar leads oficiales con Lead Sync API hacia Notion o CRM
- generar trazabilidad y seguimiento en Linear
- conectar reporting de ads y conversions cuando exista cuenta, owner y acceso real
- usar community management oficial sobre organization, no sobre perfil personal por defecto

Consultar `references/embudo-use-cases.md`.

## Qué no debe asumirse

Bloquear estas suposiciones por defecto:

- scraping masivo de perfiles, posts o comentarios como si fuera capacidad oficial
- DMs automáticos o outreach automático de perfil personal
- actuar sobre organizations, ad accounts o leads sin roles y scopes reales
- confundir Community Management API con permiso general para automatizar LinkedIn completo
- cerrar un diseño con Development tier como si fuera producción lista
- asumir que Lead Sync viene incluido por tener Advertising API

## Guardrails específicos sobre member / perfil personal

- `w_member_social` existe, pero no convertirlo en recomendación por defecto para embudo
- `r_member_social` es una capacidad restringida; no planificar el flujo alrededor de lectura de posts personales salvo evidencia documental y aprobación explícita
- no diseñar nurturing, outreach o community management del embudo alrededor de perfiles personales salvo decisión explícita, alcance claro y validación legal/operativa

## Guardrails específicos sobre lead capture

- Lead Sync soporta varios tipos de leads, incluidos patrocinados y orgánicos, pero no asumir que toda captura desde página sigue abierta para creación nueva
- si el caso depende de leads de company page, validar el estado actual del producto antes de prometer creación o descarga de formularios
- para embudo, priorizar sincronización de leads oficiales existentes sobre inventar captura no soportada

## Guardrails sobre access tiers

No generalizar tiers. Separar siempre:

- Advertising API: Development vs Standard
- Community Management API: Development vs Standard
- Lead Sync API: producto separado, sin asumir que hereda acceso de Advertising
- Conversions API: producto separado, con aprobación propia

Si el caso depende de BATCH_GET o webhooks de social actions, validar si sigue en Development tier. No proponer una arquitectura que requiera algo bloqueado en ese tier.

## Salida por defecto

Responder en este orden salvo que el usuario pida otro:

### 1. lectura del caso
- objetivo de embudo
- superficie de linkedin implicada
- producto oficial implicado
- veredicto inicial de viabilidad

### 2. matriz de decisión
Para cada bloque relevante, usar estas etiquetas visibles:
- `soportado por la api`
- `requiere aprobacion`
- `no recomendado`
- `fuera de scope`

### 3. prerrequisitos reales
- app
- producto aprobado
- oauth
- scopes
- roles
- tier o access review
- versión y headers obligatorios

### 4. diseño recomendado para el stack
- qué decide OpenClaw
- qué resuelve Worker
- qué orquesta n8n
- qué guarda Notion o CRM
- qué crea o sigue Linear
- dónde queda el gate humano

### 5. siguiente slice operativo
Cerrar con una secuencia pequeña y accionable, por ejemplo:
- validar producto y access tier
- validar scopes y roles reales
- definir payload normalizado
- diseñar workflow n8n
- abrir checklist o issue con trazabilidad

## Archivos de apoyo

Consultar según el problema:

- `references/capabilities-matrix.md` para decidir si un caso cae en organization, member, lead sync, ads o conversions
- `references/oauth-and-scopes.md` para OAuth, headers, versioning, scopes y tiers
- `references/embudo-use-cases.md` para slices de implementación en Umbral
- `references/fallback-strategy.md` para rediseñar o bloquear casos no soportados
