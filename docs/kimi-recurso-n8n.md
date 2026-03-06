# Kimi-K2.5 como recurso para n8n y automatizaciones

Kimi (Azure Cognitive Services) está configurado como **recurso solo para uso por API**, no como modelo seleccionable en el chat de OpenClaw/Telegram. Rick puede usarlo en automatizaciones con n8n o desde scripts en la VPS.

## Cuándo usar este recurso

- Flujos n8n que necesiten generar texto con un LLM (resúmenes, clasificación, extracción).
- Scripts o cron en la VPS que llamen a Kimi por HTTP.
- Cualquier automatización que requiera el modelo Kimi-K2.5 sin pasar por el chat de OpenClaw.

## Endpoint y autenticación

- **URL:** `https://cursor-api-david.cognitiveservices.azure.com/openai/deployments/Kimi-K2.5/chat/completions?api-version=2024-05-01-preview`
- **Método:** POST
- **Headers:**
  - `Content-Type: application/json`
  - `api-key: <KIMI_AZURE_API_KEY>` (la clave está en `~/.config/openclaw/env` o `~/.openclaw/.env` en la VPS; en n8n usar variable/credencial que apunte a ese valor)

## Cuerpo de la petición (OpenAI-compatible)

```json
{
  "model": "Kimi-K2.5",
  "messages": [
    { "role": "user", "content": "Tu prompt aquí." }
  ],
  "max_tokens": 1024,
  "temperature": 0.7
}
```

Kimi puede devolver la respuesta en `reasoning_content` además de (o en lugar de) `content`. Al leer la respuesta, comprobar ambos campos y usar el que venga relleno.

## Uso en n8n (VPS)

1. **Credencial:** En n8n, crear una credencial (o variable de workflow) con el valor de `KIMI_AZURE_API_KEY`. En la VPS ese valor está en `~/.config/openclaw/env` (línea `export KIMI_AZURE_API_KEY=...`). No commitear la clave.
2. **Nodo HTTP Request:** Añadir un nodo "HTTP Request":
   - Method: POST
   - URL: `https://cursor-api-david.cognitiveservices.azure.com/openai/deployments/Kimi-K2.5/chat/completions?api-version=2024-05-01-preview`
   - Headers: `api-key` = valor de la credencial/variable.
   - Body: JSON como el de arriba (mensajes, max_tokens, temperature).
3. **Respuesta:** El JSON devuelto tiene `choices[0].message.content` y a veces `choices[0].message.reasoning_content`; usar el que venga relleno para el siguiente nodo.

## Probar desde la VPS (sin n8n)

```bash
cd ~/umbral-agent-stack
source ~/.config/openclaw/env
python3 scripts/test_kimi_azure.py
```

El script carga `KIMI_AZURE_API_KEY` desde el env y hace una petición de prueba.

## Indicaciones para Rick

- Kimi está disponible como **recurso HTTP** para automatizaciones (n8n, scripts). No está asignado a agentes del chat; los agentes siguen con Codex 5.3, GPT 5.4, Gemini, etc.
- Cuando diseñes o ejecutes flujos en n8n que necesiten un LLM, puedes usar este endpoint con la clave de `~/.config/openclaw/env` (o la variable que se inyecte en n8n).
- Config y clave: ver también `docs/openclaw-rick-skill-y-modelos.md` (sección 5).
