# Instrucciones para GitHub Copilot

**Repo:** `C:\GitHub\umbral-agent-stack-copilot`  
**Rama:** `feat/copilot-quota-report`  
**Tarea:** Quota usage report + deploy en VPS

## Contexto
Este es TU clon del repo. Trabaja solo aquí. No toques otros clones.
Tu tarea anterior (004) ya está completada. Esta es nueva.

## Tu tarea nueva

### A. Finalizar quota_usage_report.py
Si ya tienes `scripts/quota_usage_report.py` de tu tarea anterior, tráelo aquí y verifica que:
- Lea Redis para cuotas (`QuotaTracker`)
- Lea OpsLogger para tareas procesadas
- Genere un reporte en texto y JSON
- Pueda postear el resultado en Notion via `notion.add_comment`

### B. Health check completo para VPS
Crear `scripts/vps/health-check.sh` que:
1. Verifique que Redis está corriendo (`redis-cli ping`)
2. Verifique que el Worker responde (`curl http://127.0.0.1:8088/health`)
3. Verifique que el Dispatcher está corriendo (`pgrep -f dispatcher.service`)
4. Verifique que hay eventos recientes en ops_log (`wc -l ~/.config/umbral/ops_log.jsonl`)
5. Si algo falla, postear alerta en Notion Control Room
6. Salida con exit code 0 si todo OK, 1 si algo falla

### C. Instalar health check como cron
- Agregar instrucciones para crontab: `*/30 * * * * bash ~/umbral-agent-stack/scripts/vps/health-check.sh`

## Conectividad VPS
- SSH: `ssh rick@100.113.249.25` (via Tailscale)
- Env vars: `source ~/.config/openclaw/env`

## Flujo de trabajo
```bash
git checkout feat/copilot-quota-report
git add .
git commit -m "feat: quota report + VPS health check cron"
git push -u origin feat/copilot-quota-report
gh pr create --base main --title "[Copilot] Quota report + health check" --body "Health monitoring + quota tracking"
```

## Protocolo
- NO edites `.agents/board.md` (lo hace Cursor)
- Cuando termines, avísale a David para que Cursor revise y mergee
