---
id: "2026-03-24-009"
title: "Diferidos OpenClaw: tailscale, tracking repo-side, costo y propuesta Tavily"
status: done
assigned_to: codex
created_by: codex
priority: high
sprint: R24
created_at: 2026-03-24T20:05:00-03:00
updated_at: 2026-03-24T05:03:00-03:00
---

## Objetivo
Avanzar durante la noche todo lo posible en los diferidos post-acciones de OpenClaw sin esperar intervencion humana, dejando implementado lo que sea cerrable en repo/VPS y documentado con precision lo que siga dependiendo de un gate de David.

## Contexto
- Las Acciones 1, 2, 3, 4, 5, 6 y 8 ya quedaron cerradas.
- El test general post-acciones (`2026-03-24-008`) tambien quedo cerrado y mergeado a `main`.
- Quedaron como diferidos: snapshot repo-side del tracking de paneles/OpenClaw, atribucion fina de costo/tokens por componente, decision Tavily/proveedor y revalidacion Tailscale VPS -> VM tras reinicio del host.

## Criterios de aceptacion
- [x] Queda revalidado y documentado el estado real de reachability VPS -> VM por Tailscale.
- [x] Queda implementado el snapshot repo-side del tracking de paneles/OpenClaw o explicado con precision el bloqueo si apareciera uno real.
- [x] Queda evaluada la atribucion fina de costo/tokens por componente y, si es viable, implementada.
- [x] Queda una propuesta operativa clara para Tavily/proveedor con recomendacion y proximos pasos.
- [x] Quedan anotadas oportunidades adicionales de mejora detectadas durante esta pasada.

## Log
### [codex] 2026-03-24 20:05
Tarea creada. Se arranca por revalidacion Tailscale VPS -> VM y luego se capitaliza tracking repo-side y costo/tokens de OpenClaw sobre la base del `ops_log` y del wiring ya saneado.

### [codex] 2026-03-24 05:03
Se cerro el paquete diferido sin esperar intervencion humana. Resultado:

- revalidacion tailnet VPS -> VM: sigue degradada post reboot; `100.109.16.40` no responde a `ping` ni a `8088/8089` desde VPS ni desde host. Quedo documentado en `docs/audits/vm-tailnet-operational-recovery-2026-03-15.md`.
- snapshot repo-side implementado y versionado:
  - `scripts/openclaw_runtime_snapshot.py`
  - `reports/runtime/openclaw-runtime-snapshot-2026-03-24.md`
  - `reports/runtime/openclaw-runtime-snapshot-latest.json`
- atribucion fina de costo/tokens: ampliada con dos capas:
  - `ops_log` ya traza `llm_usage` para `llm.generate` y `composite.research_report.query_generation`
  - el snapshot ahora incorpora `~/.openclaw/agents/*/sessions/sessions.json` para resumir uso por agente y modelo
- propuesta Tavily/proveedor cerrada en `docs/audits/openclaw-deferreds-followup-2026-03-24.md`: Gemini grounded search queda como camino canonico; Tavily pasa a decision presupuestaria/estrategica, no incidente runtime.
- oportunidades adicionales registradas en el mismo follow-up: exporter del snapshot, trazado de grounded search cuando exponga usage, resumen compacto en Dashboard Rick, reharden del path VPS -> VM y retry/backoff para `Gemini 503 UNAVAILABLE`.

Validacion:

- `python -m pytest tests/test_openclaw_runtime_snapshot.py tests/test_ops_logger.py tests/test_llm_handler.py tests/test_composite_handler.py tests/test_worker.py -q` -> `108 passed`
- refresh real de paneles en VPS desde la rama
- llamadas reales a `/run` en VPS:
  - `llm.generate` -> `200`, `provider=gemini`, texto `OK-DEFERREDS-LLM`
  - `composite.research_report` -> `200`, research OK; report generation cayo en `Gemini 503 UNAVAILABLE` y devolvio fallback con research data
