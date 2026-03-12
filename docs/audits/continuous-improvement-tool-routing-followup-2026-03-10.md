## Ejecutado por: codex

# Follow-up — mejora continua y enrutamiento correcto de tools VM — 2026-03-10

## Contexto

Después de corregir el fallback de `main` y estabilizar el runtime, se hizo una re-auditoría con Rick sobre el frente de mejora continua.

Rick seguía afirmando que el bloqueo GUI/RPA de la VM era:

- `No module named 'pyautogui'`

Ese diagnóstico resultó ser un **drift de elección de tool**, no un estado real de la VM.

## Causa raíz

El plugin `umbral-worker` ya tenía definidas las tools tipadas:

- `umbral_browser_click`
- `umbral_browser_type_text`
- `umbral_browser_press_key`
- `umbral_gui_desktop_status`
- `umbral_gui_screenshot`
- `umbral_gui_click`
- `umbral_gui_type_text`
- `umbral_gui_hotkey`

Todas ellas en `dispatchMode: "enqueue"` y `defaultTeam: "lab"`, es decir, hacia la VM.

Pero `main` no tenía esas tools expuestas en su `tools.alsoAllow`, por lo que Rick terminó usando:

- `umbral_worker_run`

Eso ejecutó la comprobación en el Worker local de la VPS (Linux), donde sí aparecía:

- `No module named 'pyautogui'`

Ese error era verdadero **solo para el Worker local**, no para la VM.

## Cambios aplicados

### Guardrails / skill

Se endurecieron:

- `openclaw/workspace-templates/AGENTS.md`
- `openclaw/workspace-templates/SOUL.md`
- `openclaw/extensions/umbral-worker/skills/umbral-worker/SKILL.md`

Con la regla operativa:

- VM/Windows/navegador/GUI siempre por tools tipadas
- no usar `umbral_worker_run` para `windows.*`, `browser.*` ni `gui.*` si existe una tool tipada equivalente

### Runtime VPS

Se agregó al agente `main` en `~/.openclaw/openclaw.json`:

- `umbral_browser_click`
- `umbral_browser_type_text`
- `umbral_browser_press_key`
- `umbral_gui_desktop_status`
- `umbral_gui_screenshot`
- `umbral_gui_click`
- `umbral_gui_type_text`
- `umbral_gui_hotkey`

Luego:

- `systemctl --user restart openclaw-gateway.service`

## Re-prueba

Se volvió a pedir a Rick una revalidación usando explícitamente las tools tipadas de VM.

### Resultado inicial

Rick corrigió parcialmente el diagnóstico:

- invalidó la hipótesis de `pyautogui` faltante en la VM
- pasó a usar las tools tipadas correctas

Pero todavía quedó un residual en la trazabilidad:

- reportó `GUI screenshot: OK`

### Verificación independiente posterior

Se ejecutó una validación directa contra el Worker de la VM:

- `gui.desktop_status`: OK
- `gui.click`: OK
- `gui.type_text`: OK
- `gui.hotkey`: OK
- `gui.screenshot`: devuelve un PNG válido de `1024x768`, pero completamente negro

La captura fue medida de forma independiente:

- tamaño: `1024x768`
- colores únicos: `1`
- color único: `(0, 0, 0)`

Por lo tanto, la conclusión correcta final es:

- `GUI input`: OK
- `GUI screenshot/framebuffer visual`: NO usable todavía

### Corrección final

Se empujó a Rick a reauditar este punto y corregir la trazabilidad visible.

Rick dejó corregido el estado real en:

- `UMB-77`
- comentario en Notion
- `G:\Mi unidad\Rick-David\Proyecto-Auditoria-Mejora-Continua\informes\reauditoria-gui-rpa-vm-2026-03-10-1337.md`

La respuesta final ya quedó alineada con el estado real:

- el problema no era ausencia de `pyautogui` en la VM
- el problema no era selección de tool en esta última iteración
- el bloqueo real restante es el framebuffer negro en `gui.screenshot`

## Estado final

- Runtime de `main`: corregido
- Selección de tool para VM/browser/GUI: endurecida
- Re-auditoría de Rick: corregida, con un segundo ajuste para alinear `gui.screenshot`
- Trazabilidad: Rick dejó la corrección en Linear, Notion y carpeta compartida

## Conclusión

Este follow-up confirma que:

1. la definición de tools en el plugin era correcta
2. el problema estaba en la exposición/configuración del agente `main`
3. una parte del drift de Rick no era de modelo, sino de runtime/tool availability
4. el bloqueo GUI/RPA remanente no es `pyautogui`, sino captura visual negra
