# OpenClaw Config Notes

## Archivos de configuracion en produccion (VPS)

| Archivo | Ubicacion | Proposito |
|---------|-----------|-----------|
| `env` | `~/.config/openclaw/env` | Variables de entorno (`WORKER_URL`, `WORKER_TOKEN`, etc.) |
| `openclaw-gateway.service` | `~/.config/systemd/user/openclaw-gateway.service` | Unit systemd canonica del gateway |
| `openclaw.service` | `~/.config/systemd/user/openclaw.service` | Unit legacy; no usar en nuevas instalaciones |
| OpenClaw config | Gestionado por `openclaw configure` | Config principal de OpenClaw |

## Plantillas en este repo

- `env.template` -> Copiar a `~/.config/openclaw/env` y rellenar.
- `systemd/openclaw-gateway.service.template` -> Copiar o adaptar para systemd.
- `systemd/openclaw.service.template` -> Legacy, solo referencia historica.

## Seguridad

- `env` nunca se versiona (esta en `.gitignore`).
- Permisos: `chmod 600 ~/.config/openclaw/env`.
- Rotacion de tokens: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`.

## Worker scripts

- `bin/worker-run` -> Envia tarea completa (JSON completo).
- `bin/worker-call` -> Wrapper que construye JSON a partir de `task` + `input`.
- Ambos requieren `WORKER_URL` y `WORKER_TOKEN` en el entorno.
- Hacer ejecutables: `chmod +x bin/worker-run bin/worker-call`.
