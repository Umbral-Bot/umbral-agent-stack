---
name: composite
description: >-
  Ejecutar tareas compuestas de investigación y generación de reportes.
  Orquesta múltiples búsquedas web (research.web) + generación LLM
  (llm.generate) para producir un reporte de investigación completo en
  Notion. Usa cuando el usuario pida "investigar y reportar",
  "research report", "reporte de investigación", "buscar y resumir",
  "análisis de mercado", "estudio de tema".
metadata:
  openclaw:
    emoji: "📊"
    requires:
      env:
        - TAVILY_API_KEY
        - GOOGLE_AI_API_KEY
---

# Composite Research Report

Skill para generar reportes de investigación completos a partir de un solo tema. Orquesta automáticamente el pipeline: generación de queries → búsqueda web → síntesis LLM.

## Worker Task

`composite.research_report`

## Parámetros

| Parámetro | Tipo | Requerido | Default | Descripción |
|-----------|------|-----------|---------|-------------|
| `topic` | string | ✅ | — | Tema a investigar |
| `queries` | list[str] | ❌ | auto-generadas | Queries de búsqueda explícitas |
| `depth` | string | ❌ | `"standard"` | Profundidad: `"quick"` (3 queries), `"standard"` (5), `"deep"` (10) |
| `language` | string | ❌ | `"es"` | Idioma del reporte |

## Respuesta

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `report` | string | Reporte completo en markdown |
| `sources` | list[dict] | Fuentes usadas `{title, url, query}` |
| `queries_used` | list[str] | Queries ejecutadas |
| `stats` | dict | Estadísticas `{total_sources, research_time_ms, generation_time_ms}` |

## Estructura del Reporte

1. **Resumen Ejecutivo** — 2-3 párrafos
2. **Hallazgos Principales** — con citas de fuentes
3. **Tendencias Identificadas** — patrones observados
4. **Recomendaciones** — acciones concretas

## Ejemplos de Uso

### Investigación rápida

```json
{
  "task": "composite.research_report",
  "input": {
    "topic": "Adopción de BIM en Latinoamérica 2025",
    "depth": "quick"
  }
}
```

### Investigación profunda con queries custom

```json
{
  "task": "composite.research_report",
  "input": {
    "topic": "IA generativa en diseño arquitectónico",
    "depth": "deep",
    "queries": [
      "AI generative design architecture 2025",
      "parametric design machine learning",
      "midjourney architecture workflow"
    ],
    "language": "es"
  }
}
```

## Pipeline Interno

```
topic → LLM genera N queries → research.web × N → LLM sintetiza → reporte markdown
```

## Dependencias

- `research.web` (Tavily API)
- `llm.generate` (Gemini / OpenAI / Anthropic según routing)

## Regla cuando el reporte alimenta una verificacion en browser

Si el trabajo no termina en el reporte y despues alguien abrira una fuente en
browser o GUI para comprobarla:

- no dependas de una sola URL por hallazgo importante;
- conserva al menos 2 fuentes plausibles cuando el tema lo permita;
- si la primera fuente abierta devuelve `404`, `Page not found`, homepage
  generica o contenido no relacionado, la verificacion debe saltar a la
  siguiente fuente antes de cerrar;
- separar siempre `hallazgo de research` de `verificacion browser`.
