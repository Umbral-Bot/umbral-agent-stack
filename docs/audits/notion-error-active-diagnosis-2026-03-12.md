# Diagnóstico Activo — Errores Registrados en Notion (2026-03-12)

## Contexto

Se revisó el estado operativo mientras Rick interactuaba sobre el frente web del embudo.
En esta sesión no fue posible leer Notion por MCP porque la autenticación del conector no estaba disponible (Auth required), así que el diagnóstico se hizo por correlación entre:

- sesión activa de main en OpenClaw
- ops_log.jsonl en la VPS
- estado real de tools ejecutadas
- routing del Dispatcher

## Hallazgos iniciales

### 1. No había un error nuevo de Notion asociado al turno activo de Rick

Durante la ventana inspeccionada, Rick sí entró a trabajar en el proyecto embudo y ejecutó:

- windows.fs.read_text
- archivo: G:\Mi unidad\Rick-David\Proyecto-Embudo-Ventas\estado-actual-proyecto-embudo-web.md

No aparecieron en ese tramo:

- escrituras nuevas a Notion
- updates nuevos en Linear
- errores nuevos de 
otion.*

Conclusión: en ese turno visible, Rick estaba en fase de lectura/contexto y no generó todavía un error nuevo en Notion.

### 2. El error operativo activo más claro no era de Notion sino de esearch.web

Persistían fallos intermitentes del frente improvement:

- task: esearch.web
- team: improvement
- worker destino: http://100.109.16.40:8088/run
- resultado: 500 Internal Server Error

Queries observadas:

- SaaS herramientas gestión agentes AI
- 
8n make automatización workflows IA

### 3. Había ruido repetitivo de baja señal desde el frente embudo

Se observaron ejecuciones periódicas repetidas de:

- windows.fs.list
- ruta: G:\Mi unidad\Rick-David\Proyecto-Embudo-Ventas

Estas llamadas no son un error por sí mismas, pero generan ruido y pueden inflar la percepción de actividad si no se traducen en:

- artefactos nuevos
- updates en Linear
- cambios persistidos en Notion

## Causa raíz confirmada

El problema principal no era Notion ni la VM como tal, sino el routing por equipo del Dispatcher:

- scripts/sim_daily_research.py encola búsquedas esearch.web para el pool improvement
- config/teams.yaml define improvement.requires_vm: true
- el Dispatcher usaba equires_vm a nivel de equipo, no de task
- resultado: tareas esearch.web del equipo improvement se mandaban a la VM aunque no lo necesitan
- en la VM esas búsquedas devolvían 500, contaminando el tracking del equipo de mejora continua y lo que luego se reflejaba en Notion

## Fix aplicado

Se introdujo routing por task:

- tasks locales aunque el equipo use VM:
  - esearch.*
  - llm.*
  - composite.*
  - 
otion.*
  - linear.*
  - 
8n.*
  - google.*
  - zure.*
  - openai.*
  - make.*
- tasks que sí siguen yendo a VM:
  - windows.*
  - rowser.*
  - gui.*
  - granola.*

Archivos tocados:

- dispatcher/task_routing.py
- dispatcher/router.py
- dispatcher/service.py
- 	ests/test_task_routing.py
- 	ests/test_dispatcher.py

## Validación local

- python -m pytest tests/test_dispatcher.py tests/test_task_routing.py -q -p no:cacheprovider
- resultado: 34 passed

## Despliegue y smoke en VPS

Se desplegó el fix en la VPS con backup previo y se reinició el Dispatcher.

Smoke real:

- team: improvement
- task: esearch.web
- query: outing smoke improvement

Resultado observado en ops_log:

- 	ask_completed
- 	eam: improvement
- 	ask: research.web
- worker: vps
- sin 500

Con esto quedó confirmado que el error activo ya no reproduce por la misma causa.

## Diagnóstico final

El problema principal en esta pasada no fue “Notion roto”, sino:

1. falta de visibilidad directa de Notion desde esta sesión
2. un fallo real del equipo improvement en esearch.web contra la VM
3. ruido operativo de listados repetidos sin cambio de estado visible
4. routing por equipo demasiado grueso para tasks que en realidad son VPS-only

## Siguiente paso recomendado

1. Vigilar si los próximos runs de SIM Daily Research dejan de generar 500 para improvement
2. Reducir o reencaminar los windows.fs.list repetitivos del frente embudo si no generan acciones reales
3. Cuando vuelva a haber acceso MCP a Notion, confirmar que el dashboard/registro ya no refleja esos fallos recurrentes