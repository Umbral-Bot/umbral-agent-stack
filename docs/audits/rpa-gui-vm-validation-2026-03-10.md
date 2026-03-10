## Ejecutado por: codex

# Validación RPA GUI VM — 2026-03-10

## Objetivo

Medir el estado real del control GUI de la VM como si el agente usara el PC “como una persona”: clicks, tipeo, hotkeys y capturas de pantalla.

## Alcance

Se validó en dos rutas distintas de la VM:

- Worker estándar: `http://100.109.16.40:8088`
- Worker interactivo: `http://100.109.16.40:8089`

Tasks cubiertos:

- `gui.desktop_status`
- `gui.screenshot`
- `gui.click`
- `gui.type_text`
- `gui.hotkey`

## Resultado ejecutivo

El slice GUI quedó **operativo para baseline visual**, pero todavía no para flujos completos:

- input GUI: OK
- metadatos de escritorio: OK
- screenshot GUI en `8088`: negro / no usable
- screenshot GUI en `8089` interactivo: OK / usable

Conclusión:

- el agente ya puede inyectar input real
- la captura visual ya es usable cuando la tool GUI entra por el worker interactivo
- todavía falta validar un flujo RPA/GUI completo sobre una app objetivo real antes de tratar este frente como cerrado

## Implementación validada

### Código local relevante

- `worker/tasks/gui.py`
- `worker/tasks/windows.py`
- `worker/tasks/__init__.py`

### Librerías probadas en VM

Se probaron o dejaron instaladas para el frente GUI:

- `pyautogui`
- `pywinauto`
- `uiautomation`
- `mss`

## Smoke tests ejecutados

### 1. Estado de escritorio

`gui.desktop_status` respondió correctamente con:

- tamaño de pantalla
- posición de cursor
- control raíz

### 2. Input GUI

Funcionaron:

- `gui.click`
- `gui.type_text`
- `gui.hotkey`

Esto confirma que la sesión acepta input.

### 3. Screenshot GUI

`gui.screenshot` ahora:

- ya no exige `path`
- usa por defecto `%TEMP%\\openclaw-gui-shots\\gui-shot.png`
- prueba varios backends (`ImageGrab`, `pyautogui`, `mss`)
- reporta `usable_visual` y `black_frame`

Resultado observado:

- en `8088`, `mss` responde pero devuelve negro
- en `8089`, `ImageGrab` devuelve una captura real, no negra

Verificación analítica del caso bueno:

- tamaño correcto: `1024x768`
- `mean_luma` > 0
- `max_luma = 255`
- `black_frame = false`

## Causa raíz más probable

La VM no estaba fallando "por GUI" en general, sino por el camino de ejecución:

- el worker estándar (`8088`) no tiene una superficie visual útil para captura GUI
- el worker interactivo (`8089`) sí

Síntomas observados:

- `8088`:
  - `ImageGrab`: falla
  - `pyautogui.screenshot()`: falla
  - `mss`: devuelve negro
- `8089`:
  - `ImageGrab`: OK
  - captura visual real y usable

## Qué hizo Rick vs qué hice yo

### Hecho por Rick

- trazabilidad previa del proyecto `Autonomía RPA GUI en VM`
- reauditoría final cuando el routing ya quedó corregido, reflejando que la captura GUI pasó a ser usable

### Hecho por codex

- hardening del task `gui.screenshot`
- tests unitarios
- despliegue del handler mejorado en la VM
- reroute de `umbral_gui_*` al worker interactivo
- validación remota final del estado real

## Validación posterior sobre app real simple

En una pasada adicional posterior al reroute, Rick validó un flujo real sobre Notepad y dejó trazabilidad en:

- `UMB-77`
- `G:\Mi unidad\Rick-David\Proyecto-Auditoria-Mejora-Continua\informes\reauditoria-gui-rpa-vm-2026-03-10-1918-notepad-real.md`

Resultado de esa pasada:

- `windows.open_notepad`: OK
- `gui.click`: OK
- `gui.type_text`: OK
- `gui.screenshot`: OK
- captura visual utilizable: sí

## Higiene del escritorio interactivo

Durante una pasada posterior se detectó que el escritorio interactivo seguía
contaminado por una consola visible de `granola_watcher.py`, lo que robaba foco
al probar navegador/GUI.

Fix aplicado:

- se agregó `scripts/vm/start_granola_watcher_hidden.ps1`
- se actualizó `scripts/vm/setup_granola_watcher.ps1` para registrar `GranolaWatcher`
  con launcher oculto
- se reconfiguró la tarea `GranolaWatcher` en la VM para usar ese launcher

Resultado:

- el watcher dejó de aparecer como consola visible en foreground
- la captura interactiva volvió a mostrar apps reales de usuario (Granola, navegador, etc.)

## Veredicto

El objetivo de “usar el PC de la VM como una persona” ya quedó demostrado en un nivel básico real, pero no totalmente cerrado.

Lo que sí quedó:

- input real usable
- visión/screenshot útil por la ruta correcta (`8089`)

Lo que sigue bloqueando:

- falta una validación e2e sobre una app objetivo más compleja
- todavía no conviene reemplazar browser typed como primer canal

Por eso, la estrategia correcta ahora es:

1. browser typed primero
2. GUI con captura visual ya es complemento serio
3. validar un flujo más complejo antes de dar GUI/RPA por totalmente cerrado
