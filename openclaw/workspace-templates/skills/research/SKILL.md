---
name: research
description: >-
  Perform web searches and generate structured research reports using Tavily API
  and LLM synthesis. Use when "search the web", "research topic", "find information",
  "generate report", "market research", "investigate", "web search".
metadata:
  openclaw:
    emoji: "\U0001F50D"
    requires:
      env:
        - TAVILY_API_KEY
---

# Research Skill

Rick puede buscar información en la web y generar reportes de investigación estructurados combinando búsquedas con síntesis LLM.

## Requisitos

- `TAVILY_API_KEY`: API key de Tavily Search (https://tavily.com).

## Tasks disponibles

### 1. Búsqueda web

Task: `research.web`

```json
{
  "query": "tendencias fintech 2026 latam",
  "count": 5,
  "search_depth": "basic"
}
```

Parámetros:

| Parámetro | Tipo | Requerido | Default | Descripción |
|---|---|---|---|---|
| `query` | str | ✅ | — | Término o pregunta de búsqueda |
| `count` | int | — | `5` | Número de resultados (max 20) |
| `search_depth` | str | — | `"basic"` | `"basic"` o `"advanced"` |

Devuelve: lista de resultados con `title`, `url` y `snippet`.

### 2. Reporte de investigación compuesto

Task: `composite.research_report`

```json
{
  "topic": "Impacto de la IA generativa en marketing digital",
  "depth": "standard",
  "language": "es"
}
```

Parámetros:

| Parámetro | Tipo | Requerido | Default | Descripción |
|---|---|---|---|---|
| `topic` | str | ✅ | — | Tema a investigar |
| `queries` | list[str] | — | auto-generadas | Queries de búsqueda específicas |
| `depth` | str | — | `"standard"` | `"quick"` (3), `"standard"` (5), `"deep"` (10) queries |
| `language` | str | — | `"es"` | Idioma del reporte |

Devuelve:

```json
{
  "report": "# Reporte...",
  "sources": [{"title": "...", "url": "...", "query": "..."}],
  "queries_used": ["query1", "query2"],
  "stats": {
    "total_sources": 25,
    "research_time_ms": 4500,
    "generation_time_ms": 8200
  }
}
```

El reporte incluye: Resumen Ejecutivo, Hallazgos Principales, Tendencias Identificadas y Recomendaciones, con citas de fuentes inline.

## Notas

- Todas las tasks se encolan vía el Dispatcher a Redis y las ejecuta el Worker.
- `composite.research_report` orquesta internamente múltiples llamadas a `research.web` + `llm.generate`.
- Si las queries no se proporcionan, se auto-generan usando el LLM.
- Tavily tiene rate limits; `search_depth: "advanced"` consume más cuota.
