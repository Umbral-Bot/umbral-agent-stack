---
id: "2026-07-02-003"
title: "Rick voz MVP — push-to-talk Telegram STT/TTS + fallbacks (VPS smoke)"
status: done
assigned_to: copilot-vps
created_by: cursor
priority: medium
sprint: rick-voice-mvp
created_at: "2026-07-02"
updated_at: "2026-07-02T19:40"
lead_ref: "2026-07-02-001-rick-voice (nomenclatura lead)"
---

## Objetivo

Dejar operativo en VPS el MVP de voz Rick vía Telegram push-to-talk (STT inbound + TTS outbound) y fallbacks LLM, con smoke OK.

## Contexto

Ejecutado en VPS por Copilot-VPS. **NO rehacer.** Esta task documenta el estado operativo ya alcanzado.

## Ya operativo en VPS (evidencia runtime)

- Push-to-talk Telegram: STT + TTS inbound con voz **`es-CL-LorenzoNeural`** — smoke OK
- Fallbacks LLM parcheados (`kimi-k2.5`, `vertex`) — script `scripts/ops/patch-openclaw-voice-fallbacks.py`
- Persona hablada desplegada en `~/.openclaw/workspace/`:
  - `VOICE.md`
  - `SOUL` regla 21
  - `AGENTS` regla 28
  - `IDENTITY` CEO + voz

## Criterios de aceptación

- [x] Audio Telegram → Rick responde con TTS LorenzoNeural
- [x] Fallbacks LLM aplicados sin romper gateway
- [x] Persona hablada cargada en workspace main

## Kill-switches (registrados)

- No tocar `model.primary`
- No userbot Telegram
- No reiniciar gateway salvo necesidad explícita

## Log

### [cursor] 2026-07-02 19:40
Task formalizada post-MVP VPS. Capitalización repo → task `2026-07-02-004-capitalize-rick-voice-persona-mvp.md`.
