## Rick Benchmark Stability Retest (Second Case) — 2026-03-13

Ejecutado por: codex

### Objetivo

Comprobar si el comportamiento corregido de Rick para benchmarks competitivos ya quedó estable y generalizable, y no solo afinado al caso Cristian Tala.

Caso usado:

- referente: Justin Welsh
- proyecto: `Proyecto Embudo Ventas`
- pregunta adicional: distinguir benchmark público real vs adaptación para Umbral vs alcance de LinkedIn Marketing API

### Contexto

Antes de este retest ya estaban activos:

- hardening de persistencia de benchmark en proyecto
- skill `competitive-funnel-benchmark`
- skill nueva `linkedin-marketing-api-embudo`
- guardrails en runtime de Rick para exigir trazabilidad real

### Prompt de retest

Se le pidió a Rick:

- benchmark profundo del caso Justin Welsh
- adaptación al embudo de Umbral
- separación clara entre:
  - observación pública real
  - adaptación recomendada
  - qué parte sí/no conectaría con LinkedIn Marketing API
- persistencia dentro del proyecto si el caso servía al embudo

### Evidencia de ejecución real

La traza del tramo mostró este uso de tools:

- `memory_search`: 1
- `web_fetch`: 10
- `umbral_linear_list_projects`: 1
- `umbral_windows_fs_write_text`: 1
- `umbral_linear_update_issue_status`: 1
- `umbral_linear_create_project_update`: 1
- `umbral_notion_upsert_project`: 1

### Lectura del comportamiento

Rick esta vez no se limitó a responder en chat.

Repitió el patrón correcto:

1. investigó fuentes reales
2. produjo benchmark utilizable
3. lo persistió en carpeta compartida
4. dejó comentario en Linear
5. dejó project update en Linear
6. actualizó el registro del proyecto en Notion

### Persistencia confirmada

Artefacto creado:

- `G:\Mi unidad\Rick-David\Proyecto-Embudo-Ventas\benchmark-justin-welsh-linkedin-funnel-vs-marketing-api-2026-03-13.md`

Verificación independiente:

- lectura directa al Worker remoto de la VM
- `ok: true`
- longitud: `10000`

### Trazabilidad confirmada

Linear:

- comentario agregado en la issue del proyecto
- project update creado para `Proyecto Embudo Ventas`

Notion:

- `Proyecto Embudo Ventas` actualizado nuevamente vía `notion.upsert_project`

### Hallazgo importante

La estabilidad del comportamiento ya no depende del caso Cristian Tala.

Con Justin Welsh, Rick volvió a:

- investigar
- separar capas de análisis
- persistir resultados
- dejar trazabilidad real

Eso sugiere que el patrón nuevo ya es reutilizable.

### Matiz técnico

En este retest no hizo `browser.*`.

No fue necesariamente un fallo, porque el caso se sostuvo bien con:

- artículo estratégico
- páginas de producto
- free series
- home/ecosistema público

Pero si en el futuro se pide teardown de:

- comentarios
- CTA dentro de plataforma
- primer comentario
- perfil vivo de LinkedIn

entonces sí convendrá exigir `browser.*` como parte del benchmark.

### Conclusión

La corrección ya parece estable.

Rick no solo mejoró el caso original; ahora reproduce el patrón correcto en un segundo referente y deja el benchmark convertido en entregable real del proyecto.
