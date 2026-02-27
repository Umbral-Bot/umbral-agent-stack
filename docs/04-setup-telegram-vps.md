# 04 — Setup Telegram en VPS

## Habilitar Plugin Telegram

```bash
openclaw plugins enable telegram
```

## Configurar Bot Token

```bash
openclaw configure
```

En la sección `channels` / `telegram`, configurar:

```yaml
telegram:
  token: "CHANGE_ME_TELEGRAM_BOT_TOKEN"
  allowlist:
    - "CHANGE_ME_NUMERIC_SENDER_ID"
  dm_policy: "allowlist"
```

> **⚠️ IMPORTANTE**: Usar el ID numérico del sender, NO el username. Puedes obtener tu ID con bots como `@userinfobot` o revisando los logs de OpenClaw.

## Verificar

```bash
openclaw status --all
```

Debe mostrar Telegram como **OK** / **connected**.

## Troubleshooting

### 409 — getUpdates conflict

```
Telegram error: 409 Conflict: terminated by other getUpdates request
```

**Causa**: Hay más de una instancia del bot corriendo (por ejemplo, una en VPS y otra en Windows).

**Solución**:
1. Detener TODAS las instancias del bot excepto una.
2. En Windows, si hay una instancia local: detenerla.
3. Telegram solo permite UN cliente haciendo polling a la vez.

```bash
# En Windows (si corre localmente): detener
# En VPS: reiniciar
systemctl --user restart openclaw
```

### 429 — Too Many Requests (setMyCommands)

```
429 Too Many Requests: retry after 60
```

**Causa**: Se reinició OpenClaw demasiadas veces en poco tiempo, y Telegram aplica rate-limiting en `setMyCommands`.

**Solución**:
1. **Esperar** el tiempo indicado (generalmente 60 segundos).
2. **No reiniciar en loop** — cada reinicio intenta registrar comandos nuevamente.
3. El servicio debería recuperarse solo después del cooldown.

### Bot no responde a mensajes

1. Verificar que el sender ID está en `allowlist`.
2. Verificar que `dm_policy` es `allowlist` y no `block_all`.
3. Revisar logs:
   ```bash
   journalctl --user -u openclaw -f | grep -i telegram
   ```

### Doble instancia — política

> **Regla**: Telegram corre SOLO en VPS. No habilitar Telegram en Windows para evitar conflictos 409.
