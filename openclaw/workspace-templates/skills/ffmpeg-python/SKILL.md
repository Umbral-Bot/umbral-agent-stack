---
name: ffmpeg-python
description: >-
  Procesamiento de video y audio con ffmpeg-python: conversión de formatos,
  extracción de frames, compresión, subtítulos y edición no destructiva.
  Ideal para preparar videos de proyectos, comprimir grabaciones de cursos
  y extraer thumbnails de recorridos virtuales BIM.
  Usar cuando: "convertir video", "comprimir mp4", "extraer frames",
  "agregar subtítulos", "optimizar video para web", "recortar video".
metadata:
  openclaw:
    emoji: "\U0001F39E\uFE0F"
    requires:
      env: []
---

# ffmpeg-python — Procesamiento de Video con Python

`ffmpeg-python` es una librería de bindings Pythonicos para FFmpeg, el
procesador de video/audio más potente del ecosistema open source.
Permite definir pipelines de procesamiento de video con código Python
en lugar de comandos de shell complejos.

## Instalación

```bash
# Requiere ffmpeg instalado en el sistema
brew install ffmpeg          # macOS
sudo apt install ffmpeg      # Ubuntu/Debian

pip install ffmpeg-python
```

## Casos de uso

### 1. Comprimir videos de recorridos virtuales para entrega web

Optimiza videos MP4 de recorridos BIM para subir al portfolio o entregar
al cliente, reduciendo el tamaño sin pérdida visual apreciable.

```python
import ffmpeg

def comprimir_video_web(
    entrada: str,
    salida: str,
    crf: int = 23,      # 18=alta calidad, 28=mayor compresión
    preset: str = "slow",  # más lento = mejor compresión
) -> None:
    """
    CRF (Constant Rate Factor): 18-28 es el rango práctico.
    preset: ultrafast, fast, medium, slow, veryslow
    """
    (
        ffmpeg
        .input(entrada)
        .output(
            salida,
            vcodec="libx264",
            crf=crf,
            preset=preset,
            acodec="aac",
            audio_bitrate="128k",
            movflags="faststart",   # streaming web optimizado
        )
        .overwrite_output()
        .run(quiet=True)
    )
    print(f"Video comprimido: {salida}")

comprimir_video_web("recorrido_bim_raw.mp4", "recorrido_bim_web.mp4", crf=24)
```

### 2. Extraer thumbnails de un recorrido virtual

Genera una imagen de preview cada N segundos del video para usar en
catálogos, portfolios o la miniatura del curso en plataformas educativas.

```python
import ffmpeg
from pathlib import Path

def extraer_thumbnails(
    video: str,
    carpeta_salida: str = "thumbnails/",
    intervalo_segundos: int = 10,
) -> None:
    Path(carpeta_salida).mkdir(exist_ok=True)
    patron_salida = f"{carpeta_salida}/frame_%04d.jpg"

    (
        ffmpeg
        .input(video)
        .filter("fps", fps=f"1/{intervalo_segundos}")   # 1 frame cada N segundos
        .output(
            patron_salida,
            vframes=100,        # máximo 100 frames
            qscale=2,           # calidad JPEG (1=mejor, 31=peor)
        )
        .overwrite_output()
        .run(quiet=True)
    )
    frames = list(Path(carpeta_salida).glob("frame_*.jpg"))
    print(f"Extraídos {len(frames)} thumbnails en {carpeta_salida}")

extraer_thumbnails("recorrido_obra.mp4", intervalo_segundos=15)
```

### 3. Convertir grabaciones de pantalla a formato optimizado para cursos

Transforma grabaciones OBS (.mkv) a MP4 con resolución 1080p y bitrate
adecuado para plataformas de e-learning (Udemy, Hotmart, Teachable).

```python
import ffmpeg

def preparar_video_para_curso(
    entrada: str,
    salida: str,
    resolucion: str = "1920:1080",
) -> dict:
    probe = ffmpeg.probe(entrada)
    duracion = float(probe["format"]["duration"])
    tamano_mb = int(probe["format"]["size"]) / (1024 * 1024)

    (
        ffmpeg
        .input(entrada)
        .output(
            salida,
            vf=f"scale={resolucion}:force_original_aspect_ratio=decrease,"
               f"pad={resolucion}:(ow-iw)/2:(oh-ih)/2",
            vcodec="libx264",
            crf=20,
            preset="medium",
            acodec="aac",
            ar=44100,              # sample rate estándar
            audio_bitrate="192k",  # buena calidad para voz
        )
        .overwrite_output()
        .run(quiet=True)
    )

    return {
        "duracion_min": round(duracion / 60, 1),
        "tamano_entrada_mb": round(tamano_mb, 1),
        "archivo_salida": salida,
    }

info = preparar_video_para_curso("clase_revit_raw.mkv", "clase_revit_curso.mp4")
print(f"Listo: {info['duracion_min']} min, entrada: {info['tamano_entrada_mb']} MB")
```

## Notas

- `ffmpeg.probe()` devuelve metadata del video (duración, resolución, codecs).
- `movflags="faststart"` reorganiza el archivo para streaming web progresivo.
- Para videos con audio y video independientes usar `.audio` y `.video` del stream.
- `ffmpeg.compile()` devuelve la lista de argumentos sin ejecutar (útil para debug).
- Docs oficiales: https://kkroening.github.io/ffmpeg-python/
