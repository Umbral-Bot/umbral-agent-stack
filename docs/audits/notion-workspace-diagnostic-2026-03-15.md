# Diagnostico integral de Notion y oportunidades de mejora (2026-03-15)

## Alcance

Barrido operativo y estructural de los elementos de Notion actualmente accesibles desde el stack:

- `OpenClaw`
- `Dashboard Rick`
- `📁 Proyectos — Umbral`
- `🗂 Tareas — Umbral Agent Stack`
- `📬 Entregables Rick — Revision`
- `📬 Bandeja Puente`
- `🔄 Bitacora — Umbral Agent Stack`
- recursos historicos ligados a `Archivo historico — Umbral`

Tambien se reviso el repositorio y la VPS para detectar drift entre:

- configuracion de Notion
- runtime real
- skills/guardrails
- scripts de dashboard y trazabilidad

## Cambios aplicados en esta iteracion

### 1. Dashboard Rick saneado

Se elimino del payload y del renderer la seccion historica `Seguimiento R16/R17`, que ya no reflejaba el estado operativo actual.

Archivos:

- `scripts/dashboard_report_vps.py`
- `worker/notion_client.py`
- `tests/test_dashboard.py`
- `docs/30-linear-notion-architecture.md`

Validacion:

- `python -m pytest tests/test_dashboard.py tests/test_notion_project_registry.py tests/test_notion_deliverables_registry.py tests/test_notion_tasks_registry.py -q`
- resultado: `30 passed`
- `python scripts/validate_skills.py`
- resultado: `OK`

Despliegue:

- `worker/notion_client.py` y `scripts/dashboard_report_vps.py` sincronizados a la VPS
- `umbral-worker.service` reiniciado
- dashboard regenerado en Notion

Resultado visible:

- `Dashboard Rick` ya no muestra `Seguimiento R16/R17`
- la tabla de equipos ahora dice `Enrutamiento` en vez de `Plano`
- el valor mostrado es `Por tarea`, que si refleja el routing actual

### 2. Vistas operativas nuevas o corregidas

En Notion quedaron disponibles estas vistas:

- `🗂 Tareas — Umbral Agent Stack`
  - `Recientes ligadas`
  - `Sistema / automatizaciones abiertas`
  - `Sistema / historial`
- `📁 Proyectos — Umbral`
  - `Activos con bloqueos`

Estas vistas mejoran lectura, aunque no corrigen por si solas el origen del ruido.

## Hallazgos principales

### Hallazgo 1. Dashboard Rick estaba mezclando estado actual con tracking historico

Severidad: alta

El dashboard mostraba una seccion cerrada hace tiempo (`R16/R17`, `900 passed`) que hacia parecer vigente un release tracking ya obsoleto. Esto degradaba la lectura gerencial y desviaba atencion de problemas actuales.

Estado:

- corregido en codigo
- corregido en produccion

### Hallazgo 2. El dashboard sigue mostrando ruido operativo real

Severidad: alta

Tras regenerar el dashboard, lo que aparece hoy como problemas reales es:

- `Worker VM (8088)` offline por timeout
- `Worker VM interactivo (8089)` offline por timeout
- `Redis` con `25` tareas bloqueadas
- `Tareas recientes` dominadas por `windows.fs.list`
- `Ultimo error`: `llm.generate` devolviendo `500` contra `127.0.0.1:8088`

Interpretacion:

- el dashboard ya esta diciendo la verdad
- el problema ahora es el runtime, no la visualizacion

### Hallazgo 3. `📬 Bandeja Puente` sigue siendo dificil de leer

Severidad: media

La base esta contaminada por muchas entradas periodicas tipo `Revision periodica ...`, casi todas resueltas. Se intentaron crear vistas separadas (`Abiertos / accionables`, `Resueltos / historial`), pero la configuracion DSL disponible no termino de persistir correctamente los filtros sobre la propiedad `Estado`.

Implicacion:

- el problema no es solo de contenido
- hay una limitacion practica del tooling actual para configurar esa base con la precision deseada desde automatizacion

Recomendacion:

- ajustar esas vistas manualmente en Notion UI o ampliar el tooling para escribir filtros de views con mas control

### Hallazgo 4. `🗂 Tareas` sigue recibiendo ruido de automatizaciones/sistema

Severidad: alta

Aunque ya existe el guardrail para poblar Notion solo con tareas project-scoped o `notion_track=true`, siguen apareciendo tareas recientes del sistema y del lab:

- `windows.fs.list`
- `research.web`
- `llm.generate`
- fallos browser viejos

Diagnostico cruzado:

- en la VPS, varios registros Redis recientes no tienen `source`, `callback_url`, `linear_issue_id` ni `envelope`
- por lo tanto hoy falta trazabilidad de origen en el propio runtime

Conclusion:

- `Tareas` no esta recibiendo ruido por una sola causa obvia en el repo
- parte del ruido viene de productores o envelopes que no dejan suficiente procedencia

### Hallazgo 5. La busqueda global de Notion no sirve como herramienta principal de operacion

Severidad: media

La busqueda interna devuelve mucho ruido de:

- calendario
- correo
- inbox

antes que estructuras operativas del stack.

Conclusion:

- para operacion cotidiana conviene navegar por dashboard + bases filtradas
- no por busqueda semantica global del workspace

### Hallazgo 6. La estructura principal de Notion esta mejor que hace una semana

Severidad: positiva

Lo mas sano hoy es:

- `📁 Proyectos — Umbral`
- `📬 Entregables Rick — Revision`
- `OpenClaw` como hub
- `Archivo historico — Umbral` fuera del flujo activo

En otras palabras:

- el problema principal ya no es desorden estructural grueso
- es ruido operativo, visibilidad y disciplina de origen

## Oportunidades de mejora concretas

### A. Persistir procedencia de tareas en Redis y en Notion

Prioridad: alta

Hoy faltan campos fiables de procedencia para muchas tareas. Conviene persistir siempre, cuando exista:

- `source`
- `source_kind`
- `envelope_id`
- `project_name`
- `deliverable_name`
- `notion_track`

Beneficio:

- explicar por que aparecen tareas en `Tareas`
- filtrar mejor el dashboard
- depurar automatizaciones ruidosas

### B. Reducir ruido del dashboard de tareas recientes

Prioridad: alta

Opciones razonables:

- excluir tareas tecnicas repetitivas de `recent_tasks` si no son project-scoped
- o separar `Recentes operativas` de `Recentes sistema`

No se aplico automaticamente en esta iteracion para no ocultar incidentes reales sin una politica clara.

### C. Corregir la salud real de la VM

Prioridad: alta

El dashboard muestra timeout tanto en `8088` como en `8089`. Mientras eso no se corrija:

- el dashboard seguira en rojo parcial
- el routing con necesidad de VM seguira degradado

### D. Limpiar `📬 Bandeja Puente`

Prioridad: media

Conviene:

- separar de verdad lo accionable de lo historico
- reducir la periodicidad si esos check-ins no agregan senal
- o mover el historial repetitivo a otra vista/base

### E. Convertir `Dashboard Rick` en dashboard de decisiones, no de exhaustividad

Prioridad: media

Deberia quedarse con:

- estado general
- workers y Redis
- cuotas
- equipos
- tareas recientes relevantes
- alertas activas

Y mover el resto a vistas enlazadas o bases filtradas.

## Recomendacion de siguiente slice

Si se quiere una mejora estructural de verdad, el siguiente slice deberia ser:

1. persistencia de `source` y `envelope` en tareas
2. politica explicita de que entra o no entra a `🗂 Tareas`
3. separar `Dashboard Rick` en:
   - `tareas recientes relevantes`
   - `ruido tecnico / sistema`
4. arreglo real del estado de la VM
5. ajuste manual o tooling mejorado para vistas de `📬 Bandeja Puente`

## Veredicto final

Notion hoy ya no esta desordenado por falta de estructura.

Los problemas reales pasan por:

- ruido de runtime
- falta de procedencia de tareas
- dashboard con demasiada mezcla entre senal y ruido
- algunas vistas que el tooling actual no logra dejar finas del todo

La parte positiva es que el flujo central ya esta bastante sano:

`Proyecto -> Tarea -> Entregable -> Revision`

El mayor valor a partir de aqui no es crear mas bases, sino mejorar:

- procedencia
- filtros
- lectura operativa
- y salud real de los workers
