# Task R13 — Dashboard de métricas de gobernanza

**Fecha:** 2026-03-04  
**Ronda:** 13  
**Agente:** Antigravity / Code Claude / Cursor Agent Cloud  
**Branch:** `feat/governance-metrics-dashboard`

---

## Contexto

Para medir estrategias, el responsable de mantenimiento necesita **métricas agregadas**: tasks por día, tasa de éxito por team/task_type, uso de modelos, duración media. El OODA report (`scripts/ooda_report.py`) y `quota_usage_report` dan resúmenes pero no un panel estructurado para gobernanza.

**Objetivo:** Crear un script o endpoint que genere un reporte de métricas de gobernanza, consumible por Notion o como JSON/Markdown, para evaluar "qué se hizo y cómo" y medir estrategias.

---

## Fuentes de datos

- `~/.config/umbral/ops_log.jsonl` — eventos OpsLogger (task_completed, task_failed, model_selected, etc.)
- Redis: `umbral:task:*`, queue stats, task history
- `config/quota_policy.yaml` — providers y cuotas
- Langfuse (opcional) — si LANGFUSE_* configurado

---

## Tareas requeridas

### 1. `scripts/governance_metrics_report.py`

Script que genera reporte de métricas de gobernanza.

**Argumentos:**
```
python scripts/governance_metrics_report.py [--days 7] [--format json|markdown|notion] [--output FILE]
```

**Métricas a incluir:**

| Métrica | Descripción | Fuente |
|---------|-------------|--------|
| tasks_total | Total de tareas en el período | ops_log |
| tasks_completed | Tareas exitosas | ops_log task_completed |
| tasks_failed | Tareas fallidas | ops_log task_failed |
| tasks_blocked | Tareas bloqueadas | ops_log task_blocked |
| success_rate | tasks_completed / (completed + failed) | calculado |
| tasks_by_day | Conteo por día | ops_log |
| tasks_by_team | Conteo por team | ops_log |
| tasks_by_task_type | Conteo por task (llm.generate, research.web, etc.) | ops_log |
| model_usage | Uso por modelo (gemini_pro, claude_pro, etc.) | ops_log model_selected |
| avg_duration_ms | Duración media por task | ops_log duration_ms |
| worker_distribution | vps vs vm | ops_log worker |
| quota_usage | Uso vs límite por provider | quota_policy + Redis |

**Output Markdown ejemplo:**
```markdown
# Métricas de gobernanza — Últimos 7 días

## Resumen
- Tasks totales: 142
- Completadas: 128 (90.1%)
- Fallidas: 12
- Bloqueadas: 2

## Por team
| Team | Completadas | Fallidas | Success rate |
|------|-------------|----------|--------------|
| general | 45 | 3 | 93.8% |
| research | 38 | 2 | 95.0% |
...

## Por task type
| Task | Completadas | Fallidas |
|------|-------------|----------|
| llm.generate | 52 | 1 |
| research.web | 30 | 2 |
...
```

---

### 2. Integración con cron (opcional)

Si existe cron de dashboard, agregar invocación de `governance_metrics_report.py --format markdown` y publicar en Notion o enviar por webhook.

---

### 3. Tests

Crear `tests/test_governance_metrics.py` con al menos 6 tests:

- `test_report_with_empty_ops_log`
- `test_report_with_sample_events`
- `test_success_rate_calculation`
- `test_tasks_by_team_aggregation`
- `test_json_output_format`
- `test_markdown_output_format`

---

## Criterios de éxito

- [ ] `scripts/governance_metrics_report.py` — script funcional
- [ ] Soporta --days, --format json|markdown
- [ ] Métricas: tasks_total, success_rate, tasks_by_team, tasks_by_task, model_usage, avg_duration
- [ ] `tests/test_governance_metrics.py` — 6+ tests
- [ ] PR abierto a `main`
