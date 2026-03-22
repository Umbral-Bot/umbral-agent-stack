---
id: "013"
title: "Daily Activity Digest + Notion Post"
assigned_to: github-copilot
status: done
updated_at: "2026-03-22T19:04:21-03:00"
branch: feat/copilot-daily-digest
priority: high
round: 3
---

# Daily Activity Digest

## Problema
David no tiene visibilidad de qué hizo Rick durante el día. No hay un resumen
consolidado de tareas ejecutadas, resultados de research, ni estado del sistema.

## Tu tarea

### A. Script scripts/daily_digest.py
Crear un script que:
1. Lee de Redis todas las tareas completadas en las últimas 24h (scan keys `umbral:task:*`)
2. Agrupa por equipo y tipo de tarea
3. Extrae métricas: total ejecutadas, exitosas, fallidas, tiempo promedio
4. Recopila resultados de research.web y llm.generate recientes
5. Genera un prompt para llm.generate pidiendo un resumen ejecutivo en español
6. Llama al Worker (POST /run con task llm.generate) para generar el resumen
7. Postea el resumen en Notion via notion.add_comment en la Control Room

### B. Formato del digest
```
Rick: Resumen diario — [fecha]

📊 Actividad:
- X tareas ejecutadas (Y exitosas, Z fallidas)
- Equipos activos: marketing, system
- Investigaciones: [temas investigados]

🔍 Highlights:
- [Resumen de hallazgos de research]
- [Estado del sistema]

📋 Pendientes:
- [Tareas bloqueadas o en cola]
```

### C. Cron wrapper
Crear `scripts/vps/daily-digest-cron.sh` y agregar a `install-cron.sh`:
- Ejecutar a las 22:00 UTC (hora de cierre del día en Chile)
- `0 22 * * * bash ~/umbral-agent-stack/scripts/vps/daily-digest-cron.sh`

### D. Tests
Crear `tests/test_daily_digest.py`:
- Mock Redis con tareas de ejemplo
- Test que genera resumen correcto
- Test que maneja Redis vacío (sin tareas)
- Test que maneja error de LLM (fallback sin resumen IA)

## Archivos relevantes
- `dispatcher/queue.py` — TaskQueue, TASK_KEY_PREFIX (para leer tareas)
- `worker/tasks/llm.py` — handle_llm_generate (referencia del formato)
- `scripts/sim_daily_report.py` — referencia de script similar
- `scripts/vps/install-cron.sh` — agregar entrada del cron
- `worker/config.py` — variables de entorno

## Log

### [codex] 2026-03-22 19:04 -03:00
Regularizacion administrativa por UMB-132. Esta tarea quedo como arrastre historico y ya no representa trabajo vivo; se cierra el archivo para alinearlo con el board y el estado real del repo.
