Ejecutado por: codex
Fecha: 2026-03-11

# Auditoría de uso real y drift operativo

## Objetivo

Revisar el estado real de las piezas activas del stack y detectar:

- proyectos o registros sin uso consistente
- páginas o bases de Notion parcialmente mantenidas
- procesos activos solo en documentación pero no en operación
- workflows de n8n creados pero no usados
- drift entre Linear, Notion y carpeta compartida

## Alcance

- VPS: gateway, worker, crons, n8n
- VM: carpetas compartidas de proyectos
- Notion: registro maestro `📁 Proyectos — Umbral` y base `🗂 Tareas — Umbral Agent Stack`
- Linear: proyectos e issues asociadas
- Rick: mini auditoría correctiva ejecutada desde `main`

## Verificaciones realizadas

### VPS

- `openclaw-gateway.service`: activo
- `umbral-worker.service`: activo
- `n8n.service`: activo
- `openclaw-dispatcher.service`: inactivo
- `openclaw.service`: inactivo

### Crons OpenClaw

Todos los jobs visibles están habilitados, con `delivery.mode = none` y `lastRunStatus = ok`.

### n8n

Inventario real:

- activos: 1
- creados pero no usados: 6

Activo real:

- `Correo de prueba diario 08:00`

Creados pero no usados:

- `SIM Diario - Embudo`
- `Reporte Ejecutivo Diario`
- `Editorial Shortlist - Sistema Editorial Automatizado Umbral`
- `Editorial Gate de Aprobación - Sistema Editorial Automatizado Umbral`
- `Editorial Multicanal Prep - Sistema Editorial Automatizado Umbral`
- `Laboral Gate Humano - Shortlist y Preparación`

Conclusión: n8n existe como capacidad, pero hoy la operación real es mínima.

### Registro maestro de proyectos en Notion

Base auditada:

- `📁 Proyectos — Umbral`
- `https://www.notion.so/d4098fa43280434a8ae4b11cab81246f`

Estado al inicio de la auditoría:

- faltaba `Proyecto Granola`
- `Sistema Automatizado de Búsqueda y Postulación Laboral` no tenía `Linear Project`
- `Sistema Automatizado de Búsqueda y Postulación Laboral` no tenía `Issues abiertas`
- `Sistema Editorial Automatizado Umbral` no tenía `Issues abiertas`

Acción correctiva:

- se instruyó a Rick a corregir el drift
- se releyó la base directamente por `notion.read_database`

Estado final confirmado:

- `Proyecto Granola` ya figura en Notion
- `Sistema Automatizado de Búsqueda y Postulación Laboral` ya tiene `Linear Project` e `Issues abiertas = 1`
- `Sistema Editorial Automatizado Umbral` ya tiene `Issues abiertas = 5`
- `Proyecto Granola` ya tiene `Issues abiertas = 1`

## Hallazgos por frente

### Proyecto Embudo Ventas

- estado: activo
- trazabilidad: buena
- carpeta compartida: viva y con entregables
- issues en Linear: muchas, pero la mayoría siguen en `Backlog`

### Sistema Editorial Automatizado Umbral

- estado: activo en registro, pero poco vivo operativamente
- carpeta compartida: estable, sin movimiento reciente fuerte
- n8n: todos sus workflows siguen creados-manuales y apagados
- issues abiertas: 5

Diagnóstico:

- proyecto documentado y modelado
- poca operación real sostenida
- principal proceso estancado del stack

### Proyecto Granola

- estado: activo en Linear y Notion
- carpeta compartida: casi vacía
- evidencia reciente: muy poca

Diagnóstico:

- pipeline base existe
- gobernanza ya corregida
- sigue faltando evidencia operativa reciente en entregables

### Sistema Automatizado de Búsqueda y Postulación Laboral

- estado: activo
- ruta compartida: corregida
- `Linear Project`: corregido
- workflow `n8n`: creado pero no usado

Diagnóstico:

- mejor gobernado que al inicio de la auditoría
- todavía no pasó a loop vivo recurrente

### Auditoría Mejora Continua — Umbral Agent Stack

- estado: activo
- carpeta `informes`: viva y con múltiples reauditorías
- carpeta `entregables`: sin uso real (`desktop.ini` únicamente)

Diagnóstico:

- es el frente más activo en auditoría documental
- pero aún no produce suficientes entregables operativos reutilizables

## Páginas y procesos sin uso o con uso débil

### Sin uso o bajo uso real

- `Proyecto-Auditoria-Mejora-Continua\\entregables`
- workflows `n8n` editoriales
- workflow `n8n` laboral
- carpeta compartida de `Proyecto Granola`

### Parcialmente vivos

- `Sistema Editorial Automatizado Umbral`
- `Sistema Automatizado de Búsqueda y Postulación Laboral`

### Bien vivos

- `Proyecto Embudo Ventas`
- `Auditoría Mejora Continua — Umbral Agent Stack`

## Drift detectado

1. Linear se usa, pero muchos frentes siguen semánticamente en `Backlog` aunque ya tengan trabajo real.
2. Notion registro maestro estaba desalineado hasta esta auditoría.
3. n8n está sobrerrepresentado como capacidad frente a su uso real.
4. Mejora continua está auditando más infraestructura que cierres de loop completos.
5. Algunos proyectos tienen documentación suficiente, pero poca evidencia fresca en carpeta compartida.

## Qué corrigió Rick durante esta iteración

- completó `Proyecto Granola` en el registro maestro
- completó `Linear Project` e `Issues abiertas` en el proyecto laboral
- completó `Issues abiertas` en el proyecto editorial
- dejó nota de gobernanza y uso real de n8n en:
  - `G:\Mi unidad\Rick-David\Proyecto-Auditoria-Mejora-Continua\informes\nota-gobernanza-proyectos-y-n8n-2026-03-11.md`

## Conclusión

El sistema sí tiene seguimiento y mejora continua operando, pero todavía con drift claro entre:

- lo que existe como capacidad
- lo que está gobernado correctamente
- y lo que se usa de verdad de forma sostenida

La corrección de esta iteración mejoró la gobernanza del registro maestro, pero el principal cuello de botella ya no es infraestructura:

- es convertir proyectos y workflows creados en loops vivos con evidencia reciente y estados consistentes.

## Siguiente corte útil

1. Sacar al menos un workflow de n8n de `creado-manual` a uso real.
2. Forzar estados más honestos en Linear para proyectos con trabajo ya ejecutado.
3. Exigir evidencia reciente en carpeta compartida para `Proyecto Granola`.
4. Convertir `Proyecto-Auditoria-Mejora-Continua\\entregables` en una carpeta con entregables reutilizables, no solo informes.
