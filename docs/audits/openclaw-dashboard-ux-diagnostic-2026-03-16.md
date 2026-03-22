# Diagnóstico UX/arquitectura — OpenClaw como dashboard operativo

Fecha: 2026-03-16
Autor: Codex

## Problema observado

La página `OpenClaw` hoy muestra secciones como:

- `Entregables pendientes de revision`
- `Proyectos con bloqueo o drift`
- `Bandeja viva`
- `Proximos vencimientos`

pero lo hace como **texto generado**, no como un dashboard/board real de Notion.

Eso produce tres problemas de UX:

1. se siente como reporte estático, no como panel navegable,
2. pierde escaneabilidad visual,
3. queda débilmente amarrado al mantenimiento futuro porque depende de bullets regenerados, no de vistas vivas.

## Diagnóstico técnico

### 1. El script actual genera bloques narrativos, no superficies vivas

El renderer actual está en:

- [scripts/openclaw_panel_vps.py](C:/GitHub/umbral-agent-stack-codex/scripts/openclaw_panel_vps.py)

Hoy construye el panel con:

- `heading_2`
- `heading_3`
- `callout`
- `paragraph`
- `bulleted_list_item`

O sea: aunque el contenido venga de bases reales, el resultado final es un reporte de texto.

### 2. El cliente Notion del repo no tiene soporte para crear vistas enlazadas

En el stack actual sí existe soporte para:

- leer bases
- crear páginas en bases
- actualizar propiedades
- renderizar tablas simples dentro de páginas

Pero no existe un camino robusto para crear/configurar por API:

- linked database views
- board views
- filtros persistentes complejos por vista
- grouping visual de vistas de board

Se ve además en el propio cliente que `child_database`/`child_page` no son tratadas como bloques escribibles.

Conclusión: hoy el sistema sí puede poblar las bases correctas, pero **no está preparado para fabricar un dashboard estilo Notion UI por API**.

### 3. La arquitectura correcta ya existe en las bases, pero no en la presentación

La parte de datos va razonablemente bien:

- `📁 Proyectos — Umbral`
- `🗂 Tareas — Umbral Agent Stack`
- `📬 Entregables Rick — Revisión`
- `📬 Bandeja Puente`

El problema no está principalmente en los datos, sino en **cómo se proyectan en OpenClaw**.

## Conclusión senior

No conviene seguir empujando `OpenClaw` como si fuera una página-report generada enteramente por API.

Eso siempre va a verse “suelto”.

La solución correcta es cambiar el enfoque:

- `OpenClaw` no debe ser una página reescrita en texto.
- `OpenClaw` debe ser una **shell estable de dashboard**, con:
  - una introducción breve,
  - una leyenda,
  - y sobre todo **vistas enlazadas de las bases operativas**.

## Qué mantener

Mantendría:

- `Dashboard Rick` como dashboard técnico
- `OpenClaw` como hub humano
- `Entregables`, `Proyectos`, `Tareas`, `Bandeja Puente` como fuentes de verdad

No botaría esa estructura.

## Qué cambiar

### Opción recomendada: `OpenClaw` como shell fija + vistas enlazadas

Diseño recomendado:

1. Encabezado corto
   - qué es `OpenClaw`
   - cómo leerlo

2. `Entregables por revisar`
   - linked view de `📬 Entregables Rick — Revisión`
   - vista tipo tabla o board
   - filtro: `Estado revision` en `Pendiente revision`, `Aprobado con ajustes`

3. `Proyectos que requieren atención`
   - linked view de `📁 Proyectos — Umbral`
   - filtro por:
     - bloqueos no vacíos
     - issues abiertas > 0
     - o siguiente acción no vacía

4. `Bandeja viva`
   - linked view de `📬 Bandeja Puente`
   - filtro: `Estado != Resuelto`

5. `Próximos vencimientos`
   - linked view de `📬 Entregables`
   - orden por `Fecha limite sugerida`

6. `Indicadores`
   - un callout o tabla resumen muy corta
   - no narrativa larga

### Resultado esperado

`OpenClaw` pasaría de:

- reporte textual

a:

- dashboard navegable
- mantenible
- legible en móvil
- y naturalmente actualizado desde las bases

## Restricción importante

Esto probablemente requiere **configuración manual inicial dentro de Notion**.

La razón:

- el stack actual no tiene una forma confiable de crear/configurar esas vistas enlazadas por API
- y aunque se pudiera crear parte, el acabado de filtros/grouping/board en Notion UI sigue siendo mucho mejor manualmente

## Diseño operativo recomendado

### Qué actualiza el sistema

Los agentes/Rick deben seguir actualizando:

- `Proyectos`
- `Tareas`
- `Entregables`
- `Bandeja Puente`

### Qué NO deben hacer

No deberían “escribir el dashboard” como texto cada vez.

### Qué sí puede seguir automatizado

Se puede mantener un script para:

- refrescar un callout superior con timestamp/estado
- actualizar una tabla resumen muy corta
- verificar consistencia

Pero no para rehacer el panel entero en bullets.

## Siguiente movimiento recomendado

### Fase 1

Congelar `OpenClaw` como shell fija:

- parar la reescritura completa por `scripts/openclaw_panel_vps.py`
- dejar solo un bloque superior vivo si hace falta

### Fase 2

Diseñar manualmente la página en Notion con vistas enlazadas:

- `Entregables por revisar`
- `Proyectos que requieren atención`
- `Bandeja viva`
- `Próximos vencimientos`

### Fase 3

Ajustar el stack para que:

- Rick mantenga las bases
- no vuelva a generar bullets de dashboard
- y un agente pueda validar periódicamente que las vistas siguen útiles

## Veredicto

Tu observación es correcta.

`OpenClaw` hoy no está funcionando con la semántica visual de dashboard; está funcionando como reporte textual decorado.

La mejora correcta no es “otro formato de bullets”.

La mejora correcta es:

- pasar a un `dashboard-shell` de Notion basado en vistas enlazadas de bases reales,
- y dejar la automatización enfocada en mantener los datos y un resumen corto, no en redactar el panel.
