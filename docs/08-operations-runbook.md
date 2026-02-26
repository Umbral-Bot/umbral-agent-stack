# 08 — Operations Runbook

## Estado General de OpenClaw

```bash
# Estado del servicio
systemctl --user status openclaw

# Estado completo de OpenClaw
openclaw status --all

# Estado de modelos/providers
openclaw models status

# Doctor (Windows)
openclaw doctor
```

## Reinicios Controlados

### VPS — OpenClaw

```bash
systemctl --user restart openclaw
```

### Windows — Worker

```powershell
nssm restart openclaw-worker
```

### Verificar después de reinicio

```bash
# VPS
systemctl --user status openclaw
curl http://WINDOWS_TAILSCALE_IP:8088/health

# Windows
nssm status openclaw-worker
netstat -ano | findstr :8088
```

## Checklist Diario

| Componente | Comando | Esperado |
|-----------|---------|----------|
| OpenClaw service | `systemctl --user status openclaw` | `active (running)` |
| Telegram | `openclaw status --all \| grep telegram` | OK/connected |
| Tailscale VPS | `tailscale status` | conectado |
| Worker health | `curl http://WINDOWS_TS_IP:8088/health` | `{"ok":true}` |
| Worker service | `nssm status openclaw-worker` (Windows) | `SERVICE_RUNNING` |

## Flujo de Verificación Rápida

```bash
# 1. OpenClaw OK?
systemctl --user is-active openclaw && echo "✅ OpenClaw OK" || echo "❌ OpenClaw DOWN"

# 2. Worker OK?
curl -sf http://WINDOWS_TAILSCALE_IP:8088/health > /dev/null && echo "✅ Worker OK" || echo "❌ Worker DOWN"

# 3. Tailscale OK?
tailscale status > /dev/null 2>&1 && echo "✅ Tailscale OK" || echo "❌ Tailscale DOWN"
```

## Logs

### VPS — OpenClaw

```bash
# Últimas 100 líneas
journalctl --user -u openclaw -n 100 --no-pager

# En vivo
journalctl --user -u openclaw -f

# Filtrar errores
journalctl --user -u openclaw --no-pager | grep -i error
```

### Windows — Worker

```powershell
# stdout
Get-Content C:\openclaw-worker\service-stdout.log -Tail 50

# stderr
Get-Content C:\openclaw-worker\service-stderr.log -Tail 50

# En vivo
Get-Content C:\openclaw-worker\service-stdout.log -Wait
```
