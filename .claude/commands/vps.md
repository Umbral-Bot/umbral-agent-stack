# VPS Operations — Umbral Agent Stack

Runbook operacional para el VPS del Umbral Agent Stack.
VPS: Hostinger Ubuntu 24 LTS, accesible vía Tailscale o SSH directo.

## Variables de entorno requeridas
- `VPS_HOST`: hostname o IP del VPS (ej. `srv1431451.hostingersite.com`)
- `VPS_USER`: usuario SSH (generalmente `rick` o `root`)
- SSH key configurada para acceso sin contraseña

## Comandos rápidos

### Health check completo
```bash
ssh $VPS_USER@$VPS_HOST "bash ~/umbral-agent-stack/scripts/vps/health-check.sh"
```

### Estado del stack completo
```bash
ssh $VPS_USER@$VPS_HOST "systemctl status openclaw dispatcher redis 2>/dev/null; docker ps 2>/dev/null"
```

### Levantar stack
```bash
ssh $VPS_USER@$VPS_HOST "bash ~/umbral-agent-stack/scripts/vps/full-stack-up.sh"
```

### Verificar OpenClaw
```bash
ssh $VPS_USER@$VPS_HOST "bash ~/umbral-agent-stack/scripts/vps/verify-openclaw.sh"
```

### Reiniciar Worker remoto (desde VPS → VM)
```bash
ssh $VPS_USER@$VPS_HOST "bash ~/umbral-agent-stack/scripts/vps/restart-worker.sh"
```

### Ver logs del Dispatcher
```bash
ssh $VPS_USER@$VPS_HOST "journalctl -u dispatcher -n 100 --no-pager"
```

### Ver logs de OpenClaw
```bash
ssh $VPS_USER@$VPS_HOST "journalctl -u openclaw -n 100 --no-pager"
```

### Crons activos
```bash
ssh $VPS_USER@$VPS_HOST "crontab -l"
```

### Redis status
```bash
ssh $VPS_USER@$VPS_HOST "redis-cli ping && redis-cli info server | grep -E 'version|uptime'"
```

### Dispatcher queue depth
```bash
ssh $VPS_USER@$VPS_HOST "redis-cli XLEN task_stream 2>/dev/null || redis-cli LLEN task_queue"
```

## Troubleshooting

### Worker VM no responde
1. Verificar Tailscale: `ssh $VPS_USER@$VPS_HOST "tailscale status"`
2. Verificar tunnel inverso: estado en scripts/vps/health-check.sh
3. En VM Windows: revisar NSSM service `nssm status umbral-worker`
4. Restart VM worker: `scripts/vm/fix_worker_service.ps1`

### Dispatcher no procesa tareas
1. `redis-cli ping` — verificar que Redis esté up
2. `journalctl -u dispatcher -n 50` — ver últimos errores
3. Revisar `config/teams.yaml` y `config/quota_policy.yaml`
4. Verificar variables de entorno: `cat .env | grep -v "^#" | grep -v "^$"`

### OpenClaw no recibe mensajes Telegram
1. `journalctl -u openclaw -n 50` — ver estado
2. Verificar token: `grep OPENCLAW_GATEWAY_TOKEN .env`
3. Reiniciar: `systemctl restart openclaw`

### Crons no ejecutan
1. `crontab -l` — verificar que estén instalados
2. `journalctl -t CRON -n 30` — ver logs de cron
3. Re-instalar: `bash scripts/vps/install-cron.sh`

## Sync y deploy

### Actualizar código en VPS
```bash
ssh $VPS_USER@$VPS_HOST "cd ~/umbral-agent-stack && git pull origin main && systemctl restart dispatcher"
```

### Script de sync completo
```bash
bash scripts/sync-and-setup-vps.sh
```

## Archivos de referencia
- `docs/08-operations-runbook.md` — Runbook completo
- `docs/62-operational-runbook.md` — Runbook operacional v2
- `docs/09-troubleshooting.md` — Troubleshooting guide
- `runbooks/` — Procedimientos específicos
