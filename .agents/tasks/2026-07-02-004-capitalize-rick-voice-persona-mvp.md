---
id: "2026-07-02-004"
title: "Capitalizar Rick voz MVP + persona hablada en repo (templates, runbook, governance sync)"
status: assigned
assigned_to: cursor
created_by: cursor
priority: medium
sprint: rick-voice-mvp
created_at: "2026-07-02"
updated_at: "2026-07-02T19:40"
lead_ref: "2026-07-02-002-capitalize (nomenclatura lead)"
depends_on: "2026-07-02-003"
---

## Objetivo

Capitalizar en el repo lo ya operativo en VPS (Rick voz MVP + persona hablada) sin rehacer runtime ni tocar secretos.

## Contexto previo (NO rehacer)

Ver task `2026-07-02-003-rick-voice-tts-mvp-restart-smoke.md` — smoke VPS OK.

MEGAPROMPT: `docs/ops/MEGAPROMPT-cursor-capitalize-rick-voice-persona-mvp.md`

## Slice Cursor (lead)

1. Revisar diff local vs `origin/main` en:
   - `openclaw/workspace-templates/`
   - `openclaw/workspace-agent-overrides/main/`
   - `scripts/ops/`
   - `docs/ops/`
2. Commit **solo cuando David autorice** (sin secretos, sin `openclaw.json` live)
3. Runbook breve voice MVP Telegram (config, smoke, persona, `/reset` si sesión vieja)
4. Verificar/extender `scripts/sync_openclaw_workspace_governance.py` para incluir **`VOICE.md`** en sync main
5. Registrar deuda Fase 2: Azure gpt-realtime + web Tailscale (NO llamada TG bot) — `docs/ops/MEGAPROMPT-rick-voice-realtime-phase2.md`
6. Actualizar board + esta task → `done` cuando capitalizado

## Criterios de aceptación

- [ ] Diff revisado y listo para commit (o PR) con archivos canónicos identificados
- [ ] `docs/ops/rick-voice-telegram-mvp-runbook.md` creado
- [ ] `scripts/ops/patch-openclaw-voice-fallbacks.py` versionado (si existe en VPS checkout / diff local)
- [ ] `VOICE.md` + reglas SOUL/AGENTS/IDENTITY reflejadas en templates/overrides repo-side
- [ ] Governance sync incluye `VOICE.md` (dry-run documentado)
- [ ] Deuda Fase 2 referenciada, sin implementar
- [ ] Board actualizado; task → `done`

## Kill-switches

- No tocar `model.primary`
- No userbot Telegram
- No reiniciar gateway salvo necesidad
- No commitear secretos ni `openclaw.json` live de VPS

## Log

### [cursor] 2026-07-02 19:40
Encargo formalizado. MVP voz ya funciona en producción VPS; slice es capitalización repo-side.
