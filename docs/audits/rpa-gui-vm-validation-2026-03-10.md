## Ejecutado por: codex

# Validación RPA GUI VM — 2026-03-10

## Objetivo

Medir el estado real del control GUI de la VM como si el agente usara el PC “como una persona”: clicks, tipeo, hotkeys y capturas de pantalla.

## Alcance

Se validó sobre el Worker de la VM en `http://100.109.16.40:8088`:

- `gui.desktop_status`
- `gui.screenshot`
- `gui.click`
- `gui.type_text`
- `gui.hotkey`

## Resultado ejecutivo

El slice GUI quedó **parcialmente operativo**:

- input GUI: OK
- metadatos de escritorio: OK
- screenshot GUI: responde, pero el framebuffer sale negro

Conclusión:

- el agente ya puede inyectar input real
- pero sigue ciego para verificar visualmente lo que hace
- por tanto, este frente todavía no está listo para reemplazar browser typed ni para sostener Freepik/login visual como flujo confiable

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

Pero la imagen resultante sigue siendo negra.

Verificación analítica previa:

- tamaño correcto
- contenido RGB plano en negro

Eso confirma que no es un error de archivo; es un problema de captura/render.

## Causa raíz más probable

La VM acepta input, pero no expone una superficie visual útil al método de captura actual.

Síntomas observados:

- `mss` devuelve negro
- `pyautogui.screenshot()` no es utilizable de forma confiable
- `uiautomation` no devuelve un árbol suficientemente útil para control semántico completo

## Qué hizo Rick vs qué hice yo

### Hecho por Rick

- trazabilidad previa del proyecto `Autonomía RPA GUI en VM`
- documentación operativa de que GUI input era usable y framebuffer no

### Hecho por codex

- hardening del task `gui.screenshot`
- tests unitarios
- validación remota final del estado real

## Veredicto

El objetivo de “usar el PC de la VM como una persona” todavía no está logrado de punta a punta.

Lo que sí quedó:

- input real usable

Lo que sigue bloqueando:

- visión/screenshot útil del escritorio

Por eso, la estrategia correcta sigue siendo:

1. browser typed primero
2. GUI solo para casos donde haga falta input real
3. no depender todavía de GUI visual como canal principal
