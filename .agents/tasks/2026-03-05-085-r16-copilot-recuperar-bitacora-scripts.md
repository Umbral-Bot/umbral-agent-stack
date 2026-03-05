---
id: "2026-03-05-085"
title: "R16 — Recuperar scripts de enriquecimiento Bitácora"
status: done
assigned_to: github-copilot
created_by: david
priority: medium
sprint: R16
created_at: 2026-03-05T05:00:00-06:00
updated_at: 2026-03-05T05:30:00-06:00
---

## Objetivo
Recuperar los scripts de enriquecimiento de la Bitácora Notion desde la rama cerrada de PR #72, sin modificar worker/dispatcher/CI.

## Contexto
PR #72 (`cursor/bit-cora-contenido-enriquecido-4099`) fue cerrado en la tarea 080. Contenía scripts únicos para enriquecer las páginas de la Bitácora en Notion con métricas, diagramas Mermaid y resúmenes no técnicos. El inventario (tarea 082) marcó estos como "⚠️ Recuperar parcial".

## Rama origen
`cursor/bit-cora-contenido-enriquecido-4099` (PR #72 cerrado)

## Archivos recuperados
1. `scripts/enrich_bitacora_pages.py` — Enriquece 22 páginas de la Bitácora con resúmenes ampliados, diagramas Mermaid, tablas de tareas/PRs, línea de tiempo
2. `scripts/add_resumen_amigable.py` — Añade sección "En pocas palabras" con resúmenes no técnicos al inicio de cada página
3. `tests/test_notion_enrich_bitacora.py` — 34 tests para el handler `enrich_bitacora_page` y helpers de notion_client

## Dependencias pendientes (requieren PR separado)
Los scripts importan funciones de `worker/notion_client.py` que **no existen aún en main**:

| Función | Módulo | Usada por |
|---------|--------|-----------|
| `_block_code` | worker.notion_client | enrich_bitacora_pages.py, tests |
| `query_database` | worker.notion_client | ambos scripts, tests |
| `append_blocks_to_page` | worker.notion_client | enrich_bitacora_pages.py, tests |
| `prepend_blocks_to_page` | worker.notion_client | add_resumen_amigable.py, tests |
| `_convert_block_for_write` | worker.notion_client | tests |
| `_fetch_children_blocks` | worker.notion_client | (interna, usada por prepend) |
| `handle_notion_enrich_bitacora_page` | worker.tasks.notion | tests |
| `_sections_to_blocks` | worker.tasks.notion | tests |
| `_raw_blocks_to_notion` | worker.tasks.notion | tests |

### Funciones que ya existen en main (✅)
`_block_heading2`, `_block_heading3`, `_block_paragraph`, `_block_bulleted`, `_block_callout`, `_block_divider`, `_block_table`

### Variables de entorno requeridas
- `NOTION_API_KEY` — API key de Notion
- `NOTION_BITACORA_DB_ID` — ID de la base de datos Bitácora (default: `85f89758684744fb9f14076e7ba0930e`)

### Dependencias externas
- `gh` CLI (GitHub CLI) — usado por `enrich_bitacora_pages.py` para obtener info de PRs (`gh pr view`, `gh pr list`)

## Criterios de aceptación
- [x] Scripts de enriquecimiento Bitácora recuperados de rama cerrada PR #72
- [x] Tests recuperados (34 tests para handler + helpers)
- [x] Dependencias documentadas (funciones faltantes, env vars, gh CLI)
- [x] PR abierto desde `copilot/085-recuperar-bitacora-scripts` a main (solo scripts + docs)
- [x] No se modifica worker, dispatcher ni CI

## Log
### [github-copilot] 2026-03-05 05:30
- Fetched branch `origin/cursor/bit-cora-contenido-enriquecido-4099` (PR #72)
- `git diff --name-status` mostró 22 archivos cambiados en esa rama
- Recuperados 3 archivos nuevos via `git checkout origin/<branch> -- <files>`
- Import audit: 7 funciones de notion_client ya existen en main; 6 funciones + 3 handlers faltan
- Documentadas todas las dependencias pendientes para PR de worker separado
