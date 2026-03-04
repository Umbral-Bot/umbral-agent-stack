---
name: svgwrite
description: >-
  Generar graficos SVG vectoriales programaticamente con svgwrite. Crear diagramas
  tecnicos, planos esquematicos, infografias vectoriales, planos de piso simplificados
  y graficos de datos para propuestas BIM. Ideal para generar assets visuales desde
  datos de proyectos sin necesidad de Illustrator o Inkscape.
  Use when "generar SVG", "diagrama vectorial", "plano esquematico python",
  "grafico tecnico vectorial", "infografia SVG", "generar plano desde datos".
metadata:
  openclaw:
    emoji: "\U0001F4D0"
    requires:
      env: []
---

# svgwrite — Graficos Vectoriales SVG con Python

svgwrite genera archivos SVG (Scalable Vector Graphics) de forma programatica. Los SVG son vectoriales, escalables a cualquier resolucion y editables en Illustrator, Inkscape, o directamente en navegadores y Notion.

**Docs oficiales:** https://svgwrite.readthedocs.io/

## Instalacion

**Instalacion:**
```bash
pip install svgwrite
# Para exportar SVG a PNG/PDF (opcional):
pip install cairosvg
```

---

## Casos de uso

### 1. Plano de piso esquematico desde datos de Revit/IFC

Genera un plano simplificado de planta desde datos exportados de un modelo BIM:

```python
import svgwrite
from dataclasses import dataclass

@dataclass
class Recinto:
    nombre: str
    x: float      # metros
    y: float
    ancho: float
    alto: float
    tipo: str     # "habitacion", "bano", "cocina", "circulacion"

COLORES_TIPO = {
    "habitacion": "#D4E6F1",
    "bano": "#D5F5E3",
    "cocina": "#FDEBD0",
    "circulacion": "#F5F5F5",
    "sala": "#EBF5FB",
}

def generar_plano_piso(recintos: list[Recinto], salida: str, escala: float = 50.0):
    """
    Genera plano de piso SVG desde lista de recintos.
    escala: pixeles por metro (50px/m = 1:20 aprox)
    """
    # Calcular dimensiones totales
    max_x = max(r.x + r.ancho for r in recintos) * escala + 60
    max_y = max(r.y + r.alto for r in recintos) * escala + 60

    dwg = svgwrite.Drawing(salida, size=(f"{max_x}px", f"{max_y}px"), profile="full")

    # Fondo
    dwg.add(dwg.rect(insert=(0, 0), size=("100%", "100%"), fill="white"))

    # Recintos
    for r in recintos:
        px = r.x * escala + 30
        py = r.y * escala + 30
        pw = r.ancho * escala
        ph = r.alto * escala
        color = COLORES_TIPO.get(r.tipo, "#EEEEEE")

        # Rectangulo relleno
        dwg.add(dwg.rect(
            insert=(px, py),
            size=(pw, ph),
            fill=color,
            stroke="#333333",
            stroke_width=1.5
        ))

        # Etiqueta centrada
        dwg.add(dwg.text(
            r.nombre,
            insert=(px + pw / 2, py + ph / 2),
            text_anchor="middle",
            dominant_baseline="middle",
            font_size="11px",
            font_family="Arial, sans-serif",
            fill="#333333"
        ))

    # Titulo
    dwg.add(dwg.text(
        "Planta Esquematica — Nivel 1",
        insert=(30, 20),
        font_size="14px",
        font_family="Arial, sans-serif",
        font_weight="bold",
        fill="#1A1A1A"
    ))

    dwg.save()
    print(f"Plano guardado: {salida}")


# Ejemplo de uso con datos de proyecto
recintos_proyecto = [
    Recinto("Sala Reuniones", 0, 0, 8, 5, "sala"),
    Recinto("Oficina Principal", 8, 0, 6, 5, "habitacion"),
    Recinto("Cocina", 0, 5, 4, 3, "cocina"),
    Recinto("Bano", 4, 5, 2, 3, "bano"),
    Recinto("Corredor", 6, 5, 8, 3, "circulacion"),
]
generar_plano_piso(recintos_proyecto, "planta_esquematica.svg")
```

### 2. Grafico de barras para propuesta de consultoria — KPIs de impacto

Genera un infografico vectorial de resultados para incluir en propuestas:

```python
import svgwrite

def grafico_barras_kpi(
    datos: list[tuple[str, float, str]],  # (label, valor_pct, color)
    titulo: str,
    salida: str
):
    """Genera grafico de barras horizontales para KPIs de propuesta."""
    ANCHO = 700
    ALTO = 80 + len(datos) * 70
    BAR_MAX = 400
    OFFSET_X = 200

    dwg = svgwrite.Drawing(salida, size=(f"{ANCHO}px", f"{ALTO}px"), profile="full")
    dwg.add(dwg.rect(insert=(0, 0), size=("100%", "100%"), fill="#FAFAFA"))

    # Titulo
    dwg.add(dwg.text(
        titulo,
        insert=(ANCHO / 2, 40),
        text_anchor="middle",
        font_size="18px",
        font_family="Arial, sans-serif",
        font_weight="bold",
        fill="#1A365D"
    ))

    for i, (label, valor_pct, color) in enumerate(datos):
        y_base = 70 + i * 70
        barra_ancho = BAR_MAX * (valor_pct / 100)

        # Etiqueta izquierda
        dwg.add(dwg.text(
            label,
            insert=(OFFSET_X - 10, y_base + 20),
            text_anchor="end",
            font_size="13px",
            font_family="Arial, sans-serif",
            fill="#333333"
        ))

        # Fondo de barra (gris claro)
        dwg.add(dwg.rect(
            insert=(OFFSET_X, y_base),
            size=(BAR_MAX, 35),
            fill="#E2E8F0",
            rx=4, ry=4
        ))

        # Barra de valor
        dwg.add(dwg.rect(
            insert=(OFFSET_X, y_base),
            size=(barra_ancho, 35),
            fill=color,
            rx=4, ry=4
        ))

        # Valor en texto
        dwg.add(dwg.text(
            f"{int(valor_pct)}%",
            insert=(OFFSET_X + barra_ancho + 8, y_base + 22),
            font_size="14px",
            font_family="Arial, sans-serif",
            font_weight="bold",
            fill=color
        ))

    dwg.save()
    print(f"Grafico guardado: {salida}")


# Caso de exito OXXO Chile para propuesta
grafico_barras_kpi(
    datos=[
        ("Reduccion costos", 40, "#2ECC71"),
        ("Reduccion tiempos", 20, "#3498DB"),
        ("Tareas automatizadas", 60, "#9B59B6"),
        ("Mas proyectos/anio", 80, "#E67E22"),
    ],
    titulo="Resultados — OXXO Chile 2022-2024",
    salida="kpis_oxxo_chile.svg"
)
```

### 3. Diagrama de fases de proyecto — cronograma tipo Gantt simplificado

Genera un Gantt vectorial para incluir en propuestas de consultoria:

```python
import svgwrite
from datetime import date, timedelta

def gantt_simple(
    tareas: list[tuple[str, int, int]],  # (nombre, semana_inicio, duracion_semanas)
    titulo: str,
    salida: str,
    total_semanas: int = 12
):
    """Genera Gantt simplificado en SVG para propuestas."""
    ANCHO = 900
    FILA_H = 45
    OFFSET_X = 200
    BARRA_W = (ANCHO - OFFSET_X - 30) / total_semanas
    ALTO = 80 + len(tareas) * FILA_H + 40

    COLORES = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899"]

    dwg = svgwrite.Drawing(salida, size=(f"{ANCHO}px", f"{ALTO}px"), profile="full")
    dwg.add(dwg.rect(insert=(0, 0), size=("100%", "100%"), fill="white"))

    # Titulo
    dwg.add(dwg.text(
        titulo,
        insert=(ANCHO / 2, 35),
        text_anchor="middle",
        font_size="16px",
        font_family="Arial, sans-serif",
        font_weight="bold",
        fill="#1E293B"
    ))

    # Encabezados de semanas
    for s in range(total_semanas):
        x = OFFSET_X + s * BARRA_W
        dwg.add(dwg.text(
            f"S{s + 1}",
            insert=(x + BARRA_W / 2, 65),
            text_anchor="middle",
            font_size="10px",
            font_family="Arial, sans-serif",
            fill="#64748B"
        ))
        dwg.add(dwg.line(
            start=(x, 55), end=(x, ALTO - 20),
            stroke="#E2E8F0", stroke_width=0.5
        ))

    # Tareas
    for i, (nombre, inicio, duracion) in enumerate(tareas):
        y = 75 + i * FILA_H
        color = COLORES[i % len(COLORES)]

        # Etiqueta
        dwg.add(dwg.text(
            nombre,
            insert=(OFFSET_X - 10, y + 22),
            text_anchor="end",
            font_size="12px",
            font_family="Arial, sans-serif",
            fill="#374151"
        ))

        # Barra del Gantt
        bx = OFFSET_X + inicio * BARRA_W
        bw = duracion * BARRA_W - 3
        dwg.add(dwg.rect(
            insert=(bx, y + 5),
            size=(bw, 28),
            fill=color,
            rx=3, ry=3,
            opacity=0.85
        ))

    dwg.save()
    print(f"Gantt guardado: {salida}")


gantt_simple(
    tareas=[
        ("Diagnostico BIM", 0, 2),
        ("Modelado Base", 2, 3),
        ("Coordinacion", 3, 3),
        ("Clash Detection", 5, 2),
        ("Capacitacion", 6, 2),
        ("Entrega Final", 8, 1),
    ],
    titulo="Plan de Implementacion BIM — Proyecto XYZ",
    salida="gantt_proyecto.svg"
)
```

## Elementos SVG disponibles en svgwrite

```python
# Formas basicas
dwg.add(dwg.rect(insert=(x, y), size=(w, h), fill="blue", stroke="black", stroke_width=1))
dwg.add(dwg.circle(center=(cx, cy), r=radio, fill="red"))
dwg.add(dwg.line(start=(x1, y1), end=(x2, y2), stroke="black", stroke_width=1.5))
dwg.add(dwg.ellipse(center=(cx, cy), r=(rx, ry), fill="green"))

# Texto
dwg.add(dwg.text("Hola", insert=(x, y), font_size="14px", font_family="Arial", fill="black"))

# Polilínea y poligono
dwg.add(dwg.polyline(points=[(0,0),(10,20),(20,0)], stroke="blue", fill="none"))
dwg.add(dwg.polygon(points=[(0,0),(10,20),(20,0)], fill="yellow"))

# Path (curvas bezier)
dwg.add(dwg.path(d="M 0 0 C 10 10 20 10 30 0", stroke="black", fill="none"))

# Grupos (para transformaciones en conjunto)
g = dwg.g(transform="translate(100, 50)")
g.add(dwg.rect(insert=(0, 0), size=(50, 30)))
dwg.add(g)
```

## Convertir SVG a PNG con cairosvg

```python
import cairosvg

# SVG a PNG (para Notion, Word, presentaciones)
cairosvg.svg2png(url="diagrama.svg", write_to="diagrama.png", scale=2.0)

# SVG a PDF (para impresion y documentos tecnicos)
cairosvg.svg2pdf(url="gantt_proyecto.svg", write_to="gantt_proyecto.pdf")
```

## Notas

- svgwrite 1.4.3 es estable y sin dependencias externas (pure Python)
- Los SVG generados son editables directamente en Inkscape o Illustrator
- Para embeber en HTML/Notion: guardar como `.svg` y subir directamente
- Combinar con datos de Revit/Excel: leer datos → generar SVG → exportar a PNG con cairosvg
- Para fuentes personalizadas en SVG, embeber el font-face en el archivo o usar Google Fonts URL
