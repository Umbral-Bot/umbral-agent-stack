---
name: playwright-python
description: >-
  Automatización de browsers con Playwright para Python: web scraping
  avanzado, capturas de pantalla, interacción con páginas dinámicas y
  extracción de datos. Ideal para scraping de precios de materiales,
  normativas, portales de licitaciones y plataformas BIM SaaS.
  Usar cuando: "scraping", "automatizar browser", "captura de pantalla web",
  "extraer datos de sitio", "llenar formulario automáticamente".
metadata:
  openclaw:
    emoji: "\U0001F3AD"
    requires:
      env: []
---

# Playwright — Automatización de Browsers con Python

Playwright permite controlar browsers reales (Chromium, Firefox, WebKit)
desde Python para scraping avanzado, testing y automatización de tareas
web repetitivas. Maneja JavaScript, SPAs y páginas dinámicas sin problema.

## Instalación

```bash
pip install playwright
playwright install chromium   # descarga el binario del browser
```

## Modos de uso

- **Sync API**: más simple, ideal para scripts lineales.
- **Async API**: mayor rendimiento, ideal para scraping concurrente.

## Casos de uso

### 1. Scraping de precios de materiales de construcción

Extrae precios actualizados de un portal de materiales para alimentar
presupuestos de proyectos BIM automáticamente.

```python
from playwright.sync_api import sync_playwright

def scrape_precios_materiales(url_catalogo: str) -> list[dict]:
    resultados = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url_catalogo, wait_until="networkidle")

        # Esperar que los productos carguen (SPA)
        page.wait_for_selector(".producto-item", timeout=10000)
        productos = page.query_selector_all(".producto-item")

        for prod in productos:
            nombre = prod.query_selector(".nombre")?.inner_text() or ""
            precio = prod.query_selector(".precio")?.inner_text() or ""
            resultados.append({"nombre": nombre, "precio": precio})

        browser.close()
    return resultados

precios = scrape_precios_materiales("https://catalogo-materiales.ejemplo.com")
for p in precios[:5]:
    print(f"{p['nombre']}: {p['precio']}")
```

### 2. Captura de pantalla de portales BIM SaaS para informe

Genera screenshots automáticos de dashboards de Autodesk Construction Cloud
u otros portales SaaS para incluir en informes semanales.

```python
import asyncio
from playwright.async_api import async_playwright

async def capturar_dashboard_bim(url: str, usuario: str, contrasena: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        await page.goto(url)
        # Login
        await page.fill("#email", usuario)
        await page.fill("#password", contrasena)
        await page.click("#btn-login")
        await page.wait_for_url("**/dashboard**", timeout=15000)

        # Esperar que los datos del dashboard carguen
        await page.wait_for_selector(".dashboard-chart", timeout=10000)
        await page.wait_for_timeout(2000)  # stabilizar animaciones

        archivo = "dashboard_bim_semanal.png"
        await page.screenshot(path=archivo, full_page=False)
        await browser.close()
        return archivo

# Ejecutar
path = asyncio.run(capturar_dashboard_bim(
    url="https://acc.autodesk.com/dashboard",
    usuario="david@empresa.com",
    contrasena="tu_password",
))
print(f"Screenshot guardado: {path}")
```

### 3. Monitoreo de licitaciones en portales de gobierno

Revisa automáticamente un portal de licitaciones de obras públicas y extrae
los proyectos publicados en el día con sus montos estimados.

```python
from playwright.sync_api import sync_playwright
from datetime import date

def obtener_licitaciones_hoy(url_portal: str) -> list[dict]:
    hoy = date.today().strftime("%d/%m/%Y")
    licitaciones = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url_portal)

        # Filtrar por fecha de hoy
        page.fill("#filtro-fecha", hoy)
        page.click("#btn-buscar")
        page.wait_for_selector("table#resultados tbody tr", timeout=8000)

        filas = page.query_selector_all("table#resultados tbody tr")
        for fila in filas:
            celdas = fila.query_selector_all("td")
            if len(celdas) >= 3:
                licitaciones.append({
                    "expediente": celdas[0].inner_text(),
                    "descripcion": celdas[1].inner_text(),
                    "monto": celdas[2].inner_text(),
                })

        browser.close()
    return licitaciones

lics = obtener_licitaciones_hoy("https://portal-licitaciones.gov.ejemplo")
for l in lics:
    print(f"[{l['expediente']}] {l['descripcion']} — {l['monto']}")
```

## Notas

- `wait_until="networkidle"` espera que la red esté inactiva (bueno para SPAs).
- `wait_for_selector()` espera que un elemento aparezca antes de interactuar.
- Para sitios con auth, se puede persistir el estado con `context.storage_state()`.
- Playwright también soporta generación de PDF con `page.pdf()`.
- Docs oficiales: https://playwright.dev/python/
