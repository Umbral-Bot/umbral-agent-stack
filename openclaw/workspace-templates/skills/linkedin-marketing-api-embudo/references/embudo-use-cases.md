# embudo use cases

Estos casos de uso priorizan operación real de Umbral, no explicación genérica de la API.

## 1. publicar contenido institucional en company page

### objetivo
Distribuir contenido del embudo desde la surface institucional correcta.

### producto oficial
Community Management API con Posts API.

### diseño recomendado
- OpenClaw clasifica el asset, CTA y objetivo
- aprobación humana antes de salida externa
- Worker prepara payload tipado y media metadata si hace falta
- n8n gestiona scheduling, retries, registro y alertas
- Notion guarda el asset aprobado, permalink, estado y owner
- Linear recibe incidencias si falla la publicación

### prerequisitos críticos
- Community Management API aprobada
- `w_organization_social`
- rol válido sobre la organization
- `Linkedin-Version` y `X-Restli-Protocol-Version`

### guardrails
- no confundir post institucional con perfil personal
- no cerrar el diseño sin confirmar roles reales
- no prometer community management amplio si aún se depende de Development tier restringido

## 2. medir rendimiento de contenido y página

### objetivo
Decidir qué formatos, temas y CTAs alimentan mejor el embudo.

### señales útiles
- follower statistics
- page statistics
- share statistics
- social metadata
- video analytics

### diseño recomendado
- n8n ejecuta jobs recurrentes
- normaliza snapshots por ventana temporal
- Notion concentra dashboard y base operativa
- OpenClaw interpreta señales y propone acciones
- Linear recibe tareas cuando cae el rendimiento o hay hallazgos de optimización

### caveat operativo
Si la estrategia depende de `BATCH_GET` o notificaciones push de social actions, verificar si la app sigue en Community Management Development tier.

## 3. sincronizar leads oficiales a Notion o CRM

### objetivo
Tomar leads oficiales de LinkedIn y convertirlos en seguimiento accionable.

### producto oficial
Lead Sync API con:
- `leadForms`
- `leadFormResponses`
- `leadNotifications`

### diseño recomendado
1. LinkedIn genera el lead
2. n8n recibe webhook o hace polling
3. Worker normaliza payload
4. deduplicar por clave de negocio
5. crear o actualizar registro en Notion o CRM
6. crear tarea o seguimiento en Linear cuando corresponda
7. dejar trazabilidad del estado

### campos mínimos sugeridos
- lead id o identificador externo
- owner surface
- lead type
- source campaign o form
- fecha de captura
- stage
- owner interno
- siguiente acción
- notas de calificación

### caveat importante
La documentación actual indica que:
- se soportan leads `SPONSORED`, `EVENT`, `COMPANY` y `ORGANIZATION_PRODUCT`
- pero los lead forms para LinkedIn Pages y Showcase Pages ya no están disponibles para crear ni descargar; los existentes siguen funcionando

Por tanto:
- sí conviene diseñar sync de leads oficiales existentes
- no conviene prometer una estrategia nueva de captura basada en crear page lead forms si eso no está confirmado

## 4. reporting de ads y performance paga

### objetivo
Conectar paid con el resto del embudo cuando ya exista base operativa.

### cuándo sí
- ya existe trazabilidad mínima entre contenido, lead y seguimiento
- hay ad account real, owner y presupuesto
- hay permisos de reporting validados

### diseño recomendado
- n8n trae métricas
- Worker normaliza por campaña, objetivo y ventana temporal
- Notion concentra reporting operativo
- OpenClaw interpreta cambios y propone acciones
- Linear captura incidencias o próximos experimentos

### cuándo no priorizar
- cuando aún no existe lead sync oficial
- cuando el embudo no tiene owner ni proceso comercial claro

## 5. conversions api

### objetivo
Cerrar mejor la medición entre LinkedIn Ads y resultados del negocio.

### cuándo sí
- hay operación paga madura
- existe evento/conversión bien definido
- hay owner técnico y comercial
- el stack ya tiene trazabilidad seria

### diseño recomendado
- mantener el upload tipado en Worker
- usar n8n para colas, reintentos y observabilidad
- registrar estado de envío y errores en Notion
- abrir incidencias en Linear ante drift o fallos repetidos

### no adelantar
No convertir Conversions API en prioridad inicial si el equipo aún no resolvió page posting, analytics básicos y lead sync.

## 6. community management prudente

### alcance razonable
- leer y gestionar interacciones de organization donde la API lo soporte
- monitorear señales útiles para el equipo editorial/comercial

### no convertir en promesa
- moderación total de conversaciones
- scraping de comentarios a escala
- automatización de inbox o DMs personales
- operar perfil personal como si fuera una page institucional

## 7. orden sugerido de implementación para embudo

1. validar producto, app y tier real
2. resolver organization posting institucional
3. resolver analytics básicos de organization
4. resolver lead sync oficial
5. conectar Notion o CRM
6. agregar Linear y observabilidad
7. evaluar ads reporting
8. evaluar conversions
