---
name: manim
description: >-
  Crea animaciones matemáticas y técnicas con Manim Community Edition.
  Ideal para producir videos explicativos de clases BIM, presentaciones
  técnicas de cursos en Butic/TEDIvirtual y visualizaciones de datos
  de proyectos. Usar cuando: "animación técnica", "video explicativo",
  "animación para clase", "visualizar concepto", "presentación animada".
metadata:
  openclaw:
    emoji: "\U0001F3A5"
    requires:
      env: []
---

# Manim — Animaciones Técnicas con Python

Manim Community Edition (fork oficial de `3Blue1Brown`) permite crear
animaciones matemáticas y técnicas de alta calidad con Python. Cada
escena se define como una clase que Manim renderiza a video MP4.

## Instalación

```bash
pip install manim
# También requiere: LaTeX (MiKTeX/TeX Live) para fórmulas, ffmpeg
```

## Renderizar una escena

```bash
manim -pql nombre_archivo.py NombreEscena   # baja calidad (preview)
manim -pqh nombre_archivo.py NombreEscena   # alta calidad (1080p)
```

## Casos de uso

### 1. Diagrama animado del proceso BIM

Visualiza las fases del proceso BIM con aparición progresiva de etapas,
ideal para la intro de una clase o módulo de curso.

```python
from manim import *

class ProcesosBIM(Scene):
    def construct(self):
        titulo = Text("Proceso BIM — 5 Fases", font_size=48)
        self.play(Write(titulo))
        self.wait(1)
        self.play(titulo.animate.to_edge(UP))

        fases = [
            "1. Levantamiento",
            "2. Modelado 3D",
            "3. Coordinación",
            "4. Documentación",
            "5. Operación (FM)",
        ]
        lista = VGroup(*[
            Text(f, font_size=32).set_color(BLUE if i % 2 == 0 else WHITE)
            for i, f in enumerate(fases)
        ]).arrange(DOWN, aligned_edge=LEFT, buff=0.3)

        self.play(LaggedStart(*[Write(item) for item in lista], lag_ratio=0.4))
        self.wait(2)
```

### 2. Gráfico animado de ahorro de costos

Muestra un gráfico de barras comparando costos con y sin BIM, perfecto
para convencer a clientes o presentar resultados en cursos.

```python
from manim import *

class AhorroCostoBIM(Scene):
    def construct(self):
        titulo = Text("Reducción de Costos con BIM", font_size=40)
        titulo.to_edge(UP)
        self.play(FadeIn(titulo))

        # Barras comparativas
        ejes = Axes(
            x_range=[0, 3, 1],
            y_range=[0, 100, 20],
            axis_config={"include_tip": False},
            x_length=8,
            y_length=5,
        )
        etiquetas_x = ejes.get_x_axis_label(
            Tex("Fases del Proyecto"), edge=DOWN, direction=DOWN
        )

        barra_sin = ejes.get_riemann_rectangles(
            ejes.plot(lambda x: 80, x_range=[0.2, 1.2]),
            dx=1,
            color=RED,
            fill_opacity=0.7,
        )
        barra_con = ejes.get_riemann_rectangles(
            ejes.plot(lambda x: 52, x_range=[1.5, 2.5]),
            dx=1,
            color=GREEN,
            fill_opacity=0.7,
        )

        sin_bim = Text("Sin BIM: 80%", font_size=24, color=RED).next_to(barra_sin, UP)
        con_bim = Text("Con BIM: 52%", font_size=24, color=GREEN).next_to(barra_con, UP)

        self.play(Create(ejes), Write(etiquetas_x))
        self.play(Create(barra_sin), FadeIn(sin_bim))
        self.wait(0.5)
        self.play(Create(barra_con), FadeIn(con_bim))
        self.wait(2)
```

### 3. Ecuación de cálculo de área en BIM

Anima una fórmula técnica para usar en materiales didácticos de clase.

```python
from manim import *

class FormulaSuperificieBIM(Scene):
    def construct(self):
        titulo = Text("Cálculo de Superficie Útil", font_size=44)
        self.play(Write(titulo))
        self.wait(1)
        self.play(titulo.animate.shift(UP * 2.5).scale(0.7))

        formula = MathTex(
            r"S_{util} = S_{total} - S_{muros} - S_{circulacion}",
            font_size=48,
        )
        self.play(Write(formula))
        self.wait(1)

        ejemplo = MathTex(
            r"S_{util} = 250 - 32 - 18 = 200 \, m^2",
            font_size=42,
            color=YELLOW,
        ).shift(DOWN * 1.5)
        self.play(TransformFromCopy(formula, ejemplo))
        self.wait(2)
```

## Notas

- Calidad de render: `-ql` (480p), `-qm` (720p), `-qh` (1080p), `-qk` (4K).
- Las escenas se exportan a `media/videos/` por defecto.
- Para fórmulas LaTeX se necesita una instalación de LaTeX en el sistema.
- Docs oficiales: https://docs.manim.community/
