---
id: "2026-05-19-001"
title: "Runtime check: sistema-editorial-rick, bandeja-de-revisión-rick, Granola V2 (CORE-Q2 sistemas)"
status: assigned
assigned_to: copilot
created_by: copilot-chat-notion-governance
priority: high
sprint: Q2-2026
created_at: "2026-05-19"
updated_at: "2026-05-19"
---

## Contexto previo

`notion-governance@agents/governance-personal-david-2026-05-18` (commit
`b3efe03`) ejecutó O16.5 + O16.6 y consolidó en
`docs/audits/2026-05-19-O16.6-governed-reading.md` 3 grupos cuya situación
runtime no se puede verificar desde el repo de governance:

1. **sistema-editorial-rick** (O14) — 4 nodos
2. **bandeja-de-revision-rick** (O14 writer activo) — 3 nodos
3. **transcripciones-granola** (O8e cron) — 3 nodos

Releé la regla **VPS Reality Check Rule** en
`.github/copilot-instructions.md` (commit `fbc5dae`, 2026-05-04) antes de
empezar.

## Objetivo

Reportar para cada uno de los 3 sistemas:

- ¿Sigue activo el cron/writer/loop en la VPS? (`systemctl status`,
  `crontab -l`, `journalctl --since "7 days ago"`)
- ¿Está escribiendo a Notion (DB target) en los últimos 7 días?
- ¿Hay drift entre código en repo y proceso corriendo (PID start time vs git
  log)?

## Procedimiento mínimo

```bash
cd ~/umbral-agent-stack && git pull origin main

# 1. sistema-editorial-rick
systemctl status sistema-editorial-rick 2>/dev/null || systemctl --user status sistema-editorial-rick
journalctl -u sistema-editorial-rick --since "7 days ago" --no-pager | tail -60

# 2. bandeja-de-revision-rick (writer)
crontab -l | grep -i "bandeja\|revision\|rick"
ls -lat ~/umbral-agent-stack/logs/bandeja-revision-rick/ 2>/dev/null | head -10

# 3. Granola V2 cron
crontab -l | grep -i "granola\|transcripcion"
journalctl --user --since "7 days ago" --no-pager | grep -i granola | tail -40
```

## Criterios de aceptación

- [ ] Para cada uno de los 3 sistemas: bloque "Repo dice X" + "VPS muestra Y"
      explícito.
- [ ] Si alguno no está activo, anotar última escritura conocida (fecha + log
      file) ANTES de proponer reinicio.
- [ ] **NO** reiniciar nada en este pase. Sólo diagnóstico.

## Antipatrones prohibidos

- Hacer `grep` al repo y declarar "está activo" sin journalctl.
- Asumir cron está corriendo porque el archivo systemd existe.
- Decir "todo OK" sin evidencia de escritura a Notion en últimos 7d.

## Referencias

- Trigger: `notion-governance@agents/governance-personal-david-2026-05-18` commit `b3efe03`
- Governed reading: `docs/audits/2026-05-19-O16.6-governed-reading.md` §C
- Governed outcome: `docs/audits/2026-05-19-O16.6-governed-outcome.md`
- Skill aplicada: `notion-governance/.agents/skills/delegate-to-copilot-vps/SKILL.md`

## Log

(crear al iniciar)
