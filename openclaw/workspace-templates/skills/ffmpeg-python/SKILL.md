---
name: ffmpeg-python
description: >-
  Procesamiento de video y audio con ffmpeg-python (bindings Python para FFmpeg).
  Conversion de formatos, extraccion de frames, compresion, recorte, subtitulos,
  generacion de timelapses y optimizacion para web. Ideal para procesar grabaciones
  de obra, videos de cursos, walkthroughs BIM y contenido para redes sociales.
  Use when "convertir video", "comprimir video", "extraer frames", "timelapse",
  "optimizar video web", "recortar video ffmpeg", "combinar audio video".
metadata:
  openclaw:
    emoji: "\U0001F3A5"
    requires:
      env: []
---

# ffmpeg-python — Procesamiento de Video con Python

ffmpeg-python expone la potencia de FFmpeg a traves de una API Python fluida. Permite construir pipelines de video/audio complejos con filtros encadenados, sin necesidad de escribir comandos de terminal largos.

**Docs oficiales:** https://kkroening.github.io/ffmpeg-python/
**Requiere:** FFmpeg instalado en el sistema (binario en el PATH)

## Instalacion

```bash
pip install ffmpeg-python
# Instalar el binario ffmpeg:
# macOS: brew install ffmpeg
# Ubuntu: sudo apt install ffmpeg
# Windows: descargar desde ffmpeg.org, agregar carpeta bin al PATH
```

---

## Casos de uso

### 1. Convertir y comprimir video de presentacion para web/Notion

Convierte un video de Premiere o Lumion a MP4 optimizado para subir a Notion o LinkedIn:

```python
import ffmpeg

def comprimir_para_web(entrada: str, salida: str, max_width: int = 1920):
    """Comprime video manteniendo calidad para web. Ideal para Notion/LinkedIn."""
    probe = ffmpeg.probe(entrada)
    video_stream = next(s for s in probe["streams"] if s["codec_type"] == "video")
    ancho_original = int(video_stream["width"])

    # Solo redimensionar si supera el ancho maximo
    escala = f"{max_width}:-2" if ancho_original > max_width else "iw:ih"

    (
        ffmpeg
        .input(entrada)
        .output(
            salida,
            vcodec="libx264",
            acodec="aac",
            vf=f"scale={escala}",
            crf=23,               # Calidad: 18 (alta) a 28 (baja). 23 = balance
            preset="slow",        # Mayor compresion, mas tiempo
            movflags="+faststart", # Permite streaming progresivo
            audio_bitrate="128k"
        )
        .run(overwrite_output=True)
    )
    print(f"Video comprimido: {salida}")


comprimir_para_web("presentacion_4k.mov", "presentacion_web.mp4")
```

### 2. Crear timelapse de fotos de avance de obra

Genera un timelapse MP4 a partir de fotos diarias de progreso de obra:

```python
import ffmpeg
from pathlib import Path

def crear_timelapse_obra(carpeta_fotos: str, salida: str, fps: int = 12):
    """
    Crea timelapse desde carpeta de fotos nombradas secuencialmente.
    Las fotos deben seguir patron: obra_001.jpg, obra_002.jpg, etc.
    """
    # ffmpeg requiere que las fotos esten nombradas con padding de ceros
    patron = str(Path(carpeta_fotos) / "obra_%03d.jpg")

    (
        ffmpeg
        .input(patron, framerate=fps, pattern_type="sequence")
        .filter("scale", 1920, -2)
        .filter("unsharp", lx=3, ly=3, la=0.3)  # Nitidez leve
        .output(
            salida,
            vcodec="libx264",
            crf=18,
            pix_fmt="yuv420p",   # Compatibilidad maxima
            movflags="+faststart"
        )
        .run(overwrite_output=True)
    )
    print(f"Timelapse generado: {salida} ({fps}fps)")


crear_timelapse_obra("fotos_obra/", "timelapse_proyecto.mp4", fps=15)
```

### 3. Extraer frames de un video para procesar con Pillow

Extrae un frame por segundo de un walkthrough BIM para generar thumbnails:

```python
import ffmpeg
from pathlib import Path

def extraer_frames(video_path: str, carpeta_salida: str, cada_n_segundos: float = 1.0):
    """Extrae frames del video en intervalos regulares."""
    Path(carpeta_salida).mkdir(parents=True, exist_ok=True)

    # Obtener duracion total
    probe = ffmpeg.probe(video_path)
    duracion = float(probe["format"]["duration"])
    total_frames_estimados = int(duracion / cada_n_segundos)

    patron_salida = str(Path(carpeta_salida) / "frame_%04d.jpg")

    (
        ffmpeg
        .input(video_path)
        .filter("fps", fps=f"1/{cada_n_segundos}")
        .output(
            patron_salida,
            vframes=total_frames_estimados,
            qscale=2   # Calidad JPEG: 1 (maxima) a 31 (minima)
        )
        .run(overwrite_output=True)
    )
    print(f"Frames extraidos en: {carpeta_salida}/")
    return list(Path(carpeta_salida).glob("frame_*.jpg"))


frames = extraer_frames("walkthrough_bim.mp4", "frames_walkthrough/", cada_n_segundos=2.0)
print(f"Total frames extraidos: {len(frames)}")
```

### 4. Combinar audio narrado con slides/video mudo

Util para tutoriales de cursos grabados por separado (slides + voz):

```python
import ffmpeg

def combinar_video_audio(
    video_mudo: str,
    audio_narracion: str,
    salida: str,
    normalizar_audio: bool = True
):
    """Combina video sin audio con pista de voz grabada por separado."""
    video = ffmpeg.input(video_mudo).video
    audio = ffmpeg.input(audio_narracion).audio

    if normalizar_audio:
        # Normalizar volumen de la narracion
        audio = audio.filter("loudnorm", I=-16, TP=-1.5, LRA=11)

    (
        ffmpeg
        .output(
            video,
            audio,
            salida,
            vcodec="copy",          # No re-encodear video (rapido)
            acodec="aac",
            audio_bitrate="192k",
            shortest=None           # Terminar cuando el mas corto termine
        )
        .run(overwrite_output=True)
    )
    print(f"Video con narracion: {salida}")


combinar_video_audio(
    "grabacion_pantalla_sin_audio.mp4",
    "narracion_microfono.wav",
    "tutorial_final.mp4",
    normalizar_audio=True
)
```

### 5. Obtener metadata de un archivo de video

Verificar propiedades de video antes de procesarlo:

```python
import ffmpeg
import json

def info_video(archivo: str) -> dict:
    """Devuelve metadata completa del archivo de video."""
    probe = ffmpeg.probe(archivo)

    video = next((s for s in probe["streams"] if s["codec_type"] == "video"), None)
    audio = next((s for s in probe["streams"] if s["codec_type"] == "audio"), None)

    info = {
        "duracion_seg": float(probe["format"]["duration"]),
        "tamanio_mb": round(int(probe["format"]["size"]) / 1024 / 1024, 2),
        "bitrate_total_kbps": round(int(probe["format"]["bit_rate"]) / 1000),
    }

    if video:
        info.update({
            "resolucion": f"{video['width']}x{video['height']}",
            "codec_video": video["codec_name"],
            "fps": eval(video.get("r_frame_rate", "0/1")),
        })
    if audio:
        info.update({
            "codec_audio": audio["codec_name"],
            "canales": audio.get("channels", 0),
            "sample_rate": audio.get("sample_rate", "N/A"),
        })

    return info


info = info_video("presentacion_proyecto.mp4")
print(json.dumps(info, indent=2, ensure_ascii=False))
```

## Parametros CRF — Guia de calidad

| CRF | Calidad | Uso recomendado |
|-----|---------|----------------|
| 18 | Muy alta | Master/archivo, renders 4K |
| 23 | Alta (default) | Presentaciones cliente, LinkedIn |
| 26 | Media | Borradores, previews internos |
| 28 | Baja | Prototipos rapidos, pruebas |

## Filtros utiles para contexto AEC

```python
# Escalar video
.filter("scale", 1920, -2)         # 1920px ancho, alto proporcional
.filter("scale", 1280, 720)        # HD exacto

# Recortar temporalmente
.input(video, ss="00:00:30", t="60")   # Desde seg 30, duracion 60s

# Ajustar velocidad (timelapse o slow-motion)
.filter("setpts", "0.5*PTS")       # Doble velocidad
.filter("setpts", "2.0*PTS")       # Mitad de velocidad

# Overlay: agregar logo/watermark
ffmpeg.overlay(video, logo, x="W-w-20", y="H-h-20")  # Esquina inferior derecha

# Fade de entrada y salida
.filter("fade", t="in", st=0, d=1)    # Fade in 1 segundo
.filter("fade", t="out", st=30, d=1)  # Fade out al segundo 30
```

## Notas

- `ffmpeg-python` es un wrapper; FFmpeg debe estar instalado y en el PATH del sistema
- Para procesamiento en lote, paralelizar con `concurrent.futures.ThreadPoolExecutor`
- El parametro `crf=23` con `preset="slow"` da el mejor balance calidad/tamanio
- Combinado con Pillow: extraer frames → procesar con Pillow → reensamblar con ffmpeg
