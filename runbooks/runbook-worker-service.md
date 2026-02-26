# Runbook: Worker Service (Windows)

## Verificar estado

```powershell
nssm status openclaw-worker
```

## Iniciar / Detener / Reiniciar

```powershell
nssm start openclaw-worker
nssm stop openclaw-worker
nssm restart openclaw-worker
```

## Verificar que escucha en el puerto

```powershell
netstat -ano | findstr :8088
```

## Health check local

```powershell
curl http://localhost:8088/health
```

## Ver logs

```powershell
# stdout
Get-Content C:\openclaw-worker\service-stdout.log -Tail 50

# stderr
Get-Content C:\openclaw-worker\service-stderr.log -Tail 50

# Follow (en vivo)
Get-Content C:\openclaw-worker\service-stdout.log -Wait
```

## Reinstalar servicio

```powershell
# Remover
.\scripts\remove-openclaw-service.ps1

# Instalar
.\scripts\setup-openclaw-service.ps1

# Verificar
nssm status openclaw-worker
```

## Modo desarrollo (sin NSSM)

```powershell
cd C:\openclaw-worker
$env:WORKER_TOKEN="CHANGE_ME_WORKER_TOKEN"
python -m uvicorn app:app --host 0.0.0.0 --port 8088 --log-level info
```
