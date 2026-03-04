---
name: svgwrite
description: >-
  Generar archivos SVG programaticamente con Python usando svgwrite: diagramas
  tecnicos vectoriales, planos esquematicos, infografias, leyendas de proyecto
  y visualizaciones de datos BIM. Los SVG son escalables, editables en Inkscape
  y exportables a PDF.
  Use when "generar SVG", "diagrama vectorial", "plano esquematico Python",
  "infografia tecnica", "leyenda proyecto", "diagramas tecnicos SVG",
  "generar plano Python", "visualizacion vectorial", "SVG programatico".
metadata:
  openclaw:
    emoji: "\U0001F4D0"
    requires:
      env: []
---

# svgwrite — Generacion de SVG Programatico

`svgwrite` es una libreria Python para crear graficos vectoriales escalables (SVG) desde codigo. Los SVG son ideales para diagramas tecnicos porque son infinitamente escalables, editables en Inkscape/Illustrator y se pueden embeber directamente en HTML o exportar a PDF vectorial.

**Instalacion:**
```bash
pip install svgwrite
# Para convertir SVG a PDF (opcional):
pip install cairosvg
```

**Docs oficiales:** https://svgwrite.readthedocs.io/

---

## Casos de uso para David (BIM / Consultoría / Docencia)

### 1. Generar plano esquematico de zonificacion de planta

Genera un plano de zonificacion con colores por uso (oficinas, circulacion, servicios) a partir de datos estructurados.

```python
import svgwrite
from dataclasses import dataclass

@dataclass
class Zona:
    nombre: str
    x: float
    y: float
    ancho: float
    alto: float
    color: str
    uso: str

def generar_plano_zonificacion(
    zonas: list[Zona],
    titulo: str,
    output: str = "zonificacion.svg",
    escala_px_por_m: float = 30,
) -> None:
    margen = 60
    max_x = max(z.x + z.ancho for z in zonas) * escala_px_por_m + 2 * margen
    max_y = max(z.y + z.alto for z in zonas) * escala_px_por_m + 2 * margen + 80

    dwg = svgwrite.Drawing(output, size=(f"{max_x}px", f"{max_y}px"))
    dwg.viewbox(0, 0, max_x, max_y)

    # Fondo
    dwg.add(dwg.rect(insert=(0, 0), size=(max_x, max_y), fill="#f8f8f8"))

    # Titulo
    dwg.add(dwg.text(titulo, insert=(margen, 35), font_size=22,
                     font_family="Arial", font_weight="bold", fill="#1a1a2e"))

    # Escala indicativa
    dwg.add(dwg.text(f"Escala referencial: 1m = {escala_px_por_m}px",
                     insert=(margen, 55), font_size=11, font_family="Arial", fill="#666"))

    # Zonas
    for zona in zonas:
        px = margen + zona.x * escala_px_por_m
        py = 70 + zona.y * escala_px_por_m
        pw = zona.ancho * escala_px_por_m
        ph = zona.alto * escala_px_por_m

        grupo = dwg.g(id=f"zona_{zona.nombre.replace(' ', '_')}")
        grupo.add(dwg.rect(insert=(px, py), size=(pw, ph),
                           fill=zona.color, stroke="#333", stroke_width=1.5,
                           fill_opacity=0.75, rx=3))
        # Etiqueta centrada
        cx, cy = px + pw / 2, py + ph / 2 - 8
        grupo.add(dwg.text(zona.nombre, insert=(cx, cy),
                           text_anchor="middle", font_size=12,
                           font_family="Arial", font_weight="bold", fill="#1a1a1a"))
        grupo.add(dwg.text(f"{zona.ancho*zona.alto:.1f} m²",
                           insert=(cx, cy + 16),
                           text_anchor="middle", font_size=10,
                           font_family="Arial", fill="#444"))
        dwg.add(grupo)

    dwg.save(pretty=True)
    print(f"Plano guardado: {output}")


zonas_planta_tipo = [
    Zona("Hall", 0, 0, 4, 3, "#a8d8ea", "Circulacion"),
    Zona("Oficina A", 4, 0, 6, 4, "#b8e0d2", "Oficinas"),
    Zona("Oficina B", 10, 0, 6, 4, "#b8e0d2", "Oficinas"),
    Zona("Sala Reunion", 4, 4, 5, 3, "#ffd6a5", "Reunion"),
    Zona("Servicios", 9, 4, 3, 3, "#e8d5b7", "Servicios"),
    Zona("Bodega", 12, 4, 4, 3, "#d4c5f9", "Almacenamiento"),
]

generar_plano_zonificacion(zonas_planta_tipo, "Zonificacion Planta Tipo — Torre Costanera")
```

### 2. Generar diagrama de flujo de proceso BIM como SVG vectorial

Crea un diagrama de flujo de proceso con flechas, cajas y texto, exportable a PDF para incluir en propuestas.

```python
import svgwrite

def crear_diagrama_flujo(
    pasos: list[dict],
    titulo: str,
    output: str = "flujo_proceso.svg",
) -> None:
    """
    pasos: lista de dicts con keys: nombre, descripcion, color (opcional)
    """
    ANCHO_CAJA = 200
    ALTO_CAJA = 70
    ESPACIO_X = 60
    MARGEN_Y = 100
    ALTO_SVG = 600
    TOTAL_ANCHO = len(pasos) * ANCHO_CAJA + (len(pasos) - 1) * ESPACIO_X + 100

    dwg = svgwrite.Drawing(output, size=(f"{TOTAL_ANCHO}px", f"{ALTO_SVG}px"))
    dwg.viewbox(0, 0, TOTAL_ANCHO, ALTO_SVG)
    dwg.add(dwg.rect(insert=(0, 0), size=(TOTAL_ANCHO, ALTO_SVG), fill="white"))

    # Titulo
    dwg.add(dwg.text(titulo, insert=(TOTAL_ANCHO / 2, 50),
                     text_anchor="middle", font_size=24,
                     font_family="Arial", font_weight="bold", fill="#1a1a2e"))

    PASO_Y = MARGEN_Y + 30
    colores_default = ["#4A90D9", "#50C878", "#F5A623", "#D0021B", "#9B59B6", "#1ABC9C"]

    for i, paso in enumerate(pasos):
        x = 50 + i * (ANCHO_CAJA + ESPACIO_X)
        color = paso.get("color", colores_default[i % len(colores_default)])

        # Caja del paso
        grupo = dwg.g()
        grupo.add(dwg.rect(insert=(x, PASO_Y), size=(ANCHO_CAJA, ALTO_CAJA),
                           rx=8, ry=8, fill=color, stroke="#fff", stroke_width=2))
        # Numero de paso
        grupo.add(dwg.text(f"0{i+1}", insert=(x + 15, PASO_Y + 22),
                           font_size=20, font_family="Arial", font_weight="bold",
                           fill="white", fill_opacity=0.7))
        # Nombre del paso
        grupo.add(dwg.text(paso["nombre"], insert=(x + ANCHO_CAJA / 2, PASO_Y + 40),
                           text_anchor="middle", font_size=14,
                           font_family="Arial", font_weight="bold", fill="white"))
        # Descripcion
        grupo.add(dwg.text(paso.get("descripcion", ""), insert=(x + ANCHO_CAJA / 2, PASO_Y + 56),
                           text_anchor="middle", font_size=11, font_family="Arial", fill="white",
                           fill_opacity=0.9))
        dwg.add(grupo)

        # Flecha entre pasos
        if i < len(pasos) - 1:
            ax = x + ANCHO_CAJA + 5
            ay = PASO_Y + ALTO_CAJA / 2
            bx = ax + ESPACIO_X - 10
            dwg.add(dwg.line(start=(ax, ay), end=(bx, ay),
                             stroke="#999", stroke_width=2))
            # Punta de flecha
            dwg.add(dwg.polygon(points=[(bx, ay), (bx - 10, ay - 6), (bx - 10, ay + 6)],
                                fill="#999"))

    dwg.save(pretty=True)
    print(f"Diagrama guardado: {output}")


pasos_consultoria = [
    {"nombre": "Diagnostico", "descripcion": "Levantamiento procesos"},
    {"nombre": "Plan BIM", "descripcion": "BEP + estandares"},
    {"nombre": "Piloto", "descripcion": "Proyecto prueba"},
    {"nombre": "Capacitacion", "descripcion": "Equipo del cliente"},
    {"nombre": "Entrega", "descripcion": "Documentacion + cierre"},
]
crear_diagrama_flujo(pasos_consultoria, "Proceso de Consultoria BIM", "proceso_bim.svg")
```

### 3. Generar leyenda de colores para planos o presentaciones

Crea una leyenda vectorial reutilizable con los colores de disciplinas BIM para planos de coordinacion.

```python
import svgwrite

def generar_leyenda_bim(
    disciplinas: list[tuple[str, str, str]],
    output: str = "leyenda_bim.svg",
) -> None:
    """
    disciplinas: lista de (nombre, color_hex, descripcion)
    """
    ALTO_ITEM = 36
    PADDING = 16
    ANCHO = 320
    ALTO_TOTAL = len(disciplinas) * ALTO_ITEM + PADDING * 3 + 40

    dwg = svgwrite.Drawing(output, size=(f"{ANCHO}px", f"{ALTO_TOTAL}px"))
    dwg.viewbox(0, 0, ANCHO, ALTO_TOTAL)
    dwg.add(dwg.rect(insert=(0, 0), size=(ANCHO, ALTO_TOTAL), fill="white",
                     stroke="#ddd", stroke_width=1, rx=8))

    dwg.add(dwg.text("LEYENDA — Disciplinas BIM",
                     insert=(ANCHO / 2, 28), text_anchor="middle",
                     font_size=14, font_family="Arial", font_weight="bold", fill="#333"))

    for i, (nombre, color, descripcion) in enumerate(disciplinas):
        y = PADDING * 2 + 30 + i * ALTO_ITEM
        # Cuadrado de color
        dwg.add(dwg.rect(insert=(PADDING, y), size=(22, 22),
                         fill=color, rx=3, stroke="#ccc", stroke_width=0.5))
        # Nombre de disciplina
        dwg.add(dwg.text(nombre, insert=(PADDING + 32, y + 14),
                         font_size=12, font_family="Arial",
                         font_weight="bold", fill="#222"))
        # Descripcion
        if descripcion:
            dwg.add(dwg.text(descripcion, insert=(PADDING + 32, y + 27),
                             font_size=10, font_family="Arial", fill="#666"))

    dwg.save(pretty=True)
    print(f"Leyenda guardada: {output}")


disciplinas_bim = [
    ("ARQ", "#4A90D9", "Arquitectura"),
    ("EST", "#F5A623", "Estructura"),
    ("MEP", "#7ED321", "Mecanica, Electrica, Plomeria"),
    ("CIV", "#D0021B", "Obras Civiles"),
    ("INT", "#9B59B6", "Interiorismo"),
    ("PAI", "#1ABC9C", "Paisajismo"),
]
generar_leyenda_bim(disciplinas_bim, "leyenda_bim.svg")
```

### 4. Generar infografia de metricas de proyecto BIM

Crea una infografia vectorial con los KPIs de un proyecto (avance, horas, interferencias) para reportes de cliente.

```python
import svgwrite

def generar_infografia_kpis(
    kpis: list[dict],
    titulo_proyecto: str,
    output: str = "kpis_proyecto.svg",
) -> None:
    """
    kpis: lista de dicts con keys: metrica, valor, unidad, color
    """
    COLS = min(len(kpis), 4)
    FILAS = (len(kpis) + COLS - 1) // COLS
    ANCHO_CARD = 220
    ALTO_CARD = 140
    GAP = 20
    MARGEN = 40
    ANCHO_SVG = COLS * ANCHO_CARD + (COLS - 1) * GAP + 2 * MARGEN
    ALTO_SVG = FILAS * ALTO_CARD + (FILAS - 1) * GAP + 2 * MARGEN + 70

    dwg = svgwrite.Drawing(output, size=(f"{ANCHO_SVG}px", f"{ALTO_SVG}px"))
    dwg.viewbox(0, 0, ANCHO_SVG, ALTO_SVG)
    dwg.add(dwg.rect(insert=(0, 0), size=(ANCHO_SVG, ALTO_SVG), fill="#0f1923"))

    dwg.add(dwg.text(titulo_proyecto, insert=(ANCHO_SVG / 2, 45),
                     text_anchor="middle", font_size=22,
                     font_family="Arial", font_weight="bold", fill="white"))

    for i, kpi in enumerate(kpis):
        col = i % COLS
        fila = i // COLS
        x = MARGEN + col * (ANCHO_CARD + GAP)
        y = MARGEN + 50 + fila * (ALTO_CARD + GAP)
        color = kpi.get("color", "#4A90D9")

        # Card
        dwg.add(dwg.rect(insert=(x, y), size=(ANCHO_CARD, ALTO_CARD),
                         rx=10, fill="#1e2d3d", stroke=color, stroke_width=2))
        # Barra superior de color
        dwg.add(dwg.rect(insert=(x, y), size=(ANCHO_CARD, 6), rx=2, fill=color))

        # Valor grande
        dwg.add(dwg.text(str(kpi["valor"]),
                         insert=(x + ANCHO_CARD / 2, y + 70),
                         text_anchor="middle", font_size=42,
                         font_family="Arial", font_weight="bold", fill=color))
        # Unidad
        dwg.add(dwg.text(kpi.get("unidad", ""),
                         insert=(x + ANCHO_CARD / 2, y + 92),
                         text_anchor="middle", font_size=14,
                         font_family="Arial", fill="#aaa"))
        # Metrica
        dwg.add(dwg.text(kpi["metrica"],
                         insert=(x + ANCHO_CARD / 2, y + 120),
                         text_anchor="middle", font_size=13,
                         font_family="Arial", font_weight="bold", fill="white"))

    dwg.save(pretty=True)
    print(f"Infografia guardada: {output}")


kpis_proyecto = [
    {"metrica": "Avance General", "valor": "73%", "unidad": "completado", "color": "#50C878"},
    {"metrica": "Interferencias Resueltas", "valor": "142", "unidad": "clash / 8 pendientes", "color": "#F5A623"},
    {"metrica": "Horas BIM", "valor": "284", "unidad": "horas acumuladas", "color": "#4A90D9"},
    {"metrica": "Reduccion Costos", "valor": "-18%", "unidad": "vs proyecto ejecutivo", "color": "#D4AC0D"},
]
generar_infografia_kpis(kpis_proyecto, "KPIs — Torre Costanera Norte", "kpis_torre.svg")
```

---

## Convertir SVG a PDF con cairosvg

```python
import cairosvg

# SVG a PDF vectorial (para propuestas e informes)
cairosvg.svg2pdf(url="diagrama.svg", write_to="diagrama.pdf")

# SVG a PNG de alta resolucion
cairosvg.svg2png(url="diagrama.svg", write_to="diagrama.png", output_width=2400)
```

## Notas

- `dwg.save(pretty=True)` genera SVG con indentacion legible; omitir `pretty=True` para archivos mas compactos.
- Las coordenadas en SVG tienen el origen (0,0) en la esquina superior izquierda; el eje Y crece hacia abajo.
- `text_anchor="middle"` centra el texto horizontalmente respecto al punto de insercion.
- Para fuentes personalizadas en SVG, usar `font-face` o incrustar la fuente; las fuentes del sistema no estan garantizadas en todos los visualizadores.
- Los SVG generados se pueden abrir y editar en Inkscape (gratuito) o Adobe Illustrator.
- Para diagramas complejos de redes/grafos, considerar `networkx` + `matplotlib` o `diagrams-python` como alternativa.
