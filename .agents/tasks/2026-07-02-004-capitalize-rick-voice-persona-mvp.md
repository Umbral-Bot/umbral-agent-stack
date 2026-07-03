---
id: "2026-07-02-004"
title: "Capitalizar Rick voz MVP + persona hablada en repo (templates, runbook, governance sync)"
status: done
assigned_to: cursor
created_by: cursor
priority: medium
sprint: rick-voice-mvp
created_at: "2026-07-02"
updated_at: "2026-07-03T08:55"
lead_ref: "2026-07-02-002-capitalize (nomenclatura lead)"
depends_on: "2026-07-02-003"
---

## Objetivo

Capitalizar en el repo lo ya operativo en VPS (Rick voz MVP + persona hablada) sin rehacer runtime ni tocar secretos.

## Contexto previo (NO rehacer)

Ver task `2026-07-02-003-rick-voice-tts-mvp-restart-smoke.md` — smoke VPS OK.

MEGAPROMPT: `docs/ops/MEGAPROMPT-cursor-capitalize-rick-voice-persona-mvp.md`

## Criterios de aceptación

- [x] Diff revisado — canónicos ya en `main` (VOICE/SOUL/AGENTS/IDENTITY/patch); slice = runbook + sync
- [x] `docs/ops/rick-voice-telegram-mvp-runbook.md` creado
- [x] `scripts/ops/patch-openclaw-voice-fallbacks.py` versionado en main
- [x] `VOICE.md` + reglas SOUL/AGENTS/IDENTITY en templates/overrides repo-side
- [x] Governance sync incluye `VOICE.md` para workspace `main` + test
- [x] Deuda Fase 2 referenciada en runbook (`MEGAPROMPT-rick-voice-realtime-phase2.md`)
- [x] Board actualizado; task → `done`

## Kill-switches

- No tocar `model.primary`
- No userbot Telegram
- No reiniciar gateway salvo necesidad
- No commitear secretos ni `openclaw.json` live de VPS

## Log

### [cursor] 2026-07-02 19:40
Encargo formalizado. MVP voz ya funciona en producción VPS; slice es capitalización repo-side.

### [cursor] 2026-07-03
Preflight: `origin/main` @ fc42020c ya contenía VOICE.md, SOUL regla 21, AGENTS regla 28, IDENTITY CEO+voz, patch script, megaprompts. Drift VPS vs repo templates: **full** (VOICE/patch idénticos). Slice cerrado: runbook `rick-voice-telegram-mvp-runbook.md`, `MAIN_ONLY_TEMPLATE_FILES` + test sync VOICE.md, PR `cursor/rick-voice-capitalize-mvp`. Sync `--execute` en VPS: paso separado Copilot-VPS post-merge.
