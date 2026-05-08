---
id: 013-J
status: open
created: 2026-05-07
owner: rick
assigned_to: tbd
blocks: 013-F Phase 4.4 bulk
related: 013-F, 013-G, 013-H, 013-I, gap YouTube/RSSHub
---

# 013-J — Skip Phase 4.4 bulk + abrir gap YouTube/RSSHub

## Decisión

**Phase 4.4 bulk de 013-F: SKIP.**

Owner (Rick) dio go/no-go = no-go el 2026-05-07 tras Comet round-3 PASS sobre los
5 items de prueba de 013-I.

### Justificación

- Items pendientes en SQLite con `promovido_a_candidato_at IS NOT NULL AND notion_page_id IS NULL`: **15**, todos canal `youtube`.
- Ya tenemos un test live de YouTube en round-3: `sqlite_id=51` (referente `e9271bac-4dd2-4b7a-a8b8-ccd2e9089057`, "¿Existen Fisuras en el Universo?") — se pusheó a Notion como `created_no_body` con `blocks_count=1` (solo header, sin cuerpo).
- Causa: el pipeline Stage 2 actual no extrae `contenido_html` para items que vienen vía RSSHub de YouTube — el `description`/`content` queda vacío o trivial. Stage 4 entonces crea una página Notion sin cuerpo (stub).
- Conclusión: ejecutar el bulk de 15 items youtube produciría **15 stubs vacíos en `📰 Publicaciones de Referentes`** sin valor, ensuciando la base. Mejor dejarlos en SQLite hasta resolver el gap.

### Estado SQLite congelado (snapshot 2026-05-07)

- 5 items con `notion_page_id` (rowids `1, 31, 32, 33, 51`) — round-3 ya validados visualmente. **NO TOCAR.**
- 15 items promoted sin `notion_page_id`, todos youtube, distribuidos entre 8 referentes:

| referente_id | rowids |
|---|---|
| `080bbf47-03b9-4362-b4ff-0bd198249eb0` | 52 |
| `1848755f-3a58-4d11-ad97-8c23a80c962d` | 81, 82 |
| `186db773-ec72-4717-8098-ff12f45279d0` | 111 |
| `23addaef-d334-4b86-b90a-649ce7f7d82a` | 141, 142 |
| `6af76981-e122-41d4-9ef2-bb75ad977f63` | 261, 262 |
| `7f4f58e9-80cd-41e5-a78d-a0e0f079aa8d` | 291, 292, 293 |
| `d7c794b6-a61f-4739-b7fb-10e0bdc61ae0` | 351, 352, 353 |
| `e9271bac-4dd2-4b7a-a8b8-ccd2e9089057` | 408 |

## Bloqueo

Bulk de los 15 youtube queda **bloqueado por el gap YouTube/RSSHub** descrito en este task. Se desbloquea cuando 013-J entregue extracción de cuerpo no-trivial para al menos 1 video de prueba por referente youtube.

## Próximo trabajo (013-J)

Investigar 3 alternativas en orden de menor a mayor invasividad:

1. **`yt-dlp --write-info-json --skip-download`** — produce JSON con `description`, `chapters`, `tags`, `categories`, `upload_date`, etc. + opcionalmente `--write-auto-sub --sub-format vtt` para subtitles auto-generados. Sin descarga del video. Comparar campos disponibles vs schema actual de `discovered_items.contenido_html`.

2. **`youtube-transcript-api`** (paquete pip) — extrae transcripciones (auto-captions o manuales) directamente vía API pública de YouTube. Más rápido que yt-dlp, menos metadata, foco en texto.

3. **Feed RSS oficial de YouTube** (`https://www.youtube.com/feeds/videos.xml?channel_id=<UC...>`) — vs RSSHub que usamos hoy. El feed oficial expone `media:description` y `media:title` que pueden traer más contenido que lo que RSSHub está parseando. Comparar diff de campos por canal.

### Aceptación 013-J

- Al menos **1 video de prueba por cada uno de los 8 referentes youtube** listados arriba debe quedar capturado en SQLite con:
  - `titulo` (ya OK)
  - `contenido_html` (o equivalente) con descripción no-trivial (>200 chars)
  - **OR** transcript con timestamps (>500 chars)
- Adapter en Stage 2 que normalice los 3 caminos a `contenido_html` consumible por `html_to_notion_blocks._md_lines_to_blocks`.
- 3 tests nuevos (uno por alternativa) en `tests/test_stage2_content_extraction.py` o nuevo file.
- Tras 013-J en verde: re-evaluar Phase 4.4 bulk con los 15 items pendientes.

## Hard rules para 013-J

- NO modificar SQLite manualmente (solo via pipeline Stage 2).
- NO tocar las 5 páginas Notion ya creadas (rowids 1, 31, 32, 33, 51).
- Default dry-run en cualquier nuevo script de extracción/push; `--commit` opt-in.
- Token Notion solo en headers HTTP, nunca en logs/reports/PR body.
- Rate-limit YouTube/RSSHub: máximo 1 request/segundo por host (más conservador que Notion 350ms).
