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

> ⚠️ **secret-output-guard (B2):** `openclaw models status` re-emite un
> fingerprint parcial de la credencial Google Vertex en cada corrida. Un prefijo
> enmascarado basta para correlacionar en audit logs y queda en transcripts.
> **Nunca** captures su salida cruda a chat/logs/evidencia: filtrala siempre por
> el redactor reproducible del repo.

```bash
# Salida saneada (fingerprints parciales → [REDACTED]):
openclaw models status 2>&1 | python3 ~/umbral-agent-stack/scripts/vps/secret_output_filter.py
```

El filtro (`scripts/vps/secret_output_filter.py`, con test en
`tests/test_secret_output_filter.py`) reemplaza valores tipo credencial por
`[REDACTED]` sin tocar el texto normal (nombres de perfil, model ids,
timestamps). No lee el auth store ni rota nada — es defensa conductual sobre la
salida visible. Ver la skill `secret-output-guard` ("Tool-emitted partial
leaks") y `docs/plans/tanda-b-security-execution-plan-2026-07-19.md` §B2.

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
