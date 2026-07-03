MEGAPROMPT — Rick voz Fase 2 · Azure gpt-realtime + web Tailscale (DEFERIDO)
Versión: RICK-VOICE-PHASE2-v0 · 2026-07-02
Estado: deuda registrada · NO ejecutar en MVP Fase 1

================================================================================
CONTEXTO
================================================================================
Fase 1 (MVP) cerrada en VPS: Telegram push-to-talk STT/TTS + persona hablada.
Task capitalización repo: 2026-07-02-004-capitalize-rick-voice-persona-mvp.md

================================================================================
FASE 2 — ALCANCE (futuro)
================================================================================
- Azure OpenAI **gpt-realtime** (audio bidireccional / baja latencia)
- Exposición web vía **Tailscale** (acceso controlado)
- **NO** llamada directa desde bot Telegram en Fase 2 inicial
- Separar trust boundary: TG MVP (Fase 1) vs realtime web (Fase 2)

================================================================================
PRECONDICIONES ANTES DE ARRANCAR FASE 2
================================================================================
- [ ] Fase 1 capitalizada en repo + runbook
- [ ] Gate David explícito (G-VOICE-2)
- [ ] ADR breve o sección en runbook Fase 2
- [ ] Smoke gpt-realtime en entorno aislado (no prod gateway)
- [ ] Revisión coste/latencia vs LorenzoNeural TTS actual

================================================================================
FUERA DE ALCANCE FASE 2 (inicial)
================================================================================
- Userbot Telegram
- Cambiar model.primary del gateway sin gate
- Reemplazar MVP Telegram push-to-talk

================================================================================
REFERENCIAS
================================================================================
- VPS tests realtime previos: docs/audits/vps-test-results-2026-03-08.md
- Recurso Azure canónico UAS (crear si no existe): `oai-umbral-agents-prod` @ `rg-umbral-agents-prod` — ver `docs/ops/azure-openai-umbral-agents-provisioning.md`
