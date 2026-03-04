---
name: playwright-python
description: >-
  Automatizacion de browsers con Python usando Playwright: web scraping
  avanzado con JavaScript renderizado, automatizacion de formularios,
  capturas de pantalla, testing de apps web y extraccion de datos de
  portales de construccion, normativas y precios de materiales.
  Use when "scraping web", "automatizar browser", "extraer datos web",
  "captura pantalla web", "automatizar formulario", "web scraping playwright",
  "datos de portal", "navegar web Python", "precios materiales web".
metadata:
  openclaw:
    emoji: "\U0001F3AD"
    requires:
      env: []
---

# Playwright Python — Automatizacion de Browsers

Playwright es la libreria de automatizacion de browsers de Microsoft, con bindings para Python. Soporta Chromium, Firefox y WebKit en modo headless o con UI visible. Es superior a Selenium para sitios modernos con JavaScript renderizado (React, Angular, Vue).

**Instalacion:**
```bash
pip install playwright
playwright install chromium  # Solo Chromium (mas liviano)
# O instalar todos los browsers:
playwright install
```

**Docs oficiales:** https://playwright.dev/python/

---

## Casos de uso para David (BIM / Consultoría / Docencia)

### 1. Scraping de precios de materiales de construccion de portales

Extrae precios de materiales desde portales de proveedores de construccion con JavaScript dinamico.

```python
from playwright.sync_api import sync_playwright
import json
from datetime import date

def extraer_precios_materiales(url_portal: str, selector_items: str) -> list[dict]:
    """Extrae tabla de precios de un portal de materiales de construccion."""
    resultados = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # User-agent de browser real para evitar bloqueos basicos
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        page.goto(url_portal, wait_until="networkidle", timeout=30000)

        # Esperar a que los precios carguen (JS dinamico)
        page.wait_for_selector(selector_items, timeout=15000)

        items = page.query_selector_all(selector_items)
        for item in items:
            nombre = item.query_selector(".nombre-producto, .product-name")
            precio = item.query_selector(".precio, .price")
            unidad = item.query_selector(".unidad, .unit")

            if nombre and precio:
                resultados.append({
                    "nombre": nombre.inner_text().strip(),
                    "precio": precio.inner_text().strip(),
                    "unidad": unidad.inner_text().strip() if unidad else "unidad",
                    "fecha": str(date.today()),
                })

        browser.close()

    return resultados


# Guardar resultados en JSON
precios = extraer_precios_materiales(
    "https://www.ejemplo-proveedor-construccion.cl/catalogo",
    ".product-card"
)
with open("precios_materiales.json", "w", encoding="utf-8") as f:
    json.dump(precios, f, ensure_ascii=False, indent=2)
print(f"Extraidos: {len(precios)} materiales")
```

### 2. Capturar screenshots automaticos de dashboards Power BI para reportes

Automatiza la captura de paneles Power BI embebidos o reportes web para incluirlos en informes PDF.

```python
from playwright.sync_api import sync_playwright
from pathlib import Path
from datetime import datetime

DASHBOARDS = [
    {
        "nombre": "Avance_Obra",
        "url": "https://app.powerbi.com/view?r=TOKEN_DASHBOARD_1",
        "espera_selector": ".visual-container",
    },
    {
        "nombre": "Costos_Proyecto",
        "url": "https://app.powerbi.com/view?r=TOKEN_DASHBOARD_2",
        "espera_selector": ".visual-container",
    },
]

OUTPUT_DIR = Path("capturas_reportes")
OUTPUT_DIR.mkdir(exist_ok=True)
fecha = datetime.now().strftime("%Y%m%d_%H%M")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()

    for dash in DASHBOARDS:
        page.goto(dash["url"], wait_until="networkidle", timeout=60000)
        page.wait_for_selector(dash["espera_selector"], timeout=30000)
        page.wait_for_timeout(3000)  # Esperar animaciones de carga

        nombre_archivo = OUTPUT_DIR / f"{fecha}_{dash['nombre']}.png"
        page.screenshot(path=str(nombre_archivo), full_page=False)
        print(f"Capturado: {nombre_archivo}")

    browser.close()
```

### 3. Automatizar descarga de normativas y documentos tecnicos desde portales gubernamentales

Navega portales de ministerios o municipios, busca documentos y los descarga automaticamente.

```python
from playwright.sync_api import sync_playwright
from pathlib import Path
import re

def descargar_normativas(portal_url: str, termino_busqueda: str, carpeta_output: str) -> list[str]:
    """Busca y descarga documentos PDF de normativas desde un portal."""
    Path(carpeta_output).mkdir(exist_ok=True)
    archivos_descargados = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        page.goto(portal_url, wait_until="networkidle")

        # Buscar en el portal
        buscador = page.query_selector("input[type='search'], input[name='q'], #buscar")
        if buscador:
            buscador.fill(termino_busqueda)
            buscador.press("Enter")
            page.wait_for_load_state("networkidle")

        # Encontrar todos los links a PDF
        links_pdf = page.query_selector_all("a[href$='.pdf'], a[href*='download']")
        print(f"Encontrados: {len(links_pdf)} documentos")

        for link in links_pdf[:10]:  # Limitar a primeros 10
            try:
                with page.expect_download(timeout=30000) as dl_info:
                    link.click()
                descarga = dl_info.value
                nombre = re.sub(r'[<>:"/\\|?*]', "_", descarga.suggested_filename)
                ruta = f"{carpeta_output}/{nombre}"
                descarga.save_as(ruta)
                archivos_descargados.append(ruta)
                print(f"Descargado: {nombre}")
            except Exception as e:
                print(f"Error descargando: {e}")

        browser.close()

    return archivos_descargados


normativas = descargar_normativas(
    "https://www.minvu.gob.cl/normativas",
    "ordenanza general urbanismo construccion",
    "normativas_descargadas",
)
print(f"Total descargados: {len(normativas)} archivos")
```

### 4. Monitorear precios de proveedores BIM (licencias software)

Verifica periodicamente los precios publicados de licencias de software BIM (Revit, Navisworks, etc.) y alerta si cambian.

```python
from playwright.sync_api import sync_playwright
import json
from pathlib import Path
from datetime import date

PROVEEDORES = [
    {
        "nombre": "Autodesk AEC Collection",
        "url": "https://www.autodesk.com/collections/architecture-engineering-construction/overview",
        "selector_precio": ".pricing-card .price, [data-price], .price-amount",
    },
]

HISTORIAL_FILE = Path("historial_precios.json")

def leer_historial() -> dict:
    if HISTORIAL_FILE.exists():
        return json.loads(HISTORIAL_FILE.read_text())
    return {}

def guardar_historial(historial: dict):
    HISTORIAL_FILE.write_text(json.dumps(historial, indent=2, ensure_ascii=False))

historial = leer_historial()
alertas = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    for proveedor in PROVEEDORES:
        page.goto(proveedor["url"], wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        elementos = page.query_selector_all(proveedor["selector_precio"])
        precios_actuales = [e.inner_text().strip() for e in elementos if e.inner_text().strip()]

        nombre = proveedor["nombre"]
        precio_hoy = precios_actuales[0] if precios_actuales else "No encontrado"
        precio_anterior = historial.get(nombre, {}).get("precio")

        historial[nombre] = {"precio": precio_hoy, "fecha": str(date.today())}

        if precio_anterior and precio_anterior != precio_hoy:
            alertas.append(f"CAMBIO DE PRECIO: {nombre} — Antes: {precio_anterior} → Ahora: {precio_hoy}")

    browser.close()

guardar_historial(historial)
if alertas:
    print("ALERTAS DE PRECIOS:")
    for alerta in alertas:
        print(f"  {alerta}")
else:
    print("Sin cambios de precios detectados.")
```

---

## Async API (para integracion con FastAPI / asyncio)

```python
import asyncio
from playwright.async_api import async_playwright

async def capturar_pagina(url: str, output: str) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        await page.screenshot(path=output, full_page=True)
        await browser.close()

asyncio.run(capturar_pagina("https://www.ejemplo.com", "captura.png"))
```

## Notas

- `wait_until="networkidle"` espera a que no haya requests activos; usar `"domcontentloaded"` para sitios mas rapidos.
- Para sitios con autenticacion, guardar el estado de sesion: `context.storage_state(path="session.json")`.
- Playwright puede ejecutarse en servidores sin display con `headless=True` (modo por defecto).
- `page.wait_for_timeout(ms)` es un sleep; preferir `page.wait_for_selector()` para esperas basadas en DOM.
- En la VM Windows del stack, usar el Worker task `windows.run_script` para ejecutar scripts Playwright remotamente.
