---
name: moviepy
description: >-
  Edición de video con Python usando MoviePy 2.x: cortar, unir, agregar texto,
  overlays y música. Ideal para crear presentaciones de proyectos, tutoriales
  de cursos BIM y reels de portfolio de consultoría.
  Usar cuando: "crear video resumen", "unir clips", "agregar título al video",
  "video de portfolio", "editar presentación en video", "time-lapse de obra".
metadata:
  openclaw:
    emoji: "\U0001F3AC"
    requires:
      env: []
---

# MoviePy — Edición de Video con Python

MoviePy 2.x permite editar video programáticamente: cortar, unir, compositar
texto y audio. Como Premiere Pro pero reproducible y automatizable.

## Instalación

```bash
pip install moviepy
```

Para texto en video se requiere una fuente TrueType (`.ttf`) accesible.

## Casos de uso

### 1. Video resumen de proyecto con renders

Convierte imágenes de renders en un video de presentación con música de fondo.

```python
from moviepy import ImageClip, concatenate_videoclips, AudioFileClip
from glob import glob

# Cargar renders ordenados como clips de 3 segundos cada uno
clips = [ImageClip(f, duration=3) for f in sorted(glob("renders/*.png"))]

# Unir clips con transición
video = concatenate_videoclips(clips, method="compose")

# Agregar música de fondo
audio = AudioFileClip("musica_presentacion.mp3").with_duration(video.duration)
video = video.with_audio(audio)

video.write_videofile("presentacion_proyecto.mp4", fps=24)
```

### 2. Título animado sobre video de obra

Agrega un overlay de texto con el nombre del proyecto al inicio del clip.

```python
from moviepy import VideoFileClip, TextClip, CompositeVideoClip

video = VideoFileClip("recorrido_obra.mp4")

titulo = (
    TextClip(
        font="Arial.ttf",
        text="Torre Reforma BIM — Fase 2",
        font_size=60,
        color="white",
    )
    .with_duration(5)
    .with_position("center")
)

final = CompositeVideoClip([video, titulo])
final.write_videofile("recorrido_con_titulo.mp4", fps=24)
```

### 3. Cortar y compilar tutoriales para curso

Extrae segmentos clave de grabaciones de pantalla para armar un tutorial editado.

```python
from moviepy import VideoFileClip, concatenate_videoclips

grabacion = VideoFileClip("clase_revit_full.mp4")

# Segmentos de interés (en segundos)
segmentos = [
    (120, 300),   # Intro Revit
    (540, 720),   # Familias
    (900, 1080),  # Exportar IFC
]

clips = [grabacion.subclipped(inicio, fin) for inicio, fin in segmentos]
tutorial = concatenate_videoclips(clips)
tutorial.write_videofile("tutorial_revit_editado.mp4", fps=24)
```

## Notas

- MoviePy 2.x importa desde `moviepy` directamente (no `moviepy.editor`).
- Los métodos `.set_*` de v1.x se reemplazan por `.with_*()` en v2.x.
- Para renderizar texto se necesita `imagemagick` o pasar `font="ruta/fuente.ttf"`.
- Docs oficiales: https://zulko.github.io/moviepy/
