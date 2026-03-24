---
id: "2026-03-24-011"
title: "Gemini canonico, Tavily backup y tracking de necesidad futura"
status: done
assigned_to: codex
created_by: codex
priority: medium
sprint: R24
created_at: 2026-03-24T10:05:00-03:00
updated_at: 2026-03-24T08:58:00-03:00
---

## Objetivo
Formalizar la decision operativa de discovery:

1. Gemini grounded search queda como backend canonico
2. Tavily queda como backup secundario y barato
3. Perplexity queda diferido solo si los casos reales muestran necesidad
4. dejar tracking minimo para contar cuantas veces `research.web` tuvo que salir de Gemini y caer a Tavily

## Contexto
- `2026-03-24-010` ya dejo Gemini primario en runtime y documentado el sizing para Perplexity
- falta aterrizar la decision final de negocio/operacion y dejar una señal cuantificable de necesidad futura

## Criterios de aceptacion
- [ ] Queda documentado que Gemini es el camino canonico y Tavily el backup secundario
- [ ] Perplexity queda explicitamente diferido como propuesta futura y no trabajo activo
- [ ] Se registra en el sistema cuantas veces `research.web` usa Tavily como fallback
- [ ] Hay tests para el tracking nuevo

## Log
### [codex] 2026-03-24 10:05
Tarea creada para capitalizar la decision operativa de provider routing y dejar tracking de fallback real.

### [codex] 2026-03-24 08:58
Decision formalizada:
- Gemini grounded search queda canonico
- Tavily queda como backup secundario y barato
- Perplexity queda diferido; solo se retoma si los casos reales muestran necesidad

Implementacion:
- `infra/ops_logger.py`: nuevo evento `research_usage`
- `worker/app.py`: `research.web` recibe contexto oculto (`_task_id`, `_task_type`, `_source`, `_source_kind`)
- `worker/tasks/research.py`: registra provider usado y `fallback_reason` cuando cae a Tavily
- `scripts/openclaw_runtime_snapshot.py`: resume el uso por provider/fallback para lectura repo-side
- docs alineados en `docs/audits/openclaw-deferreds-followup-2026-03-24.md` y `docs/36-rick-embudo-capabilities.md`

Validacion:
- `python -m pytest tests/test_ops_logger.py tests/test_openclaw_runtime_snapshot.py tests/test_research_handler.py tests/test_worker.py -q` -> `66 passed`
- VPS temporalmente en esta rama:
  - `PYTHONPATH=. python3 scripts/research_web_smoke.py --query "BIM automation trends 2026" --count 2`
  - `ops_log` confirmo un evento real:
    - `research_usage`
    - `provider=gemini_google_search`
    - `result_count=2`

Pendiente derivado:
- si en el tiempo empiezan a aparecer `research_usage` con `provider=tavily` y `fallback_reason` repetido, ese sera el gatillo objetivo para reevaluar Perplexity
