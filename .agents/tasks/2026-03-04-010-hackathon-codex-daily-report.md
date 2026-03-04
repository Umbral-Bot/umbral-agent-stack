# Hackathon: Reporte diario automático + tests nuevos handlers

**Assigned:** codex  
**Priority:** P1  
**Status:** assigned  
**Created:** 2026-03-04

## Contexto

Las tareas anteriores de Codex (002 infra VPS y 005 OpsLogger) ya fueron completadas por Cursor durante el hackathon. Se necesita que Codex aporte con trabajo nuevo.

El sistema ahora tiene 2 nuevos task handlers (`research.web` y `llm.generate`) y un cron SIM que corre 3x/día. Falta:
1. Tests unitarios para los nuevos handlers.
2. Un script que genere un reporte diario resumiendo los resultados del SIM.

## Tareas

### A. Tests para nuevos handlers (prioridad alta)
1. Crear `tests/test_research_handler.py`:
   - Test que `handle_research_web` valide input (query requerido).
   - Test que falle graciosamente si `TAVILY_API_KEY` no está configurada.
   - Test con mock de `urllib.request.urlopen` que simule respuesta exitosa de Tavily.

2. Crear `tests/test_llm_handler.py`:
   - Test que `handle_llm_generate` valide input (prompt requerido).
   - Test que falle graciosamente si `GOOGLE_API_KEY` no está configurada.
   - Test con mock de `urllib.request.urlopen` que simule respuesta exitosa de Gemini.

### B. Script de reporte diario SIM
1. Crear `scripts/sim_daily_report.py`:
   - Leer los últimos eventos de `~/.config/umbral/ops_log.jsonl` (via `OpsLogger.read_events()`).
   - Filtrar solo tareas `research.web` y `llm.generate` de las últimas 24h.
   - Generar un resumen: cuántas búsquedas, cuántas exitosas, temas cubiertos, resumen LLM.
   - Postear el resumen como comentario en la Control Room de Notion (via `notion.add_comment`).

2. Agregar al cron (opcional): `30 21 * * * bash ~/umbral-agent-stack/scripts/vps/sim-report-cron.sh`

## Archivos relevantes

- `worker/tasks/research.py` — handler de research.web
- `worker/tasks/llm.py` — handler de llm.generate
- `infra/ops_logger.py` — OpsLogger (read_events)
- `scripts/sim_daily_research.py` — cron SIM (referencia)
- `tests/` — directorio de tests existentes

## Entrega

Responder en `.agents/board.md` con estado de la tarea y commit con los cambios.
