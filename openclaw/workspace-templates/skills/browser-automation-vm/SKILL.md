---
name: browser-automation-vm
description: >-
  Automatización de navegador web en la VM de Rick (tipo Claude in Chrome).
  Permite navegar URLs, hacer clics, rellenar formularios, tomar capturas de
  pantalla, gestionar múltiples pestañas y reproducir flujos grabados usando
  la VM Windows como plano de ejecución. Orquestado desde el Dispatcher del VPS
  via tareas browser.* encoladas en Redis.
  Use when "navegar web desde Rick", "captura de pantalla de portal",
  "rellenar formulario automático en VM", "abrir pestaña nueva",
  "automatización navegador VM", "clic en botón web", "extraer datos de portal
  con login", "grabar y repetir flujo web", "browser automation", "Rick navega".
metadata:
  openclaw:
    emoji: "🌐"
    requires:
      env:
        - WORKER_TOKEN
      vm:
        - playwright (pip install playwright && playwright install chromium)
        - Python 3.11+
      optional:
        - browser-use (pip install browser-use) — para tareas en lenguaje natural
        - workflow-use (pip install workflow-use) — para record & replay
---

# Browser Automation en la VM — Habilidad de Rick (tipo Claude in Chrome)

Rick puede controlar un navegador web en la VM Windows como lo hace Claude in Chrome: navegar, hacer clics, rellenar formularios, tomar capturas y gestionar pestañas. La VM actúa como **Execution Plane**; el VPS (donde corre Rick) orquesta via tareas `browser.*` encoladas en Redis.

**Plan completo:** [`docs/64-browser-automation-vm-plan.md`](../../../../../docs/64-browser-automation-vm-plan.md)  
**Skill base:** [`skills/playwright-python/SKILL.md`](../playwright-python/SKILL.md)

---

## ¿Cuándo usar esta habilidad?

Usar `browser.*` cuando Rick necesita:

- Navegar a una URL y extraer información de una página que requiere JavaScript
- Hacer clic en botones, enlaces o menús de una web
- Rellenar y enviar formularios (login, búsqueda, registro)
- Tomar capturas de pantalla de dashboards, portales o páginas específicas
- Gestionar múltiples pestañas del navegador
- Reutilizar una sesión de login ya guardada (cookies/storage_state)
- Grabar un flujo y repetirlo determinísticamente (Fase 3)
- Ejecutar una tarea de navegación en lenguaje natural (via browser-use + LLM)

**No usar** para:
- Páginas HTML estáticas sin JS → usar `research.web` (Tavily) o requests + BeautifulSoup
- Automatización de escritorio (no-web) → usar `windows.pad.run_flow`
- APIs REST públicas → usar `research.web` o llamada HTTP directa

---

## Arquitectura de la habilidad

```
VPS (Rick / Dispatcher)
  │
  ├─ Rick clasifica tarea → "browser.screenshot", "browser.click", etc.
  │
  └─ Dispatcher encola en Redis → Tailscale → VM Worker :8088
                                                    │
                                              worker/tasks/browser.py
                                                    │
                                              Playwright Python
                                                    │
                                              Chromium (headless/headed)
                                                    │
                                              Web → resultado (texto, imagen)
                                                    │
                                              callback_url → Rick → Notion
```

---

## Tareas Worker disponibles (Fase 1 — MVP)

### `browser.navigate`

Navega a una URL y espera que la página cargue.

```json
{
  "task": "browser.navigate",
  "input": {
    "url": "https://www.ejemplo.com/dashboard",
    "wait_for": "networkidle",
    "headless": true,
    "session_id": "mi-sesion"
  }
}
```

**Respuesta:**
```json
{
  "ok": true,
  "url": "https://www.ejemplo.com/dashboard",
  "title": "Dashboard — Ejemplo",
  "session_id": "mi-sesion"
}
```

---

### `browser.screenshot`

Toma una captura de pantalla de la página actual o de un elemento específico.

```json
{
  "task": "browser.screenshot",
  "input": {
    "url": "https://acc.autodesk.com/projects/XYZ/dashboard",
    "full_page": true,
    "headless": true,
    "session_id": "acc-session",
    "output_path": "G:\\Rick-Data\\screenshots\\acc-dashboard.png"
  }
}
```

**Respuesta:**
```json
{
  "ok": true,
  "path": "G:\\Rick-Data\\screenshots\\acc-dashboard.png",
  "base64": "iVBORw0KGgoAAAANSUhEUg..."
}
```

---

### `browser.click`

Hace clic en un elemento de la página.

```json
{
  "task": "browser.click",
  "input": {
    "session_id": "mi-sesion",
    "selector": "button[type='submit']",
    "strategy": "css",
    "timeout_ms": 10000
  }
}
```

**Strategies disponibles:** `css`, `text`, `role`, `placeholder`, `xpath`

---

### `browser.fill`

Rellena campos de un formulario.

```json
{
  "task": "browser.fill",
  "input": {
    "session_id": "mi-sesion",
    "fields": {
      "input[name='search']": "BIM coordinación",
      "select[name='category']": "Licitaciones"
    }
  }
}
```

---

### `browser.get_text`

Extrae texto de un elemento o de toda la página.

```json
{
  "task": "browser.get_text",
  "input": {
    "session_id": "mi-sesion",
    "selector": ".precio-total",
    "all": false
  }
}
```

**Respuesta:**
```json
{
  "ok": true,
  "text": "$1.250.000 CLP"
}
```

---

## Tareas Worker disponibles (Fase 2 — Multi-tab y sesiones)

### `browser.new_tab`

Abre una nueva pestaña y navega a una URL.

```json
{
  "task": "browser.new_tab",
  "input": {
    "session_id": "mi-sesion",
    "url": "https://www.mercadopublico.cl"
  }
}
```

### `browser.session_save`

Guarda el estado de sesión actual (cookies, localStorage) para reutilizar en futuras tareas.

```json
{
  "task": "browser.session_save",
  "input": {
    "session_id": "acc-session",
    "path": "G:\\Rick-Data\\sessions\\acc-session.json"
  }
}
```

### `browser.session_load`

Carga una sesión guardada previamente (reutiliza login).

```json
{
  "task": "browser.session_load",
  "input": {
    "session_id": "acc-session",
    "path": "G:\\Rick-Data\\sessions\\acc-session.json"
  }
}
```

---

## Tareas Worker disponibles (Fase 3 — Agente IA y flujos)

### `browser.agent_run`

Ejecuta una instrucción en lenguaje natural usando **browser-use** + LLM.

```json
{
  "task": "browser.agent_run",
  "input": {
    "instruction": "Ir a mercadopublico.cl, buscar licitaciones de BIM, extraer los títulos y montos de las primeras 5 y devolverlos como lista",
    "llm": "gemini-2.0-flash",
    "headless": true,
    "max_steps": 15
  }
}
```

**Respuesta:**
```json
{
  "ok": true,
  "result": "1. Modelado BIM Edificio Municipal — $45M\n2. ...",
  "steps": 8
}
```

---

### `browser.run_flow`

Ejecuta un flujo grabado con **workflow-use** (replay determinista).

```json
{
  "task": "browser.run_flow",
  "input": {
    "flow_id": "licitaciones-bim-diario",
    "flow_path": "G:\\Rick-Data\\flows\\licitaciones-bim.yaml",
    "params": {
      "keyword": "BIM",
      "fecha_desde": "2026-03-01"
    }
  }
}
```

---

## Flujo completo de ejemplo — Captura ACC Dashboard

```
1. David en Notion: "Rick, captura el dashboard del proyecto X en ACC"

2. Rick encola (Dispatcher → Redis):
   {
     "task": "browser.screenshot",
     "input": {
       "url": "https://acc.autodesk.com/projects/PROJ_ID/dashboard",
       "session_id": "acc-autodesk",
       "full_page": true
     },
     "callback_url": "https://vps.umbral.cl/webhook/done"
   }

3. Worker VM ejecuta Playwright:
   - Carga session acc-autodesk (storage_state.json con login guardado)
   - Navega al dashboard
   - Espera networkidle
   - Toma screenshot full_page
   - Guarda en G:\Rick-Data\screenshots\acc-PROJ_ID-{ts}.png

4. Resultado → callback_url → Rick → Notion:
   "Captura lista: G:\Rick-Data\screenshots\acc-PROJ_ID-20260305-143022.png"
   [imagen embebida en Notion via windows.fs + notion.upload]
```

---

## Instalación en la VM

```bash
# 1. Instalar Playwright
pip install playwright
playwright install chromium

# 2. (Opcional — Fase 3) Instalar browser-use para instrucciones en lenguaje natural
pip install browser-use

# 3. (Opcional — Fase 3) Instalar workflow-use para record & replay
pip install workflow-use

# 4. Verificar instalación
python -c "from playwright.sync_api import sync_playwright; print('OK')"
```

---

## Configuración en tool_policy.yaml

```yaml
# config/tool_policy.yaml
browser:
  enabled: true
  headless_default: true
  eval_enabled: false        # browser.eval deshabilitado por seguridad
  allowlist_domains:
    - "*.autodesk.com"
    - "mercadopublico.cl"
    - "*.notion.so"
    - "*.google.com"
  sessions_dir: "G:\\Rick-Data\\sessions"
  screenshots_dir: "G:\\Rick-Data\\screenshots"
  flows_dir: "G:\\Rick-Data\\flows"
  timeout_default_ms: 30000
  max_steps_agent: 20        # límite de pasos para browser.agent_run
```

---

## Seguridad

- **Dominios permitidos:** Solo los definidos en `allowlist_domains` de `tool_policy.yaml`.
- **Credenciales:** Nunca en el TaskEnvelope. Usar `G:\Rick-Data\secrets\` accedido via `windows.fs.read_text`.
- **Sessions:** Archivos JSON locales en VM. Nunca commitear ni logear.
- **browser.eval:** Deshabilitado por defecto. Requiere `BROWSER_EVAL_ENABLED=true`.
- **Screenshots:** No incluir en logs de Redis; devolver como path o base64 en respuesta.

---

## Relación con otras habilidades

| Skill / Handler | Relación |
|-----------------|----------|
| `playwright-python` | Base técnica; este skill define la integración con el Worker de Rick |
| `windows` / `windows.pad.run_flow` | Complementario: PAD para apps de escritorio; browser.* para web |
| `windows.fs.*` | Guarda/lee screenshots, sessions y flows en la VM |
| `research` | research.web (Tavily) para búsqueda rápida; browser.* para portales con login o interacción |
| `composite` | Flujos compuestos pueden incluir browser.screenshot + llm.generate + notion.add_comment |
| `notion` | Resultados de browser.* se postean en Notion via notion.add_comment o notion.create_page |

---

## Fases de implementación

| Fase | Tareas Worker | Estado |
|------|---------------|--------|
| **Fase 1 — MVP** | `browser.navigate`, `browser.screenshot`, `browser.click` | 📋 Planificado |
| **Fase 2 — Completo** | `browser.fill`, `browser.get_text`, `browser.new_tab`, `browser.session_*` | 📋 Planificado |
| **Fase 3 — IA + Flujos** | `browser.agent_run` (browser-use), `browser.run_flow` (workflow-use) | 📋 Planificado |

Ver plan completo en [`docs/64-browser-automation-vm-plan.md`](../../../../../docs/64-browser-automation-vm-plan.md).
