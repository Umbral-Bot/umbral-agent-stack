# Runbook: Tailscale

## Verificar estado

### VPS

```bash
tailscale status
tailscale ip -4
```

### Windows

```powershell
tailscale status
tailscale ip -4
```

## Probar conectividad

### VPS → Windows

```bash
ping WINDOWS_TAILSCALE_IP
curl http://WINDOWS_TAILSCALE_IP:8088/health
```

### Windows → VPS

```powershell
ping VPS_TAILSCALE_IP
```

## Reiniciar Tailscale

### VPS

```bash
sudo systemctl restart tailscaled
tailscale status
```

### Windows

Reiniciar el servicio Tailscale desde Services (`services.msc`) o:

```powershell
Restart-Service Tailscale
```

## Re-autenticar

```bash
sudo tailscale up
```

Seguir el link de autenticación que muestra.

## Problemas comunes

- **"not connected"**: Re-autenticar con `tailscale up`.
- **IP cambió**: Verificar con `tailscale ip -4` y actualizar `WORKER_URL` si cambió.
- **Firewall**: Asegurarse de que el puerto 8088 está abierto en Windows.
