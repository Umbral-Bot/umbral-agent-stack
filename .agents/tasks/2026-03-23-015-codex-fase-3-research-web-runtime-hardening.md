---
id: "2026-03-23-015"
title: "Fase 3: hardening runtime real de research.web"
status: done
assigned_to: codex
created_by: codex
priority: high
sprint: R23
created_at: 2026-03-23T17:56:57-03:00
updated_at: 2026-03-23T18:06:00-03:00
---

## Objetivo
Endurecer `research.web` para que falle con clasificación útil en runtime real, no con `500` genérico, y dejar una validación operativa reproducible contra la VPS.

## Contexto
- El super diagnóstico de interconectividad dejó `research.web` como slice pendiente de Fase 3.
- En la VPS, el fallo real ya no era "falta env", sino un error de cuota/plan en Tavily.
- El handler actual envuelve todo como `RuntimeError`, y el Worker lo traduce a `500 Task failed: ...`.

## Criterios de aceptación
- [x] `research.web` clasifica al menos configuración, auth, cuota, timeout/red y upstream HTTP.
- [x] El Worker responde con status útil y cuerpo estructurado para errores tipados de tareas.
- [x] Existe un smoke directo y corto para `research.web`.
- [x] Hay tests suficientes para los casos nuevos.
- [x] La VPS queda validada con evidencia real.

## Log
### [codex] 2026-03-23 17:56
Inicio de Fase 3. Reproducción real previa en VPS: `research.web` respondió `500` con detalle de Tavily `432` por límite de plan. Se implementa hardening para clasificar y exponer ese fallo como error operativo útil.

### [codex] 2026-03-23 18:06
Cierre de Fase 3. Se introdujo `worker/task_errors.py` para tipar fallos operativos de tareas; `worker/tasks/research.py` ahora clasifica `research.web` en configuración, auth, cuota, timeout/red, respuesta inválida y fallos upstream HTTP. `worker/app.py` devuelve status y cuerpo estructurado para `TaskExecutionError`.

Validación local:
- `WORKER_TOKEN=test python -m pytest tests/test_research_handler.py tests/test_worker.py -q` -> `37 passed`
- `WORKER_TOKEN=test python -m pytest tests -q` -> `1211 passed, 4 skipped, 1 warning`
- `git diff --check` -> sin errores de diff (solo warnings CRLF del checkout Windows)

Validación VPS:
- deploy de la rama `codex/fase-3-research-web-hardening` en `~/umbral-agent-stack`
- `bash scripts/vps/restart-worker.sh` -> worker reiniciado correctamente
- `PYTHONPATH=. python3 scripts/research_web_smoke.py --query "BIM trends 2026"` -> `HTTP 503`
- cuerpo real del smoke:
  - `detail`: `research.web unavailable: Tavily plan/quota exceeded`
  - `error_code`: `research_provider_quota_exceeded`
  - `error_kind`: `quota`
  - `provider`: `tavily`
  - `retryable`: `false`
  - `upstream_status`: `432`

Resultado: el runtime real ya no devuelve `500` genérico cuando Tavily agota cuota; expone un fallo operativo clasificable y accionable.
