---
id: "028"
title: "OODA Report con Langfuse — Reporte semanal de observabilidad"
assigned_to: github-copilot
branch: feat/copilot-ooda-langfuse
round: 7
status: assigned
created: 2026-03-04
---

## Objetivo

Completar el script `scripts/ooda_report.py` que actualmente tiene un stub para Langfuse. Conectarlo a la API de Langfuse para generar reportes semanales de observabilidad con métricas reales de uso LLM.

## Contexto

- `scripts/ooda_report.py` — tiene `_report_from_langfuse()` con un TODO
- `worker/tracing.py` — módulo de tracing (creado en tarea 027)
- `worker/tasks/observability.py` — handlers `handle_ooda_report` y `handle_self_eval`

## Requisitos

### 1. Completar `_report_from_langfuse()` en `scripts/ooda_report.py`

Usar la API REST de Langfuse o el SDK para obtener:

```python
def _report_from_langfuse(days: int = 7) -> Dict[str, Any]:
    """Genera métricas de las últimas N days desde Langfuse."""
    from langfuse import Langfuse
    lf = Langfuse(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
    )
    
    # Métricas a obtener:
    # - Total de traces (calls) por provider
    # - Tokens consumidos por provider
    # - Latencia promedio por provider
    # - Errores por provider
    # - Top 5 task_types por volumen
    # - Costo estimado por provider (tokens * rate)
```

### 2. Formato del reporte OODA

Generar un reporte semanal con formato:

```
📊 OODA Weekly Report — Semana del 2026-02-24 al 2026-03-02

== Observe ==
- Total LLM calls: 847
- Providers: gemini (612), openai (180), anthropic (55)
- Tokens totales: 1.2M (input: 890K, output: 310K)

== Orient ==
- Gemini: 72% del volumen, latencia promedio 1.2s
- OpenAI: 21% del volumen, latencia promedio 0.8s
- Errores: 12 (1.4%) — 8 Gemini timeout, 4 Anthropic rate limit

== Decide ==
- Gemini warn threshold alcanzado 3 veces
- Recomendación: rotar más tráfico a OpenAI para research

== Act ==
- Acciones sugeridas:
  1. Ajustar warn threshold de gemini_pro a 0.75
  2. Considerar gpt-4o-mini para tasks "general" (más barato)
  3. Revisar timeouts de Gemini (8 errores esta semana)
```

### 3. Cron semanal

- Crear `scripts/vps/ooda-report-cron.sh`
- Agregar a `install-cron.sh`: `0 7 * * 1` (lunes 7:00 UTC)
- Postear reporte en Notion via Worker API

### 4. Graceful cuando Langfuse no está

Si `LANGFUSE_PUBLIC_KEY` no está configurado:
- Generar reporte solo con datos de Redis (quota_tracker)
- Indicar claramente "Langfuse no configurado — datos parciales"

### 5. Tests

- Test `_report_from_langfuse` con mock del SDK
- Test formato OODA con datos sintéticos
- Test fallback sin Langfuse keys

## Entregable

PR a `main` desde `feat/copilot-ooda-langfuse` con todos los tests pasando.
