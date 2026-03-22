# Diseño exacto — OpenClaw shell de dashboard

Fecha: 2026-03-16
Autor: Codex

## Objetivo

Rediseñar `OpenClaw` para que deje de funcionar como reporte textual generado y pase a operar como:

- shell fija de dashboard humano,
- basada en vistas enlazadas de bases reales,
- con un resumen corto automatizable arriba,
- y con mantenimiento centrado en datos, no en narrativa.

## Principio de diseño

`OpenClaw` no debe ser la fuente de verdad.

La fuente de verdad sigue siendo:

- `📁 Proyectos — Umbral`
- `🗂 Tareas — Umbral Agent Stack`
- `📬 Entregables Rick — Revisión`
- `📬 Bandeja Puente`

`OpenClaw` debe ser solo:

- panel de lectura,
- navegación,
- y priorización.

## Estructura exacta de la página

La página debe quedar con este orden, sin secciones narrativas largas:

### 1. Encabezado fijo

Bloques:

- `heading_1`: `OpenClaw`
- `callout`: resumen corto del rol de la página
- `paragraph`: una sola línea explicando la diferencia entre `OpenClaw` y `Dashboard Rick`

Texto sugerido:

- `OpenClaw es el panel operativo humano. Aquí revisas qué atender, aprobar o destrabar.`
- `Para salud técnica del stack, usa Dashboard Rick.`

### 2. Resumen operativo corto

No más de 4 indicadores.

Idealmente como:

- tabla corta o callout con KPIs

Contenido:

- entregables pendientes de revisión
- entregables con ajustes
- items vivos en bandeja
- proyectos con bloqueo o issues abiertas

Esto sí puede seguir siendo actualizado por script.

### 3. Sección `Entregables por revisar`

Tipo:

- linked view de `📬 Entregables Rick — Revisión`

Vista recomendada:

- tabla por defecto en móvil
- board opcional en desktop por `Estado revision`

Filtro:

- `Estado revision` es `Pendiente revision`
- o `Estado revision` es `Aprobado con ajustes`

Sort:

- `Fecha limite sugerida` ascendente
- luego `Fecha` descendente

Propiedades visibles:

- `Nombre`
- `Proyecto`
- `Tipo`
- `Estado revision`
- `Fecha limite sugerida`
- `Agente`
- `Siguiente accion`

Objetivo de lectura:

- saber qué revisar ahora
- saber qué vence antes

### 4. Sección `Proyectos que requieren atención`

Tipo:

- linked view de `📁 Proyectos — Umbral`

Vista recomendada:

- tabla compacta

Filtro recomendado:

- `Bloqueos` no vacío
- o `Issues abiertas` > `0`
- o `Siguiente acción` no vacía

Sort:

- `Último update` ascendente
- luego `Issues abiertas` descendente

Propiedades visibles:

- `Nombre`
- `Estado`
- `Issues abiertas`
- `Bloqueos`
- `Siguiente acción`
- `Último update`
- `Tareas`

Objetivo de lectura:

- detectar drift
- detectar proyectos sin cierre claro

### 5. Sección `Bandeja viva`

Tipo:

- linked view de `📬 Bandeja Puente`

Vista recomendada:

- board o tabla simple

Filtro:

- `Estado != Resuelto`

Sort:

- `Último movimiento` descendente

Propiedades visibles:

- `Ítem`
- `Estado`
- `Notas`
- `Último movimiento`

Objetivo:

- ver solo lo activo
- no ver histórico resuelto

### 6. Sección `Próximos vencimientos`

Tipo:

- segunda linked view de `📬 Entregables Rick — Revisión`

Vista recomendada:

- tabla muy compacta

Filtro:

- `Fecha limite sugerida` no vacía
- `Estado revision` no es `Archivado`
- `Estado revision` no es `Aprobado`

Sort:

- `Fecha limite sugerida` ascendente

Propiedades visibles:

- `Nombre`
- `Proyecto`
- `Fecha limite sugerida`
- `Estado revision`

Objetivo:

- leer vencimientos sin ruido

### 7. Sección `Bases operativas`

Tipo:

- links permanentes o child pages/databases ya existentes

Contenido:

- `📁 Proyectos — Umbral`
- `🗂 Tareas — Umbral Agent Stack`
- `📬 Entregables Rick — Revisión`
- `📬 Bandeja Puente`
- `Dashboard Rick`

Esto reemplaza texto explicativo largo.

## Qué debe desaparecer de OpenClaw

Eliminar:

- bullets tipo reporte
- listas narrativas de entregables/proyectos
- explicaciones largas sobre cómo leer el dashboard
- cualquier texto que replique manualmente lo que ya vive en una base

## Qué sí puede seguir automatizado

Automatizable por script:

- callout superior con timestamp
- tabla/resumen corto de 3-4 KPIs
- validación de que existan las vistas correctas
- alerta si alguna base queda sin items esperados

No automatizar:

- reconstrucción total de la página con bullets
- resúmenes largos
- “reportes” del dashboard

## Regla de mantenimiento para Rick y agentes

Los agentes no actualizan `OpenClaw` escribiendo contenido operativo manual.

Los agentes actualizan:

- proyectos
- tareas
- entregables
- bandeja

`OpenClaw` se actualiza solo de dos formas:

1. por las vistas enlazadas
2. por un script mínimo que refresca el resumen corto

## Relación con Dashboard Rick

### `OpenClaw`

Rol:

- priorización humana
- revisión
- aprobación
- navegación

### `Dashboard Rick`

Rol:

- observabilidad técnica
- workers
- redis
- cuotas
- errores
- ruido técnico

No deben competir por el mismo trabajo.

## Implementación recomendada por fases

### Fase 1 — manual en Notion

Configurar manualmente la shell de `OpenClaw` con:

- estructura fija
- vistas enlazadas
- filtros
- columnas visibles

Motivo:

- Notion UI resuelve mejor esto que la API para linked views/boards

### Fase 2 — ajuste de scripts

Cambiar:

- [scripts/openclaw_panel_vps.py](C:/GitHub/umbral-agent-stack-codex/scripts/openclaw_panel_vps.py)

para que:

- deje intacta la shell
- solo actualice el callout/KPI summary
- valide presencia de secciones clave

### Fase 3 — guardrails

Agregar reglas para que Rick:

- no vuelva a crear bullets de dashboard
- no use `OpenClaw` como página de reporte
- priorice siempre bases operativas

## Esquema visual final esperado

```text
OpenClaw
  [Callout corto: estado / timestamp / cómo usar]
  [Resumen operativo corto]
  Entregables por revisar
    [linked view]
  Proyectos que requieren atención
    [linked view]
  Bandeja viva
    [linked view]
  Próximos vencimientos
    [linked view]
  Bases operativas
    [links permanentes]
```

## Criterio de aceptación

La rediseño queda bien cuando:

- `OpenClaw` se puede leer en 10-15 segundos
- no hay bullets narrativos largos
- todo lo importante es clickable/navegable
- los datos se sienten vivos, no “copiados”
- Rick no necesita reescribir la página para mantenerla útil

## Siguiente paso exacto

El siguiente slice ya no es seguir diagnosticando.

Es este:

1. diseñar manualmente la shell `OpenClaw` en Notion
2. congelar su estructura
3. adaptar `openclaw_panel_vps.py` a modo `summary-only`
4. agregar validación de shell

Ese es el movimiento correcto para pasar de “reporte generado” a “dashboard usable”.
