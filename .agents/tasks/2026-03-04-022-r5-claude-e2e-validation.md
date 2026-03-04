---
id: "022"
title: "E2E Validation Suite — Prueba completa del sistema en producción"
assigned_to: claude-code
status: assigned
branch: feat/claude-e2e-validation
priority: critical
round: 5
---

# E2E Validation Suite

## Problema
Hemos mergeado 22 PRs en 4 rondas sin validar que todo funcione end-to-end en producción.
El smart reply, composite research, webhook callback, daily digest — todo está desplegado
pero nadie ha verificado que funcionen juntos correctamente.

## Tu tarea

### A. Script scripts/e2e_validation.py
Crear un script de validación completa que se conecte al Worker VPS real y ejecute:

```python
def run_e2e_suite():
    """Ejecuta tests end-to-end contra el sistema en producción."""

    # 1. Health check — Worker VPS responde
    # 2. Health check — Worker VM responde (si está disponible)
    # 3. Ping — task más básica funciona
    # 4. research.web — Tavily busca y retorna resultados
    # 5. llm.generate — Gemini genera texto
    # 6. composite.research_report — pipeline completo
    # 7. POST /enqueue — encolar tarea y verificar con GET /task/{id}/status
    # 8. GET /task/history — endpoint de historial funciona
    # 9. notion.add_comment — puede postear en Notion
    # 10. Dispatcher health — Redis + queue stats

    # Para cada test:
    #   - Ejecutar con timeout
    #   - Capturar resultado o error
    #   - Medir tiempo de respuesta
    #   - Imprimir resultado formateado

    # Al final: resumen con pass/fail por test
```

### B. Formato de salida
```
=== Umbral E2E Validation ===
Date: 2026-03-04 08:45 UTC

[PASS] 1. Worker VPS health     (45ms)  v0.4.0, 27 handlers
[PASS] 2. Worker VM health      (120ms) v0.4.0, 25 handlers
[PASS] 3. Ping                  (30ms)  echo OK
[PASS] 4. research.web          (2.1s)  5 resultados
[PASS] 5. llm.generate          (3.4s)  152 chars generados
[PASS] 6. composite.research    (8.2s)  reporte 2.3KB
[PASS] 7. POST /enqueue         (55ms)  task_id=abc123
[PASS] 8. GET /task/history     (80ms)  42 tareas en 24h
[PASS] 9. notion.add_comment    (1.2s)  comment_id=xyz
[PASS] 10. Redis queue stats    (15ms)  pending=0, blocked=0

=== Results: 10/10 PASS ===
Total time: 15.3s
```

### C. Cron wrapper opcional
Crear `scripts/vps/e2e-validation-cron.sh`:
- Ejecutar 1x/día a las 06:00 UTC (antes del SIM research)
- Si algún test falla, postear alerta en Notion

### D. Postear resultado en Notion
Si se pasa --notion, postear el resultado como comment en Control Room.
Si se pasa --quiet, solo imprimir el resumen (no detalles).

### E. Agregar al install-cron.sh
Agregar entry para e2e-validation-cron.sh

### F. Ejecutar la validación
Después de crear el script, EJECUTARLO en la VPS:
```bash
ssh rick@100.113.249.25
cd ~/umbral-agent-stack && source .venv/bin/activate
set -a && source ~/.config/openclaw/env && set +a
PYTHONPATH=. python3 scripts/e2e_validation.py --notion
```

Reportar los resultados reales.

## Archivos relevantes
- `client/worker_client.py` — WorkerClient (para llamar al Worker)
- `worker/app.py` — endpoints a testear
- `dispatcher/queue.py` — TaskQueue, queue_stats
- `scripts/post_notion_message.py` — referencia para postear en Notion
