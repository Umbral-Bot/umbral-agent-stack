# Runbook — Rick voz MVP (Telegram push-to-talk)

> Estado: operativo en VPS (smoke 2026-07-02). Repo = fuente de verdad para templates; VPS sync en paso separado.

## Qué es

Conversación por **turnos de voz** en Telegram (`@Rick_lot_bot`):

1. David envía **voice note** (no texto pegado).
2. OpenClaw transcribe (STT local / media pipeline).
3. Rick razona (LLM).
4. Si el input fue voz → TTS automático responde con audio (`messages.tts.auto = inbound`).

**No es** llamada en tiempo real. Los bots de Telegram no atienden llamadas de voz. Fase 2: ver `docs/ops/MEGAPROMPT-rick-voice-realtime-phase2.md`.

## Archivos canónicos (repo)

| Archivo | Rol |
|---------|-----|
| `openclaw/workspace-templates/VOICE.md` | Persona hablada |
| `openclaw/workspace-templates/SOUL.md` | Regla 21 presencia hablada |
| `openclaw/workspace-templates/AGENTS.md` | Regla 28 personaje en TTS |
| `openclaw/workspace-agent-overrides/main/IDENTITY.md` | CEO + línea voz |
| `scripts/ops/patch-openclaw-voice-fallbacks.py` | Fallbacks LLM para voz |

## Config runtime (VPS — referencia, no commitear)

En `~/.openclaw/openclaw.json`:

```json
"messages": {
  "tts": {
    "auto": "inbound",
    "provider": "microsoft",
    "providers": {
      "microsoft": {
        "enabled": true,
        "speakerVoice": "es-CL-LorenzoNeural",
        "lang": "es-CL",
        "outputFormat": "audio-24khz-48kbitrate-mono-mp3"
      }
    }
  }
}
```

Cambios en `openclaw.json` requieren `systemctl --user restart openclaw-gateway`.

## Smoke test (David)

1. Abrir chat directo con `@Rick_lot_bot`.
2. Mantener micrófono → grabar 5–10 s → enviar como **nota de voz**.
3. Esperar respuesta en **audio** (no solo texto).
4. El audio debe sonar natural: primera persona, sin prefijo `Rick:`, sin leer transcripción literal.

Si suena robótico o con prefijo `Rick:`:

- Escribir `/reset` o `/new` en Telegram (sesión vieja).
- Verificar que `VOICE.md` está en `~/.openclaw/workspace/` (sync governance).

## Sync repo → VPS (Copilot-VPS, post-merge)

```bash
cd ~/umbral-agent-stack
git pull --ff-only origin main
python3 scripts/sync_openclaw_workspace_governance.py --dry-run
python3 scripts/sync_openclaw_workspace_governance.py --execute
```

Debe incluir `main VOICE.md` (y `HEARTBEAT.md`, `IDENTITY.md` según overrides).

**Nota:** `SOUL.md` y `AGENTS.md` viven en workspace bootstrap; si hay drift, alinear manualmente desde templates o re-scp hasta automatizar.

## Fallbacks LLM (si audio dice error técnico)

```bash
python3 scripts/ops/patch-openclaw-voice-fallbacks.py
openclaw config validate
systemctl --user restart openclaw-gateway   # solo con autorización
```

Orden fallback `main`: gpt-5.4 → kimi-k2.5 → vertex gemini-3.1 → gpt-5.2-chat → openai gpt-5.4.

## Diagnóstico rápido

```bash
journalctl --user -u openclaw-gateway --since "10 min ago" --no-pager | tail -40
openclaw status --all
ls -la ~/.openclaw/media/inbound/*.ogg | tail -3
```

| Síntoma | Causa probable |
|---------|----------------|
| Solo texto, sin audio | Input fue texto, no voice note |
| Audio "LLM request failed" | Rate limit / fallback roto — ver patch |
| Prefijo "Rick:" en audio | Sesión vieja o VOICE.md no cargado — `/reset` + sync |
| Sin inbound .ogg | Voice note no llegó al gateway |

## Deuda Fase 2

Azure `gpt-realtime` + cliente web Tailscale para latencia <3 s. **No** userbot Telegram.

Ver: `docs/ops/MEGAPROMPT-rick-voice-realtime-phase2.md`
