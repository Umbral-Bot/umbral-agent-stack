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

## Verificar que funciona

```bash
curl http://localhost:18789
```

Debe mostrar la UI o devolver HTML.
