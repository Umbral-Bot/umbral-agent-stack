# 25 — S6 Evals y Ciclo OODA

## Evals automáticos

- **Core Eval Harness v0**: `scripts/eval_harness.py` corre suites deterministicas offline:
  `editorial_gold_set`, `stage5_ranking`, `agent_output_gold_set`.
- **Self-Evaluation agent**: `scripts/evals_self_check.py` evalua tareas completadas en Redis con heuristicas basicas.
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

### Core Eval Harness v0

```bash
python scripts/eval_harness.py --format markdown
python scripts/eval_harness.py --write
```

Contrato v0:
- `read_only: true`
- `network: none`
- `llm_calls: 0`
- salida non-zero si alguna suite falla
- reportes generados en `reports/evals/generated/`

Mission Control expone el ultimo JSON generado en `GET /evals`; no ejecuta el
harness desde el dashboard.
