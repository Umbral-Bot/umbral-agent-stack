# Task R16 — Investigación exhaustiva: automatización de navegador tipo "Claude in Chrome" en la VM

**Fecha:** 2026-03-05  
**Ronda:** 16  
**Agente:** Cursor Agent Cloud  
**Branch:** `feat/browser-automation-vm-research`

---

## Contexto

[Claude in Chrome](https://support.claude.com/en/articles/12012173-getting-started-with-claude-in-chrome) permite a Claude **leer, hacer clic y navegar** en sitios web: ver lo que el usuario ve, hacer clics, rellenar formularios, tomar capturas, gestionar pestañas, ejecutar flujos grabados y tareas programadas. El objetivo es tener **capacidades equivalentes en la VM** del Umbral Agent Stack, para que Rick pueda orquestar automatización de navegador (navegar, clics, formularios, capturas, etc.) usando la VM como plano de ejecución.

---

## Objetivo

Realizar una **investigación exhaustiva** (herramientas, librerías Python, repositorios abiertos en GitHub) que permitan **manipular un navegador web** de forma similar a Claude in Chrome: navegar, hacer clics, llenar formularios, tomar capturas, gestionar ventanas/pestañas, y opcionalmente grabar y repetir flujos. Con eso, **diseñar un plan y un pipeline** para desarrollar e implementar esta capacidad como **habilidad de Rick usando la VM**, y dejar el resultado documentado y como skill reutilizable.

---

## Referencia: qué hace Claude in Chrome

Según la [documentación oficial](https://support.claude.com/en/articles/12012173-getting-started-with-claude-in-chrome):

| Capacidad | Descripción |
|-----------|-------------|
| Leer páginas | Ver texto y estructura de la página en el panel lateral |
| Clics y navegación | Hacer clic en botones, enlaces, rellenar campos |
| Múltiples pestañas | Abrir, cerrar, cambiar de pestaña; agrupar pestañas |
| Capturas | Tomar screenshots de regiones o páginas completas |
| Formularios | Rellenar formularios y enviar |
| Flujos grabados | Grabar pasos del usuario y repetirlos (workflows) |
| Tareas programadas | Ejecutar acciones en horarios (diario, semanal, etc.) |
| Consola / depuración | Leer logs de consola, peticiones de red, estado del DOM |
| Integración Desktop | Iniciar tareas desde Claude Desktop y que el navegador las ejecute |

En la VM necesitamos un subconjunto accionable por código: **navegar, clic, rellenar, captura, multi-tab**, y opcionalmente **flujos guardados** y **programación**.

---

## Tareas requeridas

### 1. Búsqueda exhaustiva

Investigar y documentar:

**Librerías Python (prioridad):**
- Playwright (Python): ya hay skill `playwright-python`; evaluar si cubre todo (navegación, clics, formularios, capturas, multi-tab, persistencia de sesión).
- Selenium (Python): comparar con Playwright; ventajas/desventajas para VM.
- Pyppeteer / Puppeteer (Python/Node): control de Chromium headless/headed.
- Otras: Splinter, Mechanize, requests + BeautifulSoup (solo lectura; anotar limitaciones).
- Librerías para "recording & replay" de flujos (si existen en Python o integrables).

**Repositorios abiertos en GitHub:**
- Proyectos que expongan API o CLI para "controlar navegador" (navegar, clic, formularios, capturas).
- Integraciones "browser automation as a service" o agentes que usen Playwright/Selenium.
- Herramientas de grabación de flujos (export a script Python o JSON) que se puedan ejecutar en la VM.

**Herramientas no-Python (referencia):**
- Puppeteer (Node), Playwright (Node), Selenium (múltiples lenguajes).
- Browserless, Apify, etc.: anotar si son útiles para VM (self-hosted vs cloud).

**Criterios para la VM:**
- Ejecutable en Windows (VM actual).
- Preferiblemente Python (alineado con Worker) o invocable desde Python.
- Soporte headless y/o headed (ventana visible si hace falta para capturas o depuración).
- Posibilidad de recibir órdenes por API o cola (Worker → tarea "navegar a X, clic en Y, rellenar Z, captura").

### 2. Matriz comparativa

Crear una tabla (en el documento de entrega) con:
- Nombre de la herramienta/librería/repo
- Lenguaje / entorno
- Capacidades: navegación, clic, formularios, capturas, multi-tab, grabación de flujos, programación
- Uso en VM (Windows): viable / con restricciones / no
- Enlace (PyPI, GitHub, docs)
- Observaciones (mantenimiento, licencia, dependencias)

### 3. Diseño del plan y pipeline

Redactar un **plan de implementación** (pipeline) que incluya:

- **Arquitectura:** Cómo se integra con el stack actual: Dispatcher → Worker → ¿nuevo módulo en VM? ¿Worker llama a un servicio local en la VM (Playwright/Selenium) vía HTTP o cola? ¿O la VM ejecuta scripts Playwright invocados por `windows.pad.run_flow` o una nueva task tipo `browser.navigate`, `browser.click`, etc.?
- **Seguridad y permisos:** Ejecución en VM con usuario limitado; qué sitios o dominios permitir; evitar credenciales en código.
- **Flujo mínimo:** Ejemplo de flujo "Rick recibe petición → encola tarea → Worker (o VM) ejecuta navegación + clics + captura → resultado a Notion/Telegram".
- **Condicionantes:** ¿Solo VM? ¿Solo headless o también headed? ¿Sesiones persistentes (cookies, login) o sesiones efímeras?
- **Fases sugeridas:** Fase 1 (MVP: navegar, clic, captura, un solo task), Fase 2 (formularios, multi-tab), Fase 3 (flujos grabados/replay, tareas programadas).

### 4. Documento de entrega

Crear **`docs/64-browser-automation-vm-plan.md`** (en español) con:
- Resumen ejecutivo (1 párrafo).
- Referencia a Claude in Chrome y tabla de capacidades objetivo.
- Resultados de la búsqueda: herramientas, librerías, repos (con enlaces).
- Matriz comparativa.
- Plan y pipeline (arquitectura, flujo, fases, condicionantes).
- Recomendación: stack concreto (ej. Playwright Python en VM + task `browser.*` en Worker).
- Riesgos y mitigaciones (mantenimiento de selectores, detección de bots, rendimiento).

### 5. Skill para Rick

Crear o ampliar un skill de OpenClaw que documente esta capacidad como **habilidad de Rick usando la VM**:

- **Opción A:** Ampliar `openclaw/workspace-templates/skills/playwright-python/SKILL.md` con una sección "Uso desde Rick en la VM" que describa el pipeline, las tareas Worker previstas (`browser.*`) y ejemplos de uso (navegar, clic, formulario, captura).
- **Opción B:** Crear `openclaw/workspace-templates/skills/browser-automation-vm/SKILL.md` dedicado a "automatización de navegador en la VM (tipo Claude in Chrome)", con frontmatter, descripción, cuándo usar, y referencia a `docs/64-browser-automation-vm-plan.md`.

El skill debe dejar claro que Rick puede orquestar estas acciones en la VM (navegar ventanas, clics, llenar formularios, capturas, etc.) según el plan diseñado.

---

## Criterios de éxito

- [x] Búsqueda exhaustiva documentada (libs Python, repos GitHub, herramientas).
- [x] Matriz comparativa con criterios VM y enlaces.
- [x] Documento `docs/64-browser-automation-vm-plan.md` con plan, pipeline y recomendación.
- [x] Skill actualizado o nuevo que registre la habilidad de Rick "automatización de navegador en la VM".
- [x] Todo en español.
- [ ] PR abierto a `main`.

---

## Log

### [cursor-agent-cloud] 2026-03-05

**Investigación completada.**

1. **Búsqueda exhaustiva:** 9+ herramientas — Playwright Python (recomendado), Selenium, Pyppeteer (descartado), browser-use (79k★, capa AI), workflow-use (RPA), Skyvern, AgentQL, LaVague, Browserless.
2. **Matriz comparativa:** 9 herramientas × 8 criterios + VM Windows + mantenimiento + licencia.
3. **Plan:** `docs/64-browser-automation-vm-plan.md` — arquitectura, 4 fases, seguridad, riesgos.
4. **Skill:** `openclaw/workspace-templates/skills/browser-automation-vm/SKILL.md` (Opción B — skill dedicado) — tareas `browser.*`, ejemplos, comparación con Claude in Chrome.

**Archivos creados/modificados:**
- `docs/64-browser-automation-vm-plan.md` (nuevo)
- `openclaw/workspace-templates/skills/browser-automation-vm/SKILL.md` (nuevo)
- `.agents/tasks/2026-03-04-076-r16-browser-automation-vm-investigacion.md` (actualizado)
- `.agents/board.md` (actualizado)
