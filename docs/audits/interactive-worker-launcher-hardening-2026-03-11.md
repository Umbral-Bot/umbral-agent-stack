## Ejecutado por: codex

# Hardening del Worker Interactivo de la VM - 2026-03-11

## Objetivo

Cerrar el punto débil del canal GUI interactivo (`8089`) de la VM y dejar un arranque persistente, verificable y usable desde la VPS/gateway.

## Síntoma observado

`gui.*` funcionaba de forma intermitente:

- localmente en la VM podía responder por momentos
- desde la VPS se caía o quedaba en timeout
- los relanzamientos manuales desde SSH daban falsos positivos

## Causa raíz

El problema no era la tool GUI en sí.

La causa raíz real era el **modo de arranque** del Worker interactivo:

- cuando `8089` se lanzaba desde una sesión SSH, el proceso quedaba atado a esa sesión
- al cerrarse la sesión SSH, el worker interactivo moría
- eso producía drift entre:
  - pruebas locales dentro de la sesión
  - disponibilidad real desde la VPS
  - resultados de GUI aparentemente “inestables”

## Fix aplicado

### 1. Launcher endurecido

Se actualizó `scripts/vm/start_interactive_worker.ps1` para:

- fijar `PYTHONPATH=C:\GitHub\umbral-agent-stack`
- fijar `PYTHONIOENCODING=utf-8`
- resolver `uvicorn.exe` explícitamente con `Get-Command`
- escribir logs en `C:\openclaw-worker\logs\`

### 2. Criterio operativo correcto

Se validó que el arranque robusto no debe hacerse por SSH.

La ruta correcta es:

- tarea programada `StartInteractiveWorkerHiddenNow`

Eso saca al worker interactivo del job efímero de la sesión SSH y lo deja persistente para uso remoto desde la VPS.

## Pruebas ejecutadas

### Prueba local en la VM

Tras lanzar la tarea programada:

- `http://127.0.0.1:8089/health` -> `200`

### Prueba remota desde la VPS

Con la misma instancia ya viva:

- `POST /run` a `gui.desktop_status` sobre `100.109.16.40:8089` -> `200`

### Prueba funcional real

Se validó el flujo:

1. `windows.open_notepad`
2. `gui.list_windows`
3. `gui.activate_window`
4. `gui.screenshot`

Resultado:

- Notepad abrió correctamente
- la ventana apareció en el inventario top-level
- `activate_window` dejó a Notepad realmente al frente
- la captura visual mostró esa ventana de forma usable

## Estado final

El punto débil quedó resuelto.

Conclusión operativa:

- `8088` sigue siendo el worker estándar
- `8089` es el worker interactivo oficial para `gui.*`
- `8089` debe arrancarse por tarea programada, no por sesiones SSH

## Pendiente real

No queda un bloqueo de infraestructura en este frente.

Lo pendiente ahora es solamente funcional:

- validar un flujo GUI más complejo sobre una app objetivo real
- no reabrir el diagnóstico base del launcher
