# Diagnóstico consultivo — Notion operativo y dashboard

Fecha: 2026-03-16
Autor: Codex

## Objetivo

Revisar el estado real de la capa Notion del stack y determinar:

- qué está funcionando bien,
- qué está aportando poco valor,
- qué está estructuralmente mal diseñado,
- y qué conviene reestructurar sin romper lo que ya sirve.

## Método

Se cruzó información desde:

- repo local (`scripts/dashboard_report_vps.py`, `worker/notion_client.py`, `worker/tasks/notion.py`, `dispatcher/service.py`),
- configuración real de la VPS (`~/.config/openclaw/env`),
- API real de Notion usando `NOTION_API_KEY`,
- contenido actual de:
  - `OpenClaw`,
  - `Dashboard Rick`,
  - `📁 Proyectos — Umbral`,
  - `🗂 Tareas — Umbral Agent Stack`,
  - `📬 Entregables Rick — Revisión`,
  - `📬 Bandeja Puente`.

## Hallazgos principales

### 1. El problema principal no es "Notion roto"; es arquitectura de información mezclada

Hoy conviven tres capas con lógicas distintas:

- dashboard técnico del stack,
- panel operativo humano,
- histórico operativo.

Esas tres cosas no están separadas con suficiente claridad.

Resultado:

- `Dashboard Rick` parece incompleto para operación humana,
- `OpenClaw` muestra instrucciones y señales viejas junto con recursos vigentes,
- `Bandeja Puente` mezcla inbox vivo con bitácora periódica resuelta,
- `Tareas` conserva demasiado ruido histórico del runtime.

### 2. `Dashboard Rick` funciona técnicamente, pero no como dashboard de operación humana

El generador actual (`scripts/dashboard_report_vps.py`) saca métricas desde:

- Redis,
- salud de workers,
- cuotas,
- equipos,
- tareas recientes,
- error reciente.

Eso sirve para observabilidad técnica.

Pero no muestra bien lo que David necesita decidir en Notion:

- entregables pendientes de revisión,
- proyectos con drift o bloqueo,
- items realmente vivos en `Bandeja Puente`,
- próximos vencimientos,
- relación entre proyecto, tarea y entregable.

Conclusión:

`Dashboard Rick` hoy es más bien un **runtime dashboard**, no un **panel operativo de decisión**.

### 3. `OpenClaw` contiene una capa estática vieja que ya no representa el estado actual

El primer bloque visible de `OpenClaw` sigue diciendo:

- "Estado: Operativo con stack estable (Anthropic + OpenAI) · Última actualización: 2026-03-02"

Eso hoy genera ruido porque:

- es estático,
- quedó viejo,
- y compite visualmente con `Dashboard Rick`, que sí se actualiza.

Además, `OpenClaw` mezcla:

- instrucciones de uso,
- recursos históricos,
- bases vivas,
- referencias.

La página sigue siendo útil, pero no está ordenada como panel operativo moderno.

### 4. `🗂 Tareas — Umbral Agent Stack` está mejor que antes, pero sigue semánticamente contaminada

Estado real observado:

- total filas: `673`
- `632 done`
- `22 failed`
- `18 blocked`
- `670` sin proyecto
- `670` sin entregable

Esto confirma que la base sigue cargando herencia histórica de telemetría/runtimes.

Lo positivo:

- las tareas nuevas y buenas sí quedaron bien formadas,
- con nombre humano,
- contenido útil,
- icono correcto,
- y enlaces a proyecto/entregable.

Lo negativo:

- la base sigue dominada por ruido histórico,
- y por eso como herramienta de lectura humana aporta poco.

### 5. `📬 Entregables Rick — Revisión` es la base más sana del sistema actual

Estado real observado:

- total filas: `21`
- `2 Pendiente revisión`
- `9 Aprobado`
- `1 Aprobado con ajustes`
- `9 Archivado`

La base ya tiene valor real.

Problemas restantes:

- `6` entregables todavía sin proyecto,
- `18` sin tarea origen,
- algunos textos vienen con problemas de encoding histórico,
- el backfill dejó piezas correctas, pero no completamente normalizadas.

Conclusión:

esta base sí merece seguir siendo el eje humano de revisión.

### 6. `📁 Proyectos — Umbral` está bien como registro canónico, pero hoy está subalimentado

Estado real observado:

- `8` proyectos
- todos en `Activo`
- `7/8` sin tareas relacionadas visibles

El problema no es que la base esté mal diseñada.

El problema es que:

- no recibe suficientes relaciones útiles desde `Tareas`,
- no tiene relación explícita a entregables,
- y por eso no refleja bien la vida operativa de cada proyecto.

Hoy funciona más como ficha maestra de estado que como centro de navegación.

### 7. `📬 Bandeja Puente` perdió foco operativo

Estado real observado:

- total filas: `202`
- `200 Resuelto`
- `2 En curso`

La base contiene demasiadas entradas periódicas tipo:

- `Revisión periódica 2026-03-10 01:00`
- `Revisión periódica 2026-03-10 02:00`
- etc.

Eso tiene dos problemas:

1. el inbox vivo queda sepultado,
2. la base pasa a funcionar como log horario, no como bandeja de coordinación.

Conclusión:

`Bandeja Puente` hoy no está mal por schema; está mal por patrón de uso.

## Qué sí está funcionando bien

- relación básica `Proyecto -> Tarea -> Entregable` ya existe y fue validada,
- iconos heredados por proyecto/entregable/tarea ya funcionan,
- subpáginas de proyectos, tareas y entregables ya no quedan vacías,
- `Entregables` ya cumple rol de gate humano,
- `Dashboard Rick` ya refleja bien salud del stack y workers,
- `OpenClaw` ya no está contaminado por páginas sueltas del legacy.

## Causas raíz

### A. El dashboard se construyó desde telemetría, no desde decisiones humanas

El script actual no consulta las bases operativas de Notion.

Por eso muestra:

- salud de infraestructura,
- cuotas,
- tareas recientes,

pero no muestra:

- pendientes de revisión,
- bloqueos de proyecto,
- items vivos en bandeja,
- próximos vencimientos.

### B. `Bandeja Puente` se usa como log de supervisión, no como inbox

La automatización periódica genera demasiadas entradas resueltas.

Eso destruye la capacidad de lectura rápida.

### C. `Tareas` absorbe demasiado historial técnico para una base pensada para humanos

Aunque el contrato nuevo ya evita parte del ruido, el histórico viejo sigue dominando la base.

### D. La página `OpenClaw` sigue cargando una capa estática vieja

Eso confunde, porque el usuario ve primero una narrativa desactualizada antes que el estado operativo real.

## Recomendación de arquitectura

### Mantener

- `📁 Proyectos — Umbral`
- `📬 Entregables Rick — Revisión`
- `📬 Bandeja Puente`
- `Dashboard Rick`
- `OpenClaw`

### Pero redefinir roles

#### 1. `Dashboard Rick` -> Estado del stack

Debe quedar explícitamente como dashboard técnico/operativo del sistema:

- workers,
- redis,
- cuotas,
- errores,
- tareas recientes,
- ruido técnico.

No debería intentar ser también el panel de decisiones humanas.

#### 2. `OpenClaw` -> Panel operativo humano

Debe ser la página principal que David lee.

Debería mostrar:

- un resumen corto del estado del stack,
- entregables pendientes de revisión,
- proyectos con bloqueo o drift,
- items vivos de `Bandeja Puente`,
- enlaces a las 3 bases principales.

Y debería sacar o relegar:

- callout estático viejo,
- instrucciones desactualizadas,
- referencias históricas que no sean de uso frecuente.

#### 3. `Bandeja Puente` -> Inbox vivo

Debe contener solo:

- cosas pendientes,
- cosas activas,
- comunicación viva entre actores,
- escalaciones o handoffs.

No debería llenarse con una fila nueva por cada revisión horaria sin novedades.

Lo correcto sería:

- usar una sola fila o heartbeat que se actualiza,
- o archivar automáticamente revisiones periódicas resueltas más antiguas.

#### 4. `Tareas` -> Tareas significativas

Debe reservarse para:

- tareas ligadas a proyecto,
- tareas ligadas a entregable,
- tareas explícitamente marcadas para seguimiento humano.

No debería ser el histórico completo de telemetría del dispatcher.

## Propuesta concreta de reestructuración

### Fase 1 — Alta prioridad

1. Reconvertir `OpenClaw` en panel de lectura principal.
2. Reemplazar el callout viejo por:
   - link/síntesis del estado de `Dashboard Rick`,
   - entregables pendientes,
   - bandeja viva,
   - proyectos con bloqueo.
3. Mantener `Dashboard Rick` como dashboard técnico separado.

### Fase 2 — Alta prioridad

4. Limpiar `Bandeja Puente`:
   - archivar o mover revisiones periódicas resueltas,
   - dejar solo items `En curso` y últimos `Resuelto` relevantes,
   - cambiar el patrón de escritura del poller para no crear una fila nueva cada vez que no pasó nada.

### Fase 3 — Media prioridad

5. Archivar/ocultar en `Tareas` el histórico técnico no ligado a proyecto.
6. Dejar una vista principal que muestre solo tareas:
   - con proyecto,
   - o con entregable,
   - o con `notion_track=true`.

### Fase 4 — Media prioridad

7. Normalizar `Entregables`:
   - asignar proyecto a los 6 huérfanos,
   - completar `Tareas origen` donde sea posible,
   - corregir encoding histórico en nombres/resúmenes antiguos.

### Fase 5 — Media prioridad

8. En `Proyectos`, agregar mejor navegación:
   - relación explícita o rollup a entregables,
   - contador de entregables pendientes,
   - último entregable relevante,
   - próxima fecha límite sugerida.

## Qué NO recomiendo

- no crear más bases nuevas ahora,
- no rehacer todo desde cero,
- no fusionar `Dashboard Rick` con `OpenClaw`,
- no seguir usando `Bandeja Puente` como log horario,
- no usar `Tareas` como histórico total del runtime.

## Priorización ejecutiva

Si hubiera que elegir solo tres acciones:

1. Rehacer `OpenClaw` como panel humano real.
2. Limpiar y redefinir `Bandeja Puente` como inbox vivo.
3. Podar/ocultar el ruido histórico de `Tareas`.

## Veredicto

La estructura base actual **es recuperable**.

No conviene tirar todo ni crear otra arquitectura paralela.

Pero sí conviene una reestructuración fuerte en tres puntos:

- separar mejor **panel humano** vs **dashboard técnico**,
- dejar `Bandeja Puente` como inbox y no como log,
- y convertir `Tareas` en una base legible para humanos, no en reflejo casi completo de Redis.

Con esos cambios, Notion pasaría de "funciona pero confunde" a "sirve para operar y decidir".
