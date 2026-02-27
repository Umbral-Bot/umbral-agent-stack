# Runbook: Estado de OpenClaw

## Verificar servicio

```bash
systemctl --user status openclaw
```

## Estado detallado

```bash
openclaw status --all
```

## Estado de modelos

```bash
openclaw models status
```

## Logs recientes

```bash
journalctl --user -u openclaw -n 50 --no-pager
```

## Logs en vivo

```bash
journalctl --user -u openclaw -f
```

## Si está caído → reiniciar

```bash
systemctl --user restart openclaw
systemctl --user status openclaw
```

## Verificar puertos

```bash
ss -lntp | grep -E '18789|18791'
```

## OpenClaw congelado (cuota Anthropic/Claude agotada)

Si el LLM deja de responder porque se acabaron los tokens de Claude, el proceso puede quedar colgado. Reiniciar solo no basta si la config sigue usando Claude.

1. **Cambiar a modelo fallback y reiniciar (reactivo):**
   ```bash
   cd ~/umbral-agent-stack
   export OPENCLAW_FALLBACK_MODEL=openai-codex/gpt-5.3-codex   # o el modelo fallback que uses
   export OPENCLAW_CONFIG_PATH=~/.openclaw/openclaw.json
   PYTHONPATH=$(pwd) python3 scripts/openclaw_quota_guard.py --force
   ```
2. **Preventivo:** Configurar cron para ejecutar `openclaw_quota_guard.py` (sin `--force`) cada 15–30 min; así se cambia a fallback antes de llegar al límite. Ver [docs/19-openclaw-claude-quota.md](../docs/19-openclaw-claude-quota.md).
