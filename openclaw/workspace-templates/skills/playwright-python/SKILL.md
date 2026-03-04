---
name: playwright-python
description: >-
  Automatizacion de navegadores web con Playwright Python. Web scraping avanzado,
  capturas de pantalla automatizadas, extraccion de datos de portales AEC, testing
  de plataformas web y automatizacion de formularios. Ideal para monitorear precios
  de materiales, normativas, portales de licitaciones y plataformas BIM online.
  Use when "scraping web", "automatizar navegador", "extraer datos web", "captura pantalla",
  "llenar formulario automatico", "monitorear portal", "descargar reportes web".
metadata:
  openclaw:
    emoji: "\U0001F3AD"
    requires:
      env: []
---

# Playwright Python — Automatizacion de Navegadores

Playwright es la alternativa moderna a Selenium. Controla Chromium, Firefox y WebKit con una API unificada. Maneja JavaScript, SPAs, autenticacion y descarga de archivos sin necesidad de drivers adicionales.

**Docs oficiales:** https://playwright.dev/python/

## Instalacion

**Instalacion:**
```bash
pip install playwright
playwright install          # Descarga los 3 navegadores (~800MB)
playwright install chromium # Solo Chromium (mas liviano)
```

---

## Casos de uso para David (BIM / Consultoría / Docencia)

### 1. Monitorear precios de materiales de construccion — portal de proveedor

Extrae precios de un portal de materiales y los guarda en CSV:

```python
import asyncio
import csv
from datetime import date
from playwright.async_api import async_playwright

async def scrape_precios_materiales(url: str, salida_csv: str):
    """Extrae tabla de precios de materiales desde portal web."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Ir a la pagina de materiales
        await page.goto(url, wait_until="networkidle")

        # Esperar tabla de precios (ajustar selector al portal real)
        await page.wait_for_selector("table.precios-materiales")

        filas = await page.query_selector_all("table.precios-materiales tbody tr")

        with open(salida_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Fecha", "Material", "Unidad", "Precio_CLP"])

            for fila in filas:
                celdas = await fila.query_selector_all("td")
                if len(celdas) >= 3:
                    material = await celdas[0].inner_text()
                    unidad = await celdas[1].inner_text()
                    precio = await celdas[2].inner_text()
                    writer.writerow([date.today(), material.strip(), unidad.strip(), precio.strip()])

        print(f"Precios guardados en: {salida_csv}")
        await browser.close()


asyncio.run(scrape_precios_materiales(
    "https://proveedor-materiales.cl/precios",
    "precios_materiales_hoy.csv"
))
```

### 2. Captura automatica de portal Autodesk Construction Cloud

Tomar screenshots de dashboards de proyectos para reportes ejecutivos:

```python
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def capturar_dashboard_acc(
    email: str,
    password: str,
    proyecto_url: str,
    carpeta_capturas: str = "capturas_acc"
):
    """Loguea en ACC y toma capturas del dashboard del proyecto."""
    Path(carpeta_capturas).mkdir(exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # False para ver el proceso
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        # Login Autodesk
        await page.goto("https://accounts.autodesk.com/Authentication/LogOn")
        await page.fill("input[name='userName']", email)
        await page.click("button[type='submit']")
        await page.wait_for_selector("input[name='password']", timeout=5000)
        await page.fill("input[name='password']", password)
        await page.click("button[type='submit']")
        await page.wait_for_url("**/acc.autodesk.com/**", timeout=15000)

        # Navegar al proyecto
        await page.goto(proyecto_url)
        await page.wait_for_load_state("networkidle")

        # Captura pantalla completa del dashboard
        await page.screenshot(
            path=f"{carpeta_capturas}/dashboard_completo.png",
            full_page=True
        )

        # Captura solo el grafico de progreso (ajustar selector)
        grafico = page.locator(".progress-chart")
        if await grafico.count() > 0:
            await grafico.screenshot(path=f"{carpeta_capturas}/grafico_progreso.png")

        print(f"Capturas guardadas en: {carpeta_capturas}/")
        await browser.close()


asyncio.run(capturar_dashboard_acc(
    email="david@umbral.cl",
    password="mi_password",
    proyecto_url="https://acc.autodesk.com/projects/PROYECTO_ID/dashboard"
))
```

### 3. Scraping de licitaciones publicas — portal Mercado Publico Chile

Monitorea nuevas licitaciones relevantes para consultoria BIM:

```python
import asyncio
from playwright.async_api import async_playwright
from datetime import date

async def buscar_licitaciones_bim(palabras_clave: list[str]) -> list[dict]:
    """Busca licitaciones en Mercado Publico por palabras clave AEC/BIM."""
    licitaciones = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for keyword in palabras_clave:
            url = f"https://www.mercadopublico.cl/Licitacion?keyword={keyword}"
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_selector(".lista-licitaciones", timeout=10000)

            items = await page.query_selector_all(".item-licitacion")

            for item in items[:10]:  # Primeros 10 resultados
                titulo_el = await item.query_selector(".titulo-licitacion")
                org_el = await item.query_selector(".organismo")
                fecha_el = await item.query_selector(".fecha-cierre")

                if titulo_el:
                    licitaciones.append({
                        "fecha_busqueda": str(date.today()),
                        "keyword": keyword,
                        "titulo": await titulo_el.inner_text(),
                        "organismo": await org_el.inner_text() if org_el else "N/A",
                        "cierre": await fecha_el.inner_text() if fecha_el else "N/A",
                    })

        await browser.close()

    return licitaciones


async def main():
    keywords = ["BIM", "modelado arquitectonico", "coordinacion BIM", "Revit"]
    resultados = await buscar_licitaciones_bim(keywords)
    for lic in resultados:
        print(f"[{lic['keyword']}] {lic['titulo']} — {lic['organismo']} (Cierre: {lic['cierre']})")

asyncio.run(main())
```

### 4. Uso sincronico (sin asyncio) — para scripts simples

Para scripts rapidos sin necesidad de asyncio:

```python
from playwright.sync_api import sync_playwright

def capturar_pagina(url: str, archivo: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(url, wait_until="networkidle")
        page.screenshot(path=archivo, full_page=True)
        browser.close()
        print(f"Captura guardada: {archivo}")

capturar_pagina("https://viewer.autodesk.com/", "captura_viewer.png")
```

## Selectores Playwright — Referencia rapida

```python
# Por CSS
page.locator(".clase-css")
page.locator("#id-elemento")
page.locator("table.datos tr")

# Por texto visible
page.get_by_text("Confirmar")
page.get_by_role("button", name="Enviar")

# Por placeholder
page.get_by_placeholder("Ingrese email")

# XPath (legacy)
page.locator("xpath=//div[@class='container']")
```

## Opciones de lanzamiento utiles

```python
browser = await p.chromium.launch(
    headless=True,             # False para debug visual
    slow_mo=50,                # Milisegundos entre acciones (debug)
    downloads_path="./descargas"  # Carpeta para archivos descargados
)

context = await browser.new_context(
    viewport={"width": 1920, "height": 1080},
    locale="es-CL",
    timezone_id="America/Santiago",
    accept_downloads=True
)
```

## Notas

- Playwright maneja automaticamente waits (no necesita `time.sleep`)
- Para sitios con Cloudflare/CAPTCHA, usar `headless=False` y `slow_mo=100`
- Los screenshots se pueden enviar directo a Notion via API para reportes automaticos
- Combinado con Redis + Worker de Umbral Stack: crear un scraper programado como cron task
