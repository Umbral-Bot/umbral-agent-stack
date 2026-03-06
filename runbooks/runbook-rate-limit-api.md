# Runbook: API rate limit (OpenClaw / modelo)

## Cuándo aparece

Mensaje **"⚠️ API rate limit reached. Please try again later."** al usar Rick por Telegram/OpenClaw: el proveedor del modelo (OpenAI, Anthropic, etc.) devolvió 429 (demasiadas peticiones o tokens en un periodo).

## Qué hacer

1. **Esperar 1–2 minutos** y volver a enviar el mensaje. Los límites suelen ser por minuto.
2. **Reintentar sin repetir en bucle.** Si Rick estaba enviando muchas respuestas seguidas (p. ej. por un bucle "End."), eso pudo gastar la cuota; al esperar se recupera.
3. **Comprobar fallbacks.** En `~/.openclaw/openclaw.json`, `agents.defaults.model` debe tener `primary` y `fallbacks`. Cuando el primary devuelve 429, OpenClaw puede usar el siguiente modelo de la lista; a veces el mensaje se muestra igual y el siguiente intento ya va a otro modelo.

## Config (VPS)

- Fallbacks ya configurados: Codex 5.3 (primary), luego GPT 5.4, Claude, Gemini, etc. No hace falta cambiar nada si ya están.
- Retry de canal (Telegram): en `channels.telegram` se puede añadir `retry: { attempts: 3, minDelayMs: 400, maxDelayMs: 30000 }` para reintentos al enviar mensajes; no evita el 429 del **modelo**, pero ayuda en fallos transitorios del canal.

## Para Rick (workspace)

En el workspace de Rick (`~/.openclaw/workspace`) está la nota: si el usuario ve "API rate limit", responder que espere 1–2 min y reintente; el siguiente intento puede usar un modelo de respaldo.

## Referencias

- OpenClaw: [Model Failover](https://docs.openclaw.ai/concepts/model-failover), [Retry](https://docs.openclaw.ai/concepts/retry).
- Config referencia: `docs/openclaw-config-reference-2026-03.json5`.
