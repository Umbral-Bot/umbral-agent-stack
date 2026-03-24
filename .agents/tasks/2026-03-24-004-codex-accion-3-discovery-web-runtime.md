---
id: "2026-03-24-004"
title: "Accion 3: resolver discovery web y degradacion Tavily en runtime"
status: done
assigned_to: codex
created_by: codex
priority: high
sprint: R23
created_at: 2026-03-24T01:20:26-03:00
updated_at: 2026-03-24T01:44:12-03:00
---

## Objetivo
Sacar a `research.web` y a los jobs de discovery del estado "scheduler sano pero contenido degradado", usando un backend real y operativo cuando Tavily quede sin cuota.

## Contexto
- `worker/tasks/research.py` ya no es Tavily-only: comparte backend con fallback Gemini grounded.
- `scripts/web_discovery.py` ya no depende solo de Tavily: usa el mismo fallback operativo real y deja Google CSE legado solo como tercer path opt-in.
- En la VPS, `TAVILY_API_KEY` esta presente pero Tavily responde `432 usage limit`.
- En la VPS, `GOOGLE_API_KEY` esta presente y ya hay evidencia viva de `google_search` via Gemini 2.5 Flash.
- `GOOGLE_CSE_*` sigue siendo legado/experimental y devuelve 403 en proyectos nuevos.

## Criterios de aceptacion
- [x] `research.web` deja de fallar por cuota Tavily cuando `GOOGLE_API_KEY` este disponible.
- [x] `scripts/web_discovery.py` usa el mismo fallback operativo real.
- [x] Se prueban en VPS `research_web_smoke.py` y `web_discovery.py`.
- [x] Queda documentado el orden de providers y el impacto en los cron jobs de discovery.
- [x] Tarea y board quedan actualizados con evidencia honesta.

## Log
### [codex] 2026-03-24 01:20
Tarea creada. Se confirmo en vivo que Tavily sigue en quota exceeded, que Google Custom Search sigue como path legado no operativo, y que Gemini 2.5 Flash con `tools=[google_search]` ya responde desde la VPS. Siguiente paso: capitalizar ese path como fallback real compartido entre Worker y scripts de discovery.

### [codex] 2026-03-24 01:44
Implementacion mergeada en `main` via PR #155 (`2e10647`). Se agrego `worker/research_backends.py` y se alinearon `worker/tasks/research.py`, `scripts/web_discovery.py` y `scripts/diagnose_google_cloud_apis.py` para usar Tavily como primario, Gemini grounded search como fallback real y Google CSE legado solo como tercer path opt-in.

Validacion local:
- `python -m pytest tests/test_research_handler.py tests/test_web_discovery.py -q`
- `python -m pytest tests/test_worker.py tests/test_e2e_validation.py -q`
- `WORKER_TOKEN=test python -m pytest tests -q` -> `1219 passed, 4 skipped`

Validacion viva en VPS despues de `git pull origin main` y `bash scripts/vps/restart-worker.sh`:
- `python3 scripts/research_web_smoke.py --query "BIM trends 2026"` -> `HTTP 200`, `engine=gemini_google_search`, `count=3`
- `python3 scripts/web_discovery.py "BIM trends 2026" --count 3` -> `engine_used=gemini_google_search`, `fallback_reason=research_provider_quota_exceeded:quota`
- `python3 scripts/diagnose_google_cloud_apis.py` -> Tavily `432`, Gemini grounded `OK (200)`, Google CSE legado `403`
- `python3 scripts/sim_daily_research.py` + polling de `/task/{id}/status` -> las 6 tareas `research.web` y el resumen `llm.generate` quedaron `done`
- `python3 scripts/sim_daily_report.py --hours 1` -> vuelve a producir reporte con URLs recientes del path grounded

Resultado honesto:
- Tavily sigue sin cuota y no se "arreglo" como proveedor.
- El runtime de discovery si quedo saneado: `research.web` y `web_discovery.py` ya no quedan degradados cuando Tavily responde `432`.
