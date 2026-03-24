---
name: research
description: >-
  Search the web and generate research reports using Tavily/Google CSE and LLM
  synthesis. Use when "search the web", "research topic", "find information",
  "market research", "generate report", "investigate", "web search".
metadata:
  openclaw:
    emoji: "\U0001F50D"
    requires:
      env:
        - TAVILY_API_KEY
---

# Research Skill

Rick puede buscar información en la web y generar reportes de investigación completos combinando búsqueda web con síntesis LLM.

## Requisitos

- `TAVILY_API_KEY`: API key de Tavily Search (preferido).
- Alternativa: `GOOGLE_CSE_API_KEY_RICK_UMBRAL` + `GOOGLE_CSE_CX` para Google Custom Search.

## Tasks disponibles

### 1. Búsqueda web

Task: `research.web`

```json
{
  "query": "tendencias inteligencia artificial 2026",
  "count": 5,
  "search_depth": "basic"
}
```

#### Parámetros

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `query` | str | sí | Término o pregunta de búsqueda |
| `count` | int | no | Número de resultados (default: 5, max: 20) |
| `search_depth` | str | no | `"basic"` o `"advanced"` (default: `"basic"`) |

#### Respuesta

```json
{
  "results": [
    {"title": "...", "url": "https://...", "snippet": "..."}
  ],
  "count": 5,
  "engine": "tavily"
}
```

### 2. Reporte de investigación compuesto

Task: `composite.research_report`

Orquesta múltiples `research.web` + `llm.generate` para producir un reporte completo de investigación.

```json
{
  "topic": "Impacto de la IA generativa en el sector financiero",
  "depth": "standard",
  "language": "es"
}
```

#### Parámetros

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `topic` | str | sí | Tema a investigar |
| `queries` | list[str] | no | Queries específicos (auto-generados si se omiten) |
| `depth` | str | no | `"quick"` (3 queries), `"standard"` (5), `"deep"` (10). Default: `"standard"` |
| `language` | str | no | Idioma del reporte (default: `"es"`) |

#### Respuesta

```json
{
  "report": "# Reporte: Impacto de la IA...\n\n## Resumen Ejecutivo\n...",
  "sources": [{"title": "...", "url": "...", "query": "..."}],
  "queries_used": ["query 1", "query 2"],
  "stats": {
    "total_sources": 25,
    "research_time_ms": 4500,
    "generation_time_ms": 3200
  }
}
```

## Notas

- El reporte incluye: Resumen Ejecutivo, Hallazgos Principales, Tendencias Identificadas y Recomendaciones.
- Las fuentes se citan inline como `[Título](URL)` en el reporte markdown.
- Profundidad `deep` produce reportes más detallados pero consume más cuota de API.
- Todas las tasks se encolan vía el Dispatcher a Redis y las ejecuta el Worker.

## Regla de verificacion cuando despues usaras browser o GUI

Si el pedido no es solo "buscar", sino tambien "abrir", "verificar", "comprobar"
o "mirar en browser" una fuente encontrada:

1. no cierres con una sola URL candidata;
2. guarda al menos 2 resultados plausibles de `research.web`;
3. intenta verificar primero la mejor fuente;
4. si la primera devuelve `404`, `Page not found`, homepage generica, paywall
   no superable, login wall o contenido no relacionado con el hallazgo buscado,
   prueba una segunda fuente antes de concluir;
5. separa siempre:
   - **hallazgo de research**
   - **verificacion browser**

No uses "verificado", "confirmado" u otra formula equivalente si la URL abierta
no muestra el contenido esperado en browser o GUI.

## Cierre esperado para research + browser

Cuando combines research con browser/gui, la salida debe dejar claro:

- que fuente salio de `research.web`;
- si la primera URL candidata abrio bien o fallo;
- si fue necesario fallback a una segunda fuente;
- si el hallazgo quedo **verificado en browser** o solo **sugerido por research**.
