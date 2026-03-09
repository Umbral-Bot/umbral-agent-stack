# Rick Live Test 2026-03-08

## Context

Prompt enviado a Rick por Telegram para iniciar el proyecto `Proyecto-Embudo-Ventas`:

- usar carpeta `Rick-David\Proyecto-Embudo-Ventas`
- estudiar perfil local en `Rick-David\Perfil de David Moreira\Creado por David`
- estudiar perfil público en Notion
- seguir los 6 pasos del proyecto comercial y web

## Comportamiento esperado

Rick debía:

1. leer el perfil local desde la VM por las tools `umbral_windows_fs_*`
2. leer el perfil público con `umbral_notion_read_page`
3. usar `umbral_research_web` para planificar y ejecutar investigación
4. luego producir artefactos y trazabilidad en Notion/Linear según el plan

La VM debía ser una capacidad adicional, no una dependencia estructural vía `nodes`.

## Comportamiento observado

### Falla inicial

El `main` agent intentó usar `nodes` en vez de las tools del Worker:

- `nodes status`
- luego `node.invoke -> system.run`
- resultado: `UNAVAILABLE: SYSTEM_RUN_DENIED: approval required`

Consecuencia:

- no hubo llamadas nuevas a `windows.fs.*`
- no hubo lecturas de Notion para ese prompt
- no hubo actualizaciones de negocio en Linear o Notion derivadas de ese turno
- Rick respondió con bloqueo operacional aunque la VM estaba sana

### Causa raíz 1

`main` todavía tenía `group:nodes` habilitado en OpenClaw. Eso permitía que el modelo prefiriera el camino de `nodes` y fallara por política de aprobación.

## Fix 1

En la VPS se removió `group:nodes` de `main` y de los subagentes no operativos. `nodes` quedó solo para `rick-ops`.

Validación:

- `main` dejó de tener `nodes` en `systemPromptReport.tools.entries`
- `umbral_notion_read_page` quedó operativo desde `main`

## Falla secundaria

Una vez forzado al camino correcto del Worker, `umbral_windows_fs_list` devolvió:

`Solo disponible en Windows.`

### Causa raíz 2

El plugin `umbral-worker` ejecutaba las tools Windows con `POST /run` directo al Worker local de la VPS. Eso corría el handler Linux local en vez de enrutar la tarea a la VM.

## Fix 2

Se cambió el plugin `openclaw/extensions/umbral-worker/index.ts` para que todas las tools `windows.*` usen:

- `POST /enqueue`
- `team: lab`
- polling con `GET /task/{task_id}/status`

Eso hace que el Dispatcher enrute la tarea a la VM cuando `requires_vm: true`.

## Verificación post-fix

### Notion

Prueba controlada con `main`:

- tool: `umbral_notion_read_page`
- resultado: `Perfil David Moreira — Arquitecto, Consultor BIM, Docente, Educador y Comunicador`

### Windows FS

Prueba controlada con `main`:

- tool: `umbral_windows_fs_list`
- path: `G:\Mi unidad\Rick-David\Perfil de David Moreira\Creado por David`
- resultado: `06-estrategia-marketing.md, 02-servicios-actuales.md, 03-servicios-potencia.md`

Trazabilidad en `ops_log.jsonl`:

- `task_queued` id `4d135f9c-17c0-4c2e-9de9-5744fab31437`
- `task_completed` id `4d135f9c-17c0-4c2e-9de9-5744fab31437`
- `task = windows.fs.list`
- `team = lab`
- `worker = vm`

## Estado final

Después de estos fixes:

- Rick ya no depende de `nodes` para acceder a la VM
- Rick puede leer Notion por tool tipada
- Rick puede listar archivos de la VM por `umbral_windows_fs_list` usando Dispatcher -> VM
- la VM queda como capacidad adicional de cómputo e interacción manual, no como prerrequisito para la coordinación base

## Pendiente operativo

El prompt original enviado por Telegram no se re-ejecutó automáticamente después del fix. Para evaluar el flujo completo del proyecto real, conviene enviar un nuevo prompt o pedir explícitamente a Rick que retome desde el paso 1 con la configuración ya corregida.
