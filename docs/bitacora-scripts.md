# Scripts de Enriquecimiento — Bitácora Notion

> Documentación de los scripts que enriquecen las páginas de la **Bitácora Umbral Agent Stack** en Notion.
>
> Scripts recuperados de la rama `cursor/bit-cora-contenido-enriquecido-4099` (PR #72 cerrado, tarea R16-085, PR #89).

---

## Scripts disponibles

### 1. `scripts/enrich_bitacora_pages.py`

Enriquece las páginas existentes de la Bitácora en Notion. Para cada entrada de la base de datos:

1. Extrae título y propiedades existentes de la página.
2. Busca contexto relevante en `.agents/board.md`, `.agents/tasks/`, y PRs de GitHub (vía `gh` CLI).
3. Genera contenido enriquecido:
   - **Resumen ampliado** (2-4 párrafos con contexto técnico y agentes involucrados)
   - **Diagrama Mermaid** (flowchart, arquitectura, componente, timeline — según tipo de entrada)
   - **Tabla de tareas** relacionadas (título, asignado, estado)
   - **Tabla de Pull Requests** (número, título, fecha merge)
   - **Lista de archivos** modificados (+/-)
   - **Línea de tiempo** Mermaid (si la ronda tiene ≥2 tareas)
4. Añade los bloques generados al final de la página vía `notion_client.append_blocks_to_page`.

**Uso:**
```bash
# Enriquecer todas las páginas
python scripts/enrich_bitacora_pages.py

# Solo generar, sin enviar a Notion
python scripts/enrich_bitacora_pages.py --dry-run

# Limitar a N páginas
python scripts/enrich_bitacora_pages.py --limit 5

# Enriquecer una sola página
python scripts/enrich_bitacora_pages.py --page-id <UUID>
```

### 2. `scripts/add_resumen_amigable.py`

Añade la sección **"En pocas palabras"** al inicio de cada página de la Bitácora. Genera un resumen corto (2-4 oraciones) en español no técnico, e inserta un bloque `callout` como primer contenido visible, sin eliminar lo existente.

Incluye un mapeo de 20+ temas a resúmenes amigables (hackathon, rondas R1-R13, poller, skills, BIM, calendar, audit, governance, bitácora, pipeline, RRSS, etc.). Si no encuentra coincidencia, genera un resumen genérico.

**Uso:**
```bash
# Añadir resúmenes a todas las páginas
python scripts/add_resumen_amigable.py

# Solo generar, sin enviar a Notion
python scripts/add_resumen_amigable.py --dry-run

# Limitar a N páginas
python scripts/add_resumen_amigable.py --limit 5

# Solo una página
python scripts/add_resumen_amigable.py --page-id <UUID>
```

### 3. `tests/test_notion_enrich_bitacora.py`

34 tests unitarios que cubren:

| Clase | Tests | Qué cubre |
|-------|-------|-----------|
| `TestSectionsToBlocks` | 7 | Conversión secciones → bloques Notion (contenido, Mermaid, items, tabla, dividers) |
| `TestRawBlocksToNotion` | 9 | Conversión bloques raw → formato API (headings, code, paragraph, bullet, divider, callout, quote, table, unknown) |
| `TestHandlerEnrichBitacora` | 4 | Handler principal: con sections, con blocks, missing page_id, missing content |
| `TestNotionClientBlockCode` | 3 | `_block_code`: Mermaid, default language, truncación a 2000 chars |
| `TestNotionClientQueryDatabase` | 3 | `query_database`: básico, paginación, sin API key |
| `TestAppendBlocks` | 2 | `append_blocks_to_page`: básico, sin API key |
| `TestPrependBlocks` | 2 | `prepend_blocks_to_page`: básico, sin API key |
| `TestConvertBlockForWrite` | 4 | `_convert_block_for_write`: paragraph, divider, code, skip child_database |

---

## Variables de entorno requeridas

| Variable | Requerida | Default | Descripción |
|----------|-----------|---------|-------------|
| `NOTION_API_KEY` | **Sí** | — | Token de la integración Notion (formato `ntn_...`) |
| `NOTION_BITACORA_DB_ID` | No | `85f89758684744fb9f14076e7ba0930e` | ID de la base de datos Bitácora en Notion |

### Dependencia externa

- **`gh` CLI** (GitHub CLI) — usado por `enrich_bitacora_pages.py` para obtener info de PRs (`gh pr view`, `gh pr list`). Debe estar autenticado con `gh auth login`.

---

## Dependencias faltantes en `worker/`

Los scripts y tests importan funciones que **no existen aún en `main`**. Se deben implementar en un PR futuro antes de que los scripts sean ejecutables.

### `worker/notion_client.py` — 6 funciones faltantes

| # | Función | Firma sugerida | Descripción |
|---|---------|---------------|-------------|
| 1 | `_block_code` | `_block_code(text: str, language: str = "plain text") -> dict[str, Any]` | Genera un bloque de código Notion. Trunca `text` a 2000 caracteres (límite API). Soporta cualquier lenguaje Notion (mermaid, python, javascript, etc.). |
| 2 | `query_database` | `query_database(database_id: str, filter_obj: dict[str, Any] \| None = None) -> list[dict[str, Any]]` | Consulta una base de datos Notion con paginación automática (sigue `next_cursor`). Requiere `NOTION_API_KEY`. Lanza `RuntimeError` si no hay API key. |
| 3 | `append_blocks_to_page` | `append_blocks_to_page(page_id: str, blocks: list[dict[str, Any]]) -> dict[str, Any]` | Añade bloques al final de una página Notion vía `PATCH /v1/blocks/{page_id}/children`. Retorna `{"blocks_appended": N, "page_id": ...}`. Requiere `NOTION_API_KEY`. |
| 4 | `prepend_blocks_to_page` | `prepend_blocks_to_page(page_id: str, new_blocks: list[dict[str, Any]]) -> dict[str, Any]` | Inserta bloques al inicio de una página. Internamente: lee bloques existentes con `_fetch_children_blocks`, borra todos, reescribe `new_blocks + existentes`. Retorna `{"blocks_prepended": N, "blocks_preserved": M}`. |
| 5 | `_convert_block_for_write` | `_convert_block_for_write(block: dict[str, Any], client: httpx.Client) -> dict[str, Any] \| None` | Convierte un bloque leído (con `id`, `has_children`, etc.) al formato requerido para escritura (sin campos read-only). Retorna `None` para tipos no soportados (`child_database`, `child_page`). |
| 6 | `_fetch_children_blocks` | `_fetch_children_blocks(block_id: str, client: httpx.Client) -> list[dict[str, Any]]` | Lee todos los bloques hijos de una página/bloque vía `GET /v1/blocks/{block_id}/children` con paginación. Usada internamente por `prepend_blocks_to_page`. |

### `worker/tasks/notion.py` — 3 funciones faltantes

| # | Función | Firma sugerida | Descripción |
|---|---------|---------------|-------------|
| 1 | `handle_notion_enrich_bitacora_page` | `handle_notion_enrich_bitacora_page(input_data: Dict[str, Any]) -> Dict[str, Any]` | Handler principal del task `notion.enrich_bitacora_page`. Acepta `page_id` + (`sections` o `blocks`). Si recibe `sections`, las convierte con `_sections_to_blocks`. Si recibe `blocks`, los convierte con `_raw_blocks_to_notion`. Llama a `append_blocks_to_page`. Lanza `ValueError` si falta `page_id` o ambos `sections`/`blocks`. |
| 2 | `_sections_to_blocks` | `_sections_to_blocks(sections: list[Dict[str, Any]]) -> list[Dict[str, Any]]` | Convierte una lista de secciones de alto nivel a bloques Notion. Cada sección puede tener: `title` (→ heading_2), `content` (→ paragraphs separados por `\n\n`), `mermaid` (→ code block), `items` (→ bulleted list), `table` con `headers`+`rows` (→ table block). Añade divider tras cada sección. |
| 3 | `_raw_blocks_to_notion` | `_raw_blocks_to_notion(raw_blocks: list[Dict[str, Any]]) -> list[Dict[str, Any]]` | Convierte bloques en formato simplificado (`{"type": "heading_2", "text": "..."}`) al formato completo de la API Notion. Soporta: heading_1/2/3, paragraph, code, bulleted_list_item, divider, callout, quote, table. Tipos desconocidos → paragraph. |

---

## Orden recomendado de implementación

1. **`_block_code`** — sin dependencias, usado por los otros.
2. **`query_database`** — sin dependencias internas, necesario para ambos scripts.
3. **`append_blocks_to_page`** — necesario para `enrich_bitacora_pages.py` y el handler.
4. **`_convert_block_for_write`** + **`_fetch_children_blocks`** — necesarios para prepend.
5. **`prepend_blocks_to_page`** — depende de los dos anteriores, necesario para `add_resumen_amigable.py`.
6. **`_sections_to_blocks`** + **`_raw_blocks_to_notion`** + **`handle_notion_enrich_bitacora_page`** — handler completo.

> Una vez implementadas estas 9 funciones, los 34 tests de `test_notion_enrich_bitacora.py` deberían pasar, y ambos scripts serán ejecutables.
