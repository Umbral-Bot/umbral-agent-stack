---
name: pillow-imaging
description: >-
  Procesamiento de imagenes con Python usando Pillow (PIL Fork): resize batch,
  crop, filtros, marca de agua, compositing, conversion de formatos y
  generacion de imagenes programaticas. Util para renders BIM, presentaciones
  y marketing visual.
  Use when "procesar imagenes", "resize imagenes", "marca de agua renders",
  "batch imagenes", "compositar imagenes", "miniatura renders",
  "convertir formato imagen", "agregar logo imagen", "filtros imagen".
metadata:
  openclaw:
    emoji: "\U0001F5BC"
    requires:
      env: []
---

# Pillow — Procesamiento de Imagenes con Python

Pillow es el fork activo de PIL (Python Imaging Library), la libreria estandar de procesamiento de imagenes en Python. Soporta mas de 30 formatos (PNG, JPG, TIFF, BMP, WebP, PDF), operaciones de resize, crop, filtros, compositing, texto y conversion de formatos.

**Instalacion:**
```bash
pip install Pillow
```

**Docs oficiales:** https://pillow.readthedocs.io/

---

## Casos de uso para David (BIM / Consultoría / Docencia)

### 1. Batch resize y conversion de renders para presentacion

Procesa una carpeta entera de renders de alta resolucion: los redimensiona para web/presentacion y aplica marca de agua del estudio.

```python
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

CARPETA_RENDERS = Path("renders_proyecto/")
CARPETA_OUTPUT = Path("renders_web/")
CARPETA_OUTPUT.mkdir(exist_ok=True)

ANCHO_WEB = 1920
MARCA_AGUA = "David Moreira — Consultoria BIM"

def agregar_marca_agua(img: Image.Image, texto: str) -> Image.Image:
    """Agrega texto semitransparente en esquina inferior derecha."""
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    try:
        font = ImageFont.truetype("arial.ttf", size=32)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), texto, font=font)
    ancho_texto = bbox[2] - bbox[0]
    alto_texto = bbox[3] - bbox[1]
    x = img.width - ancho_texto - 30
    y = img.height - alto_texto - 20
    draw.text((x, y), texto, fill=(255, 255, 255, 180), font=font)
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

for ruta in CARPETA_RENDERS.glob("*.png"):
    img = Image.open(ruta)
    # Resize proporcional
    ratio = ANCHO_WEB / img.width
    nuevo_alto = int(img.height * ratio)
    img_resized = img.resize((ANCHO_WEB, nuevo_alto), Image.LANCZOS)
    # Marca de agua
    img_final = agregar_marca_agua(img_resized, MARCA_AGUA)
    img_final.save(CARPETA_OUTPUT / ruta.name, quality=90)
    print(f"Procesado: {ruta.name} → {img_resized.size}")

print(f"Total: {len(list(CARPETA_OUTPUT.glob('*.png')))} imagenes procesadas")
```

### 2. Generar laminas de presentacion con grid de imagenes

Crea una imagen compuesta tipo "portfolio" combinando multiples renders en una grilla.

```python
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import math

def crear_grid_renders(
    rutas_imagenes: list[str],
    columnas: int = 3,
    padding: int = 20,
    fondo: tuple = (30, 30, 30),
    output: str = "portfolio_proyecto.jpg",
) -> None:
    imagenes = [Image.open(r) for r in rutas_imagenes]
    # Normalizar al mismo ancho
    ancho_celda = 600
    celdas = []
    for img in imagenes:
        ratio = ancho_celda / img.width
        alto = int(img.height * ratio)
        celdas.append(img.resize((ancho_celda, alto), Image.LANCZOS))

    filas = math.ceil(len(celdas) / columnas)
    alto_celda = celdas[0].height

    lienzo_ancho = columnas * ancho_celda + (columnas + 1) * padding
    lienzo_alto = filas * alto_celda + (filas + 1) * padding
    lienzo = Image.new("RGB", (lienzo_ancho, lienzo_alto), fondo)

    for i, celda in enumerate(celdas):
        col = i % columnas
        fila = i // columnas
        x = padding + col * (ancho_celda + padding)
        y = padding + fila * (alto_celda + padding)
        lienzo.paste(celda, (x, y))

    lienzo.save(output, quality=95)
    print(f"Grid guardado: {output} — {lienzo.size}")


# Uso
renders = sorted(Path("renders_proyecto/").glob("*.png"))
crear_grid_renders([str(r) for r in renders[:9]], columnas=3, output="portfolio_proyecto.jpg")
```

### 3. Agregar logo del estudio a planos exportados desde Revit

Superpone el logo del estudio/consultora sobre planos exportados en PNG desde Revit, para distribucion a cliente.

```python
from PIL import Image

def agregar_logo_plano(
    ruta_plano: str,
    ruta_logo: str,
    posicion: str = "bottom-right",
    escala_logo: float = 0.08,
    output: str = None,
) -> str:
    plano = Image.open(ruta_plano).convert("RGBA")
    logo = Image.open(ruta_logo).convert("RGBA")

    # Escalar logo al porcentaje del ancho del plano
    nuevo_ancho_logo = int(plano.width * escala_logo)
    ratio = nuevo_ancho_logo / logo.width
    nuevo_alto_logo = int(logo.height * ratio)
    logo = logo.resize((nuevo_ancho_logo, nuevo_alto_logo), Image.LANCZOS)

    margen = 40
    posiciones = {
        "bottom-right": (plano.width - logo.width - margen, plano.height - logo.height - margen),
        "bottom-left": (margen, plano.height - logo.height - margen),
        "top-right": (plano.width - logo.width - margen, margen),
        "top-left": (margen, margen),
    }
    xy = posiciones.get(posicion, posiciones["bottom-right"])

    plano.paste(logo, xy, mask=logo)
    resultado = plano.convert("RGB")

    salida = output or ruta_plano.replace(".png", "_con_logo.png")
    resultado.save(salida, quality=95)
    return salida


# Procesar todos los planos de una carpeta
from pathlib import Path
for plano in Path("planos_exportados/").glob("*.png"):
    salida = agregar_logo_plano(
        str(plano),
        "assets/logo_estudio.png",
        posicion="bottom-right",
        output=f"planos_entrega/{plano.name}",
    )
    print(f"Listo: {salida}")
```

### 4. Generar imagenes de portada para cursos con texto dinamico

Crea imagenes de portada para modulos de cursos BIM con nombre del modulo y datos del curso.

```python
from PIL import Image, ImageDraw, ImageFont

def generar_portada_modulo(
    titulo: str,
    subtitulo: str,
    numero_modulo: int,
    output: str,
    color_fondo: tuple = (15, 25, 50),
    color_acento: tuple = (0, 180, 255),
) -> None:
    img = Image.new("RGB", (1280, 720), color_fondo)
    draw = ImageDraw.Draw(img)

    # Linea de acento lateral izquierda
    draw.rectangle([60, 80, 70, 640], fill=color_acento)

    # Numero de modulo
    try:
        font_num = ImageFont.truetype("arialbd.ttf", 120)
        font_titulo = ImageFont.truetype("arialbd.ttf", 60)
        font_sub = ImageFont.truetype("arial.ttf", 36)
    except OSError:
        font_num = font_titulo = font_sub = ImageFont.load_default()

    draw.text((100, 100), f"M{numero_modulo:02d}", fill=color_acento, font=font_num)
    draw.text((100, 280), titulo, fill=(255, 255, 255), font=font_titulo)
    draw.text((100, 380), subtitulo, fill=(180, 200, 220), font=font_sub)
    draw.text((100, 650), "Master BIM + IA — Butic The New School", fill=(100, 130, 160), font=font_sub)

    img.save(output, quality=95)
    print(f"Portada generada: {output}")


modulos = [
    ("Fundamentos BIM", "Que es BIM y por que importa en 2025"),
    ("Revit Avanzado", "Familias, parametros y flujos colaborativos"),
    ("Automatizacion con Dynamo", "Visual scripting para tareas repetitivas"),
    ("Power BI para AEC", "Dashboards de proyecto conectados a ACC"),
]

for i, (titulo, sub) in enumerate(modulos, start=1):
    generar_portada_modulo(titulo, sub, i, f"portadas/modulo_{i:02d}.jpg")
```

---

## Notas

- Pillow no modifica el archivo original; siempre usar `.save()` a una nueva ruta para preservar originals.
- Para imagenes TIFF de alta resolucion de planos (>10,000px), usar `Image.MAX_IMAGE_PIXELS = None` con cuidado — solo en archivos de confianza.
- `LANCZOS` (antes `ANTIALIAS`) es el filtro de mayor calidad para resize; usar para outputs finales.
- Para operaciones en batch de muchas imagenes, considerar `concurrent.futures.ThreadPoolExecutor` para paralelizar.
- Pillow soporta lectura de PDFs de una pagina via `pdf2image` (requiere poppler) para procesar planos exportados como PDF.
