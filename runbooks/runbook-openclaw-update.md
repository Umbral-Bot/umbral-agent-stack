# Runbook: Actualizar OpenClaw

## Pre-actualización

```bash
# Verificar versión actual
openclaw --version

# Backup de config
cp ~/.config/openclaw/env ~/.config/openclaw/env.bak
```

## Actualizar

```bash
# Seguir instrucciones oficiales de actualización de OpenClaw
# (el comando exacto depende de la instalación)
# Ejemplo genérico:
openclaw update
```

## Post-actualización

```bash
# Reiniciar servicio
systemctl --user restart openclaw

# Verificar
systemctl --user status openclaw
openclaw status --all
openclaw models status
```

## Rollback (si falla)

```bash
# Restaurar config
cp ~/.config/openclaw/env.bak ~/.config/openclaw/env

# Reiniciar
systemctl --user restart openclaw
```

## Notas

- Siempre hacer backup del env file antes de actualizar.
- Verificar que Telegram sigue funcionando después de la actualización.
- Verificar conectividad al worker.
