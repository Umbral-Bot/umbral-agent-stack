# 19 — OpenClaw y cuota Anthropic (Claude)

## Problema

Cuando OpenClaw usa la cuenta de Anthropic (Claude) y se agotan los tokens de la ventana, el LLM puede **congelarse**: las peticiones no responden y el gateway deja de operar. Reiniciar el servicio no basta si la config sigue apuntando a Claude.

## Enfoque recomendado: **preventivo + reactivo**

| Enfoque | Cuándo | Qué hace |
|--------|--------|----------|
| **Preventivo** | Antes de llegar al límite | Cambiar el modelo de OpenClaw de Claude a un fallback (p. ej. OpenAI/Codex) cuando el uso de Claude supera un umbral (p. ej. 75–80 %). Así OpenClaw **nunca** usa Claude cerca del tope y no se congela. |
| **Reactivo** | Cuando ya se agotó o se detecta congelado | Script que cambia la config de OpenClaw al modelo fallback y reinicia el servicio. Sirve como red de seguridad si el preventivo no se ejecutó a tiempo. |

**Recomendación:** usar **los dos**.

1. **Preventivo** como medida principal: cron (o timer systemd) que ejecuta el script de comprobación cada X minutos; si la cuota de Claude supera el umbral configurado, el script cambia OpenClaw al modelo fallback y reinicia. Así se evita el freeze.
2. **Reactivo** como respaldo: el mismo script con opción `--force` (o invocado por un health check que detecte “OpenClaw no responde”) para forzar el cambio a fallback y reinicio cuando ya hay problema.

No conviene depender solo del reactivo: si el proceso está colgado, puede costar más recuperar el servicio; con preventivo se cambia de modelo antes de llegar al límite.

## Implementación en este repo

Un solo script hace preventivo y reactivo:

- **`scripts/openclaw_quota_guard.py`**
  - **Preventivo:** Sin argumentos (o con `--check` solo para comprobar). Lee la cuota de `claude_pro` desde Redis (QuotaTracker). Si el uso ≥ umbral, actualiza `openclaw.json` al modelo fallback y reinicia el servicio systemd de usuario.
  - **Solo comprobar:** `--check` → exit 0 si hay que cambiar, exit 1 si no. Útil para cron que luego ejecute el mismo script sin `--check` para aplicar el cambio.
  - **Reactivo:** `--force` → cambia a fallback y reinicia sin mirar Redis (para cuando OpenClaw ya está congelado o se acaban los tokens).

Configuración (variables de entorno):

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `REDIS_URL` | Redis del QuotaTracker | `redis://localhost:6379/0` |
| `OPENCLAW_QUOTA_SWITCH_THRESHOLD` | Umbral 0.0–1.0 para cambiar antes del límite | `0.75` |
| `OPENCLAW_FALLBACK_MODEL` | Modelo al que cambiar (formato OpenClaw) | `openai-codex/gpt-5.3-codex` |
| `OPENCLAW_CONFIG_PATH` | Ruta a `openclaw.json` | `~/.openclaw/openclaw.json` |
| `OPENCLAW_MODEL_JSON_KEY` | Clave del modelo en el JSON (anidada con punto) | `agents.defaults.model.primary` |

Ejemplo de cron (preventivo, cada 15 min):

```bash
OPENCLAW_QUOTA_SWITCH_THRESHOLD=0.75 OPENCLAW_FALLBACK_MODEL=openai-codex/gpt-5.3-codex REDIS_URL=redis://localhost:6379/0 PYTHONPATH=/home/rick/umbral-agent-stack python3 /home/rick/umbral-agent-stack/scripts/openclaw_quota_guard.py
```

Ejemplo reactivo (OpenClaw congelado):

```bash
OPENCLAW_FALLBACK_MODEL=openai-codex/gpt-5.3-codex python3 scripts/openclaw_quota_guard.py --force
```

**Nota:** Si `openclaw.json` usa JSON5 (comentarios), puede fallar el parseo con `json` estándar. En ese caso revisar la clave con un editor y, si hace falta, usar la misma ruta en otro formato o un script que soporte JSON5.

## Resumen

- **Mejor:** cambiar el modelo **antes** de llegar al límite (preventivo) para que OpenClaw no use Claude cuando la cuota está alta y no se congele.
- **Además:** tener un script que, cuando ya se acabó la cuota o OpenClaw está congelado, cambie a fallback y reinicie (reactivo).
