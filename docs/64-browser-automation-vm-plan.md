# 64 — Plan de Automatización de Navegador en la VM (tipo Claude in Chrome)

> **Fecha:** 2026-03-05
> **Ronda:** 16 — Tarea R16-076
> **Autor:** Cursor Agent Cloud
> **Estado:** Investigación completada — Plan de implementación propuesto

---

## Resumen ejecutivo

Este documento presenta la investigación, comparación y plan de implementación para dotar a Rick de la capacidad de **controlar un navegador web en la VM de Windows**, de forma análoga a lo que ofrece Claude in Chrome: navegar a URLs, hacer clics, rellenar formularios, tomar capturas de pantalla, gestionar múltiples pestañas y, opcionalmente, grabar y reproducir flujos automatizados. La recomendación principal es **Playwright Python** como motor de automatización, integrado al Worker de la VM mediante nuevas tareas `browser.*`, con **browser-use** como capa de inteligencia AI opcional para flujos complejos.

---

## 1. Referencia: qué hace Claude in Chrome

Claude in Chrome (beta, marzo 2026) es una extensión de Chrome que permite a Claude interactuar con el navegador del usuario en tiempo real.

| Capacidad | Descripción | ¿Replicable en VM? |
|-----------|-------------|---------------------|
| Leer páginas | Ver texto, estructura DOM, consola | ✅ Playwright expone DOM completo |
| Clics y navegación | Clic en botones, enlaces, navegación | ✅ Nativo en Playwright |
| Múltiples pestañas | Abrir, cerrar, cambiar pestañas | ✅ Playwright maneja múltiples pages/contexts |
| Capturas de pantalla | Screenshots de regiones o página completa | ✅ `page.screenshot()` nativo |
| Formularios | Rellenar campos, selects, checkboxes | ✅ `page.fill()`, `page.select_option()` |
| Flujos grabados | Grabar pasos y repetirlos | ✅ `playwright codegen` + workflow-use |
| Tareas programadas | Ejecución en horarios | ✅ Crons del stack + scheduled tasks Redis |
| Consola/depuración | Leer logs, peticiones de red, DOM | ✅ CDP events en Playwright |
| Integración Desktop | Iniciar desde Claude Desktop | ✅ Dispatcher → Worker VM → Playwright |

**Diferencia clave:** Claude in Chrome comparte la sesión de Chrome del usuario (cookies, login). En la VM, Playwright puede usar **persistent contexts** para mantener sesiones con cookies entre ejecuciones, logrando un efecto equivalente.

---

## 2. Resultados de la búsqueda

### 2.1 Librerías Python (prioridad)

#### Playwright Python
- **Repo:** [microsoft/playwright-python](https://github.com/microsoft/playwright-python)
- **Estrellas:** 12k+ | **Licencia:** Apache 2.0
- **Descripción:** API Python oficial de Playwright. Controla Chromium, Firefox y WebKit. Soporta headless y headed, auto-waits, network interception, múltiples contexts/pages, persistent contexts (sesiones con cookies), codegen (grabación de scripts), screenshots, PDF generation.
- **Instalación:** `pip install playwright && playwright install chromium`
- **VM Windows:** ✅ Compatible nativo. Funciona en headed (ventana visible) y headless.
- **Async/Sync:** Ambas APIs disponibles.
- **Codegen:** `playwright codegen URL` abre navegador, graba acciones y genera código Python.
- **Performance:** 46% más rápido que Selenium en benchmarks 2026.

#### Selenium Python
- **Repo:** [SeleniumHQ/selenium](https://github.com/SeleniumHQ/selenium)
- **Estrellas:** 31k+ | **Licencia:** Apache 2.0
- **Descripción:** Framework clásico de automatización web. Requiere WebDriver externo (chromedriver). Soporte amplio de navegadores incluyendo legacy.
- **VM Windows:** ✅ Compatible, pero requiere gestión manual de chromedriver.
- **Debilidades:** Más lento que Playwright, no tiene auto-waiting nativo, setup más complejo, sin codegen integrado.

#### Pyppeteer
- **Repo:** [pyppeteer/pyppeteer](https://github.com/pyppeteer/pyppeteer)
- **Estrellas:** 3.9k | **Licencia:** MIT
- **Estado:** ⚠️ **No mantenido** — el propio README recomienda migrar a Playwright.
- **Última actualización significativa:** Junio 2024.
- **Veredicto:** Descartado.

#### Splinter
- **Repo:** [cobrateam/splinter](https://github.com/cobrateam/splinter)
- **Descripción:** Wrapper de alto nivel sobre Selenium/Playwright. Simplifica la API pero agrega una capa de abstracción innecesaria para nuestro caso.
- **Veredicto:** No aporta valor sobre Playwright directo.

#### Mechanize / requests + BeautifulSoup
- **Descripción:** Herramientas HTTP puras sin motor de renderizado.
- **Limitaciones:** No ejecutan JavaScript, no pueden interactuar con SPAs, no toman screenshots.
- **Veredicto:** Solo útiles para scraping estático; no cubren los requisitos de automatización de navegador.

### 2.2 Herramientas AI para navegador

#### browser-use
- **Repo:** [browser-use/browser-use](https://github.com/browser-use/browser-use)
- **Estrellas:** 79k+ | **Licencia:** MIT | **Versión:** 0.12.1 (marzo 2026)
- **Descripción:** Librería Python que permite a agentes AI controlar el navegador. Soporta múltiples LLMs (OpenAI, Gemini, Anthropic). Construido sobre Playwright. El agente interpreta instrucciones en lenguaje natural y las ejecuta como acciones de navegador.
- **VM Windows:** ✅ Compatible (usa Playwright internamente).
- **Valor:** Capa de inteligencia que convierte instrucciones de Rick en acciones de navegador sin necesidad de selectores hardcoded.

#### workflow-use (RPA 2.0)
- **Repo:** [browser-use/workflow-use](https://github.com/browser-use/workflow-use)
- **Estrellas:** 3.9k | **Licencia:** MIT
- **Descripción:** Grabación y reproducción de flujos de navegador. Genera workflows determinísticos con fallback AI. 10-100x más rápido que ejecución LLM pura. Usa selectores semánticos (text matching, ARIA labels) con 7 estrategias de fallback.
- **VM Windows:** ✅ Compatible.
- **Estado:** Early development, no recomendado para producción aún.

#### Skyvern
- **Repo:** [Skyvern-AI/skyvern](https://github.com/skyvern-ai/skyvern)
- **Estrellas:** 20k+ | **Licencia:** AGPL-3.0
- **Descripción:** Agente AI de automatización de navegador que usa vision LLMs. No depende de selectores DOM — usa computer vision para interactuar con páginas.
- **Dependencias:** Kubernetes, PostgreSQL, pesado para self-hosted.
- **Veredicto:** Interesante pero demasiado complejo y pesado para la VM. Licencia AGPL restrictiva.

#### AgentQL
- **Repo/Sitio:** [agentql.com](https://www.agentql.com/)
- **Descripción:** SDK que usa lenguaje natural en lugar de selectores CSS/XPath. Construido sobre Playwright. Self-healing contra cambios de estructura de página.
- **Veredicto:** Interesante para scraping resiliente; evaluar en Fase 2.

#### LaVague
- **Repo:** [lavague-ai/LaVague](https://github.com/lavague-ai/LaVague)
- **Descripción:** Framework Python open-source para crear agentes web con IA. Combina World Model (LLM) + Action Engine (Playwright/Selenium).
- **Veredicto:** Similar a browser-use pero menos maduro y con menos comunidad.

### 2.3 Herramientas no-Python (referencia)

| Herramienta | Lenguaje | Descripción | Self-hosted | Notas |
|-------------|----------|-------------|-------------|-------|
| Puppeteer | Node.js | API de Google para Chromium headless/headed | ✅ | Referencia; Playwright lo supera |
| Playwright (Node) | Node.js | Versión Node original de Playwright | ✅ | Preferimos Python por alineación con Worker |
| Browserless | Docker | API HTTP para browser automation. Open-source + Enterprise | ✅ | Útil si se necesita servicio separado |
| Apify | Cloud | Plataforma de web scraping/automation | ❌ Cloud-only | No aplica para VM local |

---

## 3. Matriz comparativa

| Herramienta | Lenguaje | Navegación | Clics | Formularios | Capturas | Multi-tab | Grabación flujos | Programación | VM Windows | Mantenimiento | Licencia | Enlace |
|-------------|----------|:----------:|:-----:|:-----------:|:--------:|:---------:|:----------------:|:------------:|:----------:|:-------------:|----------|--------|
| **Playwright Python** | Python | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ codegen | ✅ via cron | ✅ Nativo | ✅ Microsoft | Apache 2.0 | [PyPI](https://pypi.org/project/playwright/) |
| Selenium Python | Python | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ via cron | ✅ + chromedriver | ✅ Activo | Apache 2.0 | [PyPI](https://pypi.org/project/selenium/) |
| **browser-use** | Python | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (Playwright) | ✅ Activo (79k★) | MIT | [GitHub](https://github.com/browser-use/browser-use) |
| workflow-use | Python | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Nativo | ✅ | ✅ (Playwright) | ⚠️ Early dev | MIT | [GitHub](https://github.com/browser-use/workflow-use) |
| Skyvern | Python | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ⚠️ Pesado | ✅ Activo | AGPL-3.0 | [GitHub](https://github.com/skyvern-ai/skyvern) |
| AgentQL | Python | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (Playwright) | ✅ Activo | Propietaria | [agentql.com](https://www.agentql.com/) |
| Pyppeteer | Python | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ Abandonado | MIT | [GitHub](https://github.com/pyppeteer/pyppeteer) |
| Browserless | Docker | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ Docker | ✅ Activo | MIT / Comercial | [browserless.io](https://www.browserless.io/) |
| Splinter | Python | ✅ | ✅ | ✅ | ✅ | ⚠️ | ❌ | ✅ | ✅ | ⚠️ Bajo | MIT | [GitHub](https://github.com/cobrateam/splinter) |

**Leyenda:** ✅ Soportado | ⚠️ Parcial/Limitado | ❌ No soportado

---

## 4. Arquitectura propuesta

### 4.1 Integración con el stack actual

```
┌─────────────────────────────────────────────────────────┐
│                    CONTROL PLANE (VPS)                   │
│                                                         │
│  David (Notion/Telegram)                                │
│       │                                                 │
│       ▼                                                 │
│  Dispatcher ──── Redis Queue                            │
│       │                                                 │
│       │  Encola tareas browser.*                        │
│       │                                                 │
└───────┼─────────────────────────────────────────────────┘
        │ HTTP (Tailscale)
        ▼
┌─────────────────────────────────────────────────────────┐
│                 EXECUTION PLANE (VM Windows)             │
│                                                         │
│  Worker API (FastAPI :8088)                              │
│       │                                                 │
│       ├─── browser.navigate     ──┐                     │
│       ├─── browser.click         │                      │
│       ├─── browser.fill          ├── BrowserManager     │
│       ├─── browser.screenshot    │   (Playwright)       │
│       ├─── browser.execute      ──┘                     │
│       ├─── browser.tabs.list                            │
│       ├─── browser.tabs.open                            │
│       ├─── browser.tabs.close                           │
│       ├─── browser.session.save                         │
│       └─── browser.session.restore                      │
│                                                         │
│  BrowserManager (Singleton)                             │
│       │                                                 │
│       ├── Playwright Instance                           │
│       ├── Browser (Chromium, headed o headless)          │
│       ├── Persistent Context (cookies/sesión)            │
│       └── Page Pool (multi-tab)                          │
│                                                         │
│  [Opcional] browser-use Agent                           │
│       └── Para instrucciones en lenguaje natural        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Componentes clave

#### BrowserManager (`worker/browser/manager.py`)

Singleton que gestiona la instancia de Playwright y el navegador:

- **Lifecycle:** Se inicializa al primer uso y se mantiene vivo entre tareas (evita reiniciar el navegador en cada llamada).
- **Persistent Context:** Usa `browser_type.launch_persistent_context(user_data_dir)` para mantener cookies, localStorage y sesiones entre ejecuciones.
- **Page Pool:** Mantiene un diccionario de páginas activas (tabs) identificadas por `page_id` para soporte multi-tab.
- **Modo:** Configurable via env var `BROWSER_HEADLESS` (default: `true` para servidores, `false` para debug).

#### Tareas Worker (`worker/tasks/browser.py`)

Nuevos handlers registrados en `TASK_HANDLERS`:

| Tarea | Parámetros | Retorno |
|-------|-----------|---------|
| `browser.navigate` | `url`, `wait_until?`, `page_id?` | `{page_id, title, url}` |
| `browser.click` | `selector`, `page_id?` | `{clicked: true}` |
| `browser.fill` | `selector`, `value`, `page_id?` | `{filled: true}` |
| `browser.screenshot` | `path?`, `full_page?`, `selector?`, `page_id?` | `{path, base64?}` |
| `browser.execute` | `script` (JS), `page_id?` | `{result}` |
| `browser.read_page` | `page_id?`, `selector?` | `{text, html?, title, url}` |
| `browser.tabs.list` | — | `{tabs: [{page_id, title, url}]}` |
| `browser.tabs.open` | `url?` | `{page_id}` |
| `browser.tabs.close` | `page_id` | `{closed: true}` |
| `browser.session.save` | `name` | `{saved: true, path}` |
| `browser.session.restore` | `name` | `{restored: true}` |
| `browser.ai.execute` | `instruction` (lenguaje natural) | `{result, screenshots[]}` |

### 4.3 Flujo mínimo de ejemplo

**Escenario:** Rick recibe petición "toma una captura del dashboard de ACC".

```
1. David escribe en Notion: "Rick: captura el dashboard de ACC"
2. Notion Poller detecta → Dispatcher clasifica como browser task
3. Dispatcher encola en Redis:
   {
     "task": "browser.navigate",
     "params": {"url": "https://acc.autodesk.com/dashboard", "wait_until": "networkidle"}
   }
4. Worker VM recibe → BrowserManager navega (usando persistent context con sesión ACC guardada)
5. Dispatcher encola segunda tarea:
   {
     "task": "browser.screenshot",
     "params": {"full_page": true, "path": "G:\\Mi unidad\\Rick-David\\capturas\\acc_dashboard.png"}
   }
6. Worker VM ejecuta → screenshot guardado
7. Rick sube la imagen a Notion como respuesta
```

Para flujos complejos, Rick puede usar `browser.ai.execute` con browser-use:

```
{
  "task": "browser.ai.execute",
  "params": {
    "instruction": "Ir a Mercado Público, buscar licitaciones BIM, extraer las 5 primeras con título, organismo y fecha de cierre"
  }
}
```

---

## 5. Seguridad y permisos

| Aspecto | Política |
|---------|----------|
| **Usuario de ejecución** | El Worker corre como usuario `rick` en la VM (sin privilegios admin) |
| **Dominios permitidos** | Configurable via `config/browser_allowed_domains.yaml` — whitelist de dominios |
| **Credenciales** | Nunca en código; usar variables de entorno o archivos de sesión en persistent context |
| **Sesiones persistentes** | Directorio `user_data_dir` en `C:\Users\rick\.browser-sessions\` con permisos restrictivos |
| **Timeout** | Cada tarea browser tiene timeout configurable (default 30s, max 120s) |
| **Screenshots** | Se guardan en directorio controlado; se limpian periódicamente |
| **JavaScript execution** | `browser.execute` solo disponible si `BROWSER_ALLOW_JS_EXEC=true` |

---

## 6. Condicionantes

| Aspecto | Decisión | Justificación |
|---------|----------|---------------|
| **¿Solo VM?** | Sí, fase 1-3 | El Worker de la VM tiene acceso a la sesión de escritorio Windows |
| **¿Headless o headed?** | Ambos | Headless por defecto para eficiencia; headed para debug y cuando se necesita ventana visible |
| **¿Sesiones persistentes?** | Sí | Persistent context de Playwright mantiene cookies entre ejecuciones; esencial para sitios con login |
| **¿Sesiones efímeras?** | Opcional | Disponible via parámetro `ephemeral: true` en tareas browser |
| **¿Multi-navegador?** | No inicialmente | Solo Chromium en Fase 1; Firefox/WebKit en Fase 3 si se necesita |

---

## 7. Fases de implementación

### Fase 1 — MVP (Semana 1-2)

**Objetivo:** Navegación básica, clics, capturas y lectura de páginas.

| Entregable | Descripción |
|------------|-------------|
| `worker/browser/manager.py` | BrowserManager singleton con Playwright |
| `worker/tasks/browser.py` | Handlers: `browser.navigate`, `browser.click`, `browser.fill`, `browser.screenshot`, `browser.read_page` |
| `worker/tasks/__init__.py` | Registrar nuevos handlers |
| Tests unitarios | Tests con mocks de Playwright |
| Tests de integración | E2E contra sitio de prueba local o `example.com` |

**Tareas Worker Fase 1:**
- `browser.navigate` — Ir a una URL
- `browser.click` — Clic en un elemento por selector
- `browser.fill` — Rellenar un campo
- `browser.screenshot` — Tomar captura
- `browser.read_page` — Leer texto/HTML de la página

**Dependencias a instalar en la VM:**
```bash
pip install playwright
playwright install chromium --with-deps
```

### Fase 2 — Multi-tab y formularios avanzados (Semana 3-4)

**Objetivo:** Gestión de pestañas, formularios complejos, ejecución de JS, sesiones.

| Entregable | Descripción |
|------------|-------------|
| Multi-tab handlers | `browser.tabs.list`, `browser.tabs.open`, `browser.tabs.close` |
| Sesiones | `browser.session.save`, `browser.session.restore` |
| JS execution | `browser.execute` para scripts arbitrarios |
| Formularios avanzados | Soporte para selects, checkboxes, file uploads, date pickers |
| Network interception | Capturar requests/responses para debugging |

### Fase 3 — Flujos grabados, AI y programación (Semana 5-8)

**Objetivo:** Grabación de flujos, ejecución con AI, tareas programadas.

| Entregable | Descripción |
|------------|-------------|
| `browser.ai.execute` | Integración con browser-use para instrucciones en lenguaje natural |
| Flujos grabados | Integración con workflow-use o sistema propio basado en Playwright codegen |
| `browser.flow.record` | Iniciar grabación de acciones del usuario |
| `browser.flow.replay` | Reproducir un flujo grabado |
| Tareas programadas | Reutilizar scheduled tasks de Redis para browser automation |
| Dominios config | `config/browser_allowed_domains.yaml` con whitelist |

### Fase 4 — Hardening y producción (Semana 9+)

**Objetivo:** Estabilidad, resiliencia, monitoring.

| Entregable | Descripción |
|------------|-------------|
| Retry logic | Reintentos automáticos para errores de red/timeout |
| Health monitoring | Verificar que el browser está vivo; reiniciar si se cuelga |
| Langfuse tracing | Instrumentar acciones de navegador para observabilidad |
| Anti-detection | User-agent rotation, human-like delays para sitios con protección |
| Rate limiting | Limitar frecuencia de acciones para evitar bans |

---

## 8. Recomendación

### Stack recomendado

| Componente | Herramienta | Justificación |
|------------|-------------|---------------|
| **Motor de navegador** | **Playwright Python** | Más rápido que Selenium, auto-waits, multi-browser, codegen, persistent contexts, mantenido por Microsoft |
| **Capa AI (Fase 3)** | **browser-use** | 79k★, MIT, construido sobre Playwright, soporta múltiples LLMs, extensible |
| **Grabación de flujos** | **Playwright Codegen** (Fase 1-2) + **workflow-use** (Fase 3) | Codegen genera scripts Python directos; workflow-use agrega self-healing y ejecución determinística |
| **Integración Worker** | **Tareas `browser.*`** en `worker/tasks/browser.py` | Alineado con la arquitectura existente (task handlers) |
| **Sesiones** | **Playwright Persistent Context** | Mantiene cookies/login entre ejecuciones sin código adicional |

### ¿Por qué Playwright sobre Selenium?

1. **Performance:** 46% más rápido en benchmarks 2026.
2. **Auto-waits:** No necesita `time.sleep()` ni waits manuales.
3. **Setup simple:** `pip install playwright && playwright install chromium`. Sin chromedriver.
4. **Codegen:** Grabación de acciones incluida de fábrica.
5. **Persistent contexts:** Sesiones con cookies nativas.
6. **Multi-context:** Aislamiento de sesiones sin reiniciar el navegador.
7. **CDP nativo:** Acceso a Chrome DevTools Protocol para debugging avanzado.
8. **Ecosistema AI:** browser-use y workflow-use están construidos sobre Playwright.

### ¿Por qué browser-use como capa AI?

1. **Comunidad:** 79k★ en GitHub, 300+ contributors.
2. **Compatibilidad:** Usa Playwright internamente — se integra con nuestro BrowserManager.
3. **Multi-LLM:** Soporta Gemini (nuestro LLM principal), OpenAI y Anthropic.
4. **Extensible:** Custom tools via decoradores.
5. **Licencia:** MIT, sin restricciones.

---

## 9. Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|:------------:|:-------:|------------|
| **Selectores frágiles** | Alta | Medio | Usar selectores semánticos (`get_by_text`, `get_by_role`); browser-use con AI self-healing |
| **Detección de bots** | Media | Alto | Persistent context (parece usuario real), headers reales, human-like delays |
| **CAPTCHAs** | Media | Alto | Pausa automática + notificación a David para resolución manual; en Fase 3 evaluar servicios anti-CAPTCHA |
| **Rendimiento en VM** | Baja | Medio | Chromium headed consume RAM; configurar `--disable-gpu` si es necesario; limitar tabs simultáneas |
| **Cambios en sitios web** | Alta | Medio | Self-healing via browser-use; alertas cuando falla un flujo guardado |
| **Sesiones expiradas** | Media | Bajo | Detectar redirects a login → notificar a David o re-autenticar automáticamente |
| **Seguridad: ejecución de JS arbitrario** | Baja | Alto | Feature flag `BROWSER_ALLOW_JS_EXEC`; sanitización de scripts |
| **Concurrencia** | Baja | Medio | Un solo browser por Worker; cola de tareas serializada; múltiples Workers si se necesita paralelismo |

---

## 10. Dependencias y requisitos

### En la VM (Windows)

```bash
# Python packages
pip install playwright browser-use

# Instalar navegador Chromium
playwright install chromium --with-deps

# Opcional (Fase 3)
pip install workflow-use
```

### Variables de entorno nuevas

| Variable | Default | Descripción |
|----------|---------|-------------|
| `BROWSER_HEADLESS` | `true` | `true` para headless, `false` para ventana visible |
| `BROWSER_USER_DATA_DIR` | `C:\Users\rick\.browser-sessions\default` | Directorio de sesión persistente |
| `BROWSER_ALLOW_JS_EXEC` | `false` | Habilitar `browser.execute` |
| `BROWSER_TIMEOUT` | `30000` | Timeout por defecto (ms) |
| `BROWSER_MAX_TABS` | `5` | Máximo de pestañas simultáneas |

---

## 11. Referencias

- [Playwright Python — Docs oficiales](https://playwright.dev/python/)
- [browser-use — GitHub](https://github.com/browser-use/browser-use)
- [workflow-use — GitHub](https://github.com/browser-use/workflow-use)
- [Skyvern — GitHub](https://github.com/skyvern-ai/skyvern)
- [AgentQL — Sitio oficial](https://www.agentql.com/)
- [Claude in Chrome — Docs](https://support.claude.com/en/articles/12012173-getting-started-with-claude-in-chrome)
- [Claude Code + Chrome — Docs](https://code.claude.com/docs/en/chrome)
- [Browserless — Docs](https://docs.browserless.io/)
- [Selenium Python — Docs](https://www.selenium.dev/documentation/)
- [Playwright vs Selenium 2026 — BrowserStack](https://www.browserstack.com/guide/playwright-vs-selenium)
