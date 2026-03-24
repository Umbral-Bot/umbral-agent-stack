---
id: "2026-03-24-004"
title: "Accion 3: resolver discovery web y degradacion Tavily en runtime"
status: in_progress
assigned_to: codex
created_by: codex
priority: high
sprint: R23
created_at: 2026-03-24T01:20:26-03:00
updated_at: 2026-03-24T01:20:26-03:00
---

## Objetivo
Sacar a `research.web` y a los jobs de discovery del estado "scheduler sano pero contenido degradado", usando un backend real y operativo cuando Tavily quede sin cuota.

## Contexto
- `worker/tasks/research.py` sigue siendo Tavily-only.
- `scripts/web_discovery.py` usa Tavily como primario y Google CSE legado solo como opt-in experimental.
- En la VPS, `TAVILY_API_KEY` esta presente pero Tavily responde `432 usage limit`.
- En la VPS, `GOOGLE_API_KEY` esta presente y ya hay evidencia viva de `google_search` via Gemini 2.5 Flash.
- `GOOGLE_CSE_*` sigue siendo legado/experimental y devuelve 403 en proyectos nuevos.

## Criterios de aceptacion
- [ ] `research.web` deja de fallar por cuota Tavily cuando `GOOGLE_API_KEY` este disponible.
- [ ] `scripts/web_discovery.py` usa el mismo fallback operativo real.
- [ ] Se prueban en VPS `research_web_smoke.py` y `web_discovery.py`.
- [ ] Queda documentado el orden de providers y el impacto en los cron jobs de discovery.
- [ ] Tarea y board quedan actualizados con evidencia honesta.

## Log
### [codex] 2026-03-24 01:20
Tarea creada. Se confirmo en vivo que Tavily sigue en quota exceeded, que Google Custom Search sigue como path legado no operativo, y que Gemini 2.5 Flash con `tools=[google_search]` ya responde desde la VPS. Siguiente paso: capitalizar ese path como fallback real compartido entre Worker y scripts de discovery.
