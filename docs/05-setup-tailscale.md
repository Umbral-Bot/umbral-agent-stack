# 05 — Setup Tailscale

## Qué es Tailscale

Tailscale crea una red privada mesh (WireGuard) entre tus dispositivos. Permite que el VPS y la máquina Windows se comuniquen por IPs privadas sin exponer puertos a internet.

## Instalación en VPS (Ubuntu)

```bash
# Instalar
curl -fsSL https://tailscale.com/install.sh | sh

# Iniciar y autenticar (con SSH habilitado)
sudo tailscale up --ssh

# Verificar estado
tailscale status

# Obtener IP v4 asignada
tailscale ip -4
```

> Anotar la IP Tailscale del VPS (ej: `100.x.y.z`).

## Instalación en Windows

1. Descargar Tailscale desde [tailscale.com/download](https://tailscale.com/download).
2. Instalar y hacer login con la misma cuenta que el VPS.
3. Obtener IP:
   ```powershell
   tailscale ip -4
   ```

> Anotar la IP Tailscale de Windows (ej: `100.a.b.c`).

## Validación de Conectividad

### Desde Windows → VPS

```powershell
ping VPS_TAILSCALE_IP
```

### Desde VPS → Windows

```bash
ping WINDOWS_TAILSCALE_IP
```

### Desde VPS → Worker en Windows

```bash
curl http://WINDOWS_TAILSCALE_IP:8088/health
```

Debe devolver:
```json
{"ok": true, "ts": 1740000000}
```

## Uso en el Sistema

| Conexión | Mecanismo | Puerto |
|----------|-----------|--------|
| VPS → Worker | Tailscale | 8088 |
| PC → Control UI | SSH tunnel | 18789, 18791 |
| PC → VPS shell | SSH directo | 22 |

## Nota sobre Control UI

- **Seguir usando SSH tunnel** para acceder a la Control UI (puertos 18789/18791).
- Tailscale es para la conectividad VPS ↔ Worker, no para exponer la UI.
- Si se necesita acceder a la UI vía Tailscale, se puede, pero SSH tunnel es preferido por auditabilidad.

## Troubleshooting

### Tailscale no conecta

```bash
# Verificar servicio
sudo systemctl status tailscaled

# Reiniciar
sudo systemctl restart tailscaled

# Re-autenticar
sudo tailscale up
```

### Ping funciona pero curl no

- Verificar que el firewall de Windows permite el puerto 8088.
- Verificar que Uvicorn escucha en `0.0.0.0` (no `127.0.0.1`).
- Verificar que el worker está corriendo.

### IPs cambiaron

Tailscale asigna IPs estables, pero si hay problemas:

```bash
tailscale status  # Ver IPs actuales
tailscale ip -4   # Ver tu propia IP
```
