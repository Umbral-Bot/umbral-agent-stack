---
id: "015"
title: "Composite Task Handler (Research Report)"
assigned_to: antigravity
status: assigned
branch: feat/antigravity-composite-tasks
priority: high
round: 3
---

# Composite Task Handler — Research Report

## Problema
Actualmente las tareas son atómicas: research.web busca, llm.generate genera texto,
pero no hay forma de encadenarlas. Para producir un informe de mercado completo,
se necesitan múltiples pasos manuales. Necesitamos un task handler que orqueste
múltiples sub-tareas internamente.

## Tu tarea

### A. Nuevo handler composite.research_report
Crear `worker/tasks/composite.py`:

```python
def handle_composite_research_report(input_data):
    """
    Input:
        topic: str — tema a investigar
        queries: list[str] — (opcional) queries específicas, si no se proveen se generan
        depth: str — "quick" (3 queries) | "standard" (5) | "deep" (10)
        language: str — idioma del reporte (default "es")

    Proceso:
        1. Si no hay queries, usar llm.generate para generar N queries relevantes
        2. Ejecutar research.web para cada query
        3. Consolidar todos los resultados
        4. Usar llm.generate para producir un reporte estructurado:
           - Resumen ejecutivo
           - Hallazgos principales (con fuentes)
           - Tendencias identificadas
           - Recomendaciones
        5. Retornar el reporte completo

    Output:
        report: str — reporte completo en markdown
        sources: list[dict] — fuentes utilizadas
        queries_used: list[str]
        stats: {total_sources, research_time_ms, generation_time_ms}
    """
```

### B. Registrar en worker/tasks/__init__.py
Agregar `composite.research_report` → `handle_composite_research_report`

### C. Tests
Crear `tests/test_composite_handler.py`:
- Mock de research.web y llm.generate (llamar internamente)
- Test: topic genera queries + research + reporte
- Test: queries explícitas se usan directamente
- Test: depth controla cantidad de queries
- Test: error en un research no crashea (usa los demás)
- Test: error en llm retorna resultados raw sin reporte

### D. Documentar
Crear entrada en `docs/07-worker-api-contract.md` para el nuevo task type.

## Archivos relevantes
- `worker/tasks/research.py` — handle_research_web (importar y reusar)
- `worker/tasks/llm.py` — handle_llm_generate (importar y reusar)
- `worker/tasks/__init__.py` — registrar handler
- `worker/app.py` — ya soporta cualquier task registrado via POST /run
