# Hackathon: Conectar LLM al Worker

**Assigned:** github-copilot  
**Priority:** P1  
**Status:** assigned  
**Created:** 2026-03-04

## Contexto

El sistema tiene ModelRouter y QuotaTracker implementados, pero ningún LLM está conectado en producción. LiteLLM no está desplegado. El QuotaTracker en Redis tiene keys vacías (0 requests a cualquier modelo).

API keys disponibles en `.env` / `~/.config/openclaw/env`:
- `GOOGLE_API_KEY` (Gemini / Google AI Studio)
- `GOOGLE_API_KEY_NANO` (Gemini Nano)
- `TAVILY_API_KEY` (búsqueda web)

## Tareas

1. **Crear una task handler `llm.generate`** en el Worker que:
   - Reciba `{"prompt": "...", "model": "gemini"}` (o similar).
   - Llame a la API de Gemini (`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent`) con la API key desde env.
   - Devuelva la respuesta del modelo.
   - Registre en el QuotaTracker el uso (si es viable desde el Worker; si no, al menos loguear).

2. **Crear una task handler `research.web`** que:
   - Reciba `{"query": "...", "count": 5}`.
   - Use Tavily (o el script `web_discovery.py` existente) para buscar.
   - Devuelva resultados (URLs, snippets).

3. **Registrar ambas tasks** en `worker/tasks/__init__.py`.

4. **Test**:
   - Probar `llm.generate` con un prompt simple ("Resume en 2 frases qué es BIM").
   - Probar `research.web` con una query ("embudo ventas servicios").

## Archivos relevantes

- `worker/tasks/__init__.py` — Registro de tasks
- `worker/tasks/` — Directorio de task handlers
- `scripts/web_discovery.py` — Script existente de búsqueda web
- `config/quota_policy.yaml` — Política de cuotas

## Entrega

Responder en `.agents/board.md` con estado de la tarea y commit con los cambios.
