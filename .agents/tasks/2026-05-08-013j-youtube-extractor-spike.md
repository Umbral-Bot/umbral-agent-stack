# Task 013-J — Spike YouTube extractor (cerrar gap RSSHub)

**Owner**: Copilot VPS
**Tipo**: spike de investigación + benchmark, NO refactor de pipeline.
**Bloquea**: Phase 4.4 bulk de 013-F (15 items youtube en SQLite con `notion_page_id IS NULL`).
**Branch**: `copilot-vps/013j-youtube-extractor-spike`
**Base**: `main` (stack 013-F/G/H/I ya aterrizado en `cc0803b`).

## Contexto

Pipeline render Notion (013-F→I) listo y validado en main. Quedan 15 items
youtube en SQLite (`promovido_a_candidato_at IS NOT NULL AND notion_page_id
IS NULL`) de 8 referentes. sqlite_id=51 (test, ya pusheado) cayó en
`created_no_body` → confirmado: el feed RSSHub no entrega cuerpo para los
canales de los 8 referentes youtube.

## Objetivo del spike

Comparar 3 alternativas de extracción de contenido YouTube y entregar
recomendación accionable + microbenchmark sobre 1 video por referente
(8 videos total). NO modificar Stage 2 todavía. NO crear pages Notion.

## Alternativas a evaluar (en orden estricto)

### Alt 1 — `yt-dlp --skip-download --write-info-json`
- Instalación: `pip install yt-dlp` (ya disponible en .venv, verificar).
- Output: JSON estructurado con `title`, `description`, `upload_date`,
  `channel`, `channel_id`, `tags`, `categories`, `duration`, `view_count`,
  `like_count`, `webpage_url`, `thumbnail`, `chapters` (si existen).
- NO incluye transcript por sí solo (requiere `--write-auto-subs`).
- Pro: 1 sola llamada, robusto, mantenido, no API keys.
- Contra: `description` puede ser texto plano sin formato HTML; `chapters`
  son la estructura más rica pero opcionales.

### Alt 2 — `youtube-transcript-api` (Python)
- Instalación: `pip install youtube-transcript-api`.
- Output: lista de `{text, start, duration}` para auto-captions o manual
  captions.
- Pro: transcript completo, bueno para resúmenes / búsqueda full-text.
- Contra: depende de que el video tenga captions habilitadas (probable
  para canales profesionales, no garantizado).

### Alt 3 — Feed RSS oficial de YouTube
- URL pattern: `https://www.youtube.com/feeds/videos.xml?channel_id=<UCxxxx>`.
- Output: Atom feed con `<media:description>` (corto, sin HTML).
- Pro: 0 deps, 0 auth, oficial.
- Contra: descripción truncada (~200 char), no transcript, no chapters.

## Tareas concretas

### Task 1 — Crear script de spike

Path: `scripts/discovery/spike_youtube_extractor.py`

CLI:
```
python -m scripts.discovery.spike_youtube_extractor \
  --sqlite-ids <list>                      # default: los 15 promoted youtube
  --output reports/spike-youtube-<TS>.json
```

Read-only. NO escribe en SQLite. NO llama a Notion API.

Por cada sqlite_id:
1. Lee `url_canonica` y `referente_id` desde SQLite.
2. Extrae `youtube_video_id` desde la URL (regex `(?:v=|youtu\.be/)([\w-]{11})`).
3. Ejecuta las 3 alternativas (cada una con timeout 30s y try/except aislado):
   - alt1: `yt_dlp.YoutubeDL({'skip_download': True, 'quiet': True}).extract_info(url, download=False)`
   - alt2: `YouTubeTranscriptApi.get_transcript(video_id, languages=['es','en'])`
   - alt3: `httpx.get(f"https://www.youtube.com/feeds/videos.xml?channel_id=...")` + parse del entry correspondiente
4. Guarda en el report:
   ```json
   {
     "sqlite_id": 7,
     "video_id": "abcDef12345",
     "url": "...",
     "referente_id": "186db773",
     "alt1_yt_dlp": {
       "ok": true,
       "title_len": 42,
       "description_len": 1843,
       "has_chapters": true,
       "chapters_count": 8,
       "tags_count": 12,
       "duration_seconds": 2340,
       "elapsed_ms": 1234
     },
     "alt2_transcript": {
       "ok": true,
       "transcript_segments": 487,
       "transcript_chars": 28950,
       "language": "es",
       "is_auto": true,
       "elapsed_ms": 8210
     },
     "alt3_atom": {
       "ok": true,
       "description_len": 198,
       "elapsed_ms": 412
     }
   }
   ```

### Task 2 — Microbenchmark + recomendación

En el mismo report (top-level), agregar:
- Conteo de éxitos por alternativa.
- Promedio de `elapsed_ms` por alternativa.
- Cobertura de `description_len > 500` por alternativa (proxy de "cuerpo
  útil").
- Cobertura de `transcript_chars > 1000` (alt2).
- **Recomendación textual** (1-2 párrafos): qué alternativa o combinación
  usar para el adapter de Stage 2, justificando con números del benchmark.

Hipótesis previa a validar: **alt1 + alt2 combinadas** es lo más rico
(metadata estructurada + transcript completo). Si alt2 falla en >50% de
los videos, queda solo alt1. Si alt1 también falla en >25%, fallback a
alt3.

### Task 3 — NO tocar Stage 2 todavía

El spike termina con el report + recomendación. Stage 2 adapter es 013-K
(siguiente task, no incluida en este spike).

## Quality gates

- Script ejecuta los 8 videos sin errores fatales (cada alt puede fallar
  individualmente, pero el script termina).
- Report JSON válido, parseable.
- Recomendación basada en datos del report, no opinión.
- 0 secretos en el código (no hay API keys involucradas, pero verificar).
- Tests: 1 test mínimo en `tests/test_spike_youtube_extractor.py`
  validando el parser de `video_id` desde URL (acepta `youtube.com/watch?v=`
  y `youtu.be/` y URLs con `&t=`).

## Reglas duras

- Read-only sobre SQLite.
- 0 escrituras Notion.
- Branch nueva sobre `main`: `copilot-vps/013j-youtube-extractor-spike`.
- PR base = `main`.
- Token Notion no necesario (no se usa).
- Si yt-dlp no está en `.venv`, instalar con `pip install yt-dlp
  youtube-transcript-api` y agregar a `pyproject.toml [project.optional-dependencies]`
  bajo nuevo grupo `youtube` (NO al `test` ni al core).

## Aceptación

- PR abierto contra main.
- Report `reports/spike-youtube-<TS>.json` commiteado con datos reales de
  los 8 videos.
- Sección de recomendación en el report.
- 1 test verde.
- STOP — owner decide si arrancar 013-K (adapter Stage 2) o iterar el spike.
