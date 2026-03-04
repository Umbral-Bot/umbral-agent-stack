---
name: ffmpeg-python
description: >-
  Procesamiento de video y audio con Python usando ffmpeg-python, wrapper
  Pythonic sobre FFmpeg CLI. Conversion de formatos, extraccion de frames,
  compresion, concatenacion, subtitulos y pipelines de video para presentaciones
  BIM, tutoriales y contenido de marketing.
  Use when "convertir video", "comprimir video", "extraer frames", "cortar video ffmpeg",
  "agregar subtitulos video", "concatenar videos ffmpeg", "pipeline video",
  "procesar audio", "video batch ffmpeg", "formato video".
metadata:
  openclaw:
    emoji: "\U0001F4FD"
    requires:
      env: []
---

# ffmpeg-python — Procesamiento de Video y Audio

`ffmpeg-python` es un wrapper Python para FFmpeg que expone su poder completo con una API orientada a objetos y soporte para pipelines encadenados. FFmpeg es el estandar de la industria para procesamiento de video/audio: soporta todos los formatos y codecs relevantes.

**Instalacion:**
```bash
pip install ffmpeg-python
# Requiere FFmpeg instalado en el sistema:
# macOS: brew install ffmpeg
# Ubuntu: sudo apt install ffmpeg
# Windows: descargar de https://ffmpeg.org/download.html y agregar al PATH
```

**Docs oficiales:** https://kkroening.github.io/ffmpeg-python/

---

## Casos de uso para David (BIM / Consultoría / Docencia)

### 1. Comprimir y convertir videos de presentacion para compartir por web

Convierte videos de alta resolucion de capturas de pantalla o grabaciones de Revit a MP4 optimizado para web.

```python
import ffmpeg
from pathlib import Path

def comprimir_para_web(
    input_path: str,
    output_path: str,
    resolucion_max: int = 1080,
    crf: int = 23,
) -> dict:
    """
    Comprime video para web usando H.264.
    crf: 18=alta calidad, 23=estandar, 28=bajo bitrate (mayor compresion)
    """
    probe = ffmpeg.probe(input_path)
    stream_video = next(s for s in probe["streams"] if s["codec_type"] == "video")
    ancho = int(stream_video["width"])
    alto = int(stream_video["height"])

    # Calcular nueva resolucion manteniendo aspecto
    if alto > resolucion_max:
        nuevo_alto = resolucion_max
        nuevo_ancho = int(ancho * resolucion_max / alto)
        nuevo_ancho = nuevo_ancho if nuevo_ancho % 2 == 0 else nuevo_ancho + 1
    else:
        nuevo_ancho, nuevo_alto = ancho, alto

    (
        ffmpeg
        .input(input_path)
        .output(
            output_path,
            vf=f"scale={nuevo_ancho}:{nuevo_alto}",
            vcodec="libx264",
            crf=crf,
            preset="medium",
            acodec="aac",
            audio_bitrate="128k",
            movflags="faststart",  # Permite streaming sin descargar completo
        )
        .overwrite_output()
        .run(quiet=True)
    )

    size_original = Path(input_path).stat().st_size / 1024 / 1024
    size_comprimido = Path(output_path).stat().st_size / 1024 / 1024
    reduccion = (1 - size_comprimido / size_original) * 100

    return {
        "original_mb": round(size_original, 1),
        "comprimido_mb": round(size_comprimido, 1),
        "reduccion_pct": round(reduccion, 1),
        "resolucion": f"{nuevo_ancho}x{nuevo_alto}",
    }


# Comprimir toda una carpeta
for video in Path("grabaciones_revit/").glob("*.mov"):
    resultado = comprimir_para_web(str(video), f"videos_web/{video.stem}.mp4")
    print(f"{video.name}: {resultado['original_mb']}MB → {resultado['comprimido_mb']}MB (-{resultado['reduccion_pct']}%)")
```

### 2. Extraer frames de un video de walkthrough BIM para generar galeria

Extrae fotogramas cada N segundos de un video de recorrido virtual BIM para crear imagenes de la galeria del proyecto.

```python
import ffmpeg
from pathlib import Path

def extraer_frames_walkthrough(
    video_path: str,
    output_dir: str,
    intervalo_segundos: float = 2.0,
    calidad_jpg: int = 95,
) -> int:
    """Extrae un frame cada N segundos. Retorna la cantidad de frames extraidos."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Obtener duracion del video
    probe = ffmpeg.probe(video_path)
    duracion = float(probe["format"]["duration"])

    patron_output = f"{output_dir}/frame_%04d.jpg"

    (
        ffmpeg
        .input(video_path)
        .filter("fps", fps=f"1/{intervalo_segundos}")  # 1 frame cada N segundos
        .output(
            patron_output,
            qscale=2,           # calidad JPEG (1=maxima, 31=minima)
            vframes=int(duracion / intervalo_segundos) + 1,
        )
        .overwrite_output()
        .run(quiet=True)
    )

    frames = list(Path(output_dir).glob("frame_*.jpg"))
    print(f"Extraidos {len(frames)} frames de {duracion:.1f}s ({intervalo_segundos}s intervalo)")
    return len(frames)


# Extraer frames de walkthrough BIM
n_frames = extraer_frames_walkthrough(
    "walkthrough_proyecto_residencial.mp4",
    "galeria_proyecto/frames",
    intervalo_segundos=3.0,
)
print(f"Galeria lista: {n_frames} imagenes")
```

### 3. Concatenar clips de grabaciones de clase para publicar curso

Une multiples grabaciones de modulos de un curso en un solo video con transicion, recodificando al mismo formato.

```python
import ffmpeg
from pathlib import Path
import tempfile
import os

def concatenar_clips_curso(
    clips: list[str],
    output: str,
    titulo_curso: str = "",
) -> None:
    """
    Concatena clips de video al mismo codec. Todos los clips deben tener
    la misma resolucion y frame rate para mejor compatibilidad.
    """
    # Crear archivo de lista temporal para ffmpeg concat demuxer
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for clip in clips:
            ruta_abs = Path(clip).resolve()
            f.write(f"file '{ruta_abs}'\n")
        lista_path = f.name

    try:
        (
            ffmpeg
            .input(lista_path, format="concat", safe=0)
            .output(
                output,
                vcodec="libx264",
                acodec="aac",
                crf=22,
                preset="fast",
                movflags="faststart",
            )
            .overwrite_output()
            .run(quiet=False)
        )
    finally:
        os.unlink(lista_path)

    size_mb = Path(output).stat().st_size / 1024 / 1024
    print(f"Curso compilado: {output} ({size_mb:.1f} MB, {len(clips)} clips)")


modulos = sorted(Path("grabaciones_modulos/").glob("modulo_*.mp4"))
concatenar_clips_curso(
    [str(m) for m in modulos],
    "curso_bim_completo.mp4",
    titulo_curso="Master BIM + IA 2025",
)
```

### 4. Generar GIF animado de un detalle constructivo para Notion o LinkedIn

Convierte un segmento de video a GIF optimizado para redes sociales o documentacion en Notion.

```python
import ffmpeg
from pathlib import Path

def video_a_gif_optimizado(
    video_path: str,
    output_gif: str,
    inicio: float = 0,
    duracion: float = 6.0,
    ancho: int = 640,
    fps: int = 12,
) -> None:
    """
    Convierte segmento de video a GIF de alta calidad usando paleta de colores
    personalizada (mejor calidad que conversion directa).
    """
    paleta_path = output_gif.replace(".gif", "_paleta.png")

    # Paso 1: Generar paleta de colores optima
    (
        ffmpeg
        .input(video_path, ss=inicio, t=duracion)
        .filter("fps", fps=fps)
        .filter("scale", ancho, -1, flags="lanczos")
        .filter("palettegen", stats_mode="diff")
        .output(paleta_path)
        .overwrite_output()
        .run(quiet=True)
    )

    # Paso 2: Aplicar paleta para generar GIF
    stream = ffmpeg.input(video_path, ss=inicio, t=duracion)
    paleta = ffmpeg.input(paleta_path)

    (
        ffmpeg
        .filter([stream.filter("fps", fps=fps).filter("scale", ancho, -1, flags="lanczos"), paleta],
                "paletteuse", dither="bayer")
        .output(output_gif)
        .overwrite_output()
        .run(quiet=True)
    )

    Path(paleta_path).unlink(missing_ok=True)
    size_kb = Path(output_gif).stat().st_size / 1024
    print(f"GIF generado: {output_gif} ({size_kb:.0f} KB, {fps}fps, {ancho}px)")


# Generar GIF de un detalle de modelo BIM para compartir
video_a_gif_optimizado(
    "walkthrough_modelo.mp4",
    "detalle_estructura.gif",
    inicio=45.0,
    duracion=5.0,
    ancho=480,
    fps=10,
)
```

---

## Utilidades rapidas (one-liners)

```python
import ffmpeg

# Ver metadata de un video
info = ffmpeg.probe("video.mp4")
print(info["format"]["duration"], info["streams"][0]["codec_name"])

# Extraer audio de un video (para transcripcion)
ffmpeg.input("grabacion.mp4").output("audio.mp3", acodec="libmp3lame", q=2).run()

# Convertir imagenes PNG en secuencia a video (time-lapse)
ffmpeg.input("frames/frame_%04d.png", framerate=10).output("timelapse.mp4", vcodec="libx264", crf=18).run()

# Rotar video 90 grados (video grabado en portrait desde movil)
ffmpeg.input("vertical.mp4").filter("transpose", 1).output("horizontal.mp4").run()
```

## Notas

- `ffmpeg-python` no incluye FFmpeg; este debe instalarse por separado en el sistema.
- El parametro `crf` (Constant Rate Factor) controla calidad: 18=casi sin perdida, 23=default web, 28=streaming bajo bitrate.
- `movflags="faststart"` reubica los metadatos al inicio del archivo MP4, permitiendo reproduccion antes de descarga completa.
- Para procesamiento en lotes de muchos videos, usar `subprocess` con `ffmpeg` directamente o `concurrent.futures`.
- Verificar version de FFmpeg instalada: `ffmpeg -version`. Versiones >=4.x soportan todos los filtros documentados.
