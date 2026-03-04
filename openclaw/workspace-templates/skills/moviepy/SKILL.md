---
name: moviepy
description: >-
  Edicion de video con Python usando MoviePy v2. Cortar, unir, agregar texto,
  musica, efectos, transiciones. Ideal para crear videos de presentacion de
  proyectos AEC, tutoriales de cursos BIM y marketing de consultoria.
  Use when "crear video proyecto", "editar video python", "video presentacion",
  "unir clips", "agregar texto video", "video con musica", "reel proyecto".
metadata:
  openclaw:
    emoji: "\U0001F3AC"
    requires:
      env: []
---

# MoviePy — Edicion de Video con Python

MoviePy v2 es una libreria Python para editar video de forma programatica. Permite cortar, unir, agregar texto, musica y efectos sin necesidad de Premiere Pro o DaVinci Resolve.

**Docs oficiales:** https://zulko.github.io/moviepy/

## Instalacion

**Instalacion:**
```bash
pip install moviepy
# Requiere ffmpeg instalado en el sistema
# macOS: brew install ffmpeg
# Ubuntu: sudo apt install ffmpeg
# Windows: descargar desde ffmpeg.org
```

## Conceptos clave (v2.0)

- **Importacion directa** — ya no existe `moviepy.editor`, usar `from moviepy import *`
- **Metodos inmutables** — `with_*` en lugar de `set_*` (devuelven copia modificada)
- **Efectos como clases** — se usan con `.with_effects([FadeIn(1)])`

---

---

### 1. Video resumen de proyecto — renders a video de presentacion

Convierte una carpeta de renders PNG en un video de presentacion con duracion controlada:

```python
from moviepy import ImageClip, concatenate_videoclips
from pathlib import Path

render_dir = Path("renders")
imagenes = sorted(render_dir.glob("*.png"))

clips = [
    ImageClip(str(img)).with_duration(4)
    for img in imagenes
]

video = concatenate_videoclips(clips, method="compose")
video.write_videofile(
    "presentacion_proyecto.mp4",
    fps=24,
    codec="libx264",
    audio_codec="aac"
)
```

### 2. Agregar titulo y musica de fondo a video existente

Ideal para videos de walkthrough BIM con branding profesional:

```python
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, AudioFileClip
from moviepy.video.fx import FadeIn, FadeOut

video = VideoFileClip("walkthrough_bim.mp4")

titulo = (
    TextClip(
        text="Proyecto OXXO Chile — BIM Level 2",
        font_size=48,
        color="white",
        font="Arial-Bold"
    )
    .with_duration(4)
    .with_position(("center", 50))
    .with_effects([FadeIn(1), FadeOut(1)])
)

musica = (
    AudioFileClip("background.mp3")
    .with_duration(video.duration)
    .with_effects([FadeOut(3)])
)

video_con_titulo = CompositeVideoClip([video, titulo])
video_final = video_con_titulo.with_audio(musica)
video_final.write_videofile("presentacion_final.mp4", fps=24)
```

### 3. Recortar y exportar fragmento especifico

Extraer un clip de 30 segundos para reel de LinkedIn:

```python
from moviepy import VideoFileClip

video = VideoFileClip("grabacion_clase.mp4")

# Extraer desde segundo 120 hasta 150
fragmento = video.subclipped(120, 150)

# Redimensionar a formato vertical 9:16 para Stories/Reels
fragmento_vertical = fragmento.resized(height=1920).cropped(
    x_center=fragmento.w / 2,
    width=1080
)

fragmento_vertical.write_videofile(
    "reel_linkedin_30s.mp4",
    fps=30,
    codec="libx264"
)
```

### 4. Concatenar capturas de pantalla con voz en off

Crear un tutorial de curso con slides + audio narrado:

```python
from moviepy import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips
from pathlib import Path

slides = sorted(Path("slides").glob("*.png"))
audios = sorted(Path("narracion").glob("*.mp3"))

clips = []
for slide_path, audio_path in zip(slides, audios):
    audio = AudioFileClip(str(audio_path))
    clip = (
        ImageClip(str(slide_path))
        .with_duration(audio.duration)
        .with_audio(audio)
    )
    clips.append(clip)

tutorial = concatenate_videoclips(clips, method="compose")
tutorial.write_videofile(
    "tutorial_bim_completo.mp4",
    fps=24,
    codec="libx264",
    audio_codec="aac"
)
```

## Parametros utiles para `write_videofile`

| Parametro | Valor recomendado | Uso |
|-----------|-------------------|-----|
| `fps` | 24 o 30 | Presentaciones: 24, tutoriales: 30 |
| `codec` | `"libx264"` | Maxima compatibilidad |
| `bitrate` | `"5000k"` | Alta calidad para renders |
| `preset` | `"slow"` | Mayor compresion, menor tamanio |
| `audio_codec` | `"aac"` | Compatible con todos los reproductores |

## Notas

- MoviePy v2 requiere Python 3.7+. Verificar version: `pip show moviepy`
- Para render de alta calidad usar `bitrate="8000k"` y `preset="slow"`
- Los archivos de salida de Revit/Navisworks pueden necesitar conversion previa con ffmpeg
- Tiempo de render: ~1 min de video = 2-5 min de procesamiento en laptop normal
