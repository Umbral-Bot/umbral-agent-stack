---
name: browser-automation-vm
description: >-
  Automatización de navegador web en la VM Windows tipo Claude in Chrome.
  Rick puede navegar a URLs, hacer clics, rellenar formularios, tomar capturas
  de pantalla, gestionar múltiples pestañas, mantener sesiones con cookies y
  ejecutar flujos grabados. Motor: Playwright Python con browser-use como capa AI.
  Use when "navegar web en VM", "captura pantalla sitio", "clic en página",
  "llenar formulario web", "automatizar navegador", "browser automation",
  "abrir pestaña", "scraping en VM", "flujo web automatizado", "screenshot web".
metadata:
  openclaw:
    emoji: "🌐"
    requires:
      env:
        - WORKER_TOKEN
        - BROWSER_HEADLESS
---

# Browser Automation VM — Automatización de Navegador en la VM (tipo Claude in Chrome)

Rick puede controlar un navegador Chromium en la VM de Windows para navegar, hacer clics, rellenar formularios, tomar capturas y gestionar pestañas — de forma similar a lo que hace Claude in Chrome pero ejecutado en el Execution Plane (VM).

**Motor:** Playwright Python  
**Capa AI (opcional):** browser-use  
**Plan completo:** [`docs/64-browser-automation-vm-plan.md`](../../docs/64-browser-automation-vm-plan.md)

---

## Capacidades

| Capacidad | Tarea Worker | Estado |
|-----------|-------------|--------|
| Navegar a URL | `browser.navigate` | 📋 Planificada (Fase 1) |
| Clic en elemento | `browser.click` | 📋 Planificada (Fase 1) |
| Rellenar campo | `browser.fill` | 📋 Planificada (Fase 1) |
| Captura de pantalla | `browser.screenshot` | 📋 Planificada (Fase 1) |
| Leer contenido de página | `browser.read_page` | 📋 Planificada (Fase 1) |
| Listar pestañas | `browser.tabs.list` | 📋 Planificada (Fase 2) |
| Abrir pestaña | `browser.tabs.open` | 📋 Planificada (Fase 2) |
| Cerrar pestaña | `browser.tabs.close` | 📋 Planificada (Fase 2) |
| Ejecutar JavaScript | `browser.execute` | 📋 Planificada (Fase 2) |
| Guardar sesión | `browser.session.save` | 📋 Planificada (Fase 2) |
| Restaurar sesión | `browser.session.restore` | 📋 Planificada (Fase 2) |
| Ejecución con AI (lenguaje natural) | `browser.ai.execute` | 📋 Planificada (Fase 3) |

---

## Arquitectura

```
David (Notion/Telegram)
    │
    ▼
Dispatcher (VPS) ──── Redis Queue
    │
    │  Encola tareas browser.*
    ▼
Worker VM (FastAPI :8088)
    │
    ├── browser.navigate / click / fill / screenshot / ...
    │       │
    │       ▼
    │   BrowserManager (Singleton)
    │       ├── Playwright Instance
    │       ├── Chromium (headed o headless)
    │       ├── Persistent Context (cookies/sesión)
    │       └── Page Pool (multi-tab)
    │
    └── browser.ai.execute (Fase 3)
            └── browser-use Agent + LLM
```

El Worker de la VM recibe tareas `browser.*` como cualquier otra tarea (ping, windows.*, etc.) y las ejecuta usando un BrowserManager singleton que mantiene el navegador vivo entre llamadas.

---

## Uso desde Rick en la VM

### Navegación básica

Rick puede navegar a una URL y tomar una captura:

```json
{
  "task": "browser.navigate",
  "params": {
    "url": "https://acc.autodesk.com/dashboard",
    "wait_until": "networkidle"
  }
}
```

Respuesta:
```json
{
  "page_id": "page_1",
  "title": "ACC Dashboard",
  "url": "https://acc.autodesk.com/dashboard"
}
```

### Captura de pantalla

```json
{
  "task": "browser.screenshot",
  "params": {
    "full_page": true,
    "path": "G:\\Mi unidad\\Rick-David\\capturas\\dashboard.png"
  }
}
```

### Clic en un elemento

```json
{
  "task": "browser.click",
  "params": {
    "selector": "button:has-text('Exportar')"
  }
}
```

### Rellenar un formulario

```json
{
  "task": "browser.fill",
  "params": {
    "selector": "input[name='search']",
    "value": "licitaciones BIM 2026"
  }
}
```

### Leer contenido de la página

```json
{
  "task": "browser.read_page",
  "params": {
    "selector": "table.resultados"
  }
}
```

Respuesta:
```json
{
  "text": "Título | Organismo | Fecha...",
  "title": "Resultados de búsqueda",
  "url": "https://www.mercadopublico.cl/..."
}
```

### Multi-tab (Fase 2)

```json
{
  "task": "browser.tabs.open",
  "params": {
    "url": "https://gmail.com"
  }
}
```

```json
{
  "task": "browser.tabs.list",
  "params": {}
}
```

Respuesta:
```json
{
  "tabs": [
    {"page_id": "page_1", "title": "ACC Dashboard", "url": "https://acc.autodesk.com/dashboard"},
    {"page_id": "page_2", "title": "Gmail", "url": "https://gmail.com"}
  ]
}
```

### Ejecución con AI (Fase 3)

Instrucciones en lenguaje natural que browser-use traduce a acciones:

```json
{
  "task": "browser.ai.execute",
  "params": {
    "instruction": "Ir a Mercado Público, buscar licitaciones de BIM, extraer las primeras 5 con título, organismo y fecha de cierre"
  }
}
```

---

## Sesiones persistentes

El BrowserManager usa **Playwright Persistent Context** para mantener cookies, localStorage y sesiones entre ejecuciones. Rick puede "loguearse una vez" en un sitio y las siguientes llamadas ya estarán autenticadas.

```json
{
  "task": "browser.session.save",
  "params": {"name": "acc-david"}
}
```

```json
{
  "task": "browser.session.restore",
  "params": {"name": "acc-david"}
}
```

Las sesiones se guardan en `C:\Users\rick\.browser-sessions\` en la VM.

---

## Flujos grabados (Fase 3)

Usando Playwright Codegen o workflow-use, Rick puede grabar acciones del usuario y reproducirlas:

1. **Grabar:** `playwright codegen https://portal.ejemplo.com` genera script Python
2. **Guardar:** El script se guarda como flujo reutilizable
3. **Reproducir:** `browser.flow.replay` ejecuta el flujo guardado

---

## Comparación con Claude in Chrome

| Capacidad | Claude in Chrome | Rick en VM |
|-----------|:----------------:|:----------:|
| Leer páginas | ✅ | ✅ `browser.read_page` |
| Clics y navegación | ✅ | ✅ `browser.navigate`, `browser.click` |
| Múltiples pestañas | ✅ | ✅ `browser.tabs.*` |
| Capturas | ✅ | ✅ `browser.screenshot` |
| Formularios | ✅ | ✅ `browser.fill` |
| Flujos grabados | ✅ | ✅ `browser.flow.*` (Fase 3) |
| Tareas programadas | ✅ | ✅ Scheduled tasks Redis |
| Consola/depuración | ✅ | ✅ `browser.execute` (JS) |
| Integración Desktop | ✅ | ✅ Dispatcher → Worker VM |

---

## Configuración

Variables de entorno en la VM:

| Variable | Default | Descripción |
|----------|---------|-------------|
| `BROWSER_HEADLESS` | `true` | Modo sin ventana (`true`) o con ventana visible (`false`) |
| `BROWSER_USER_DATA_DIR` | `C:\Users\rick\.browser-sessions\default` | Directorio de sesión persistente |
| `BROWSER_ALLOW_JS_EXEC` | `false` | Habilitar ejecución de JavaScript arbitrario |
| `BROWSER_TIMEOUT` | `30000` | Timeout por operación (ms) |
| `BROWSER_MAX_TABS` | `5` | Número máximo de pestañas simultáneas |

---

## Prerequisitos en la VM

```bash
pip install playwright
playwright install chromium --with-deps

# Fase 3 (opcional)
pip install browser-use workflow-use
```

---

## Notas

- El BrowserManager es un singleton: se inicializa al primer uso y se mantiene vivo entre tareas.
- Si el navegador se cuelga o no responde, el health monitor del Worker lo reinicia.
- Las capturas se guardan en la ruta especificada o se devuelven como base64 en la respuesta.
- Para sitios con CAPTCHA, Rick pausa y notifica a David para resolución manual.
- El modo headed (`BROWSER_HEADLESS=false`) es útil para debug y para flujos que necesitan ventana visible.
