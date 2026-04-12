---
name: rag-knowledge
description: >-
  RAG (Retrieval-Augmented Generation) sobre base de conocimiento en Azure AI
  Search. Rick puede indexar documentos (Notion pages, archivos, web), buscar
  con búsqueda híbrida (keyword + vector), y responder preguntas con contexto
  recuperado. Usa cuando "buscar en la base de conocimiento", "qué sabemos de",
  "indexar documentos", "RAG", "buscar en nuestros docs", "base de conocimiento",
  "knowledge base", "pregunta sobre el proyecto".
metadata:
  openclaw:
    emoji: "\U0001F4DA"
    requires:
      env:
        - AZURE_SEARCH_ENDPOINT
        - AZURE_SEARCH_API_KEY
        - AZURE_OPENAI_ENDPOINT
        - AZURE_OPENAI_API_KEY
---

# RAG Knowledge Skill

Rick puede indexar documentos en Azure AI Search y luego buscar/responder
preguntas usando contexto recuperado (RAG).

## Cuándo usar

- David pregunta algo que debería estar en la documentación interna.
- Se necesita buscar información en documentos ya indexados.
- Se requiere indexar nuevos documentos al knowledge base.
- Responder preguntas complejas con evidencia de múltiples fuentes.

## Tasks disponibles

### 1. Crear/actualizar índice

```json
{
  "task": "rag.ensure_index",
  "input": {
    "index_name": "umbral-knowledge"
  }
}
```

### 2. Indexar documentos

```json
{
  "task": "rag.index",
  "input": {
    "documents": [
      {
        "content": "Texto completo del documento...",
        "title": "Arquitectura Worker v2",
        "source": "docs/01-architecture-v2.3.md",
        "source_type": "file"
      }
    ],
    "chunk_size": 1000,
    "chunk_overlap": 200
  }
}
```

### 3. Buscar (sin LLM)

```json
{
  "task": "rag.search",
  "input": {
    "query": "cómo funciona el dispatcher",
    "top": 5,
    "mode": "hybrid",
    "source_type_filter": "file"
  }
}
```

### 4. Preguntar (buscar + LLM)

```json
{
  "task": "rag.query",
  "input": {
    "question": "¿Cómo maneja el Worker las tareas de Notion?",
    "top": 5,
    "model": "azure_foundry"
  }
}
```

## Parámetros de búsqueda

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `query` / `question` | str | **requerido** | Texto de búsqueda o pregunta |
| `top` | int | 5 | Número de resultados (max 20) |
| `mode` | str | "hybrid" | "keyword", "vector", o "hybrid" |
| `source_filter` | str | — | Filtrar por fuente específica |
| `source_type_filter` | str | — | Filtrar por tipo: notion, file, web |

## Flujo RAG (rag.query)

1. **Retrieve** — Búsqueda híbrida en Azure AI Search (keyword + vector).
2. **Augment** — Contexto recuperado se inyecta en system prompt del LLM.
3. **Generate** — LLM genera respuesta basada SOLO en contexto recuperado.
   Si no hay suficiente contexto, lo declara explícitamente.

## Fuentes indexables

| Tipo | source_type | Ejemplo |
|------|------------|---------|
| Docs del repo | file | docs/01-architecture-v2.3.md |
| Páginas Notion | notion | notion://page/{id} |
| Transcripts Granola | granola | granola://session/{id} |
| Web research | web | https://example.com/article |
| Runbooks | file | runbooks/deploy-worker.md |

## Pipeline típico de indexación

Rick puede combinar las herramientas existentes para indexar:

1. `notion.read_page` → obtener contenido
2. `rag.index` → indexar con source_type="notion"
3. Repetir para múltiples páginas

O para documentos del repo:

1. Leer archivos desde docs/ o runbooks/
2. `rag.index` → indexar con source_type="file"
