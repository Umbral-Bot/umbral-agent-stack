## Ejecutado por: codex

# Validación reroute GUI interactivo VM - 2026-03-10

## Objetivo

Cerrar el gap entre:

- el baseline GUI del worker estándar de la VM (`8088`), donde la captura visual seguía negra
- y el worker interactivo (`8089`), donde `ImageGrab` ya devolvía una captura útil

La meta de esta iteración fue hacer que Rick y las tools `umbral_gui_*` usaran la ruta correcta sin depender de llamadas manuales fuera del gateway.

## Cambio aplicado

Se modificó el plugin `umbral-worker` para soportar un override de base URL por tool:

- nueva capacidad: `baseUrlEnv` por `TaskToolDefinition`
- nuevas opciones en `workerRequest` y `runNamedTask`
- `umbral_gui_desktop_status`
- `umbral_gui_screenshot`
- `umbral_gui_click`
- `umbral_gui_type_text`
- `umbral_gui_hotkey`

quedaron configuradas con:

- `dispatchMode: "run"`
- `baseUrlEnv: "WORKER_URL_VM_INTERACTIVE"`

En la VPS ya existía:

- `WORKER_URL_VM_INTERACTIVE=http://100.109.16.40:8089`

Por tanto, el cambio efectivo fue sincronizar el plugin actualizado al gateway y reiniciar el servicio.

## Despliegue

En la VPS se hizo:

- backup de `~/.openclaw/extensions/umbral-worker/index.ts`
- copia del `index.ts` nuevo
- reinicio de `openclaw-gateway.service`

Estado del servicio tras el deploy:

- `active`

## Validación técnica

### 1. Llamada directa al worker interactivo

Antes de tocar el plugin, ya se había confirmado:

- `gui.screenshot` en `8089` devolvía imagen no negra
- `capture_method: imagegrab`
- `usable_visual: true`
- `black_frame: false`

### 2. Validación end-to-end a través de Rick

Se ejecutó un turno directo a `main` pidiéndole usar solamente:

- `umbral_gui_desktop_status`
- `umbral_gui_screenshot`

Resultado real devuelto por Rick:

- `screen_width: 1024`
- `screen_height: 768`
- `root_name: "Escritorio 1"`
- screenshot en `C:\\Users\\Rick\\AppData\\Local\\Temp\\gui-check-20260310-1817.png`
- `capture_method: imagegrab`
- `usable_visual: true`
- `mean_luma: 100.89343770345052`
- `min_luma: 0`
- `max_luma: 255`
- `black_frame: false`

Esto confirma que el reroute quedó operativo a nivel de gateway/agent runtime, no solo por llamadas manuales a la VM.

### 3. Reauditoría con Rick

Después del reroute se pidió a Rick reauditar el frente GUI/RPA.

Resumen correcto que dejó:

- la captura GUI de la VM sí es utilizable
- siguen funcionando input GUI, screenshot GUI y estado de escritorio
- todavía no hay validación de un flujo completo GUI/RPA sobre una app objetivo real

## Estado final

### Lo que quedó logrado

- `gui.desktop_status`: usable por Rick
- `gui.screenshot`: usable por Rick
- `gui.click`: enrutable por la misma vía interactiva
- `gui.type_text`: enrutable por la misma vía interactiva
- `gui.hotkey`: enrutable por la misma vía interactiva

### Lo que sigue pendiente

- validar un flujo GUI/RPA completo sobre una app real
- decidir en qué casos conviene GUI y en cuáles browser typed sigue siendo mejor

## Conclusión

El bloqueo principal de GUI visual ya no es la captura misma, sino la falta de una validación e2e sobre una tarea real.

Estado honesto después de esta iteración:

- `8088`: no confiar para GUI visual
- `8089`: usar como ruta oficial para `umbral_gui_*`
- Rick: ya puede verificar la pantalla de la VM con evidencia real a través del gateway
