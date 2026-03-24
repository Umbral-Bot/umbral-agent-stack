---
name: browser-automation-vm
description: >-
  Operar navegador y escritorio en la VM Windows del stack. Usar cuando el
  trabajo requiera `browser.*`, `gui.*` o `windows.open_url`, por ejemplo para
  abrir una URL en la sesion interactiva, navegar con Playwright, leer DOM,
  hacer clics, tomar capturas o automatizar ventanas y dialogs nativos.
metadata:
  openclaw:
    emoji: "\U0001F310"
    requires:
      env:
        - WORKER_TOKEN
        - BROWSER_HEADLESS
---

# Browser Automation VM

Esta skill gobierna la operacion completa de navegador y escritorio en la VM
Windows. No cubre solo `browser.*`: tambien decide cuando usar `gui.*` y
`windows.open_url`.

## Decision rapida

### Usa `windows.open_url`

Cuando solo necesitas abrir una URL en el navegador predeterminado y dejar la
sesion lista para el usuario o para otra tool.

```json
{
  "task_type": "windows.open_url",
  "input": {
    "url": "https://linear.app/umbral"
  }
}
```

### Usa `browser.*`

Cuando el flujo es DOM-driven y necesitas selectors, titulo, texto estructurado
o capturas de una pagina manejada por Playwright.

Tasks reales:

- `browser.navigate`
- `browser.read_page`
- `browser.screenshot`
- `browser.click`
- `browser.type_text`
- `browser.press_key`

### Usa `gui.*`

Cuando dependes del escritorio interactivo, una ventana ya abierta, un dialog
nativo, una app sin DOM o un control que Playwright no ve.

Tasks reales:

- `gui.desktop_status`
- `gui.screenshot`
- `gui.click`
- `gui.type_text`
- `gui.hotkey`
- `gui.list_windows`
- `gui.activate_window`

## Checklist de readiness

1. Decide si el caso es `headless` o `interactive`.
2. Si vas a usar `gui.*`, corre primero `gui.desktop_status`.
3. Si necesitas una ventana concreta, usa `gui.list_windows` antes de `gui.activate_window`.
4. Si el objetivo es un sitio con selectors claros, prefiere `browser.*`.
5. No uses `umbral_worker_run` para VM si ya tienes tools tipadas.
6. Si la URL viene de una fase previa de `research`, no asumas que la primera
   fuente es valida: confirma titulo, DOM o contenido visible con `browser.read_page`
   o evidencia equivalente.
7. Si la pagina devuelve `404`, `Page not found`, homepage generica o contenido
   no relacionado, no cierres el caso: vuelve a la segunda fuente candidata.

## Ejemplos reales

### Abrir una URL

```json
{
  "task_type": "windows.open_url",
  "input": {
    "url": "https://www.notion.so/"
  }
}
```

### Navegar con Playwright

```json
{
  "task_type": "browser.navigate",
  "input": {
    "url": "https://acc.autodesk.com/dashboard",
    "wait_until": "networkidle",
    "timeout_ms": 30000
  }
}
```

### Leer una pagina

```json
{
  "task_type": "browser.read_page",
  "input": {
    "selector": "main",
    "include_html": false
  }
}
```

### Escribir en un campo

```json
{
  "task_type": "browser.type_text",
  "input": {
    "selector": "input[name='q']",
    "text": "licitaciones BIM 2026",
    "clear": true,
    "press_enter": true
  }
}
```

### Estado del escritorio

```json
{
  "task_type": "gui.desktop_status",
  "input": {}
}
```

### Listar ventanas

```json
{
  "task_type": "gui.list_windows",
  "input": {
    "visible_only": true
  }
}
```

### Activar ventana por titulo

```json
{
  "task_type": "gui.activate_window",
  "input": {
    "title_contains": "Chrome"
  }
}
```

### Capturar escritorio

```json
{
  "task_type": "gui.screenshot",
  "input": {
    "path": "G:\\Mi unidad\\Rick-David\\capturas\\vm.png",
    "return_b64": false
  }
}
```

### Click y escritura

```json
{
  "task_type": "gui.click",
  "input": {
    "x": 640,
    "y": 380,
    "button": "left",
    "clicks": 1
  }
}
```

```json
{
  "task_type": "gui.type_text",
  "input": {
    "text": "Hola desde Rick",
    "interval": 0.02
  }
}
```

### Hotkey

```json
{
  "task_type": "gui.hotkey",
  "input": {
    "keys": ["ctrl", "l"]
  }
}
```

## Regla practica

- `windows.open_url` abre
- `browser.*` navega y entiende DOM
- `gui.*` opera la sesion interactiva visible

No mezcles los tres enfoques sin motivo.

## Regla especial para verificacion de fuentes

Cuando el objetivo sea validar una fuente encontrada por research:

- abrir una URL no equivale a verificarla;
- necesitas al menos una senal observable del contenido correcto:
  - titulo esperado,
  - texto principal relacionado,
  - DOM legible,
  - o screenshot util;
- si la primera fuente falla, intenta una segunda antes de declarar degradacion;
- si ambas fallan, reporta que hubo degradacion de verificacion web y separa eso
  del hallazgo original de research.

## Anti-patrones

- No usar `gui.*` para un sitio que Playwright puede resolver con selector.
- No declarar exito visual sin screenshot o estado de ventana.
- No asumir que `browser.*` controla dialogs nativos del sistema operativo.
- No documentar tareas inexistentes como `browser.fill`, `browser.tabs.*` o
  `browser.ai.execute` mientras no existan en el Worker.
- No marcar una referencia como verificada si la pagina abierta devuelve `404`,
  `Page not found` o contenido no relacionado.
- No abandonar la verificacion tras la primera URL caida si existe una segunda
  fuente candidata razonable del mismo hallazgo.

## Cierre esperado

Cuando cierres un trabajo con esta skill, deja claro:

- si operaste `headless` o `interactive`;
- que tasks exactas corriste;
- y que evidencia visual o textual confirma el resultado.

Si el trabajo venia de research, deja ademas:

- si la verificacion quedo en primera fuente o segunda fuente;
- o si el hallazgo quedo solo como señal de research no verificada en browser.
