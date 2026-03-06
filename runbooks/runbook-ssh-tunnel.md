# Runbook: SSH Tunnel para Control UI

## Objetivo

Acceder a la Control UI de OpenClaw (localhost:18789) desde tu PC sin exponer puertos a internet.

## Comando

```bash
ssh -N -L 18789:127.0.0.1:18789 -L 18791:127.0.0.1:18791 rick@VPS_PUBLIC_IP
```

## Parámetros

| Flag | Significado |
|------|-------------|
| `-N` | No ejecutar comando remoto (solo túnel) |
| `-L 18789:127.0.0.1:18789` | Mapea localhost:18789 local → 127.0.0.1:18789 en VPS |
| `-L 18791:127.0.0.1:18791` | Mapea localhost:18791 local → 127.0.0.1:18791 en VPS |

## Después del túnel

- **Control UI**: [http://localhost:18789](http://localhost:18789)
- **API**: [http://localhost:18791](http://localhost:18791)

## Desde PowerShell (Windows)

```powershell
ssh -N -L 18789:127.0.0.1:18789 -L 18791:127.0.0.1:18791 rick@VPS_PUBLIC_IP
```

> El túnel se mantiene activo mientras la ventana esté abierta. Para cerrar: `Ctrl+C`.

## Si el puerto 18789 está ocupado en tu PC

Usa otro puerto local (ej. 18790):

```powershell
ssh -N -L 18790:127.0.0.1:18789 -L 18792:127.0.0.1:18791 rick@VPS_PUBLIC_IP
```

- **Control UI:** http://127.0.0.1:18790/
- **WebSocket URL en el dashboard:** ws://127.0.0.1:18790

## Verificar que funciona

```bash
curl http://localhost:18789
```

O con puerto alternativo: `curl http://127.0.0.1:18790`. Debe mostrar la UI o devolver HTML.

---

## Acceso desde la VM (Tailscale) — nodo OpenClaw

Si la VM Windows tiene Tailscale y los tags están configurados, la VM puede conectar el nodo OpenClaw al gateway de la VPS por la red Tailscale (sin túnel SSH desde el PC).

### ACL en Tailscale (menor privilegio)

Regla para que **solo** la VM (`tag:umbral-vm`) acceda a la VPS (`tag:umbral-vps`) en puertos 18789 (OpenClaw) y 22 (SSH):

| Source       | Destination  | Port and protocol |
|-------------|---------------|--------------------|
| tag:umbral-vm | tag:umbral-vps | 22, 18789          |

En la UI de Tailscale: **Add rule** → Source: `tag:umbral-vm`, Destination: `tag:umbral-vps`, Ports: `22` y `18789` → Save grant.

### En la VM (Windows)

Con Tailscale activo y la ACL aplicada:

```powershell
openclaw node run --host srv1431451.tail0b266a.ts.net --port 18789 --tls
```

Sustituye el hostname por el de tu VPS en Tailscale (`*.ts.net`). Así el nodo de la VM se conecta al gateway de la VPS por Tailscale (Zero Trust, sin abrir puertos a internet).
