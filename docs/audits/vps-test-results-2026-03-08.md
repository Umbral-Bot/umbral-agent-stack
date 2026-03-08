# VPS Test Results — 2026-03-08

> Ejecutado por: Claude Code (tarea 100).
> SSH a `rick@srv1431451`.

---

## Fix P0: Token Mismatch — RESUELTO ✓

**Causa raíz:** El Dispatcher arrancó el 2026-03-04 con token `!EN6V4zt...` (25 chars).
El env file se actualizó entre el 4 y el 7 de marzo (token nuevo `64e38901...`, 48 chars),
pero el Dispatcher nunca se reinició — seguía usando el token viejo en cada request.

**Fix aplicado en VPS (2026-03-08 ~12:48 UTC):**
```bash
pkill -f "dispatcher.service"
set -a && source ~/.config/openclaw/env && set +a
source .venv/bin/activate
PYTHONPATH=~/umbral-agent-stack nohup python3 -m dispatcher.service >> logs/dispatcher.log 2>&1 &
```

**Verificación E2E:**

| Check | Resultado |
|-------|-----------|
| Dispatcher token = Worker token | ✓ ambos 48 chars, `64e38901...` |
| POST /run con env token | HTTP 200 ✓ |
| `ping` via TaskQueue.enqueue() | `task_completed` en OpsLog ✓ |
| VM health check (100.109.16.40:8088) | HTTP 200 ✓ |
| OpsLog timestamp | 2026-03-08T15:48:49 ✓ |

**Nota para el futuro:** el supervisor.sh verifica que el proceso existe pero no que
el token sea correcto. Si se actualiza el env, reiniciar el Dispatcher manualmente.
Posible mejora: agregar `POST /run ping` como health-check funcional en supervisor.

---

## Test 1: test_gpt_rick_agent.py — FALLA (keys no configuradas)

```
ERROR: GPT_RICK_API_KEY o AZURE_OPENAI_API_KEY no definida.
```

**Estado:** `AZURE_OPENAI_API_KEY` y `GPT_RICK_API_KEY` no existen en `~/.config/openclaw/env` del VPS.
El VPS solo tiene `KIMI_AZURE_API_KEY`.

**Qué se necesita configurar:**

| Variable | Dónde obtenerla | Descripción |
|----------|----------------|-------------|
| `AZURE_OPENAI_API_KEY` | Azure Portal → recurso `cursor-api-david` → Keys | Key del Azure AI Foundry / Cognitive Services |
| `GPT_RICK_API_KEY` | Mismo recurso (puede ser la misma key) | Key específica para el agente Gpt-Rick |
| `AZURE_OPENAI_ENDPOINT` | `https://cursor-api-david.services.ai.azure.com` | Ya definido por defecto en el script |

**Acción:** David debe agregar estas vars en `~/.config/openclaw/env` del VPS:
```bash
export AZURE_OPENAI_API_KEY=<key-del-portal>
export GPT_RICK_API_KEY=<misma-o-distinta-key>
```

El script ya tiene el endpoint correcto hardcodeado como default
(`cursor-api-david.services.ai.azure.com`), solo falta la API key.

---

## Test 2: test_gpt_realtime_audio.py — FALLA (misma causa)

```
ERROR: AZURE_OPENAI_API_KEY no definida.
```

**Estado:** Misma causa que Test 1. Una vez agregada `AZURE_OPENAI_API_KEY`, este test
debería funcionar si el deployment `gpt-realtime` existe en el recurso
`cursor-api-david.cognitiveservices.azure.com`.

**Qué verificar post-configuración:**

- Que el deployment se llame exactamente `gpt-realtime` (configurable via `--deployment`)
- Que el recurso Cognitive Services tenga habilitado TTS/realtime
- Salida esperada: `assets/audio/rick_audio_prueba.wav`

---

## Resumen de Acciones

| Item | Estado | Acción requerida |
|------|--------|-----------------|
| Token mismatch P0 | ✅ RESUELTO | Dispatcher reiniciado |
| E2E Redis→Dispatcher→Worker | ✅ FUNCIONAL | Ninguna |
| test_gpt_rick_agent.py | ❌ Sin key | David: agregar `AZURE_OPENAI_API_KEY` en VPS env |
| test_gpt_realtime_audio.py | ❌ Sin key | Ídem + verificar deployment `gpt-realtime` existe |
| VM SSH habilitado | ❌ Pendiente | David: habilitar desde Hyper-V GUI |
| Dispatcher restart automático al cambiar env | ⚠️ Mejora futura | Cursor: agregar health-check funcional en supervisor.sh |
