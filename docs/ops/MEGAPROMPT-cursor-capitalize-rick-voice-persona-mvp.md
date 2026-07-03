MEGAPROMPT — Cursor (lead) · Capitalizar Rick voz MVP + persona hablada
Versión: RICK-VOICE-CAP-v1 · 2026-07-02
Prioridad: medium · puede ir en este sprint o el siguiente

================================================================================
ROL
================================================================================
Sos Cursor lead en C:\GitHub\umbral-agent-stack-copilot (o clone Cursor equivalente).
Capitalizás en repo lo ya operativo en VPS. NO rehacés smoke VPS ni runtime.

================================================================================
LECTURA OBLIGATORIA
================================================================================
1. .agents/tasks/2026-07-02-003-rick-voice-tts-mvp-restart-smoke.md  (done VPS)
2. .agents/tasks/2026-07-02-004-capitalize-rick-voice-persona-mvp.md (esta task)
3. .agents/board.md — sección Rick voz MVP
4. scripts/sync_openclaw_workspace_governance.py
5. docs/ops/MEGAPROMPT-rick-voice-realtime-phase2.md (solo deuda Fase 2)

================================================================================
YA OPERATIVO EN VPS — NO REHACER
================================================================================
- Push-to-talk Telegram: STT + TTS inbound (es-CL-LorenzoNeural) — smoke OK
- Fallbacks LLM: kimi-k2.5, vertex — scripts/ops/patch-openclaw-voice-fallbacks.py
- Persona hablada en ~/.openclaw/workspace/:
  VOICE.md · SOUL regla 21 · AGENTS regla 28 · IDENTITY CEO+voz

================================================================================
PREFLIGHT REPO
================================================================================
cd C:\GitHub\umbral-agent-stack-copilot
git fetch origin main
git checkout main
git pull --ff-only origin main
git checkout -b cursor/rick-voice-capitalize-mvp

git diff origin/main -- openclaw/workspace-templates/ openclaw/workspace-agent-overrides/main/ scripts/ops/ docs/ops/

Si el diff está vacío pero VPS tiene cambios no reflejados → documentar gap en task Log;
pedir a David/Copilot-VPS export controlado de archivos canónicos (sin secretos).

================================================================================
SLICE (orden)
================================================================================
1. REVISAR DIFF vs main en:
   - openclaw/workspace-templates/
   - openclaw/workspace-agent-overrides/main/
   - scripts/ops/  (incl. patch-openclaw-voice-fallbacks.py)
   - docs/ops/

2. VERSIONAR CANÓNICOS (commit solo con autorización David):
   - VOICE.md en templates (y override main si aplica)
   - Reglas SOUL/AGENTS/IDENTITY alineadas a VPS
   - patch-openclaw-voice-fallbacks.py si falta en repo
   - Sin secretos · sin openclaw.json live · sin auth-profiles

3. RUNBOOK: docs/ops/rick-voice-telegram-mvp-runbook.md
   - Config voz Telegram (LorenzoNeural)
   - Smoke push-to-talk
   - Persona hablada (VOICE/SOUL/AGENTS/IDENTITY)
   - /reset si sesión vieja no carga persona
   - Cuándo aplicar patch-openclaw-voice-fallbacks.py

4. GOVERNANCE SYNC — VOICE.md
   - Revisar scripts/sync_openclaw_workspace_governance.py
   - Añadir VOICE.md al sync del workspace `main` si no está
   - Documentar dry-run: python scripts/sync_openclaw_workspace_governance.py --dry-run
   - NO ejecutar --execute en VPS desde Cursor salvo delegación explícita

5. DEUDA FASE 2 (solo doc, no implementar):
   - Referenciar docs/ops/MEGAPROMPT-rick-voice-realtime-phase2.md
   - Azure gpt-realtime + web Tailscale · NO llamada TG bot

6. CIERRE
   - Log en task 2026-07-02-004
   - Board → done
   - PR a main si David autoriza commit

================================================================================
KILL-SWITCHES
================================================================================
- No tocar model.primary
- No userbot Telegram
- No reiniciar gateway salvo necesidad
- No re-smoke VPS salvo regresión reportada

================================================================================
RESPUESTA A DAVID
================================================================================
RICK_VOICE_CAPITALIZE_<READY|GAP|BLOCKED> | files=N | sync_voice=ok|pending | runbook=ok|pending
