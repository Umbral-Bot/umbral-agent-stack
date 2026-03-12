## Ejecutado por: codex

# Validación Browser VM — 2026-03-10

## Objetivo

Verificar si la VM ya soporta control de navegador tipado desde el Worker, con un nivel equivalente al slice mínimo necesario para navegación web real sin depender todavía de RPA GUI ni de PAD.

## Alcance

Se validó sobre el Worker de la VM en `http://100.109.16.40:8088`:

- `browser.navigate`
- `browser.read_page`
- `browser.screenshot`
- `browser.click`
- `browser.type_text`
- `browser.press_key`

## Resultado ejecutivo

El slice `browser.*` quedó operativo en la VM sobre el Worker principal (`8088`).

Resultado real:

- navegación real: OK
- lectura de contenido visible: OK
- screenshot de página: OK
- click por selector: OK
- tipeo por selector: OK
- envío de tecla: OK

La conclusión es que el control de navegador typed/browser-first ya es una base real y superior a RPA GUI para muchos flujos de automatización web.

## Implementación validada

### Código local relevante

- `worker/browser/manager.py`
- `worker/tasks/browser.py`
- `worker/tasks/__init__.py`
- `openclaw/extensions/umbral-worker/index.ts`

### Endpoints / tasks expuestos por la VM

Verificados en `/health` del Worker VM:

- `browser.navigate`
- `browser.read_page`
- `browser.screenshot`
- `browser.click`
- `browser.type_text`
- `browser.press_key`

## Smoke tests ejecutados

### 1. Inventario de tasks

Resultado:

- la VM expone correctamente toda la familia `browser.*`
- la VM expone además la familia `gui.*`

### 2. Flujo secuencial de control de página

Se validó un flujo stateful sobre la misma página:

1. navegar a una URL
2. hacer click en un selector
3. tipear texto en un input
4. presionar `Enter`
5. releer la página
6. sacar screenshot

Resultado:

- el flujo secuencial funciona
- no se debe testear en paralelo sobre la misma página persistente porque la sesión de Playwright comparte estado y se pisan las navegaciones

### 3. Hardening aplicado a `browser.press_key`

Se endureció `worker/browser/manager.py` para que:

- espere carga breve después de la tecla
- no falle si el título cambia durante navegación

Ese ajuste evitó fallos intermitentes en `Enter` durante submit de formularios o cajas de búsqueda.

### 4. Validación sobre sitio real más complejo

Se ejecutó una pasada real sobre `https://www.freepik.com/` usando `browser.*`.

Resultado:

- landing real cargada: OK
- lectura de texto visible: OK
- screenshot headful usable: OK
- click en `Sign in`: OK
- navegación a `https://www.freepik.com/log-in?...`: OK

Esto confirma que el slice no sirve solo para demos triviales: ya soporta una web moderna y más exigente.

## Limitaciones reales

- El Worker interactivo `8089` sigue inestable y no es la base recomendada para este frente.
- La validación buena y repetible hoy está sobre `8088`.
- El modelo correcto para avanzar es:
  - browser typed primero
  - GUI/RPA solo donde el navegador typed no alcance
  - PAD como último recurso

## Qué hizo Rick vs qué hice yo

### Hecho por Rick

- trazabilidad previa de los proyectos de browser/RPA en Linear, Notion y carpeta compartida

### Hecho por codex

- implementación del slice `browser.*`
- despliegue a la VM vía VPS
- hardening de `press_key`
- validación remota real en `8088`

## Veredicto

El objetivo de “controlar el navegador de la VM de forma similar al slice útil de una extensión” quedó logrado en su base técnica:

- navegación real
- lectura real
- screenshot real
- interacción por selector real

El siguiente paso útil ya no es diseñar más. Es usar este slice para automatizaciones concretas de sitios, login flows y acciones web antes de caer en RPA GUI.
