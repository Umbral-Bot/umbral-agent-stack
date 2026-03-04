---
name: moviepy
description: >-
  Edicion de video con Python usando MoviePy: cortar clips, concatenar
  secuencias de imagenes, agregar texto animado, musica de fondo y exportar
  MP4. Util para crear videos de presentacion de proyectos BIM, tutoriales
  y material de marketing.
  Use when "crear video", "editar video", "video presentacion proyecto",
  "video con imagenes renders", "agregar texto video", "compilar clips",
  "video marketing BIM", "tutorial video Python".
metadata:
  openclaw:
    emoji: "\U0001F3AC"
    requires:
      env: []
---

# MoviePy — Edicion de Video con Python

MoviePy es una libreria Python para edicion de video: cortar, concatenar, agregar texto, musica y efectos visuales. Funciona sobre FFmpeg y permite crear videos de calidad profesional con pocas lineas de codigo.

**Instalacion:**
```bash
pip install moviepy
# Requiere FFmpeg instalado en el sistema:
# macOS: brew install ffmpeg
# Ubuntu: sudo apt install ffmpeg
# Windows: descargar desde https://ffmpeg.org/download.html
```

**Docs oficiales:** https://zulko.github.io/moviepy/

---

## Casos de uso para David (BIM / Consultoría / Docencia)

### 1. Video resumen de proyecto BIM a partir de renders

Genera un video de presentacion compilando imagenes de renders PNG ordenadas cronologicamente, con un fade entre cada imagen.

```python
from moviepy.editor import ImageClip, concatenate_videoclips
from glob import glob

# Carpeta con renders del proyecto (orden alfabetico = orden cronologico)
imagenes = sorted(glob("renders_proyecto/*.png"))

clips = [
    ImageClip(img, duration=4).fadein(0.5).fadeout(0.5)
    for img in imagenes
]

video = concatenate_videoclips(clips, method="compose")
video.write_videofile(
    "presentacion_proyecto.mp4",
    fps=24,
    codec="libx264",
    audio=False
)
print(f"Video creado: {len(clips)} renders, {video.duration:.1f}s")
```

### 2. Agregar texto de titulo y musica de fondo a un video existente

Superpone el nombre del proyecto y el cliente sobre el video, con musica de fondo a volumen reducido.

```python
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, AudioFileClip

video = VideoFileClip("presentacion_proyecto.mp4")

# Texto de titulo en la esquina inferior izquierda
titulo = (
    TextClip(
        "Proyecto Torre Costanera — Coordinacion BIM",
        fontsize=36,
        color="white",
        font="Arial-Bold",
        stroke_color="black",
        stroke_width=1,
    )
    .set_position(("left", "bottom"))
    .set_duration(video.duration)
    .margin(left=30, bottom=20, opacity=0)
)

# Musica de fondo al 20% del volumen original
musica = AudioFileClip("background_music.mp3").volumex(0.2).set_duration(video.duration)

video_final = CompositeVideoClip([video, titulo]).set_audio(musica)
video_final.write_videofile("presentacion_final.mp4", fps=24, codec="libx264")
```

### 3. Crear video tipo time-lapse de avance de obra desde fotos de terreno

Genera un time-lapse a partir de fotografias de progreso de obra, con marca de fecha en cada frame.

```python
from moviepy.editor import ImageClip, TextClip, CompositeVideoClip, concatenate_videoclips
import os

fotos_con_fecha = [
    ("fotos_obra/semana_01.jpg", "Semana 1 — Excavacion"),
    ("fotos_obra/semana_04.jpg", "Semana 4 — Fundaciones"),
    ("fotos_obra/semana_08.jpg", "Semana 8 — Estructura"),
    ("fotos_obra/semana_16.jpg", "Semana 16 — Fachada"),
    ("fotos_obra/semana_24.jpg", "Semana 24 — Terminaciones"),
]

clips = []
for ruta_foto, etiqueta in fotos_con_fecha:
    if not os.path.exists(ruta_foto):
        continue
    img = ImageClip(ruta_foto, duration=2)
    texto = (
        TextClip(etiqueta, fontsize=28, color="yellow", font="Arial")
        .set_position(("center", "top"))
        .set_duration(2)
        .margin(top=15, opacity=0)
    )
    clips.append(CompositeVideoClip([img, texto]))

timelapse = concatenate_videoclips(clips, method="compose")
timelapse.write_videofile("avance_obra_timelapse.mp4", fps=4)
```

### 4. Cortar y exportar fragmentos especificos de un video grabado

Extrae segmentos de una grabacion de reunion o tutorial para reutilizarlos como clips independientes.

```python
from moviepy.editor import VideoFileClip

grabacion = VideoFileClip("reunion_cliente_completa.mp4")

# Definir segmentos: (inicio_seg, fin_seg, nombre_output)
segmentos = [
    (0, 120, "intro_presentacion.mp4"),
    (300, 480, "demo_revit_workflow.mp4"),
    (600, 720, "cierre_preguntas.mp4"),
]

for inicio, fin, nombre in segmentos:
    clip = grabacion.subclip(inicio, min(fin, grabacion.duration))
    clip.write_videofile(nombre, codec="libx264", audio_codec="aac")
    print(f"Exportado: {nombre} ({fin - inicio}s)")

grabacion.close()
```

---

## Notas

- MoviePy 2.x cambio la API: `from moviepy import *` en lugar de `from moviepy.editor import *`. Verificar version instalada con `pip show moviepy`.
- Para videos largos (>5 min), usar `threads=4` en `write_videofile()` para acelerar la exportacion.
- Los formatos de imagen soportados son PNG, JPG, TIFF, BMP. Para renders de alta resolucion, PNG es recomendado.
- `TextClip` requiere ImageMagick instalado. Sin ImageMagick, usar `ImageClip` con texto pre-renderizado.
