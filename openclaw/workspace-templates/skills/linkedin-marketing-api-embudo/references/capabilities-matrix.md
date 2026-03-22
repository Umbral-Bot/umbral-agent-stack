# capabilities matrix

Usar esta matriz para aterrizar un pedido sin mezclar superficies distintas de LinkedIn.

## 1. regla de lectura

Para cada caso, responder siempre con cuatro etiquetas visibles:
- `soportado por la api`
- `requiere aprobacion`
- `no recomendado`
- `fuera de scope`

No mover un caso a `soportado` si falta cualquiera de estas pruebas:
- producto oficial aplicable
- app aprobada para ese producto
- 3-legged OAuth para el miembro correcto
- scopes verificados
- rol suficiente en organization o ad account
- tier o access review resuelto cuando aplique
- versión vigente y headers obligatorios

## 2. matriz por superficie

| superficie | producto oficial | endpoints o familias útiles | member permissions a validar | roles a validar | tier o approval dependency | recomendación para embudo | notas de guardrail |
|---|---|---|---|---|---|---|---|
| company page posting | community management | `posts`, assets de media, social metadata | `w_organization_social`, a veces `r_organization_social` | `ADMINISTRATOR`, `DIRECT_SPONSORED_CONTENT_POSTER`, y en docs de Posts también `CONTENT_ADMIN`/`CONTENT_ADMINISTRATOR` | Community Management API + Development o Standard | sí, prioridad alta | usar gate humano para publicación externa |
| company page analytics | community management | follower, page, share, video analytics, social metadata | `r_organization_admin`, `r_organization_social` y/o feed scopes según caso | `ADMINISTRATOR`, `ANALYST`, `CURATOR` u otros roles con analytics según endpoint | Community Management API; algunas arquitecturas quedan limitadas en Development tier | sí, prioridad alta | no prometer métricas no documentadas |
| social actions / moderación de organization | community management | `socialMetadata`, social action feeds, notifications | `r_organization_social_feed`, `w_organization_social_feed`, `r_organization_social`, `w_organization_social` | normalmente admin de organization | Development tier bloquea push de social actions; Standard elimina esa restricción | sí, con alcance prudente | no vender moderación total ni scraping de comentarios |
| lead sync patrocinado | lead sync | `leadForms`, `leadFormResponses`, `leadNotifications` | `r_marketing_leadgen_automation`, `r_ads`, `r_organization_admin`, `r_liteprofile` según flujo | rol válido en ad account y company page asociada | Lead Sync API separada; no viene incluida por Advertising | sí, prioridad alta | perfecto para n8n + Notion/CRM + Linear |
| lead sync orgánico | lead sync | `leadForms`, `leadFormResponses`, `leadNotifications` | `r_marketing_leadgen_automation`, `r_events` o `r_organization_admin` según owner | `ADMINISTRATOR`, `LEAD_GEN_FORMS_MANAGER`, `CURATOR`, `CONTENT_ADMINISTRATOR`, `ANALYST` según doc | Lead Sync API separada | sí, pero validar estado exacto del surface | no asumir creación nueva de page lead forms |
| ads reporting | advertising | reporting y analytics de ad account | `r_ads_reporting`, `r_ads` | rol en ad account | Advertising API Development o Standard | sí, después de la base orgánica y lead sync | separar reporting de campaign management |
| campaign management | advertising | cuentas, campañas, creatives | `rw_ads`, `r_ads` | rol en ad account | Development limita edición a 5 ad accounts y 1 test ad account | opcional, posterior | no meterlo en el primer slice si el embudo aún no está estable |
| conversions upload | conversions | conversions api | `rw_conversions`, `r_ads`, `r_liteprofile` | rol en ad account y setup comercial real | Conversions API separada, requiere aprobación | sí, pero no en fase 1 | útil cuando ya existe operación paga madura |
| member posting | community management o advertising | member social scopes | `w_member_social` | consentimiento del miembro; no depende de organization | producto aprobado + consentimiento | no recomendado por defecto | no usar como base del embudo institucional |
| member read-back / personal analytics | community management | member social o member analytics | `r_member_social`, `r_member_profileAnalytics`, `r_member_postAnalytics` | consentimiento del miembro | `r_member_social` es restringido; analytics depende de versiones nuevas | normalmente fuera de scope inicial | no prometer lectura de actividad personal como capacidad estándar |
| dms automáticos | ninguno dentro de este alcance | n/a | n/a | n/a | n/a | fuera de scope | bloquear |
| scraping masivo de perfiles o terceros | ninguno dentro de este alcance | n/a | n/a | n/a | n/a | fuera de scope | bloquear |

## 3. preguntas de triage obligatorias

Antes de decidir, responder internamente:
1. ¿La entidad es organization, ad account, lead form o member?
2. ¿Existe un producto oficial exacto para esa entidad?
3. ¿La app está aprobada para ese producto?
4. ¿El miembro autenticado tiene el rol correcto?
5. ¿La arquitectura propuesta depende de una restricción de Development tier?
6. ¿El caso puede resolverse mejor con organization en lugar de member?

## 4. errores frecuentes a bloquear

- asumir que Community Management equivale a “puedo automatizar LinkedIn entero”
- asumir que Lead Sync viene desbloqueado por tener Advertising API
- asumir que una persona con acceso comercial también tiene permiso técnico para leads
- usar member automation como atajo para un caso que debería resolverse con organization
- citar endpoints viejos de `/v2` o `ugcPosts`/`shares` como baseline operativo nuevo
- olvidar `Linkedin-Version` o `X-Restli-Protocol-Version: 2.0.0`
