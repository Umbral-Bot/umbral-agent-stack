# Auditoria Detallada Live Test Rick 2026-03-09

> **Fecha:** 2026-03-09
> **Ejecutado por:** codex
> **Entorno:** Telegram -> OpenClaw gateway -> sesion main + Worker VPS/VM

## Resumen del test

- Tipo de test: auditoria manual end-to-end de comportamiento
- Agente bajo prueba: `main` (`Rick`)
- Canal bajo prueba: Telegram -> OpenClaw gateway -> sesion `main`
- Foco: verificar si Rick pasa de entender el contexto a ejecutar trabajo real en un proyecto
- Documentos relacionados:
  - `docs/audits/rick-live-test-2026-03-08.md`
  - `docs/audits/rick-live-test-2026-03-09-followup.md`

## Objetivo

Validar que, despues de los fixes de infraestructura ya aplicados, Rick sea capaz de:

1. entender un prompt de proyecto real,
2. usar las tools correctas,
3. arrancar el trabajo sin loops de confirmacion evitables,
4. dejar trazabilidad real en Linear, Notion o filesystem,
5. delegar cuando tenga sentido.

La pregunta central de este test es simple:

- si la infra ya funciona, Rick efectivamente trabaja o solo suena como si estuviera trabajando.

## Entorno

- Repo: `c:\GitHub\umbral-agent-stack-codex`
- VPS:
  - config OpenClaw: `/home/rick/.openclaw/openclaw.json`
  - sesion principal inspeccionada: `/home/rick/.openclaw/agents/main/sessions/3653842f-a0b7-4e99-937a-1cea5d5e5be0.jsonl`
  - ops log del Worker: `~/.config/umbral/ops_log.jsonl`
- VM Worker:
  - endpoint: `http://100.109.16.40:8088/run`
- Rutas relevantes en la VM:
  - proyecto: `G:\Mi unidad\Rick-David\Proyecto-Embudo-Ventas`
  - docs de perfil: `G:\Mi unidad\Rick-David\Perfil de David Moreira\Creado por David`

## Precondiciones

Antes de este test ya estaba confirmado que:

- `main` ya no dependia de `nodes` para acceder a la VM
- `umbral_notion_read_page` funcionaba desde `main`
- `umbral_windows_fs_list` funcionaba por Dispatcher -> VM
- la carpeta del proyecto estaba vacia a proposito
- el usuario habia dicho explicitamente que el proyecto de Linear `Proyecto Embudo Ventas` debia ser el contexto operativo oficial

## Prompt bajo prueba

El usuario envio por Telegram un prompt de trabajo real indicando:

- la carpeta del proyecto esta en `Rick-David\Proyecto-Embudo-Ventas`
- la carpeta esta vacia a proposito porque lo anterior estaba mal
- Rick debe estudiar:
  - los docs locales en `Rick-David\Perfil de David Moreira\Creado por David`
  - la pagina publica de perfil en Notion
- Rick debe seguir estos 6 pasos:
  1. analisis del perfil
  2. estrategia de recoleccion de data de internet
  3. estudio de mercado
  4. embudo y captura de leads
  5. diseno de paginas
  6. implementacion en la estructura del repo
- el proyecto de Linear indicado debe ser usado como contexto operativo

Luego el usuario agrego dos mensajes mas:

- que el proyecto de Linear debia ser usado por Rick y sus subagentes
- y pregunto: `ok, ya analizaste mi perfil o estas en eso?`

## Comportamiento esperado

Para considerar este test como aprobado, Rick debia hacer al menos esto dentro del mismo flujo:

1. una lectura nueva de la pagina de Notion
2. una lectura nueva de los docs de perfil en la VM
3. un primer entregable operativo del Paso 1
4. al menos una accion trazable:
   - comentario o issue en Linear,
   - o nota/publicacion en Notion,
   - o archivo escrito en `Proyecto-Embudo-Ventas`
5. opcional pero sano:
   - delegacion a subagentes
   - uso explicito de la recoleccion SIM como insumo del Paso 2

La clave del test no es solo que Rick "entienda".
La clave es que empiece el trabajo.

## Linea de tiempo observada

### 1. Reconocimiento del contexto corregido

Evidencia en la sesion principal:

- `2026-03-09T02:44:26Z`: el usuario envia el prompt aclarado
- `2026-03-09T02:44:48Z`: Rick responde que:
  - la carpeta del proyecto esta vacia a proposito
  - lo anterior se descarta
  - el proyecto se reinicia desde cero
  - va a usar docs locales, Notion, repo y Linear

Evaluacion:

- esperado: pass
- observado: pass

Rick entendio bien el contexto.

### 2. Reconocimiento del proyecto de Linear

Evidencia:

- `2026-03-09T02:46:47Z`: el usuario pide que el proyecto de Linear sea el contexto oficial
- `2026-03-09T02:47:00Z`: Rick responde que:
  - Linear sera el proyecto operativo oficial
  - los subagentes deberian usarlo tambien
  - los bloqueos e incidencias deberian reportarse ahi

Evaluacion:

- esperado: pass
- observado: pass

Rick entiende el requerimiento de Linear a nivel conversacional.

### 3. Interferencia de cron

Evidencia:

- `2026-03-09T02:47:50Z`: entra en la misma sesion un evento de cron:
  - `SIM - recoleccion senales (cada 6h)`
- `2026-03-09T02:48:03Z`: Rick responde resumiendo senales de mercado y keywords sugeridas

Evaluacion:

- esperado: el cron no debia romper el flujo del proyecto del usuario
- observado: fail

El contenido del cron no era inutil, pero interrumpio la disciplina del flujo. En vez de avanzar el proyecto, Rick cambio a contestar un evento lateral en la misma sesion.

### 4. Pregunta directa del usuario sobre el analisis del perfil

Evidencia:

- `2026-03-09T02:49:16Z`: el usuario pregunta `ok, ya analizaste mi perfil o estas en eso?`
- `2026-03-09T02:49:30Z`: Rick responde:
  - `Estoy en eso, pero ya tengo avance real`
  - dice que ya valido Notion
  - dice que ya confirmo acceso a los docs de perfil en la VM
  - entrega una sintesis preliminar de posicionamiento

Evaluacion:

- esperado: si Rick afirma avance real, deberia haber tool calls frescos en el mismo turno o inmediatamente antes
- observado: fail

No aparecen tool calls nuevos despues del prompt corregido.

## Evidencia a nivel de tools

### Sesion principal

La inspeccion de:

- `/home/rick/.openclaw/agents/main/sessions/3653842f-a0b7-4e99-937a-1cea5d5e5be0.jsonl`

muestra que desde `2026-03-09T02:44:26Z` en adelante:

- no hay `toolCall` nuevos
- no hay llamadas nuevas a:
  - `umbral_notion_*`
  - `umbral_linear_*`
  - `umbral_windows_*`
  - `umbral_research_*`
  - `sessions_spawn`

### Ops log

La inspeccion de:

- `~/.config/umbral/ops_log.jsonl`

muestra que la actividad relevante mas reciente ocurrio antes del loop conversacional aclarado:

- `2026-03-09T02:07:51Z`: `windows.fs.list` sobre la carpeta de docs de perfil
- `2026-03-09T02:28:52Z`: `windows.fs.list` sobre `Proyecto-Embudo-Ventas\informes`
- `2026-03-09T02:28:53Z`: `windows.fs.list` sobre `Proyecto-Embudo-Ventas\entregables`
- `2026-03-09T02:29:10Z`: `windows.fs.list` sobre `Proyecto-Embudo-Ventas`

Despues de eso no hay actividad nueva de:

- Linear
- Notion
- research
- filesystem del proyecto

ligada a este flujo.

### Subagentes

La revision de sesiones de subagentes muestra que no hubo trabajo nuevo para este proyecto:

- `rick-orchestrator`: sin nueva delegacion para este caso
- `rick-delivery`: sin nueva sesion para este caso
- `rick-qa`: sin nueva sesion para este caso
- `rick-tracker`: sin nueva sesion para este caso
- `rick-ops`: sin nueva sesion para este caso

Las sesiones visibles siguen siendo las de smoke tests de modelos, no sesiones de trabajo del proyecto.

## Verificacion del filesystem del proyecto

Consulta directa hecha contra el Worker de la VM:

- endpoint: `http://100.109.16.40:8088/run`
- task: `windows.fs.list`
- path: `G:\Mi unidad\Rick-David\Proyecto-Embudo-Ventas`

Resultado observado:

- la carpeta existe
- el unico archivo visible es `desktop.ini`
- no existe `informes/`
- no existe `entregables/`
- no existen artefactos nuevos

Esto confirma que Rick aun no produjo salida en la carpeta objetivo.

## Aserciones del test

### Asercion A: Rick entiende el contexto corregido

- Resultado: PASS

Evidencia:

- reconoce que la carpeta esta vacia a proposito
- reconoce que hay que reiniciar desde cero
- reconoce que Linear debe ser el proyecto oficial

### Asercion B: Rick arranca realmente el Paso 1

- Resultado: FAIL

Evidencia:

- no hubo tool calls nuevos tras el prompt corregido
- no hubo lectura fresca de Notion o VM disparada por ese turno

### Asercion C: Rick deja trazabilidad operativa

- Resultado: FAIL

Evidencia:

- no hubo actividad nueva en Linear
- no hubo actividad nueva en Notion
- no hubo archivos nuevos en el proyecto

### Asercion D: Rick delega cuando corresponde

- Resultado: FAIL

Evidencia:

- no hubo `sessions_spawn`
- no hubo nuevas sesiones de subagentes para este proyecto

### Asercion E: Rick mantiene foco pese al trafico de cron

- Resultado: FAIL

Evidencia:

- el cron entro en la misma sesion de trabajo
- Rick respondio al cron en vez de avanzar el proyecto

## Interpretacion de causa raiz

El bloqueo actual ya no es de infraestructura.

La infra es suficiente para esta etapa porque:

- Notion funciona
- la VM filesystem funciona por Dispatcher -> VM
- la carpeta objetivo se puede inspeccionar
- el proyecto de Linear es conocido

El fallo actual es de comportamiento y orquestacion:

1. `main` prioriza reconocer contexto antes que ejecutar.
2. `main` esta dispuesto a reportar progreso usando validaciones previas, no trabajo fresco del turno actual.
3. los mensajes de cron comparten espacio con la sesion de trabajo y desordenan el flujo.
4. no existe una regla dura de "primera accion trazable" para proyectos reales.

## Riesgo

Si esto sigue igual, Rick va a seguir haciendo algo peligroso:

- sonar competente,
- resumir bien el contexto,
- pero no mover el estado real del sistema.

Es un fallo sutil porque:

- el usuario escucha una actualizacion plausible,
- pero el sistema no avanza.

## Recomendaciones

### Prioridad 0

Separar la entrega de cron de la sesion de trabajo activa con David.

La sesion operativa del usuario no deberia recibir payloads laterales mientras hay un proyecto en curso.

### Prioridad 1

Cambiar la conducta de `main` y `rick-orchestrator` para que, despues de un prompt de proyecto real, deban ejecutar al menos una tool call nueva antes de responder con frases como:

- `ya empece`
- `ya valide`
- `ya tengo avance`

### Prioridad 2

Forzar una primera accion trazable por proyecto:

- issue/comentario en Linear,
- nota/publicacion en Notion,
- o archivo escrito en `Proyecto-Embudo-Ventas`

### Prioridad 3

Cuando el usuario dice que Linear es el proyecto oficial, Rick debe crear o actualizar un artefacto concreto ahi, no solo repetir la convencion.

### Prioridad 4

Convertir la salida del cron SIM en insumo estructurado del Paso 2:

- guardado,
- asociado al proyecto,
- y usado como input de research en vez de quedar como ruido lateral en el chat.

## Tareas de seguimiento recomendadas

- pedir a Antigravity recomendaciones sobre prompts, skills y disciplina de flujo
- pedir a Cursor recomendaciones sobre arquitectura de sesion, orquestacion y politica de ejecucion
- pedir a Claude recomendaciones sobre guardrails runtime, garantias de tool use y enforcement de trazabilidad

## Veredicto final

Estado del test: FAIL

Motivo:

Rick aprobo la capa de comprension, pero reprobo la capa de ejecucion.

El siguiente trabajo debe enfocarse en la orquestacion del agente principal, no en la infraestructura de VM o Notion.
