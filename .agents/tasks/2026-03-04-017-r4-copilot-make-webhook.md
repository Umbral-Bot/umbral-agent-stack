---
id: "017"
title: "Make.com Webhook Integration — SIM Pipeline"
assigned_to: github-copilot
status: assigned
branch: feat/copilot-make-webhook
priority: high
round: 4
---

# Make.com Webhook Integration — SIM Pipeline

## Contexto
Ahora tenemos POST /enqueue con callback_url. El sistema puede recibir tareas de externos
y responder de vuelta. David tiene Make.com con créditos disponibles.
Necesitamos conectar Make.com al sistema para potenciar el análisis de mercado SIM.

## Tu tarea

### A. Script worker/tasks/make_webhook.py — Enviar resultados a Make.com
Nuevo task handler `make.post_webhook`:

```python
def handle_make_post_webhook(input_data):
    """
    Envía datos a un webhook de Make.com.

    Input:
        webhook_url: str — URL del webhook de Make.com
        payload: dict — datos a enviar
        timeout: int = 30

    Output:
        ok: bool
        status_code: int
        response: str
    """
```

Registrar en `worker/tasks/__init__.py`.

### B. Script scripts/sim_to_make.py — Pipeline SIM → Make.com
Crear script que:
1. Encola un `composite.research_report` con topic="mercado inmobiliario BIM"
2. Espera resultado (polling GET /task/{id}/status, timeout 120s)
3. Si hay resultado, envía via `make.post_webhook` al webhook de Make.com configurado
4. Lee MAKE_WEBHOOK_SIM_URL del entorno

### C. Cron wrapper
Crear `scripts/vps/sim-to-make-cron.sh`:
- Ejecutar después del SIM report (a las 9:00, 15:00, 21:00 UTC)
- Agregar a install-cron.sh

### D. Documentar en openclaw/env.template
Agregar variable: `MAKE_WEBHOOK_SIM_URL=https://hook.make.com/...`

### E. Tests
Crear `tests/test_make_webhook.py`:
- Test: handle_make_post_webhook hace POST correcto
- Test: timeout maneja error graciosamente
- Test: payload se serializa como JSON
- Test: retorna status_code correcto

## Archivos relevantes
- `worker/tasks/__init__.py` — registrar handler
- `worker/app.py` — POST /enqueue + GET /task/{id}/status (para polling)
- `scripts/sim_daily_research.py` — referencia de script similar
- `openclaw/env.template` — agregar MAKE_WEBHOOK_SIM_URL
