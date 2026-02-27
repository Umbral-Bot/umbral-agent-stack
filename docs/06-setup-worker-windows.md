# 06 — Setup Worker Windows

## Requisitos

- Windows 10/11 (host o Hyper-V VM)
- Python 3.11+
- pip actualizado
- Tailscale instalado y conectado

## Instalación

### 1. Crear directorio de trabajo

```powershell
mkdir C:\openclaw-worker
cd C:\openclaw-worker
```

### 2. Copiar archivos del worker

Copiar `worker/app.py` y `worker/requirements.txt` del repo a `C:\openclaw-worker\`.

### 3. Instalar dependencias

```powershell
pip install -r requirements.txt
```

Si pip está desactualizado:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Modo Desarrollo

### Configurar token

```powershell
$env:WORKER_TOKEN="CHANGE_ME_WORKER_TOKEN"
```

### Iniciar servidor

```powershell
python -m uvicorn app:app --host 0.0.0.0 --port 8088 --log-level info
```

> ⚠️ Debe escuchar en `0.0.0.0` (no `127.0.0.1`) para que Tailscale pueda acceder.

## Firewall

Crear regla para permitir conexiones entrantes al puerto 8088:

```powershell
New-NetFirewallRule -DisplayName "OpenClaw Worker 8088" `
  -Direction Inbound `
  -LocalPort 8088 `
  -Protocol TCP `
  -Action Allow
```

O ejecutar el script incluido:

```powershell
.\scripts\firewall-rule-8088.ps1
```

## Prueba

### Health check (sin auth)

```powershell
curl http://localhost:8088/health
```

### Ejecutar tarea (con auth)

```powershell
curl -X POST http://localhost:8088/run `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer CHANGE_ME_WORKER_TOKEN" `
  -d '{"task":"ping","input":{}}'
```

### Desde el VPS (via Tailscale)

```bash
# Health
curl http://WINDOWS_TAILSCALE_IP:8088/health

# Run (usar comillas simples por si el token tiene "!")
curl -s -X POST http://WINDOWS_TAILSCALE_IP:8088/run \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer CHANGE_ME_WORKER_TOKEN' \
  -d '{"task":"ping","input":{}}'
```

## Servicio NSSM (producción)

NSSM (Non-Sucking Service Manager) permite correr el worker como servicio de Windows.

### Instalar servicio

```powershell
.\scripts\setup-openclaw-service.ps1
```

### Comandos NSSM

```powershell
# Estado
nssm status openclaw-worker

# Iniciar
nssm start openclaw-worker

# Detener
nssm stop openclaw-worker

# Reiniciar
nssm restart openclaw-worker

# Remover servicio
nssm remove openclaw-worker confirm
```

### Verificar que está escuchando

```powershell
netstat -ano | findstr :8088
```

### Ver logs del servicio

Los logs se guardan en:
- `C:\openclaw-worker\service-stdout.log`
- `C:\openclaw-worker\service-stderr.log`

```powershell
Get-Content C:\openclaw-worker\service-stdout.log -Tail 50
Get-Content C:\openclaw-worker\service-stderr.log -Tail 50
```

### Remover servicio

```powershell
.\scripts\remove-openclaw-service.ps1
```
