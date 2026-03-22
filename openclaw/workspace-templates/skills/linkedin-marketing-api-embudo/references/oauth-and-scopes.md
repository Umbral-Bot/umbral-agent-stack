# oauth and scopes

## 1. baseline de autenticación

Para LinkedIn Marketing APIs:
- usar OAuth 2.0 con **Member Authorization (3-legged OAuth)**
- no proponer 2-legged OAuth como flujo base para Marketing APIs
- pedir el mínimo scope necesario

## 2. baseline de versionado y request

Para integraciones nuevas de marketing:
- usar `https://api.linkedin.com/rest/`
- enviar `Linkedin-Version: YYYYMM`
- enviar `X-Restli-Protocol-Version: 2.0.0`

Regla de higiene:
- si una guía vieja muestra `/v2`, no copiarla como baseline operativo para marketing actual
- si el usuario trae código legado, separar migración de operación nueva

## 3. scopes y permisos verificados hoy

## advertising api

Permisos abiertos que suelen importar para embudo y paid:
- `r_ads`
- `rw_ads`
- `r_ads_reporting`
- `r_organization_admin`
- `r_organization_social`
- `rw_organization_admin`
- `w_organization_social`
- `w_member_social`

Regla operativa:
- separar siempre lectura, reporting y mutación
- `rw_ads` exige rol válido en la ad account

## community management api

Permisos relevantes para embudo:
- `r_organization_followers`
- `r_organization_social`
- `r_organization_social_feed`
- `rw_organization_admin`
- `w_member_social`
- `w_member_social_feed`
- `w_organization_social`
- `w_organization_social_feed`
- `r_member_profileAnalytics` desde versiones `202504+`
- `r_member_postAnalytics` desde versiones `202506+`

Regla operativa:
- no usar member analytics como base por defecto del embudo
- para organization, combinar scopes con roles reales de page admin

## lead sync api

Permisos relevantes:
- `r_marketing_leadgen_automation`
- `r_ads`
- `r_events`
- `r_liteprofile`
- `r_organization_admin`

Regla operativa:
- Lead Sync API es un producto separado; access a Advertising no lo habilita solo
- `rw_ads` sirve para gestionar forms, pero no basta para leer leads de `leadFormResponses`
- para leer leads y gestionar `leadNotifications`, validar `r_marketing_leadgen_automation`

## conversions api

Permisos relevantes:
- `rw_conversions`
- `r_ads`
- `r_liteprofile`

Regla operativa:
- no meter Conversions API en el primer slice si todavía no existe trazabilidad seria del embudo

## member / personal profile

Permisos relevantes que pueden aparecer:
- `w_member_social`
- `w_member_social_feed`
- `r_member_profileAnalytics`
- `r_member_postAnalytics`
- `r_member_social`

Regla operativa:
- `w_member_social` existe, pero no lo conviertas en recomendación por defecto para embudo
- `r_member_social` es restringido; no planificar lectura de actividad personal como baseline

## 4. roles y scopes no son lo mismo

No decir “tenemos el scope, entonces ya se puede”.

Siempre validar ambas capas:
- scope correcto
- rol correcto

Ejemplos:
- organization posting requiere scope social y rol suficiente sobre la página
- analytics de organization requiere permisos de organization y rol con acceso a reporting/analytics
- lead sync patrocinado requiere rol en ad account y company page asociada

## 5. development tier vs standard tier

Separar por producto.

### advertising
- Development: lectura sin límite en ad accounts que administras, edición en hasta 5 ad accounts, creación de 1 test ad account; las ad accounts reales se crean por Campaign Manager
- Standard: sin ese límite operativo

### community management
- Development: 500 calls por app por 24h, 100 calls por miembro por 24h, `BATCH_GET` bloqueado, push de social actions deshabilitado
- Standard: sin restricciones

### lead sync y conversions
- tratarlos como productos separados con aprobación propia, no como un tier de Advertising o Community Management

## 6. lead sync migration a tener en cuenta

No usar como baseline nuevo las permissions legacy:
- `r_ads_leadgen_automation`
- `r_events_leadgen_automation`

La guía de migración indica que esas rutas legacy dejaron de funcionar después de julio de 2025. Para diseño nuevo, asumir el set actual basado en:
- `leadForms`
- `leadFormResponses`
- `leadNotifications`
- `r_marketing_leadgen_automation`

## 7. salida recomendada cuando el usuario pida OAuth o scopes

Responder con este orden:
1. objetivo del caso
2. entidad implicada
3. producto oficial
4. flujo OAuth
5. scopes exactos a validar
6. roles a validar
7. tier o approval dependency
8. headers y versión obligatorios
9. huecos por confirmar
10. siguiente validación concreta
