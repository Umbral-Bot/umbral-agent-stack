---
name: manim
description: >-
  Crear animaciones matematicas y tecnicas con Python usando Manim Community.
  Ideal para explicar conceptos BIM, flujos de datos, geometria de modelos
  y presentaciones tecnicas con calidad cinematografica. Como los videos de
  3Blue1Brown pero orientados a AEC/consultoría.
  Use when "animacion tecnica", "animar concepto BIM", "video explicativo",
  "animacion matematica", "visualizar proceso", "animacion presentacion",
  "video pedagogico", "animacion parametrica".
metadata:
  openclaw:
    emoji: "\U0001F3A5"
    requires:
      env: []
---

# Manim Community — Animaciones Tecnicas con Python

Manim es el motor de animacion matematica creado por Grant Sanderson (3Blue1Brown) y mantenido por la comunidad. Permite crear animaciones de precision con texto, graficos, geometria 2D/3D y transiciones fluidas. Renderiza en MP4 o GIF de alta calidad.

**Instalacion:**
```bash
pip install manim
# Requiere: ffmpeg, LaTeX (MiKTeX en Windows / texlive en Linux)
# Ubuntu: sudo apt install ffmpeg texlive-full
# macOS: brew install ffmpeg mactex
```

**Docs oficiales:** https://docs.manim.community/

---

## Casos de uso para David (BIM / Docencia / Consultoría)

### 1. Animar el flujo de informacion BIM de Open BIM a cerrado

Visualiza con flechas y etiquetas animadas como fluye la informacion entre herramientas BIM abiertas y propietarias.

```python
from manim import *

class FlujoBIM(Scene):
    def construct(self):
        # Titulo
        titulo = Text("Flujo de Informacion BIM", font_size=40, weight=BOLD)
        self.play(Write(titulo))
        self.wait(0.5)
        self.play(titulo.animate.to_edge(UP))

        # Nodos
        revit = RoundedRectangle(width=2.5, height=1.0, corner_radius=0.2, color=BLUE)
        revit_label = Text("Revit", font_size=24).move_to(revit)
        ifc = RoundedRectangle(width=2.5, height=1.0, corner_radius=0.2, color=GREEN)
        ifc_label = Text("IFC / Open BIM", font_size=20).move_to(ifc)
        acc = RoundedRectangle(width=2.5, height=1.0, corner_radius=0.2, color=ORANGE)
        acc_label = Text("ACC / BIM360", font_size=20).move_to(acc)

        nodos = VGroup(revit, revit_label, ifc, ifc_label, acc, acc_label)
        revit_g = VGroup(revit, revit_label).move_to(LEFT * 4)
        ifc_g = VGroup(ifc, ifc_label).move_to(ORIGIN)
        acc_g = VGroup(acc, acc_label).move_to(RIGHT * 4)

        self.play(FadeIn(revit_g), FadeIn(ifc_g), FadeIn(acc_g))

        # Flechas de flujo
        flecha1 = Arrow(revit.get_right(), ifc.get_left(), buff=0.1, color=YELLOW)
        label1 = Text("exporta .ifc", font_size=18).next_to(flecha1, UP, buff=0.1)
        flecha2 = Arrow(ifc.get_right(), acc.get_left(), buff=0.1, color=YELLOW)
        label2 = Text("sube modelo", font_size=18).next_to(flecha2, UP, buff=0.1)

        self.play(GrowArrow(flecha1), Write(label1))
        self.wait(0.3)
        self.play(GrowArrow(flecha2), Write(label2))
        self.wait(1.5)
```

### 2. Animar el impacto de la automatizacion: de 4 horas a 90 segundos

Grafico de barras animado que muestra la reduccion de tiempo en un proceso administrativo BIM.

```python
from manim import *

class ImpactoAutomatizacion(Scene):
    def construct(self):
        titulo = Text("Impacto de la Automatizacion", font_size=36, weight=BOLD)
        self.play(Write(titulo.to_edge(UP)))

        ax = BarChart(
            values=[240, 1.5],
            bar_names=["Proceso manual\n(4 horas)", "Con automatizacion\n(90 segundos)"],
            y_range=[0, 250, 50],
            y_axis_config={"label_constructor": lambda v: Tex(f"{int(v)} min")},
            bar_colors=[RED, GREEN],
        )
        ax.scale(0.85).center()

        self.play(Create(ax))
        self.wait(0.5)

        # Etiquetas de valor encima de cada barra
        for bar, valor, label in zip(ax.bars, [240, 1.5], ["240 min", "1.5 min"]):
            text = Text(label, font_size=22, color=WHITE).next_to(bar, UP, buff=0.1)
            self.play(FadeIn(text))

        reduccion = Text("-99% tiempo", font_size=32, color=YELLOW, weight=BOLD)
        reduccion.to_corner(DR)
        self.play(Write(reduccion))
        self.wait(2)
```

### 3. Visualizar geometria parametrica: como un parametro modifica una forma

Animacion pedagogica que muestra como un parametro en Revit/Dynamo controla una familia parametrica.

```python
from manim import *
import numpy as np

class GeometriaParametrica(Scene):
    def construct(self):
        titulo = Text("Geometria Parametrica en BIM", font_size=34, weight=BOLD)
        self.play(Write(titulo.to_edge(UP)))

        # Variable tracker para el parametro de altura
        altura = ValueTracker(1.5)

        # Edificio como rectangulo que cambia con el tracker
        edificio = always_redraw(
            lambda: Rectangle(
                width=2,
                height=altura.get_value(),
                color=BLUE,
                fill_color=BLUE,
                fill_opacity=0.4,
            ).shift(DOWN * (2 - altura.get_value() / 2))
        )

        label_altura = always_redraw(
            lambda: Text(
                f"Altura = {altura.get_value():.1f} m", font_size=28
            ).next_to(edificio, RIGHT, buff=0.5)
        )

        self.play(FadeIn(edificio), Write(label_altura))
        self.wait(0.5)

        # Variar el parametro de altura
        for nueva_altura in [3.0, 1.0, 2.5, 4.0, 2.0]:
            self.play(
                altura.animate.set_value(nueva_altura),
                run_time=1.5,
                rate_func=smooth,
            )
            self.wait(0.3)

        self.wait(1)
```

### 4. Animar diagrama de fases de proyecto para curso

Linea de tiempo animada con las fases de un proyecto BIM, util para material didactico.

```python
from manim import *

class FasesProyectoBIM(Scene):
    def construct(self):
        titulo = Text("Fases de un Proyecto BIM", font_size=36, weight=BOLD)
        self.play(Write(titulo.to_edge(UP)))

        fases = [
            ("Fase 1", "Diagnostico", BLUE),
            ("Fase 2", "Diseno", GREEN),
            ("Fase 3", "Implementacion", ORANGE),
            ("Fase 4", "Entrega", RED),
        ]

        linea = Line(LEFT * 5.5, RIGHT * 5.5, color=GRAY)
        self.play(Create(linea))

        puntos_x = [-4.5, -1.5, 1.5, 4.5]
        for (fase, desc, color), x in zip(fases, puntos_x):
            punto = Dot(point=[x, 0, 0], radius=0.15, color=color)
            etiqueta_fase = Text(fase, font_size=20, color=color).next_to(punto, UP, buff=0.15)
            etiqueta_desc = Text(desc, font_size=16, color=GRAY).next_to(punto, DOWN, buff=0.15)
            self.play(
                FadeIn(punto, scale=1.5),
                Write(etiqueta_fase),
                Write(etiqueta_desc),
                run_time=0.7,
            )

        self.wait(2)
```

---

## Renderizar escenas

```bash
# Calidad media (720p, rapido para preview)
manim -pql archivo.py FlujoBIM

# Alta calidad (1080p, para produccion)
manim -pqh archivo.py FlujoBIM

# Exportar como GIF
manim -pql --format=gif archivo.py FlujoBIM

# Solo guardar el video sin abrirlo
manim -ql archivo.py FlujoBIM
```

## Notas

- Manim Community (pip: `manim`) es diferente de ManimGL (version de 3Blue1Brown). La version Community es la recomendada para uso general.
- LaTeX es opcional pero necesario para formulas matematicas con `MathTex`. Sin LaTeX, usar `Text()` para texto simple.
- Los videos se guardan en `media/videos/<archivo>/<calidad>/`.
- Para presentaciones interactivas, exportar a GIF y embeber en PowerPoint/Notion.
- `always_redraw()` permite crear objetos que se actualizan continuamente al cambiar `ValueTracker`.
