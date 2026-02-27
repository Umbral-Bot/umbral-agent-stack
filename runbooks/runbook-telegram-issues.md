# Runbook: Problemas de Telegram

## Bot no responde

1. Verificar que Telegram está habilitado:
   ```bash
   openclaw status --all | grep -i telegram
   ```

2. Verificar sender ID en allowlist:
   - Revisar config de OpenClaw, sección channels/telegram.
   - El ID debe ser numérico (no username).

3. Revisar logs:
   ```bash
   journalctl --user -u openclaw -f | grep -i telegram
   ```

## Error 409 — getUpdates conflict

**Solo una instancia del bot puede hacer polling.**

1. Verificar que NO hay instancia en Windows:
   ```powershell
   # En Windows: si OpenClaw corre localmente con Telegram, detenerlo
   ```

2. Reiniciar en VPS:
   ```bash
   systemctl --user restart openclaw
   ```

## Error 429 — Too Many Requests

**Telegram aplica rate-limiting en setMyCommands.**

1. **Esperar** el tiempo indicado (generalmente 60s).
2. **No reiniciar en loop** — empeora el rate-limiting.
3. Verificar después de esperar:
   ```bash
   openclaw status --all
   ```

## Bot recibe mensajes pero no responde

1. Verificar que los modelos LLM están configurados:
   ```bash
   openclaw models status
   ```

2. Verificar que hay un provider activo con auth válido.

3. Revisar logs de error:
   ```bash
   journalctl --user -u openclaw --no-pager | grep -i error | tail -20
   ```
