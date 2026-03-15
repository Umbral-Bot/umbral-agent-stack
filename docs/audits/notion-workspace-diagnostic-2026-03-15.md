# Diagnostico integral de Notion y oportunidades de mejora (2026-03-15)

## Alcance

Barrido operativo y estructural de los elementos de Notion actualmente accesibles desde el stack:

- `OpenClaw`
- `Dashboard Rick`
- `📁 Proyectos — Umbral`
- `📒 Tareas — Umbral Agent Stack`
- `📬 Entregables Rick — Revision`
- `📬 Bandeja Puente`
- `🔄 Bitacora — Umbral Agent Stack`
- recursos historicos ligados a `Archivo historico — Umbral`

Tambien se reviso el repositorio y la VPS para detectar drift entre:

- configuracion de Notion
- runtime real
- skills y guardrails
- scripts de dashboard y trazabilidad
- salud real de la VM

## Cambios aplicados en esta iteracion

### 1. Dashboard Rick saneado

Se elimino del payload y del renderer la seccion historica `Seguimiento R16/R17`, que ya no reflejaba el estado operativo actual.

Archivos:

- `scripts/dashboard_report_vps.py`
- `worker/notion_client.py`
- `tests/test_dashboard.py`
- `docs/30-linear-notion-architecture.md`

Resultado visible:

- `Dashboard Rick` ya no muestra `Seguimiento R16/R17`
- la tabla de equipos ahora dice `Enrutamiento` en vez de `Plano`
- el valor mostrado es `Por tarea`, que si refleja el routing actual

### 2. Procedencia de tareas propagada hasta Notion

Se corrigio el camino de trazabilidad para que las tareas que pasan por enqueue, dispatcher y worker puedan conservar mejor su origen.

Archivos:

- `worker/models/__init__.py`
- `worker/app.py`
- `client/worker_client.py`
- `dispatcher/queue.py`
- `dispatcher/service.py`
- `worker/tasks/notion.py`
- `openclaw/extensions/umbral-worker/index.ts`
- `tests/test_enqueue_api.py`
- `tests/test_dispatcher.py`
- `tests/test_dispatcher_resilience.py`
- `tests/test_notion_tasks_registry.py`

Campos propagados:

- `source`
- `source_kind`
- `source_comment_id`
- `linear_issue_id`
- `project_name`
- `project_page_id`
- `deliverable_name`
- `deliverable_page_id`
- `notion_track`
- `trace_id`

Resultado:

- las tareas nuevas muestran mejor por que existen
- OpenClaw deja su procedencia explicita
- la separacion entre tareas project-scoped y ruido tecnico ya no depende tanto de inferencias fragiles

### 3. Dashboard separado entre senal y ruido tecnico

Se cambio el dashboard para separar:

- `Tareas recientes relevantes`
- `Ruido tecnico / sistema`

Regla aplicada:

- una tarea es relevante si trae `project_name`, `deliverable_name` o `notion_track`
- tambien si viene de `openclaw_gateway`, `linear_webhook`, `notion_poller` o `smart_reply`
- tareas tecnicas repetitivas como `windows.fs.*`, `ping` y varias `notion.*` de infraestructura se muestran aparte

Ademas se corrigio la logica del semaforo general:

- si la VPS esta bien pero la VM esta caida, el dashboard ya no puede quedar `Operativo`
- ahora queda `Degradado`, que es el estado correcto del stack

### 4. Vistas operativas nuevas o corregidas

En Notion quedaron disponibles estas vistas:

- `📒 Tareas — Umbral Agent Stack`
  - `Recientes ligadas`
  - `Sistema / automatizaciones abiertas`
  - `Activas / seguimiento`
  - `Sistema / historial`
- `📁 Proyectos — Umbral`
  - `Activos con bloqueos`
- `📬 Bandeja Puente`
  - `Pendientes`
  - `En curso`
  - `Resueltos / historial`
  - `Rick / abiertos`

Resultado real:

- `En curso` en `Bandeja Puente` muestra solo los dos items abiertos vigentes
- `Resueltos / historial` concentra el ruido periodico
- `Recientes ligadas` en `Tareas` ya deja ver trabajo ligado a proyecto/entregable sin enterrarlo bajo ruido del sistema

### 5. Estado real de la VM confirmado

Se verifico desde host y desde VPS:

- `tailscale status` reporta `pcrick` offline
- `http://100.109.16.40:8088/health` -> timeout
- `http://100.109.16.40:8089/health` -> timeout
- `http://127.0.0.1:8088/health` en la VPS -> `200`

Conclusiones:

- el dashboard no estaba exagerando
- la VM esta realmente fuera
- el problema ya no es de visualizacion sino de infraestructura

## Validacion

- `python -m pytest tests/test_dashboard.py tests/test_enqueue_api.py tests/test_dispatcher.py tests/test_dispatcher_resilience.py tests/test_notion_tasks_registry.py -q`
- resultado: `90 passed`
- `python -m pytest -q`
- resultado: `1077 passed, 4 skipped, 1 warning`
- `python scripts/validate_skills.py`
- resultado: `OK`
- despliegue en VPS:
  - `umbral-worker.service` reiniciado
  - `openclaw-gateway.service` reiniciado
  - dashboard regenerado en Notion

## Hallazgos principales

### Hallazgo 1. El dashboard mezclaba estado actual con tracking historico

Severidad: alta

Antes mostraba una seccion vieja (`R16/R17`, `900 passed`) que ya no servia para operar.

Estado:

- corregido en codigo
- corregido en produccion

### Hallazgo 2. El dashboard ya separa bien senal y ruido, pero el runtime sigue degradado

Severidad: alta

Estado visible final del dashboard:

- `Worker VPS`: OK
- `Worker VM (8088)`: Offline (ConnectTimeout)
- `Worker VM interactivo (8089)`: Offline (ConnectTimeout)
- `Redis`: conectado, con bloqueadas acumuladas
- `Ruido tecnico / sistema`: visible y separado
- semaforo global: `Degradado`

Interpretacion:

- la visualizacion ya no es el problema principal
- el problema ahora es la VM y algunos productores que siguen poblando tareas tecnicas

### Hallazgo 3. `📬 Bandeja Puente` era dificil de leer, pero ya quedo razonablemente util

Severidad: media

El problema original era mezcla de:

- muchas entradas periodicas tipo `Revision periodica ...`
- vistas con filtros poco fiables desde tooling

Estado actual:

- mejorado
- no perfecto
- suficientemente legible para operacion con vistas simples por estado

Limite detectado:

- el tooling de views de Notion sigue siendo inconsistente para representar y volver a leer filtros compuestos complejos

### Hallazgo 4. `📒 Tareas` sigue mostrando ruido historico y ruido tecnico abierto

Severidad: alta

Aunque ya existe mejor procedencia, siguen apareciendo tareas del sistema y del laboratorio:

- `windows.fs.list`
- `research.web`
- `llm.generate`
- fallos browser viejos

Conclusion:

- una parte del problema ya quedo corregida con propagacion de `source` y contexto
- el ruido historico sigue ahi
- varios productores viejos siguen dejando tareas tecnicas que conviene tratar como sistema, no como trabajo humano revisable

### Hallazgo 5. La busqueda global de Notion no sirve como herramienta principal de operacion

Severidad: media

La busqueda interna devuelve mucho ruido de:

- calendario
- correo
- inbox

Conclusion:

- para operar conviene dashboard + bases filtradas
- no busqueda semantica global del workspace

### Hallazgo 6. La estructura principal de Notion ya esta bastante sana

Severidad: positiva

Lo mas sano hoy es:

- `📁 Proyectos — Umbral`
- `📬 Entregables Rick — Revision`
- `📒 Tareas — Umbral Agent Stack`
- `OpenClaw` como hub
- `Archivo historico — Umbral` fuera del flujo activo

En otras palabras:

- el problema principal ya no es desorden estructural grueso
- es ruido operativo, visibilidad y disciplina de origen

## Oportunidades de mejora concretas

### A. Terminar de propagar procedencia desde productores viejos

Prioridad: alta

Estado: parcialmente resuelto

Ya persiste mejor:

- `source`
- `source_kind`
- `project_name`
- `deliverable_name`
- `notion_track`
- `trace_id`

Pendiente:

- que mas productores viejos realmente llenen ese contexto

### B. Reducir el ruido historico de `📒 Tareas`

Prioridad: alta

Estado: pendiente

Conviene decidir si:

- las tareas tecnicas historicas se archivan
- o se dejan solo en vistas de sistema

Hoy el dashboard ya no las mezcla con trabajo relevante, pero la base aun conserva bastante ruido viejo.

### C. Recuperar la VM

Prioridad: alta

Mientras `pcrick` siga offline:

- el dashboard seguira degradado
- el routing que necesita VM seguira bloqueando tareas
- `Tareas` seguira llenandose con bloqueos legitimos de laboratorio

### D. Afinar `📬 Bandeja Puente` solo si se quiere una UX mas fina

Prioridad: media

Ya es usable con vistas simples.

Lo pendiente seria solo:

- filtros mas ricos
- o mover historial periodico si se quiere una bandeja todavia mas limpia

### E. Agregar columnas visibles de procedencia en `📒 Tareas`

Prioridad: media

Hoy la procedencia ya existe en el cuerpo de las subpaginas.

Si se quiere mayor legibilidad directa en tabla, convendria agregar columnas tipo:

- `Source`
- `Trace ID`

No es obligatorio para operar, pero mejoraria debugging.

## Recomendacion de siguiente slice

Si se quiere un avance real y no cosmetico, el siguiente slice deberia ser:

1. recuperar la VM `pcrick`
2. decidir que productores tecnicos deben seguir poblando `📒 Tareas`
3. archivar o aislar mejor el ruido historico viejo de `📒 Tareas`
4. agregar columnas de procedencia si se quiere debugging mas directo

## Veredicto final

Notion ya no esta desordenado por falta de estructura.

Los problemas reales hoy pasan por:

- VM fuera
- ruido historico de tareas
- algunos productores tecnicos sin suficiente disciplina de origen

La parte positiva es que el flujo central ya esta bastante sano:

`Proyecto -> Tarea -> Entregable -> Revision`

El mayor valor a partir de aqui no es crear mas bases, sino mejorar:

- procedencia
- limpieza historica
- lectura operativa
- y salud real de la VM
