---
id: "2026-03-24-013"
title: "Follow-up OpenClaw post-Rick: aterrar residuales reales y endurecer composite.research_report"
status: done
assigned_to: codex
created_by: codex
priority: medium
sprint: R23
created_at: 2026-03-24T10:07:38-03:00
updated_at: 2026-03-24T10:23:00-03:00
---

## Objetivo
Tomar la respuesta operativa de Rick, contrastarla contra evidencia real del runtime OpenClaw/VPS y cerrar el siguiente hueco repo-side util sin esperar otra ronda humana:

1. distinguir residuales aceptados vs degradacion real;
2. dejar documentado el diagnostico ajustado;
3. endurecer `composite.research_report` frente a `Gemini 503 UNAVAILABLE` transitorio en la generacion final del reporte.

## Contexto
- Rick reporto: base stack sano, `trustedProxies` vacio, `node service` no instalado, `Tailscale off` y discovery usable pero supuestamente degradado.
- El snapshot repo-side y las comprobaciones VPS ya muestran que:
  - Gemini grounded search es el provider primario actual de `research.web`;
  - Tavily no entro como fallback en la ventana reciente trazada;
  - el residual real mas cercano al runtime sigue siendo la VM / execution plane, no discovery web.
- `worker/tasks/composite.py` hoy hace una sola llamada de generacion final via `llm.generate`; si Gemini devuelve `503`, cae directo al fallback de raw research data.

## Criterios de aceptacion
- [x] Existe una tarea/documentacion que contraste la respuesta de Rick con evidencia real del snapshot y del runtime.
- [x] `composite.research_report` reintenta de forma acotada ante errores transitorios retryable (`503`, `UNAVAILABLE`, timeout equivalente) antes de caer al fallback crudo.
- [x] Hay tests dirigidos para exito tras retry y agotamiento de retries.
- [x] Queda documentado que `trustedProxies` y `Tailscale off` en la VPS no son fallas criticas mientras la UI siga local-only, y que `node service` en la VM sigue siendo decision/intervencion manual.

## Log
### [codex] 2026-03-24 10:07
Tarea creada para capitalizar la respuesta de Rick con evidencia real del runtime y cerrar el siguiente frente repo-side util: retry/backoff acotado en `composite.research_report` frente a `Gemini 503`.

### [codex] 2026-03-24 10:23
Contraste la respuesta de Rick contra evidencia viva de la VPS:

- `openclaw status --all` confirmo que `Tailscale off` y `trustedProxies` vacio son residuales aceptados mientras el gateway siga local-only por loopback;
- `openclaw_runtime_snapshot.py --days 7` mostro `research_usage.by_provider = gemini_google_search: 3`, `fallback_calls = 0`, asi que discovery web no esta hoy degradado en la ventana trazada;
- el residual operativo mas visible sigue siendo la execution plane Windows (`windows.fs.list` bloqueado 16 veces) y la persistencia manual del nodo/servicio de la VM.

Implementacion repo-side:

- agregue retry/backoff acotado en `worker/tasks/composite.py` para la llamada final de `composite.research_report`;
- agregue tests de exito tras retry y agotamiento de retries en `tests/test_composite_handler.py`;
- estabilice `tests/test_linear.py` para que el dedupe de follow-up no dependa de una fecha fija ya vencida;
- documente la lectura ajustada en `docs/audits/openclaw-rick-response-followup-2026-03-24.md`.

Validacion:

- `WORKER_TOKEN=test python -m pytest tests/test_composite_handler.py tests/test_worker.py -q` -> `43 passed`
- `WORKER_TOKEN=test python -m pytest tests -q` -> `1234 passed, 4 skipped`
