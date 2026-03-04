---
name: manim
description: >-
  Crear animaciones matematicas y tecnicas con Manim Community Edition. Ideal
  para crear material didactico para clases BIM en Butic/TEDIvirtual, explicar
  conceptos de automatizacion visualmente y producir videos tecnicos de alto impacto.
  Use when "animacion tecnica", "video educativo", "explicar concepto visual",
  "animacion matematica", "video clase BIM", "crear presentacion animada".
metadata:
  openclaw:
    emoji: "\U0001F3A8"
    requires:
      env: []
---

# Manim — Animaciones Tecnicas con Python

Manim Community Edition es la libreria que usa 3Blue1Brown para crear videos matematicos. Permite generar animaciones vectoriales de alta calidad para presentaciones tecnicas, clases y marketing educativo.

**Docs oficiales:** https://docs.manim.community/

## Instalacion

```bash
pip install manim
# Requiere: LaTeX (para formulas), ffmpeg, Cairo, Pango
# Ubuntu: sudo apt install texlive-full ffmpeg libcairo2-dev libpango1.0-dev
# macOS: brew install --cask mactex && brew install ffmpeg cairo pango
# Windows: instalar MiKTeX + ffmpeg + ejecutar desde WSL2 recomendado
```

## Renderizar una escena

```bash
# Calidad baja (rapido, para preview)
manim -pql nombre_archivo.py NombreClase

# Calidad alta (para produccion, 1080p)
manim -pqh nombre_archivo.py NombreClase

# Solo guardar (sin abrir reproductor)
manim -qh nombre_archivo.py NombreClase --save_last_frame
```

---

## Casos de uso

### 1. Animacion del flujo BIM — para clase introductoria en Butic

Explica visualmente el concepto de LOD (Level of Development) en BIM:

```python
from manim import *

class FlujoBIM(Scene):
    def construct(self):
        # Titulo
        titulo = Text("Flujo BIM — LOD de Modelado", font_size=40, color=BLUE)
        self.play(Write(titulo))
        self.wait(1)
        self.play(titulo.animate.to_edge(UP))

        # Crear etapas del flujo como rectangulos
        etapas = ["LOD 100\nConcepto", "LOD 200\nEsquematico", "LOD 300\nCoordin.", "LOD 400\nFabric."]
        colores = [BLUE_D, GREEN_D, YELLOW_D, RED_D]

        cajas = VGroup()
        for i, (etapa, color) in enumerate(zip(etapas, colores)):
            caja = RoundedRectangle(
                corner_radius=0.2,
                width=2.5,
                height=1.5,
                color=color,
                fill_opacity=0.3
            )
            texto = Text(etapa, font_size=22).move_to(caja)
            grupo = VGroup(caja, texto).shift(RIGHT * (i * 3 - 4.5) + DOWN * 0.5)
            cajas.add(grupo)

        # Animar aparicion secuencial
        for caja in cajas:
            self.play(FadeIn(caja), run_time=0.5)

        # Flechas de conexion
        flechas = VGroup()
        for i in range(len(cajas) - 1):
            flecha = Arrow(
                cajas[i].get_right(),
                cajas[i + 1].get_left(),
                buff=0.1,
                color=WHITE
            )
            flechas.add(flecha)
            self.play(GrowArrow(flecha), run_time=0.4)

        self.wait(2)
```

### 2. Animacion de reduccion de tiempo — caso de exito para propuestas

Visualiza el impacto de la automatizacion con un grafico animado (4h → 90 seg):

```python
from manim import *

class ReduccionTiempos(Scene):
    def construct(self):
        titulo = Text("Impacto de la Automatizacion", font_size=36, color=BLUE)
        self.play(Write(titulo.to_edge(UP)))

        # Barras comparativas
        barra_antes = Rectangle(width=1.2, height=4, color=RED, fill_opacity=0.7)
        barra_despues = Rectangle(width=1.2, height=0.15, color=GREEN, fill_opacity=0.7)

        barra_antes.next_to(ORIGIN, LEFT, buff=1.5).align_to(DOWN * 2, DOWN)
        barra_despues.next_to(ORIGIN, RIGHT, buff=1.5).align_to(DOWN * 2, DOWN)

        label_antes = Text("Antes\n4 horas", font_size=24).next_to(barra_antes, DOWN)
        label_despues = Text("Despues\n90 segundos", font_size=24).next_to(barra_despues, DOWN)
        label_reduccion = Text("-96%", font_size=48, color=GREEN).next_to(barra_despues, UP)

        self.play(
            GrowFromEdge(barra_antes, DOWN),
            Write(label_antes),
            run_time=1.5
        )
        self.wait(0.5)
        self.play(
            GrowFromEdge(barra_despues, DOWN),
            Write(label_despues),
            run_time=1.5
        )
        self.play(Write(label_reduccion))
        self.wait(2)
```

### 3. Grafico animado de progreso de obra — para reportes dinamicos

Crea un grafico de barras que muestra avance de hitos por semana:

```python
from manim import *

class ProgresoCronograma(Scene):
    def construct(self):
        titulo = Text("Avance de Obra — Semana 12", font_size=32, color=WHITE)
        self.add(titulo.to_edge(UP))

        hitos = ["Fundaciones", "Estructura", "Instalaciones", "Terminaciones"]
        avances = [1.0, 0.75, 0.40, 0.10]  # porcentaje completado
        colores = [GREEN, YELLOW, ORANGE, RED]

        for i, (hito, avance, color) in enumerate(zip(hitos, avances, colores)):
            # Etiqueta
            label = Text(hito, font_size=20).shift(LEFT * 3.5 + DOWN * (i * 1.2 - 1.5))
            self.add(label)

            # Barra de fondo (gris)
            bg = Rectangle(width=5, height=0.5, color=GREY, fill_opacity=0.3)
            bg.next_to(label, RIGHT, buff=0.3)
            bg.align_to(label, LEFT).shift(RIGHT * 2.2)
            self.add(bg)

            # Barra de progreso
            barra = Rectangle(
                width=5 * avance,
                height=0.5,
                color=color,
                fill_opacity=0.8
            )
            barra.align_to(bg, LEFT).align_to(bg, UP)

            pct_text = Text(f"{int(avance * 100)}%", font_size=18).next_to(barra, RIGHT, buff=0.1)

            self.play(
                GrowFromEdge(barra, LEFT),
                Write(pct_text),
                run_time=0.8
            )

        self.wait(2)
```

## Comandos de renderizado frecuentes

| Comando | Descripcion |
|---------|-------------|
| `manim -pql scene.py Clase` | Preview baja calidad (rapido) |
| `manim -pqh scene.py Clase` | Preview alta calidad (1080p) |
| `manim -qh scene.py Clase` | Solo renderizar, no abrir |
| `manim --save_last_frame` | Exportar como imagen estatica |
| `manim -qh --format=gif` | Exportar como GIF animado |

## Objetos Manim mas utiles para contexto tecnico

```python
# Texto y formulas
Text("Hola Mundo", font_size=36, color=BLUE)
MathTex(r"\Delta t = t_1 - t_0")    # Formula LaTeX
Tex(r"\textbf{BIM Level 2}")         # LaTeX con formato

# Formas geometricas
Rectangle(width=3, height=2, color=BLUE, fill_opacity=0.5)
Circle(radius=1, color=RED)
Arrow(start=LEFT, end=RIGHT, color=WHITE)
RoundedRectangle(corner_radius=0.3, width=3, height=1.5)

# Animaciones basicas
self.play(Write(objeto))           # Escribir texto
self.play(FadeIn(objeto))          # Aparecer con fade
self.play(GrowArrow(flecha))       # Crecer flecha
self.play(objeto.animate.shift(RIGHT))  # Mover
self.play(objeto.animate.scale(2))      # Escalar
```

## Notas

- Manim usa LaTeX para formulas matematicas; sin LaTeX instalado, `MathTex` falla
- Para presentaciones de cursos, exportar en 1080p MP4 y luego insertar en PowerPoint
- Los videos se guardan en `./media/videos/nombre_archivo/calidad/`
- En laptops lentas: usar `-ql` (480p) para iterar rapido y `-qh` solo para produccion final
