# OpenClaw Config Notes

## Archivos de configuración en producción (VPS)

| Archivo | Ubicación | Propósito |
|---------|-----------|-----------|
| `env` | `~/.config/openclaw/env` | Variables de entorno (WORKER_URL, WORKER_TOKEN, etc) |
| `openclaw.service` | `~/.config/systemd/user/openclaw.service` | Unit systemd |
| OpenClaw config | Gestionado por `openclaw configure` | Config principal de OpenClaw |

## Plantillas en este repo

- `env.template` → Copiar a `~/.config/openclaw/env` y rellenar.
- `systemd/openclaw.service.template` → Copiar o adaptar para systemd.

## Seguridad

- `env` NUNCA se versiona (está en `.gitignore`).
- Permisos: `chmod 600 ~/.config/openclaw/env`.
- Rotación de tokens: generar con `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`.

## Worker Scripts

- `bin/worker-run` — Envía tarea completa (JSON completo).
- `bin/worker-call` — Wrapper que construye JSON a partir de task + input.
- Ambos requieren `WORKER_URL` y `WORKER_TOKEN` en el entorno.
- Hacer ejecutables: `chmod +x bin/worker-run bin/worker-call`.
