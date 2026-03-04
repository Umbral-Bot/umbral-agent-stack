---
name: observability
description: >-
  System observability tasks for OODA reports and self-evaluation of Rick's
  performance. Provides operational metrics from Redis and Langfuse.
  Use when "system report", "ooda report", "self evaluation", "how am I doing",
  "system status", "weekly report", "evaluate performance", "check task metrics".
metadata:
  openclaw:
    emoji: "\U0001F4CA"
    requires:
      env:
        - WORKER_TOKEN
        - REDIS_URL
---

# Observability Skill

Rick puede generar reportes operativos y auto-evaluaciones de rendimiento a través de las tasks de observabilidad del Umbral Worker.

## Requisitos

| Variable | Descripción |
|----------|-------------|
| `WORKER_TOKEN` | Token de autenticación del Worker |
| `REDIS_URL` | URL de conexión a Redis (default: `redis://localhost:6379/0`) |
| `LANGFUSE_PUBLIC_KEY` | (Opcional) Para métricas de Langfuse en el reporte OODA |
| `LANGFUSE_SECRET_KEY` | (Opcional) Para métricas de Langfuse en el reporte OODA |

## Tasks disponibles

### 1. Reporte OODA

Task: `system.ooda_report`

Genera un reporte semanal basado en el ciclo **OODA** (Observe – Orient – Decide – Act) con datos reales de Redis y Langfuse.

**Input:**

| Campo | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `week_ago` | int | No | 0 | Semana a reportar: 0 = esta semana, 1 = semana pasada |
| `format` | str | No | `"markdown"` | Formato de salida: `"markdown"` o `"json"` |

**Output:**

```json
{
  "ok": true,
  "format": "markdown",
  "report": "# Reporte OODA — Semana 2026-03-03\n\n## Observe\n- Tareas completadas: 42\n..."
}
```

**Contenido del reporte:**

| Sección | Datos incluidos |
|---------|-----------------|
| **Observe** | Tareas completadas, fallidas, bloqueadas, pendientes en Redis |
| **Orient** | Uso de cuotas por provider, traces de Langfuse (tokens, latencia, errores) |
| **Decide** | Top task_types, distribución por provider, costo estimado |
| **Act** | Recomendaciones basadas en métricas |

#### Ejemplo

```json
{
  "task_type": "system.ooda_report",
  "input": {}
}
```

#### Reporte de semana pasada en JSON

```json
{
  "task_type": "system.ooda_report",
  "input": {
    "week_ago": 1,
    "format": "json"
  }
}
```

### 2. Auto-evaluación (Self Eval)

Task: `system.self_eval`

Evalúa la calidad de las tareas completadas recientemente por Rick. Cada tarea recibe un score en múltiples dimensiones.

**Input:**

| Campo | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `limit` | int | No | 20 | Máximo de tareas a evaluar |
| `format` | str | No | `"markdown"` | Formato de salida: `"markdown"` o `"json"` |

**Output:**

```json
{
  "ok": true,
  "format": "markdown",
  "tasks_evaluated": 15,
  "average_score": 0.82,
  "report": "# Self-Evaluation\n\n## Resumen\n- Tareas evaluadas: 15\n- Score promedio: 0.82\n..."
}
```

**Métricas de evaluación:**

| Dimensión | Descripción |
|-----------|-------------|
| `overall` | Score general de la tarea (0.0–1.0) |
| Calidad | ¿La respuesta es correcta y completa? |
| Eficiencia | ¿Se usaron los recursos óptimos? |
| Tiempo | ¿La tarea se completó en tiempo razonable? |

#### Ejemplo básico

```json
{
  "task_type": "system.self_eval",
  "input": {}
}
```

#### Evaluar últimas 50 tareas en JSON

```json
{
  "task_type": "system.self_eval",
  "input": {
    "limit": 50,
    "format": "json"
  }
}
```

## Manejo de errores

| Escenario | Resultado |
|-----------|-----------|
| Redis no disponible | `{"ok": true, ...}` con `source: "redis_unavailable"` en métricas |
| Langfuse no configurado | Reporte parcial sin sección de traces |
| Script no encontrado | `{"ok": false, "error": "No module named 'scripts.ooda_report'"}` |
| Error inesperado | `{"ok": false, "error": "descripción del error"}` |

## Notas

- El reporte OODA es ideal para enviar a Notion o Telegram como resumen semanal.
- La auto-evaluación analiza tareas almacenadas en Redis (`umbral:task:*`).
- Langfuse es opcional: si las keys no están configuradas, el reporte incluye métricas de Redis solamente.
- Ambas tasks se ejecutan de forma síncrona — no requieren conexión a APIs externas de LLM.
- Referencia: `worker/tasks/observability.py`, `scripts/ooda_report.py`, `scripts/evals_self_check.py`.
