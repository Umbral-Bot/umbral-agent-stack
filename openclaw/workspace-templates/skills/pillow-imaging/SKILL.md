---
name: pillow-imaging
description: >-
  Procesamiento y manipulacion de imagenes con Pillow (PIL Fork). Resize, crop,
  filtros, compositing, watermark, batch processing. Ideal para procesar renders
  de proyectos, planos, presentaciones en batch y generar materiales de marketing.
  Use when "procesar imagenes", "batch resize", "agregar watermark", "resize renders",
  "compositing imagenes", "convertir formato imagen", "thumbnail automatico".
metadata:
  openclaw:
    emoji: "\U0001F5BC"
    requires:
      env: []
---

# Pillow — Procesamiento de Imagenes con Python

Pillow es el fork activo de PIL (Python Imaging Library). Permite abrir, manipular y guardar imagenes en mas de 30 formatos. Esencial para procesar renders, planos y materiales visuales de forma automatizada.

**Docs oficiales:** https://pillow.readthedocs.io/

## Instalacion

```bash
pip install Pillow
```

---

## Casos de uso

### 1. Batch resize de renders — preparar carpeta para entrega a cliente

Redimensiona todos los renders de un proyecto manteniendo proporcion:

```python
from PIL import Image
from pathlib import Path

def batch_resize_renders(carpeta_entrada: str, carpeta_salida: str, ancho_max: int = 1920):
    """Redimensiona renders a ancho maximo preservando aspect ratio."""
    entrada = Path(carpeta_entrada)
    salida = Path(carpeta_salida)
    salida.mkdir(parents=True, exist_ok=True)

    formatos_validos = {".jpg", ".jpeg", ".png", ".tiff", ".tif"}

    for archivo in entrada.iterdir():
        if archivo.suffix.lower() not in formatos_validos:
            continue

        with Image.open(archivo) as img:
            # Calcular nueva altura manteniendo aspect ratio
            ratio = ancho_max / img.width
            nueva_altura = int(img.height * ratio)

            img_resized = img.resize(
                (ancho_max, nueva_altura),
                Image.Resampling.LANCZOS
            )

            # Convertir a RGB si es RGBA (PNG con transparencia)
            if img_resized.mode == "RGBA":
                img_resized = img_resized.convert("RGB")

            destino = salida / f"{archivo.stem}_1920.jpg"
            img_resized.save(destino, "JPEG", quality=90, optimize=True)
            print(f"OK: {archivo.name} → {destino.name}")


batch_resize_renders("renders/originales", "renders/entrega_cliente")
```

### 2. Agregar watermark con logo al portfolio de imagenes

Marca todas las imagenes del proyecto con el logo de la consultoria:

```python
from PIL import Image
from pathlib import Path

def agregar_watermark(carpeta: str, logo_path: str, opacidad: float = 0.6):
    """Agrega logo como watermark en esquina inferior derecha."""
    logo_original = Image.open(logo_path).convert("RGBA")

    # Redimensionar logo al 15% del ancho de la imagen destino
    for archivo in Path(carpeta).glob("*.jpg"):
        with Image.open(archivo).convert("RGBA") as base:
            # Escalar logo proporcional a la imagen
            escala = int(base.width * 0.15)
            ratio = escala / logo_original.width
            logo = logo_original.resize(
                (escala, int(logo_original.height * ratio)),
                Image.Resampling.LANCZOS
            )

            # Ajustar opacidad del logo
            r, g, b, a = logo.split()
            a = a.point(lambda x: int(x * opacidad))
            logo.putalpha(a)

            # Posicion: margen 20px desde esquina inferior derecha
            margen = 20
            pos_x = base.width - logo.width - margen
            pos_y = base.height - logo.height - margen

            base.paste(logo, (pos_x, pos_y), logo)

            # Guardar como JPG (sin canal alpha)
            base.convert("RGB").save(archivo, "JPEG", quality=92)
            print(f"Watermark aplicado: {archivo.name}")


agregar_watermark("portfolio/", "logo_consultoria.png", opacidad=0.7)
```

### 3. Generar thumbnails automaticos para catalogo web o Notion

Crea una galeria de miniaturas de renders para cargar en Notion o web:

```python
from PIL import Image
from pathlib import Path

def generar_thumbnails(carpeta_renders: str, tamano: tuple = (400, 300)):
    """Genera thumbnails con recorte centrado (sin deformacion)."""
    carpeta = Path(carpeta_renders)
    thumbs_dir = carpeta / "thumbnails"
    thumbs_dir.mkdir(exist_ok=True)

    for archivo in carpeta.glob("*.png"):
        with Image.open(archivo) as img:
            # thumbnail() mantiene aspect ratio y NO agranda la imagen
            img_thumb = img.copy()
            img_thumb.thumbnail(tamano, Image.Resampling.LANCZOS)

            # Centrar en canvas exacto del tamano deseado
            canvas = Image.new("RGB", tamano, (255, 255, 255))
            offset_x = (tamano[0] - img_thumb.width) // 2
            offset_y = (tamano[1] - img_thumb.height) // 2
            canvas.paste(
                img_thumb.convert("RGB"),
                (offset_x, offset_y)
            )

            destino = thumbs_dir / f"thumb_{archivo.name.replace('.png', '.jpg')}"
            canvas.save(destino, "JPEG", quality=85)

    print(f"Thumbnails generados en: {thumbs_dir}")


generar_thumbnails("renders/proyecto_actual/")
```

### 4. Compositing — montar render sobre plantilla de presentacion

Insertar render en plantilla PDF-ready con datos del proyecto:

```python
from PIL import Image, ImageDraw, ImageFont

def crear_lamina_presentacion(
    render_path: str,
    nombre_proyecto: str,
    cliente: str,
    salida: str
):
    """Crea lamina A4 horizontal con render + datos del proyecto."""
    A4_LANDSCAPE = (3508, 2480)  # 300 DPI
    MARGEN = 80

    # Fondo blanco
    lamina = Image.new("RGB", A4_LANDSCAPE, (255, 255, 255))
    draw = ImageDraw.Draw(lamina)

    # Barra lateral izquierda (branding)
    draw.rectangle([(0, 0), (400, A4_LANDSCAPE[1])], fill=(30, 50, 80))

    # Cargar render y ajustar al area disponible
    with Image.open(render_path) as render:
        area_render = (A4_LANDSCAPE[0] - 400 - MARGEN * 2, A4_LANDSCAPE[1] - MARGEN * 2)
        render.thumbnail(area_render, Image.Resampling.LANCZOS)
        lamina.paste(render, (400 + MARGEN, MARGEN))

    # Texto en barra lateral (requiere fuente instalada o usar default)
    try:
        fuente_titulo = ImageFont.truetype("arial.ttf", 60)
        fuente_datos = ImageFont.truetype("arial.ttf", 36)
    except OSError:
        fuente_titulo = ImageFont.load_default()
        fuente_datos = fuente_titulo

    draw.text((40, 200), nombre_proyecto, font=fuente_titulo, fill="white")
    draw.text((40, 320), f"Cliente: {cliente}", font=fuente_datos, fill=(200, 220, 240))

    lamina.save(salida, "PNG", dpi=(300, 300))
    print(f"Lamina guardada: {salida}")


crear_lamina_presentacion(
    render_path="renders/exterior_01.jpg",
    nombre_proyecto="Torre Residencial\nSantiago Centro",
    cliente="Inmobiliaria XYZ",
    salida="laminas/lamina_01.png"
)
```

## Formatos de imagen soportados

| Formato | Extension | Uso en AEC |
|---------|-----------|------------|
| JPEG | `.jpg` | Renders, fotos de obra, presupuestos |
| PNG | `.png` | Planos con transparencia, diagramas |
| TIFF | `.tif` | Renders de alta calidad, impresion |
| WebP | `.webp` | Web, Notion, newsletters |
| PDF | `.pdf` | Solo apertura, no creacion compleja |

## Modos de color importantes

```python
img.mode          # "RGB", "RGBA", "L" (gris), "CMYK"
img.convert("RGB")    # Para guardar como JPG (requiere RGB)
img.convert("RGBA")   # Para trabajar con transparencia
img.convert("L")      # Escala de grises
```

## Notas

- Pillow 10+ renombro `Image.ANTIALIAS` a `Image.Resampling.LANCZOS`
- Para batch processing de cientos de imagenes, usar `with Image.open()` para liberar memoria
- CMYK es comun en renders de alta gama; convertir a RGB antes de guardar como JPG web
- ImageFont requiere archivos `.ttf` instalados en el sistema
