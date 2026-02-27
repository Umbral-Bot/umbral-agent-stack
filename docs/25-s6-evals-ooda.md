# 25 — S6 Evals y Ciclo OODA

## Evals automáticos

- **Self-Evaluation agent**: agente que evalúa salidas de Rick (relevancia, calidad, completitud).
- **Integración con Langfuse**: scores y evals pueden enviarse a Langfuse para dashboards.
- **Próximo paso**: definir criterios de evaluación y script `scripts/evals_self_check.py` que invoque un modelo para calificar outputs.

## Reporte OODA

- **Script**: `scripts/ooda_report.py`
- **Frecuencia**: semanal (cron o scheduled task).
- **Contenido**: tareas completadas/fallidas, uso LLM, traces Langfuse.
- **Salida**: Markdown o JSON, para Notion o Telegram.

### Ejecución

```bash
python scripts/ooda_report.py --week-ago 0 --format markdown
```

Actualmente devuelve stubs; conectar Redis y Langfuse API para datos reales.
