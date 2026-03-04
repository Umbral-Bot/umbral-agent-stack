---
name: svgwrite
description: >-
  Generación programática de SVG vectoriales con svgwrite: diagramas técnicos,
  plantas esquemáticas, leyendas de proyectos e infografías vectoriales.
  Ideal para generar planos simplificados desde datos BIM, visualizar
  estadísticas de proyectos y crear materiales gráficos escalables.
  Usar cuando: "generar SVG", "diagrama vectorial", "plano esquemático",
  "infografía técnica", "leyenda de proyecto", "gráfico vectorial".
metadata:
  openclaw:
    emoji: "\U0001F4D0"
    requires:
      env: []
---

# svgwrite — Diagramas Vectoriales con Python

`svgwrite` permite generar archivos SVG (Scalable Vector Graphics) desde
Python sin dependencias externas. Los SVG son vectoriales: escalan sin
pérdida y son editables en Illustrator, Inkscape o directamente en web.

## Instalación

```bash
pip install svgwrite
```

## Casos de uso

### 1. Planta esquemática de distribución de espacios BIM

Genera un diagrama vectorial simplificado de la distribución de espacios
de un proyecto desde datos exportados del modelo BIM (áreas y nombres).

```python
import svgwrite

def generar_planta_esquematica(
    espacios: list[dict],
    archivo_salida: str = "planta_esquematica.svg",
    ancho_lienzo: int = 800,
    alto_lienzo: int = 600,
) -> None:
    """
    espacios = [
        {"nombre": "Recepción", "x": 10, "y": 10, "ancho": 150, "alto": 100, "area_m2": 15},
        {"nombre": "Sala reuniones", "x": 170, "y": 10, "ancho": 200, "alto": 150, "area_m2": 30},
    ]
    """
    dwg = svgwrite.Drawing(archivo_salida, size=(ancho_lienzo, alto_lienzo), profile="full")

    # Fondo
    dwg.add(dwg.rect(insert=(0, 0), size=(ancho_lienzo, alto_lienzo), fill="#f5f5f0"))

    colores = ["#4A90D9", "#E87722", "#2ECC71", "#9B59B6", "#E74C3C", "#1ABC9C"]

    for i, esp in enumerate(espacios):
        color = colores[i % len(colores)]
        # Rectángulo del espacio
        dwg.add(dwg.rect(
            insert=(esp["x"], esp["y"]),
            size=(esp["ancho"], esp["alto"]),
            fill=color,
            fill_opacity=0.3,
            stroke=color,
            stroke_width=2,
        ))
        # Nombre del espacio
        cx = esp["x"] + esp["ancho"] / 2
        cy = esp["y"] + esp["alto"] / 2 - 8
        dwg.add(dwg.text(
            esp["nombre"],
            insert=(cx, cy),
            text_anchor="middle",
            font_size="11px",
            font_family="Arial",
            font_weight="bold",
            fill="#333",
        ))
        # Área
        dwg.add(dwg.text(
            f"{esp['area_m2']} m²",
            insert=(cx, cy + 16),
            text_anchor="middle",
            font_size="10px",
            font_family="Arial",
            fill="#555",
        ))

    dwg.save()
    print(f"Planta generada: {archivo_salida}")

espacios = [
    {"nombre": "Recepción", "x": 20, "y": 20, "ancho": 160, "alto": 100, "area_m2": 16},
    {"nombre": "Sala Reuniones", "x": 200, "y": 20, "ancho": 220, "alto": 150, "area_m2": 33},
    {"nombre": "Oficina BIM", "x": 440, "y": 20, "ancho": 180, "alto": 120, "area_m2": 21.6},
    {"nombre": "Archivo", "x": 20, "y": 140, "ancho": 160, "alto": 80, "area_m2": 12.8},
]
generar_planta_esquematica(espacios)
```

### 2. Leyenda de colores para planos BIM

Crea automáticamente una leyenda vectorial para planos codificados por
colores según uso de espacio (estándar ISO 11442 / BIM Level 2).

```python
import svgwrite

def generar_leyenda_bim(
    categorias: list[dict],
    archivo_salida: str = "leyenda_bim.svg",
) -> None:
    """
    categorias = [
        {"nombre": "Área Húmeda", "color": "#4A90D9"},
        {"nombre": "Área Seca", "color": "#E87722"},
        ...
    ]
    """
    alto_item = 36
    padding = 12
    alto_total = len(categorias) * alto_item + padding * 2 + 30
    ancho_total = 260

    dwg = svgwrite.Drawing(archivo_salida, size=(ancho_total, alto_total), profile="full")

    # Fondo con borde
    dwg.add(dwg.rect(
        insert=(0, 0), size=(ancho_total, alto_total),
        fill="white", stroke="#ccc", stroke_width=1,
        rx=4, ry=4,
    ))

    # Título
    dwg.add(dwg.text(
        "LEYENDA — Usos de Espacio",
        insert=(ancho_total / 2, padding + 14),
        text_anchor="middle",
        font_size="13px",
        font_family="Arial",
        font_weight="bold",
        fill="#222",
    ))

    for i, cat in enumerate(categorias):
        y = padding + 30 + i * alto_item
        # Cuadrado de color
        dwg.add(dwg.rect(
            insert=(padding, y), size=(20, 20),
            fill=cat["color"], stroke="#999", stroke_width=0.5,
        ))
        # Etiqueta
        dwg.add(dwg.text(
            cat["nombre"],
            insert=(padding + 28, y + 14),
            font_size="12px",
            font_family="Arial",
            fill="#333",
        ))

    dwg.save()
    print(f"Leyenda generada: {archivo_salida}")

categorias = [
    {"nombre": "Área Húmeda (baños, cocinas)", "color": "#4A90D9"},
    {"nombre": "Área Seca (oficinas, salas)", "color": "#E87722"},
    {"nombre": "Circulación (pasillos, escaleras)", "color": "#2ECC71"},
    {"nombre": "Servicios (instalaciones)", "color": "#9B59B6"},
    {"nombre": "Estructura (muros, pilares)", "color": "#95A5A6"},
]
generar_leyenda_bim(categorias)
```

### 3. Gráfico de barras de presupuesto por partida

Visualiza la distribución del presupuesto de obra como gráfico de barras
vectorial para incluir en informes y presentaciones de proyecto.

```python
import svgwrite

def grafico_presupuesto(
    partidas: dict[str, float],
    archivo_salida: str = "presupuesto_partidas.svg",
) -> None:
    ancho = 600
    alto = 400
    margen = {"top": 50, "bottom": 80, "left": 160, "right": 30}
    dwg = svgwrite.Drawing(archivo_salida, size=(ancho, alto), profile="full")
    dwg.add(dwg.rect(insert=(0, 0), size=(ancho, alto), fill="white"))

    # Título
    dwg.add(dwg.text(
        "Presupuesto por Partida (USD)",
        insert=(ancho / 2, 30),
        text_anchor="middle", font_size="16px",
        font_family="Arial", font_weight="bold", fill="#222",
    ))

    nombres = list(partidas.keys())
    valores = list(partidas.values())
    max_val = max(valores)
    area_ancho = ancho - margen["left"] - margen["right"]
    area_alto = alto - margen["top"] - margen["bottom"]
    barra_alto = area_alto / len(nombres) * 0.7
    espacio = area_alto / len(nombres)

    colores = ["#4A90D9", "#E87722", "#2ECC71", "#9B59B6", "#E74C3C"]

    for i, (nombre, valor) in enumerate(partidas.items()):
        y = margen["top"] + i * espacio + (espacio - barra_alto) / 2
        barra_ancho = (valor / max_val) * area_ancho

        dwg.add(dwg.rect(
            insert=(margen["left"], y),
            size=(barra_ancho, barra_alto),
            fill=colores[i % len(colores)],
            fill_opacity=0.85,
        ))
        # Etiqueta izquierda
        dwg.add(dwg.text(
            nombre,
            insert=(margen["left"] - 8, y + barra_alto / 2 + 4),
            text_anchor="end", font_size="11px",
            font_family="Arial", fill="#333",
        ))
        # Valor derecha
        dwg.add(dwg.text(
            f"${valor:,.0f}",
            insert=(margen["left"] + barra_ancho + 6, y + barra_alto / 2 + 4),
            font_size="11px", font_family="Arial", fill="#555",
        ))

    dwg.save()
    print(f"Gráfico generado: {archivo_salida}")

partidas = {
    "Estructura": 320000,
    "Mampostería": 85000,
    "Instalaciones": 120000,
    "Carpintería": 65000,
    "Acabados": 95000,
}
grafico_presupuesto(partidas)
```

## Notas

- SVG es un formato XML: editable en cualquier editor de texto o Inkscape.
- `profile="full"` habilita todas las características SVG; `"tiny"` es más restrictivo.
- Para convertir SVG a PNG/PDF se puede usar CairoSVG: `pip install cairosvg`.
- Docs oficiales: https://svgwrite.readthedocs.io/
