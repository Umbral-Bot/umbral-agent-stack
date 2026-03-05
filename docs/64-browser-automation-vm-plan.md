# 64 — Plan de Automatización de Navegador en la VM (tipo Claude in Chrome)

> **Fecha:** 2026-03-05  
> **Autor:** Cursor Agent Cloud (R16)  
> **Estado:** Borrador — listo para revisión  
> **Skill asociado:** `openclaw/workspace-templates/skills/browser-automation-vm/SKILL.md`

---

## Resumen ejecutivo

Este documento define el plan para dotar a **Rick** de capacidades de automatización de navegador web en la VM Windows del Umbral Agent Stack, equivalentes a las que ofrece **Claude in Chrome**: navegar, hacer clic, rellenar formularios, tomar capturas de pantalla, gestionar múltiples pestañas y opcionalmente grabar y reproducir flujos. La recomendación principal es construir sobre **Playwright Python** (ya presente como skill) como motor central, encapsulado en un nuevo módulo `browser.*` del Worker de la VM, orquestado desde el Dispatcher del VPS mediante tareas encoladas en Redis. Opcionalmente, se integra **browser-use** (79k⭐ en GitHub) como capa de orquestación inteligente con LLM para tareas ambiguas o complejas.

---

## 1. Referencia: qué hace Claude in Chrome

Según la [documentación oficial de Claude in Chrome](https://support.claude.com/en/articles/12012173-getting-started-with-claude-in-chrome), las capacidades son:

| Capacidad | Descripción | ¿Objetivo en VM? |
|-----------|-------------|-----------------|
| Leer páginas | Ver texto, DOM y estructura de la página | ✅ Sí |
| Clics y navegación | Hacer clic en botones, enlaces, navegar URLs | ✅ Sí |
| Múltiples pestañas | Abrir, cerrar, cambiar de pestaña, agrupar | ✅ Sí |
| Capturas de pantalla | Screenshots de regiones o páginas completas | ✅ Sí |
| Rellenar formularios | Llenar campos y enviar formularios | ✅ Sí |
| Flujos grabados | Grabar pasos del usuario y repetirlos | ✅ Fase 3 |
| Tareas programadas | Ejecutar acciones en horarios (diario, etc.) | ✅ Ya existe en stack |
| Consola / depuración | Leer logs de consola, peticiones de red, DOM | ⚠️ Opcional |
| Integración Desktop | Iniciar tareas desde Claude Desktop | ➖ Fuera de scope |
| Sesión autenticada | Reutilizar cookies y login existentes | ✅ Sí (storage_state) |

---

## 2. Investigación exhaustiva

### 2.1 Librerías Python (orden de prioridad)

#### Playwright Python ⭐⭐⭐⭐⭐ — **Recomendado principal**

- **PyPI:** `playwright` · **GitHub:** [microsoft/playwright-python](https://github.com/microsoft/playwright-python) (12k⭐)
- **Docs:** https://playwright.dev/python/
- **Capacidades:** Navegación, clics, formularios, capturas, multi-tab, sesiones persistentes, descarga de archivos, intercepción de red, video recording, modo headless y headed.
- **Instalación en VM:** `pip install playwright && playwright install chromium`
- **Windows:** Funciona nativamente en Windows 11. **No usar WSL2** (rendimiento degradado).
- **Integración Worker:** API sincrónica y asincrónica; compatible con FastAPI via `asyncio`.
- **Sesiones persistentes:** `launch_persistent_context(userDataDir=...)` o `context.storage_state(path="state.json")` para reutilizar cookies/login.
- **Licencia:** Apache 2.0. Mantenimiento activo (Microsoft).

#### browser-use ⭐⭐⭐⭐ — **Capa de orquestación IA opcional**

- **PyPI:** `browser-use` · **GitHub:** [browser-use/browser-use](https://github.com/browser-use/browser-use) (79k⭐)
- **Docs:** https://docs.browser-use.com
- **Capacidades:** Agente IA sobre Playwright. Recibe instrucciones en lenguaje natural (`"Ir a Google y buscar X, luego descargar el primer PDF"`). Multi-LLM: OpenAI, Anthropic, Gemini. 3.5M descargas/mes.
- **Windows:** Requiere Python ≥ 3.11 (disponible en VM). Instalación simple.
- **Uso ideal:** Para tareas complejas o ambiguas donde el LLM debe decidir el siguiente paso. Para tareas deterministas usar Playwright directo.
- **Licencia:** MIT.

#### workflow-use ⭐⭐⭐ — **Grabación y replay**

- **PyPI:** `workflow-use` · **GitHub:** [browser-use/workflow-use](https://github.com/browser-use/workflow-use) (3.9k⭐)
- **Capacidades:** Graba flujos del usuario → genera YAML con semántica → replay determinista 10-100x más rápido que el agente IA. Estrategias de fallback para selectores rotos.
- **Uso ideal:** Flujos repetitivos que se graban una vez y se ejecutan muchas veces (ej. extraer datos de portal diariamente).
- **Licencia:** AGPL-3.0. Atención a la licencia copyleft si se integra en stack comercial.

#### Selenium WebDriver ⭐⭐⭐ — **Alternativa legacy**

- **PyPI:** `selenium` · **GitHub:** [seleniumhq/selenium](https://github.com/SeleniumHQ/selenium) (30k⭐)
- **Capacidades:** Navegación, clics, formularios, multi-tab, capturas básicas.
- **Pros:** Ecosistema maduro, soporte para IE/Edge legacy, bien documentado.
- **Contras:** Más lento, más verboso, requiere `WebDriverWait` manual, menos estable que Playwright en SPAs.
- **Recomendación:** Solo si existe código Selenium legado que reutilizar. Para proyectos nuevos, usar Playwright.

#### Pyppeteer ⭐⭐ — **No recomendado**

- **PyPI:** `pyppeteer` · **GitHub:** [pyppeteer/pyppeteer](https://github.com/pyppeteer/pyppeteer) (9k⭐, poco activo)
- **Capacidades:** Wrapping de Puppeteer (Node) en Python. Solo Chromium.
- **Contras:** Mantenimiento errático, API async-only, no oficial (port comunitario). **Playwright lo supera en todos los aspectos.**

#### Splinter ⭐⭐ — **No recomendado para VM**

- **PyPI:** `splinter` · Abstracción sobre Selenium.
- **Contras:** Agrega una capa de abstracción sin ventajas claras. Mantenimiento lento.

#### MechanicalSoup / Requests + BeautifulSoup ⭐ — **Solo lectura estática**

- **PyPI:** `mechanicalsoup`, `requests`, `beautifulsoup4`
- **Limitación crítica:** No ejecuta JavaScript. No sirve para SPAs, clics reales, formularios dinámicos ni capturas.
- **Uso válido:** Scraping de páginas HTML estáticas simples o llamadas a APIs REST.

---

### 2.2 Repositorios GitHub relevantes

| Repo | ⭐ | Lenguaje | Descripción | Enlace |
|------|----|----------|-------------|--------|
| browser-use/browser-use | 79k | Python | Agente IA que controla navegador con Playwright + LLM | [GitHub](https://github.com/browser-use/browser-use) |
| browser-use/workflow-use | 3.9k | Python | Record & replay de flujos (RPA 2.0) sobre browser-use | [GitHub](https://github.com/browser-use/workflow-use) |
| microsoft/playwright-python | 12k | Python | Binding oficial Python de Playwright | [GitHub](https://github.com/microsoft/playwright-python) |
| mbroton/browsy | ~200 | Python | Playwright-as-a-service via FastAPI + workers | [GitHub](https://github.com/mbroton/browsy) |
| mbroton/playwright-distributed | ~100 | Python | Playwright distribuido con colas | [GitHub](https://github.com/mbroton/playwright-distributed) |
| browserless/browserless | 7k | Node.js | Browser automation service self-hosted (REST API) | [GitHub](https://github.com/browserless/browserless) |
| apify/crawlee-python | 4k | Python | Web scraping + browser automation (Playwright/Puppeteer) | [GitHub](https://github.com/apify/crawlee-python) |

---

### 2.3 Herramientas no-Python (referencia comparativa)

| Herramienta | Lenguaje | Descripción | Relevancia para VM |
|-------------|----------|-------------|-------------------|
| Playwright (Node.js) | TypeScript/JS | Motor original de Microsoft | ⚠️ Usar binding Python |
| Puppeteer | Node.js | Chrome/Chromium solo, Google | ⚠️ Sin binding Python oficial |
| Selenium (Java/C#) | Múltiples | Estándar legacy, multiplataforma | ⚠️ Usar binding Python |
| Browserless | Node.js | Self-hosted BaaS, REST API | ✅ Invocable desde Python via HTTP |
| Apify Cloud | SaaS | Browser automation as a service | ⚠️ Depende de cloud externo |
| Power Automate Desktop | Windows | RPA visual en VM (ya existe) | ✅ Para flujos grabados simples |

---

## 3. Matriz comparativa

| Herramienta | Lenguaje | Navegar | Clics | Formularios | Capturas | Multi-tab | Grabación | Sesión persistente | VM Windows | Headless | Enlace | Observaciones |
|-------------|----------|---------|-------|-------------|----------|-----------|-----------|-------------------|------------|----------|--------|---------------|
| **Playwright Python** | Python | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (video) | ✅ (storage_state) | ✅ Nativo | ✅/headed | [PyPI](https://pypi.org/project/playwright/) | **Recomendado.** Apache 2.0, Microsoft, activo |
| **browser-use** | Python | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (GIF) | ✅ | ✅ | ✅/headed | [PyPI](https://pypi.org/project/browser-use/) | Requiere LLM API key. MIT |
| **workflow-use** | Python | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ record+replay | ✅ | ✅ | ✅ | [PyPI](https://pypi.org/project/workflow-use/) | AGPL-3.0 — revisar licencia |
| **Selenium** | Python | ✅ | ✅ | ✅ | ⚠️ básico | ✅ | ❌ | ✅ (cookies) | ✅ | ✅/headed | [PyPI](https://pypi.org/project/selenium/) | Legacy, más lento. Apache 2.0 |
| **Pyppeteer** | Python | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ⚠️ | ✅ | ✅ | [PyPI](https://pypi.org/project/pyppeteer/) | Poco mantenido. MIT |
| **Splinter** | Python | ✅ | ✅ | ✅ | ❌ | ⚠️ | ❌ | ⚠️ | ✅ | ⚠️ | [PyPI](https://pypi.org/project/splinter/) | Abstracción sobre Selenium. BSD |
| **MechanicalSoup** | Python | ✅ | ⚠️ | ⚠️ | ❌ | ❌ | ❌ | ✅ (cookies) | ✅ | N/A | [PyPI](https://pypi.org/project/MechanicalSoup/) | Sin JS. Solo HTML estático. MIT |
| **Browserless** | Node.js | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (Docker) | ✅ | [Docs](https://docs.browserless.io/) | Self-hosted vía Docker. Complejo setup |
| **PAD (Power Automate)** | Windows/GUI | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ recorder | ✅ | ✅ Solo VM | headed only | [Docs](https://docs.microsoft.com/power-automate/desktop-flows/) | Ya existe en VM. Sin API programática |

---

## 4. Plan de implementación

### 4.1 Arquitectura de integración

El diseño sigue el patrón del stack existente: **Dispatcher (VPS) → Redis → Worker (VM) → módulo `browser.*`**.

```
┌──────────────────────────────────────────────────────────────────┐
│  Control Plane (VPS — 24/7)                                      │
│                                                                  │
│  Rick (meta-orquestador)                                         │
│    │                                                             │
│    ├── Clasifica tarea: browser.navigate / browser.click / ...   │
│    │                                                             │
│    └── Dispatcher ──enqueue──→ Redis (cola) ──Tailscale──┐       │
└─────────────────────────────────────────────────────────-│───────┘
                                                           │
┌──────────────────────────────────────────────────────────▼───────┐
│  Execution Plane (VM Windows — cuando está encendida)            │
│                                                                  │
│  Worker FastAPI :8088                                            │
│    │                                                             │
│    ├── handle_browser_navigate(url, wait_for)                    │
│    ├── handle_browser_click(selector, strategy)                  │
│    ├── handle_browser_fill(fields: {selector: value})            │
│    ├── handle_browser_screenshot(path, full_page, region)        │
│    ├── handle_browser_run_flow(flow_id, params)   [Fase 3]       │
│    └── handle_browser_eval(js_code)               [opcional]     │
│         │                                                        │
│         └── Playwright Python (Chromium headless/headed)         │
│              │                                                   │
│              └── Chromium/Chrome instalado en VM                 │
└──────────────────────────────────────────────────────────────────┘
         │
         ▼ resultado (screenshot base64, texto, status)
   Redis → Dispatcher → Rick → Notion/Telegram/callback_url
```

**Decisiones arquitectónicas:**

1. **Playwright Python en la VM** — No en el VPS. La VM ya tiene Chrome instalado; el VPS es Linux sin display y el foco es delegar la ejecución pesada.
2. **Nuevas tareas `browser.*` en el Worker** — Siguiendo el patrón de `windows.*`, `notion.*`, etc. Cada acción es un handler atómico.
3. **Sesión compartida opcional** — Un `BrowserContext` persistente que el Worker puede reusar entre tareas (para flujos que requieran login previo).
4. **Screenshots como base64 o path** — El resultado de `browser.screenshot` devuelve la imagen en base64 (inline) o la guarda en una ruta de la VM accesible vía `windows.fs.*`.
5. **browser-use como handler opcional** — `browser.agent_run` para instrucciones en lenguaje natural. Requiere LLM API key ya disponible en el stack.

---

### 4.2 Flujo mínimo completo

```
1. David escribe en Notion Control Room:
   "Rick, captura la página https://acc.autodesk.com/projects/X/dashboard"

2. Rick (OpenClaw en VPS) clasifica:
   task_type = "browser.screenshot"
   target = "VM Worker"

3. Dispatcher encola en Redis:
   {
     "task": "browser.screenshot",
     "input": {
       "url": "https://acc.autodesk.com/projects/X/dashboard",
       "full_page": true,
       "session_id": "acc-session"  ← reutiliza login guardado
     },
     "callback_url": "https://vps/webhook/task-done"
   }

4. Worker VM desencola (poll Redis o HTTP push):
   → handle_browser_screenshot(input)
   → Playwright abre Chromium con storage_state="sessions/acc-session.json"
   → Navega a la URL
   → Espera networkidle
   → Toma screenshot (full_page=True)
   → Guarda en G:\Rick-Data\screenshots\{task_id}.png
   → Retorna {"ok": true, "path": "G:\\...\\{task_id}.png", "base64": "..."}

5. Dispatcher recibe resultado → fire callback_url → Rick postea en Notion:
   "Captura tomada: [adjunta imagen o enlace]"
```

---

### 4.3 Diseño de los handlers `browser.*`

Todos los handlers residirán en `worker/tasks/browser.py` en la VM:

```python
# worker/tasks/browser.py — esquema (pseudocódigo)

BROWSER_HANDLERS = {
    "browser.navigate": handle_browser_navigate,
    "browser.click":    handle_browser_click,
    "browser.fill":     handle_browser_fill,
    "browser.screenshot": handle_browser_screenshot,
    "browser.get_text": handle_browser_get_text,
    "browser.new_tab":  handle_browser_new_tab,
    "browser.close_tab": handle_browser_close_tab,
    "browser.eval":     handle_browser_eval,
    "browser.agent_run": handle_browser_agent_run,  # Fase 2 (browser-use)
    "browser.run_flow": handle_browser_run_flow,    # Fase 3 (workflow-use)
}
```

**Contrato de entrada común:**

```json
{
  "session_id": "opcional — ID de sesión reutilizable (default: efímera)",
  "headless": true,
  "timeout_ms": 30000,
  "url": "...",
  "selector": "...",
  "strategy": "css | text | role | placeholder | xpath"
}
```

**Contrato de salida común:**

```json
{
  "ok": true,
  "task_id": "...",
  "data": {...},
  "screenshot_base64": "...",
  "error": null
}
```

---

### 4.4 Seguridad y permisos

| Riesgo | Mitigación |
|--------|------------|
| Acceso a dominios arbitrarios | `tool_policy.yaml` con `browser_allowlist_domains: [...]`; bloquear por defecto |
| Credenciales en input | Usar `windows.fs.read_text` para leer secrets desde archivo local; jamás en el envelope |
| Inyección de JS via `browser.eval` | Validar/sanitizar; solo habilitado si `BROWSER_EVAL_ENABLED=true` |
| Screenshots de datos sensibles | Guardar localmente en VM; no incluir base64 en logs de Redis |
| Detección de bots (CAPTCHA) | `headless=False` + `slow_mo=100` como fallback; no bypass automático |
| Sesión compartida entre tareas | Usar `session_id` como aislamiento; limpiar sesiones antiguas via cron |

---

### 4.5 Condicionantes técnicos

| Condicionante | Detalle |
|---------------|---------|
| **¿Solo VM?** | Sí. El VPS es Linux sin display físico; Playwright headless es posible pero la VM tiene Chrome real instalado y es el Execution Plane designado |
| **¿Headless o headed?** | Headless por defecto (más rápido, sin pantalla). Headed disponible para debug o cuando sitios detectan headless |
| **¿Sesiones persistentes?** | Sí. Via `storage_state` de Playwright (JSON con cookies/localStorage). Se guardan en `G:\Rick-Data\sessions\` |
| **¿VM siempre encendida?** | No. La VM puede estar apagada. El Worker tiene health check; el Dispatcher espera o notifica `VM_OFFLINE` |
| **Python version** | Python 3.11+ requerido (ya disponible en VM) |
| **Chromium vs Chrome** | Se puede usar el Chromium bundled de Playwright O el Chrome instalado en la VM. Recomendado: Chromium bundled para mayor compatibilidad |

---

## 5. Fases de implementación

### Fase 1 — MVP: navegar, clic, captura (1-2 días)

**Objetivo:** Rick puede navegar a una URL, hacer un clic y tomar un screenshot.

**Entregables:**
- [ ] `worker/tasks/browser.py` con handlers: `browser.navigate`, `browser.screenshot`, `browser.click`
- [ ] Registro en `worker/app.py`
- [ ] `playwright install chromium` en la VM
- [ ] Test unitario básico (mock Playwright)
- [ ] Test E2E: tarea `browser.screenshot` desde Notion → captura → resultado en Notion

**Dependencias:** Playwright instalado en VM (Python 3.11+).

---

### Fase 2 — Formularios, multi-tab y sesiones (3-5 días)

**Objetivo:** Rick puede rellenar formularios, gestionar pestañas y reutilizar sesiones de login.

**Entregables:**
- [ ] Handler `browser.fill` (rellenar campos por selector)
- [ ] Handler `browser.get_text` (extraer texto de elemento o página)
- [ ] Handler `browser.new_tab` / `browser.close_tab`
- [ ] Handler `browser.eval` (con validación; solo si habilitado en policy)
- [ ] Sistema de sesiones persistentes: `browser.session_save` / `browser.session_load`
- [ ] `tool_policy.yaml` actualizado con `browser_allowlist_domains`
- [ ] Tests unitarios + test E2E de flujo con login

**Dependencias:** Fase 1 completa.

---

### Fase 3 — Flujos grabados, agente IA y tareas programadas (5-10 días)

**Objetivo:** Rick puede grabar flujos, reproducirlos determinísticamente y ejecutar tareas de navegación en lenguaje natural.

**Entregables:**
- [ ] Handler `browser.agent_run` usando `browser-use` + LLM ya disponible en stack
- [ ] Handler `browser.run_flow` usando `workflow-use` (grabar → YAML → replay)
- [ ] UI o CLI mínima para grabar flujos (David graba desde VM, flujo se guarda en `G:\Rick-Data\flows\`)
- [ ] Scheduler: tareas `browser.*` disparables desde el scheduler de Redis (ya existe en stack)
- [ ] Documentación de flujos en Notion

**Dependencias:** Fase 2 completa; `browser-use` y `workflow-use` instalados; LLM API key disponible.

---

## 6. Recomendación de stack

**Stack concreto recomendado:**

| Componente | Herramienta | Versión | Justificación |
|------------|-------------|---------|---------------|
| Motor de automatización | **Playwright Python** | `>=1.50` | Más rápido, más estable, API moderna, mantenido por Microsoft, ya skill existente |
| Capa de orquestación IA | **browser-use** | `>=0.12` | Permite instrucciones en lenguaje natural; reutiliza LLMs ya integrados en el stack |
| Grabación y replay | **workflow-use** | `>=0.1` | Record & replay determinista con fallback semántico; 10-100x más rápido que IA |
| Browser | **Chromium** (bundled Playwright) | auto | Sin dependencia de Chrome instalado; reproducible |
| Sesiones | `storage_state` de Playwright | - | JSON simple, no requiere DB; rotación via cron |
| Integración | Handler `browser.*` en Worker | - | Sigue patrón existente del stack |
| Scheduling | Redis sorted set (ya existe) | - | Sin nueva infraestructura |

**Instalación en VM:**

```bash
# En la VM (Python 3.11+)
pip install playwright browser-use workflow-use
playwright install chromium

# Variables de entorno (ya disponibles en stack)
# WORKER_TOKEN, OPENAI_API_KEY o GEMINI_API_KEY (para browser-use)
```

---

## 7. Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| Sitios con anti-bot (Cloudflare, CAPTCHA) | Alta | Medio | `headless=False` + `slow_mo=100`; stealth plugins; no garantiza bypass |
| Selectores rotos tras actualización de sitio | Alta | Medio | Usar selectores semánticos (`get_by_text`, `get_by_role`); workflow-use con 7 fallbacks |
| VM apagada cuando llega tarea | Media | Medio | Worker health check; Dispatcher notifica `VM_OFFLINE`; retry con backoff |
| Sesión expirada (cookies vencidas) | Media | Bajo | Re-login automático con credenciales en `G:\Rick-Data\secrets\`; alertar si falla |
| Rendimiento degradado en WSL2 | Baja | Bajo | **No usar WSL2.** Ejecutar Playwright directamente en Windows |
| Licencia AGPL de workflow-use | Baja | Alto | Evaluar antes de distribuir. Alternativa: implementar replay propio sobre Playwright |
| Abuso de `browser.eval` (inyección JS) | Baja | Alto | Deshabilitar por defecto; `BROWSER_EVAL_ENABLED=false` en producción |
| Instalación inicial Chromium (~200MB) | Baja | Bajo | Tarea única; documentar en runbook VM |
| Detección de automatización por login SSO | Media | Medio | Usar sesión headed para login inicial; guardar `storage_state`; no repetir login |

---

## 8. Integración con el stack actual

### Relación con handlers existentes

| Handler existente | Relación con `browser.*` |
|-------------------|--------------------------|
| `windows.pad.run_flow` | Complementario: PAD para flujos GUI no-web; `browser.*` para web |
| `windows.fs.*` | `browser.screenshot` puede guardar imagen via `windows.fs.write_bin` |
| `research.web` (Tavily) | Complementario: Tavily para búsqueda rápida; `browser.*` para interacción real con páginas |
| `composite.research_report` | `browser.*` puede enriquecer reportes con capturas o datos de portales con login |
| Scheduler (Redis sorted set) | `browser.*` tasks son schedulables sin cambios adicionales |
| `llm.generate` | `browser.agent_run` usa LLM internamente vía browser-use |

### Ejemplo de tarea completa (Fase 1, MVP)

```python
# Ejemplo de tarea encolada por Rick para el Worker de la VM
task_envelope = {
    "task": "browser.screenshot",
    "input": {
        "url": "https://www.mercadopublico.cl/Licitacion?keyword=BIM",
        "full_page": True,
        "wait_for": "networkidle",
        "headless": True,
        "session_id": None  # sesión efímera
    },
    "callback_url": "https://vps.umbral.cl/webhook/task-done"
}
```

---

## Referencias

- [Playwright Python Docs](https://playwright.dev/python/)
- [browser-use GitHub](https://github.com/browser-use/browser-use)
- [workflow-use GitHub](https://github.com/browser-use/workflow-use)
- [Claude in Chrome — Soporte oficial](https://support.claude.com/en/articles/12012173-getting-started-with-claude-in-chrome)
- [Browserless Docs](https://docs.browserless.io/)
- [Selenium vs Playwright 2026 — Apify](https://use-apify.com/blog/selenium-vs-playwright-vs-puppeteer-2026)
- [Playwright Persistent Context — BrowserStack](https://www.browserstack.com/guide/playwright-persistent-context)
- Skill relacionado: `openclaw/workspace-templates/skills/playwright-python/SKILL.md`
- Skill dedicado: `openclaw/workspace-templates/skills/browser-automation-vm/SKILL.md`
- Arquitectura: `docs/01-architecture-v2.3.md`
- Tool Policy: `config/tool_policy.yaml`
