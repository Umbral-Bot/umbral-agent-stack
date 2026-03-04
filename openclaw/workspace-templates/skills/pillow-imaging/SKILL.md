---
name: pillow-imaging
description: >-
  Manipulación y procesamiento de imágenes con Pillow (PIL): batch resize,
  crop, filtros, compositing, generación de thumbnails y watermarks.
  Ideal para procesar renders de proyectos, planos escaneados y portfolios
  en lote. Usar cuando: "redimensionar imágenes", "batch de renders",
  "agregar watermark", "procesar fotos de obra", "optimizar imágenes".
metadata:
  openclaw:
    emoji: "\U0001F5BC\uFE0F"
    requires:
      env: []
---

# Pillow — Procesamiento de Imágenes con Python

Pillow (PIL fork) es la librería estándar de Python para manipular imágenes:
resize, crop, filtros, compositing y generación programática. Perfecta para
automatizar el procesamiento de renders y materiales gráficos de proyectos.

## Instalación

```bash
pip install pillow
```

## Casos de uso

### 1. Batch resize de renders para portfolio web

Procesa toda una carpeta de renders al tamaño óptimo para web, preservando
la proporción y aplicando compresión para carga rápida.

```python
from pathlib import Path
from PIL import Image

def optimizar_renders_para_web(
    carpeta_entrada: str = "renders/",
    carpeta_salida: str = "renders_web/",
    ancho_max: int = 1920,
    calidad: int = 85,
) -> None:
    entrada = Path(carpeta_entrada)
    salida = Path(carpeta_salida)
    salida.mkdir(exist_ok=True)

    for archivo in entrada.glob("*.{png,jpg,jpeg,PNG,JPG}"):
        with Image.open(archivo) as img:
            # Convertir a RGB si es RGBA (transparencia)
            if img.mode == "RGBA":
                img = img.convert("RGB")
            # thumbnail preserva proporción
            img.thumbnail((ancho_max, ancho_max), Image.LANCZOS)
            destino = salida / archivo.with_suffix(".jpg").name
            img.save(destino, "JPEG", quality=calidad, optimize=True)
            print(f"✓ {archivo.name} → {destino.name} ({img.size})")

optimizar_renders_para_web()
```

### 2. Agregar watermark de consultoría a renders

Estampa el logo de la empresa o texto de copyright sobre renders de proyectos.

```python
from PIL import Image, ImageDraw, ImageFont

def agregar_watermark(
    ruta_imagen: str,
    texto: str = "© Consultoría BIM | David Architect",
    opacidad: int = 128,
) -> Image.Image:
    with Image.open(ruta_imagen).convert("RGBA") as base:
        overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        # Intentar cargar fuente del sistema, fallback a default
        try:
            font = ImageFont.truetype("Arial.ttf", size=36)
        except OSError:
            font = ImageFont.load_default()

        # Posición: esquina inferior derecha
        bbox = draw.textbbox((0, 0), texto, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = base.width - w - 20
        y = base.height - h - 20

        draw.text((x, y), texto, font=font, fill=(255, 255, 255, opacidad))
        resultado = Image.alpha_composite(base, overlay)
        return resultado.convert("RGB")

img = agregar_watermark("render_fachada.png")
img.save("render_fachada_firmado.jpg", quality=92)
```

### 3. Collage de vistas de proyecto

Crea una imagen comparativa con las 4 vistas estándar (planta, fachadas) para
incluir en informes o presentaciones.

```python
from PIL import Image

def crear_collage_vistas(
    vistas: dict[str, str],
    ancho_total: int = 2400,
    padding: int = 10,
) -> Image.Image:
    """
    vistas = {"Planta": "planta.png", "Norte": "fachada_n.png",
              "Sur": "fachada_s.png", "Isometría": "iso.png"}
    """
    alto_celda = ancho_total // 2 - padding
    ancho_celda = ancho_total // 2 - padding
    lienzo = Image.new("RGB", (ancho_total, ancho_total), (240, 240, 240))

    posiciones = [(0, 0), (ancho_celda + padding, 0),
                  (0, alto_celda + padding), (ancho_celda + padding, alto_celda + padding)]

    for (nombre, ruta), (x, y) in zip(vistas.items(), posiciones):
        with Image.open(ruta) as img:
            img.thumbnail((ancho_celda, alto_celda), Image.LANCZOS)
            lienzo.paste(img, (x, y))

    return lienzo

vistas = {
    "Planta": "planta_baja.png",
    "Norte": "fachada_norte.png",
    "Sur": "fachada_sur.png",
    "Isometría": "isometria.png",
}
collage = crear_collage_vistas(vistas)
collage.save("vistas_proyecto.jpg", quality=90)
```

## Notas

- `Image.thumbnail()` preserva la relación de aspecto (a diferencia de `resize()`).
- Para RGBA (PNG con transparencia) convertir a RGB antes de guardar como JPEG.
- `ImageFilter` ofrece filtros como `SHARPEN`, `BLUR`, `EDGE_ENHANCE`.
- Docs oficiales: https://pillow.readthedocs.io/
